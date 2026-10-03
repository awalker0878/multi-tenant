from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
from tools.restic_run import validate, manifest, restore
from provisioner.execution.run_files import utcnow


def fixture():
    return dict(format='hosting-restic-export/1', scope=dict(environment_key='test', site_key='site-a',
        platform='vmware', tenant_key='tenant-a', wsd_key='science'), member='guest-a', machine_id='a' * 32,
        source='/srv/exports/science', repository='rest:https://backup.example.com/tenant-a/science/',
        repository_id='b' * 64, restic_sha256='c' * 64, valid_until=(utcnow() + timedelta(hours=1)).isoformat(),
        consistency_ref='EXPORT-1', max_seconds=600)


class ResticRunTests(unittest.TestCase):
    def test_rejects_unapproved_transport_and_scope(self):
        config = fixture()
        validate(config)
        for update in [dict(repository='sftp:someone@host:/path'), dict(repository='/tmp/repo'),
                       dict(repository='rest:http://backup.example.com/path/'), dict(source='/'),
                       dict(repository='rest:https://name:password@backup.example.com/path/'),
                       dict(max_seconds=True), dict(valid_until=(utcnow() - timedelta(seconds=1)).isoformat())]:
            with self.subTest(update=update), self.assertRaises(ValueError):
                validate(config | update)

    def test_manifest_detects_changes_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data').write_text('useful original data')
            before = manifest(root)
            (root / 'data').write_text('changed data')
            self.assertNotEqual(manifest(root), before)
            (root / 'link').symlink_to(root / 'data')
            with self.assertRaises(ValueError):
                manifest(root)

    def test_restore_rejects_foreign_receipt_before_command(self):
        config = fixture()
        receipt = dict(format='hosting-restic-receipt/1', status='CAPTURED_REQUIRES_RESTORE_TEST',
                       repository_id='b' * 64, scope=config['scope'] | {'tenant_key': 'tenant-b'})
        with self.assertRaises(ValueError):
            restore(config, receipt, {}, None, Path('/unused'), Path('/unused-target'))
