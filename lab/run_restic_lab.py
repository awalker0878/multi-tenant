#!/usr/bin/env python3
"""Real restic encrypted local capture/restore; no service or native target contact."""
import argparse
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from provisioner.execution.restic_run import Restic, backup, restore, sha_file
from provisioner.execution.run_files import utcnow


def run(binary):
    with tempfile.TemporaryDirectory(prefix='hosting-restic-lab-') as tmp:
        base = Path(tmp)
        repository, source = base / 'repository', base / 'export'
        source.mkdir(mode=0o700)
        data = b'Useful synthetic dataset\n' * 2000
        (source / 'dataset.bin').write_bytes(data)
        (source / 'index.json').write_text('{"dataset":"dataset.bin","rows":2000}\n')
        password = 'disposable-' + os.urandom(24).hex()
        env = {'PATH': '/usr/bin:/bin', 'RESTIC_PASSWORD': password, 'GOMAXPROCS': '2'}
        # Repository initialization belongs exclusively to this disposable lab.
        subprocess.run([str(binary), '--no-cache', '--repo', str(repository), 'init'], env=env,
                       check=True, capture_output=True, timeout=45)
        native = json.loads(subprocess.check_output([str(binary), '--no-cache', '--repo', str(repository), 'cat', 'config'], env=env, timeout=20))
        config = dict(format='hosting-restic-export/1',
            scope=dict(environment_key='test', site_key='lab-site', platform='openstack', tenant_key='tenant-a', wsd_key='science'),
            member='guest-a', machine_id='a' * 32, source=str(source), repository=str(repository),
            repository_id=native['id'], restic_sha256=sha_file(Path(binary)),
            valid_until=(utcnow() + timedelta(hours=1)).isoformat(), consistency_ref='LOCAL-IMMUTABLE-FIXTURE', max_seconds=120)
        credentials = dict(password=password, username='lab', http_password='lab')
        first = base / 'capture'; first.mkdir(mode=0o700)
        receipt, expected = backup(config, Restic(binary, config, credentials, first), first, fixture=True)
        # Prove recovery from retained bytes after the source export changes.
        (source / 'dataset.bin').write_bytes(b'changed after capture')
        second = base / 'recovery'; second.mkdir(mode=0o700)
        restored = restore(config, receipt, expected, Restic(binary, config, credentials, second),
                           second, base / 'isolated-target', fixture=True)
        if (base / 'isolated-target' / str(source).lstrip('/') / 'dataset.bin').read_bytes() != data:
            raise RuntimeError('Restored useful data differs')
        third = base / 'wrong-key'; third.mkdir(mode=0o700)
        rejected = False
        try:
            Restic(binary, config, credentials | {'password': 'incorrect-disposable-key'}, third).repository()
        except ValueError:
            rejected = True
        if not rejected:
            raise RuntimeError('Wrong repository key was accepted')
        fourth = base / 'foreign'; fourth.mkdir(mode=0o700)
        foreign = deepcopy(receipt); foreign['scope']['tenant_key'] = 'tenant-b'
        try:
            restore(config, foreign, expected, Restic(binary, config, credentials, fourth), fourth,
                    base / 'foreign-target', fixture=True)
        except ValueError:
            pass
        else:
            raise RuntimeError('Foreign restore scope was accepted')
        for directory in [first, second, third, fourth]:
            if any(path.stat().st_mode & 0o077 for path in directory.iterdir() if path.is_file()):
                raise RuntimeError('Private backup artifact permissions changed')
        return {'status': 'PASSED_LOCAL_RESTIC_RECOVERY_ONLY', 'file_count': restored['file_count'],
                'useful_bytes_recovered': True, 'source_changed_after_capture': True,
                'wrong_key_rejected': rejected, 'foreign_scope_rejected': True,
                'restore_seconds': restored['restore_seconds'], 'native_target_contacted': False,
                'remote_append_only_service_tested': False, 'application_consistency_tested': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restic', type=Path, default=shutil.which('restic'))
    args = parser.parse_args()
    try:
        if args.restic is None:
            raise ValueError('Install the declared restic engine')
        report = run(args.restic.resolve())
        code = 0
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        report = {'status': 'FAILED_LOCAL_RESTIC_RECOVERY', 'reason': str(exc), 'native_target_contacted': False}
        code = 2
    output = ROOT / 'build/reports/restic_recovery_lab.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
