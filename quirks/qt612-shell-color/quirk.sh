#!/bin/bash
set -euo pipefail
quirk_dir=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
phase=$1
repo=$2
base=$3
case "$phase" in
  retired-prs)
    if git -C "$repo" show "$base:shell/plugins/notifications/components/NotificationCard.qml" 2>/dev/null | rg -q '^import qs\.Commons as Commons$'; then
      echo 14511
    fi
    ;;
  select-prs)
    qt_version=$(pacman -Q qt6-declarative 2>/dev/null | awk '{print $2}') || qt_version=
    if [[ $qt_version =~ ^([0-9]+)\.([0-9]+) ]] && (( BASH_REMATCH[1] > 6 || (BASH_REMATCH[1] == 6 && BASH_REMATCH[2] >= 12) )); then
      if git -C "$repo" cat-file -e "$base:shell/Commons/Color.qml" 2>/dev/null && ! git -C "$repo" cat-file -e "$base:shell/Commons/ShellColor.qml" 2>/dev/null && ! git -C "$repo" show "$base:shell/plugins/notifications/components/NotificationCard.qml" 2>/dev/null | rg -q '^import qs\.Commons as Commons$'; then
        echo "Including Qt 6.12 palette compatibility PR #14511 (quirk qt612-shell-color)." >&2
        echo 14511
      fi
    fi
    ;;
  resolve-source)
    python3 "$quirk_dir/compat.py" resolve "$repo"
    ;;
  before-restart)
    python3 "$quirk_dir/compat.py" migrate "$repo"
    ;;
  *) exit 2 ;;
esac
