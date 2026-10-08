#!/bin/bash
set -euo pipefail
quirk_dir=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
case "$1" in
  resolve-packages) python3 "$quirk_dir/resolve.py" "$2" ;;
  *) exit 2 ;;
esac
