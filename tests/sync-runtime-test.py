#!/usr/bin/env python3
"""Exercise real git integration plus fake package building/installation."""
import os
import pathlib
import shutil
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[1]

def run(args, cwd=None, env=None):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout

with tempfile.TemporaryDirectory() as directory:
    temp = pathlib.Path(directory)
    home = temp / 'home'
    home.mkdir()
    tools = temp / 'bin'
    tools.mkdir()
    script = temp / 'sync'
    shutil.copytree(root, script, ignore=shutil.ignore_patterns('.git'))
    source = temp / 'source'
    run(['git', 'init', '-q', '-b', 'quattro', str(source)])
    run(['git', 'config', 'user.name', 'Test'], source)
    run(['git', 'config', 'user.email', 'test@example.invalid'], source)
    (source / 'marker').write_text('base\n')
    run(['git', 'add', '.'], source)
    run(['git', 'commit', '-qm', 'base'], source)
    run(['git', 'branch', 'integration-prs'], source)
    upstream = temp / 'upstream.git'
    fork = temp / 'fork.git'
    run(['git', 'clone', '-q', '--bare', str(source), str(upstream)])
    run(['git', 'clone', '-q', '--bare', str(source), str(fork)])
    run(['git', 'remote', 'add', 'upstream', str(upstream)], source)
    run(['git', 'remote', 'add', 'fork', str(fork)], source)
    run(['git', 'switch', '-qc', 'selected-pr'], source)
    (source / 'selected').write_text('selected upstream fix\n')
    run(['git', 'add', '.'], source)
    run(['git', 'commit', '-qm', 'selected upstream fix'], source)
    run(['git', 'push', '-q', 'upstream', 'HEAD:refs/pull/14511/head'], source)
    run(['git', 'switch', '-q', 'integration-prs'], source)
    config = home / '.config/omarchy-dev-sync'
    config.mkdir(parents=True)
    (config / 'config').write_text(f'repo={source}\nupstream=upstream\nfork=fork\npkgs_repo={temp}/absent\n')
    (config / 'extra-prs').write_text('14511 # reviewed Qt fix\n')
    state = temp / 'installed-version'
    state.write_text('0.3.1-1\n')
    qt = temp / 'qt-version'
    qt.write_text('6.12.0-1\n')
    log = temp / 'builds'
    log.write_text('')
    mock = {
        'gh': """#!/bin/bash
if [[ $1 == pr && $2 == list && $* != *"--author @me"* ]]; then
  echo 'PR author must come from the active gh account (@me)' >&2
  exit 88
fi
if [[ -n ${TEST_PKGS_SLUG:-} && $* == *"$TEST_PKGS_SLUG"* ]]; then
  [[ ! -f $TEST_PKGS_ERROR ]] || exit 7
  printf '%s\\n' "${TEST_PKGS_PRS:-}"
else
  printf '[]\\n'
fi
""",
        'pacman': '''#!/bin/bash
if [[ $1 != "-Q" ]]; then exit 99; fi
if [[ $2 == "quickshell" ]]; then
  echo "quickshell $(cat "$TEST_VERSION")"
else
  echo "$2 $(cat "$TEST_QT")"
fi
''',
        'makepkg': '''#!/bin/bash
if [[ $1 == "--packagelist" ]]; then
  echo "$PWD/quickshell-0.3.1-1.1-x86_64.pkg.tar.zst"
  exit 0
fi
[[ ! -f $TEST_FAILURE ]] || exit 7
echo "$PWD" >> "$TEST_BUILDS"
touch quickshell-0.3.1-1.1-x86_64.pkg.tar.zst
''',
        'pkexec': '''#!/bin/bash
[[ $1 == "pacman" && $2 == "-U" ]] || exit 99
echo 0.3.1-1.1 > "$TEST_VERSION"
''',
        'omarchy-notification-send': '#!/bin/bash\nexit 0\n',
    }
    for name, content in mock.items():
        file = tools / name
        file.write_text(content)
        file.chmod(0o755)
    env = dict(os.environ, HOME=str(home), XDG_STATE_HOME=str(home / '.local/state'),
               PATH=str(tools) + ':' + os.environ['PATH'], TEST_VERSION=str(state),
               TEST_QT=str(qt), TEST_BUILDS=str(log), TEST_FAILURE=str(temp / 'fail'))
    for name in list(env):
        if name.startswith('OMARCHY_'):
            del env[name]
    command = ['bash', str(script / 'omarchy-dev-sync'), '--no-restart']
    run(command, env=env)
    assert (source / 'selected').is_file()
    assert len(log.read_text().splitlines()) == 1
    print('ok - selected upstream PR merges and runtime rebuild runs with zero helper skew')
    run(command, env=env)
    assert len(log.read_text().splitlines()) == 1
    print('ok - unchanged recipe and Qt skip the runtime rebuild')
    qt.write_text('6.12.1-1\n')
    run(command, env=env)
    assert len(log.read_text().splitlines()) == 2
    print('ok - Qt change rebuilds the runtime package independently of source changes')
    with (script / 'packages/quickshell/qt612-moc.patch').open('a') as file:
        file.write('\n# test patch change\n')
    run(command, env=env)
    assert len(log.read_text().splitlines()) == 3
    print('ok - recipe patch change rebuilds the runtime package')
    state.write_text('0.3.1-1\n')
    run(command + ['--no-pkg'], env=env)
    assert len(log.read_text().splitlines()) == 3
    run(command, env=env)
    assert len(log.read_text().splitlines()) == 4
    print('ok - no-pkg skips packages; replacing the installed package rebuilds on next sync')
    stamp = home / '.local/state/omarchy-dev-sync/packages/quickshell'
    before = stamp.read_bytes()
    qt.write_text('6.13.0-1\n')
    (temp / 'fail').touch()
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert stamp.read_bytes() == before
    assert 'runtime package refresh failed' in result.stderr
    print('ok - failed build stops the sync and never marks the package current')
    # Packaging-only changes must refresh the dev pair with zero helper skew.
    (temp / 'fail').unlink()
    packages = temp / 'pkgs/pkgbuilds'
    for name in ['omarchy-dev', 'omarchy-settings-dev']:
        recipe = packages / name
        recipe.mkdir(parents=True)
        (recipe / 'PKGBUILD').write_text(f'pkgname={name}\npkgver=1\npkgrel=1\n')
    env['OMARCHY_DEV_SYNC_PKGS_REPO'] = str(temp / 'pkgs')
    before_builds = len(log.read_text().splitlines())
    run(command, env=env)
    assert len(log.read_text().splitlines()) == before_builds + 3
    run(command, env=env)
    assert len(log.read_text().splitlines()) == before_builds + 3
    (packages / 'omarchy-dev/new-hook.patch').write_text('packaging-only fix\n')
    run(command, env=env)
    assert len(log.read_text().splitlines()) == before_builds + 5
    print('ok - packaging-only changes rebuild the dev pair; unchanged recipes skip it')
    # Use actual Git pull refs to test packaging PR merge and fail-closed paths.
    pkgs_repo = temp / 'pkgs'
    run(['git', 'init', '-q', '-b', 'master'], pkgs_repo)
    run(['git', 'config', 'user.name', 'Test'], pkgs_repo)
    run(['git', 'config', 'user.email', 'test@example.invalid'], pkgs_repo)
    run(['git', 'add', '.'], pkgs_repo)
    run(['git', 'commit', '-qm', 'base recipes'], pkgs_repo)
    pkgs_remote = temp / 'pkgs-upstream.git'
    run(['git', 'clone', '-q', '--bare', str(pkgs_repo), str(pkgs_remote)])
    run(['git', 'remote', 'add', 'origin', str(pkgs_remote)], pkgs_repo)
    run(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/master'], pkgs_repo)
    run(['git', 'switch', '-qc', 'packaging-pr'], pkgs_repo)
    (packages / 'omarchy-dev/pr-hook.patch').write_text('selected package patch\n')
    run(['git', 'add', '.'], pkgs_repo)
    run(['git', 'commit', '-qm', 'package patch'], pkgs_repo)
    run(['git', 'push', '-q', 'origin', 'HEAD:refs/pull/645/head'], pkgs_repo)
    run(['git', 'switch', '-q', 'master'], pkgs_repo)
    env.update(TEST_PKGS_SLUG=str(pkgs_remote).removesuffix('.git'), TEST_PKGS_PRS='645', TEST_PKGS_ERROR=str(temp / 'api-fail'))
    before_builds = len(log.read_text().splitlines())
    run(command, env=env)
    assert len(log.read_text().splitlines()) == before_builds + 2
    assert not (packages / 'omarchy-dev/pr-hook.patch').exists()
    print('ok - packaging PR recipes trigger builds without modifying the packaging checkout')
    (temp / 'api-fail').touch()
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'refusing to omit packaging patches' in result.stderr
    assert len(log.read_text().splitlines()) == before_builds + 2
    (temp / 'api-fail').unlink()
    print('ok - packaging API failures stop instead of building without patches')
    run(['git', 'switch', '-qc', 'conflicting-pr'], pkgs_repo)
    recipe = packages / 'omarchy-dev/PKGBUILD'
    recipe.write_text(recipe.read_text().replace('pkgrel=1', 'pkgrel=2'))
    run(['git', 'commit', '-qam', 'PR conflicting recipe'], pkgs_repo)
    run(['git', 'push', '-q', 'origin', '+HEAD:refs/pull/645/head'], pkgs_repo)
    run(['git', 'switch', '-q', 'master'], pkgs_repo)
    recipe.write_text(recipe.read_text().replace('pkgrel=1', 'pkgrel=3'))
    run(['git', 'commit', '-qam', 'upstream conflicting recipe'], pkgs_repo)
    run(['git', 'push', '-q', 'origin', 'master'], pkgs_repo)
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'unresolved conflict in omarchy-pkgs PR #645' in result.stderr
    assert len(log.read_text().splitlines()) == before_builds + 2
    print('ok - unresolved packaging merge conflicts stop instead of dropping the PR')
    (config / 'extra-prs').write_text('not-a-pr\n')
    old_head = run(['git', 'rev-parse', 'HEAD'], source)
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert run(['git', 'rev-parse', 'HEAD'], source) == old_head
    print('ok - invalid selected PR leaves integration untouched')
