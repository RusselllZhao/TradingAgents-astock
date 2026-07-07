# DATA_SOURCE_FAILURE_CASES

Generated: 2026-07-07 14:33:14

## Failure-Like Returns

- Failure-like rows: 16
- Returned without Python exception but contained failure/empty/error text: 15

| Function | Inputs | Python exception? | Snippet | Why it matters |
|---|---|---|---|---|
| `a_stock.get_stock_data` | `{"args": ["999999", "2026-06-01", "2026-07-07"], "kwargs": {}}` | False | K线数据获取失败：mootdx和新浪备用源均不可用，请检查网络连接 | 错误/空结果以普通返回值进入上游，路由或 Agent 可能视为成功工具结果。 |
| `a_stock.get_indicators` | `{"args": ["999999", "rsi", "2026-07-07", 10], "kwargs": {}}` | False | Error calculating rsi for 999999: No OHLCV data from mootdx/sina for 999999 | 错误/空结果以普通返回值进入上游，路由或 Agent 可能视为成功工具结果。 |
| `a_stock.get_balance_sheet` | `{"args": ["600519", "quarterly", "2026-07-07"], "kwargs": {}}` | False | No balance sheet data found for A-stock '600519' | 错误/空结果以普通返回值进入上游，路由或 Agent 可能视为成功工具结果。 |
| `a_stock.get_cashflow` | `{"args": ["600519", "quarterly", "2026-07-07"], "kwargs": {}}` | False | No cash flow data found for A-stock '600519' | 错误/空结果以普通返回值进入上游，路由或 Agent 可能视为成功工具结果。 |
| `a_stock.get_income_statement` | `{"args": ["600519", "quarterly", "2026-07-07"], "kwargs": {}}` | False | No income statement data found for A-stock '600519' | 错误/空结果以普通返回值进入上游，路由或 Agent 可能视为成功工具结果。 |
| `a_stock.get_insider_transactions` | `{"args": ["999999"], "kwargs": {}}` | False | Error retrieving insider/shareholder data for 999999: 'dict' object has no attribute 'strip' | 错误/空结果以普通返回值进入上游，路由或 Agent 可能视为成功工具结果。 |
| `a_stock.get_profit_forecast` | `{"args": ["600519", "2026-07-07"], "kwargs": {}}` | False | Error retrieving profit forecast for 600519: [Errno 2] No such file or directory: <!DOCTYPE HTML> <html> <head id="head"> <title>贵州茅台(600519) 盈利预测_F10_同花顺金融服务网</title> <meta http-equiv="X-UA-Compatible" content="IE=EmulateIE7;IE=9"/> <meta http-equiv="Content-Type" content="text/html; charset=gbk"/> <meta name="keywords" content="贵州茅台最新动态,贵州茅台公司概况,贵州茅台财务分析,贵 | 错误/空结果以普通返回值进入上游，路由或 Agent 可能视为成功工具结果。 |
| `a_stock.get_concept_blocks` | `{"args": ["999999"], "kwargs": {}}` | False | Baidu PAE error: ResultCode=10003 | 错误/空结果以普通返回值进入上游，路由或 Agent 可能视为成功工具结果。 |
| `a_stock.get_fund_flow` | `{"args": ["300750", "2026-07-07", true], "kwargs": {}}` | False | Error fetching fund flow for 300750: HTTPSConnectionPool(host='push2.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/fflow/kline/get?secid=0.300750&klt=1&fields1=f1%2Cf2%2Cf3%2Cf7&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without | 错误/空结果以普通返回值进入上游，路由或 Agent 可能视为成功工具结果。 |
| `a_stock.get_fund_flow` | `{"args": ["999999", "2026-07-07", true], "kwargs": {}}` | False | Error fetching fund flow for 999999: HTTPSConnectionPool(host='push2.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/fflow/kline/get?secid=0.999999&klt=1&fields1=f1%2Cf2%2Cf3%2Cf7&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without | 错误/空结果以普通返回值进入上游，路由或 Agent 可能视为成功工具结果。 |
| `a_stock.get_dragon_tiger_board` | `{"args": ["300450", "2026-07-07", 30], "kwargs": {}}` | False | # 龙虎榜数据 \| 300450 \| 2026-07-07 (近30日) 近30日未上龙虎榜。 | 错误/空结果以普通返回值进入上游，路由或 Agent 可能视为成功工具结果。 |
| `a_stock.get_lockup_expiry` | `{"args": ["688981", "2026-07-07", 90], "kwargs": {}}` | False | # 限售解禁日历 \| 688981 \| 2026-07-07 ## 个股解禁记录 (共 4 批) 解禁时间 \| 类型 \| 解禁数量 \| 占比 2027-06-23 \| \| \| 0.273650890928 2022-07-18 \| \| \| 0.034782608696 2021-07-16 \| \| \| 0.414414414414 2021-01-18 \| \| \| 0.050583329759 未来 90 天无待解禁。 | 错误/空结果以普通返回值进入上游，路由或 Agent 可能视为成功工具结果。 |
| `y_finance.get_YFin_data_online` | `{"args": ["600519.SS", "2026-06-01", "2026-07-07"], "kwargs": {}}` | True | YFRateLimitError: Too Many Requests. Rate limited. Try after a while. Traceback (most recent call last): File "/Users/chenyuzhao/Documents/investment-system3.0 - trading agents/TradingAgents-astock-data-source-recovery/scripts/recovery/smoke_data_sources.py", line 225, in run_calls value = with_timeout(call.timeout, lambda c=call: c.func(*c.args, **c.kwargs) | 调用抛出异常或超时，需要上游显式处理。 |
| `y_finance.get_fundamentals` | `{"args": ["600519.SS", "2026-07-07"], "kwargs": {}}` | False | No fundamentals data found for symbol '600519.SS' | 错误/空结果以普通返回值进入上游，路由或 Agent 可能视为成功工具结果。 |
| `yfinance_news.get_news_yfinance` | `{"args": ["600519.SS", "2026-06-01", "2026-07-07"], "kwargs": {}}` | False | Error fetching news for 600519.SS: Too Many Requests. Rate limited. Try after a while. | 错误/空结果以普通返回值进入上游，路由或 Agent 可能视为成功工具结果。 |
| `yfinance_news.get_global_news_yfinance` | `{"args": ["2026-07-07", 7, 5], "kwargs": {}}` | False | Error fetching global news: Too Many Requests. Rate limited. Try after a while. | 错误/空结果以普通返回值进入上游，路由或 Agent 可能视为成功工具结果。 |

## Unable To Directly Test

| Function | Reason |
|---|---|
| `alpha_vantage_stock.get_stock` | 需要 ALPHA_VANTAGE_API_KEY；本轮不提交或配置密钥，且该源不适配 A 股主线。 |
| `alpha_vantage_indicator.get_indicator` | 需要 ALPHA_VANTAGE_API_KEY；本轮不提交或配置密钥，且该源不适配 A 股主线。 |
| `alpha_vantage_fundamentals.*` | 需要 ALPHA_VANTAGE_API_KEY；返回类型与 A 股主线不同，本轮仅记录为无法直接实测。 |
| `alpha_vantage_news.*` | 需要 ALPHA_VANTAGE_API_KEY；海外新闻/情绪源，不适配本轮 A 股 smoke 主线。 |
| `y_finance.get_balance_sheet/get_cashflow/get_income_statement/get_insider_transactions` | Yahoo 代表性 A 股兼容调用已触发限流；这些函数不是 A 股主线，本轮不继续扩大非主线外部请求。 |
| `TradingAgentsGraph._fetch_returns` | 实例方法依赖 TradingAgentsGraph 初始化，可能牵涉 LLM/图配置；本轮禁止运行完整投资分析流程。 |
| `cli.announcements.fetch_announcements / cli.utils._fetch_openrouter_models` | 运维/模型元数据，不进入投研 Agent 上下文；不纳入本轮底层金融数据 smoke。 |
