# Tushare Pro 第一批字段映射

本文件只定义字段映射和口径，不包含实现代码。

## 公共字段与状态

| 输出字段 | 含义 | 适用函数 |
|---|---|---|
| `source` | 固定为 `Tushare`，或 fallback 时标明原源 | 全部 |
| `api` | Tushare 接口名，例如 `income` | 全部 |
| `status` | `ok` / `partial_data` / `no_data` / `technical_error` / `no_coverage` | 全部 |
| `ts_code` | Tushare 股票代码 | 全部 |
| `as_of` | 调用方传入的截止日期 | 全部 |
| `as_of_field` | 实际用于防未来函数的字段，例如 `ann_date` / `trade_date` / `report_date` | 全部 |
| `empty_reason` | 空结果原因，短字符串 | 全部失败或空结果 |

## `get_profit_forecast` -> `report_rc`

### 输入映射

| 原参数 | Tushare 参数 | 规则 |
|---|---|---|
| `ticker` | `ts_code` | 6 位代码转换为 `.SH` / `.SZ` / `.BJ` |
| `curr_date` | `end_date` / 本地过滤 | `report_date <= curr_date` |
| 无 | `start_date` | 默认 `curr_date - 365 days`，无数据可扩大但需标注 |

### 输出映射

| Tushare 字段 | 第一批输出 | 聚合规则 |
|---|---|---|
| `quarter` | `forecast_period` / `FY{year}` | 按预测期分组 |
| `report_date` | `report_date_range` / 最新研报日期 | as-of 与新鲜度判断 |
| `org_name` | `institution` / `source_org_count` | 同机构同预测期保留最近一条 |
| `author_name` | `analyst` | 明细可选输出 |
| `eps` | `eps_mean` / `eps_median` / `eps_min` / `eps_max` | 数值聚合 |
| `np` | `net_profit_mean` / median/min/max | 有值时聚合 |
| `op_rt` | `revenue_mean` / median/min/max | 有值时聚合 |
| `rating` | 第二批字段 | 第一批不做评级结论 |
| `max_price` / `min_price` | 第二批字段 | 第一批不输出强目标价结论 |

### 输出兼容样式

```text
# Consensus EPS Forecast for 600519 (A-stock)
# Source: Tushare report_rc sell-side forecast aggregation
# Retrieved: ...
# as_of_field: report_date
# note: sell-side forecast, not company guidance

FY2026: EPS mean=..., median=..., range ...~..., institutions=...
FY2027: ...
```

## 财务三表字段映射

### 共同输入映射

| 原参数 | Tushare 参数/过滤 | 规则 |
|---|---|---|
| `ticker` | `ts_code` | 6 位代码转换 |
| `freq=annual` | `period` / 本地过滤 | 只保留 `end_date` 月日为 `1231` |
| `freq=quarterly` | `period` / 本地过滤 | 保留 `0331/0630/0930/1231`，累计口径 |
| `curr_date` | `ann_date` 本地过滤 | 必须 `ann_date <= curr_date` |
| 无 | `report_type` | 第一批只取合并报表；实现阶段需核对代码值 |
| 无 | `comp_type` | 输出保留，第一批不做行业排除 |

### 公共输出字段

| Tushare 字段 | 输出字段 | 说明 |
|---|---|---|
| `ts_code` | `ts_code` | 股票代码 |
| `ann_date` | `ann_date` | as-of 字段 |
| `f_ann_date` | `f_ann_date` | 实际公告日期，保留 |
| `end_date` | `end_date` | 报告期 |
| `report_type` | `report_type` | 用于合并/母公司等口径识别 |
| `comp_type` | `comp_type` | 公司类型 |
| `end_type` | `end_type` | 报告期类型 |

### `balancesheet` 核心字段

| Tushare 字段 | 中文含义 | 第一批处理 |
|---|---|---|
| `total_share` | 期末总股本 | 输出 |
| `money_cap` | 货币资金 | 输出 |
| `accounts_receiv` | 应收账款 | 输出 |
| `inventories` | 存货 | 输出 |
| `total_assets` | 资产总计 | 输出 |
| `total_liab` | 负债合计 | 输出 |
| `total_hldr_eqy_exc_min_int` | 归母权益 | 输出 |
| 其他字段 | Tushare 完整资产负债表字段 | CSV 原样保留 |

### `cashflow` 核心字段

| Tushare 字段 | 中文含义 | 第一批处理 |
|---|---|---|
| `net_profit` | 净利润 | 输出 |
| `c_fr_sale_sg` | 销售商品、提供劳务收到的现金 | 输出 |
| `n_cashflow_act` | 经营活动现金流净额 | 输出，如字段存在 |
| `n_cashflow_inv_act` | 投资活动现金流净额 | 输出，如字段存在 |
| `n_cash_flows_fnc_act` | 筹资活动现金流净额 | 输出，如字段存在 |
| `c_cash_equ_end_period` | 期末现金及现金等价物余额 | 输出，如字段存在 |
| 其他字段 | Tushare 完整现金流量表字段 | CSV 原样保留 |

### `income` 核心字段

| Tushare 字段 | 中文含义 | 第一批处理 |
|---|---|---|
| `basic_eps` | 基本每股收益 | 输出 |
| `total_revenue` | 营业总收入 | 输出 |
| `revenue` | 营业收入 | 输出 |
| `oper_profit` | 营业利润 | 输出，如字段存在 |
| `total_profit` | 利润总额 | 输出 |
| `n_income` | 净利润 | 输出 |
| `n_income_attr_p` | 归母净利润 | 输出，如字段存在 |
| 其他字段 | Tushare 完整利润表字段 | CSV 原样保留 |

## `get_fundamentals` -> `daily_basic + stock_basic`

### 输入映射

| 原参数 | Tushare 参数 | 规则 |
|---|---|---|
| `ticker` | `ts_code` | 6 位代码转换 |
| `curr_date` | `trade_date` / 回看过滤 | 取 `trade_date <= curr_date` 最近交易日 |
| 无 | `stock_basic.list_status` | 默认 `L`，必要时允许退市/暂停状态第二批扩展 |

### 字段映射

| 第一批输出 | Tushare 接口 | Tushare 字段 | 说明 |
|---|---|---|---|
| 股票代码 | `stock_basic` / `daily_basic` | `ts_code` / `symbol` | 保留 TS 代码与 6 位代码 |
| 股票名称 | `stock_basic` | `name` | 静态基础信息 |
| 行业 | `stock_basic` | `industry` | 行业口径来自 Tushare 股票基础 |
| 上市日期 | `stock_basic` | `list_date` | 静态基础信息 |
| 市场类型 | `stock_basic` | `market` | 主板/创业板/科创板等 |
| 交易日期 | `daily_basic` | `trade_date` | 最近交易日 |
| 收盘价 | `daily_basic` | `close` | 日频，不是实时 |
| PE | `daily_basic` | `pe` / `pe_ttm` | 优先输出 `pe_ttm`，同时保留 `pe` |
| PB | `daily_basic` | `pb` | 日频估值 |
| PS | `daily_basic` | `ps` / `ps_ttm` | 优先输出 `ps_ttm` |
| 总市值 | `daily_basic` | `total_mv` | 单位万元 |
| 流通市值 | `daily_basic` | `circ_mv` | 单位万元 |
| 换手率 | `daily_basic` | `turnover_rate` / `turnover_rate_f` | 可同时输出 |
| 量比 | `daily_basic` | `volume_ratio` | 日频指标 |
| 总股本 | `daily_basic` | `total_share` | 单位万股 |
| 流通股本 | `daily_basic` | `float_share` | 单位万股 |

### 不进入第一批字段

| 接口/字段 | 原因 |
|---|---|
| `stock_company` 公司画像字段 | 第二批补充 |
| `fina_indicator` EPS/ROE 等财务指标 | 第二批补充 |
| `dividend` 分红字段 | 第二批事件补充 |
| `adj_factor` 复权因子 | 行情复权支持，不是 fundamentals |

## `get_fund_flow` -> `moneyflow` / `moneyflow_dc`

### 输入映射

| 原参数 | Tushare 参数 | 规则 |
|---|---|---|
| `ticker` | `ts_code` | 6 位代码转换 |
| `curr_date` | `trade_date` / `end_date` | 取 `trade_date <= curr_date` |
| `include_history=True` | `start_date` + `end_date` | 默认最近 20 个可得交易日 |
| `include_history=False` | `trade_date` | 最近一个可得交易日 |

### `moneyflow` 主源字段映射

| Tushare 字段 | 第一批输出 | 说明 |
|---|---|---|
| `trade_date` | `trade_date` | 交易日 |
| `buy_sm_amount` / `sell_sm_amount` | 小单买入/卖出金额 | 万元 |
| `buy_md_amount` / `sell_md_amount` | 中单买入/卖出金额 | 万元 |
| `buy_lg_amount` / `sell_lg_amount` | 大单买入/卖出金额 | 万元 |
| `buy_elg_amount` / `sell_elg_amount` | 超大单买入/卖出金额 | 万元 |
| `net_mf_amount` | 净流入额 | 万元 |
| `buy_*_vol` / `sell_*_vol` | 买入/卖出量 | 手 |

### `moneyflow_dc` 备用字段映射

| Tushare 字段 | 第一批输出 | 说明 |
|---|---|---|
| `trade_date` | `trade_date` | 交易日 |
| `close` | `close` | 最新/收盘价 |
| `pct_change` | `pct_change` | 涨跌幅 |
| `net_amount` | 主力净流入额 | 万元 |
| `net_amount_rate` | 主力净流入占比 | % |
| `buy_elg_amount` | 超大单净流入额 | 万元，净额口径 |
| `buy_lg_amount` | 大单净流入额 | 万元，净额口径 |
| `buy_md_amount` | 中单净流入额 | 万元，净额口径 |
| `buy_sm_amount` | 小单净流入额 | 万元，净额口径 |

### 不能映射到 `get_fund_flow`

| 接口 | 原因 |
|---|---|
| `moneyflow_hsgt` | 北向/南向市场资金，不是个股资金流 |
| `moneyflow_mkt_dc` | 大盘资金流，不是个股资金流；正式权限需 6000 积分 |
| `moneyflow_ths` | 语义接近但需 6000 积分，第二批再评估 |

