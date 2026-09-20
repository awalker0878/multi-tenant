"""Bind selected existing vSphere devices to pinned-provider plans; never mutate state."""
import re
from tools import readback_core as c, vsphere_observe as vm
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
                and backing.get('sharing', '') in {'', 'sharingNone'}, 'Explicit thin unshared base disk required')
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
            require(plan['disk_sharing'] == backing.get('sharing', 'sharingNone'), 'Disk sharing differs')
        if 'write_through' in plan:
            require(type(backing.get('writeThrough')) is bool and plan['write_through'] is backing['writeThrough'],
                    'Disk write-through differs')
