#!/bin/bash

# Serialize package work and remove only private workspaces from earlier runs.
prepare_build_workspace() {
  local stale
  build_cache=${XDG_CACHE_HOME:-$HOME/.cache}/omarchy-dev-sync/builds
  [[ ! -L $build_cache ]] || return 1
  mkdir -p "$build_cache" || return 1
  [[ -O $build_cache ]] || return 1
  chmod 700 "$build_cache" || return 1
  exec {build_lock}>"$build_cache/lock"
  if ! flock -n "$build_lock"; then
    echo "Error: another dev-sync package build is running." >&2
    return 1
  fi
  for stale in "$build_cache"/run.*; do
    [[ -d $stale && ! -L $stale && -O $stale ]] || continue
    rm -rf -- "$stale" || return 1
  done
  build_workspace=$(mktemp -d "$build_cache/run.XXXXXX") || return 1
}

cleanup_build_workspace() {
  cleanup_pkgs_worktree
  if [[ -n ${build_workspace:-} ]]; then
    rm -rf -- "$build_workspace"
  fi
}
