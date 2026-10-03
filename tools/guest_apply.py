#!/usr/bin/env python3
"""Execute one exactly reviewed guest bundle; interrupted outcomes remain held."""
import argparse
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''): sys.path.insert(0, str(ROOT))
from tools import guest_run as g
from tools.guest_inventory import timestamp
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import (current_window, digest, encoded, file_map, load_private, private_path,
    read_private, replace_private, require, sync_directory, utcnow, write_new)

ARTIFACTS = {'outputs.json', 'access.json', 'original-access.json', 'references.json', 'inventory.json',
             'credentials.json', 'runtime.json', 'handoff.json', 'known_hosts', 'ssh_key-cert.pub', 'ansible.cfg'}
ATTEMPT_FIELDS = {'format', 'status', 'operation_id', 'generation', 'scope', 'mode', 'source_commit',
                  'bundle_sha256', 'change_ref', 'started_at', 'targets', 'native_acceptance', 'production_activation'}


def exact(value, keys):
    require(isinstance(value, dict) and set(value) == set(keys), 'Unexpected guest execution fields')


def execution_deadline(access, approval):
    deadlines = [timestamp(approval['valid_until']), timestamp(access['valid_until'])]
    for target in access['targets'].values():
        backup = target.get('services', {}).get('backup')
        if backup and backup['enabled']: deadlines.append(timestamp(backup['config']['valid_until']))
    return min(deadlines)


def execution_budget(bundle, access, approval):
    current_window(approval)
    require((execution_deadline(access, approval) - utcnow()).total_seconds() >= bundle['max_seconds'],
            'Insufficient authority, guest access or enrollment lifetime for the entire execution')
    return bundle['max_seconds']


def validate_bundle(directory, approval, root=ROOT):
    directory = private_path(g.safe_path(directory), directory=True)
    require(not directory.resolve().is_relative_to(root.resolve()), 'Private bundle must be outside the repository')
    raw = read_private(directory/'bundle.json'); bundle = load_private(directory/'bundle.json')
    exact(bundle, {'format', 'status', 'operation_id', 'generation', 'source_commit', 'scope', 'mode',
                  'max_seconds', 'created_at', 'directory', 'artifacts', 'source_files', 'service_assets'})
    require(bundle['format'] == 'hosting-guest-bundle/1' and bundle['status'] == 'AWAITING_EXACT_GUEST_REVIEW'
            and bundle['directory'] == str(directory), 'Unknown or relocated guest bundle')
    g.identity(bundle['operation_id'])
    require(type(bundle['generation']) is int and bundle['generation'] > 0 and bundle['mode'] in {'check', 'configure'}
            and type(bundle['max_seconds']) is int and 30 <= bundle['max_seconds'] <= 3600, 'Invalid execution identity or bound')
    exact(approval, {'format', 'bundle_sha256', 'operation_id', 'generation', 'valid_from', 'valid_until', 'change_ref'})
    require(approval['format'] == 'hosting-guest-approval/1' and approval['bundle_sha256'] == digest(raw)
            and approval['operation_id'] == bundle['operation_id'] and type(approval['generation']) is int
            and approval['generation'] == bundle['generation'],
            'Authority does not match the exact guest bundle')
    current_window(approval)
    require(0 <= (utcnow() - timestamp(bundle['created_at'])).total_seconds() <= 3600, 'Guest bundle is stale or future-dated')
    source = g.verify(root)
    require(source['status'] == 'HASHES_MATCH' and source['commit'] == bundle['source_commit'], 'Exact clean source revision required')
    expected_source = {p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in g.source_paths(root)}
    require(bundle['source_files'] == expected_source == file_map(directory/'source'), 'Guest source copy differs from the reviewed revision')
    exact(bundle['artifacts'], ARTIFACTS)
    for name, expected in bundle['artifacts'].items():
        require(digest(read_private(directory/name)) == expected, 'Guest execution artifact changed')
    require(bundle['service_assets'] == file_map(directory/'assets'), 'Sealed service material changed')
    references = load_private(directory/'references.json'); exact(references, g.REFERENCES)
    require(all(isinstance(v, str) and g.re.fullmatch(r'[A-Za-z0-9:._/-]{3,200}', v) for v in references.values()),
            'Guest handoff reference changed')
    runtime = load_private(directory/'runtime.json')
    require(g.runtime_record(runtime['python_path'], runtime['ssh_path']) == runtime, 'Approved execution runtime changed')
    require(read_private(directory/'ansible.cfg') == g.configuration(directory, runtime['ssh_path']), 'Unreviewed Ansible configuration')
    original = load_private(directory/'original-access.json'); access = load_private(directory/'access.json')
    rewritten = deepcopy(original)
    expected_assets = {}
    for name, target in rewritten['targets'].items():
        for index, asset in enumerate(g.assets(target)):
            filename = name + '-' + str(index); expected_assets[filename] = asset['sha256']
            asset['path'] = str(directory/'assets'/filename)
    require(rewritten == access and expected_assets == bundle['service_assets'], 'Service paths or original guest intent changed')
    require(access['scope'] == bundle['scope'] and approval['change_ref'] == access['change_ref'], 'Guest scope or change authority differs')
    outputs = load_private(directory/'outputs.json')
    inventory, pins = g.build(outputs, access, str(directory/'known_hosts'))
    inventory['all']['vars']['hosting_native_enabled'] = True
    require(inventory == load_private(directory/'inventory.json') and pins.encode() == read_private(directory/'known_hosts'),
            'Guest inventory or connection bindings changed')
    hosts = inventory['all']['children']['hosting_guests']['hosts']
    g.gate(True, outputs, access, str(directory/'known_hosts'), list(hosts), hosts)
    credential = load_private(directory/'credentials.json'); exact(credential, {'ssh_key'})
    exact(credential['ssh_key'], {'path', 'sha256'})
    require(digest(read_private(credential['ssh_key']['path'])) == credential['ssh_key']['sha256'], 'SSH credential changed')
    execution_budget(bundle, access, approval)
    return bundle, access, runtime


@contextmanager
def scope_ledger(path, scope):
    parent = private_path(path, directory=True); directory = parent/digest(encoded(scope))
    try: directory.mkdir(mode=0o700); sync_directory(parent)
    except FileExistsError: private_path(directory, directory=True)
    lock = directory/'writer.lock'
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        private_path(lock); fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # An abrupt stop can occur after the immutable start but before head.json.
        # A renamed operation cannot bypass that incomplete write window.
        records = {}
        for started in directory.glob('*.started.json'):
            prior = load_private(started)
            exact(prior, ATTEMPT_FIELDS)
            require(prior['format'] == 'hosting-guest-attempt/1' and prior['scope'] == scope
                    and prior['status'] == 'STARTED_OUTCOME_UNKNOWN'
                    and prior['native_acceptance'] is False and prior['production_activation'] is False,
                    'Guest attempt scope or authority changed')
            g.identity(prior['operation_id'])
            require(isinstance(prior['targets'], list) and prior['targets']
                    and all(isinstance(name, str) for name in prior['targets'])
                    and prior['targets'] == sorted(set(prior['targets'])), 'Invalid recorded guest target set')
            for name in prior['targets']: g.identity(name)
            require(type(prior['generation']) is int and prior['generation'] > 0
                    and prior['mode'] in {'check', 'configure'}
                    and isinstance(prior['source_commit'], str) and g.re.fullmatch(r'[0-9a-f]{40}', prior['source_commit'])
                    and isinstance(prior['bundle_sha256'], str) and g.re.fullmatch(r'[0-9a-f]{64}', prior['bundle_sha256'])
                    and isinstance(prior['change_ref'], str) and prior['change_ref'], 'Invalid guest attempt identity')
            attempt = digest(encoded({k: prior[k] for k in ('operation_id', 'generation')}))
            require(started.name == attempt+'.started.json', 'Guest attempt filename differs from its identity')
            result = directory/(attempt+'.result.json')
            require(result.exists(), 'Guest attempt has no completed outcome')
            completed = load_private(result)
            exact(completed, ATTEMPT_FIELDS | {'completed_at', 'stats_sha256', 'hosts'})
            expected_status = ('CHECK_COMPLETED_REQUIRES_REVIEW' if prior['mode'] == 'check'
                               else 'CONFIGURED_REQUIRES_NATIVE_ACCEPTANCE')
            require(completed['status'] == expected_status
                    and all(completed[k] == prior[k] for k in ATTEMPT_FIELDS - {'status'})
                    and completed['native_acceptance'] is False and completed['production_activation'] is False,
                    'Guest attempt is uncertain or has inconsistent records')
            begin, end = timestamp(prior['started_at']), timestamp(completed['completed_at'])
            require(begin <= end <= utcnow(), 'Guest attempt completion time is invalid')
            raw = read_private(directory/(attempt+'.stats.json'))
            stats_sha, hosts = validate_stats(raw, set(prior['targets']), begin, end)
            require(stats_sha == completed['stats_sha256'] and hosts == completed['hosts'],
                    'Guest completion counters differ from retained evidence')
            records[attempt] = completed
        require({p.name for p in directory.glob('*.result.json')} == {k+'.result.json' for k in records}
                and {p.name for p in directory.glob('*.stats.json')} == {k+'.stats.json' for k in records},
                'Orphan guest completion evidence requires reconciliation')
        if (directory/'head.json').exists():
            previous = load_private(directory/'head.json')
            require(records and previous == max(records.values(), key=lambda row: timestamp(row['completed_at'])),
                    'Guest ledger head differs from the latest complete attempt')
        else:
            require(not records, 'Guest ledger head is missing; reconcile the interrupted publication')
        yield directory
    finally: os.close(descriptor)


def command(directory, bundle, runtime):
    argv = [runtime['python_path'], '-I', '-B', '-m', 'ansible.cli.playbook',
            '-i', str(directory/'inventory.json'), '--private-key', str(directory/'runtime/ssh_key'),
            str(directory/'source'/g.PLAYBOOK)]
    if bundle['mode'] == 'check': argv.append('--check')
    return argv


def run_process(argv, directory, env, timeout):
    with os.fdopen(os.open(directory/'ansible.log', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as log:
        process = subprocess.Popen(argv, cwd=directory/'source/ansible', env=env,
            stdin=subprocess.DEVNULL, stdout=log, stderr=log, umask=0o077, start_new_session=True)
        try:
            require(process.wait(timeout=timeout) == 0, 'Guest configuration failed; inspect private execution evidence')
        except BaseException:
            # Controller termination cannot cancel already dispatched remote work.
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait(timeout=5)
            raise


def validate_stats(raw, targets, started, completed):
    report = strict_loads(raw)
    exact(report, {'format', 'completed_at', 'hosts'})
    require(report['format'] == 'hosting-guest-stats/1' and started <= timestamp(report['completed_at']) <= completed,
            'Guest completion counters are stale or missing')
    require(targets and 'localhost' not in targets, 'Guest completion target set is empty or reserved')
    exact(report['hosts'], set(targets) | {'localhost'})
    for summary in report['hosts'].values():
        exact(summary, {'ok', 'failures', 'unreachable', 'changed', 'skipped', 'rescued', 'ignored'})
        require(all(type(v) is int and v >= 0 for v in summary.values()) and summary['ok'] > 0
                and summary['changed'] <= summary['ok']
                and not any(summary[k] for k in ('failures', 'unreachable', 'rescued', 'ignored')),
                'A guest failed, was skipped entirely or has unresolved results')
    return digest(raw), report['hosts']


def apply(args, root=ROOT):
    require(args.execute is True, 'Explicit authorized guest execution required')
    directory = private_path(args.bundle, directory=True); approval = load_private(args.approval)
    bundle, access, runtime = validate_bundle(directory, approval, root)
    require(not file_map(directory/'runtime'), 'Runtime output already exists; reconcile the prior attempt')
    attempt = digest(encoded({'operation_id': bundle['operation_id'], 'generation': bundle['generation']}))
    with scope_ledger(args.ledger, bundle['scope']) as ledger:
        require(not (ledger/(attempt+'.started.json')).exists(), 'Guest operation/generation was already attempted')
        execution_budget(bundle, access, approval)
        receipt = {'format': 'hosting-guest-attempt/1', 'status': 'STARTED_OUTCOME_UNKNOWN',
            'operation_id': bundle['operation_id'], 'generation': bundle['generation'], 'scope': bundle['scope'],
            'mode': bundle['mode'], 'source_commit': bundle['source_commit'], 'bundle_sha256': approval['bundle_sha256'],
            'change_ref': approval['change_ref'], 'started_at': utcnow().isoformat(),
            'targets': sorted(access['targets']),
            'native_acceptance': False, 'production_activation': False}
        write_new(ledger/(attempt+'.started.json'), encoded(receipt))
        replace_private(ledger/'head.json', encoded(receipt))
        try:
            write_new(directory/'approval.json', encoded(approval))
            credential = load_private(directory/'credentials.json')['ssh_key']; key = read_private(credential['path'])
            require(digest(key) == credential['sha256'], 'SSH key changed before execution')
            write_new(directory/'runtime/ssh_key', key)
            # Recheck after waiting for coordination, before the child can open SSH.
            validate_bundle(directory, approval, root)
            run_process(command(directory, bundle, runtime), directory, g.runtime_environment(directory),
                        execution_budget(bundle, access, approval))
            current_window(approval)
            require(execution_deadline(access, approval) > utcnow(), 'Guest access or enrollment expired during execution')
            stats_raw = read_private(directory/'runtime/stats.json')
            stats_sha, hosts = validate_stats(stats_raw, set(access['targets']), timestamp(receipt['started_at']), utcnow())
            write_new(ledger/(attempt+'.stats.json'), stats_raw)
            receipt.update(status='CHECK_COMPLETED_REQUIRES_REVIEW' if bundle['mode'] == 'check'
                           else 'CONFIGURED_REQUIRES_NATIVE_ACCEPTANCE', completed_at=utcnow().isoformat(),
                           stats_sha256=stats_sha, hosts=hosts)
        except BaseException:
            receipt.update(status='HOLD_RECONCILIATION_REQUIRED', stopped_at=utcnow().isoformat())
            write_new(ledger/(attempt+'.result.json'), encoded(receipt))
            replace_private(ledger/'head.json', encoded(receipt)); write_new(directory/'result.json', encoded(receipt))
            raise
        finally:
            (directory/'runtime/ssh_key').unlink(missing_ok=True); sync_directory(directory/'runtime')
        write_new(ledger/(attempt+'.result.json'), encoded(receipt))
        replace_private(ledger/'head.json', encoded(receipt)); write_new(directory/'result.json', encoded(receipt))
    return {'status': receipt['status'], 'native_acceptance': False, 'production_activation': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'approval', 'ledger'): parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    try:
        print(json.dumps(apply(parser.parse_args()))); return 0
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print(json.dumps({'status': 'STOPPED', 'native_acceptance': False,
                         'reason': 'Guest precondition failed or execution is uncertain; inspect private evidence'})); return 2


if __name__ == '__main__': raise SystemExit(main())
