#!/usr/bin/env python3
"""Align known Omarchy mirrors with edge for the persistent dev-linked repo."""
import argparse
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import tempfile


def source_changes(repo, etc=Path('/etc')):
    config = etc / 'omarchy.conf'
    if not config.is_file():
        return {}
    linked = None
    for line in config.read_text().splitlines():
        match = re.fullmatch(r'\s*(?:export\s+)?OMARCHY_PATH=(.*)\s*', line)
        if match:
            words = shlex.split(match[1], comments=True)
            if len(words) != 1 or not words[0].startswith('/'):
                raise ValueError('Cannot parse the persistent Omarchy dev link')
            linked = Path(words[0]).resolve()
    if linked is None or linked == Path('/usr/share/omarchy') or linked != repo.resolve():
        return {}
    metadata = config.stat()
    if metadata.st_uid != 0 or metadata.st_mode & 0o022:
        raise ValueError('Persistent Omarchy dev link must be root-owned and not writable by others')
    paths = (etc / 'pacman.conf', etc / 'pacman.d/mirrorlist')
    changes = {}
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Refusing to replace missing or symlinked package configuration: {path}')
        original = path.read_text()
        lines = original.splitlines(keepends=True)
        section = ''
        updated = []
        for line in lines:
            heading = re.fullmatch(r'\s*\[([^]]+)\]\s*(?:#.*)?', line.strip())
            if heading:
                section = heading[1]
            if path.name == 'pacman.conf' and section == 'omarchy':
                line = re.sub(r'^(\s*Server\s*=\s*https://pkgs\.omarchy\.org/)(stable|rc)(/)',
                              r'\1edge\3', line)
            elif path.name == 'mirrorlist':
                line = re.sub(r'^(\s*Server\s*=\s*https://)(stable-|rc-)mirror\.omarchy\.org/',
                              r'\1mirror.omarchy.org/', line)
            updated.append(line)
        content = ''.join(updated)
        if content != original:
            changes[path] = (original, content)
    return changes


def install_changes(changes):
    # Stage everything and verify originals before replacing any live file.
    staged = {}
    backups = {}
    replaced = []
    try:
        for path, (original, content) in changes.items():
            if path.is_symlink() or path.read_text() != original:
                raise ValueError(f'Package configuration changed during repair: {path}')
            metadata = path.stat()
            fd, temporary = tempfile.mkstemp(prefix=f'.{path.name}.dev-sync.', dir=path.parent)
            staged[path] = Path(temporary)
            with os.fdopen(fd, 'w') as file:
                file.write(content)
            os.chmod(temporary, stat.S_IMODE(metadata.st_mode))
            os.chown(temporary, metadata.st_uid, metadata.st_gid)
            fd, backup = tempfile.mkstemp(prefix=f'{path.name}.bak.omarchy-dev-sync.', dir=path.parent)
            os.close(fd)
            backups[path] = Path(backup)
            shutil.copy2(path, backup)
            os.chown(backup, metadata.st_uid, metadata.st_gid)
        for path, temporary in staged.items():
            if path.is_symlink() or path.read_text() != changes[path][0]:
                raise ValueError(f'Package configuration changed during repair: {path}')
            os.replace(temporary, path)
            replaced.append(path)
        for path, backup in backups.items():
            print(f'Set dev-linked package sources to edge: {path} (backup: {backup})')
    except Exception:
        for path in reversed(replaced):
            shutil.copy2(backups[path], path)
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('repo', type=Path)
    args = parser.parse_args()
    try:
        changes = source_changes(args.repo)
        if args.check:
            raise SystemExit(2 if changes else 0)
        if os.geteuid() != 0:
            raise ValueError('Package source repair requires root')
        install_changes(changes)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Error: {error}\n')
