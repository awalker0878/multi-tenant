#!/usr/bin/env python3
"""Launch fixed disposable engine labs from an independent root-owned checkout.

This fixture does not change installation/source trust. It clones the current
clean commit without hard links, adopts only that new tree, and copies declared
lab reports back to the original checkout after the isolated child exits.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LABS = {
    'owner-worker': ('lab/run_owner_worker_lab.py', 'owner_worker_lab.json'),
    'runtime-build': ('lab/run_runtime_build_lab.py', 'runtime_build_lab.json'),
    'nft-edge': ('lab/run_nft_edge_lab.py', 'nft_edge_lab.json'),
}
LAUNCH = ('import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); '
          'runpy.run_path(sys.argv.pop(1),run_name="__main__")')
VERIFY = '''import json,sys
from pathlib import Path
root=Path(sys.argv.pop(1)).resolve()
sys.path.insert(0,str(root))
from provisioner.execution import source_integrity
assert Path(source_integrity.__file__).resolve().is_relative_to(root)
assert source_integrity._protected_checkout(root)
result=source_integrity.verify(root)
assert result['status']=='HASHES_MATCH',result
print(json.dumps(result))'''


def environment():
    values = {key: value for key, value in os.environ.items()
              if not key.startswith(('GIT_', 'PYTHON')) and key != 'SUDO_UID'}
    values.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                  GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1')
    return values


def clone_owned_checkout(source, destination):
    """Prepare only a newly cloned fixture, leaving original custody untouched."""
    if os.getuid() != 0 or os.geteuid() != 0:
        raise RuntimeError('Disposable protected checkout preparation requires root')
    source, destination = Path(source).resolve(strict=True), Path(destination)
    if destination.exists() or not (source / '.git').is_dir():
        raise RuntimeError('A current checkout and new fixture destination are required')
    owner = source.stat()
    prefix = []
    if owner.st_uid != 0:
        account = pwd.getpwuid(owner.st_uid)
        prefix = [shutil.which('runuser') or '/usr/sbin/runuser', '-u', account.pw_name, '--']
    git = prefix + [shutil.which('git') or '/usr/bin/git', '--no-replace-objects',
                    '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false']
    def command(argv):
        return subprocess.check_output(argv, env=environment(), stdin=subprocess.DEVNULL,
                                       stderr=subprocess.PIPE, timeout=120)
    commit = command([*git, '-C', str(source), 'rev-parse', '--verify', 'HEAD^{commit}']).decode().strip()
    if command([*git, '-C', str(source), 'status', '--porcelain', '-z', '--untracked-files=all']):
        raise RuntimeError('Disposable lab requires the exact clean committed source')
    destination.mkdir(mode=0o755)
    if owner.st_uid != 0:
        os.chown(destination, owner.st_uid, owner.st_gid)
    command([*git, 'clone', '--quiet', '--no-hardlinks', '--no-recurse-submodules',
             '--', str(source), str(destination)])
    if (destination / '.git/objects/info/alternates').exists():
        raise RuntimeError('External fixture Git object stores are unsupported')
    for path in (destination, *destination.rglob('*')):
        info = path.lstat()
        if (path.is_symlink() or path.is_junction()
                or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode))
                or (stat.S_ISREG(info.st_mode) and info.st_nlink != 1)):
            raise RuntimeError('Linked or unsupported protected fixture source')
        if (info.st_uid, info.st_gid) != (0, 0):
            os.chown(path, 0, 0, follow_symlinks=False)
        path.chmod(0o755 if path.is_dir() or info.st_mode & 0o111 else 0o644)
    return commit


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--lab', choices=tuple(LABS), required=True)
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    arguments = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
    lab, report = LABS[args.lab]
    reports = ROOT / 'build/reports'
    reports.mkdir(parents=True, exist_ok=True)
    outcome = {'status': 'PROTECTED_SOURCE_FIXTURE_HELD', 'lab': args.lab,
               'nativeQualification': False, 'productionActivation': False}
    code = 2
    try:
        with tempfile.TemporaryDirectory(prefix='hosting-protected-source-', dir='/var/lib') as temporary:
            base = Path(temporary); base.chmod(0o755)
            source = base / 'source'
            commit = clone_owned_checkout(ROOT, source)
            verified = json.loads(subprocess.check_output(
                [sys.executable, '-I', '-B', '-c', VERIFY, str(source)], cwd=source,
                env=environment(), stdin=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=120))
            if verified['commit'] != commit:
                raise RuntimeError('Protected fixture source commit changed')
            outcome.update(sourceCommit=commit, rootOwnedCheckout=True,
                           independentGitObjects=True, isolatedPythonLaunch=True)
            child = subprocess.run([sys.executable, '-I', '-B', '-c', LAUNCH,
                                    str(source), str(source / lab), *arguments],
                                   cwd=source, env=environment(), stdin=subprocess.DEVNULL)
            code = child.returncode
            retained = source / 'build/reports' / report
            if retained.is_file() and not retained.is_symlink() and retained.stat().st_size <= 8 * 1024 * 1024:
                (reports / report).write_bytes(retained.read_bytes())
            elif code == 0:
                raise RuntimeError('Successful disposable lab omitted its declared evidence report')
            outcome['status'] = 'PASSED_PROTECTED_SOURCE_LAUNCH' if code == 0 else 'PROTECTED_SOURCE_LAB_FAILED'
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        code = 2
        outcome['status'] = 'PROTECTED_SOURCE_FIXTURE_HELD'
    (reports / ('protected_source_' + args.lab + '.json')).write_text(
        json.dumps(outcome, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(outcome, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
