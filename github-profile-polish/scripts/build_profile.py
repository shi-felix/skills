#!/usr/bin/env python3
"""从个人配置生成完整主页、离线预览或四种风格的对比页。仅依赖标准库。"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import sys
import tempfile
from pathlib import Path

import generate_contrib
import scaffold
import verify_render


PREVIEW_CSS = """
* { box-sizing: border-box; }
body { margin: 0; color: #1f2328; background: #ffffff;
  font: 16px/1.65 -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; }
main { max-width: 1708px; margin: auto; padding: 28px 24px; }
header, section { margin-bottom: 36px; }
header h1 { margin: 0; font-size: 24px; }
h2 { font-size: 20px; margin: 0 0 12px; }
h3 { font-size: 18px; margin: 24px 0 10px; }
a { color: #0969da; text-decoration-thickness: 1px; text-underline-offset: 3px; }
nav { display: flex; gap: 18px; flex-wrap: wrap; margin: 14px 0; }
.variants { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; }
.variant { min-width: 0; max-width: 806px; }
.label { display: block; margin-bottom: 8px; font-size: 13px; color: #59636e; }
.surface { padding: 20px 0; overflow-wrap: anywhere; }
.surface.light { color: #1f2328; background: #ffffff; }
.surface.dark { color: #f0f6fc; background: #0d1117; }
.surface.dark a { color: #4493f8; }
.surface img { display: block; width: 100%; height: auto; }
.text { padding: 0 24px; }
.text h1 { font-size: 28px; margin: 0 0 18px; }
.text p { margin: 12px 0; }
ul { padding-left: 24px; }
li { margin-bottom: 10px; }
section { padding-bottom: 24px; border-bottom: 1px solid #d1d9e0; }
@media (max-width: 1100px) { .variants { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 480px) { main { padding: 20px 12px; } .text { padding: 0 16px; } .surface { padding: 10px 0; } }
"""


def preview_content(profile: dict, variant: str, data: dict | None = None,
                    prefix: str = "", top: int = 4, identity_only: bool = False) -> str:
    escape = html.escape
    content = []
    if profile["theme"] != "t4":
        content.append(f'<img src="{prefix}assets/hero-{variant}.svg" alt="{escape(profile["name"], quote=True)}">')
    else:
        paragraphs = "".join(f"<p>{escape(profile[field])}</p>" for field in ("tagline", "sub") if profile[field])
        content.append(f'<div class="text"><h1>{escape(profile["name"])}</h1>{paragraphs}</div>')
    if identity_only:
        return "".join(content)
    if data and data["total_merged"]:
        if profile["theme"] == "t4":
            label = "已合并 PR" if profile["language"] == "zh" else "Merged PRs"
            entries = "".join(
                f'<li><a href="https://github.com/{escape(repo["repo"], quote=True)}">{escape(repo["repo"])}</a>'
                f' / {repo["prs"]} {"PR" if repo["prs"] == 1 else "PRs"} / ★ {generate_contrib.fmt_stars(repo["stars"])}</li>'
                for repo in data["repos"][:top])
            content.append(f'<div class="text"><h3>{label}</h3><p><strong>{data["total_merged"]}</strong></p><ul>{entries}</ul></div>')
        else:
            content.append(f'<img src="{prefix}assets/contrib-{variant}.svg" alt="Merged pull requests">')
    labels = scaffold.LABELS[profile["language"]]
    if profile["projects"]:
        entries = "".join(
            f'<li><strong><a href="{escape(project["url"], quote=True)}">{escape(project["name"])}</a></strong>'
            + (("：" if profile["language"] == "zh" else ": ") + escape(project["description"]) if project["description"] else "") + "</li>"
            for project in profile["projects"])
        content.append(f'<div class="text"><h3>{labels["projects"]}</h3><ul>{entries}</ul></div>')
    if profile["links"]:
        links = " · ".join(f'<a href="{escape(link["url"], quote=True)}">{escape(link["name"])}</a>' for link in profile["links"])
        content.append(f'<div class="text"><h3>{labels["links"]}</h3><p>{links}</p></div>')
    return "".join(content)


def variant_pair(profile: dict, data: dict | None = None, prefix: str = "",
                 top: int = 4, identity_only: bool = False) -> str:
    panels = []
    for variant, label in (("light", "亮色"), ("dark", "暗色")):
        content = preview_content(profile, variant, data, prefix, top, identity_only)
        panels.append(f'<div class="variant"><span class="label">{label}</span>'
                      f'<div class="surface {variant}">{content}</div></div>')
    return '<div class="variants">' + "".join(panels) + "</div>"


def preview_page(title: str, body: str, language: str = "zh") -> str:
    return (f'<!doctype html><html lang="{language}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{html.escape(title)}</title><style>{PREVIEW_CSS}</style></head>'
            f'<body><main>{body}</main></body></html>\n')


def workflow_for(profile: dict, top: int) -> str:
    return f"""name: 更新主页贡献

on:
  schedule:
    - cron: '23 3 * * *'
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: profile-contributions
  cancel-in-progress: true

jobs:
  refresh:
    if: github.repository == '{profile['username']}/{profile['username']}'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: 获取真实贡献并更新展示区
        env:
          GH_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}
        run: python scripts/generate_contrib.py {profile['username']} --out . --theme {profile['theme']} --accent {profile['accent']} --language {profile['language']} --top {top}
      - name: 校验本地资源
        run: python scripts/verify_render.py --local .
      - name: 仅在内容变化时提交
        run: |
          git add README.md assets/
          if git diff --cached --quiet; then exit 0; fi
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git commit -m "chore: 更新主页贡献 [skip ci]"
          git push
"""


def build_artifacts(root: Path, profile: dict, data: dict | None, automation: bool, top: int) -> None:
    if data is not None:
        generate_contrib.validate_data(data, profile["username"], data.get("scope") == "all")
    scaffold.write_scaffold(root, profile)
    if data is not None:
        generate_contrib.write_contribution(root, data, theme=profile["theme"], accent=profile["accent"],
                                           top=top, language=profile["language"])
    (root / "profile.json").write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    title = f"{profile['name']} / {scaffold.THEMES[profile['theme']]}"
    body = f"<header><h1>{html.escape(title)}</h1></header>" + variant_pair(profile, data, top=top)
    (root / "preview.html").write_text(preview_page(title, body, profile["language"]), encoding="utf-8")
    if automation:
        (root / "scripts").mkdir()
        for filename in ("scaffold.py", "generate_contrib.py", "verify_render.py"):
            shutil.copyfile(Path(__file__).parent / filename, root / "scripts" / filename)
        workflow = root / ".github" / "workflows" / "update-stats.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text(workflow_for(profile, top), encoding="utf-8")
    issues = verify_render.local_findings(root)
    if issues:
        raise ValueError("生成结果未通过本地检查：" + "; ".join(issues))


def publish_local(stage: Path, out: Path, overwrite: bool) -> None:
    files = sorted(path for path in stage.rglob("*") if path.is_file())
    relative_paths = [path.relative_to(stage).as_posix() for path in files]
    scaffold.ensure_targets(out, relative_paths, overwrite)
    for source, relative in zip(files, relative_paths):
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def create_gallery(out: Path, profile: dict, overwrite: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="profile-polish-gallery-") as temporary:
        stage = Path(temporary)
        sections = []
        for theme, label in scaffold.THEMES.items():
            sample = {**profile, "theme": theme, "mode": "projects"}
            build_artifacts(stage / theme, sample, None, False, 4)
            heading = f'<h2 id="{theme}"><a href="./{theme}/preview.html">{theme} / {label}</a></h2>'
            sections.append("<section>" + heading + variant_pair(sample, prefix=f"./{theme}/", identity_only=True) + "</section>")
        navigation = "".join(f'<a href="#{theme}">{label}</a>' for theme, label in scaffold.THEMES.items())
        body = '<header><h1>GitHub 主页风格</h1><nav>' + navigation + "</nav></header>" + "".join(sections)
        (stage / "index.html").write_text(preview_page("GitHub 主页风格", body), encoding="utf-8")
        publish_local(stage, out, overwrite)


def main() -> int:
    scaffold.harden_stdout()
    parser = argparse.ArgumentParser(description="生成个人主页、首次配置或四种风格对比；不会自动推送 GitHub")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--config", type=Path, help="个人 JSON 配置，可从 --init 创建")
    source.add_argument("--init", type=Path, help="创建可编辑配置，不访问 GitHub")
    for field in ("username", "name", "latin", "eyebrow", "tagline", "sub"):
        parser.add_argument("--" + field)
    parser.add_argument("--theme", choices=list(scaffold.THEMES))
    parser.add_argument("--accent", choices=list(scaffold.ACCENTS))
    parser.add_argument("--mode", choices=("auto", "projects", "contributions"))
    parser.add_argument("--language", choices=list(scaffold.LABELS))
    parser.add_argument("--out", type=Path, help="输出目录，默认 profile-用户名")
    parser.add_argument("--gallery", type=Path, help="生成四种风格对比页，不联网、不生成示例统计")
    parser.add_argument("--offline", action="store_true", help="读取输出目录内同一用户的已核实贡献缓存")
    parser.add_argument("--automation", action="store_true", help="额外生成可独立运行的每日刷新工作流")
    parser.add_argument("--overwrite", action="store_true", help="确认后覆盖生成的同名文件，保留其他文件")
    parser.add_argument("--top", type=int, default=4, help="展示贡献仓库数量，1-10，默认 4")
    args = parser.parse_args()
    try:
        config = json.loads(args.config.expanduser().read_text(encoding="utf-8-sig")) if args.config else {}
        if not isinstance(config, dict):
            raise ValueError("配置文件的顶层必须是 JSON 对象")
        for field in scaffold.PROFILE_DEFAULTS:
            value = getattr(args, field, None)
            if value is not None:
                config[field] = value
        if args.gallery and not (config.get("name") or config.get("username")):
            config = {"username": "demo-user", "name": "示例用户", "latin": "Demo Maker",
                      "eyebrow": "BUILD / SHARE", "tagline": "让自己的作品和贡献更容易被看懂。",
                      "sub": "演示内容，仅用于比较风格", "mode": "projects", **config}
        profile = scaffold.normalize_profile(config)
        if not 1 <= args.top <= 10:
            raise ValueError("top 必须在 1-10 之间")
        if args.init:
            if args.gallery or args.out or args.automation or args.offline:
                raise ValueError("--init 只创建配置，不能同时生成主页、预览或工作流")
            if not profile["username"]:
                raise ValueError("首次配置请提供 --username GitHub用户名")
            destination = args.init.expanduser()
            scaffold.ensure_targets(destination.parent, [destination.name], args.overwrite)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"已创建个人配置：{destination.resolve()}；请填写真实介绍、作品和联系链接。")
            return 0
        if args.gallery:
            if args.automation or args.offline or args.out:
                raise ValueError("--gallery 只比较风格，不能同时使用 --automation、--offline 或 --out")
            create_gallery(args.gallery.expanduser(), profile, args.overwrite)
            print(f"风格对比：{(args.gallery.expanduser() / 'index.html').resolve()}")
            return 0
        if not profile["username"]:
            raise ValueError("生成个人主页需要 username；请提供 --username 或在配置文件中填写")
        if args.automation and profile["mode"] == "projects":
            raise ValueError("projects 模式无需贡献刷新；如需自动刷新，请选择 auto 或 contributions")
        out = (args.out or Path("profile-" + profile["username"])).expanduser()
        existing_config = out / "profile.json"
        if existing_config.is_file():
            existing = scaffold.read_profile(existing_config)
            if existing["username"].lower() != profile["username"].lower():
                raise ValueError("不同 GitHub 账号必须使用不同输出目录，不能混用个人资料和缓存")
        if (out / ".github" / "workflows" / "update-stats.yml").exists() and not args.automation:
            raise ValueError("此目录已有自动刷新工作流，请换新目录，或确认保留后加 --automation")
        scaffold.ensure_targets(out, ["README.md", "profile.json", "preview.html"], args.overwrite)
        data = None
        if profile["mode"] != "projects":
            if args.offline:
                cache = out / "assets" / "contrib.json"
                data = generate_contrib.validate_data(json.loads(cache.read_text(encoding="utf-8-sig")), profile["username"])
            else:
                data = generate_contrib.collect_data(generate_contrib.Fetcher(generate_contrib.get_token(None)),
                                                     profile["username"], probe=max(8, args.top))
            generate_contrib.validate_data(data, profile["username"])
            if not data["total_merged"] and profile["mode"] == "contributions":
                raise ValueError("没有可展示的已合并 PR；请选择 auto 或 projects，不需要编造贡献")
        with tempfile.TemporaryDirectory(prefix="profile-polish-build-") as temporary:
            stage = Path(temporary)
            cache = out / "assets" / "contrib.json"
            if data is not None and cache.is_file():
                (stage / "assets").mkdir()
                shutil.copyfile(cache, stage / "assets" / "contrib.json")
            build_artifacts(stage, profile, data, args.automation, args.top)
            publish_local(stage, out, args.overwrite)
        print(f"主页文件：{out.resolve()}")
        print(f"本地预览：{(out / 'preview.html').resolve()}")
        if data is not None:
            print(f"已合并 PR：{data['total_merged']}；缓存时间：{data.get('generated_at', '未知')}")
            if not data["total_merged"]:
                print("当前统计范围尚无已合并 PR，已自动省略贡献卡；介绍和作品仍可展示。")
        if args.automation:
            print("已附带独立刷新脚本和工作流；需发布到同名仓库并允许 Actions 写入后才会运行。")
        print("本地结构检查通过；尚未推送 GitHub，也未替你修改头像、简介或置顶仓库。")
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        print("未完成生成。网络失败可先用 --mode projects 离线排版；缓存缺失不能冒充零贡献。", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
