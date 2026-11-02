#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""线上渲染验证 —— 主页上的图真的能看见吗？

audit_profile.py 看的是**源码**，这个脚本看的是**渲染结果**。
两者会不一致：图挂了页面不报错、暗色版画错但亮色正常、SVG 里写的外部资源被 CSP 掐掉。

用法:
    python verify_render.py <username>
    python verify_render.py <username> --direct
    python verify_render.py <username> --save       # 把抓到的主页 HTML 存到本地排查

退出码: 0 = 全部通过; 1 = 有问题。

只依赖标准库。
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

UA = "profile-polish-verify/1.0"

# SVG 里会被 GitHub 掐掉 / 剥掉的东西
SVG_FORBIDDEN = [
    (r"<script[\s>]", "含 `<script>` → GitHub 会剥离"),
    (r"<foreignObject[\s>]", "含 `<foreignObject>` → 高风险，不保证渲染"),
    (r"@import\s", "含 `@import` → 外部样式被 CSP 阻止"),
    (r"<image[^>]+href=\"https?://", "含远程 `<image>` → 外部图片不加载"),
    (r"@font-face", "含 `@font-face` → 远程字体不加载，会掉回系统字体"),
    (r"\son\w+=\"", "含内联事件处理器 → GitHub 会剥离"),
]


class Fetch:
    def __init__(self, direct: bool = False):
        handlers = [urllib.request.ProxyHandler({})] if direct else []
        self.opener = urllib.request.build_opener(*handlers)

    def get(self, url: str, retries: int = 3, timeout: int = 20) -> tuple[int, bytes, dict]:
        last = None
        for i in range(retries):
            req = urllib.request.Request(url)
            req.add_header("User-Agent", UA)
            try:
                with self.opener.open(req, timeout=timeout) as r:
                    return r.status, r.read(), dict(r.headers)
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 404):
                    return e.code, b"", {}
                last = e
            except Exception as e:  # noqa: BLE001
                last = e
            time.sleep(1.2 * (i + 1))
        return 0, str(last).encode(), {}


def parse_article(html: str) -> str:
    m = re.search(r'<article[^>]*itemprop="text"[^>]*>', html)
    if not m:
        m = re.search(r"<article[^>]*>", html)
    if not m:
        return ""
    start = m.end()
    end = html.find("</article>", start)
    return html[start:end if end > 0 else len(html)]


def main() -> int:
    ap = argparse.ArgumentParser(description="线上渲染验证")
    ap.add_argument("username")
    ap.add_argument("--direct", action="store_true")
    ap.add_argument("--save", action="store_true", help="保存主页 HTML")
    args = ap.parse_args()

    f = Fetch(args.direct)
    url = f"https://github.com/{args.username}"
    status, body, _ = f.get(url)
    if status != 200:
        print(f"❌ 主页 {url} 返回 {status}", file=sys.stderr)
        return 2
    html = body.decode("utf-8", errors="replace")
    if args.save:
        p = Path(f"{args.username}-profile.html")
        p.write_text(html, encoding="utf-8")
        print(f"主页 HTML 已存到 {p.resolve()}\n")

    art = parse_article(html)
    if not art:
        print("❌ 页面里找不到 README 容器（没有 Profile README？）", file=sys.stderr)
        return 1

    print(f"# 线上渲染验证 · `{args.username}`\n")

    # ---- 结构
    pics = len(re.findall(r"<themed-picture", art))
    sources = re.findall(r'<source[^>]*srcset="([^"]+)"', art)
    imgs = re.findall(r'<img[^>]*\ssrc="([^"]+)"', art)
    print("## 结构\n")
    print(f"- `<themed-picture>` {pics} 个 · `<source>` {len(sources)} 个 · `<img>` {len(imgs)} 个")
    fails: list[str] = []
    if pics and len(sources) < pics:
        print(f"  ❌ 有 {pics} 个 picture 但只有 {len(sources)} 个 dark source —— "
              "暗色主题下会掉回亮色版")
        fails.append("picture 缺少 dark source")
    if pics:
        print("  ✅ picture 已被 GitHub 包成 themed-picture，跟随站点主题")
    print()

    # ---- 图片存活（亮色 + 暗色都要验，只验一个会漏掉一半）
    print("## 图片存活\n")

    def check(src: str, label: str) -> tuple[bool, bytes | None]:
        full = src if src.startswith("http") else "https://github.com" + src
        st, data, hdrs = f.get(full, retries=2, timeout=25)
        ctype = hdrs.get("Content-Type", "")
        ok = st == 200 and ctype.startswith("image/")
        short = src if len(src) <= 70 else src[:67] + "…"
        print(f"- {'✅' if ok else '❌'} [{label}] {st} · "
              f"{ctype[:24] or '?':24} · `{short}`")
        if not ok:
            fails.append(src)
            return False, None
        return True, data

    svg_issues: dict[str, list[str]] = {}
    checked: set[str] = set()

    def audit_svg(src: str, data: bytes | None) -> None:
        if not data or len(data) > 2_000_000:
            return
        text = data.decode("utf-8", errors="replace")
        bad = [why for rx, why in SVG_FORBIDDEN if re.search(rx, text, re.I)]
        # 自己生成的东西应该有 title / viewBox；第三方工具的输出只提示不阻断
        third_party = bool(re.search(r"githubusercontent\.com|shields\.io|ghpvc", src))
        if not re.search(r"<title[\s>]", text):
            bad.append(("⚠️ " if third_party else "") +
                       "没有 `<title>` → 缺少无障碍描述与原生 tooltip")
        if not re.search(r'viewBox="', text):
            bad.append("没有 `viewBox` → 缩放会失真")
        if bad:
            svg_issues[src] = bad

    for src in sources:
        if src in checked:
            continue
        checked.add(src)
        ok, data = check(src, "暗")
        if ok:
            audit_svg(src, data)
    for src in imgs:
        if src in checked:
            continue
        checked.add(src)
        ok, data = check(src, "亮")
        if ok:
            audit_svg(src, data)
    print()

    # ---- SVG 内容合规
    hard_svg = {k: v for k, v in svg_issues.items()
                if any(not x.startswith("⚠️") for x in v)}
    if svg_issues:
        print("## SVG 内容检查\n")
        for src, issues in svg_issues.items():
            print(f"`{src}`")
            for i in issues:
                print(f"  - {i}")
        print()
        fails.extend(hard_svg.keys())

    # ---- 结论
    print("## 结论\n")
    if fails:
        print(f"**{len(fails)} 项待修**：")
        for i, x in enumerate(dict.fromkeys(fails), 1):
            print(f"{i}. `{x}`")
        print()
        print("> 图片 404 通常是路径写错或还没 push；content-type 不是 image/* 说明"
              "GitHub 没把它当图片给，多半是文件太大或后缀不对。")
        return 1
    print("全部通过 ✅")
    print()
    print("> 这个脚本查的是「能不能看见」。**看不见之外的问题它查不到**——"
          "字号太小、对比度不够、暗色版配色错了，都得 headless chrome 截图看：")
    print("> `chrome.exe --headless --disable-gpu --screenshot=out.png "
          "--window-size=962,400 file:///<svg路径>`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
