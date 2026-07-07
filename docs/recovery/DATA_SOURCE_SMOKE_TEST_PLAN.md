# DATA_SOURCE_SMOKE_TEST_PLAN

Generated: 2026-07-07 14:31:56

## Guardrails

- Direct dataflow/tool function calls only.
- No LLM calls.
- No Agent graph propagation.
- No prompt, debate, Quality Gate, endpoint, or business-code edits.
- `TRADINGAGENTS_CACHE_DIR` is redirected to a temporary directory and removed after the run.
- Alpha Vantage functions are not called without `ALPHA_VANTAGE_API_KEY`.

## Sample Universe

- `600519` / `600519.SH` 贵州茅台：主板白马。
- `300450` / `300450.SZ` 先导智能：创业板制造成长。
- `300750` / `300750.SZ` 宁德时代：创业板权重。
- `000001` / `000001.SZ` 平安银行：深市主板。
- `688981` / `688981.SH` 中芯国际：科创板。
- `999999`：错误代码失败场景。

## Planned Calls

| # | Function | Purpose | Inputs |
|---:|---|---|---|
| 1 | `a_stock.get_stock_data` | 主板白马 K 线 | `{"args": ["600519", "2026-06-01", "2026-07-07"], "kwargs": {}}` |
| 2 | `a_stock.get_stock_data` | 科创板 K 线 | `{"args": ["688981", "2026-06-01", "2026-07-07"], "kwargs": {}}` |
| 3 | `a_stock.get_stock_data` | 错误代码 K 线失败表现 | `{"args": ["999999", "2026-06-01", "2026-07-07"], "kwargs": {}}` |
| 4 | `a_stock.get_indicators` | 创业板权重技术指标 | `{"args": ["300750", "rsi", "2026-07-07", 10], "kwargs": {}}` |
| 5 | `a_stock.get_indicators` | 错误代码技术指标失败表现 | `{"args": ["999999", "rsi", "2026-07-07", 10], "kwargs": {}}` |
| 6 | `a_stock.get_fundamentals` | 主板白马基本面 | `{"args": ["600519", "2026-07-07"], "kwargs": {}}` |
| 7 | `a_stock.get_fundamentals` | 错误代码基本面失败表现 | `{"args": ["999999", "2026-07-07"], "kwargs": {}}` |
| 8 | `a_stock.get_balance_sheet` | 资产负债表 | `{"args": ["600519", "quarterly", "2026-07-07"], "kwargs": {}}` |
| 9 | `a_stock.get_cashflow` | 现金流量表 | `{"args": ["600519", "quarterly", "2026-07-07"], "kwargs": {}}` |
| 10 | `a_stock.get_income_statement` | 利润表 | `{"args": ["600519", "quarterly", "2026-07-07"], "kwargs": {}}` |
| 11 | `a_stock.get_news` | 个股新闻 | `{"args": ["600519", "2026-06-01", "2026-07-07"], "kwargs": {}}` |
| 12 | `a_stock.get_news` | 错误代码新闻失败表现 | `{"args": ["999999", "2026-06-01", "2026-07-07"], "kwargs": {}}` |
| 13 | `a_stock.get_global_news` | 宏观/市场新闻 | `{"args": ["2026-07-07", 7, 5], "kwargs": {}}` |
| 14 | `a_stock.get_insider_transactions` | 股东研究/F10 | `{"args": ["600519"], "kwargs": {}}` |
| 15 | `a_stock.get_insider_transactions` | 错误代码 F10 失败表现 | `{"args": ["999999"], "kwargs": {}}` |
| 16 | `a_stock.get_profit_forecast` | 一致预期 | `{"args": ["600519", "2026-07-07"], "kwargs": {}}` |
| 17 | `a_stock.get_hot_stocks` | 当日强势股 | `{"args": ["2026-07-07"], "kwargs": {}}` |
| 18 | `a_stock.get_northbound_flow` | 北向资金 | `{"args": ["2026-07-07", false], "kwargs": {}}` |
| 19 | `a_stock.get_concept_blocks` | 创业板制造成长概念 | `{"args": ["300450"], "kwargs": {}}` |
| 20 | `a_stock.get_concept_blocks` | 错误代码概念失败表现 | `{"args": ["999999"], "kwargs": {}}` |
| 21 | `a_stock.get_fund_flow` | 创业板权重资金流 | `{"args": ["300750", "2026-07-07", true], "kwargs": {}}` |
| 22 | `a_stock.get_fund_flow` | 错误代码资金流失败表现 | `{"args": ["999999", "2026-07-07", true], "kwargs": {}}` |
| 23 | `a_stock.get_dragon_tiger_board` | 龙虎榜 | `{"args": ["300450", "2026-07-07", 30], "kwargs": {}}` |
| 24 | `a_stock.get_lockup_expiry` | 科创板解禁 | `{"args": ["688981", "2026-07-07", 90], "kwargs": {}}` |
| 25 | `a_stock.get_industry_comparison` | 深市主板行业横向对比 | `{"args": ["000001", "2026-07-07", 10], "kwargs": {}}` |
| 26 | `interface.route_to_vendor` | 路由层正常返回 | `{"args": ["get_stock_data", "000001", "2026-06-01", "2026-07-07"], "kwargs": {}}` |
| 27 | `interface.route_to_vendor` | 路由层错误文本是否视为成功 | `{"args": ["get_news", "999999", "2026-06-01", "2026-07-07"], "kwargs": {}}` |
| 28 | `y_finance.get_YFin_data_online` | Yahoo A 股后缀行情兼容性 | `{"args": ["600519.SS", "2026-06-01", "2026-07-07"], "kwargs": {}}` |
| 29 | `y_finance.get_fundamentals` | Yahoo A 股后缀基本面兼容性 | `{"args": ["600519.SS", "2026-07-07"], "kwargs": {}}` |
| 30 | `yfinance_news.get_news_yfinance` | Yahoo A 股新闻兼容性 | `{"args": ["600519.SS", "2026-06-01", "2026-07-07"], "kwargs": {}}` |
| 31 | `yfinance_news.get_global_news_yfinance` | Yahoo 全球新闻 | `{"args": ["2026-07-07", 7, 5], "kwargs": {}}` |

## Not Directly Smoke-Tested

| Function | Reason |
|---|---|
| `alpha_vantage_stock.get_stock` | 需要 ALPHA_VANTAGE_API_KEY；本轮不提交或配置密钥，且该源不适配 A 股主线。 |
| `alpha_vantage_indicator.get_indicator` | 需要 ALPHA_VANTAGE_API_KEY；本轮不提交或配置密钥，且该源不适配 A 股主线。 |
| `alpha_vantage_fundamentals.*` | 需要 ALPHA_VANTAGE_API_KEY；返回类型与 A 股主线不同，本轮仅记录为无法直接实测。 |
| `alpha_vantage_news.*` | 需要 ALPHA_VANTAGE_API_KEY；海外新闻/情绪源，不适配本轮 A 股 smoke 主线。 |
| `y_finance.get_balance_sheet/get_cashflow/get_income_statement/get_insider_transactions` | Yahoo 代表性 A 股兼容调用已触发限流；这些函数不是 A 股主线，本轮不继续扩大非主线外部请求。 |
| `TradingAgentsGraph._fetch_returns` | 实例方法依赖 TradingAgentsGraph 初始化，可能牵涉 LLM/图配置；本轮禁止运行完整投资分析流程。 |
| `cli.announcements.fetch_announcements / cli.utils._fetch_openrouter_models` | 运维/模型元数据，不进入投研 Agent 上下文；不纳入本轮底层金融数据 smoke。 |
