#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按主题生成 Profile README + hero SVG 骨架（亮暗双版）。

生成的是**能直接用的起点**，不是成品：跑完打开 SVG 看一眼，再按
references/design-system.md 调字号和间距。

用法:
    python scaffold.py --theme t1 --name "石敬荣" --latin "Felix Shi" \
        --eyebrow "AGENT DEVELOPER" --tagline "构建 Coding Agent，也持续向开源仓库贡献代码。" \
        --sub "2028 届本科在读 · Agent Harness / MCP" --out ./profile

    python scaffold.py --theme t2 --name "张三" --tagline "..." --out ./profile
    python scaffold.py --theme t3 ... 
    python scaffold.py --theme t4 --name "张三" --tagline "..." --out ./profile   # 不出 SVG

主题:
    t1 Editorial（默认） 透明背景 + 发丝线 + mono 眉行
    t2 Terminal          终端窗口 + 提示符 + 光标
    t3 Card              圆角卡片 + 边框
    t4 Minimal           纯 Markdown，不出 SVG

只依赖标准库。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SANS = ("-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',"
        "'Hiragino Sans GB','Microsoft YaHei',sans-serif")
MONO = "ui-monospace,'SF Mono',Menlo,Consolas,monospace"

# Primer 色值，见 references/design-system.md
LIGHT = dict(text="#1f2328", muted="#59636e", disabled="#818b98",
             border="#d1d9e0", canvas="#ffffff", inset="#f6f8fa", accent="#8250df")
DARK = dict(text="#f0f6fc", muted="#9198a1", disabled="#656c76",
            border="#3d444d", canvas="#0d1117", inset="#151b23", accent="#ab7df8")

ACCENTS = {  # (light, dark)
    "purple": ("#8250df", "#ab7df8"),
    "blue": ("#0969da", "#4493f8"),
    "green": ("#1a7f37", "#3fb950"),
}


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def is_cjk(ch: str) -> bool:
    o = ord(ch)
    return (0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF
            or 0xFF00 <= o <= 0xFF60 or 0x3000 <= o <= 0x303F)


def text_w(s: str, size: float) -> float:
    """粗估文本宽度：CJK 按 1em、其余按 0.55em。

    SVG 是静态文件，没法 getComputedTextLength()，所以只能估。
    比例字体下这条公式对中英混排足够准（误差 <5%）；
    光标这类必须贴边的元素一定要用它算，不要按字符数乘个常数。
    """
    return sum(size * (1.0 if is_cjk(c) else 0.55) for c in s)


def tx(x, y, s, size, fill, weight="normal", anchor="start",
       family=None, ls=None, opacity=None) -> str:
    a = f'<text x="{x}" y="{y}" font-family="{family or SANS}" font-size="{size}" ' \
        f'fill="{fill}" font-weight="{weight}"'
    if anchor != "start":
        a += f' text-anchor="{anchor}"'
    if ls is not None:
        a += f' letter-spacing="{ls}"'
    if opacity is not None:
        a += f' fill-opacity="{opacity}"'
    return f'{a}>{esc(s)}</text>'


def svg_open(w, h, title) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">\n'
            f'<title>{esc(title)}</title>\n')


# ---------------------------------------------------------------- T1 Editorial
def hero_t1(name, latin, eyebrow, tagline, sub, C, accent) -> str:
    W, H = 962, 226
    p = [svg_open(W, H, f"{name} {latin}")]
    p.append(f'<rect x="40" y="47" width="7" height="7" fill="{accent}"/>')
    p.append(tx(56, 54, eyebrow.upper(), 11.5, accent, "600",
                family=MONO, ls=2.6))
    name_svg = (f'<text x="38" y="126" font-family="{SANS}" font-size="44" '
                f'font-weight="700" fill="{C["text"]}" letter-spacing="-1">'
                f'{esc(name)}'
                + (f'<tspan fill="{C["muted"]}" font-weight="400"> · {esc(latin)}</tspan>'
                   if latin else "") + "</text>")
    p.append(name_svg)
    p.append(tx(40, 168, tagline, 15.5, C["muted"]))
    p.append(tx(40, 198, sub, 13, C["muted"]))
    p.append(f'<line x1="40" y1="{H-9}" x2="{W-40}" y2="{H-9}" '
             f'stroke="{C["border"]}" stroke-width="1"/>')
    p.append("</svg>")
    return "\n".join(p)


# ---------------------------------------------------------------- T2 Terminal
def hero_t2(name, latin, eyebrow, tagline, sub, C, accent) -> str:
    W, H = 962, 246
    p = [svg_open(W, H, f"{name} terminal")]
    p.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="10" '
             f'fill="{C["canvas"]}" stroke="{C["border"]}" stroke-width="1"/>')
    # 标题栏
    p.append(f'<path d="M0 10a10 10 0 0 1 10-10h942a10 10 0 0 1 10 10v24H0z" '
             f'fill="{C["inset"]}"/>')
    for i, col in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        p.append(f'<circle cx="{26+i*20}" cy="17" r="5.5" fill="{col}"/>')
    p.append(tx(W // 2, 22, f"{name} — zsh", 11.5, C["muted"],
                family=MONO, anchor="middle"))
    p.append(f'<line x1="0" y1="34" x2="{W}" y2="34" stroke="{C["border"]}"/>')
    # 内容（等宽只用于英数符号，中文走无衬线）
    y = 84
    p.append(tx(40, y, "$", 17, accent, "700", family=MONO))
    p.append(tx(62, y, eyebrow, 17, C["muted"], family=MONO))
    y += 50
    name_svg = (f'<text x="40" y="{y}" font-family="{SANS}" font-size="42" '
                f'font-weight="700" fill="{C["text"]}" letter-spacing="-1">'
                f'{esc(name)}'
                + (f'<tspan fill="{C["muted"]}" font-weight="400"> · {esc(latin)}</tspan>'
                   if latin else "") + "</text>")
    p.append(name_svg)
    # 光标位置必须实测文本宽度：中英混排按字符数乘常数一定会压到字上
    line = name + (" · " + latin if latin else "")
    cx = 40 + text_w(line, 42) + 10
    p.append(f'<rect x="{cx:.1f}" y="{y-31}" width="9" height="32" '
             f'rx="2" fill="{accent}"><animate attributeName="opacity" '
             f'values="1;1;0;0;1" keyTimes="0;0.45;0.55;0.95;1" dur="1.1s" '
             f'repeatCount="indefinite"/></rect>')
    y += 40
    p.append(tx(40, y, tagline, 15.5, C["muted"]))
    y += 30
    p.append(tx(40, y, sub, 13, C["muted"]))
    p.append("</svg>")
    return "\n".join(p)


# ---------------------------------------------------------------- T3 Card
def hero_t3(name, latin, eyebrow, tagline, sub, C, accent) -> str:
    W, H = 962, 218
    p = [svg_open(W, H, f"{name} card")]
    p.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="8" '
             f'fill="{C["canvas"]}" stroke="{C["border"]}" stroke-width="1"/>')
    p.append(f'<rect x="32" y="36" width="3" height="15" rx="1.5" fill="{accent}"/>')
    p.append(tx(44, 48, eyebrow.upper(), 11.5, accent, "600", family=MONO, ls=2.2))
    p.append(f'<text x="32" y="112" font-family="{SANS}" font-size="40" '
             f'font-weight="700" fill="{C["text"]}" letter-spacing="-0.8">'
             f'{esc(name)}'
             + (f'<tspan fill="{C["muted"]}" font-weight="400"> · {esc(latin)}</tspan>'
                if latin else "") + "</text>")
    p.append(tx(32, 152, tagline, 15.5, C["muted"]))
    p.append(tx(32, 180, sub, 13, C["muted"]))
    p.append("</svg>")
    return "\n".join(p)


BUILDERS = {"t1": hero_t1, "t2": hero_t2, "t3": hero_t3}


# ---------------------------------------------------------------- README
def readme_for(theme: str, name: str, tagline: str, sub: str, has_svg: bool) -> str:
    hero = """<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/hero-dark.svg">
  <img src="./assets/hero-light.svg" width="100%" alt="{alt}">
</picture>""".format(alt=f"{name} — {sub}") if has_svg else f"# {name}\n\n{tagline}\n\n{sub}"

    return f"""{hero}

<!-- STATS:BEGIN -->
<!-- STATS:END -->

## 代表项目

**项目名** —— 一句话说清它是什么、解决什么问题。

[仓库](链接) · 技术栈 · `文件数 / 代码行数`

---

## 写法提醒（定稿后删掉这一节）

- 只留**一个**视觉焦点：上面的 hero 已经是了，别再叠第二张密集卡片
- 「代表项目」最多 3 个，每个一句话 + 一个可验证的数字
- 不写「正在学习」「Hi there 👋」「访客计数」
- 数字必须能复算；表述强度 ≤ 证据强度
- 主题 `{theme}` 的完整规格见 skill 的 references/design-system.md
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="生成 Profile README + hero SVG 骨架")
    ap.add_argument("--theme", default="t1", choices=["t1", "t2", "t3", "t4"])
    ap.add_argument("--name", required=True)
    ap.add_argument("--latin", default="")
    ap.add_argument("--eyebrow", default="DEVELOPER")
    ap.add_argument("--tagline", default="")
    ap.add_argument("--sub", default="")
    ap.add_argument("--accent", default="purple", choices=list(ACCENTS))
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    out = Path(args.out)
    (out / "assets").mkdir(parents=True, exist_ok=True)

    light_accent, dark_accent = ACCENTS[args.accent]
    has_svg = args.theme in BUILDERS

    if has_svg:
        build = BUILDERS[args.theme]
        args_l = (args.name, args.latin, args.eyebrow, args.tagline, args.sub)
        (out / "assets" / "hero-light.svg").write_text(
            build(*args_l, LIGHT, light_accent), encoding="utf-8")
        (out / "assets" / "hero-dark.svg").write_text(
            build(*args_l, DARK, dark_accent), encoding="utf-8")

    (out / "README.md").write_text(
        readme_for(args.theme, args.name, args.tagline, args.sub, has_svg),
        encoding="utf-8")

    print(f"✅ 已生成到 {out.resolve()}")
    if has_svg:
        print(f"   assets/hero-light.svg / hero-dark.svg  （{args.theme}）")
    print("   README.md")
    print("\n下一步：")
    print("  1) 截图看一眼（headless chrome，见 SKILL.md 的 S5）")
    print("  2) 按 design-system.md 调字号：大标题 44-52 / 正文 15.5-18 / 脚注 ≥13")
    print("  3) 写真正的生成脚本（generate_stats.py），别手改 SVG")
    return 0


if __name__ == "__main__":
    sys.exit(main())
