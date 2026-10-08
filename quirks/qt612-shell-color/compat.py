#!/usr/bin/env python3
"""Portable resolution and plugin migration for Qt 6.12's Color collision."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True)


def resolve(repo):
    files = git(repo, 'diff', '--name-only', '--diff-filter=U').splitlines()
    replacements = {}
    for file in files:
        if not file.startswith('shell/') or not file.endswith('.qml'):
            return False
        base, ours, theirs = (git(repo, 'show', f':{stage}:{file}') for stage in (1, 2, 3))
        renamed = re.sub(r'\bColor\.', 'ShellColor.', base)
        if renamed == base or theirs != renamed:
            return False
        # Incoming changes must be exactly the palette rename. Retain every
        # local behavior change, applying that same rename to our version.
        replacements[file] = re.sub(r'\bColor\.', 'ShellColor.', ours)
    if not replacements:
        return False
    for file, content in replacements.items():
        (repo / file).write_text(content)
    git(repo, 'add', '--', *replacements)
    return True


def migrate(repo, plugins):
    palette = repo / 'shell/Commons/ShellColor.qml'
    if not palette.is_file() or not plugins.is_dir():
        return
    # Match only members actually exposed by this shell palette, and files
    # that import it unqualified. Qt.Color and other namespaces stay intact.
    members = re.findall(r'^  (?:readonly )?property \w+ (\w+)\s*:', palette.read_text(), re.MULTILINE)
    if not members:
        return
    pattern = re.compile(r'(?<![\w.])Color\.(' + '|'.join(map(re.escape, members)) + r')\b')
    for plugin in sorted(plugins.iterdir()):
        if plugin.is_symlink() or not plugin.is_dir() or (plugin / 'Color.qml').exists():
            continue
        for file in sorted(plugin.rglob('*.qml')):
            if file.is_symlink() or any(parent.is_symlink() for parent in file.parents if parent != plugins):
                continue
            original = file.read_text()
            if not re.search(r'^import qs\.Commons(?:\s+\d+(?:\.\d+)?)?[ \t]*(?://[^\n]*)?$', original, re.MULTILINE):
                continue
            updated = pattern.sub(r'ShellColor.\1', original)
            if updated == original:
                continue
            fd, backup = tempfile.mkstemp(prefix=file.name + '.bak.dev-sync-color.', dir=file.parent)
            os.close(fd)
            shutil.copy2(file, backup)
            try:
                file.write_text(updated)
            except OSError:
                shutil.copy2(backup, file)
                raise
            print(f'Migrated plugin palette: {file} (backup: {backup})')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('resolve', 'migrate'))
    parser.add_argument('repo', type=Path)
    parser.add_argument('--plugins', type=Path, default=Path.home() / '.config/omarchy/plugins')
    args = parser.parse_args()
    try:
        if args.mode == 'resolve':
            raise SystemExit(0 if resolve(args.repo) else 2)
        migrate(args.repo, args.plugins)
    except (OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Error: {error}\n')
