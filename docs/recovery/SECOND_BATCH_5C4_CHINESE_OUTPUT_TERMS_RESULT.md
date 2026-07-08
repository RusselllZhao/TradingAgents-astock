# Second Batch 5C-4 Chinese Output Terms Result

## 1. Background

The second-batch minimal Agent regression passed for `300450`, `600519`, and
`688981`. The scan found one residual English `bullish` term in the `600519`
final report. Prior review classified it as Agent-generated debate text rather
than a data-source output or Data Source Contract regression.

This 5C-4 pass only addresses Chinese final-report wording consistency for
residual English direction terms such as `bullish` and `bearish`.

## 2. Cause Assessment

Read-only scan found English direction terms in researcher prompts and internal
state annotations, especially the Bull/Bear research roles. Because the prior
`600519` occurrence appeared in Agent debate text, the likely source is direct
LLM generation influenced by the English Bull/Bear debate context and prompts,
not a bottom-layer tool return.

This pass did not change those prompts or the debate mechanism. The chosen
fix is a final-report output normalization step after Agent reasoning has
completed.

## 3. Modified Scope

- Added `tradingagents/agents/utils/report_terms.py`.
- Updated `tradingagents/graph/trading_graph.py`.
- Added `scripts/recovery/run_chinese_output_terms_smoke.py`.
- Added this result document.

## 4. Unmodified Scope

- No data-source function changes.
- No changes to `tradingagents/dataflows/a_stock.py`.
- No changes to `tradingagents/dataflows/interface.py`.
- No Bull/Bear debate logic changes.
- No Quality Gate changes.
- No trading recommendation rule changes.
- No prompt rewrite.
- No Data Source Contract changes.
- No `.cache`, raw HTML, local run log, `.env`, token, or API key files added.

## 5. Fix Method

Added `normalize_chinese_report_terms(text: str) -> str` and
`normalize_chinese_report_state(final_state)` for final report fields.

The graph now applies `normalize_chinese_report_state` in
`TradingAgentsGraph.finalize_graph_run()` only when `output_language` is Chinese.
This point is after all Agent reasoning and debate steps are complete, before
state logging, memory logging, signal parsing, and returning the final state.

The helper normalizes report fields and debate/risk report histories, but does
not touch message/tool-output containers or lower-level data-source returns.

## 6. Replacement Rules

- `bullish arguments` / `Bullish argument` -> `偏多论据`
- `bearish arguments` / `Bearish argument` -> `偏空论据`
- `bullish thesis` / `Bullish thesis` -> `偏多逻辑`
- `bearish thesis` / `Bearish thesis` -> `偏空逻辑`
- `bullish risk` / `Bullish risk` -> `偏多风险`
- `bearish risk` / `Bearish risk` -> `偏空风险`
- standalone `bullish` / `Bullish` / `BULLISH` -> `偏多`
- standalone `bearish` / `Bearish` / `BEARISH` -> `偏空`

The replacements are word-boundary based and case-insensitive.

## 7. Prompt / Bull-Bear / Quality Gate Changes

None.

## 8. Data Source Changes

None.

## 9. Verification

Commands run:

```bash
python -m py_compile tradingagents/agents/utils/report_terms.py tradingagents/graph/trading_graph.py scripts/recovery/run_chinese_output_terms_smoke.py
python scripts/recovery/run_chinese_output_terms_smoke.py
```

Smoke test result:

```text
chinese_output_terms_smoke: passed
```

The smoke test covered:

- `This is bullish` -> no English `bullish`, contains `偏多`.
- `This is bearish` -> no English `bearish`, contains `偏空`.
- `Bullish thesis and bearish risk` -> contains Chinese phrase replacements.
- Ordinary Chinese text remains unchanged.
- Data Source Contract status/empty-reason fields remain unchanged.
- Non-report `messages` content is not normalized.

## 10. 600519 Minimal Agent Regression

Not run in this pass.

Reason: the task scope permits helper smoke plus static checks when Agent cost
is high. Also, the current Python environment used for the smoke test does not
have `langchain_core` installed, so a real Agent run would require restoring
the full Agent runtime environment first. This pass therefore used the targeted
helper smoke and static code inspection.

## 11. Remaining Risk

- English `bullish` / `bearish` can still exist in internal prompts and comments.
  This is intentional for this pass because changing Bull/Bear prompt logic was
  out of scope.
- If a future report writer bypasses `TradingAgentsGraph.finalize_graph_run()`,
  it should call `normalize_chinese_report_terms` or
  `normalize_chinese_report_state` before writing Chinese final reports.
- The normalization is intentionally narrow and does not translate unrelated
  English text.

## 12. Next Suggestions

- If a later pass updates final report writers outside `TradingAgentsGraph`,
  reuse the same helper at those output boundaries.
- Keep prompt/debate wording changes separate from this data-source recovery
  branch unless explicitly scheduled.
