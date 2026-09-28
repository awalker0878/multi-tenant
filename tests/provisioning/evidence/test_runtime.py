"""Installed evidence configuration and mutation lag gates."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from provisioner.controlplane.evidence.runtime import (
    EvidenceHold, EvidenceMutationGate, EvidenceRuntimeConfig, _private_file,
    build_gate, main)
from provisioner.controlplane.persistence import TenantContext
from tests.provisioning.evidence.test_retained_adapters import FakeObjectLock, FakeTransit


def environment():
    return {
        'HOSTING_RUNTIME_DSN':
            'host=postgres.example.org dbname=hosting user=runtime sslmode=verify-full',
        'HOSTING_EVIDENCE_S3_ENDPOINT': 'https://objects.example.org',
        'HOSTING_EVIDENCE_S3_REGION': 'sovereign-1',
        'HOSTING_EVIDENCE_S3_CA': '/etc/hosting/objects-ca.pem',
        'HOSTING_EVIDENCE_S3_ACCESS_KEY_ID': 'scoped-writer',
        'HOSTING_EVIDENCE_S3_SECRET_FILE': '/run/hosting/object-secret',
        'HOSTING_EVIDENCE_ARTIFACT_BUCKET': 'artifact-retained',
        'HOSTING_EVIDENCE_CHECKPOINT_BUCKET': 'checkpoint-independent',
        'HOSTING_EVIDENCE_RETENTION_DAYS': '365',
        'HOSTING_EVIDENCE_VAULT_URL': 'https://vault.example.org',
        'HOSTING_EVIDENCE_VAULT_CA': '/etc/hosting/vault-ca.pem',
        'HOSTING_EVIDENCE_VAULT_VERIFY_TOKEN_FILE': '/run/hosting/vault-verify-token',
        'HOSTING_EVIDENCE_VAULT_SIGN_TOKEN_FILE': '/run/hosting/vault-sign-token',
        'HOSTING_EVIDENCE_VAULT_MOUNT': 'transit',
        'HOSTING_EVIDENCE_VAULT_KEY': 'checkpoints',
        'HOSTING_EVIDENCE_VAULT_KEY_ID': 'evidence-2026',
        'HOSTING_EVIDENCE_VAULT_TRUST_JSON':
            '{"evidence-2026":["transit","checkpoints"]}',
        'HOSTING_EVIDENCE_MAX_UNANCHORED_COUNT': '0',
    }


class RuntimeEvidenceTests(unittest.TestCase):
    def test_api_composition_has_no_signing_key_and_runner_requires_one(self):
        values = environment()
        values.pop('HOSTING_EVIDENCE_VAULT_SIGN_TOKEN_FILE')
        config = EvidenceRuntimeConfig.from_environment(values)
        service = FakeObjectLock()
        verifier = FakeTransit()
        gate = build_gate(config, s3_client=service, verifier_client=verifier,
                          connection_factory=lambda: None)
        with self.assertRaises(EvidenceHold):
            gate.audit._signer.sign(b'checkpoint')
        with self.assertRaises(ValueError):
            build_gate(config, s3_client=service, verifier_client=verifier,
                       signer_client=verifier, connection_factory=lambda: None,
                       allow_signing=True)
        runner = build_gate(EvidenceRuntimeConfig.from_environment(environment()),
                            s3_client=service, verifier_client=verifier,
                            signer_client=verifier, connection_factory=lambda: None,
                            allow_signing=True)
        self.assertTrue(runner.audit._signer.sign(b'checkpoint'))

    def test_operator_cli_requires_attested_enrollment_and_calls_checkpoint(self):
        calls = []
        gate = SimpleNamespace(
            evidence=SimpleNamespace(initialize=lambda ctx: calls.append('evidence-enroll')),
            audit=SimpleNamespace(initialize=lambda ctx, **kw: calls.append(
                ('audit-enroll', kw['expected_sequence'], kw['expected_head_hash'])),
                inspect_baseline=lambda ctx: (0, '0' * 64)),
            checkpoint=lambda ctx: calls.append('checkpoint'),
            require=lambda ctx: calls.append('verify'))
        common = ['--organization-id', 'org', '--tenant-id', 'tenant']
        with (patch('provisioner.controlplane.evidence.runtime.EvidenceRuntimeConfig.from_environment'),
              patch('provisioner.controlplane.evidence.runtime.build_gate', return_value=gate)):
            with self.assertRaises(SystemExit):
                main(['enroll', *common])
            self.assertEqual(calls, [])
            self.assertEqual(main(['inspect', *common]), 0)
            self.assertEqual(main(['enroll', *common, '--expected-audit-sequence', '0',
                                   '--expected-audit-head', '0' * 64]), 0)
            self.assertEqual(main(['checkpoint', *common]), 0)
            self.assertEqual(main(['verify', *common]), 0)
        self.assertEqual(calls, ['evidence-enroll', ('audit-enroll', 0, '0' * 64),
                                 'checkpoint', 'verify'])

    def test_config_requires_independent_https_services_trust_and_scope_inventory(self):
        values = environment()
        with self.assertRaises(ValueError):
            EvidenceRuntimeConfig.from_environment(values, require_scopes=True)
        with tempfile.TemporaryDirectory() as directory:
            scopes = Path(directory) / 'scopes.json'
            scopes.write_text(json.dumps([{'organizationId': 'org', 'tenantId': 'tenant'}]))
            values['HOSTING_EVIDENCE_SCOPES_FILE'] = str(scopes)
            config = EvidenceRuntimeConfig.from_environment(values, require_scopes=True)
            self.assertEqual(config.startup_scopes(), (TenantContext('org', 'tenant'),))
            for name, bad in (
                    ('HOSTING_EVIDENCE_S3_ENDPOINT', 'http://objects.example.org'),
                    ('HOSTING_EVIDENCE_S3_ENDPOINT', 'https://user:pass@objects.example.org'),
                    ('HOSTING_EVIDENCE_CHECKPOINT_BUCKET', 'artifact-retained'),
                    ('HOSTING_EVIDENCE_VAULT_TRUST_JSON', '{}'),
                    ('HOSTING_EVIDENCE_MAX_UNANCHORED_COUNT', '-1')):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    EvidenceRuntimeConfig.from_environment(dict(values, **{name: bad}))
            scopes.chmod(0o666)
            with self.assertRaises(ValueError):
                config.startup_scopes()

    def test_private_credential_file_rejects_insecure_mode_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            secret = Path(directory) / 'token'
            secret.write_text('vault-test-token\n')
            secret.chmod(0o600)
            self.assertEqual(_private_file(secret), 'vault-test-token')
            secret.chmod(0o644)
            with self.assertRaises(ValueError):
                _private_file(secret)
            secret.chmod(0o600)
            shortcut = Path(directory) / 'link'
            shortcut.symlink_to(secret)
            with self.assertRaises(OSError):
                _private_file(shortcut)

    def test_signed_prefix_lag_and_missing_service_hold_mutation(self):
        class Provider:
            def __init__(self, count):
                self.count = count
                self.fail = False

            def verify(self, context):
                if self.fail:
                    raise OSError('external checkpoint unavailable')
                return SimpleNamespace(unanchored_count=self.count)

            def checkpoint(self, context):
                self.count = 0

        audit, evidence = Provider(1), Provider(0)
        gate = EvidenceMutationGate(audit, evidence, max_unanchored_count=0)
        ctx = TenantContext('org', 'tenant')
        with self.assertRaises(EvidenceHold):
            gate.require(ctx)
        gate.checkpoint(ctx)
        gate.require(ctx)
        evidence.fail = True
        with self.assertRaises(EvidenceHold):
            gate.require(ctx)


if __name__ == '__main__':
    unittest.main()
