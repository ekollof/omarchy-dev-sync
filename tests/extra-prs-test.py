#!/usr/bin/env python3
"""Check persistent selection retirement without contacting GitHub."""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    gh = temp / 'gh'
    gh.write_text('''#!/bin/bash
case $2 in
  repos/test/repo/pulls/1) echo open ;;
  repos/test/repo/pulls/2) echo closed ;;
  repos/test/repo/pulls/3) echo 'Not Found (HTTP 404)' >&2; exit 1 ;;
  repos/test/repo/pulls/4) echo 'API rate limit exceeded (HTTP 403)' >&2; exit 1 ;;
  repos/test/repo) [[ ${DENY_REPO:-0} == 0 ]] ;;
  *) exit 99 ;;
esac
''')
    gh.chmod(0o755)
    selection = temp / 'extra-prs'
    original = '# selections\n1 # open\n2 # closed or merged\n3\n\n'
    env = dict(os.environ, PATH=f'{temp}:{os.environ["PATH"]}')
    command = ['bash', '-c', 'set -euo pipefail; source "$1"; cleanup_extra_prs "$2" test/repo',
               'test', str(root / 'lib/extra-prs.sh'), str(selection)]
    selection.write_text(original)
    selection.chmod(0o600)
    subprocess.run(command, env=env, check=True)
    assert selection.read_text() == '# selections\n1 # open\n\n'
    assert selection.stat().st_mode & 0o777 == 0o600
    for content, overrides in [(original + '4\n', {}), (original, {'DENY_REPO': '1'}),
                               (original + 'bad\n', {})]:
        selection.write_text(content)
        result = subprocess.run(command, env=dict(env, **overrides), capture_output=True)
        assert result.returncode != 0
        assert selection.read_text() == content
    selection.unlink()
    subprocess.run(command, env=env, check=True)
    print('ok - open retained, closed/deleted removed, comments/mode preserved, errors fail closed')
