from copy import deepcopy
import base64
from pathlib import Path
import struct
import tempfile
import unittest
from datetime import timedelta

from lab.native_readback_fixture import credentials
from tools.guest_services import validate_services, verify_assets, resolver_bound
from provisioner.execution.run_files import digest, utcnow


def fixture(directory='/private/operator'):
    key = 'ssh-ed25519 ' + base64.b64encode(struct.pack('>I', 11) + b'ssh-ed25519' +
                                           struct.pack('>I', 32) + b'a' * 32).decode()
    services = dict(ownership_ref='CHANGE-1', resolver_addresses=['192.0.2.53'],
                    admin_users=['operator'], user_ca_keys=[key], revoked_user_keys=[],
                    breakglass={'user': 'recovery', 'public_key': key},
                    log=dict(address='192.0.2.60', peer_name='logs.example.com', port=6514, queue_mib=256),
                    journal_mib=512, files={name: dict(path=str(Path(directory) / path), sha256='a' * 64)
                        for name, path in [('log_ca', 'ca.pem'), ('log_certificate', 'server.pem'), ('log_key', 'server.key')]})
    return dict(user='operator', port=22, services=services), dict(tenant_key='tenant-a', wsd_key='science')


class GuestServicesTests(unittest.TestCase):
    def test_backup_scope_and_expired_withdrawal(self):
        target, scope = fixture()
        scope.update(environment_key='test', site_key='site-a', platform='nutanix', phase='workloads')
        target.update(hostname='guest-a', machine_id='a' * 32)
        config = dict(format='hosting-restic-export/1', scope={k: v for k, v in scope.items() if k != 'phase'},
            member='guest-a', machine_id='a' * 32, source='/srv/hosting-exports/tenant-a/science/guest-a',
            repository='rest:https://backup.example.com/tenant-a/science/', repository_id='b' * 64,
            restic_sha256='c' * 64, valid_until=(utcnow() + timedelta(hours=1)).isoformat(),
            consistency_ref='EXPORT-1', max_seconds=600)
        binding = dict(config=config, credentials={'path': '/private/credentials', 'sha256': 'a' * 64},
                       ca={'path': '/private/ca.pem', 'sha256': 'b' * 64}, enabled=True, interval_minutes=60)
        target['services']['backup'] = binding
        validate_services(target, scope)
        binding['config']['source'] = '/srv/hosting-exports/tenant-b/science/guest-a'
        with self.assertRaises(ValueError):
            validate_services(target, scope)
        binding['config']['source'] = '/srv/hosting-exports/tenant-a/science/guest-a'
        binding['config']['valid_until'] = (utcnow() - timedelta(hours=1)).isoformat()
        with self.assertRaises(ValueError):
            validate_services(target, scope)
        binding['enabled'] = False
        validate_services(target, scope)

    def test_foreign_link_dns_cannot_bypass_global_selection(self):
        self.assertTrue(resolver_bound('Global: 192.0.2.53\nLink 2 (eth0):\n', ['192.0.2.53']))
        for output in ['Global: 192.0.2.53\nLink 2 (eth0): 198.51.100.53', 'Global:']:
            with self.assertRaises(ValueError):
                resolver_bound(output, ['192.0.2.53'])

    def test_dangerous_profile_changes_are_rejected(self):
        target, scope = fixture()
        validate_services(target, scope)
        variants = [dict(admin_users=['root']), dict(admin_users=['someone-else']),
                    dict(resolver_addresses=['0.0.0.0']), dict(user_ca_keys=['arbitrary-key']),
                    dict(breakglass={'user': 'operator', 'public_key': target['services']['user_ca_keys'][0]}),
                    dict(log=target['services']['log'] | {'peer_name': '*.example.com'}),
                    dict(log=target['services']['log'] | {'port': '6514\nother-directive'}),
                    dict(journal_mib=True)]
        for change in variants:
            with self.subTest(change=list(change)), self.assertRaises(ValueError):
                validate_services(target | {'services': target['services'] | change}, scope)

    def test_credentials_are_private_bound_and_parseable(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            credentials(directory)
            target, scope = fixture(directory)
            for asset in target['services']['files'].values():
                path = Path(asset['path'])
                path.chmod(0o600)
                asset['sha256'] = digest(path.read_bytes())
            verify_assets(target, scope)
            (directory / 'server.key').write_text('replaced')
            with self.assertRaises(ValueError):
                verify_assets(target, scope)

    def test_unbound_asset_and_service_injection_rejected(self):
        target, scope = fixture()
        for changed in [dict(path='/private/../unreviewed/key', sha256='a' * 64),
                        dict(path='/private/operator/key', sha256='unknown')]:
            copy = deepcopy(target)
            copy['services']['files']['log_key'] = changed
            with self.assertRaises(ValueError):
                validate_services(copy, scope)
