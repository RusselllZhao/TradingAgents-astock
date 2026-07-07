# Tushare Pro 第一批候选接口最小实测

阶段：4B-2

## 执行边界

- `TUSHARE_TOKEN`：present（未输出 token 值）。
- 仅调用第一批候选接口：`stock_basic`、`daily_basic`、`balancesheet`、`cashflow`、`income`、`report_rc`、`moneyflow`、`moneyflow_dc`。
- 未调用 `forecast` / `express` / `fina_indicator` / 新闻公告 / 北向资金 / 大盘资金 / 同花顺资金流等非第一批接口。
- 未修改 `a_stock.py` / `interface.py`，未接入业务函数。
- 未写入真实缓存，未提交 token。
- 当前 Codex Python 标准库 HTTPS 证书校验不可用，本脚本使用系统 `curl` 并通过 stdin 传递请求体，token 不进入命令行参数或输出。

## 汇总

| 接口 | 样例 | 状态 | 行数 | 权限可用 | 缺失核心字段 | 短错误 | 备注 |
|---|---|---:|---:|---|---|---|---|
| stock_basic | 600519.SH | ok | 1 | yes | 无 | 无 | 基础股票信息可用性 |
| daily_basic | 600519.SH@20260707 | ok | 1 | yes | 无 | 无 | 最近可用交易日 |
| balancesheet | 600519.SH | ok | 100 | yes | 无 | 无 | 最近已公告报表字段验证 |
| cashflow | 600519.SH | ok | 96 | yes | 无 | 无 | 最近已公告报表字段验证 |
| income | 600519.SH | ok | 117 | yes | 无 | 无 | 最近已公告报表字段验证 |
| report_rc | 600519.SH@20250707-20260707 | ok | 823 | yes | 无 | 无 | 近一年卖方盈利预测 |
| moneyflow | 300750.SZ@20260707 | ok | 1 | yes | 无 | 无 | 最近可用交易日 |
| moneyflow_dc | 300750.SZ@20260707 | ok | 1 | yes | 无 | 无 | 备用资金流源字段验证 |

## 字段核验

### `stock_basic`

- 样例：`600519.SH`
- 状态：`ok`
- 返回行数：`1`
- 权限可用：`yes`
- 已返回核心字段：`ts_code, symbol, name, area, industry, market, list_date`
- 缺失核心字段：`无`
- 返回字段：`ts_code, symbol, name, area, industry, market, list_date`
- 短错误类型：`无`

### `daily_basic`

- 样例：`600519.SH@20260707`
- 状态：`ok`
- 返回行数：`1`
- 权限可用：`yes`
- 已返回核心字段：`trade_date, close, pe, pe_ttm, pb, ps, ps_ttm, total_mv, circ_mv, turnover_rate, volume_ratio, total_share, float_share`
- 缺失核心字段：`无`
- 返回字段：`trade_date, close, pe, pe_ttm, pb, ps, ps_ttm, total_mv, circ_mv, turnover_rate, volume_ratio, total_share, float_share`
- 短错误类型：`无`

### `balancesheet`

- 样例：`600519.SH`
- 状态：`ok`
- 返回行数：`100`
- 权限可用：`yes`
- 已返回核心字段：`ts_code, ann_date, f_ann_date, end_date, report_type, comp_type, end_type`
- 缺失核心字段：`无`
- 返回字段：`ts_code, ann_date, f_ann_date, end_date, report_type, comp_type, end_type`
- 短错误类型：`无`

### `cashflow`

- 样例：`600519.SH`
- 状态：`ok`
- 返回行数：`96`
- 权限可用：`yes`
- 已返回核心字段：`ts_code, ann_date, end_date, report_type, comp_type, net_profit, n_cashflow_act, n_cashflow_inv_act, n_cash_flows_fnc_act`
- 缺失核心字段：`无`
- 返回字段：`ts_code, ann_date, end_date, report_type, comp_type, net_profit, n_cashflow_act, n_cashflow_inv_act, n_cash_flows_fnc_act`
- 短错误类型：`无`

### `income`

- 样例：`600519.SH`
- 状态：`ok`
- 返回行数：`117`
- 权限可用：`yes`
- 已返回核心字段：`basic_eps, total_revenue, revenue, total_profit, n_income, n_income_attr_p`
- 缺失核心字段：`无`
- 返回字段：`basic_eps, total_revenue, revenue, total_profit, n_income, n_income_attr_p`
- 短错误类型：`无`

### `report_rc`

- 样例：`600519.SH@20250707-20260707`
- 状态：`ok`
- 返回行数：`823`
- 权限可用：`yes`
- 已返回核心字段：`report_date, quarter, org_name, author_name, eps, np, op_rt, rating`
- 缺失核心字段：`无`
- 返回字段：`report_date, quarter, org_name, author_name, eps, np, op_rt, rating`
- 短错误类型：`无`

### `moneyflow`

- 样例：`300750.SZ@20260707`
- 状态：`ok`
- 返回行数：`1`
- 权限可用：`yes`
- 已返回核心字段：`trade_date, buy_sm_amount, sell_sm_amount, buy_md_amount, sell_md_amount, buy_lg_amount, sell_lg_amount, buy_elg_amount, sell_elg_amount, net_mf_amount`
- 缺失核心字段：`无`
- 返回字段：`trade_date, buy_sm_amount, sell_sm_amount, buy_md_amount, sell_md_amount, buy_lg_amount, sell_lg_amount, buy_elg_amount, sell_elg_amount, net_mf_amount`
- 短错误类型：`无`

### `moneyflow_dc`

- 样例：`300750.SZ@20260707`
- 状态：`ok`
- 返回行数：`1`
- 权限可用：`yes`
- 已返回核心字段：`trade_date, net_amount, net_amount_rate, buy_elg_amount, buy_lg_amount, buy_md_amount, buy_sm_amount`
- 缺失核心字段：`无`
- 返回字段：`trade_date, net_amount, net_amount_rate, buy_elg_amount, buy_lg_amount, buy_md_amount, buy_sm_amount`
- 短错误类型：`无`

