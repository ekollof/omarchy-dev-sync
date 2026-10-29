#!/bin/bash

# Commands and sourced setup helpers must match the checkout before migrations
# run. Checking only commands with privileged_copy_matches misses new helpers.
packaged_skew() {
  PACKAGED_SKEW=()
  local installed_root=${1:-/} source_file installed_file relative
  for source_file in "$repo"/bin/omarchy-* "$repo"/install/helpers/*; do
    [[ -f $source_file ]] || continue
    # The installer registers this external tool locally, not as a dev package.
    if [[ $source_file == "$repo/bin/omarchy-dev-sync" && -L $source_file &&
          $(readlink -f "$source_file") == "${script_dir:-}/omarchy-dev-sync" ]]; then
      continue
    fi
    relative=${source_file#"$repo"/}
    if [[ $relative == bin/* ]]; then
      installed_file="$installed_root/usr/bin/${source_file##*/}"
    else
      installed_file="$installed_root/usr/share/omarchy/$relative"
    fi
    if [[ ! -f $installed_file ]] || ! cmp -s "$source_file" "$installed_file"; then
      PACKAGED_SKEW+=("$relative")
    fi
  done
  return 0
}
