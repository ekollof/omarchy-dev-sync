#!/usr/bin/env python3
"""Repository setup consent, cloning, idempotence and remote preservation."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    tools = base / 'tools'
    tools.mkdir()
    log = base / 'calls'
    mock = tools / 'gh'
    mock.write_text('''#!/bin/bash
printf '%s\\n' "$*" >> "$CALLS"
case "$1 $2" in
  'api user') echo developer ;;
  'repo list')
    if [[ ${EXISTING_FORK:-0} == 1 ]]; then
      printf '%s' '[{"url":"https://github.com/developer/renamed-fork","parent":{"owner":{"login":"omacom"},"name":"omarchy"}}]'
    else
      echo '[]'
    fi | jq -r "${@: -1}"
    ;;
  'repo fork') exit 0 ;;
  'repo view')
    parent=omacom
    [[ ${BAD_FORK:-0} != 1 ]] || parent=unrelated
    printf '{"url":"https://github.com/%s","parent":{"owner":{"login":"%s"},"name":"omarchy"}}' "$3" "$parent" | jq -r "${@: -1}"
    ;;
  'repo clone')
    git init -q "$4"
    git -C "$4" remote add "${@: -3:1}" "https://github.com/$3.git"
    ;;
  *) exit 99 ;;
esac
''')
    mock.chmod(0o755)
    env = dict(os.environ, PATH=f'{tools}:/usr/bin:/bin', CALLS=str(log))
    prelude = f'source {root}/lib/terminal.sh; source {root}/lib/install-repositories.sh; '
    def run(repo, answer='', **extra):
        command = prelude + f'setup_development_repository {shlex.quote(str(repo))} omacom/omarchy upstream mine quattro'
        return subprocess.run(['bash', '-euc', command], env=dict(env, **extra), input=answer, text=True, capture_output=True)
    repo = base / 'checkout'
    assert run(repo, 'n\n').returncode == 1
    assert not repo.exists() and 'repo fork' not in log.read_text()
    assert run(repo).returncode == 1 and 'repo fork' not in log.read_text()
    result = run(repo, 'yes\n')
    assert result.returncode == 0, result
    def remote(name):
        return subprocess.check_output(['git', '-C', str(repo), 'remote', 'get-url', name], text=True).strip()
    assert remote('mine') == 'https://github.com/developer/omarchy.git'
    assert remote('upstream') == 'https://github.com/omacom/omarchy.git'
    calls = log.read_text()
    assert '--clone=false --remote=false' in calls and '--branch quattro' in calls
    assert run(repo).returncode == 0 and log.read_text() == calls
    subprocess.run(['git', '-C', str(repo), 'remote', 'remove', 'upstream'], check=True)
    result = run(repo)
    assert result.returncode == 0 and remote('mine') == 'https://github.com/developer/omarchy.git'
    assert log.read_text() == calls  # no GitHub mutation for an upstream-only repair
    subprocess.run(['git', '-C', str(repo), 'remote', 'remove', 'mine'], check=True)
    calls = log.read_text()
    result = run(repo, EXISTING_FORK='1')
    assert result.returncode == 0, result
    assert remote('mine') == 'https://github.com/developer/renamed-fork.git'
    assert 'repo fork' not in log.read_text()[len(calls):]
    bad = base / 'bad'
    result = run(bad, 'y\n', BAD_FORK='1')
    assert result.returncode == 1 and not bad.exists()
    occupied = base / 'occupied'
    occupied.mkdir()
    (occupied / 'keep').write_text('local work')
    result = run(occupied, 'y\n')
    assert result.returncode != 0 and (occupied / 'keep').read_text() == 'local work'
print('ok - consent, fork verification, clone, missing remotes, idempotence and existing files')
