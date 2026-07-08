# SECOND_BATCH_5B1_NORTHBOUND_FLOW_RESULT

- Stage: `5B-1`
- Date: 2026-07-08
- Branch: `recovery/data-source-only`
- Scope: data-source-layer change for `get_northbound_flow` only.

## 1. Modification Scope

Changed files:

- `tradingagents/dataflows/a_stock.py`
- `scripts/recovery/run_northbound_flow_contract_smoke.py`

Added result document:

- `docs/recovery/SECOND_BATCH_5B1_NORTHBOUND_FLOW_RESULT.md`

Code changes in `a_stock.py`:

- Replaced the `get_northbound_flow` data path from direct THS hsgtApi plus local CSV snapshot cache to Tushare Pro `moneyflow_hsgt`.
- Added small northbound-flow-specific formatting helpers.
- Added a string-compatible `# Data Source Contract` header to `get_northbound_flow`.
- Minimally enhanced the existing data-source error classifier for Tushare permission/rate/upstream error strings.
- Disabled Tushare cache for this function call with `use_cache=False`.
- Removed source-level `bullish` / `bearish` wording from the function output.

## 2. Unchanged Scope

No changes were made to:

- Agent prompts.
- Bull/Bear debate logic.
- Quality Gate.
- Trading recommendation rules.
- `agents/`.
- `graph/`.
- `cli/`.
- `web/`.
- `tradingagents/dataflows/interface.py`.
- `get_concept_blocks`.
- `get_hot_stocks`.
- `get_dragon_tiger_board`.
- Other P1/P2 functions.

No LLM, Agent, or multi-Agent workflow was run.

## 3. Data Source Replacement

Previous source:

- Direct THS hsgtApi realtime endpoint.
- Local `northbound_daily.csv` runtime cache for history.

Current source:

- Tushare Pro `moneyflow_hsgt`.
- Queried by date window.
- No `hk_hold` supplement.
- No stock-level northbound holding data.
- No local `northbound_daily.csv` runtime cache write.

The function remains market-level. It does not claim individual-stock northbound flow or holding data.

## 4. Final Function Semantics

Current `get_northbound_flow` contract labels:

| Field | Value |
|---|---|
| `source` | `Tushare moneyflow_hsgt` |
| `data_type` | `northbound_flow` |
| `query_target` | `market` |
| `symbol` | `N/A` |
| `coverage` | `market_wide` |
| `fallback` | `none` |
| `unit` | `CNY million (Tushare moneyflow_hsgt raw fields)` |

The visible data body includes the Tushare fields:

- `trade_date`
- `hgt`
- `sgt`
- `north_money`
- `south_money`

`curr_date` is used as `as_of`. If the source's latest returned row is earlier than `curr_date`, the header uses `trade_date` for the actual latest data date.

## 5. Output Contracts

### Normal Success

- `status: ok`
- `empty_reason: none`
- `error_type: none`
- `raw_error_suppressed: false`
- Body contains a Markdown table of `moneyflow_hsgt` rows.

### Empty Result

- `status: empty`
- `empty_reason: source_empty`
- `raw_error_suppressed: false`
- Body contains a short neutral empty-result sentence.
- No bare `No data found` text is returned.

### Technical Error

- `status: technical_error`
- `error_type`: classified by the existing data-source error classifier.
- `raw_error_suppressed: true`
- Body contains only:

```text
Data source request failed; raw technical details suppressed.
```

Raw exceptions, HTML, traceback, proxy stack, and long network errors are not returned in the Agent-visible output.

## 6. Directional Wording

The previous implementation could emit source-level direction text such as `bullish` or `bearish`.

The new implementation does not emit `bullish`, `bearish`, or source-generated investment-direction wording. It returns data only.

## 7. Smoke Test Result

Command:

```bash
.venv/bin/python scripts/recovery/run_northbound_flow_contract_smoke.py
```

Result:

```text
TUSHARE_TOKEN=present
northbound_flow: PASS status=ok len=1788 note=ok
```

The smoke test validates:

- return type is `str`;
- `# Data Source Contract` exists;
- required header keys exist;
- `source=Tushare moneyflow_hsgt`;
- `data_type=northbound_flow`;
- `query_target=market`;
- `coverage=market_wide`;
- `raw_error_suppressed` is present and status-consistent;
- success output includes `moneyflow_hsgt` fields;
- empty output includes `empty_reason`;
- technical-error output is short and raw-suppressed;
- output does not include raw HTML, traceback, proxy stack, token values, oversized technical error text, `bullish`, or `bearish`.

## 8. Raw Artifact Check

No smoke output or sampled function output contained:

- raw HTML;
- traceback;
- proxy stack;
- raw exception text;
- `HTTPSConnectionPool`;
- `ProxyError`;
- token/API key values;
- oversized technical error text;
- `bullish`;
- `bearish`.

No `.env`, `.cache`, raw HTML, local runtime cache, run log, token, or API key file was added.

## 9. String Compatibility

String compatibility is preserved. `get_northbound_flow` still returns a single `str` with:

1. `# Data Source Contract`
2. header fields
3. `## Data`
4. Markdown body

No dict/JSON return type was introduced.

## 10. Boundary Confirmation

This change is data-source-layer only. It does not modify prompt logic, debate logic, Quality Gate logic, Agent orchestration, or trading recommendation rules.

## 11. Next Step

The planned next batch is `5B-2`: `get_concept_blocks`.

Before changing it, keep the same boundary:

- data-source layer only;
- `dc_concept_cons` as the primary Tushare candidate;
- no mixing of stock concept membership and board-level performance without separate labels;
- bottom-level smoke test only;
- no Agent, multi-Agent, LLM, prompt, Bull/Bear, or Quality Gate change.
