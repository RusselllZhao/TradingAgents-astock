# Second Batch 5B-2 Concept Blocks Result

## 1. Scope Changed

This stage changed only the data-source implementation for:

- `tradingagents/dataflows/a_stock.py::get_concept_blocks`

The function now uses Tushare Pro `dc_concept_cons` as the primary source for
stock-to-concept membership and returns a string-compatible Data Source
Contract header before the Markdown body.

New bottom-level smoke test:

- `scripts/recovery/run_concept_blocks_contract_smoke.py`

## 2. Scope Not Changed

This stage did not modify:

- Agent prompts;
- Bull/Bear debate logic;
- Quality Gate;
- trading rules;
- `agents/`, `graph/`, `cli/`, or `web/`;
- `tradingagents/dataflows/interface.py`;
- `get_hot_stocks`, `get_dragon_tiger_board`, `get_insider_transactions`,
  `get_global_news`, `get_news`, or other P1/P2 functions.

No Agent, multi-Agent workflow, or LLM call was run.

## 3. Data Source Replacement

Previous source:

- Baidu PAE related-block endpoint.

New source:

- Tushare Pro `dc_concept_cons`.

This first implementation is intentionally limited to stock-to-concept
membership:

- no `dc_index` board performance data;
- no `ths_member` supplemental membership data;
- no mixing of stock membership rows and concept board market performance.

## 4. Final Semantics

`get_concept_blocks` now declares the following contract semantics:

| Field | Value |
| --- | --- |
| `source` | `Tushare dc_concept_cons` |
| `data_type` | `concept_blocks` |
| `query_target` | `stock` |
| `coverage` | `individual_stock` |
| `fallback` | `none` |
| `unit` | `membership rows; hot_num is raw Tushare field` |

The output remains a plain string. The body keeps a Markdown table with
available `dc_concept_cons` fields such as:

- `ts_code`
- `trade_date`
- `name`
- `theme_code`
- `industry_code`
- `industry`
- `reason`
- `hot_num`

Fields are emitted only when returned by Tushare; no fields are fabricated.

## 5. Output Contracts

### Normal

When Tushare returns rows for the requested stock:

- `status: ok`
- `source: Tushare dc_concept_cons`
- `data_type: concept_blocks`
- `query_target: stock`
- `coverage: individual_stock`
- `raw_error_suppressed: false`

The body shows only the latest available `trade_date` rows within the query
window for the requested `ts_code`.

### Empty

When the requested stock is syntactically valid but Tushare returns no rows:

- `status: empty`
- `empty_reason: no_coverage`
- `coverage: individual_stock`
- `raw_error_suppressed: false`

The body is a short neutral sentence. It does not return a bare `No data found`
string and does not fall back to a generic concept list.

### Invalid Input

When the input cannot be resolved to a six-digit A-share code:

- `status: invalid_input`
- `empty_reason: invalid_or_unresolved_ticker`
- `coverage: symbol_unresolved`
- `raw_error_suppressed: false`

The function does not call a generic concept source and does not return
unrelated concept data.

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

## 6. Removed Source-Level Directional Text

The new implementation returns Tushare concept membership rows only. It does
not add source-level `bullish` or `bearish` wording, directional conclusions,
or debate guidance.

## 7. Smoke Test

Command:

```bash
.venv/bin/python scripts/recovery/run_concept_blocks_contract_smoke.py
```

Result:

```text
TUSHARE_TOKEN=present
300450: PASS status=ok len=1771 note=ok
600519: PASS status=ok len=947 note=ok
688981: PASS status=ok len=1012 note=ok
BADCODE: PASS status=invalid_input len=512 note=ok
SUMMARY: 4/4 PASS
```

The smoke test validated:

- output type is `str`;
- `# Data Source Contract` is present;
- required header fields are present;
- `data_type=concept_blocks`;
- `query_target=stock`;
- normal cases use `coverage=individual_stock`;
- invalid input uses `coverage=symbol_unresolved`;
- success outputs include `dc_concept_cons` fields;
- invalid input does not return a concept table.

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

The planned next batch is `5B-3`: `get_hot_stocks`.

Before changing `get_hot_stocks`, keep the same boundaries:

- use Tushare `ths_hot` only for hot-stock semantics;
- keep limit-up pools and limit-step data separate if they are introduced;
- do not mix hot-stock list semantics with unrelated market event data;
- keep contract status, scope, units, and technical-error suppression explicit.
