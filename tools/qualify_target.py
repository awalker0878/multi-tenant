#!/usr/bin/env python3
"""Collect real native readback and controlled guest traffic evidence, not acceptance."""
import argparse
from datetime import datetime
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import readback_core as c, neutron_observe, nsx_observe, nutanix_observe, openstack_observe, nutanix_vm_observe, nutanix_flow_observe
from tools.compile_wsd import STATE
from tools import vsphere_observe, vsphere_task_observe, vsphere_task_tree_observe, nutanix_vm_task_observe, nutanix_vm_activity_observe
from tools import nsx_segment_observe, vmware_network_binding
from tools.check_release import verify
from tools.guest_inventory import build
from tools.run_files import (current_window, digest, encoded, load_private, new_directory,
    read_private, replace_private, require, utcnow, write_new)

ASSETS = {'inventory', 'native_manifest', 'native_credentials', 'native_ca',
          'ssh_key', 'ssh_certificate', 'probe_ca'}
WORKLOAD_ASSETS = {'workload_manifest', 'workload_token', 'workload_ca'}
FLOW_ASSETS = {'flow_manifest', 'domain_outputs'}
VSPHERE_ASSETS = {'workload_manifest', 'workload_session', 'workload_ca'}
NETWORK_BINDING_ASSETS = {'portgroup_manifest', 'domain_outputs', 'workload_inputs'}
ADAPTERS = {'openstack': neutron_observe, 'vmware': nsx_observe, 'nutanix': nutanix_observe}


def validate(plan):
    c.exact_keys(plan, {'format', 'scope', 'source_commit', 'origin', 'assets', 'cases'})
    require(plan['format'] in {'hosting-target-campaign/' + str(i) for i in range(1, 8)}, 'Unknown target campaign')
    c.exact_keys(plan['scope'], {'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key'})
    for value in plan['scope'].values():
        c.identifier(value)
    require(plan['scope']['platform'] in ADAPTERS and re.fullmatch('[0-9a-f]{40}', plan['source_commit']),
            'Exact platform and committed source required')
    require(c.origin(plan['origin']) == plan['origin'], 'Canonical native HTTPS origin required')
    extended = plan['format'] == 'hosting-target-campaign/2'
    flow = plan['format'] == 'hosting-target-campaign/4'
    ahv = plan['format'] == 'hosting-target-campaign/3' or flow
    mapping = plan['format'] in {'hosting-target-campaign/6', 'hosting-target-campaign/7'}
    vsphere = plan['format'] == 'hosting-target-campaign/5' or mapping
    require(not extended or plan['scope']['platform'] == 'openstack', 'Workload readback campaign requires OpenStack')
    require(not ahv or plan['scope']['platform'] == 'nutanix', 'AHV readback campaign requires Nutanix')
    require(not vsphere or plan['scope']['platform'] == 'vmware', 'vSphere readback campaign requires VMware')
    c.exact_keys(plan['assets'], ASSETS | (WORKLOAD_ASSETS if extended else VSPHERE_ASSETS if vsphere else {'workload_manifest'} if ahv else set())
                 | (FLOW_ASSETS if flow else set()) | (NETWORK_BINDING_ASSETS if mapping else set()))
    for asset in plan['assets'].values():
        c.exact_keys(asset, {'path', 'sha256'})
        require(isinstance(asset['path'], str) and Path(asset['path']).is_absolute()
                and re.fullmatch('[0-9a-f]{64}', asset['sha256']), 'Exact private campaign asset required')
    require(isinstance(plan['cases'], list) and 1 <= len(plan['cases']) <= 32, 'Enumerate 1-32 exact traffic cases')
    cases = {}
    for case in plan['cases']:
        c.exact_keys(case, {'id', 'guest', 'destination', 'port', 'server_name', 'path',
                            'body_sha256', 'expect', 'healthy_control'})
        c.identifier(case['id']); c.identifier(case['guest'])
        require(case['id'] not in cases, 'Duplicate traffic case')
        cases[case['id']] = case
        address = ipaddress.ip_address(case['destination'])
        require(address.version == 4 and str(address) == case['destination'] and not
                (address.is_loopback or address.is_link_local or address.is_multicast or address.is_unspecified),
                'Exact workload IPv4 endpoint required')
        require(type(case['port']) is int and 1 <= case['port'] <= 65535, 'Exact destination port required')
        require(isinstance(case['server_name'], str) and len(case['server_name']) <= 253
                and re.fullmatch(r'[a-z0-9][a-z0-9.-]*[a-z0-9]', case['server_name'])
                and '..' not in case['server_name'], 'Exact TLS peer name required')
        require(isinstance(case['path'], str) and re.fullmatch(r'/[A-Za-z0-9_./-]*', case['path'])
                and len(case['path']) <= 256 and '..' not in case['path'], 'Fixed read-only health path required')
        require(re.fullmatch('[0-9a-f]{64}', case['body_sha256']) and case['expect'] in {'allow', 'deny'},
                'Exact expected health bytes and result required')
    for case in cases.values():
        if case['expect'] == 'allow':
            require(case['healthy_control'] is None, 'Positive cases do not reference controls')
        else:
            control = cases.get(case['healthy_control'])
            require(control is not None and control['expect'] == 'allow' and control['guest'] != case['guest']
                    and all(control[k] == case[k] for k in ('destination', 'port', 'server_name', 'path', 'body_sha256')),
                    'Every denial requires a distinct healthy source to the same exact service')
    return cases


def bound_inputs(plan, known_hosts):
    validate(plan)
    assets = {}
    for key, asset in plan['assets'].items():
        raw = read_private(asset['path'])
        require(len(raw) <= 4 * 1024 * 1024 and digest(raw) == asset['sha256'], 'Campaign asset changed or oversized')
        assets[key] = raw
    inventory = c.strict_loads(assets['inventory'])
    variables = inventory['all']['vars']
    access = variables['hosting_guest_access']
    require(access['scope'] == plan['scope'] | {'phase': 'workloads'}, 'Foreign guest scope')
    _, pins = build(variables['hosting_workload_outputs'], access, known_hosts)
    # Inventory connection overrides never enter the transport. Only the freshly
    # rebuilt exact targets and public host keys are used.
    require(all(case['guest'] in access['targets'] for case in plan['cases']), 'Unknown guest selector')
    require(all(ipaddress.ip_address(t['address']).version == 4 for t in access['targets'].values()), 'IPv4 campaign required')
    manifest = c.strict_loads(assets['native_manifest'])
    adapter = nsx_segment_observe if plan['format'] in {'hosting-target-campaign/6', 'hosting-target-campaign/7'} else ADAPTERS[plan['scope']['platform']]
    if adapter is neutron_observe:
        adapter.validate_manifest(manifest)
        if plan['format'] == 'hosting-target-campaign/2':
            workload = c.strict_loads(assets['workload_manifest'])
            workload_binding(plan['scope'], workload, variables['hosting_workload_outputs'], manifest['project_id'])
    else:
        adapter.validate(manifest)
        require(manifest['origin'] == plan['origin'] and manifest['contact_enabled'] is True, 'Native manifest contact differs')
        if plan['format'] in {'hosting-target-campaign/3', 'hosting-target-campaign/4'}:
            workload = c.strict_loads(assets['workload_manifest'])
            ahv_binding(plan['scope'], workload,
                        variables['hosting_workload_outputs'], access, manifest)
            if plan['format'] == 'hosting-target-campaign/4':
                flow_binding(plan['scope'], c.strict_loads(assets['flow_manifest']),
                             c.strict_loads(assets['domain_outputs']), workload, manifest)
        if plan['format'] in {'hosting-target-campaign/5', 'hosting-target-campaign/6', 'hosting-target-campaign/7'}:
            vsphere_binding(plan['scope'], c.strict_loads(assets['workload_manifest']), variables['hosting_workload_outputs'], manifest)
        if plan['format'] in {'hosting-target-campaign/6', 'hosting-target-campaign/7'}:
            binder = vmware_network_binding.bind_attachments if plan['format'] == 'hosting-target-campaign/7' else vmware_network_binding.bind
            binder(plan['scope'], c.strict_loads(assets['workload_manifest']), variables['hosting_workload_outputs'], manifest,
                c.strict_loads(assets['portgroup_manifest']), c.strict_loads(assets['domain_outputs']), c.strict_loads(assets['workload_inputs']))
    return assets, access, pins


def ahv_adapter(manifest):
    adapters = {a.PROFILE: a for a in (nutanix_vm_observe, nutanix_vm_task_observe, nutanix_vm_activity_observe)}
    require(manifest.get('profile') in adapters, 'Supported explicit AHV observer required')
    return adapters[manifest['profile']]


def ahv_binding(scope, manifest, outputs, access, network):
    ahv_adapter(manifest).validate(manifest)
    require(scope['platform'] == 'nutanix' and manifest['contact_enabled'] is True, 'Enabled AHV observation required')
    require(all(manifest[key] == network[key] for key in ('origin', 'operation_id', 'tenant_id', 'scope_id',
            'target_binding_ref', 'engineering_record_ref')), 'Network and AHV observation bindings differ')
    require(manifest['tenant_id'] == scope['tenant_key'] and manifest['scope_id'] == scope['wsd_key'], 'Foreign AHV scope')
    members = outputs['members']['value']
    selected = {r['ext_id']: r['expected'] for r in manifest['resources']}
    require(set(selected) == {v['vm_id'] for v in members.values()}, 'AHV readback must cover every owned VM exactly')
    tenants = {r['expected']['tenantId'] for r in network['resources']}
    subnets = {r['ext_id'] for r in network['resources'] if r['kind'] == 'subnet'}
    require(len(tenants) == 1 and tenants == {r['tenantId'] for r in selected.values()}, 'Foreign native tenant')
    for name, member in members.items():
        vm = selected[member['vm_id']]
        require(vm['powerState'] == 'ON', 'Traffic campaign requires powered-on VM observations')
        addresses = set()
        for nic in vm['nics']:
            require(nic['nicBackingInfo']['isConnected'] is True
                    and nic['nicNetworkInfo']['subnet']['extId'] in subnets, 'NIC must be connected to an observed subnet')
            addresses.add(nic['nicNetworkInfo']['ipv4Config']['ipAddress']['value'])
        require(access['targets'][name]['address'] in addresses, 'Guest access address differs from accepted AHV NIC')


def flow_binding(scope, manifest, outputs, workload, network):
    nutanix_flow_observe.validate(manifest)
    require(scope['platform'] == 'nutanix' and manifest['contact_enabled'] is True, 'Enabled Flow observation required')
    require(all(manifest[key] == network[key] for key in ('origin', 'operation_id', 'tenant_id', 'scope_id',
            'target_binding_ref', 'engineering_record_ref')), 'Flow and network observation bindings differ')
    require(manifest['tenant_id'] == scope['tenant_key'] and manifest['scope_id'] == scope['wsd_key'], 'Foreign Flow scope')
    require(outputs.get('scope', {}).get('value') == scope | {'phase': 'domains'}
            and outputs.get('delivery_state', {}).get('value') == STATE, 'Domain output scope differs')
    members = outputs.get('members', {}).get('value')
    require(isinstance(members, dict) and members, 'Owned domain outputs required')
    selected = {r['ext_id']: r for r in manifest['resources']}
    require(set(selected) == {m['quarantine_policy_id'] for m in members.values()}
            and len(selected) == len(members), 'Every owned domain policy must be observed exactly once')
    tenants = {r['expected']['tenantId'] for r in network['resources']}
    require(len(tenants) == 1 and tenants == {r['expected']['tenantId'] for r in selected.values()}, 'Foreign Flow tenant')
    vpcs = {r['ext_id'] for r in network['resources'] if r['kind'] == 'vpc'}
    subnets = {r['ext_id']: r['expected']['vpcReference'] for r in network['resources'] if r['kind'] == 'subnet'}
    categories = {}
    for member in members.values():
        r = selected[member['quarantine_policy_id']]
        require(member.get('delivery_state') == STATE and r['category_id'] == member['security_category_id']
                and r['vpc_id'] == member['vpc_id'] and r['vpc_id'] in vpcs
                and r['category_id'] not in categories, 'Foreign or ambiguous Flow ownership')
        categories[r['category_id']] = r['vpc_id']
    for resource in workload['resources']:
        vm = resource['expected']; membership = {x['extId'] for x in vm['categories']} & categories.keys()
        require(len(membership) == 1, 'Each VM requires exactly one owned domain category')
        vpc = categories[next(iter(membership))]
        require(all(subnets.get(n['nicNetworkInfo']['subnet']['extId']) == vpc for n in vm['nics']), 'VM NIC VPC differs from Flow scope')


def vsphere_adapter(manifest):
    adapters = {a.PROFILE: a for a in (vsphere_observe, vsphere_task_observe, vsphere_task_tree_observe)}
    adapters.update({profile: vsphere_task_tree_observe for profile in vsphere_task_tree_observe.PROFILES})
    require(manifest.get('profile') in adapters, 'Supported vSphere observer required')
    return adapters[manifest['profile']]


def vsphere_binding(scope, manifest, outputs, network):
    vsphere_adapter(manifest).validate(manifest)
    require(scope['platform'] == 'vmware' and manifest['contact_enabled'] is True, 'Enabled vSphere observation required')
    require(all(manifest[key] == network[key] for key in ('operation_id', 'tenant_id', 'scope_id',
            'target_binding_ref', 'engineering_record_ref')), 'vCenter and NSX evidence bindings differ')
    require(manifest['tenant_id'] == scope['tenant_key'] and manifest['scope_id'] == scope['wsd_key'], 'Foreign vSphere scope')
    members = outputs['members']['value']
    selected = {r['expected']['config']['uuid']: r['expected'] for r in manifest['resources']}
    require(set(selected) == {r['vm_id'] for r in members.values()}, 'vSphere readback must cover every owned VM UUID exactly')
    for vm in selected.values():
        require(vm['runtime']['powerState'] == 'poweredOn', 'Guest traffic requires powered-on VM observations')
        for device in vm['config']['hardware']['device']:
            if device['_typeName'] == 'VirtualVmxnet3':
                require(device['connectable']['connected'] is True, 'Guest traffic requires connected NIC observations')


def workload_binding(scope, manifest, outputs, project_id):
    openstack_observe.validate(manifest)
    require(manifest['scope'] == scope and manifest['project_id'] == project_id, 'Foreign workload observation scope')
    members = outputs['members']['value']
    servers = {v['server_id'] for v in members.values()}
    volumes = {volume for v in members.values() for volume in [v['boot_volume_id'], *v['data_volume_ids']]}
    selected = {kind: {r['id'] for r in manifest['resources'] if r['kind'] == kind} for kind in openstack_observe.KINDS}
    require(selected['server'] == servers and selected['volume'] == volumes and selected['image'], 'Readback must cover every owned server and retained volume plus an accepted image')
    for member in members.values():
        server = next(r['expected'] for r in manifest['resources'] if r['kind'] == 'server' and r['id'] == member['server_id'])
        require(server['status'] == 'ACTIVE' and {x['id'] for x in server['os-extended-volumes:volumes_attached']} ==
                {member['boot_volume_id'], *member['data_volume_ids']}, 'Server attachments differ from owned outputs')
        for volume_id in [member['boot_volume_id'], *member['data_volume_ids']]:
            volume = next(r['expected'] for r in manifest['resources'] if r['kind'] == 'volume' and r['id'] == volume_id)
            require(volume['status'] == 'in-use' and len(volume['attachments']) == 1
                    and volume['attachments'][0].get('server_id') == member['server_id']
                    and volume['attachments'][0].get('volume_id') == volume_id, 'Cinder attachment differs from the owned server')
            if volume_id == member['boot_volume_id']:
                require(volume['bootable'] == 'true' and volume['volume_image_metadata']['image_id'] in selected['image'], 'Boot volume image is absent from readback')


def authority_matches(authority, plan_bytes, source, ssh_bytes):
    c.exact_keys(authority, {'format', 'plan_sha256', 'source_commit', 'ssh_sha256',
                            'valid_from', 'valid_until', 'change_ref', 'target_binding_ref', 'isolation_ref'})
    require(authority['format'] == 'hosting-target-campaign-authority/1'
            and authority['plan_sha256'] == digest(plan_bytes) and authority['source_commit'] == source
            and authority['ssh_sha256'] == digest(ssh_bytes), 'Campaign authority differs')
    for key in ('change_ref', 'target_binding_ref', 'isolation_ref'):
        c.text(authority[key])
    current_window(authority)


def budget(authority, maximum):
    current_window(authority)
    remaining = (datetime.fromisoformat(authority['valid_until'].replace('Z', '+00:00')) - utcnow()).total_seconds()
    require(remaining >= maximum + 2, 'Insufficient authority for the next bounded observation')
    return maximum


def native_readback(plan, assets, authority, directory, label):
    platform = plan['scope']['platform']
    script = {'openstack': 'neutron_observe.py', 'vmware': 'nsx_observe.py', 'nutanix': 'nutanix_observe.py'}[platform]
    if plan.get('format') in {'hosting-target-campaign/6', 'hosting-target-campaign/7'}:
        adapter = vsphere_adapter(c.strict_loads(assets['workload_manifest']))
        port_reader = 'vsphere_port_observe.py' if plan['format'] == 'hosting-target-campaign/7' else 'vsphere_network_observe.py'
        collected = {}
        for key, script, manifest_name in (
            ('network_before', 'nsx_segment_observe.py', 'native_manifest'),
            ('portgroups_before', port_reader, 'portgroup_manifest'),
            ('workloads', Path(adapter.__file__).name, 'workload_manifest'),
            ('portgroups_after', port_reader, 'portgroup_manifest'),
            ('network_after', 'nsx_segment_observe.py', 'native_manifest')):
            collected[key + '_sha256'] = reader_child(plan, assets, authority, directory, label + '-' + key, script, manifest_name)
        return digest(encoded(collected))
    network_hash = reader_child(plan, assets, authority, directory, label, script, 'native_manifest')
    if plan.get('format') == 'hosting-target-campaign/5':
        adapter = vsphere_adapter(c.strict_loads(assets['workload_manifest']))
        workload_hash = reader_child(plan, assets, authority, directory, label + '-workloads',
                                     Path(adapter.__file__).name, 'workload_manifest')
        return digest(encoded({'network_sha256': network_hash, 'workloads_sha256': workload_hash}))
    if plan.get('format') == 'hosting-target-campaign/2':
        budget(authority, 120)
        manifest = c.strict_loads(assets['workload_manifest'])
        client = openstack_observe.Client(manifest, assets['workload_token'].decode().strip(), assets['workload_ca'], authority)
        observation = openstack_observe.observe(manifest, client)
        write_new(directory / (label + '-workloads.json'), encoded(observation))
        require(observation['status'] == 'OBSERVED_MATCH_NOT_QUALIFIED', 'Workload identity, placement or storage readback failed')
        return digest(encoded({'network_sha256': network_hash, 'workloads_sha256': digest(encoded(observation))}))
    if plan.get('format') in {'hosting-target-campaign/3', 'hosting-target-campaign/4'}:
        adapter = ahv_adapter(c.strict_loads(assets['workload_manifest']))
        workload_hash = reader_child(plan, assets, authority, directory, label + '-workloads',
                                     Path(adapter.__file__).name, 'workload_manifest')
        combined = {'network_sha256': network_hash, 'workloads_sha256': workload_hash}
        if plan['format'] == 'hosting-target-campaign/4':
            combined['flow_sha256'] = reader_child(plan, assets, authority, directory, label + '-flow',
                                                   'nutanix_flow_observe.py', 'flow_manifest')
        return digest(encoded(combined))
    return network_hash


def reader_child(plan, assets, authority, directory, label, script, manifest_name):
    platform = plan['scope']['platform']
    output = directory / (label + '.json')
    vcenter = platform == 'vmware' and manifest_name in {'workload_manifest', 'portgroup_manifest'}
    origin = c.strict_loads(assets[manifest_name])['origin'] if vcenter else plan['origin']
    argv = [sys.executable, str(ROOT / 'tools' / script), str(directory / manifest_name),
            '--read-authorized-target', '--expected-origin', origin,
            '--ca-file', str(directory / ('workload_ca' if vcenter else 'native_ca')), '--output', str(output)]
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'}
    if vcenter:
        env['VCENTER_SESSION'] = assets['workload_session'].decode().strip()
        c.text(env['VCENTER_SESSION'], length=4096)
    elif platform == 'openstack':
        credentials = c.strict_loads(assets['native_credentials'])
        c.exact_keys(credentials, {'token'})
        c.text(credentials['token'], length=8192)
        env['OS_TOKEN'] = credentials['token']
        argv += ['--endpoint', plan['origin'] + '/v2.0']
    else:
        credentials = c.strict_loads(assets['native_credentials'])
        c.exact_keys(credentials, {'username', 'password'})
        for key in credentials:
            c.text(credentials[key], length=4096)
            env[('NSXT' if platform == 'vmware' else 'NUTANIX') + '_' + key.upper()] = credentials[key]
    with os.fdopen(os.open(directory / (label + '.log'), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as log:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                env=env, timeout=budget(authority, 120), umask=0o077)
    require(result.returncode == 0, 'Native readback failed; exposure must remain held')
    report = load_private(output)
    require(report.get('outcome', report.get('status')) in {'READBACK_MATCH_NOT_QUALIFIED', 'OBSERVED_MATCH_NOT_QUALIFIED'},
            'Native readback is not stable and matching')
    return digest(read_private(output))


def ssh_probe(case, target, authority, directory, binary, ca, sequence):
    require(utcnow() < datetime.fromisoformat(target['access_valid_until'].replace('Z', '+00:00')), 'Guest access expired')
    payload = case | {'machine_id': target['machine_id'], 'source': target['address'], 'ca_pem': ca.decode('ascii')}
    fixed = (ROOT / 'tools/guest_probe.py').read_text()
    argv = [str(binary), '-F', '/dev/null', '-T', '-i', str(directory / 'ssh_key'),
            '-p', str(target['port']), '-l', target['user']]
    settings = ['BatchMode=yes', 'StrictHostKeyChecking=yes', 'UpdateHostKeys=no',
        'GlobalKnownHostsFile=/dev/null', 'UserKnownHostsFile=' + str(directory / 'known_hosts'),
        # Adjacent ssh_key-cert.pub retains the private-key filename when the
        # raw identity is filtered out by the certificate-only algorithm list.
        'IdentitiesOnly=yes', 'IdentityAgent=none',
        'PubkeyAcceptedAlgorithms=ssh-ed25519-cert-v01@openssh.com', 'ForwardAgent=no', 'ClearAllForwardings=yes',
        'ProxyCommand=none', 'ProxyJump=none', 'ConnectionAttempts=1', 'ConnectTimeout=5',
        'ServerAliveInterval=3', 'ServerAliveCountMax=1', 'LogLevel=ERROR']
    for option in settings:
        argv += ['-o', option]
    argv += [target['address'], '/usr/bin/python3 -I -c ' + shlex.quote(fixed)]
    output = directory / f'ssh-{sequence}.json'
    with os.fdopen(os.open(directory / f'ssh-{sequence}.log', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as log, \
         os.fdopen(os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as out:
        result = subprocess.run(argv, input=encoded(payload), stdout=out, stderr=log,
            env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, timeout=budget(authority, 20), umask=0o077)
    if result.returncode != 0 or output.stat().st_size > 4096:
        return {'status': 'SSH_INCONCLUSIVE'}
    value = c.strict_loads(output.read_bytes())
    c.exact_keys(value, {'status'})
    require(value['status'] in {'WRONG_GUEST', 'BLOCKED', 'INCONCLUSIVE', 'UNEXPECTED_CONNECTION',
                              'HEALTHY', 'UNHEALTHY'}, 'Unexpected guest observation')
    return value


def traffic_campaign(cases, observe):
    observations = []
    for case in cases.values():
        if case['expect'] == 'deny':
            control = cases[case['healthy_control']]
            before = observe(control)
            denied = observe(case) if before['status'] == 'HEALTHY' else {'status': 'NOT_ATTEMPTED'}
            after = observe(control)
            passed = before['status'] == after['status'] == 'HEALTHY' and denied['status'] == 'BLOCKED'
            evidence = {'before': before, 'traffic': denied, 'after': after}
        else:
            observed = observe(case)
            passed, evidence = observed['status'] == 'HEALTHY', {'traffic': observed}
        observations.append({'id': case['id'], 'passed': passed, **evidence})
        if not passed:
            break
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--authority', type=Path)
    parser.add_argument('--ssh', type=Path, default=Path('/usr/bin/ssh'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    directory = None
    try:
        raw = read_private(args.plan); plan = c.strict_loads(raw); cases = validate(plan)
        if not args.execute:
            print('{"status":"VALIDATED_NO_CONTACT"}'); return 0
        require(args.authority and args.output, 'Current private authority and new output required')
        source = verify(ROOT)
        require(source['status'] == 'HASHES_MATCH' and source['commit'] == plan['source_commit'], 'Clean exact source required')
        binary = args.ssh.resolve(strict=True)
        authority = load_private(args.authority)
        authority_matches(authority, raw, source['commit'], binary.read_bytes())
        require('.invalid' not in plan['origin'], 'Documentation endpoint refused')
        assets, access, pins = bound_inputs(plan, str(args.output.absolute() / 'known_hosts'))
        directory = new_directory(args.output, ROOT)
        write_new(directory / 'plan.json', raw)
        write_new(directory / 'authority.json', encoded(authority))
        # Copy only assets the child processes need; API credentials stay in memory.
        for key in ('native_manifest', 'native_ca', 'ssh_key'):
            write_new(directory / key, assets[key])
        if plan['format'] in {'hosting-target-campaign/3', 'hosting-target-campaign/4', 'hosting-target-campaign/5', 'hosting-target-campaign/6', 'hosting-target-campaign/7'}:
            write_new(directory / 'workload_manifest', assets['workload_manifest'])
        if plan['format'] == 'hosting-target-campaign/4':
            write_new(directory / 'flow_manifest', assets['flow_manifest'])
        if plan['format'] in {'hosting-target-campaign/5', 'hosting-target-campaign/6', 'hosting-target-campaign/7'}:
            write_new(directory / 'workload_ca', assets['workload_ca'])
        if plan['format'] in {'hosting-target-campaign/6', 'hosting-target-campaign/7'}:
            write_new(directory / 'portgroup_manifest', assets['portgroup_manifest'])
        write_new(directory / 'ssh_key-cert.pub', assets['ssh_certificate'])
        write_new(directory / 'known_hosts', pins.encode())
        result = {'status': 'HOLD_INCOMPLETE', 'scope': plan['scope'], 'source_commit': source['commit'],
                  'plan_sha256': digest(raw), 'started_at': utcnow().isoformat(), 'production_qualified': False}
        write_new(directory / 'result.json', encoded(result))
        before = native_readback(plan, assets, authority, directory, 'native-before')
        sequence = 0
        def observe(case):
            nonlocal sequence
            sequence += 1
            target = access['targets'][case['guest']] | {'access_valid_until': access['valid_until']}
            answer = ssh_probe(case, target, authority, directory, binary, assets['probe_ca'], sequence)
            write_new(directory / f'probe-{sequence}.json', encoded({'case': case['id'], **answer, 'observed_at': utcnow().isoformat()}))
            return answer
        observations = traffic_campaign(cases, observe)
        after = native_readback(plan, assets, authority, directory, 'native-after')
        passed = len(observations) == len(cases) and all(o['passed'] for o in observations)
        result |= {'status': 'COLLECTED_REQUIRES_INDEPENDENT_ACCEPTANCE' if passed else 'HOLD_FAILED_TRAFFIC',
                   'native_before_sha256': before, 'native_after_sha256': after, 'cases': observations,
                   'completed_at': utcnow().isoformat()}
        replace_private(directory / 'result.json', encoded(result))
        print(json.dumps({'status': result['status'], 'production_qualified': False}))
        return 0 if passed else 2
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print('{"status":"HOLD_INCOMPLETE","production_qualified":false}')
        return 2
    finally:
        if directory:
            # Preserve evidence and public trust; remove the extra private key copy.
            (directory / 'ssh_key').unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(main())
