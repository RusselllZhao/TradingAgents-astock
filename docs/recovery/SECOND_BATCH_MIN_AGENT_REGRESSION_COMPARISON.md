# SECOND_BATCH_MIN_AGENT_REGRESSION_COMPARISON

- Stage: `5C-3`
- Date: 2026-07-08
- Branch: `recovery/data-source-only`
- Baseline commit: `625ff37`
- Result source: `docs/recovery/SECOND_BATCH_MIN_AGENT_REGRESSION_RESULT.md`
- Prior comparison source: `docs/recovery/tushare_pro_inventory/MIN_AGENT_REGRESSION_COMPARISON_300450.md`

This comparison evaluates whether second-batch data-source governance improved the minimal Agent path. It is not an investment view.

## 1. Summary

Second-batch bottom-level data-source pollution is controlled in the tested minimal Agent path.

All three stocks completed the minimal Agent workflow:

- `300450` / 先导智能
- `600519` / 贵州茅台
- `688981` / 中芯国际

No raw HTML, traceback, proxy stack, `HTTPSConnectionPool`, `ProxyError`, old `read_html` exception, bare `No data found`, raw exception text, oversized technical error, or real token/API key value appeared in final report sections or tool-call heads.

The key improvement versus the prior 300450 minimal regression is `get_industry_comparison`: it still fails technically at the Eastmoney source in this environment, but it now returns a bounded Data Source Contract `technical_error` instead of Eastmoney proxy-style raw text.

## 2. Comparison Against Prior 300450 Run

| Dimension | Prior 300450 minimal regression | Current 5C 300450 regression | Assessment |
|---|---|---|---|
| Workflow completion | passed | passed | unchanged, still passes |
| `get_industry_comparison` tool-layer behavior | Eastmoney proxy-style ordinary error text appeared in tool call record | `status: technical_error`, raw details suppressed | improved |
| Raw proxy/network stack in final report | not observed | not observed | unchanged clean |
| Raw proxy/network stack in tool output | observed for `get_industry_comparison` | not observed; short contract only | improved |
| Second-batch contract header visibility | not present for several tools | present for reached second-batch tools | improved |
| Market-wide source labeling | previously ambiguous for some tools | visible through contract on reached tools | improved |
| Agent no-event consumption | risk was known but not fully governed | no-event entered investment narrative | still present as consumption-layer risk |

## 3. Cross-Stock Differences

| Ticker | Result | Second-batch tools reached | Notable behavior |
|---|---|---|---|
| `300450` | passed | `get_industry_comparison`, `get_northbound_flow`, `get_concept_blocks`, `get_hot_stocks`, `get_dragon_tiger_board` | Clearest consumption risk: dragon-tiger `no_event` was used as low tour-capital / low catalyst context. |
| `600519` | passed | same reached second-batch tool set | No-event was described as normal for a large-cap blue chip but also used as no tour-capital speculation. One English `bullish` term appeared in Agent debate text, not source output. |
| `688981` | passed | same reached second-batch tool set | No-event was mostly treated as neutral / non-tour-capital context; industry comparison failure was noted as unavailable data. |

The minimal analyst set did not call `get_news`, `get_global_news`, or `get_insider_transactions`. Their bottom-level contract smoke tests remain the current evidence for those three functions until a broader Agent path includes them.

## 4. Raw Error and Token Check

The 5C regression did not observe:

- raw HTML;
- traceback;
- `HTTPSConnectionPool`;
- `ProxyError`;
- proxy stack;
- raw exception text;
- anti-scraping page text;
- oversized technical error text;
- real token/API key value;
- bare `No data found`;
- old Tonghuashun `read_html` exception;
- uncompressed Eastmoney proxy-style error.

This supports the conclusion that second-batch stability governance is effective in the reached minimal Agent path.

## 5. Contract Misread / Consumption Risk

Observed consumption risks:

| Risk | Observed? | Notes |
|---|---|---|
| `technical_error` used as factual evidence | no direct evidence | Reports mention missing/failed industry comparison data, but do not include raw stack or turn the failure itself into a market fact. |
| `no_event` interpreted as investment context | yes | Dragon-tiger no-event was used as tour-capital / catalyst context, especially for `300450`. |
| `industry_ranking / market / market_wide` claimed as true target-stock peer comparison | no direct evidence | Reports generally treated industry comparison as unavailable rather than claiming a resolved peer comparison. |
| `global_news` treated as stock-specific news | not reached | `get_global_news` was not called by the minimal analyst set. |
| `shareholder_f10` treated as US-style insider transactions | not reached | `get_insider_transactions` was not called by the minimal analyst set. |
| market-level northbound flow treated as stock-level holding | no direct evidence | Northbound market data was used as market context; no literal stock-level holding claim from this tool was observed. |
| hot-stock market-wide list treated as target-only data | mixed but bounded | Reports used not-in-hot-list as attention/catalyst context. This is Agent interpretation, not raw data-source pollution. |
| concept membership mixed with board performance | no direct evidence | Concept output was used as membership / theme context. |
| news fallback / partial-data treated as news fact | not reached | `get_news` and `get_global_news` were not called. |

Interpretation:

- Data-source pollution is controlled.
- Agent consumption of contract states is not fully controlled by data-source changes alone.
- The clearest remaining consumption issue is `no_event` being woven into investment reasoning.

## 6. The Three Deferred Issues

These issues were marked and not executed:

| Deferred issue | 5C status |
|---|---|
| `get_industry_comparison` accuracy upgrade | not performed; current behavior remains `industry_ranking / market / market_wide` plus technical contract |
| Tushare stock-news permission problem | not retried; `get_news` remains Eastmoney/Sina |
| `get_global_news` hybrid `partial_data` behavior | not redesigned |

## 7. Recommendation

Recommended next step:

1. Treat second-batch source-level stability governance as validated for the reached minimal Agent path.
2. Do not change Agent prompts, Bull/Bear logic, Quality Gate, or trading recommendation rules solely because 5C output contains strong investment language. That language comes from the existing Agent layers, which were intentionally out of scope.
3. Before wider Agent regression, decide whether to run `get_industry_comparison` accuracy upgrade. The current technical contract works, but the function still does not implement target-stock peer comparison.
4. If the project wants to reduce contract-state interpretation, plan a separate Agent consumption-side design stage. The concrete evidence is dragon-tiger `no_event` being used as tour-capital / catalyst context.
5. A broader Agent regression can be useful after the industry-comparison decision, especially with an analyst set that reaches `get_news`, `get_global_news`, and `get_insider_transactions`.

## 8. Final Conclusion

For the tested minimal Agent configuration, second-batch data-source governance prevented raw technical artifacts from entering Agent-visible reports. The remaining risk is not raw data-source pollution; it is upper-layer interpretation of structured contract states and market/event-level context.
