#!/usr/bin/env python3
"""Apply one reviewed saved plan; persist uncertainty before any native mutation.

Only an already authorized operator may invoke this command. The private approval
record must come from that operator's controlled change system. Local locking is
not a distributed native task fence, and Terraform success is not service readiness.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.check_release import verify
from tools.compile_wsd import STATE
from tools.plan_review import review
from tools.run_files import (current_window, digest, encoded, file_map, load_private,
    private_path, read_private, replace_private, require, utcnow, write_new)
from tools.terraform_run import backend_settings, command, runtime_environment, select_scope


def validate_bundle(operation, approval, binary, root=ROOT):
    operation = private_path(operation, directory=True)
    require(not operation.resolve().is_relative_to(root.resolve()), 'Private operation required')
    bundle_bytes = read_private(operation / 'bundle.json')
    bundle = load_private(operation / 'bundle.json')
    require(bundle['format'] == 'hosting-terraform-bundle/1'
            and bundle['status'] == 'AWAITING_EXACT_PLAN_REVIEW', 'Unsupported execution bundle')
    require(set(approval) == {'format', 'bundle_sha256', 'review_sha256', 'operation_id', 'generation',
            'valid_from', 'valid_until', 'change_ref'}, 'Invalid apply approval fields')
    require(approval['format'] == 'hosting-terraform-approval/1'
            and approval['bundle_sha256'] == digest(bundle_bytes)
            and approval['operation_id'] == bundle['operation_id']
            and approval['generation'] == bundle['generation'], 'Approval does not match the exact bundle')
    require(isinstance(approval['change_ref'], str) and approval['change_ref'].strip(), 'External apply authority required')
    current_window(approval)
    created = datetime.fromisoformat(bundle['created_at'])
    require(created.tzinfo is not None and 0 <= (utcnow() - created).total_seconds() <= 3600,
            'Plan is stale or future-dated; prepare and review a new plan')
    source = verify(root)
    require(source['status'] == 'HASHES_MATCH' and source['commit'] == bundle['source_commit'],
            'Execute from the exact clean source revision used to prepare the plan')
    require(digest(Path(binary).read_bytes()) == bundle['terraform_sha256'], 'Terraform executable changed')
    require(file_map(operation / 'source') == bundle['source_files'], 'Execution source/runtime changed')
    for name, expected in bundle['artifacts'].items():
        require(Path(name).name == name, 'Unsafe bundle artifact name')
        require(digest(read_private(operation / name)) == expected, 'Execution artifact changed')
    entry, scope, state_key = select_scope(root, bundle['catalog_id'], load_private(operation / 'inputs.json'))
    require((entry['root'], scope, state_key) == (bundle['root'], bundle['scope'], bundle['state_key']),
            'Bundle scope differs from its inputs')
    backend_settings(load_private(operation / 'backend.json'), state_key)
    result = review(load_private(operation / 'plan.json'), load_private(operation / 'references.json'))
    require(result['status'] != 'BLOCKED' and result == load_private(operation / 'review.json'),
            'Plan review is blocked or changed')
    require(approval['review_sha256'] == digest(encoded(result)), 'All exact review findings must be reviewed')
    return bundle


@contextmanager
def scope_ledger(ledger, backend_address):
    ledger = private_path(ledger, directory=True)
    scope = ledger / digest(backend_address.encode())
    try:
        scope.mkdir(mode=0o700)
    except FileExistsError:
        private_path(scope, directory=True)
    lock = scope / 'writer.lock'
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        private_path(lock)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (scope / 'head.json').exists():
            previous = load_private(scope / 'head.json')
            require(previous['status'] == 'APPLIED_REQUIRES_NATIVE_ACCEPTANCE',
                    'Previous native outcome is uncertain; independent reconciliation is required')
        yield scope
    finally:
        os.close(fd)


def verify_outputs(outputs, bundle, inputs):
    require(outputs.get('scope', {}).get('value') == bundle['scope'], 'Native output scope differs')
    require(outputs.get('delivery_state', {}).get('value') == STATE, 'Unexpected delivery state')
    members = outputs.get('members', {}).get('value')
    require(isinstance(members, dict) and set(members) == set(inputs['members']), 'Output member identities differ')
    require(all(isinstance(v, dict) and v.get('delivery_state') == STATE for v in members.values()),
            'Unexpected member delivery state')


def apply(args, root=ROOT):
    require(args.execute_approved_change is True, 'Explicit native mutation opt-in required')
    operation = private_path(args.bundle, directory=True)
    approval = load_private(args.approval)
    binary = Path(args.terraform).resolve(strict=True)
    bundle = validate_bundle(operation, approval, binary, root)
    credentials = load_private(operation / 'environment.json')
    directory = operation / 'source' / bundle['root']
    env = runtime_environment(operation, credentials, bundle['scope']['platform'], directory)
    backend = load_private(operation / 'backend.json')
    identity = digest(encoded({'operation': bundle['operation_id'], 'generation': bundle['generation']}))
    with scope_ledger(args.ledger, backend['address']) as ledger:
        # Attempt identity survives a copied bundle or a new coordinator process.
        require(not (ledger / (identity + '.started.json')).exists(), 'This operation/generation was already attempted')
        current_window(approval)
        receipt = {'format': 'hosting-terraform-attempt/1', 'status': 'STARTED_OUTCOME_UNKNOWN',
                   'bundle_sha256': approval['bundle_sha256'], 'scope': bundle['scope'],
                   'operation_id': bundle['operation_id'], 'generation': bundle['generation'],
                   'change_ref': approval['change_ref'], 'started_at': utcnow().isoformat()}
        # Persist uncertainty before invoking a process that can mutate infrastructure.
        write_new(ledger / (identity + '.started.json'), encoded(receipt))
        replace_private(ledger / 'head.json', encoded(receipt))
        write_new(operation / 'approval.json', encoded(approval))
        try:
            remaining = (datetime.fromisoformat(approval['valid_until'].replace('Z', '+00:00')) - utcnow()).total_seconds()
            require(remaining > 0, 'Approval expired before mutation')
            command(binary, directory, ['apply', '-input=false', '-no-color', '-lock=true', '-lock-timeout=60s',
                    str(operation / 'saved.tfplan')], env, operation / 'apply.log', timeout=min(remaining, 3600))
            # Query outputs only; never invoke a second apply to recover missing output.
            current_window(approval)
            remaining = (datetime.fromisoformat(approval['valid_until'].replace('Z', '+00:00')) - utcnow()).total_seconds()
            command(binary, directory, ['output', '-json'], env, operation / 'outputs.json', timeout=remaining)
            verify_outputs(load_private(operation / 'outputs.json'), bundle, load_private(operation / 'inputs.json'))
            receipt.update(status='APPLIED_REQUIRES_NATIVE_ACCEPTANCE', completed_at=utcnow().isoformat(),
                           outputs_sha256=digest(read_private(operation / 'outputs.json')))
        except BaseException:
            # Timeout/interrupt/failed apply may have created resources or late tasks.
            receipt.update(status='HOLD_RECONCILIATION_REQUIRED', stopped_at=utcnow().isoformat())
            write_new(ledger / (identity + '.result.json'), encoded(receipt))
            replace_private(ledger / 'head.json', encoded(receipt))
            write_new(operation / 'result.json', encoded(receipt))
            raise
        write_new(ledger / (identity + '.result.json'), encoded(receipt))
        replace_private(ledger / 'head.json', encoded(receipt))
        write_new(operation / 'result.json', encoded(receipt))
    return {'status': receipt['status'], 'native_acceptance': False, 'production_activation': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'approval', 'terraform', 'ledger'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--execute-approved-change', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(apply(args)))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print(json.dumps({'status': 'STOPPED', 'native_acceptance': False,
                          'reason': 'Precondition failed or native result is uncertain; inspect the private ledger'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
