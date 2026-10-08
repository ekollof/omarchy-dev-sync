#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT
mkdir -p "$temporary/bin" "$temporary/a/.omarchy" "$temporary/b"
cat > "$temporary/bin/pacman" <<'MOCK'
#!/bin/bash
if [[ $2 == "quickshell" ]]; then
  printf 'quickshell %s\n' "$(cat "$TEST_VERSION")"
else
  printf '%s %s\n' "$2" "$(cat "$TEST_QT")"
fi
MOCK
chmod +x "$temporary/bin/pacman"
export PATH="$temporary/bin:$PATH" TEST_VERSION="$temporary/version" TEST_QT="$temporary/qt"
echo 0.3.1-1.1 > "$TEST_VERSION"
echo 6.12.0-1 > "$TEST_QT"
echo 'pkgname=quickshell' > "$temporary/a/PKGBUILD"
echo '{"rebuild_on":["qt6-base"]}' > "$temporary/a/.omarchy/package.json"
cp -a "$temporary/a/." "$temporary/b/"
source "$root/lib/package-state.sh"
package_state_dir=$temporary/state
a=$(package_fingerprint "$temporary/a")
b=$(package_fingerprint "$temporary/b")
[[ $a == "$b" ]] || exit 1
echo 'ok - temporary worktree locations do not trigger rebuilds'
! package_current quickshell "$a"
record_package quickshell "$a"
package_current quickshell "$a"
echo 'ok - only a recorded installed build is current'
echo 0.3.1-1 > "$TEST_VERSION"
! package_current quickshell "$a"
echo 'ok - replacing the installed package invalidates its stamp'
echo 0.3.1-1.1 > "$TEST_VERSION"
echo 6.12.1-1 > "$TEST_QT"
[[ $a != "$(package_fingerprint "$temporary/a")" ]]
echo 'ok - Qt dependency updates invalidate the fingerprint'
echo 6.12.0-1 > "$TEST_QT"
echo 'upstream fix' > "$temporary/a/qt612.patch"
[[ $a != "$(package_fingerprint "$temporary/a")" ]]
echo 'ok - packaging-only patch changes invalidate the fingerprint'
