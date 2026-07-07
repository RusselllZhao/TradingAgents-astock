# Minimal Agent Regression Comparison for 300450

- Stage: 4C-3
- Target ticker: `300450`
- Target company: `先导智能`
- Regression result source: `docs/recovery/tushare_pro_inventory/MIN_AGENT_REGRESSION_RESULT_300450.md`
- Runtime evidence root: `.cache/recovery/min_agent_regression_300450/20260707_215342`
- This comparison evaluates whether prior data-source contamination issues disappeared. It is not an investment view.

## Summary

The first-batch Tushare data-source pollution issues are materially fixed for the tested `300450` minimal Agent run. All six replaced functions were invoked and returned clean Tushare-backed outputs. No first-batch HTML, traceback, token value, push2 proxy stack, bare `No data found`, or old Tonghuashun `read_html` failure entered the final Agent report.

However, second-batch risks remain visible. In this run, `get_industry_comparison` returned Eastmoney proxy-style error text at the tool layer. It did not appear in the final report, but it confirms that non-first-batch ordinary-string failure contracts still need later treatment.

## Issue-by-Issue Comparison

| Prior issue | Status | Evidence summary |
|---|---|---|
| 1. Data-source failure, unverifiable data, or empty result entered Agent as ordinary natural language | improved | First-batch functions did not do this. A non-first-batch function, `get_industry_comparison`, still returned ordinary proxy-style failure text at tool level. |
| 2. Agent may use unverifiable data as Bear-side factual evidence | improved | No `technical_error`, `no_data`, `no_coverage`, `partial_data`, HTML, traceback, or proxy stack appeared in the final report. Bear-side arguments used generated interpretations of financial/fund-flow data, not visible first-batch failure text. |
| 3. HTML / anti-bot page / exception stack / proxy error may enter report | improved | No HTML, traceback, or proxy stack appeared in final report text. Proxy-style text still appeared in `get_industry_comparison` tool output only. |
| 4. Fund-flow data source directly generates bullish / bearish strong signal | disappeared | For the first-batch data source, `get_fund_flow` used Tushare `moneyflow`, daily individual-stock scope, and did not return old push2 realtime signal text. The Agent still generated strong trading language from its prompts, which is outside first-batch data-source scope. |
| 5. Market-level data may be individualized | still_present | Hot-money flow still exposed `get_northbound_flow` and other market/sector tools; the Agent incorporated market-level flow into the individual-stock narrative. This is a second-batch business-risk item. |
| 6. News / media / second-hand information may be treated as first-hand fact | still_present | The run exposed `get_news`, `get_hot_stocks`, and related second-batch tools through the hot-money analyst. No first-batch change addresses this. |
| 7. Old `get_profit_forecast` may return Tonghuashun HTML exception text | disappeared | `get_profit_forecast` returned Tushare `report_rc` sell-side forecast aggregation; no HTML or `read_html` exception appeared. |
| 8. Old financial statements return bare `No data` for normal stocks | disappeared | `get_balance_sheet`, `get_cashflow`, and `get_income_statement` all returned `status: ok` Tushare outputs for `300450`. |
| 9. Old `get_fundamentals` may only return share counts while looking normal | disappeared | `get_fundamentals` returned Tushare `daily_basic + stock_basic` with core name, industry, market, valuation, market cap, turnover, and share fields. |
| 10. Old `get_fund_flow` may return Eastmoney push2 ProxyError long text | disappeared | `get_fund_flow` returned Tushare `moneyflow`; no push2 proxy stack appeared in the function output or final report. |
| 11. `get_news(999999)` and invalid-code news issues | not_tested | This run only tested valid ticker `300450`; invalid-code news behavior remains downgraded and out of first-batch scope. |

## Required Dimension Checks

| Dimension | Status | Evidence summary |
|---|---|---|
| Financial statements still show bare `No data` | disappeared | All three statement functions returned clean Tushare data. |
| Fundamentals still only show share capital without explanation | disappeared | `get_fundamentals` returned a fuller daily valuation/basic profile. |
| Fund flow still shows Eastmoney proxy long exception | disappeared | Tushare `moneyflow` was used. |
| Fund flow still shows direct bullish / bearish strong source signal | disappeared | The source output no longer emits old strong signal text. Agent language remains strong because prompts were unchanged. |
| Profit forecast still shows HTML / `read_html` exception | disappeared | Tushare `report_rc` output was used. |
| Profit forecast preserves sell-side forecast semantics | disappeared | Final report described sell-side institution consensus; no company-guidance confusion was observed. |
| Report contains token / traceback / HTML / proxy stack | disappeared | Direct report scan found none. |
| Agent treats `technical_error` / `no_data` / `no_coverage` as factual evidence | not_tested | These statuses did not appear in final report for first-batch functions, so misinterpretation of those statuses was not directly exercised. |
| Agent treats unverifiable data as Bear-side strong evidence | improved | No first-batch failure text was visible in Bear-side evidence. |
| Second-batch risks remain | still_present | `get_industry_comparison` proxy-style text appeared at tool level; market-level and media/editorial tools remain semantically risky. |

## Conclusion

For the single tested ticker `300450`, it is reasonable to conclude that the first-batch data-source pollution problems are basically fixed at the minimal Agent-consumption level. The upper-layer workflow successfully consumed the six Tushare replacements without reintroducing the old first-batch failure artifacts.

This does not mean the broader Agent system is semantically clean. The run still confirms the need for a second-batch business/contract stage covering:

- `get_news`;
- `get_global_news`;
- `get_hot_stocks`;
- `get_northbound_flow`;
- `get_concept_blocks`;
- `get_industry_comparison`;
- `get_insider_transactions`;
- market-level versus individual-stock scope labels;
- ordinary-string error contracts outside the first-batch functions.

## Next Recommendations

1. Expand minimal Agent regression to a small ticker set only after reviewing output size and LLM cost.
2. Keep first-batch Tushare functions unchanged unless future regressions find a direct defect.
3. Start Stage 5A as a design-only pass for second-batch business-risk metadata and failure-contract cleanup.
4. Do not modify prompts, Quality Gate, or Bull/Bear logic until the second-batch data contract has a clear design and evidence trail.
