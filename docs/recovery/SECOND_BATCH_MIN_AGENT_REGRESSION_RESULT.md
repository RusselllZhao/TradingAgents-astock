# SECOND_BATCH_MIN_AGENT_REGRESSION_RESULT

- Stage: `5C-1` and `5C-2`
- Date: 2026-07-08
- Branch: `recovery/data-source-only`
- Baseline commit: `625ff37`
- Runner: `scripts/recovery/run_second_batch_min_agent_regression.py`
- Runtime output root: `.cache/recovery/second_batch_min_agent_regression/20260708_162555`
- Structured CSV: `docs/recovery/SECOND_BATCH_MIN_AGENT_REGRESSION_RESULT.csv`

This document evaluates data-source pollution and contract consumption behavior only. It is not an investment view on any tested stock.

## 1. Command

```bash
.venv/bin/python scripts/recovery/run_second_batch_min_agent_regression.py
```

## 2. Configuration

| Item | Value |
|---|---|
| LLM provider | `deepseek` |
| Quick model | `deepseek-chat` |
| Deep model | `deepseek-chat` |
| Selected analysts | `fundamentals`, `hot_money` |
| Trade date | `2026-07-07` |
| Ticker mode | sequential single-stock runs |
| `max_debate_rounds` | `1` |
| `max_risk_discuss_rounds` | `0` |
| `checkpoint_enabled` | `False` |
| Output language | Chinese |
| Raw runtime output | `.cache/recovery/second_batch_min_agent_regression/20260708_162555` |

Token/API key presence was checked only as present/missing.

| Variable | Status |
|---|---|
| `TUSHARE_TOKEN` | present |
| `DEEPSEEK_API_KEY` | present |

## 3. Run Summary

| Ticker | Company | Result | Elapsed seconds | Tool calls | LLM used | Tushare used | Final report |
|---|---|---:|---:|---:|---|---|---|
| `300450` | 先导智能 | passed | 149.614 | 12 | yes | yes | `.cache/recovery/second_batch_min_agent_regression/20260708_162555/300450/agent_report_sections.md` |
| `600519` | 贵州茅台 | passed | 179.187 | 16 | yes | yes | `.cache/recovery/second_batch_min_agent_regression/20260708_162555/600519/agent_report_sections.md` |
| `688981` | 中芯国际 | passed | 204.974 | 12 | yes | yes | `.cache/recovery/second_batch_min_agent_regression/20260708_162555/688981/agent_report_sections.md` |

All three minimal Agent regressions completed successfully.

## 4. Tool Call Summary

The minimal `fundamentals + hot_money` path called these tools for all three stocks:

- `get_balance_sheet`
- `get_cashflow`
- `get_concept_blocks`
- `get_dragon_tiger_board`
- `get_fund_flow`
- `get_fundamentals`
- `get_hot_stocks`
- `get_income_statement`
- `get_industry_comparison`
- `get_northbound_flow`
- `get_profit_forecast`

The configured minimal path did not call:

- `get_news`
- `get_global_news`
- `get_insider_transactions`

Second-batch tools reached in this minimal run:

| Tool | Observed status values | Notes |
|---|---|---|
| `get_industry_comparison` | `technical_error` | Eastmoney source failed, but output was contract-form short technical error with raw details suppressed. |
| `get_northbound_flow` | `ok` | Tushare `moneyflow_hsgt`, market-level flow. |
| `get_concept_blocks` | `ok` | Tushare `dc_concept_cons`, stock concept membership. |
| `get_hot_stocks` | `ok` | Tushare `ths_hot`, market-wide hot-stock list. |
| `get_dragon_tiger_board` | `no_event` | Tushare event lookup; no event in the queried window for tested symbols. |

## 5. Pollution Scan

Scanned tool-call heads and final report sections for:

- raw HTML / `<html` / `<!DOCTYPE html`;
- traceback / `Traceback`;
- `HTTPSConnectionPool`;
- `ProxyError`;
- proxy stack text;
- raw exception text;
- anti-scraping markers;
- oversized technical error text;
- real token/API key value;
- bare `No data found`;
- old `read_html` exception text.

Result:

| Ticker | Tool output scan | Final report scan | Result |
|---|---|---|---|
| `300450` | clean | clean | no raw data-source pollution observed |
| `600519` | clean | clean | no raw data-source pollution observed |
| `688981` | clean | clean | no raw data-source pollution observed |

No real token/API key value was found in the committed CSV or this document.

## 6. Directional / Prohibited Label Scan

Tool-call heads did not contain source-level English `bullish` / `bearish` wording.

One final report, `600519`, contains the English word `bullish` inside Agent-generated debate text. This is not source-level data output and is not a Data Source Contract regression. It is recorded because the scan includes final Agent reports.

No `confidence`, `conclusion_level`, or prohibited evidence-label terms were observed in tool-call heads or committed summaries.

## 7. Contract Consumption Review

| Ticker | Observed contract states | Final report behavior | Assessment |
|---|---|---|---|
| `300450` | `ok`, `technical_error`, `no_event` | `get_industry_comparison` technical failure appeared as a missing-data note, not raw stack. Dragon-tiger `no_event` was used in the investment narrative as low tour-capital / low catalyst context. | raw pollution controlled; Agent consumption risk remains for `no_event`. |
| `600519` | `ok`, `technical_error`, `no_event` | Dragon-tiger no-event was described as normal for a large-cap blue chip but also used to say no tour-capital speculation. | raw pollution controlled; mild `no_event` narrative use remains. |
| `688981` | `ok`, `technical_error`, `no_event` | Dragon-tiger no-event was treated mostly as neutral / non-tour-capital context. | raw pollution controlled; mild `no_event` narrative use remains. |

Industry comparison behavior:

- The tool returned `status: technical_error`, `data_type: industry_ranking`, `query_target: market`, and `coverage: market_wide`.
- Final reports did not include raw Eastmoney proxy/network text.
- Reports mentioned industry comparison data as missing or unavailable. This is acceptable as a missing-data note, but it confirms the known limitation that the function has not received the accuracy upgrade.

Market-wide data behavior:

- `get_northbound_flow` and `get_hot_stocks` are market-wide tools.
- Reports used these as market/hot-money context. No raw contract label misuse was observed.
- The Agent can still weave market-wide context into stock-specific reasoning, which is a consumption-layer behavior and not a source pollution failure.

## 8. Known Legacy / Deferred Issues

The following issues were marked but not executed or fixed in this stage:

| Issue | Stage 5C action |
|---|---|
| `get_industry_comparison` accuracy upgrade | marked only; no symbol-to-industry mapping or peer comparison implemented |
| Tushare stock-news permission issue | marked only; no `get_news` source replacement attempted |
| `get_global_news` hybrid `partial_data` behavior | marked only; no redesign attempted |

## 9. No-Change Confirmation

This stage did not modify:

- business code;
- `tradingagents/dataflows/a_stock.py`;
- `tradingagents/dataflows/interface.py`;
- Agent prompts;
- Bull/Bear debate logic;
- Quality Gate logic;
- trading recommendation rules;
- `tradingagents/agents/`;
- `tradingagents/graph/`;
- `cli`;
- `web`.

Runtime raw artifacts remain under `.cache/` and are not intended for commit.
