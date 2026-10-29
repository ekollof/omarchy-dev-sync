#!/bin/bash

# Keep a private transcript and one exit path for explicit exits and errexit.
start_workflow() {
  local log_dir=${XDG_STATE_HOME:-$HOME/.local/state}/omarchy-dev-sync/logs
  mkdir -p "$log_dir"
  chmod 700 "$log_dir"
  workflow_log=$(mktemp "$log_dir/sync.XXXXXXXX.log")
  exec {workflow_stdout}>&1 {workflow_stderr}>&2
  exec > >(tee -a "$workflow_log")
  workflow_logger=$!
  exec 2> >(tee -a "$workflow_log" >&2)
  workflow_error_logger=$!
  workflow_phase=sync
  trap finish_workflow EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
}

finish_workflow() {
  local status=$? prompt
  trap - EXIT INT TERM
  set +e
  if [[ -n ${build_workspace:-} ]]; then
    cleanup_build_workspace
  fi
  # Close the transcript before launching an interactive agent and release the
  # build lock so its retry can build packages.
  if [[ -n ${build_lock:-} ]]; then exec {build_lock}>&-; fi
  exec 1>&$workflow_stdout 2>&$workflow_stderr
  wait "$workflow_logger" "$workflow_error_logger"
  if (( status != 0 && status != 130 && status != 143 )) &&
    [[ $agent_on_failure == 1 && ${OMARCHY_DEV_SYNC_TROUBLESHOOTING:-0} != 1 ]]; then
    prompt="Diagnose and fix the omarchy-dev-sync $workflow_phase failure (exit $status). Read the transcript at $workflow_log. Sync tool source: $script_dir. Omarchy checkout: $repo. Integration branch: $integration."
    prompt+=" For system update failures also inspect /tmp/omarchy-update.log. Follow the omarchy-dev skill: fix source on individual feature/PR branches, never edit the disposable integration branch directly. Preserve unrelated changes. Verify the fix and retry with OMARCHY_DEV_SYNC_TROUBLESHOOTING=1 to avoid recursive troubleshooting. Do not publish PR comments or reboot without approval."
    echo "Starting the default agent to troubleshoot $workflow_phase; log: $workflow_log" >&2
    if command -v omarchy-agent >/dev/null; then
      (cd "$script_dir" && OMARCHY_DEV_SYNC_TROUBLESHOOTING=1 omarchy-agent --prompt "$prompt") ||
        echo "Warning: default agent could not complete troubleshooting; see $workflow_log" >&2
    else
      echo "Warning: omarchy-agent unavailable; see $workflow_log" >&2
    fi
  fi
  exit "$status"
}

update_integrated_system() {
  [[ $system_update == 1 ]] || return 0
  workflow_phase='system update'
  echo "Updating the system from $repo ($integration)..."
  # Use the integrated updater and its migrations, not a packaged/other checkout.
  OMARCHY_PATH="$repo" PATH="$repo/bin:$PATH" "$repo/bin/omarchy-update" -y
  workflow_phase=sync
}
