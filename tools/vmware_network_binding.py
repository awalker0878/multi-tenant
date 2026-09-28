"""Bind campaign VM NICs through observed portgroups to owned NSX segments."""
from tools import readback_core as c, nsx_segment_observe as nsx, vsphere_network_observe as pg, vsphere_port_observe as ports
from provisioner.compiler.wsd import STATE
from tools.run_files import require


def bind(scope, workloads, outputs, network, portgroups, domain_outputs, inputs):
    nsx.validate(network); pg.validate(portgroups)
    require(scope['platform'] == 'vmware' and portgroups['contact_enabled'] is True
            and portgroups['origin'] == workloads['origin'], 'Enabled same-vCenter portgroup readback required')
    for key in ('operation_id', 'tenant_id', 'scope_id', 'engineering_record_ref', 'target_binding_ref'):
        require(portgroups[key] == workloads[key] == network[key], 'Network association evidence scope differs')
    require(portgroups['tenant_id'] == scope['tenant_key'] and portgroups['scope_id'] == scope['wsd_key'], 'Foreign network association scope')
    require(domain_outputs.get('scope', {}).get('value') == scope | {'phase': 'domains'}
            and domain_outputs.get('delivery_state', {}).get('value') == STATE, 'Owned domain outputs required')
    require(outputs.get('scope', {}).get('value') == scope | {'phase': 'workloads'}
            and outputs.get('delivery_state', {}).get('value') == STATE, 'Owned workload outputs required')
    require(all(inputs.get(k) == scope[k] for k in ('environment_key', 'site_key', 'tenant_key', 'wsd_key')), 'Workload inputs scope differs')
    endpoint = inputs['platform_endpoint']
    c.text(endpoint, 'workload platform endpoint', 512)
    require(c.origin(endpoint if endpoint.startswith('https://') else 'https://' + endpoint) == workloads['origin'], 'Workload endpoint differs')
    domains = domain_outputs.get('members', {}).get('value'); members = outputs['members']['value']
    require(isinstance(domains, dict) and domains and isinstance(members, dict) and members
            and isinstance(inputs.get('members'), dict) and set(inputs['members']) == set(members), 'Exact owned member inputs required')
    segments = {r['path']: r for r in network['resources'] if r['kind'] == 'segment'}
    require(len(domains) == len(segments) and {d['segment_path'] for d in domains.values()} == set(segments)
            and all(d.get('delivery_state') == STATE for d in domains.values()), 'Every owned segment must be observed exactly')
    groups = {r['moid']: r for r in portgroups['resources']}
    for r in groups.values():
        require(r['segment_path'] in segments and r['expected']['config']['logicalSwitchUuid'] ==
                segments[r['segment_path']]['logical_switch']['realization_specific_identifier'], 'Portgroup logical switch differs from NSX realization')
    vms = {r['expected']['config']['uuid']: r['expected'] for r in workloads['resources']}
    require(len(members) == len(vms) and {v['vm_id'] for v in members.values()} == set(vms), 'Exact unique owned VM coverage required')
    used = set()
    for name, member in members.items():
        require(member.get('delivery_state') == STATE, 'Unknown workload delivery state')
        selection = inputs['members'][name]; identity = selection['quarantine_network_id']
        require(identity in groups and selection['domain_key'] in domains, 'Unobserved member network/domain')
        r = groups[identity]; used.add(identity)
        require(r['segment_path'] == domains[selection['domain_key']]['segment_path'], 'VM network belongs to a different owned domain')
        nics = [d for d in vms[member['vm_id']]['config']['hardware']['device'] if d['_typeName'] == 'VirtualVmxnet3']
        require(nics, 'Native NIC coverage required')
        for nic in nics:
            backing = nic['backing']
            require(backing['_typeName'] == 'VirtualEthernetCardDistributedVirtualPortBackingInfo', 'Campaign requires NSX-backed distributed ports')
            port = backing['port']
            require((port['switchUuid'], port['portgroupKey']) == pg.backing_key(r), 'NIC backing differs from assigned domain network')
    require(used == set(groups), 'Unused or incomplete portgroup coverage')


def bind_attachments(scope, workloads, outputs, network, portgroups, domain_outputs, inputs):
    ports.validate(portgroups)
    bind(scope, workloads, outputs, network, ports.group_manifest(portgroups), domain_outputs, inputs)
    selected = {(p['dvsUuid'], p['portgroupKey'], p['key']): p for r in portgroups['resources'] for p in r['ports']}
    used = set()
    for resource in workloads['resources']:
        vm = resource['expected']
        for nic in vm['config']['hardware']['device']:
            if nic['_typeName'] != 'VirtualVmxnet3': continue
            backing = nic['backing']['port']; key = (backing['switchUuid'], backing['portgroupKey'], backing['portKey'])
            require(key in selected and key not in used, 'Every VM NIC requires one unique observed port')
            used.add(key); port = selected[key]; entity = port['connectee']
            ports.cookie(backing.get('connectionCookie'))
            require(port['connectionCookie'] == backing['connectionCookie'], 'Port connection instance differs from VM backing')
            require(entity['connectedEntity']['value'] == resource['moid'] and entity['nicKey'] == str(nic['key']), 'Port connects to a different VM or NIC')
            require(port['proxyHost']['value'] == vm['runtime']['host']['value'], 'Port host differs from VM runtime')
            require(port['state']['runtimeInfo']['macAddress'] == nic['macAddress'], 'Port runtime MAC differs from VM NIC')
    require(used == set(selected), 'Unassigned port evidence refused')
