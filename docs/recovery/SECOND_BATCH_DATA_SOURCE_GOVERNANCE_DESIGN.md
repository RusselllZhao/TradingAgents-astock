# SECOND_BATCH_DATA_SOURCE_GOVERNANCE_DESIGN

- Stage: `5A-1`
- Date: 2026-07-08
- Branch: `recovery/data-source-only`
- Baseline commit: `ecfee0e`
- Scope: design only. No code, prompt, Quality Gate, Bull/Bear, trading-rule, Agent, or external data-source run is part of this document.

## 1. Background and Scope

The first Tushare replacement batch fixed the six highest-priority A-share dataflow defects and passed both bottom-level regression and the `300450` minimal Agent regression. The remaining second-batch risk is not that every remaining tool is broken. The risk is that several tools still mix successful data, empty results, vendor failures, fallback state, and scope information inside free-form strings.

The `300450` minimal Agent regression exposed the concrete Stage 5 trigger: `get_industry_comparison` was called twice and returned Eastmoney proxy-style ordinary text at the tool layer. The text did not enter the final report, but it proved that non-first-batch functions can still return technical failures in a form that looks like normal tool content.

This design covers the second-batch functions prioritized by `SECOND_BATCH_SCOPE_REVIEW.md`:

| Priority | Functions |
|---|---|
| P0 | `get_industry_comparison` |
| P1 | `get_news`, `get_hot_stocks`, `get_northbound_flow`, `get_concept_blocks` |
| P2 | `get_global_news`, `get_insider_transactions`, `get_dragon_tiger_board` |

This design also records a string-compatible contract that can later be reused by first-batch functions and by `route_to_vendor`, but the 5B code boundary should start with P0 and then P1/P2.

## 2. Why Data Source Governance First

The current tools and Agents primarily consume strings. A direct change from string return values to dict or JSON objects would likely require broader Agent and tool-consumption changes. That would violate the current recovery boundary.

The safer 5B path is therefore:

1. Keep string returns.
2. Add a structured, machine-readable header at the top of the string.
3. Keep the data body below that header.
4. Ensure empty results and technical errors have distinct status values.
5. Ensure raw technical artifacts never enter the Agent-visible body.

This keeps the design focused on data-source stability, accuracy, and coverage before any prompt or debate-layer work.

## 3. Three Principles: Stability, Accuracy, Coverage

### Stability

Data-source tools should return stable, bounded output. A technical problem must not be returned as raw HTML, traceback, proxy stack, raw exception text, anti-scraping page, or oversized failure text. A technical failure should be represented by a short `status=technical_error` header with `error_type` and `raw_error_suppressed=true`.

### Accuracy

Tool output must match tool semantics. A news tool should return news data. A fund-flow tool should return fund-flow data. A profit-forecast tool should return institutional forecast data, not company guidance. A dragon-tiger-board tool should return dragon-tiger event data. If the implementation returns a related but different shape, the header must expose the actual `data_type`, `query_target`, and `coverage` instead of letting the function name imply a different meaning.

### Coverage

Tools should make the query object and coverage boundary explicit. If a tool returns all-market data, industry-wide data, concept-wide data, or event-lookup data, the header should say so. If a stock symbol cannot be resolved or data only partially covers the requested object or date range, the header should say so with `coverage=symbol_unresolved` or `coverage=partial_coverage`.

## 4. What This Design Does Not Do

This design does not do the following:

1. It does not design evidence grades.
2. It does not decide whether news, media, hot-stock lists, northbound flow, industry rankings, concept tags, or any other material should be a main Bull/Bear debate argument.
3. It does not introduce labels such as `strong evidence`, `weak evidence`, `first-hand fact`, `second-hand information`, or `weak signal`.
4. It does not introduce `conclusion_level`.
5. It does not introduce `confidence`.
6. It does not modify Agent prompts, Bull/Bear logic, Quality Gate, or trading recommendation rules.
7. It does not replace Bull/Bear judgment about reliability, materiality, direction, or interpretation.

The contract only describes what the data-source call returned, what it tried to query, what range it covers, and whether it succeeded, returned no applicable data, or failed technically.

## 5. String-Compatible Header Design

Each governed tool should return a string with this shape:

```text
# Data Source Contract
status: ok
source: Eastmoney push2
data_type: industry_ranking
query_target: market
symbol: 300450
as_of: 2026-07-07
trade_date: 2026-07-07
unit: pct_change=percent; count=stocks
coverage: market_wide
fallback: none
empty_reason: none
error_type: none
raw_error_suppressed: false
limitations: target stock industry is not resolved in this output
notes: function requested industry comparison; current body is all-market industry ranking

## Data
...
```

The header is intentionally simple:

| Field | Meaning | Required |
|---|---|---|
| `status` | Call result state. It is not an investment meaning. | yes |
| `source` | Vendor or internal source used for the visible body. | yes |
| `data_type` | What kind of data is returned. | yes |
| `query_target` | What object the call actually queried. | yes |
| `symbol` | Requested stock symbol if applicable; `N/A` if not applicable. | yes |
| `as_of` | Data cutoff, retrieval timestamp, or query baseline. | yes |
| `trade_date` | Trading-date basis if applicable; `N/A` otherwise. | yes |
| `unit` | Units used in the body, or `mixed/see_data` if table fields differ. | yes |
| `coverage` | Coverage range of the returned body. | yes |
| `fallback` | `none`, source name, or ordered fallback chain used. | yes |
| `empty_reason` | Standard reason when no records are returned; `none` otherwise. | yes |
| `error_type` | Standard technical error type; `none` unless `status=technical_error`. | yes |
| `raw_error_suppressed` | `true` if raw technical text was hidden from Agent-visible output. | yes |
| `data` | Body marker. Body remains Markdown/table/text. | yes |
| `notes` | Neutral implementation notes needed to understand the body. | optional |
| `limitations` | Neutral data limitations, without judging debate importance. | optional |

Header values should be short and bounded. Free-form raw errors belong in logs only, not in Agent-visible output.

## 6. Standard Status Taxonomy

`status` describes only the data-source call result. It does not describe investment meaning, debate value, or recommendation direction.

| Status | Meaning | Agent-visible body | Normal consumption? |
|---|---|---|---|
| `ok` | The requested source returned data matching the declared `data_type` and `coverage`. | Include data body. | yes |
| `empty` | The source call succeeded, but no rows/items remained after query and filtering. | No data table; include `empty_reason`. | limited |
| `no_event` | The query is event-based and no event was found for the requested object/window. | No event table; include event window. | limited |
| `no_coverage` | The source does not cover the requested symbol/date/type, or coverage is unavailable. | No data table; include coverage note. | limited |
| `partial_data` | Some requested data was returned, but one or more sections, sources, or fallback parts were missing. | Include returned data and missing sections. | yes, with header |
| `stale_data` | Data is available but older than the requested date/window. | Include stale timestamp and body if useful. | yes, with header |
| `technical_error` | The source failed due to network, proxy, anti-scraping, parse, timeout, schema, vendor, or similar technical issue. | No raw error; short message only. | no |
| `unsupported` | The tool/source cannot support the requested query type under current implementation. | No data body. | no |
| `invalid_input` | Input is malformed or cannot be resolved to the expected query object. | No data body. | no |

Required distinctions:

- `empty` is not `technical_error`.
- `no_event` is not `technical_error`.
- `no_coverage` is not `technical_error`.
- `technical_error` must not include raw exception text, HTML, proxy stack, or traceback.

## 7. Standard Data Type Taxonomy

`data_type` describes what the body contains. It does not evaluate whether the body is important or how Bull/Bear should use it.

| Data type | Meaning |
|---|---|
| `news` | Stock-related news articles or article summaries. |
| `global_news` | Market, macro, or global news articles/summaries. |
| `hot_stocks` | Hot-stock or limit-up list with fields returned by the hot-stock vendor. |
| `northbound_flow` | Northbound capital-flow time series or snapshots. |
| `concept_blocks` | Stock concept, sector, region, or block membership and related block fields. |
| `industry_comparison` | A comparison that actually links the requested stock to its industry peers or industry context. |
| `industry_ranking` | Cross-industry or all-market industry ranking not necessarily resolved to the requested stock's industry. |
| `shareholder_f10` | A-share F10 shareholder research or shareholder-change text. |
| `dragon_tiger_event` | Dragon-tiger board appearances and seat-detail event records. |
| `financial_statement` | Balance sheet, cashflow, or income statement data. |
| `fundamentals` | Basic company, valuation, market-cap, shares, and profile data. |
| `fund_flow` | Individual-stock fund-flow data. |
| `profit_forecast` | Institutional forecast / forecast aggregation data. |
| `unknown` | The source returned a shape that cannot be classified safely. Use with `partial_data`, `unsupported`, or `technical_error` as appropriate. |

If a function name implies one data type but the body contains another, the header must describe the body honestly. Example: current `get_industry_comparison` should use `data_type=industry_ranking` until it truly resolves a target-stock industry comparison.

## 8. Standard Query Target Taxonomy

`query_target` describes the object actually queried.

| Query target | Meaning |
|---|---|
| `stock` | A specific stock symbol is the primary query object. |
| `market` | The query returns all-market or market-wide data. |
| `industry` | The query returns one industry or multiple industries. |
| `concept` | The query returns concept or block membership/coverage. |
| `event` | The query checks whether an event exists for a symbol/window. |
| `macro` | The query is macro/global/market-news oriented, not symbol-specific. |
| `unknown` | The actual query target cannot be determined. |

If the tool accepts a `symbol` but the source call ignores it or uses it only in the title, the header should not claim `query_target=stock`. It should disclose the actual target and coverage.

## 9. Standard Coverage Taxonomy

`coverage` describes the returned data boundary. It does not judge importance.

| Coverage | Meaning |
|---|---|
| `individual_stock` | Data is specifically for the requested stock. |
| `all_a_share` | Data covers the A-share universe or a broad A-share list. |
| `market_wide` | Data is market-level and not tied to one stock. |
| `industry_wide` | Data covers an industry or multiple industries. |
| `concept_wide` | Data covers concept/block membership or concept/block-level data. |
| `event_lookup` | Data is an event lookup for the requested symbol/window. |
| `symbol_unresolved` | The requested symbol could not be validated or mapped. |
| `partial_coverage` | Some sections or date ranges are covered, but not the full request. |
| `unknown` | Coverage cannot be determined safely. |

Coverage is the main guardrail against returning data unrelated to the query stock or query scenario.

## 10. Empty Reason Taxonomy

`empty_reason` explains why no records are visible. It does not explain investment meaning.

| Empty reason | Meaning |
|---|---|
| `no_event` | No event occurred in the requested event window. |
| `no_coverage` | The source does not cover this symbol, date, or data type. |
| `non_trading_day` | The requested date is not a trading day for this data type. |
| `source_empty` | The source returned an empty list/table for the query. |
| `not_applicable` | The requested data type does not apply to this query object. |
| `invalid_or_unresolved_ticker` | The symbol is invalid or could not be resolved. |
| `filtered_out` | Source had data, but all rows were removed by date, symbol, or type filtering. |
| `unknown` | The reason cannot be determined without raw debugging. |

Recommended mapping:

- Use `status=no_event` and `empty_reason=no_event` for event functions such as dragon-tiger board no-appearance cases.
- Use `status=empty` and `empty_reason=source_empty` when a successful source call returns no rows.
- Use `status=invalid_input` and `empty_reason=invalid_or_unresolved_ticker` for malformed or unresolved symbols.
- Use `status=no_coverage` and `empty_reason=no_coverage` when the source does not cover the requested object.

## 11. Technical Error Taxonomy

`error_type` describes technical failure only. It does not describe data importance or investment meaning.

| Error type | Meaning |
|---|---|
| `network_error` | Connection failure, DNS, refused connection, or generic network failure. |
| `proxy_error` | Proxy connection failure, proxy disconnect, or proxy stack. |
| `anti_scraping` | Vendor anti-scraping or access-block behavior. |
| `html_response` | HTML page returned where JSON/table/data was expected. |
| `parse_error` | Data was returned but parser failed. |
| `vendor_error` | Vendor returned an explicit error code/message. |
| `timeout` | Request timed out. |
| `rate_limited` | Vendor rate limit or quota limit was encountered. |
| `unexpected_schema` | Response schema did not match expected fields. |
| `unknown` | Technical failure category cannot be safely classified. |

For `status=technical_error`:

- `raw_error_suppressed` must be `true`.
- Body should contain at most a short neutral sentence, for example: `Data source request failed; raw technical details suppressed.`
- Raw exception details can be logged for developers, but must not be returned to the Agent-visible string.

## 12. Function-Level Application Plan

| Function | Recommended status scenarios | data_type | query_target | coverage | Empty expression | Technical-error expression | Fallback expression | Old text to forbid | Semantic mismatch? | 5B minimal code recommendation |
|---|---|---|---|---|---|---|---|---|---|---|
| `get_industry_comparison` | `ok`, `empty`, `technical_error`, `partial_data` if target industry unresolved but ranking returned | `industry_ranking` now; `industry_comparison` only after target industry is resolved | `market` now; `stock` or `industry` only after mapping exists | `market_wide` or `industry_wide`; `symbol_unresolved` if ticker invalid | `status=empty`; `empty_reason=source_empty`; include requested date | `status=technical_error`; `error_type=proxy_error/html_response/timeout/vendor_error/unexpected_schema`; suppress raw text | `fallback=none` unless a later fallback is added | `HTTPSConnectionPool`, proxy stack, `行业对比查询失败: {raw}`, HTML, traceback, bare `行业数据获取为空` | Yes. Name implies target-stock industry comparison; current body is all-market industry ranking. | Add contract header and short error suppression first. Do not change source semantics in the same step unless symbol-to-industry mapping is explicitly implemented. |
| `get_news` | `ok`, `empty`, `invalid_input`, `partial_data`, `technical_error` | `news` | `stock` when symbol/query match is validated; `unknown` if unresolved | `individual_stock`, `symbol_unresolved`, or `partial_coverage` | `status=empty`; `empty_reason=source_empty/filtered_out`; include date range | Short technical header; classify Eastmoney/Sina failures; no raw exception | `fallback=Eastmoney->Sina` if Sina used; `fallback=none` otherwise | Bare `No news found...`; raw vendor errors; generic news for invalid code without `symbol_unresolved` | Possible if invalid code returns general news unrelated to requested symbol. | Validate symbol shape/resolution before accepting article list; add header; expose fallback source and query date range. |
| `get_hot_stocks` | `ok`, `empty`, `technical_error`, `stale_data` | `hot_stocks` | `market` | `market_wide` or `all_a_share` | `status=empty`; `empty_reason=non_trading_day/source_empty`; include date | `status=technical_error`; `error_type=vendor_error/parse_error/network_error/timeout`; suppress vendor/raw message | `fallback=none` | `Tonghuashun API error: {raw}`; `Error fetching hot stocks...`; bare `No hot stocks data...` | No stock-specific query; should not imply relation to a requested symbol. | Add header with `symbol=N/A`, `query_target=market`, `coverage=market_wide`, `trade_date=curr_date`; structure vendor error. |
| `get_northbound_flow` | `ok`, `partial_data`, `empty`, `stale_data`, `technical_error` | `northbound_flow` | `market` | `market_wide` | `status=empty`; `empty_reason=non_trading_day/source_empty`; no realtime rows | Short technical header; classify network/proxy/parse/timeout | `fallback=local_cache` when only cache/history is used; otherwise `none` | Raw exception; `Error fetching northbound flow...`; unstructured `No realtime data`; source-generated `bullish`/`bearish` wording | No stock-specific query; it is market-level flow. | Add header with market coverage and cache `as_of`; remove source-level investment wording from data-source output and keep numeric flow fields. |
| `get_concept_blocks` | `ok`, `empty`, `invalid_input`, `technical_error`, `partial_data` | `concept_blocks` | `stock` | `individual_stock` plus `concept_wide` for block fields; `symbol_unresolved` if invalid | `status=empty`; `empty_reason=source_empty/no_coverage/invalid_or_unresolved_ticker` | `status=technical_error`; `error_type=vendor_error/parse_error/unexpected_schema/network_error`; suppress raw ResultMsg if verbose | `fallback=none` | `Baidu PAE error: ResultCode=...`; `Error fetching concept blocks...`; bare `No concept/block data...` | Possible if source returns categories for a different/unresolved symbol. | Validate response key equals requested symbol; add unit notes for ratio fields; structure ResultCode failures. |
| `get_global_news` | `ok`, `empty`, `partial_data`, `technical_error` | `global_news` | `macro` or `market` | `market_wide` | `status=empty`; `empty_reason=source_empty/filtered_out`; include date window | Short technical header; classify per-source failure if all sources fail | `fallback=CLS+Eastmoney`; use `partial_data` if one source fails and another returns rows | Bare `No global news found...`; raw source errors | No stock-specific query; should not imply symbol coverage. | Add header with `symbol=N/A`, date window, per-source availability, and no raw errors. |
| `get_insider_transactions` | `ok`, `empty`, `invalid_input`, `technical_error`, `stale_data` | `shareholder_f10` | `stock` | `individual_stock` or `symbol_unresolved` | `status=empty`; `empty_reason=source_empty/no_coverage` | `status=technical_error`; `error_type=vendor_error/parse_error/unexpected_schema/network_error`; suppress raw exception | `fallback=none` | `Error retrieving insider/shareholder data...`; bare `No insider/shareholder data...` | Yes. Function name says insider transactions, current A-share source is F10 shareholder research. | Add header with `data_type=shareholder_f10`; keep body title aligned with shareholder F10; avoid implying US-style insider transaction data. |
| `get_dragon_tiger_board` | `ok`, `no_event`, `partial_data`, `technical_error`, `invalid_input` | `dragon_tiger_event` | `event` | `event_lookup` or `partial_coverage` | `status=no_event`; `empty_reason=no_event`; include lookback window | `status=technical_error`; classify list-query failures; no raw error text | `fallback=none`; if seat detail fails but list succeeds use `partial_data` | `龙虎榜列表查询失败: {raw}`; silent seat-detail failure; bare no-event text without header | No, but no-event and technical error are currently easy to blur. | Add header; distinguish no board event from source failure; expose seat-detail partial status. |

## 13. P0 Implementation Guidance

### `get_industry_comparison`

Current facts:

- The function name and docstring imply target-stock industry comparison.
- The current implementation requests Eastmoney industry-board ranking with `fs=m:90+t:2`.
- The body currently returns all-market industry ranking and does not resolve the requested symbol to its own industry.
- `300450` Agent regression recorded proxy-style ordinary text twice for this tool.

5B minimal implementation boundary:

1. Add the standard header.
2. Use `data_type=industry_ranking` until target-stock industry mapping exists.
3. Use `query_target=market` and `coverage=market_wide` for the current body.
4. Keep `symbol` as the requested symbol, but add a neutral note such as `target industry not resolved by current implementation`.
5. Convert empty `diff` to `status=empty`, `empty_reason=source_empty`.
6. Convert exceptions to `status=technical_error` and classified `error_type`.
7. Suppress raw proxy/HTML/traceback/exception text from Agent-visible output.

Do not change prompt or debate logic to compensate for this mismatch. The tool output itself should state the actual data type and coverage.

## 14. P1 Implementation Guidance

### `get_news`

5B should make the function stable and symbol-bound:

- Header: `data_type=news`, `query_target=stock`, `coverage=individual_stock`.
- If the symbol is invalid or cannot be resolved: `status=invalid_input`, `coverage=symbol_unresolved`, `empty_reason=invalid_or_unresolved_ticker`.
- If Eastmoney fails and Sina returns rows: `status=ok`, `fallback=Eastmoney->Sina`.
- If both sources fail technically: `status=technical_error`, classified `error_type`, `raw_error_suppressed=true`.
- If sources are reachable but no articles match date/symbol filters: `status=empty`, `empty_reason=source_empty` or `filtered_out`.
- The body should remain article title/time/source/link/snippet data.

### `get_hot_stocks`

5B should clarify that this is market-list data:

- Header: `data_type=hot_stocks`, `query_target=market`, `coverage=market_wide`, `symbol=N/A`.
- Empty market list: `status=empty`, `empty_reason=non_trading_day` or `source_empty`.
- Vendor error code: `status=technical_error`, `error_type=vendor_error`, `raw_error_suppressed=true`.
- Request/parse failures: classify as `network_error`, `timeout`, `parse_error`, or `unexpected_schema`.
- The body should include returned hot-stock fields and vendor reason fields as data columns, not as a source-level conclusion.

### `get_northbound_flow`

5B should keep only data-source output, not investment conclusions:

- Header: `data_type=northbound_flow`, `query_target=market`, `coverage=market_wide`, `unit=CNY 100M`.
- If realtime works: `status=ok`, `as_of` should reflect snapshot time if available.
- If realtime fails but local history/cache is shown: `status=partial_data` or `stale_data`, `fallback=local_cache`, and `as_of` should reflect cache date.
- If no realtime rows because the date is not a trading day or market is closed: `status=empty`, `empty_reason=non_trading_day` or `source_empty`.
- Technical failures should not return raw request exceptions.
- Remove Agent-visible `bullish` / `bearish` source wording from the data-source output in 5B; keep numeric flow rows and totals.

### `get_concept_blocks`

5B should bind output to the requested symbol and clarify units:

- Header: `data_type=concept_blocks`, `query_target=stock`, `coverage=individual_stock`.
- If returned block data contains broader block fields, add `coverage=individual_stock; concept fields include concept_wide values` or use `notes`.
- Baidu `ResultCode` failures should become `status=technical_error`, `error_type=vendor_error`, and a short message.
- Empty category list should become `status=empty`, `empty_reason=source_empty` or `no_coverage`.
- Invalid or unresolved symbols should become `status=invalid_input`.
- `unit` should describe `ratio` explicitly if known; otherwise use `unit=ratio: upstream raw field, not normalized`.

## 15. P2 Backlog Guidance

### `get_global_news`

5B or later should make market/macro scope explicit:

- Header: `data_type=global_news`, `query_target=macro` or `market`, `coverage=market_wide`, `symbol=N/A`.
- If one source fails but another returns data: `status=partial_data` and record source availability in `notes`.
- Empty result: `status=empty`, `empty_reason=source_empty` or `filtered_out`.
- All-source technical failure: `status=technical_error`.

### `get_insider_transactions`

5B or later should correct the A-share data type:

- Header: `data_type=shareholder_f10`, `query_target=stock`, `coverage=individual_stock`.
- Keep the function name for compatibility, but make the body/header say that the returned data is F10 shareholder research.
- Empty F10 text: `status=empty`, `empty_reason=source_empty` or `no_coverage`.
- Invalid symbol: `status=invalid_input`.
- Raw mootdx exceptions should be suppressed and classified.

### `get_dragon_tiger_board`

5B or later should separate no-event from source failure:

- Header: `data_type=dragon_tiger_event`, `query_target=event`, `coverage=event_lookup`.
- No board appearance in the lookback window: `status=no_event`, `empty_reason=no_event`.
- Listing query technical failure: `status=technical_error`.
- Listing succeeds but buy/sell seat details fail: `status=partial_data`, with `notes=seat detail unavailable`.
- No exception should be silently swallowed without a visible partial-data marker.

## 16. Forbidden Outputs Into Agent Context

The following outputs must not appear in Agent-visible tool strings after 5B governance:

1. Raw exception text.
2. HTML pages or HTML fragments.
3. Traceback text.
4. Proxy stack text.
5. Anti-scraping pages.
6. Oversized error text.
7. Bare `No data found` without structured `status` and `empty_reason`.
8. Data that does not match the tool's declared `data_type`.
9. Data unrelated to the query object without explicit `query_target` and `coverage`.
10. Institutional forecast data presented as company earnings forecast/guidance.
11. Company earnings forecast/guidance presented as institutional forecast data.
12. Generic news returned for an invalid or unresolved stock code without `status=invalid_input` or `coverage=symbol_unresolved`.
13. Market-wide lists returned as stock-specific data without header disclosure.
14. Silent partial failures where one section succeeds and another section fails.
15. Any output that makes a data-source call unstable, inaccurate, or unclear about coverage.

## 17. Next Step: 5B Minimal Code Change Boundary

5B should remain minimal and data-source-only.

Recommended order:

1. Add small helper functions for building the string header and for mapping exceptions to `error_type`.
2. Apply the helper first to `get_industry_comparison`.
3. Add a bottom-level smoke script or existing-script extension that validates:
   - header fields exist;
   - `status` is one of the taxonomy values;
   - technical errors are short and raw-error suppressed;
   - body does not include HTML, traceback, proxy stack, or oversized error text;
   - current all-market industry ranking is labeled as `industry_ranking`, not target-stock `industry_comparison`.
4. Apply the same pattern to P1 functions.
5. Add P2 functions after P0/P1 shape is stable.

5B should not:

- Modify Agent prompts.
- Modify Bull/Bear debate.
- Modify Quality Gate.
- Modify trading recommendation rules.
- Run multi-Agent workflows.
- Call external data sources unless a later task explicitly allows bottom-level smoke calls.
- Commit cache, local config, raw runtime artifacts, or credential material.

## 18. Open Questions

| Question | Why it matters |
|---|---|
| Should `get_industry_comparison` remain a market industry-ranking tool under the current name, or should 5B add symbol-to-industry mapping? | Mapping would improve semantic accuracy but may require new source logic. |
| Should `route_to_vendor` receive a generic wrapper in 5B, or should P0/P1 functions be governed individually first? | A generic wrapper reduces duplication but may be wider than minimal P0 code change. |
| What exact unit should Baidu PAE `ratio` use when upstream does not document it clearly in current code? | The contract should avoid claiming a normalized unit until verified. |
| Should local cache writes in `get_northbound_flow` be deferred or isolated during tests? | The function currently can write `northbound_daily.csv`; 5B tests should avoid committing runtime cache. |
| Should invalid ticker validation rely on six-digit format only or on a symbol-resolution helper? | Format-only validation may still allow nonexistent symbols; resolver validation may require network/vendor availability. |
| Should P2 functions be modified in the same 5B batch or left for 5C after P0/P1 passes smoke checks? | Smaller batches reduce regression risk. |

## 19. Design Conclusion

The second-batch governance contract should be string-compatible and data-source-only. It should make status, data type, query target, coverage, date basis, unit, fallback, empty reason, and technical error category explicit without judging debate importance or modifying Agent logic.

The first 5B code change should target `get_industry_comparison`, because it has both a documented semantic mismatch and observed proxy-style ordinary error text in the `300450` minimal Agent regression. P1 functions should follow once the header and error-suppression pattern is verified.
