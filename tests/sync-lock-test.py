#!/usr/bin/env python3
"""Real flock contention, re-exec inheritance and explicit unlock."""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    env = dict(os.environ, HOME=tmp, XDG_RUNTIME_DIR=tmp)
    prelude = f'source "{root}/lib/terminal.sh"; source "{root}/lib/sync-lock.sh"; '
    holder = subprocess.Popen(['bash', '-euc', prelude + 'acquire_sync_lock; echo ready; read -r; release_sync_lock; echo released; read -r'], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == 'ready'
        blocked = subprocess.run(['bash', '-euc', prelude + 'acquire_sync_lock'], env=env, capture_output=True, text=True)
        assert blocked.returncode == 75 and 'already running' in blocked.stderr
        holder.stdin.write('release\n'); holder.stdin.flush()
        assert holder.stdout.readline().strip() == 'released'
        subprocess.run(['bash', '-euc', prelude + 'acquire_sync_lock; release_sync_lock'], env=env, check=True)
    finally:
        holder.communicate('exit\n')
    child = prelude + 'acquire_sync_lock; echo reexec-ok; release_sync_lock'
    import shlex
    result = subprocess.run(['bash', '-euc', prelude + 'acquire_sync_lock; export OMARCHY_DEV_SYNC_SELF_UPDATED=1; exec bash -euc ' + shlex.quote(child)], env=env, capture_output=True, text=True)
    assert result.returncode == 0 and 'reexec-ok' in result.stdout, result
print('ok - contention, release and self-update re-exec')
