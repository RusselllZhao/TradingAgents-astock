# Minimal Agent Regression Result for 300450

- Stage: 4C-2
- Run time: 2026-07-07 21:53:42
- Target ticker: `300450`
- Target company: `先导智能`
- Branch: `recovery/data-source-only`
- Start HEAD: `e2a8c55`
- Result: `passed`
- This document evaluates data-source consumption and contamination risk only. It is not an investment view on `300450`.

## Actual Command

```bash
.venv/bin/python scripts/recovery/run_min_agent_regression_300450.py
```

## Actual Configuration

| Item | Value |
|---|---|
| LLM provider | `deepseek` |
| Quick model | `deepseek-chat` |
| Deep model | `deepseek-chat` |
| Selected analysts | `fundamentals`, `hot_money` |
| Ticker count | 1 |
| Ticker | `300450` |
| Trade date | `2026-07-07` |
| `max_debate_rounds` | `1` |
| `max_risk_discuss_rounds` | `0` |
| `checkpoint_enabled` | `False` |
| `output_language` | `Chinese` |
| Data vendors | all relevant categories set to `a_stock` |
| Runtime output root | `.cache/recovery/min_agent_regression_300450/20260707_215342` |

## Environment Summary

Presence checks only; no key or token value was printed or written.

| Variable | Status |
|---|---|
| `TUSHARE_TOKEN` | present |
| `DEEPSEEK_API_KEY` | present |
| Other checked LLM keys | missing |

## Run Outcome

| Check | Result |
|---|---|
| Agent workflow completed | yes |
| Duration | 163.085 seconds |
| LLM called | yes, DeepSeek |
| Tushare called | yes |
| Error | none |
| Raw runtime output root | `.cache/recovery/min_agent_regression_300450/20260707_215342` |
| Structured summary | `.cache/recovery/min_agent_regression_300450/20260707_215342/run_summary.json` |
| Agent report sections | `.cache/recovery/min_agent_regression_300450/20260707_215342/agent_report_sections.md` |
| Graph full-state log | `.cache/recovery/min_agent_regression_300450/20260707_215342/graph_results/300450/TradingAgentsStrategy_logs/full_states_log_2026-07-07.json` |

Runtime artifacts are under `.cache/` and are not intended for git commit.

## Data Function Calls

The run recorded 15 data tool calls. The six first-batch Tushare replacement functions were all invoked.

| Function | Called | First-batch replacement | Result |
|---|---:|---:|---|
| `get_balance_sheet` | yes | yes | ok, Tushare header present |
| `get_cashflow` | yes | yes | ok, Tushare header present |
| `get_income_statement` | yes | yes | ok, Tushare header present |
| `get_fundamentals` | yes | yes | ok, Tushare header present |
| `get_fund_flow` | yes | yes | ok, Tushare `moneyflow` header present |
| `get_profit_forecast` | yes | yes | ok, Tushare `report_rc` sell-side header present |
| `get_industry_comparison` | yes | no | returned Eastmoney proxy-style error text twice |
| `get_hot_stocks` | yes | no | ok |
| `get_concept_blocks` | yes | no | ok |
| `get_dragon_tiger_board` | yes | no | ok empty-event text |
| `get_northbound_flow` | yes | no | ok |

The companion CSV contains one row per observed tool call:

- `docs/recovery/tushare_pro_inventory/MIN_AGENT_REGRESSION_RESULT_300450.csv`

## First-Batch Safety Checks

| Check | Result | Evidence |
|---|---|---|
| HTML entered first-batch tool output | no | First-batch tool heads did not contain `<html` / `<!doctype`. |
| HTML entered final report | no | Direct report scan found no HTML markers. |
| Traceback entered final report | no | Direct report scan found no traceback marker. |
| Token or API key value entered outputs | no evidence | Runtime safety scan checked present env values against report/tool heads. |
| Eastmoney proxy stack in first-batch functions | no | `get_fund_flow` used Tushare `moneyflow`; no push2 proxy text in first-batch output. |
| Bare `No data found` in first-batch functions | no | First-batch outputs had `status: ok` and Tushare source headers. |
| `technical_error` / `no_data` / `no_coverage` misread as fact | no evidence | These status strings did not appear in the final report. |
| `get_profit_forecast` HTML / `read_html` exception | no | Tool output used `Tushare report_rc sell-side forecast aggregation`. |
| `get_profit_forecast` semantic confusion | no evidence | Final report described analyst / sell-side / consensus forecast semantics, not company guidance. |
| `get_fund_flow` direct bullish/bearish source signal | no | Tool output was daily individual-stock Tushare flow; no old realtime push2 signal text. |

## Observed Non-First-Batch Risk

`get_industry_comparison` returned a short ordinary text result containing an Eastmoney `HTTPSConnectionPool` / proxy-style failure. This function is not part of the first Tushare replacement batch and was already in the second-batch business/contract backlog.

Observed behavior:

- The proxy-style text appeared in the tool-call record.
- It did not appear in the final report sections.
- It should remain a Stage 5 / second-batch item rather than a reason to change first-batch Tushare functions.

## Key Output Summary

The workflow produced:

- a fundamentals analyst report;
- a hot-money / capital-flow report;
- a Bull/Bear research debate;
- a research manager synthesis;
- a trader section;
- a risk / portfolio manager section.

The reports consumed the first-batch Tushare-backed data successfully. This result document intentionally does not evaluate or endorse the generated investment stance.

## Agent Pollution Risk

No first-batch data-source pollution was observed in the final report. Specifically:

- no first-batch HTML, traceback, token, or proxy stack appeared;
- no first-batch bare `No data found` text appeared;
- no old Tonghuashun `read_html` error appeared;
- no old Eastmoney push2 fund-flow proxy stack appeared;
- no evidence was found that `technical_error`, `no_data`, `no_coverage`, or `partial_data` was interpreted as factual evidence.

Residual risk remains outside the first-batch scope:

- second-batch tools can still return ordinary natural-language error text;
- market-level / sector-level signals can still be woven into an individual-stock argument by the existing Agent prompts;
- the Agent debate/trading layers can still produce strong trading language because prompts and Bull/Bear logic were intentionally not changed.

## Failure Reproduction

Not applicable. The minimal regression run succeeded.
