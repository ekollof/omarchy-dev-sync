#!/usr/bin/env python3
"""Exercise the portable GPD resolver with rerere disabled."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('resolver', root / 'quirks/gpd-first-run-units/resolve.py')
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)


def git(repo, *args, check=True):
    return subprocess.run(['git', '-C', str(repo), *args], check=check,
                          capture_output=True, text=True)


with tempfile.TemporaryDirectory() as directory:
    repo = Path(directory)
    git(repo, 'init', '-q', '-b', 'base')
    git(repo, 'config', 'user.name', 'Test')
    git(repo, 'config', 'user.email', 'test@example.invalid')
    git(repo, 'config', 'rerere.enabled', 'false')
    path = repo / resolver.PATH
    path.parent.mkdir(parents=True)
    prefix = '#!/bin/bash\n# Preserve this unrelated addition\n'
    common = ''.join(f'  service-{n}.service \\\n' for n in range(10))
    base = prefix + 'systemctl --user enable --now \\\n' + common + '  omarchy-crash-watch.service \\\n  omarchy-usb-authorization.service \\\n  omarchy-thunderbolt-authorization.service\n'
    footer = '\nomarchy-hook-install theme-set /usr/share/owe/10-owe-sync\n'
    base += footer
    path.write_text(base)
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'base')
    git(repo, 'checkout', '-qb', 'gpd')
    path.write_text(prefix + 'systemctl --user enable --now \\\n' + common + resolver.THEIRS + '\n' + footer)
    git(repo, 'commit', '-qam', 'GPD')
    git(repo, 'checkout', '-qb', 'upstream', 'base')
    ours = prefix + 'failed=0\nfor unit in \\\n' + common + resolver.OURS + '\n' + footer + 'exit "$failed"\n'
    path.write_text(ours)
    git(repo, 'commit', '-qam', 'upstream loop and retirement')
    assert git(repo, 'merge', '--no-commit', 'gpd', check=False).returncode == 1
    original = path.read_text()
    # An extra unmerged file must prevent any writes.
    blob = git(repo, 'rev-parse', f'HEAD:{resolver.PATH}').stdout.strip()
    subprocess.run(['git', '-C', str(repo), 'update-index', '--index-info'],
                   input=f'100644 {blob} 1\tother\n100644 {blob} 2\tother\n100644 {blob} 3\tother\n',
                   text=True, check=True)
    assert not resolver.resolve(repo)
    assert path.read_text() == original
    git(repo, 'update-index', '--force-remove', 'other')
    path.write_text(original.replace('omarchy-gpd-pocket-4-rotate.service', 'unexpected.service'))
    altered = path.read_text()
    assert not resolver.resolve(repo)
    assert path.read_text() == altered
    path.write_text(original)
    assert resolver.resolve(repo)
    assert path.read_text() == ours.replace(resolver.OURS, resolver.RESOLVED)
    assert not git(repo, 'diff', '--name-only', '--diff-filter=U').stdout
    subprocess.run(['bash', '-n', str(path)], check=True)
    assert not resolver.resolve(repo)  # Clean/retired condition.
print('ok - exact GPD conflict resolves without rerere; unrelated conflicts refused; clean merge inactive')
