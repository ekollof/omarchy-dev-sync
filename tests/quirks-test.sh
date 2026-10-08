#!/bin/bash
set -euo pipefail
project_dir=$(dirname "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")")
source "$project_dir/lib/quirks.sh"
task_temp=$(mktemp -d)
trap 'rm -rf "$task_temp"' EXIT
script_dir=$task_temp/fixture
upstream=origin
head=master
disabled_quirks=""
mkdir -p "$script_dir/quirks/example"
cat > "$script_dir/quirks/example/quirk.sh" <<'QUIRK'
case "$1" in
  select-prs) echo 123 ;;
  resolve-source) exit 2 ;;
  before-restart) exit 7 ;;
  *) exit 2 ;;
esac
QUIRK
[[ $(run_quirks select-prs "$task_temp") == 123 ]]
if run_quirks resolve-source "$task_temp"; then exit 1; else [[ $? == 2 ]]; fi
if run_quirks before-restart "$task_temp" 2>/dev/null; then exit 1; else [[ $? == 7 ]]; fi
disabled_quirks=example
[[ -z $(run_quirks select-prs "$task_temp") ]]
run_quirks before-restart "$task_temp"
disabled_quirks=""
rm -r "$script_dir/quirks/example"
[[ -z $(run_quirks select-prs "$task_temp") ]]
echo 'ok - discovered hooks, inactive/conflict statuses, failures, disabling and retirement'

repo=$task_temp/repo
mkdir -p "$repo/shell/Commons" "$task_temp/bin"
git -C "$repo" init -q -b master
git -C "$repo" config user.name Test
git -C "$repo" config user.email test@example.invalid
echo palette > "$repo/shell/Commons/Color.qml"
git -C "$repo" add .
git -C "$repo" commit -qm base
cat > "$task_temp/bin/pacman" <<'PACMAN'
#!/bin/bash
echo "qt6-declarative ${TEST_QT_VERSION:-6.12.0-1}"
PACMAN
chmod +x "$task_temp/bin/pacman"
export PATH="$task_temp/bin:$PATH"
script_dir=$project_dir
head=HEAD
upstream=""
# Call the hook with the local ref directly for this isolated fixture.
hook=$project_dir/quirks/qt612-shell-color/quirk.sh
[[ $(bash "$hook" select-prs "$repo" HEAD) == 14511 ]]
[[ -z $(TEST_QT_VERSION=6.11.2 bash "$hook" select-prs "$repo" HEAD) ]]
git -C "$repo" mv shell/Commons/Color.qml shell/Commons/ShellColor.qml
git -C "$repo" commit -qm upstream-fixed
[[ -z $(bash "$hook" select-prs "$repo" HEAD) ]]
echo 'ok - Qt quirk selects fix only when needed and retires PR selection once upstream is fixed'
