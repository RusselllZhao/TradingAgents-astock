# Canonical mainline handoff

## Canonical repository

This Recovery checkout is the only formal TradingAgents development version.

- Local path: `/Users/chenyuzhao/Documents/investment-system3.0 - trading agents/TradingAgents-astock-data-source-recovery`
- GitHub repository: `https://github.com/RusselllZhao/TradingAgents-astock`
- Default and development branch: `main`
- Recovery history branch retained for audit: `recovery/data-source-only`
- Formal baseline tag: `v1.0-recovery-baseline`
- Original upstream: `https://github.com/simonlin1212/TradingAgents-astock.git`

All future changes must start from this repository and its `main` branch.

## Legacy archive

- Local archive: `/Users/chenyuzhao/Documents/investment-system3.0 - trading agents/_archive/TradingAgents-astock-legacy-20260712`
- Archived GitHub repository: `https://github.com/RusselllZhao/TradingAgents-astock-legacy`

The legacy version is retained only for audit, traceability, and reference. Do not merge or cherry-pick from it into Recovery unless the candidate material first receives a separate, explicit audit. The archived working tree must never be treated as a development mainline.

## Baseline scope

The canonical baseline includes:

- first-batch Tushare data-source recovery;
- second-batch data-source stability, accuracy, and coverage governance;
- 22/22 second-batch bottom-level smoke completion;
- minimal Agent regression for 300450, 600519, and 688981;
- normalization of Chinese bullish and bearish direction terminology;
- local cleanup and launcher handoff documentation.

## Known follow-up items

These existing issues remain follow-up work and are not changed by the repository migration:

1. `get_industry_comparison` accuracy upgrade;
2. Tushare stock-news permission availability;
3. `get_global_news partial_data` handling.

This handoff contains no credentials or secret values.
