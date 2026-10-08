# omarchy-dev-sync

Rebuild an [Omarchy](https://omarchy.org/) `dev link` checkout from **all of your open PRs and selected upstream PRs**, so the live desktop runs every patch together.

If you keep several Omarchy PRs in flight, testing them one branch at a time misses interactions. This script fetches upstream, fast-forwards your PR branches, and rebuilds a throwaway integration branch (`integration-prs` by default) by merging each open PR onto `quattro`. The checkout stays on that branch, so `omarchy dev link` is already running the combined tree.

## What it does

Before syncing, it checks its own Git tracking branch and fast-forwards a clean checkout to the latest commit, then restarts with the original arguments. Local changes, detached HEAD, missing tracking branches, ahead/diverged history, or fetch failures leave the existing version running with a warning. Copies outside a Git checkout run without self-updating. `--help` never fetches. Use `--no-self-update`, `self_update=0` in the config, or `OMARCHY_DEV_SYNC_SELF_UPDATE=0` to disable it.

1. Fetches the upstream remote (`origin`) and your fork (`fork`).
2. Lists **your** open PRs against that upstream with `gh`.
3. Fast-forwards each PR branch from the fork (or merges the remote tip if the local branch cannot fast-forward).
4. Checks out `$upstream/quattro` as `integration-prs` and merges every PR branch into it.
5. Force-pushes `integration-prs` to the fork with `--force-with-lease`.
6. Rebuilds and installs the `omarchy-settings-dev` and `omarchy-dev` packages from the rebuilt checkout when the packaged copies behind pkexec or their packaging recipes have gone stale, so helpers like `omarchy-windows-vm` keep elevating. Your open omarchy-pkgs PRs are merged into a disposable worktree first, so the packages under test include your packaging fixes. Both packages go into a single pacman transaction (installed separately, the settings package conflicts with the installed release omarchy). The dev builds carry `epoch=1` so `dev.<sha>` sorts above official releases and `omarchy update` does not replace them.
7. Checks installed runtime packages independently of Omarchy helper differences. Quickshell uses the merged omarchy-pkgs recipe when available, otherwise the bundled Arch recipe with upstream Qt 6.12 fix `5d5d498`. A recipe/patch change, an installed Qt dependency change, or replacement of the installed package triggers a rebuild. Successful installations are recorded under `${XDG_STATE_HOME:-~/.local/state}/omarchy-dev-sync/packages`; unchanged packages are skipped. A build/install failure stops before restarting the shell.
8. Restarts the live Omarchy shell when this checkout is the session `OMARCHY_PATH`.

Before restarting, it checks the persistent dev link in `/etc/omarchy.conf`. When that link points at the synced checkout, it aligns known Omarchy stable/rc URLs in `/etc/pacman.conf` and `/etc/pacman.d/mirrorlist` with edge, preserving custom repositories, settings and comments. Changed files get `*.bak.omarchy-dev-sync.*` backups. It does not refresh package databases or perform a system upgrade: run `omarchy update` afterwards. This prevents development migrations from requesting packages missing from stable. Packaged installations and other linked checkouts are untouched. Repair needs sudo in a terminal or pkexec otherwise; failure stops the sync. This check also runs with `--no-pkg`; use `--no-package-sources`, config `package_sources=0`, or `OMARCHY_DEV_SYNC_PACKAGE_SOURCES=0` to opt out.

Known append-only conflicts in `test/shell.d/theme-staging-test.sh` (`colour_only` / `denied` arrays) are resolved as a sorted union. Other conflicts require a matching verified quirk; unresolved conflicts abort the rebuild and restore the previous integration branch.

Compatibility fixes live in independently removable `quirks/<id>/` directories. The [quirk contract](quirks/README.md) defines activation, source/package conflict and pre-restart hooks, including retirement rules. Each quirk checks whether it is still needed. Disable named quirks with config `disabled_quirks="qt612-shell-color"` or `OMARCHY_DEV_SYNC_DISABLED_QUIRKS` (space-separated); deleting a quirk directory retires it without editing the main script.

Qt 6.12 compatibility is portable: installed Qt 6.12 or newer automatically includes upstream PR #14511 until upstream ships `ShellColor` or its qualified `Commons.Color` replacement. The latter also suppresses obsolete PR #14511 entries in `extra-prs`. Verified mechanical palette rename/qualification conflicts preserve feature behavior through a three-way merge; unrelated conflicts still stop the sync. Before restart, user plugin QML importing `qs.Commons` is migrated for actual palette members with per-file backups, including previous `ShellColor` migrations back to upstream qualification. Unrelated Qt color members, qualified imports and symlinked plugins are preserved. No saved rerere cache is required.

## Requirements

- A local Omarchy clone with:
  - `origin` → upstream (`omacom/omarchy`)
  - `fork` → your GitHub fork
- [`gh`](https://cli.github.com/) authenticated as the PR author
- Optional: `omarchy dev link` pointing at that clone

- Optional, for the automatic package refresh: an [omarchy-pkgs](https://github.com/omacom/omarchy-pkgs) checkout at `~/Work/omarchy/omarchy-pkgs` (or `OMARCHY_PKGBUILDS_DIR` pointed at one), and sudo for terminal installs (pkexec for noninteractive callers). Runtime builds also need their PKGBUILD build dependencies; terminal calls let makepkg install them, while agent/background calls must install missing dependencies separately. Your open PRs against omacom/omarchy-pkgs are merged into a throwaway worktree for the build; the checkout itself is never modified. Point `OMARCHY_PKGBUILDS_DIR` at a directory to use those PKGBUILDs as-is and skip the PR merge.

PR ownership follows the active GitHub CLI account: both source and packaging queries use `gh pr list --author @me`. Switch accounts with `gh auth switch`; no username is configured or hardcoded in the script. Upstream, fork and self-update URLs come from Git remotes. The clone URL below identifies this project's repository, not the account whose PRs are selected.

## Install

```bash
git clone https://github.com/ekollof/omarchy-dev-sync.git ~/src/omarchy-dev-sync
ln -sf ~/src/omarchy-dev-sync/omarchy-dev-sync ~/.local/bin/omarchy-dev-sync
```

The script installs the `omarchy-dev` agent skill on its first run so coding agents know this
workflow (dev-linked checkout, never edit the integration branch directly,
verify with `./test/shell` / `./test/cli`, never post PR comments without
approval). The skill lives in `skills/omarchy-dev/`; link it where your
agent looks for global skills. To install it before the first run, link it manually:

```bash
ln -sf ~/src/omarchy-dev-sync/skills/omarchy-dev ~/.config/opencode/skills/omarchy-dev
# Claude Code and compatible agents also discover these locations:
ln -sf ~/src/omarchy-dev-sync/skills/omarchy-dev ~/.claude/skills/omarchy-dev
ln -sf ~/src/omarchy-dev-sync/skills/omarchy-dev ~/.agents/skills/omarchy-dev
```

Startup installs missing `omarchy-dev` skills in `~/.agents/skills`, `~/.claude/skills`, `${XDG_CONFIG_HOME:-~/.config}/opencode/skills`, and `${CODEX_HOME:-~/.codex}/skills` as symlinks to the bundled skill, creating parent directories as needed. Existing changed copies are replaced with the bundled skill directory, with the previous directory retained as `omarchy-dev.bak.*`. Unchanged copies are skipped; symlinks into this checkout update automatically, and symlinks elsewhere are preserved with a warning. Skill installation and refresh also run after manual Git pulls and with `--no-self-update` or `self_update=0`; `--help` does not install anything.

Then from anywhere:

```bash
omarchy-dev-sync
```

Skip the shell restart with `omarchy-dev-sync --no-restart`. Skip the package rebuild with `--no-pkg`.

## Configuration

Settings live in `~/.config/omarchy-dev-sync/` (override the directory with `OMARCHY_DEV_SYNC_CONFIG`).

`config` is sourced as bash. Environment variables still win over the file.

```bash
# ~/.config/omarchy-dev-sync/config
repo=$HOME/src/omarchy
upstream=origin
fork=fork
head=quattro
integration=integration-prs
pkgs_repo=$HOME/Work/omarchy/omarchy-pkgs
pkgs_prs=1
runtime_packages="quickshell"
self_update=1
package_sources=1
```

| File / variable | Default | Meaning |
|---|---|---|
| `config` `repo` / `OMARCHY_DEV_SYNC_REPO` | `~/src/omarchy` | Omarchy checkout |
| `config` `upstream` / `OMARCHY_DEV_SYNC_UPSTREAM` | `origin` | Upstream remote |
| `config` `fork` / `OMARCHY_DEV_SYNC_FORK` | `fork` | Your fork remote |
| `config` `head` / `OMARCHY_DEV_SYNC_HEAD` | `quattro` | Upstream branch |
| `config` `integration` / `OMARCHY_DEV_SYNC_INTEGRATION` | `integration-prs` | Integration branch to rebuild |
| `config` `pkgs_repo` / `OMARCHY_DEV_SYNC_PKGS_REPO` | `~/Work/omarchy/omarchy-pkgs` | omarchy-pkgs checkout for package builds |
| `config` `pkgs_prs` / `OMARCHY_DEV_SYNC_PKGS_PRS` | `1` | Merge your open omarchy-pkgs PRs into a disposable worktree for the package build |

To merge a branch **before** its PR is open, put the branch name in `extra-branches` (one per line, `#` comments allowed). Delete the line once the PR exists; `gh` will pick it up.

For a reviewed PR by another author, put its upstream PR number in `extra-prs` (one per line; `#` comments allowed). The script fetches upstream pull refs directly, so no fork branch or duplicate PR is needed. Invalid entries or a failed fetch stop before rebuilding integration. Remove an entry once its fix is merged upstream.

## Validation

```bash
python3 tests/self-update-test.py
bash tests/skill-refresh-test.sh
python3 tests/package-version-merge-test.py
python3 tests/dev-package-sources-test.py
python3 tests/shell-color-compat-test.py
bash tests/quirks-test.sh
bash tests/package-state-test.sh
python3 tests/sync-runtime-test.py
```

These tests cover selected PR inclusion, runtime refresh with zero helper skew, Qt/patch/package changes, unchanged-build skipping, and failure handling without touching the real desktop or package database.

## Notes

- The working tree of the Omarchy checkout must be clean.
- Dev package refresh checks both privileged-helper skew and packaging recipe fingerprints. Runtime package refresh checks its own recipe, installed version, and declared ABI dependencies. `--no-pkg` skips all package work. The first package-enabled sync establishes fingerprints, so it rebuilds packages once even if a matching local rebuild was previously installed by hand.
- The omarchy-pkgs PR merge is local only: nothing is pushed. Fetch failures and unresolved merge conflicts stop package refresh so packaging patches cannot silently disappear. For the two dev PKGBUILDs, independent upstream `pkgver` changes and PR `pkgrel` increases are combined automatically, preserving the upstream version and PR release bump; all remaining content must merge cleanly with Git. Git rerere can also replay a resolution you have verified by hand. With PR merging enabled, recipes come from a disposable worktree of the freshly fetched default branch even when no PR is open; the original checkout stays untouched.
- This is not part of Omarchy itself. It is a personal workflow published in case it is useful to other people with a stack of open PRs.
