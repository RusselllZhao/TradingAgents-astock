# Local Environment Cleanup and Launcher Result

## 1. Task Background

This pass was a local environment cleanup assessment after the recovery branch
completed second-batch data-source governance, 5C minimal Agent regression, and
5C-4 Chinese output term normalization.

Scope:

- audit the old local project directory before any deletion;
- do not delete or modify the old directory;
- create a macOS desktop launcher for the current recovery project;
- do not run Agent, LLM, Tushare, or external data-source calls.

## 2. Current Recovery Project

Path:

```text
/Users/chenyuzhao/Documents/investment-system3.0 - trading agents/TradingAgents-astock-data-source-recovery
```

Git audit:

- remote: `origin https://github.com/simonlin1212/TradingAgents-astock`
- branch: `recovery/data-source-only`
- latest commit: `20bdc90 fix: normalize Chinese report direction terms`
- recent commits:
  - `20bdc90 fix: normalize Chinese report direction terms`
  - `8dcd3d2 test: run second batch minimal agent regression`
  - `625ff37 docs: close out second batch data source governance`
  - `6735369 fix: add contract for stock news source`
  - `8cf1890 fix: add contract for global news source`
- size: `651M`
- status before this document: clean

Local sensitive/runtime indicators:

- `.env`: file exists
- `.env.local`: missing
- `TUSHARE_TOKEN`: missing in `.env`
- `DEEPSEEK_API_KEY`: present in `.env`
- `OPENAI_API_KEY`: missing in `.env`
- `GOOGLE_API_KEY`: missing in `.env`
- `.cache`: present as local runtime/cache directory

No secret values were printed or copied.

## 3. Old Directory Audit

Path:

```text
/Users/chenyuzhao/Documents/investment-system3.0 - trading agents/TradingAgents-astock
```

Existence:

- old directory exists.
- current recovery directory exists.

Git audit:

- remotes:
  - `origin https://github.com/RusselllZhao/TradingAgents-astock.git`
  - `upstream https://github.com/simonlin1212/TradingAgents-astock.git`
- branch: `main`
- latest commit: `5218b18 fix: enforce GAL01 tool contracts`
- recent commits:
  - `5218b18 fix: enforce GAL01 tool contracts`
  - `8bf4386 chore: checkpoint GDL data coverage updates`
  - `e888a3e fix: keep data quality visible in web only`
  - `b04e115 fix: align web signal with final decision`
  - `63b8261 chore: stabilize A-share evidence and web signals`
- status: `main...origin/main [ahead 5]`
- size: `639M`

Uncommitted state:

- old directory has uncommitted modifications.
- modified files include analyst prompts, manager/trader agents, Quality Gate,
  graph logic, tests, and `tradingagents/dataflows/a_stock.py`.
- untracked files include additional baseline reports, acceptance outputs,
  runtime/cache artifacts, and test scripts.

Sensitive/runtime indicators:

- `.env`: file exists
- `.env.local`: missing
- `TUSHARE_TOKEN`: present in `.env`
- `DEEPSEEK_API_KEY`: present in `.env`
- `OPENAI_API_KEY`: present in `.env`
- `GOOGLE_API_KEY`: present in `.env`
- `.pytest_cache`: present
- multiple `__pycache__` directories are present
- untracked baseline acceptance output includes `_cache`, `_memory`, and
  `_runtime_logs` directories
- no files larger than 20M were found outside `.git` and `.venv`

No secret values were printed or copied.

## 4. Unique Old-Directory Material

Tracked files present only in the old directory: `68`.

Examples include:

- `DEPLOYMENT_ACCEPTANCE.md`
- `PROJECT_BOUNDARY.md`
- `WEB_UI_QUICKSTART.md`
- `baselines/v0/2026-07-04/*`
- `baselines/v0/2026-07-06/*`
- `baselines/v0/2026-07-07/*`
- `scripts/gdl03b_tushare_postclose_comparison.py`
- `scripts/gdl04_financial_source_comparison.py`
- `scripts/gdl05_news_policy_regression.py`
- `scripts/gdl06_tushare_capital_samples.py`
- `scripts/gdl07_tushare_corporate_actions_samples.py`
- `scripts/setup_tushare_token.command`
- `tests/test_evidence_contract.py`
- `tests/test_gal01_tool_contracts.py`
- `tradingagents/agents/utils/tool_contracts.py`
- `tradingagents/dataflows/evidence.py`
- `tradingagents/dataflows/tushare_capital.py`
- `tradingagents/dataflows/tushare_corporate_actions.py`
- `tradingagents/dataflows/tushare_financial.py`
- `tradingagents/dataflows/tushare_postclose.py`
- `web/evidence_summary.py`

Untracked files in the old directory include GAL02/GAL03/GVAL01 acceptance
reports and runtime artifacts.

Assessment: the old directory is consistent with a historical wrong改造 /
experimental branch and is not the current recovery mainline. However, it is
not safe to delete or move automatically because it has uncommitted changes,
untracked outputs, `.env` secrets, and unique historical source/test/document
material.

## 5. Old Directory Handling Decision

Action taken:

- did not delete old directory;
- did not move old directory.

Recommendation:

- do not delete directly;
- if cleanup is desired, first move it manually or after explicit confirmation
  to a desktop holding directory such as:

```text
/Users/chenyuzhao/Desktop/TradingAgents-astock_OLD_TO_DELETE_YYYYMMDD
```

Recommended category: `C. 暂不建议删除，因为存在未提交修改或独有文件`.

## 6. Desktop Launcher

Created launcher:

```text
/Users/chenyuzhao/Desktop/启动新版TradingAgents-Recovery.command
```

Permissions:

- executable bit set with `chmod +x`.

Launcher behavior:

- opens in macOS Terminal by double click;
- `cd` into the current recovery project path;
- activates `.venv` when `.venv/bin/activate` exists;
- displays current directory;
- displays current branch;
- displays latest commit;
- displays `git status --short --branch`;
- displays `python --version`;
- checks `TUSHARE_TOKEN` and `DEEPSEEK_API_KEY` as `present` / `missing`
  without printing values;
- checks shell environment first and `.env` key presence second;
- prints common local command reminders;
- does not automatically run Agent, LLM, Tushare, or external data calls;
- leaves the user in an interactive shell for manual commands.

## 7. Verification

Commands run:

```bash
chmod +x "/Users/chenyuzhao/Desktop/启动新版TradingAgents-Recovery.command"
sed -n '1,80p' "/Users/chenyuzhao/Desktop/启动新版TradingAgents-Recovery.command"
bash -n "/Users/chenyuzhao/Desktop/启动新版TradingAgents-Recovery.command"
git status --short --branch
git diff --check
```

Results:

- launcher file exists and is executable;
- launcher header/path inspection passed;
- `bash -n` passed;
- local status check showed branch `recovery/data-source-only`;
- latest commit before this document was `20bdc90`;
- Python version check returned `Python 3.12.10`;
- no Agent, LLM, Tushare, or external data-source command was run.

## 8. Sensitive Information

Findings:

- old directory `.env`: exists and includes key names marked present;
- recovery directory `.env`: exists and includes `DEEPSEEK_API_KEY` marked
  present, while `TUSHARE_TOKEN`, `OPENAI_API_KEY`, and `GOOGLE_API_KEY` were
  missing in `.env`;
- desktop launcher contains no secret values;
- this document contains no secret values.

Only `present` / `missing` status was recorded.

## 9. Recovery Code Changes

No recovery business code was modified.

No Agent, prompt, Bull/Bear debate logic, Quality Gate, trading rule, data-source
function, or interface file was modified.

Only this documentation file is intended for git commit.

## 10. Next Suggestions

- Keep using the recovery directory as the mainline.
- Before deleting the old directory, either archive it to a desktop holding
  folder or manually review the uncommitted and unique files listed above.
- Double-click the desktop launcher when starting a local recovery session.
