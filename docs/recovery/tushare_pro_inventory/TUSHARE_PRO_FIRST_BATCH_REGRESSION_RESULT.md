# Tushare Pro First Batch Regression Result

- Test time: 2026-07-07 21:04:58
- Commit: `baf5ec9`
- TUSHARE_TOKEN: `present`
- Overall: `passed` (18/18 passed)
- Scope: bottom-level dataflow functions only; no LLM, no multi-agent workflow.

## Tested Functions

- `get_balance_sheet`
- `get_cashflow`
- `get_income_statement`
- `get_fundamentals`
- `get_fund_flow`
- `get_profit_forecast`

## Test Cases

- `get_balance_sheet('600519', 'quarterly', '2026-07-07')`
- `get_balance_sheet('600519', 'annual', '2026-07-07')`
- `get_cashflow('600519', 'quarterly', '2026-07-07')`
- `get_cashflow('300750', 'annual', '2026-07-07')`
- `get_income_statement('600519', 'quarterly', '2026-07-07')`
- `get_income_statement('300750', 'annual', '2026-07-07')`
- `get_fundamentals('600519', '2026-07-07')`
- `get_fundamentals('300750', '2026-07-07')`
- `get_fundamentals('300450', '2026-07-07')`
- `get_fundamentals('688981', '2026-07-07')`
- `get_fund_flow('300750', '2026-07-07', include_history=True)`
- `get_fund_flow('600519', '2026-07-07', include_history=False)`
- `get_fund_flow('300450', '2026-07-07', include_history=True)`
- `get_fund_flow('688981', '2026-07-07', include_history=False)`
- `get_profit_forecast('600519', '2026-07-07')`
- `get_profit_forecast('300750', '2026-07-07')`
- `get_profit_forecast('300450', '2026-07-07')`
- `get_profit_forecast('688981', '2026-07-07')`

## Results

| Function | Input | Status | Length | Source/API | Date | Safety | Semantics | Pass | Notes |
|---|---|---:|---:|---|---|---|---|---|---|
| get_balance_sheet | `get_balance_sheet('600519', 'quarterly', '2026-07-07')` | ok | 1695 | ok | ok | ok | ok | yes | ok |
| get_balance_sheet | `get_balance_sheet('600519', 'annual', '2026-07-07')` | ok | 1666 | ok | ok | ok | ok | yes | ok |
| get_cashflow | `get_cashflow('600519', 'quarterly', '2026-07-07')` | ok | 1523 | ok | ok | ok | ok | yes | ok |
| get_cashflow | `get_cashflow('300750', 'annual', '2026-07-07')` | ok | 1571 | ok | ok | ok | ok | yes | ok |
| get_income_statement | `get_income_statement('600519', 'quarterly', '2026-07-07')` | ok | 1507 | ok | ok | ok | ok | yes | ok |
| get_income_statement | `get_income_statement('300750', 'annual', '2026-07-07')` | ok | 1475 | ok | ok | ok | ok | yes | ok |
| get_fundamentals | `get_fundamentals('600519', '2026-07-07')` | ok | 617 | ok | ok | ok | ok | yes | ok |
| get_fundamentals | `get_fundamentals('300750', '2026-07-07')` | ok | 622 | ok | ok | ok | ok | yes | ok |
| get_fundamentals | `get_fundamentals('300450', '2026-07-07')` | ok | 612 | ok | ok | ok | ok | yes | ok |
| get_fundamentals | `get_fundamentals('688981', '2026-07-07')` | ok | 621 | ok | ok | ok | ok | yes | ok |
| get_fund_flow | `get_fund_flow('300750', '2026-07-07', include_history=True)` | ok | 5351 | ok | ok | ok | ok | yes | ok |
| get_fund_flow | `get_fund_flow('600519', '2026-07-07', include_history=False)` | ok | 993 | ok | ok | ok | ok | yes | ok |
| get_fund_flow | `get_fund_flow('300450', '2026-07-07', include_history=True)` | ok | 5242 | ok | ok | ok | ok | yes | ok |
| get_fund_flow | `get_fund_flow('688981', '2026-07-07', include_history=False)` | ok | 1019 | ok | ok | ok | ok | yes | ok |
| get_profit_forecast | `get_profit_forecast('600519', '2026-07-07')` | ok | 1858 | ok | ok | ok | ok | yes | ok |
| get_profit_forecast | `get_profit_forecast('300750', '2026-07-07')` | ok | 1781 | ok | ok | ok | ok | yes | ok |
| get_profit_forecast | `get_profit_forecast('300450', '2026-07-07')` | ok | 1662 | ok | ok | ok | ok | yes | ok |
| get_profit_forecast | `get_profit_forecast('688981', '2026-07-07')` | ok | 1498 | ok | ok | ok | ok | yes | ok |

## Conclusion

- Overall result: passed.
- No future-date leakage was detected.
- No HTML, traceback, token value, proxy stack, or oversized error text was detected.
- No first-batch business semantic violations were detected.
