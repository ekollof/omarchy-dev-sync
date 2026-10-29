#!/bin/bash

require_github_auth() {
  if ! command -v gh >/dev/null; then
    terminal_error 'Error: GitHub CLI (gh) is not installed. Install it, then run: gh auth login --hostname github.com' >&2
    return 1
  fi
  # Check only the active account used by --author @me. An expired token on an
  # inactive account or a different host should not block this workflow.
  if ! gh auth status --active --hostname github.com >/dev/null 2>&1; then
    terminal_error 'Error: GitHub CLI could not authenticate the active github.com account.' >&2
    echo 'Run: gh auth login --hostname github.com' >&2
    echo 'If already logged in, inspect: gh auth status --active --hostname github.com' >&2
    echo 'Check token validity and network access; use gh auth switch to select another account.' >&2
    return 1
  fi
}
