#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compat', root / 'quirks/qt612-shell-color/compat.py')
compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compat)

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True, stderr=subprocess.DEVNULL)

for pure in (True, False):
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory)
        git(repo, 'init', '-q', '-b', 'master')
        git(repo, 'config', 'user.name', 'Test')
        git(repo, 'config', 'user.email', 'test@example.invalid')
        git(repo, 'config', 'rerere.enabled', 'false')
        file = repo / 'shell/plugins/notifications/components/NotificationCard.qml'
        file.parent.mkdir(parents=True)
        base = 'import qs.Commons\nText { color: Color.foreground; font.family: "default" }\n'
        file.write_text(base)
        git(repo, 'add', '.')
        git(repo, 'commit', '-qm', 'base')
        git(repo, 'switch', '-qc', 'rename')
        incoming = base.replace('Color.', 'ShellColor.')
        if not pure:
            incoming = incoming.replace('default', 'incoming')
        file.write_text(incoming)
        git(repo, 'commit', '-qam', 'rename')
        git(repo, 'switch', '-q', 'master')
        file.write_text(base.replace('default', 'user font'))
        git(repo, 'commit', '-qam', 'font configuration')
        assert subprocess.run(['git', '-C', str(repo), 'merge', '--no-edit', 'rename'], capture_output=True).returncode
        before = file.read_text()
        assert compat.resolve(repo) == pure
        if pure:
            assert 'ShellColor.foreground' in file.read_text() and 'user font' in file.read_text()
            assert not git(repo, 'diff', '--name-only', '--diff-filter=U')
        else:
            assert file.read_text() == before and git(repo, 'diff', '--name-only', '--diff-filter=U')
        print('ok - ' + ('pure incoming rename preserves local font behavior without rerere' if pure else 'incoming logic changes rejected without editing conflict'))

with tempfile.TemporaryDirectory() as directory:
    repo = Path(directory) / 'repo'
    palette = repo / 'shell/Commons/ShellColor.qml'
    palette.parent.mkdir(parents=True)
    palette.write_text('  property color foreground: "#fff"\n  readonly property QtObject bar: QtObject {}\n')
    plugins = Path(directory) / 'plugins'
    file = plugins / 'custom/Panel.qml'
    file.parent.mkdir(parents=True)
    original = 'import qs.Commons\nColor.foreground\nColor.bar.background\nQt.Color.Rgb\nColor.Rgb\nOther.Color.foreground\n'
    file.write_text(original)
    alias = file.parent / 'Alias.qml'
    alias.write_text('import qs.Commons as Commons\nColor.foreground\n')
    outside = Path(directory) / 'outside.qml'
    outside.write_text(original)
    (file.parent / 'Link.qml').symlink_to(outside)
    compat.migrate(repo, plugins)
    assert file.read_text() == original.replace('Color.foreground\nColor.bar', 'ShellColor.foreground\nShellColor.bar', 1)
    assert next(file.parent.glob('Panel.qml.bak.*')).read_text() == original
    assert outside.read_text() == original
    assert alias.read_text().endswith('Color.foreground\n')
    compat.migrate(repo, plugins)
    assert len(list(file.parent.glob('Panel.qml.bak.*'))) == 1
    print('ok - only shell palette references migrated; backup/idempotence; Qt colors, aliases and symlinks preserved')
