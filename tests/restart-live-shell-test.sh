#!/bin/bash
set -euo pipefail
project_dir=$(dirname "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")")
source "$project_dir/lib/terminal.sh"
source "$project_dir/lib/restart.sh"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
tools=$stage/bin
repo=$stage/repo
calls=$stage/calls
mkdir -p "$tools" "$repo"
: >"$calls"
cat >"$tools/systemctl" <<'MOCK'
#!/bin/bash
[[ $1 == --user && $2 == show-environment ]] || exit 99
printf 'OMARCHY_PATH=%s\n' "${TEST_SESSION_PATH:?}"
MOCK
cat >"$tools/omarchy-restart-shell" <<'MOCK'
#!/bin/bash
printf 'call\n' >>"$TEST_RESTART_CALLS"
[[ -z ${TEST_RESTART_OUTPUT:-} ]] || printf '%s\n' "$TEST_RESTART_OUTPUT"
exit "${TEST_RESTART_STATUS:-0}"
MOCK
chmod +x "$tools/systemctl" "$tools/omarchy-restart-shell"
export PATH="$tools:$PATH" TEST_SESSION_PATH="$repo" TEST_RESTART_CALLS="$calls"
terminal_init
restart=1
integration=integration-prs

out=$(restart_live_shell)
[[ $out == *"Restarted the live Omarchy shell so it runs this integration-prs build."* ]]
[[ $(wc -l <"$calls" | tr -d ' ') == 1 ]]
echo 'ok - successful shell restart is reported'

out=$(TEST_RESTART_STATUS=1 TEST_RESTART_OUTPUT='Refusing to restart Omarchy shell while the session is locked.' restart_live_shell 2>&1)
[[ $out == *"Refusing to restart Omarchy shell while the session is locked."* ]]
[[ $out == *"Run 'omarchy restart shell' after unlocking"* ]]
[[ $out != *"Error:"* ]]
[[ $(wc -l <"$calls" | tr -d ' ') == 2 ]]
echo 'ok - a locked session defers the restart without failing the sync'

if out=$(TEST_RESTART_STATUS=1 TEST_RESTART_OUTPUT='Omarchy shell did not become ready after restart.' restart_live_shell 2>&1); then
  echo 'expected an unrelated restart failure to fail' >&2
  exit 1
fi
[[ $out == *"Error: integration-prs rebuilt, but the live shell was not restarted."* ]]
[[ $(wc -l <"$calls" | tr -d ' ') == 3 ]]
echo 'ok - unrelated restart failures still stop the sync'

out=$(TEST_SESSION_PATH="$stage/other" restart_live_shell)
[[ -z $out ]]
[[ $(wc -l <"$calls" | tr -d ' ') == 3 ]]
echo 'ok - a session running another checkout is left alone'

restart=0
out=$(restart_live_shell)
[[ -z $out ]]
[[ $(wc -l <"$calls" | tr -d ' ') == 3 ]]
echo 'ok - --no-restart skips the shell restart'
