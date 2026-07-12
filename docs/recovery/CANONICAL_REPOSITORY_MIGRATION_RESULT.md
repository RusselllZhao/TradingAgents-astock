# Canonical repository migration result

## Background and outcome

On 2026-07-12, the historical `TradingAgents-astock` checkout was preserved as a recoverable legacy archive and the Recovery checkout was established as the only formal local and GitHub development mainline. No business logic, data-source implementation, Agent, prompt, Bull/Bear behavior, Quality Gate, or trading rule was changed during this migration.

## State before migration

### Historical local checkout

- Original path: `/Users/chenyuzhao/Documents/investment-system3.0 - trading agents/TradingAgents-astock`
- Branch and HEAD: `main` at `5218b18c0f8af721eed0fc20c63724ddeba795c4`
- Remote relationship: five commits ahead of the former `origin/main`, with no commits behind
- Working tree: 25 unstaged tracked paths, no staged paths, and 27 untracked file paths
- Approximate directory size: 639 MB
- Local environment: `.env` present; `.env.local` missing
- Runtime material observed: Python caches, pytest cache, and output directories
- Former GitHub repository: `https://github.com/RusselllZhao/TradingAgents-astock`

### Recovery checkout

- Path: `/Users/chenyuzhao/Documents/investment-system3.0 - trading agents/TradingAgents-astock-data-source-recovery`
- Starting branch and HEAD: `recovery/data-source-only` at `bdd9a14dfdd920567a00b597e086b91eb8db72a2`
- Starting state: clean, with no staged, unstaged, or untracked paths
- Approximate directory size: 651 MB
- Former `origin`: original upstream repository

### GitHub access

- Authenticated account: `RusselllZhao`
- Old repository visibility: Public
- Old repository default branch: `main`
- Old repository permission: administrator
- Old repository was not archived before migration

No token or API key value was recorded during the audit.

## Local legacy archive

- Final archive path: `/Users/chenyuzhao/Documents/investment-system3.0 - trading agents/_archive/TradingAgents-astock-legacy-20260712`
- The original local path no longer exists.
- The complete directory was moved without deletion, preserving `.git`, committed history, five local-only commits, tracked changes, untracked files, runtime material, and `.env`.
- The archived `.env` remains local and has mode `600`. Its values were neither displayed nor copied into migration documentation.

The `_ARCHIVE_METADATA` directory contains:

- `OLD_REPO_STATUS.txt`
- `OLD_REPO_TRACKED_DIFF.patch`
- `OLD_REPO_STAGED_DIFF.patch`
- `OLD_REPO_UNTRACKED_FILES.txt`
- `OLD_REPO_UNIQUE_FILES.txt`
- `OLD_REPO_GIT.bundle`
- `OLD_REPO_BRANCHES.txt`
- `ARCHIVE_MANIFEST.md`
- `BUNDLE_VERIFY.txt`
- `SHA256SUMS.txt`

The tracked diff patch is 42,338 bytes. The staged diff patch is empty, consistent with the starting Git status. The untracked list contains 27 paths, and the relative-to-Recovery unique-file list contains 95 paths.

Bundle verification succeeded. SHA-256 verification succeeded for the bundle, both patches, and manifest. A sensitive-pattern scan of generated text metadata returned zero matches. The archive repository remains readable by Git and continues to report the original uncommitted state.

## GitHub legacy repository

- Original address: `https://github.com/RusselllZhao/TradingAgents-astock`
- Archived address: `https://github.com/RusselllZhao/TradingAgents-astock-legacy`
- Visibility: Public, unchanged
- Default branch: `main`, unchanged
- Archived/read-only: yes

The repository was renamed, its description and homepage were redirected to the canonical repository, and it was archived. No branch, tag, or commit was deleted. The dirty local archive and its local-only commits were not pushed as part of this operation.

## Canonical Recovery repository

- Local path: `/Users/chenyuzhao/Documents/investment-system3.0 - trading agents/TradingAgents-astock-data-source-recovery`
- GitHub: `https://github.com/RusselllZhao/TradingAgents-astock`
- Visibility: Public, matching the old repository
- Default branch: `main`
- Formal baseline tag: `v1.0-recovery-baseline`
- Historical recovery branch retained: `recovery/data-source-only`

The pre-existing local `main` pointed to `b81197653b367f84242e6fe0bca3fb6bac4619b5`. Before assigning the canonical `main`, that ref was preserved by annotated tag `pre-canonical-main-20260712-b81197653`. No rebase, squash, history rewrite, or force push occurred.

Final remotes:

```text
origin   https://github.com/RusselllZhao/TradingAgents-astock.git
upstream https://github.com/simonlin1212/TradingAgents-astock
```

Both remote `main` and the retained recovery branch initially resolved to `bdd9a14dfdd920567a00b597e086b91eb8db72a2`. The annotated baseline tag peels to the same commit. This migration result and handoff documentation are committed afterward on canonical `main`.

## Desktop launcher

The launcher at `/Users/chenyuzhao/Desktop/启动新版TradingAgents-Recovery.command` still points to the canonical Recovery path. Its user-facing text now describes the canonical launcher, and its Git status section reports the actual current branch rather than assuming the recovery branch. It continues to start only the local Web UI; it does not automatically run an Agent, LLM, Tushare, or external data source. Shell syntax validation succeeded.

## Security and scope checks

- No `.env` or `.env.local` was added to Git.
- Cache, Python cache, log, runtime-log, local output, and local credential paths are ignored.
- No secret values were printed or written to migration files.
- The canonical tracked tree contains only environment example files, not a real `.env`.
- No legacy source file was merged, copied, or cherry-picked into Recovery.
- No Agent, LLM, Tushare, external data source, or unrelated test was run.
- Recovery business code was not modified.
- The old local directory and old GitHub repository were not deleted.
- No force push was used.

## Outstanding items

No migration action is blocked. These pre-existing product follow-ups remain outside this migration:

1. `get_industry_comparison` accuracy upgrade;
2. Tushare stock-news permission availability;
3. `get_global_news partial_data` handling.

## Development rule after handoff

All subsequent development must use the canonical Recovery repository and begin from its `main` branch. The local and GitHub legacy archives are reference-only and must not be merged or cherry-picked without a separate audit.

Final repository status and remote equality are recorded by the completion commit and the final verification performed after this document was added.
