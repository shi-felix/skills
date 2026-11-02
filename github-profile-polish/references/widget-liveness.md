# 第三方挂件存活实测与替代方案

## 为什么必须先实测

绝大多数「GitHub 主页美化」教程都在教你贴一行 stats 卡片 URL。
问题是这些服务**没有 SLA**，是个人用 Vercel 免费额度跑的，挂了你不会收到通知——
只会某天有人发截图给你「你主页图裂了」。

**判据永远是自己 curl 一遍，不要引用文章的推荐。** 下面的表是
**2026-11-01 本机实测**，隔一个月就要重测。

## 实测结果（2026-11-01）

| 服务 | URL | HTTP | 耗时 | 判断 |
|---|---|---|---|---|
| github-readme-stats | `github-readme-stats.vercel.app/api` | **503** | 2.1s | ❌ 已死 |
| github-readme-stats | `.../api/top-langs/` | **503** | 0.7s | ❌ 已死 |
| github-profile-trophy | `github-profile-trophy.vercel.app` | **402** | 1.4s | ❌ Vercel 欠费 |
| metrics (lowlighter) | `metrics.lecoq.io` | **500** | 8.7s | ❌ 已死 |
| streak-stats | `streak-stats.demolab.com` | 200 | 2.4s | ✅ 存活 |
| capsule-render | `capsule-render.vercel.app/api` | 200 | 1.4s | ✅ 存活 |
| readme-typing-svg | `readme-typing-svg.demolab.com` | 200 | 1.5s | ✅ 存活 |
| skillicons | `skillicons.dev/icons` | 200 | 2.1s | ✅ 存活 |
| visitor counter | `komarev.com/ghpvc` | 200 | 3.8s | ✅ 存活（但别用，见下） |
| shields.io | `img.shields.io` | 200 | 1.3s | ✅ 存活 |

### 关于 `github-readme-stats`（最常被推荐的那个）
- 2026-06-30 上游 commit `docs: add deprecation notice to readme (#4895)`：
  README 首行挂出 **"This repository is no longer maintained"**，
  指向继任项目 **GitHub Stats Extended**（活跃 fork）或 **GitHub Readme Stats Action**。
- 追溯原因（上游 issue #1471）：7 个轮换 PAT（约 35k GraphQL points/hr）被打爆，
  即使 Vercel 缓存命中率约 73%。根因是**每次渲染都调 GitHub API**。
- 所以即使哪天 503 恢复，**也不要再推荐它**——它已经没人修 bug 了。

## 复测脚本（要贴进任何方案前先跑）

```bash
for u in \
"https://streak-stats.demolab.com?user=<user>" \
"https://capsule-render.vercel.app/api?type=waving&text=x" \
"https://img.shields.io/badge/a-b-blue" \
; do
  echo "$(curl -s -o /dev/null -w '%{http_code} %{time_total}s %{content_type}' \
        --max-time 12 "$u")  <- $u"
done
```
判据：**HTTP 200 且 `content_type` 以 `image/` 开头**。
返回 200 但 content-type 是 `text/html` 说明是错误页，一样是死的。

## 决策：什么时候可以用第三方

| 场景 | 结论 |
|---|---|
| 数据在你自己仓库里（PR 数、仓库 stars） | **必须自产**。别人挂了不该拖垮你 |
| 纯装饰、挂了也不影响信息（分隔条、图标） | 可以用，但最多 1 个 |
| 强时效数据（Spotify 在听、wakatime） | 只能用第三方，接受它会坏 |

自产的三个结构性优势（不只是「更可控」）：
1. **绕过 camo**：仓库内相对路径由 GitHub CDN 直给，外部服务走 camo 缓存
   （缓存键 = URL，内容更新可能不生效）
2. **不受共享 API 限流**：Actions 用的是你自己的 token 和额度
3. **没有运行时依赖**：静态文件不会 500

## 个人黑名单（不管实测通不通）

| 东西 | 为什么不用 |
|---|---|
| 访客计数器（komarev 等） | 零信息量，被明确列为业余信号；数字本身也没有意义 |
| 打字动画（readme-typing-svg） | 被多个来源点名「显得初级」；且动画抢走唯一焦点 |
| 奖杯墙（profile-trophy） | 徽章墙变体，信息密度为零 |
| 「技能雷达图」 | 自己给自己打分，不可验证，等于自夸 |
| 3D 贡献城市 / 贡献热力大图 | 看起来炫，实际在把有用内容往下挤 |
| 多个 stats 卡叠放 | 每多一张就多一个会坏的依赖 |

唯一例外：**贡献贪吃蛇**。它被广泛接受，但要在贡献历史里堆积自动化提交——
主动告知用户代价，让他自己决定。

## 自产方案的骨架

```
scripts/generate_stats.py     # 纯标准库，拉 API → 算布局 → 输出亮暗两版 SVG
assets/stats.json             # 缓存，支持 --offline
assets/card-light.svg / -dark.svg
.github/workflows/update-stats.yml
README.md                     # <!-- STATS:BEGIN --> 区间由脚本回写
```

生成器要点（完整实现参考 `shi-felix/shi-felix` 的 448 行版本）：
- `GITHUB_TOKEN` 或 `gh auth token` 鉴权；无 token 时公开 API 60 req/hr 也够
- 取数用 `search/issues?q=author:<user>+type:pr+is:merged`，**不要**用
  MCP 的 `list_pull_requests`（`head` 参数会被忽略，返回整个仓库的 PR）
- 增删行数只有 `/repos/{o}/{r}/pulls/{n}` 有，search 结果里没有
- 交付周期用原始时间戳自己算（`merged_at - created_at`），
  别用后端四舍五入过的小时数（会把 2 分钟记成 0.0 小时）
- 失败重试：`urllib` + 6 次退避，`timeout=15`。本机对 `api.github.com`
  的连通性不稳定，`gh` CLI 会 `TLS handshake timeout`，python 直连更稳
