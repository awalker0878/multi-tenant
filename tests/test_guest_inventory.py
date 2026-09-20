import base64
import copy
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import struct
import tempfile
import unittest

from tools.compile_wsd import STATE
from tools.guest_inventory import build, gate


def fixture():
    scope = dict(environment_key='test-01', site_key='site-01', tenant_key='tenant-01',
                 wsd_key='wsd-01', platform='nutanix', phase='workloads')
    outputs = {'scope': {'value': scope}, 'delivery_state': {'value': STATE},
               'members': {'value': {'guest-01': {'vm_id': 'vm-01', 'delivery_state': STATE}}}}
    key = struct.pack('>I', 11) + b'ssh-ed25519' + struct.pack('>I', 32) + bytes(range(32))
    target = dict(native_id='vm-01', address='192.0.2.10', port=22, user='operator',
                  host_key='ssh-ed25519 ' + base64.b64encode(key).decode(), machine_id='a'*32,
                  hostname='guest-01', profile='ubuntu-24.04-chrony', time_servers=['192.0.2.130'])
    access = dict(format='hosting-guest-access/1', scope=scope, change_ref='MOCK-NO-AUTHORITY',
                  valid_until=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                  targets={'guest-01': target})
    return outputs, access


class GuestInventoryTests(unittest.TestCase):
    def test_immutable_outputs_and_disabled_inventory(self):
        outputs, access = fixture(); before = copy.deepcopy((outputs, access))
        inv, keys = build(outputs, access, '/private/run/known_hosts')
        self.assertEqual(before, (outputs, access))
        self.assertIs(inv['all']['vars']['hosting_native_enabled'], False)
        self.assertIn('[192.0.2.10]:22 ssh-ed25519 ', keys)
        self.assertTrue(inv['all']['children']['hosting_guests']['hosts']['guest-01']['ansible_host_key_checking'])

    def test_binding_and_guest_profile_rejections(self):
        for field, value in [('native_id', 'foreign'), ('address', '127.0.0.1'), ('port', True),
                             ('user', 'root'), ('machine_id', 'unknown'), ('profile', 'windows'),
                             ('host_key', 'ssh-ed25519 invalid'), ('time_servers', ['pool.invalid'])]:
            with self.subTest(field=field):
                outputs, access = fixture(); access['targets']['guest-01'][field] = value
                with self.assertRaises(ValueError):
                    build(outputs, access, '/private/known_hosts')

    def test_wrong_scope_missing_member_and_stale_handoff(self):
        outputs, access = fixture(); outputs = copy.deepcopy(outputs)
        outputs['scope']['value']['environment_key'] = 'production'
        with self.assertRaises(ValueError): build(outputs, access, '/private/known_hosts')
        outputs, access = fixture(); access['targets'] = {}
        with self.assertRaises(ValueError): build(outputs, access, '/private/known_hosts')
        outputs, access = fixture(); access['valid_until'] = '2020-01-01T00:00:00Z'
        with self.assertRaises(ValueError): build(outputs, access, '/private/known_hosts')

    def test_runtime_gate_detects_key_inventory_and_connection_changes(self):
        outputs, access = fixture()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'known_hosts'
            inv, keys = build(outputs, access, str(path)); path.write_text(keys); path.chmod(0o600)
            hosts = inv['all']['children']['hosting_guests']['hosts']
            self.assertEqual(gate(True, outputs, access, str(path), ['guest-01'], hosts), ['guest-01'])
            with self.assertRaises(ValueError): gate(False, outputs, access, str(path), ['guest-01'], hosts)
            hosts['guest-01']['ansible_connection'] = 'local'
            with self.assertRaises(ValueError): gate(True, outputs, access, str(path), ['guest-01'], hosts)
            hosts['guest-01']['ansible_connection'] = 'ssh'; path.write_text(keys + '\n')
            with self.assertRaises(ValueError): gate(True, outputs, access, str(path), ['guest-01'], hosts)
            path.write_text(keys); path.chmod(0o644)
            with self.assertRaises(ValueError): gate(True, outputs, access, str(path), ['guest-01'], hosts)
