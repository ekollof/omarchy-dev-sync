#!/bin/bash

# Symlinks follow Git automatically; refresh installed copies with a backup.
refresh_local_dev_skills() {
  local source=$1 destination parent staging backup
  local skill_home=${2:-$HOME}
  local skill_config=${3:-${XDG_CONFIG_HOME:-$HOME/.config}}
  local skill_codex=${4:-${CODEX_HOME:-$HOME/.codex}}
  [[ -f $source/SKILL.md ]] || return 0
  local -a destinations=(
    "$skill_home/.agents/skills/omarchy-dev"
    "$skill_home/.claude/skills/omarchy-dev"
    "$skill_config/opencode/skills/omarchy-dev"
    "$skill_codex/skills/omarchy-dev"
  )
  for destination in "${destinations[@]}"; do
    if [[ -L $destination ]]; then
      if [[ $(readlink -f "$destination") != "$(readlink -f "$source")" ]]; then
        echo "Warning: leaving unrelated skill symlink unchanged: $destination" >&2
      fi
      continue
    fi
    [[ -d $destination && -f $destination/SKILL.md ]] || continue
    diff -qr "$source" "$destination" >/dev/null && continue
    parent=${destination%/*}
    staging=$(mktemp -d "$parent/.omarchy-dev-update.XXXXXX") || return 1
    if ! cp -a "$source/." "$staging/"; then
      rm -rf "$staging"
      return 1
    fi
    backup=$(mktemp -d "$destination.bak.XXXXXX") || {
      rm -rf "$staging"
      return 1
    }
    rmdir "$backup"
    if ! mv "$destination" "$backup"; then
      rm -rf "$staging"
      return 1
    fi
    if ! mv "$staging" "$destination"; then
      mv "$backup" "$destination"
      rm -rf "$staging"
      return 1
    fi
    echo "Updated local omarchy-dev skill: $destination (backup: $backup)"
  done
}

# Only fast-forward a clean checkout; never stash, reset, or merge local work.
self_update_checkout() {
  local checkout=$1 script=$2 branch remote merge_ref current target status
  shift 2
  [[ -z ${OMARCHY_DEV_SYNC_SELF_UPDATED:-} ]] || return 0
  [[ $(git -C "$checkout" rev-parse --show-toplevel 2>/dev/null) == "$checkout" ]] || return 0
  branch=$(git -C "$checkout" symbolic-ref --quiet --short HEAD) || {
    echo "Warning: self-update skipped (detached HEAD)." >&2
    return 0
  }
  remote=$(git -C "$checkout" config --get "branch.$branch.remote") || remote=
  merge_ref=$(git -C "$checkout" config --get "branch.$branch.merge") || merge_ref=
  if [[ -z $remote || $remote == "." || $merge_ref != refs/heads/* ]]; then
    echo "Warning: self-update skipped (no remote tracking branch)." >&2
    return 0
  fi
  status=$(git -C "$checkout" status --porcelain) || return 1
  if [[ -n $status ]]; then
    echo "Warning: self-update skipped ($checkout has local changes)." >&2
    return 0
  fi
  echo "Checking omarchy-dev-sync for updates ($remote/${merge_ref#refs/heads/})..."
  if ! GIT_TERMINAL_PROMPT=0 git -C "$checkout" fetch --quiet "$remote" "$merge_ref"; then
    echo "Warning: self-update fetch failed; continuing with the installed version." >&2
    return 0
  fi
  current=$(git -C "$checkout" rev-parse HEAD)
  target=$(git -C "$checkout" rev-parse FETCH_HEAD)
  [[ $current != "$target" ]] || return 0
  if ! git -C "$checkout" merge-base --is-ancestor "$current" "$target"; then
    echo "Warning: self-update skipped (local history is ahead or diverged)." >&2
    return 0
  fi
  # Recheck after the fetch in case a local edit happened meanwhile.
  if [[ -n $(git -C "$checkout" status --porcelain) ]]; then
    echo "Warning: self-update skipped (checkout changed during fetch)." >&2
    return 0
  fi
  if ! git -C "$checkout" merge --ff-only "$target"; then
    echo "Error: self-update failed; stopping before syncing Omarchy." >&2
    return 1
  fi
  echo "Updated omarchy-dev-sync to ${target:0:7}; restarting..."
  export OMARCHY_DEV_SYNC_SELF_UPDATED=1
  exec bash "$script" "$@"
}
