# SECOND_BATCH_MIN_AGENT_REGRESSION_PRECHECK

- Stage: `5C`
- Date: 2026-07-08
- Branch: `recovery/data-source-only`
- HEAD at precheck: `625ff37`
- Goal: run second-batch post-governance minimal Agent regression for `300450`, `600519`, and `688981`.

## 1. Repository State

| Check | Result |
|---|---|
| `git status --short --branch` | `## recovery/data-source-only` |
| Working tree before adding 5C files | clean |
| Current baseline commit | `625ff37 docs: close out second batch data source governance` |

## 2. Token Presence

Presence checks only. No token or API key value was printed or written.

| Variable | Status | Source note |
|---|---|---|
| `TUSHARE_TOKEN` | present | present in the running environment |
| `DEEPSEEK_API_KEY` | present | present when loading project `.env` |

## 3. Run Readiness

Result: proceed.

Reason:

- Tushare access is available for bottom-level data source calls.
- DeepSeek access is available for the minimal Agent run.
- The working tree was clean before this 5C stage started.
- The requested run is Agent-level regression and is explicitly allowed in this stage.

## 4. Regression Scope

| Ticker | Company | Purpose |
|---|---|---|
| `300450` | 先导智能 | Compare with the prior minimal 300450 Agent regression. |
| `600519` | 贵州茅台 | Large-cap blue-chip sample. |
| `688981` | 中芯国际 | STAR Market / semiconductor sample. |

## 5. Planned Configuration

| Item | Value |
|---|---|
| LLM provider | `deepseek` |
| Quick model | `deepseek-chat` |
| Deep model | `deepseek-chat` |
| Selected analysts | `fundamentals`, `hot_money` |
| Trade date | `2026-07-07` |
| Run mode | single ticker at a time, sequential |
| Debate rounds | minimal, `max_debate_rounds=1` |
| Risk discussion rounds | minimal, `max_risk_discuss_rounds=0` |
| Data vendors | A-share dataflow path |
| Raw runtime output | `.cache/recovery/second_batch_min_agent_regression/<run_id>/` |

## 6. No-Change Boundary

This stage does not modify:

- business code;
- `tradingagents/dataflows/a_stock.py`;
- `tradingagents/dataflows/interface.py`;
- Agent prompts;
- Bull/Bear debate logic;
- Quality Gate logic;
- trading recommendation rules;
- `tradingagents/agents/`;
- `tradingagents/graph/`;
- `cli`;
- `web`.

This stage also does not perform:

- `get_industry_comparison` accuracy upgrade;
- Tushare stock-news replacement;
- `get_global_news` hybrid partial-data redesign;
- new investment recommendation rules.

## 7. Runner

The dedicated 5C runner is:

```bash
.venv/bin/python scripts/recovery/run_second_batch_min_agent_regression.py
```

The runner is intentionally narrow and writes only the structured CSV result into `docs/recovery/`. Raw Agent reports, tool-call heads, and full JSON summaries stay under `.cache/` and are not intended for git commit.
