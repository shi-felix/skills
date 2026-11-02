---
name: github-profile-polish
description: 把 GitHub 主页做成「打开 10 秒就知道你做过什么」的对外凭证。主线是**贡献可视化**：用自产 SVG 把「已合并 PR 数 + 上游仓库官方 logo + star 数」做成一张贡献卡，上面压一句身份定性，下面接可复核的证据链。附带头像/bio/pinned 另外五层、四套主题预设、GitHub 渲染硬规则、Actions 每日自动刷新。触发词：GitHub 主页、profile README、贡献展示、PR 卡片、主页美化、主页重做、给面试官看的主页、开源贡献怎么展示。
agent_created: true
---

# GitHub 主页：把贡献做成看得见的东西

## 交付物是什么

一句话：**上面一层「我是谁」，下面一层「我做过什么，你能去 GitHub 查」。**

| 产物 | 作用 | 生成方式 |
|---|---|---|
| `assets/hero-{light,dark}.svg` | 身份层：名字 + 一句定位 + 身份标签 | `scaffold.py` |
| `assets/contrib-{light,dark}.svg` | **证据层**：焦点数字（已合并 PR 总数）+ 逐仓库的官方 logo / ★star / PR 数 | `generate_contrib.py` |
| `README.md` | 把两张图串起来 + 代表项目 | `scaffold.py` 出骨架，脚本回写标记区间 |

**为什么证据层比身份层重要**：面试官/招聘方看主页只做一件事——验证简历上的话。
一句「熟悉 Agent 开发」不值钱，「给 `langgenius/dify`（★160k）合并了 19 个 PR，点开就能看」值钱。
所以贡献卡是默认要做的，hero 是配菜。

## 适用范围（先判断，别硬套）

| 用户是谁 | 主页定位 | 该怎么做 |
|---|---|---|
| **求职者 / 学生** | 主要可控面，必须做到位 | 全套：bio、pinned、hero、**贡献卡**、自动化 |
| **开源维护者 / 已有强仓库** | 锦上添花，**过度装饰是负分** | 只修客观错误（裂图、空白 pin 卡、错数字），不重做视觉 |
| **设计师 / 写作者等非代码岗** | 作品集为主，GitHub 是辅证 | 只要 hero + 一段文字，贡献卡按需 |
| **组织账号（Organization）** | —— | **不适用**。`audit_profile.py` 会直接拒绝，组织的 README 走 `<org>/.github/profile/README.md` |

判据由 `audit_profile.py` 自动分档（★≥500 → 强信号），别拍脑袋。
**星数取不到时它给「未能判定」而不是硬判成弱**——那是真实状态，不是缺陷。

## 铁律：表述强度 ≤ 证据强度

所有数字必须能从公开 API 复算，不能写「熟悉 X」而仓库里没有 X。
贡献卡每个数字都能在 `https://github.com/search?q=author:<user>+is:pr+is:merged` 点出来，
卡片底部也印了这句话。违反一次，整张卡就变成装饰品。

## 三条核心判断

**① 一屏一个视觉焦点。** 用户原话：「一点都不高级，搞得很复杂，面试官抓不住重点」。
一张图只允许一个焦点数字或一句定性 → 一条支撑证据链 → 结束。
hero 的焦点是名字，贡献卡的焦点是 **PR 总数**，两图不争。

**② 不依赖第三方实时服务。** 见 `references/widget-liveness.md`：
`github-readme-stats` 已 503 + 官方弃维护、`profile-trophy` 402、`metrics.lecoq.io` 500。
**唯一稳的路线 = 自己生成 SVG 提交进仓库**，GitHub Actions 每日刷新。

**③ 深浅双版用 `<picture>`，不用 SVG 内 CSS。**
`<img>` 里的 `@media (prefers-color-scheme:dark)` 按**操作系统**判断，
且 WebKit（Safari / GitHub iOS App）不生效（WebKit bug 199134）。
GitHub 会把 `<picture>` 包成 `<themed-picture>`，跟随**站点主题**。

## 官方 logo 怎么进 SVG（这条决定贡献卡长什么样）

GitHub 给 raw SVG 的响应头是：

```
Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; sandbox
```

2026-11 用同款响应头在本地 1:1 复现实测（`<img>` 加载、截图数像素）：

| 嵌法 | 结果 |
|---|---|
| `<image href="data:image/png;base64,…">` | ✅ **显示**（64×64 → 4096 红色像素，完全吻合） |
| `<image href="https://…">` 外链 | ❌ 全拦（0 像素） |
| 内联 `<circle>` / `<rect>` 矢量 | ✅ 显示（对照组） |

**结论：官方 logo 只能 base64 内嵌。** 一张 64px 头像约 3KB，base64 后 4KB，
6 个仓库的卡约 25KB——完全可接受，换来「单文件自包含、不依赖 camo、不会某天开天窗」。

### logo 从哪来（默认就是官方头像）

```
--logo owner=path      临时指定（极少用）
logos/<owner>.svg|png  你自己想覆盖的组织
GitHub 官方头像        默认走这条，owner.avatar_url?s=64
首字母方块             兜底，并提示你补文件
```

**刻意不内置任何品牌图标库。** 内置 25 个图标要 98KB，而且上游换 logo 就过期、
还牵扯商标归属；而 owner 头像本身就是官方标识，实时拉永远是最新的，一张才 3KB。
矢量更清晰这点收益，不值得让整个 skill 变重。

真要覆盖某个组织，把文件丢进 `logos/` 或用 `--logo`，细节见 `logos/README.md`。
缺 logo 时脚本会把「放哪个路径 / 用什么参数」直接打印出来，不会静默留空。

## 六层，README 只是第三层

改 README 之前先看这六层，改错层性价比极低：

| # | 层 | 控制方式 | 60 秒内被看到 | 成本 |
|---|---|---|---|---|
| 1 | 头像 | 设置 → Public profile | 100% | 10 分钟 |
| 2 | 名字 + bio（160 字符） | 同上 | 100% | 5 分钟 |
| 3 | **Profile README（含贡献卡）** | `<user>/<user>` 仓库 | 90% | 小时级 |
| 4 | Pinned repositories（6 个上限） | 网页 Customize pins（**无 API**） | 80% | 20 分钟 |
| 5 | 社交链接（4 个上限） | 设置 → Social accounts | 60% | 5 分钟 |
| 6 | 贡献图 | 只能靠真实提交 | 50% | 不可伪造 |

**先做 1/2/4，再动 README。** 详情见 `references/content-model.md`。

## 四套主题预设

默认 **T1 编辑排版风**。选型看用户身份，不看他喜欢什么：

| 预设 | 一句话 | 适合 | 一票否决 |
|---|---|---|---|
| **T1 Editorial** | 透明背景、无卡片、发丝线、mono 眉行 + 大标题、单一强调色 | 想显克制/成熟，多数技术岗 | 再叠图标墙 = 自相矛盾 |
| **T2 Terminal** | 全等宽、提示符、光标、终端窗口装饰 | 后端 / 系统 / Agent / CLI | 中文标题别用等宽（字宽不齐） |
| **T3 Card** | 圆角 + 1px 边框 + bg.inset 底，最多 2 张 | 信息量大 | 超过 2 张就变仪表盘 |
| **T4 Minimal** | 零 SVG，纯 Markdown 排版 | 不想维护 | 内容不足以填满一屏时别用 |

完整规格见 `references/design-system.md`；强调色是独立参数：`purple|blue|green|orange`，取值一律 Primer token。

---

## 流程

> 脚本都在 `scripts/` 下，用绝对路径调用，不要假设 cwd。

### S1 审计（先跑脚本，别靠眼看）
```bash
python scripts/audit_profile.py <username>
```
输出六层实际状态 + 外链图片存活 + 反模式命中 + 按信号强度分档的待修清单。
**这一步决定后面改什么**，跳过就会美化了不该改的层。
组织账号会被拒绝并给出正确入口；星数取不到时标「未能判定」，不会硬判成弱。

### S2 定主题 + 定口径
一次问完两件事：
- 给谁看（面试官 / 开源同行 / 自己）→ 决定 T1–T4
- 只算「已合并 PR」还是也含 open → 未验证的声明会稀释可信度，
  但要主动提示代价：知名仓库往往还在待审，过滤后品牌信号会消失

### S3 身份层：出 hero 骨架
```bash
python scripts/scaffold.py --theme t1 --name "张三" --latin "San Zhang" \
  --eyebrow "AGENT DEVELOPER" --tagline "一句话说清你在做什么。" \
  --sub "身份 · 专注方向" --out ./profile
```
`t4` 不出 SVG。换强调色加 `--accent purple|blue|green|orange`。
名字过长会自动缩字号、再不行截断——**不会让字被画布裁掉**。

### S4 证据层：出贡献卡（这一步是重点）
```bash
python scripts/generate_contrib.py <username> --out ./profile --top 4
```
- 拉 `search/issues?q=author:<user>+type:pr+is:merged+-user:<user>`（**排除自己的仓库**）
- 逐仓库用 `repo:` 维度精确查 PR 数——样本里数出来的会差一到两个数量级
  （实测 antfu 的 vitejs/vite：样本 1，真实 130）
- 拉 `stargazers_count` + 仓库描述；logo 走 `logos/` 四档解析
- 输出 `assets/contrib-{light,dark}.svg` + 缓存 `assets/contrib.json`
- README 里有 `<!-- CONTRIB:BEGIN -->` … `<!-- CONTRIB:END -->` 就自动回写
- `--offline` 用缓存重渲染（本地出图、CI 联网刷新的标准姿势）
- `--sort prs|stars`：默认按贡献深度；`--top N` 展示几个仓库
- `--logo owner=path` 覆盖单个组织的 logo；`--avatar-only` 只用官方头像

**排序口径**：他人仓库 > 自有项目；默认按**每个仓库的已合并 PR 数**降序
（卡片叙事是「贡献深度」，不是「蹭到了多少大仓库」），star 作为每行的展示信息。
自己给自己合并的 PR 默认排除，排除数量会在终端明确打印出来。

### S5 组装 README
硬规则：
- 每张图用 `<picture>` 包，`<img>` 本身不要再裸放
- 深浅双版 `<source media="(prefers-color-scheme: dark)">`
- 动态回写区间用标记：`<!-- CONTRIB:BEGIN/END -->`、`<!-- STATS:BEGIN/END -->`
- 排序按**含金量不按时间**

### S6 验证（交付前必做）
```bash
python scripts/verify_render.py <username>
```
跑的是**线上页面**：`<picture>` 双版是否配齐、亮暗两套图是否各自 200 且 `content-type: image/*`、
SVG 内有没有会被 GitHub 掐掉的东西（`<script>`、远程字体、**外链图片**——logo 必须是 data URI）、
是否缺 `<title>` / `viewBox`。

截图肉眼看（三平台都行，找到 chrome/chromium 即可）：
```bash
# Windows: C:/Program Files/Google/Chrome/Application/chrome.exe
# macOS:   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome
# Linux:   google-chrome 或 chromium
<chrome> --headless --disable-gpu --screenshot=out.png \
  --window-size=806,400 "file:///<预览页绝对路径>"
```
**必须按 806 宽渲染**（962 原生宽看不出真实观感）；中文路径会让 headless 写文件失败，输出图放 `/tmp` 或 `%TEMP%`。

### S7 自动化
`.github/workflows/update-stats.yml`：`schedule` 每日 + `workflow_dispatch` +
`paths: scripts/**` 的 push 触发；`permissions: contents: write`；提交带 `[skip ci]`。
GitHub 的 schedule 实际会晚 15–45 分钟，要立刻看到效果就
`gh workflow run update-stats.yml --repo <user>/<user>`。

---

## 反面清单（会被判定为业余）

- 打字动画、访客计数器、旋转 logo、徽章墙（>6 个徽章就是纹理不是信息）
- 「正在学习」清单超过 3 项 —— 三个月后就是谎话，没人回来删
- 2 张以上重复统计卡片堆叠
- 空描述仓库被 pin（GitHub 渲染成空白卡）
- 用低信号提交刷贡献图（`docs: fix typo` 连刷）—— 招聘方看得懂
- README 写「Hi there 👋」模板 / emoji 轰炸
- 只有机制没结果：「使用了 React」；应该是「React + 30 个组件，首屏 1.2s」
- **贡献卡里混入自有项目的 PR 却标「上游合并」**（口径造假，比难看严重）

判断标准：**把仓库名/用户名遮住，这张卡片还能原样贴到别人主页上吗？**
能 → 重做，它没承载任何个人信息。

## GitHub 渲染硬规则速查

完整白名单/剥离清单见 `references/github-rendering.md`。最容易踩的五条：
1. README 内联 `<svg>` 会被剥离 → 必须存成文件用 `<img src="./x.svg">` 引用
2. 裸 `<img>` 用 `<p>` 包住；`<picture>` 是块级容器，顶层放即可，**不必**再包
3. `<img>` 加载的 SVG **不能引用任何外部资源**（字体、图片、CSS）——CSP `default-src 'none'`；
   **图片只能 base64 内嵌**（2026-11 实测，见上文）
4. 外链图片走 `camo.githubusercontent.com` 代理；仓库内相对路径**绕过 camo**
5. 卡片按 962 宽设计 → GitHub 内容列约 806，等比缩到 0.84。
   **实际观感 = 设计字号 × 0.84**（实测 44→37、15.5→13、13→11）。
   推荐 大标题 44–52 / 正文 15.5–18 / 脚注 ≥13

## 参照实现

`shi-felix/shi-felix` 是 T1 + 贡献卡的完整活样本：hero + 贡献卡 + snake + 每日 Actions。
改版时先读它，不要从零想。

## 多语种与跨平台（别人的机器上也得对）

- 字宽模型按 Unicode 分档：汉字/假名/谚文/全角 1.0em、emoji 1.15、拉丁五档、
  西里尔/阿拉伯/泰文 0.60em。**CJK 是 0 误差，其余语种 ±5–7%**
- 因此 `fit_headline` 留了 **4% 安全余量**，任何估算误差都不会让字被裁掉
- 字体栈 macOS 走 SF Pro、Windows 走 Segoe UI，同一串字实际宽度不同 →
  贴边元素（如 T2 光标）算完还会按画布钳一次，不会飞出画布
