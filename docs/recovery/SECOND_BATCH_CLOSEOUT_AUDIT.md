# SECOND_BATCH_CLOSEOUT_AUDIT

- Stage: `5B-Summary`
- Date: 2026-07-08
- Branch: `recovery/data-source-only`
- Baseline commit: `6735369`
- Scope: closeout audit and bottom-level smoke summary only.

## 1. Background

The second-batch data source governance work is now functionally complete for the eight scoped tools:

| Stage | Commit | Function / deliverable |
|---|---|---|
| 5A-0 | `ecfee0e` | second-batch scope review |
| 5A-1 | `ff311e8` | string-compatible Data Source Contract design |
| 5B-P0 | `a7de873` | `get_industry_comparison` technical contract |
| 5B-API | `7276ab2` | Tushare 8000 source-fit review |
| 5B-Plan | `766fc64` | post-Tushare implementation plan |
| 5B-1 | `b307427` | `get_northbound_flow` |
| 5B-2 | `a7a5e53` | `get_concept_blocks` |
| 5B-3 | `5d8306c` | `get_hot_stocks` |
| 5B-4 | `60f47b7` | `get_dragon_tiger_board` |
| 5B-5 | `6b878ae` | `get_insider_transactions` |
| 5B-6 | `8cf1890` | `get_global_news` |
| 5B-7 | `6735369` | `get_news` |

This audit cross-checks the result documents, `tradingagents/dataflows/a_stock.py`, `tradingagents/dataflows/interface.py`, and all eight existing bottom-level smoke scripts.

## 2. Scope and Boundary

This stage did not add functionality and did not modify business code.

Allowed in this stage:

- read recovery documents and dataflow code;
- run existing bottom-level dataflow smoke scripts;
- call Tushare Pro and current bottom-level data sources only through those smoke scripts;
- add this closeout audit document.

Not allowed and not performed:

- Agent, multi-Agent, or LLM runs;
- Agent prompt changes;
- Bull/Bear debate logic changes;
- Quality Gate changes;
- trading recommendation rule changes;
- changes under `agents`, `graph`, `cli`, or `web`;
- token/API key printing beyond present/missing status.

## 3. Changed Function Inventory

| Function | Stage | Current source | Contract semantics |
|---|---|---|---|
| `get_industry_comparison` | 5B-P0 | Eastmoney push2 | `data_type=industry_ranking`, `query_target=market`, `coverage=market_wide` |
| `get_northbound_flow` | 5B-1 | Tushare `moneyflow_hsgt` | `data_type=northbound_flow`, `query_target=market`, `coverage=market_wide` |
| `get_concept_blocks` | 5B-2 | Tushare `dc_concept_cons` | `data_type=concept_blocks`, `query_target=stock`, `coverage=individual_stock` |
| `get_hot_stocks` | 5B-3 | Tushare `ths_hot` | `data_type=hot_stocks`, `query_target=market`, `coverage=market_wide` |
| `get_dragon_tiger_board` | 5B-4 | Tushare `top_list` + `top_inst` | `data_type=dragon_tiger_event`, `query_target=event`, `coverage=event_lookup` |
| `get_insider_transactions` | 5B-5 | Tushare `stk_holdertrade` + `top10_holders` + `top10_floatholders` + `stk_holdernumber` | `data_type=shareholder_f10`, `query_target=stock`, `coverage=individual_stock` |
| `get_global_news` | 5B-6 | CLS + Eastmoney 7x24 + Tushare `major_news` | `data_type=global_news`, `query_target=market`, `coverage=market_wide` |
| `get_news` | 5B-7 | Eastmoney stock news + Sina fallback | `data_type=news`, `query_target=stock`, `coverage=individual_stock` |

All eight functions remain string-returning dataflow functions and now expose `# Data Source Contract` at the top of governed output.

## 4. Smoke Test Summary

Smoke tests were run on 2026-07-08 from the local recovery branch. Tushare token status was reported only as `present` where applicable; no token value was printed.

| Function | Stage | Current source | Data type | Query target | Coverage | Smoke script | Smoke result | Status observed | Raw artifact check | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| `get_industry_comparison` | 5B-P0 | Eastmoney push2 | `industry_ranking` | `market` | `market_wide` | `scripts/recovery/run_industry_comparison_contract_smoke.py` | PASS, 3/3 | `technical_error` | clean | External source failed, but raw details were suppressed and bounded. |
| `get_northbound_flow` | 5B-1 | Tushare `moneyflow_hsgt` | `northbound_flow` | `market` | `market_wide` | `scripts/recovery/run_northbound_flow_contract_smoke.py` | PASS, 1/1 | `ok` | clean | Market-level northbound/southbound flow only. |
| `get_concept_blocks` | 5B-2 | Tushare `dc_concept_cons` | `concept_blocks` | `stock` | `individual_stock` | `scripts/recovery/run_concept_blocks_contract_smoke.py` | PASS, 4/4 | `ok`, `invalid_input` | clean | Stock-to-concept membership only; invalid input guarded. |
| `get_hot_stocks` | 5B-3 | Tushare `ths_hot` | `hot_stocks` | `market` | `market_wide` | `scripts/recovery/run_hot_stocks_contract_smoke.py` | PASS, 1/1 | `ok` | clean | Hot-stock ranking only. |
| `get_dragon_tiger_board` | 5B-4 | Tushare `top_list` + `top_inst` | `dragon_tiger_event` | `event` | `event_lookup` | `scripts/recovery/run_dragon_tiger_board_contract_smoke.py` | PASS, 4/4 | `no_event`, `invalid_input` | clean | No-event is neutral and distinct from technical failure. |
| `get_insider_transactions` | 5B-5 | Tushare shareholder APIs | `shareholder_f10` | `stock` | `individual_stock` | `scripts/recovery/run_insider_transactions_contract_smoke.py` | PASS, 4/4 | `ok`, `invalid_input` | clean | Compatible function name retained; actual A-share shareholder/F10 semantics exposed. |
| `get_global_news` | 5B-6 | CLS + Eastmoney 7x24 + Tushare `major_news` | `global_news` | `market` | `market_wide` | `scripts/recovery/run_global_news_contract_smoke.py` | PASS, 1/1 | `partial_data` | clean | At least one source was unavailable, while other market/global news rows were returned. |
| `get_news` | 5B-7 | Eastmoney stock news + Sina fallback | `news` | `stock` | `individual_stock` | `scripts/recovery/run_news_contract_smoke.py` | PASS, 4/4 | `ok`, `invalid_input` | clean | Stock-specific news only; invalid input did not return generic news. |

Raw smoke output summary:

```text
run_industry_comparison_contract_smoke.py:
300450: PASS status=technical_error len=575 note=ok
600519: PASS status=technical_error len=575 note=ok
688981: PASS status=technical_error len=575 note=ok

run_northbound_flow_contract_smoke.py:
TUSHARE_TOKEN=present
northbound_flow: PASS status=ok len=1788 note=ok

run_concept_blocks_contract_smoke.py:
TUSHARE_TOKEN=present
300450: PASS status=ok len=1771 note=ok
600519: PASS status=ok len=947 note=ok
688981: PASS status=ok len=1012 note=ok
BADCODE: PASS status=invalid_input len=512 note=ok
SUMMARY: 4/4 PASS

run_hot_stocks_contract_smoke.py:
TUSHARE_TOKEN=present
hot_stocks: PASS status=ok len=13541 note=ok
SUMMARY: 1/1 PASS

run_dragon_tiger_board_contract_smoke.py:
TUSHARE_TOKEN=present
300450: PASS status=no_event len=536 note=ok
600519: PASS status=no_event len=536 note=ok
688981: PASS status=no_event len=536 note=ok
BADCODE: PASS status=invalid_input len=551 note=ok
SUMMARY: 4/4 PASS

run_insider_transactions_contract_smoke.py:
TUSHARE_TOKEN=present
300450: PASS status=ok len=3108 note=ok
600519: PASS status=ok len=3512 note=ok
688981: PASS status=ok len=3481 note=ok
BADCODE: PASS status=invalid_input len=649 note=ok
SUMMARY: 4/4 PASS

run_global_news_contract_smoke.py:
TUSHARE_TOKEN=present
global_news: PASS status=partial_data len=3049 note=ok
SUMMARY: 1/1 PASS

run_news_contract_smoke.py:
300450: PASS status=ok len=5836 note=ok
600519: PASS status=ok len=5521 note=ok
688981: PASS status=ok len=5812 note=ok
BADCODE: PASS status=invalid_input len=474 note=ok
SUMMARY: 4/4 PASS
```

Full bottom-level smoke result: PASS.

## 5. Contract Consistency Review

The audited functions consistently include the required header fields:

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

Observed statuses remain within the design taxonomy:

- `ok`
- `partial_data`
- `no_event`
- `invalid_input`
- `technical_error`

The smoke run did not observe malformed headers. It also verified the key Stage 5B distinctions:

- `technical_error` is separate from empty/no-event states;
- invalid stock input returns `invalid_input` or symbol-unresolved coverage instead of generic data;
- no dragon-tiger event returns `no_event`, not an investment interpretation;
- `get_global_news` remains market/global scoped;
- `get_news` remains stock-specific;
- `get_insider_transactions` exposes A-share shareholder/F10 semantics;
- `get_industry_comparison` remains honestly labeled as `industry_ranking`, not a resolved target-stock peer comparison.

## 6. Data Source Replacement Summary

Second-batch source changes now stand as follows:

| Function | Old source / issue | Current source / contract result |
|---|---|---|
| `get_industry_comparison` | Eastmoney proxy-style raw text could enter normal output. | Still Eastmoney push2, but technical failures are short and raw-suppressed. Actual output is labeled industry ranking. |
| `get_northbound_flow` | Direct THS hsgt API plus local runtime cache and source-level direction text. | Tushare `moneyflow_hsgt`; no local runtime cache; market-level flow only. |
| `get_concept_blocks` | Baidu PAE related-block endpoint with plain vendor errors. | Tushare `dc_concept_cons`; stock concept membership only. |
| `get_hot_stocks` | Direct THS hot endpoint and unstructured errors. | Tushare `ths_hot`; hot ranking only. |
| `get_dragon_tiger_board` | Eastmoney datacenter with unclear no-event and seat-detail failures. | Tushare `top_list` plus separated `top_inst` details. |
| `get_insider_transactions` | mootdx F10 raw text under potentially misleading insider-transaction name. | Tushare shareholder APIs with `shareholder_f10` semantics. |
| `get_global_news` | CLS/Eastmoney warnings and partial-source failures not fully structured. | CLS/Eastmoney plus Tushare `major_news`, separated into market/global sections. |
| `get_news` | Eastmoney/Sina stock-news path had unstructured fallback and invalid-input risk. | Same stock-specific sources with contract, fallback, invalid-input, and empty/error states. |

## 7. Remaining Known Limitations

Known remaining limitations are deliberate scope boundaries, not smoke failures:

- `get_industry_comparison` has only technical governance. Accuracy upgrade is still pending because the current function body is all-market industry ranking, not true target-stock industry peer comparison.
- `get_global_news` can return `partial_data` when one of CLS, Eastmoney 7x24, or Tushare `major_news` is unavailable. This is expected for a hybrid market-news source.
- `get_dragon_tiger_board` may return `no_event` for normal samples when the requested stocks did not appear in the lookback window. This is expected event-query behavior.
- `get_news` still depends on Eastmoney/Sina because Tushare stock-news and announcement interfaces were not available in the 8000-point probe.
- Second-batch tools are still string-compatible rather than dict/JSON, by design, to avoid Agent consumption changes.

## 8. No-Change Confirmation for Agent / Prompt / Bull-Bear / Quality Gate

This closeout stage changed no code and did not touch:

- Agent prompts;
- Bull/Bear debate logic;
- Quality Gate logic;
- trading recommendation rules;
- `tradingagents/agents/`;
- `tradingagents/graph/`;
- `cli`;
- `web`.

Only bottom-level smoke scripts were run. No Agent, multi-Agent, or LLM path was run.

## 9. Security and Raw Artifact Check

The smoke scripts and this audit checked for the following Agent-visible forbidden raw artifacts:

- raw HTML;
- traceback text;
- proxy stack text;
- raw exception text;
- anti-scraping page text;
- oversized technical error text;
- token/API key values.

No such artifact was observed in the smoke outputs. Tushare token state was printed only as `TUSHARE_TOKEN=present`.

The audit also found no source-level investment-direction wording in the governed function outputs and no prohibited evidence/confidence/conclusion labels in Agent-visible smoke output.

No `.env`, `.env.local`, `.cache`, raw HTML, local runtime cache, run log, token file, or API key file was added.

## 10. Recommendation Before Next Stage

Recommended next step:

1. Treat second-batch data source governance as closed at bottom-level smoke scope.
2. Before any Agent-level regression, decide whether to perform `get_industry_comparison` accuracy upgrade:
   - keep it as an industry-ranking tool with current labels; or
   - implement true target-stock industry/peer comparison using a confirmed symbol-to-industry mapping route.
3. If moving to Agent-level regression, keep the same boundary: do not change prompts, Bull/Bear logic, Quality Gate, or recommendation rules unless a separate stage explicitly approves that work.
