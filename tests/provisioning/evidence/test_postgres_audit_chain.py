"""PostgreSQL audit commit chain and independent rollback detection."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from provisioner.controlplane.evidence import (AuditCheckpointRepository,
                                               EvidenceIntegrityError,
                                               FileCheckpointStore)
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.persistence.migrate import apply_migrations
from tests.provisioning.evidence.test_postgres_evidence import TestSigner


class PostgresAuditChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.migration_dsn = os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN')
        cls.runtime_dsn = os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN')
        cls.admin_dsn = os.environ.get('HOSTING_TEST_POSTGRES_ADMIN_DSN')
        if not cls.migration_dsn or not cls.runtime_dsn:
            raise unittest.SkipTest('Set isolated PostgreSQL migration/runtime DSNs')
        try:
            import psycopg
            from psycopg import sql
        except ImportError as exc:
            raise unittest.SkipTest('Install hosting-provisioner[controlplane]') from exc
        cls.psycopg = psycopg
        apply_migrations(lambda: psycopg.connect(cls.migration_dsn))
        with psycopg.connect(cls.runtime_dsn) as connection:
            role_name = connection.execute('SELECT current_user').fetchone()[0]
            flags = connection.execute('SELECT rolsuper, rolbypassrls FROM pg_roles '
                                       'WHERE rolname = current_user').fetchone()
            if flags != (False, False):
                raise RuntimeError('Audit verifier requires NOBYPASSRLS runtime role')
        with psycopg.connect(cls.migration_dsn) as connection:
            role = sql.Identifier(role_name)
            connection.execute(sql.SQL('GRANT USAGE ON SCHEMA hosting_controlplane TO {}').format(role))
            connection.execute(sql.SQL('GRANT SELECT ON hosting_controlplane.audit_streams '
                                       'TO {}').format(role))
            connection.execute(sql.SQL('GRANT SELECT, INSERT ON hosting_controlplane.audit_events '
                                       'TO {}').format(role))
            connection.execute(sql.SQL('GRANT USAGE ON ALL SEQUENCES IN SCHEMA '
                                       'hosting_controlplane TO {}').format(role))

    def setUp(self):
        suffix = uuid4().hex[:12]
        self.context = TenantContext('audit-' + suffix, 'tenant-a')
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.checkpoints = FileCheckpointStore(Path(self.directory.name) / 'audit-checkpoints')
        self.signer = TestSigner()
        self.repository = AuditCheckpointRepository(
            lambda: self.psycopg.connect(self.runtime_dsn),
            self.checkpoints, self.signer, self.signer)
        self.repository.initialize(self.context, expected_sequence=0,
                                   expected_head_hash='0' * 64)

    def _append(self, correlation: str, *, details: dict | None = None):
        with self.psycopg.connect(self.runtime_dsn) as connection:
            connection.execute("SELECT set_config('app.organization_id', %s, true), "
                               "set_config('app.tenant_id', %s, true)",
                               (self.context.organization_id, self.context.tenant_id))
            return connection.execute(
                'INSERT INTO hosting_controlplane.audit_events '
                '(organization_id, tenant_id, actor_id, correlation_id, action, '
                'record_kind, record_id, revision, record_digest, details) '
                "VALUES (%s, %s, %s, %s, 'RECORD_CREATE', 'Workload', %s, 1, %s, %s::jsonb) "
                'RETURNING audit_sequence, previous_hash, event_hash',
                (self.context.organization_id, self.context.tenant_id, 'operator-' + correlation,
                 correlation, 'workload-' + correlation, 'a' * 64,
                 json.dumps(details or {}))).fetchone()

    def test_all_audit_rows_are_chained_and_scoped(self):
        first = self._append('first', details={'Unicode': 'café', 'reason': 'approved'})
        second = self._append('second')
        self.assertEqual((first[0], first[1], second[0], second[1]),
                         (1, '0' * 64, 2, first[2]))
        self.assertEqual(self.repository.verify(self.context).unanchored_count, 2)
        anchor = self.repository.checkpoint(self.context)
        self.assertEqual((anchor.sequence, anchor.head_hash), (2, second[2]))
        self.assertEqual(self.repository.verify(self.context).unanchored_count, 0)
        foreign = TenantContext(self.context.organization_id, 'tenant-b')
        self.repository.initialize(foreign, expected_sequence=0,
                                   expected_head_hash='0' * 64)
        self.assertEqual(self.repository.verify(foreign).head_sequence, 0)

    def test_corrupt_external_signature_and_stale_restored_prefix(self):
        first = self._append('first')
        self.repository.checkpoint(self.context)
        path = self.checkpoints._directory(self.context.organization_id,
                                            self.context.tenant_id) / '00000000000000000001.json'
        original = path.read_bytes()
        envelope = json.loads(original)
        envelope['signature'] = 'AAAA'
        path.write_text(json.dumps(envelope))
        with self.assertRaises(EvidenceIntegrityError):
            self.repository.verify(self.context)
        path.write_bytes(original)
        self.assertEqual(self.repository.verify(self.context).head_hash, first[2])
        if not self.admin_dsn:
            return
        # A privileged rollback of the database to an older tenant prefix
        # cannot roll back the independently retained signed watermark.
        with self.psycopg.connect(self.admin_dsn) as connection:
            connection.execute('ALTER TABLE hosting_controlplane.audit_events '
                               'DISABLE TRIGGER audit_append_only')
            connection.execute('DELETE FROM hosting_controlplane.audit_events '
                               'WHERE organization_id = %s AND tenant_id = %s',
                               (self.context.organization_id, self.context.tenant_id))
            connection.execute('UPDATE hosting_controlplane.audit_streams '
                               "SET last_sequence = 0, head_hash = repeat('0', 64) "
                               'WHERE organization_id = %s AND tenant_id = %s',
                               (self.context.organization_id, self.context.tenant_id))
            connection.execute('ALTER TABLE hosting_controlplane.audit_events '
                               'ENABLE TRIGGER audit_append_only')
        with self.assertRaises(EvidenceIntegrityError):
            self.repository.verify(self.context)

    def test_modified_audit_row_is_rejected_even_without_a_new_checkpoint(self):
        self._append('first')
        if not self.admin_dsn:
            self.skipTest('Privileged test role is needed for tamper injection')
        with self.psycopg.connect(self.admin_dsn) as connection:
            connection.execute('ALTER TABLE hosting_controlplane.audit_events '
                               'DISABLE TRIGGER audit_append_only')
            connection.execute('UPDATE hosting_controlplane.audit_events '
                               "SET details = '{\"forged\":true}'::jsonb "
                               'WHERE organization_id = %s AND tenant_id = %s',
                               (self.context.organization_id, self.context.tenant_id))
            connection.execute('ALTER TABLE hosting_controlplane.audit_events '
                               'ENABLE TRIGGER audit_append_only')
        with self.assertRaises(EvidenceIntegrityError):
            self.repository.verify(self.context)


if __name__ == '__main__':
    unittest.main()
