from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from provisioner.controlplane.operations import recovery


def manifest():
    return {'format': recovery.FORMAT, 'capturedAt': datetime.now(timezone.utc).isoformat(),
            'archiveSha256': 'a' * 64, 'mutationAuthorized': False,
            'externalComponents': ['separate-custody'],
            'state': {'tables': {name: {'rows': 1, 'sha256': 'b' * 64}
                                 for name in recovery._REQUIRED},
                      'rls': {'native_ownership': {'enabled': True, 'forced': True}},
                      'migrationLedger': [[1, 'c' * 64]], 'sequences': [['audit', 42]]}}


class RecoveryTests(unittest.TestCase):
    def test_equal_archive_keeps_native_epoch_workflow_and_authority_holds(self):
        value = manifest()
        report = recovery.compare_restore(value, deepcopy(value['state']))
        self.assertEqual(report['status'], 'ARCHIVE_RECONCILED_OBSERVATION_ONLY')
        self.assertFalse(report['mutationAuthorized'])
        self.assertIn('NATIVE_OWNER_EPOCH_AND_OLD_WRITER_FENCING', report['holds'])

    def test_every_retained_state_dimension_blocks_mismatched_restore(self):
        value = manifest()
        for field in value['state']:
            with self.subTest(field=field):
                observed = deepcopy(value['state'])
                observed[field] = []
                self.assertEqual(recovery.compare_restore(value, observed)['status'], 'RESTORE_HELD')

    def test_manifest_cannot_authorize_writes_or_omit_core_tables(self):
        value = manifest()
        value['mutationAuthorized'] = True
        with self.assertRaises(ValueError):
            recovery.compare_restore(value, value['state'])
        value = manifest()
        del value['state']['tables']['native_ownership']
        with self.assertRaises(ValueError):
            recovery.compare_restore(value, value['state'])

    def test_nonisolated_database_is_rejected_before_archive_or_connection(self):
        with self.assertRaisesRegex(ValueError, 'isolated'):
            recovery.restore('host=site.example user=restore dbname=hosting_controlplane sslmode=verify-full',
                             Path('/missing'), expected_manifest_sha256='a' * 64,
                             connect=lambda: self.fail('must not connect'))

    def test_independent_manifest_and_archive_digests_checked_before_restore_sql(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'controlplane.dump'
            archive.write_bytes(b'fixture-archive')
            value = manifest()
            value['archiveSha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
            raw = json.dumps(value).encode()
            (root / 'manifest.json').write_bytes(raw)
            dsn = 'host=isolated.example user=restore dbname=hosting_observation_restore_test sslmode=verify-full'
            with self.assertRaisesRegex(ValueError, 'independent'):
                recovery.restore(dsn, root, expected_manifest_sha256='d' * 64,
                                 connect=lambda: self.fail('must not connect'))
            archive.write_bytes(b'altered')
            with self.assertRaisesRegex(ValueError, 'Archive bytes'):
                recovery.restore(dsn, root, expected_manifest_sha256=hashlib.sha256(raw).hexdigest(),
                                 connect=lambda: self.fail('must not connect'))

    def test_pg_client_uses_current_snapshot_without_password_arguments(self):
        calls = []
        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            kwargs['stdout'].write(b'fixture-pg-custom-dump')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'archive'
            with patch.object(recovery, '_reviewed_pg_binary', return_value=Path('/usr/bin/pg_dump')):
                recovery._client('host=backup.example user=custodian password=synthetic-password '
                    'dbname=hosting sslmode=verify-full', 'pg_dump', path,
                    snapshot='00000003-00000007-1', runner=run)
            argv, options = calls[0]
            self.assertTrue(any(value.startswith('--snapshot=') for value in argv))
            self.assertFalse(any('synthetic-password' in value for value in argv))
            self.assertEqual(options['env']['PGPASSWORD'], 'synthetic-password')
            self.assertEqual(path.read_bytes(), b'fixture-pg-custom-dump')

    def test_client_never_accepts_arbitrary_commands_or_insecure_connection(self):
        with self.assertRaises(ValueError):
            recovery._client('host=backup.example user=custodian dbname=hosting sslmode=require',
                             'pg_dump', Path('/missing'), snapshot='abc')
        with self.assertRaises(ValueError):
            recovery._client('host=backup.example user=custodian dbname=hosting sslmode=verify-full',
                             '/bin/sh', Path('/missing'), runner=lambda *args: self.fail('must not run'))

    def test_archive_binary_owner_absent_changed_or_arbitrary_path_cannot_run(self):
        for value in ('/bin/sh', '/missing/pg_dump'):
            with patch.dict('os.environ', {'HOSTING_PG_DUMP_PATH': value,
                                          'HOSTING_PG_DUMP_SHA256': '0' * 64}):
                with self.assertRaises((ValueError, FileNotFoundError)):
                    recovery._reviewed_pg_binary('pg_dump')


if __name__ == '__main__':
    unittest.main()
