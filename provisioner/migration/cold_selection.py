"""One immutable VMware snapshot to private Glance image selection.

This is a lower-owner contract. Capturing/importing disks does not establish a
bootable guest, remediate drivers, or admit the whole cold migration method.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlsplit

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence.store import NativeBinding, canonical_record_digest
from provisioner.domain.enterprise_records import validate_record
from provisioner.execution import image_sandbox, readback_core as c, vsphere_observe as vm
from provisioner.execution.run_files import encoded, load_private, private_path, require
from provisioner.migration.resources import LinuxTransferResources, TransferLimits
from provisioner.migration.vsphere_credentials import VsphereNativeCredentialProfile

FORMAT = 'hosting-vmware-openstack-cold-selection/1'
DRIVER = 'vmware-openstack-cold-capture/1'
PHASES = frozenset({'CREATE', 'UPLOAD'})
_PROFILES = frozenset({'linux-ubuntu-2404', 'windows-server-2022'})
_ROUTE = ('vmware', 'openstack')
_SCOPE_FIELDS = frozenset({'organizationId','tenantId','securityDomainId','endpointId',
                           'nativeScopeId','locationId','platformFamily'})
_BACKINGS = frozenset({'VirtualDiskFlatVer2BackingInfo', 'VirtualDiskSparseVer2BackingInfo',
                       'VirtualDiskSeSparseBackingInfo'})
_SCSI = frozenset({'ParaVirtualSCSIController', 'VirtualLsiLogicController',
                   'VirtualLsiLogicSASController'})


def _exact(value, fields):
    require(type(value) is dict and value.keys() == fields, 'Exact cold owner fields required')


def _sha(value):
    require(type(value) is str and c.HEX.fullmatch(value), 'Exact cold owner SHA-256 required')


def _id(value):
    require(type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', value),
            'Bounded exact cold owner identity required')


def _scope(value):
    _exact(value, _SCOPE_FIELDS)
    return PlanScope.from_record(value)


def service_endpoint(value, suffix):
    """An approved fixed HTTPS service endpoint, with no caller query or path."""
    require(type(value) is str and len(value) <= 512 and '\\' not in value
            and not any(character.isspace() for character in value), 'Exact HTTPS service endpoint required')
    address = urlsplit(value)
    origin = c.origin('https://' + address.netloc)
    require(address.scheme == 'https' and address.path == suffix and not address.query
            and not address.fragment and value == origin + suffix,
            'The service endpoint differs from its fixed native protocol')
    return value


def backing_chain(backing):
    """Retain actual snapshot head-to-base native backing identities, never files.

    The pinned API's optional absent parent terminates a chain. It does not mean
    a missing snapshot, device inventory, checksum, or encryption check passed.
    """
    result, names = [], set()
    while backing is not None:
        require(type(backing) is dict and len(result) < 64 and
                backing.get('_typeName') in _BACKINGS and backing.get('diskMode') == 'persistent'
                and backing.get('sharing') == 'sharingNone' and backing.get('keyId') is None,
                'Encrypted, shared, raw-device or nonpersistent snapshot disk is unsupported')
        name = c.text(backing.get('fileName'), length=1024)
        match = re.fullmatch(r'\[[^\]\r\n]+\] ([^\r\n]+)', name)
        require(match is not None and not match[1].startswith('/') and
                all(part not in {'', '.', '..'} for part in match[1].split('/')) and name not in names,
                'The native snapshot disk lineage is invalid or cyclic')
        vm.reference(backing.get('datastore'), 'Datastore', 'datastore')
        require(backing.get('uuid') is not None, 'Every native disk-chain link needs its actual UUID')
        c.text(backing['uuid'], length=128)
        names.add(name)
        result.append({'fileName': name, 'uuid': backing['uuid'],
                       'datastore': backing['datastore'], 'type': backing['_typeName']})
        backing = backing.get('parent')
    require(bool(result) and result[-1]['type'] == 'VirtualDiskFlatVer2BackingInfo',
            'Snapshot chain must terminate at one known persistent native base disk')
    return result


def capture_configuration(config):
    """Complete hardware plus explicit boot/key facts; unknown devices hold."""
    c.exact_keys(config, vm.CONFIG | {'firmware','bootOptions'}, {'keyId'})
    require(config['_typeName'] == 'VirtualMachineConfigInfo' and config['template'] is False
            and config.get('keyId') is None and config['firmware'] in {'bios','efi'},
            'The selected snapshot needs an unencrypted non-template supported firmware')
    for field in ('uuid','instanceUuid'):
        require(type(config[field]) is str and c.UUID.fullmatch(config[field]), 'Actual native VM UUID required')
    c.text(config['name'], length=256); c.text(config['changeVersion'])
    boot = config['bootOptions']
    require(type(boot) is dict and type(boot.get('efiSecureBootEnabled')) is bool
            and (config['firmware'] == 'efi' or boot['efiSecureBootEnabled'] is False),
            'Explicit native secure-boot state required')
    hardware = config['hardware']
    c.exact_keys(hardware, {'numCPU','numCoresPerSocket','memoryMB','device'}, {'_typeName'})
    require(all(type(hardware[key]) is int and hardware[key] > 0
                for key in ('numCPU','numCoresPerSocket','memoryMB')) and
            hardware['numCPU'] % hardware['numCoresPerSocket'] == 0, 'Complete integral hardware topology required')
    devices = hardware['device']
    require(type(devices) is list and 1 <= len(devices) <= 64, 'Complete bounded native hardware required')
    keys, slots, disks = set(), set(), []
    for device in devices:
        require(type(device) is dict and device.get('_typeName') in vm.DEVICES and
                type(device.get('key')) is int and device['key'] >= 0 and device['key'] not in keys,
                'Passthrough, vTPM, duplicate or unknown native device is unsupported')
        keys.add(device['key'])
        if device['_typeName'] in _SCSI:
            require(device.get('sharedBus') == 'noSharing', 'Native shared SCSI bus is unsupported')
        if device['_typeName'] == 'VirtualDisk':
            require(type(device.get('capacityInBytes')) is int and type(device.get('capacityInKB')) is int
                    and 0 < device['capacityInBytes'] == device['capacityInKB'] * 1024
                    and type(device.get('controllerKey')) is int and type(device.get('unitNumber')) is int
                    and device['unitNumber'] >= 0, 'Exact native disk capacity and slot required')
            slot = device['controllerKey'], device['unitNumber']
            require(slot not in slots, 'Native disk slot is duplicated'); slots.add(slot)
            backing_chain(device.get('backing')); disks.append(device)
    require(1 <= len(disks) <= 16, 'The complete selected VM disk inventory is required')
    for disk in disks:
        require(any(device['key'] == disk['controllerKey'] and device['_typeName'] in _SCSI
                    for device in devices), 'Only exact reviewed unshared SCSI disk controllers are captured')
    return tuple(disks)


@dataclass(frozen=True)
class ColdVmSelection:
    canonical: bytes

    def __post_init__(self):
        require(type(self.canonical) is bytes and len(self.canonical) <= 4 * 1024 * 1024,
                'A bounded immutable cold selection is required')
        value = c.strict_loads(self.canonical)
        _exact(value, {'format','guest_profile','workload_id','workload_revision','source_scope',
                       'destination_scope','source_snapshot_id','resource_bundle_sha256','vm',
                       'source_contact','destination_contact','export','disks','sandbox',
                       'source_pool_id','image_pool_id','capture_resources'})
        require(encoded(value) == self.canonical and value['format'] == FORMAT
                and value['guest_profile'] in _PROFILES and type(value['workload_revision']) is int
                and value['workload_revision'] > 0, 'Exact supported cold selection version required')
        _id(value['workload_id']); _id(value['source_snapshot_id']); _sha(value['resource_bundle_sha256'])
        _id(value['source_pool_id']); _id(value['image_pool_id'])
        source, destination = _scope(value['source_scope']), _scope(value['destination_scope'])
        require((source.platform_family,destination.platform_family) == _ROUTE and
                (source.organization_id,source.tenant_id) == (destination.organization_id,destination.tenant_id),
                'Only the explicit same-tenant VMware snapshot to Glance owner exists')
        selected = value['vm']
        _exact(selected, {'moid','snapshot_moid','current_config','snapshot_config','runtime','previous_owner'})
        vm.moid(selected['moid'], 'vm'); vm.moid(selected['snapshot_moid'], 'snapshot')
        current, snapshot = capture_configuration(selected['current_config']), capture_configuration(selected['snapshot_config'])
        require((selected['current_config']['uuid'],selected['current_config']['instanceUuid']) ==
                (selected['snapshot_config']['uuid'],selected['snapshot_config']['instanceUuid']) and
                {(disk['key'],disk['controllerKey'],disk['unitNumber'],disk['capacityInBytes']) for disk in current} ==
                {(disk['key'],disk['controllerKey'],disk['unitNumber'],disk['capacityInBytes']) for disk in snapshot},
                'The selected snapshot belongs to another VM or disk inventory')
        runtime = selected['runtime']; _exact(runtime, vm.RUNTIME)
        require(runtime['_typeName'] == 'VirtualMachineRuntimeInfo' and runtime['connectionState'] == 'connected'
                and runtime['powerState'] == 'poweredOff' and runtime['faultToleranceState'] in {'notConfigured','disabled'}
                and all(runtime[field] is False for field in ('paused','vmFailoverInProgress','consolidationNeeded')),
                'Cold capture requires an independently excluded stable powered-off VM')
        vm.reference(runtime['host'], 'HostSystem', 'host')
        previous = selected['previous_owner']; _exact(previous, {'worker_id','owner_epoch','incident_id'})
        _id(previous['worker_id']); _id(previous['incident_id'])
        require(type(previous['owner_epoch']) is int and previous['owner_epoch'] > 0,
                'Exact original source writer epoch required')
        contact = value['source_contact']
        _exact(contact, {'vcenter_origin','vcenter_ca_sha256','nfc_origins','nfc_ca_sha256',
                         'writer_credential_profile','reader_credential_profile'})
        require(contact['vcenter_origin'] == c.origin(contact['vcenter_origin']), 'Exact approved vCenter origin required')
        _sha(contact['vcenter_ca_sha256']); _sha(contact['nfc_ca_sha256'])
        require(type(contact['nfc_origins']) is list and 1 <= len(contact['nfc_origins']) <= 16
                and len(set(contact['nfc_origins'])) == len(contact['nfc_origins'])
                and all(origin == c.origin(origin) for origin in contact['nfc_origins']),
                'Every native NFC HTTPS origin must be separately approved')
        profiles=[]
        for field in ('writer_credential_profile','reader_credential_profile'):
            _exact(contact[field],{'origin','datacenter_id','session_manager_id','authorization_manager_id','principal'})
            profile=VsphereNativeCredentialProfile(**contact[field]);profiles.append(profile)
            require(profile.origin == contact['vcenter_origin'] and profile.datacenter_id == source.native_scope_id,
                    'Every native credential profile needs its exact approved actual datacenter scope')
        require(profiles[0].principal != profiles[1].principal,
                'Native capture acceptance needs an independently commissioned reader principal')
        target = value['destination_contact']
        _exact(target, {'identity_endpoint','glance_endpoint','region','interface','cloud_alias','ca_sha256'})
        service_endpoint(target['identity_endpoint'], '/v3'); service_endpoint(target['glance_endpoint'], '/v2')
        require(target['interface'] in {'public','internal'}, 'Exact approved catalogue interface required')
        for field in ('region','cloud_alias'): _id(target[field])
        _sha(target['ca_sha256'])
        steps, operations, leases = set(), set(), set()
        rows = [value['export']]
        require(type(value['disks']) is list and len(value['disks']) == len(snapshot),
                'Every actual snapshot disk needs its own selected image')
        ids, keys, nfc_keys, images = set(), set(), set(), set()
        for row in value['disks']:
            _exact(row, {'disk_id','device_key','nfc_key','logical_image_id','max_export_bytes','max_output_bytes','phases'})
            for field, seen in (('disk_id',ids),('nfc_key',nfc_keys),('logical_image_id',images)):
                _id(row[field]); require(row[field] not in seen, 'Cold image identities cannot be duplicated'); seen.add(row[field])
            require(type(row['device_key']) is int and row['device_key'] not in keys,
                    'Each native snapshot disk needs its exact device key'); keys.add(row['device_key'])
            require(all(type(row[field]) is int and 1 <= row[field] <= 64 * 1024**4
                        for field in ('max_export_bytes','max_output_bytes')), 'Bounded captured/imported image bytes required')
            _exact(row['phases'], PHASES); rows.extend(row['phases'].values())
        require(keys == {disk['key'] for disk in snapshot}, 'Selected native disk keys are incomplete or foreign')
        for row in rows:
            _exact(row, {'step_id','operation_id','lease_key'})
            for field, seen in (('step_id',steps),('operation_id',operations),('lease_key',leases)):
                _id(row[field]); require(row[field] not in seen, 'Cold actions cannot share an original intent or lease'); seen.add(row[field])
        sandbox = value['sandbox']; _exact(sandbox, {'tools','limits'})
        tools = sandbox['tools']
        _exact(tools, {'bwrap','qemu_img','prlimit','bwrap_sha256','qemu_img_sha256','prlimit_sha256'})
        for field in ('bwrap','qemu_img','prlimit'):
            require(type(tools[field]) is str and Path(tools[field]).is_absolute(), 'Exact reviewed sandbox tool path required')
            _sha(tools[field+'_sha256'])
        limits = image_sandbox.ImageLimits(**sandbox['limits'])
        require(all(row['max_export_bytes'] <= limits.max_input_bytes and
                    row['max_output_bytes'] <= limits.max_virtual_bytes + 16 * 1024**2 for row in value['disks']),
                'Selected image extents exceed mandatory sandbox ceilings')
        controls = value['capture_resources']
        _exact(controls, {'stage_parent','cgroup','block_device','limits'})
        resources = LinuxTransferResources(Path(controls['stage_parent']),controls['cgroup'],
                                          controls['block_device'],TransferLimits(**controls['limits']))
        require(resources.limits.expected_bytes == sum(2*row['max_export_bytes']+row['max_output_bytes']
                                                        for row in value['disks']),
                'Captured originals, isolated input copies and converted outputs need additive staging')

    @classmethod
    def from_record(cls, value):
        return cls(encoded(value))

    @property
    def sha256(self):
        return canonical_record_digest(self.to_dict())

    def to_dict(self):
        return c.strict_loads(self.canonical)

    def disk(self, disk_id):
        found = [row for row in self.to_dict()['disks'] if row['disk_id'] == disk_id]
        require(len(found) == 1, 'The exact approved cold disk is unavailable')
        return found[0]

    def binding(self):
        value = self.to_dict(); scope = _scope(value['source_scope'])
        return NativeBinding(scope.platform_family,scope.endpoint_id,scope.native_scope_id,'vm',value['vm']['moid'])

    def require_plan(self, plan, artifact):
        value = self.to_dict()
        require(type(plan) is dict and not validate_record(plan) and plan.get('kind') == 'MigrationPlan'
                and (plan['spec']['workloadId'],plan['spec']['workloadRevision'],plan['spec']['source'],
                     plan['spec']['destination'],plan['spec']['sourceSnapshotId']) ==
                    (value['workload_id'],value['workload_revision'],value['source_scope'],
                     value['destination_scope'],value['source_snapshot_id'])
                and plan['spec']['route']['method'] == 'COLD_VM_CONVERSION'
                and plan['spec']['route']['guestProfile'] == value['guest_profile']
                and plan['spec'].get('coldCapture') == {
                    'format':'hosting-cold-capture-purpose/1','selectionDigest':self.sha256}
                and artifact.get('driver') == DRIVER and artifact.get('coldCaptureSelectionDigest') == self.sha256
                and artifact.get('resourceBundleDigest') == value['resource_bundle_sha256'],
                'The current approved cold plan or protected capture selection changed')
        selected = [mapping for mapping in plan['spec']['machineMappings']
                    if NativeBinding.from_record(mapping['sourceBinding']) == self.binding()]
        require(len(selected) == len(plan['spec']['machineMappings']) == 1
                and plan['spec']['selectedMachineIds'] == [selected[0]['machineId']]
                and {row['diskId'] for row in selected[0]['diskMappings']} ==
                {row['disk_id'] for row in value['disks']}, 'The capture differs from exact approved machine/disk mappings')

    def tools_and_limits(self):
        sandbox = self.to_dict()['sandbox']; tools = dict(sandbox['tools'])
        for key in ('bwrap','qemu_img','prlimit'): tools[key] = Path(tools[key])
        return image_sandbox.SandboxToolchain(**tools), image_sandbox.ImageLimits(**sandbox['limits'])

    def transfer_resources(self):
        controls = self.to_dict()['capture_resources']
        return LinuxTransferResources(Path(controls['stage_parent']),controls['cgroup'],
                                      controls['block_device'],TransferLimits(**controls['limits']))


class FileColdSelectionStore:
    def __init__(self, directory):
        self.directory = private_path(directory, directory=True)

    def load_verified(self, sha256):
        _sha(sha256)
        selection = ColdVmSelection.from_record(load_private(self.directory / (sha256 + '.json')))
        require(selection.sha256 == sha256, 'The protected cold selection content changed')
        return selection
