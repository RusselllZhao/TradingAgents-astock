# SECOND_BATCH_POST_TUSHARE_8000_DEVELOPMENT_PLAN

- Stage: `5B-Plan`
- Date: 2026-07-08
- Branch: `recovery/data-source-only`
- Baseline commit: `7276ab2`
- Scope: planning only. No business code, prompt, Bull/Bear, Quality Gate, trading-rule, Agent, LLM, Tushare, or external data-source run is part of this document.

## 1. Background

Second-batch recovery has completed four preparatory stages:

| Stage | Commit | Deliverable |
|---|---|---|
| 5A-0 | `ecfee0e` | `docs/recovery/SECOND_BATCH_SCOPE_REVIEW.md` |
| 5A-1 | `ff311e8` | `docs/recovery/SECOND_BATCH_DATA_SOURCE_GOVERNANCE_DESIGN.md` |
| 5B-P0 | `a7de873` | `docs/recovery/SECOND_BATCH_P0_INDUSTRY_COMPARISON_RESULT.md` |
| 5B-API | `7276ab2` | `docs/recovery/SECOND_BATCH_TUSHARE_8000_API_REVIEW.md`; `docs/recovery/SECOND_BATCH_TUSHARE_8000_API_MATRIX.csv` |

The original second-batch order was risk-driven:

- P0: `get_industry_comparison`
- P1: `get_news`, `get_hot_stocks`, `get_northbound_flow`, `get_concept_blocks`
- P2: `get_global_news`, `get_insider_transactions`, `get_dragon_tiger_board`

The 8000-point Tushare probe changes the practical code route. Several functions now have a stable Tushare replacement candidate, while `get_news` still does not.

## 2. Inputs Reviewed

Reviewed inputs:

| File | Planning use |
|---|---|
| `docs/recovery/SECOND_BATCH_TUSHARE_8000_API_REVIEW.md` | Primary source-fit conclusions after the 8000-point probe. |
| `docs/recovery/SECOND_BATCH_TUSHARE_8000_API_MATRIX.csv` | Interface availability, row counts, semantic fit, and coverage fit. |
| `docs/recovery/SECOND_BATCH_DATA_SOURCE_GOVERNANCE_DESIGN.md` | String-compatible contract, status taxonomy, and field requirements. |
| `docs/recovery/SECOND_BATCH_P0_INDUSTRY_COMPARISON_RESULT.md` | Current P0 technical contract state and remaining accuracy boundary. |
| `docs/recovery/SECOND_BATCH_SCOPE_REVIEW.md` | Original P0/P1/P2 ordering and 300450 regression evidence. |
| `docs/recovery/DATA_SOURCE_INVENTORY.md` and `.csv` | Current source, failure mode, unit, fallback, and misread risk by function. |
| `tradingagents/dataflows/tushare_client.py` | Existing safe Tushare HTTP boundary and short-error behavior. |
| `tradingagents/dataflows/a_stock.py` | Current implementations of all eight functions. |
| `tradingagents/dataflows/interface.py` | Tool routing and exposure categories. |

Repository note:

- `docs/recovery/tushare_pro_inventory/TUSHARE_PRO_5000_POINTS_AVAILABLE.csv` was already modified in the working tree at the start of this planning pass. This plan does not depend on unstaged changes in that file and does not modify it.

## 3. Why Route Changes After Tushare 8000 Probe

The route should change. The next code batches should not follow the old P1/P2 order mechanically.

Reason:

| Finding | Planning impact |
|---|---|
| `moneyflow_hsgt` is available and exactly matches market-level northbound flow. | Move `get_northbound_flow` to first code batch. |
| `dc_concept_cons` is available and directly maps stock to concept membership. | Move `get_concept_blocks` ahead of news. |
| `ths_hot`, `limit_list_ths`, and `limit_step` are available. | Move `get_hot_stocks` into an early Tushare-backed batch. |
| `top_list` and `top_inst` are available and match dragon-tiger event data. | Promote `get_dragon_tiger_board` from P2 to an early replacement batch. |
| `news`, `anns_d`, and `cctv_news` returned no-permission. | Move `get_news` later and keep current sources with contract. |
| `major_news` is available but market/global, not stock-specific. | Treat it as a `get_global_news` supplement only. |
| `index_member_all` is available for symbol-to-industry mapping, but no single full peer-comparison API was validated. | Defer `get_industry_comparison` accuracy upgrade until the desired tool semantics are confirmed. |

This is still a data-source-only route. It does not change Agent prompts, Bull/Bear logic, Quality Gate, or recommendation rules.

## 4. Second-Batch Function Classification

| Function | Current status | Tushare 8000 fit | Recommended action |
|---|---|---|---|
| `get_northbound_flow` | Direct THS hsgtApi plus local CSV cache; includes market-level flow and generated signal text. | `moneyflow_hsgt` available; exact market-level flow fit. `hk_hold` available as holding supplement only. | `replace_with_tushare` first. |
| `get_concept_blocks` | Baidu PAE related-block endpoint; plain error/empty strings. | `dc_concept_cons` available; exact stock-to-concept membership fit. `ths_member` and `dc_index` can supplement only if clearly separated. | `replace_with_tushare` or tightly scoped hybrid. |
| `get_hot_stocks` | Direct THS hot-stock endpoint; market-level hot list and reason text. | `ths_hot` available; `limit_list_ths`, `limit_step`, and `limit_list_d` available as separate market-heat sections. | `replace_with_tushare` or hybrid with sectioned output. |
| `get_dragon_tiger_board` | Eastmoney datacenter; no-event and seat-detail failures are not cleanly separated. | `top_list` available; `top_inst` available. | `replace_with_tushare`. |
| `get_insider_transactions` | mootdx F10 shareholder research under an insider-transaction function name. | `stk_holdertrade`, `top10_holders`, `top10_floatholders`, `stk_holdernumber`, `stk_managers`, `stk_rewards` available. | `semantic_correction_first`, then Tushare-backed shareholder data. |
| `get_global_news` | CLS plus Eastmoney 7x24; market/global scope. | `major_news` available; not a complete replacement for fast-wire sources. | `supplement_with_tushare` after higher-fit replacements. |
| `get_news` | Eastmoney search plus Sina fallback; stock-news source remains external direct HTTP. | `news`, `anns_d`, and `cctv_news` not available in this probe; `major_news` is not stock-specific. | `keep_current_with_contract`. |
| `get_industry_comparison` | P0 technical contract done; current output honestly labels `industry_ranking / market / market_wide`. | `index_member_all` supports symbol-to-industry mapping; full peer-comparison body still requires design. | Defer accuracy upgrade until user confirms target semantics. |

## 5. Recommended Implementation Order

Recommended order after the 8000-point review:

| Batch | Function(s) | Route | Why this order |
|---|---|---|---|
| 5B-1 | `get_northbound_flow` | Tushare `moneyflow_hsgt` primary. | Highest semantic fit and easiest removal of current direct HTTP/local-cache weakness. |
| 5B-2 | `get_concept_blocks` | Tushare `dc_concept_cons` primary; evaluate `ths_member` and `dc_index` as separated optional sections. | Direct stock-to-concept membership is now available and improves coverage/stability. |
| 5B-3 | `get_hot_stocks` | Tushare `ths_hot` primary; evaluate `limit_list_ths`, `limit_step`, `limit_list_d` as separate sections. | Better stable hot-list source is available; market-heat subtypes must not be mixed. |
| 5B-4 | `get_dragon_tiger_board` | Tushare `top_list` plus `top_inst`. | P2 in old order, but now an exact event-data replacement with clear `no_event` handling. |
| 5B-5 | `get_insider_transactions` | Rename semantics in contract to shareholder/F10-style output; use Tushare shareholder APIs. | Source is available, but function semantics must be corrected before replacement. |
| 5B-6 | `get_global_news` | Current CLS/Eastmoney plus optional Tushare `major_news`. | Tushare supplements market/global news but does not replace fast-wire coverage by itself. |
| 5B-7 | `get_news` | Current Eastmoney/Sina with contract. | Tushare stock-news and announcement sources were not available in the 8000 probe. |
| 5B-8 | `get_industry_comparison` accuracy upgrade | User-confirmed route: keep ranking, or build true industry/peer comparison using mapping APIs. | P0 stability is already done; accuracy upgrade depends on desired tool semantics. |

## 6. Batch-by-Batch Scope

### 5B-1: `get_northbound_flow`

Minimum code scope:

- `tradingagents/dataflows/a_stock.py`
- one bottom-level smoke script under `scripts/recovery/`
- one result document under `docs/recovery/`

Recommended implementation:

- Replace current direct THS hsgtApi and local snapshot dependency with Tushare `moneyflow_hsgt` for daily northbound/southbound flow.
- Keep string-compatible `# Data Source Contract`.
- Use `data_type=northbound_flow`, `query_target=market`, `coverage=market_wide`.
- Do not include source-generated investment-direction wording.
- If `include_history=True`, use Tushare date-window rows rather than writing a local runtime cache.
- Treat `hk_hold` only as a future optional holding section, not a flow replacement.

Smoke test:

- `scripts/recovery/run_northbound_flow_contract_smoke.py`
- test recent date and a recent 30-day window;
- assert string output, header fields, status handling, `market_wide` coverage, no raw technical artifacts, and no local cache write.

External call policy:

- Future code batch may call Tushare in bottom-level smoke tests.
- Do not run Agent.

### 5B-2: `get_concept_blocks`

Minimum code scope:

- `tradingagents/dataflows/a_stock.py`
- one bottom-level smoke script
- one result document

Recommended implementation:

- Use Tushare `dc_concept_cons` as primary stock-to-concept membership source.
- Consider `ths_member` only if it returns useful membership fields for the requested stock.
- Use `dc_index` only for board-level performance and put it in a separate section if included.
- Do not mix symbol membership rows with board-wide performance rows without explicit `data_type`, `query_target`, and `coverage`.

Smoke test:

- `scripts/recovery/run_concept_blocks_contract_smoke.py`
- sample `300450`, `600519`, `688981`;
- assert `data_type=concept_blocks`;
- assert stock membership and board-level sections, if any, are labeled separately;
- assert empty and technical-error contracts are distinct.

External call policy:

- Future code batch may call Tushare bottom-level smoke tests.
- Do not run Agent.

### 5B-3: `get_hot_stocks`

Minimum code scope:

- `tradingagents/dataflows/a_stock.py`
- one bottom-level smoke script
- one result document

Recommended implementation:

- Use Tushare `ths_hot` as primary hot-stock source.
- Consider optional separate sections:
  - `limit_list_ths` for THS limit-up pool;
  - `limit_step` for consecutive limit-up ladder;
  - `limit_list_d` as fallback or alternate limit-up/down list.
- Keep output sectioned so hot ranking, limit-up pool, and consecutive limit ladder are not collapsed into one data type.
- Use `query_target=market`, `coverage=market_wide`.

Smoke test:

- `scripts/recovery/run_hot_stocks_contract_smoke.py`
- test recent trade-date window;
- assert no raw THS/API errors;
- assert section labels and units exist;
- assert technical errors are short and raw-suppressed.

External call policy:

- Future code batch may call Tushare bottom-level smoke tests.
- Do not run Agent.

### 5B-4: `get_dragon_tiger_board`

Minimum code scope:

- `tradingagents/dataflows/a_stock.py`
- one bottom-level smoke script
- one result document

Recommended implementation:

- Replace Eastmoney datacenter with Tushare `top_list` and `top_inst`.
- Query by date/lookback and filter by requested `ts_code`.
- Return `status=no_event` and `empty_reason=no_event` when the stock did not appear in the lookback window.
- Return `status=partial_data` if `top_list` succeeds but `top_inst` is unavailable or empty for a listed event.
- Use `data_type=dragon_tiger_event`, `query_target=event`, `coverage=event_lookup`.

Smoke test:

- `scripts/recovery/run_dragon_tiger_board_contract_smoke.py`
- sample at least one no-event path and one recent market event path if available;
- assert no-event is not technical error;
- assert partial seat detail, if triggered, is explicit.

External call policy:

- Future code batch may call Tushare bottom-level smoke tests.
- Do not run Agent.

### 5B-5: `get_insider_transactions`

Minimum code scope:

- `tradingagents/dataflows/a_stock.py`
- one bottom-level smoke script
- one result document

Recommended implementation:

- Keep function name for compatibility unless user approves a new tool name.
- Correct the visible contract semantics to A-share shareholder data.
- Preferred `data_type`: `shareholder_f10` or a user-confirmed shareholder-change label.
- Use `stk_holdertrade` for increase/decrease records.
- Use `top10_holders`, `top10_floatholders`, and `stk_holdernumber` for F10-style shareholder context.
- Use `stk_managers` and `stk_rewards` only if management context is explicitly included and sectioned.

Smoke test:

- `scripts/recovery/run_shareholder_contract_smoke.py`
- sample `300450`, `600519`, `688981`;
- assert the output does not claim US-style insider transactions;
- assert normal empty shareholder-change rows are not technical errors.

External call policy:

- Future code batch may call Tushare bottom-level smoke tests.
- Do not run Agent.

### 5B-6: `get_global_news`

Minimum code scope:

- `tradingagents/dataflows/a_stock.py`
- one bottom-level smoke script
- one result document

Recommended implementation:

- Keep current CLS/Eastmoney 7x24 path.
- Optionally add Tushare `major_news` as a supplemental source.
- Use `data_type=global_news`, `query_target=macro` or `market`, and `coverage=market_wide`.
- Keep source sections clear.
- Do not use company announcements as replacement for global news.

Smoke test:

- `scripts/recovery/run_global_news_contract_smoke.py`
- assert fallback/partial-data behavior when one source fails;
- assert publication time and source fields are present where available.

External call policy:

- Future code batch may call current direct news sources and/or Tushare only in bottom-level smoke tests.
- Do not run Agent.

### 5B-7: `get_news`

Minimum code scope:

- `tradingagents/dataflows/a_stock.py`
- one bottom-level smoke script
- one result document

Recommended implementation:

- Keep Eastmoney/Sina because Tushare `news`, `anns_d`, and `cctv_news` were not available in the 8000 probe.
- Add the standard contract header.
- Distinguish:
  - `invalid_input`;
  - `empty`;
  - `partial_data` when fallback source succeeds after primary failure;
  - `technical_error` when all sources fail technically.
- Avoid returning generic market news for an invalid or unresolved stock code.

Smoke test:

- `scripts/recovery/run_news_contract_smoke.py`
- sample valid `300450` and invalid/unresolved input;
- assert invalid input does not return unrelated generic news;
- assert no raw HTML, traceback, proxy stack, or long exception text appears.

External call policy:

- Future code batch may call direct bottom-level news endpoints for smoke tests if needed.
- No Tushare call is needed unless permission changes.
- Do not run Agent.

### 5B-8: `get_industry_comparison` accuracy upgrade

Minimum code scope:

- only after user confirms desired semantics;
- `tradingagents/dataflows/a_stock.py`
- one bottom-level smoke script
- one result document

Potential routes:

| Option | Meaning | Code implication |
|---|---|---|
| A. Keep as industry ranking | Preserve current P0 fixed behavior. | No accuracy upgrade needed; keep `data_type=industry_ranking`, `query_target=market`, `coverage=market_wide`. |
| B. Upgrade to target-stock industry comparison | Resolve symbol to industry and compare against industry/peer context. | Use `index_member_all` or `ci_index_member` for symbol-to-industry mapping; design peer or industry body before code. |
| C. Split tool semantics later | Keep existing function compatible, add a future distinct tool for peer comparison. | Requires separate tool and interface planning, so it is outside minimal second-batch replacement unless approved. |

Smoke test:

- if Option B is approved: `scripts/recovery/run_industry_comparison_accuracy_smoke.py`;
- sample `300450`, `600519`, `688981`;
- assert target industry is resolved;
- assert `industry_ranking` is not mislabeled as `industry_comparison`.

External call policy:

- Future code batch may call Tushare bottom-level smoke tests if Option B is approved.
- Do not run Agent.

## 7. Smoke Test Strategy

All future code batches should follow the same testing pattern:

| Test layer | Required? | Notes |
|---|---|---|
| Python syntax check | yes | Cover modified Python files and new smoke scripts. |
| Bottom-level smoke script | yes | Allowed to call Tushare only for batches that explicitly replace/supplement with Tushare. |
| Contract assertions | yes | Check `# Data Source Contract`, `status`, `data_type`, `query_target`, `coverage`, `raw_error_suppressed`, and body marker. |
| Raw technical artifact scan | yes | Check returned strings for HTML, traceback, proxy stack, raw exception, long connection errors, and token-like values. |
| Empty/no-event tests | yes where applicable | Especially `get_dragon_tiger_board`, `get_news`, and `get_concept_blocks`. |
| Agent or multi-Agent run | no | Not needed for these data-source-only batches. |
| LLM call | no | Not needed. |

Suggested sample symbols:

- `300450`
- `600519`
- `688981`

Suggested date handling:

- use current date or recent trading windows in future live smoke tests;
- do not hardcode future dates;
- for event tools, use a lookback window and accept `no_event` as a normal result when appropriate.

Each code batch should also add a short result document under `docs/recovery/` recording:

- changed files;
- unchanged scope;
- source selection;
- normal/empty/no-event/technical-error contract;
- smoke command and result;
- raw artifact scan result;
- prompt/Bull-Bear/Quality Gate/Agent unchanged confirmation.

## 8. What Still Should Not Be Changed

The later code batches should still not change:

- Agent prompts;
- Bull/Bear debate logic;
- Quality Gate;
- trading recommendation rules;
- Agent orchestration;
- `agents/`;
- `graph/`;
- `cli/`;
- `web/`;
- return type from string to dict/JSON;
- broad routing behavior in `interface.py`, unless a specific batch first documents why a data-source-only helper cannot work without it.

The later batches should also not introduce:

- evidence grades;
- labels that rank material importance for Bull/Bear;
- `confidence`;
- `conclusion_level`;
- rules that decide whether a data type should be a main debate argument.

The contract should describe only data-source state, data type, query target, coverage, freshness, unit, fallback, empty reason, and technical-error state.

## 9. User Confirmation Needed

Before code work reaches the following points, user confirmation is needed:

| Topic | Confirmation needed |
|---|---|
| `get_industry_comparison` semantics | Keep as all-market `industry_ranking`, upgrade to target-stock peer/industry comparison, or split into a future new tool. |
| `get_insider_transactions` naming | Keep compatible function name while exposing `shareholder_f10`, or plan a future renamed/new tool. |
| `get_hot_stocks` output sections | Whether to include only `ths_hot`, or also include `limit_list_ths`, `limit_step`, and/or `limit_list_d` as separate sections. |
| `get_concept_blocks` supplement policy | Whether to use only `dc_concept_cons`, or include `ths_member`/`dc_index` sections. |
| `get_northbound_flow` stock-connect supplement | Whether to keep it purely market-level `moneyflow_hsgt`, or add `hk_hold` as a separate holding section later. |
| `get_global_news` hybrid policy | Whether to keep CLS/Eastmoney primary and add `major_news`, or defer news changes until a stock/global news source policy is decided. |
| Tushare cache policy | Whether future Tushare replacements may use `.cache/tushare` for repeated calls, or should keep cache disabled in smoke tests and avoid runtime writes. |

## 10. Final Recommendation

Adopt the route change.

The old P1/P2 ordering was useful for risk discovery, but the 8000-point probe gives a clearer implementation path:

1. Start with `get_northbound_flow` because `moneyflow_hsgt` is the cleanest exact match and removes direct THS/local-cache fragility.
2. Then handle `get_concept_blocks` and `get_hot_stocks`, where 8000-point Tushare interfaces now provide materially better source options.
3. Promote `get_dragon_tiger_board` ahead of some old P1 items because `top_list` and `top_inst` fit the event semantics well.
4. Correct `get_insider_transactions` semantics before replacing its source.
5. Treat `get_global_news` as a later hybrid supplement.
6. Keep `get_news` late with current sources plus contract because Tushare stock-news/announcement interfaces were not available in the probe.
7. Defer `get_industry_comparison` accuracy work until the user confirms whether the tool should remain an all-market ranking or become a true target-stock industry/peer comparison.

No future code batch should require an Agent run. Bottom-level dataflow smoke tests are enough until the data-source contracts are stable across the second-batch functions.
