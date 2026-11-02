#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub 主页审计 —— 六层状态 + 反模式检测 + 图片存活体检。

用法:
    python audit_profile.py <username>
    python audit_profile.py <username> --json report.json
    python audit_profile.py <username> --direct      # 强制不走代理
    python audit_profile.py <username> --no-net      # 只分析本地缓存的 README

退出码: 0 = 无阻断问题; 1 = 有「必须修」项。

只依赖标准库。token 优先取 --token，其次 GITHUB_TOKEN，再次 `gh auth token`。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

UA = "profile-polish-audit/1.0"
API = "https://api.github.com"


def harden_stdout() -> None:
    """Windows 中文环境下输出重定向到管道时编码是 cp936，
    打印 ✅/❌ 会抛 UnicodeEncodeError 中断整个审计。降级为替换字符。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

# ---------------------------------------------------------------- 反面模式清单
# (正则, 名称, 后果说明)
ANTI_PATTERNS: list[tuple[str, str, str]] = [
    (r"readme-typing-svg|readme-typing-svg\.herokuapp", "打字动画",
     "被多个来源点名为初级信号，且抢走唯一视觉焦点"),
    (r"komarev\.com/ghpvc|visitor-badge|hits\.seeyoufarm", "访客计数器",
     "零信息量，是最典型的业余特征"),
    (r"github-profile-trophy", "奖杯墙",
     "徽章墙变体，信息密度为零；且该服务实测 402"),
    (r"github-readme-stats\.vercel\.app", "github-readme-stats",
     "该服务实测 503 且上游已弃维护"),
    (r"metrics\.lecoq\.io", "metrics 卡片", "实测 500"),
    (r"capsule-render", "胶囊横幅", "存活但纯装饰，占掉首屏黄金位置"),
    (r"目前正在学习|currently learning|Currently Learning|正在学习", "「正在学习」清单",
     "3 个月后就变成谎话，且几乎没人回来删"),
    (r"(?i)\bHi there\b|👋", "「Hi there 👋」模板",
     "GitHub 自动生成的模板残留，一眼看出没重写"),
    (r"(?i)^#{1,3}\s*(About Me|关于我)\b", "「关于我」标题",
     "自我介绍不需要标题，直接写句子"),
]

# 已知第三方服务的域名 -> 存活状态（2026-11-01 实测，见 references/widget-liveness.md）
KNOWN_HOSTS = {
    "github-readme-stats.vercel.app": "503 已死",
    "github-profile-trophy.vercel.app": "402 已死",
    "metrics.lecoq.io": "500 已死",
    "streak-stats.demolab.com": "200 存活",
    "capsule-render.vercel.app": "200 存活",
    "readme-typing-svg.demolab.com": "200 存活",
    "skillicons.dev": "200 存活",
    "img.shields.io": "200 存活",
    "komarev.com": "200 存活（但不建议用）",
}


# ---------------------------------------------------------------- HTTP
class Fetcher:
    def __init__(self, token: str | None, use_proxy: bool = True):
        self.token = token
        handlers = []
        if not use_proxy:
            handlers.append(urllib.request.ProxyHandler({}))
        self.opener = urllib.request.build_opener(*handlers)

    def request(self, url: str, *, accept: str | None = None,
                retries: int = 3, timeout: int = 15) -> tuple[int, bytes, dict]:
        last: Exception | None = None
        for i in range(retries):
            req = urllib.request.Request(url)
            req.add_header("User-Agent", UA)
            if accept:
                req.add_header("Accept", accept)
            if self.token and url.startswith(API):
                req.add_header("Authorization", f"Bearer {self.token}")
            try:
                with self.opener.open(req, timeout=timeout) as r:
                    return r.status, r.read(), dict(r.headers)
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 404):
                    return e.code, b"", dict(e.headers or {})
                last = e
            except Exception as e:  # noqa: BLE001 - 网络层什么都可能抛
                last = e
            time.sleep(1.2 * (i + 1))
        return 0, str(last).encode(), {}

    def json(self, path: str) -> dict | list | None:
        url = path if path.startswith("http") else API + path
        status, body, _ = self.request(url, accept="application/vnd.github+json")
        if status != 200:
            return None
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def head_ok(self, url: str) -> tuple[int, str]:
        status, _, headers = self.request(url, retries=2, timeout=12)
        return status, headers.get("Content-Type", "")


# ---------------------------------------------------------------- 取数
def get_token(cli: str | None) -> str | None:
    if cli:
        return cli
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    if os.environ.get("GH_TOKEN"):
        return os.environ["GH_TOKEN"]
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True,
                             text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:  # noqa: BLE001
        pass
    return None


def collect_user(f: Fetcher, user: str, raw: dict | None = None) -> dict:
    u = raw if raw is not None else (f.json(f"/users/{user}") or {})
    return {
        "login": u.get("login", user),
        "name": u.get("name") or "",
        "bio": u.get("bio") or "",
        "blog": u.get("blog") or "",
        "twitter": u.get("twitter_username") or "",
        "company": u.get("company") or "",
        "location": u.get("location") or "",
        "followers": u.get("followers", 0),
        "public_repos": u.get("public_repos", 0),
        "avatar": u.get("avatar_url", ""),
        "created_at": u.get("created_at", ""),
    }


PINNED_QUERY = {
    "query": "query($login:String!){user(login:$login){pinnedItems(first:6,"
             "types:[REPOSITORY]){nodes{... on Repository{nameWithOwner "
             "stargazerCount description isFork primaryLanguage{name}}}}}}"
}


def parse_count(s: str) -> int:
    """把 `143k` / `1.2k` / `1,204` / `828` 解析成整数；解析不了返回 -1。

    GitHub 的 pin 卡在星数过千后显示的是缩写，直接 int() 会抛 ValueError。
    """
    t = s.strip().replace(",", "")
    mult = 1
    if t[-1:].lower() == "k":
        mult, t = 1000, t[:-1]
    elif t[-1:].lower() == "m":
        mult, t = 1_000_000, t[:-1]
    try:
        return int(round(float(t) * mult))
    except (ValueError, IndexError):
        return -1


def collect_pinned(f: Fetcher, user: str) -> tuple[list[dict], str]:
    """返回 (pinned 列表, 来源)。GraphQL 优先，HTML 兜底。

    pinned 没有公开的写 API，但**读**是可以的：User.pinnedItems。
    """
    if f.token:
        payload = json.dumps({**PINNED_QUERY, "variables": {"login": user}}).encode()
        req = urllib.request.Request(API + "/graphql", data=payload)
        req.add_header("User-Agent", UA)
        req.add_header("Authorization", f"Bearer {f.token}")
        req.add_header("Content-Type", "application/json")
        try:
            with f.opener.open(req, timeout=20) as r:
                data = json.loads(r.read().decode())
            nodes = (((data.get("data") or {}).get("user") or {})
                     .get("pinnedItems") or {}).get("nodes") or []
            if nodes:
                return [{
                    "repo": n["nameWithOwner"],
                    "stars": n.get("stargazerCount", 0),
                    "desc": n.get("description") or "",
                    "fork": bool(n.get("isFork")),
                } for n in nodes], "graphql"
        except Exception:  # noqa: BLE001
            pass

    status, body, _ = f.request(f"https://github.com/{user}", retries=2)
    if status != 200:
        return [], "unavailable"
    html = body.decode("utf-8", errors="replace")
    repos, seen = [], set()
    for block in re.split(r"pinned-item-list-item", html)[1:]:
        block = block[:3000]
        m = re.search(r'href="/([^/"\s]+/[^/"\s#?]+)"', block)
        if not m:
            continue
        full = m.group(1)
        if not full.startswith(user + "/") or full in seen:
            continue
        seen.add(full)
        # 星数在 <a href="/o/r/stargazers"> 里，中间隔着一整个 600+ 字符的 svg 图标，
        # 旧正则用 .{0,400}? 根本跨不过去（2026-11 实测命中 0 次）→ 必须锚到 </svg>
        star = re.search(r'href="/[^"]*/stargazers"[^>]*>.*?</svg>\s*([\d,\.]+[kKmM]?)',
                         block, re.S)
        desc = re.search(r'pinned-item-desc[^>]*>\s*([^<]{0,200})', block)
        repos.append({
            "repo": full,
            "stars": parse_count(star.group(1)) if star else -1,
            "desc": (desc.group(1).strip() if desc else ""),
            "fork": "fork" in block.lower()[:800] and "Forked" in block,
        })
        if len(repos) >= 6:
            break
    return repos, "html"


def collect_readme(f: Fetcher, user: str) -> tuple[str | None, str | None]:
    """返回 (README 文本, 仓库全名)。"""
    for branch in ("main", "master"):
        status, body, _ = f.request(
            f"https://raw.githubusercontent.com/{user}/{user}/{branch}/README.md",
            retries=2)
        if status == 200 and body:
            return body.decode("utf-8", errors="replace"), f"{user}/{user}"
    repo = f.json(f"/repos/{user}/{user}")
    if isinstance(repo, dict) and repo.get("default_branch"):
        b = repo["default_branch"]
        status, body, _ = f.request(
            f"https://raw.githubusercontent.com/{user}/{user}/{b}/README.md")
        if status == 200:
            return body.decode("utf-8", errors="replace"), f"{user}/{user}"
    return None, None


# ---------------------------------------------------------------- 分析
IMG_TAG = re.compile(r"<img[^>]*?\ssrc=\"([^\"]+)\"", re.I)
IMG_MD = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
SOURCE_TAG = re.compile(r"<source[^>]*?srcset=\"([^\"]+)\"", re.I)


def extract_images(md: str) -> list[str]:
    out = []
    for rx in (IMG_TAG, IMG_MD, SOURCE_TAG):
        for m in rx.finditer(md):
            u = m.group(1).strip()
            if u and u not in out:
                out.append(u)
    return out


def analyze_readme(md: str, user: str) -> dict:
    pics_img = IMG_TAG.findall(md)
    pics_src = SOURCE_TAG.findall(md)
    images = extract_images(md)

    light = [u for u in images if "dark" not in u.lower()]
    dark = [u for u in images if "dark" in u.lower()]

    hits = []
    for rx, name, why in ANTI_PATTERNS:
        if re.search(rx, md, re.M):
            hits.append({"name": name, "why": why})

    badge_count = len(re.findall(r"img\.shields\.io|badge/", md))
    has_stats_marker = "STATS:BEGIN" in md and "STATS:END" in md
    external = [u for u in images if u.startswith("http")]
    local = [u for u in images if not u.startswith("http")]

    return {
        "length": len(md),
        "images": images,
        "local_images": len(local),
        "external_images": len(external),
        "picture_pairs": min(len(pics_src), len(light)),
        "dark_variants": len(dark),
        "has_picture": "<picture>" in md.lower(),
        "inline_svg": bool(re.search(r"<svg[\s>]", md, re.I)),
        "stats_marker": has_stats_marker,
        "badge_count": badge_count,
        "h2_count": len(re.findall(r"^##\s+", md, re.M)),
        "anti_patterns": hits,
        "external_hosts": sorted({
            re.sub(r"^https?://", "", u).split("/")[0] for u in external
        }),
    }


def check_images(f: Fetcher, images: list[str], user: str) -> list[dict]:
    out = []
    for u in images[:20]:
        if u.startswith("http"):
            target = u
        elif u.startswith("./"):
            target = f"https://raw.githubusercontent.com/{user}/{user}/main/{u[2:]}"
        elif u.startswith("/"):
            target = f"https://raw.githubusercontent.com/{user}/{user}/main{u}"
        else:
            target = f"https://raw.githubusercontent.com/{user}/{user}/main/{u}"
        status, ctype = f.head_ok(target)
        ok = status == 200 and ctype.startswith("image/")
        out.append({"src": u, "status": status, "type": ctype, "ok": ok})
    return out


# ---------------------------------------------------------------- 报告
def build_report(user: dict, pinned: list[dict], pinned_src: str,
                 rm: dict | None, imgs: list[dict]) -> tuple[str, list[str], list[str]]:
    L: list[str] = []
    must: list[str] = []
    suggest: list[str] = []
    add = L.append

    # 信号强度：已经有强仓库（★≥500）时，主页装饰是可选甚至负分，
    # 强行「补齐 bio / 建 README」反而是错的建议。
    # 关键：星数取不到（无 token + HTML 解析失败）时必须判「未知」，
    # 不能当成 0 —— 否则会把 ★143k 的账号判成「弱信号、必须全套补齐」。
    known = [p["stars"] for p in pinned if p["stars"] >= 0]
    max_star = max(known) if known else -1
    if not pinned:
        level = "weak"
    elif not known:
        level = "unknown"
    elif max_star >= 500:
        level = "strong"
    else:
        level = "weak"
    target = suggest

    add(f"# GitHub 主页审计 · `{user['login']}`\n")
    star_txt = f"★{max_star}" if max_star >= 0 else "取不到（无 token 且页面解析失败）"
    add(f"公开仓库 {user['public_repos']} · followers {user['followers']} "
        f"· 账号创建于 {str(user['created_at'])[:10]}"
        f" · 最强 pinned 仓库 {star_txt}\n")
    if level == "strong":
        add("> 置顶仓库已有较高关注度。可以突出真实作品和贡献；是否重做视觉仍由用户决定，"
            "不根据 star 数限制风格选择。\n")
    elif level == "weak":
        add("> 当前没有高关注度置顶仓库。这不表示能力弱，也不影响美化主页；"
            "可以从个人介绍、作品或文章开始，下面的内容建议并非必填清单。\n")
    else:
        add("> 信号强度：**未能判定**——pin 的仓库一个 star 数都没取到。"
            "配一个 GITHUB_TOKEN 重跑就能确定分档；在此之前不要把下面的清单当"
            "「必须修」，先按「建议」看。\n")

    # 层 1-2
    add("## 第 1-2 层 · 头像 / 名字 / bio\n")
    add(f"- 头像：{'已设置' if user['avatar'] else '**未设置**'}")
    add(f"- 名字：`{user['name']}`" if user["name"] else "- 名字：**未设置**（显示的是用户名）")
    bio_len = len(user["bio"])
    if not user["bio"]:
        add("- bio：**空** → " + ("这是最该先修的"
                                 if level == "weak" else "填一句不亏，但这一档不是重点"))
        target.append("填写 bio（160 字符内，角色 + 领域 + 正在做什么 + 想要什么）")
    else:
        flag = "⚠️ 偏长" if bio_len > 160 else "✅"
        add(f"- bio（{bio_len} 字符）：{user['bio']}  {flag}")
        if re.search(r"(?i)^(student|i love coding|coder|passionate)", user["bio"].strip()):
            add("  ⚠️ 套话开头，改成具体的能力域")
    add(f"- blog 字段：{user['blog'] or '**空**'}")
    add(f"- twitter：{user['twitter'] or '**空**'}\n")
    if not user["blog"]:
        target.append("填 blog 字段（个人站 / 博客 / 简历页，没有就给 LinkedIn）")

    # 层 4
    add(f"## 第 4 层 · Pinned repositories（来源：{pinned_src}）\n")
    if not pinned:
        add("- **没有 pin 任何仓库** → 侧栏显示的是 GitHub 自动挑的 Popular repositories，"
            "会混入无描述仓库并渲染成空白卡")
        target.append("按展示目的手动 pin 1-6 个合适仓库；没有合适内容时不凑数（网页 Customize your pins）")
    else:
        add(f"- 共 {len(pinned)} 个（上限 6）")
        for p in pinned:
            star = f"★ {p['stars']}" if p["stars"] >= 0 else "★ ?"
            desc = p["desc"] or "**无描述**"
            add(f"  - `{p['repo']}` {star} — {desc}")
            if not p["desc"]:
                target.append(f"给 `{p['repo']}` 补仓库描述（否则 pin 卡是空白的）")
            if p.get("fork"):
                add("    这是 fork：会标注 Forked from，显示 fork 本身而非上游的 star 数。"
                    "有自己的实际改动时可以保留，但应说明来源与贡献范围。")
                target.append(
                    f"确认 `{p['repo']}` 是要展示自己的改动还是上游贡献，再决定置顶 fork 或上游；"
                    "不要用上游 star 数替代 fork 的实际数据。")
        if len(pinned) < 3:
            add("- 少于 3 个也可以，内容相关性比填满数量更重要")
    add("")

    # 层 3
    add("## 第 3 层 · Profile README\n")
    if rm is None:
        add("- **没有 Profile README** → 需要建同名公开仓库")
        target.append(f"创建 `{user['login']}/{user['login']}` 公开仓库 + README.md")
    else:
        add(f"- 长度 {rm['length']} 字符 · {rm['h2_count']} 个二级标题")
        add(f"- 图片 {len(rm['images'])} 张（本地 {rm['local_images']} / 外链 {rm['external_images']}）")
        if rm["inline_svg"]:
            add("- ❌ **存在内联 `<svg>`** → GitHub 会整个剥掉，必须存成文件用 `<img>` 引用")
            must.append("把内联 SVG 抽成 assets/*.svg 文件")
        if rm["has_picture"]:
            add(f"- `<picture>` 双版：{rm['picture_pairs']} 对（暗色变体 {rm['dark_variants']} 个）")
            if rm["picture_pairs"] == 0:
                add("  ⚠️ 有 `<picture>` 但没有 `<source srcset>`，暗色版可能缺失")
        elif rm["dark_variants"] == 0 and rm["local_images"]:
            add("- ⚠️ 有本地图但没有深浅双版，暗色主题下可能看不清")
        add(f"- STATS 回写区间：{'有' if rm['stats_marker'] else '**无**'}"
            f" · shields 徽章 {rm['badge_count']} 个")
        if rm["badge_count"] > 6:
            add(f"  ❌ 徽章 {rm['badge_count']} 个（>6 就是纹理不是信息）")
            target.append("把徽章砍到 6 个以内，优先留社交链接")
        if rm["external_hosts"]:
            add("- 外链域名：" + "、".join(f"`{h}`" for h in rm["external_hosts"]))
            for h in rm["external_hosts"]:
                if h in KNOWN_HOSTS and "死" in KNOWN_HOSTS[h]:
                    add(f"  历史记录：`{h}` 曾出现 {KNOWN_HOSTS[h]}。是否仍失败以本次图片检查为准，"
                        "不根据旧记录直接删除。")

        if rm["anti_patterns"]:
            add("\n**反模式命中**：")
            for h in rm["anti_patterns"]:
                add(f"- ❌ {h['name']} —— {h['why']}")
            target.extend(f"移除反模式：{h['name']}" for h in rm["anti_patterns"])
        else:
            add("\n反模式命中：无 ✅")
    add("")

    # 图片存活
    if imgs:
        add("## 图片存活体检\n")
        bad = [i for i in imgs if not i["ok"]]
        for i in imgs:
            mark = "✅" if i["ok"] else "❌"
            add(f"- {mark} `{i['src'][:80]}` → {i['status']} {i['type'][:30]}")
        if bad:
            must.append(f"{len(bad)} 张图片加载失败")
        add("")

    # 结论
    add("## 结论\n")
    if must:
        add("**必须修**（客观错误，与信号强弱无关）：")
        for i, m in enumerate(dict.fromkeys(must), 1):
            add(f"{i}. {m}")
        add("")
    if suggest:
        add("**建议**（做完上一节再看，不碍事）：")
        for i, m in enumerate(dict.fromkeys(suggest), 1):
            add(f"{i}. {m}")
        add("")
    if not must and not suggest:
        add("没有发现问题。剩下的是「要不要重做视觉」的选择，见 SKILL.md 的主题预设。")
        add("")
    add("> 本报告只覆盖可自动检测的部分。视觉层次、信息密度、焦点是否唯一，"
        "需要人眼判断——用 headless chrome 截图看，别只看源码。")
    return "\n".join(L), must, suggest


# ---------------------------------------------------------------- main
def main() -> int:
    harden_stdout()
    ap = argparse.ArgumentParser(description="GitHub 主页审计")
    ap.add_argument("username")
    ap.add_argument("--token", default=None)
    ap.add_argument("--json", default=None, help="把结构化结果写到文件")
    ap.add_argument("--direct", action="store_true", help="强制不走代理")
    ap.add_argument("--no-net", action="store_true", help="跳过图片存活检查")
    args = ap.parse_args()

    f = Fetcher(get_token(args.token), use_proxy=not args.direct)
    raw_user = f.json(f"/users/{args.username}")
    if raw_user is None:
        print(f"❌ 取不到 /users/{args.username}（网络或用户名错误）", file=sys.stderr)
        return 2
    if raw_user.get("type") == "Organization":
        print(f"「{args.username}」是组织账号（Organization），不是个人主页。", file=sys.stderr)
        print("本 skill 的六层模型面向个人：bio、同名 `<user>/<user>` README、"
              "pinned 的个人叙事，对组织都不成立——组织的 README 放在 "
              "`<org>/.github/profile/README.md`。", file=sys.stderr)
        print("换个个人账号跑，或直接按组织规范手改。", file=sys.stderr)
        return 2
    user = collect_user(f, args.username, raw_user)

    pinned, pinned_src = collect_pinned(f, args.username)
    md, repo_full = collect_readme(f, args.username)
    rm = analyze_readme(md, args.username) if md else None
    imgs = [] if (args.no_net or not rm) else check_images(f, rm["images"], args.username)

    report, must, suggest = build_report(user, pinned, pinned_src, rm, imgs)
    print(report)

    if args.json:
        Path(args.json).write_text(json.dumps({
            "user": user, "pinned": pinned, "readme": rm, "images": imgs,
            "must_fix": must, "suggest": suggest,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n结构化结果已写入 {args.json}")

    return 1 if must else 0


if __name__ == "__main__":
    sys.exit(main())
