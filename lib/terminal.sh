#!/bin/bash
# Match Omarchy's terminal headings and severity colors without coloring pipes.
terminal_init() {
  terminal_color=0
  if [[ -t 1 && ${TERM:-dumb} != dumb && ! ${NO_COLOR+x} ]]; then
    terminal_color=1
  fi
}

terminal_message() {
  local color=$1
  shift
  if [[ ${terminal_color:-0} == 1 ]]; then
    printf '\033[%sm%s\033[0m\n' "$color" "$*"
  else
    printf '%s\n' "$*"
  fi
}

terminal_heading() { printf '\n'; terminal_message 32 "$@"; }
terminal_warning() { terminal_message 33 "$@"; }
terminal_error() { terminal_message 31 "$@"; }
terminal_success() { terminal_message 32 "$@"; }

terminal_notice() {
  if [[ ${terminal_color:-0} == 1 ]] && command -v gum >/dev/null; then
    gum style --border normal --padding '1 2' "$@"
  else
    printf '%s\n' "$@"
  fi
}

terminal_confirm() {
  local answer=''
  if [[ -t 0 && -t 1 ]] && command -v gum >/dev/null; then
    gum confirm --default=false --affirmative Yes --negative No "$1"
  else
    read -r -p "$1 [y/N] " answer && [[ $answer =~ ^([yY]|[yY][eE][sS])$ ]]
  fi
}
