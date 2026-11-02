---
name: github-profile-polish
description: 把 GitHub 个人主页做成「打开 10 秒就有判断」的对外凭证 —— 覆盖头像/bio/pinned repos/Profile README 四层，用脚本自产亮暗双版 SVG 规避第三方挂件失效，配 GitHub Actions 每日自动刷新。含四套主题预设（编辑排版/终端/卡片/极简）、GitHub 渲染硬规则、第三方服务存活实测。触发词：GitHub 主页美化、profile README、主页重做、主页改版、主页太丑、给面试官看的主页、GitHub 个人主页。
agent_created: true
---

# GitHub 主页美化

## 何时用
用户说「美化 GitHub 主页 / 主页重做 / 给面试官看 / profile README」。
先分清两种意图，走法完全不同：

| 用户说的是 | 真实需求 | 走法 |
|---|---|---|
| 「在 GitHub 上展示」「面试官打开就能看」 | 交付物必须在 **github.com 直接渲染** | Profile README（本 skill 主线） |
| 「做个主页」「要好看」 | 可能是要**本地 HTML 作品集** | 先问载体，别默认 README |

铁律：**简历/GitHub 的表述强度 ≤ 证据强度**。所有数字必须能从公开 API 复算，
不能写「熟悉 X」而仓库里没有 X。这是用户的硬约束，违反一次全盘作废。

## 第 0 步：先判断这个主页「该不该花力气」

**信号强度决定装饰预算。** 同一个改法，对两种人是相反的结论：

| 信号强度 | 判据 | 主页的定位 | 该做什么 |
|---|---|---|---|
| **强** | 有 ★≥500 的仓库，或知名项目里已合入的 PR | 锦上添花，**过度装饰是负分** | 只修客观错误：裂图、空白 pin 卡、错数字。不重做视觉 |
| **弱** | 学生 / 转行 / 项目还没起来 | **主要可控面**，必须做到位 | 全套：bio、pinned、README、自动化 |

先算出这个判断再动手。给一个 ★25 万仓库的人建议「必须填 bio」是荒谬的
（`audit_profile.py` 会自动分档，别自己拍脑袋）。

## 三条核心判断（违反任一条，做出来就是业余）

**① 一屏一个视觉焦点。** 用户明确说过：「一点都不高级，搞得很复杂，面试官抓不住重点」。
一个焦点数字或一句定性 → 一条支撑证据链 → 结束。加图表、饼图、热力图、
徽章墙全部是在稀释信号，不是加强。

**② 不依赖第三方实时服务。** 见 `references/widget-liveness.md`：
`github-readme-stats` 已 503 + 官方弃维护、`profile-trophy` 402、`metrics.lecoq.io` 500。
**唯一稳的路线 = 自己生成 SVG 提交进仓库**，GitHub Actions 每日刷新。
好处：不依赖别人、不走 camo 代理、不受 API 限流、不会某天开天窗。

**③ 深浅双版，用 `<picture>` 而不是 SVG 内 CSS。**
`<img>` 里的 `@media (prefers-color-scheme:dark)` 按**操作系统**判断，
且 WebKit（Safari / GitHub iOS App）不生效（WebKit bug 199134）。
GitHub 会把 `<picture>` 包成 `<themed-picture>`，跟随**站点主题**。这才是对的。

## 主页是六层，README 只是第三层
改 README 之前先看这六层，改错层的性价比极低：

| # | 层 | 控制方式 | 60 秒内被看到的概率 | 改动成本 |
|---|---|---|---|---|
| 1 | 头像 | 设置 → Public profile | 100% | 10 分钟 |
| 2 | 名字 + bio（160 字符） | 同上 | 100% | 5 分钟 |
| 3 | **Profile README** | `<user>/<user>` 仓库 | 90% | 小时级 |
| 4 | Pinned repositories（6 个上限） | 网页 Customize pins（**无 API**） | 80% | 20 分钟 |
| 5 | 社交链接（4 个上限） | 设置 → Social accounts | 60% | 5 分钟 |
| 6 | 贡献图 | 只能靠真实提交 | 50% | 不可伪造 |

**先做 1/2/4，再动 README。** 很多「主页不好看」的真实原因是 pin 了 6 个
无描述仓库 + bio 写「Student」。第 4 层见 `references/content-model.md`。

## 四套主题预设
默认 **T1 编辑排版风**。选型看用户身份，不看他喜欢什么：

| 预设 | 一句话 | 适合 | 一票否决 |
|---|---|---|---|
| **T1 Editorial** 编辑排版 | 透明背景、无卡片、发丝线、mono 眉行 + 大标题、单一强调色 | 想显克制/成熟，多数技术岗 | 用它再叠图标墙 = 自相矛盾 |
| **T2 Terminal** 终端 | 全等宽、提示符、光标、终端窗口装饰 | 后端 / 系统 / Agent / CLI 方向 | 中文标题别用等宽（字宽不齐） |
| **T3 Card** 卡片 | 圆角 + 1px 边框 + bg.inset 底，最多 2 张 | 信息量大（技术栈 + 多仓库统计） | 超过 2 张就变仪表盘 |
| **T4 Minimal** 极简文字 | 零 SVG，纯 Markdown 排版 | 不想维护 / 任何装饰都是噪音 | 内容不足以填满一屏时别用 |

完整规格（字号/行距/圆角/间距/每套的禁用项）在 `references/design-system.md`。
强调色是独立参数（紫/蓝/绿/橙），取值一律用 Primer token，见同一文件。

## 流程

> 脚本都在本 skill 的 `scripts/` 下。执行时先 `cd` 到 skill 目录，
> 或直接用绝对路径调用，不要假设 cwd。

### S1 审计（先跑脚本，别靠眼看）
```bash
python scripts/audit_profile.py <username>
```
输出六层的实际状态 + 外链图片存活 + 反模式命中 + 按信号强度分档的待修清单。
**这一步的产出决定后面改什么**，跳过去就会美化了不该改的层。

### S2 定主题 + 定信号
问清两件事，一次问完：
- 这个主页给谁看（面试官 / 招聘方 / 开源同行 / 自己）→ 决定 T1-T4
- 只展示「已合并 PR」还是含 open → 未经验证的声明会稀释可信度，
  但要主动提示代价：知名仓库往往还在待审，过滤掉品牌信号会消失

先出一版骨架给对方看，别直接改线上：
```bash
python scripts/scaffold.py --theme t1 --name "张三" --latin "San Zhang" \
  --eyebrow "BACKEND ENGINEER" --tagline "一句话说清你在做什么。" \
  --sub "身份 · 专注方向" --out ./preview
```
生成 `preview/assets/hero-{light,dark}.svg` + `README.md`。
`t4` 不出 SVG（纯 Markdown）。换强调色加 `--accent purple|blue|green`。

截图验收（零依赖）：
```bash
chrome.exe --headless --disable-gpu --screenshot=out.png \
  --window-size=806,240 "file:///<preview 目录>/preview.html"
```
`preview.html` 自己写一个 `<img src="assets/hero-light.svg" width="806">` 即可——
**必须用 806 宽渲染**，962 原生宽看不出真实观感。

### S3 写生成器（不要手写 SVG）
手写 SVG 无法维护——加一个仓库就要改三处坐标。正确做法是一个
`scripts/generate_stats.py`：拉 API → 算布局 → 输出亮暗两版 → 回写 README 标记区间。

**核心原则：数字只能有一个来源。** 徽章、正文、SVG、表格全由同一脚本渲染，
否则跑几次 Actions 之后必然出现「徽章写 16、卡片写 17」。

必备设计：
- SVG **透明背景**（T1/T2/T4）或双版背景色（T3），不依赖 `prefers-color-scheme`
- 高度自适应：`H = 最后一行 y + 尾部留白 + 页脚高`
- `--offline` 模式读 `assets/stats.json` 缓存，先出图再让 CI 联网刷新
- 只依赖标准库，不需要 `pip install`

### S4 组装 README
结构见 `references/content-model.md`。硬规则：
- 每张图用 `<p>` 包住（裸 `<img>` 会被 GitHub 加 `js-gh-image-fallback`，间距全乱）
- 深浅双版用 `<picture>` + `<source media="(prefers-color-scheme: dark)">`
- 动态回写区间用 `<!-- STATS:BEGIN --> ... <!-- STATS:END -->` 标记
- 排序按**含金量不按时间**：他人仓库 > 自有项目，组内按 stars 降序

### S5 验证（交付前必做，别省）
```bash
python scripts/verify_render.py <username>
```
跑的是**线上页面**，不是源码，检查：`<picture>` 双版是否配齐、
**亮色和暗色两套图各自**是否 200 且 `content-type: image/*`、
SVG 内是否有会被 GitHub 掐掉的东西（`<script>`、远程字体、外链图片）、
是否缺 `<title>` / `viewBox`。

单独验证一张图想肉眼看，用 headless chrome 直接截图，免装任何包——
```bash
chrome.exe --headless --disable-gpu --screenshot=out.png \
  --window-size=<svg宽>,<svg高> file:///<svg绝对路径>
```
chromium 在 `C:/Users/<u>/AppData/Local/ms-playwright/chromium-*/chrome-win64/chrome.exe`。
**注意中文路径会让 headless 写文件失败**（`系统找不到指定的路径`），
输出图放到 `AppData/Local/Temp/` 下。

### S6 自动化
`.github/workflows/update-stats.yml`：`schedule` 每日 + `workflow_dispatch` +
`paths: scripts/**` 的 push 触发；`permissions: contents: write`；提交带 `[skip ci]`。
注意 GitHub 的 schedule 实际触发时间会比 cron 晚 15-45 分钟，
要立刻看到效果就 `gh workflow run update-stats.yml --repo <user>/<user>`。

贡献贪吃蛇另起一个 workflow（`Platane/snk`），推 `output` 分支。
细节和 sed 后处理配方见 `references/content-model.md`。

## 反面清单（会被判定为业余）
这些不是「不够好」，是**负分**：
- 打字动画、访客计数器、旋转 logo、徽章墙（>6 个徽章就是纹理不是信息）
- 「正在学习」清单超过 3 项 —— 三个月后就变成谎话，且没人回来删
- 2 张以上重复统计卡片堆叠
- 空描述仓库被 pin（GitHub 会渲染成空白卡）
- 用低信号提交刷贡献图（`docs: fix typo` 连刷）—— 招聘方看得懂
- README 里写「Hi there 👋」模板 / emoji 轰炸
- 只有机制没结果：「使用了 React」；应该是「React + 30 个组件，首屏 1.2s」

判断标准（很好用）：**把仓库名/用户名遮住，这张卡片还能原样贴到别人主页上吗？
能 → 重做，它没有承载任何个人信息。**

## GitHub 渲染硬规则速查
完整白名单/剥离清单见 `references/github-rendering.md`。最容易踩的五条：
1. README 里内联 `<svg>` 会被剥离 → 必须存成文件用 `<img src="./x.svg">` 引用
2. `<img>` 一律用 `<p>` 包住（裸 `<img>` 会被加 `js-gh-image-fallback`，间距全乱；
   这条是来源转述，本机未复现，但包一层成本为零）
3. `<img>` 加载的 SVG **不能**引用任何外部资源（字体、图片、CSS）——CSP `default-src 'none'`
4. 外链图片走 `camo.githubusercontent.com` 代理；仓库内相对路径**绕过 camo**
5. 卡片按 962 宽设计 → GitHub 内容列约 806，等比缩到 0.84。
   换算：**实际观感 = 设计字号 × 0.84**（实测 44→37、15.5→13、13→11）。
   推荐 大标题 44-52 / 正文 15.5-18 / 脚注 ≥13；小字才是要放大的重点

## 参照实现
`shi-felix/shi-felix` 是 T1 的完整活样本：`scripts/generate_stats.py`（448 行，
标准库，亮暗双版，`--offline` 缓存）+ hero/PR 卡片 + snake + 每日 Actions。
改版时先读它，不要从零想。
