# DATA_SOURCE_AGENT_MISREAD_RISKS

Generated: 2026-07-07 14:33:14

## Main Findings

- Rows with possible Agent misread risk: 31
- Rows with direct judgment/signal terms: 5
- Rows demonstrating fallback/routing ambiguity: 1

## Direct Judgment Or Signal Terms

| Function | Snippet | Risk |
|---|---|---|
| `a_stock.get_news` | ## 600519 (A-stock) News, from 2026-06-01 to 2026-07-07: ### A股白酒板块震荡反弹，酒鬼酒盘中触及涨停，科技股却突发跳水 (source: 红星资本局) 图据Wind 酒鬼酒（000799.SZ）领涨，盘中一度触及涨停，舍得酒业（600702.SH）、贵州茅台（600519.SH）、山西汾酒（600809.SH）、迎驾贡酒（603198.SH）涨幅靠前，一度涨超3%，水井坊（600779.SH）、口子窖（603589.SH）、洋河股份 Link: http://finance.eastmoney.com/a/202606293786531311.html ### 每10股派280.24元，贵州茅台今日分红 (source: 21世纪经济报道) 贵州茅台 | 可能把数据源文本中的 signal/买入/卖出/主力等词当作独立投资结论。 |
| `a_stock.get_news` | ## 999999 (A-stock) News, from 2026-06-01 to 2026-07-07: ### RC18新批两大适应症，商业化潜力继续释放，深度绑定艾伯维，加速挺进世界级创新药企业 (source: 新浪财经) Link: https://finance.sina.cn/app/tzyb/poly/index.html ### 快讯：碳化硅概念局部异动 露笑科技触及涨停 (source: 新浪财经) Link: https://finance.sina.cn/stock/dpps/2026-07-07/detail-inifyefa8377180.d.html ### 快讯：创业板指跌超2% 全市场下跌个股近4900只 (source: 新浪财经) Link: https://fina | 可能把数据源文本中的 signal/买入/卖出/主力等词当作独立投资结论。 |
| `a_stock.get_profit_forecast` | Error retrieving profit forecast for 600519: [Errno 2] No such file or directory: <!DOCTYPE HTML> <html> <head id="head"> <title>贵州茅台(600519) 盈利预测_F10_同花顺金融服务网</title> <meta http-equiv="X-UA-Compatible" content="IE=EmulateIE7;IE=9"/> <meta http-equiv="Content-Type" content="text/html; charset=gbk"/> <meta name="keywords" content="贵州茅台最新动态,贵州茅台公司概况,贵州茅台财务分析,贵 | 可能把数据源文本中的 signal/买入/卖出/主力等词当作独立投资结论。 |
| `a_stock.get_northbound_flow` | # Northbound Capital Flow (2026-07-07) # Source: 同花顺 hsgtApi (沪深股通) + local cache ## Realtime (cumulative net buying, 亿元) 14:51: HGT=-7.84 SGT=-37.14 14:52: HGT=-7.99 SGT=-36.8 14:53: HGT=-8.51 SGT=-36.76 14:54: HGT=-8.75 SGT=-36.21 14:55: HGT=-9.35 SGT=-36.03 14:56: HGT=-10.07 SGT=-36.22 14:57: HGT=-10.87 SGT=-36.2 14:58: HGT=-10.52 SGT=-36.24 14:59: HGT=-1 | 可能把数据源文本中的 signal/买入/卖出/主力等词当作独立投资结论。 |
| `interface.route_to_vendor` | ## 999999 (A-stock) News, from 2026-06-01 to 2026-07-07: ### RC18新批两大适应症，商业化潜力继续释放，深度绑定艾伯维，加速挺进世界级创新药企业 (source: 新浪财经) Link: https://finance.sina.cn/app/tzyb/poly/index.html ### 快讯：碳化硅概念局部异动 露笑科技触及涨停 (source: 新浪财经) Link: https://finance.sina.cn/stock/dpps/2026-07-07/detail-inifyefa8377180.d.html ### 快讯：创业板指跌超2% 全市场下跌个股近4900只 (source: 新浪财经) Link: https://fina | 可能把数据源文本中的 signal/买入/卖出/主力等词当作独立投资结论。 |

## Failure Text That Can Look Like Normal Tool Output

| Function | Snippet | Risk |
|---|---|---|
| `a_stock.get_stock_data` | K线数据获取失败：mootdx和新浪备用源均不可用，请检查网络连接 | 工具未抛异常，失败状态只存在于自然语言文本中。 |
| `a_stock.get_indicators` | Error calculating rsi for 999999: No OHLCV data from mootdx/sina for 999999 | 工具未抛异常，失败状态只存在于自然语言文本中。 |
| `a_stock.get_balance_sheet` | No balance sheet data found for A-stock '600519' | 工具未抛异常，失败状态只存在于自然语言文本中。 |
| `a_stock.get_cashflow` | No cash flow data found for A-stock '600519' | 工具未抛异常，失败状态只存在于自然语言文本中。 |
| `a_stock.get_income_statement` | No income statement data found for A-stock '600519' | 工具未抛异常，失败状态只存在于自然语言文本中。 |
| `a_stock.get_insider_transactions` | Error retrieving insider/shareholder data for 999999: 'dict' object has no attribute 'strip' | 工具未抛异常，失败状态只存在于自然语言文本中。 |
| `a_stock.get_profit_forecast` | Error retrieving profit forecast for 600519: [Errno 2] No such file or directory: <!DOCTYPE HTML> <html> <head id="head"> <title>贵州茅台(600519) 盈利预测_F10_同花顺金融服务网</title> <meta http-equiv="X-UA-Compatible" content="IE=EmulateIE7;IE=9"/> <meta http-equiv="Content-Type" content="text/html; charset=gbk"/> <meta name="keywords" content="贵州茅台最新动态,贵州茅台公司概况,贵州茅台财务分析,贵 | 工具未抛异常，失败状态只存在于自然语言文本中。 |
| `a_stock.get_concept_blocks` | Baidu PAE error: ResultCode=10003 | 工具未抛异常，失败状态只存在于自然语言文本中。 |
| `a_stock.get_fund_flow` | Error fetching fund flow for 300750: HTTPSConnectionPool(host='push2.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/fflow/kline/get?secid=0.300750&klt=1&fields1=f1%2Cf2%2Cf3%2Cf7&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without | 工具未抛异常，失败状态只存在于自然语言文本中。 |
| `a_stock.get_fund_flow` | Error fetching fund flow for 999999: HTTPSConnectionPool(host='push2.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/fflow/kline/get?secid=0.999999&klt=1&fields1=f1%2Cf2%2Cf3%2Cf7&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without | 工具未抛异常，失败状态只存在于自然语言文本中。 |
| `a_stock.get_dragon_tiger_board` | # 龙虎榜数据 \| 300450 \| 2026-07-07 (近30日) 近30日未上龙虎榜。 | 工具未抛异常，失败状态只存在于自然语言文本中。 |
| `a_stock.get_lockup_expiry` | # 限售解禁日历 \| 688981 \| 2026-07-07 ## 个股解禁记录 (共 4 批) 解禁时间 \| 类型 \| 解禁数量 \| 占比 2027-06-23 \| \| \| 0.273650890928 2022-07-18 \| \| \| 0.034782608696 2021-07-16 \| \| \| 0.414414414414 2021-01-18 \| \| \| 0.050583329759 未来 90 天无待解禁。 | 工具未抛异常，失败状态只存在于自然语言文本中。 |
| `y_finance.get_fundamentals` | No fundamentals data found for symbol '600519.SS' | 工具未抛异常，失败状态只存在于自然语言文本中。 |
| `yfinance_news.get_news_yfinance` | Error fetching news for 600519.SS: Too Many Requests. Rate limited. Try after a while. | 工具未抛异常，失败状态只存在于自然语言文本中。 |
| `yfinance_news.get_global_news_yfinance` | Error fetching global news: Too Many Requests. Rate limited. Try after a while. | 工具未抛异常，失败状态只存在于自然语言文本中。 |

## Fallback Or Scope Ambiguity

| Function | Snippet | Risk |
|---|---|---|
| `a_stock.get_stock_data` | K线数据获取失败：mootdx和新浪备用源均不可用，请检查网络连接 | fallback/路由信息不是结构化字段，Agent 难以区分主源、备源、失败源。 |

## Highest Misread-Risk Functions

- `a_stock.get_fundamentals`: # Company Fundamentals for 600519 (A-stock) # Data retrieved on: 2026-07-07 14:31:59 Float Shares: 1250081562.5 Total Sh; # Company Fundamentals for 999999 (A-stock) # Data retrieved on: 2026-07-07 14:32:00 Float Shares: 4826284800000.0 Total
- `a_stock.get_news`: 返回文本包含判断性词语或信号。; 返回文本包含判断性词语或信号。
- `a_stock.get_global_news`: ## China & Global Market News, from 2026-06-30 to 2026-07-07: ### 安踏集团携手中华慈善总会捐赠1000万元物资 紧急驰援广西救灾 (source: Eastmoney Glo
- `a_stock.get_insider_transactions`: # Shareholder Research for 600519 (A-stock) # Note: A-stock equivalent of insider transactions # Data source: mootdx F10; 返回文本包含失败/空结果提示。
- `a_stock.get_profit_forecast`: 返回文本包含判断性词语或信号。
- `a_stock.get_hot_stocks`: # Hot Stocks with Topic Attribution (2026-07-07) # Source: 同花顺 editorial (human-curated reason tags) # Total: 30 stocks 
- `a_stock.get_northbound_flow`: 返回文本包含判断性词语或信号。
- `a_stock.get_fund_flow`: 返回文本包含失败/空结果提示。; 返回文本包含失败/空结果提示。
- `a_stock.get_industry_comparison`: # 行业横向对比 \| 000001 \| 2026-07-07 ## 全行业表现 (东财 100 个行业) 排名 \| 行业 \| 涨跌幅 \| 上涨 \| 下跌 \| 领涨股 1. 航空机场 \| -2.22% \| 0 \| 14 \| 600897 2.
- `interface.route_to_vendor`: # Stock data for 000001 (A-stock) from 2026-06-01 to 2026-07-07 # Total records: 26 # Data source: mootdx (TCP) # Data r; 返回文本包含判断性词语或信号。
