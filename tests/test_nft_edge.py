from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
from tools.nft_edge import validate, render, apply, normalized
from tools.run_files import digest, encoded, load_private, utcnow


def fixture():
    return dict(format='hosting-nft-edge/1',
        scope=dict(environment_key='test', site_key='site-a', platform='nutanix', tenant_key='tenant-a', wsd_key='science'),
        machine_id='a' * 32, network_namespace_inode=123, nft_sha256='b' * 64, operation_id='change-a', generation=1,
        interfaces={'domain0': ['192.0.2.0/24'], 'service0': ['198.51.100.0/24']}, owned_interfaces=['domain0'],
        flows=[dict(ingress='domain0', egress='service0', source='192.0.2.10', destination='198.51.100.20',
                    protocol='tcp', port=443, phase='active')], max_lease_seconds=300)


class EdgeTests(unittest.TestCase):
    def test_closed_rules_bind_both_directions_and_expire(self):
        spec = fixture()
        active = render(spec, 'active', 60)
        self.assertIn('192.0.2.10 . 198.51.100.20 . 443 timeout 60s', active)
        self.assertIn('ip daddr . ip saddr . tcp sport @f0 ct state established', active)
        self.assertNotIn('ct state established,related accept', active)
        self.assertNotIn('flush ruleset', active)
        withdrawn = render(spec, 'withdraw', 60, exists=True)
        self.assertNotIn('counter accept', withdrawn)
        self.assertIn('iifname "domain0" counter drop', withdrawn)
        self.assertIn('oifname "domain0" counter drop', withdrawn)

    def test_arbitrary_commands_broad_flows_and_foreign_scope_rejected(self):
        for key, value in [('source', '0.0.0.0/0'), ('destination', '203.0.113.1'),
                           ('ingress', 'eth0; flush ruleset'), ('port', True), ('protocol', 'all')]:
            spec = fixture(); spec['flows'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(spec)

    def test_native_drift_stops_before_mutation_and_failed_apply_holds(self):
        spec = fixture()
        class Kernel:
            commands = []
            def inspect(self, spec):
                return {'owned': True}, 'c' * 64
            def command(self, args):
                self.commands.append(args)
                if '--check' not in args:
                    raise OSError('Lost native response')
        authority = dict(spec_sha256=digest(encoded(spec)), mode='active', expected_state_sha256='d' * 64,
                         valid_from=(utcnow() - timedelta(seconds=1)).isoformat(),
                         valid_until=(utcnow() + timedelta(minutes=10)).isoformat(),
                         change_ref='CHANGE-1', boundary_acceptance_ref='BOUNDARY-1', readiness_ref='READINESS-1')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); ledger = root / 'ledger'; ledger.mkdir(mode=0o700)
            operation = root / 'run'; operation.mkdir(mode=0o700)
            kernel = Kernel()
            with self.assertRaises(ValueError):
                apply(spec, 'active', authority, kernel, ledger, operation)
            self.assertEqual(kernel.commands, [])
            authority['expected_state_sha256'] = 'c' * 64
            with self.assertRaises(OSError):
                apply(spec, 'active', authority, kernel, ledger, operation)
            self.assertEqual(load_private(next(ledger.glob('*/head.json')))['status'], 'OUTCOME_UNKNOWN')
            other = root / 'again'; other.mkdir(mode=0o700)
            with self.assertRaises(ValueError):
                apply(spec, 'active', authority, kernel, ledger, other)

    def test_only_volatile_observation_values_are_ignored(self):
        first = {'nftables': [{'metainfo': {'genid': 1}}, {'rule': {'handle': 3, 'expr': [{'counter': {'packets': 2, 'bytes': 60}}, {'drop': None}]}}]}
        second = deepcopy(first); second['nftables'][1]['rule']['expr'][0]['counter']['packets'] = 20
        self.assertEqual(normalized(first), normalized(second))
        second['nftables'][1]['rule']['expr'][-1] = {'accept': None}
        self.assertNotEqual(normalized(first), normalized(second))
