# 内容模型：六层各写什么

## 第 1 层 头像
- GitHub 会渲染成圆形，**四角内容会被裁掉**
- 硬限制：PNG/JPG/GIF，< 1MB，< 3000×3000，推荐 ~500×500（**【实测】GitHub Docs**）
- 有效做法：纯色/深色底 + 居中头部特写；或极简几何标识
- 无效做法：和别人的合照、风景、动漫头像（除非是个人品牌）、在圆内塞公司 logo

## 第 2 层 名字 + bio
- bio 长度：**160 字符**（UI 限制）；显示时会被截断，前 60 字符最关键
- 公式：`角色 + 领域 + 现在在做什么 + 想要什么`
  - ✅ `Agent 开发 · 构建 Coding Agent，持续向上游 AI 开源仓库提交 PR · 2028 届`
  - ❌ `Student` / `I love coding` / `Passionate developer on a journey`
- 不要写职位（换工作那天就错了），写**能力域**
- 有 `@org` 提及时，该组织会置顶在 activity 区

## 第 3 层 Profile README
### 信息架构（按读者原型选一种，不要混）

| 读者 | 首个视觉元素必须是 | 后接 | 长度上限 |
|---|---|---|---|
| 面试官 / 招聘方 | 一句身份定性（可有可无的一张 hero） | 3-5 条带结果的项目/贡献 | 一屏半 |
| 开源同行 | 真实贡献列表（仓库 + 数量） | 正在做的事 | 一屏 |
| 技术社区 | 一个有观点的判断 | 支撑证据 | 半屏 |

### 结构模板（T1，已被验证有效）
```
<picture> hero（眉行 + 名字 + 一句定位）   ← 可选，纯 Markdown 版去掉
<picture> 主卡片（焦点数字 + 支撑列表）
<!-- STATS:BEGIN --> 一行小字兜底 <!-- STATS:END -->
## 代表项目
<picture> 贡献图 / snake
```
**不要**再加：技术栈徽章墙、「正在学习」、联系我（社交链接已有）、访客计数。

### 排序：按含金量，不按时间、不按数量
含金量的**可验证代理 = 仓库 stars**（公开、每日可刷）。
- 他人仓库 > 自有项目（自有的初始导入 PR 可能几万行，数字大但没说服力）
- **pinned 选品**按 stars 降序，tie-break：PR 数 → 合并时间倒序
- **贡献卡明细行**按「每个仓库的已合并 PR 数」降序——那张卡的叙事是贡献深度，
  按 stars 排会把「只提过 1 个 PR 的大仓库」顶到第一，把主战场挤下去
- stars 直接标在仓库名旁（`★ 83.3k`），让含金量自己说话，**不加主观形容词**

### 只展示「已合并」PR
默认口径：**已开未合并的不进主页**。未经验证的声明会稀释可信度。
但必须**主动提示代价**：知名仓库（vitest / excalidraw 等）往往还在待审，
过滤后品牌信号会消失。让用户自己决定要不要留一行低调文字。

自己给自己合并的 PR 必须和别人仓库的分开计数：
- ❌ 卡片写「N 个 PR 已被**上游**合并」（自有项目不是上游）
- ✅ 写「已被合并」，副标题拆成「X 个提给他人仓库 · Y 个自有项目」
- ❌ **副标题重复焦点数字**（2026-11-02 实测反例）：焦点数字是 37，副标题又写
  「37 个提给他人仓库 · 近 30 天 +32」——一行文案位白扔，读起来像排版出错。
- ✅ 副标题换**另一个维度**：「分布在 7 个上游仓库 · 近 30 天 +32」。
  README 的 STATS 小字行同理，两处必须同一口径，否则卡片和文字两套表述。
- ⚠️ **点阵类图形先算信息密度再决定要不要**：把 N 个时间点铺在固定宽度上，
  中段出现 >20% 连续空白，说明它只是在说「最近才密集」，而这句话副标题一行字
  就说了。实测反例：37 个 PR 的合并日期铺满 960px，中间约 300px 纯空白，
  占掉 100px 高度只换来一个可免费获得的信息 → 已删除，卡片高度 750→676。

### 叙事 vs 流水账
同一仓库的一组相关 PR 合并成一个叙事块，而不是平铺 4 行——**仅当用户主动要细节时才用**。
主题词必须从标题**自动推导**，不能写死（换项目就露馅）：
剥掉 `type(scope):` 前缀 → 按非字母数字切词 → 过滤长度 <3 与停用词 →
取交集 → 按首个标题的出现顺序连接（最多 3 个）。

## 第 4 层 Pinned repositories（性价比最高的一层）
- 上限 **6 个**；不 pin 时显示的是 GitHub 自动生成的「Popular repositories」，
  会混入无描述仓库并渲染成**空白卡**
- **能 pin 什么**（官方规则）：你**拥有**的公开仓库，或**近一年内有贡献**的公开仓库。
  注意「对 fork 的提交不算贡献」。
- **没有公开 API**：GraphQL 只有 `pinIssue`/`pinIssueComment` 这类，没有 profile pin 的
  mutation；`viewer.pinnedItems` 只能**读**。网页「Customize your pins」是唯一入口
  → 让用户手动 pin，助手给出精确清单和顺序即可，**别再试 mutation**
- 选择规则：
  - 按**目标岗位**选，不按 star 数选
  - 删掉：教程跟做、无 fork 贡献的 fork、半成品、无描述仓库
  - 少于 6 个就 pin 少一点，不要凑数（3 个精的 > 6 个杂的）
  - 至少 1 个展示「能在别人的代码库里工作」（上游贡献 / 协作项目）
- 每个 pinned 仓库的 README 第一行必须是「这是什么」，**在一句话之内**

### 不要 pin 自己的 fork（常见错误，实测确认）
pin 自己的 fork 时，卡片会渲染成 `名字 · Public · **Forked from 上游/仓库**`，
且 **star 计 0**——哪怕上游有两万星。等于把最强的信号亲手抹掉，还附赠一个
「这个仓库不是我的」的烙印。

正确做法：**直接 pin 上游仓库本体**。因为你近一年给上游提过已合并 PR，
这个 pin 是官方允许的，卡片上显示的是上游的 star 数和你作为贡献者的身份。
（自己 fork 的副本只用来提 PR，不该出现在主页。
**实测**：`shi-felix/deer-flow` 的 pin 卡显示 `Forked from bytedance/deer-flow`、
GraphQL `stargazerCount: 0`，而 `bytedance/deer-flow` 是 ★2 万+。）

## 第 5 层 社交链接
上限 **4 个**。优先级：个人站/博客 > LinkedIn/GitHub 之外的职业身份 > 邮箱 > 其他。
不要放：微信二维码、QQ、无内容的 Twitter。

## 第 6 层 贡献图
- 计入的事件很窄：默认分支的 commit、非 fork 仓库的 issue/PR/discussion **开**事件
- 它只读时间戳，不读 diff → 所以能刷，也因此**招聘方权重低**
- 有效信号：**持续性**（多数周有提交）；无效信号：单日暴击、365 天连续（看起来像脚本）
- 别用 `docs: fix typo` 刷绿格子

### 贡献贪吃蛇（可选，但要注意口径）
用 `Platane/snk`，独立 workflow：
- `Platane/snk/svg-only@v3`（免 Playwright），输出亮暗两版（`?palette=github-dark`）
- `crazy-max/ghaction-github-pages@v4` 推到 **output 分支**
  （`target_branch: output, build_dir: dist`）
- `permissions: contents: write`；cron + workflow_dispatch + push main 触发
- README 用 `<picture>` 引用
  `raw.githubusercontent.com/<user>/<user>/output/github-contribution-grid-snake[-dark].svg`
- raw CDN 首次生效有几分钟窗口期，push 完立刻 404 是正常的

**默认输出有三处业余信号，在生成和 push 之间加 sed 后处理**（实测生效）：
1. 底部时间条 = 4 个 `<rect class="u uN">` 拼成的绿渐变，零信息量
   → `s|<rect class="u [^>]*/>||g`
2. 蛇默认 `--cs:purple`（#800080 茄紫）和页面强调色打架 → 亮版 `#8250DF` / 暗版 `#A371F7`
3. 删条后底部留 34px 死空间 → viewBox/width/height `880 192` → `880 158`

sed 结构化匹配失败时**不改动文件、保留原样**（安全降级）；
配方必须先在本地对真实 SVG 验证（headless chrome 截图肉眼确认）再进 CI。

⚠️ 口径提示：snake 会在贡献历史里堆积自动化提交。有人视为作弊，
**明确告诉用户这个代价**，让他自己决定，不要默认推荐。

## 自动化
`.github/workflows/update-stats.yml`：
```yaml
on:
  schedule: [{cron: '17 10 * * *'}]      # 北京 18:17，GitHub 实际会晚 15-45 分钟
  workflow_dispatch:
  push: {paths: ['scripts/**', 'assets/**']}
permissions: {contents: write}
```
- 提交信息带 `[skip ci]` 防自触发
- 脚本读 `secrets.GITHUB_TOKEN`；本地走 `gh auth token` 或 `--offline`
- **注意**：bot token 推的提交不会触发 `on: push` 事件 →
  要同期刷 snake 得单独 `gh workflow run snake.yml`

## 文案口径（硬约束）
- 表述强度 ≤ 证据强度。没有来源的数字不进主页
- 状态动词要和事实一致：「已合并」不能说成「上游合并」
- 不写「精通 / 资深 / 专家」，写做了什么、用了什么、结果是什么
- 项目名不自我贬低（不写 MVP / 玩具项目）
- 每条结果句必须是「做了什么 → 怎么做的 → 解决了什么问题」，不接受纯机制罗列
