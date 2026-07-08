# SECOND_BATCH_TUSHARE_8000_API_REVIEW

- Stage: `5B-API`
- Date: 2026-07-08
- Branch: `recovery/data-source-only`
- Baseline commit: `a7de873`
- Scope: Tushare Pro 8000-point interface probe and second-batch source-fit assessment only.

## 1. Background

The second-batch data-source recovery previously had to assume that several non-Tushare sources would remain in place and receive string-compatible contract headers. The user's Tushare Pro point level is now 8000, so this review rechecks whether Tushare can provide more stable, accurate, and broad A-share coverage for the eight second-batch functions.

The already completed stages are:

| Stage | Commit | Deliverable |
|---|---|---|
| 5A-0 | `ecfee0e` | `docs/recovery/SECOND_BATCH_SCOPE_REVIEW.md` |
| 5A-1 | `ff311e8` | `docs/recovery/SECOND_BATCH_DATA_SOURCE_GOVERNANCE_DESIGN.md` |
| 5B-P0 | `a7de873` | `docs/recovery/SECOND_BATCH_P0_INDUSTRY_COMPARISON_RESULT.md` |

The P0 technical contract fix for `get_industry_comparison` remains valid. This review asks a different question: for P1/P2 and future P0 accuracy work, should the underlying source be Tushare, a hybrid source, or the current source plus contract protection?

## 2. Scope and Boundaries

Covered second-batch functions:

| Priority | Functions |
|---|---|
| P0 | `get_industry_comparison` |
| P1 | `get_news`, `get_hot_stocks`, `get_northbound_flow`, `get_concept_blocks` |
| P2 | `get_global_news`, `get_insider_transactions`, `get_dragon_tiger_board` |

This review did not modify:

- business dataflow code;
- `tradingagents/dataflows/a_stock.py`;
- `tradingagents/dataflows/interface.py`;
- Agent prompts;
- Bull/Bear debate logic;
- Quality Gate;
- trading recommendation rules;
- `agents/`, `graph/`, `cli/`, or `web/`.

No Agent, multi-Agent workflow, or LLM was run.

## 3. Tushare 8000 Permission Context

The probe loaded `TUSHARE_TOKEN` only to check and call the API. The token value was not printed or written.

Probe summary:

| Item | Result |
|---|---|
| `TUSHARE_TOKEN` | present |
| Candidate Tushare interfaces probed | 26 |
| Available interfaces | 22 |
| Callable but empty in sample | 1 |
| No-permission interfaces | 3 |
| Output file | `docs/recovery/SECOND_BATCH_TUSHARE_8000_API_MATRIX.csv` |

Important change from the old 5000-point context:

- Several interfaces marked `5000积分不可用` in the existing inventory are now callable at 8000 points, including `ths_index`, `ths_member`, `dc_concept_cons`, `dc_index`, `ths_hot`, `limit_list_ths`, `limit_step`, `moneyflow_ind_*`-adjacent board interfaces represented by the concept/THS probes, and related 6000/8000-point datasets.
- `news`, `anns_d`, and `cctv_news` still returned no-permission responses in this probe.

## 4. Reviewed Documents and Existing Interface Inventory

Core documents reviewed:

| File | Use in this review |
|---|---|
| `docs/recovery/SECOND_BATCH_SCOPE_REVIEW.md` | Second-batch P0/P1/P2 scope and 300450 regression evidence. |
| `docs/recovery/SECOND_BATCH_DATA_SOURCE_GOVERNANCE_DESIGN.md` | String-compatible contract and stability/accuracy/coverage principles. |
| `docs/recovery/SECOND_BATCH_P0_INDUSTRY_COMPARISON_RESULT.md` | Current P0 header fix and current `industry_ranking / market / market_wide` label. |
| `docs/recovery/SECOND_BATCH_BUSINESS_RISK_BACKLOG.md` | Previously recorded function-level backlog. |
| `docs/recovery/DATA_SOURCE_INVENTORY.md` and `.csv` | Current source, return format, fallback, and failure behavior for candidate functions. |
| `docs/recovery/tushare_pro_inventory/TUSHARE_PRO_FULL_INTERFACE_INVENTORY.csv` | Full local Tushare API inventory and candidate selection. |
| `docs/recovery/tushare_pro_inventory/TUSHARE_PRO_5000_POINTS_AVAILABLE.csv` | Comparison against previous 5000-point state. |
| `docs/recovery/tushare_pro_inventory/MIN_AGENT_REGRESSION_RESULT_300450.md` and `.csv` | 300450 tool path evidence and P0 trigger. |
| `docs/recovery/tushare_pro_inventory/MIN_AGENT_REGRESSION_COMPARISON_300450.md` | Remaining second-batch risk after first-batch fix. |
| `tradingagents/dataflows/tushare_client.py` | Safe token lookup, short error normalization, and cache controls for the probe. |
| `tradingagents/dataflows/a_stock.py` | Current implementation of all eight candidate functions. |
| `tradingagents/dataflows/interface.py` | Function exposure and routing. |

## 5. Probe Method

Probe script:

```bash
.venv/bin/python scripts/recovery/run_second_batch_tushare_api_probe.py
```

Probe properties:

- uses the project `TushareClient`;
- disables local Tushare cache with `TUSHARE_ENABLE_CACHE=0`;
- probes only compact fields;
- writes only the summarized CSV matrix;
- does not write raw API payloads or raw response files;
- does not print or persist token values;
- classifies no-permission, empty, and error paths without raw stack text.

Sample symbols:

- `300450.SZ`
- `600519.SH`
- `688981.SH`

Sample dates:

- current date basis: `2026-07-08`;
- recent weekday windows for daily/event data;
- 30-day, 90-day, and 365-day windows where the API semantics required history.

## 6. Candidate Tushare Interfaces

The probe focused on interfaces that can improve the eight functions on stability, accuracy, or coverage grounds.

| Area | Interfaces probed |
|---|---|
| Industry / concept / board | `index_classify`, `index_member_all`, `ci_index_member`, `ths_index`, `ths_member`, `dc_concept_cons`, `dc_index` |
| News / announcement / information | `news`, `major_news`, `anns_d`, `cctv_news` |
| Northbound / stock-connect flow | `moneyflow_hsgt`, `hsgt_top10`, `hk_hold` |
| Hot stocks / limit-up / market heat | `limit_list_d`, `ths_hot`, `limit_list_ths`, `limit_step` |
| Dragon-tiger board | `top_list`, `top_inst` |
| Shareholder / F10-like data | `stk_holdernumber`, `stk_holdertrade`, `top10_holders`, `top10_floatholders`, `stk_managers`, `stk_rewards` |

## 7. Interface Probe Results

Detailed results are in:

- `docs/recovery/SECOND_BATCH_TUSHARE_8000_API_MATRIX.csv`

Compact result table:

| Interface | Required points | Status | Rows | Fit summary |
|---|---:|---|---:|---|
| `index_classify` | 2000 | available | 165 | Industry taxonomy; useful but not peer metrics by itself. |
| `index_member_all` | 2000 | available | 3 | Exact symbol-to-SW-industry mapping for sampled stocks. |
| `ci_index_member` | 5000 | available | 3 | Supplemental CITIC industry mapping. |
| `ths_index` | 6000 | available | 1003 | THS industry/concept index catalog. |
| `ths_member` | 6000 | available | 169 | THS membership by component stock; broad concept/industry help. |
| `dc_concept_cons` | 6000 | available | 940 | Exact stock-to-concept membership candidate. |
| `dc_index` | 6000 | available | 1023 | Concept board performance supplement. |
| `news` | unclear | no_permission | 0 | Not usable at current permission state. |
| `major_news` | unclear | available | 299 | Market/global news fit; not stock-specific news. |
| `anns_d` | unclear | no_permission | 0 | Company announcements unavailable in this probe. |
| `cctv_news` | unclear | no_permission | 0 | Unavailable in this probe. |
| `moneyflow_hsgt` | 2000 | available | 20 | Exact market-level northbound/southbound flow. |
| `hsgt_top10` | unclear | empty | 0 | Callable path, but sampled stocks returned empty. |
| `hk_hold` | 120 | available | 2 | Stock-connect holdings, not same-day flow. |
| `limit_list_d` | 5000 | available | 86 | Limit-up/down supplement for hot-stock route. |
| `ths_hot` | 6000 | available | 100 | Closest Tushare match for hot-stock ranking. |
| `limit_list_ths` | 8000 | available | 31 | 8000-point THS limit-up pool with reason text. |
| `limit_step` | 8000 | available | 484 | Consecutive limit-up ladder. |
| `top_list` | 2000 | available | 90 | Exact dragon-tiger daily event list. |
| `top_inst` | 5000 | available | 925 | Dragon-tiger institution/seat detail supplement. |
| `stk_holdernumber` | 600 | available | 14 | Shareholder count. |
| `stk_holdertrade` | 2000 | available | 3 | Important shareholder increase/decrease records. |
| `top10_holders` | 2000 | available | 649 | Top ten shareholders. |
| `top10_floatholders` | 2000 | available | 1113 | Top ten floating shareholders. |
| `stk_managers` | 2000 | available | 57 | Management roster. |
| `stk_rewards` | 2000 | available | 2333 | Management compensation and holdings. |

## 8. Function-Level Replacement / Supplement / Keep Assessment

| Function | Current source | Current main issue | Tushare replacement candidates | Tushare supplement candidates | Recommended conclusion |
|---|---|---|---|---|---|
| `get_industry_comparison` | Eastmoney push2 all-market industry ranking with 5B contract header | Current body is industry ranking, not true target-stock industry comparison. | No single exact replacement was validated for full comparison. | `index_member_all`, `ci_index_member`, `ths_index`, `ths_member`, `dc_index` | `hybrid_source` plus `rename_or_semantic_correction_first` if peer comparison is not implemented. |
| `get_news` | Eastmoney search; Sina fallback | Current source is stock-news text, but failures/empty need contract. | None validated. `news` no permission; `anns_d` no permission; `major_news` is not stock-specific. | `major_news` only for market/global context, not stock-specific replacement. | `keep_current_with_contract`. |
| `get_hot_stocks` | Direct THS hot-stock endpoint | Current direct HTTP can fail outside contract; source is all-market hot list. | `ths_hot` | `limit_list_ths`, `limit_step`, `limit_list_d` | `replace_with_tushare` or `hybrid_source`, with Tushare as preferred primary candidate. |
| `get_northbound_flow` | Direct THS hsgtApi plus local cache | Market-level flow with local cache and explanatory signal text. | `moneyflow_hsgt` | `hk_hold`, possibly `hsgt_top10` when data exists | `replace_with_tushare` for market-level flow; optional stock-connect supplements. |
| `get_concept_blocks` | Baidu PAE related-block endpoint | Third-party endpoint can return plain errors; stock-to-concept coverage and units need clearer contract. | `dc_concept_cons` | `ths_member`, `ths_index`, `dc_index` | `replace_with_tushare` or `hybrid_source`; Tushare can cover symbol-to-concept membership. |
| `get_global_news` | CLS wire plus Eastmoney 7x24 | Market/global news needs stable contract and freshness bounds. | No full replacement validated. | `major_news` | `hybrid_source` or `supplement_with_tushare`; do not use company announcements as news. |
| `get_insider_transactions` | mootdx F10 shareholder research | Function name implies insider transactions, current body is shareholder/F10 text. | `stk_holdertrade` for important shareholder changes | `top10_holders`, `top10_floatholders`, `stk_holdernumber`, `stk_managers`, `stk_rewards` | `rename_or_semantic_correction_first` plus Tushare-backed `shareholder_f10` data. |
| `get_dragon_tiger_board` | Eastmoney datacenter | Event empty and partial seat failures need clearer status. | `top_list` | `top_inst` | `replace_with_tushare`, with `no_event` and `partial_data` handling. |

## 9. Per-Function Detail

### `get_industry_comparison`

Tushare can now improve accuracy because `index_member_all` returned current SW industry membership for all three sampled stocks. This means a later code pass can resolve:

- requested symbol;
- SW industry hierarchy;
- peer universe or industry label.

However, the probe did not validate a single Tushare interface that directly returns a complete "target stock vs industry peers" comparison. The best next step is a hybrid design:

1. use `index_member_all` as the source of symbol-to-industry mapping;
2. use `index_classify` or `ci_index_member` as taxonomy fallback/supplement;
3. use Tushare board/industry/concept datasets where the body is a ranking or board performance table;
4. keep the current 5B contract label as `industry_ranking / market / market_wide` until peer comparison is actually implemented.

Recommended 5B follow-up:

- do not claim true `industry_comparison` unless the implementation resolves target industry and constructs a peer/industry comparison body;
- otherwise retain the current semantic correction in the header.

### `get_news`

The current Tushare permission state does not provide a clean stock-specific news replacement:

- `news`: no permission;
- `anns_d`: no permission;
- `major_news`: available, but market/global and not symbol-specific;
- `cctv_news`: no permission.

Do not replace stock news with `major_news`, and do not use announcements as news unless the tool contract declares a different `data_type`.

Recommended 5B follow-up:

- keep Eastmoney/Sina source for now;
- add the standard contract header;
- separate `empty`, `invalid_input`, fallback, and technical errors;
- only use `major_news` in `get_global_news` or a clearly market/global context.

### `get_hot_stocks`

Tushare is now a good fit for this route:

- `ths_hot` returned 100 compact rows and matches hot ranking semantics;
- `limit_list_ths` is an 8000-point API and returned rows;
- `limit_step` and `limit_list_d` can supplement the market heat / limit-up angle.

Recommended 5B follow-up:

- replace direct THS HTTP primary call with Tushare `ths_hot`;
- optionally supplement with `limit_list_ths` for limit-up pool fields and `limit_step` for consecutive limit-up counts;
- keep the string-compatible contract and mark `query_target=market`, `coverage=market_wide`.

### `get_northbound_flow`

`moneyflow_hsgt` is an exact fit for the current market-level northbound-flow function:

- it returned 20 rows over the recent 30-day sample;
- key fields include `hgt`, `sgt`, `north_money`, and `south_money`;
- it avoids the current direct THS HTTP and local-cache dependency for daily history.

`hk_hold` is useful only as a stock-connect holding supplement, not a replacement for flow. `hsgt_top10` was callable but empty for sampled symbols/windows.

Recommended 5B follow-up:

- replace current market-level flow source with `moneyflow_hsgt`;
- decide separately whether to add stock-level holdings as optional body sections;
- remove source-generated investment-direction wording while keeping numeric data.

### `get_concept_blocks`

Tushare can materially improve stability and coverage:

- `dc_concept_cons` returned rows for all sampled stocks and directly supports stock-to-concept membership;
- `ths_member` returned membership rows by component stock;
- `dc_index` and `ths_index` can supplement board/index metadata and daily board performance.

Recommended 5B follow-up:

- use `dc_concept_cons` as the primary candidate for symbol-to-concept membership;
- use `ths_member` as fallback or supplemental membership if fields are useful;
- use `dc_index` only for board-level performance, not as a substitute for membership;
- express `trade_date`, membership date, units, and board scope in the header/body.

### `get_global_news`

`major_news` is available and can supplement market/global news. It should not be used as a replacement for stock-specific `get_news`.

Recommended 5B follow-up:

- consider a hybrid `get_global_news` source: current CLS/Eastmoney 7x24 plus Tushare `major_news`;
- add contract fields for `data_type=global_news`, `query_target=macro` or `market`, and freshness;
- keep empty and technical-error outputs structured.

### `get_insider_transactions`

Tushare has several stable A-share shareholder and management datasets:

- `stk_holdertrade` is the closest fit for important shareholder increase/decrease activity;
- `top10_holders`, `top10_floatholders`, and `stk_holdernumber` are broad shareholder/F10-like datasets;
- `stk_managers` and `stk_rewards` can supplement management roster and holdings, but they are not transaction data.

Recommended 5B follow-up:

- correct the visible contract semantics to `data_type=shareholder_f10` or an equivalent A-share shareholder label;
- use `stk_holdertrade` when the function needs transaction-like shareholder changes;
- use top-ten shareholder and shareholder count data for stable F10-style context;
- preserve function compatibility for now, but consider future tool naming cleanup.

### `get_dragon_tiger_board`

Tushare is a usable replacement candidate:

- `top_list` returned daily dragon-tiger event rows;
- `top_inst` returned seat/institution detail rows;
- the APIs fit event lookup and can support `no_event` vs `partial_data`.

Recommended 5B follow-up:

- replace Eastmoney datacenter calls with Tushare `top_list` plus `top_inst`;
- implement lookback query logic by trading date iteration or calendar resolution;
- return `status=no_event` when the stock is not on the board during the window;
- return `status=partial_data` if the list is present but seat detail is unavailable.

## 10. Recommended Development Route After 5B-P0

Recommended route:

1. `get_northbound_flow`: replace direct THS hsgtApi/local-cache path with Tushare `moneyflow_hsgt`; this is the cleanest exact data-type match.
2. `get_concept_blocks`: replace Baidu PAE primary path with `dc_concept_cons`, with `ths_member`/`dc_index` only where their fields match the declared body.
3. `get_hot_stocks`: move primary source to Tushare `ths_hot`; supplement with `limit_list_ths` and `limit_step` as separate sections if needed.
4. `get_dragon_tiger_board`: replace Eastmoney datacenter with `top_list`/`top_inst`, with event-empty and partial-detail contracts.
5. `get_insider_transactions`: perform semantic correction to shareholder/F10-style data, then use Tushare shareholder APIs.
6. `get_global_news`: add contract and optionally supplement with `major_news`.
7. `get_news`: keep current source with contract until a stock-specific Tushare news/announcement permission is available or a proper announcement-specific tool is introduced.
8. `get_industry_comparison`: design an accuracy upgrade separately if true peer comparison is required; otherwise retain current corrected `industry_ranking` label.

## 11. Suggested Priority for P1/P2 Code Changes

Suggested next P1/P2 implementation order:

| Order | Function | Reason |
|---:|---|---|
| 1 | `get_northbound_flow` | `moneyflow_hsgt` is available and matches the current market-level function. |
| 2 | `get_concept_blocks` | `dc_concept_cons` is available and directly resolves stock-to-concept membership. |
| 3 | `get_hot_stocks` | `ths_hot`, `limit_list_ths`, and `limit_step` are available at 8000 points. |
| 4 | `get_dragon_tiger_board` | `top_list` and `top_inst` are available and fit the event workflow. |
| 5 | `get_insider_transactions` | Tushare data is available, but function semantics should be corrected first. |
| 6 | `get_global_news` | `major_news` is useful as supplement, not a full replacement. |
| 7 | `get_news` | No Tushare stock-news replacement was validated in this permission state. |
| 8 | `get_industry_comparison` | P0 stability is already fixed; accuracy upgrade needs a separate peer-comparison design. |

## 12. Risks and Open Questions

Open questions for the user or next design pass:

| Question | Why it matters |
|---|---|
| Should `get_industry_comparison` become a true peer comparison tool, or remain an industry-ranking tool with corrected metadata? | Tushare can resolve industry membership, but comparison logic still needs a defined body. |
| Should `get_insider_transactions` keep its current function name for compatibility while declaring A-share shareholder semantics? | Tushare can replace raw F10 text, but the current name is not a precise A-share label. |
| Should stock-connect holdings be included in `get_northbound_flow`, or kept separate from market-level flow? | `hk_hold` is holdings, while `moneyflow_hsgt` is flow. |
| Should `get_global_news` be hybrid, or should it stay current-source-only with contract? | `major_news` is available but has different freshness/source scope than CLS/Eastmoney 7x24. |
| Should company announcements become a separate future tool if `anns_d` permission is later available? | Announcements are not ordinary news and should not silently replace `get_news`. |

## 13. Final Recommendation

Do not blindly add headers to all old second-batch sources. The 8000-point probe shows that several better Tushare-backed paths are now available.

Recommended classification:

| Classification | Functions |
|---|---|
| `replace_with_tushare` | `get_northbound_flow`, `get_dragon_tiger_board` |
| `replace_with_tushare` or `hybrid_source` | `get_hot_stocks`, `get_concept_blocks` |
| `supplement_with_tushare` | `get_global_news` |
| `keep_current_with_contract` | `get_news` |
| `rename_or_semantic_correction_first` plus Tushare data | `get_insider_transactions` |
| `hybrid_source` or `rename_or_semantic_correction_first` | `get_industry_comparison` |

The next code pass should still keep the established 5B boundary: data-source layer only, string-compatible contract output, no prompt changes, no Bull/Bear changes, no Quality Gate changes, and no new trading recommendation rules.
