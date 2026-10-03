#!/usr/bin/env python3
"""Bounded file-export backup and isolated, byte-verified restic restore.

Native CLI supports only pre-created TLS REST repositories. It never initializes,
forgets, prunes, unlocks or restores over an existing destination. Application
consistency remains the export producer's responsibility.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parents[2]
from provisioner.execution.run_files import (digest, encoded, load_private, new_directory, private_path,
                             read_private, replace_private, require, utcnow, write_new, OperatorError)


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'Timezone required')
    return result


def sha_file(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(data)
    return result.hexdigest()


def manifest(source):
    source = Path(source).absolute()
    require(source.is_dir() and not any(p.is_symlink() for p in [source, *source.parents]), 'Real export directory required')
    files = {}
    device = source.stat().st_dev
    for path in sorted(source.rglob('*')):
        info = path.lstat()
        require(info.st_dev == device and (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)),
                'Export must contain only ordinary files/directories on one filesystem')
        if stat.S_ISREG(info.st_mode):
            files[path.relative_to(source).as_posix()] = {'size': info.st_size, 'sha256': sha_file(path)}
    require(bool(files), 'A useful nonempty file export is required')
    return files


def validate(config, *, fixture=False, allow_expired=False):
    require(set(config) == {'format', 'scope', 'member', 'machine_id', 'source', 'repository',
            'repository_id', 'restic_sha256', 'valid_until', 'consistency_ref', 'max_seconds'}, 'Invalid backup configuration')
    require(config['format'] == 'hosting-restic-export/1', 'Unknown backup configuration')
    require(set(config['scope']) == {'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key'},
            'Complete backup scope required')
    for value in [*config['scope'].values(), config['member']]:
        require(isinstance(value, str) and re.fullmatch(r'[a-z][a-z0-9-]{1,40}', value), 'Stable backup identities required')
    require(config['scope']['platform'] in {'nutanix', 'vmware', 'openstack'}, 'Unknown backup platform')
    for key in ('repository_id', 'restic_sha256'):
        require(re.fullmatch('[0-9a-f]{64}', config[key]), 'Exact repository and executable digests required')
    require(re.fullmatch('[0-9a-f]{32}', config['machine_id']), 'Observed source machine ID required')
    source = Path(config['source'])
    require(source.is_absolute() and source != Path('/') and '..' not in source.parts
            and str(source) == config['source'], 'Absolute canonical bounded export path required')
    require(re.fullmatch(r'[A-Za-z0-9:._/-]{3,200}', config['consistency_ref']), 'Export consistency ownership required')
    require(type(config['max_seconds']) is int and 1 <= config['max_seconds'] <= 3600, 'Bounded backup/restore duration required')
    seconds = (timestamp(config['valid_until']) - utcnow()).total_seconds()
    require((allow_expired and seconds <= 0) or 0 < seconds <= 31 * 86400,
            'Delegated backup entitlement expired or exceeds 31 days')
    if not fixture:
        require(config['repository'].startswith('rest:https://'), 'Pre-created authenticated TLS REST repository required')
        url = urlsplit(config['repository'][5:])
        require(url.hostname and not url.username and not url.password and not url.query and not url.fragment
                and re.fullmatch(r'/[A-Za-z0-9_/-]+/', url.path) and '..' not in Path(url.path).parts,
                'Explicit scoped repository without embedded credentials required')
    return 'hosting-' + digest(encoded({'scope': config['scope'], 'member': config['member']}))


class Restic:
    def __init__(self, binary, config, credentials, operation, ca_file=None,
                 resource_control=None):
        if resource_control is not None:
            from provisioner.migration.resources import LinuxTransferResources
            require(isinstance(resource_control, LinuxTransferResources),
                    'Trusted commissioned transfer resource controls required')
            resource_control.require_current()
        self.resource_control = resource_control
        self.binary = Path(binary).resolve(strict=True)
        require(sha_file(self.binary) == config['restic_sha256'], 'Restic executable differs from the approved image')
        require(set(credentials) == {'password', 'username', 'http_password'} and all(
            isinstance(v, str) and v and '\x00' not in v for v in credentials.values()), 'Exact private repository credentials required')
        self.config, self.operation = config, Path(operation)
        private_path(self.operation, directory=True)
        self.ca = str(private_path(ca_file)) if ca_file else None
        self.deadline = min(time.monotonic() + config['max_seconds'],
                            time.monotonic() + (timestamp(config['valid_until']) - utcnow()).total_seconds())
        self.environment = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'TMPDIR': str(self.operation),
                            'RESTIC_PASSWORD': credentials['password'], 'RESTIC_REST_USERNAME': credentials['username'],
                            'RESTIC_REST_PASSWORD': credentials['http_password'], 'GOMAXPROCS': '2'}
        self.counter = 0

    def command(self, arguments):
        require(arguments and arguments[0] in {'cat', 'backup', 'snapshots', 'restore', 'check'}, 'Unsupported restic operation')
        require(not self.binary.is_symlink() and sha_file(self.binary) == self.config['restic_sha256'],
                'The approved restic executable changed between commands')
        if self.resource_control is not None:
            self.resource_control.require_current()
        remaining = self.deadline - time.monotonic()
        require(remaining > 0, 'Backup operation deadline expired')
        self.counter += 1
        stdout, stderr = [self.operation / f'{self.counter:02d}.{name}' for name in ('json', 'log')]
        argv = [str(self.binary), '--no-cache', '--json', '--repo', self.config['repository']]
        if self.resource_control is not None:
            argv += ['--limit-download',
                     str(self.resource_control.limits.download_kib_per_second)]
        if self.ca:
            argv += ['--cacert', self.ca]
        with os.fdopen(os.open(stdout, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as out, \
             os.fdopen(os.open(stderr, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as err:
            result = subprocess.run(argv + arguments, env=self.environment, stdin=subprocess.DEVNULL,
                                    stdout=out, stderr=err, timeout=remaining, umask=0o077)
            out.flush(); os.fsync(out.fileno())
            err.flush(); os.fsync(err.fileno())
        require(result.returncode == 0, 'Restic failed or returned an incomplete backup; inspect private logs')
        if self.resource_control is not None:
            self.resource_control.require_current()
        return stdout.read_text()

    def repository(self):
        config = json.loads(self.command(['cat', 'config']))
        require(config.get('id') == self.config['repository_id'], 'Repository identity changed')


def backup(config, client, operation, *, fixture=False):
    tag = validate(config, fixture=fixture)
    source = Path(config['source'])
    require(not Path(operation).resolve().is_relative_to(source.resolve()), 'Execution artifacts must be outside the export')
    before = manifest(source)
    captured = utcnow().isoformat()
    payload = {'format': 'hosting-file-manifest/1', 'scope': config['scope'], 'member': config['member'],
               'source': str(source), 'files': before, 'captured_at': captured, 'consistency_ref': config['consistency_ref']}
    path = Path(operation) / 'manifest.json'
    write_new(path, encoded(payload))
    client.repository()
    attempt = {'status': 'BACKUP_OUTCOME_UNKNOWN', 'config_sha256': digest(encoded(config)), 'started_at': captured}
    write_new(Path(operation) / 'attempt.json', encoded(attempt))
    output = client.command(['backup', '--force', '--one-file-system', '--host', config['member'],
                            '--tag', tag, '--tag', 'manifest-' + digest(encoded(payload)), '--', str(source), str(path)])
    summaries = [json.loads(line) for line in output.splitlines() if line.strip()]
    summaries = [x for x in summaries if x.get('message_type') == 'summary']
    require(len(summaries) == 1 and re.fullmatch('[0-9a-f]{64}', summaries[0].get('snapshot_id', '')),
            'One exact completed snapshot ID required')
    require(manifest(source) == before, 'Export changed during capture; preserve snapshot but do not accept it')
    result = {'format': 'hosting-restic-receipt/1', 'status': 'CAPTURED_REQUIRES_RESTORE_TEST',
              'scope': config['scope'], 'member': config['member'], 'source': str(source),
              'repository_id': config['repository_id'], 'snapshot_id': summaries[0]['snapshot_id'],
              'manifest_sha256': digest(encoded(payload)), 'manifest_path': str(path),
              'captured_at': captured, 'completed_at': utcnow().isoformat(), 'file_count': len(before),
              'application_consistency': 'EXTERNAL_EXPORT_OWNER', 'native_qualification': False}
    write_new(Path(operation) / 'receipt.json', encoded(result))
    return result, payload


def restore(config, receipt, expected, client, operation, target, *, fixture=False,
            transfer=None, transfer_guard=None):
    tag = validate(config, fixture=fixture)
    if transfer is not None or transfer_guard is not None:
        from provisioner.execution.restic_transfer import GuardedRestic, TransferGuard, validate as validate_transfer
        require(transfer is not None and isinstance(transfer_guard, TransferGuard),
                'Cross-scope restore requires live trusted worker authority')
        validate_transfer(transfer, config, receipt, expected, target)
        transfer_guard.check(transfer)
        client = GuardedRestic(client, transfer_guard, transfer)

    require(receipt['format'] == 'hosting-restic-receipt/1' and receipt['status'] == 'CAPTURED_REQUIRES_RESTORE_TEST'
            and receipt['repository_id'] == config['repository_id'] and receipt['scope'] == config['scope']
            and receipt['member'] == config['member'] and receipt['source'] == config['source']
            and receipt['manifest_sha256'] == digest(encoded(expected)), 'Backup receipt or manifest binding changed')
    require(re.fullmatch('[0-9a-f]{64}', receipt['snapshot_id']), 'Exact snapshot ID required')
    stored_manifest = Path(receipt['manifest_path'])
    require(stored_manifest.is_absolute() and '..' not in stored_manifest.parts
            and str(stored_manifest) == receipt['manifest_path'], 'Canonical stored manifest path required')
    require(expected['format'] == 'hosting-file-manifest/1'
            and expected['source'] == config['source'] and expected['scope'] == config['scope']
            and expected['member'] == config['member'], 'Foreign restore manifest')
    require(expected['captured_at'] == receipt['captured_at']
            and expected['consistency_ref'] == config['consistency_ref']
            and type(receipt['file_count']) is int
            and receipt['file_count'] == len(expected['files'])
            and receipt['application_consistency'] == 'EXTERNAL_EXPORT_OWNER'
            and receipt['native_qualification'] is False,
            'Capture metadata differs from the immutable source manifest')
    require(timestamp(receipt['captured_at']) <= timestamp(receipt['completed_at']) <= utcnow(),
            'Capture timestamps are inconsistent or future-dated')
    require(not Path(target).exists(), 'Restore requires a new isolated destination')
    target_machine_id = Path('/etc/machine-id').read_text().strip()
    require(re.fullmatch('[0-9a-f]{32}', target_machine_id), 'Observed restore machine identity required')
    started = time.monotonic()
    client.repository()
    snapshots = json.loads(client.command(['snapshots', receipt['snapshot_id']]))
    require(len(snapshots) == 1 and snapshots[0]['id'] == receipt['snapshot_id']
            and tag in snapshots[0].get('tags', [])
            and 'manifest-' + receipt['manifest_sha256'] in snapshots[0].get('tags', [])
            and snapshots[0].get('hostname') == config['member']
            and set(snapshots[0].get('paths', [])) == {config['source'], receipt['manifest_path']},
            'Native snapshot identity, scope or contents differ')
    target = new_directory(target, ROOT)
    write_new(Path(operation) / 'attempt.json', encoded({'status': 'RESTORE_INCOMPLETE', 'snapshot_id': receipt['snapshot_id']}))
    client.command(['restore', receipt['snapshot_id'], '--target', str(target), '--verify'])
    recovered_manifest = target / receipt['manifest_path'].lstrip('/')
    require(digest(recovered_manifest.read_bytes()) == receipt['manifest_sha256'], 'Recovered manifest differs')
    actual = manifest(target / config['source'].lstrip('/'))
    require(actual == expected['files'], 'Recovered useful file bytes differ from the capture manifest')
    result = {'format': 'hosting-restic-restore-receipt/1',
              'status': 'RESTORED_FILE_BYTES_VERIFIED_NOT_APPLICATION_ACCEPTED',
              'target_machine_id': target_machine_id, 'restore_root': str(target),
              'snapshot_id': receipt['snapshot_id'], 'scope': config['scope'], 'member': config['member'],
              'file_count': len(actual), 'restore_seconds': round(time.monotonic() - started, 3),
              'data_age_seconds': round((utcnow() - timestamp(receipt['captured_at'])).total_seconds(), 3),
              'completed_at': utcnow().isoformat(), 'production_activation': False}
    write_new(Path(operation) / 'receipt.json', encoded(result))
    if transfer is not None:
        from provisioner.execution.restic_transfer import destination_receipt
        transfer_guard.check(transfer)
        write_new(Path(operation) / 'transfer-receipt.json',
                  encoded(destination_receipt(transfer, receipt, result)))
    return result


def execute(action, config, credentials, binary, operation, *, ca_file=None,
            receipt=None, expected=None, target=None, authority=None,
            transfer=None, transfer_guard=None, resource_control=None):
    """Execute one fixed owner operation, preserving a deterministic private path."""
    validate(config)
    require(action in {'backup', 'restore'}, 'Unknown backup operation')
    machine = Path('/etc/machine-id').read_text().strip()
    if action == 'backup':
        require(machine == config['machine_id'], 'Backup source machine identity changed')
        require(all(value is None for value in (receipt, expected, target, authority, transfer, transfer_guard)),
                'Backup cannot carry restore inputs')
    else:
        from provisioner.execution.run_files import current_window
        require(all(value is not None for value in (receipt, expected, target, authority)), 'Exact restore inputs required')
        current_window(authority)
        require(set(authority) == {'valid_from', 'valid_until', 'config_sha256', 'receipt_sha256',
                'machine_id', 'target', 'isolation_ref', 'change_ref'}
                and authority['config_sha256'] == digest(encoded(config))
                and authority['receipt_sha256'] == digest(encoded(receipt))
                and authority['machine_id'] == machine and machine != config['machine_id']
                and authority['target'] == str(Path(target).absolute())
                and all(re.fullmatch(r'[A-Za-z0-9:._/-]{3,200}', authority[k]) for k in ('isolation_ref', 'change_ref')),
                'Restore requires current authority for an independent isolated target')
        if transfer is not None or transfer_guard is not None:
            from provisioner.execution.restic_transfer import TransferGuard, validate as validate_transfer
            require(transfer is not None and isinstance(transfer_guard, TransferGuard),
                    'Cross-scope restore requires live trusted worker authority')
            validate_transfer(transfer, config, receipt, expected, target)
            transfer_guard.check(transfer)
        if resource_control is not None:
            from provisioner.migration.resources import LinuxTransferResources
            require(isinstance(resource_control, LinuxTransferResources),
                    'Trusted commissioned transfer resource controls required')
            resource_control.require_target(target)
            require(sum(row['size'] for row in expected['files'].values()) ==
                    resource_control.limits.expected_bytes,
                    'Transfer limits do not bind the captured useful byte count')
            resource_control.require_capacity(len(encoded(expected)))
    operation = new_directory(operation, ROOT)
    context = {'action': action, 'config_sha256': digest(encoded(config)),
        'receipt_sha256': digest(encoded(receipt)) if receipt is not None else None,
        'manifest_sha256': digest(encoded(expected)) if expected is not None else None,
        'authority_sha256': digest(encoded(authority)) if authority is not None else None,
        'machine_id': machine, 'target': str(Path(target).absolute()) if target is not None else None}
    if transfer is not None:
        context['transfer_manifest_sha256'] = digest(encoded(transfer))
        write_new(operation / 'transfer-manifest.json', encoded(transfer))
    if resource_control is not None:
        context['resource_control'] = resource_control.binding()
    write_new(operation / 'context.json', encoded(context))
    client = Restic(binary, config, credentials, operation, ca_file,
                    resource_control=resource_control) if resource_control is not None else \
             Restic(binary, config, credentials, operation, ca_file)
    if action == 'backup':
        result, _ = backup(config, client, operation)
    else:
        client.deadline = min(client.deadline, time.monotonic() +
            (timestamp(authority['valid_until']) - utcnow()).total_seconds())
        result = restore(config, receipt, expected, client, operation, target,
                         transfer=transfer, transfer_guard=transfer_guard)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['backup', 'restore'])
    for name in ('config', 'credentials', 'restic', 'output_root'):
        parser.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    for name in ('ca_bundle', 'receipt', 'manifest', 'target', 'restore_authority', 'transfer_manifest'):
        parser.add_argument('--' + name.replace('_', '-'), type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    try:
        config = load_private(args.config)
        validate(config)
        if not args.execute:
            print('{"status":"VALIDATED_NO_CONTACT"}')
            return 0
        operation = args.output_root / ('run-' + uuid.uuid4().hex)
        result = execute(args.action, config, load_private(args.credentials), args.restic, operation,
            ca_file=args.ca_bundle, receipt=load_private(args.receipt) if args.receipt else None,
            expected=load_private(args.manifest) if args.manifest else None, target=args.target,
            authority=load_private(args.restore_authority) if args.restore_authority else None,
            transfer=load_private(args.transfer_manifest) if args.transfer_manifest else None)
        print(json.dumps({'status': result['status'], 'operation': str(operation), 'production_activation': False}))
        return 0
    except OperatorError as exc:
        print(json.dumps({'status': 'STOPPED', 'reason': str(exc)}))
        return 2
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print('{"status":"STOPPED","reason":"Inspect private backup records; retained data was not deleted"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
