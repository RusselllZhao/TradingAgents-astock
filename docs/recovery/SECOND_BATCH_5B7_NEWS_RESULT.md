# Second Batch 5B-7 Stock News Result

## 1. Scope Changed

This stage changed only the data-source implementation for:

- `tradingagents/dataflows/a_stock.py::get_news`

The function now keeps the existing stock-specific Eastmoney / Sina path and
returns a string-compatible Data Source Contract header before the Markdown
body.

New bottom-level smoke test:

- `scripts/recovery/run_news_contract_smoke.py`

## 2. Scope Not Changed

This stage did not modify:

- Agent prompts;
- Bull/Bear debate logic;
- Quality Gate;
- trading rules;
- `agents/`, `graph/`, `cli/`, or `web/`;
- `tradingagents/dataflows/interface.py`;
- `get_global_news`, `get_industry_comparison`, or other functions.

No Agent, multi-Agent workflow, LLM call, or Tushare news call was run.

## 3. Data Source Governance

Previous source:

- Eastmoney stock-news search;
- Sina stock-news page as fallback.

Current source:

- Eastmoney stock-news search remains the primary stock-specific source;
- Sina stock-news page remains the fallback source;
- source failures are classified and suppressed from Agent-visible output.

This stage does not use Tushare `major_news`, `news`, `anns_d`, or `cctv_news`.

## 4. Why Tushare major_news Is Not Used

The 8000-point Tushare probe found:

- `news`: unavailable in the current permission state;
- `anns_d`: unavailable and announcement-like rather than ordinary stock news;
- `cctv_news`: unavailable and macro/news-like;
- `major_news`: available but market/global, not symbol-specific.

Therefore `major_news` remains limited to `get_global_news` and is not used in
`get_news`.

## 5. Final Semantics

`get_news` now declares the following contract semantics:

| Field | Value |
| --- | --- |
| `source` | `Eastmoney stock news + Sina fallback` |
| `data_type` | `news` |
| `query_target` | `stock` |
| `coverage` | `individual_stock` |
| `fallback` | `none` or `Eastmoney->Sina` |
| `unit` | `news_items` |

The function remains stock-specific and uses `symbol=<six digit A-share code>`.

## 6. Output Contracts

### Normal

When Eastmoney returns stock-specific rows within the requested date window:

- `status: ok`
- `fallback: none`
- `data_type: news`
- `query_target: stock`
- `coverage: individual_stock`
- `raw_error_suppressed: false`

The body includes a Markdown table with publication time, source, title,
summary, and URL.

### Fallback Partial Data

When Eastmoney is unavailable or empty/filtered and Sina returns stock-specific
rows:

- `status: partial_data`
- `fallback: Eastmoney->Sina`
- `notes` states the fallback reason and source used;
- raw Eastmoney errors are suppressed when the primary source failed
  technically.

### Empty

When both sources are callable but no rows remain for the requested stock and
date window:

- `status: empty`
- `empty_reason: source_empty` or `filtered_out`
- `fallback: Eastmoney->Sina`
- `raw_error_suppressed: false`

The body is a short neutral sentence.

### Invalid Input

When the input cannot be resolved to a six-digit A-share code:

- `status: invalid_input`
- `empty_reason: invalid_or_unresolved_ticker`
- `coverage: symbol_unresolved`
- `raw_error_suppressed: false`

The function does not call generic news sources and does not return a news
table.

### Technical Error

When Eastmoney and Sina both fail technically:

- `status: technical_error`
- `error_type`: classified by source error type or `mixed_source_error`
- `raw_error_suppressed: true`

The Agent-visible body is limited to:

```text
Data source request failed; raw technical details suppressed.
```

## 7. Generic News Guard

The implementation does not return market-wide, macro, announcement, or other
unrelated feeds as stock-specific news. Invalid ticker input returns
`invalid_input` with `coverage=symbol_unresolved`.

## 8. Smoke Test

Command:

```bash
.venv/bin/python scripts/recovery/run_news_contract_smoke.py
```

Result:

```text
300450: PASS status=ok len=5836 note=ok
600519: PASS status=ok len=5521 note=ok
688981: PASS status=ok len=5812 note=ok
BADCODE: PASS status=invalid_input len=474 note=ok
SUMMARY: 4/4 PASS
```

The smoke test validated:

- output type is `str`;
- `# Data Source Contract` is present;
- required header fields are present;
- `source=Eastmoney stock news + Sina fallback`;
- `data_type=news`;
- `query_target=stock`;
- normal cases use `coverage=individual_stock`;
- invalid input uses `coverage=symbol_unresolved`;
- successful output includes stock-news publication time, source, and title;
- invalid input does not return generic news.

## 9. Raw Error and Sensitive Output Check

Smoke test did not find Agent-visible:

- raw HTML;
- traceback or `Traceback`;
- `HTTPSConnectionPool`;
- `ProxyError`;
- proxy stack text;
- raw exception text;
- anti-scraping page text;
- overlong technical error output;
- token value leaks.

## 10. String Compatibility

The function still returns a plain string. The only consumption-side change is
that the returned string now starts with the standard Data Source Contract
header.

## 11. Prompt / Bull-Bear / Quality Gate / Agent Check

This stage did not modify prompts, Bull/Bear debate logic, Quality Gate,
trading rules, Agent orchestration, or tool routing.

## 12. Next Step

With the second-batch named P1/P2 functions now contract-governed, the next
step is either:

- `get_industry_comparison` accuracy upgrade, if the tool should move from
  market-wide industry ranking toward target-stock industry peer comparison;
- or a second-batch closeout regression that reruns bottom-level smoke tests
  across all changed functions before any Agent-level regression.
