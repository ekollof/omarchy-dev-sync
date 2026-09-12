# omarchy-dev-sync

Rebuild an [Omarchy](https://omarchy.org/) `dev link` checkout from **all of your open PRs**, so the live desktop runs every patch together.

If you keep several Omarchy PRs in flight, testing them one branch at a time misses interactions. This script fetches upstream, fast-forwards your PR branches, and rebuilds a throwaway integration branch (`integration-prs` by default) by merging each open PR onto `quattro`. The checkout stays on that branch, so `omarchy dev link` is already running the combined tree.

## What it does

1. Fetches the upstream remote (`origin`) and your fork (`fork`).
2. Lists **your** open PRs against that upstream with `gh`.
3. Fast-forwards each PR branch from the fork (or merges the remote tip if the local branch cannot fast-forward).
4. Checks out `$upstream/quattro` as `integration-prs` and merges every PR branch into it.
5. Force-pushes `integration-prs` to the fork with `--force-with-lease`.
6. Rebuilds and installs the `omarchy-settings-dev` and `omarchy-dev` packages from the rebuilt checkout when the packaged copies behind pkexec have gone stale, so helpers like `omarchy-windows-vm` keep elevating. Both packages go into a single pacman transaction (installed separately, the settings package conflicts with the installed release omarchy). The dev builds carry `epoch=1` so `dev.<sha>` sorts above official releases and `omarchy update` does not replace them.
7. Restarts the live Omarchy shell when this checkout is the session `OMARCHY_PATH`.

Known append-only conflicts in `test/shell.d/theme-staging-test.sh` (`colour_only` / `denied` arrays) are resolved as a sorted union. Anything else aborts the rebuild and restores the previous integration branch.

## Requirements

- A local Omarchy clone with:
  - `origin` → upstream (`omacom/omarchy`)
  - `fork` → your GitHub fork
- [`gh`](https://cli.github.com/) authenticated as the PR author
- Optional: `omarchy dev link` pointing at that clone
- Optional, for the automatic package refresh: an [omarchy-pkgs](https://github.com/omacom/omarchy-pkgs) checkout at `~/Work/omarchy/omarchy-pkgs` (or `OMARCHY_PKGBUILDS_DIR` pointed at one), and sudo for the pacman install

## Install

```bash
git clone https://github.com/ekollof/omarchy-dev-sync.git ~/src/omarchy-dev-sync
ln -sf ~/src/omarchy-dev-sync/omarchy-dev-sync ~/.local/bin/omarchy-dev-sync
```

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
```

| File / variable | Default | Meaning |
|---|---|---|
| `config` `repo` / `OMARCHY_DEV_SYNC_REPO` | `~/src/omarchy` | Omarchy checkout |
| `config` `upstream` / `OMARCHY_DEV_SYNC_UPSTREAM` | `origin` | Upstream remote |
| `config` `fork` / `OMARCHY_DEV_SYNC_FORK` | `fork` | Your fork remote |
| `config` `head` / `OMARCHY_DEV_SYNC_HEAD` | `quattro` | Upstream branch |
| `config` `integration` / `OMARCHY_DEV_SYNC_INTEGRATION` | `integration-prs` | Integration branch to rebuild |

To merge a branch **before** its PR is open, put the branch name in `extra-branches` (one per line, `#` comments allowed). Delete the line once the PR exists; `gh` will pick it up.

## Notes

- The working tree of the Omarchy checkout must be clean.
- The package refresh only runs when the checkout and the installed package actually differ (`omarchy-windows-vm` and similar helpers compare the two and refuse to elevate on skew); `--no-pkg` skips it entirely.
- This is not part of Omarchy itself. It is a personal workflow published in case it is useful to other people with a stack of open PRs.
