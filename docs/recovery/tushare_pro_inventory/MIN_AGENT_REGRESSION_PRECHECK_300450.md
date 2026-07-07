# Minimal Agent Regression Precheck for 300450

- Precheck date: 2026-07-07
- Branch: `recovery/data-source-only`
- HEAD at precheck start: `e2a8c55`
- Target ticker: `300450`
- Target company: `先导智能`
- Scope: Stage 4C-1 only. This precheck did not run a multi-agent workflow, did not call any LLM, and did not call Tushare.

## Current Repository State

| Check | Result |
|---|---|
| `git status --short --branch` | `## recovery/data-source-only` |
| HEAD | `e2a8c55` |
| Working tree before document write | clean |
| Required baseline docs | present |

## Environment Variables

Values below are presence checks only. No token or API key value was printed or written.

| Variable | Status | Purpose |
|---|---|---|
| `TUSHARE_TOKEN` | present | Tushare data source calls |
| `MINIMAX_API_KEY` | missing | MiniMax LLM provider |
| `DEEPSEEK_API_KEY` | present | DeepSeek LLM provider |
| `DASHSCOPE_API_KEY` | missing | Qwen / DashScope LLM provider |
| `ZHIPU_API_KEY` | missing | GLM LLM provider |
| `OPENAI_API_KEY` | missing | OpenAI LLM provider |
| `ANTHROPIC_API_KEY` | missing | Anthropic LLM provider |
| `ANTHROPIC_AUTH_TOKEN` | missing | Kimi Anthropic-compatible path |
| `GOOGLE_API_KEY` | missing | Google / Gemini provider |
| `GEMINI_API_KEY` | missing | Alternate Gemini key name |
| `XAI_API_KEY` | missing | xAI provider |
| `OPENROUTER_API_KEY` | missing | OpenRouter provider |
| `FINNHUB_API_KEY` | missing | Optional legacy market data key |
| `ALPHA_VANTAGE_API_KEY` | missing | Optional Alpha Vantage data source |
| `TRADINGAGENTS_RESULTS_DIR` | missing | Optional output directory override |
| `TRADINGAGENTS_CACHE_DIR` | missing | Optional data cache directory override |
| `TUSHARE_ENABLE_CACHE` | missing | Optional Tushare cache toggle |
| `TUSHARE_CACHE_DIR` | missing | Optional Tushare cache directory override |

Additional local-model check:

| Check | Result |
|---|---|
| `.env` | present |
| `.env.local` | missing |
| Ollama service at `localhost:11434` | missing |
| Ollama local models | not available because service is missing |

## Current Run Entry Points

The project has three relevant run paths:

| Entry | Status for this goal | Notes |
|---|---|---|
| `main.py` | not recommended as-is | Hard-coded for `NVDA`, yfinance vendors, and non-A-share sample config. |
| `examples/run_cases.py` | not recommended as-is | Supports one ticker argument, but its default path writes under `examples/cases/` and uses a broader example configuration. |
| Direct `TradingAgentsGraph` call | recommended if runtime conditions are met | Allows a tightly scoped one-ticker script with explicit analysts, config, output path, and safety scans. |

The minimal programmatic entry point is:

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph

graph = TradingAgentsGraph(
    selected_analysts=["fundamentals", "hot_money"],
    debug=False,
    config=config,
)
final_state, decision = graph.propagate("300450", "2026-07-07")
```

## Minimal Run Parameter Recommendation

If an LLM runtime becomes available, use a dedicated recovery script rather than the existing batch example.

Recommended target command:

```bash
.venv/bin/python scripts/recovery/run_min_agent_regression_300450.py
```

Recommended config shape:

| Parameter | Recommended value | Reason |
|---|---|---|
| ticker | `300450` | Single target only. |
| trade date | `2026-07-07` | Matches current recovery date and first-batch regression context. |
| `selected_analysts` | `["fundamentals", "hot_money"]` | `fundamentals` is needed for statements, fundamentals, and forecast; `hot_money` is needed for fund flow. |
| `llm_provider` | `deepseek` | `DEEPSEEK_API_KEY` is present in the project `.env`. |
| `quick_think_llm` / `deep_think_llm` | lowest-cost tool-capable model for chosen provider | Analyst nodes need tool calling. |
| `max_debate_rounds` | `1` | Keeps one Bull and one Bear response so Bear misuse can be observed. Setting `0` would skip Bear after the initial Bull node. |
| `max_risk_discuss_rounds` | `0` or `1` | `0` minimizes cost but still runs Aggressive + Portfolio Manager; `1` runs the full risk trio. |
| `checkpoint_enabled` | `False` | Avoid resumable SQLite state for this one-shot regression. |
| `output_language` | `Chinese` | Matches project default user-facing A-share report language. |
| `data_vendors` | all relevant categories set to `a_stock` | Ensures A-share dataflow path and Tushare replacements are reachable. |
| `results_dir` | `.cache/recovery/min_agent_regression_300450/<run_id>/graph_results` | Keeps one-shot output bounded and ignored by git. Commit only summaries, not large raw runtime artifacts. |
| `data_cache_dir` | default or a controlled local cache path | May create cache. Do not commit runtime cache. |

## Expected LLM Calls

The graph always constructs quick and deep LLM clients during `TradingAgentsGraph` initialization. A successful run will call an LLM for:

- selected analyst nodes;
- Quality Gate;
- Bull/Bear research debate;
- Research Manager;
- Trader;
- at least one risk analyst;
- Portfolio Manager.

Therefore Stage 4C-2 can run with DeepSeek in the current environment, provided the run uses the project virtual environment and explicitly loads the project root `.env`.

## Expected Data Functions

With `selected_analysts=["fundamentals", "hot_money"]`, the graph can expose these tools:

| Analyst | Tools exposed | First-batch replaced functions included |
|---|---|---|
| `fundamentals` | `get_fundamentals`, `get_balance_sheet`, `get_cashflow`, `get_income_statement`, `get_profit_forecast`, `get_industry_comparison` | `get_fundamentals`, `get_balance_sheet`, `get_cashflow`, `get_income_statement`, `get_profit_forecast` |
| `hot_money` | `get_stock_data`, `get_news`, `get_insider_transactions`, `get_hot_stocks`, `get_northbound_flow`, `get_concept_blocks`, `get_fund_flow`, `get_dragon_tiger_board`, `get_industry_comparison` | `get_fund_flow` |

Whether each tool is actually called depends on the selected LLM's tool-calling behavior. The prompts request the first-batch functions, but the runtime does not hard-force every tool call.

## Expected Tushare Calls

If the selected LLM calls the first-batch tools, Tushare may be called through:

- `get_balance_sheet` -> `balancesheet`
- `get_cashflow` -> `cashflow`
- `get_income_statement` -> `income`
- `get_fundamentals` -> `daily_basic`, `stock_basic`
- `get_fund_flow` -> `moneyflow`, fallback `moneyflow_dc`
- `get_profit_forecast` -> `report_rc`

The `TUSHARE_TOKEN` status is present, but the precheck intentionally did not call Tushare.

## Expected Output Writes

A normal direct graph run writes:

- `config["results_dir"] / 300450 / TradingAgentsStrategy_logs / full_states_log_2026-07-07.json`
- memory log at `config["memory_log_path"]`

A dedicated recovery script can additionally write a compact report bundle and summary under:

- `.cache/recovery/min_agent_regression_300450/<run_id>/`

Any full raw report/log should be reviewed for size and sensitive strings before committing. Runtime cache and raw outputs should stay untracked unless intentionally summarized.

## Cache Risk

Potential cache/output locations:

- default TradingAgents cache: `~/.tradingagents/cache`
- default TradingAgents logs: `~/.tradingagents/logs`
- default TradingAgents memory: `~/.tradingagents/memory/trading_memory.md`
- Tushare cache: `.cache/tushare/` unless overridden

The existing ignore rules cover `.cache/tushare/`. A recovery script should avoid committing runtime caches and should summarize rather than commit large raw state files.

## Data Source Path Check

The configured A-share route uses `tradingagents.dataflows.interface.route_to_vendor`, which dispatches to the configured vendor. With `data_vendors` set to `a_stock`, the first-batch functions are expected to use the updated Tushare-backed implementations in `tradingagents/dataflows/a_stock.py`.

No change to `tradingagents/dataflows/interface.py` is needed or recommended.

## Risks Before Running

- Local Ollama service is not available, but it is not needed because `DEEPSEEK_API_KEY` is present.
- The run must use `.venv/bin/python`; the system Python does not have all project dependencies.
- Even after an LLM is configured, tool use is model-dependent. A weak tool-calling model may produce empty or incomplete analyst reports.
- Including `hot_money` is necessary to test upper-layer consumption of `get_fund_flow`, but it also exposes second-batch-risk tools such as news, northbound flow, hot stocks, concept blocks, and industry comparison.
- The hot-money prompt text still describes fund flow as realtime/minute-level in the tool description, while the first-batch implementation now returns daily Tushare data. This is a known agent-consumption risk to observe, not a reason to modify prompt in this phase.

## Recommendation

Run Stage 4C-2 in the current environment using DeepSeek.

Reason: `TUSHARE_TOKEN=present` and `DEEPSEEK_API_KEY=present` when loaded from the project `.env` with `.venv/bin/python`. Use the dedicated minimal regression script so output and cache paths remain bounded and ignored.

## Precheck Conclusion

| Question | Answer |
|---|---|
| Can 300450 be run as a single ticker? | Yes, through a dedicated direct `TradingAgentsGraph` script. |
| Can cost be minimized? | Yes, by selecting `fundamentals` + `hot_money`, one run only, bounded output, and minimal debate/risk rounds. |
| Would the run call LLMs? | Yes. |
| Would the run call external LLMs? | Yes, DeepSeek. |
| Would the run call Tushare? | Yes if the LLM invokes the first-batch tools. |
| Would the run write output files? | Yes, graph logs and memory; a recovery script can control additional outputs. |
| Would the run call six replaced functions? | Exposed to the LLM through `fundamentals` and `hot_money`; actual calls depend on tool behavior. |
| Should Stage 4C-2 run now? | Yes. |
| Stop condition triggered? | No. |
