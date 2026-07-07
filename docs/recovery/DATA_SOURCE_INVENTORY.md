# DATA_SOURCE_INVENTORY

基线：`recovery/data-source-only` @ `b81197653b367f84242e6fe0bca3fb6bac4619b5`

本文件为阶段 1 只读盘点结果。主表共识别 40 个外部数据源调用/路由入口；完整字段版见同目录 `DATA_SOURCE_INVENTORY.csv`。

## 扫描范围

- 目录：项目根目录、`tradingagents/`、`tradingagents/dataflows/`、`tradingagents/agents/`、`tradingagents/graph/`、`cli/`、`web/`、`tests/`、`issues/`、`examples/`。
- 文件类型：`.py`、`.toml`、`.txt`、`.md`、`.json`、`.yml`/`.yaml`、`Dockerfile`。
- 关键词/模式：`requests`、`urllib`、`httpx`、`aiohttp`、`akshare`、`tushare`、`baostock`、`mootdx`、`yfinance`、`Alpha Vantage`、`东方财富`、`腾讯`、`新浪`、`同花顺`、`财联社`、`百度股市通`、硬编码 `http://`/`https://`、`read_html`、`urlopen`、`route_to_vendor`。
- 未发现运行时代码中的 `akshare`、`tushare`、`baostock`、`httpx`、`aiohttp` 数据源调用；`akshare` 仅在文档/issue 中提到已移除。

## 统计

| 主题 | 数量 |
|---|---:|
| 行情/技术/回报 | 6 |
| 基本面/财务/估值 | 13 |
| 新闻/宏观/舆情 | 6 |
| 资金/题材/板块/行业 | 5 |
| 股东/解禁/龙虎榜 | 5 |
| 路由/元数据/运维 | 5 |
| 合计 | 40 |

## 核心数据源概览

| 文件路径 | 函数/类 | 数据主题 | 数据源 | endpoint / 第三方库 | 实时 | A 股适配 | fallback | 稳定性 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| `tradingagents/dataflows/a_stock.py` | `resolve_ticker` / `_build_name_code_map` | 股票名称-代码映射 | mootdx | `Quotes.stocks(market=0/1)`; TCP 7709 | 否 | 是 | 是 | 一般 | 北交所 8 开头未进入 name-code map 过滤 |
| `tradingagents/dataflows/a_stock.py` | `get_stock_data` | 行情/K线 | mootdx; 新浪 | `Quotes.bars`; `CN_MarketData.getKLineData` | 否 | 是 | 是 | 一般 | 失败返回普通文本；新浪 fallback/supplement 在 header 标明 |
| `tradingagents/dataflows/a_stock.py` | `get_indicators` | 技术指标 | stockstats + mootdx/新浪 | `stockstats.wrap`; `_load_ohlcv_astock` | 否 | 是 | 是 | 一般 | 指标、错误、非交易日提示同为文本 |
| `tradingagents/dataflows/a_stock.py` | `get_fundamentals` | 基本面/估值 | 腾讯; mootdx; 东财; 同花顺 | `qt.gtimg.cn`; `finance`; `push2 stock/get`; `10jqka worth.html` | 部分 | 是 | 子源级静默跳过 | 高风险 | 多源拼接；市值/财务字段单位不统一 |
| `tradingagents/dataflows/a_stock.py` | `get_balance_sheet` | 财务报表 | 新浪 | `CompanyFinanceService.getFinanceReport2022?source=fzb` | 否 | 是 | 否 | 一般 | 原始中文字段 CSV；单位未声明 |
| `tradingagents/dataflows/a_stock.py` | `get_cashflow` | 财务报表 | 新浪 | `CompanyFinanceService.getFinanceReport2022?source=llb` | 否 | 是 | 否 | 一般 | 原始中文字段 CSV；单位未声明 |
| `tradingagents/dataflows/a_stock.py` | `get_income_statement` | 财务报表 | 新浪 | `CompanyFinanceService.getFinanceReport2022?source=lrb` | 否 | 是 | 否 | 一般 | 原始中文字段 CSV；单位未声明 |
| `tradingagents/dataflows/a_stock.py` | `get_news` | 个股新闻 | 东方财富; 新浪 | `search-api-web.eastmoney.com/search/jsonp`; `vCB_AllNewsStock.php` | 近实时 | 是 | 是 | 高风险 | 二手新闻标题/摘要进入 Agent；不核验公告原文 |
| `tradingagents/dataflows/a_stock.py` | `get_global_news` | 宏观/市场新闻 | 财联社; 东财 7x24 | `cls.cn/nodeapi/telegraphList`; `np-weblist.eastmoney.com/...getFastNewsList` | 近实时 | 市场级 | 是 | 高风险 | 市场级新闻可能被个股化解释 |
| `tradingagents/dataflows/a_stock.py` | `get_insider_transactions` | 股东/内部人近似数据 | mootdx F10 | `Quotes.F10(name='股东研究')` | 否 | 是 | 否 | 高风险 | 将股东研究近似为 insider transactions |
| `tradingagents/dataflows/a_stock.py` | `get_profit_forecast` | 盈利预测/前向估值 | 同花顺; 腾讯 | `10jqka worth.html`; `qt.gtimg.cn` | 部分 | 是 | 部分 | 高风险 | 一致预期和估值推导可能被当强事实 |
| `tradingagents/dataflows/a_stock.py` | `get_hot_stocks` | 涨停/题材归因 | 同花顺 | `zx.10jqka.com.cn/event/api/getharden` | 当日 | 是 | 否 | 高风险 | 编辑 reason tags 易被误读为确定因果 |
| `tradingagents/dataflows/a_stock.py` | `get_northbound_flow` | 北向资金 | 同花顺 + 本地 cache | `data.hexin.cn/market/hsgtApi/method/dayChart/` | 是 | 市场级 | 历史 cache | 高风险 | `curr_date` 只用于标题；快照用当前系统日期 |
| `tradingagents/dataflows/a_stock.py` | `get_concept_blocks` | 概念/行业/地域 | 百度股市通 | `finance.pae.baidu.com/api/getrelatedblock` | 当日 | 是 | 否 | 高风险 | 概念标签和 ratio 单位不清 |
| `tradingagents/dataflows/a_stock.py` | `get_fund_flow` | 个股资金流 | 东财 push2/push2his | `stock/fflow/kline/get`; `stock/fflow/daykline/get` | 是 | 是 | 部分 | 高风险 | 东财资金流算法黑盒；输出自带 bullish/bearish signal |
| `tradingagents/dataflows/a_stock.py` | `get_dragon_tiger_board` | 龙虎榜/席位 | 东财 datacenter | `RPT_DAILYBILLBOARD_DETAILSNEW`; `RPT_BILLBOARD_DAILYDETAILSBUY/SELL` | 否 | 是 | 否 | 高风险 | 席位异常被 `pass` 隐藏；机构动向由席位代码推断 |
| `tradingagents/dataflows/a_stock.py` | `get_lockup_expiry` | 限售解禁 | 东财 datacenter | `RPT_LIFT_STAGE` | 否 | 是 | 否 | 一般 | 数量/占比原始口径未标准化 |
| `tradingagents/dataflows/a_stock.py` | `get_industry_comparison` | 行业横向对比 | 东财 push2 | `qt/clist/get?fs=m:90+t:2` | 当日 | 市场级 | 否 | 高风险 | 未识别目标个股所属行业；返回全行业排名 |
| `tradingagents/dataflows/interface.py` | `route_to_vendor` | 数据源路由 | 本地 vendor map | `a_stock` / `yfinance` / `alpha_vantage` | 继承 | 部分 | 是 | 高风险 | 隐藏 fallback 链；只有 Alpha 限流异常会继续 fallback |
| `tradingagents/dataflows/y_finance.py` | `get_YFin_data_online` | 行情/K线 | Yahoo Finance | `yf.Ticker().history` | 延迟 | 否 | 否 | 一般 | A 股纯 6 位代码不适配 |
| `tradingagents/dataflows/y_finance.py` / `stockstats_utils.py` | `get_stock_stats_indicators_window` / `load_ohlcv` | 技术指标 | Yahoo Finance + stockstats | `yf.download`; local cache | 否 | 否 | 代码内 bulk->single fallback | 高风险 | 单日失败返回空字符串 |
| `tradingagents/dataflows/y_finance.py` | `get_fundamentals` | 基本面/估值 | Yahoo Finance | `yf.Ticker().info` | 延迟 | 否 | 否 | 一般 | 字段币种/百分比未标注 |
| `tradingagents/dataflows/y_finance.py` | `get_balance_sheet` | 财务报表 | Yahoo Finance | `quarterly_balance_sheet` / `balance_sheet` | 否 | 否 | 否 | 一般 | A 股会计准则不适配 |
| `tradingagents/dataflows/y_finance.py` | `get_cashflow` | 财务报表 | Yahoo Finance | `quarterly_cashflow` / `cashflow` | 否 | 否 | 否 | 一般 | A 股会计准则不适配 |
| `tradingagents/dataflows/y_finance.py` | `get_income_statement` | 财务报表 | Yahoo Finance | `quarterly_income_stmt` / `income_stmt` | 否 | 否 | 否 | 一般 | A 股会计准则不适配 |
| `tradingagents/dataflows/y_finance.py` | `get_insider_transactions` | 内部人交易 | Yahoo Finance | `insider_transactions` | 否 | 否 | 否 | 高风险 | 不适合 A 股内部人/股东口径 |
| `tradingagents/dataflows/yfinance_news.py` | `get_news_yfinance` | 个股新闻 | Yahoo Finance | `Ticker.get_news(count=20)` | 近实时 | 否 | 否 | 高风险 | 海外媒体新闻摘要进入 Agent |
| `tradingagents/dataflows/yfinance_news.py` | `get_global_news_yfinance` | 全球新闻/宏观 | Yahoo Finance Search | `yf.Search(...)` | 近实时 | 否 | 多 query 聚合 | 高风险 | 查询主题偏美股/美联储 |
| `tradingagents/dataflows/alpha_vantage_stock.py` | `get_stock` | 行情/K线 | Alpha Vantage | `TIME_SERIES_DAILY_ADJUSTED` | 否 | 否 | route rate-limit fallback | 一般 | 需 API key；输出 CSV |
| `tradingagents/dataflows/alpha_vantage_indicator.py` | `get_indicator` | 技术指标 | Alpha Vantage | `SMA/EMA/MACD/RSI/BBANDS/ATR` | 否 | 否 | route rate-limit fallback | 一般 | VWMA 未真实计算但返回说明文本 |
| `tradingagents/dataflows/alpha_vantage_fundamentals.py` | `get_fundamentals` | 基本面/估值 | Alpha Vantage | `OVERVIEW` | 否 | 否 | route rate-limit fallback | 一般 | 返回类型与其他 vendor 不一致 |
| `tradingagents/dataflows/alpha_vantage_fundamentals.py` | `get_balance_sheet` | 财务报表 | Alpha Vantage | `BALANCE_SHEET` | 否 | 否 | route rate-limit fallback | 一般 | `_filter_reports_by_date` 对字符串响应无效 |
| `tradingagents/dataflows/alpha_vantage_fundamentals.py` | `get_cashflow` | 财务报表 | Alpha Vantage | `CASH_FLOW` | 否 | 否 | route rate-limit fallback | 一般 | 类型不一致风险 |
| `tradingagents/dataflows/alpha_vantage_fundamentals.py` | `get_income_statement` | 财务报表 | Alpha Vantage | `INCOME_STATEMENT` | 否 | 否 | route rate-limit fallback | 一般 | 类型不一致风险 |
| `tradingagents/dataflows/alpha_vantage_news.py` | `get_news` | 个股新闻/情绪 | Alpha Vantage | `NEWS_SENTIMENT` with `tickers` | 近实时 | 否 | route rate-limit fallback | 高风险 | 海外新闻/情绪不适合 A 股 |
| `tradingagents/dataflows/alpha_vantage_news.py` | `get_global_news` | 全球新闻/情绪 | Alpha Vantage | `NEWS_SENTIMENT` with topics | 近实时 | 否 | route rate-limit fallback | 高风险 | 宏观主题偏全球/美国 |
| `tradingagents/dataflows/alpha_vantage_news.py` | `get_insider_transactions` | 内部人交易 | Alpha Vantage | `INSIDER_TRANSACTIONS` | 否 | 否 | route rate-limit fallback | 高风险 | 不适合作为 A 股内部人数据 |
| `tradingagents/graph/trading_graph.py` | `TradingAgentsGraph._fetch_returns` | 收益回填/记忆评估 | Yahoo Finance | `Ticker(ticker).history`; `Ticker('000300.SS').history` | 否 | 部分 | 否 | 一般 | 与主 A 股数据源不一致 |
| `cli/announcements.py` | `fetch_announcements` | CLI 公告/运维 | Tauric API | `https://api.tauric.ai/v1/announcements` | 是 | 非投研 | 本地 fallback | 稳定 | 不进入投研上下文 |
| `cli/utils.py` | `_fetch_openrouter_models` | 模型目录/运维 | OpenRouter | `https://openrouter.ai/api/v1/models` | 是 | 非投研 | 否 | 稳定 | 不进入投研上下文 |

## 硬编码 URL 旁注

另扫描到 `web/app.py` 的 Google Fonts CSS URL、`tradingagents/llm_clients/openai_client.py`/`cli/utils.py` 的 LLM provider base URL、README/issues/examples 中的文档链接和 badge URL。这些属于 UI/LLM/文档元数据，不是行情、财务、新闻或资金数据源，未计入上表金融数据源主项；其中 OpenRouter 模型目录和 CLI 公告因存在运行时 `requests.get` 已纳入主表。

## 当前结论

- A 股主线默认配置在 `tradingagents/default_config.py` 指向 `a_stock`，但 `main.py` 示例仍配置 `yfinance`，且接口路由保留 `yfinance`/`alpha_vantage`。
- A 股数据层真实依赖集中在 `mootdx`、腾讯、东方财富、同花顺、新浪、财联社、百度股市通。
- 大多数数据函数返回类型为 `str`，成功、空结果、错误、fallback 信息都混在自然语言/Markdown/CSV 字符串里。
- `route_to_vendor` 存在 fallback 链，但只有 `AlphaVantageRateLimitError` 会触发继续；普通错误文本不会触发 fallback。
