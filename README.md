# Skills

我日常在 AI 编程助手里用的 skill 集合 —— 每个 skill 是一个可复用的工作流，不是提示词片段。
都只依赖标准库或系统自带工具，能直接跑。

> A collection of workflow skills I use daily with AI coding agents.
> Each skill is a runnable workflow, not a prompt snippet.

## 安装

```bash
git clone https://github.com/shi-felix/skills.git ~/.workbuddy/skills-src

# 装单个
cp -r ~/.workbuddy/skills-src/github-profile-polish ~/.workbuddy/skills/

# 或全部软链（改完仓库即时生效）
for d in ~/.workbuddy/skills-src/*/; do
  [ -f "$d/SKILL.md" ] && ln -sfn "$d" ~/.workbuddy/skills/"$(basename "$d")"
done
```

Claude Code 用户把目标目录换成 `~/.claude/skills/` 即可，目录结构一致。
Cursor / Windsurf 等把 `SKILL.md` 当规则文件读也可以，脚本照跑。

## 目录

| Skill | 做什么 | 依赖 |
|---|---|---|
| [`github-profile-polish`](./github-profile-polish) | 任何个人账号都能用：四种风格预览 → 个人配置 → 离线作品展示或真实公开 PR 卡片 → 本地检查 → 可选每日刷新 | Python 3.10+（仅标准库） |

## 先体验 GitHub 主页美化

从仓库根目录运行，不需要 token，也不用先上传 GitHub：

```bash
python github-profile-polish/scripts/build_profile.py --gallery ./style-preview
python github-profile-polish/scripts/build_profile.py --init ./profile.json --username YOUR_USERNAME
python github-profile-polish/scripts/build_profile.py --config ./profile.json --mode projects --out ./my-profile
```

第一条生成四种布局的亮暗对比页；第二条中的 `YOUR_USERNAME` 换成自己的账号。在第三条运行前，填写配置中的名字、介绍、真实作品和链接。然后打开 `my-profile/preview.html`。

风格为 `t1` 编辑排版、`t2` 终端、`t3` 卡片、`t4` 纯 Markdown；支持中文/英文标题与四种独立强调色。没有 PR 或高星仓库也能使用。需要真实公开贡献时选择 `--mode auto`，需要每日刷新时再加 `--automation`。

生成器默认保护已有文件，不自动上传或改账号设置。详细使用方法见 [`SKILL.md`](./github-profile-polish/SKILL.md) 和 [首次使用说明](./github-profile-polish/references/first-run.md)。分发单个 skill 目录时请同时保留本仓库的 `LICENSE`。

## 每个 skill 里有什么

```
<skill-name>/
├── SKILL.md          # 主流程：什么时候用、怎么判断、按什么步骤做
├── references/       # 细节：规格、硬规则、实测数据（按需加载，不占上下文）
└── scripts/          # 能直接跑的工具，不是伪代码
```

约定两条：

1. **SKILL.md 只写决策**，不写实现细节。细节进 `references/`，只在需要时读。
2. **脚本必须能跑**。跑不通的脚本比没有更糟 —— 它会让人以为事情做完了。

## 加新 skill

```bash
mkdir -p my-skill/{references,scripts}
# 写 SKILL.md，frontmatter 至少要有 name 和 description
# description 里带上触发词 —— 这是它被选中的唯一依据
```

检验标准：把这个 skill 给别人，他能不能在不知道背景的情况下跑通。
如果 SKILL.md 里写满了「详见我之前那次对话」，那它不是 skill。

## License

MIT
