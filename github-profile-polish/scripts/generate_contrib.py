#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「开源贡献」卡片：官方 logo + ★star + 已合并 PR 数，亮暗双版。

数据全部来自 GitHub 公开 API，任何数字都能被第三方复算：
    /search/issues?q=author:<user>+type:pr+is:merged   → 已合并 PR 总数 + 逐仓库分布
    /repos/<owner>/<repo>                              → star 数、仓库描述、owner 官方头像

logo 用 base64 内嵌进 SVG，不写外链——GitHub 给 raw SVG 的响应头是
`Content-Security-Policy: default-src 'none'`，外链图片一律被拦，
只有 data: URI 能显示（2026-11 按线上 CSP 本地 1:1 复现验证过）。

logo 来源：**默认就是仓库自己的 owner 官方头像**，不内置任何品牌图标库
（内置一份 25 个图标 ≈98KB，还会随品牌改版过期，且涉及商标归属）。
只有想覆盖时才用 `--logo owner=path` 或把文件放进 `logos/`。

用法:
    python generate_contrib.py shi-felix --out ./profile
    python generate_contrib.py shi-felix --out ./profile --top 5 --accent blue
    python generate_contrib.py shi-felix --out ./profile --offline   # 用缓存重渲染
    python generate_contrib.py shi-felix --json contrib.json          # 只导出数据

只依赖标准库。token 优先取 --token，其次 GITHUB_TOKEN / GH_TOKEN，再次 `gh auth token`。
没有 token 时 search API 限流 10 次/分钟，仓库接口 60 次/小时——够跑一次，但别狂刷。
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scaffold as S  # noqa: E402  复用色值、字体栈、字宽与转义，保证设计口径唯一

API = "https://api.github.com"
UA = "profile-polish-contrib/1.0"
BEGIN, END = "<!-- CONTRIB:BEGIN -->", "<!-- CONTRIB:END -->"

# 版式常量（962 宽画布，GitHub 内容列 806 → 缩放 0.84）
W = 962
MARGIN = 40
LIST_TOP = 206
ROW_H = 62
LOGO = 30

LOGO_DIR = Path(__file__).resolve().parent.parent / "logos"


# ---------------------------------------------------------------- logo 解析
# 设计决策：**不内置任何品牌图标**。
# 权威来源就是仓库自己的 owner 头像（实时、换了 logo 自动跟上），
# 内置一份图标库既增加体积（实测 98KB/25 个），又会随品牌改版过期，
# 还有商标归属问题。只在「自己想覆盖」时留一个本地目录。
def _read_logo_file(p: Path) -> dict | None:
    try:
        if p.suffix.lower() == ".svg":
            return {"kind": "svg", "svg": p.read_text(encoding="utf-8-sig")}
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "webp": "image/webp", "gif": "image/gif"}.get(p.suffix.lower().lstrip("."))
        if not mime:
            return None
        return {"kind": "raster", "b64": base64.b64encode(p.read_bytes()).decode(),
                "mime": mime}
    except OSError:
        return None


def resolve_logo(owner: str, overrides: dict, repo: dict | None = None,
                 allow_local: bool = True, allow_avatar: bool = True,
                 f: "Fetcher | None" = None) -> tuple[dict | None, str]:
    """取 logo：`--logo` 指定 > `logos/<owner>.*` 自备 > GitHub 官方头像 > 无。

    返回 (logo, 来源标记)。`allow_local=False`（--avatar-only）只用官方头像。
    """
    key = owner.lower()
    if allow_local:
        if key in overrides:
            got = _read_logo_file(overrides[key])
            if got:
                return got, "override"
        for suffix in (".svg", ".png", ".jpg", ".jpeg", ".webp"):
            p = LOGO_DIR / f"{key}{suffix}"
            if p.exists():
                got = _read_logo_file(p)
                if got:
                    return got, "local"
    if allow_avatar and f and repo:
        avatar = ((repo.get("owner") or {}).get("avatar_url") or "")
        if avatar:
            sep = "&" if "?" in avatar else "?"
            st, body, hdrs = f.raw(f"{avatar}{sep}s=64", retries=2, timeout=15)
            ctype = hdrs.get("Content-Type", "")
            if st == 200 and ctype.startswith("image/") and len(body) < 200_000:
                return ({"kind": "raster", "b64": base64.b64encode(body).decode(),
                         "mime": ctype.split(";")[0]}, "avatar")
    return None, "none"


def logo_href(logo: dict | None, C: dict) -> str:
    """把 logo 变成 data: URI。

    自备的 SVG 若自身没写 fill，就注入主题文字色 —— 这样同一个文件在亮暗两版都看得见；
    已经写了 fill 的彩色 logo 不受影响（根元素 fill 只对没写 fill 的图元生效）。
    """
    if not logo:
        return ""
    if logo.get("kind") == "svg":
        svg = re.sub(r"<svg\b", f'<svg fill="{C["text"]}"', logo["svg"], count=1)
        return "data:image/svg+xml;base64," + base64.b64encode(
            svg.encode("utf-8")).decode()
    return f'data:{logo["mime"]};base64,{logo["b64"]}'


class Fetcher:
    def __init__(self, token: str | None):
        self.token = token
        self.opener = urllib.request.build_opener()

    def raw(self, url: str, *, accept: str | None = None,
            retries: int = 3, timeout: int = 20) -> tuple[int, bytes, dict]:
        last: Exception | str = "unknown"
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
                if e.code in (401, 403, 404, 422):
                    return e.code, b"", dict(e.headers or {})
                last = e
            except Exception as e:  # noqa: BLE001
                last = e
            time.sleep(1.2 * (i + 1))
        return 0, str(last).encode(), {}

    def json(self, path: str) -> tuple[dict | list | None, int]:
        url = path if path.startswith("http") else API + path
        st, body, _ = self.raw(url, accept="application/vnd.github+json")
        if st != 200:
            return None, st
        try:
            return json.loads(body.decode("utf-8")), st
        except json.JSONDecodeError:
            return None, st


def get_token(cli: str | None) -> str | None:
    if cli:
        return cli
    for env in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(env):
            return os.environ[env]
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True,
                             text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:  # noqa: BLE001
        pass
    return None


# ---------------------------------------------------------------- 取数
def collect_merged(f: Fetcher, user: str, max_pages: int = 3,
                   include_self: bool = False) -> tuple[dict, int, str, int]:
    """返回 ({repo: 样本内 PR 数}, 总数, 最近合并年月, 实际抓到的条数)。

    ⚠️ 样本内计数**不等于**该仓库的真实 PR 数：search API 最多翻 1000 条，
    对贡献多的人（如 1910 个 PR）样本只覆盖最近一小段。
    逐仓库的真实数字必须再用 `repo:` 维度精确查（见 exact_pr_count）。

    默认排除 `user:<自己>`：自己给自己合并的 PR 不是「上游贡献」，
    混进来会让卡片的口径站不住（见 references/content-model.md）。
    """
    q = f"author:{user} type:pr is:merged"
    if not include_self:
        q += f" -user:{user}"
    counts: dict[str, int] = {}
    total = 0
    latest = ""
    fetched = 0
    page = 0
    url = (f"{API}/search/issues?q={urllib.parse.quote(q)}"
           f"&per_page=100&sort=updated&order=desc")
    while url and page < max_pages:
        data, st = f.json(url)
        if not isinstance(data, dict):
            if st == 403:
                raise RuntimeError("search API 被限流（403）。等一分钟，或配 GITHUB_TOKEN，"
                                   "或直接用 --offline 读缓存")
            raise RuntimeError(f"search API 返回 {st}")
        total = data.get("total_count", total)
        for it in data.get("items", []):
            repo_url = (it.get("repository_url") or "")
            m = re.search(r"/repos/([^/]+/[^/]+)$", repo_url)
            if not m:
                continue
            name = m.group(1)
            counts[name] = counts.get(name, 0) + 1
            fetched += 1
            closed = (it.get("closed_at") or "")[:7]
            if closed > latest:
                latest = closed
        page += 1
        url = ""
        if page < max_pages and len(data.get("items", [])) == 100:
            url = (f"{API}/search/issues?q={urllib.parse.quote(q)}"
                   f"&per_page=100&sort=updated&order=desc&page={page + 1}")
    return counts, total, latest, fetched


def search_total(f: Fetcher, q: str) -> int:
    """跑一条 search 查询，只取 total_count；失败返回 -1。"""
    data, st = f.json(f"{API}/search/issues?q={urllib.parse.quote(q)}&per_page=1")
    if isinstance(data, dict) and "total_count" in data:
        return int(data["total_count"])
    return -1


def exact_pr_count(f: Fetcher, user: str, repo: str) -> int:
    """该用户在本仓库的**真实**已合并 PR 数（search 的 total_count）。

    卡片上的每个数字都必须走这里：样本计数在大账号上会差一到两个数量级
    （实测 antfu 的 vitejs/vite：样本数 1，真实 130）。
    """
    return search_total(f, f"author:{user} type:pr is:merged repo:{repo}")


def collect_repos(f: Fetcher, names: list[str], overrides: dict,
                  allow_local: bool = True,
                  allow_avatar: bool = True) -> list[dict]:
    out = []
    for name in names:
        data, st = f.json(f"/repos/{name}")
        if not isinstance(data, dict):
            out.append({"repo": name, "stars": -1, "desc": "", "owner": name.split("/")[0],
                        "logo": None, "logo_src": "none"})
            continue
        owner_login = ((data.get("owner") or {}).get("login")
                       or name.split("/")[0])
        logo, src = resolve_logo(owner_login, overrides, data,
                                 allow_local, allow_avatar, f)
        out.append({
            "repo": data.get("full_name") or name,
            "stars": data.get("stargazers_count", -1),
            "desc": (data.get("description") or "").strip(),
            "owner": owner_login,
            "logo": logo,
            "logo_src": src,
        })
    return out


# ---------------------------------------------------------------- 版式
def fmt_stars(n: int) -> str:
    if n < 0:
        return "★ ?"
    if n < 1000:
        return str(n)
    if n < 100_000:
        v = f"{n / 1000:.1f}"
        return (v[:-2] if v.endswith(".0") else v) + "k"
    return f"{n / 1000:.0f}k"


def render(rows: list[dict], total: int, last: str, C: dict, accent: str,
           complete: bool = True, repo_count: int = 0) -> str:
    n = len(rows)
    last_bottom = LIST_TOP + (n - 1) * ROW_H + 34
    line_y = last_bottom + 24
    note_y = line_y + 26
    H = note_y + 16

    p = [S.svg_open(W, H, f"开源贡献 · {total} 个已合并 PR")]
    # 眉行
    p.append(f'<rect x="{MARGIN}" y="47" width="7" height="7" fill="{accent}"/>')
    p.append(S.tx(56, 54, "OPEN SOURCE · MERGED PULL REQUESTS", 11.5, accent,
                  "600", family=S.MONO, ls=2.4))
    # 焦点数字：唯一的重心
    num = str(total)
    p.append(S.tx(MARGIN - 4, 152, num, 96, C["text"], "700", ls=-3))
    nx = MARGIN - 4 + S.text_w(num, 96) - 3 * max(len(num) - 1, 0) + 18
    p.append(S.tx(nx, 130, "merged PRs", 18.5, C["muted"]))
    # 副标题只说能被 API 证实的：抓全了才敢报仓库总数，
    # 抓不全（大账号翻不完）就老实说是「展示贡献最深的 N 个」
    if not complete:
        sub = f"展示贡献最深的 {n} 个上游仓库"
    elif repo_count > n:
        sub = f"覆盖 {repo_count} 个上游仓库 · 展示前 {n} 个"
    else:
        sub = f"覆盖 {repo_count} 个上游仓库"
    p.append(S.tx(nx, 152, sub + (f" · 最近 {last}" if last else ""), 13, C["muted"]))
    p.append(f'<line x1="{MARGIN}" y1="182" x2="{W - MARGIN}" y2="182" '
             f'stroke="{C["border"]}" stroke-width="1"/>')

    right = W - MARGIN
    name_x = MARGIN + LOGO + 12
    reserve = 150                      # 右侧 star / PR 列
    avail = right - reserve - name_x
    for i, r in enumerate(rows):
        y = LIST_TOP + i * ROW_H
        href = logo_href(r.get("logo"), C)
        if href:
            p.append(f'<defs><clipPath id="lg{i}"><rect x="{MARGIN}" y="{y + 3}" '
                     f'width="{LOGO}" height="{LOGO}" rx="7"/></clipPath></defs>')
            p.append(f'<image x="{MARGIN}" y="{y + 3}" width="{LOGO}" height="{LOGO}" '
                     f'clip-path="url(#lg{i})" href="{href}"/>')
        else:
            # 没有 logo 就退成一个字母方块，不要让整行塌掉
            p.append(f'<rect x="{MARGIN}" y="{y + 3}" width="{LOGO}" height="{LOGO}" '
                     f'rx="7" fill="{C["inset"]}"/>')
            p.append(S.tx(MARGIN + LOGO / 2, y + 24, r["repo"][:1].upper(), 14,
                          C["muted"], "700", anchor="middle"))
        p.append(S.tx(name_x, y + 14, S.clip(r["repo"], 19, avail, word=False), 19,
                      C["text"], "700"))
        desc = r.get("desc") or "（仓库无描述）"
        p.append(S.tx(name_x, y + 34, S.clip(desc, 13, avail, word=True), 13, C["muted"]))
        p.append(S.tx(right, y + 14, f'★ {fmt_stars(r["stars"])}', 17, C["muted"],
                      "600", anchor="end"))
        n_pr = r["prs"]
        p.append(S.tx(right, y + 34, f'{n_pr} PR' if n_pr == 1 else f'{n_pr} PRs', 13,
                      accent, "600", family=S.MONO, anchor="end"))
    p.append(f'<line x1="{MARGIN}" y1="{line_y}" x2="{W - MARGIN}" y2="{line_y}" '
             f'stroke="{C["border"]}" stroke-width="1"/>')
    p.append(S.tx(MARGIN, note_y,
                  "数据源 GitHub Search API（is:pr is:merged）· 每个 PR 均可在 GitHub 复核",
                  13, C["muted"]))
    p.append("</svg>")
    return "\n".join(p)


def snippet() -> str:
    return f"""{BEGIN}
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/contrib-dark.svg">
  <img src="./assets/contrib-light.svg" width="100%" alt="开源贡献：已合并 PR 与上游仓库">
</picture>
{END}"""


# ---------------------------------------------------------------- main
def main() -> int:
    S.harden_stdout()
    ap = argparse.ArgumentParser(description="生成开源贡献卡（logo + star + PR 数）")
    ap.add_argument("user")
    ap.add_argument("--out", default=".")
    ap.add_argument("--top", type=int, default=4, help="展示几个仓库，默认 4")
    ap.add_argument("--accent", default="purple", choices=list(S.ACCENTS))
    ap.add_argument("--offline", action="store_true", help="只读 assets/contrib.json 缓存")
    ap.add_argument("--token", default=None)
    ap.add_argument("--json", default=None, help="把结构化数据写到指定文件")
    ap.add_argument("--max-pages", type=int, default=3, help="search 最多翻几页（100/页）")
    ap.add_argument("--probe", type=int, default=8,
                    help="精确查询几个候选仓库的 PR 数（每个 1 次 search 调用）")
    ap.add_argument("--sort", default="prs", choices=["prs", "stars"],
                    help="列表排序：prs=贡献深度（默认），stars=仓库含金量")
    ap.add_argument("--include-self", action="store_true",
                    help="把自己的仓库也算进来（默认只统计提给他人的 PR）")
    ap.add_argument("--logo", action="append", default=[], metavar="OWNER=PATH",
                    help="用本地文件覆盖某个组织的 logo，可重复：--logo vitejs=./my.svg")
    ap.add_argument("--avatar-only", action="store_true",
                    help="只用 GitHub 官方头像，忽略 logos/ 里的内置图标")
    ap.add_argument("--no-readme", action="store_true", help="不回写 README 标记区间")
    args = ap.parse_args()

    out = Path(args.out)
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    cache = assets / "contrib.json"

    overrides: dict[str, Path] = {}
    for item in args.logo:
        if "=" not in item:
            print(f"--logo 要写成 OWNER=PATH，收到：{item}", file=sys.stderr)
            return 2
        k, v = item.split("=", 1)
        p = Path(v.strip()).expanduser()
        if not p.exists():
            print(f"--logo {k.strip()}={p}：文件不存在，这一条不会生效", file=sys.stderr)
            continue
        overrides[k.strip().lower()] = p

    if args.offline:
        if not cache.exists():
            print(f"没有缓存：{cache}", file=sys.stderr)
            return 2
        data = json.loads(cache.read_text(encoding="utf-8"))
    else:
        f = Fetcher(get_token(args.token))
        try:
            counts, total, last, fetched = collect_merged(
                f, args.user, args.max_pages, args.include_self)
        except RuntimeError as e:
            print(f"{e}", file=sys.stderr)
            if cache.exists():
                print(f"可改用 --offline 读缓存：{cache}", file=sys.stderr)
            return 2

        # 排除掉多少自有仓库的 PR，要明确说出来，别默默少算
        self_total = -1
        if not args.include_self:
            self_total = search_total(
                f, f"author:{args.user} type:pr is:merged user:{args.user}")

        if not counts:
            hint = (f"（另有 {self_total} 个提给自己仓库的 PR 未计入；"
                    f"要包含它们加 --include-self）" if self_total > 0 else "")
            print(f"{args.user} 没有提给他人仓库的已合并 PR，跳过贡献卡。{hint}")
            return 0
        # 先按样本出现次数挑候选，再逐个精确查——样本计数对大账号会差一到两个数量级
        candidates = sorted(counts, key=lambda k: counts[k], reverse=True)[:args.probe]
        repos = collect_repos(f, candidates, overrides,
                              allow_local=not args.avatar_only)
        for r, nm in zip(repos, candidates):   # collect_repos 按 candidates 顺序返回
            exact = exact_pr_count(f, args.user, nm)
            r["prs"] = exact if exact >= 0 else counts[nm]
            r["prs_exact"] = exact >= 0
        key = (lambda r: (r["prs"], r["stars"])) if args.sort == "prs" \
            else (lambda r: (r["stars"], r["prs"]))
        repos.sort(key=key, reverse=True)
        data = {"user": args.user, "total_merged": total, "last_merged": last,
                "complete": fetched >= total, "repo_count": len(counts),
                "excluded_self": max(self_total, 0), "repos": repos}

    rows = data["repos"][:args.top]
    if not rows:
        print("缓存里没有仓库数据。")
        return 0

    light_accent, dark_accent = S.ACCENTS[args.accent]
    complete = bool(data.get("complete", True))
    repo_count = int(data.get("repo_count", len(rows)))
    (assets / "contrib-light.svg").write_text(
        render(rows, data["total_merged"], data.get("last_merged", ""),
               S.LIGHT, light_accent, complete, repo_count), encoding="utf-8")
    (assets / "contrib-dark.svg").write_text(
        render(rows, data["total_merged"], data.get("last_merged", ""),
               S.DARK, dark_accent, complete, repo_count), encoding="utf-8")
    if not args.offline:
        cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                   encoding="utf-8")

    readme = out / "README.md"
    if not args.no_readme and readme.exists():
        md = readme.read_text(encoding="utf-8")
        if BEGIN in md and END in md:
            md = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END),
                        snippet(), md, flags=re.S)
            readme.write_text(md, encoding="utf-8")
            print(f"已回写 {readme}")
        else:
            print(f"README 里没有 {BEGIN} 标记，跳过回写（片段见下）")
            print(snippet())
    else:
        print(snippet())

    print(f"\n{data['total_merged']} 个已合并 PR · 展示 {len(rows)} 个仓库")
    marks = {"bundled": "内置", "local": "本地", "override": "指定", "avatar": "头像",
             "none": "缺"}
    for r in rows:
        n_pr = r["prs"]
        pr_txt = "1 PR" if n_pr == 1 else f"{n_pr} PRs"
        print(f"  {r['repo']:<34s} {fmt_stars(r['stars']):>7s}  {pr_txt:<8s}"
              f"logo[{marks.get(r.get('logo_src'), '?')}]")
    if data.get("excluded_self"):
        print(f"  （已排除 {data['excluded_self']} 个提给自己仓库的 PR）")

    # 缺 logo 的组织：把「该怎么办」说清楚，别让使用者自己猜
    missing = [r for r in rows if r.get("logo_src") == "none"]
    if missing:
        print(f"\n以下 {len(missing)} 个组织没取到 logo（网络失败且不在内置表里）：")
        for r in missing:
            print(f"  {r['owner']}")
        print(f"  处理方式二选一：")
        print(f"    ① 把 SVG/PNG 放到 {LOGO_DIR / (missing[0]['owner'] + '.svg')}")
        print(f"    ② 生成时指定：--logo {missing[0]['owner']}=<你的文件路径>")
    print(f"\n产物：{assets / 'contrib-light.svg'} / contrib-dark.svg")
    print("下一步：截图看一眼（SKILL.md S5），再 push 让 Actions 每日刷新")
    return 0


if __name__ == "__main__":
    sys.exit(main())
