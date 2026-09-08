# omarchy-dev-sync

Rebuild an [Omarchy](https://omarchy.org/) `dev link` checkout from **all of your open PRs**, so the live desktop runs every patch together.

If you keep several Omarchy PRs in flight, testing them one branch at a time misses interactions. This script fetches upstream, fast-forwards your PR branches, and rebuilds a throwaway integration branch (`integration-prs` by default) by merging each open PR onto `quattro`. The checkout stays on that branch, so `omarchy dev link` is already running the combined tree.

## What it does

1. Fetches the upstream remote (`origin`) and your fork (`fork`).
2. Lists **your** open PRs against that upstream with `gh`.
3. Fast-forwards each PR branch from the fork (or merges the remote tip if the local branch cannot fast-forward).
4. Checks out `$upstream/quattro` as `integration-prs` and merges every PR branch into it.
5. Force-pushes `integration-prs` to the fork with `--force-with-lease`.
6. Restarts the live Omarchy shell when this checkout is the session `OMARCHY_PATH`.

Known append-only conflicts in `test/shell.d/theme-staging-test.sh` (`colour_only` / `denied` arrays) are resolved as a sorted union. Anything else aborts the rebuild and restores the previous integration branch.

## Requirements

- A local Omarchy clone with:
  - `origin` → upstream (`omacom/omarchy`)
  - `fork` → your GitHub fork
- [`gh`](https://cli.github.com/) authenticated as the PR author
- Optional: `omarchy dev link` pointing at that clone

## Install

```bash
git clone https://github.com/ekollof/omarchy-dev-sync.git ~/src/omarchy-dev-sync
ln -sf ~/src/omarchy-dev-sync/omarchy-dev-sync ~/.local/bin/omarchy-dev-sync
```

Then from anywhere:

```bash
omarchy-dev-sync
```

Skip the shell restart with `omarchy-dev-sync --no-restart`.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `OMARCHY_DEV_SYNC_REPO` | `~/src/omarchy` | Omarchy checkout |
| `OMARCHY_DEV_SYNC_UPSTREAM` | `origin` | Upstream remote |
| `OMARCHY_DEV_SYNC_FORK` | `fork` | Your fork remote |
| `OMARCHY_DEV_SYNC_HEAD` | `quattro` | Upstream branch |
| `OMARCHY_DEV_SYNC_INTEGRATION` | `integration-prs` | Integration branch to rebuild |
| `OMARCHY_DEV_SYNC_CONFIG` | `~/.config/omarchy-dev-sync` | Config directory |

To merge a branch **before** its PR is open, put the branch name in `~/.config/omarchy-dev-sync/extra-branches` (one per line, `#` comments allowed). Delete the line once the PR exists; `gh` will pick it up.

## Notes

- The working tree of the Omarchy checkout must be clean.
- `pkexec` still runs packaged copies under `/usr/bin`. Helpers that compare checkout vs package (today: `omarchy-windows-vm`) will refuse to elevate until you refresh the package with `omarchy-dev-pkg-test`.
- This is not part of Omarchy itself. It is a personal workflow published in case it is useful to other people with a stack of open PRs.
