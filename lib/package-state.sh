#!/bin/bash

# Hash relative recipe paths, their content, and installed ABI dependencies.
# Disposable worktree locations must not change the fingerprint.
package_fingerprint() {
  local recipe=$1
  python3 - "$recipe" <<'PY'
import hashlib
import json
import pathlib
import subprocess
import sys

root = pathlib.Path(sys.argv[1])
hash = hashlib.sha256()
for path in sorted(root.rglob('*')):
    relative = path.relative_to(root)
    if any(part in {'.git', 'src', 'pkg', 'build'} for part in relative.parts):
        continue
    if not path.is_file() or '.pkg.tar.' in path.name:
        continue
    hash.update(str(relative).encode() + b'\0' + path.read_bytes() + b'\0')
metadata = root / '.omarchy/package.json'
dependencies = json.loads(metadata.read_text()).get('rebuild_on', []) if metadata.exists() else []
for dependency in sorted(dependencies):
    version = subprocess.check_output(['pacman', '-Q', dependency])
    hash.update(version)
print(hash.hexdigest())
PY
}

# Record the installed version too: replacing a patched package must invalidate
# the cache even if its recipe and Qt dependencies did not change.
package_current() {
  local package=$1 fingerprint=$2 version recorded
  version=$(pacman -Q "$package" 2>/dev/null) || return 1
  recorded=$(cat "$package_state_dir/$package" 2>/dev/null) || return 1
  [[ $recorded == "$fingerprint $version" ]]
}

record_package() {
  local package=$1 fingerprint=$2 version temporary
  version=$(pacman -Q "$package") || return 1
  mkdir -p "$package_state_dir" || return 1
  temporary=$(mktemp "$package_state_dir/.${package}.XXXXXX") || return 1
  if ! printf '%s %s\n' "$fingerprint" "$version" > "$temporary" || ! mv "$temporary" "$package_state_dir/$package"; then
    rm -f "$temporary"
    return 1
  fi
}
