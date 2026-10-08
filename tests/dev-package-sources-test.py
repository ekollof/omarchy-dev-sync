#!/usr/bin/env python3
"""Check source repair using isolated configs, never the real package database."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('sources', root / 'lib/dev-package-sources.py')
sources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sources)

with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    repo = temp / 'repo with spaces'
    repo.mkdir()
    etc = temp / 'etc'
    (etc / 'pacman.d').mkdir(parents=True)
    config = etc / 'omarchy.conf'
    config.write_text(f'export OMARCHY_PATH="{repo}"\n')
    pacman = etc / 'pacman.conf'
    mirrors = etc / 'pacman.d/mirrorlist'
    original = '''[options]
IgnorePkg = custom
[custom]
Server = https://custom.example/stable/$arch
[omarchy]
# Server = https://pkgs.omarchy.org/stable/$arch
Server = https://pkgs.omarchy.org/stable/$arch
[another]
Server = https://pkgs.omarchy.org/stable/$arch
'''
    original_mirrors = '# custom mirror comment\nServer = https://stable-mirror.omarchy.org/$repo/os/$arch\nServer = https://custom.example/$repo/os/$arch\n'
    pacman.write_text(original)
    mirrors.write_text(original_mirrors)
    real_stat = Path.stat

    def root_config_stat(path, *args, **kwargs):
        metadata = real_stat(path, *args, **kwargs)
        if path == config:
            fields = list(metadata)
            fields[4] = 0  # Model a root-owned /etc/omarchy.conf in the fixture.
            return os.stat_result(fields)
        return metadata

    with patch.object(Path, 'stat', root_config_stat):
        changes = sources.source_changes(repo, etc)
        assert len(changes) == 2
        assert changes[pacman][1] == original.replace(
            'Server = https://pkgs.omarchy.org/stable/$arch\n[another]',
            'Server = https://pkgs.omarchy.org/edge/$arch\n[another]')
        sources.install_changes(changes)
        assert 'IgnorePkg = custom' in pacman.read_text()
        assert mirrors.read_text() == original_mirrors.replace('stable-mirror.', 'mirror.')
        assert next(etc.glob('pacman.conf.bak.*')).read_text() == original
        assert next((etc / 'pacman.d').glob('mirrorlist.bak.*')).read_text() == original_mirrors
        assert not sources.source_changes(repo, etc)
        print('ok - stable URLs aligned; custom settings/comments retained; backups created; repeat is a no-op')
        pacman.write_text(original.replace('/stable/', '/rc/'))
        mirrors.write_text(original_mirrors.replace('stable-mirror.', 'rc-mirror.'))
        assert len(sources.source_changes(repo, etc)) == 2
        assert not sources.source_changes(temp / 'different-repo', etc)
        config.write_text('export OMARCHY_PATH="/usr/share/omarchy"\n')
        assert not sources.source_changes(repo, etc)
        config.unlink()
        assert not sources.source_changes(repo, etc)
        print('ok - rc handled; unrelated checkouts, packaged installs and missing dev links untouched')
        config.write_text(f'export OMARCHY_PATH="{repo}"\n')
        config.chmod(0o666)
        try:
            sources.source_changes(repo, etc)
            raise AssertionError('writable dev link accepted')
        except ValueError:
            pass
        config.chmod(0o644)
        pending = sources.source_changes(repo, etc)
        real_replace = os.replace
        replace_count = 0

        def fail_second_replace(source, destination):
            global replace_count
            replace_count += 1
            if replace_count == 2:
                raise OSError('simulated second-file installation failure')
            return real_replace(source, destination)

        before_install = (pacman.read_text(), mirrors.read_text())
        with patch.object(os, 'replace', fail_second_replace):
            try:
                sources.install_changes(pending)
                raise AssertionError('installation failure accepted')
            except OSError:
                pass
        assert (pacman.read_text(), mirrors.read_text()) == before_install
        print('ok - insecure dev-link config refused; second-file installation failure rolls back the first')
        pacman.write_text('concurrent edit\n')
        try:
            sources.install_changes(pending)
            raise AssertionError('concurrent edit accepted')
        except ValueError:
            pass
        assert pacman.read_text() == 'concurrent edit\n'
        assert 'rc-mirror.' in mirrors.read_text()
        pacman.unlink()
        pacman.symlink_to(temp / 'custom-config')
        try:
            sources.source_changes(repo, etc)
            raise AssertionError('symlink accepted')
        except ValueError:
            pass
        print('ok - concurrent edits and symlinked configs refused before replacing files')

    # Exercise privilege dispatch without actually elevating.
    tools = temp / 'tools'
    tools.mkdir()
    log = temp / 'calls'
    for name, content in {
        'python3': '#!/bin/bash\nexit "${CHECK_STATUS:-2}"\n',
        'pkexec': '#!/bin/bash\nprintf "%s\\n" "$*" >> "$CALL_LOG"\nexit "${INSTALL_STATUS:-0}"\n',
    }.items():
        file = tools / name
        file.write_text(content)
        file.chmod(0o755)
    env = dict(os.environ, PATH=f'{tools}:{os.environ["PATH"]}', CALL_LOG=str(log))
    command = ['bash', '-c', 'set -euo pipefail; source "$1/lib/dev-package-sources.sh"; script_dir=$1; repo=$2; ensure_dev_package_sources', 'test', str(root), str(repo)]
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    assert result.returncode == 0 and '/usr/bin/python3 -I' in log.read_text()
    assert 'Run omarchy update' in result.stdout
    log.unlink()
    env['CHECK_STATUS'] = '0'
    assert subprocess.run(command, env=env, capture_output=True).returncode == 0
    assert not log.exists()
    env['CHECK_STATUS'] = '1'
    assert subprocess.run(command, env=env, capture_output=True).returncode == 1
    assert not log.exists()
    env['CHECK_STATUS'] = '2'
    env['INSTALL_STATUS'] = '1'
    assert subprocess.run(command, env=env, capture_output=True).returncode == 1
    print('ok - privilege requested only for repairs; check and installation failures stop the sync')
