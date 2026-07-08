# SECOND_BATCH_P0_INDUSTRY_COMPARISON_RESULT

- Stage: `5B`
- Date: 2026-07-08
- Branch: `recovery/data-source-only`
- Scope: P0 data-source governance for `get_industry_comparison` only.

## 1. Modification Scope

Changed files:

- `tradingagents/dataflows/a_stock.py`
- `scripts/recovery/run_industry_comparison_contract_smoke.py`

Code changes in `a_stock.py`:

- Added `_build_data_source_contract_header`.
- Added `_classify_data_source_error`.
- Updated `get_industry_comparison` to return a string-compatible data-source contract header before the existing Markdown data body.
- Updated `get_industry_comparison` technical-error handling so raw exceptions, HTML, traceback, proxy stack, and long network errors are not returned to Agent-visible output.

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
- P1 or P2 data-source functions.

No LLM, Agent, or multi-Agent workflow was run.

## 3. Helper Design

### `_build_data_source_contract_header`

Builds a string-compatible header:

- `status`
- `source`
- `data_type`
- `query_target`
- `symbol`
- `as_of`
- `trade_date`
- `unit`
- `coverage`
- `fallback`
- `empty_reason`
- `error_type`
- `raw_error_suppressed`
- optional `limitations`
- optional `notes`

The helper returns text headed by `# Data Source Contract` and ending with `## Data`, so downstream tools still receive a single string.

### `_classify_data_source_error`

Maps technical failures to bounded `error_type` values:

- `proxy_error`
- `html_response`
- `timeout`
- `network_error`
- `parse_error`
- `vendor_error`
- `unexpected_schema`
- `unknown`

The helper classifies errors without exposing raw exception text in the returned string.

## 4. `get_industry_comparison` Governance Result

The current implementation is intentionally not represented as true target-stock industry comparison. Until symbol-to-industry mapping is implemented, the output contract is:

```text
data_type: industry_ranking
query_target: market
coverage: market_wide
limitations: target stock industry is not resolved by current implementation
notes: function requested industry comparison; current body is all-market industry ranking
```

The function still returns Markdown data when Eastmoney returns industry rows. The data body is now preceded by the contract header.

## 5. Output Contracts

### Normal Success

- `status: ok`
- `source: Eastmoney push2`
- `data_type: industry_ranking`
- `query_target: market`
- `coverage: market_wide`
- `raw_error_suppressed: false`
- Body contains the all-market industry ranking table.

### Empty Result

- `status: empty`
- `empty_reason: source_empty`
- `data_type: industry_ranking`
- `query_target: market`
- `coverage: market_wide`
- `raw_error_suppressed: false`
- Body contains a short neutral empty-result sentence.

### Technical Error

- `status: technical_error`
- `error_type: proxy_error/html_response/timeout/network_error/parse_error/vendor_error/unexpected_schema/unknown`
- `data_type: industry_ranking`
- `query_target: market`
- `coverage: market_wide`
- `raw_error_suppressed: true`
- Body contains only:

```text
Data source request failed; raw technical details suppressed.
```

## 6. Smoke Test Result

Command:

```bash
.venv/bin/python scripts/recovery/run_industry_comparison_contract_smoke.py
```

Result:

```text
Industry comparison source failed for 300450; raw technical details suppressed
Industry comparison source failed for 600519; raw technical details suppressed
Industry comparison source failed for 688981; raw technical details suppressed
300450: PASS status=technical_error len=575 note=ok
600519: PASS status=technical_error len=575 note=ok
688981: PASS status=technical_error len=575 note=ok
```

The smoke test validates:

- return type is `str`;
- `# Data Source Contract` exists;
- required header keys exist;
- current successful semantics are `industry_ranking / market / market_wide`;
- `raw_error_suppressed` is present and correct;
- technical-error output is short and raw-error suppressed if the source fails;
- output does not contain HTML, traceback, `HTTPSConnectionPool`, `ProxyError`, proxy stack text, raw exception text, anti-scraping text, or checked sensitive env values.

The final smoke run encountered transient source failures and verified the expected failure contract: `status=technical_error`, `raw_error_suppressed=true`, bounded output length, and no raw proxy/network stack in the returned string.

## 7. Raw Artifact Check

No Agent-visible function output or smoke output contained:

- raw HTML;
- traceback;
- proxy stack;
- raw exception text;
- `HTTPSConnectionPool`;
- `ProxyError`;
- token/API key values;
- oversized error text.

## 8. String Compatibility

String compatibility is preserved. `get_industry_comparison` still returns a single `str`, with a structured header followed by Markdown body content.

No dict/JSON return type was introduced.

## 9. Boundary Confirmation

This P0 change does not implement full target-stock industry resolution. It only makes the current all-market Eastmoney industry ranking honest and stable through:

- `data_type: industry_ranking`
- `query_target: market`
- `coverage: market_wide`
- explicit neutral limitation that target stock industry is not resolved.

## 10. Follow-up P1 Recommendation

After this P0 contract shape is accepted, apply the same string-compatible contract pattern to P1 functions in separate, scoped changes:

1. `get_news`
2. `get_hot_stocks`
3. `get_northbound_flow`
4. `get_concept_blocks`

P1 should reuse the header and error-classification helpers rather than introducing a second contract style.
