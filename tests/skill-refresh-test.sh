#!/bin/bash
set -euo pipefail
script_dir=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
source "$script_dir/../lib/self-update.sh"
task_temp=$(mktemp -d)
trap 'rm -rf "$task_temp"' EXIT
skill_home=$task_temp/home
skill_config=$task_temp/config
skill_codex=$task_temp/codex
refresh_test_skills() {
  refresh_local_dev_skills "$source_skill" "$skill_home" "$skill_config" "$skill_codex"
}
source_skill=$task_temp/source
mkdir -p "$source_skill/support" "$skill_home/.agents/skills/omarchy-dev" "$skill_home/.claude/skills" "$skill_config/opencode/skills/omarchy-dev" "$skill_codex/skills"
echo new > "$source_skill/SKILL.md"
echo resource > "$source_skill/support/guide.md"
echo old > "$skill_home/.agents/skills/omarchy-dev/SKILL.md"
echo custom > "$skill_home/.agents/skills/omarchy-dev/local.md"
cp -a "$source_skill/." "$skill_config/opencode/skills/omarchy-dev/"
ln -s "$source_skill" "$skill_home/.claude/skills/omarchy-dev"
refresh_test_skills
diff -qr "$source_skill" "$skill_home/.agents/skills/omarchy-dev"
backups=("$skill_home"/.agents/skills/omarchy-dev.bak.*)
[[ ${#backups[@]} == 1 && $(cat "${backups[0]}/SKILL.md") == old ]]
[[ $(cat "${backups[0]}/local.md") == custom ]]
[[ -L $skill_home/.claude/skills/omarchy-dev && -L $skill_codex/skills/omarchy-dev ]]
[[ $(readlink -f "$skill_codex/skills/omarchy-dev") == "$source_skill" ]]
[[ -z $(refresh_test_skills) ]]
echo 'ok - changed copies backed up; missing installs linked to bundled skill; unchanged copies and links skipped'
mkdir -p "$task_temp/other"
echo unrelated > "$task_temp/other/SKILL.md"
rm "$skill_codex/skills/omarchy-dev"
ln -s "$task_temp/other" "$skill_codex/skills/omarchy-dev"
refresh_test_skills 2> "$task_temp/warnings"
[[ -L $skill_codex/skills/omarchy-dev && $(cat "$skill_codex/skills/omarchy-dev/SKILL.md") == unrelated ]]
[[ $(cat "$task_temp/warnings") == *'unrelated skill symlink'* ]]
echo 'ok - unrelated skill links preserved'
rm "$skill_codex/skills/omarchy-dev"
rm -r "$skill_home/.agents" "$skill_home/.claude" "$skill_config" "$skill_codex"
refresh_test_skills
for destination in "$skill_home/.agents/skills/omarchy-dev" "$skill_home/.claude/skills/omarchy-dev" "$skill_config/opencode/skills/omarchy-dev" "$skill_codex/skills/omarchy-dev"; do
  [[ -L $destination && -f $destination/SKILL.md && -f $destination/support/guide.md ]]
done
[[ -z $(refresh_test_skills) ]]
echo 'ok - fresh home installs all four agent paths and resources; repeat is a no-op'
