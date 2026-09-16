---
name: omarchy-dev
description: Use when working on Omarchy source contributions from a dev-linked checkout — integration branch rebuilds with omarchy-dev-sync, PR branches, gh PR checks. Triggers on omarchy dev, dev link, omarchy-dev-sync, integration branch, PR updates or comments.
license: MIT
---

# Omarchy Dev Setup

This machine contributes to Omarchy from a dev-linked fork checkout. The live
desktop runs the checkout, and all open PRs are tested together on one
integration branch.

## Layout

- Checkout: the Omarchy clone (default `~/src/omarchy`), dev-linked via
  `omarchy dev link`, so the session `OMARCHY_PATH` points here.
- Remotes inside the checkout: one remote for upstream (`omacom/omarchy`,
  default name `origin`) and one for your fork (default name `fork`).
- Base branch: `quattro` (upstream's dev branch). Override with
  `OMARCHY_DEV_SYNC_HEAD` or `head=` in the config file.
- Sync script: `omarchy-dev-sync` (this repo's `omarchy-dev-sync`
  executable, typically symlinked onto PATH as `omarchy-dev-sync`).
  Config lives in `~/.config/omarchy-dev-sync/config`
  (`repo`, `upstream`, `fork`, `head`, `integration`) and optional
  `extra-branches` (override the directory with `OMARCHY_DEV_SYNC_CONFIG`;
  environment variables win over the file). Defaults:
  `repo=~/src/omarchy`, `upstream=origin`, `fork=fork`, `head=quattro`,
  `integration=integration-prs`.
- `integration-prs` (or your configured `integration` name): disposable
  integration branch = `$upstream/$head` plus a merge of every open PR. It
  is the normally-active checkout so the live desktop runs all PRs together.
  **Never edit it directly** — it is rebuilt by the script and force-pushed
  to the fork with `--force-with-lease`.

## Workflow

1. Do feature/fix work on the individual PR branch (`fix/...`,
   `feature/...`), never on the integration branch.
2. Commits are atomic with succinct messages (e.g. `fix(bar): ...` plus a
   matching `test(bar): ...` commit, following the branch's existing style).
3. Push the PR branch (use `--force-with-lease` if local history was
   rewritten; these are personal fork branches).
4. Run `omarchy-dev-sync` from anywhere to rebuild and push the integration
   branch, refresh stale dev packages, and restart the live shell. It ends
   back on the integration branch. Flags: `--no-restart` skips the shell
   restart, `--no-pkg` skips the package rebuild.
5. Verify with focused suites first (`bash test/shell.d/<area>-test.sh`),
   then `./test/shell` and/or `./test/cli` as appropriate.

## Repo conventions (in the Omarchy checkout)

- Read `AGENTS.md` and the matching guide under `agents/skills/` before
  editing: `shell-dev.md` for Quickshell UI under `shell/`,
  `visual-verification.md` for UI changes, `acceptance-tests.md` for
  `test/acceptance.d/`.
- Never rewrite `shell/plugins/bar/widgets/` files wholesale (Nerd Font
  glyphs get stripped); use targeted edits.
- QML changes take effect via `omarchy-restart-shell`.

## Checking PRs

- List your open PRs: `gh pr list --repo <upstream-slug> --author @me --state open`
  (the script derives `<upstream-slug>` from the upstream remote URL).
- Details, comments, reviews: `gh pr view <n> --repo <upstream-slug> --json
  comments,reviews,mergeable,mergeStateStatus`, `gh pr checks <n> --repo
  <upstream-slug>`.
- `mergeable=UNKNOWN` right after upstream moves is usually GitHub
  recompute lag; a clean local `omarchy-dev-sync` rebuild means no real
  conflict.
- **Never post PR comments without explicit user approval** — draft the
  reply and confirm first.
- Closing a PR drops it from the next integration rebuild, which is what
  the live desktop runs. Never close a PR whose fix is load-bearing for the
  live session until its replacement has actually merged — not when a
  canonical alternative is merely identified (closing a working menu-plugin
  fix in favor of a not-yet-merged competing PR emptied the live menu
  clone's Apps list).

## Known environment quirks

- The script auto-resolves append-only conflicts in
  `test/shell.d/theme-staging-test.sh` (`colour_only` / `denied` arrays) as
  a sorted union. Any other conflict aborts the rebuild and restores the
  previous integration branch.
- `config-test.sh`, `snapper-test.sh`, `unowned-system-paths-test.sh` fail
  without an `omarchy-pkgs` checkout — environmental, unrelated to PR work.
- Environment-specific pre-existing failures exist (e.g.
  `test/shell.d/runtime-smoke-test.sh` IPC-handler count with multi-screen
  setups). If a failure looks unrelated, verify it fails without your change
  too before chasing it.
