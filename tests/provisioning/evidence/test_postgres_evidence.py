"""Real tenant-scoped PostgreSQL evidence and signed checkpoint tests."""
from __future__ import annotations

import os
import json
import base64
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from provisioner.controlplane.evidence import (EvidenceConflict,
                                               EvidenceIntegrityError,
                                               EvidenceRepository,
                                               EvidenceUnavailable,
                                               FileArtifactStore,
                                               FileCheckpointStore)
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.persistence.migrate import apply_migrations


class TestSigner:
    key_id = 'test-ephemeral-ed25519'

    def __init__(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        self.private = Ed25519PrivateKey.generate()
        self.public = self.private.public_key()

    def sign(self, payload: bytes) -> bytes:
        return self.private.sign(payload)

    def verify(self, key_id: str, payload: bytes, signature: bytes) -> None:
        if key_id != self.key_id:
            raise ValueError('Unknown signing identity')
        self.public.verify(signature, payload)


class FailingCheckpointStore(FileCheckpointStore):
    fail = False

    def publish(self, envelope: dict) -> None:
        if self.fail:
            raise OSError('Simulated external checkpoint outage')
        super().publish(envelope)


class PostgresEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.migration_dsn = os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN')
        cls.runtime_dsn = os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN')
        if not cls.migration_dsn or not cls.runtime_dsn:
            raise unittest.SkipTest('Set PostgreSQL migration/runtime DSNs')
        try:
            import psycopg
            from psycopg import sql
            import cryptography
        except ImportError as exc:
            raise unittest.SkipTest('Install hosting-provisioner[controlplane]') from exc
        cls.psycopg = psycopg
        apply_migrations(lambda: psycopg.connect(cls.migration_dsn))
        with psycopg.connect(cls.runtime_dsn) as connection:
            runtime = connection.execute('SELECT current_user').fetchone()[0]
            flags = connection.execute('SELECT rolsuper, rolbypassrls FROM pg_roles '
                                       'WHERE rolname = current_user').fetchone()
            if flags[0] or flags[1]:
                raise RuntimeError('Evidence tests require a NOBYPASSRLS runtime role')
        # CI role provisioning grants the same DML. This also keeps the test
        # runnable against an isolated developer PostgreSQL instance.
        with psycopg.connect(cls.migration_dsn) as connection:
            role = sql.Identifier(runtime)
            connection.execute(sql.SQL('GRANT USAGE ON SCHEMA hosting_controlplane TO {}').format(role))
            connection.execute(sql.SQL('GRANT SELECT, INSERT, UPDATE ON '
                                       'hosting_controlplane.evidence_streams TO {}').format(role))
            connection.execute(sql.SQL('GRANT SELECT, INSERT ON '
                                       'hosting_controlplane.evidence_entries TO {}').format(role))

    def setUp(self):
        suffix = uuid4().hex[:12]
        self.context = TenantContext('evidence-' + suffix, 'tenant-a')
        self.foreign = TenantContext(self.context.organization_id, 'tenant-b')
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.artifacts = FileArtifactStore(root / 'artifacts')
        self.checkpoints = FailingCheckpointStore(root / 'independent-checkpoints')
        self.signer = TestSigner()
        self.repository = EvidenceRepository(
            lambda: self.psycopg.connect(self.runtime_dsn), self.artifacts,
            self.checkpoints, self.signer, self.signer)
        self.repository.initialize(self.context)

    def test_append_replay_foreign_scope_and_mutation(self):
        initial = self.repository.append(
            self.context, event_key='native-result-1',
            evidence_kind='NATIVE_RECEIPT', subject_id='job-1',
            artifact={'status': 'COMPLETED', 'nativeTaskId': 'task-1'})
        self.assertEqual(initial.sequence, 1)
        self.assertEqual(self.repository.verify(self.context).unanchored_count, 0)
        self.assertEqual(self.repository.append(
            self.context, event_key='native-result-1',
            evidence_kind='NATIVE_RECEIPT', subject_id='job-1',
            artifact={'nativeTaskId': 'task-1', 'status': 'COMPLETED'}), initial)
        with self.assertRaises(EvidenceConflict):
            self.repository.append(self.context, event_key='native-result-1',
                                   evidence_kind='NATIVE_RECEIPT', subject_id='job-1',
                                   artifact={'status': 'FAILED'})
        self.repository.initialize(self.foreign)
        self.assertIsNone(self.repository.get(self.foreign, 'native-result-1'))
        self.assertEqual(self.repository.get(self.context, 'native-result-1')[0], initial)
        with self.psycopg.connect(self.runtime_dsn) as connection:
            connection.execute("SELECT set_config('app.organization_id', %s, true), "
                               "set_config('app.tenant_id', %s, true)",
                               (self.context.organization_id, self.context.tenant_id))
            with self.assertRaises(self.psycopg.Error):
                connection.execute('UPDATE hosting_controlplane.evidence_entries '
                                   "SET subject_id = 'forged'")
            connection.rollback()

    def test_tampered_bytes_signature_and_stale_prefix_fail_closed(self):
        entry = self.repository.append(
            self.context, event_key='observed', evidence_kind='OBSERVATION',
            subject_id='workload-1', artifact={'status': 'OBSERVED'})
        path = self.artifacts._path(entry.blob_digest)
        path.write_bytes(b'{"status":"FORGED"}')
        with self.assertRaises(EvidenceIntegrityError):
            self.repository.verify(self.context)
        # A distinct tenant demonstrates checkpoint signature and rollback
        # detection without needing privileged SQL to disable append-only guards.
        context = TenantContext(self.context.organization_id, 'tenant-c')
        self.repository.initialize(context)
        self.repository.append(context, event_key='observed',
                               evidence_kind='OBSERVATION', subject_id='workload-1',
                               artifact={'status': 'AVAILABLE'})
        checkpoint_path = self.checkpoints._directory(
            context.organization_id, context.tenant_id) / '00000000000000000001.json'
        envelope = json.loads(checkpoint_path.read_text())
        envelope['signature'] = 'AAAA'
        checkpoint_path.write_text(json.dumps(envelope))
        with self.assertRaises(EvidenceIntegrityError):
            self.repository.verify(context)
        # Restore the signed file. A higher independent watermark than the
        # database models a stale restored database prefix and must be held.
        envelope['signature'] = base64.b64encode(self.signer.sign(
            json.dumps(envelope['payload'], sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False).encode())).decode()
        checkpoint_path.write_text(json.dumps(envelope))
        stale = dict(envelope['payload'], sequence=2, headHash='f' * 64)
        stale_envelope = {'payload': stale, 'signature': base64.b64encode(
            self.signer.sign(json.dumps(stale, sort_keys=True, separators=(',', ':'),
                                        ensure_ascii=False).encode())).decode()}
        self.checkpoints.publish(stale_envelope)
        with self.assertRaises(EvidenceIntegrityError):
            self.repository.verify(context)

    def test_outage_after_commit_is_retryable_by_same_event(self):
        self.checkpoints.fail = True
        with self.assertRaises(EvidenceUnavailable):
            self.repository.append(self.context, event_key='result-1',
                                   evidence_kind='VERIFICATION_RESULT',
                                   subject_id='job-1', artifact={'result': 'PASS'})
        self.assertEqual(self.repository.verify(self.context).unanchored_count, 1)
        self.checkpoints.fail = False
        entry = self.repository.append(self.context, event_key='result-1',
                                       evidence_kind='VERIFICATION_RESULT',
                                       subject_id='job-1', artifact={'result': 'PASS'})
        self.assertEqual(entry.sequence, 1)
        self.assertEqual(self.repository.verify(self.context).unanchored_count, 0)


if __name__ == '__main__':
    unittest.main()
