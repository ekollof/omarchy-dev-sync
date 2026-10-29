# omarchy-dev-sync

Rebuild an [Omarchy](https://omarchy.org/) `dev link` checkout from **all of your open PRs and selected upstream PRs**, so the live desktop runs every patch together.

If you keep several Omarchy PRs in flight, testing them one branch at a time misses interactions. This script fetches upstream, fast-forwards your PR branches, and rebuilds a throwaway integration branch (`integration-prs` by default) by merging each open PR onto `quattro`. The checkout stays on that branch, so `omarchy dev link` is already running the combined tree.

## What it does

Only one sync can run at a time per user, including across checkouts. A second invocation exits immediately with status `75` before self-update, Git operations, or package work. The lock survives self-update and is released on exit or before launching the troubleshooting agent. `--help` remains available while a sync is running.

Before syncing, it checks its own Git tracking branch and fast-forwards a clean checkout to the latest commit, then restarts with the original arguments. Local changes, detached HEAD, missing tracking branches, ahead/diverged history, or fetch failures leave the existing version running with a warning. Copies outside a Git checkout run without self-updating. `--help` never fetches. Use `--no-self-update`, `self_update=0` in the config, or `OMARCHY_DEV_SYNC_SELF_UPDATE=0` to disable it.

1. Fetches the upstream remote (`origin`) and your fork (`fork`).
2. Lists **your** open PRs against that upstream with `gh`.
3. Fast-forwards each PR branch from the fork (or merges the remote tip if the local branch cannot fast-forward).
4. Checks out `$upstream/quattro` as `integration-prs` and merges every PR branch into it.
5. Force-pushes `integration-prs` to the fork with `--force-with-lease`.
6. Rebuilds and installs the `omarchy-settings-dev` and `omarchy-dev` packages from the rebuilt checkout when the packaged copies behind pkexec or their packaging recipes have gone stale, so helpers like `omarchy-windows-vm` keep elevating. Your open omarchy-pkgs PRs are merged into a disposable worktree first, so the packages under test include your packaging fixes. Both packages go into a single pacman transaction (installed separately, the settings package conflicts with the installed release omarchy). The dev builds carry `epoch=1` so `dev.<sha>` sorts above official releases and `omarchy update` does not replace them.
7. Checks installed runtime packages independently of Omarchy helper differences. Quickshell uses the merged omarchy-pkgs recipe when available, otherwise the bundled Arch recipe with upstream Qt 6.12 fix `5d5d498`. A recipe/patch change, an installed Qt dependency change, or replacement of the installed package triggers a rebuild. Successful installations are recorded under `${XDG_STATE_HOME:-~/.local/state}/omarchy-dev-sync/packages`; unchanged packages are skipped. A build/install failure stops before restarting the shell.
8. Restarts the live Omarchy shell when this checkout is the session `OMARCHY_PATH`.

Before restarting, it checks the persistent dev link in `/etc/omarchy.conf`. When that link points at the synced checkout, it aligns known Omarchy stable/rc URLs in `/etc/pacman.conf` and `/etc/pacman.d/mirrorlist` with edge, preserving custom repositories, settings and comments. Changed files get `*.bak.omarchy-dev-sync.*` backups. The full system update now runs automatically after integration and mirror alignment, before package rebuilds so runtime packages build against the upgraded dependencies. This prevents development migrations from requesting packages missing from stable. Packaged installations and other linked checkouts are untouched. Repair needs sudo in a terminal or pkexec otherwise; failure stops the sync. This check also runs with `--no-pkg`; use `--no-package-sources`, config `package_sources=0`, or `OMARCHY_DEV_SYNC_PACKAGE_SOURCES=0` to opt out.

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

Run these steps as your normal user in a terminal on an existing Omarchy installation. You need Git, Python 3, an authenticated GitHub CLI (`gh auth login`), and sudo access for dev-link setup and package installation.

1. Prepare an Omarchy source checkout. If you do not already have one:

   ```bash
   mkdir -p ~/src
   git clone --branch quattro https://github.com/omacom/omarchy.git ~/src/omarchy
   git -C ~/src/omarchy remote add fork git@github.com:YOUR-GITHUB-USERNAME/omarchy.git
   ```

   Replace `YOUR-GITHUB-USERNAME` with your account and create your Omarchy fork on GitHub first. The default remote names are `origin` for upstream and `fork` for your fork. For an existing checkout, inspect `git remote -v` and use the configuration below if your names differ. The installer does not clone Omarchy or create your fork.

2. Clone this tool:

   ```bash
   git clone https://github.com/ekollof/omarchy-dev-sync.git ~/src/omarchy-dev-sync
   cd ~/src/omarchy-dev-sync
   ```

3. If your checkout or remote names differ from the defaults, create or edit `~/.config/omarchy-dev-sync/config` before installing:

   ```bash
   mkdir -p ~/.config/omarchy-dev-sync
   # Edit this file; preserve any existing settings.
   $EDITOR ~/.config/omarchy-dev-sync/config
   ```

   Example contents:

   ```bash
   repo=$HOME/src/omarchy
   upstream=origin
   fork=fork
   head=quattro
   ```

   Both the installer and sync honor `OMARCHY_DEV_SYNC_CONFIG` and `OMARCHY_DEV_SYNC_REPO`. See [Configuration](#configuration) for other settings and optional packaging checkout setup.

4. Run the installer without sudo:

   ```bash
   ./install.sh
   ```

   It checks the configured checkout, the persistent link in `/etc/omarchy.conf`, and the running session. If the checkout is not dev-linked, it warns about unstable development code, privileged commands, edge packages, and migrations, then asks `Enable this development setup? [y/N]`. Enter `y` or `yes` to run `omarchy dev link <checkout> --no-reboot`. Declining or closed stdin cancels installation. Run the installer directly in a terminal so you can review and answer the prompt.

   **Development branches and integrated PRs can break the desktop, updates, or boot.** Dev linking trusts your writable checkout for system commands, including privileged commands. Keep backups and a recovery method. `omarchy dev unlink` restores the packaged path after reboot, but does not undo package upgrades or migrations.

   The installer links the launcher at `~/.local/bin/omarchy-dev-sync`, registers `omarchy dev sync` with a symlink in the configured checkout’s `bin/`, and installs the bundled agent skills. The command link is ignored locally through Git’s `info/exclude`; it is not committed or included in package-skew checks. Existing commands are preserved, and registration conflicts stop installation. It does not run a sync, system update, or reboot. If the correct link is already configured, it leaves it in place.

5. If the installer says the link is not active, reboot before syncing. Changing `OMARCHY_PATH` in a terminal does not activate the link across the desktop session. You can rerun `./install.sh` after reboot to check that the link is configured and active.

6. Ensure `~/.local/bin` is on your `PATH`, then run:

   ```bash
   omarchy dev sync --help
   omarchy dev sync
   ```

   The standalone `omarchy-dev-sync` command remains available. Rerun `./install.sh` to register the subcommand on an existing installation.

   A normal sync rebuilds integration, runs the full system updater and migrations, refreshes development/runtime packages, and restarts the live shell. It can request sudo authorization. Use `--no-system-update` to skip the system update, `--no-pkg` to skip package builds, or `--no-restart` to skip the shell restart.

For automatic troubleshooting, select an installed default agent with `omarchy default agent <name>`. Failures launch that agent with the sync log and checkout paths. Use `--no-agent` to disable this behavior.

The installer and sync startup install the `omarchy-dev` skill in `~/.agents/skills`, `~/.claude/skills`, `${XDG_CONFIG_HOME:-~/.config}/opencode/skills`, and `${CODEX_HOME:-~/.codex}/skills`. Missing skills become symlinks to this checkout. Changed copies are refreshed with `omarchy-dev.bak.*` backups; unrelated symlinks are preserved with a warning. Manual skill links are not required. Keep this tool’s checkout in place because the launcher and skills link to it.

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

For a reviewed PR by another author, put its upstream PR number in `extra-prs` (one per line; `#` comments allowed). The script fetches upstream pull refs directly, so no fork branch or duplicate PR is needed. Closed (including merged) PRs and deleted PRs are automatically removed from this file before selection. A missing PR is removed only when GitHub confirms the repository remains accessible. Invalid entries, authentication/network errors or a failed fetch stop before rebuilding integration; status-check failures preserve the entire selection file. Comments and remaining entries are retained. Open PRs remain selected even if their fixes are incorporated through another branch.

## Validation

```bash
python3 tests/self-update-test.py
python3 tests/extra-prs-test.py
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
- Dev package refresh compares every checkout `bin/omarchy-*` command and file under `install/helpers/` with its installed copy, detecting missing files as well as changed contents. It also checks packaging recipe fingerprints. This catches newly added migration helpers even when no existing privileged command changes. Runtime package refresh checks its own recipe, installed version, and declared ABI dependencies. `--no-pkg` skips all package work. The first package-enabled sync establishes fingerprints, so it rebuilds packages once even if a matching local rebuild was previously installed by hand.
- Package workspaces live under `${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-dev-sync/builds`, avoiding `/tmp` quotas. Normal exits, errors and handled interruptions remove the current workspace; the next package-enabled run removes abandoned workspaces. A lock prevents concurrent package builds from deleting each other's files. Older untracked `/tmp/omarchy-dev-sync-*` directories are left alone because they may belong to a still-running older version.
- The omarchy-pkgs PR merge is local only: nothing is pushed. Fetch failures and unresolved merge conflicts stop package refresh so packaging patches cannot silently disappear. For the two dev PKGBUILDs, independent upstream `pkgver` changes and PR `pkgrel` increases are combined automatically, preserving the upstream version and PR release bump; all remaining content must merge cleanly with Git. Git rerere can also replay a resolution you have verified by hand. With PR merging enabled, recipes come from a disposable worktree of the freshly fetched default branch even when no PR is open; the original checkout stays untouched.
- This is not part of Omarchy itself. It is a personal workflow published in case it is useful to other people with a stack of open PRs.

Sync now runs the integrated checkout’s `bin/omarchy-update -y` after integration and mirror alignment, before package builds and shell restart. This includes system packages and migrations. Skip with `--no-system-update`, config `system_update=0`, or `OMARCHY_DEV_SYNC_SYSTEM_UPDATE=0`. `--no-pkg` and `--no-restart` only skip their respective steps.

Failures launch Omarchy’s default agent with a private transcript under `${XDG_STATE_HOME:-~/.local/state}/omarchy-dev-sync/logs`, the failed phase, and checkout paths. Cleanup and build-lock release happen first. The original failure exit status is preserved; interruptions do not launch an agent. Skip with `--no-agent`, config `agent_on_failure=0`, or `OMARCHY_DEV_SYNC_AGENT_ON_FAILURE=0`. Agent retries inherit `OMARCHY_DEV_SYNC_TROUBLESHOOTING=1` to prevent recursive launches. A configured default agent and `omarchy-agent` are required.
