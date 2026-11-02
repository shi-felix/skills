# logos/ · 自备 logo（默认为空）

## 默认不用放东西

贡献卡左侧的 logo，**默认直接取仓库 owner 的 GitHub 官方头像**（`avatar_url?s=64`）。

这是刻意选的：

- **权威** —— 上游换了 logo，卡片自动跟上，不需要回来改 skill
- **零维护** —— 不用维护一份会过期的品牌图标表
- **体积小** —— 内置 25 个图标要 98KB，而头像每张只有 3KB，且随用随取
- **少一层商标问题** —— 不随 skill 分发第三方品牌资产

所以这个目录平时是空的，脚本也不会因为它是空的而报错。

## 什么时候需要放东西

只有一种情况：**你想让某个组织显示成一张特定的图**，而不是它现在的头像。比如：

- 头像在暗色背景下看不清
- 想用矢量图（矢量在 2x 屏上比 64px 头像锐利）
- 该组织头像本身不是它的产品 logo

## 怎么放

用 GitHub 组织登录名命名，丢进本目录：

```
logos/langgenius.svg     # 对应 github.com/langgenius
logos/bytedance.png      # png 也行
```

支持 `.svg` / `.png` / `.jpg` / `.webp`。或者不落盘，生成时临时指定：

```bash
python scripts/generate_contrib.py <user> --logo langgenius=./dify-logo.svg
```

可取用优先级：

```
--logo owner=path     临时指定
  ↓
logos/<owner>.svg|png 你放在这里的
  ↓
GitHub 官方头像        默认走这条
  ↓
首字母圆角方块         兜底，同时终端会提示你补文件
```

`--avatar-only` 可以强制跳过前两档，只用官方头像。

## 关于 SVG 的颜色

自备的 SVG 如果是**单色路径**（没写 `fill`），生成时会注入主题文字色，
所以同一个文件在亮色 / 暗色下都看得见。已经写了 `fill` 的彩色 logo 不受影响。

如果你的 SVG 是彩色的但只想在亮色下用，那就准备两个文件、用 `--logo` 分两次生成——
本 skill 不做按主题切换 logo 的事（只有 hero / 卡片本身分亮暗双版）。

## 找不到 logo 时

脚本不会静默留空，会打印：

```
以下 N 个组织没取到 logo（网络失败且没有本地文件）：
  <owner>
  ① 把 SVG/PNG 放到 .../logos/<owner>.svg
  ② 生成时指定：--logo <owner>=<你的文件路径>
```

图依然会出，只是那个位置是首字母方块。**断网也能出完整卡片**，这是这条链路的设计目标。
