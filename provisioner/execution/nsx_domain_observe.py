#!/usr/bin/env python3
"""GET-only owned NSX domain snapshots; no native fencing or lifecycle authority."""
from copy import deepcopy
from pathlib import Path
import sys
from provisioner.execution import readback_core as c
from provisioner.execution import nsx_observe as nsx
from provisioner.execution.run_files import require

PROFILE = 'nsx-local-policy-v1-domain-lifecycle'
FIELDS = {
    'tier1': {'tier0_path', 'route_advertisement_types', 'route_advertisement_rules'},
    'segment': {'connectivity_path', 'transport_zone_path', 'subnets', 'advanced_config'},
    'group': {'expression', 'extended_expression'},
    'security_policy': {'category', 'sequence_number', 'stateful', 'tcp_strict', 'locked', 'scope', 'rules'},
}
BASE = nsx.BASE | {'display_name', 'tags'}
RULE = nsx.RULE | {'display_name', 'path', 'resource_type', '_revision', 'rule_id'}
# Read-only attribution is deliberately omitted from exported configuration.
METADATA = {'_create_time', '_create_user', '_last_modified_time', '_last_modified_user', '_links',
            'description', 'parent_path', 'relative_path', 'unique_id', 'realization_id'}
DEFAULTS = {'marked_for_delete': False, '_system_owned': False, 'overridden': False, '_protection': 'NOT_PROTECTED'}
INACTIVE = {
    'tier1': {'failover_mode': 'NON_PREEMPTIVE', 'enable_standby_relocation': False, 'disable_firewall': False},
    'segment': {'admin_state': 'UP', 'type': 'DISCONNECTED', 'vlan_ids': [], 'bridge_profiles': [],
                'dhcp_config_path': '', 'l2_extension': None, 'domain_name': '', 'replication_mode': 'MTEP'},
    'group': {},
    'security_policy': {'scheduler_path': '', 'is_default': False},
}


def selected(body, fields, *, defaults=None, metadata=METADATA):
    require(isinstance(body, dict) and fields <= body.keys(), 'Missing domain configuration fields')
    defaults = DEFAULTS | (defaults or {})
    for key in body.keys() - fields - metadata:
        require(key in defaults and c.digest(body[key]) == c.digest(defaults[key]), 'Unreviewed NSX selector or behavior')
    return {key: deepcopy(body[key]) for key in fields}


def project(body, resource):
    """Reject additional selectors before projecting both native configuration reads."""
    kind = resource['kind']; defaults = INACTIVE[kind]
    if kind == 'segment' and isinstance(body, dict) and 'type' in body:
        require(body['type'] in ('DISCONNECTED', 'ROUTED'), 'Unsupported segment type')
        defaults = defaults | {'type': body['type']}
    result = selected(body, BASE | FIELDS[kind], defaults=defaults)
    if kind == 'segment':
        # Overlay connectivity is represented by connectivity_path/advanced_config.
        if 'type' in body: require(body['type'] in ('DISCONNECTED', 'ROUTED'), 'Unsupported segment type')
        result['subnets'] = [selected(s, {'gateway_address'}, defaults={'dhcp_ranges': [], 'network': ''}, metadata=set())
                             for s in result['subnets']]
        result['advanced_config'] = selected(result['advanced_config'], {'connectivity', 'urpf_mode'},
            defaults={'hybrid': False, 'local_egress': False, 'multicast': False, 'address_pool_paths': [],
                      'address_pool_path': '', 'uplink_teaming_policy_name': ''}, metadata=set())
    elif kind == 'group':
        result['expression'] = [selected(e, {'resource_type', 'paths'}, metadata={'id', '_revision'}) for e in result['expression']]
    elif kind == 'security_policy':
        rules = []
        for rule in result['rules']:
            r = selected(rule, RULE, defaults={'notes': '', 'log_label': '', 'tag': '', 'tags': [],
                         'disabled_reason': '', 'directional': False})
            require(r['path'] == resource['path'] + '/rules/' + r['id'] and r['resource_type'] == 'Rule', 'Rule identity differs')
            r['service_entries'] = [selected(e, {'resource_type', 'l4_protocol', 'source_ports', 'destination_ports'},
                metadata={'display_name', 'description'}) for e in r['service_entries']]
            rules.append(r)
        result['rules'] = rules
    return result


def policy_manifest(m):
    result = deepcopy(m); result['profile'] = nsx.PROFILE
    for r in result['resources']: r['expected'].pop('display_name', None)
    return result


def validate(m):
    require(m.get('profile') == PROFILE, 'Explicit NSX domain lifecycle profile required')
    nsx.validate(policy_manifest(m))
    by_kind = {kind: {} for kind in FIELDS}
    for r in m['resources']:
        require(r['kind'] in FIELDS, 'Unsupported domain resource')
        e = r['expected']; c.exact_keys(e, BASE | FIELDS[r['kind']])
        require(c.digest(project(e, r)) == c.digest(e), 'Expected domain shape is not canonical')
        c.text(e['display_name']); require(e['tags'] == [], 'Tagged domain objects need separate membership review')
        by_kind[r['kind']][r['path']] = r
        if r['kind'] == 'security_policy':
            for rule in e['rules']:
                c.exact_keys(rule, RULE)
                require(type(rule['_revision']) is int and rule['_revision'] >= 0
                        and type(rule['rule_id']) is int and rule['rule_id'] >= 0, 'Exact native rule metadata required')
                c.text(rule['display_name'])
                for entry in rule['service_entries']:
                    require(entry['resource_type'] == 'L4PortSetServiceEntry' and entry['l4_protocol'] in ('TCP', 'UDP')
                            and entry['source_ports'] == [] and isinstance(entry['destination_ports'], list)
                            and len(entry['destination_ports']) == 1 and isinstance(entry['destination_ports'][0], str)
                            and entry['destination_ports'][0].isdigit() and 1 <= int(entry['destination_ports'][0]) <= 65535,
                            'Only a single TCP/UDP destination port is supported')
    size = len(by_kind['security_policy'])
    require(size > 0 and all(len(values) == size for values in by_kind.values()), 'Complete four-object domain coverage required')
    groups = set(); segments = set(); gateways = set()
    for policy in by_kind['security_policy'].values():
        scope = policy['expected']['scope']; require(len(scope) == 1 and scope[0] in by_kind['group'], 'Exact owned policy group required')
        group = by_kind['group'][scope[0]]; expression = group['expected']['expression']
        require(group['expected']['extended_expression'] == [] and len(expression) == 1
                and expression[0]['resource_type'] == 'PathExpression' and len(expression[0]['paths']) == 1
                and expression[0]['paths'][0] in by_kind['segment'], 'Exact segment-only group required')
        segment = by_kind['segment'][expression[0]['paths'][0]]; gateway = segment['expected']['connectivity_path']
        require(gateway in by_kind['tier1'], 'Exact owned Tier-1 required')
        e = by_kind['tier1'][gateway]['expected']
        require(e['tier0_path'] == '' and e['route_advertisement_types'] == e['route_advertisement_rules'] == [], 'Distributed-only Tier-1 required')
        groups.add(group['path']); segments.add(segment['path']); gateways.add(gateway)
    require(len(groups) == len(segments) == len(gateways) == size, 'Shared or unbound domain identity')


def targets(m):
    validate(m)
    return nsx.targets(policy_manifest(m))


def sample(m, client):
    resources = {'/policy/api/v1' + r['path']: r for r in m['resources']}
    class CheckedClient:
        def get(self, target):
            body, headers = client.get(target)
            if target in resources:
                try: body = project(body, resources[target])
                except (ValueError, TypeError, KeyError, IndexError, AttributeError):
                    raise c.ObservationError('NSX_DOMAIN_SHAPE_UNSUPPORTED') from None
            return body, headers
    states = nsx.sample(m, CheckedClient())
    for state in states: state['shape_witness'] = {'before': True, 'after': True}
    return states


def validate_observation_history(m, history, states, current=None):
    nsx.validate_observation_history(m, history, states, current)
    if len(states) == 1 and states[0].get('resource_key') == 'scope': return
    if any(c.digest(s.get('shape_witness')) != c.digest({'before': True, 'after': True}) for s in states):
        raise c.ObservationError('NSX_DOMAIN_SHAPE_WITNESS_INVALID')


if __name__ == '__main__':
    from provisioner.execution.readback_cli import run
    raise SystemExit(run(sys.modules[__name__], 'NSXT'))
