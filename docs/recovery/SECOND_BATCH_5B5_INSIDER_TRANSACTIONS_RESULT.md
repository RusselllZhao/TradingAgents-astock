# Second Batch 5B-5 Insider Transactions Result

## 1. Scope Changed

This stage changed only the data-source implementation for:

- `tradingagents/dataflows/a_stock.py::get_insider_transactions`

The compatible function name is retained, but the returned contract and body now
declare the actual A-share semantics: shareholder/F10 and holder-change data.

New bottom-level smoke test:

- `scripts/recovery/run_insider_transactions_contract_smoke.py`

## 2. Scope Not Changed

This stage did not modify:

- Agent prompts;
- Bull/Bear debate logic;
- Quality Gate;
- trading rules;
- `agents/`, `graph/`, `cli/`, or `web/`;
- `tradingagents/dataflows/interface.py`;
- `get_global_news`, `get_news`, `get_industry_comparison`, or other P1/P2
  functions.

No Agent, multi-Agent workflow, or LLM call was run.

## 3. Data Source Replacement

Previous source:

- mootdx F10 raw `股东研究` text.

New Tushare sources:

- `stk_holdertrade` for important shareholder increase/decrease records;
- `stk_holdernumber` for shareholder count;
- `top10_holders` for top ten shareholders;
- `top10_floatholders` for top ten floating shareholders.

This stage intentionally did not include:

- `stk_managers`;
- `stk_rewards`.

Those management-related datasets can be considered later only if their output
sections and contract semantics are explicitly designed.

## 4. Final Semantics

`get_insider_transactions` now declares the following contract semantics:

| Field | Value |
| --- | --- |
| `source` | `Tushare stk_holdertrade + top10_holders + top10_floatholders + stk_holdernumber` |
| `data_type` | `shareholder_f10` |
| `query_target` | `stock` |
| `coverage` | `individual_stock` |
| `fallback` | `none` |
| `unit` | `shares; percent; holder_num households; other fields raw Tushare` |

The header also states that the compatible function name is retained and that
the output is A-share shareholder/F10 and holder-change data, not US-style
insider transaction data.

## 5. Output Contracts

### Normal

When one or more Tushare shareholder sections return rows:

- `status: ok`
- `source`: Tushare shareholder APIs listed above
- `data_type: shareholder_f10`
- `query_target: stock`
- `coverage: individual_stock`
- `raw_error_suppressed: false`

The body is split into sections such as:

- `## Important Shareholder Increase / Decrease Records`
- `## Shareholder Count`
- `## Top 10 Shareholders`
- `## Top 10 Floating Shareholders`

### Partial Data

When at least one section returns rows but one or more Tushare shareholder APIs
fail:

- `status: partial_data`
- successful sections are still emitted;
- unavailable APIs are listed only by API name in `notes`;
- raw technical details remain suppressed.

### Empty

When all queried shareholder APIs are callable but return no rows:

- `status: empty`
- `empty_reason: no_coverage`
- `coverage: individual_stock`
- `raw_error_suppressed: false`

The body is a short neutral sentence.

### Invalid Input

When the input cannot be resolved to a six-digit A-share code:

- `status: invalid_input`
- `empty_reason: invalid_or_unresolved_ticker`
- `coverage: symbol_unresolved`
- `raw_error_suppressed: false`

The function does not return generic shareholder rows.

### Technical Error

When all required Tushare access fails or parsing raises an exception:

- `status: technical_error`
- `error_type`: classified by the shared data-source error classifier
- `raw_error_suppressed: true`

The Agent-visible body is limited to:

```text
Data source request failed; raw technical details suppressed.
```

Raw exceptions, HTML, traceback text, proxy stacks, and long network errors are
not included in the Agent-visible output.

## 6. Semantic Correction Check

This stage keeps the function name for compatibility but no longer claims to
return US-style insider transaction data. The visible contract uses
`data_type=shareholder_f10`, and the body title is:

```text
A-share Shareholder / F10 Data
```

No investment-directional interpretation is attached to shareholder changes,
shareholder count, top shareholders, or floating-shareholder rows.

## 7. Smoke Test

Command:

```bash
.venv/bin/python scripts/recovery/run_insider_transactions_contract_smoke.py
```

Result:

```text
TUSHARE_TOKEN=present
300450: PASS status=ok len=3108 note=ok
600519: PASS status=ok len=3512 note=ok
688981: PASS status=ok len=3481 note=ok
BADCODE: PASS status=invalid_input len=649 note=ok
SUMMARY: 4/4 PASS
```

The smoke test validated:

- output type is `str`;
- `# Data Source Contract` is present;
- required header fields are present;
- `data_type=shareholder_f10`;
- `query_target=stock`;
- normal cases use `coverage=individual_stock`;
- invalid input uses `coverage=symbol_unresolved`;
- successful output includes shareholder/F10 sections;
- invalid input does not return a shareholder table.

## 8. Raw Error and Sensitive Output Check

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

## 9. String Compatibility

The function still returns a plain string. The only consumption-side change is
that the returned string now starts with the standard Data Source Contract
header.

## 10. Prompt / Bull-Bear / Quality Gate / Agent Check

This stage did not modify prompts, Bull/Bear debate logic, Quality Gate,
trading rules, Agent orchestration, or tool routing.

## 11. Next Step

The planned next batch is `5B-6`: `get_global_news`.

Before changing `get_global_news`, keep the same boundaries:

- do not use stock-specific news semantics for global news;
- keep global / market / macro scope explicit;
- separate Tushare `major_news` from any existing CLS or Eastmoney 7x24 sources
  if a hybrid output is used;
- keep empty, stale, fallback, and technical-error states explicit.
