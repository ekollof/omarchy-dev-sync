#!/usr/bin/env python3
"""Exercise installer consent and session detection without changing the desktop."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    home = base / 'home'
    home.mkdir()
    repo = base / 'omarchy'
    for name in ('bin', 'default', 'shell'):
        (repo / name).mkdir(parents=True)
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    for remote in ('origin', 'fork'):
        subprocess.run(['git', '-C', str(repo), 'remote', 'add', remote, 'https://example.invalid/omarchy'], check=True)
    pkgs = base / 'pkgs'
    subprocess.run(['git', 'init', '-q', str(pkgs)], check=True)
    for remote in ('origin', 'fork'):
        subprocess.run(['git', '-C', str(pkgs), 'remote', 'add', remote, 'https://example.invalid/pkgs'], check=True)
    project = base / 'tool'
    project.mkdir()
    shutil.copytree(root / 'lib', project / 'lib')
    shutil.copytree(root / 'skills', project / 'skills')
    shutil.copy2(root / 'omarchy-dev-sync', project / 'omarchy-dev-sync')
    conf = base / 'omarchy.conf'
    script = project / 'install.sh'
    script.write_text((root / 'install.sh').read_text().replace('/etc/omarchy.conf', str(conf)))
    tools = base / 'tools'
    tools.mkdir()
    calls = base / 'calls'
    for name, body in {
        'gh': '[[ $* == "auth status --active --hostname github.com" ]]',
        'systemctl': 'printf "OMARCHY_PATH=%s\\n" "$SESSION"',
        'omarchy': 'printf "%s\\n" "$@" > "$CALLS"',
    }.items():
        path = tools / name
        path.write_text('#!/bin/bash\n' + body + '\n')
        path.chmod(0o755)
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / '.config'), CODEX_HOME=str(home / '.codex'), OMARCHY_DEV_SYNC_REPO=str(repo), OMARCHY_DEV_SYNC_PKGS_REPO=str(pkgs), OMARCHY_DEV_SYNC_CONFIG=str(home / 'config'), PATH=f'{tools}:/usr/bin:/bin', SESSION='/usr/share/omarchy', CALLS=str(calls))
    def run(answer):
        return subprocess.run(['bash', str(script)], input=answer, env=env, capture_output=True, text=True)
    for answer in ('n\n', ''):
        result = run(answer)
        assert result.returncode == 1, result
        assert 'WARNING' in result.stdout and not calls.exists()
        assert not (home / '.local/bin/omarchy-dev-sync').exists()
        assert not (home / 'config').exists()
    result = run('yes\n')
    assert result.returncode == 0, result
    assert calls.read_text().splitlines() == ['dev', 'link', str(repo), '--no-reboot']
    assert 'not active' in result.stdout
    generated_config = home / 'config/config'
    config_text = generated_config.read_text()
    assert f'repo={repo}' in config_text and f'pkgs_repo={pkgs}' in config_text
    assert 'self_update=1' in config_text and 'system_update=1' in config_text
    assert generated_config.stat().st_mode & 0o777 == 0o600
    assert (home / 'config/extra-branches').is_file()
    assert (home / 'config/extra-prs').is_file()
    generated_config.write_text(config_text + '# Keep my settings\n')
    (home / 'config/extra-prs').write_text('# Keep my selections\n123\n')
    calls.unlink()
    conf.write_text(f'export OMARCHY_PATH="{repo}"\n')
    result = run('')
    assert result.returncode == 0 and 'not active' in result.stdout
    assert not calls.exists()
    env['SESSION'] = str(repo)
    result = run('')
    assert result.returncode == 0 and 'configured and active' in result.stdout
    assert generated_config.read_text() == config_text + '# Keep my settings\n'
    assert (home / 'config/extra-prs').read_text() == '# Keep my selections\n123\n'
    assert not calls.exists()
    assert (repo / 'bin/omarchy-dev-sync').resolve() == project / 'omarchy-dev-sync'
    ignored = subprocess.check_output(['git', '-C', str(repo), 'check-ignore', 'bin/omarchy-dev-sync'], text=True)
    assert ignored.strip() == 'bin/omarchy-dev-sync'
    # Exercise the real dispatcher when available, entirely in the fixture tree.
    dispatcher = Path.home() / 'src/omarchy/bin/omarchy'
    if dispatcher.exists():
        shutil.copy2(dispatcher, repo / 'bin/omarchy')
        result = subprocess.run(['bash', str(repo / 'bin/omarchy'), 'dev', 'sync', '--help'], env=env, capture_output=True, text=True)
        assert result.returncode == 0 and 'Integrate development PRs' in result.stdout, result
    (repo / 'bin/omarchy-dev-sync').unlink()
    (repo / 'bin/omarchy-dev-sync').write_text('existing command')
    result = run('')
    assert result.returncode == 1 and 'refusing to replace' in result.stderr
    assert (repo / 'bin/omarchy-dev-sync').read_text() == 'existing command'
print('ok - consent, EOF, dev-link invocation, pending reboot and active setup')
