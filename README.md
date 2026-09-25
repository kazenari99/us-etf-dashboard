# ORBIT PULSE

现有 Hermes 美股 ETF Momentum Radar 的独立 GitHub Pages 发布仓库。保留原20/60/120日评分、动量地图、机会卡片、搜索筛选及详情。A股配套：[JADE PULSE · A股ETF](https://kazenari99.github.io/a-etf-dashboard/)。

## 数据更新

云端使用Yahoo Finance复权日线，通过yfinance获取，无需API key、OpenD或付费行情额度。同花顺公开API目前不提供美股行情。原本地OpenD项目和私有Site保留独立运行。

GitHub Actions每周一至周五23:37 UTC自动运行，即北京时间次日07:37（周二至周六），冬夏令时均在美股收盘之后，调度可能延迟。推送main、手动运行也会刷新行情并发布。

本地刷新：

```sh
pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/refresh_snapshot.py
python scripts/validate_snapshot.py
```

通过NYSE日历处理休市、提前收盘和夏令时，收盘后留出一小时才使用当日日线。全量71只必须具有相同交易日和完整窗口（320自然日、至少121个交易日）。缺失、非数值、异常OHLC或日期不齐时重试，仍失败则停止部署，线上保留上一份完整快照。不会拼接OpenD与Yahoo行情或不同复权批次。免费数据源可能限流或不可用，不保证每日刷新成功。

网页显示真实行情日期、生成时间、来源和完整数量；超过4天未生成新快照会提示。CSV与元信息通过SHA-256核对。运行状态见[Actions](https://github.com/kazenari99/us-etf-dashboard/actions/workflows/pages.yml)。成功运行的复权日线、评分CSV及元信息以Actions artifact保留90天。

Yahoo `auto_adjust=True`按分红和拆股调整OHLC。评分代码从原Hermes美股模型中独立提取，通过固定合成行情验证数值一致。由于来源和复权口径变化，数值可能与原OpenD快照不同；历史归档保留各自来源，不能视为同一时点回测。

`scripts/sync_snapshot.py ../etf-dashboard/dist`可导入完整本地OpenD快照，不覆盖UI。提交CSV和元信息后，手动运行工作流并选中 `use_committed_snapshot` 可发布该快照；发布前核验最新完整交易日、71只标的和校验和。页面按元信息显示真实来源。定时及普通推送仍重新获取Yahoo Finance数据，不拼接两种来源。此仓库不包含密钥、OpenD连接配置、持仓或账户信息。

## 基金详情

详情框展示基金策略、管理机构、最多10项主要持仓及其占基金权重，另提供成交额与历史波动率。`scripts/refresh_funds.py` 单独更新公开资料：ARKK 优先使用 ARK 官方日持仓 CSV，其余使用 Yahoo 基金资料。来源未给出持仓日期时明确显示未知，不将获取时间当作披露日期。股票表缺失不代表零持仓，尤其是实物、期货及债券基金。失败时保留原资料及原获取日期并标记状态。持仓数据不参与动量评分，原始资料归档在 `archive/fund_profiles/`。

## 本地查看

```sh
python -m http.server 8767 --bind 127.0.0.1 --directory dist
```

运行 `python scripts/validate_snapshot.py` 检查日期、标的与关键数值完整性。
