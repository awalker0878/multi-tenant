#!/usr/bin/env python3
"""Review brownfield ownership transfer and emit exact non-mutating import handoffs."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''):
    sys.path.insert(0, str(ROOT))

from tools import readback_core as c
from tools.check_release import verify
from tools.run_files import encoded, load_private, require, write_new

MODES = {'retain_existing', 'handover_to_terraform'}
METHODS = {'observe_only', 'terraform_import'}
DELTAS = {'no-op', 'update'}
CLASSES = {'routine', 'connectivity_security', 'shared_foundation', 'profile_trust'}


def _sha(value, name):
    require(isinstance(value, str) and c.HEX.fullmatch(value), f'Invalid {name}')


def _text_or_none(value, name):
    require(value is None or (isinstance(value, str) and value.strip()), f'Invalid {name}')


def validate_plan(plan):
    c.exact_keys(plan, {
        'format', 'source_commit', 'operation_id', 'generation', 'scope',
        'state', 'resources'
    })
    require(
        plan['format'] == 'hosting-adoption/1'
        and isinstance(plan['source_commit'], str)
        and re.fullmatch(r'[0-9a-f]{40}', plan['source_commit']),
        'Exact adoption source required',
    )
    c.identifier(plan['operation_id'])
    require(type(plan['generation']) is int and plan['generation'] > 0, 'Positive adoption generation required')
    c.exact_keys(plan['scope'], {'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key'})
    for value in plan['scope'].values():
        c.identifier(value)
    require(plan['scope']['platform'] in {'nutanix', 'vmware', 'openstack'}, 'Unknown adoption platform')

    c.exact_keys(plan['state'], {'backend_sha256', 'state_key', 'backup_ref', 'lock_ref'})
    _sha(plan['state']['backend_sha256'], 'backend digest')
    for key in ('state_key', 'backup_ref', 'lock_ref'):
        c.text(plan['state'][key])

    require(isinstance(plan['resources'], list) and plan['resources'], 'Adoption resources required')
    addresses = set()
    native_ids = set()
    resources = {}
    for row in plan['resources']:
        c.exact_keys(row, {
            'address', 'type', 'native_id', 'current_owner', 'target_owner',
            'ownership_mode', 'shared', 'import_method', 'import_id',
            'current_sha256', 'desired_sha256', 'delta', 'change_class',
            'allowed_update_fields', 'discovery_ref', 'recovery_ref',
            'old_writer_fence_ref'
        })
        c.text(row['address'])
        require(row['address'] not in addresses, 'Duplicate Terraform/native ownership address')
        c.identifier(row['type'])
        c.text(row['native_id'])
        require(row['native_id'] not in native_ids, 'Duplicate native identity in adoption scope')
        for key in ('current_owner', 'target_owner', 'discovery_ref', 'recovery_ref'):
            c.text(row[key])
        require(row['ownership_mode'] in MODES and type(row['shared']) is bool, 'Invalid adoption ownership mode')
        require(row['import_method'] in METHODS and row['delta'] in DELTAS
                and row['change_class'] in CLASSES, 'Invalid adoption method or change classification')
        _sha(row['current_sha256'], 'current configuration digest')
        _sha(row['desired_sha256'], 'desired configuration digest')
        require(isinstance(row['allowed_update_fields'], list)
                and len(row['allowed_update_fields']) == len(set(row['allowed_update_fields'])), 'Invalid allowed update fields')
        for field in row['allowed_update_fields']:
            c.text(field)
        _text_or_none(row['import_id'], 'import identity')
        _text_or_none(row['old_writer_fence_ref'], 'old-writer fence reference')

        if row['delta'] == 'no-op':
            require(row['current_sha256'] == row['desired_sha256']
                    and not row['allowed_update_fields'], 'No-op adoption cannot hide desired configuration drift')
        else:
            require(row['current_sha256'] != row['desired_sha256']
                    and row['allowed_update_fields'], 'Explicit update requires changed configuration and bounded fields')

        if row['shared']:
            require(row['ownership_mode'] == 'retain_existing'
                    and row['import_method'] == 'observe_only'
                    and row['target_owner'] == row['current_owner']
                    and row['import_id'] is None
                    and row['delta'] == 'no-op',
                    'Shared resources remain with their existing owner during adoption')

        if row['ownership_mode'] == 'retain_existing':
            require(row['target_owner'] == row['current_owner']
                    and row['import_method'] == 'observe_only'
                    and row['import_id'] is None
                    and row['old_writer_fence_ref'] is None,
                    'Retained ownership cannot create a second writer')
        else:
            require(not row['shared']
                    and row['current_owner'] != 'terraform'
                    and row['target_owner'] == 'terraform'
                    and row['import_method'] == 'terraform_import'
                    and row['import_id'] is not None
                    and row['old_writer_fence_ref'] is not None,
                    'Terraform handover requires exact import identity and old-writer fencing')

        addresses.add(row['address'])
        native_ids.add(row['native_id'])
        resources[row['address']] = row
    return resources


def validate_evidence(plan, evidence):
    resources = validate_plan(plan)
    c.exact_keys(evidence, {'format', 'plan_sha256', 'state', 'resources'})
    require(evidence['format'] == 'hosting-adoption-evidence/1'
            and evidence['plan_sha256'] == c.digest(plan), 'Adoption evidence belongs to another plan')

    c.exact_keys(evidence['state'], {
        'backend_sha256', 'state_key', 'backup_verified', 'lock_verified',
        'observed_at', 'evidence_ref'
    })
    require(evidence['state']['backend_sha256'] == plan['state']['backend_sha256']
            and evidence['state']['state_key'] == plan['state']['state_key'],
            'Adoption state evidence differs from reviewed backend')
    require(evidence['state']['backup_verified'] is True
            and evidence['state']['lock_verified'] is True,
            'Protected state backup and writer lock are required before adoption')
    c.timestamp(evidence['state']['observed_at'])
    c.text(evidence['state']['evidence_ref'])

    require(isinstance(evidence['resources'], list)
            and len(evidence['resources']) == len(resources), 'Complete adoption resource evidence required')
    observed = {}
    for row in evidence['resources']:
        c.exact_keys(row, {
            'address', 'native_id', 'observed_sha256', 'current_owner',
            'old_writer_active', 'recovery_verified', 'import_supported',
            'plan_actions', 'replacement', 'delete', 'exposure_change',
            'observed_at', 'evidence_ref'
        })
        require(row['address'] in resources and row['address'] not in observed, 'Unknown or duplicate adoption evidence')
        expected = resources[row['address']]
        require(row['native_id'] == expected['native_id']
                and row['current_owner'] == expected['current_owner']
                and row['observed_sha256'] == expected['current_sha256'],
                'Native identity, ownership or configuration changed during adoption review')
        require(type(row['old_writer_active']) is bool
                and row['recovery_verified'] is True
                and row['import_supported'] is True,
                'Recovery and supported adoption mechanism must be verified')
        require(row['plan_actions'] == ([expected['delta']] if expected['delta'] == 'no-op' else ['update']),
                'Adoption plan action differs from the reviewed delta')
        require(row['replacement'] is False
                and row['delete'] is False
                and row['exposure_change'] is False,
                'Adoption cannot authorize replacement, deletion or new exposure')
        if expected['ownership_mode'] == 'handover_to_terraform':
            require(row['old_writer_active'] is False, 'Old writer remains active during Terraform handover')
        else:
            require(row['old_writer_active'] is True, 'Retained owner must remain the active writer')
        c.timestamp(row['observed_at'])
        c.text(row['evidence_ref'])
        observed[row['address']] = row
    return resources, observed


def evaluate(plan, evidence):
    resources, observed = validate_evidence(plan, evidence)
    imports = []
    retained = []
    deltas = []
    for address in sorted(resources):
        row = resources[address]
        if row['ownership_mode'] == 'handover_to_terraform':
            imports.append({
                'address': row['address'],
                'type': row['type'],
                'native_id': row['native_id'],
                'import_id': row['import_id'],
                'current_sha256': row['current_sha256'],
                'desired_sha256': row['desired_sha256'],
                'old_writer_fence_ref': row['old_writer_fence_ref'],
                'discovery_ref': row['discovery_ref'],
                'recovery_ref': row['recovery_ref'],
                'evidence_ref': observed[address]['evidence_ref'],
            })
            if row['delta'] == 'update':
                deltas.append({
                    'address': row['address'],
                    'change_class': row['change_class'],
                    'allowed_update_fields': sorted(row['allowed_update_fields']),
                })
        else:
            retained.append({
                'address': row['address'],
                'native_id': row['native_id'],
                'owner': row['current_owner'],
                'evidence_ref': observed[address]['evidence_ref'],
            })
    result = {
        'format': 'hosting-adoption-review/1',
        'status': 'ADOPTION_READY_FOR_EXPLICIT_IMPORT_AND_PLAN_REVIEW',
        'plan_sha256': c.digest(plan),
        'scope': plan['scope'],
        'state': {
            'backend_sha256': plan['state']['backend_sha256'],
            'state_key': plan['state']['state_key'],
            'backup_ref': plan['state']['backup_ref'],
            'lock_ref': plan['state']['lock_ref'],
            'evidence_ref': evidence['state']['evidence_ref'],
        },
        'imports': imports,
        'retained_owners': retained,
        'explicit_deltas': deltas,
        'may_import_automatically': False,
        'may_apply': False,
        'may_replace': False,
        'may_delete': False,
        'native_acceptance': False,
        'production_activation': False,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        plan = load_private(args.plan)
        source = verify(ROOT)
        require(source['status'] == 'HASHES_MATCH' and source['commit'] == plan['source_commit'],
                'Exact clean adoption source required')
        result = evaluate(plan, load_private(args.evidence))
        data = encoded(result)
        if args.output:
            write_new(args.output, data)
        else:
            print(data.decode().rstrip())
        return 0
    except (ValueError, OSError, KeyError, TypeError):
        print(json.dumps({
            'status': 'HOLD_ADOPTION_RECONCILIATION',
            'may_import_automatically': False,
            'may_apply': False,
            'native_acceptance': False,
            'production_activation': False,
        }))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
