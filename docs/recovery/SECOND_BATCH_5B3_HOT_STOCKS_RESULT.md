# Second Batch 5B-3 Hot Stocks Result

## 1. Scope Changed

This stage changed only the data-source implementation for:

- `tradingagents/dataflows/a_stock.py::get_hot_stocks`

The function now uses Tushare Pro `ths_hot` as the primary source for
market-wide hot-stock ranking and returns a string-compatible Data Source
Contract header before the Markdown body.

New bottom-level smoke test:

- `scripts/recovery/run_hot_stocks_contract_smoke.py`

## 2. Scope Not Changed

This stage did not modify:

- Agent prompts;
- Bull/Bear debate logic;
- Quality Gate;
- trading rules;
- `agents/`, `graph/`, `cli/`, or `web/`;
- `tradingagents/dataflows/interface.py`;
- `get_dragon_tiger_board`, `get_insider_transactions`, `get_global_news`,
  `get_news`, `get_industry_comparison`, or other P1/P2 functions.

No Agent, multi-Agent workflow, or LLM call was run.

## 3. Data Source Replacement

Previous source:

- direct THS hot-stock HTTP endpoint.

New source:

- Tushare Pro `ths_hot`.

This first implementation is intentionally limited to market-wide hot-stock
ranking:

- no `limit_list_ths`;
- no `limit_step`;
- no `limit_list_d`;
- no mixing of hot-stock ranking, limit-up pool, or consecutive limit-up ladder
  data.

## 4. Final Semantics

`get_hot_stocks` now declares the following contract semantics:

| Field | Value |
| --- | --- |
| `source` | `Tushare ths_hot` |
| `data_type` | `hot_stocks` |
| `query_target` | `market` |
| `symbol` | `N/A` |
| `coverage` | `market_wide` |
| `fallback` | `none` |
| `unit` | `rank; pct_change percent; current_price CNY; other fields raw Tushare` |

The output remains a plain string. The body keeps a Markdown table with
available `ths_hot` fields such as:

- `trade_date`
- `data_type`
- `ts_code`
- `ts_name`
- `rank`
- `pct_change`
- `current_price`
- `concept`
- `rank_reason`

Fields are emitted only when returned by Tushare; no fields are fabricated.

## 5. Output Contracts

### Normal

When Tushare returns rows for the queried recent trade-date window:

- `status: ok`
- `source: Tushare ths_hot`
- `data_type: hot_stocks`
- `query_target: market`
- `symbol: N/A`
- `coverage: market_wide`
- `raw_error_suppressed: false`

The body shows the latest available `ths_hot` hot-stock ranking rows.

### Empty

When Tushare returns no rows across the recent trade-date query window:

- `status: empty`
- `empty_reason: source_empty`
- `coverage: market_wide`
- `raw_error_suppressed: false`

The body is a short neutral sentence. It does not return a bare `No data found`
string and does not fall back to unrelated market-event data.

### Technical Error

When Tushare or parsing fails:

- `status: technical_error`
- `error_type`: classified by the shared data-source error classifier
- `raw_error_suppressed: true`

The Agent-visible body is limited to:

```text
Data source request failed; raw technical details suppressed.
```

Raw exceptions, HTML, traceback text, proxy stacks, and long network errors are
not included in the Agent-visible output.

## 6. Directional Text and Mixed Data Check

The new implementation returns Tushare hot-stock ranking rows only. It does
not add source-level directional wording, debate guidance, or trading-rule
language.

It also does not include:

- `limit_list_ths`;
- `limit_step`;
- `limit_list_d`;
- limit-up pool rows;
- consecutive limit-up ladder rows.

## 7. Smoke Test

Command:

```bash
.venv/bin/python scripts/recovery/run_hot_stocks_contract_smoke.py
```

Result:

```text
TUSHARE_TOKEN=present
hot_stocks: PASS status=ok len=13541 note=ok
SUMMARY: 1/1 PASS
```

The smoke test validated:

- output type is `str`;
- `# Data Source Contract` is present;
- required header fields are present;
- `source=Tushare ths_hot`;
- `data_type=hot_stocks`;
- `query_target=market`;
- `coverage=market_wide`;
- `symbol=N/A`;
- success output includes `ths_hot` fields;
- technical errors, if encountered, must use short raw-suppressed output.

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
- token value leaks.

## 9. String Compatibility

The function still returns a plain string. The only consumption-side change is
that the returned string now starts with the standard Data Source Contract
header.

## 10. Prompt / Bull-Bear / Quality Gate / Agent Check

This stage did not modify prompts, Bull/Bear debate logic, Quality Gate,
trading rules, Agent orchestration, or tool routing.

## 11. Next Step

The planned next batch is `5B-4`: `get_dragon_tiger_board`.

Before changing `get_dragon_tiger_board`, keep the same boundaries:

- use Tushare `top_list` for dragon-tiger event rows;
- use `top_inst` only as clearly separated seat/institution detail if included;
- distinguish `no_event`, `empty`, `partial_data`, and `technical_error`;
- do not interpret absence from dragon-tiger board as an investment conclusion.
