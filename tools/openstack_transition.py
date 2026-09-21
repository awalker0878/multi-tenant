#!/usr/bin/env python3
"""Bind a restricted OpenStack lifecycle change to a successful prior execution.

The record is an exact-plan review input, not an approval issuer or native fence.
"""
import argparse
import ipaddress
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import readback_core as c
from tools.run_files import current_window, digest, encoded, load_private, read_private, require, write_new

STAGES = {'prepared', 'bootstrap'}
RULE = 'openstack_networking_secgroup_rule_v2'
FIELDS = {'openstack_networking_network_v2': ('network_id', 'admin_state_up', 'domain'),
          'openstack_networking_router_v2': ('router_id', 'admin_state_up', 'domain'),
          'openstack_networking_port_v2': ('port_id', 'admin_state_up', 'workload'),
          'openstack_compute_instance_v2': ('server_id', 'power_state', 'workload')}
REFS = {'native_boundary', 'service_paths', 'image_bootstrap', 'withdrawal'}


def bindings(scope, inputs, outputs, stage):
    require(scope['platform'] == 'openstack' and scope['phase'] in {'domains', 'workloads'}, 'OpenStack WSD lifecycle only')
    require(outputs['scope']['value'] == scope and set(outputs['members']['value']) == set(inputs['members']), 'Prior output scope differs')
    result = {}
    for name, member in inputs['members'].items():
        c.identifier(name)
        require(member.get('lifecycle_stage', 'prepared') == stage, 'Every member must use the exact target stage')
        c.text(member.get('bootstrap_acceptance_ref'), 'bootstrap acceptance reference')
        native = outputs['members']['value'][name]
        prefix = 'module.owned.module.member[' + json.dumps(name) + '].'
        kinds = list(FIELDS)[:2] if scope['phase'] == 'domains' else list(FIELDS)[2:]
        for kind in kinds:
            output, field, resource = FIELDS[kind]
            require(isinstance(native.get(output), str) and c.UUID.fullmatch(native[output]), 'Owned native UUID required')
            value = (stage == 'bootstrap') if field == 'admin_state_up' else ('active' if stage == 'bootstrap' else 'shutoff')
            result[prefix + kind + '.' + resource] = {'type': kind, 'id': native[output], 'values': {field: value}}
        if scope['phase'] == 'workloads':
            require(stage == 'prepared' or member.get('config_drive') is True, 'Bootstrap requires the previously created config drive')
            continue
        rules = member.get('bootstrap_rules', {})
        require(isinstance(rules, dict) and len(rules) <= 32, 'Bounded exact service rules required')
        require(set(native.get('bootstrap_rule_ids', {})) <= set(rules), 'Withdrawal must retain owned service rules')
        for key, rule in rules.items():
            c.identifier(key); c.exact_keys(rule, {'direction', 'protocol', 'port', 'remote_ipv4'})
            address = ipaddress.IPv4Address(rule['remote_ipv4'])
            require(str(address) == rule['remote_ipv4'] and not (address.is_unspecified or address.is_multicast or address.is_loopback), 'Unicast service address required')
            require(rule['direction'] in {'ingress', 'egress'} and rule['protocol'] in {'tcp', 'udp'}
                    and type(rule['port']) is int and 1 <= rule['port'] <= 65535, 'Exact service tuple required')
            c.text(member['project_id']); require(c.UUID.fullmatch(native['security_group_id']), 'Owned group required')
            rule_id = native.get('bootstrap_rule_ids', {}).get(key)
            require(rule_id is None or isinstance(rule_id, str) and c.UUID.fullmatch(rule_id), 'Exact existing rule ID required')
            require(stage == 'bootstrap' or rule_id is not None, 'Withdrawal cannot create service rules')
            result[prefix + RULE + '.bootstrap[' + json.dumps(key) + ']'] = {'type': RULE, 'id': rule_id, 'values': {
                'tenant_id': member['project_id'], 'security_group_id': native['security_group_id'],
                'direction': rule['direction'], 'ethertype': 'IPv4', 'protocol': rule['protocol'],
                'port_range_min': rule['port'], 'port_range_max': rule['port'], 'remote_ip_prefix': str(address) + '/32'}}
    return result


def validate(record, scope=None, input_bytes=None):
    c.exact_keys(record, {'format', 'scope', 'input_sha256', 'prior_bundle_sha256', 'prior_outputs',
                          'target_stage', 'valid_from', 'valid_until', 'acceptance_refs', 'resources'})
    require(record['format'] == 'hosting-openstack-transition/1' and record['target_stage'] in STAGES, 'Unknown lifecycle transition')
    c.exact_keys(record['scope'], {'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key', 'phase'})
    for value in record['scope'].values(): c.identifier(value)
    require(record['scope']['platform'] == 'openstack' and record['scope']['phase'] in {'domains', 'workloads'}, 'Wrong lifecycle scope')
    for key in ('input_sha256', 'prior_bundle_sha256'): require(c.HEX.fullmatch(record[key]), 'Exact artifact hash required')
    current_window(record)
    c.exact_keys(record['acceptance_refs'], REFS)
    for value in record['acceptance_refs'].values(): c.text(value)
    require(isinstance(record['resources'], dict) and record['resources'], 'Exact lifecycle resources required')
    for value in record['resources'].values():
        c.exact_keys(value, {'type', 'id', 'values'})
        require(value['type'] in {*FIELDS, RULE} and isinstance(value['values'], dict), 'Unsupported lifecycle resource')
        require(value['id'] is None and value['type'] == RULE or isinstance(value['id'], str) and c.UUID.fullmatch(value['id']), 'Exact lifecycle UUID required')
        if value['type'] in FIELDS:
            field = FIELDS[value['type']][1]
            expected = record['target_stage'] == 'bootstrap' if field == 'admin_state_up' else ('active' if record['target_stage'] == 'bootstrap' else 'shutoff')
            require(c.digest(value['values']) == c.digest({field: expected}), 'Only the target lifecycle field may be overridden')
        else:
            rule = value['values']
            c.exact_keys(rule, {'tenant_id', 'security_group_id', 'direction', 'ethertype', 'protocol', 'port_range_min', 'port_range_max', 'remote_ip_prefix'})
            network = ipaddress.ip_network(rule['remote_ip_prefix'], strict=True)
            require(network.version == 4 and network.prefixlen == 32 and not (network.network_address.is_unspecified or network.network_address.is_multicast or network.network_address.is_loopback), 'Exact unicast service rule required')
            require(rule['ethertype'] == 'IPv4' and rule['direction'] in {'ingress', 'egress'} and rule['protocol'] in {'tcp', 'udp'}
                    and type(rule['port_range_min']) is int and type(rule['port_range_max']) is int
                    and 1 <= rule['port_range_min'] == rule['port_range_max'] <= 65535, 'Exact service rule required')
            c.text(rule['tenant_id']); require(c.UUID.fullmatch(rule['security_group_id']), 'Owned rule group required')
    if scope is not None:
        require(record['scope'] == scope and record['input_sha256'] == digest(input_bytes), 'Transition inputs or scope changed')
        require(record['resources'] == bindings(scope, c.strict_loads(input_bytes), record['prior_outputs'], record['target_stage']),
                'Transition resource ownership differs from prior outputs and requested inputs')


def plan_bindings(plan, record):
    """Reject every mutation except bound power/port transitions and exact new rules."""
    validate(record)
    require(not plan.get('resource_drift') and plan.get('complete') is not False and not plan.get('deferred_changes'), 'Resolve drift/incomplete plans before lifecycle changes')
    seen = set()
    for item in plan['resource_changes']:
        address = item['address']; change = item['change']; spec = record['resources'].get(address)
        require(item.get('mode') == 'managed' and not item.get('previous_address') and not item.get('deposed')
                and not change.get('importing') and address not in seen, 'Lifecycle cannot adopt, move or duplicate resources')
        seen.add(address)
        before, after, actions = change.get('before'), change.get('after'), change.get('actions')
        unknown = change.get('after_unknown', {})
        require(isinstance(after, dict) and isinstance(unknown, dict), 'Resolved lifecycle plan required')
        if spec is None:
            require(actions == ['no-op'] and c.digest(before) == c.digest(after) and not any_true(unknown), 'Unrelated changes prohibited during transition')
            continue
        require(item['type'] == spec['type'], 'Lifecycle type mismatch')
        require(not c.differences(after, spec['values']) and not any(any_true(unknown.get(k)) for k in spec['values']), 'Lifecycle values unresolved or outside contract')
        if spec['type'] == 'openstack_networking_network_v2':
            require(not c.differences(after, {'shared': False, 'external': False, 'port_security_enabled': True}), 'Known isolated network security required')
        if spec['type'] == 'openstack_networking_router_v2':
            require(not after.get('external_network_id') and not after.get('external_fixed_ip'), 'External router attachment prohibited')
        if spec['type'] == 'openstack_networking_port_v2':
            groups = after.get('security_group_ids')
            require(after.get('port_security_enabled') is True and isinstance(groups, list) and len(groups) == 1 and groups[0]
                    and not after.get('no_security_groups') and not after.get('allowed_address_pairs'), 'Known single-group port security required')
        if spec['type'] == 'openstack_compute_instance_v2':
            blocks = after.get('block_device')
            require(isinstance(blocks, list) and len(blocks) == 1 and isinstance(blocks[0], dict)
                    and blocks[0].get('delete_on_termination') is False, 'Known retained boot attachment required')
        if spec['type'] == RULE:
            require(not after.get('remote_group_id') and not after.get('remote_address_group_id'), 'Extra rule selectors prohibited')
        if spec['id'] is None:
            require(spec['type'] == RULE and record['target_stage'] == 'bootstrap' and actions == ['create'] and before is None,
                    'Only exact bootstrap service rules may be created')
            require(not set(k for k, v in unknown.items() if any_true(v)) - {'id', 'region'}, 'Unresolved service rule')
        else:
            require(actions in (['no-op'], ['update']) and isinstance(before, dict)
                    and before.get('id') == after.get('id') == spec['id'], 'Lifecycle native identity changed')
            # Provider-computed status/timestamps can change when power changes.
            ignored = {'status', 'updated_at'}
            allowed = set(spec['values']) if spec['type'] != RULE else set()
            require(not set(k for k, v in unknown.items() if any_true(v)) - ignored, 'Unknown mutation outside lifecycle field')
            require(c.digest({k: v for k, v in before.items() if k not in allowed | ignored}) ==
                    c.digest({k: v for k, v in after.items() if k not in allowed | ignored}), 'Unrelated attribute mutation prohibited')
        if spec['type'] == 'openstack_compute_instance_v2' and record['target_stage'] == 'bootstrap':
            require(after.get('config_drive') is True, 'Existing config drive required')
    require(set(record['resources']) <= seen, 'Lifecycle plan omits owned resources')
    return record['resources']


def any_true(value):
    return value is True or isinstance(value, dict) and any(any_true(v) for v in value.values()) or isinstance(value, list) and any(any_true(v) for v in value)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('prior-run', 'inputs', 'acceptance', 'output'): p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--stage', choices=sorted(STAGES), required=True); args = p.parse_args()
    try:
        from tools.wsd_handoff import execution_outputs
        prior = load_private(args.prior_run / 'bundle.json')
        outputs, previous, provenance = execution_outputs(args.prior_run, prior['scope']['phase'])
        raw = read_private(args.inputs); inputs = c.strict_loads(raw); accepted = load_private(args.acceptance)
        c.exact_keys(accepted, {'valid_from', 'valid_until', 'acceptance_refs'})
        require({k: inputs[k] for k in ('environment_key', 'site_key', 'tenant_key', 'wsd_key')} ==
                {k: prior['scope'][k] for k in ('environment_key', 'site_key', 'tenant_key', 'wsd_key')}, 'Input scope changed')
        record = {'format': 'hosting-openstack-transition/1', 'scope': prior['scope'], 'input_sha256': digest(raw),
                  'prior_bundle_sha256': provenance['bundle_sha256'], 'prior_outputs': outputs,
                  'target_stage': args.stage, **accepted,
                  'resources': bindings(prior['scope'], inputs, outputs, args.stage)}
        validate(record, prior['scope'], raw); write_new(args.output, encoded(record))
        print('{"status":"TRANSITION_REQUIRES_EXACT_PLAN_REVIEW","native_contact":false}'); return 0
    except (OSError, ValueError, KeyError, TypeError):
        print('{"status":"HOLD_INVALID_TRANSITION"}'); return 2


if __name__ == '__main__': raise SystemExit(main())
