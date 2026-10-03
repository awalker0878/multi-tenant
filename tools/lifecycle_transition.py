#!/usr/bin/env python3
"""Bind supported native lifecycle changes to prior inputs, outputs and exact plans.

External acceptance references do not authenticate an approver or fence native
writers. The saved-plan executor seals this record and requires separate approval.
"""
import argparse
import copy
import ipaddress
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from provisioner.execution import readback_core as c
from tools import openstack_transition as os_transition
from provisioner.execution.run_files import current_window, digest, encoded, load_private, read_private, require, write_new

FORMAT = 'hosting-platform-transition/1'
KNOBS = {'lifecycle_stage', 'bootstrap_acceptance_ref', 'bootstrap_rules'}
SUPPORTED = {('nutanix', 'workloads'), ('nutanix', 'domains'), ('vmware', 'domains')}
RULE_METADATA = {'nsx_id', 'path', 'revision', 'rule_id', 'sequence_number'}
EMPTY_RULE_DEFAULTS = {'description', 'notes', 'log_label', 'tag', 'scope', 'profiles',
                       'sources_excluded', 'destinations_excluded'}


def service_rules(member):
    rules = member.get('bootstrap_rules', {})
    require(isinstance(rules, dict) and len(rules) <= 32, 'Bounded service rules required')
    for key, rule in rules.items():
        c.identifier(key); c.exact_keys(rule, {'direction', 'protocol', 'port', 'remote_ipv4'})
        ip = ipaddress.IPv4Address(rule['remote_ipv4'])
        require(str(ip) == rule['remote_ipv4'] and not (ip.is_unspecified or ip.is_loopback or ip.is_multicast or ip.is_link_local), 'Exact unicast peer required')
        require(rule['direction'] in {'ingress', 'egress'} and rule['protocol'] in {'tcp', 'udp'}
                and type(rule['port']) is int and 1 <= rule['port'] <= 65535, 'Exact service tuple required')
    return rules


def nsx_path(value, collection):
    require(isinstance(value, str) and re.fullmatch('/infra/' + collection + r'/[A-Za-z0-9_-]+', value), 'Exact owned NSX path required')
    return value


def bindings(record):
    scope, inputs, outputs = record['scope'], record['requested_inputs'], record['prior_outputs']
    require((scope['platform'], scope['phase']) in SUPPORTED, 'Unsupported platform lifecycle scope')
    require(outputs['scope']['value'] == scope and isinstance(inputs['members'], dict) and inputs['members']
            and set(outputs['members']['value']) == set(inputs['members']), 'Exact prior members required')
    require(all(inputs[k] == scope[k] for k in ('environment_key', 'site_key', 'tenant_key', 'wsd_key')), 'Input scope differs')
    resources = {}
    for name, member in inputs['members'].items():
        c.identifier(name)
        require(member.get('lifecycle_stage', 'prepared') == record['target_stage'], 'All members must use the target stage')
        c.text(member.get('bootstrap_acceptance_ref'), 'native bootstrap acceptance')
        native = outputs['members']['value'][name]
        prefix = 'module.owned.module.member[' + json.dumps(name) + '].'
        if scope['platform'] == 'nutanix' and scope['phase'] == 'domains':
            service_rules(member)
            for key in ('quarantine_policy_id', 'security_category_id', 'vpc_id'):
                require(isinstance(native[key], str) and c.UUID.fullmatch(native[key]), 'Exact prior Flow ownership required')
            kind = 'nutanix_network_security_policy_v2'
            resources[prefix + kind + '.quarantine'] = {'type': kind, 'identity_field': 'ext_id',
                'id': native['quarantine_policy_id'], 'member': name, 'values': {}}
        elif scope['platform'] == 'nutanix':
            require(isinstance(native['vm_id'], str) and c.UUID.fullmatch(native['vm_id']), 'Owned AHV VM UUID required')
            kind = 'nutanix_virtual_machine_v2'
            resources[prefix + kind + '.workload'] = {'type': kind, 'identity_field': 'id', 'id': native['vm_id'],
                'member': name, 'values': {'power_state': 'ON' if record['target_stage'] == 'bootstrap' else 'OFF'}}
        else:
            service_rules(member)
            nsx_path(native['group_path'], 'domains/default/groups')
            for kind, key, collection, resource in [('nsxt_policy_segment', 'segment_path', 'segments', 'domain'),
                    ('nsxt_policy_security_policy', 'quarantine_policy_path', 'domains/default/security-policies', 'quarantine')]:
                path = nsx_path(native[key], collection)
                resources[prefix + kind + '.' + resource] = {'type': kind, 'identity_field': 'path', 'id': path, 'member': name, 'values': {}}
    return resources


def validate(record, scope=None, input_bytes=None, *, as_of=None):
    require(isinstance(record, dict), 'Lifecycle record object required')
    if record.get('format') == 'hosting-openstack-transition/1':
        require(as_of is None, 'Historical validation is limited to the platform transition profile')
        return os_transition.validate(record, scope, input_bytes)
    c.exact_keys(record, {'format', 'scope', 'input_sha256', 'prior_bundle_sha256', 'prior_outputs',
                         'prior_inputs', 'requested_inputs', 'target_stage', 'valid_from', 'valid_until', 'acceptance_refs', 'resources'})
    require(record['format'] == FORMAT and record['target_stage'] in os_transition.STAGES, 'Unknown lifecycle contract')
    c.exact_keys(record['scope'], {'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key', 'phase'})
    for value in record['scope'].values(): c.identifier(value)
    for key in ('input_sha256', 'prior_bundle_sha256'): require(isinstance(record[key], str) and c.HEX.fullmatch(record[key]), 'Exact artifact hash required')
    # Recovery may inspect the original window at an immutable attempt timestamp.
    # Prepare/apply callers omit as_of and still require current authority.
    current_window(record, now=as_of); c.exact_keys(record['acceptance_refs'], os_transition.REFS)
    for value in record['acceptance_refs'].values(): c.text(value)
    previous, intended = copy.deepcopy(record['prior_inputs']), copy.deepcopy(record['requested_inputs'])
    require(isinstance(previous, dict) and isinstance(intended, dict) and previous.get('allow_restricted_build') is True
            and intended.get('allow_restricted_build') is True, 'Prior and requested authorized build scope required')
    for doc in (previous, intended):
        doc.pop('test_authorization_ref', None)
        for member in doc['members'].values():
            for key in KNOBS: member.pop(key, None)
    require(c.digest(previous) == c.digest(intended), 'Lifecycle cannot change allocation, placement, image, hardware or provider inputs')
    require(c.digest(record['resources']) == c.digest(bindings(record)), 'Lifecycle resource contract changed')
    if scope is not None:
        require(scope == record['scope'] and digest(input_bytes) == record['input_sha256']
                and c.digest(c.strict_loads(input_bytes)) == c.digest(record['requested_inputs']), 'Transition scope or inputs changed')


def unchanged(before, after, ignored):
    require(c.digest({k: v for k, v in before.items() if k not in ignored}) ==
            c.digest({k: v for k, v in after.items() if k not in ignored}), 'Unrelated native mutation prohibited')


def exact_shape(actual, expected, metadata=frozenset(), empty_defaults=frozenset()):
    """Expected fields must resolve; only enumerated computed/empty defaults may vary."""
    require(isinstance(actual, dict) and not c.differences(actual, expected), 'Native policy differs from exact service intent')
    for key in set(actual) - set(expected):
        require(key in metadata or key in empty_defaults and (actual[key] is None or actual[key] is False or actual[key] == '' or actual[key] == []),
                'Unreviewed native policy selector or behavior')


def nsx_policy(after, member, group, stage):
    require(after.get('scope') == [group] and after.get('category') == 'Emergency'
            and after.get('stateful') is True and after.get('tcp_strict') is True
            and after.get('sequence_number') == member['quarantine_sequence'], 'Mandatory policy boundary changed')
    rules = service_rules(member) if stage == 'bootstrap' else {}
    actual = after.get('rule')
    require(isinstance(actual, list) and len(actual) == len(rules) + 1, 'Exact allow list and terminal drop required')
    last_sequence = 0
    for index, key in enumerate([*sorted(rules), None]):
        rule = rules.get(key)
        expected = {'display_name': key or 'deny-scoped-ip-traffic', 'action': 'ALLOW' if rule else 'DROP',
                    'direction': 'IN_OUT', 'logged': True, 'disabled': False,
                    'ip_version': 'IPV4' if rule else 'IPV4_IPV6', 'services': [],
                    'source_groups': [], 'destination_groups': []}
        if rule:
            peer = [rule['remote_ipv4'] + '/32']
            expected['source_groups'] = peer if rule['direction'] == 'ingress' else [group]
            expected['destination_groups'] = [group] if rule['direction'] == 'ingress' else peer
        require(isinstance(actual[index], dict), 'Native rule object required')
        sequence = actual[index].get('sequence_number')
        # The provider assigns an omitted/zero sequence in list order. Refuse
        # contradictory explicit values rather than relying on silent repair.
        if sequence is None or type(sequence) is int and sequence == 0:
            last_sequence += 1
        else:
            require(type(sequence) is int and sequence > last_sequence, 'NSX sequence contradicts reviewed rule order')
            last_sequence = sequence
        current = copy.deepcopy(actual[index]); entries = current.pop('service_entries', [])
        exact_shape(current, expected, RULE_METADATA, EMPTY_RULE_DEFAULTS)
        if rule:
            require(isinstance(entries, list) and len(entries) == 1 and isinstance(entries[0], dict), 'Single service entry required')
            sets = entries[0].get('l4_port_set_entry')
            require(isinstance(sets, list) and len(sets) == 1, 'Single TCP/UDP service required')
            exact_shape(entries[0], {'l4_port_set_entry': sets}, empty_defaults={'icmp_entry', 'igmp_entry', 'ether_type_entry', 'ip_protocol_entry', 'algorithm_entry'})
            exact_shape(sets[0], {'protocol': rule['protocol'].upper(), 'destination_ports': [str(rule['port'])], 'source_ports': []},
                        empty_defaults={'display_name', 'description'})
        else: require(entries == [], 'Terminal drop must not be narrowed to a service')


def plan_bindings(plan, record, *, as_of=None):
    require(isinstance(record, dict), 'Lifecycle record object required')
    if record.get('format') == 'hosting-openstack-transition/1':
        require(as_of is None, 'Historical validation is limited to the platform transition profile')
        return os_transition.plan_bindings(plan, record)
    validate(record, as_of=as_of)
    require(not plan.get('resource_drift') and plan.get('complete') is not False and not plan.get('deferred_changes'), 'Resolve native drift before lifecycle')
    seen = set()
    for item in plan['resource_changes']:
        address, change = item['address'], item['change']; spec = record['resources'].get(address)
        require(item.get('mode') == 'managed' and address not in seen and not item.get('previous_address')
                and not item.get('deposed') and not change.get('importing'), 'No adoption, moved or duplicate lifecycle resources')
        seen.add(address)
        before, after, unknown = change.get('before'), change.get('after'), change.get('after_unknown', {})
        require(change.get('actions') in (['no-op'], ['update']) and isinstance(before, dict) and isinstance(after, dict)
                and isinstance(unknown, dict), 'Only existing resolved native resources may transition')
        if spec is None:
            require(change['actions'] == ['no-op'] and c.digest(before) == c.digest(after)
                    and not os_transition.any_true(unknown), 'Unrelated lifecycle resource mutation')
            continue
        require(item['type'] == spec['type'] and before.get(spec['identity_field']) == after.get(spec['identity_field']) == spec['id'], 'Native identity changed')
        ignored = {'revision'} if spec['type'].startswith('nsxt_') else {'update_time', 'status'}
        if spec['type'] == 'nutanix_network_security_policy_v2': ignored = {'last_update_time'}
        security_unknown = {k: v for k, v in unknown.items() if k not in ignored}
        if spec['type'] == 'nsxt_policy_security_policy' and isinstance(security_unknown.get('rule'), list):
            require(all(isinstance(r, dict) for r in security_unknown['rule']), 'Malformed policy unknown fields')
            security_unknown['rule'] = [{k: v for k, v in r.items() if k not in RULE_METADATA} for r in security_unknown['rule']]
        if spec['type'] == 'nutanix_network_security_policy_v2' and isinstance(security_unknown.get('rules'), list):
            require(all(isinstance(r, dict) for r in security_unknown['rules']), 'Malformed Flow unknown fields')
            security_unknown['rules'] = [{k: v for k, v in r.items() if k != 'ext_id'} for r in security_unknown['rules']]
        require(not os_transition.any_true(security_unknown), 'Unknown lifecycle security or mutation fields')
        member = record['requested_inputs']['members'][spec['member']]
        if spec['type'] == 'nutanix_network_security_policy_v2':
            from tools import flow_policy
            native = record['prior_outputs']['members']['value'][spec['member']]
            services = service_rules(member) if record['target_stage'] == 'bootstrap' else {}
            flow_policy.validate(after, native['security_category_id'], native['vpc_id'], services)
            unchanged(before, after, ignored | {'rules'})
            require(c.digest(before.get('rules', [])[:2]) == c.digest(after['rules'][:2]), 'Existing Flow deny rules must remain unchanged')
        elif spec['type'] == 'nutanix_virtual_machine_v2':
            require(after.get('power_state') == spec['values']['power_state'], 'Wrong AHV power target')
            for key, input_key in [('cluster', 'cluster_id'), ('project', 'project_id'), ('categories', 'security_category_id')]:
                require(isinstance(after.get(key), list) and len(after[key]) == 1 and after[key][0].get('ext_id') == member[input_key], 'AHV placement or security membership changed')
            old, new = copy.deepcopy(before), copy.deepcopy(after)
            require(len(old.get('nics', [])) == len(new.get('nics', [])) == 1, 'Exact single NIC required')
            nic = new['nics'][0]; network = nic['nic_network_info'][0]['virtual_ethernet_nic_network_info'][0]
            require(network['subnet'][0]['ext_id'] == member['subnet_id'] and network['ipv4_config'][0]['ip_address'][0]['value'] == member['ipv4_address'], 'AHV address/subnet changed')
            target = record['target_stage'] == 'bootstrap'
            require(nic['nic_backing_info'][0]['virtual_ethernet_nic'][0]['is_connected'] is target, 'Wrong AHV NIC target')
            for doc in (old, new): doc['nics'][0]['nic_backing_info'][0]['virtual_ethernet_nic'][0].pop('is_connected')
            unchanged(old, new, ignored | {'power_state'})
        elif spec['type'] == 'nsxt_policy_segment':
            old, new = copy.deepcopy(before), copy.deepcopy(after)
            require(len(new.get('advanced_config', [])) == len(old.get('advanced_config', [])) == 1, 'Exact segment config required')
            require(new['advanced_config'][0].get('connectivity') == ('ON' if record['target_stage'] == 'bootstrap' else 'OFF')
                    and new['advanced_config'][0].get('urpf_mode') == 'STRICT', 'Wrong segment target or uRPF')
            for doc in (old, new): doc['advanced_config'][0].pop('connectivity')
            unchanged(old, new, ignored)
        else:
            native = record['prior_outputs']['members']['value'][spec['member']]
            nsx_policy(after, member, native['group_path'], record['target_stage'])
            unchanged(before, after, ignored | {'rule'})
    require(set(record['resources']) <= seen, 'Plan omits owned lifecycle resources')
    return record['resources']


def prepare(prior_run, inputs_path, acceptance_path, stage):
    from tools.wsd_handoff import execution_outputs
    prior_run=Path(prior_run)
    bundle=load_private(prior_run/'bundle.json')
    if bundle['scope']['platform']=='openstack':
        return os_transition.prepare(prior_run,inputs_path,acceptance_path,stage)
    outputs,previous,provenance=execution_outputs(prior_run,bundle['scope']['phase'])
    raw=read_private(inputs_path); accepted=load_private(acceptance_path)
    c.exact_keys(accepted,{'valid_from','valid_until','acceptance_refs'})
    record={'format':FORMAT,'scope':bundle['scope'],'input_sha256':digest(raw),
            'prior_bundle_sha256':provenance['bundle_sha256'],'prior_outputs':outputs,
            'prior_inputs':previous,'requested_inputs':c.strict_loads(raw),'target_stage':stage,**accepted}
    record['resources']=bindings(record); validate(record,bundle['scope'],raw)
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('prior-run', 'inputs', 'acceptance', 'output'): p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--stage', choices=sorted(os_transition.STAGES), required=True); args = p.parse_args()
    try:
        record=prepare(args.prior_run,args.inputs,args.acceptance,args.stage)
        write_new(args.output, encoded(record)); print('{"status":"TRANSITION_REQUIRES_EXACT_PLAN_REVIEW"}'); return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        print('{"status":"HOLD_INVALID_TRANSITION"}'); return 2


if __name__ == '__main__': raise SystemExit(main())
