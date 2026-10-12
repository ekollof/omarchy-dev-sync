#!/usr/bin/env python3
"""Preserve upstream's unit loop and authorization retirement for stale GPD PRs."""
from pathlib import Path
import re
import subprocess
import sys

PATH = 'install/user/first-run/enable-user-units.sh'
OURS = '''  omarchy-crash-watch.service; do
  systemctl --user enable --now "$unit" || failed=1
done'''
THEIRS = '''  omarchy-crash-watch.service \\
  omarchy-gpd-pocket-4-rotate.service \\
  omarchy-usb-authorization.service \\
  omarchy-thunderbolt-authorization.service'''
RESOLVED = OURS.replace('omarchy-crash-watch.service; do',
                        'omarchy-crash-watch.service \\\n  omarchy-gpd-pocket-4-rotate.service; do')


def git(checkout, *args):
    return subprocess.check_output(['git', '-C', str(checkout), *args], text=True)


def resolve(checkout):
    if git(checkout, 'diff', '--name-only', '--diff-filter=U').splitlines() != [PATH]:
        return False
    content = (checkout / PATH).read_text()
    pattern = r'^<<<<<<< [^\n]+\n(.*?)\n=======\n(.*?)\n>>>>>>> [^\n]+\n'
    blocks = list(re.finditer(pattern, content, re.M | re.S))
    if len(blocks) != 1 or blocks[0].groups() != (OURS, THEIRS):
        return False
    # The retired services must actually be absent on the upstream side.
    ours = git(checkout, 'show', f':2:{PATH}')
    if 'omarchy-usb-authorization' in ours or 'omarchy-thunderbolt-authorization' in ours:
        return False
    block = blocks[0]
    result = content[:block.start()] + RESOLVED + '\n' + content[block.end():]
    if re.search(r'^(<<<<<<<|=======|>>>>>>>)', result, re.M):
        return False
    (checkout / PATH).write_text(result)
    git(checkout, 'add', '--', PATH)
    return True


if __name__ == '__main__':
    try:
        success = resolve(Path(sys.argv[1]))
    except (OSError, subprocess.CalledProcessError):
        success = False
    sys.exit(0 if success else 2)
