# Tushare Pro 第一批问题函数业务口径复核

本文件属于阶段 3C-0：只做业务语义复核，不做替换实现方案设计。未调用 Tushare token，未修改 TradingAgents 业务代码。

## 总体结论

- `a_stock.get_profit_forecast`：当前代码语义是机构/分析师 EPS 一致预期。Tushare `forecast`、`express`、`fina_indicator` 均不能直接替换；`report_rc` 语义最接近，但 5000 积分只是试用权限，不能作为稳定第一批主源。
- 财务三表：`balancesheet`、`cashflow`、`income` 与原函数业务语义高度匹配，可进入下一步替换方案设计候选，但需在方案阶段确认报告期、公告日、报表类型、合并/母公司、单季/累计口径。
- `a_stock.get_fundamentals`：不能用单一接口替换。第一批核心候选是 `daily_basic` 补估值/市值/换手/股本，`stock_basic` 补股票基础信息；`stock_company`、`fina_indicator`、`dividend` 更偏补充。`adj_factor` 不建议作为 fundamentals 替换。
- `a_stock.get_fund_flow`：`moneyflow` 最匹配个股资金流；`moneyflow_dc` 部分匹配且日频盘后；`moneyflow_hsgt` 是北向/南向市场资金，不应替代个股资金流；`moneyflow_mkt_dc` 是大盘资金且 5000 非正式权限，不建议第一批使用。

## 第一批问题函数清单

| 函数 | 第一批是否必须修 | 当前技术问题 | 业务复核后是否建议进入下一步替换方案设计 |
|---|---|---|---|
| `a_stock.get_profit_forecast` | 是 | 正常股票 600519 返回同花顺 HTML/反爬页异常文本，长度约 281991，失败内容进入普通返回字符串。 | 暂不建议直接进入替换设计；需先确认是否接受 report_rc 试用/补权限 |
| `a_stock.get_balance_sheet` | 是 | 正常股票 600519 返回 No balance sheet data found。 | 是，Tushare 同名三表接口业务匹配 |
| `a_stock.get_cashflow` | 是 | 正常股票 600519 返回 No cash flow data found。 | 是，Tushare 同名三表接口业务匹配 |
| `a_stock.get_income_statement` | 是 | 正常股票 600519 返回 No income statement data found。 | 是，Tushare 同名三表接口业务匹配 |
| `a_stock.get_fundamentals` | 是 | 正常股票 600519 只返回 Float Shares/Total Shares，腾讯/东财/同花顺子源疑似失败且静默。 | 是，但必须按字段拆解，不做单接口替换 |
| `a_stock.get_fund_flow` | 是 | 正常股票 300750 东财 push2 连接/代理错误，以普通错误字符串返回。 | 是，仅限 `moneyflow` / 可能备用 `moneyflow_dc` |

## a_stock.get_profit_forecast

- 当前代码实际数据来源：同花顺 basic.10jqka.com.cn worth.html；`_ths_eps_forecast` 用 pandas.read_html 解析机构 EPS 一致预期表；再结合腾讯实时价格计算 Forward PE/PEG。
- 函数名暗示业务含义：机构盈利预测 / 分析师一致预期 / Forward valuation，而不是上市公司正式业绩预告。
- 当前实际返回业务含义：返回 Consensus EPS Forecast、预测机构数、EPS 均值/区间、低覆盖提示、当前价、PE(TTM)、Forward PE、PEG 等。

| Tushare 接口 | 中文名 | 真实业务含义 | 5000 积分稳定可用 | 试用权限 | 单独权限 | 完全匹配 | 部分匹配 | 不匹配 | 第一批主源 | 第一批备用 | 第二批补充 | 不建议 | 推荐结论 | 需要人工确认 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| report_rc | 卖方盈利预测数据 | 券商/卖方研报盈利预测数据，按研报日期和预测报告期提供机构、作者、预测 EPS/利润等，语义最接近“机构盈利预测”。 | 否。页面写 2000 积分可试用、每天 10 次；正式权限需 8000 积分，5000 积分不应视为稳定主权限。 | 是 | 否 | 否 | 是 | 否 | 否 | 否 | 是 | 否 | 不能直接作为第一批稳定主源；可作为语义最接近的候选补充或人工确认后的备用源。 | 是否接受“每天 10 次试用”的 report_rc 作为人工验证/备用？是否计划补到 8000 积分以获得正式权限？ |
| forecast | 业绩预告 | 上市公司正式披露的业绩预告，反映公司对报告期净利润变动区间和预告类型的公告口径。 | 是 | 否 | 否 | 否 | 是 | 否 | 否 | 否 | 是 | 否 | 不能直接替换，只能作为补充；若使用必须改业务表述为“公司业绩预告”。 | 是否希望在第二批新增“公司业绩预告”数据主题，而不是替代 get_profit_forecast？ |
| express | 业绩快报 | 上市公司正式披露的业绩快报，通常为正式财报前的初步经营结果。 | 是 | 否 | 否 | 否 | 是 | 否 | 否 | 否 | 是 | 否 | 不能直接替换，只能作为补充；业务名称应是“业绩快报”。 | 是否需要在第二批补充“正式业绩快报”作为已披露事实源？ |
| fina_indicator | 财务指标数据 | 上市公司已披露财务指标，包括 EPS、ROE、每股指标、利润率等历史报告期指标。 | 是 | 否 | 否 | 否 | 是 | 否 | 否 | 否 | 是 | 否 | 不能替代预测；可补强 fundamentals 或作为历史实际财务指标对照。 | 是否允许将历史财务指标并入 fundamentals，而不放入 profit_forecast？ |

## a_stock.get_balance_sheet

- 当前代码实际数据来源：新浪 CompanyFinanceService.getFinanceReport2022，source=fzb，按报告日过滤，annual 仅取 12 月报告，返回前 8 条 CSV。
- 函数名暗示业务含义：资产负债表财务报表数据。
- 当前实际返回业务含义：资产负债表历史报告期 CSV；当前实现未显式区分合并/母公司、报表类型细节，依赖新浪字段。

| Tushare 接口 | 中文名 | 真实业务含义 | 5000 积分稳定可用 | 试用权限 | 单独权限 | 完全匹配 | 部分匹配 | 不匹配 | 第一批主源 | 第一批备用 | 第二批补充 | 不建议 | 推荐结论 | 需要人工确认 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| balancesheet | 资产负债表 | 资产负债表接口；按股票代码、公告日期、报告期、报告类型等参数获取上市公司财务报表，输出含 ann_date/f_ann_date/end_date/report_type/comp_type/end_type 等口径字段。 | 是 | 否 | 否 | 是 | 否 | 否 | 是（若下一步确认允许引入 Tushare 替换源） | 是 | 否 | 否 | 业务语义高度匹配，可进入下一步替换方案设计的主候选。 | 是否要求返回“单季”而非累计值？是否只保留合并报表，还是允许母公司/调整表？是否按 ann_date 还是 f_ann_date 做 as_of 截止？ |

## a_stock.get_cashflow

- 当前代码实际数据来源：新浪 CompanyFinanceService.getFinanceReport2022，source=llb，按报告日过滤，annual 仅取 12 月报告，返回前 8 条 CSV。
- 函数名暗示业务含义：现金流量表财务报表数据。
- 当前实际返回业务含义：现金流量表历史报告期 CSV；当前实现未显式区分合并/母公司、报表类型细节，依赖新浪字段。

| Tushare 接口 | 中文名 | 真实业务含义 | 5000 积分稳定可用 | 试用权限 | 单独权限 | 完全匹配 | 部分匹配 | 不匹配 | 第一批主源 | 第一批备用 | 第二批补充 | 不建议 | 推荐结论 | 需要人工确认 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cashflow | 现金流量表 | 现金流量表接口；按股票代码、公告日期、报告期、报告类型等参数获取上市公司财务报表，输出含 ann_date/f_ann_date/end_date/report_type/comp_type/end_type 等口径字段。 | 是 | 否 | 否 | 是 | 否 | 否 | 是（若下一步确认允许引入 Tushare 替换源） | 是 | 否 | 否 | 业务语义高度匹配，可进入下一步替换方案设计的主候选。 | 是否要求返回“单季”而非累计值？是否只保留合并报表，还是允许母公司/调整表？是否按 ann_date 还是 f_ann_date 做 as_of 截止？ |

## a_stock.get_income_statement

- 当前代码实际数据来源：新浪 CompanyFinanceService.getFinanceReport2022，source=lrb，按报告日过滤，annual 仅取 12 月报告，返回前 8 条 CSV。
- 函数名暗示业务含义：利润表财务报表数据。
- 当前实际返回业务含义：利润表历史报告期 CSV；当前实现未显式区分合并/母公司、报表类型细节，依赖新浪字段。

| Tushare 接口 | 中文名 | 真实业务含义 | 5000 积分稳定可用 | 试用权限 | 单独权限 | 完全匹配 | 部分匹配 | 不匹配 | 第一批主源 | 第一批备用 | 第二批补充 | 不建议 | 推荐结论 | 需要人工确认 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| income | 利润表 | 利润表接口；按股票代码、公告日期、报告期、报告类型等参数获取上市公司财务报表，输出含 ann_date/f_ann_date/end_date/report_type/comp_type/end_type 等口径字段。 | 是 | 否 | 否 | 是 | 否 | 否 | 是（若下一步确认允许引入 Tushare 替换源） | 是 | 否 | 否 | 业务语义高度匹配，可进入下一步替换方案设计的主候选。 | 是否要求返回“单季”而非累计值？是否只保留合并报表，还是允许母公司/调整表？是否按 ann_date 还是 f_ann_date 做 as_of 截止？ |

## a_stock.get_fundamentals

- 当前代码实际数据来源：组合源：腾讯实时估值/行情、mootdx finance 财务快照、东财 push2 基础信息、同花顺 EPS 一致预期；输出拼接文本。
- 函数名暗示业务含义：公司基本面总览，包括名称、行业、价格、估值、市值、股本、财务快照、可能的一致预期。
- 当前实际返回业务含义：理想情况下返回 Name/Price/PE/PB/Market Cap/Turnover/股本/行业/上市日期/一致预期 EPS/Forward PE；Smoke 中实际只剩 Float Shares/Total Shares。

| Tushare 接口 | 中文名 | 真实业务含义 | 5000 积分稳定可用 | 试用权限 | 单独权限 | 完全匹配 | 部分匹配 | 不匹配 | 第一批主源 | 第一批备用 | 第二批补充 | 不建议 | 推荐结论 | 需要人工确认 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| stock_basic | 股票基础信息 | A股股票基础列表，包含代码、名称、地域、行业、市场类型、上市状态、上市日期等证券基础信息。 | 是 | 否 | 否 | 否 | 是 | 否 | 否 | 是 | 否 | 否 | 适合作为基础信息部分的稳定候选，不可单独替换整个 fundamentals。 | fundamentals 第一批是否只要求恢复核心估值/市值，还是也必须补齐基础信息？ |
| stock_company | 上市公司基本信息 | 上市公司公司层面基础信息，含公司全称、法人、董秘、注册资本、成立日期、主营业务等。 | 是 | 否 | 否 | 否 | 是 | 否 | 否 | 是 | 否 | 否 | 适合作为公司画像补充，不适合作为第一批核心主源。 | 是否需要在 fundamentals 输出公司高管/注册地址/主营业务等画像字段？ |
| daily_basic | 每日指标 | 每日股票基本面指标，含收盘价、换手率、量比、PE、PB、PS、总市值、流通市值、股本等交易日指标。 | 是 | 否 | 否 | 否 | 是 | 否 | 是 | 是 | 否 | 否 | 适合作为第一批 fundamentals 核心估值/市值主候选。 | 第一批是否允许 fundamentals 从“实时”估值降级为最近交易日 EOD 指标？ |
| fina_indicator | 财务指标数据 | 已披露财务指标，含 EPS、ROE、每股指标、利润率、成长能力、偿债能力等报告期指标。 | 是 | 否 | 否 | 否 | 是 | 否 | 否 | 是 | 是 | 否 | 适合作为 fundamentals 财务指标补充；不建议作为第一批最小修复唯一主源。 | 是否希望第一批 fundamentals 包含报告期财务指标，还是只恢复日频估值/市值？ |
| dividend | 分红送股 | 上市公司分红送股数据，含预案、实施进度、每股分红、送转比例等。 | 是 | 否 | 否 | 否 | 是 | 否 | 否 | 否 | 是 | 否 | 只适合作为第二批业务补充。 | 是否要把分红纳入 fundamentals，还是独立成事件数据？ |
| adj_factor | 复权因子 | 股票复权因子，用于复权行情计算。 | 是 | 否 | 否 | 否 | 是 | 否 | 否 | 否 | 是 | 否 | 不建议作为 fundamentals 替换；仅作为行情复权支持数据。 | 是否需要在行情替换阶段单独评估 adj_factor，而不是 fundamentals 阶段？ |

## a_stock.get_fund_flow

- 当前代码实际数据来源：东财 push2 个股资金流接口：实时分钟主力/大小单/超大单净流入，以及 push2his 近 20 个交易日日资金流。
- 函数名暗示业务含义：个股资金流向，尤其是主力/大单/中单/小单净流入，不是市场级资金或北向资金。
- 当前实际返回业务含义：返回单只股票实时分钟资金流和历史日资金流，并附带主力净流入 Signal 文案。

| Tushare 接口 | 中文名 | 真实业务含义 | 5000 积分稳定可用 | 试用权限 | 单独权限 | 完全匹配 | 部分匹配 | 不匹配 | 第一批主源 | 第一批备用 | 第二批补充 | 不建议 | 推荐结论 | 需要人工确认 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| moneyflow | 个股资金流向 | 沪深A股个股资金流向，分析大单小单成交情况，字段包括小/中/大/超大单买卖量和金额。 | 是 | 否 | 否 | 是 | 否 | 否 | 是 | 是 | 否 | 否 | 业务语义最匹配，可作为第一批主替换候选。 | 是否接受 Tushare 历史日频资金流替代当前“实时分钟 + 近20日”混合口径中的实时部分？ |
| moneyflow_dc | 个股资金流向（DC） | 东方财富个股资金流向，日频盘后更新，含主力净流入额、净占比、大单/超大单等字段。 | 是 | 否 | 否 | 否 | 是 | 否 | 否 | 是 | 否 | 否 | 适合作为第一批备用源或字段对齐候选。 | 第一批是否必须保留实时分钟资金流？若必须，moneyflow_dc 只能补历史日频。 |
| moneyflow_hsgt | 沪深港通资金流向 | 沪股通、深股通、港股通每日资金流向，输出北向/南向市场级资金。 | 是 | 否 | 否 | 否 | 是 | 否 | 否 | 否 | 是 | 否 | 不能直接替代个股资金流；只适合作为北向资金/市场资金补充。 | 是否在第二批单独映射到 get_northbound_flow，而非 get_fund_flow？ |
| moneyflow_mkt_dc | 大盘资金流向（DC） | 东方财富大盘资金流向，市场指数层面的主力净流入。 | 否。页面写 120 积分可试用、6000 积分可正式调取，5000 积分不是稳定正式权限。 | 是 | 否 | 否 | 否 | 是 | 否 | 否 | 否 | 是 | 不建议第一批使用；语义不匹配且 5000 仅试用/非正式。 | 是否完全排除市场级资金流替代个股资金流？建议排除。 |
| moneyflow_ths | 个股资金流向（THS） | 同花顺个股资金流向，日频盘后更新。 | 否。最低 6000 积分，5000 不可用。 | 否 | 否 | 否 | 是 | 否 | 否 | 否 | 否 | 是 | 暂不建议使用。 | 若后续积分到 6000，是否重新评估同花顺资金流作为备选？ |

## 分类清单

### 业务语义完全匹配的接口

- `a_stock.get_balance_sheet` -> `balancesheet`：业务语义高度匹配，可进入下一步替换方案设计的主候选。
- `a_stock.get_cashflow` -> `cashflow`：业务语义高度匹配，可进入下一步替换方案设计的主候选。
- `a_stock.get_income_statement` -> `income`：业务语义高度匹配，可进入下一步替换方案设计的主候选。
- `a_stock.get_fund_flow` -> `moneyflow`：业务语义最匹配，可作为第一批主替换候选。

### 业务语义部分匹配的接口

- `a_stock.get_profit_forecast` -> `report_rc`：不能直接作为第一批稳定主源；可作为语义最接近的候选补充或人工确认后的备用源。
- `a_stock.get_profit_forecast` -> `forecast`：不能直接替换，只能作为补充；若使用必须改业务表述为“公司业绩预告”。
- `a_stock.get_profit_forecast` -> `express`：不能直接替换，只能作为补充；业务名称应是“业绩快报”。
- `a_stock.get_profit_forecast` -> `fina_indicator`：不能替代预测；可补强 fundamentals 或作为历史实际财务指标对照。
- `a_stock.get_fundamentals` -> `stock_basic`：适合作为基础信息部分的稳定候选，不可单独替换整个 fundamentals。
- `a_stock.get_fundamentals` -> `stock_company`：适合作为公司画像补充，不适合作为第一批核心主源。
- `a_stock.get_fundamentals` -> `daily_basic`：适合作为第一批 fundamentals 核心估值/市值主候选。
- `a_stock.get_fundamentals` -> `fina_indicator`：适合作为 fundamentals 财务指标补充；不建议作为第一批最小修复唯一主源。
- `a_stock.get_fundamentals` -> `dividend`：只适合作为第二批业务补充。
- `a_stock.get_fundamentals` -> `adj_factor`：不建议作为 fundamentals 替换；仅作为行情复权支持数据。
- `a_stock.get_fund_flow` -> `moneyflow_dc`：适合作为第一批备用源或字段对齐候选。
- `a_stock.get_fund_flow` -> `moneyflow_hsgt`：不能直接替代个股资金流；只适合作为北向资金/市场资金补充。
- `a_stock.get_fund_flow` -> `moneyflow_ths`：暂不建议使用。

### 业务语义不匹配的接口

- `a_stock.get_fund_flow` -> `moneyflow_mkt_dc`：不建议第一批使用；语义不匹配且 5000 仅试用/非正式。

### 5000 积分稳定可用的接口

- `forecast` (业绩预告) for `a_stock.get_profit_forecast`
- `express` (业绩快报) for `a_stock.get_profit_forecast`
- `fina_indicator` (财务指标数据) for `a_stock.get_profit_forecast`
- `balancesheet` (资产负债表) for `a_stock.get_balance_sheet`
- `cashflow` (现金流量表) for `a_stock.get_cashflow`
- `income` (利润表) for `a_stock.get_income_statement`
- `stock_basic` (股票基础信息) for `a_stock.get_fundamentals`
- `stock_company` (上市公司基本信息) for `a_stock.get_fundamentals`
- `daily_basic` (每日指标) for `a_stock.get_fundamentals`
- `fina_indicator` (财务指标数据) for `a_stock.get_fundamentals`
- `dividend` (分红送股) for `a_stock.get_fundamentals`
- `adj_factor` (复权因子) for `a_stock.get_fundamentals`
- `moneyflow` (个股资金流向) for `a_stock.get_fund_flow`
- `moneyflow_dc` (个股资金流向（DC）) for `a_stock.get_fund_flow`
- `moneyflow_hsgt` (沪深港通资金流向) for `a_stock.get_fund_flow`

### 5000 积分只是试用或需确认的接口

- `report_rc`：稳定可用=否。页面写 2000 积分可试用、每天 10 次；正式权限需 8000 积分，5000 积分不应视为稳定主权限。；试用=是；单独权限=否；权限原文：描述：获取券商（卖方）每天研报的盈利预测数据，数据从2010年开始，每晚19~22点更新当日数据；限量：单次最大3000条，可分页和循环提取所有数据；权限：本接口2000积分可以试用，每天10次请求，正式权限需8000积分，每天可请求100000次，10000积分以上无总量限制。
- `moneyflow_mkt_dc`：稳定可用=否。页面写 120 积分可试用、6000 积分可正式调取，5000 积分不是稳定正式权限。；试用=是；单独权限=否；权限原文：限量：单次最大3000条，可根据日期或日期区间循环获取；积分：120积分可试用，6000积分可正式调取，具体请参阅 积分获取办法
- `moneyflow_ths`：稳定可用=否。最低 6000 积分，5000 不可用。；试用=否；单独权限=否；权限原文：限量：单次最大6000，可根据日期或股票代码循环提取数据；积分：6000积分可调取，具体请参阅 积分获取办法

### 不建议第一批接入的接口

- `report_rc` for `a_stock.get_profit_forecast`：不能直接作为第一批稳定主源；可作为语义最接近的候选补充或人工确认后的备用源。
- `forecast` for `a_stock.get_profit_forecast`：不能直接替换，只能作为补充；若使用必须改业务表述为“公司业绩预告”。
- `express` for `a_stock.get_profit_forecast`：不能直接替换，只能作为补充；业务名称应是“业绩快报”。
- `fina_indicator` for `a_stock.get_profit_forecast`：不能替代预测；可补强 fundamentals 或作为历史实际财务指标对照。
- `fina_indicator` for `a_stock.get_fundamentals`：适合作为 fundamentals 财务指标补充；不建议作为第一批最小修复唯一主源。
- `dividend` for `a_stock.get_fundamentals`：只适合作为第二批业务补充。
- `adj_factor` for `a_stock.get_fundamentals`：不建议作为 fundamentals 替换；仅作为行情复权支持数据。
- `moneyflow_hsgt` for `a_stock.get_fund_flow`：不能直接替代个股资金流；只适合作为北向资金/市场资金补充。
- `moneyflow_mkt_dc` for `a_stock.get_fund_flow`：不建议第一批使用；语义不匹配且 5000 仅试用/非正式。
- `moneyflow_ths` for `a_stock.get_fund_flow`：暂不建议使用。

## 是否建议进入下一步替换方案设计

- 建议进入：财务三表 `balancesheet` / `cashflow` / `income`；个股资金流 `moneyflow`；fundamentals 的 `daily_basic` + `stock_basic` 字段级组合。
- 暂缓进入：`a_stock.get_profit_forecast`，除非你确认接受 `report_rc` 试用权限或后续补足 8000 积分；`forecast` / `express` / `fina_indicator` 不能作为直接替换。
- 不建议进入第一批：`moneyflow_hsgt`、`moneyflow_mkt_dc`、`moneyflow_ths`、`adj_factor` 作为 fundamentals 替换。
