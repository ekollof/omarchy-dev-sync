#!/bin/bash

ensure_dev_package_sources() {
  local status
  if python3 "$script_dir/lib/dev-package-sources.py" --check "$repo"; then
    return 0
  else
    status=$?
  fi
  (( status == 2 )) || return "$status"
  echo "Aligning package sources with the active Omarchy dev link..."
  if [[ -t 0 ]]; then
    sudo /usr/bin/python3 -I "$script_dir/lib/dev-package-sources.py" "$repo" || return 1
  else
    pkexec /usr/bin/python3 -I "$script_dir/lib/dev-package-sources.py" "$repo" || return 1
  fi
  echo "Package databases were not refreshed. Run omarchy update for the full system upgrade."
}
