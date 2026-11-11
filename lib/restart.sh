#!/bin/bash

# A secure session lock intentionally blocks omarchy-restart-shell: killing the
# live lock client would strand the session behind Hyprland's failsafe. That is
# an expected condition, not a sync failure, so defer the restart until the next
# login or a manual `omarchy restart shell`.
restart_live_shell() {
  local session_path output status
  (( restart )) || return 0
  session_path=$(systemctl --user show-environment 2>/dev/null | sed -n 's/^OMARCHY_PATH=//p' | tail -n 1)
  [[ $session_path == "$repo" ]] || return 0
  command -v omarchy-restart-shell >/dev/null || return 0
  if output=$(omarchy-restart-shell 2>&1); then
    [[ -z $output ]] || printf '%s\n' "$output"
    echo "Restarted the live Omarchy shell so it runs this $integration build."
    return 0
  else
    status=$?
  fi
  [[ -z $output ]] || printf '%s\n' "$output" >&2
  if [[ $output == *"Refusing to restart Omarchy shell while the session is locked."* ]]; then
    terminal_warning "Note: the session is locked; the running shell was left alone."
    terminal_warning "      Run 'omarchy restart shell' after unlocking to load this $integration build."
    return 0
  fi
  terminal_error "Error: $integration rebuilt, but the live shell was not restarted." >&2
  return "$status"
}
