# SECOND_BATCH_BUSINESS_RISK_BACKLOG

基线：`recovery/data-source-only` @ `b81197653b367f84242e6fe0bca3fb6bac4619b5`

本文件记录第二批业务口径优化 backlog。这里的问题不建议进入第一批代码整改，尤其不建议现在修改 prompt、Quality Gate 或 Agent 辩论逻辑。

## 第二批 backlog

| 优先级 | 函数/主题 | 风险 | 分类 | 建议动作 | 暂缓原因 | 后续验收方式 |
|---:|---|---|---|---|---|---|
| B1 | `a_stock.get_news` | 媒体新闻可能被当作公司一手事实；999999 可返回泛新闻 | D业务解释风险 / B契约观察 | 后续业务评估 | 技术上正常股票可返回新闻；一手事实边界属于业务口径 | 增加 source_type、is_official、scope 或新闻可信等级后再验收 |
| B1 | `a_stock.get_global_news` | 宏观/市场新闻可能被个股化解释 | D业务解释风险 | 后续业务评估 | 当前技术可用；是否用于个股判断不是第一批技术问题 | 返回显式 `scope=market`；下游能区分市场级信息 |
| B1 | `a_stock.get_northbound_flow` | 北向资金是市场级数据，却含 Signal/流入流出判断词 | D业务解释风险 | 后续业务评估 | 不属于接口失败；是否保留 signal 需业务确认 | 标注 `scope=market` 和 `conclusion_level=weak/derived` |
| B1 | `a_stock.get_hot_stocks` | 同花顺人工题材标签可能被当作确定涨停因果 | D业务解释风险 | 后续业务评估 | 技术上能返回；可靠性是业务解释问题 | 标注 `source_type=editorial`，题材标签作为弱证据 |
| B1 | `a_stock.get_industry_comparison` | 函数名暗示个股行业对比，但实际返回全行业排名 | D业务解释风险 | 后续业务评估 | 技术上能返回；是否补目标行业定位需业务确认 | 标注 `scope=market/sector_rank`，或后续补目标行业识别 |
| B2 | `a_stock.get_insider_transactions` | F10 股东研究被命名为 insider transactions，可能套用美股口径 | D业务解释风险 | 后续业务评估 | 返回本身可用；命名/口径需要业务确认 | 标注 `equivalent_only=true`，避免“内部人交易”强解释 |
| B2 | `a_stock.get_concept_blocks` | 百度概念标签和 ratio 口径不清 | D业务解释风险 / B契约观察 | 后续业务评估 | 技术上能返回；标签可信等级需确认 | 标注单位、更新时间、source_type 和概念可信等级 |
| B2 | `a_stock.get_profit_forecast` | 一致预期可能被作为强估值证据 | D业务解释风险 | 后续业务评估 | 第一批只修 HTML/解析错误；一致预期强弱属于第二批 | 标注 analyst_count、coverage_level、derived_metrics |
| B2 | `a_stock.get_fund_flow` | 东财资金流黑盒算法和主力/散户解释强度 | D业务解释风险 | 后续业务评估 | 第一批只处理请求失败/错误文本；资金流解释口径暂缓 | 标注 vendor_method=black_box，信号作为弱证据 |
| B3 | `route_to_vendor` | vendor fallback/status 不可见，错误文本可被视为成功 | B技术契约问题 | 包装规范 | 可作为后续统一 wrapper，不进入第一批大重构 | 路由返回包含 vendor/status/error/fallback_chain |
| B3 | 业务空结果 | 无龙虎榜、无未来解禁、无非交易日指标值 | C正常业务空结果 | 仅标记 | 当前不是接口失败 | 增加 `empty_reason=no_event/non_trading_day` |

## 暂缓原因

- 这些问题多数不是“接口坏了”，而是数据解释边界不清。
- 若现在修改 prompt 或辩论逻辑，容易扩大范围并掩盖底层技术错误。
- 第二批更适合在第一批技术错误稳定后，统一设计 metadata/schema。

## 明确不建议现在做

- 不建议现在修改 analysts/researchers/trader/risk/manager prompt。
- 不建议现在修改 Quality Gate。
- 不建议现在修改 Bull/Bear 辩论逻辑。
- 不建议现在替换数据源。
- 不建议现在接入 Tushare 或其他新源。

## 后续建议顺序

1. 先完成第一批 A 类技术错误拦截。
2. 再设计轻量 metadata：`status`、`source`、`as_of`、`unit`、`scope`、`fallback`、`empty_reason`、`confidence`。
3. 最后再决定是否需要 prompt 或 Agent 消费侧调整。
