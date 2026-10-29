#!/bin/bash

# Ask before creating forks/checkouts or filling missing remotes. Existing
# remotes and working trees are never rewritten, reset, or switched.
setup_development_repository() {
  local checkout=$1 slug=$2 upstream_remote=$3 fork_remote=$4 branch=${5:-}
  local missing_checkout=0 missing_upstream=0 missing_fork=0 account fork_url
  if [[ $upstream_remote == "$fork_remote" ]]; then
    terminal_error 'Error: upstream and fork remote names must differ.' >&2
    return 1
  fi
  if [[ ! -e $checkout ]]; then
    missing_checkout=1
    missing_upstream=1
    missing_fork=1
  elif [[ $(git -C "$checkout" rev-parse --show-toplevel 2>/dev/null) != "$(realpath -e "$checkout")" ]]; then
    terminal_error "Error: refusing to use a non-checkout path: $checkout" >&2
    return 1
  else
    git -C "$checkout" remote get-url "$upstream_remote" >/dev/null 2>&1 || missing_upstream=1
    git -C "$checkout" remote get-url "$fork_remote" >/dev/null 2>&1 || missing_fork=1
  fi
  if (( missing_checkout == 0 && missing_upstream == 0 && missing_fork == 0 )); then
    return 0
  fi
  # Read-only discovery distinguishes an existing GitHub fork from one we
  # would need to create. Reuse renamed forks by checking their parent.
  if (( missing_fork )); then
    account=$(gh api user --jq .login) || return 1
    [[ -n $account && $account != *[!a-zA-Z0-9-]* ]] || return 1
    fork_url=$(gh repo list "$account" --fork --limit 1000 --json url,parent \
      --jq ".[] | select(.parent.nameWithOwner == \"$slug\") | .url" ) || return 1
    if [[ $fork_url == *$'\n'* ]]; then
      terminal_error "Error: multiple forks of $slug found; configure the fork remote explicitly." >&2
      return 1
    fi
  fi
  # Existing local setup plus an existing fork needs no setup confirmation.
  if (( missing_checkout == 0 )) && { (( missing_fork == 0 )) || [[ -n $fork_url ]]; }; then
    if (( missing_upstream )); then
      git -C "$checkout" remote add "$upstream_remote" "https://github.com/$slug.git" || return 1
    fi
    if (( missing_fork )); then
      git -C "$checkout" remote add "$fork_remote" "$fork_url.git" || return 1
    fi
    terminal_success "Reused existing development repositories for $slug"
    return 0
  fi
  terminal_notice "Set up $slug for development" \
    "Checkout: $checkout" \
    "Upstream remote: $upstream_remote (https://github.com/$slug.git)" \
    "Fork remote: $fork_remote (your active GitHub account)" \
    'Missing checkouts/remotes will be created. A missing fork remote requires creating or reusing your GitHub fork.' \
    'Existing remotes and working files will be preserved. GitHub forks are public.'
  if ! terminal_confirm "Set up missing development repositories/remotes for $slug?"; then
    echo 'Repository setup declined; installation stopped.'
    return 1
  fi
  if (( missing_fork )); then
    if [[ -z $fork_url ]]; then
      gh repo fork "$slug" --clone=false --remote=false || return 1
    fi
    # Reject an unrelated repository occupying the expected fork name.
    fork_url=$(gh repo view "$account/${slug##*/}" --json url,parent \
      --jq "select(.parent.nameWithOwner == \"$slug\") | .url") || return 1
    if [[ $fork_url != "https://github.com/$account/"* ]]; then
      terminal_error "Error: cannot verify your fork of $slug." >&2
      return 1
    fi
  fi
  if (( missing_checkout )); then
    mkdir -p "${checkout%/*}" || return 1
    local -a clone_args=(--origin "$upstream_remote")
    [[ -z $branch ]] || clone_args+=(--branch "$branch")
    gh repo clone "$slug" "$checkout" -- "${clone_args[@]}" || return 1
  elif (( missing_upstream )); then
    git -C "$checkout" remote add "$upstream_remote" "https://github.com/$slug.git" || return 1
  fi
  if (( missing_fork )); then
    git -C "$checkout" remote add "$fork_remote" "$fork_url.git" || return 1
  fi
}
