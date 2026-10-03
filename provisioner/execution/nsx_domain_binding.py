"""Bind observed NSX domain intent to exact owned outputs and provider inputs.

Binding establishes record consistency; it does not authenticate ownership,
prove packet enforcement, renew apply authority or release a held operation.
"""
import ipaddress
import re
from provisioner.execution import readback_core as c
from provisioner.execution import lifecycle_transition as lifecycle
from provisioner.execution import nsx_domain_observe as domain
from provisioner.compiler.wsd import STATE
from provisioner.execution.run_files import require
from provisioner.execution.terraform_run import ROOT, select_scope

OBJECTS = {'tier1': ('tier1_path', ''), 'segment': ('segment_path', '-network'),
           'group': ('group_path', '-members'), 'security_policy': ('quarantine_policy_path', '-quarantine')}
RULE_METADATA = {'id', 'path', 'resource_type', '_revision', 'rule_id', 'sequence_number'}


def service_intent(member, group, stage):
    services = lifecycle.service_rules(member) if stage == 'bootstrap' else {}
    result = []
    for name in [*sorted(services), None]:
        service = services.get(name)
        rule = dict(display_name=name or 'deny-scoped-ip-traffic', action='ALLOW' if service else 'DROP',
            direction='IN_OUT', ip_protocol='IPV4' if service else 'IPV4_IPV6', logged=True, disabled=False,
            source_groups=['ANY'], destination_groups=['ANY'], sources_excluded=False, destinations_excluded=False,
            services=['ANY'], profiles=['ANY'], scope=['ANY'], service_entries=[])
        if service:
            peer = [service['remote_ipv4'] + '/32']
            rule.update(source_groups=peer if service['direction'] == 'ingress' else [group],
                        destination_groups=[group] if service['direction'] == 'ingress' else peer,
                        service_entries=[dict(resource_type='L4PortSetServiceEntry', l4_protocol=service['protocol'].upper(),
                                              source_ports=[], destination_ports=[str(service['port'])])])
        result.append(rule)
    require(len({r['display_name'] for r in result}) == len(result), 'Reserved terminal deny name cannot be a service key')
    return result


def bind(scope, outputs, inputs, manifest, *, root=ROOT):
    domain.validate(manifest)
    _, selected_scope, _ = select_scope(root, 'vmware-wsd-domains', inputs)
    require(scope['platform'] == 'vmware' and selected_scope == scope | {'phase': 'domains'}
            and outputs.get('scope', {}).get('value') == selected_scope
            and outputs.get('delivery_state', {}).get('value') == STATE, 'Exact owned domain scope required')
    require(manifest['tenant_id'] == scope['tenant_key'] and manifest['scope_id'] == scope['wsd_key'], 'Foreign domain observation')
    endpoint = inputs['platform_endpoint']; c.text(endpoint, 'domain endpoint', 512)
    require(c.origin(endpoint if endpoint.startswith('https://') else 'https://' + endpoint) == manifest['origin'], 'Domain endpoint differs')
    members = outputs.get('members', {}).get('value')
    require(isinstance(members, dict) and set(members) == set(inputs['members']), 'Exact owned domain member coverage required')
    selected = {r['path']: r for r in manifest['resources']}; used = set(); bound = {}
    for name, member in inputs['members'].items():
        c.identifier(name); native = members[name]; stage = member.get('lifecycle_stage', 'prepared')
        c.exact_keys(member, {'ipv4_cidr', 'transport_zone_path', 'quarantine_sequence'},
                     {'gateway_host_number', 'lifecycle_stage', 'bootstrap_acceptance_ref', 'bootstrap_rules'})
        require(stage in {'bootstrap', 'prepared'} and native.get('delivery_state') == STATE
                and native.get('lifecycle_stage') == stage, 'Owned domain lifecycle stage differs')
        if stage == 'bootstrap': c.text(member.get('bootstrap_acceptance_ref'), 'bootstrap acceptance')
        lifecycle.service_rules(member)
        require(type(member['quarantine_sequence']) is int and member['quarantine_sequence'] > 0, 'Exact policy sequence required')
        network = ipaddress.IPv4Network(member['ipv4_cidr'])
        require(str(network) == member['ipv4_cidr'], 'Canonical domain allocation required')
        offset = member.get('gateway_host_number', 1)
        require(type(offset) is int and 0 < offset < network.num_addresses - 1, 'Usable gateway offset required')
        zone = member['transport_zone_path']
        require(isinstance(zone, str) and re.fullmatch(domain.nsx.EP.pattern + '/transport-zones/' + domain.nsx.PART, zone), 'Exact transport zone required')
        gateway = str(network[offset]) + '/' + str(network.prefixlen)
        intended = {
            'tier1': dict(tier0_path='', route_advertisement_types=[], route_advertisement_rules=[]),
            'segment': dict(connectivity_path=native['tier1_path'], transport_zone_path=zone,
                subnets=[{'gateway_address': gateway}], advanced_config=dict(connectivity='ON' if stage == 'bootstrap' else 'OFF', urpf_mode='STRICT')),
            'group': dict(expression=[dict(resource_type='PathExpression', paths=[native['segment_path']])], extended_expression=[]),
            'security_policy': dict(category='Emergency', sequence_number=member['quarantine_sequence'], stateful=True,
                tcp_strict=True, locked=False, scope=[native['group_path']], rules=service_intent(member, native['group_path'], stage)),
        }
        bound[name] = {}
        for kind, (key, ending) in OBJECTS.items():
            path = native[key]
            require(path in selected and selected[path]['kind'] == kind and path not in used, 'Foreign, shared or missing owned object')
            used.add(path); expected = selected[path]['expected']
            actual = {k: v for k, v in expected.items() if k not in domain.nsx.BASE}
            if kind == 'security_policy':
                sequence = 0
                for rule in actual['rules']:
                    require(type(rule['sequence_number']) is int and rule['sequence_number'] > sequence, 'Native order contradicts service precedence')
                    sequence = rule['sequence_number']
                actual = actual | {'rules': [{k: v for k, v in rule.items() if k not in RULE_METADATA} for rule in actual['rules']]}
            intent = intended[kind] | dict(display_name=inputs['tenant_key'] + '-' + name + ending, tags=[])
            require(c.digest(actual) == c.digest(intent), 'Native expectations differ from domain inputs or service intent')
            bound[name][key] = path
    require(used == set(selected), 'Extra unowned domain observations')
    return bound
