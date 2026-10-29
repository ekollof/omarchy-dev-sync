#!/bin/bash

# Persist the setup selected by the installer without replacing user files.
initialize_sync_config() {
  local name value selection
  local -a names=(repo upstream fork head integration restart pkg_build pkgs_repo
    pkgs_prs runtime_packages self_update package_sources system_update
    agent_on_failure disabled_quirks)
  mkdir -p "$config_dir" || return 1
  if [[ ! -e $config_dir/config && ! -L $config_dir/config ]]; then
    (
      umask 077
      set -o noclobber
      {
        printf '# omarchy-dev-sync settings (Bash assignments).\n'
        printf '# OMARCHY_DEV_SYNC_* environment variables override these values.\n'
        for name in "${names[@]}"; do
          case $name in
            repo|upstream|fork|head|pkgs_repo) value=${!name} ;;
            integration) value=${OMARCHY_DEV_SYNC_INTEGRATION:-integration-prs} ;;
            restart) value=${OMARCHY_DEV_SYNC_RESTART:-1} ;;
            pkg_build) value=${OMARCHY_DEV_SYNC_PKG:-1} ;;
            pkgs_prs) value=${OMARCHY_DEV_SYNC_PKGS_PRS:-1} ;;
            runtime_packages) value=${OMARCHY_DEV_SYNC_RUNTIME_PACKAGES-quickshell} ;;
            self_update) value=${OMARCHY_DEV_SYNC_SELF_UPDATE:-1} ;;
            package_sources) value=${OMARCHY_DEV_SYNC_PACKAGE_SOURCES:-1} ;;
            system_update) value=${OMARCHY_DEV_SYNC_SYSTEM_UPDATE:-1} ;;
            agent_on_failure) value=${OMARCHY_DEV_SYNC_AGENT_ON_FAILURE:-1} ;;
            disabled_quirks) value=${OMARCHY_DEV_SYNC_DISABLED_QUIRKS-} ;;
          esac
          printf '%s=%q\n' "$name" "$value"
        done
      } > "$config_dir/config"
    ) || return 1
    terminal_success "Created default config: $config_dir/config"
  fi
  for selection in extra-branches extra-prs; do
    [[ ! -e $config_dir/$selection && ! -L $config_dir/$selection ]] || continue
    (
      umask 077
      set -o noclobber
      {
        if [[ $selection == extra-branches ]]; then
          printf '# Optional fork branches without open PRs, one branch name per line.\n'
        else
          printf '# Optional upstream PR numbers by other authors, one number per line.\n'
        fi
      } > "$config_dir/$selection"
    ) || return 1
  done
}
