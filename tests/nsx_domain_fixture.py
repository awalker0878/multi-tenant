"""Synthetic owned domain lifecycle; never an accepted native/site record."""
from copy import deepcopy
from datetime import timedelta
import ipaddress
import json
from uuid import uuid5, NAMESPACE_URL
from tests.test_lifecycle_transition import fixture as lifecycle_fixture
from lab.native_readback_fixture import manifest, responses
from provisioner.execution import readback_core as c
from tools import nsx_domain_observe as domain
from provisioner.execution.run_files import digest, encoded


def uid(name): return str(uuid5(NAMESPACE_URL, 'nsx-domain-fixture/' + name))


def scenario(origin, stage='bootstrap', *, expired=False):
    transition, plan = lifecycle_fixture('vmware', stage); inputs = transition['requested_inputs']
    inputs['platform_endpoint'] = transition['prior_inputs']['platform_endpoint'] = origin
    m = manifest('nsx', origin); m.update(profile=domain.PROFILE, tenant_id=inputs['tenant_key'], scope_id=inputs['wsd_key'], resources=[])
    start = c.timestamp(c.now()) - timedelta(seconds=120)
    transition.update(input_sha256=digest(encoded(inputs)), valid_from=(start-timedelta(seconds=1)).isoformat(),
                      valid_until=(start+timedelta(seconds=30 if expired else 600)).isoformat())
    for name, member in inputs['members'].items():
        native = transition['prior_outputs']['members']['value'][name]
        native['tier1_path'] = '/infra/tier-1s/' + uid(name)
        display = inputs['tenant_key'] + '-' + name; group = native['group_path']
        cidr = ipaddress.ip_network(member['ipv4_cidr']); gateway = str(cidr[member.get('gateway_host_number', 1)]) + '/' + str(cidr.prefixlen)
        prefix = 'module.owned.module.member[' + json.dumps(name) + '].'
        for suffix, key, extra in [('nsxt_policy_tier1_gateway.domain', 'tier1_path', dict(display_name=display, ha_mode='NONE', route_advertisement_types=[])),
                                   ('nsxt_policy_group.domain', 'group_path', dict(display_name=display+'-members', criteria=[{'path_expression': [{'member_paths': [native['segment_path']]}]}]))]:
            after = dict(id=native[key].rsplit('/', 1)[1], nsx_id=native[key].rsplit('/', 1)[1], path=native[key], revision=7, **extra)
            plan['resource_changes'].append(dict(address=prefix+suffix, type=suffix.split('.')[0], mode='managed',
                provider_name='registry.terraform.io/vmware/nsxt', change=dict(actions=['no-op'], before=deepcopy(after), after=after, after_unknown={})))
        configurations = {}
        for item in plan['resource_changes']:
            if not item['address'].startswith(prefix): continue
            change = item['change']; kind = item['type']
            for side in ('before', 'after'):
                doc = change[side]; ident = doc['path'].rsplit('/', 1)[1]; doc.update(id=ident, nsx_id=ident, revision=7)
                if kind == 'nsxt_policy_segment':
                    doc.update(display_name=display+'-network', connectivity_path=native['tier1_path'],
                               transport_zone_path=member['transport_zone_path'], subnet=[{'cidr': gateway}])
                if kind == 'nsxt_policy_security_policy':
                    doc.update(display_name=display+'-quarantine')
                    for index, rule in enumerate(doc['rule']):
                        rid = uid(name+'/'+rule['display_name'])
                        rule.update(nsx_id=rid, path=doc['path']+'/rules/'+rid, revision=7,
                                    rule_id=100 if rule['action'] == 'DROP' else 101, sequence_number=index+1)
            configurations[kind] = change['after']
        for kind, key, extra in [
                ('tier1', 'tier1_path', dict(display_name=display, tier0_path='', route_advertisement_types=[], route_advertisement_rules=[])),
                ('segment', 'segment_path', dict(display_name=display+'-network', connectivity_path=native['tier1_path'],
                    transport_zone_path=member['transport_zone_path'], subnets=[{'gateway_address': gateway}],
                    advanced_config=dict(connectivity='ON' if stage == 'bootstrap' else 'OFF', urpf_mode='STRICT'))),
                ('group', 'group_path', dict(display_name=display+'-members', expression=[dict(resource_type='PathExpression', paths=[native['segment_path']])], extended_expression=[])),
                ('security_policy', 'quarantine_policy_path', dict(display_name=display+'-quarantine', category='Emergency',
                    sequence_number=member['quarantine_sequence'], stateful=True, tcp_strict=True, locked=False, scope=[group], rules=[]))]:
            path = native[key]; e = dict(id=path.rsplit('/', 1)[1], path=path, resource_type=domain.nsx.TYPES[kind], _revision=7, tags=[], **extra)
            if kind == 'security_policy':
                for rule in configurations['nsxt_policy_security_policy']['rule']:
                    fields = {k: deepcopy(rule[k]) for k in ('display_name', 'path', 'rule_id', 'action', 'direction', 'logged', 'disabled', 'sequence_number')}
                    fields.update(id=rule['nsx_id'], resource_type='Rule', _revision=rule['revision'], ip_protocol=rule['ip_version'],
                        source_groups=rule['source_groups'] or ['ANY'], destination_groups=rule['destination_groups'] or ['ANY'],
                        services=['ANY'], profiles=['ANY'], scope=['ANY'], sources_excluded=False, destinations_excluded=False, service_entries=[])
                    if rule['service_entries']:
                        entry = rule['service_entries'][0]['l4_port_set_entry'][0]
                        fields['service_entries'] = [dict(resource_type='L4PortSetServiceEntry', l4_protocol=entry['protocol'], source_ports=[], destination_ports=entry['destination_ports'])]
                    e['rules'].append(fields)
            m['resources'].append(dict(kind=kind, path=path, expected=e,
                realization=dict(intent_version='accepted-intent-'+kind, enforcement_points=['/infra/sites/default/enforcement-points/default'])))
        if stage == 'bootstrap':
            item = next(x for x in plan['resource_changes'] if x['address'] == prefix+'nsxt_policy_security_policy.quarantine')
            computed = ('nsx_id', 'path', 'revision', 'rule_id')
            for field in computed: item['change']['after']['rule'][0].pop(field)
            item['change']['after_unknown']['rule'] = [{field: True for field in computed}, {}]
    return transition, plan, m, start.isoformat()
