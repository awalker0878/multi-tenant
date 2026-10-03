"""AHV snapshot drift, identity and wire regressions; not native qualification."""
from copy import deepcopy
import json
import unittest
from lab.native_readback_fixture import Fixture
from provisioner.execution import readback_core as c
from tools import nutanix_vm_observe as ahv


def uid(number):
    return f'{number:08x}-1111-4111-8111-111111111111'


def manifest(origin='https://prism.example.invalid'):
    e = {'extId': uid(1), '$objectType': ahv.TYPE + 'Vm', 'tenantId': uid(2), 'name': 'fixture-only',
         'host': {'extId': uid(3)}, 'cluster': {'extId': uid(4)}, 'project': {'extId': uid(5)},
         'categories': [{'extId': uid(6)}], 'powerState': 'ON', 'numSockets': 2,
         'numCoresPerSocket': 1, 'memorySizeBytes': 4294967296, 'isCrossClusterMigrationInProgress': False,
         'nics': [{'extId': uid(7), 'nicBackingInfo': {'$objectType': ahv.TYPE + 'VirtualEthernetNic',
                  'isConnected': True, 'macAddress': '02:00:00:00:00:01', 'model': 'VIRTIO'},
                  'nicNetworkInfo': {'$objectType': ahv.TYPE + 'VirtualEthernetNicNetworkInfo', 'nicType': 'NORMAL_NIC',
                  'subnet': {'extId': uid(8)}, 'ipv4Config': {'shouldAssignIp': True,
                  'ipAddress': {'value': '192.0.2.10', 'prefixLength': 24}, 'secondaryIpAddressList': []}}}],
         'disks': [{'extId': uid(9), 'diskAddress': {'busType': 'SCSI', 'index': 0},
                    'backingInfo': {'$objectType': ahv.TYPE + 'VmDisk', 'diskExtId': uid(10),
                    'diskSizeBytes': 10737418240, 'storageContainer': {'extId': uid(11)}, 'isMigrationInProgress': False}}]}
    return {'platform': 'nutanix', 'profile': ahv.PROFILE, 'origin': origin, 'operation_id': 'fixture-snapshot',
            'tenant_id': 'tenant-001', 'scope_id': 'WSD01', 'engineering_record_ref': 'FIXTURE',
            'target_binding_ref': 'FIXTURE', 'contact_enabled': False,
            'resources': [{'kind': 'vm', 'ext_id': uid(1), 'expected': e, 'expected_etag': '"fixture-1"'}]}


class Client:
    def __init__(self, m, body=None, etag='"fixture-1"'):
        self.origin = m['origin']; self.request_count = 0; self.etag = etag
        self.body = {'data': deepcopy(m['resources'][0]['expected'])} if body is None else body
    def get(self, target):
        self.request_count += 1
        return deepcopy(self.body), self.etag


class AhvSnapshots(unittest.TestCase):
    def setUp(self): self.m = manifest(); self.client = Client(self.m)
    def observe(self): return c.observe(self.m, self.client, ahv, interval=0)
    def test_snapshot_does_not_complete_task_or_authorize_activation(self):
        report = self.observe()
        self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
        self.assertEqual(report['request_count'], 2)
        self.assertFalse(report['may_activate'])
        self.assertFalse(report['history'][-1]['states'][0]['task_completion_observed'])
    def test_changed_placement_membership_power_nic_or_disk_holds(self):
        mutations = [lambda e: e['host'].update(extId=uid(12)), lambda e: e['cluster'].update(extId=uid(12)),
                     lambda e: e['project'].update(extId=uid(12)), lambda e: e['categories'].append({'extId': uid(12)}),
                     lambda e: e.update(powerState='OFF'), lambda e: e.update(isCrossClusterMigrationInProgress=True),
                     lambda e: e['nics'][0]['nicBackingInfo'].update(isConnected=False),
                     lambda e: e['nics'][0]['nicNetworkInfo']['subnet'].update(extId=uid(12)),
                     lambda e: e['disks'][0]['backingInfo'].update(diskExtId=uid(12)),
                     lambda e: e['disks'][0]['backingInfo'].update(isMigrationInProgress=True),
                     lambda e: e['disks'].clear()]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self.client = Client(self.m); mutate(self.client.body['data'])
                self.assertEqual(self.observe()['outcome'], 'HOLD_DIFFERENCE')
    def test_unknown_identity_missing_fields_and_boolean_types_hold(self):
        for mutate in (lambda e: e.update(tenantId=uid(12)), lambda e: e.pop('host'),
                       lambda e: e['nics'][0]['nicBackingInfo'].update(isConnected=1),
                       lambda e: e['disks'][0]['backingInfo'].pop('diskExtId')):
            self.client = Client(self.m); mutate(self.client.body['data'])
            self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
        self.client = Client(self.m, body={'data': []})
        self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
    def test_revision_missing_or_changed_holds(self):
        for etag, outcome in ((None, 'HOLD_UNCERTAIN'), ('"other"', 'HOLD_DIFFERENCE')):
            self.client = Client(self.m, etag=etag)
            self.assertEqual(self.observe()['outcome'], outcome)
    def test_unselected_guest_material_is_not_journaled_or_hashed(self):
        baseline = self.observe()['history'][-1]['snapshot_sha256']
        self.client.body['data']['guestCustomization'] = {'password': 'SECRET-SENTINEL'}
        self.client.body['data']['nics'][0]['extra'] = 'SECRET-SENTINEL'
        report = self.observe()
        self.assertEqual(report['history'][-1]['snapshot_sha256'], baseline)
        self.assertNotIn('SECRET-SENTINEL', json.dumps(report))
    def test_manifest_rejects_ambiguous_selectors_and_unstable_expectations(self):
        mutations = [lambda m: m.update(task={}), lambda m: m['resources'].append(deepcopy(m['resources'][0])),
                     lambda m: m['resources'][0].update(ext_id='../other'),
                     lambda m: m['resources'][0].update(expected_etag='W/"weak"'),
                     lambda m: m['resources'][0]['expected'].update(powerState='PAUSED'),
                     lambda m: m['resources'][0]['expected'].update(host={}),
                     lambda m: m['resources'][0]['expected']['disks'].append(deepcopy(m['resources'][0]['expected']['disks'][0]))]
        for mutate in mutations:
            m = deepcopy(self.m); mutate(m)
            with self.assertRaises(ValueError): ahv.targets(m)
    def test_real_tls_get_uses_exact_vmm_endpoint(self):
        with Fixture() as fixture:
            m = manifest(fixture.origin); r = m['resources'][0]
            target = '/api/vmm/v4.2/ahv/config/vms/' + uid(1)
            fixture.routes = {target: {'body': {'data': r['expected']}, 'etag': r['expected_etag']}}
            client = c.ReadClient(fixture.origin, fixture.origin, 'reader', 'fixture-only', ahv.targets(m), str(fixture.directory / 'ca.pem'))
            report = c.observe(m, client, ahv, interval=0)
            self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
            self.assertEqual(len(fixture.requests), 2)
            self.assertTrue(all(r['method'] == 'GET' and r['path'] == target and r['has_basic_auth'] for r in fixture.requests))


if __name__ == '__main__': unittest.main()
