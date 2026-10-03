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

from provisioner.execution.source_integrity import verify
from provisioner.compiler.wsd import STATE
from tools.plan_review import review
from tools import readback_core as c
from tools.run_files import (current_window, digest, encoded, file_map, load_private,
    private_path, read_private, replace_private, require, sync_directory, utcnow, write_new, OperatorError)
from tools.terraform_run import backend_settings, command, runtime_environment, select_scope

ATTEMPT_FIELDS = {'format','status','bundle_sha256','scope','operation_id','generation','change_ref','started_at'}


def completed_history(scope, expected_scope=None):
    """Every immutable attempt must complete before any new operation can start."""
    records={}
    for path in scope.glob('*.started.json'):
        started=load_private(path); c.exact_keys(started,ATTEMPT_FIELDS)
        require(started['format']=='hosting-terraform-attempt/1' and started['status']=='STARTED_OUTCOME_UNKNOWN',
                'Unknown Terraform attempt record')
        c.identifier(started['operation_id']); c.text(started['change_ref'])
        require(type(started['generation']) is int and started['generation']>0
                and isinstance(started['bundle_sha256'],str) and c.HEX.fullmatch(started['bundle_sha256']),
                'Invalid Terraform attempt identity')
        c.exact_keys(started['scope'],{'environment_key','site_key','platform','tenant_key','wsd_key','phase'})
        for value in started['scope'].values(): c.identifier(value)
        require(expected_scope is None or started['scope']==expected_scope,'Terraform ledger belongs to another scope')
        identity=digest(encoded({'operation':started['operation_id'],'generation':started['generation']}))
        require(path.name==identity+'.started.json','Terraform attempt filename differs')
        completed_path=scope/(identity+'.result.json')
        require(completed_path.exists(),'Terraform attempt has no completed outcome; reconcile the durable start')
        completed=load_private(completed_path)
        c.exact_keys(completed,ATTEMPT_FIELDS|{'completed_at','outputs_sha256'})
        require(completed['status']=='APPLIED_REQUIRES_NATIVE_ACCEPTANCE'
                and not c.differences({key:completed[key] for key in ATTEMPT_FIELDS-{'status'}},
                                      {key:started[key] for key in ATTEMPT_FIELDS-{'status'}}),
                'Terraform outcome is uncertain or its completion identity changed')
        require(isinstance(completed['outputs_sha256'],str) and c.HEX.fullmatch(completed['outputs_sha256']),
                'Terraform output digest required')
        require(c.timestamp(started['started_at'])<=c.timestamp(completed['completed_at'])<=utcnow(),
                'Invalid Terraform completion chronology')
        records[identity]=completed
    require({p.name for p in scope.glob('*.result.json')}=={key+'.result.json' for key in records},
            'Orphan Terraform completion evidence requires reconciliation')
    ordered=sorted(records.values(),key=lambda row:c.timestamp(row['started_at']))
    for previous,current in zip(ordered,ordered[1:]):
        require(c.timestamp(previous['completed_at'])<=c.timestamp(current['started_at']),
                'Overlapping Terraform execution history')
    if (scope/'head.json').exists():
        require(ordered and c.digest(load_private(scope/'head.json'))==c.digest(ordered[-1]),
                'Terraform head differs from the latest complete attempt')
    else:
        require(not records,'Terraform completion head is missing; reconcile publication')
    return records


def validate_bundle(operation, approval, binary, root=ROOT):
    operation = private_path(operation, directory=True)
    require(not operation.resolve().is_relative_to(root.resolve()), 'Private operation required')
    bundle_bytes = read_private(operation / 'bundle.json')
    bundle = load_private(operation / 'bundle.json')
    require(bundle['format'] == 'hosting-terraform-bundle/1'
            and bundle['status'] == 'AWAITING_EXACT_PLAN_REVIEW', 'Unsupported execution bundle')
    required = {'inputs.json', 'backend.json', 'backend.hcl', 'environment.json', 'contact.json',
                'references.json', 'terraform.rc', 'version.json', 'saved.tfplan', 'plan.json', 'review.json'}
    require(isinstance(bundle['artifacts'], dict) and required <= set(bundle['artifacts'])
            and not set(bundle['artifacts']) - required - {'ca.pem', 'transition.json'}, 'Incomplete or unknown bundle artifacts')
    require(bool(bundle['source_files']), 'Execution source manifest is empty')
    require(set(approval) == {'format', 'bundle_sha256', 'review_sha256', 'operation_id', 'generation',
            'valid_from', 'valid_until', 'change_ref'}, 'Invalid apply approval fields')
    require(approval['format'] == 'hosting-terraform-approval/1'
            and approval['bundle_sha256'] == digest(bundle_bytes)
            and approval['operation_id'] == bundle['operation_id']
            and type(approval['generation']) is int and type(bundle['generation']) is int
            and bundle['generation']>0 and approval['generation'] == bundle['generation'], 'Approval does not match the exact bundle')
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
    transition = load_private(operation / 'transition.json') if 'transition.json' in bundle['artifacts'] else None
    if transition is not None:
        from tools.lifecycle_transition import validate as validate_transition
        validate_transition(transition, scope, read_private(operation / 'inputs.json'))
    result = review(load_private(operation / 'plan.json'), load_private(operation / 'references.json'), transition)
    require(result['status'] != 'BLOCKED' and result == load_private(operation / 'review.json'),
            'Plan review is blocked or changed')
    require(approval['review_sha256'] == digest(encoded(result)), 'All exact review findings must be reviewed')
    return bundle


@contextmanager
def scope_ledger(ledger, backend_address, expected_scope=None):
    ledger = private_path(ledger, directory=True)
    scope = ledger / digest(backend_address.encode())
    try:
        scope.mkdir(mode=0o700)
        sync_directory(ledger)
    except FileExistsError:
        private_path(scope, directory=True)
    lock = scope / 'writer.lock'
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        private_path(lock)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        completed_history(scope,expected_scope)
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
    if bundle['scope']['platform'] in {'openstack', 'nutanix', 'vmware'}:
        for name, member in members.items():
            # Legacy prepared receipts remain readable; bootstrap must be explicit.
            require(member.get('lifecycle_stage', 'prepared') == inputs['members'][name].get('lifecycle_stage', 'prepared'),
                    'Native output lifecycle differs from the exact plan inputs')


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
    with scope_ledger(args.ledger, backend['address'],bundle['scope']) as ledger:
        # Attempt identity survives a copied bundle or a new coordinator process.
        require(not (ledger / (identity + '.started.json')).exists(), 'This operation/generation was already attempted')
        current_window(approval)
        if 'transition.json' in bundle['artifacts']:
            current_window(load_private(operation / 'transition.json'))
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
            if 'transition.json' in bundle['artifacts']:
                deadline = load_private(operation / 'transition.json')['valid_until']
                remaining = min(remaining, (datetime.fromisoformat(deadline.replace('Z', '+00:00')) - utcnow()).total_seconds())
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
    except OperatorError as exc:
        print(json.dumps({'status': 'STOPPED', 'reason': str(exc), 'native_acceptance': False}))
        return 2
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print(json.dumps({'status': 'STOPPED', 'native_acceptance': False,
                          'reason': 'Precondition failed or native result is uncertain; inspect the private ledger'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
