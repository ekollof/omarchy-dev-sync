# Portable quirks

Each quirk lives in its own directory with `quirk.sh` and any helpers. No machine-local rerere cache is required. Discovery is automatic in directory name order; remove a directory to retire the fix. Set `disabled_quirks="qt612-shell-color"` in config or `OMARCHY_DEV_SYNC_DISABLED_QUIRKS` to temporarily disable named quirks (space-separated).

The dispatcher receives `phase`, checkout path and fetched source base ref. Exit 0 means success, 2 means not applicable, and any other exit status stops the operation. Conflict phases must resolve and stage all conflicted files or leave them untouched. General phases may be no-ops when their condition no longer applies. Helpers must validate all planned resolutions before editing, preserve unrelated changes, and back up user config migrations.

| Phase | Contract |
|---|---|
| `select-prs` | Print only needed upstream PR numbers, one per line; diagnostics go to stderr. |
| `resolve-source` | Handle a source merge conflict, or return 2 without edits. |
| `resolve-packages` | Handle a packaging merge conflict, or return 2 without edits. |
| `before-restart` | Apply required user config compatibility migrations before shell restart. |

Every new quirk needs focused tests demonstrating activation, no-op/retirement conditions, and refusal to resolve unrelated changes.

`qt612-shell-color`: activates for Qt 6.12+ with the old palette on the fetched base. Selects PR14511 until upstream ships ShellColor or the qualified Commons.Color replacement. The `retired-prs` hook suppresses the obsolete rename PR even in extra-prs once upstream qualifies its palette. Resolves only verified mechanical palette changes, preserving feature behavior through a three-way merge. Migrates user plugin palette references with backups, including previous ShellColor migrations back to upstream Commons.Color. Remove this directory once supported source/plugin versions no longer need compatibility.

`dev-package-version`: resolves only independent upstream pkgver and PR pkgrel increases in the two dev PKGBUILDs, requiring all other content to merge cleanly. Inactive on clean merges; remove once stale packaging branches no longer require this compatibility.
