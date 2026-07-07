# DATA_SOURCE_RISK_NOTES

基线：`recovery/data-source-only` @ `b81197653b367f84242e6fe0bca3fb6bac4619b5`

本文件只记录阶段 1 只读风险初判，不提出业务代码改动。

## 高风险总览

| 风险 | 涉及函数/位置 | 初判 |
|---|---|---|
| 数据源失败后返回看似正常的文本 | `a_stock.py` 多数 public tool、`y_finance.py`、`yfinance_news.py`、`alpha_vantage_indicator.py` | 高风险 |
| 媒体二手报道包装成事实 | `get_news`、`get_global_news`、`get_news_yfinance`、`get_global_news_yfinance`、Alpha Vantage `NEWS_SENTIMENT` | 高风险 |
| 市场级数据误当成个股级数据 | `get_global_news`、`get_northbound_flow`、`get_hot_stocks`、`get_industry_comparison`、Yahoo global search | 高风险 |
| 字段单位不清或口径混杂 | `get_fundamentals`、三张财报、`get_concept_blocks`、`get_lockup_expiry`、`get_fund_flow` | 高风险 |
| 空结果静默降级 | `get_fundamentals` 子源 warning 后继续、`get_dragon_tiger_board` 席位异常 `pass`、Yahoo 技术指标空字符串 | 高风险 |
| fallback 被隐藏或不一致 | `route_to_vendor`、`get_stock_data`、`get_news`、`get_northbound_flow`、`get_fund_flow` | 高风险 |
| 不可核验数据被下游当强事实 | 同花顺题材/一致预期、东财资金流 signal、mootdx F10 股东研究、百度概念标签 | 高风险 |

## 重点高风险数据源列表

1. `tradingagents/dataflows/a_stock.py::get_fundamentals`
   - 拼接腾讯实时估值、mootdx 财务快照、东财基本信息、同花顺一致预期。
   - 子源失败只写 warning 并继续，输出没有字段级 provenance。
   - 市值既有 `Market Cap (100M CNY)`，又有东财 `总市值` 原始数值，单位可能被 Agent 混读。

2. `tradingagents/dataflows/a_stock.py::get_news`
   - 东财搜索失败或无结果后 fallback 到新浪个股新闻。
   - 输出为 Markdown 标题/摘要/链接；来源多为媒体稿，不等于公告或公司一手事实。
   - 两源都失败时返回 `No news found...` 文本，形式上仍像正常工具结果。

3. `tradingagents/dataflows/a_stock.py::get_global_news`
   - 财联社和东财 7x24 聚合为宏观/市场新闻。
   - 新闻时间未严格按 `look_back_days` 二次过滤所有条目；更多依赖接口返回。
   - 下游新闻/政策 Agent 可能把市场级消息强行映射到个股。

4. `tradingagents/dataflows/a_stock.py::get_insider_transactions`
   - 使用 mootdx F10 `股东研究` 作为 A 股 insider transactions 的近似替代。
   - 函数名和工具描述可能让下游按美股 insider transaction 理解。

5. `tradingagents/dataflows/a_stock.py::get_profit_forecast`
   - 同花顺一致预期 + 腾讯价格推导 Forward PE/PEG。
   - 低覆盖仅输出文本 warning，不影响后续估值推导。
   - 一致预期属于第三方聚合，非公司公告或交易所披露。

6. `tradingagents/dataflows/a_stock.py::get_hot_stocks`
   - 同花顺编辑题材 reason tags 被直接统计成 Theme Frequency。
   - 题材归因可能是人工标签或资讯归纳，不应等价于涨停的确定因果。

7. `tradingagents/dataflows/a_stock.py::get_northbound_flow`
   - `curr_date` 只用于报告标题；本地快照保存使用 `datetime.now()`。
   - 北向资金是市场级数据，但输出包含 `Signal: ... bullish/bearish`，易影响个股判断。

8. `tradingagents/dataflows/a_stock.py::get_fund_flow`
   - 东财资金流分单算法为黑盒；输出直接给出 `Signal: Net main force INFLOW/OUTFLOW`。
   - 实时为空时只写 `No realtime fund flow`，仍可继续输出历史段落。

9. `tradingagents/dataflows/a_stock.py::get_dragon_tiger_board`
   - 上榜记录、买席、卖席、机构筛选分多次接口调用。
   - 买卖席位查询异常被 `except Exception: pass` 隐藏。
   - 机构动向通过 `OPERATEDEPT_CODE == "0"` 推断，需谨慎。

10. `tradingagents/dataflows/a_stock.py::get_industry_comparison`
    - `ticker` 只用于标题，没有实际定位个股所属行业。
    - 返回全行业排名，可能被 Agent 当作目标公司所在行业横向对比。

11. `tradingagents/dataflows/interface.py::route_to_vendor`
    - 配置 vendor 后会把其他可用 vendor 追加到 fallback 链。
    - 实际只有 `AlphaVantageRateLimitError` 会继续尝试下一个 vendor。
    - 如果某 vendor 返回 `Error ...` / `No data ...` 字符串，路由视为成功返回。

12. `tradingagents/dataflows/yfinance_news.py::get_global_news_yfinance`
    - 查询词偏美股/美联储/全球市场。
    - 若配置误切到 `yfinance`，可能把海外宏观新闻注入 A 股辩论。

13. `tradingagents/dataflows/alpha_vantage_news.py::*`
    - Alpha Vantage 新闻和情绪源面向海外市场。
    - 对 A 股适配为否，且返回原始 JSON 字符串，与 A 股 Markdown 工具返回形态不一致。

14. `tradingagents/graph/trading_graph.py::TradingAgentsGraph._fetch_returns`
    - 记忆/结果回填使用 yfinance，而默认 A 股分析使用 `a_stock`。
    - 个股 `ticker` 未强制 Yahoo A 股后缀，可能出现回报数据不可得或错配。

## 失败文本与正常文本混淆

当前多数工具函数返回 `str`。这些字符串既可能是成功数据，也可能是错误、空结果、非交易日或 fallback 说明：

- `K线数据获取失败：mootdx和新浪备用源均不可用，请检查网络连接`
- `No news found for A-stock 'xxxxxx'`
- `Error retrieving fundamentals for ...`
- `No realtime fund flow (non-trading hours or holiday)`
- `行业数据获取为空。`
- `同花顺 API error: ...`

由于工具层没有统一结构化状态字段，Agent 可能把这些文本当作数据证据的一部分，或在报告里把“没有数据/接口失败”解释为“没有风险/没有事件”。

## 二手报道与一手事实边界

新闻相关函数主要读取媒体或资讯聚合：

- 东方财富搜索：个股新闻标题、摘要、媒体名、链接。
- 新浪财经新闻页：标题和链接。
- 财联社快讯：快讯标题/brief/content。
- 东财 7x24：标题/summary。
- Yahoo/Alpha Vantage：海外媒体新闻和 sentiment。

未看到巨潮资讯公告正文、交易所公告正文、公司公告 PDF 或可核验原文解析。新闻 Analyst prompt 虽提示注意官方消息与传闻，但数据工具本身没有提供“是否一手公告/是否媒体转载/是否已核验”的字段。

## 市场级数据个股化风险

以下函数返回的是市场级、板块级或全局列表，但可能在个股分析上下文中被直接解释为目标公司的证据：

- `get_global_news`：宏观/市场新闻。
- `get_northbound_flow`：沪股通+深股通总流入。
- `get_hot_stocks`：当日强势股和题材频次。
- `get_industry_comparison`：全行业排名，且未真正匹配目标个股行业。
- `get_global_news_yfinance`：全球市场搜索新闻。

建议后续如做最小替换或 wrapper，优先增加“scope=market/sector/stock”的显式标记；本轮未修改代码。

## 单位和口径不清

已发现的主要单位/口径风险：

- 腾讯 `mcap_yi` 标为 `100M CNY`，东财 `f116/f117` 原始数值未转换，两者同时出现在 `get_fundamentals`。
- mootdx `finance` 字段如 `profit`、`income`、`liutongguben`、`zongguben` 未在输出中声明单位。
- 新浪三张表输出原始中文字段 CSV，单位依赖上游但代码未标注。
- `get_fund_flow` 原始为元，输出转万元；实时和历史都用同一文字口径，但上游字段含义依赖东财。
- `get_concept_blocks` 的 `ratio` 原样输出，未声明是否百分比、涨跌幅或其他指标。
- `get_lockup_expiry` 的 `FREE_SHARES_NUM` 原样输出，未声明股/万股/亿股等单位。

## fallback 与静默降级

- `get_stock_data`：mootdx 失败后新浪 fallback；mootdx 数据滞后时新浪 supplement。结果 header 会写 source，但无结构化 fallback 字段。
- `get_news`：东财失败/无结果后新浪 fallback；若东财返回过期或低质量结果，不会再查新浪补充。
- `get_fundamentals`：腾讯、mootdx、东财、同花顺各自 try/except，单源失败只 warning 后继续。
- `get_dragon_tiger_board`：席位细节异常静默 `pass`，报告可能只剩上榜记录。
- `get_northbound_flow`：历史依赖本地 cache，cache 缺失时输出说明；实时失败则整个函数 Error。
- `route_to_vendor`：隐藏 vendor fallback 链，但普通错误文本不会触发 fallback。

## 是否可能污染 Agent 辩论逻辑

发现可能污染 Agent 辩论逻辑的数据返回方式，主要原因不是单个 endpoint，而是返回契约：

- 工具统一返回自然语言/Markdown/CSV 混合字符串，没有 `ok/error/empty/source/fallback/scope/unit/as_of` 等结构化字段。
- 部分工具直接生成 `bullish/bearish` 信号，例如资金流和北向资金，可能在 Bull/Bear 辩论中被当作独立强结论。
- 市场级数据和个股级数据在文本上没有强隔离。
- 二手新闻、人工题材、第三方一致预期、黑盒资金流没有可核验等级。
- fallback 和子源失败不总是显式暴露给 Agent。

## 后续优先确认对象

1. `get_fundamentals` 字段单位和子源失败契约。
2. `get_news`/`get_global_news` 是否需要官方公告源或至少加媒体/公告标记。
3. `get_industry_comparison` 是否应真正定位目标个股行业。
4. `get_northbound_flow`/`get_fund_flow` 是否应去掉或降级自然语言 bullish/bearish 结论。
5. `route_to_vendor` 是否应把错误文本视为失败并暴露 vendor/fallback 状态。

本轮未修改任何业务代码、prompt、辩论逻辑或 Quality Gate。
