#!/usr/bin/env python3
"""GET-only microseg v4.2 exact Flow policy snapshots; not enforcement or tasks."""
from pathlib import Path
import re
import sys
if __package__ in (None, ''): sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from provisioner.execution import readback_core as c
from provisioner.execution import flow_policy
from tools import nutanix_vm_observe as vm
from provisioner.execution.lifecycle_transition import service_rules
from provisioner.execution.run_files import require

PROFILE = 'nutanix-microseg-v4.2-policy-snapshot'
TYPE = 'microseg.v4.config.'
FIELDS = {'extId', '$objectType', 'tenantId', 'name', 'type', 'state', 'scope',
          'vpcReferences', 'isHitlogEnabled', 'isIpv6TrafficAllowed', 'rules'}
METADATA = {'createdBy', 'creationTime', 'description', 'isSystemDefined', 'lastUpdateTime', 'links',
            'securedGroups', 'isIpv4AddressScope', 'isIpv6AddressScope'}
EMPTY = {'scopeReferences', 'networkFunctionReferences', 'securedEntityGroupReferences'}


def camel(name):
    first, *rest = name.split('_')
    return first + ''.join(x[:1].upper() + x[1:] for x in rest)


def convert_fields(wire, names):
    require(isinstance(wire, dict), 'Native rule object required')
    mapping = {camel(key): key for key in names}
    c.exact_keys(wire, {'$objectType'}, set(mapping) | {'$reserved'})
    result = {mapping[key]: value for key, value in wire.items() if key in mapping}
    for key in ('src_subnet', 'dest_subnet'):
        if key in result and result[key] is not None:
            subnet = result[key]; c.exact_keys(subnet, {'value', 'prefixLength'}, {'$objectType', '$reserved'})
            require(subnet.get('$objectType', 'common.v1.config.IPv4Address') == 'common.v1.config.IPv4Address', 'Wrong peer address type')
            result[key] = [{'value': subnet['value'], 'prefix_length': subnet['prefixLength']}]
    for key in ('tcp_services', 'udp_services'):
        if key in result and result[key] is not None:
            require(isinstance(result[key], list), 'Service list required')
            ports = []
            for port in result[key]:
                c.exact_keys(port, {'startPort', 'endPort'}, {'$objectType', '$reserved'})
                port_type = TYPE + ('TcpPortRangeSpec' if key == 'tcp_services' else 'UdpPortRangeSpec')
                require(port.get('$objectType', port_type) == port_type, 'Wrong protocol service type')
                ports.append({'start_port': port['startPort'], 'end_port': port['endPort']})
            result[key] = ports
    return result


def policy_shape(data, resource):
    c.exact_keys(data, FIELDS, METADATA | EMPTY | {'$reserved'})
    require(data['$objectType'] == TYPE + 'NetworkSecurityPolicy', 'Wrong native policy type')
    for key in EMPTY:
        require(data.get(key) is None or data[key] == [], 'Unexpected native policy selector')
    if 'securedGroups' in data: require(data['securedGroups'] == [resource['category_id']], 'Derived category differs')
    if 'isIpv6AddressScope' in data: require(data['isIpv6AddressScope'] is False, 'IPv6 policy scope unsupported')
    if 'isSystemDefined' in data: require(data['isSystemDefined'] is False, 'System policy is not owned')
    if 'isIpv4AddressScope' in data: require(data['isIpv4AddressScope'] is True, 'IPv4 policy scope required')
    converted = {key: data[camel(key)] for key in ('type', 'state', 'scope', 'is_hitlog_enabled', 'is_ipv6_traffic_allowed')}
    converted['vpc_reference'] = data['vpcReferences']; converted['rules'] = []
    require(isinstance(data['rules'], list), 'Native rule list required')
    ids = set()
    for rule in data['rules']:
        c.exact_keys(rule, {'extId', 'type', 'spec'}, {'$objectType', '$specItemDiscriminator', 'tenantId', 'links', 'description', '$reserved'})
        vm.uuid(rule['extId']); require(rule['extId'] not in ids, 'Duplicate native rule ID'); ids.add(rule['extId'])
        if 'tenantId' in rule: require(rule['tenantId'] == data['tenantId'], 'Foreign rule tenant')
        if '$objectType' in rule: require(rule['$objectType'] == TYPE + 'NetworkSecurityPolicyRule', 'Wrong native rule type')
        kind = rule['type']; require(kind in ('APPLICATION', 'INTRA_GROUP'), 'Unexpected native rule union')
        spec = rule['spec']; require(isinstance(spec, dict), 'Native specification missing')
        names = {'secured_group_category_associated_entity_type', 'secured_group_category_references'}
        if kind == 'APPLICATION':
            names |= flow_policy.EMPTY_APPLICATION | {'src_allow_spec', 'dest_allow_spec', 'is_all_protocol_allowed',
                                                      'src_category_associated_entity_type', 'dest_category_associated_entity_type'}
            wire_type, key = 'ApplicationRuleSpec', 'application_rule_spec'
        else:
            names |= flow_policy.EMPTY_INTRA | {'secured_group_action'}
            wire_type, key = 'IntraEntityGroupRuleSpec', 'intra_entity_group_rule_spec'
        require(spec.get('$objectType') == TYPE + wire_type, 'Native rule discriminator differs')
        require(rule.get('$specItemDiscriminator', TYPE + wire_type) == TYPE + wire_type, 'Contradictory native union discriminator')
        item = {'ext_id': rule['extId'], 'type': kind, 'spec': [{key: [convert_fields(spec, names)]}]}
        if 'description' in rule: item['description'] = rule['description']
        converted['rules'].append(item)
    flow_policy.validate(converted, resource['category_id'], resource['vpc_id'], resource['services'])
    return converted


def validate(m):
    c.common_manifest(m, 'nutanix')
    require(m['profile'] == PROFILE and 'task' not in m, 'Flow snapshot cannot claim task completion')
    ids = set(); tenants = set()
    for r in m['resources']:
        c.exact_keys(r, {'kind', 'ext_id', 'expected_etag', 'category_id', 'vpc_id', 'services', 'expected'})
        for key in ('ext_id', 'category_id', 'vpc_id'): vm.uuid(r[key])
        require(r['kind'] == 'policy' and r['ext_id'] not in ids, 'Unique policy selector required'); ids.add(r['ext_id'])
        service_rules({'bootstrap_rules': r['services']})
        e = r['expected']; policy_shape(e, r)
        require(e['extId'] == r['ext_id'], 'Policy selector differs'); vm.uuid(e['tenantId']); tenants.add(e['tenantId'])
        c.text(e['name'], length=256)
        require(isinstance(r['expected_etag'], str) and len(r['expected_etag']) <= 512
                and re.fullmatch(r'"[\x21\x23-\x7e]+"', r['expected_etag']), 'Strong policy ETag required')
    require(len(tenants) == 1, 'Single native tenant required')


def resource_target(r): return '/api/microseg/v4.2/config/policies/' + r['ext_id']


def targets(m):
    validate(m)
    return {resource_target(r) for r in m['resources']}


def sample(m, client):
    results = []
    for r in m['resources']:
        body, etag = client.get(resource_target(r)); data = body.get('data')
        if not isinstance(data, dict): raise c.ObservationError('FLOW_BODY_MISSING')
        actual = vm.selected(data, r['expected']); mismatch = c.differences(actual, r['expected'])
        identity = not c.differences(actual, {key: r['expected'][key] for key in ('extId', '$objectType', 'tenantId')})
        shape_valid = True
        try: policy_shape(data, r)
        except (ValueError, TypeError, KeyError, IndexError):
            shape_valid = False; mismatch.append('/policy:unreviewed_shape_or_selector')
        if etag is None: mismatch.append('/ETag:missing')
        elif etag != r['expected_etag']: mismatch.append('/ETag:value')
        config = 'UNKNOWN' if not identity or any(x.endswith((':missing', ':type')) for x in mismatch) else ('DIFFERENT' if mismatch else 'MATCH')
        results.append({'resource_key': r['ext_id'], 'identity_match': identity, 'config_status': config,
            'mismatch_fields': mismatch, 'config_sha256': c.digest(actual), 'etag_sha256': c.digest(etag),
            'policy_witness': dict(selected_sha256=c.digest(actual), etag_sha256=c.digest(etag), policy_shape_valid=shape_valid),
            'progress': 'COMPLETE', 'reason': 'FLOW_SNAPSHOT_ONLY_ENFORCEMENT_AND_TASKS_NOT_OBSERVED',
            'task_completion_observed': False})
    return results


def validate_snapshot_witnesses(m, states):
    """Recheck selected hashes and full-shape verdict, including unselected selectors.

    These are consistency witnesses, not authenticated evidence or native fences.
    Task adapters may replace progress while preserving policy evidence.
    """
    require([s.get('resource_key') for s in states] == [r['ext_id'] for r in m['resources']], 'Policy coverage differs')
    for r, state in zip(m['resources'], states):
        witness = state.get('policy_witness'); c.exact_keys(witness, {'selected_sha256', 'etag_sha256', 'policy_shape_valid'})
        require(type(witness['policy_shape_valid']) is bool, 'Policy shape verdict missing')
        for field, summary in (('selected_sha256', 'config_sha256'), ('etag_sha256', 'etag_sha256')):
            require(isinstance(witness[field], str) and re.fullmatch(r'[0-9a-f]{64}', witness[field])
                    and witness[field] == state.get(summary), 'Policy snapshot digest differs')
        if state.get('config_status') == 'MATCH':
            require(state.get('identity_match') is True and state.get('mismatch_fields') == []
                    and witness['policy_shape_valid'] is True
                    and witness['selected_sha256'] == c.digest(r['expected'])
                    and witness['etag_sha256'] == c.digest(r['expected_etag']), 'Policy match contradicts snapshot witness')


def validate_observation_history(m, history, states, current=None):
    try:
        if len(states) == 1 and states[0].get('resource_key') == 'scope':
            require(states[0].get('config_status') == states[0].get('progress') == 'UNKNOWN', 'Invalid scope hold')
            return
        validate_snapshot_witnesses(m, states)
        for state in states:
            require(state.get('task_completion_observed') is False and state.get('progress') == 'COMPLETE'
                    and state.get('reason') == 'FLOW_SNAPSHOT_ONLY_ENFORCEMENT_AND_TASKS_NOT_OBSERVED',
                    'Snapshot cannot claim native task completion')
    except (ValueError, TypeError, KeyError, IndexError):
        raise c.ObservationError('FLOW_SNAPSHOT_WITNESS_INVALID') from None


if __name__ == '__main__':
    from tools.readback_cli import run
    raise SystemExit(run(sys.modules[__name__], 'NUTANIX'))
