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
        qualified = re.sub(r'(?<![\w.])Color\.', 'Commons.Color.', base)
        qualified = qualified.replace('import qs.Commons\n', 'import qs.Commons\nimport qs.Commons as Commons\n')
        if ours == qualified and ours != base:
            # Upstream qualified the palette; normalize only that mechanical
            # change before a real three-way merge of the feature branch.
            normalized_ours = base
            normalized_theirs = re.sub(r'(?<![\w.])Commons\.Color\.', 'Color.', theirs)
            normalized_theirs = normalized_theirs.replace('import qs.Commons as Commons\n', '')
            with tempfile.TemporaryDirectory() as directory:
                paths = [Path(directory) / str(i) for i in range(3)]
                for path, content in zip(paths, (normalized_ours, base, normalized_theirs)):
                    path.write_text(content)
                merged = subprocess.run(['git', 'merge-file', '-p', *map(str, paths)], capture_output=True, text=True)
            if merged.returncode:
                return False
            content = re.sub(r'(?<![\w.])Color\.', 'Commons.Color.', merged.stdout)
            replacements[file] = content.replace('import qs.Commons\n', 'import qs.Commons\nimport qs.Commons as Commons\n')
            continue
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
    qualified = not palette.is_file()
    if qualified:
        palette = repo / 'shell/Commons/Color.qml'
    if not palette.is_file() or not plugins.is_dir():
        return
    # Match only members actually exposed by this shell palette, and files
    # that import it unqualified. Qt.Color and other namespaces stay intact.
    members = re.findall(r'^  (?:readonly )?property \w+ (\w+)\s*:', palette.read_text(), re.MULTILINE)
    if not members:
        return
    pattern = re.compile(r'(?<![\w.])' + ('(?:ShellColor|Color)' if qualified else 'Color') + r'\.(' + '|'.join(map(re.escape, members)) + r')\b')
    for plugin in sorted(plugins.iterdir()):
        if plugin.is_symlink() or not plugin.is_dir() or (plugin / 'Color.qml').exists():
            continue
        for file in sorted(plugin.rglob('*.qml')):
            if file.is_symlink() or any(parent.is_symlink() for parent in file.parents if parent != plugins):
                continue
            original = file.read_text()
            if not re.search(r'^import qs\.Commons(?:\s+\d+(?:\.\d+)?)?[ \t]*(?://[^\n]*)?$', original, re.MULTILINE):
                continue
            updated = pattern.sub(r'Commons.Color.\1' if qualified else r'ShellColor.\1', original)
            if updated == original:
                continue
            if qualified and not re.search(r'^import qs\.Commons as Commons\s*$', updated, re.MULTILINE):
                updated = re.sub(r'^(import qs\.Commons(?:\s+\d+(?:\.\d+)?)?[ \t]*(?://[^\n]*)?)$', r'\1\nimport qs.Commons as Commons', updated, count=1, flags=re.MULTILINE)
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
