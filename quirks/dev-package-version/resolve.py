#!/usr/bin/env python3
"""Resolve only independent upstream pkgver and PR pkgrel changes."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def git(checkout, *args):
    return subprocess.check_output(['git', '-C', str(checkout), *args], text=True)


def resolve(checkout):
    paths = git(checkout, 'diff', '--name-only', '--diff-filter=U').splitlines()
    allowed = {'pkgbuilds/omarchy-dev/PKGBUILD', 'pkgbuilds/omarchy-settings-dev/PKGBUILD'}
    if not paths or not set(paths) <= allowed:
        return False
    resolved = {}
    for path in paths:
        base, ours, theirs = (git(checkout, 'show', f':{stage}:{path}') for stage in (1, 2, 3))
        versions = []
        for content in (base, ours, theirs):
            values = {}
            for field in ('pkgver', 'pkgrel'):
                matches = re.findall(rf'^{field}=([A-Za-z0-9.]+)$', content, re.MULTILINE)
                if len(matches) != 1:
                    return False
                values[field] = matches[0]
            versions.append(values)
        b, o, t = versions
        if not (t['pkgver'] == b['pkgver'] != o['pkgver']
                and o['pkgrel'] == b['pkgrel'] != t['pkgrel']
                and b['pkgrel'].isdigit() and t['pkgrel'].isdigit()
                and int(t['pkgrel']) > int(b['pkgrel'])):
            return False
        # Make only the independently changed version lines identical, then
        # ask Git to merge everything else. Never resolve recipe logic here.
        def normalize(content):
            for field, value in (('pkgver', o['pkgver']), ('pkgrel', t['pkgrel'])):
                content = re.sub(rf'^{field}=.*$', f'{field}={value}', content, flags=re.MULTILINE)
            return content
        with tempfile.TemporaryDirectory() as directory:
            files = [Path(directory) / name for name in ('ours', 'base', 'theirs')]
            for file, content in zip(files, (ours, base, theirs)):
                file.write_text(normalize(content))
            result = subprocess.run(['git', 'merge-file', '-p', *map(str, files)],
                                    capture_output=True, text=True)
            if result.returncode:
                return False
            resolved[path] = result.stdout
    # Validate every conflicted file before writing or staging any of them.
    for path, content in resolved.items():
        (checkout / path).write_text(content)
    git(checkout, 'add', '--', *resolved)
    return True


if __name__ == '__main__':
    try:
        success = resolve(Path(sys.argv[1]))
    except (OSError, subprocess.CalledProcessError):
        success = False
    sys.exit(0 if success else 2)
