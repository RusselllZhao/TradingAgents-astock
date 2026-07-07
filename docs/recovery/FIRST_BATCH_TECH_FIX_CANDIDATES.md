# FIRST_BATCH_TECH_FIX_CANDIDATES

基线：`recovery/data-source-only` @ `b81197653b367f84242e6fe0bca3fb6bac4619b5`

本文件只列第一批建议整改候选。筛选口径：A 股主线、正常股票、纯技术错误、可用最小代码改动验证；不包含 999999 完整治理、业务解释风险、prompt、Quality Gate、Agent 辩论逻辑。

## 第一批候选清单

| 优先级 | 函数 | 正常样本 | Smoke 表现 | 分类 | 推荐动作 | 最小改动范围 | 是否需要换源 | 验收方式 |
|---:|---|---|---|---|---|---|---|---|
| P0 | `a_stock.get_profit_forecast` | `600519` | 同花顺 HTML 被当作异常文本返回，长度约 281991 | A纯技术错误 | 立即修复 | `_ths_eps_forecast` / `get_profit_forecast` 增加 HTML/反爬页识别、解析失败短错误、低覆盖结构化说明 | 否，先不换源 | `get_profit_forecast("600519")` 不返回 HTML；成功返回预测表或短的 technical_error/no_coverage |
| P0 | `a_stock.get_balance_sheet` | `600519` | `No balance sheet data found` | A纯技术错误 | 立即修复 | `_get_financial_report_sina` 三表 helper 请求/解析/字段路径复核；无法取数时返回明确 technical_error | 待确认，优先不换源 | `get_balance_sheet("600519","quarterly","2026-07-07")` 返回非空 CSV 或明确接口失效 |
| P0 | `a_stock.get_cashflow` | `600519` | `No cash flow data found` | A纯技术错误 | 立即修复 | 同三表 helper | 待确认，优先不换源 | `get_cashflow("600519","quarterly","2026-07-07")` 返回非空 CSV 或明确接口失效 |
| P0 | `a_stock.get_income_statement` | `600519` | `No income statement data found` | A纯技术错误 | 立即修复 | 同三表 helper | 待确认，优先不换源 | `get_income_statement("600519","quarterly","2026-07-07")` 返回非空 CSV 或明确接口失效 |
| P1 | `a_stock.get_fundamentals` | `600519` | 只返回 Float Shares/Total Shares，其他子源疑似失败且静默 | A纯技术错误 | 包装规范 | 在 `get_fundamentals` 内最小记录子源状态；核心字段全缺时返回 partial_data/technical_error 标记 | 否 | 600519 至少返回价格/PE/PB/市值/行业之一，或清晰列出腾讯/东财/同花顺失败 |
| P1 | `a_stock.get_fund_flow` | `300750` | 东财 push2 ProxyError 普通字符串返回 | A纯技术错误 | 包装规范 | `get_fund_flow` 捕获请求错误时返回短 technical_error；避免代理栈文本进入 Agent | 待确认，优先不换源 | 代理/接口失败时返回短错误与 source/fallback/status；成功时返回原资金流文本 |

## 不纳入第一批的明确项

| 对象 | 原因 |
|---|---|
| 所有 `999999` 错误代码问题 | 本轮口径降级为输入校验问题；不作为第一批技术整改重点 |
| `get_news` 新闻一手事实问题 | D 类业务解释风险，进入第二批 |
| `get_global_news` 市场级新闻个股化 | D 类业务解释风险，进入第二批 |
| `get_northbound_flow` 北向资金信号词 | D 类业务解释风险，进入第二批 |
| `get_hot_stocks` 同花顺题材标签可靠性 | D 类业务解释风险，进入第二批 |
| `get_industry_comparison` 全行业榜个股化 | D 类业务解释风险，进入第二批 |
| `get_dragon_tiger_board` 近 30 日未上榜 | C 类正常业务空结果 |
| `get_lockup_expiry` 未来 90 天无解禁 | C 类正常业务空结果 |
| Yahoo / Alpha Vantage 兼容源 | 非 A 股主线，暂不扩大整改面 |

## 第一批边界

第一批整改只应包含最小 wrapper 或失败拦截：

- 可以增加短错误文本或结构化标记，但不做全局重构。
- 可以拦截 HTML/异常栈/代理错误，避免进入 Agent 文本。
- 可以复核现有 endpoint 参数和解析路径，但不替换新数据源。
- 不修改 analysts/researchers/trader/risk/manager。
- 不修改 prompt。
- 不修改 Quality Gate。
- 不修改 Agent 辩论逻辑。

## 建议验收

1. 只运行底层函数 smoke，不运行多 Agent。
2. 使用正常股票：`600519`、`300750`、必要时 `688981`。
3. 验收失败输出必须短、可识别、不可被误读为正常报告。
4. 不要求一次解决所有 B/C/D 问题。
