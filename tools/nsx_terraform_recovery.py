"""Bind existing NSX domain lifecycle observations to the original held saved plan.

This is selected-object reconciliation, not an NSX task inventory, native writer
fence, import/adoption mechanism, ledger release or authorization for another apply.
"""
from copy import deepcopy
import ipaddress
import json
from provisioner.execution import readback_core as c
from tools import nsx_domain_observe as domain, lifecycle_transition as lifecycle
from tools.nutanix_terraform_recovery import valid_mask
from tools.plan_review import has_true
from provisioner.execution.run_files import require

RESOURCES = {
    'nsxt_policy_tier1_gateway.domain': ('tier1', 'tier1_path', ''),
    'nsxt_policy_segment.domain': ('segment', 'segment_path', '-network'),
    'nsxt_policy_group.domain': ('group', 'group_path', '-members'),
    'nsxt_policy_security_policy.quarantine': ('security_policy', 'quarantine_policy_path', '-quarantine'),
}
OBSERVED_PLAN_FIELDS = {'id', 'nsx_id', 'path', 'revision', 'display_name', 'ha_mode', 'tier0_path',
    'route_advertisement_types', 'connectivity_path', 'transport_zone_path', 'subnet', 'advanced_config',
    'criteria', 'scope', 'category', 'sequence_number', 'stateful', 'tcp_strict', 'rule'}
EMPTY_DEFAULTS = {'tag'}


def bind_rules(change, native):
    """Retain rule IDs by name; only new rules may have explicitly computed IDs."""
    prior = {}; seen_ids = set()
    for rule in change['before']['rule']:
        name, ident = rule.get('display_name'), rule.get('nsx_id')
        require(isinstance(name, str) and name and name not in prior and isinstance(ident, str)
                and ident not in seen_ids, 'Exact prior rule identities required')
        c.identifier(ident); prior[name] = rule; seen_ids.add(ident)
    rules = change['after']['rule']; unknown = deepcopy(change.get('after_unknown', {}))
    mask = unknown.get('rule', [])
    require(mask is False or isinstance(mask, list) and (not mask or len(mask) == len(rules)), 'Incomplete rule unknown mask')
    require(len(rules) == len(native), 'Native rule coverage differs')
    sequence = 0
    for index, (rule, expected) in enumerate(zip(rules, native)):
        rule_mask = mask[index] if mask and isinstance(mask, list) else {}
        require(isinstance(rule_mask, dict), 'Rule unknown object required')
        old = prior.get(rule['display_name']); ident = expected['id']
        if old is not None:
            require(old['nsx_id'] == rule.get('nsx_id') == ident and not has_true(rule_mask.get('nsx_id')),
                    'Retained rule identity differs or is unknown')
        for key, target in [('nsx_id', ident), ('path', expected['path']), ('revision', expected['_revision']), ('rule_id', expected['rule_id'])]:
            if rule_mask.get(key) is True:
                require(rule.get(key) is None and (key != 'nsx_id' or old is None), 'Computed rule metadata contradicts plan')
                rule_mask.pop(key)
            else: require(c.digest(rule.get(key)) == c.digest(target), 'Known rule metadata differs from native expectation')
        value = rule.get('sequence_number')
        if value is None or type(value) is int and value == 0:
            sequence += 1
            if rule_mask.get('sequence_number') is True: rule_mask.pop('sequence_number')
        else:
            require(type(value) is int and value > sequence and not has_true(rule_mask.get('sequence_number')), 'Unresolved rule sequence')
            sequence = value
        converted = {key: rule[key] for key in ('display_name', 'action', 'direction', 'logged', 'disabled')}
        converted.update(sequence_number=sequence, ip_protocol=rule['ip_version'], sources_excluded=False, destinations_excluded=False,
            source_groups=rule['source_groups'] or ['ANY'], destination_groups=rule['destination_groups'] or ['ANY'],
            services=['ANY'], profiles=['ANY'], scope=['ANY'], service_entries=[])
        if rule.get('service_entries'):
            entry = rule['service_entries'][0]['l4_port_set_entry'][0]
            converted['service_entries'] = [dict(resource_type='L4PortSetServiceEntry', l4_protocol=entry['protocol'],
                destination_ports=entry['destination_ports'], source_ports=[])]
        require(not c.differences(expected, converted), 'Native rule semantics differ from sealed service intent')
    require(not any(has_true(v) for k, v in unknown.items() if k != 'revision'), 'Unresolved planned domain configuration')


def bind_object(change, resource, member, native, display, stage):
    after = change['after']; e = resource['expected']; kind = resource['kind']; unknown = change.get('after_unknown', {})
    ident = resource['path'].rsplit('/', 1)[1]
    required = dict(id=ident, nsx_id=ident, path=resource['path'], display_name=display)
    require(e['display_name'] == display, 'Observed name differs from owned member')
    require(change['before'].get('id') == ident and change['before'].get('nsx_id') == ident, 'Prior native ID differs')
    if unknown.get('revision') is True: require(after.get('revision') is None, 'Computed revision contradicts saved plan')
    else: require(type(after.get('revision')) is int and after['revision'] == e['_revision'], 'Known revision differs')
    empty = set(EMPTY_DEFAULTS); metadata = {'revision', 'description'}
    if kind == 'tier1':
        required.update(ha_mode='NONE', route_advertisement_types=[])
        empty |= {'tier0_path', 'edge_cluster_path', 'route_advertisement_rule', 'pool_allocation', 'intersite_config',
                  'ipv6_profiles', 'dhcp_config_path', 'enable_standby_relocation', 'disable_firewall'}
    elif kind == 'segment':
        network = ipaddress.IPv4Network(member['ipv4_cidr']); offset = member.get('gateway_host_number', 1)
        require(type(offset) is int and 0 < offset < network.num_addresses - 1, 'Exact usable gateway offset required')
        gateway = str(network[offset]) + '/' + str(network.prefixlen)
        required.update(connectivity_path=native['tier1_path'], transport_zone_path=member['transport_zone_path'],
                        subnet=[{'cidr': gateway}], advanced_config=[dict(connectivity='ON' if stage == 'bootstrap' else 'OFF', urpf_mode='STRICT')])
        require(e['connectivity_path'] == required['connectivity_path'] and e['transport_zone_path'] == required['transport_zone_path']
                and c.digest(e['subnets']) == c.digest([{'gateway_address': gateway}])
                and c.digest(e['advanced_config']) == c.digest(required['advanced_config'][0]), 'Native segment differs from sealed allocation or target')
        # Reject additional nested DHCP, bridging, pools or selectors, including unchanged ones.
        require(isinstance(after.get('subnet'), list) and len(after['subnet']) == 1, 'Single planned subnet required')
        lifecycle.exact_shape(after['subnet'][0], required['subnet'][0], empty_defaults={'dhcp_ranges', 'dhcp_config', 'network'})
        lifecycle.exact_shape(after['advanced_config'][0], required['advanced_config'][0],
            empty_defaults={'hybrid', 'local_egress', 'multicast', 'cidr', 'uplink_teaming_policy_name', 'address_pool_path'})
        empty |= {'dhcp_config_path', 'domain_name', 'vlan_ids', 'l2_extension', 'bridge_profile', 'discovery_profile', 'qos_profile', 'security_profile'}
    elif kind == 'group':
        required['criteria'] = [{'path_expression': [{'member_paths': [native['segment_path']]}]}]
        require(c.digest(e['expression']) == c.digest([dict(resource_type='PathExpression', paths=[native['segment_path']])]), 'Native group membership differs')
        criteria = after.get('criteria'); require(isinstance(criteria, list) and len(criteria) == 1, 'Single planned criterion required')
        lifecycle.exact_shape(criteria[0], required['criteria'][0], empty_defaults={'condition', 'ipaddress_expression', 'macaddress_expression', 'conjunction_operator', 'nested_expression', 'identity_group_expression'})
        expressions = criteria[0]['path_expression']; require(len(expressions) == 1, 'Single path expression required')
        lifecycle.exact_shape(expressions[0], required['criteria'][0]['path_expression'][0])
        empty |= {'conjunction_operator', 'extended_criteria'}
        if 'domain' in after: required['domain'] = 'default'
    else:
        lifecycle.nsx_policy(after, member, native['group_path'], stage)
        required.update(scope=[native['group_path']], category='Emergency', sequence_number=member['quarantine_sequence'], stateful=True, tcp_strict=True, rule=after['rule'])
        require(all(c.digest(e[k]) == c.digest(required[k]) for k in ('scope', 'category', 'sequence_number', 'stateful', 'tcp_strict'))
                and e['locked'] is False, 'Native policy boundary differs')
        bind_rules(change, e['rules']); empty |= {'locked', 'scheduler_path', 'comments'}
        if 'domain' in after: required['domain'] = 'default'
    lifecycle.exact_shape(after, required, metadata, empty)
    if kind != 'security_policy': require(not any(has_true(v) for k, v in unknown.items() if k != 'revision'), 'Unresolved planned domain fields')


def bind_plan(plan, inputs, manifest, transition, *, attempted_at):
    domain.validate(manifest)
    require(plan.get('format_version') == '1.2' and plan.get('complete') is True and not plan.get('errored')
            and not plan.get('deferred_changes') and not plan.get('resource_drift')
            and all(isinstance(check, dict) and check.get('status') == 'pass' for check in plan.get('checks', [])), 'Unresolved saved plan')
    require(transition['scope']['platform'] == 'vmware' and transition['scope']['phase'] == 'domains'
            and c.digest(transition['requested_inputs']) == c.digest(inputs), 'NSX lifecycle scope or inputs differ')
    lifecycle.plan_bindings(plan, transition, as_of=c.timestamp(attempted_at))
    wanted = {}; resources = {r['path']: r for r in manifest['resources']}; actual = {}; seen = set()
    for name, member in inputs['members'].items():
        native = transition['prior_outputs']['members']['value'][name]
        for suffix, (kind, key, ending) in RESOURCES.items():
            path = native[key]
            require(path in resources and resources[path]['kind'] == kind and path not in seen, 'Owned domain observation coverage differs')
            seen.add(path)
            address = 'module.owned.module.member[' + json.dumps(name) + '].' + suffix
            wanted[address] = (member, native, inputs['tenant_key'] + '-' + name + ending, resources[path])
    require(seen == set(resources), 'Extra native domain observation')
    for item in plan['resource_changes']:
        require(item['address'] in wanted and item.get('provider_name') == 'registry.terraform.io/vmware/nsxt', 'Unreviewed NSX plan resource')
        member, native, display, resource = wanted[item['address']]; change = item['change']
        require(item.get('type') == item['address'].rsplit('.', 1)[0].rsplit('.', 1)[1]
                and change['before'].get('path') == change['after'].get('path') == resource['path'], 'Plan type or identity differs')
        require(valid_mask(change.get('after_unknown', {})), 'Malformed planned unknown mask')
        if change['actions'] == ['no-op']: lifecycle.unchanged(change['before'], change['after'], {'revision'})
        bind_object(change, resource, member, native, display, transition['target_stage'])
        actual[item['address']] = resource['path']
    require(set(actual) == set(wanted), 'Plan omits owned domain resources')
    return actual
