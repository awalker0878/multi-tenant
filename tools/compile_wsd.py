#!/usr/bin/env python3
"""Compile cluster-aware, disabled WSD inputs; never contact or authorize a target."""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hosting_resources import RESOURCE_ROOT as ROOT
from scripts.build_wsd_compositions import COMPONENTS
from tools.neutron_observe import strict_loads

ROLES = {'management', 'security-edge', 'shared-services', 'trust', 'workload',
         'data', 'protection', 'recovery', 'qualification'}
PLACEMENT = {
    'nutanix': {'cluster_id', 'storage_container_id'},
    'vmware': {'resource_pool_id', 'datastore_id'},
    'openstack': {'compute_availability_zone', 'storage_availability_zone', 'volume_type'},
}
NETWORK = {
    'nutanix': {'subnet_id', 'security_category_id'},
    'vmware': {'quarantine_network_id'},
    'openstack': {'network_id', 'subnet_id', 'security_group_id'},
}
# Cross-phase workload-network bindings, declared once here rather than branched on.
# A platform whose workload network identity is *observed* instead of being produced
# by its own domain phase declares the accepted observation and the native field that
# observation populates. The generic compiler reads this table; it never names a
# platform, and an adapter that must state the same requirement reads it from here.
WORKLOAD_NETWORK_BINDING = {
    'vmware': {
        'observed_field': 'segment_path',
        'binding_field': 'segment_path',
        'native_field': 'quarantine_network_id',
        'binding_identity': 'network_id',
        'message': 'vCenter network must be explicitly mapped to the observed NSX segment',
    },
}
STATE = 'PREPARED_NOT_QUALIFIED_NOT_SERVICE_READY'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(value):
    require(isinstance(value, str) and re.fullmatch(r'[a-z][a-z0-9-]{1,40}', value),
            'Invalid stable identity')
    return value


def fields(value, expected, label):
    require(isinstance(value, dict) and set(value) == set(expected), f'Invalid {label} fields')


def native_module(platform, phase):
    """Load the reviewed native module configuration for one platform and phase."""
    require(platform in COMPONENTS and phase in {'domains', 'workloads'},
            'Unsupported platform or phase')
    return json.loads((ROOT / 'terraform/modules' / COMPONENTS[platform][phase] / 'main.tf.json').read_text(encoding='utf-8'))


def native_variables(platform, phase):
    """The native input names one reviewed module declares.

    This function is the single owner of native field shapes. Callers that must
    decide which inputs a platform can accept ask here instead of restating a
    provider-specific field list.
    """
    return frozenset(native_module(platform, phase)['variable'])


def native_inputs(platform, phase, supplied, excluded):
    config = native_module(platform, phase)
    variables = {k: v for k, v in config['variable'].items() if k not in excluded}
    require(isinstance(supplied, dict) and not set(supplied) - set(variables), 'Unknown or owned native input')
    values = {}
    for key, spec in variables.items():
        value = supplied.get(key, spec.get('default'))
        kind = spec['type']
        if key in {'lifecycle_stage', 'bootstrap_acceptance_ref', 'bootstrap_rules'}:
            require(value == spec['default'], 'Initial compilation cannot issue a bootstrap transition')
        require((kind == 'string' and isinstance(value, str) and (bool(value.strip()) or spec.get('default') == ''))
                or (kind == 'number' and type(value) in (int, float) and value >= 0)
                or (kind == 'bool' and type(value) is bool)
                or (key == 'bootstrap_rules' and isinstance(value, dict) and not value), f'Missing or invalid native input: {key}')
        require(not isinstance(value, str) or ('${' not in value and '%{' not in value), 'Template syntax in native input')
        values[key] = value
    return values


def compile_environment(env, phase='domains', outputs=None, phase_bindings=None):
    fields(env, {'format', 'environment_key', 'site_key', 'platform', 'lifecycle', 'clusters', 'wsds'}, 'environment')
    require(env['format'] == 'hosting-wsd-environment/1', 'Unknown environment format')
    platform = env['platform']
    require(platform in COMPONENTS and phase in {'domains', 'workloads'}, 'Unsupported platform or phase')
    require(env['lifecycle'] in {'qualification', 'development', 'test', 'production', 'recovery'}, 'Unknown lifecycle')
    environment, site = identity(env['environment_key']), identity(env['site_key'])
    require(isinstance(env['clusters'], list) and env['clusters'], 'Cluster catalogue required')
    clusters, hosts = {}, set()
    for c in env['clusters']:
        fields(c, {'id', 'role', 'zone', 'trust', 'service_classes', 'eligible_tenants',
                   'dedicated_wsd', 'host_ids', 'native'}, 'cluster')
        cid = identity(c['id'])
        require(cid not in clusters and c['role'] in ROLES, 'Duplicate cluster or unknown role')
        require(c['zone'] in {'OZ', 'RZ', 'PAZ', 'MANAGEMENT'}, 'Unknown cluster zone')
        identity(c['trust'])
        for key in ('service_classes', 'eligible_tenants', 'host_ids'):
            require(isinstance(c[key], list) and c[key] and len(set(c[key])) == len(c[key]), 'Empty or duplicate cluster eligibility')
            for v in c[key]:
                identity(v)
        require(not hosts.intersection(c['host_ids']), 'Physical hosts cannot belong to multiple clusters/zones')
        hosts.update(c['host_ids'])
        require(c['dedicated_wsd'] is None or isinstance(c['dedicated_wsd'], str), 'Invalid dedication')
        if c['role'] == 'workload':
            fields(c['native'], PLACEMENT[platform], 'native placement')
            require(all(isinstance(v, str) and v.strip() for v in c['native'].values()), 'Missing native placement identity')
        clusters[cid] = c
    require(isinstance(env['wsds'], list) and env['wsds'], 'WSD allocations required')
    files, scopes, seen, native_domains, native_workloads = {}, [], set(), set(), set()
    expected_output_scopes = set()
    for wsd in env['wsds']:
        fields(wsd, {'tenant_key', 'wsd_key', 'trust', 'service_class', 'domains'}, 'WSD')
        tenant, wid = identity(wsd['tenant_key']), identity(wsd['wsd_key'])
        require(len(tenant) <= 24, 'Tenant identity exceeds native module limit')
        identity(wsd['trust']); identity(wsd['service_class'])
        key = tenant + '/' + wid
        require(key not in seen, 'Duplicate tenant/WSD')
        seen.add(key)
        require(isinstance(wsd['domains'], list) and wsd['domains'], 'Domains required')
        scope = {'tenant_key': tenant, 'wsd_key': wid, 'environment_key': environment,
                 'site_key': site, 'platform': platform, 'phase': phase}
        received = {}
        if phase == 'workloads':
            expected_output_scopes.add(key)
            require(isinstance(outputs, dict) and key in outputs, 'Domain output scope missing')
            receipt = outputs[key]
            require(receipt.get('scope', {}).get('value') == {**scope, 'phase': 'domains'}, 'Domain output identity mismatch')
            require(receipt.get('delivery_state', {}).get('value') == STATE, 'Unknown domain delivery state')
            received = receipt.get('members', {}).get('value')
            require(isinstance(received, dict) and set(received) == {d['id'] for d in wsd['domains']}, 'Domain output member mismatch')
        members, prefixes = {}, []
        for domain in wsd['domains']:
            fields(domain, {'id', 'zone', 'cluster', 'inputs', 'workloads'}, 'domain')
            did = domain['id']
            require(isinstance(did, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9-]{1,23}', did), 'Invalid domain identity')
            require((tenant, did) not in native_domains, 'Native domain identity reused across WSDs')
            native_domains.add((tenant, did))
            require(domain['zone'] in {'OZ', 'RZ'}, 'Only internal OZ/RZ compositions are implemented')
            require(domain['cluster'] in clusters, 'Unknown placement cluster')
            cluster = clusters[domain['cluster']]
            require(cluster['role'] == 'workload' and cluster['zone'] == domain['zone'], 'Wrong cluster role or zone')
            require(cluster['trust'] == wsd['trust'] and tenant in cluster['eligible_tenants']
                    and wsd['service_class'] in cluster['service_classes'], 'Incompatible cluster residency')
            require(cluster['dedicated_wsd'] in {None, key}, 'Dedicated cluster belongs to another WSD')
            domain_inputs = native_inputs(platform, 'domains', domain['inputs'],
                                          {'tenant_key', 'domain_key', 'allow_restricted_build', 'test_authorization_ref'})
            network = ipaddress.IPv4Network(domain_inputs['ipv4_cidr'], strict=True)
            require(network.prefixlen <= 29 and not any(network.overlaps(p) for p in prefixes), 'Unusable or overlapping WSD prefixes')
            prefixes.append(network)
            gateway_offset = domain_inputs['gateway_host_number']
            require(type(gateway_offset) is int and 0 < gateway_offset < network.num_addresses - 1, 'Invalid gateway offset')
            require(isinstance(domain['workloads'], dict) and domain['workloads'], 'Owned workloads required')
            if phase == 'domains':
                members[did] = domain_inputs
            addresses = set()
            for name, inputs in domain['workloads'].items():
                identity(name)
                # VMware and other native VM names are not prefixed by tenant in primitives.
                require(name not in native_workloads, 'Workload native name reused in environment')
                native_workloads.add(name)
                owned = {'tenant_key', 'domain_key', 'workload_key', 'allow_restricted_build',
                         'test_authorization_ref', 'accepted_quarantine_ref'} | PLACEMENT[platform] | NETWORK[platform]
                values = native_inputs(platform, 'workloads', inputs, owned)
                if 'ipv4_address' in values:
                    address = ipaddress.IPv4Address(values['ipv4_address'])
                    require(address in network and address not in {network.network_address, network.broadcast_address,
                            network.network_address + gateway_offset} and address not in addresses, 'Invalid or duplicate workload address')
                    addresses.add(address)
                if phase == 'workloads':
                    native = received[did]
                    require(isinstance(native, dict) and native.get('delivery_state') == STATE, 'Unknown member state')
                    binding_rule = WORKLOAD_NETWORK_BINDING.get(platform)
                    if binding_rule is not None:
                        binding = (phase_bindings or {}).get(key + '/' + did, {})
                        observed = binding.get(binding_rule['binding_field'])
                        require(observed == native.get(binding_rule['observed_field']) and bool(observed),
                                binding_rule['message'])
                        native = {binding_rule['native_field']: binding.get(binding_rule['binding_identity'])}
                    network_ids = {field: native.get(field) for field in NETWORK[platform]}
                    require(all(isinstance(v, str) and v.strip() for v in network_ids.values()), 'Missing native network identity')
                    members[name] = {**values, **cluster['native'], **network_ids, 'domain_key': did,
                                     'accepted_quarantine_ref': ''}
        inputs = {k: scope[k] for k in ('tenant_key', 'wsd_key', 'environment_key', 'site_key')}
        inputs.update(allow_restricted_build=False, test_authorization_ref='', members=members)
        path = key + '/' + phase + '.tfvars.json'
        files[path] = inputs
        scopes.append({'scope': scope, 'root': f'terraform/stacks/wsd/{platform}/{phase}',
                       'input': path, 'state_key': '/'.join((environment, site, platform, key, phase))})
    if phase == 'workloads':
        require(set(outputs) == expected_output_scopes, 'Unexpected domain output scope')
    return files, {'status': 'DRAFT_DISABLED_NOT_AUTHORIZED', 'native_contact': False,
                   'lifecycle': env['lifecycle'], 'scopes': scopes,
                   'limits': ['No native commissioning, capacity reservation, IPAM or quarantine acceptance',
                              'Backend must be provisioned and matched to state_key by its owner']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('environment', type=Path)
    parser.add_argument('--phase', choices=['domains', 'workloads'], default='domains')
    parser.add_argument('--domain-outputs', type=Path)
    parser.add_argument('--vmware-bindings', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        require(not args.output.resolve().is_relative_to(ROOT), 'Use private output storage outside the repository')
        files, plan = compile_environment(strict_loads(args.environment.read_bytes()), args.phase,
            strict_loads(args.domain_outputs.read_bytes()) if args.domain_outputs else None,
            strict_loads(args.vmware_bindings.read_bytes()) if args.vmware_bindings else None)
        # No overwrite: an existing reviewed input set is immutable to this compiler.
        args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
        for name, data in {**files, 'scopes.json': plan}.items():
            path = args.output / name
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
                json.dump(data, stream, indent=2); stream.write('\n')
        print(json.dumps({'status': plan['status'], 'scopes': len(plan['scopes'])}))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'REJECTED', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
