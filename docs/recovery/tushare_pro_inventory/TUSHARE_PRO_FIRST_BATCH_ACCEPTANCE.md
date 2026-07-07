# Tushare Pro 第一批方案验收设计

本文件只定义未来代码修复后的验收方式。本轮不运行 Tushare API，不调用 token。

## 验收原则

- 只运行底层函数 smoke，不运行多 Agent。
- 使用正常股票样本：`600519`、`300750`，必要时补 `688981`。
- 不要求所有接口都有数据，但失败必须短、可识别、不可被误读为正常报告。
- 不允许出现 HTML 原文、异常栈、代理栈、超长错误文本。
- 输出必须包含 source/api/status/as-of 相关信息。

## 通用失败文本规范

| 场景 | 允许返回 | 禁止返回 |
|---|---|---|
| token 缺失 | 短 `technical_error: tushare_token_missing` | token 值、环境变量 dump |
| 权限不足 | 短 `technical_error: tushare_permission_denied` | 完整异常栈 |
| 频率限制 | 短 `technical_error: tushare_rate_limited` | 原始长 traceback |
| 无数据 | 短 `no_data` 或 `no_coverage` + reason | 裸 `No data found` 且无 source/status |
| HTML/反爬 | 短 `technical_error: upstream_html_or_challenge` | HTML 页面全文 |
| 网络失败 | 短 `technical_error: network_error` | 代理栈全文 |

建议长度上限：错误返回不超过 1200 字符；普通成功输出不在此限制内。

## `get_profit_forecast`

### 样例

```python
a_stock.get_profit_forecast("600519", "2026-07-07")
a_stock.get_profit_forecast("300750", "2026-07-07")
```

### 成功验收

- Header 包含 `Consensus EPS Forecast`。
- Header 包含 `Source: Tushare report_rc sell-side forecast aggregation`。
- 明确 `sell-side forecast`，不得出现把公司公告当作预测的措辞。
- 至少出现一个预测期或短 `no_coverage`。
- 若有数据，包含 `institutions` / `source_count` / `report_date_range`。
- 聚合字段包含 EPS mean/median/min/max；净利润或收入有值时输出聚合。

### 失败验收

- 同花顺 fallback 若触发，不返回 HTML。
- token/权限/网络错误短文本。
- `forecast`、`express`、`fina_indicator` 不出现在本函数主源输出中。

## `get_balance_sheet`

### 样例

```python
a_stock.get_balance_sheet("600519", "quarterly", "2026-07-07")
a_stock.get_balance_sheet("600519", "annual", "2026-07-07")
```

### 成功验收

- Header 包含 `Data source: Tushare`。
- Header 包含 `API: balancesheet`。
- Header 包含 `as_of_field: ann_date`、`period_field: end_date`。
- CSV 包含 `ts_code`、`ann_date`、`end_date`、`report_type`、`comp_type`。
- 不包含 `ann_date > 2026-07-07` 的记录。
- `quarterly` 返回累计报告期，不做单季转换。

### 失败验收

- 空结果返回短 `no_data`，带 `reason=no_statement_before_as_of` 或等价原因。
- 权限/网络返回短 `technical_error`。

## `get_cashflow`

### 样例

```python
a_stock.get_cashflow("600519", "quarterly", "2026-07-07")
a_stock.get_cashflow("300750", "annual", "2026-07-07")
```

### 成功验收

- Header 包含 `API: cashflow`。
- CSV 包含公共字段：`ts_code`、`ann_date`、`end_date`、`report_type`、`comp_type`。
- 如字段存在，应保留 `net_profit`、经营/投资/筹资现金流净额相关字段。
- 不读未来公告数据。

### 失败验收

- 不返回裸 `No cash flow data found`。
- 不返回长异常。

## `get_income_statement`

### 样例

```python
a_stock.get_income_statement("600519", "quarterly", "2026-07-07")
a_stock.get_income_statement("300750", "annual", "2026-07-07")
```

### 成功验收

- Header 包含 `API: income`。
- CSV 包含 `basic_eps`、`total_revenue`、`revenue`、`total_profit`、`n_income` 等可得字段。
- 保留 `ann_date` 与 `end_date`，不混淆 as-of 与报告期。

### 失败验收

- 不返回裸 `No income statement data found`。
- 不返回长异常。

## `get_fundamentals`

### 样例

```python
a_stock.get_fundamentals("600519", "2026-07-07")
a_stock.get_fundamentals("300750", "2026-07-07")
```

### 成功验收

- Header 包含 `Company Fundamentals`。
- Header 或正文标明 `Source: Tushare daily_basic + stock_basic`。
- 标明 `realtime=false` 和最近 `trade_date`。
- 至少返回以下核心字段中的多数：
  - `Name`
  - `Industry`
  - `Market`
  - `List Date`
  - `Close`
  - `PE (TTM)` 或 `PE`
  - `PB`
  - `Market Cap`
  - `Float Market Cap`
  - `Turnover Rate`
  - `Volume Ratio`
  - `Total Shares`
  - `Float Shares`
- 如果只返回部分字段，必须标注 `partial_data` 和失败子源。

### 失败验收

- 不再出现正常股票只剩 Float Shares/Total Shares 且无解释的情况。
- 空结果短 `no_data` 或 `technical_error`。

## `get_fund_flow`

### 样例

```python
a_stock.get_fund_flow("300750", "2026-07-07", include_history=True)
a_stock.get_fund_flow("600519", "2026-07-07", include_history=False)
```

### 成功验收

- Header 包含 `Fund Flow`。
- Header 包含 `Source: Tushare moneyflow` 或 fallback `moneyflow_dc`。
- Header 包含 `Frequency: daily`、`Scope: individual_stock`。
- 输出包含 `trade_date`。
- 主源成功时包含小/中/大/超大单买卖金额和净流入额。
- 备用源成功时标注 `fallback=moneyflow_dc`、`net_only=true`。
- 不出现北向资金、大盘资金字段。
- 不输出强 buy/sell 投资建议；如保留 signal，只能是数据摘要。

### 失败验收

- 不返回东财 push2 ProxyError 长文本。
- 主源失败备用成功时返回 `partial_data`。
- 主备均失败时短 `technical_error`。

## 禁止验收项

- 不运行多 Agent。
- 不调用 LLM 分析股票。
- 不修改 prompt / Quality Gate。
- 不提交 token。
- 不把真实缓存提交到 git。

