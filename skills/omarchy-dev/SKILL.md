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
  (`repo`, `upstream`, `fork`, `head`, `integration`, `self_update`, `package_sources`, `pkgs_repo`,
  `pkgs_prs`, `runtime_packages`) and optional `extra-branches` / `extra-prs` (override the directory with
  `OMARCHY_DEV_SYNC_CONFIG`; environment variables win over the file).
  Defaults: `repo=~/src/omarchy`, `upstream=origin`, `fork=fork`,
  `head=quattro`, `integration=integration-prs`,
  `pkgs_repo=~/Work/omarchy/omarchy-pkgs`, `pkgs_prs=1`.
- `integration-prs` (or your configured `integration` name): disposable
  integration branch = `$upstream/$head` plus a merge of every open PR. It
  is the normally-active checkout so the live desktop runs all PRs together.
  **Never edit it directly** — it is rebuilt by the script and force-pushed
  to the fork with `--force-with-lease`.
- Packaging checkout: omarchy-pkgs (default `~/Work/omarchy/omarchy-pkgs`),
  consumed read-only at whatever is checked out (normally `master`).
  When the script rebuilds the dev packages it first merges your open
  omarchy-pkgs PRs into a disposable worktree and builds from there, so
  packaging fixes ship in the same sync that tests them. The checkout
  itself is never modified and nothing pkgs-side is pushed. Point
  `OMARCHY_PKGBUILDS_DIR` at a directory to use those PKGBUILDs as-is and
  skip the PR merge; set `pkgs_prs=0` (or `OMARCHY_DEV_SYNC_PKGS_PRS=0`)
  to always build from the checkout.

## Workflow

1. Do feature/fix work on the individual PR branch (`fix/...`,
   `feature/...`), never on the integration branch.
2. Commits are atomic with succinct messages (e.g. `fix(bar): ...` plus a
   matching `test(bar): ...` commit, following the branch's existing style).
3. Push the PR branch (use `--force-with-lease` if local history was
   rewritten; these are personal fork branches).
4. The script checks its own remote tracking branch first, fast-forwards a clean checkout, and restarts with the original arguments when updated. Local changes or ahead/diverged history are preserved; fetch failures warn and continue. Use `--no-self-update`, config `self_update=0`, or `OMARCHY_DEV_SYNC_SELF_UPDATE=0` to opt out.
   Startup installs missing omarchy-dev skills as symlinks in standard Agents, Claude, OpenCode and Codex skill directories, creating parents as needed. Existing copied skills refresh with backups; symlinks into this checkout follow updates, and unrelated symlinks are preserved. This runs even with self-update disabled; --help does not install skills.
   Before restarting, the persistent dev link is checked against the synced repo. Known Omarchy stable/rc package and Arch mirror URLs are aligned with edge with backups, retaining custom config. No package databases or system packages are updated by this check; run omarchy update afterwards. It also runs with --no-pkg; opt out with --no-package-sources, package_sources=0, or OMARCHY_DEV_SYNC_PACKAGE_SOURCES=0.
   Run `omarchy-dev-sync` from anywhere to rebuild and push the integration
   branch, refresh stale dev packages, and restart the live shell. It ends
   back on the integration branch. Flags: `--no-restart` skips the shell
   restart, `--no-pkg` skips the package rebuild. The package refresh
   includes your open omarchy-pkgs PRs (merged into a throwaway worktree),
   so verify packaging changes by running the sync and checking the
   installed packages, not just the checkout.
   `extra-prs` can include reviewed upstream PRs by other authors, one number
   per line. No duplicate fork PR is needed. Runtime packages (default
   `quickshell`) rebuild when their recipe/patch, declared Qt dependencies, or
   installed version changes, independently of privileged-helper skew. The
   merged packaging tree takes priority over bundled recipes. Dev packaging-only
   changes also trigger a refresh. `--no-pkg` skips both paths.
   Qt 6.12 automatically selects compatibility PR14511 until upstream provides ShellColor or qualified Commons.Color. The qualified replacement suppresses obsolete PR14511 even in extra-prs. Verified mechanical rename/qualification conflicts preserve local behavior without a per-machine rerere cache. User plugin palette references migrate with backups before restart, including previous ShellColor migrations; broader conflicts still stop the sync.
   Compatibility workarounds live in independently removable quirks/<id> directories with phase hooks and retirement conditions (quirks/README.md). Config disabled_quirks or OMARCHY_DEV_SYNC_DISABLED_QUIRKS can disable named quirks; retire a fix by removing its directory.
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

PR ownership follows GitHub CLI's active account through `--author @me`, for both source and packaging repositories. Use `gh auth switch` to change accounts; Git remotes determine repository/fork URLs independently of the active account.

- List your open PRs: `gh pr list --repo <upstream-slug> --author @me --state open`
  (the script derives `<upstream-slug>` from the upstream remote URL).
  Packaging PRs live in a different repo: `gh pr list --repo
  omacom/omarchy-pkgs --author @me --state open`.
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
  clone's Apps list). Closing an omarchy-pkgs PR likewise drops it from the
  next package build.

## Known environment quirks

- The script auto-resolves append-only conflicts in
  `test/shell.d/theme-staging-test.sh` (`colour_only` / `denied` arrays) as
  a sorted union. Any other conflict aborts the rebuild and restores the
  previous integration branch. Packaging fetch failures or unresolved merge conflicts stop the refresh;
  rerere can reuse a verified manual resolution, but the script does not invent
  packaging logic resolutions. Independent upstream pkgver changes and PR
  pkgrel increases in the two dev PKGBUILDs are combined automatically only
  when all remaining content merges cleanly; this also works on fresh machines
  without a local rerere cache.
- `config-test.sh`, `snapper-test.sh`, `unowned-system-paths-test.sh` fail
  without an `omarchy-pkgs` checkout — environmental, unrelated to PR work.
- Environment-specific pre-existing failures exist (e.g.
  `test/shell.d/runtime-smoke-test.sh` IPC-handler count with multi-screen
  setups). If a failure looks unrelated, verify it fails without your change
  too before chasing it.
- Never install helpers into `/usr/lib/systemd/system-sleep/` (or anywhere
  outside the repo and home) without timeout guards: a prior agent session
  put an unbinding hook there that wedged in D-state and deadlocked every
  suspend. Sleep hooks must fail open (`timeout`, tolerate errors), never
  block the transaction.
