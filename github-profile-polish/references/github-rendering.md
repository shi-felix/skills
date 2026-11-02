# GitHub 渲染硬规则（写 SVG / README 之前必须知道）

标注约定：**【实测】** = 本机对线上页面/接口验证过；**【来源】** = 外部文档或他人实测，
本机未复现。不要把【来源】当【实测】引用。

## 1. 一张图从 README 到读者眼睛的完整链路

```
README.md 里的 Markdown / <img>
  → GitHub 的 HTML sanitizer（剥离 script / 内联 svg / 事件处理器）
  → 相对路径：改写为 /<user>/<repo>/raw/<branch>/<path>，由 GitHub CDN 直接给
    外链：改写为 https://camo.githubusercontent.com/<sha256>/<hex(原URL)>
  → <picture> 被包成 <themed-picture data-catalyst-inline="true">  【实测】
  → 浏览器加载。注意这是**两套不同的 CSP**：
      README 所在页面：default-src 'none'; img-src data:; style-src 'unsafe-inline'  【实测·CSP 头】
      raw SVG 文件本身：default-src 'none'; style-src 'unsafe-inline'; sandbox      【实测·curl -I】
```

**【实测】对比证据**
- `github.com/shi-felix` 渲染出的 `<img src="/shi-felix/shi-felix/raw/main/assets/hero-light.svg">`
  —— 相对路径**不走 camo**，直接被改写成仓库内路径。
- `github.com/anuraghazra/github-readme-stats` 页面上 `camo.githubusercontent.com`
  出现 **190 次**，所有 shields.io / vercel 按钮全部被代理。
- camo 的 URL 结构：`/<sha256(原始URL)>/<hex(原始URL)>`。
  **缓存键是 URL 本身** → 同一个 URL 换了图片内容，camo 可能还给旧图，直到缓存过期。
  所以外部图床「更新同名文件」是不可靠的；相对路径每次都跟着 commit 走。

## 2. 会被剥离 / 失效的东西

| 写法 | 结果 | 依据 |
|---|---|---|
| README 里内联 `<svg>...</svg>` | 整个标签被剥掉 | 【来源】html-pipeline sanitization_filter |
| `<script>` | 剥离 | 【来源】同上 |
| `onclick=` 等事件处理器 | 剥离 | 【来源】同上 |
| `javascript:` 链接 | 剥离 | 【来源】同上 |
| `<foreignObject>` | 高风险，不保证渲染 | 【来源】 |
| SVG 内引用远程字体 / `@import` / `<image href="https://...">` | 不加载 | 【实测】CSP `default-src 'none'` |
| `<img>` 里的 `@media (prefers-color-scheme)` | 按**操作系统**判断，且在 WebKit 不生效 | 【来源】WebKit bug 199134 |
| `#gh-dark-mode-only` / `#gh-light-mode-only` URL 片段 | **已废弃** | 【来源】GitHub Docs |

**能用的**：
- SMIL 动画（`<animate>` / `<animateTransform>`）—— 贪吃蛇就是这么动的【来源】
- SVG 内 CSS（`<style>` + `@keyframes`），字体只能用系统字体栈【来源】
- 透明背景、渐变、滤镜（滤镜别太重）【来源】
- **`data:` URI 内嵌图片**（官方 logo 走这条）【实测】

#### `data:` URI 到底能不能用（2026-11 结论）
raw SVG 的响应头是 `default-src 'none'`，**没有** `img-src data:` 豁免，
按字面读似乎应该把内嵌图片也拦掉。实测不是：

把三个 SVG 用**同一份响应头**（`default-src 'none'; style-src 'unsafe-inline'; sandbox`）
挂在本地 HTTP 服务上，再用 `<img>` 加载、截图数像素：

| 嵌法 | 红色像素 | 结论 |
|---|---|---|
| `<image href="data:image/png;base64,…">` 64×64 纯色 | 4096（= 64×64，完全吻合） | ✅ 显示 |
| `<image href="http://127.0.0.1/logo.png">` | 0 | ❌ 拦截 |
| 内联 `<circle r="32">` 对照组 | 3182（≈ π·32²） | ✅ 显示 |

**判据**：外链一律死，`data:` 一律活。所以官方 logo / 头像只能 base64 内嵌，
一张 64px 头像约 3KB（base64 后 4KB），6 个仓库的卡约 25KB。

## 3. 结构坑

### 3.1 `<img>` 必须包在 `<p>` 里
> 【来源】裸 `<img>` 作为 Markdown 容器的直接子元素时，GitHub 会给它加
> `js-gh-image-fallback`（`display:block`），破坏段落间距；且会被包一层指向
> 原图的 `<a>` 链接。

本机在两个样本页面上**未观察到** `js-gh-image-fallback`（因为它们的图都在 `<p>` 或
`<picture>` 里）。结论不变：**一律用 `<p>` 包**，成本为零，能规避未知行为。

```html
<!-- ✅ -->
<p><img src="./assets/card-light.svg" width="100%" alt="..."></p>

<!-- ❌ 裸 img -->
<img src="./assets/card-light.svg" width="100%">
```

### 3.2 深浅双版用 `<picture>`，不要用 SVG 内 media query
```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/card-dark.svg">
  <img src="./assets/card-light.svg" width="100%" alt="已合并的 Pull Request">
</picture>
```
**【实测】** GitHub 把 `<picture>` 包成 `<themed-picture data-catalyst-inline="true">`，
由这个自定义元素把 `prefers-color-scheme` 劫持成**跟随站点主题设置**，
所以用户 OS 是亮色但 GitHub 选了暗色，也能正确切图。

注意 `alt` 只写在 `<img>` 上，`<source>` 不写。

### 3.3 SVG 总是加 `width="100%"`
`<img width="100%">` 让 962 宽的卡片在 806 内容列里等比缩放。
不加会按原始像素溢出或者被裁。

## 4. 尺寸与可读性

- GitHub 主页内容列约 **806px**，卡片设计宽 **962**，缩放比 **0.84**
- 缩放后字号 = 设计字号 × 0.84 → **设计时要放大 1.19 倍**
- 实测下限：SVG 内字号 ≥ 15（装饰）/ ≥ 16（正文），且用 `fgColor-muted` 以上
- 不要用 `fgColor-disabled` 写正文（3.5:1，不达 AA）

## 5. Markdown 层的坑

| 坑 | 现象 | 解法 |
|---|---|---|
| 表格列太窄 | 日期 `2026-09-18` 被折成两行 | 写 `09-18`，年份在表格上方写一次 |
| 标题尾部 `(#123)` | 与右侧 PR 号重复、易被截断 | 入库前 `re.sub(r"\s*\(#\d+\)\s*$", "", title)` |
| `<sub>` 里的 `**` 加粗 | 部分渲染器不生效 | 需要强调就别套 `<sub>` |
| HTML 注释做标记区间 | 会出现在「View source」里，但**不渲染** | 用 `<!-- STATS:BEGIN -->...<!-- STATS:END -->` 是安全做法 |

## 6. 验证方法（照做，别靠肉眼）

### 6.1 单张 SVG 肉眼检查（最快，零依赖）
```bash
<chrome> --headless --disable-gpu --screenshot=out.png \
  --window-size=<svg width>,<svg height> file:///<svg 绝对路径>
```
chromium 怎么找（三个平台都有现成的，不需要 `npm i` 任何东西）：
- Windows：`C:/Program Files/Google/Chrome/Application/chrome.exe`，
  或已装 playwright 的 `%LOCALAPPDATA%/ms-playwright/chromium-*/chrome-win64/chrome.exe`
- macOS：`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- Linux：`google-chrome` / `chromium` / `chromium-browser`（`command -v` 试一下）

### 6.2 线上最终态
```bash
curl -sI "https://github.com/<user>" | head -1                 # 200
curl -s "https://github.com/<user>" | grep -c "assets/"          # README 图被引用
```
再用 playwright 打开主页，遍历所有 img 断言 `naturalWidth > 0`
（能查出「图挂了但页面不报错」这种最常见的静默失败）：
```js
for (const el of await page.locator('article img').all()) {
  const w = await el.evaluate(i => i.naturalWidth);
  if (!w) throw new Error('broken: ' + await el.getAttribute('src'));
}
```

### 6.3 深浅双版要分别验证
playwright 用 `newContext({ colorScheme: 'dark' | 'light' })` 各开一次，
断言 `img.currentSrc` 指向对应文件。**只验亮色会漏掉暗色版画错的情况。**

### 6.4 数据映射
正则抽 SVG 里的 `<title>日期` 和 `fill`，跟真实数据逐条 assert，
不要靠肉眼数格子（热力图尤其容易数错一行）。
