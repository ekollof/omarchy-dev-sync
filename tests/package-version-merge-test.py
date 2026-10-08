#!/usr/bin/env python3
"""Test portable version resolution with real Git conflicts and no rerere."""
from pathlib import Path
import subprocess
import tempfile

resolver = Path(__file__).resolve().parents[1] / 'quirks/dev-package-version/resolve.py'


def run(checkout, *args):
    return subprocess.check_output(['git', '-C', str(checkout), *args], text=True,
                                   stderr=subprocess.DEVNULL)


for mode in ('versions', 'logic', 'both-release', 'pr-version'):
    with tempfile.TemporaryDirectory() as directory:
        checkout = Path(directory)
        run(checkout, 'init', '-q', '-b', 'master')
        run(checkout, 'config', 'user.name', 'Test')
        run(checkout, 'config', 'user.email', 'test@example.invalid')
        run(checkout, 'config', 'rerere.enabled', 'false')
        recipes = [checkout / f'pkgbuilds/{name}/PKGBUILD'
                   for name in ('omarchy-dev', 'omarchy-settings-dev')]
        base = 'pkgver=4.0.0.r1.gabc\npkgrel=1\n\n_commit=abc\n\npackage() {\n  echo base\n}\n'
        for recipe in recipes:
            recipe.parent.mkdir(parents=True)
            recipe.write_text(base)
        run(checkout, 'add', '.')
        run(checkout, 'commit', '-qm', 'base')
        run(checkout, 'switch', '-qc', 'pr')
        for recipe in recipes:
            content = base.replace('pkgrel=1', 'pkgrel=2').replace('echo base', 'echo patch')
            if mode == 'pr-version':
                content = content.replace('pkgver=4.0.0.r1.gabc', 'pkgver=4.0.0.r3.gdef')
            recipe.write_text(content)
        run(checkout, 'commit', '-qam', 'PR release and logic')
        run(checkout, 'switch', '-q', 'master')
        for recipe in recipes:
            content = base.replace('r1.gabc', 'r2.gdef').replace('_commit=abc', '_commit=def')
            if mode == 'logic':
                content = content.replace('echo base', 'echo upstream')
            if mode == 'both-release':
                content = content.replace('pkgrel=1', 'pkgrel=3')
            recipe.write_text(content)
        run(checkout, 'commit', '-qam', 'upstream version')
        result = subprocess.run(['git', '-C', str(checkout), 'merge', '--no-edit', 'pr'],
                                capture_output=True, text=True)
        assert result.returncode != 0
        before = [recipe.read_bytes() for recipe in recipes]
        result = subprocess.run(['python3', str(resolver), str(checkout)])
        if mode == 'versions':
            assert result.returncode == 0
            assert not run(checkout, 'diff', '--name-only', '--diff-filter=U')
            for recipe in recipes:
                content = recipe.read_text()
                assert 'pkgver=4.0.0.r2.gdef' in content and 'pkgrel=2' in content
                assert '_commit=def' in content and 'echo patch' in content
            run(checkout, 'commit', '-qm', 'resolved')
        else:
            assert result.returncode != 0
            assert before == [recipe.read_bytes() for recipe in recipes]
            assert run(checkout, 'diff', '--name-only', '--diff-filter=U')
        print(f'ok - {mode}: ' + ('preserves version, pin and PR logic' if mode == 'versions' else 'refuses without edits'))
