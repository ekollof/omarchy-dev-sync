#!/usr/bin/env python3
"""Exercise self-update against a local Git remote, without touching Omarchy."""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]

def run(*args, cwd=None, env=None):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout + result.stderr

with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    remote, publisher, clone = (temp / name for name in ('remote.git', 'publisher', 'clone'))
    run('git', 'init', '-q', '--bare', str(remote))
    run('git', 'init', '-q', '-b', 'master', str(publisher))
    run('git', 'config', 'user.name', 'Test', cwd=publisher)
    run('git', 'config', 'user.email', 'test@example.invalid', cwd=publisher)
    (publisher / 'lib').mkdir()
    (publisher / 'lib/self-update.sh').write_text((root / 'lib/self-update.sh').read_text())
    script = '''#!/bin/bash
set -euo pipefail
script_dir=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
source "$script_dir/lib/self-update.sh"
self_update_checkout "$script_dir" "$script_dir/omarchy-dev-sync" "$@"
refresh_local_dev_skills "$script_dir/skills/omarchy-dev"
unset OMARCHY_DEV_SYNC_SELF_UPDATED
printf 'old\\n'
printf '<%s>\\n' "$@"
'''
    (publisher / 'omarchy-dev-sync').write_text(script)
    bundled_skill = publisher / 'skills/omarchy-dev'
    bundled_skill.mkdir(parents=True)
    (bundled_skill / 'SKILL.md').write_text('old skill\n')
    run('git', 'add', '.', cwd=publisher)
    run('git', 'commit', '-qm', 'initial', cwd=publisher)
    initial = run('git', 'rev-parse', 'HEAD', cwd=publisher).strip()
    run('git', 'remote', 'add', 'origin', str(remote), cwd=publisher)
    run('git', 'push', '-qu', 'origin', 'master', cwd=publisher)
    run('git', 'clone', '-q', '-b', 'master', str(remote), str(clone))
    env = dict(os.environ)
    env['HOME'] = str(temp / 'home')
    env['XDG_CONFIG_HOME'] = str(temp / 'config-home')
    env['CODEX_HOME'] = str(temp / 'codex-home')
    installed_skill = temp / 'home/.agents/skills/omarchy-dev'
    installed_skill.mkdir(parents=True)
    (installed_skill / 'SKILL.md').write_text('old skill\n')
    env.pop('OMARCHY_DEV_SYNC_SELF_UPDATED', None)
    launcher = temp / 'launcher'
    launcher.symlink_to(clone / 'omarchy-dev-sync')
    command = ('bash', str(launcher), '--no-pkg', 'two words', '')
    assert 'old' in run(*command, env=env)
    (publisher / 'omarchy-dev-sync').write_text(script.replace("printf 'old", "printf 'new"))
    (bundled_skill / 'SKILL.md').write_text('new skill\n')
    run('git', 'add', '.', cwd=publisher)
    run('git', 'commit', '-qm', 'update', cwd=publisher)
    run('git', 'push', '-q', cwd=publisher)
    target = run('git', 'rev-parse', 'HEAD', cwd=publisher).strip()
    (clone / 'untracked').write_text('local work')
    assert 'local changes' in run(*command, env=env)
    assert run('git', 'rev-parse', 'HEAD', cwd=clone).strip() == initial
    (clone / 'untracked').unlink()
    output = run(*command, env=env)
    assert 'new\n<--no-pkg>\n<two words>\n<>\n' in output
    assert output.count('Checking omarchy-dev-sync') == 1
    assert run('git', 'rev-parse', 'HEAD', cwd=clone).strip() == target
    assert (installed_skill / 'SKILL.md').read_text() == 'new skill\n'
    backups = list(installed_skill.parent.glob('omarchy-dev.bak.*'))
    assert len(backups) == 1 and (backups[0] / 'SKILL.md').read_text() == 'old skill\n'
    print('ok - fast-forward reexec preserves arguments and avoids a fetch loop; dirty work preserved')
    run('git', 'config', 'user.name', 'Test', cwd=clone)
    run('git', 'config', 'user.email', 'test@example.invalid', cwd=clone)
    (clone / 'local').write_text('local commit')
    run('git', 'add', '.', cwd=clone)
    run('git', 'commit', '-qm', 'local', cwd=clone)
    local = run('git', 'rev-parse', 'HEAD', cwd=clone).strip()
    assert 'ahead or diverged' in run(*command, env=env)
    (publisher / 'remote').write_text('remote commit')
    run('git', 'add', '.', cwd=publisher)
    run('git', 'commit', '-qm', 'remote', cwd=publisher)
    run('git', 'push', '-q', cwd=publisher)
    assert 'ahead or diverged' in run(*command, env=env)
    assert run('git', 'rev-parse', 'HEAD', cwd=clone).strip() == local
    print('ok - ahead and divergent history preserved')
    run('git', 'remote', 'set-url', 'origin', str(temp / 'missing'), cwd=clone)
    assert 'fetch failed' in run(*command, env=env)
    run('git', 'switch', '-q', '--detach', cwd=clone)
    assert 'detached HEAD' in run(*command, env=env)
    run('git', 'switch', '-q', 'master', cwd=clone)
    run('git', 'branch', '--unset-upstream', cwd=clone)
    assert 'no remote tracking' in run(*command, env=env)
    print('ok - unavailable remote, detached HEAD and missing tracking branch continue safely')

    # The real CLI must not fetch on help/opt-out, even when copied outside Git.
    config = temp / 'config'
    config.mkdir()
    env.update(OMARCHY_DEV_SYNC_CONFIG=str(config), OMARCHY_DEV_SYNC_REPO=str(temp / 'absent'))
    actual = str(root / 'omarchy-dev-sync')
    result = subprocess.run(['bash', actual, '--no-self-update', '--no-pkg'], env=env, capture_output=True, text=True)
    assert result.returncode == 1 and 'not a git repo' in result.stderr
    assert 'Checking omarchy-dev-sync' not in result.stdout
    assert 'Checking omarchy-dev-sync' not in run('bash', actual, '--help', env=env)
    for setting in ('config', 'environment'):
        if setting == 'config':
            (config / 'config').write_text('self_update=0\n')
        else:
            (config / 'config').write_text('self_update=1\n')
            env['OMARCHY_DEV_SYNC_SELF_UPDATE'] = '0'
        result = subprocess.run(['bash', actual], env=env, capture_output=True, text=True)
        assert 'Checking omarchy-dev-sync' not in result.stdout
        assert 'not a git repo' in result.stderr
    print('ok - help and flag/config/environment opt-outs never fetch')
