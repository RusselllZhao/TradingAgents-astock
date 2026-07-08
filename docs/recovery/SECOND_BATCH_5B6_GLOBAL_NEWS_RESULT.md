# Second Batch 5B-6 Global News Result

## 1. Scope Changed

This stage changed only the data-source implementation for:

- `tradingagents/dataflows/a_stock.py::get_global_news`

The function now returns a string-compatible Data Source Contract header and
uses a hybrid market/global news route:

- CLS wire;
- Eastmoney 7x24;
- Tushare Pro `major_news`.

New bottom-level smoke test:

- `scripts/recovery/run_global_news_contract_smoke.py`

## 2. Scope Not Changed

This stage did not modify:

- Agent prompts;
- Bull/Bear debate logic;
- Quality Gate;
- trading rules;
- `agents/`, `graph/`, `cli/`, or `web/`;
- `tradingagents/dataflows/interface.py`;
- `get_news`, `get_industry_comparison`, or other P1/P2 functions.

No Agent, multi-Agent workflow, or LLM call was run.

## 3. Data Source Governance

Previous source:

- CLS wire plus Eastmoney 7x24, without a structured contract.

Current source:

- CLS wire and Eastmoney 7x24 remain as the existing fast market-news path;
- Tushare Pro `major_news` is added as a supplemental market/global news
  source;
- source failures are summarized by source name only and raw technical details
  are suppressed from the Agent-visible output.

`major_news` is used only for `get_global_news`. It is not used as a
stock-news replacement.

## 4. Final Semantics

`get_global_news` now declares the following contract semantics:

| Field | Value |
| --- | --- |
| `source` | `CLS + Eastmoney 7x24 + Tushare major_news` |
| `data_type` | `global_news` |
| `query_target` | `market` |
| `symbol` | `N/A` |
| `coverage` | `market_wide` |
| `fallback` | `mixed_sources` |
| `unit` | `news_items` |

The scope is market/global/macro news. There is no symbol query.

## 5. Output Contracts

### Normal

When CLS/Eastmoney and Tushare sections return data without source failures:

- `status: ok`
- `data_type: global_news`
- `query_target: market`
- `coverage: market_wide`
- `raw_error_suppressed: false`

The body may contain:

- `## CLS / Eastmoney Market News`
- `## Tushare Major News`

### Partial Data

When at least one source returns news rows and at least one source fails:

- `status: partial_data`
- `raw_error_suppressed: true`
- `notes` lists unavailable source names only;
- available sections are still emitted.

Raw exception text, HTTP stack text, and vendor messages are not exposed.

### Empty

When all sources are callable but no source returns rows:

- `status: empty`
- `empty_reason: source_empty`
- `raw_error_suppressed: false`

The body is a short neutral sentence.

### Technical Error

When all sources fail technically:

- `status: technical_error`
- `error_type`: classified by source error type or `mixed_source_error`
- `raw_error_suppressed: true`

The Agent-visible body is limited to:

```text
Data source request failed; raw technical details suppressed.
```

## 6. Source Section Separation

The implementation keeps source sections separate:

- CLS and Eastmoney rows are shown under `## CLS / Eastmoney Market News`;
- Tushare `major_news` rows are shown under `## Tushare Major News`.

No company announcement interface is used. No stock-specific news semantics are
introduced.

## 7. Smoke Test

Command:

```bash
.venv/bin/python scripts/recovery/run_global_news_contract_smoke.py
```

Result:

```text
TUSHARE_TOKEN=present
global_news: PASS status=partial_data len=3441 note=ok
SUMMARY: 1/1 PASS
```

The smoke test validated:

- output type is `str`;
- `# Data Source Contract` is present;
- required header fields are present;
- `source=CLS + Eastmoney 7x24 + Tushare major_news`;
- `data_type=global_news`;
- `query_target=market`;
- `symbol=N/A`;
- `coverage=market_wide`;
- output includes news fields such as publication time, source, and title when
  data is available;
- partial-data output lists only source names in notes.

The observed `partial_data` status came from one unavailable source while other
market/global news sources returned rows.

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
- token value leaks;
- source-failure raw warning or raw error text.

## 9. String Compatibility

The function still returns a plain string. The only consumption-side change is
that the returned string now starts with the standard Data Source Contract
header.

## 10. Prompt / Bull-Bear / Quality Gate / Agent Check

This stage did not modify prompts, Bull/Bear debate logic, Quality Gate,
trading rules, Agent orchestration, or tool routing.

## 11. Next Step

The planned next batch is `5B-7`: `get_news`.

Before changing `get_news`, keep the same boundary:

- keep `get_news` stock-specific;
- do not use `major_news` as stock news;
- structure Eastmoney/Sina fallback and source failures;
- distinguish `invalid_input`, `empty`, `partial_data`, and `technical_error`;
- suppress raw HTTP, proxy, HTML, and traceback text.
