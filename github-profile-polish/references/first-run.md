# 首次使用与配置

## 最短路径

有 Python 3.10+ 即可，不必安装 npm、图标库、GitHub CLI 或第三方统计服务。先在终端切换到 `github-profile-polish` 目录；也可以把命令中的脚本路径换成该文件的绝对路径。

在 AI 助手中使用时，把整个目录放入该助手支持的 skills 目录，或让助手读取本目录的 `SKILL.md`；不要只复制入口文件而丢掉 scripts 和 references。也可以完全不安装到助手，直接通过下方终端命令使用。

先看预设，再填自己的信息：

```bash
python scripts/build_profile.py --gallery ./style-preview
python scripts/build_profile.py --init ./profile.json --username YOUR_USERNAME
```

将 `YOUR_USERNAME` 替换为个人 GitHub 用户名。配置初始内容只包含该账号名和空列表，不替用户填写履历、邮箱或项目。编辑配置后：

```bash
python scripts/build_profile.py --config ./profile.json --mode projects --theme t2 --out ./my-profile
python scripts/verify_render.py --local ./my-profile
```

打开 `my-profile/preview.html`。确认效果后，才把生成文件复制或合并到公开同名仓库的工作目录并查看 diff。**不要把示例配置或风格图库中的演示内容当成个人成果发布。**

如果通过 AI 助手使用，只需提供账号和偏好。例如：“用这个 skill 帮我美化 GitHub 主页，用户名为……，用极简风，先只生成预览，不上传。”助手负责配置与执行。

## 个人配置

示例中的账号、名字、链接和文案都要替换成自己的；没有某项就删掉或保留空列表：

```json
{
  "username": "your-username",
  "name": "你的名字",
  "latin": "",
  "eyebrow": "DEVELOPER / MAKER",
  "tagline": "用一句真实的话说明你在做什么。",
  "sub": "",
  "theme": "t1",
  "accent": "blue",
  "mode": "projects",
  "language": "zh",
  "projects": [
    {
      "name": "你的作品",
      "url": "https://github.com/your-username/your-project",
      "description": "它解决什么问题，以及你真实做过的部分。"
    }
  ],
  "links": [
    {"name": "个人网站", "url": "https://example.com"}
  ]
}
```

- `username` 是 GitHub 账号名；显示名可以是中文、英文或其他文字。不会从邮箱自动猜账号。
- `name` 为空时显示用户名；`latin / tagline / sub` 为空时省略，不塞占位段落。
- `eyebrow` 默认为中性的 `PROFILE`，不推断职业；确认角色后可以改成自己的定位。
- `projects` 最多 6 项，可链接代码仓库、文章、设计作品或演示站；不要求都是编程项目。
- `links` 最多 4 项，接受完整 http(s) 地址和 `mailto:you@example.com`。这些信息将公开，需本人确认。
- 描述由本人确认，不能用一个 star 数代替个人贡献，也不能编造性能或用户指标。生成器不会自动验证站外作品说明的真实性。
- `language` 控制生成内容的常用标题，`zh` 为中文、`en` 为英文；不自动翻译用户自己的文字。
- CLI 的 `--theme / --accent / --mode / --language` 可以覆盖配置，只影响本次生成。生成目录内的 `profile.json` 记录实际采用的配置。
- 不接受额外的 `token / password / api_key` 等字段，凭证只通过环境或已有认证取得。

快速生成也可不用 JSON：

```bash
python scripts/build_profile.py --username YOUR_USERNAME --name "你的名字" --tagline "真实的一句话定位" --mode projects --theme t4 --out ./my-profile
```

## 风格选择和预览

`t1 / t2 / t3 / t4` 是四种不同布局，不只是换颜色。`blue / purple / green / orange` 独立选择。默认 `t1 + blue`，用户可以自由选择任何组合。

```bash
python scripts/build_profile.py --config ./profile.json --gallery ./my-style-preview
```

图库只离线比较身份层，不查贡献。各风格标题可以打开完整的介绍和作品预览；真实贡献生成后使用对应输出目录的 `preview.html` 检查。

本地预览模拟常见的 GitHub 颜色和内容宽度，不调用 GitHub Markdown 渲染器。SVG 随容器缩放，窄屏文字会变小；更重视移动端可读性时，优先选 `t4`。长名字会缩小或截断，完整名字仍保留在图片描述和配置中。

## 真实贡献和缓存

```bash
python scripts/build_profile.py --config ./profile.json --mode auto --out ./profile-live
```

默认只统计用户给其他**公开**仓库的已合并 PR。没有 PR 是正常结果，会保留介绍与作品；请求失败则停止，不会显示一个假零。

这里的“其他仓库”按 `-user:USERNAME` 排除账号名下仓库，并不自动判断组织仓库是不是本人维护的项目。属于自己的组织项目时，应如实说明贡献范围，不能把一个搜索结果当作“被独立第三方采纳”的证明。

匿名访问有 API 限流。有需要时，在本机使用已有 `gh auth login`，或安全设置 `GH_TOKEN / GITHUB_TOKEN` 环境变量。不要把真实 token 放进 JSON、截图、shell 历史中的演示命令或 README。

已有输出重排版时，可以显式使用同一账号的缓存：

```bash
python scripts/build_profile.py --config ./profile-live/profile.json --offline --overwrite --theme t3 --out ./profile-live
```

这会重建同名生成文件，先保存并确认现有 README 的手写内容。缓存必须匹配用户、公开范围与统计口径；旧版本缺少 `scope / visibility` 的缓存需联网重新获取，不会被静默当成可信数据。缓存时间是上次内容变化的时间，离线生成不代表数据刚刚刷新。

只刷新贡献、保留 README 标记外的手写内容：

```bash
python scripts/generate_contrib.py YOUR_USERNAME --theme t3 --out ./profile-live
```

低层工具可显式使用 `--include-self`，此时展示“包含自有仓库”，不会标成上游贡献。切换口径后需重新生成匹配缓存。

## 自动刷新与发布

```bash
python scripts/build_profile.py --config ./profile.json --mode auto --automation --out ./profile-live
```

生成目录会附带工作流和其依赖的三个脚本；无需额外 pip 安装，也不依赖原 skill 路径。将它们一起发布到 `USERNAME/USERNAME`，并在仓库中允许 GitHub Actions 的读写权限。

- 默认定时为 UTC `03:23`，即北京时间 `11:23`；GitHub 不保证准点，必要时从 Actions 手动触发。
- 工作流使用内置 `secrets.GITHUB_TOKEN`，不把个人 token 放进提交。
- 数据或检查失败时不提交；内容不变时不新增机器人提交。
- 只刷新 `CONTRIB:BEGIN / END` 标记区；自定义文字放在标记外。
- 自动任务不是默认必选项；`projects` 模式不生成贡献刷新工作流。
- 若已有目录包含刷新工作流，不会无声切换成纯作品模式；换新目录，或先明确处理旧工作流。
- 重新分发脚本时保留原 skill 仓库的许可证，不改变已有项目的许可证声明。

本地工具不自动建仓、上传、设置 bio 或置顶仓库。发布之前，核对目标账号、公开信息和 diff；发布后：

```bash
python scripts/verify_render.py YOUR_USERNAME
```

仍需实际查看 GitHub 页面，分别检查亮暗主题、链接与移动端。只有本地检查通过不能说“线上主页已完成”。

## 常见问题

| 问题 | 处理 |
|---|---|
| 提示拒绝覆盖已有文件 | 换输出目录；确认文件清单后才用 `--overwrite`。其他文件不会删除 |
| API 401 / 403 / 429、连接或代理失败 | 检查认证和额度，稍后重试；先 `projects` 离线排版，或显式使用匹配缓存 |
| `contributions` 模式没有 PR | 改成 `auto / projects`；不必为了美化主页刷 PR |
| 缓存不存在、属于其他账号、口径未知 | 重新联网生成；不同账号使用不同目录 |
| JSON 无法解析 | 使用有效 JSON、UTF-8，不能有尾随逗号；检查字段类型，不粘贴凭证 |
| 中文终端编码异常 | 使用 `python -X utf8`；脚本会兼容输出编码，生成文件仍为 UTF-8 |
| 标记重复或顺序错误 | 保留一组顺序正确的 `CONTRIB:BEGIN / END`，不要让工具猜替换位置 |
| 线上图片 404 或旧图未更新 | 检查是否提交了 assets 和相对路径；复查实际线上页面，不只看本地预览 |
