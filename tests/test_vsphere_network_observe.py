"""Portgroup identity and revision reads; unrelated switch inventory is excluded."""
from copy import deepcopy
import json
import unittest
from lab.native_readback_fixture import Fixture
from tests.test_vsphere_observe import manifest as vm_manifest, ref
from tests.test_nutanix_vm_observe import uid
from tools import vsphere_network_observe as n, readback_core as c


def manifest(origin='https://vc.example.test'):
    m = vm_manifest(origin); m['profile'] = n.PROFILE
    m['resources'] = [dict(kind='nsx-portgroup', moid='dvportgroup-1', segment_path='/infra/segments/fixture',
        expected=dict(config=dict(_typeName='DVPortgroupConfigInfo', key='dvportgroup-1', configVersion='7',
            distributedVirtualSwitch=ref('VmwareDistributedVirtualSwitch', 'dvs-1'), backingType='nsx',
            type='ephemeral', uplink=False, logicalSwitchUuid=uid(30)), switch=dict(_typeName='DVSSummary', uuid='fixture-dvs-uuid')))]
    return m


class Client:
    def __init__(self, m):
        self.origin = m['origin']; self.request_count = 0; self.transform = None
        self.routes = {path: deepcopy(r['expected'][key]) for r in m['resources'] for key, path in n.properties(r).items()}
    def get(self, path):
        self.request_count += 1; body = deepcopy(self.routes[path])
        if self.transform: self.transform(path, body, self.request_count)
        return body, None


class NetworkTests(unittest.TestCase):
    def setUp(self): self.m = manifest(); self.client = Client(self.m)
    def observe(self): return c.observe(self.m, self.client, n, interval=0)
    def test_matching_identity_is_not_enforcement_or_activation(self):
        report = self.observe(); self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
        self.assertEqual(report['request_count'], 8); self.assertFalse(report['may_activate'])
        self.assertFalse(report['history'][-1]['states'][0]['task_completion_observed'])
    def test_wrong_backing_revision_identity_and_missing_fields_hold(self):
        path = n.properties(self.m['resources'][0])['config']
        for changes, expected in [(dict(logicalSwitchUuid=uid(31)), 'HOLD_DIFFERENCE'), (dict(configVersion='8'), 'HOLD_DIFFERENCE'),
                                 (dict(backingType='standard'), 'HOLD_DIFFERENCE'), (dict(uplink=True), 'HOLD_DIFFERENCE'),
                                 (dict(key='foreign'), 'HOLD_UNCERTAIN'), (dict(uplink=0), 'HOLD_UNCERTAIN')]:
            self.client = Client(self.m); self.client.routes[path].update(changes)
            self.assertEqual(self.observe()['outcome'], expected)
        self.client = Client(self.m); del self.client.routes[path]['distributedVirtualSwitch']
        self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
    def test_changed_snapshot_and_switch_substitution_hold(self):
        path = n.properties(self.m['resources'][0])['switch']
        self.client.routes[path]['uuid'] = 'foreign'; self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
        self.client = Client(self.m)
        self.client.transform = lambda p, b, count: b.update(configVersion='new') if p.endswith('/config') and count > 2 else None
        self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
    def test_unsupported_and_ambiguous_inputs_rejected_before_contact(self):
        for change in (lambda m: m['resources'][0]['expected']['config'].update(backingType='standard'),
            lambda m: m['resources'][0].update(moid='../other'), lambda m: m['resources'][0].update(segment_path='/global-infra/segments/fixture'),
            lambda m: m['resources'].append(deepcopy(m['resources'][0]) | dict(moid='dvportgroup-2'))):
            m = deepcopy(self.m); change(m)
            with self.assertRaises(ValueError): n.targets(m)
    def test_real_tls_exact_gets_exclude_unrelated_inventory_and_secrets(self):
        with Fixture() as f:
            m = manifest(f.origin); client = Client(m)
            for value in client.routes.values(): value.update(description='PRIVATE-SENTINEL', vm=[ref('VirtualMachine', 'vm-99')])
            f.routes = {path: dict(body=value) for path, value in client.routes.items()}
            http = c.ReadClient(f.origin, f.origin, None, None, n.targets(m), str(f.directory / 'ca.pem'), session_token='fixture-session')
            report = c.observe(m, http, n, interval=0)
            self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED'); self.assertNotIn('PRIVATE-SENTINEL', json.dumps(report))
            self.assertEqual({x['path'] for x in f.requests}, n.targets(m))
            self.assertTrue(all(x['method'] == 'GET' and x['has_session_auth'] and not x['has_basic_auth'] for x in f.requests))


if __name__ == '__main__': unittest.main()
