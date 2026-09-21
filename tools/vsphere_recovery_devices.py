"""Bind selected existing vSphere devices to pinned-provider plans; never mutate state."""
import json
import re
from tools import readback_core as c, vsphere_observe as vm, vsphere_port_observe as ports, vsphere_network_observe as pg
from tools.run_files import require

SCSI = {'pvscsi': 'ParaVirtualSCSIController', 'lsilogic': 'VirtualLsiLogicController',
        'lsilogic-sas': 'VirtualLsiLogicSASController'}
DISK_FIELDS = {'disk', 'datastore_id', 'storage_policy_id', 'scsi_type', 'scsi_controller_count'}


def bind_disks(after, expected, member):
    """Exact one-controller boot/optional-data layout from the current workload module.

    Provider v2.12.0 DiskSubresource.Read records native key/UUID, datastore,
    relative VMDK path, controller/unit and capacity. Policy IDs and retention
    are plan/input bindings, not native SPBM or recoverability evidence.
    """
    devices = expected['config']['hardware']['device']; vm.devices(devices)
    for field, default, minimum in [('boot_disk_gib', 40, 1), ('data_disk_gib', 0, 0)]:
        require(type(member.get(field, default)) is int and member.get(field, default) >= minimum, 'Typed disk size required')
    require(member['scsi_type'] in SCSI and after.get('scsi_type') == member['scsi_type']
            and type(after.get('scsi_controller_count')) is int and after['scsi_controller_count'] == 1,
            'One accepted SCSI controller required')
    controllers = [d for d in devices if d['_typeName'] in set(SCSI.values())]
    require(len(controllers) == 1 and controllers[0]['_typeName'] == SCSI[member['scsi_type']]
            and type(controllers[0].get('busNumber')) is int and controllers[0]['busNumber'] == 0,
            'Native SCSI controller differs from saved plan')
    vm.moid(member['datastore_id'], 'datastore'); c.text(member['storage_policy_id'])
    require(after.get('datastore_id') == member['datastore_id'] and after.get('storage_policy_id') == member['storage_policy_id'],
            'Storage placement differs from sealed inputs')
    sizes = [('disk0', member.get('boot_disk_gib', 40))]
    if member.get('data_disk_gib', 0): sizes.append(('data0', member['data_disk_gib']))
    disks = [d for d in devices if d['_typeName'] == 'VirtualDisk']; planned = after.get('disk')
    require(isinstance(planned, list) and len(planned) == len(disks) == len(sizes)
            and all(isinstance(d, dict) and isinstance(d.get('label'), str) for d in planned), 'Complete retained disk coverage required')
    by_label = {d['label']: d for d in planned}
    require(set(by_label) == {label for label, _ in sizes}, 'Exact owned disk labels required')
    for unit, (label, size) in enumerate(sizes):
        candidates = [d for d in disks if d['controllerKey'] == controllers[0]['key'] and d['unitNumber'] == unit]
        require(len(candidates) == 1, 'Native disk slot differs from owned layout')
        disk = candidates[0]; backing = disk['backing']; plan = by_label[label]
        require(backing.get('thinProvisioned') is True and backing.get('eagerlyScrub') is False
                and backing.get('sharing') == 'sharingNone', 'Explicit thin unshared base disk required')
        match = re.fullmatch(r'\[[^\]\r\n]+\] ([^\r\n]+)', backing['fileName'])
        require(match is not None and not match[1].startswith('/') and all(p not in {'', '.', '..'} for p in match[1].split('/')),
                'Exact relative datastore file required')
        require(disk['capacityInBytes'] == size * 1073741824, 'Native disk size differs from sealed inputs')
        values = dict(key=disk['key'], uuid=backing['uuid'], unit_number=unit, controller_type='scsi',
            size=size, path=match[1], datastore_id=backing['datastore']['value'], disk_mode='persistent',
            thin_provisioned=True, eagerly_scrub=False, keep_on_remove=True, attach=False,
            storage_policy_id=member['storage_policy_id'])
        require(values['datastore_id'] == member['datastore_id'] and not c.differences(plan, values),
                'Saved retained disk differs from native identity or sealed inputs')
        if 'device_address' in plan:
            require(plan['device_address'] == f'scsi:0:{unit}', 'Planned device address differs from native slot')
        if 'disk_sharing' in plan:
            require(plan['disk_sharing'] == backing['sharing'], 'Disk sharing differs')
        if 'write_through' in plan:
            require(type(backing.get('writeThrough')) is bool and plan['write_through'] is backing['writeThrough'],
                    'Disk write-through differs')


def bind_nic(after, expected, member):
    nics = [d for d in expected['config']['hardware']['device'] if d['_typeName'] == 'VirtualVmxnet3']
    planned = after.get('network_interface')
    require(len(nics) == 1 and isinstance(planned, list) and len(planned) == 1 and isinstance(planned[0], dict),
            'One exact existing vmxnet3 NIC required')
    nic = nics[0]; vm.moid(member['quarantine_network_id'], 'dvportgroup')
    require(nic.get('addressType') in {'generated', 'assigned'} and expected['runtime']['powerState'] == 'poweredOn'
            and nic['connectable']['connected'] is True, 'Powered-on connected NIC with native-assigned MAC required')
    require(not c.differences(planned[0], dict(key=nic['key'], mac_address=nic['macAddress'], adapter_type='vmxnet3',
            network_id=member['quarantine_network_id'], use_static_mac=False)), 'Planned NIC differs from native identity or sealed inputs')
    if 'host_system_id' in after:
        require(after['host_system_id'] == expected['runtime']['host']['value'], 'Known host differs from native placement')


def bind_network(inputs, manifest, network):
    """Join vCenter network MoIDs to native switch/portgroup keys and exact occupants."""
    ports.validate(network)
    for key in ('origin', 'operation_id', 'tenant_id', 'scope_id', 'engineering_record_ref', 'target_binding_ref'):
        require(network[key] == manifest[key], 'Attachment evidence scope differs from workload evidence')
    groups = {r['moid']: r for r in network['resources']}; used_groups = set(); used_ports = set(); result = {}
    by_name = {r['expected']['config']['name']: r for r in manifest['resources']}
    require(len(by_name) == len(manifest['resources']) and set(by_name) == set(inputs['members']), 'Exact workload names required')
    for name, member in inputs['members'].items():
        resource = by_name[name]; expected = resource['expected']; network_id = member['quarantine_network_id']
        require(network_id in groups, 'Assigned native network must be observed')
        group = groups[network_id]; used_groups.add(network_id)
        nics = [d for d in expected['config']['hardware']['device'] if d['_typeName'] == 'VirtualVmxnet3']
        require(len(nics) == 1, 'One exact existing NIC required'); nic = nics[0]; backing = nic['backing']
        require(backing['_typeName'] == 'VirtualEthernetCardDistributedVirtualPortBackingInfo', 'Observed NSX distributed backing required')
        port = backing['port']; ports.cookie(port.get('connectionCookie'))
        require((port['switchUuid'], port['portgroupKey']) == pg.backing_key(group), 'Native NIC differs from planned network MoID')
        matches = [p for p in group['ports'] if p['key'] == port['portKey']]
        require(len(matches) == 1, 'Exact native port must be observed'); observed = matches[0]
        identity = (port['switchUuid'], port['portKey']); require(identity not in used_ports, 'Port reused across owned VMs'); used_ports.add(identity)
        require(observed['connectionCookie'] == port['connectionCookie']
                and observed['connectee']['connectedEntity']['value'] == resource['moid']
                and observed['connectee']['nicKey'] == str(nic['key'])
                and observed['proxyHost']['value'] == expected['runtime']['host']['value']
                and observed['state']['runtimeInfo']['macAddress'] == nic['macAddress'], 'Native port occupant differs from VM NIC')
        address = 'module.owned.module.member[' + json.dumps(name) + '].vsphere_virtual_machine.workload'
        result[address] = dict(vm_moid=resource['moid'], network_moid=network_id, nic_key=nic['key'], mac_address=nic['macAddress'],
            switch_uuid=port['switchUuid'], portgroup_key=port['portgroupKey'], port_key=port['portKey'], connection_cookie=port['connectionCookie'])
    require(used_groups == set(groups) and used_ports == {(p['dvsUuid'], p['key']) for r in network['resources'] for p in r['ports']},
            'Unused or incomplete native attachment coverage')
    return result


def check_network_report(network, report, context, current):
    # Explicit adapter selection validates an additional read-only report; it
    # does not let a snapshot satisfy the independent VM/task completion gate.
    from tools import recovery_review
    require(recovery_review.check_report(network, report, current, 300, adapter=ports) == 'READBACK_MATCH_NOT_QUALIFIED',
            'Fresh complete matching native attachments required')
    start = c.timestamp(report['started_at'])
    attempt = max(c.timestamp(context['attempted_at']), c.timestamp(context['last_security_change_at']))
    require(start >= attempt, 'Attachment observation predates attempt or security change')
    return all(recovery_review.valid_control(context[key], network['scope_id'], attempt, start, current, 300)
               for key in ('writer_fence', 'quarantine'))
