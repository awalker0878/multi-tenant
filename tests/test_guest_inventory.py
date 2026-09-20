import base64
import copy
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import struct
import tempfile
import unittest
import json
import subprocess
import sys

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
    def test_cli_accepts_one_receipted_workload_run_without_manual_output_copy(self):
        from tools.run_files import digest, encoded, utcnow, write_new
        from tools.compile_wsd import ROOT
        outputs, access = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            inputs = {'members': {'guest-01': {}}}
            bundle = {'format': 'hosting-terraform-bundle/1', 'source_commit': 'a' * 40,
                      'scope': outputs['scope']['value'], 'operation_id': 'op-01', 'generation': 1,
                      'artifacts': {'inputs.json': digest(encoded(inputs))}}
            result = {'format': 'hosting-terraform-attempt/1', 'status': 'APPLIED_REQUIRES_NATIVE_ACCEPTANCE',
                      'bundle_sha256': digest(encoded(bundle)), 'scope': outputs['scope']['value'],
                      'operation_id': 'op-01', 'generation': 1, 'completed_at': utcnow().isoformat(),
                      'outputs_sha256': digest(encoded(outputs))}
            for name, data in [('inputs.json', inputs), ('bundle.json', bundle), ('outputs.json', outputs),
                               ('result.json', result), ('access.json', access)]:
                write_new(directory / name, encoded(data))
            invocation = subprocess.run([sys.executable, str(ROOT / 'tools/guest_inventory.py'),
                str(directory / 'access.json'), '--workload-run', str(directory), '--output', str(directory / 'inventory')],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(invocation.returncode, 0, invocation.stdout + invocation.stderr)
            inventory = json.loads((directory / 'inventory/inventory.json').read_text())
            self.assertFalse(inventory['all']['vars']['hosting_native_enabled'])

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
