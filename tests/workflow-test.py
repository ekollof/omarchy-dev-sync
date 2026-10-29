#!/usr/bin/env python3
"""Check exit handling, recursion prevention and integrated updater selection."""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    tools = base / 'bin'
    tools.mkdir()
    marker = base / 'agent'
    agent = tools / 'omarchy-agent'
    agent.write_text('#!/bin/bash\nprintf "%s\\n" "$OMARCHY_DEV_SYNC_TROUBLESHOOTING" "$PWD" "$@" > "$MARKER"\n')
    agent.chmod(0o755)
    env = dict(os.environ, HOME=tmp, XDG_STATE_HOME=tmp, PATH=f'{tools}:/usr/bin:/bin', MARKER=str(marker))
    prelude = f'''source '{root}/lib/terminal.sh'
terminal_init
source '{root}/lib/workflow.sh'
script_dir='{root}'
repo='{base}'
integration=integration-prs
agent_on_failure=1
start_workflow
'''
    for status, recursive, expected in [(7, '0', True), (7, '1', False), (130, '0', False), (0, '0', False)]:
        marker.unlink(missing_ok=True)
        result = subprocess.run(['bash', '-euc', prelude + f'echo diagnostic; exit {status}'], env=dict(env, OMARCHY_DEV_SYNC_TROUBLESHOOTING=recursive), capture_output=True, text=True)
        assert result.returncode == status, result
        assert marker.exists() == expected
        if expected:
            prompt = marker.read_text()
            assert 'sync failure (exit 7)' in prompt and 'never edit' in prompt
            assert prompt.startswith(f'1\n{root}\n--prompt\n')
    updater = tools / 'omarchy-update'
    updater.write_text('#!/bin/bash\nprintf "%s\\n" "$OMARCHY_PATH" "$1"\nexit 9\n')
    updater.chmod(0o755)
    result = subprocess.run(['bash', '-euc', prelude + 'system_update=1; update_integrated_system'], env=env, capture_output=True, text=True)
    assert result.returncode == 9
    assert f'{base}\n-y' in result.stdout
    assert 'system update failure' in marker.read_text()
print('ok - failure context, status, interrupts, recursion guard and updater')
