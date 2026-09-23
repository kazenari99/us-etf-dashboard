# 美股 ETF 动量雷达

现有 Hermes 美股 ETF Momentum Radar 的独立 GitHub Pages 发布仓库。保留原20/60/120日评分、动量地图、机会卡片、搜索筛选及详情。A股配套：[JADE PULSE · A股ETF](https://kazenari99.github.io/a-etf-dashboard/reports/etf_dashboard.html)。

## 数据更新

数据来自本地已生成的OpenD快照；本仓库只发布静态结果，不在云端请求OpenD，也不新增额度消耗。原私有Site保留。网页始终显示真实行情日；部署时间不代表行情已刷新。

最新本地快照生成后，在本仓库执行：

```sh
python scripts/sync_snapshot.py ../etf-dashboard/dist
# 检查数据日期后提交并推送

git add dist
git commit -m 'Update US ETF snapshot'
git push
```

推送main后自动发布；也可手动运行 `Publish US ETF dashboard`。没有设置只会重复发布旧数据的每日定时任务。此仓库不包含密钥、OpenD连接配置、持仓或账户信息。

## 本地查看

```sh
python -m http.server 8767 --bind 127.0.0.1 --directory dist
```

运行 `python scripts/validate_snapshot.py` 检查日期、标的与关键数值完整性。
