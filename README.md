# ORBIT PULSE

## Cloudflare Pages 发布

已添加独立的 `.github/workflows/cloudflare.yml`，复用成功的 `pages.yml` 构建产物，不重复获取行情。初次配置需要账户范围内的 Cloudflare Pages Edit API Token，存入 Repository secret `CLOUDFLARE_API_TOKEN`。

手动运行 **Publish to Cloudflare**，首次设 `create_project=true`，默认项目名为 `orbit-us`（可通过 Repository variable `CLOUDFLARE_PROJECT` 设置）。项目已经存在时会停止，避免覆盖其他网站。确认项目归属后后续发布用 `create_project=false`。实际网址以 Cloudflare 返回的域名为准。

正式网址：[ORBIT PULSE](https://orbit-us.pages.dev)。首次发布与线上核验已完成，Repository variable `CLOUDFLARE_ENABLED=true`，每日快照构建成功后自动发布至 Cloudflare。GitHub Pages 保留为同步镜像。定时任务或上游数据失败时保留最后成功版本，以页面数据日期为准。


现有 Hermes 美股 ETF Momentum Radar 的独立发布仓库，由 GitHub Actions 生成快照并发布到 Cloudflare Pages。保留原20/60/120日评分、动量地图、机会卡片、搜索筛选及详情。A股配套：[JADE PULSE · A股ETF](https://jade-a.pages.dev/)。

## 数据更新

云端使用Yahoo Finance复权日线，通过yfinance获取，无需API key、OpenD或付费行情额度。同花顺公开API目前不提供美股行情。原本地OpenD项目和私有Site保留独立运行。

GitHub Actions计划每天22:00 UTC运行，即东京时间次日07:00；另在06:00 UTC（东京15:00）独立补抓ETF，给上游日线修正留出时间。先用NYSE交易日历检查东京日期的前一天是否为交易日；周末及美股休市日跳过数据构建和发布。冬夏令时均在美股收盘后至少一小时，GitHub调度及构建可能延迟，07:00为计划启动时间而非发布完成保证。推送main、手动运行仍可刷新行情并发布。网页时间统一显示Asia/Tokyo（UTC+9）。

## 强势股筛选

同一网址的 `/#stocks` 提供Minervini候选列表，与ETF页面共享ORBIT配色、字体和中英日语言切换。默认RS≥90、距52周高点≤25%、量比≥1.0，支持搜索、排序、浏览器本地自选和CSV导出。点击股票行、代码或右侧Chart链接，均在新标签页打开对应标的的TradingView日线图。

`scripts/refresh_stocks.py` 读取VCPScanner公开的 `https://anish1294.github.io/minervini-trend-template-screener/current.json`。它是作者按RS排序后的最多300只预筛选候选，不代表全市场；不调用作者数据库，不重算RS，不与ETF行情混合。保留来源归属及MIT许可。图表链接打开源站。

股票更新独立于早间ETF行情抓取：美东周一至周五21:17首次抓取、23:17补抓，分别比源站20:17、22:17计划更新晚1小时，按America/New_York自动处理夏令时。对应东京周二至周六夏令时10:17/12:17、冬令时11:17/13:17。GitHub实际调度可能延迟；这并非保证源站实际发布完毕后精确等待1小时。

股票任务从最近成功的Pages构建产物恢复已发布ETF快照及资料，只更新股票候选和分类，完全不请求ETF行情；ETF失败不会阻断股票定时任务。早间ETF任务保留最新股票快照，避免将数据回退到仓库旧版本。手动执行工作流时选择 `stocks_only=true` 可立即独立更新股票。两类任务顺序执行，避免相互取消。两类成功发布均自动同步Cloudflare和GitHub Pages。

页面单独显示选股交易日、抓取时间和未更新状态；源站滞后或抓取失败时保留真实日期。源站时间不受本站控制。

本地刷新：

```sh
pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/refresh_snapshot.py
python scripts/validate_snapshot.py
```

通过NYSE日历处理休市、提前收盘和夏令时，收盘后留出一小时才使用当日日线。全量ETF（数量以 `scripts/momentum.py` 的 `UNIVERSE` 为准，目前80只）必须具有相同交易日和完整窗口（400自然日、至少254个交易日，满足12个月动量）。缺失、非数值、异常OHLC或日期不齐时重试，非数值错误记录具体交易日和字段；仍失败则停止部署，线上保留上一份完整快照。不会拼接OpenD与Yahoo行情或不同复权批次。免费数据源可能限流或不可用，不保证每日刷新成功。

网页显示真实行情日期、生成时间、来源和完整数量；超过4天未生成新快照会提示。CSV与元信息通过SHA-256核对。运行状态见[Actions](https://github.com/kazenari99/us-etf-dashboard/actions/workflows/pages.yml)。成功运行的复权日线、评分CSV及元信息以Actions artifact保留90天。

Yahoo `auto_adjust=True`按分红和拆股调整OHLC。评分代码从原Hermes美股模型中独立提取，通过固定合成行情验证数值一致。由于来源和复权口径变化，数值可能与原OpenD快照不同；历史归档保留各自来源，不能视为同一时点回测。

`scripts/sync_snapshot.py ../etf-dashboard/dist`可导入完整本地OpenD快照，不覆盖UI。提交CSV和元信息后，手动运行工作流并选中 `use_committed_snapshot` 可发布该快照；发布前核验最新完整交易日、71只标的和校验和。页面按元信息显示真实来源。定时及普通推送仍重新获取Yahoo Finance数据，不拼接两种来源。此仓库不包含密钥、OpenD连接配置、持仓或账户信息。

## 基金详情

页面右上角支持 English / 中文 / 日本語，首次访问默认英语，语言偏好保存在本机浏览器。筛选、ETF展示名称、交易状态和详情提示同步翻译，搜索支持三种语言的展示名称。基金策略英文原文及发行机构、持仓公司的正式名称保留原文。翻译只更新显示文本，不修改行情、评分或CSV。

详情框展示基金策略、管理机构、最多10项主要持仓及其占基金权重，另提供成交额与历史波动率。`scripts/refresh_funds.py` 单独更新公开资料：ARKK 优先使用 ARK 官方日持仓 CSV，其余使用 Yahoo 基金资料。来源未给出持仓日期时明确显示未知，不将获取时间当作披露日期。股票表缺失不代表零持仓，尤其是实物、期货及债券基金。失败时保留原资料及原获取日期并标记状态。持仓数据不参与动量评分，原始资料归档在 `archive/fund_profiles/`。

## 本地查看

```sh
python -m http.server 8767 --bind 127.0.0.1 --directory dist
```

运行 `python scripts/validate_snapshot.py` 检查日期、标的与关键数值完整性。

股票 Sector 来自 Yahoo Finance 的公司资料，云端每30天刷新缓存，新标的首次出现时补充；抓取失败保留已有分类，未知显示“—”。分类不参与选股评分，CSV包含Sector。

## 历史快照与检查

- 每次 ETF 刷新成功发布后，`history` 任务把当日结果写入 `data` 分支：`etf/<交易日>.csv`、`etf/<交易日>.json`，以及按交易日排序的 `etf/index.csv`。同一交易日重跑会覆盖，不会重复。Actions 产物 90 天过期，`data` 分支长期保留，供回测和排名变化使用。
- `ci.yml` 在每个 PR 上运行单元测试、ruff（只查错误类规则，见 `ruff.toml`）、JS 语法检查、actionlint 和快照校验。

## 回测

在 Actions 里手动运行 **Backtest**（可选起始日期和持仓数量）。脚本 `scripts/backtest.py` 在每周最后一个交易日用当时可得的数据重算生产评分，次日收盘调仓，按 5bp 单边换手计成本，比较：当前评分前 N、仅「动量成立」、波动调整排名、组内排名、SPY 跌破 200 日均线时持有 BIL，以及 SPY 和全池等权基准。报告写在运行页 Summary，并作为产物保存 90 天。ETF 池是今天的名单，存在后视偏差。

## 参考列

ETF 明细表另有两列，仅供参考，不影响评分和状态：
- **12-1动量**：12个月前到1个月前的收益（跳过最近一个月）。回测中它是预测力最强的单一指标。
- **波动调整排名**：用「收益 ÷ 同期波动」代替原始收益算出的同口径评分的排名，1 为最好。回测中其前10名回撤明显更小。

## 数据过时提醒

`freshness.yml` 每天两次（UTC 04:23、12:41）读取两个线上站点的 `snapshot_meta.json`，按 NYSE 交易日计算落后多少个交易日。落后 2 个及以上（或站点无法访问）时开一个 `data-stale` issue，之后只更新正文不重复通知；数据恢复后自动关闭。建议在 GitHub 通知设置里关闭 Actions 失败邮件，改为关注这个 issue。

## 排名变化与评分走势

每次 ETF 刷新时，用同一批已校验的日线重算最近 20 个交易日每天的评分和排名，写入 `etf_history.json`（不依赖 `data` 分支，模型或 ETF 池变化后历史自动一致）。明细表的「5日排名变化」显示 5 个交易日前到今天的名次变化（↑ 上升、↓ 下降、= 不变）；详情框显示 20 日评分走势小图和 5 日前、20 日前的名次。文件缺失或日期不一致时页面照常显示，只是这两处为「—」。

## 市场状态与高度相关

`etf_history.json` 另含 `regime`（SPY 相对 200 日均线、站上 200/50 日均线的 ETF 数）和 `peers`（最近 120 个交易日日收益相关系数 ≥ 0.90 的 ETF，每只最多 3 个）。REGIME 标题和说明按这些数据生成，不再是固定文字。综合动量排名中，若某只 ETF 与排在它前面的另一只高度相关，名称旁显示「≈ 代码」，提示两者其实是同一类机会；详情框列出所有高度相关的 ETF。

## 备用数据源（默认关闭）

Yahoo 仍是唯一的默认数据源。`scripts/sources.py` 提供 Stooq 作为备用：只有当仓库变量 `FALLBACK_SOURCE=stooq` 且 Yahoo 抓取失败（不是「最新日线尚未发布」的推迟情况）时，才会整体改用 Stooq 抓取全部 ETF；同一份快照绝不混用两个数据源。页面会提示正在使用备用源。

启用前先在 Actions 里运行 **Source parity check**：它用生产校验逻辑分别从 Yahoo 和 Stooq 抓取全部 ETF，比较收盘价和 20/60/120 日收益差异，以及评分排名相关性和前 10 名重合度，给出「可以启用 / 不要启用」的结论。只有结论为可以启用时，才在 Settings → Secrets and variables → Actions → Variables 中添加 `FALLBACK_SOURCE=stooq`。
