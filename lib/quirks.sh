#!/bin/bash

# Quirks are independently removable directories with a phase dispatcher.
# Exit 2 means not applicable; other failures stop the operation.
run_quirks() {
  local phase=$1 checkout=$2 file id status handled=0
  for file in "$script_dir"/quirks/*/quirk.sh; do
    [[ -f $file ]] || continue
    id=${file%/quirk.sh}
    id=${id##*/}
    [[ " ${disabled_quirks:-} " != *" $id "* ]] || continue
    if bash "$file" "$phase" "$checkout" "$upstream/$head"; then
      handled=1
      if [[ $phase == resolve-* ]]; then
        echo "Resolved $phase conflict with quirk: $id" >&2
        return 0
      fi
    else
      status=$?
      if (( status != 2 )); then
        echo "Error: quirk $id failed during $phase." >&2
        return "$status"
      fi
    fi
  done
  if [[ $phase == resolve-* && $handled == 0 ]]; then
    return 2
  fi
  return 0
}
