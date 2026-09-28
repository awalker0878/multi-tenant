"""Credential filtering and create-only file adapter failure behavior."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from provisioner.controlplane.evidence.filesystem import (FileArtifactStore,
                                                           FileCheckpointStore)
from provisioner.controlplane.evidence.repository import _validated_artifact
from provisioner.controlplane.evidence.repository import EvidenceRepository
from provisioner.controlplane.persistence import TenantContext


class EvidenceContractTests(unittest.TestCase):
    def test_runtime_role_must_enforce_rls_before_scope_is_set(self):
        class Cursor:
            connection = type('Connection', (), {'autocommit': False})()

            def __init__(self, role):
                self.role = role
                self.statements = []

            def execute(self, statement, parameters=None):
                self.statements.append((statement, parameters))

            def fetchone(self):
                return self.role

        context = TenantContext('organization-1', 'tenant-1')
        for role in (None, (True, False), (False, True)):
            cursor = Cursor(role)
            with self.subTest(role=role), self.assertRaises(RuntimeError):
                EvidenceRepository._tenant(cursor, context)
            self.assertEqual(len(cursor.statements), 1)
        cursor = Cursor((False, False))
        EvidenceRepository._tenant(cursor, context)
        self.assertEqual(len(cursor.statements), 2)
        self.assertIn('set_config', cursor.statements[-1][0])

    def test_credential_fields_urls_and_nonsensical_json_are_rejected(self):
        for artifact in (
                {'password': 'example'}, {'nested': {'api_key': 'example'}},
                {'headers': [{'Authorization': 'example'}]},
                {'endpoint': 'https://example.invalid/path?token=example'},
                {'note': 'Bearer example'}, {'note': 'password=canary-value'},
                {'note': '-----BEGIN PRIVATE KEY-----'},
                {'note': 'sk_test_12345678901234567890'},
                {'note': 'x' * 513}, {'n': float('nan')}):
            with self.subTest(artifact=artifact), self.assertRaises(ValueError):
                _validated_artifact(artifact)
        self.assertEqual(_validated_artifact({'result': 'PASS', 'digest': 'abc'}),
                         b'{"digest":"abc","result":"PASS"}')

    def test_content_addressed_store_detects_mutation_and_path_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = FileArtifactStore(root)
            content = b'{"result":"PASS"}'
            digest = hashlib.sha256(content).hexdigest()
            artifacts.put(digest, content)
            artifacts.put(digest, content)
            self.assertEqual(artifacts.get(digest), content)
            with self.assertRaises(ValueError):
                artifacts.get('../other')
            path = root / digest[:2] / digest
            path.write_bytes(b'{"result":"FAIL"}')
            with self.assertRaises(ValueError):
                artifacts.get(digest)
            with self.assertRaises(ValueError):
                artifacts.put(digest, content)

    def test_checkpoint_file_never_overwrites_a_signed_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoints = FileCheckpointStore(Path(directory))
            payload = {'organizationId': 'one', 'tenantId': 'two', 'sequence': 0}
            envelope = {'payload': payload, 'signature': 'a'}
            checkpoints.publish(envelope)
            self.assertEqual(checkpoints.latest('one', 'two'), envelope)
            checkpoints.publish(envelope)
            with self.assertRaises(ValueError):
                checkpoints.publish({'payload': payload, 'signature': 'b'})
            self.assertIsNone(checkpoints.latest('one', 'other'))


if __name__ == '__main__':
    unittest.main()
