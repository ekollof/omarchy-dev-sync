#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/../lib/build-workspace.sh"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
export XDG_CACHE_HOME="$stage/cache"
cleanup_pkgs_worktree() { :; }
mkdir -p "$XDG_CACHE_HOME/omarchy-dev-sync/builds/run.abandoned"
touch "$XDG_CACHE_HOME/omarchy-dev-sync/builds/run.abandoned/large-build"
prepare_build_workspace
[[ ! -e $build_cache/run.abandoned && -d $build_workspace ]]
touch "$build_workspace/active"
# A separate process must not clean the active workspace.
if bash -c 'source "$1"; prepare_build_workspace' _ "$(dirname "$0")/../lib/build-workspace.sh"; then
  echo 'FAIL: concurrent build acquired the lock' >&2
  exit 1
fi
[[ -f $build_workspace/active ]]
cleanup_build_workspace
[[ ! -e $build_workspace ]]
echo 'PASS: abandoned builds removed, active builds protected, exit cleanup removes workspace'
