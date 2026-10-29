#!/bin/bash

# One sync per user, across repositories and copies of the tool. Keep the lock
# file in place: removing it could let another process lock a different inode.
acquire_sync_lock() {
  local lock_dir=${XDG_RUNTIME_DIR:-$HOME/.cache}/omarchy-dev-sync
  mkdir -p "$lock_dir"
  [[ -d $lock_dir && ! -L $lock_dir && -O $lock_dir ]] || return 1
  chmod 700 "$lock_dir"
  local lock_file=$lock_dir/sync.lock
  [[ ! -L $lock_file ]] || return 1
  # Self-update execs Bash with this open descriptor; keep the same lock.
  if [[ ${OMARCHY_DEV_SYNC_SELF_UPDATED:-} == 1 &&
        ${OMARCHY_DEV_SYNC_LOCK_FD:-} =~ ^[0-9]+$ ]] &&
    [[ $(readlink "/proc/$$/fd/$OMARCHY_DEV_SYNC_LOCK_FD") == "$lock_file" ]]; then
    sync_lock_fd=$OMARCHY_DEV_SYNC_LOCK_FD
    return 0
  fi
  exec {sync_lock_fd}>"$lock_file"
  if ! flock -n "$sync_lock_fd"; then
    terminal_warning 'Error: another omarchy-dev-sync is already running.' >&2
    exec {sync_lock_fd}>&-
    return 75
  fi
  export OMARCHY_DEV_SYNC_LOCK_FD=$sync_lock_fd
}

release_sync_lock() {
  if [[ -n ${sync_lock_fd:-} ]]; then
    # Unlock explicitly: a restarted shell/background child may inherit the fd.
    flock -u "$sync_lock_fd"
    exec {sync_lock_fd}>&-
    unset OMARCHY_DEV_SYNC_LOCK_FD
  fi
}
