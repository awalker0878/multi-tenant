#!/usr/bin/env python3
"""GET-only vSphere VM snapshots; no inventory discovery, writes or activation."""
from pathlib import Path
import re
import sys
if __package__ in (None, ''): sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import readback_core as c, nutanix_vm_observe as projection
from tools.run_files import require

PROFILE = 'vsphere-vi-json-8.0.3.0-vm-snapshot'
PREFIX = '/sdk/vim25/8.0.3.0/'
CONFIG = {'_typeName', 'uuid', 'instanceUuid', 'name', 'template', 'changeVersion', 'hardware'}
RUNTIME = {'_typeName', 'host', 'connectionState', 'powerState', 'paused', 'vmFailoverInProgress',
           'consolidationNeeded', 'faultToleranceState'}
CONTROLLERS = {'VirtualPCIController', 'VirtualIDEController', 'VirtualPS2Controller', 'VirtualSIOController',
               'ParaVirtualSCSIController', 'VirtualLsiLogicController', 'VirtualLsiLogicSASController', 'VirtualAHCIController'}
DEVICES = CONTROLLERS | {'VirtualVideoCard', 'VirtualVMCIDevice', 'VirtualVmxnet3', 'VirtualDisk'}


def moid(value, prefix):
    require(isinstance(value, str) and re.fullmatch(prefix + r'-[1-9][0-9]{0,15}', value), 'Exact managed object ID required')


def reference(value, kind, prefix):
    c.exact_keys(value, {'type', 'value'}, {'_typeName'})
    require(value['type'] == kind and value.get('_typeName', 'ManagedObjectReference') == 'ManagedObjectReference', 'Wrong managed reference type')
    moid(value['value'], prefix)


def positive(value): require(type(value) is int and value > 0, 'Positive integer required')


def devices(items):
    require(isinstance(items, list) and 1 <= len(items) <= 64, 'Complete bounded device inventory required')
    keys = set(); disks = set(); macs = set(); slots = set()
    for device in items:
        require(isinstance(device, dict) and device.get('_typeName') in DEVICES, 'Unsupported native device')
        key = device.get('key'); require(type(key) is int and key >= 0 and key not in keys, 'Unique device key required'); keys.add(key)
        kind = device['_typeName']
        if kind == 'VirtualDisk':
            positive(device.get('capacityInKB')); positive(device.get('capacityInBytes'))
            require(device['capacityInBytes'] == device['capacityInKB'] * 1024, 'Disk capacity units differ')
            for field in ('controllerKey', 'unitNumber'): require(type(device.get(field)) is int and device[field] >= 0, 'Disk slot required')
            slot = (device['controllerKey'], device['unitNumber']); require(slot not in slots, 'Duplicate disk slot'); slots.add(slot)
            backing = device.get('backing'); require(isinstance(backing, dict) and backing.get('_typeName') == 'VirtualDiskFlatVer2BackingInfo'
                and backing.get('diskMode') == 'persistent' and not backing.get('parent'), 'Persistent base disk backing required')
            c.text(backing.get('uuid')); c.text(backing.get('fileName'), length=1024)
            reference(backing.get('datastore'), 'Datastore', 'datastore')
            require(backing['uuid'] not in disks, 'Duplicate disk identity'); disks.add(backing['uuid'])
        elif kind == 'VirtualVmxnet3':
            mac = device.get('macAddress'); require(isinstance(mac, str) and re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', mac)
                and mac not in macs, 'Unique native MAC required'); macs.add(mac)
            connection = device.get('connectable'); require(isinstance(connection, dict), 'Explicit NIC connection required')
            for field in ('connected', 'startConnected', 'allowGuestControl'):
                require(type(connection.get(field)) is bool, 'Explicit NIC flags required')
            backing = device.get('backing'); require(isinstance(backing, dict), 'Explicit NIC backing required')
            if backing.get('_typeName') == 'VirtualEthernetCardDistributedVirtualPortBackingInfo':
                port = backing.get('port'); require(isinstance(port, dict), 'Exact distributed port required')
                for field in ('switchUuid', 'portgroupKey', 'portKey'): c.text(port.get(field))
            else:
                require(backing.get('_typeName') == 'VirtualEthernetCardOpaqueNetworkBackingInfo', 'Unsupported NIC backing')
                for field in ('opaqueNetworkId', 'opaqueNetworkType'): c.text(backing.get(field))
    require(disks and macs, 'At least one retained disk and NIC required')
    for device in items:
        if device['_typeName'] == 'VirtualDisk':
            require(any(d['key'] == device['controllerKey'] and d['_typeName'] in CONTROLLERS for d in items), 'Disk controller missing')


def validate(m):
    c.common_manifest(m, 'vmware'); require(m['profile'] == PROFILE and 'task' not in m, 'Unsupported vSphere snapshot profile')
    ids = set(); uuids = set(); instances = set()
    for r in m['resources']:
        c.exact_keys(r, {'kind', 'moid', 'expected'})
        require(r['kind'] == 'vm', 'VM resource required'); moid(r['moid'], 'vm')
        require(r['moid'] not in ids, 'Duplicate VM selector'); ids.add(r['moid'])
        e = r['expected']; c.exact_keys(e, {'config', 'runtime', 'resourcePool'})
        config = e['config']; c.exact_keys(config, CONFIG)
        require(config['_typeName'] == 'VirtualMachineConfigInfo' and config['template'] is False, 'Non-template VM required')
        for field, seen in (('uuid', uuids), ('instanceUuid', instances)):
            projection.uuid(config[field]); require(config[field] not in seen, 'Duplicate VM identity'); seen.add(config[field])
        c.text(config['name'], length=256); c.text(config['changeVersion'])
        hw = config['hardware']; c.exact_keys(hw, {'numCPU', 'numCoresPerSocket', 'memoryMB', 'device'}, {'_typeName'})
        for field in ('numCPU', 'numCoresPerSocket', 'memoryMB'): positive(hw[field])
        require(hw['numCPU'] % hw['numCoresPerSocket'] == 0, 'CPU topology differs'); devices(hw['device'])
        runtime = e['runtime']; c.exact_keys(runtime, RUNTIME)
        require(runtime['_typeName'] == 'VirtualMachineRuntimeInfo' and runtime['connectionState'] == 'connected'
                and runtime['powerState'] in {'poweredOn', 'poweredOff'}, 'Stable managed VM state required')
        for field in ('paused', 'vmFailoverInProgress', 'consolidationNeeded'): require(runtime[field] is False, 'Unsettled VM state')
        require(runtime['faultToleranceState'] in {'notConfigured', 'disabled', 'enabled', 'running'}, 'Unsettled fault-tolerance state')
        reference(runtime['host'], 'HostSystem', 'host'); reference(e['resourcePool'], 'ResourcePool', 'resgroup')


def resource_target(r, property_name): return PREFIX + 'VirtualMachine/' + r['moid'] + '/' + property_name


def targets(m):
    validate(m)
    return {resource_target(r, key) for r in m['resources'] for key in ('config', 'runtime', 'resourcePool')}


def snapshot(r, client):
    actual = {}; mismatches = []
    for key, expected in r['expected'].items():
        body, _ = client.get(resource_target(r, key))
        actual[key] = projection.selected(body, expected)
        # Device collections are complete native objects, not field projections.
        # An added selector/device/backing field cannot disappear before comparison.
        if key == 'config' and isinstance(body.get('hardware'), dict) and 'device' in body['hardware']:
            actual[key]['hardware']['device'] = body['hardware']['device']
            if c.digest(body['hardware']['device']) != c.digest(expected['hardware']['device']):
                mismatches.append('/config/hardware/device:complete_inventory_differs')
        if key == 'runtime' and body.get('question') is not None:
            mismatches.append('/runtime/question:execution_blocked')
    return actual, mismatches + c.differences(actual, r['expected'])


def sample(m, client):
    results = []
    for r in m['resources']:
        first, mismatch = snapshot(r, client)
        second, second_mismatch = snapshot(r, client); mismatch += second_mismatch
        stable = c.digest(first) == c.digest(second)
        identity = all(not c.differences(s.get('config', {}), {key: r['expected']['config'][key]
            for key in ('_typeName', 'uuid', 'instanceUuid')}) for s in (first, second))
        if not stable: mismatch.append('/snapshot:changed_during_observation')
        status = 'UNKNOWN' if not stable or not identity or any(x.endswith((':missing', ':type')) for x in mismatch) else ('DIFFERENT' if mismatch else 'MATCH')
        results.append(dict(resource_key=r['moid'], identity_match=identity, config_status=status, mismatch_fields=sorted(set(mismatch)),
            config_sha256=c.digest(second), progress='COMPLETE', reason='VSPHERE_SNAPSHOT_ONLY_TASKS_NOT_OBSERVED', task_completion_observed=False))
    return results


if __name__ == '__main__':
    from tools.readback_cli import run
    raise SystemExit(run(sys.modules[__name__], 'VCENTER', session=True))
