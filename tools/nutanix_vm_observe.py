#!/usr/bin/env python3
"""GET-only AHV v4.2 VM snapshots; no task completion, Flow or HA claims.

The selected wire fields follow the vmm-go-client/v4.2.2 SDK pinned by the
Nutanix 2.4.2 provider. Unknown/omitted fields never acquire guessed defaults.
"""
from pathlib import Path
import re
import sys
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import require

PROFILE = 'nutanix-ahv-v4.2-vm-snapshot'
TYPE = 'vmm.v4.ahv.config.'
FIELDS = {'extId', '$objectType', 'tenantId', 'name', 'host', 'cluster', 'project',
          'categories', 'powerState', 'numSockets', 'numCoresPerSocket',
          'memorySizeBytes', 'isCrossClusterMigrationInProgress', 'nics', 'disks'}


def uuid(value):
    require(isinstance(value, str) and c.UUID.fullmatch(value), 'Exact native UUID required')


def reference(value):
    c.exact_keys(value, {'extId'}); uuid(value['extId'])


def collection(value, maximum=64):
    require(isinstance(value, list) and 1 <= len(value) <= maximum, 'Explicit bounded collection required')


def integer(value):
    require(type(value) is int and value > 0, 'Positive integer required')


def validate(m):
    c.common_manifest(m, 'nutanix')
    require(m['profile'] == PROFILE and 'task' not in m, 'AHV snapshot profile cannot claim task completion')
    ids = set(); tenant_ids = set()
    for r in m['resources']:
        c.exact_keys(r, {'kind', 'ext_id', 'expected', 'expected_etag'})
        uuid(r['ext_id']); require(r['kind'] == 'vm' and r['ext_id'] not in ids, 'Unique VM selector required')
        ids.add(r['ext_id']); e = r['expected']; c.exact_keys(e, FIELDS)
        require(e['extId'] == r['ext_id'] and e['$objectType'] == TYPE + 'Vm', 'VM identity differs')
        uuid(e['tenantId']); tenant_ids.add(e['tenantId']); c.text(e['name'], length=256)
        for key in ('host', 'cluster', 'project'): reference(e[key])
        collection(e['categories']); categories = []
        for item in e['categories']: reference(item); categories.append(item['extId'])
        require(len(categories) == len(set(categories)), 'Duplicate security category')
        require(e['powerState'] in ('ON', 'OFF') and e['isCrossClusterMigrationInProgress'] is False,
                'Stable explicit power and migration expectations required')
        for key in ('numSockets', 'numCoresPerSocket', 'memorySizeBytes'): integer(e[key])
        collection(e['nics'], 32); nics = []
        for nic in e['nics']:
            c.exact_keys(nic, {'extId', 'nicBackingInfo', 'nicNetworkInfo'}); uuid(nic['extId']); nics.append(nic['extId'])
            backing = nic['nicBackingInfo']; c.exact_keys(backing, {'$objectType', 'isConnected', 'macAddress', 'model'})
            require(backing['$objectType'] == TYPE + 'VirtualEthernetNic' and type(backing['isConnected']) is bool
                    and backing['model'] in ('VIRTIO', 'E1000'), 'Explicit emulated NIC backing required')
            require(isinstance(backing['macAddress'], str) and re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', backing['macAddress']), 'Exact MAC required')
            network = nic['nicNetworkInfo']; c.exact_keys(network, {'$objectType', 'nicType', 'subnet', 'ipv4Config'})
            require(network['$objectType'] == TYPE + 'VirtualEthernetNicNetworkInfo' and network['nicType'] == 'NORMAL_NIC', 'Normal subnet NIC required')
            reference(network['subnet']); ip = network['ipv4Config']
            c.exact_keys(ip, {'shouldAssignIp', 'ipAddress', 'secondaryIpAddressList'})
            require(ip['shouldAssignIp'] is True and ip['secondaryIpAddressList'] == [], 'One explicit assigned IPv4 required')
            c.exact_keys(ip['ipAddress'], {'value', 'prefixLength'})
            from ipaddress import IPv4Address
            require(isinstance(ip['ipAddress']['value'], str), 'Exact IPv4 string required')
            address = IPv4Address(ip['ipAddress']['value'])
            require(not (address.is_unspecified or address.is_multicast or address.is_loopback or address.is_link_local)
                    and type(ip['ipAddress']['prefixLength']) is int and 1 <= ip['ipAddress']['prefixLength'] <= 32, 'Unicast IPv4/prefix required')
        require(len(nics) == len(set(nics)), 'Duplicate NIC')
        collection(e['disks']); disks = []; backings = []; slots = []
        for disk in e['disks']:
            c.exact_keys(disk, {'extId', 'diskAddress', 'backingInfo'}); uuid(disk['extId']); disks.append(disk['extId'])
            slot = disk['diskAddress']; c.exact_keys(slot, {'busType', 'index'})
            require(slot['busType'] in ('SCSI', 'SATA', 'IDE', 'PCI') and type(slot['index']) is int and slot['index'] >= 0, 'Exact disk slot required')
            slots.append((slot['busType'], slot['index']))
            backing = disk['backingInfo']; c.exact_keys(backing, {'$objectType', 'diskExtId', 'diskSizeBytes', 'storageContainer', 'isMigrationInProgress'})
            require(backing['$objectType'] == TYPE + 'VmDisk' and backing['isMigrationInProgress'] is False, 'Stable VM disk required')
            uuid(backing['diskExtId']); backings.append(backing['diskExtId'])
            integer(backing['diskSizeBytes']); reference(backing['storageContainer'])
        require(all(len(items) == len(set(items)) for items in (disks, backings, slots)), 'Duplicate disk identity or slot')
        require(isinstance(r['expected_etag'], str) and len(r['expected_etag']) <= 512
                and re.fullmatch(r'"[\x21\x23-\x7e]+"', r['expected_etag']), 'Accepted strong ETag required')
    require(len(tenant_ids) == 1, 'Native tenant scope must be singular')


def resource_target(resource):
    return '/api/vmm/v4.2/ahv/config/vms/' + resource['ext_id']


def targets(m):
    validate(m)
    return {resource_target(r) for r in m['resources']}


def selected(actual, expected):
    """Omit unselected dictionary keys from evidence digests, including guest data."""
    if isinstance(actual, dict) and isinstance(expected, dict):
        return {key: selected(actual[key], value) for key, value in expected.items() if key in actual}
    if isinstance(actual, list) and isinstance(expected, list):
        # Preserve unexpected list members as a count/type mismatch without hashing their bodies.
        return [selected(item, expected[i]) if i < len(expected) else None for i, item in enumerate(actual)]
    return actual


def sample(m, client):
    result = []
    for resource in m['resources']:
        body, etag = client.get(resource_target(resource)); data = body.get('data')
        if not isinstance(data, dict): raise c.ObservationError('VM_BODY_MISSING')
        actual = selected(data, resource['expected'])
        mismatch = c.differences(actual, resource['expected'])
        identity = not c.differences(actual, {key: resource['expected'][key] for key in ('extId', '$objectType', 'tenantId')})
        if etag is None: mismatch.append('/ETag:missing')
        elif etag != resource['expected_etag']: mismatch.append('/ETag:value')
        config = 'UNKNOWN' if not identity or any(x.endswith((':missing', ':type')) for x in mismatch) else ('DIFFERENT' if mismatch else 'MATCH')
        result.append({'resource_key': resource['ext_id'], 'identity_match': identity, 'config_status': config,
            'mismatch_fields': mismatch, 'config_sha256': c.digest(actual), 'etag_sha256': c.digest(etag),
            'progress': 'COMPLETE', 'reason': 'VM_SNAPSHOT_ONLY_TASK_NOT_OBSERVED', 'task_completion_observed': False})
    return result


if __name__ == '__main__':
    from tools.readback_cli import run
    raise SystemExit(run(sys.modules[__name__], 'NUTANIX'))
