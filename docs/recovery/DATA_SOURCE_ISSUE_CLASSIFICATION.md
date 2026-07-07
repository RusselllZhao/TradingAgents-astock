# DATA_SOURCE_ISSUE_CLASSIFICATION

基线：`recovery/data-source-only` @ `b81197653b367f84242e6fe0bca3fb6bac4619b5`

本文件对阶段 2 Smoke Test 的异常、空结果、失败文本、误读风险重新分类。完整字段矩阵见 `DATA_SOURCE_ISSUE_CLASSIFICATION.csv`。

## 分类口径

| 分类 | 定义 | 是否进入第一批 |
|---|---|---|
| A纯技术错误 | 正常股票也出现接口失败、代理错误、限流、HTML/解析异常、类型错误、接口疑似失效、应有数据无法返回 | 仅 A 股主线正常股票进入第一批 |
| B技术契约问题 | 失败不抛异常、普通字符串承载失败、fallback/status/source/as_of/unit/scope 缺失、路由无法区分成功和失败文本 | 原则上不进第一批，除非为 A 类必要最小 wrapper |
| C正常业务空结果 | 查询成功但当前股票/窗口无事件，如未上龙虎榜、未来无解禁、非交易日 N/A | 不进第一批，仅建议后续结构化 empty reason |
| D业务解释风险 | 新闻事实边界、市场级数据个股化、题材标签可靠性、一致预期强证据化等 | 不进第一批，进入第二批业务口径 backlog |

## 重分类摘要

| 分类 | 数量 | 主要对象 |
|---|---:|---|
| A纯技术错误 | 9 | 正常股票三表空、同花顺盈利预测 HTML 异常、东财资金流代理错误、Yahoo 限流 |
| B技术契约问题 | 12 | 999999 输入校验、失败字符串、route_to_vendor 状态不可见、正常行情文本缺结构化 metadata |
| C正常业务空结果 | 3 | 非交易日指标 N/A、近 30 日未上龙虎榜、未来 90 天无解禁 |
| D业务解释风险 | 7 | 新闻、宏观新闻、F10 股东研究、题材、北向资金、概念、行业榜 |
| 合计 | 31 | 覆盖阶段 2 的 31 个直接调用样本 |

注：A 类数量中包含 3 个 Yahoo 兼容源限流/失败项，但第一批只建议处理 6 个 A 股主线正常股票问题，不扩大到非主线 vendor。

## 第一批候选原则

第一批只处理同时满足以下条件的问题：

- 正常股票样本触发；
- 属于 A 股主线函数；
- 属于纯技术错误或为阻断 A 类错误进入 Agent 的必要最小 wrapper；
- 不需要换源优先，不改 prompt，不改 Quality Gate，不改 Agent 辩论逻辑；
- 验收可以通过独立 smoke test 完成。

## 进入第一批的 A 股主线问题

| 函数 | Smoke 表现 | 推荐动作 | 最小改动范围 |
|---|---|---|---|
| `a_stock.get_fundamentals(600519)` | 正常股票只返回股本，腾讯/东财/同花顺子源失败被静默跳过 | 立即修复 | `get_fundamentals` 子源失败标记和必要拦截 |
| `a_stock.get_balance_sheet(600519)` | 正常股票返回 No balance sheet data found | 立即修复 | 新浪三表 helper 或最小失败拦截 |
| `a_stock.get_cashflow(600519)` | 正常股票返回 No cash flow data found | 立即修复 | 新浪三表 helper 或最小失败拦截 |
| `a_stock.get_income_statement(600519)` | 正常股票返回 No income statement data found | 立即修复 | 新浪三表 helper 或最小失败拦截 |
| `a_stock.get_profit_forecast(600519)` | 同花顺 HTML 被当作异常文本返回，长度约 281991 | 立即修复 | `_ths_eps_forecast` / `get_profit_forecast` HTML 拦截与解析修复 |
| `a_stock.get_fund_flow(300750)` | 正常股票东财资金流 ProxyError 以普通字符串返回 | 立即修复 | `get_fund_flow` 请求失败拦截和结构化技术错误 |

## 降级或暂缓的问题

| 对象 | 分类 | 暂缓原因 |
|---|---|---|
| `999999` 相关全部样本 | B技术契约问题 | 按本轮口径降级为输入校验问题，不列第一批 |
| `get_dragon_tiger_board(300450)` | C正常业务空结果 | 近 30 日未上龙虎榜可能为真实无事件 |
| `get_lockup_expiry(688981)` | C正常业务空结果 | 未来 90 天无待解禁可能为真实无事件 |
| `get_news` / `get_global_news` | D业务解释风险 | 技术上有返回；一手事实/媒体边界属于第二批业务口径 |
| `get_northbound_flow` / `get_hot_stocks` / `get_industry_comparison` | D业务解释风险 | 市场级/题材/行业解释风险，不进第一批代码修复 |
| Yahoo / Alpha Vantage | A/B/D 混合 | 非 A 股主线，暂不扩大整改面 |

## 明确不建议触碰

- 不建议修改 prompt。
- 不建议修改 Quality Gate。
- 不建议修改 Bull/Bear 或任何 Agent 辩论逻辑。
- 不建议接入或替换新数据源。
- 不建议做大规模结构化重构。

本轮只做问题分类和优先级重排，未修改业务代码。
