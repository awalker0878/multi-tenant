"""vSphere wire snapshots and failure boundaries; no live platform qualification."""
from copy import deepcopy
import json
import unittest
from lab.native_readback_fixture import Fixture
from tests.test_nutanix_vm_observe import uid
from provisioner.execution import readback_core as c
from tools import vsphere_observe as v


def ref(kind, value): return {'_typeName': 'ManagedObjectReference', 'type': kind, 'value': value}


def manifest(origin='https://vcenter.example.invalid'):
    devices = [{'_typeName': 'ParaVirtualSCSIController', 'key': 1000, 'busNumber': 0},
        {'_typeName': 'VirtualDisk', 'key': 2000, 'controllerKey': 1000, 'unitNumber': 0,
         'capacityInKB': 10485760, 'capacityInBytes': 10737418240,
         'backing': {'_typeName': 'VirtualDiskFlatVer2BackingInfo', 'diskMode': 'persistent',
                    'uuid': '6000C290-fixture-disk', 'fileName': '[fixture-ds] vm/vm.vmdk',
                    'datastore': ref('Datastore', 'datastore-1')}},
        {'_typeName': 'VirtualVmxnet3', 'key': 4000, 'macAddress': '00:50:56:00:00:01',
         'connectable': {'connected': True, 'startConnected': True, 'allowGuestControl': False},
         'backing': {'_typeName': 'VirtualEthernetCardOpaqueNetworkBackingInfo',
                     'opaqueNetworkId': 'fixture-segment', 'opaqueNetworkType': 'nsx.LogicalSwitch'}}]
    expected = dict(config={'_typeName': 'VirtualMachineConfigInfo', 'uuid': uid(1), 'instanceUuid': uid(2),
        'name': 'fixture-vm', 'template': False, 'changeVersion': 'fixture-revision',
        'hardware': {'numCPU': 2, 'numCoresPerSocket': 1, 'memoryMB': 4096, 'device': devices}},
        runtime={'_typeName': 'VirtualMachineRuntimeInfo', 'host': ref('HostSystem', 'host-1'), 'connectionState': 'connected',
                 'powerState': 'poweredOn', 'paused': False, 'vmFailoverInProgress': False,
                 'consolidationNeeded': False, 'faultToleranceState': 'notConfigured'},
        resourcePool=ref('ResourcePool', 'resgroup-1'))
    return dict(platform='vmware', profile=v.PROFILE, origin=origin, operation_id='fixture-snapshot', tenant_id='tenant-001',
        scope_id='WSD01', engineering_record_ref='FIXTURE', target_binding_ref='FIXTURE', contact_enabled=False,
        resources=[dict(kind='vm', moid='vm-1', expected=expected)])


class Client:
    def __init__(self, m):
        self.origin = m['origin']; self.request_count = 0; self.transform = None
        self.routes = {v.resource_target(r, key): deepcopy(value) for r in m['resources'] for key, value in r['expected'].items()}
    def get(self, target):
        self.request_count += 1; value = deepcopy(self.routes[target])
        if self.transform: self.transform(target, value, self.request_count)
        return value, None


class VsphereSnapshotTests(unittest.TestCase):
    def setUp(self): self.m = manifest(); self.client = Client(self.m)
    def observe(self): return c.observe(self.m, self.client, v, interval=0)
    def test_snapshot_cannot_infer_task_completion_or_activation(self):
        report = self.observe()
        self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
        self.assertEqual(report['request_count'], 12)
        self.assertFalse(report['may_activate']); self.assertFalse(report['history'][-1]['states'][0]['task_completion_observed'])
    def test_complete_hardware_and_selected_placement_drift_holds(self):
        r = self.m['resources'][0]
        cases = [('config', lambda x: x.update(changeVersion='new-revision')),
            ('config', lambda x: x['hardware']['device'].append({'_typeName': 'VirtualCdrom', 'key': 5000})),
            ('config', lambda x: x['hardware']['device'][1]['backing'].update(parent={'uuid': 'foreign-disk'})),
            ('config', lambda x: x['hardware']['device'][2]['connectable'].update(connected=False)),
            ('config', lambda x: x['hardware']['device'][2]['backing'].update(opaqueNetworkId='foreign-segment')),
            ('config', lambda x: x['hardware']['device'][2].update(hiddenSelector=True)),
            ('runtime', lambda x: x['host'].update(value='host-2')), ('runtime', lambda x: x.update(powerState='poweredOff')),
            ('runtime', lambda x: x.update(vmFailoverInProgress=True)), ('runtime', lambda x: x.update(question={'text': 'PRIVATE'})),
            ('resourcePool', lambda x: x.update(value='resgroup-2'))]
        for key, mutate in cases:
            self.client = Client(self.m); mutate(self.client.routes[v.resource_target(r, key)])
            with self.subTest(key=key, mutate=mutate): self.assertEqual(self.observe()['outcome'], 'HOLD_DIFFERENCE')
    def test_missing_ambiguous_identity_and_torn_snapshot_hold_unknown(self):
        target = v.resource_target(self.m['resources'][0], 'config')
        for mutate in (lambda x: x.update(uuid=uid(9)), lambda x: x.pop('hardware'), lambda x: x.update(template=0)):
            self.client = Client(self.m); mutate(self.client.routes[target])
            self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
        self.client = Client(self.m)
        self.client.transform = lambda path, x, n: x.update(changeVersion='changed') if path == target and n > 3 else None
        self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
    def test_guest_customization_and_unselected_config_are_not_journaled(self):
        target = v.resource_target(self.m['resources'][0], 'config')
        baseline = self.observe()['history'][-1]['snapshot_sha256']
        self.client.routes[target]['extraConfig'] = [{'key': 'guestinfo.userdata', 'value': 'SECRET-SENTINEL'}]
        report = self.observe()
        self.assertEqual(report['history'][-1]['snapshot_sha256'], baseline)
        self.assertNotIn('SECRET-SENTINEL', json.dumps(report))
    def test_unsupported_ambiguous_expected_profiles_rejected(self):
        for mutate in (lambda m: m.update(task={}), lambda m: m['resources'][0].update(moid='../other'),
            lambda m: m['resources'].append(deepcopy(m['resources'][0])),
            lambda m: m['resources'][0]['expected']['runtime'].update(connectionState='disconnected'),
            lambda m: m['resources'][0]['expected']['config']['hardware']['device'][1]['backing'].update(diskMode='nonpersistent')):
            m = deepcopy(self.m); mutate(m)
            with self.assertRaises(ValueError): v.targets(m)
    def test_real_tls_uses_session_and_exact_property_endpoints(self):
        with Fixture() as f:
            m = manifest(f.origin); f.routes = {k: {'body': value} for k, value in Client(m).routes.items()}
            client = c.ReadClient(f.origin, f.origin, None, None, v.targets(m), str(f.directory / 'ca.pem'), session_token='fixture-session')
            self.assertEqual(c.observe(m, client, v, interval=0)['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
            self.assertEqual({x['path'] for x in f.requests}, v.targets(m))
            self.assertTrue(all(x['method'] == 'GET' and x['has_session_auth'] and not x['has_basic_auth'] for x in f.requests))


if __name__ == '__main__': unittest.main()
