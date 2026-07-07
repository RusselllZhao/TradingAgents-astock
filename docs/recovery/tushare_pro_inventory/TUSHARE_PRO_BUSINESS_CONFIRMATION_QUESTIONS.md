# Tushare Pro 第一批业务复核人工确认问题

本文件只列需要你定业务口径的问题，不包含替换实现方案。

| 编号 | 主题 | 需要确认的问题 |
|---|---|---|
| Q1 | a_stock.get_profit_forecast | 当前函数代码明确是“同花顺 analyst consensus / Consensus EPS Forecast”。是否确认这个函数必须保持“机构盈利预测/一致预期”语义，而不是改成“公司业绩预告”？ |
| Q2 | report_rc 权限 | `report_rc` 页面写“2000积分可以试用，每天10次请求，正式权限需8000积分”。5000积分下是否允许作为临时人工验证/备用源，还是必须排除第一批主流程？ |
| Q3 | forecast/express | 是否希望第二批新增“公司正式业绩预告/业绩快报”主题？如果是，它们应作为补充事实源，不应替代 profit_forecast。 |
| Q4 | 财务三表报告口径 | 三表替换时是否只取合并报表？是否排除母公司报表、调整表、金融行业特殊 comp_type？ |
| Q5 | 财务三表时间口径 | 当前函数参数有 annual/quarterly。你希望 quarterly 返回累计报告期数据，还是要转换成单季数据？ |
| Q6 | 财务三表 as-of | 按 `ann_date`、`f_ann_date` 还是 `end_date` 做 curr_date 截止？推荐人工确定，避免未来函数看见未公告财报。 |
| Q7 | fundamentals 实时性 | 是否接受 `daily_basic` 的最近交易日日频指标替代当前腾讯实时估值字段？如果必须实时，Tushare 5000积分常规日频接口不能完全替代。 |
| Q8 | fundamentals 输出范围 | 第一批 fundamentals 是只修复 Price/PE/PB/Market Cap/Industry 等核心字段，还是要同步加入公司资料、财务指标、分红？ |
| Q9 | fund_flow 实时性 | 当前 `get_fund_flow` 包含实时分钟资金流。Tushare `moneyflow` 更偏历史日频/交易日资金流，是否接受第一批降级为日频稳定源？ |
| Q10 | 北向资金边界 | 确认 `moneyflow_hsgt` 只映射到 `get_northbound_flow` 或市场资金主题，不作为 `get_fund_flow` 个股资金流替代？ |
| Q11 | 大盘资金边界 | 确认 `moneyflow_mkt_dc` 因大盘语义且 6000积分正式权限，不进入第一批？ |

## 建议门槛

- 若 Q1/Q2 未确认，不建议进入 `a_stock.get_profit_forecast` 的 Tushare 替换方案设计。
- 若 Q4-Q6 未确认，财务三表可以做候选设计，但不能定最终字段/过滤规则。
- 若 Q7-Q9 未确认，`fundamentals` 和 `fund_flow` 只能做候选级方案，不能定主源语义。