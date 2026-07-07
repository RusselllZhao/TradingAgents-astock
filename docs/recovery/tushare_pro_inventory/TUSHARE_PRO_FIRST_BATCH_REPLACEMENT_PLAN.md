# Tushare Pro 第一批替换与技术防护方案

阶段：3C-1  
范围：方案设计，不实现代码，不调用 Tushare token，不运行多 Agent。

## 已确认业务口径

- `get_profit_forecast` 保持“机构盈利预测 / 卖方预测 / 一致预期”语义。补到 8000 积分后，`report_rc` 可作为第一批主替换源。
- `forecast` / `express` / `fina_indicator` 不替代 `get_profit_forecast`，第二批再作为公司正式业绩预告、业绩快报、历史财务指标补充。
- 财务三表第一批只取合并报表；`quarterly` 返回累计报告期数据；as-of 使用 `ann_date`，`end_date` 只作为报告期。
- `get_fundamentals` 第一批只恢复核心基础信息和日频估值指标，使用 `daily_basic + stock_basic`，不追求实时估值。
- `get_fund_flow` 第一批接受日频稳定资金流，`moneyflow` 主源，`moneyflow_dc` 备用。
- `moneyflow_hsgt` 只映射 `get_northbound_flow` 或市场资金主题；`moneyflow_mkt_dc` 不进入 `get_fund_flow`。

## 总体设计边界

- 不把 token 写入源码、文档或 git。未来实现只从 `TUSHARE_TOKEN` 环境变量或 gitignored 本地配置读取。
- 第一批输出仍保持现有上层可消费的 Markdown/CSV 文本形式，增加清晰的 `source=Tushare`、`api=...`、`as_of`、`status`、`empty_reason` 信息。
- 失败不抛长异常给 Agent，不返回 HTML 原文、不返回异常栈、不返回超长错误文本。
- 所有 Tushare 请求统一走未来的轻量 client/helper，负责 token、频控、缓存、短错误包装。
- 不修改 prompt、Quality Gate、Bull/Bear 辩论逻辑、Agent 层、多 Agent 流程。

## 逐函数方案矩阵

| 原函数名 | 当前技术问题 | 原函数业务语义 | 第一批处理类型 | 主接口 | 备用接口 | 明确不使用 |
|---|---|---|---|---|---|---|
| `a_stock.get_profit_forecast` | 同花顺 HTML/反爬页被作为超长错误文本返回 | 机构盈利预测 / 卖方预测 / EPS 一致预期 | Tushare 替换 + 技术防护 | `report_rc` | 同花顺原源仅可作为受保护 fallback | `forecast`、`express`、`fina_indicator` |
| `a_stock.get_balance_sheet` | 正常股票返回 `No balance sheet data found` | 资产负债表 | Tushare 替换 | `balancesheet` | 无，原新浪仅作回退观察 | 其他财务或公告接口 |
| `a_stock.get_cashflow` | 正常股票返回 `No cash flow data found` | 现金流量表 | Tushare 替换 | `cashflow` | 无，原新浪仅作回退观察 | 其他财务或公告接口 |
| `a_stock.get_income_statement` | 正常股票返回 `No income statement data found` | 利润表 | Tushare 替换 | `income` | 无，原新浪仅作回退观察 | 其他财务或公告接口 |
| `a_stock.get_fundamentals` | 正常股票只剩股本，多个子源失败静默 | 公司核心基本面：基础信息 + 估值/市值/交易日指标 | 字段级组合 | `daily_basic + stock_basic` | 无第一批备用；可保留现有源作降级补位 | `stock_company`、`fina_indicator`、`dividend`、`adj_factor` |
| `a_stock.get_fund_flow` | 东财 push2 代理错误以普通字符串返回 | 个股资金流，非北向、非大盘 | Tushare 替换 + 技术防护 | `moneyflow` | `moneyflow_dc` | `moneyflow_hsgt`、`moneyflow_mkt_dc`、`moneyflow_ths` |

## 1. `a_stock.get_profit_forecast`

### 当前技术问题

- 当前同花顺 `worth.html` 解析路径在正常股票上可能拿到 HTML/反爬页。
- `pandas.read_html` 失败或解析异常会把大段 HTML 作为异常文本进入普通返回。
- 失败文本过长，可能被上层 Agent 当作正常事实材料。

### 业务语义

保持“机构盈利预测 / 卖方预测 / 一致预期”。输出必须明确为 sell-side forecast aggregation，不得写成公司公告或正式业绩预告。

### Tushare 权限口径

- `report_rc` 文档原文：2000 积分可以试用，每天 10 次请求；正式权限需 8000 积分，每天可请求 100000 次，10000 积分以上无总量限制。
- 本方案按用户确认的 8000 积分目标设计；在 8000 积分未补齐前，不建议进入正式主流程。

### 输入参数映射

- `ticker` -> 转换为 Tushare `ts_code`，例如 `600519` -> `600519.SH`，`300750` -> `300750.SZ`。
- `curr_date` -> `end_date`，表示研报日期 as-of 截止；不得读取 `report_date > curr_date` 的预测。
- 可选窗口：默认 `start_date = curr_date - 365 days`，避免历史过旧预测污染一致预期。
- 预测年度：从 `quarter` / 预测报告期中提取年度，优先输出未来 1-3 个年度或最近可用预测期。

### 输出字段映射

- `report_date` -> 研报日期 / source report date。
- `quarter` -> forecast year / forecast period。
- `org_name` + `author_name` -> source institution / analyst。
- `eps` -> EPS 预测样本；聚合为 mean / median / min / max。
- `np` -> 净利润预测样本，如字段可用；聚合为 mean / median / min / max。
- `op_rt` -> 收入预测样本，如字段可用；聚合为 mean / median / min / max。
- `rating`、`max_price`、`min_price` -> 第二批可考虑，不进入第一批核心输出。
- 输出必须包含 `source_count`、`source_org_count`、`report_date_range`、`source=Tushare`、`api=report_rc`。

### 聚合规则

1. 按 `ts_code` 过滤。
2. 按 `report_date <= curr_date` 过滤。
3. 默认保留最近 365 天研报，若无数据可扩大到 730 天但必须标注 `stale_forecast_window`。
4. 按预测年度 / `quarter` 分组。
5. 对每个预测期统计 `eps` 的 count、mean、median、min、max；`np`、`op_rt` 有值时同样统计。
6. 同一家机构同一预测期多条记录时，第一批建议保留最近 `report_date` 一条，避免单机构重复加权。
7. 少于 3 家机构时输出 `low_coverage=true`，不得给强结论。

### 报告期与 as-of 口径

- `report_date` 是 as-of 判断字段。
- `quarter` / 预测期是 forecast period。
- 不使用公司公告 `forecast` 的 `ann_date` 替代卖方研报日期。

### 频率控制建议

- 8000 积分正式权限下仍应限速：默认每分钟不超过 200 次，单函数批量调用更低。
- 首次方案实现只允许单股票调用，不设计批量全市场抓取。
- 对 `report_rc` 加本地缓存，避免重复按同一 `ticker + curr_date` 拉取。

### 本地缓存建议

- 缓存键：`report_rc/{ts_code}/{start_date}_{end_date}.json`。
- TTL：交易日内 24 小时；历史窗口可长期缓存，手动清理。
- 缓存内容不包含 token。

### 失败返回规范

- 无数据：`no_coverage`，包含 `source=Tushare`、`api=report_rc`、`ts_code`、`as_of`、`reason=no_sell_side_forecast`。
- 权限不足：`technical_error`，`reason=tushare_permission_denied`，提示需要 8000 正式权限。
- 网络/解析错误：短 `technical_error`，不得包含异常栈。
- 同花顺 fallback 若保留，必须拦截 `<html`、`<!doctype`、`验证码`、`安全验证`、`403/404`、文本长度超阈值，返回短错误。

### 上层输出兼容

- 保持 Markdown 文本头部：`# Consensus EPS Forecast for {code}`。
- 明确 `# Source: Tushare report_rc sell-side forecast aggregation`。
- 保留类似 FY 年度行：`FY2026: EPS mean=..., median=..., range=..., institutions=...`。
- 不输出公司业绩预告摘要，不输出“正式公告”字样。

### 未来代码阶段可能新增或修改

- 可能修改：`tradingagents/dataflows/a_stock.py`。
- 可能新增：`tradingagents/dataflows/tushare_client.py` 或同等轻量 helper。
- 可能新增：Tushare 缓存目录 README / schema，但不提交真实缓存。

### 明确禁止修改

- 不修改 `tradingagents/dataflows/interface.py`。
- 不修改 prompt、Quality Gate、Bull/Bear 辩论逻辑、Agent 层。
- 不接入 `forecast` / `express` / `fina_indicator` 作为本函数直接替代。

### Smoke Test 验收样例

- `get_profit_forecast("600519", "2026-07-07")`：不得返回 HTML；成功时返回 sell-side aggregation 或短 `no_coverage`。
- `get_profit_forecast("300750", "2026-07-07")`：输出必须含 `api=report_rc`、`source_count`、预测期。
- 模拟权限不足 / token 缺失：返回短 `technical_error`，不得泄露 token。

### 回退方案

- 若 `report_rc` 权限未就绪，第一批只做技术防护：同花顺 fallback 加 HTML/长文本拦截，返回 `technical_error` 或 `no_coverage`。
- 不使用 `forecast` / `express` 冒充一致预期。

### 第二批扩展

- 增加 `forecast` 作为公司业绩预告。
- 增加 `express` 作为公司业绩快报。
- 增加 `fina_indicator` 作为历史实际指标对照。
- 研究 `research_report` 原文权限与研报摘要，但不进入第一批。

## 2. 财务三表

### 共同口径

- `get_balance_sheet` -> `balancesheet`。
- `get_cashflow` -> `cashflow`。
- `get_income_statement` -> `income`。
- 第一批只取合并报表；`quarterly` 返回累计报告期数据，不做单季转换。
- as-of 使用 `ann_date`，不得读取 `ann_date > curr_date` 的报表。
- `end_date` 只表示报告期。

### 输入参数映射

- `ticker` -> `ts_code`。
- `freq=annual` -> `period` 月份为 `1231`。
- `freq=quarterly` -> 允许 `0331/0630/0930/1231`，返回累计报告期。
- `curr_date` -> `end_date` 参数不能直接代替报告期；用于 `ann_date <= curr_date` 过滤。实现上可请求单票历史后本地过滤，或用 `end_date=curr_date` 作为公告截止需谨慎，最终以 `ann_date` 过滤为准。
- `report_type` -> 第一批只保留合并报表对应类型。Tushare 文档需在实现阶段核对 report_type 代码，未确认前不得硬编码猜测；若无法可靠识别，输出保留 `report_type` 并标注 `report_type_filter_unverified`。
- `comp_type` -> 保留原值输出，不用作第一批行业排除；金融行业字段差异不伪造。

### 输出字段映射

- 公共字段必须输出：`ts_code`、`ann_date`、`f_ann_date`、`end_date`、`report_type`、`comp_type`、`end_type`、`source`、`api`。
- 保持 CSV 主体，便于上层 Agent 延续现有消费方式。
- 表头增加 Markdown 元信息：
  - `# Data source: Tushare`
  - `# API: balancesheet/cashflow/income`
  - `# as_of_field: ann_date`
  - `# period_field: end_date`
  - `# statement_scope: consolidated_only`
  - `# quarterly_policy: cumulative_period`

### 频率控制建议

- 单股票三表按需调用，避免一次性全市场。
- 每分钟默认不超过 100 次；若三表连续调用同一股票，串行执行并复用缓存。
- `*_vip` 接口不是第一批必需；普通接口单票历史足够第一批函数语义。

### 本地缓存建议

- `balancesheet/{ts_code}/{ann_date}_{end_date}.json`
- `cashflow/{ts_code}/{ann_date}_{end_date}.json`
- `income/{ts_code}/{ann_date}_{end_date}.json`
- TTL：财报公告历史数据可长期缓存；最近一个报告期建议每日刷新一次，直到下个报告期稳定。

### 失败返回规范

- 无数据：短 `no_data`，包含 `api`、`ts_code`、`freq`、`as_of`、`reason=no_statement_before_as_of`。
- 权限/频率/网络：短 `technical_error`，不含异常栈。
- 不返回 “No balance sheet data found” 这类无 source/status 的裸文本。

### 上层输出兼容

- 继续返回 Markdown header + CSV。
- 字段可能从中文新浪字段变为 Tushare 英文字段，必须在 header 中标明字段来源和 API。
- 若上层依赖文本而非字段名，CSV 格式保持即可；若后续发现字段名依赖，第二阶段再做字段别名。

### Smoke Test 验收样例

- `get_balance_sheet("600519", "quarterly", "2026-07-07")`
- `get_cashflow("600519", "quarterly", "2026-07-07")`
- `get_income_statement("600519", "quarterly", "2026-07-07")`
- 验收：返回非空 CSV 或短 `no_data/technical_error`；不得读取 `ann_date > 2026-07-07` 的报表；输出包含 source/api/ann_date/end_date/report_type/comp_type。

### 回退方案

- 若 Tushare token 未配置或权限不足，返回短 `technical_error`。
- 可保留新浪旧源作为人工回退观察，但第一批主方案不依赖它；旧源异常也必须短错误化。

### 第二批扩展

- 单季转换。
- 更精细的 `report_type` 口径映射。
- 金融行业专用字段展示。
- `*_vip` 全市场接口，用于批量研究而非当前单股票函数。

## 3. `a_stock.get_fundamentals`

### 当前技术问题

- 正常股票只返回 Float Shares/Total Shares。
- 腾讯、东财、同花顺子源失败被静默吞掉。
- 输出缺少状态，Agent 难以识别 partial data。

### 业务语义

第一批只恢复核心基础信息和最近交易日日频估值指标。

### 主接口组合

- `stock_basic`：股票名称、行业、上市日期、市场类型。
- `daily_basic`：最近交易日收盘价、PE、PB、PS、总市值、流通市值、换手率、量比、总股本、流通股本。

### 明确不使用

- `stock_company`：公司画像第二批再补。
- `fina_indicator`：历史财务指标第二批再补。
- `dividend`：分红事件第二批再补。
- `adj_factor`：复权行情支持数据，不是 fundamentals 替换。

### 输入参数映射

- `ticker` -> `ts_code`。
- `curr_date` -> 最近交易日查找上限；第一批可先尝试 `daily_basic(ts_code, trade_date=curr_date)`，为空时向前查找最近 N 个交易日，建议 N=10。
- `stock_basic` 使用 `ts_code` 或一次性全市场缓存后本地过滤。

### 输出字段

第一批字段范围限定为：

- 股票代码：`ts_code` / `symbol`
- 股票名称：`name`
- 行业：`industry`
- 上市日期：`list_date`
- 市场类型：`market`
- 交易日期：`trade_date`
- 收盘价：`close`
- PE：优先 `pe_ttm`，同时可输出 `pe`
- PB：`pb`
- PS：优先 `ps_ttm`，同时可输出 `ps`
- 总市值：`total_mv`
- 流通市值：`circ_mv`
- 换手率：`turnover_rate`，可附 `turnover_rate_f`
- 量比：`volume_ratio`
- 总股本：`total_share`
- 流通股本：`float_share`

### 报告期与 as-of 口径

- 使用交易日口径，不是财报报告期。
- `trade_date <= curr_date`，取最近可得交易日。
- 输出必须标明 `valuation_date` 或 `trade_date`，避免被理解为实时。

### 频率控制建议

- `stock_basic` 长缓存，避免重复拉取。
- `daily_basic` 单票按日缓存；不要每次全市场请求。
- 每分钟默认不超过 100 次，优先命中缓存。

### 失败返回规范

- `daily_basic` 空：短 `no_data`，说明 `reason=no_daily_basic_before_as_of`。
- `stock_basic` 空：仍可输出 daily_basic 部分，但标注 `partial_data`。
- 两者均失败：短 `technical_error` 或 `no_data`，不得返回代理栈或 HTML。

### 上层输出兼容

- 保持 `# Company Fundamentals for {code} (A-stock)` header。
- 输出 key-value 文本，字段名可沿用现有英文标签：
  - `Name`
  - `Industry`
  - `Market`
  - `List Date`
  - `Close`
  - `PE (TTM)`
  - `PE`
  - `PB`
  - `PS (TTM)`
  - `Market Cap (10K CNY)`
  - `Float Market Cap (10K CNY)`
  - `Turnover Rate`
  - `Volume Ratio`
  - `Total Shares (10K)`
  - `Float Shares (10K)`
- Header 标明 `realtime=false`。

### Smoke Test 验收样例

- `get_fundamentals("600519", "2026-07-07")`
- `get_fundamentals("300750", "2026-07-07")`
- 验收：至少返回名称、行业或市场、最近交易日、PE/PB/市值之一；若部分缺失必须标注 `partial_data`。

### 回退方案

- Tushare 不可用时可保留旧腾讯/东财/mootdx 源作为降级，但每个子源失败必须被记录，不允许静默只剩股本。
- 如所有源失败，返回短 `technical_error`。

### 第二批扩展

- `stock_company` 公司画像。
- `fina_indicator` 历史财务指标。
- `dividend` 分红。
- 行业/概念分类增强。
- 更完整的字段别名和单位治理。

## 4. `a_stock.get_fund_flow`

### 当前技术问题

- 东财 push2 请求失败时返回代理错误普通字符串。
- 当前输出含弱信号，但没有结构化 source/status，容易被 Agent 过度解读。

### 业务语义

第一批只做个股日频资金流，不保留实时分钟资金流。输出必须说明“个股资金流”，不是北向资金，不是大盘资金。

### 主备接口

- 主源：`moneyflow`
- 备用：`moneyflow_dc`

### 明确不使用

- `moneyflow_hsgt`：沪深港通/北向南向资金，市场级，不替代个股资金流。
- `moneyflow_mkt_dc`：大盘资金流，且正式权限需 6000 积分；不进入第一批。
- `moneyflow_ths`：同花顺个股资金流，需 6000 积分；第二批再评估。

### 输入参数映射

- `ticker` -> `ts_code`。
- `curr_date` -> `trade_date <= curr_date` 的最近交易日。
- `include_history=True` -> 默认获取最近 20 个可用交易日，可用 `start_date/end_date` 实现。
- `include_history=False` -> 只返回最近一个交易日。

### 输出字段映射

`moneyflow` 主源：

- `trade_date` -> 日期。
- `buy_sm_amount` / `sell_sm_amount` -> 小单买入/卖出金额。
- `buy_md_amount` / `sell_md_amount` -> 中单买入/卖出金额。
- `buy_lg_amount` / `sell_lg_amount` -> 大单买入/卖出金额。
- `buy_elg_amount` / `sell_elg_amount` -> 超大单买入/卖出金额。
- `net_mf_amount` -> 净流入额。
- 可计算：小/中/大/超大单净额 = 买入金额 - 卖出金额。

`moneyflow_dc` 备用：

- `net_amount` -> 主力净流入额。
- `buy_elg_amount`、`buy_lg_amount`、`buy_md_amount`、`buy_sm_amount` -> 各层级净流入额。
- 缺少买入/卖出拆分时，输出字段必须标注 `net_only=true`。

### 报告期与 as-of 口径

- 使用交易日口径。
- `trade_date <= curr_date`。
- 不读取未来交易日。

### 频率控制建议

- `moneyflow` 单次最大 6000 行，按股票 + 日期窗口请求。
- 默认每分钟不超过 100 次，失败后指数退避。
- 备用 `moneyflow_dc` 只在主源无数据或技术错误时调用。

### 缓存建议

- 缓存键：`moneyflow/{ts_code}/{trade_date}.json` 或 `moneyflow/{ts_code}/{start_date}_{end_date}.json`。
- TTL：历史交易日长期缓存；当前交易日盘后前可短 TTL，例如 1 小时；盘后稳定后按日缓存。

### 失败返回规范

- 主源空且备用空：`no_data`，标明 `source=Tushare`、`api=moneyflow/moneyflow_dc`、`ts_code`、`as_of`。
- 主源错误备用成功：输出 `partial_data`，标明 fallback。
- 网络/权限错误：短 `technical_error`。
- 不输出代理异常栈。

### 上层输出兼容

- 保持 `# Fund Flow for {code} (A-stock)` header。
- Header 增加 `# Source: Tushare moneyflow`、`# Frequency: daily`、`# Scope: individual_stock`。
- 不直接生成强 buy/sell 结论。
- 如保留 signal，只能写成 `Data summary: net_mf_amount positive/negative`，不得写 bullish/bearish 投资建议。

### Smoke Test 验收样例

- `get_fund_flow("300750", "2026-07-07", include_history=True)`
- `get_fund_flow("600519", "2026-07-07", include_history=False)`
- 验收：输出 trade_date、个股资金流字段、source/api/scope；失败短文本；不包含北向/大盘字段。

### 回退方案

- 主源 `moneyflow` 无数据或技术错误 -> `moneyflow_dc`。
- Tushare 不可用 -> 返回短 `technical_error`，不回退到原东财 push2 长异常。

### 第二批扩展

- `moneyflow_ths` 在 6000 积分后评估。
- 北向资金单独映射 `moneyflow_hsgt` 到 `get_northbound_flow`。
- 弱化或结构化所有资金流 signal。

## 未来代码阶段文件影响清单

### 可能新增

- `tradingagents/dataflows/tushare_client.py`：Tushare token、请求、频控、短错误包装。
- `tradingagents/dataflows/tushare_cache.py` 或内聚到 client：本地缓存读写。
- `.env.example` 或本地配置 example：只写变量名，不含真实 token。
- 缓存目录 README / schema：不提交真实缓存。

### 可能修改

- `tradingagents/dataflows/a_stock.py`：仅六个函数及必要 helper。
- `.gitignore`：忽略本地 token 配置与缓存目录。

### 禁止修改

- `tradingagents/dataflows/interface.py`
- prompt
- Quality Gate
- Bull/Bear 辩论逻辑
- Agent 层、多 Agent 流程
- 与本轮六个函数无关的数据源逻辑

