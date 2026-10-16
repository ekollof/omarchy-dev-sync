#!/bin/bash

# Validate every selection before rewriting anything. A PR 404 only means
# gone when the same credentials can still read the repository.
cleanup_extra_prs() {
  local file=$1 slug=$2 number result temporary
  local -a retired=()
  [[ -f $file ]] || return 0
  while IFS= read -r number; do
    [[ $number =~ ^[1-9][0-9]*$ ]] || {
      echo "Error: invalid upstream PR number in extra-prs: $number" >&2
      return 1
    }
    if result=$(gh api "repos/$slug/pulls/$number" --jq '.state' 2>&1); then
      case $result in
        open) ;;
        closed) retired+=("$number") ;;
        *) echo "Error: unexpected PR status for #$number; preserving extra-prs." >&2; return 1 ;;
      esac
    elif [[ $result == *'(HTTP 404)'* ]] && gh api "repos/$slug" --silent >/dev/null 2>&1; then
      retired+=("$number")
    else
      echo "Error: cannot verify selected PR #$number; preserving extra-prs: $result" >&2
      return 1
    fi
  done < <(sed -E 's/#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//; /^$/d' "$file")
  (( ${#retired[@]} > 0 )) || return 0
  # Keep comments and unrelated entries; stage beside the file for atomic rename.
  temporary=$(mktemp "${file}.XXXXXX") || return 1
  if ! cp -p -- "$file" "$temporary" || ! awk -v retired=" ${retired[*]} " '
    { number=$0; sub(/#.*/, "", number); gsub(/^[[:space:]]+|[[:space:]]+$/, "", number) }
    number != "" && index(retired, " " number " ") { next }
    { print }
  ' "$file" >"$temporary" || ! mv -- "$temporary" "$file"; then
    rm -f -- "$temporary"
    return 1
  fi
  echo "Removed closed or unavailable PRs from extra-prs: ${retired[*]}"
}
