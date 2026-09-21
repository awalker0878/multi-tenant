#!/usr/bin/env python3
"""Validate dependency-safe service retirement evidence without performing native deletion."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''):
    sys.path.insert(0, str(ROOT))

from tools import readback_core as c
from tools.run_files import encoded, load_private, require, write_new

ACTION_ORDER = {
    'withdraw_exposure': 10,
    'revoke_service_access': 20,
    'protect_retained_data': 30,
    'cleanup_native_resources': 40,
    'withdraw_dns': 50,
    'retire_ipam': 60,
    'release_capacity': 70,
    'close_service': 80,
}
RESOURCE_KINDS = {
    'edge', 'identity', 'monitoring', 'backup', 'state',
    'compute', 'storage', 'network', 'dns', 'ipam', 'capacity',
}
DISPOSITIONS = {'remove', 'deprecate', 'retain', 'transfer'}


def _text_or_none(value, name):
    require(value is None or (isinstance(value, str) and value.strip()), f'Invalid {name}')


def validate_plan(plan):
    c.exact_keys(plan, {
        'format', 'source_commit', 'operation_id', 'generation', 'scope',
        'resources', 'retained_data', 'actions'
    })
    require(
        plan['format'] == 'hosting-retirement/1'
        and isinstance(plan['source_commit'], str)
        and re.fullmatch(r'[0-9a-f]{40}', plan['source_commit']),
        'Exact retirement source required',
    )
    c.identifier(plan['operation_id'])
    require(type(plan['generation']) is int and plan['generation'] > 0, 'Positive retirement generation required')
    c.exact_keys(plan['scope'], {'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key'})
    for value in plan['scope'].values():
        c.identifier(value)
    require(plan['scope']['platform'] in {'nutanix', 'vmware', 'openstack'}, 'Unknown retirement platform')

    require(isinstance(plan['resources'], list) and plan['resources'], 'Retirement resources required')
    resources = {}
    for row in plan['resources']:
        c.exact_keys(row, {'id', 'kind', 'owner', 'native_id', 'disposition', 'shared', 'retained_data_refs'})
        c.identifier(row['id'])
        require(row['id'] not in resources and row['kind'] in RESOURCE_KINDS, 'Duplicate or unsupported retirement resource')
        c.text(row['owner'])
        _text_or_none(row['native_id'], 'native resource identity')
        require(row['disposition'] in DISPOSITIONS and type(row['shared']) is bool, 'Invalid retirement disposition')
        require(isinstance(row['retained_data_refs'], list)
                and len(row['retained_data_refs']) == len(set(row['retained_data_refs'])), 'Invalid retained-data references')
        if row['shared']:
            require(row['disposition'] != 'remove', 'Shared resources cannot be blindly removed')
        if row['disposition'] in {'remove', 'deprecate'}:
            require(row['native_id'] is not None, 'Removal/deprecation requires exact native identity')
        resources[row['id']] = row

    require(isinstance(plan['retained_data'], list), 'Retained-data ledger must be a list')
    retained = {}
    for row in plan['retained_data']:
        c.exact_keys(row, {
            'id', 'owner', 'location_ref', 'key_ref', 'hold_ref',
            'disposition_ref', 'final_destruction_authority_ref'
        })
        c.identifier(row['id'])
        require(row['id'] not in retained, 'Duplicate retained-data identity')
        for key in ('owner', 'location_ref', 'key_ref', 'disposition_ref', 'final_destruction_authority_ref'):
            c.text(row[key])
        _text_or_none(row['hold_ref'], 'retention hold reference')
        retained[row['id']] = row

    for resource in resources.values():
        require(set(resource['retained_data_refs']) <= retained.keys(), 'Resource references unknown retained data')
        if resource['disposition'] in {'retain', 'transfer'}:
            require(resource['retained_data_refs'], 'Retained/transferred resource requires explicit retained-data custody')

    require(isinstance(plan['actions'], list) and plan['actions'], 'Retirement action graph required')
    actions = {}
    seen = set()
    last_rank = 0
    coverage = {key: set() for key in resources}
    for action in plan['actions']:
        c.exact_keys(action, {'id', 'type', 'needs', 'resources'})
        c.identifier(action['id'])
        require(action['id'] not in seen and action['type'] in ACTION_ORDER, 'Duplicate or unsupported retirement action')
        rank = ACTION_ORDER[action['type']]
        require(rank >= last_rank, 'Retirement actions must follow the safety order')
        last_rank = rank
        require(
            isinstance(action['needs'], list)
            and len(action['needs']) == len(set(action['needs']))
            and set(action['needs']) <= seen,
            'Retirement action dependencies must be topologically ordered',
        )
        require(isinstance(action['resources'], list)
                and action['resources']
                and len(action['resources']) == len(set(action['resources']))
                and set(action['resources']) <= resources.keys(), 'Retirement action resources are invalid')
        if seen:
            require(action['needs'], 'Every later retirement action must retain a predecessor dependency')
        for resource_id in action['resources']:
            coverage[resource_id].add(action['type'])
        actions[action['id']] = action
        seen.add(action['id'])

    by_type = {}
    for action in plan['actions']:
        require(action['type'] not in by_type, 'One retirement action per action type is required')
        by_type[action['type']] = action

    if retained:
        require('protect_retained_data' in by_type, 'Retained data must be protected before destructive cleanup')
        destructive = [a for a in plan['actions'] if a['type'] in {'cleanup_native_resources', 'retire_ipam', 'release_capacity'}]
        for action in destructive:
            require(by_type['protect_retained_data']['id'] in ancestors(action, actions),
                    'Destructive retirement must depend on retained-data protection')

    if any(r['kind'] == 'dns' and r['disposition'] in {'remove', 'deprecate'} for r in resources.values()):
        require('withdraw_dns' in by_type, 'DNS-owned resources require explicit withdrawal')
    if any(r['kind'] == 'ipam' and r['disposition'] in {'remove', 'deprecate'} for r in resources.values()):
        require('retire_ipam' in by_type, 'IPAM-owned resources require explicit retirement')
        if 'withdraw_dns' in by_type:
            require(by_type['withdraw_dns']['id'] in ancestors(by_type['retire_ipam'], actions),
                    'IPAM retirement must depend on DNS withdrawal')
    if any(r['kind'] == 'capacity' and r['disposition'] in {'remove', 'deprecate'} for r in resources.values()):
        require('release_capacity' in by_type, 'Capacity ownership requires explicit release')
        release_ancestors = ancestors(by_type['release_capacity'], actions)
        for required in ('cleanup_native_resources', 'withdraw_dns', 'retire_ipam'):
            if required in by_type:
                require(by_type[required]['id'] in release_ancestors,
                        'Capacity release must follow all applicable cleanup owners')

    for resource_id, resource in resources.items():
        if resource['disposition'] in {'remove', 'deprecate'}:
            allowed = {
                'edge': {'withdraw_exposure', 'cleanup_native_resources'},
                'identity': {'revoke_service_access', 'cleanup_native_resources'},
                'monitoring': {'revoke_service_access', 'cleanup_native_resources'},
                'backup': {'protect_retained_data', 'cleanup_native_resources'},
                'state': {'protect_retained_data', 'cleanup_native_resources'},
                'compute': {'cleanup_native_resources'},
                'storage': {'protect_retained_data', 'cleanup_native_resources'},
                'network': {'withdraw_exposure', 'cleanup_native_resources'},
                'dns': {'withdraw_dns'},
                'ipam': {'retire_ipam'},
                'capacity': {'release_capacity'},
            }[resource['kind']]
            require(coverage[resource_id] & allowed, 'Destructive/deprecating resource has no accountable retirement owner action')

    require(plan['actions'][-1]['type'] == 'close_service', 'Retirement graph must end with explicit service closure')
    require(set(actions) - {plan['actions'][-1]['id']} <= ancestors(plan['actions'][-1], actions),
            'Service closure must depend on every prior retirement action')
    return resources, retained, actions


def ancestors(action, actions):
    found = set()
    pending = list(action['needs'])
    while pending:
        identity = pending.pop()
        if identity in found:
            continue
        found.add(identity)
        pending.extend(actions[identity]['needs'])
    return found


def validate_evidence(plan, evidence):
    _, _, actions = validate_plan(plan)
    c.exact_keys(evidence, {'format', 'plan_sha256', 'receipts'})
    require(evidence['format'] == 'hosting-retirement-evidence/1'
            and evidence['plan_sha256'] == c.digest(plan), 'Retirement evidence belongs to another plan')
    require(isinstance(evidence['receipts'], list), 'Retirement receipts must be a list')
    receipts = {}
    for row in evidence['receipts']:
        c.exact_keys(row, {'action_id', 'status', 'resource_ids', 'observed_at', 'evidence_ref'})
        require(row['action_id'] in actions and row['action_id'] not in receipts, 'Unknown or duplicate retirement receipt')
        action = actions[row['action_id']]
        require(row['status'] == 'COMPLETED', 'Only completed owner evidence advances retirement')
        require(row['resource_ids'] == sorted(action['resources']), 'Retirement receipt resource set differs')
        c.timestamp(row['observed_at'])
        c.text(row['evidence_ref'])
        require(set(action['needs']) <= receipts.keys(), 'Retirement evidence is out of dependency order')
        receipts[row['action_id']] = row
    return actions, receipts


def evaluate(plan, evidence):
    actions, receipts = validate_evidence(plan, evidence)
    ordered = plan['actions']
    next_action = next((a for a in ordered if a['id'] not in receipts), None)
    result = {
        'format': 'hosting-retirement-review/1',
        'plan_sha256': c.digest(plan),
        'scope': plan['scope'],
        'completed_actions': [a['id'] for a in ordered if a['id'] in receipts],
        'remaining_actions': [a['id'] for a in ordered if a['id'] not in receipts],
        'next_action': next_action['id'] if next_action else None,
        'native_acceptance': False,
        'production_activation': False,
    }
    if next_action is None:
        result['status'] = 'RETIREMENT_EVIDENCE_COMPLETE_REQUIRES_ACCEPTANCE'
    else:
        result['status'] = 'RETIREMENT_HELD_PENDING_OWNER_EVIDENCE'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(load_private(args.plan), load_private(args.evidence))
        data = encoded(result)
        if args.output:
            write_new(args.output, data)
        else:
            print(data.decode().rstrip())
        return 0
    except (ValueError, OSError, KeyError, TypeError):
        print(json.dumps({
            'status': 'HOLD_RETIREMENT_RECONCILIATION',
            'native_acceptance': False,
            'production_activation': False,
        }))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
