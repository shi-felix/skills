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
| [`github-profile-polish`](./github-profile-polish) | 把 GitHub 个人主页做成「打开 10 秒就有判断」的对外凭证。六层审计 → 四套主题预设 → 自产亮暗双版 SVG → Actions 每日刷新 | Python 3.10+（仅标准库） |

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
