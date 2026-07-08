# SECOND_BATCH_SCOPE_REVIEW

- Review date: 2026-07-08
- Branch: `recovery/data-source-only`
- HEAD at review start: `cbfd4c9`
- Stage: `5A-0`
- Scope: read-only scope review before second-batch business-risk and tool-contract governance.

## 1. Review Purpose

This review consolidates the remaining second-batch data contract and Agent-consumption risks after the first Tushare replacement batch and the `300450` minimal Agent regression. It is intended to define scope, priority, evidence, and design direction before any code change.

This review intentionally does not modify business code, prompts, Quality Gate, Bull/Bear debate logic, or Agent orchestration.

## 2. First-Batch Completion Summary

The first batch is complete for the six targeted A-share dataflow functions:

| Function | Current source | Evidence |
|---|---|---|
| `get_balance_sheet` | Tushare `balancesheet` | `docs/recovery/tushare_pro_inventory/TUSHARE_PRO_FIRST_BATCH_HANDOFF.md`; `TUSHARE_PRO_FIRST_BATCH_REGRESSION_RESULT.md` |
| `get_cashflow` | Tushare `cashflow` | same |
| `get_income_statement` | Tushare `income` | same |
| `get_fundamentals` | Tushare `daily_basic` + `stock_basic` | same |
| `get_fund_flow` | Tushare `moneyflow`, fallback `moneyflow_dc` | same |
| `get_profit_forecast` | Tushare `report_rc` sell-side forecast aggregation | same |

Regression evidence:

- `TUSHARE_PRO_FIRST_BATCH_REGRESSION_RESULT.md` records `passed` with `18/18` bottom-level dataflow calls passing.
- `MIN_AGENT_REGRESSION_RESULT_300450.md` records a successful single-stock Agent run for `300450`, with all six first-batch replacement functions invoked and clean Tushare-backed outputs consumed.
- `MIN_AGENT_REGRESSION_COMPARISON_300450.md` concludes the first-batch pollution issues disappeared for the tested minimal Agent path.

## 3. Read Documents

All requested documents were present and read. No required document was missing.

| File | Status | Notes |
|---|---|---|
| `docs/recovery/DATA_SOURCE_INVENTORY.md` | read | Source inventory and route/fallback findings. |
| `docs/recovery/DATA_SOURCE_INVENTORY.csv` | read | Full function-level source/contract matrix. |
| `docs/recovery/DATA_SOURCE_SMOKE_TEST_RESULTS.md` | read | Stage 2 smoke results and snippets. |
| `docs/recovery/DATA_SOURCE_FAILURE_CASES.md` | read | Failure-like ordinary-string returns. |
| `docs/recovery/DATA_SOURCE_AGENT_MISREAD_RISKS.md` | read | Misread risks and signal-language findings. |
| `docs/recovery/DATA_SOURCE_ISSUE_CLASSIFICATION.md` | read | A/B/C/D classification and first-batch boundary. |
| `docs/recovery/FIRST_BATCH_TECH_FIX_CANDIDATES.md` | read | First-batch inclusion and second-batch deferrals. |
| `docs/recovery/SECOND_BATCH_BUSINESS_RISK_BACKLOG.md` | read | Second-batch backlog and suggested metadata. |
| `docs/recovery/tushare_pro_inventory/TUSHARE_PRO_FIRST_BATCH_HANDOFF.md` | read | First-batch handoff and guardrails. |
| `docs/recovery/tushare_pro_inventory/TUSHARE_PRO_FIRST_BATCH_CODE_AUDIT.md` | read | First-batch code audit and unchanged areas. |
| `docs/recovery/tushare_pro_inventory/TUSHARE_PRO_FIRST_BATCH_REGRESSION_RESULT.md` | read | `18/18` regression result. |
| `docs/recovery/tushare_pro_inventory/MIN_AGENT_REGRESSION_PRECHECK_300450.md` | read | Minimal Agent run precheck and exposed tools. |
| `docs/recovery/tushare_pro_inventory/MIN_AGENT_REGRESSION_RESULT_300450.md` | read | Successful `300450` run and observed non-first-batch risk. |
| `docs/recovery/tushare_pro_inventory/MIN_AGENT_REGRESSION_RESULT_300450.csv` | read | Tool-call rows; `get_industry_comparison` proxy flag. |
| `docs/recovery/tushare_pro_inventory/MIN_AGENT_REGRESSION_COMPARISON_300450.md` | read | First-batch issue comparison and remaining second-batch risks. |
| `tradingagents/dataflows/a_stock.py` | read-only | Current implementation of candidate functions. |
| `tradingagents/dataflows/interface.py` | read-only | Route and fallback behavior. |
| `tradingagents/agents/` and `tradingagents/graph/` | read-only sampled | Tool exposure paths for fundamentals, news, policy, hot-money, lockup, and graph tool nodes. |

## 4. Second-Batch Candidate Function List

Mandatory candidates covered in this review:

1. `get_news`
2. `get_global_news`
3. `get_hot_stocks`
4. `get_northbound_flow`
5. `get_concept_blocks`
6. `get_industry_comparison`
7. `get_insider_transactions`
8. `get_dragon_tiger_board`

Additional cross-cutting items retained from the backlog:

- `route_to_vendor`: not a candidate data source function, but it is the common path where text failures remain indistinguishable from successful tool outputs.
- `get_profit_forecast` and `get_fund_flow`: first-batch technical defects are fixed, but the second-batch backlog still records business-semantics follow-ups. They are not prioritized in this review because the user-specified second-batch candidate set focuses on the eight functions above.
- `get_lockup_expiry`: documented as a normal event-empty case similar to `get_dragon_tiger_board`; not included in the main eight-function priority list, but relevant to future `empty_reason` design.

## 5. Issue Type Matrix

Labels used:

- `technical_failure_contract`: technical failure returned as ordinary string, HTML/proxy/traceback, or free-text error.
- `empty_result_contract`: empty result lacks structured `no_data` / `empty_reason`.
- `scope_mismatch_risk`: market/industry/topic data can be individualized.
- `source_type_risk`: media/editorial/secondary information can be treated as primary fact.
- `signal_language_risk`: output contains strong `bullish` / `bearish` / signal language or tool descriptions encourage it.
- `stale_or_asof_risk`: missing or weak `as_of`, `trade_date`, `publish_time`, or freshness markers.
- `agent_consumption_risk`: correct output can still be over-interpreted by Agents.
- `low_priority_or_normal_empty`: event-type empty result is often normal.

| Function | Issue types |
|---|---|
| `get_news` | `empty_result_contract`, `source_type_risk`, `signal_language_risk`, `stale_or_asof_risk`, `agent_consumption_risk` |
| `get_global_news` | `empty_result_contract`, `scope_mismatch_risk`, `source_type_risk`, `stale_or_asof_risk`, `agent_consumption_risk` |
| `get_hot_stocks` | `technical_failure_contract`, `empty_result_contract`, `scope_mismatch_risk`, `source_type_risk`, `signal_language_risk`, `stale_or_asof_risk`, `agent_consumption_risk` |
| `get_northbound_flow` | `technical_failure_contract`, `empty_result_contract`, `scope_mismatch_risk`, `signal_language_risk`, `stale_or_asof_risk`, `agent_consumption_risk` |
| `get_concept_blocks` | `technical_failure_contract`, `empty_result_contract`, `scope_mismatch_risk`, `source_type_risk`, `stale_or_asof_risk`, `agent_consumption_risk` |
| `get_industry_comparison` | `technical_failure_contract`, `empty_result_contract`, `scope_mismatch_risk`, `stale_or_asof_risk`, `agent_consumption_risk` |
| `get_insider_transactions` | `technical_failure_contract`, `empty_result_contract`, `source_type_risk`, `stale_or_asof_risk`, `agent_consumption_risk` |
| `get_dragon_tiger_board` | `technical_failure_contract`, `empty_result_contract`, `source_type_risk`, `stale_or_asof_risk`, `agent_consumption_risk`, `low_priority_or_normal_empty` |

## 6. Function-Level Contract And Risk Review

| Function | Current source | Current return contract | Evidence | Risk and suggested direction |
|---|---|---|---|---|
| `get_news` | Eastmoney search, Sina fallback | Markdown string; no structured status; empty returns `No news found...`; source shown per article but no `source_type`, `is_official`, or confidence | `DATA_SOURCE_INVENTORY.csv`; `DATA_SOURCE_SMOKE_TEST_RESULTS.md` rows 11-12; `a_stock.py` lines 1296-1360 | Treat as media/secondary evidence. Add `status`, `scope=company_media`, `source_type=media`, `is_official=false/unknown`, `publish_time`, `query_match_quality`, and `empty_reason`. Also address invalid-code generic news risk observed with `999999`. |
| `get_global_news` | CLS wire, Eastmoney 7x24 | Markdown string; warning-only partial source failures; empty returns `No global news found`; market-level scope only implied by title | `DATA_SOURCE_INVENTORY.csv`; `DATA_SOURCE_SMOKE_TEST_RESULTS.md` row 13; `a_stock.py` lines 1366-1459 | Mark as `scope=market/macro`, not company fact. Add per-item `publish_time` and `source_type=media/wire`. Avoid downstream individual-stock causal claims without explicit linkage. |
| `get_hot_stocks` | Tonghuashun editorial hot-stock endpoint | Markdown string; API error returns `同花顺 API error`; empty returns `No hot stocks data...`; reason tags and theme frequency presented as text | `SECOND_BATCH_BUSINESS_RISK_BACKLOG.md`; `DATA_SOURCE_SMOKE_TEST_RESULTS.md` row 17; `a_stock.py` lines 1768-1844 | High Agent-consumption risk because editorial reason tags look causal. Add `scope=market_hot_list`, `source_type=editorial`, `confidence=weak`, `as_of/trade_date`, and structured empty/error handling. |
| `get_northbound_flow` | Tonghuashun hsgtApi plus local cache | Markdown string; realtime market-level flow; writes local cache; total positive/negative emits explicit bullish/bearish signal; errors return `Error fetching...` | `DATA_SOURCE_INVENTORY.csv`; `DATA_SOURCE_AGENT_MISREAD_RISKS.md`; `a_stock.py` lines 1904-2003 | High scope and signal risk. Remove or downgrade source-level `Signal` in a later code pass, or mark `conclusion_level=weak/derived`; add `scope=market`, `as_of`, `snapshot_date`, `cache_source`, and `empty_reason`. |
| `get_concept_blocks` | Baidu PAE related-block endpoint | Markdown string; `ResultCode` failure returns `Baidu PAE error`; empty returns `No concept/block data`; retrieved timestamp exists but no trade-date/as-of field or unit normalization | `DATA_SOURCE_FAILURE_CASES.md`; `DATA_SOURCE_SMOKE_TEST_RESULTS.md` rows 19-20; `a_stock.py` lines 2025-2087 | Concept and ratio fields are third-party classification and unclear units. Add `source_type=third_party_classification`, `scope=stock_classification_and_sector_snapshot`, `as_of`, `unit`, `confidence`, and structured technical errors. |
| `get_industry_comparison` | Eastmoney push2 industry board ranking | Markdown string; currently returns full industry ranking, not target-stock industry comparison; exceptions are appended as `行业对比查询失败: {e}` in normal output | `DATA_SOURCE_INVENTORY.csv`; `MIN_AGENT_REGRESSION_RESULT_300450.md`; `MIN_AGENT_REGRESSION_RESULT_300450.csv`; `a_stock.py` lines 2594-2658 | P0. The `300450` Agent run called it twice and recorded proxy-style text in tool-call heads. It is both a failure-contract problem and a naming/scope mismatch. Add short `technical_error`, `scope=market_sector_rank`, true target industry mapping or explicit `target_industry_unresolved`, and no raw exception/proxy text. |
| `get_insider_transactions` | mootdx F10 `股东研究` | Markdown/header plus raw F10 text; invalid input can return `Error retrieving...`; note says A-stock equivalent but output name still maps to insider transactions | `DATA_SOURCE_FAILURE_CASES.md`; `DATA_SOURCE_SMOKE_TEST_RESULTS.md` rows 14-15; `a_stock.py` lines 1465-1508 | Treat as shareholder/F10 data, not US-style insider trades. Add `source_type=f10_vendor`, `equivalent_only=true`, `scope=shareholder_research`, `as_of/update_date`, and structured error/empty status. |
| `get_dragon_tiger_board` | Eastmoney datacenter billboard details and seat details | Markdown string; list query failure appended in normal text; seat-detail exceptions are silently ignored; no-data returns `近N日未上龙虎榜` | `DATA_SOURCE_FAILURE_CASES.md`; `DATA_SOURCE_SMOKE_TEST_RESULTS.md` row 23; `DATA_SOURCE_ISSUE_CLASSIFICATION.md`; `a_stock.py` lines 2385-2506 | Event empty is often normal, so lower priority, but contract still needs `status=no_event`, `empty_reason=not_on_board`, `lookback_days`, and explicit partial-detail status if seats fail. |

## 7. 300450 Regression Evidence

The `300450` minimal Agent regression adds new second-batch evidence:

| Evidence | Source | Meaning |
|---|---|---|
| `get_industry_comparison` was called twice and returned Eastmoney proxy-style text in tool-call records | `MIN_AGENT_REGRESSION_RESULT_300450.md`; `MIN_AGENT_REGRESSION_RESULT_300450.csv` rows for `get_industry_comparison` with `proxy_stack_in_head=yes` | Ordinary-string technical failure contract still exists outside first batch. |
| The proxy-style text did not enter final report sections | `MIN_AGENT_REGRESSION_RESULT_300450.md`; `MIN_AGENT_REGRESSION_COMPARISON_300450.md` | No final-report pollution was observed in this run, but the tool layer remains unsafe. |
| `get_hot_stocks`, `get_concept_blocks`, `get_dragon_tiger_board`, and `get_northbound_flow` were called in the hot-money path | `MIN_AGENT_REGRESSION_RESULT_300450.csv` | These second-batch tools are reachable in realistic Agent execution, not just theoretical backlog items. |
| `get_news`, `get_hot_stocks`, market-level flow, and sector/topic tools remain semantically risky | `MIN_AGENT_REGRESSION_COMPARISON_300450.md` | Market-level and media/editorial data can still be woven into an individual-stock narrative. |

## 8. Priority Recommendation

### P0: Must Handle First

| Function | Reason |
|---|---|
| `get_industry_comparison` | Exposed in `300450` Agent regression; called twice; returned proxy-style ordinary text; function name promises stock industry comparison while implementation returns full market industry ranking; exposed through both fundamentals and hot-money paths. |

Recommended P0 treatment:

- First design the shared contract, then implement a minimal wrapper for this function.
- Do not let raw `HTTPSConnectionPool`, proxy, HTML, or traceback text pass through.
- Explicitly state `scope=market_sector_rank` unless true stock-to-industry resolution is added.
- If target industry is unresolved, state it as metadata instead of implying the ranking is the ticker's own industry comparison.

### P1: Handle Next

| Function | Reason |
|---|---|
| `get_news` | High-frequency exposure through social/news/policy/hot-money/lockup paths; media text and invalid-code generic-news behavior can be treated as company fact. |
| `get_hot_stocks` | Hot-money path exposure; market-level hot list and editorial reason tags can be individualized and over-causal. |
| `get_northbound_flow` | Hot-money path exposure; market-level flow and explicit bullish/bearish signal language create strong Agent-consumption risk. |
| `get_concept_blocks` | Called in `300450`; third-party concept/sector labels and `ratio` are easy to interpret as hard company fact or exact sector performance without unit/source confidence. |

### P2: Later Governance

| Function | Reason |
|---|---|
| `get_global_news` | Market/macro scope is risky but was not part of the `300450` selected minimal path; should be governed before enabling broader news/policy regressions. |
| `get_insider_transactions` | Naming/semantics issue is important, but event/source is more local than P1. Invalid-code error text also needs contract cleanup. |
| `get_dragon_tiger_board` | Event-type empty result is normal for many stocks; prioritize `empty_reason=no_event` and partial-seat-detail status rather than broad semantic redesign first. |

## 9. Should Code Be Changed Directly Now?

No.

The recommended next step is not immediate code modification. The evidence shows several different risk types sharing the same root problem: free-form text is carrying status, source, freshness, scope, fallback, confidence, and business semantics. Directly patching one function at a time without a shared contract would likely create inconsistent metadata and make Agent consumption harder to validate.

This does not mean P0 is optional. It means P0 should be implemented after a short second-batch contract design pass.

## 10. Recommended Next Step

Proceed to `5A-1`: second-batch contract design.

Suggested deliverables before code changes:

1. Define a lightweight output header schema usable inside existing string-returning tools, for example: `status`, `source`, `source_type`, `scope`, `as_of`, `trade_date`, `unit`, `fallback`, `empty_reason`, `confidence`, `conclusion_level`.
2. Define standardized short technical-error wording that suppresses raw proxy/HTML/traceback text.
3. Define normal empty-result taxonomy: `no_event`, `non_trading_day`, `no_coverage`, `not_applicable`, `source_empty`, `invalid_or_unresolved_ticker`.
4. Define source-type taxonomy: `official`, `exchange`, `vendor`, `media`, `editorial`, `third_party_classification`, `derived`, `local_cache`.
5. Apply the design first to `get_industry_comparison`, then P1 functions, with bottom-level smoke tests only.
6. Keep prompt, Quality Gate, Bull/Bear debate, and Agent orchestration unchanged until second-batch data contracts are stable.

## 11. Cross-check with ChatGPT Context Summary

| # | Claim | Status | Evidence file | Note |
|---:|---|---|---|---|
| 1 | First-batch six functions are complete. | match | `TUSHARE_PRO_FIRST_BATCH_HANDOFF.md`; `TUSHARE_PRO_FIRST_BATCH_CODE_AUDIT.md` | The six functions are listed as implemented, smoke-tested, and regression-tested. |
| 2 | First batch passed `18/18` bottom-level regression. | match | `TUSHARE_PRO_FIRST_BATCH_REGRESSION_RESULT.md` | Overall result is `passed (18/18 passed)`. |
| 3 | `300450` minimal Agent regression succeeded. | match | `MIN_AGENT_REGRESSION_RESULT_300450.md` | Result is `passed`; workflow completed with no run error. |
| 4 | `300450` exposed `get_industry_comparison` proxy-style error. | match | `MIN_AGENT_REGRESSION_RESULT_300450.md`; `MIN_AGENT_REGRESSION_RESULT_300450.csv`; `MIN_AGENT_REGRESSION_COMPARISON_300450.md` | Tool-call record shows `proxy_stack_in_head=yes`; final report did not include it. |
| 5 | Second-batch candidates cover `get_news`, `get_global_news`, `get_hot_stocks`, `get_northbound_flow`, `get_concept_blocks`, `get_industry_comparison`, `get_insider_transactions`, and `get_dragon_tiger_board`. | match | `SECOND_BATCH_BUSINESS_RISK_BACKLOG.md`; this review | All eight are covered. `get_dragon_tiger_board` was previously also classified as normal event-empty, so its priority is P2. |
| 6 | Still do not modify prompt / Quality Gate / Bull-Bear. | match | `FIRST_BATCH_TECH_FIX_CANDIDATES.md`; `SECOND_BATCH_BUSINESS_RISK_BACKLOG.md`; `TUSHARE_PRO_FIRST_BATCH_HANDOFF.md` | Multiple documents explicitly keep these areas out of scope. |
| 7 | Next should be second-batch design, not direct code change. | match | `SECOND_BATCH_BUSINESS_RISK_BACKLOG.md`; `MIN_AGENT_REGRESSION_COMPARISON_300450.md`; this review | Backlog recommends metadata design before prompt/Agent changes; this review recommends `5A-1` design before code. |

No mismatch with the repository evidence was found. Repository documents are treated as authoritative.

## 12. Still Requiring Human Confirmation

| Question | Why it matters |
|---|---|
| Should the second-batch contract remain string-header compatible, or should dataflow tools start returning structured dict/JSON objects? | Current tools and Agents expect strings; structured objects may require broader tool-consumption changes. |
| Should `get_industry_comparison` truly resolve the target stock's industry, or only rename/label the current market-sector ranking? | True resolution may require a new data source or Tushare industry membership mapping, which is a broader change. |
| Should `get_northbound_flow` remove signal language entirely, or retain it as `conclusion_level=weak/derived` metadata? | Removing it changes current report semantics; retaining it still risks overuse. |
| What source taxonomy should count as official for A-share facts: exchange公告, company公告, Tushare-provided announcements, media wires, or vendor F10? | Determines whether `get_news` can ever be used as primary evidence. |
| How strict should invalid-code validation be for news and concept functions? | `999999` news and Baidu PAE failures show that query matching can produce misleading but superficially successful results. |
| Should broader Agent regressions wait until P0/P1 data contracts are stabilized? | Broader regressions would call more risky tools and may generate noise before the contract is improved. |

## 13. Review Conclusion

Second-batch governance should start with data contracts, not prompt or Agent logic. The immediate P0 is `get_industry_comparison` because it is both empirically exposed by the `300450` minimal Agent run and contractually unsafe. The P1 group should then address high-exposure media, hot-list, market-flow, and concept-classification tools. P2 can handle broader market news, F10 shareholder semantics, and event-empty龙虎榜 behavior after the core contract shape is settled.
