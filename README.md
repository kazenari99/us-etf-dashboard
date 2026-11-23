# ORBIT PULSE · 美股 ETF 动量看板

由 GitHub Actions 每天生成快照、发布到 Cloudflare Pages 的美股 ETF 动量看板，从 Hermes 美股 ETF Momentum Radar 独立出来。

- 正式网址：<https://orbit-us.pages.dev>（GitHub Pages 镜像：<https://kazenari99.github.io/us-etf-dashboard/>）
- 运行记录：[Actions](https://github.com/kazenari99/us-etf-dashboard/actions)
- A 股配套：[JADE PULSE · A股ETF](https://jade-a.pages.dev/)

本页内容来自公开数据，仅供参考，不构成投资建议。

## 目录

1. [看板功能](#1-看板功能)
2. [数据与更新时间](#2-数据与更新时间)
3. [自动运行一览](#3-自动运行一览)
4. [需要人工处理的事](#4-需要人工处理的事)
5. [模型、回测与实盘跟踪](#5-模型回测与实盘跟踪)
6. [开发与测试](#6-开发与测试)
7. [故障排查](#7-故障排查)

---

## 1. 看板功能

### ETF 动量（首页）

- **ETF 池**：80 只非杠杆 ETF，9 个分组（宽基、行业板块、细分行业、主题、资源股、商品与另类、因子、债券、国际市场）。名单以 `scripts/momentum.py` 的 `UNIVERSE` 为准。
- **评分**：20/60/120 日收益在全部 ETF 中的百分位排名，按 0.3/0.4/0.3 加权（0–100），再加减趋势分：多头排列 +5、60 日跑赢 SPY +3、偏离 20 日均线过远 −8，所以可能超过 100。
- **状态**：动量成立 / 强势·等回踩 / 等待确认 / 趋势破坏。
- **市场状态（REGIME）**：根据 SPY 相对 200 日均线的位置、站上 200/50 日均线的 ETF 数量和 20/60/120 日上涨宽度自动生成标题与说明。
- **动量地图**：20 日 × 60 日收益散点图，圆点越大代表成交额越高。标签自动避让，不会互相重叠。
- **综合动量排名**：前 10 名。如果某只 ETF 与排在它前面的另一只高度相关（最近 120 个交易日的日收益相关系数 ≥ 0.90），名称旁会显示「≈ 代码」，提示两者其实是同一类机会。
- **当前交易机会**：「动量成立」的前 5 名，附带回踩区、突破触发价和失效参考价。手机上改为左右滑动。
- **明细表**：
  - 参考列：**12-1 动量**（12 个月前到 1 个月前的涨跌幅）和**波动调整排名**（先用收益除以同期波动再算评分，#1 最好）。两列只供参考，不影响评分和状态。
  - **5 日排名变化**：↑ 上升、↓ 下降、= 不变。
  - 表头悬停可看到列说明，表格下方「各列含义」有完整解释。
  - 手机上默认只显示代码、评分、5 日排名变化、状态四列，点「显示全部列」可展开；左右滑动时代码列固定不动。
- **详情框**：收益与风险数据、20 日评分走势小图、5 日前与 20 日前的排名、高度相关的 ETF、交易参考价、基金策略、发行机构和前 10 大持仓。
- **自选**：点代码旁的 ★ 收藏，再用「★ 自选」只看收藏的 ETF。收藏只保存在当前浏览器里。
- **分享链接**：打开详情后，地址栏会变成 `…/#etf=XLK`，直接打开这个地址就会显示该 ETF；详情框里也有「复制链接」按钮。
- **键盘**：明细表的行和综合排名都可以用 Tab 选中，按回车或空格打开；按 Esc 关闭，焦点会回到原来那一行。
- **语言**：English / 中文 / 日本語，首次访问默认英语，选择会保存在浏览器里。基金策略原文、发行机构和持仓公司的正式名称保留原文。

### 强势股筛选（`/#stocks`）

- 数据来自 VCPScanner 公开的 Minervini 候选列表：<https://anish1294.github.io/minervini-trend-template-screener/current.json>。这是源站按 RS 排序后预先筛选的候选，不代表全市场。本站不重算 RS，也不与 ETF 行情混在一起。保留来源归属及 MIT 许可。
- 默认条件为 RS ≥ 90、距 52 周高点 ≤ 25%、量比 ≥ 1.0。支持搜索、排序、浏览器本地自选和导出 CSV。点击股票会在新标签页打开 TradingView 日线图。
- 板块（Sector）来自 Yahoo 公司资料，每 30 天刷新一次；抓取失败时保留原有分类，不参与选股评分。
- 页面单独显示这份列表的数据交易日和抓取时间。源站滞后或抓取失败时，页面如实显示原来的日期。

### 基金资料

`scripts/refresh_funds.py` 单独更新基金资料：ARKK 优先使用 ARK 官方每日持仓 CSV，其余使用 Yahoo 基金资料。来源没有给出持仓日期时，页面会明确写「未知」，不会把抓取时间当作披露日期。持仓表里没有某只股票，不代表基金没有持有它，实物、期货和债券类基金尤其如此。持仓数据不参与评分。

---

## 2. 数据与更新时间

### 数据来源

- 行情使用 Yahoo Finance 的分红/拆股复权日线（yfinance，`auto_adjust=True`），不需要 API key、OpenD 或付费行情。
- 同一份快照绝不混用不同数据源或不同的复权批次。

### 更新时间（东京时间）

| 时间 | 内容 |
|---|---|
| 每天 07:00 | 刷新 ETF 数据（主力） |
| 每天 15:00 | 再刷新一次 ETF，给 Yahoo 修正前一天的日线留出时间 |
| 美东周一至周五 21:17、23:17 | 刷新强势股列表（比源站更新晚 1 小时；东京时间夏令时为 10:17/12:17，冬令时为 11:17/13:17） |

- 由 Cloudflare Worker 准点触发（见第 3 节），GitHub 自己的定时任务保留作后备。
- 刷新前用 NYSE 交易日历检查：东京时间前一天不是美股交易日时，直接跳过。日历同时处理休市、提前收盘和夏令时，收盘后至少等 1 小时才使用当天日线。
- 推送到 `main` 或手动运行，也会刷新并发布。手动运行时勾选 `stocks_only=true`，就只刷新个股。

### 数据规则与保护

- **全量才发布**：80 只 ETF 必须都有同一个交易日，并且窗口完整：最近 400 个自然日，至少 254 个交易日，这样才够算 12 个月动量。有缺失、非数值、OHLC 异常或日期对不上时会重试，仍然失败就不发布，线上保留上一份完整快照。
- **Yahoo 当天日线还没出**：如果唯一的问题是最新一根日线还没发布，会多等两轮（90 秒、180 秒）。还不行就推迟这次刷新，线上数据不变，运行结果不算失败，由下一次定时任务补上。
- **不会倒退**：每次运行前，先从最近一次成功发布中恢复线上数据；发布前再检查，日期比线上旧的快照一律拒绝发布。
- **部署自动重试**：GitHub Pages 偶尔会出现「找不到产物」的错误，这时等 60 秒后自动重试一次。
- **校验**：CSV 与元信息用 SHA-256 核对。页面会显示真实的行情日期、生成时间、数据来源和完整数量，超过 4 天没有新快照时会提示。
- **历史**：每次 ETF 刷新成功后，当天结果写入 `data` 分支（`etf/<交易日>.csv/.json` 和 `etf/index.csv`），长期保留。Actions 产物只保留 90 天。

---

## 3. 自动运行一览

| 工作流 | 什么时候运行 | 做什么 |
|---|---|---|
| `pages.yml` 发布 | 准点调度 / 推送 main / 手动 | 刷新数据、校验、发布 GitHub Pages，并写入 `data` 分支 |
| `cloudflare.yml` | 发布成功后自动运行 / 手动 | 把同一份产物发布到 Cloudflare（orbit-us 和 orbit），并核对线上页面 |
| `worker/` 调度 Worker | 东京 07:00、15:00；美东 21:17、23:17（工作日） | 准点触发 `pages.yml`（运行名为 `On-time <cron>`）。GitHub 自己晚到的后备运行如果发现同一场准点运行已经成功，就直接跳过 |
| `worker.yml` | `worker/` 有改动 / 手动 | 部署调度 Worker 和它使用的 token |
| `freshness.yml` | 每天东京 13:23、21:41 | 两个站点的 ETF 数据落后 ≥ 2 个交易日，或强势股列表落后 ≥ 3 个交易日时，开 `data-stale` issue；恢复后自动关闭 |
| `token-check.yml` | 每天东京 12:37 | `GH_DISPATCH_TOKEN` 离到期 ≤ 14 天或已经失效时，开 `token-expiry` issue |
| `live-report.yml` | 每月 2 日 | 生成实盘跟踪报告（见第 5 节） |
| Dependabot | 每周六 | 为 Python 依赖和 GitHub Actions 版本开升级 PR |
| `ci.yml` | 每个 PR | 单元测试、ruff、JS 语法检查、actionlint、快照校验、浏览器冒烟测试 |
| `backtest.yml`、`source-check.yml` | 仅手动 | 回测；备用数据源对比检查 |

---

## 4. 需要人工处理的事

平时什么都不用做。只有下面这些情况需要处理：

### 收到 `token-expiry` issue（每年一到几次）

准点调度用的 GitHub token 快过期了。
1. GitHub → Settings → Developer settings → Fine-grained tokens → **Generate new token**。Repository access 只选本仓库，Permissions 里把 **Actions** 设为 **Read and write**。
2. 仓库 → Settings → Secrets and variables → Actions，把 `GH_DISPATCH_TOKEN` 更新为新 token（不要截图，也不要贴到任何地方）。
3. Actions 里手动运行一次 **Deploy scheduler Worker**。

忘了也不会坏：token 过期后，只是退回到 GitHub 自己经常晚点的定时任务。

### 收到 `data-stale` issue

看 issue 正文的表格，判断是哪一部分落后了，然后按第 7 节处理。数据恢复后，issue 会自动关闭。

### Dependabot 升级 PR

CI 是绿的就直接合并。CI 是红的，通常是新版本有兼容问题，先不要合并，看 CI 日志里的报错。需要 Dependabot 重新整理时，在 PR 里评论 `@dependabot rebase`。

### 分支保护

`main` 要求 `check` 和 `browser` 两项检查通过才能合并（Settings → Branches）。

### 备用数据源（目前不启用）

`scripts/sources.py` 支持 Stooq，但只有设置了仓库变量 `FALLBACK_SOURCE=stooq` 才会启用。启用后，Yahoo 抓取失败时会整体改用 Stooq，不会和 Yahoo 混用。2026-11 的 **Source parity check** 发现，Stooq 对 GitHub Actions 返回的是网页而不是数据，结论是**不要启用**。以后想换别的备用源，先用这个检查验证。

### 导入本地 OpenD 快照（很少用）

运行 `python scripts/sync_snapshot.py ../etf-dashboard/dist` 导入，提交后手动运行发布，并勾选 `use_committed_snapshot`。发布前会核验它是最新的完整交易日、包含当前全部 ETF，且校验和一致。

### Cloudflare 首次配置（已完成，记录备查）

- `CLOUDFLARE_API_TOKEN` 需要 **Cloudflare Pages: Edit** 和 **Workers Scripts: Edit** 两项权限，作用范围只限本账号。
- 第一次手动运行 **Publish to Cloudflare** 时设 `create_project=true`。项目已经存在时会直接停止，不会覆盖。项目名默认是 `orbit-us`，可以用仓库变量 `CLOUDFLARE_PROJECT` 修改。
- 仓库变量 `CLOUDFLARE_ENABLED=true` 打开自动同步。
- 调度 Worker 要求账号有 workers.dev 子域名（打开一次 Workers & Pages 页面就会自动创建）。

---

## 5. 模型、回测与实盘跟踪

### 模型

评分代码从原 Hermes 美股模型中独立出来，用固定的合成行情验证过数值一致（`tests/fixtures/us_model_parity.json`）。数据来源和复权口径都和原来的 OpenD 版本不同，所以数值可能与原快照不一样。

### 回测（`scripts/backtest.py`，Actions 里手动运行 **Backtest**）

- 每周最后一个交易日，只用当时能拿到的数据重新计算评分，第二天收盘调仓，按单边换手 5bp 计成本。
- 对比的策略包括：当前评分前 N 名、只选「动量成立」、波动调整排名、组内排名、SPY 跌破 200 日均线时持有 BIL、EMA5/EMA20 过滤、每月调仓配合 6–12 个月动量，基准是 SPY 和全池等权。报告附带 Newey-West t 统计量。
- **2012–2026 年的结论**：所有变体都没有显著跑赢一直持有 SPY；评分对未来收益的预测力（IC）也都没有达到统计显著，最强的 12-1 动量 t = 1.56。波动调整排名的回撤最小。看板适合用来观察市场轮动，不适合当作自动交易信号。
- 注意：回测用的是今天的 ETF 名单，存在后视偏差。

### 实盘跟踪（`scripts/live_report.py`，每月 2 日自动运行）

读取 `data` 分支里每天真实发布过的快照：取当天评分前 10 名，用之后第 5、20 个交易日快照里记录的收盘价计算收益，和 SPY、全池等权对比，并计算 IC。不重新抓数据、也不重新打分，衡量的就是看板当时真正显示的内容。报告写在运行页 Summary，并保存为 `data` 分支的 `reports/live.md`。5 日周期大约要攒 2 个月数据，20 日周期大约要 9 个月，之前报告只会提示「数据还不够」。

---

## 6. 开发与测试

### 目录结构

| 路径 | 内容 |
|---|---|
| `dist/` | 网页（HTML/JS/CSS）、`_headers` 安全响应头，以及仓库里提交的一份旧快照（浏览器测试用作旧格式样本） |
| `scripts/` | 刷新、校验、恢复、回测、报告等脚本 |
| `tests/` | 单元测试；`tests/e2e/` 是浏览器冒烟测试 |
| `worker/` | 准点调度 Worker（Cloudflare） |
| `.github/workflows/` | 所有工作流（见第 3 节） |

### 本地运行

```bash
pip install -r requirements.txt
```

```bash
python -m unittest discover -s tests -v
```

```bash
python scripts/refresh_snapshot.py && python scripts/validate_snapshot.py
```

```bash
python -m http.server 8767 --bind 127.0.0.1 --directory dist
```

工作流使用 Python 3.12。

### 浏览器冒烟测试

```bash
python tests/e2e/build_site.py /tmp/e2e
```

然后在 `/tmp/e2e/current` 和 `/tmp/e2e/legacy` 各起一个静态服务器，运行 `node tests/e2e/smoke.cjs <current地址> <legacy地址>`（需要 Playwright）。测试覆盖桌面中/英/日三种语言、iPhone 尺寸、详情与走势图、自选、分享链接、键盘操作、手机列切换和个股页，任何控制台错误（包括 CSP 违规）都会让测试失败。

### 安全

`dist/_headers`（Cloudflare）和 `index.html` 里的 meta 标签设置了 CSP：只允许加载本站的脚本和数据，禁止被嵌入框架。本仓库不包含任何密钥、OpenD 连接配置、持仓或账户信息。

---

## 7. 故障排查

| 现象 | 原因与处理 |
|---|---|
| 页面数据停在某天 | 先看 [Actions](https://github.com/kazenari99/us-etf-dashboard/actions) 最近一次「Publish US ETF dashboard」。如果是黄色警告「ETF refresh deferred」，说明 Yahoo 还没出数据，下一次定时任务会补上 |
| 运行失败，日志写着「Incomplete universe」 | 某只 ETF 在 Yahoo 的数据有问题，报错里会写明是哪只。连续几天都失败的话，考虑把它从 `UNIVERSE` 里换掉 |
| `data-stale` issue 里只有强势股列表落后 | 第三方源站停止更新了，本站无法修复；源站恢复后 issue 会自动关闭 |
| Cloudflare 有更新，GitHub Pages 没有（或反过来） | 手动运行 **Publish to Cloudflare**，或重新运行那次发布 |
| 准点调度没触发 | 看有没有 `token-expiry` issue，以及 Cloudflare Workers & Pages 里 `us-etf-scheduler` 的日志。GitHub 自己的后备定时任务仍会运行，最多只是晚一些 |
| PR 合并按钮是灰的 | `check` 或 `browser` 检查没通过，看 PR 里的 CI 日志 |
