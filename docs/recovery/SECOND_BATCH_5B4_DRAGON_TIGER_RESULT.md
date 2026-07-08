# Second Batch 5B-4 Dragon-Tiger Board Result

## 1. Scope Changed

This stage changed only the data-source implementation for:

- `tradingagents/dataflows/a_stock.py::get_dragon_tiger_board`

The function now uses Tushare Pro `top_list` as the primary dragon-tiger event
source and Tushare Pro `top_inst` as a separated seat/institution detail
supplement when matched events exist.

New bottom-level smoke test:

- `scripts/recovery/run_dragon_tiger_board_contract_smoke.py`

## 2. Scope Not Changed

This stage did not modify:

- Agent prompts;
- Bull/Bear debate logic;
- Quality Gate;
- trading rules;
- `agents/`, `graph/`, `cli/`, or `web/`;
- `tradingagents/dataflows/interface.py`;
- `get_insider_transactions`, `get_global_news`, `get_news`,
  `get_industry_comparison`, or other P1/P2 functions.

No Agent, multi-Agent workflow, or LLM call was run.

## 3. Data Source Replacement

Previous source:

- Eastmoney datacenter daily billboard list and seat-detail endpoints.

New source:

- Tushare Pro `top_list` for dragon-tiger event rows;
- Tushare Pro `top_inst` for clearly separated seat/institution details.

`top_list` does not support a validated `start_date` / `end_date` range call in
this repo's Tushare client probe, so the implementation queries each weekday in
the requested lookback window and filters rows to the requested `ts_code`.

## 4. Final Semantics

`get_dragon_tiger_board` now declares the following contract semantics:

| Field | Value |
| --- | --- |
| `source` | `Tushare top_list + top_inst` |
| `data_type` | `dragon_tiger_event` |
| `query_target` | `event` |
| `coverage` | `event_lookup` |
| `fallback` | `none` |
| `unit` | `CNY 10k for amount fields where provided by Tushare; ratio fields percent` |

The output remains a plain string. The body contains separate sections:

- `## Event List` for `top_list` rows;
- `## Seat / Institution Details` for `top_inst` rows or a short unavailable
  note when event rows exist but details are unavailable.

## 5. Output Contracts

### Normal

When `top_list` returns event rows for the requested stock:

- `status: ok`
- `source: Tushare top_list + top_inst`
- `data_type: dragon_tiger_event`
- `query_target: event`
- `coverage: event_lookup`
- `raw_error_suppressed: false`

The body includes an event-list table. If matching `top_inst` rows are also
available, they appear only in the separate seat/institution detail section.

### No Event

When the requested stock has no dragon-tiger event in the query window:

- `status: no_event`
- `empty_reason: no_event`
- `coverage: event_lookup`
- `raw_error_suppressed: false`

The body is a short neutral sentence:

```text
No dragon-tiger board event found for the requested symbol and lookback window.
```

No investment interpretation is attached.

### Partial Data

When `top_list` returns event rows but `top_inst` details are empty or partially
unavailable:

- `status: partial_data`
- event list still appears;
- seat/institution details are placed in a separate section with an unavailable
  note when needed;
- `raw_error_suppressed: false`.

### Invalid Input

When the input cannot be resolved to a six-digit A-share code:

- `status: invalid_input`
- `empty_reason: invalid_or_unresolved_ticker`
- `coverage: symbol_unresolved`
- `raw_error_suppressed: false`

The function does not return generic dragon-tiger market rows.

### Technical Error

When Tushare or parsing fails:

- `status: technical_error`
- `error_type`: classified by the shared data-source error classifier
- `raw_error_suppressed: true`

The Agent-visible body is limited to:

```text
Data source request failed; raw technical details suppressed.
```

Raw exceptions, HTML, traceback text, proxy stacks, and long network errors are
not included in the Agent-visible output.

## 6. Event and Detail Separation

The event list and seat/institution details are not mixed into one table:

- `top_list` rows are emitted under `## Event List`;
- `top_inst` rows are emitted under `## Seat / Institution Details`;
- missing seat details can produce `partial_data` without hiding the event
  rows.

## 7. No-Event Interpretation Check

The implementation treats no event as an event-query result only. It does not
describe not appearing on the dragon-tiger board as positive, negative,
supportive, adverse, or otherwise investment-directional.

## 8. Smoke Test

Command:

```bash
.venv/bin/python scripts/recovery/run_dragon_tiger_board_contract_smoke.py
```

Result:

```text
TUSHARE_TOKEN=present
300450: PASS status=no_event len=536 note=ok
600519: PASS status=no_event len=536 note=ok
688981: PASS status=no_event len=536 note=ok
BADCODE: PASS status=invalid_input len=551 note=ok
SUMMARY: 4/4 PASS
```

The smoke test validated:

- output type is `str`;
- `# Data Source Contract` is present;
- required header fields are present;
- `source=Tushare top_list + top_inst`;
- `data_type=dragon_tiger_event`;
- `query_target=event`;
- normal cases use `coverage=event_lookup`;
- invalid input uses `coverage=symbol_unresolved`;
- no-event cases use `status=no_event` and `empty_reason=no_event`;
- invalid input does not return a generic event table.

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

The planned next batch is `5B-5`: `get_insider_transactions`.

Before changing `get_insider_transactions`, confirm the semantic correction
boundary:

- current function name implies insider transactions;
- A-share fit is closer to shareholder changes and shareholder/F10 data;
- likely Tushare candidates include `stk_holdertrade`, `top10_holders`,
  `top10_floatholders`, `stk_holdernumber`, `stk_managers`, and `stk_rewards`;
- do not mix shareholder roster, shareholder-count, and increase/decrease
  events without clear sections and contract fields.
