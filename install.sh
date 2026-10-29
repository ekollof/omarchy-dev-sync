#!/bin/bash
# Install the sync launcher and prepare the configured Omarchy dev link.
set -euo pipefail

script_dir=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
if [[ ${1:-} == --help || ${1:-} == -h ]]; then
  echo 'Usage: ./install.sh'
  echo 'Install the launcher and skills; ask before enabling an Omarchy dev link.'
  exit 0
fi
(( $# == 0 )) || { echo 'Error: unexpected arguments (use --help).' >&2; exit 1; }
(( EUID != 0 )) || { echo 'Error: run as your normal user, without sudo.' >&2; exit 1; }
config_dir=${OMARCHY_DEV_SYNC_CONFIG:-$HOME/.config/omarchy-dev-sync}
repo=$HOME/src/omarchy
[[ ! -f $config_dir/config ]] || source "$config_dir/config"
repo=${OMARCHY_DEV_SYNC_REPO:-$repo}
repo=$(realpath -e "$repo") || { echo 'Error: create your Omarchy checkout and configure repo first.' >&2; exit 1; }
git -C "$repo" rev-parse --is-inside-work-tree >/dev/null
for directory in bin default shell; do
  [[ -d $repo/$directory ]] || { echo "Error: missing Omarchy directory: $repo/$directory" >&2; exit 1; }
done

# Parse the persistent setting as data; never execute system configuration.
persistent=$(python3 - <<'PY'
from pathlib import Path
import re
import shlex
p = Path('/etc/omarchy.conf')
linked = ''
if p.exists():
    for line in p.read_text().splitlines():
        match = re.fullmatch(r'\s*(?:export\s+)?OMARCHY_PATH=(.*)', line)
        if match:
            parts = shlex.split(match[1], comments=True)
            if len(parts) != 1 or not parts[0].startswith('/'):
                raise SystemExit('Error: cannot parse /etc/omarchy.conf')
            linked = str(Path(parts[0]).resolve())
print(linked)
PY
)
session=$(systemctl --user show-environment 2>/dev/null | sed -n 's/^OMARCHY_PATH=//p' | tail -n 1) || session=''
session=${session:-${OMARCHY_PATH:-}}
[[ -z $session ]] || session=$(realpath -m "$session")

if [[ $persistent != "$repo" ]]; then
  cat <<WARNING
Omarchy is not dev-linked to $repo.

WARNING: Development branches and your integrated PRs can contain unstable or
untested changes that break the desktop, updates, or boot. Dev linking trusts
this user-writable checkout for system commands, including commands run as root.
Sync also runs system updates and migrations and may switch package sources to
edge. Keep backups and a recovery method; returning to stable can require manual
repair. 'omarchy dev unlink' restores the packaged path after a reboot but does
not undo package upgrades or migrations.

Setup will run: omarchy dev link "$repo" --no-reboot
This changes /etc/omarchy.conf and may change sudo command resolution immediately.
WARNING
  answer=''
  if ! read -r -p 'Enable this development setup? [y/N] ' answer || [[ ! $answer =~ ^([yY]|[yY][eE][sS])$ ]]; then
    echo 'Setup declined; nothing installed.'
    exit 1
  fi
  omarchy dev link "$repo" --no-reboot
  persistent=$repo
fi

install_dir=$HOME/.local/bin
mkdir -p "$install_dir"
launcher=$install_dir/omarchy-dev-sync
if [[ -e $launcher && ! -L $launcher ]]; then
  echo "Error: refusing to replace existing file: $launcher" >&2
  exit 1
fi
ln -sfn "$script_dir/omarchy-dev-sync" "$launcher"
source "$script_dir/lib/self-update.sh"
refresh_local_dev_skills "$script_dir/skills/omarchy-dev"
echo "Installed $launcher"
if [[ $session != "$repo" ]]; then
  echo "Dev link configured for $repo but not active in this session."
  echo 'Reboot to activate it before running omarchy-dev-sync. No reboot was started.'
else
  echo "Dev link is configured and active for $repo."
fi
