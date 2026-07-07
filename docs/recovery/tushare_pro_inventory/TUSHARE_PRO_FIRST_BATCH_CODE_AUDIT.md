# Tushare Pro First Batch Code Audit

- Audit date: 2026-07-07
- Branch: `recovery/data-source-only`
- Audited range: `fd16d00^..e4f2073`
- Current first-batch regression commit before this audit document: `e4f2073`
- Scope: Tushare client foundation, first-batch live smoke, six dataflow replacements, and first-batch regression records.
- This audit did not call Tushare APIs, run multi-agent workflows, or invoke any LLM workflow.

## Commit Chain

| Commit | Message | Modification scope | Touches business code | Notes |
|---|---|---|---|---|
| `fd16d00` | `feat: add tushare client foundation` | `.env.example`, `.gitignore`, `tradingagents/dataflows/tushare_client.py` | Yes, new dataflow client foundation only | Adds token lookup through environment variables, short error normalization, optional JSON cache, and ignore rules for local cache/config. `.env.example` contains placeholders only. |
| `1003192` | `test: add tushare first batch live smoke results` | First-batch live smoke script and result docs | No | Records minimal live interface availability for `stock_basic`, `daily_basic`, `balancesheet`, `cashflow`, `income`, `report_rc`, `moneyflow`, and `moneyflow_dc`. |
| `41017c3` | `feat: replace financial statements with tushare` | `tradingagents/dataflows/a_stock.py`, `scripts/recovery/smoke_tushare_financials.py` | Yes, `a_stock.py` only | Replaces balance sheet, cashflow, and income statement functions with Tushare `balancesheet`, `cashflow`, and `income`. |
| `0d2f0ab` | `feat: replace fundamentals with tushare basics` | `tradingagents/dataflows/a_stock.py`, `scripts/recovery/smoke_tushare_fundamentals.py` | Yes, `a_stock.py` only | Replaces `get_fundamentals` with Tushare `daily_basic` plus `stock_basic`. |
| `4a2a6f3` | `feat: replace fund flow with tushare moneyflow` | `tradingagents/dataflows/a_stock.py`, `scripts/recovery/smoke_tushare_fund_flow.py` | Yes, `a_stock.py` only | Replaces `get_fund_flow` with Tushare `moneyflow`, with `moneyflow_dc` fallback. Removes Eastmoney push2 realtime minute flow semantics from this function. |
| `baf5ec9` | `feat: replace profit forecast with tushare report_rc` | `tradingagents/dataflows/a_stock.py`, `scripts/recovery/smoke_tushare_profit_forecast.py` | Yes, `a_stock.py` only | Replaces `get_profit_forecast` with Tushare `report_rc` sell-side forecast aggregation. Does not use `forecast`, `express`, or `fina_indicator` as substitutes. |
| `e4f2073` | `test: add first batch tushare regression results` | First-batch regression script and result docs | No | Records total regression for 18 bottom-level dataflow calls; all passed. |

## Scope Audit

| Check | Result | Evidence / note |
|---|---|---|
| Business code limited to data source layer | Pass | Business code changes are limited to `tradingagents/dataflows/a_stock.py` and new `tradingagents/dataflows/tushare_client.py`. |
| `tradingagents/dataflows/interface.py` changed | No | No file in the audited range touches `interface.py`. |
| `agents / graph / cli / web` changed | No | No file in the audited range is under these directories. |
| Prompts changed | No | No prompt file is touched in the audited range. |
| Quality Gate changed | No | No quality gate file is touched in the audited range. |
| Bull/Bear debate logic changed | No | No analyst, researcher, debate, trader, risk, or manager workflow file is touched. |
| Dependency declarations changed | No | No `pyproject.toml`, `requirements.txt`, `setup.py`, or lock file changes in first-batch implementation commits. |
| `.env` / `.env.local` / local config committed | No | No tracked `.env` or `.env.local`; `config/local_tushare.toml` is ignored. `.env.example` is a placeholder template only. |
| Real token leakage risk | No evidence found | Scans found only variable names, placeholder text, and token presence markers such as `present` / `missing`; no token value was found. |
| Real cache committed | No | `.cache/tushare/` is ignored. No tracked cache output was found. |
| Raw HTML cache committed | No | `docs/recovery/tushare_pro_inventory/raw_html/` is ignored. No tracked raw HTML file was found. |
| Large raw data artifact committed | No evidence found | Added artifacts are smoke/regression scripts plus small Markdown/CSV result records. |
| Need additional `.gitignore` entries | Not currently | Existing ignore rules cover `.cache/tushare/`, `config/local_tushare.toml`, and recovery `raw_html/` / scrape summary files. |

## Function-Level Audit

### `get_balance_sheet`

- Current data source: Tushare.
- Main API: `balancesheet`.
- Fallback API: none.
- As-of policy: filters `ann_date <= curr_date`; `end_date` is treated only as report period.
- Future-data guard: yes, through `ann_date` filtering.
- Frequency policy: `annual` keeps `end_date` ending `1231`; `quarterly` keeps `0331`, `0630`, `0930`, and `1231` cumulative report periods without single-quarter conversion.
- Short errors: returns short `technical_error` or `no_data` headers; no traceback or raw HTML output.
- Old source retained: not as the active implementation for this function.
- Business semantic risk: `report_type_filter=unverified`; first batch does not hard-code a consolidated-report code until the code is verified.
- Passed tests: financial smoke test and first-batch regression cases for `600519` quarterly and annual.
- Follow-up: verify `report_type` / `comp_type` semantics in a later batch if consolidated-only filtering must be enforced beyond header disclosure.

### `get_cashflow`

- Current data source: Tushare.
- Main API: `cashflow`.
- Fallback API: none.
- As-of policy: filters `ann_date <= curr_date`; `end_date` is treated only as report period.
- Future-data guard: yes, through `ann_date` filtering.
- Frequency policy: `annual` keeps `1231`; `quarterly` keeps cumulative quarter-end report periods.
- Short errors: returns short `technical_error` or `no_data` headers.
- Old source retained: not as the active implementation for this function.
- Business semantic risk: same first-batch `report_type_filter=unverified` limitation as the other statements.
- Passed tests: financial smoke test and first-batch regression cases for `600519` quarterly and `300750` annual.
- Follow-up: later verify consolidated-report filtering code if required.

### `get_income_statement`

- Current data source: Tushare.
- Main API: `income`.
- Fallback API: none.
- As-of policy: filters `ann_date <= curr_date`; `end_date` is treated only as report period.
- Future-data guard: yes, through `ann_date` filtering.
- Frequency policy: `annual` keeps `1231`; `quarterly` keeps cumulative quarter-end report periods.
- Short errors: returns short `technical_error` or `no_data` headers.
- Old source retained: not as the active implementation for this function.
- Business semantic risk: same first-batch `report_type_filter=unverified` limitation as the other statements.
- Passed tests: financial smoke test and first-batch regression cases for `600519` quarterly and `300750` annual.
- Follow-up: later verify consolidated-report filtering code if required.

### `get_fundamentals`

- Current data source: Tushare `daily_basic` plus `stock_basic`.
- Main APIs: `daily_basic`, `stock_basic`.
- Fallback API: none; partial output is allowed if only one source succeeds.
- As-of policy: `daily_basic.trade_date <= curr_date`; current implementation looks back up to 10 natural days for the latest available daily basic row.
- Future-data guard: yes, because it queries from `curr_date` backward and outputs the returned `trade_date`.
- Short errors: returns short `technical_error` or `no_data`; partial failures are marked `partial_data` with `missing_source` and `empty_reason`.
- Old source retained: not as the active implementation for this function.
- Business semantic risk: explicitly `realtime=false`; first batch intentionally does not include `stock_company`, `fina_indicator`, `dividend`, or `adj_factor`.
- Passed tests: fundamentals smoke test and first-batch regression cases for `600519`, `300750`, `300450`, and `688981`.
- Follow-up: second batch can add company profile, historical financial indicators, and dividend fields if needed, but should keep them semantically separate from this first-batch daily valuation snapshot.

### `get_fund_flow`

- Current data source: Tushare individual-stock daily fund flow.
- Main API: `moneyflow`.
- Fallback API: `moneyflow_dc`.
- As-of policy: `trade_date <= curr_date`; latest mode checks up to 10 natural days backward, and history mode queries a bounded prior window then keeps recent rows.
- Future-data guard: yes, through `trade_date` filtering.
- Short errors: returns short `technical_error` or `no_data`; fallback success is marked `partial_data` with `fallback=moneyflow_dc` and `net_only=true`.
- Old source retained: Eastmoney push2 realtime minute-flow path is no longer active for this function.
- Business semantic risk: output is daily individual-stock fund flow only; not northbound flow and not market-wide flow. Summary is weak data direction only, not an investment recommendation.
- Passed tests: fund-flow smoke test and first-batch regression cases for `300750`, `600519`, `300450`, and `688981`.
- Follow-up: second batch can evaluate `moneyflow_ths`, but it should not be mixed with northbound or market-level flow semantics.

### `get_profit_forecast`

- Current data source: Tushare sell-side research forecast.
- Main API: `report_rc`.
- Fallback API: none; the old Tonghuashun fallback is not retained.
- As-of policy: `report_date <= curr_date`; default window is 365 days, expanded to 730 days only when no coverage exists and marked `stale_forecast_window=true`.
- Future-data guard: yes, through `report_date` filtering.
- Short errors: returns short `technical_error` or `no_coverage`; no traceback, raw HTML, or long `read_html` exception is returned.
- Old source retained: not for this function.
- Business semantic risk: low institution coverage is marked `low_coverage=true`; this is sell-side forecast aggregation, not company guidance, earnings preview, earnings flash, or historical financial indicators.
- Passed tests: profit-forecast smoke test and first-batch regression cases for `600519`, `300750`, `300450`, and `688981`.
- Follow-up: monitor `report_rc` coverage and permissions; if later adding company forecast / express / historical financial indicators, expose them through separate semantics rather than replacing this function.

## Regression Evidence

- Regression document: `docs/recovery/tushare_pro_inventory/TUSHARE_PRO_FIRST_BATCH_REGRESSION_RESULT.md`.
- Regression result: `passed` with 18 / 18 bottom-level dataflow cases passing.
- Regression scope: only the six first-batch dataflow functions; no multi-agent run and no LLM workflow.
- Regression safety checks reported no future-date leakage, no HTML, no traceback, no token value, no proxy stack, no oversized error text, and no first-batch business semantic violations.

## Audit Conclusion

The first Tushare replacement batch is scoped correctly to the data source layer. The implementation does not modify `interface.py`, prompts, Quality Gate, Bull/Bear debate logic, or agent orchestration. Sensitive runtime material is handled through environment variables and ignored local cache/config paths. The known remaining issues are business-scope follow-ups rather than first-batch blockers: consolidated-report code verification for financial statements, richer fundamentals expansion, possible fund-flow source comparison, and broader forecast coverage handling.
