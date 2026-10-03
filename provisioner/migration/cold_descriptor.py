"""Inspect explicit cold-VM capture prerequisites without advertising a VM mover.

No vSphere export, disk-chain capture, target image import or guest remediation
owner is implemented by this descriptor. Only already retained standalone disks
are passed to the mandatory offline image inspection owner. Every returned route
remains unavailable, including an internally consistent descriptor.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence.store import NativeBinding
from provisioner.domain.enterprise_records import validate_record
from provisioner.execution import image_sandbox
from provisioner.execution.run_files import private_path
from provisioner.qualification.directed_mobility import PLAN_METHODS, campaign_implementation_blockers
from provisioner.qualification.mobility import MobilityCampaign

FORMAT = 'hosting-vmware-openstack-cold-descriptor/1'
_SHA = re.compile(r'^[0-9a-f]{64}$')
_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_SCOPE = {'organizationId', 'tenantId', 'securityDomainId', 'endpointId',
          'nativeScopeId', 'locationId', 'platformFamily'}
_DESCRIPTOR_PROFILES = {
    ('vmware-nsx', 'openstack', 'COLD_WHOLE_VM', 'linux-ubuntu-2404'): ('x86_64',),
    ('vmware-nsx', 'openstack', 'COLD_WHOLE_VM', 'windows-server-2022'): ('x86_64',),
}
_PLATFORM = {'vmware': 'vmware-nsx', 'nutanix': 'nutanix', 'openstack': 'openstack'}
_DEVICE_MODELS = {
    'VIRTUAL_NIC': {'e1000', 'e1000e', 'vmxnet3'},
    'VIRTUAL_CONTROLLER': {'lsilogic', 'lsilogic-sas', 'pvscsi', 'sata', 'nvme'},
    'VIRTUAL_DISK': {'vmdk'},
}


class ColdDescriptorHold(ValueError):
    """Declared capture identity, device facts or retained disk are not inspectable."""


def _require(condition, message):
    if not condition:
        raise ColdDescriptorHold(message)


def _keys(value, expected):
    _require(type(value) is dict and set(value) == set(expected), 'Exact cold descriptor fields required')


def _sha(value, *, nullable=False):
    _require(nullable and value is None or isinstance(value, str) and _SHA.fullmatch(value),
             'Exact cold descriptor digest required')


def _id(value):
    _require(isinstance(value, str) and _ID.fullmatch(value), 'Bounded cold descriptor identity required')


def _path(value):
    _require(isinstance(value, str) and value and len(value) <= 512,
             'Explicit relative retained disk path required')
    path = PurePosixPath(value)
    _require(not path.is_absolute() and '..' not in path.parts and str(path) == value,
             'Canonical relative retained disk path required')
    return value


def _scope(value):
    _keys(value, _SCOPE)
    scope = PlanScope.from_record(value)
    _require(scope.platform_family in _PLATFORM and len(scope.native_scope_id) <= 512,
             'Exact supported native scope required')
    return scope


def _binding(value, scope):
    binding = NativeBinding.from_record(value)
    _require((binding.platform_family, binding.endpoint_id, binding.native_scope_id, binding.resource_kind) ==
             (scope.platform_family, scope.endpoint_id, scope.native_scope_id, 'vm'),
             'Cold VM capture belongs to another native scope')
    return binding


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


@dataclass(frozen=True, init=False)
class ColdCaptureDescriptor:
    """Immutable parsed capture declaration, never authenticated export evidence."""
    canonical_json: str
    campaign_digest: str

    def __init__(self, *args, **kwargs):
        raise TypeError('Parse the explicit cold descriptor and canonical plan through from_record')

    @classmethod
    def from_record(cls, value: dict, campaign: MobilityCampaign, plan: dict):
        _require(isinstance(campaign, MobilityCampaign), 'Exact directed mobility campaign required')
        _keys(value, {'format', 'campaignDigest', 'source', 'destination', 'sourceBinding',
                      'capture', 'guest', 'disks'})
        _require(value['format'] == FORMAT and value['campaignDigest'] == campaign.digest,
                 'Cold descriptor version or directed campaign binding differs')
        profile = _DESCRIPTOR_PROFILES.get((campaign.source.platform, campaign.destination.platform,
                                            campaign.method, campaign.guest_profile))
        _require(profile is not None, 'No explicit cold descriptor profile for this direction/method/guest')
        _require(not validate_record(plan) and plan['kind'] == 'MigrationPlan' and
                 plan['metadata']['planDigest'] == campaign.plan_digest and
                 plan['spec']['workloadId'] == campaign.workload_id and
                 PLAN_METHODS.get(plan['spec']['route']['method']) == campaign.method and
                 plan['spec']['route']['guestProfile'] == campaign.guest_profile,
                 'Exact canonical cold migration plan and guest binding required')
        _require(value['source'] == plan['spec']['source'] and value['destination'] == plan['spec']['destination'],
                 'Cold descriptor native scopes differ from the selected plan')
        source, destination = _scope(value['source']), _scope(value['destination'])
        _require((_PLATFORM[source.platform_family], _PLATFORM[destination.platform_family]) ==
                 (campaign.source.platform, campaign.destination.platform), 'Cold descriptor direction differs')
        _require((source.organization_id, source.tenant_id) ==
                 (destination.organization_id, destination.tenant_id), 'Cold capture crosses the selected tenant')
        _binding(value['sourceBinding'], source)
        mappings = [row for row in plan['spec']['machineMappings']
                    if row['sourceBinding'] == value['sourceBinding']]
        _require(len(mappings) == 1, 'Cold descriptor VM is not selected by the canonical plan')
        capture = value['capture']
        _keys(capture, {'snapshotId', 'capturedAt', 'sourceObservationDigest', 'powerState',
                        'writerFenceDigest', 'nativeTaskIds', 'nativeTaskState',
                        'nativeTaskObservationDigest', 'snapshotChainComplete'})
        _id(capture['snapshotId'])
        _require(capture['snapshotId'] == plan['spec']['sourceSnapshotId'],
                 'Cold capture snapshot differs from selected source observation')
        at = datetime.fromisoformat(capture['capturedAt'].replace('Z', '+00:00'))
        _require(at.tzinfo is not None, 'Cold capture time must be aware')
        _sha(capture['sourceObservationDigest'])
        _sha(capture['writerFenceDigest'], nullable=True)
        _sha(capture['nativeTaskObservationDigest'], nullable=True)
        _require(capture['powerState'] in {'POWERED_OFF', 'POWERED_ON', 'UNKNOWN'} and
                 capture['nativeTaskState'] in {'QUIESCED', 'IN_FLIGHT', 'UNKNOWN'} and
                 type(capture['snapshotChainComplete']) is bool,
                 'Explicit power/task/chain facts required')
        tasks = capture['nativeTaskIds']
        _require(isinstance(tasks, list) and len(tasks) <= 512 and len(tasks) == len(set(tasks)) and
                 all(isinstance(item, str) and 1 <= len(item) <= 512 for item in tasks),
                 'Exact native task identity inventory required')
        guest = value['guest']
        _keys(guest, {'profile', 'architecture', 'firmware', 'secureBoot', 'bootDiskId',
                      'devicesComplete', 'devices', 'driverEvidenceDigest', 'remediationPlanDigest'})
        _require(guest['profile'] == campaign.guest_profile and guest['architecture'] in profile and
                 guest['firmware'] in {'BIOS', 'UEFI', 'UNKNOWN'} and
                 (type(guest['secureBoot']) is bool or guest['secureBoot'] == 'UNKNOWN') and
                 type(guest['devicesComplete']) is bool,
                 'Exact guest, architecture and known-or-unknown boot/device facts required')
        _id(guest['bootDiskId'])
        _sha(guest['driverEvidenceDigest'], nullable=True)
        _sha(guest['remediationPlanDigest'], nullable=True)
        _require(isinstance(guest['devices'], list) and 1 <= len(guest['devices']) <= 256,
                 'Explicit bounded virtual device inventory required')
        devices = set()
        for row in guest['devices']:
            _keys(row, {'deviceId', 'kind', 'model', 'backingId'})
            _id(row['deviceId'])
            _require(row['deviceId'] not in devices and isinstance(row['kind'], str) and
                     isinstance(row['model'], str) and 1 <= len(row['model']) <= 128 and
                     isinstance(row['backingId'], str) and 1 <= len(row['backingId']) <= 512,
                     'Duplicate or unknown device identity')
            devices.add(row['deviceId'])
        disks, slots, paths = set(), set(), set()
        _require(isinstance(value['disks'], list) and 1 <= len(value['disks']) <= 64,
                 'Explicit bounded retained disk inventory required')
        for row in value['disks']:
            _keys(row, {'diskId', 'slot', 'path', 'format', 'virtualSize', 'sha256',
                        'standalone', 'encrypted', 'chain'})
            _id(row['diskId']); _path(row['path']); _sha(row['sha256'])
            _require(row['diskId'] not in disks and type(row['slot']) is int and 0 <= row['slot'] < 64
                     and row['slot'] not in slots and row['path'] not in paths,
                     'Duplicate disk identity, slot or retained path')
            disks.add(row['diskId']); slots.add(row['slot']); paths.add(row['path'])
            _require(row['format'] in {'raw', 'qcow2', 'vmdk', 'vdi'} and type(row['virtualSize']) is int
                     and 1 <= row['virtualSize'] <= 64 * 1024**4 and type(row['standalone']) is bool
                     and (type(row['encrypted']) is bool or row['encrypted'] == 'UNKNOWN'),
                     'Exact retained format, size, chain and encryption facts required')
            _require(isinstance(row['chain'], list) and 1 <= len(row['chain']) <= 128,
                     'Complete retained disk-chain manifest required')
            native_ids = set()
            for link in row['chain']:
                _keys(link, {'nativeId', 'parentNativeId', 'sha256'})
                _sha(link['sha256'])
                _require(isinstance(link['nativeId'], str) and 1 <= len(link['nativeId']) <= 512 and
                         link['nativeId'] not in native_ids and (link['parentNativeId'] is None or
                         isinstance(link['parentNativeId'], str) and 1 <= len(link['parentNativeId']) <= 512),
                         'Duplicate or invalid native disk-chain identity')
                native_ids.add(link['nativeId'])
            _require(row['chain'][-1]['sha256'] == row['sha256'], 'Retained disk bytes do not bind chain tip')
            _require(row['chain'][0]['parentNativeId'] is None and all(
                current['parentNativeId'] == previous['nativeId']
                for previous, current in zip(row['chain'], row['chain'][1:])),
                'Native disk-chain lineage is incomplete or cyclic')
        _require(guest['bootDiskId'] in disks, 'Declared boot disk is absent from retained disk inventory')
        _require(disks == {row['diskId'] for row in mappings[0]['diskMappings']},
                 'Retained disk set differs from selected canonical VM mapping')
        result = object.__new__(cls)
        object.__setattr__(result, 'canonical_json', _canonical(value).decode('utf-8'))
        object.__setattr__(result, 'campaign_digest', campaign.digest)
        return result

    @property
    def digest(self):
        return hashlib.sha256(self.canonical_json.encode('utf-8')).hexdigest()

    def to_dict(self):
        return json.loads(self.canonical_json)


def inspection_blockers(descriptor: ColdCaptureDescriptor, *, as_of: datetime):
    """Fail before parsing a disk if capture/device/boot dependencies are unknown."""
    _require(isinstance(descriptor, ColdCaptureDescriptor) and isinstance(as_of, datetime)
             and as_of.tzinfo is not None, 'Parsed cold descriptor and aware inspection time required')
    value = descriptor.to_dict(); capture, guest = value['capture'], value['guest']
    blocks = set()
    at = datetime.fromisoformat(capture['capturedAt'].replace('Z', '+00:00'))
    if at > as_of:
        blocks.add('COLD_CAPTURE_OBSERVATION_IN_FUTURE')
    if capture['powerState'] != 'POWERED_OFF' or capture['writerFenceDigest'] is None:
        blocks.add('COLD_SOURCE_WRITER_EXCLUSION_UNPROVEN')
    if capture['nativeTaskState'] != 'QUIESCED' or capture['nativeTaskObservationDigest'] is None:
        blocks.add('COLD_NATIVE_TASK_QUIESCENCE_UNPROVEN')
    if not capture['snapshotChainComplete']:
        blocks.add('COLD_SNAPSHOT_CHAIN_INCOMPLETE')
    if guest['firmware'] == 'UNKNOWN' or guest['secureBoot'] == 'UNKNOWN':
        blocks.add('COLD_BOOT_DEPENDENCIES_UNKNOWN')
    if not guest['devicesComplete']:
        blocks.add('COLD_DEVICE_INVENTORY_INCOMPLETE')
    if guest['driverEvidenceDigest'] is None or guest['remediationPlanDigest'] is None:
        blocks.add('COLD_GUEST_DRIVER_OR_REMEDIATION_DEPENDENCY_UNBOUND')
    for device in guest['devices']:
        if device['model'] not in _DEVICE_MODELS.get(device['kind'], set()):
            blocks.add('COLD_DEVICE_OR_MODEL_UNSUPPORTED')
    for disk in value['disks']:
        if disk['encrypted'] is not False:
            blocks.add('COLD_ENCRYPTED_OR_UNKNOWN_DISK_UNSUPPORTED')
        if not disk['standalone'] or len(disk['chain']) != 1:
            blocks.add('COLD_DISK_CHAIN_REQUIRES_NATIVE_CONSOLIDATION')
    return sorted(blocks)


def inspect_retained_disks(descriptor: ColdCaptureDescriptor, campaign: MobilityCampaign,
                           source_root: Path, destination: Path, *, tools: image_sandbox.SandboxToolchain,
                           limits: image_sandbox.ImageLimits, as_of: datetime,
                           runner=subprocess.run):
    """Inspect retained standalone files through the mandatory sandbox owner."""
    _require(isinstance(campaign, MobilityCampaign) and descriptor.campaign_digest == campaign.digest,
             'Cold inspection belongs to another directed campaign')
    blocks = inspection_blockers(descriptor, as_of=as_of)
    native_blocks = campaign_implementation_blockers(campaign)
    receipts = []
    if not blocks:
        source_root = private_path(source_root, directory=True)
        destination = Path(destination)
        _require(not destination.exists() and not destination.is_symlink(), 'New private inspection directory required')
        private_path(destination.parent, directory=True)
        destination.mkdir(mode=0o700)
        for row in descriptor.to_dict()['disks']:
            source = private_path(source_root / row['path'])
            receipt = image_sandbox.inspect(source, destination / row['diskId'], source_sha256=row['sha256'],
                input_format=row['format'], tools=tools, limits=limits, runner=runner)
            _require(receipt['virtualSize'] == row['virtualSize'], 'Observed virtual extent differs from cold descriptor')
            receipts.append({'diskId': row['diskId'], 'slot': row['slot'], 'receipt': receipt})
    return {'format': 'hosting-cold-descriptor-inspection/1',
            'descriptorDigest': descriptor.digest, 'campaignDigest': campaign.digest,
            'status': 'COLD_DESCRIPTOR_HELD' if blocks else 'RETAINED_DISKS_INSPECTED_ROUTE_UNAVAILABLE',
            'inspectionBlockers': blocks, 'nativeImplementationBlockers': native_blocks,
            'diskInspections': receipts, 'captureAuthenticated': False, 'capturePerformed': False,
            'nativeContact': False, 'conversionPerformed': False, 'targetImported': False,
            'guestBootQualified': False, 'mutationAuthorized': False}
