"""Real Ed25519 provenance rejects cross-scope, replay and revoked identities."""
from __future__ import annotations

import base64
import json
import os
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provisioner.controlplane.discovery.model import assemble_discovery_result
from provisioner.controlplane.discovery.trust import (
    DiscoveryKeyEnrollment, DiscoverySignature, DiscoveryTrustDenied,
    DiscoveryTrustPolicy, ReadOnlyCredentialEvidence, SignedDiscoveryIngestVerifier,
    SignedFileDiscoveryTrustStore, campaign_signing_bytes, result_signing_bytes,
    trust_policy_signing_bytes,
)
from tests.provisioning.controlplane.test_discovery_model import (
    SCOPE, START, campaign, obj, page,
)


def encoded(raw):
    return base64.b64encode(raw).decode('ascii')


class CredentialAuthority:
    def __init__(self):
        self.calls = []
        self.denied = False
        self.changes = {}

    def verify_read_only(self, reference, *, collector_id, environment_id,
                         scope, checked_at):
        self.calls.append((reference, collector_id, environment_id, scope, checked_at))
        if self.denied:
            raise DiscoveryTrustDenied('Native credential revoked or write-capable')
        return replace(ReadOnlyCredentialEvidence(reference, collector_id, environment_id,
            scope, checked_at, START + timedelta(hours=1), 'a' * 64), **self.changes)


class DiscoveryTrustTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'policy.json'
        self.authority = Ed25519PrivateKey.generate()
        self.issuer = Ed25519PrivateKey.generate()
        self.collector = Ed25519PrivateKey.generate()
        self.now = START + timedelta(minutes=3)
        self.campaign = campaign()
        self.result = assemble_discovery_result(self.campaign, (page(),), checked_at=self.now)
        self.issuer_enrollment = DiscoveryKeyEnrollment(
            'issuer-key-1', 'approvals-service', 'issuer',
            encoded(self.issuer.public_key().public_bytes_raw()),
            'environment-1', SCOPE, START, START + timedelta(hours=1))
        self.collector_enrollment = DiscoveryKeyEnrollment(
            'collector-key-1', 'collector-01', 'collector',
            encoded(self.collector.public_key().public_bytes_raw()),
            'environment-1', SCOPE, START, START + timedelta(hours=1), 'vault:read-01')
        self.policy = DiscoveryTrustPolicy(1, START, START + timedelta(hours=1),
            (self.issuer_enrollment, self.collector_enrollment))
        self.write_policy(self.policy)
        self.store = SignedFileDiscoveryTrustStore(self.path,
            authority_public_key=self.authority.public_key(), minimum_revision=1)
        self.credentials = CredentialAuthority()
        self.verifier = SignedDiscoveryIngestVerifier(self.store, self.credentials)
        self.campaign_signature = self.sign_campaign(self.campaign)
        self.result_signature = self.sign_result(self.result)
        self.bound = self.verifier.bind(self.campaign_signature, self.result_signature)

    def write_policy(self, policy, *, key=None):
        self.path.write_text(json.dumps({'policy': policy.as_dict(),
            'signature': encoded((key or self.authority).sign(trust_policy_signing_bytes(policy)))}))
        self.path.chmod(0o600)

    def sign_campaign(self, value, *, environment='environment-1', key=None, key_id='issuer-key-1'):
        return DiscoverySignature(key_id, encoded((key or self.issuer).sign(
            campaign_signing_bytes(value, environment))))

    def sign_result(self, value, *, campaign_value=None, environment='environment-1',
                    key=None, key_id='collector-key-1'):
        return DiscoverySignature(key_id, encoded((key or self.collector).sign(
            result_signing_bytes(campaign_value or self.campaign, value, environment))))

    def verify_result(self, **changes):
        return self.bound.verify_result(changes.get('campaign', self.campaign),
            changes.get('result', self.result), changes.get('environment', 'environment-1'),
            changes.get('checked_at', self.now))

    def test_campaign_and_result_have_exact_digests_and_live_credential_checks(self):
        proof = self.bound.verify_campaign(self.campaign, 'environment-1', self.now)
        self.assertEqual(proof.authorization_digest, self.campaign.digest())
        self.assertIsNone(proof.result_digest)
        self.assertEqual(proof.verified_by, 'approvals-service')
        result = self.verify_result()
        self.assertEqual(result.result_digest, self.result.digest)
        self.assertEqual(result.verified_by, 'collector-01')
        self.assertNotEqual(proof.verification_reference, result.verification_reference)
        self.assertEqual(len(self.credentials.calls), 2)

    def test_campaign_signature_binds_every_authorization_field(self):
        changes = ({'campaign_id': 'campaign-2'}, {'authority_reference': 'other-approval'},
            {'max_objects': 6}, {'max_pages': 5}, {'max_page_size': 3},
            {'allowed_kinds': ('vm',)}, {'collector_id': 'collector-2'},
            {'issued_at': START + timedelta(seconds=1)},
            {'expires_at': START + timedelta(minutes=14)})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(DiscoveryTrustDenied):
                self.bound.verify_campaign(replace(self.campaign, **change),
                                           'environment-1', self.now)

    def test_unapproved_environment_and_each_scope_component_denied_even_if_resigned(self):
        for field in SCOPE.__dataclass_fields__:
            value = 'vmware' if field == 'platform_family' else 'different'
            foreign = replace(self.campaign, scope=replace(SCOPE, **{field: value}))
            with self.subTest(field=field), self.assertRaises(DiscoveryTrustDenied):
                self.verifier.bind(self.sign_campaign(foreign)).verify_campaign(
                    foreign, 'environment-1', self.now)
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify_result(environment='environment-2')

    def test_result_signature_binds_content_and_cannot_be_a_campaign_signature(self):
        changed = replace(self.result, objects=(obj('different-vm'),))
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify_result(result=changed)
        for signature in (None, self.campaign_signature, DiscoverySignature(
                'collector-key-1', self.campaign_signature.signature),
                self.sign_result(self.result, key=Ed25519PrivateKey.generate())):
            with self.subTest(signature=signature), self.assertRaises(DiscoveryTrustDenied):
                self.verifier.bind(self.campaign_signature, signature).verify_result(
                    self.campaign, self.result, 'environment-1', self.now)

    def test_issuer_and_collector_revocation_are_live_on_existing_bound_verifier(self):
        for position in (0, 1):
            self.verify_result()
            entries = list(self.policy.enrollments)
            entries[position] = replace(entries[position], revoked_at=self.now)
            revised = replace(self.policy, revision=self.policy.revision + 1,
                               enrollments=tuple(entries))
            self.write_policy(revised)
            with self.subTest(position=position), self.assertRaises(DiscoveryTrustDenied):
                self.verify_result()
            # A later authority-approved revision can explicitly enroll again.
            self.policy = replace(self.policy, revision=revised.revision + 1)
            self.write_policy(self.policy)

    def test_removed_collector_and_expired_key_are_not_implicitly_enrolled(self):
        for enrollment in (None, replace(self.collector_enrollment,
                expires_at=START + timedelta(minutes=10)), replace(self.collector_enrollment,
                not_before=START + timedelta(seconds=1))):
            entries = (self.issuer_enrollment,) + ((enrollment,) if enrollment else ())
            self.policy = replace(self.policy, revision=self.policy.revision + 1,
                                  enrollments=entries)
            self.write_policy(self.policy)
            with self.assertRaises(DiscoveryTrustDenied):
                self.verify_result()

    def test_authority_signed_rotation_requires_new_collectors_actual_private_key(self):
        replacement = Ed25519PrivateKey.generate()
        rotated = replace(self.collector_enrollment, key_id='collector-key-2',
            public_key=encoded(replacement.public_key().public_bytes_raw()))
        self.write_policy(replace(self.policy, revision=2, enrollments=(
            self.issuer_enrollment, replace(self.collector_enrollment, revoked_at=self.now),
            rotated)))
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify_result()
        relabeled = replace(self.result_signature, key_id=rotated.key_id)
        with self.assertRaises(DiscoveryTrustDenied):
            self.verifier.bind(self.campaign_signature, relabeled).verify_result(
                self.campaign, self.result, 'environment-1', self.now)
        new_signature = self.sign_result(self.result, key=replacement, key_id=rotated.key_id)
        verified = self.verifier.bind(self.campaign_signature, new_signature).verify_result(
            self.campaign, self.result, 'environment-1', self.now)
        self.assertEqual(verified.result_digest, self.result.digest)

    def test_untrusted_root_tamper_missing_file_and_expiry_fail_closed(self):
        self.verify_result()
        self.write_policy(self.policy, key=Ed25519PrivateKey.generate())
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify_result()
        self.write_policy(self.policy)
        body = json.loads(self.path.read_text())
        body['policy']['enrollments'][0]['subjectId'] = 'imposter'
        self.path.write_text(json.dumps(body))
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify_result()
        self.path.unlink()
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify_result()
        self.write_policy(self.policy)
        for checked_at in (START - timedelta(seconds=1), self.policy.expires_at):
            with self.assertRaises(DiscoveryTrustDenied):
                self.store.current_policy(checked_at)

    def test_signed_policy_cannot_roll_back_or_equivocate_and_floor_survives_restart(self):
        advanced = replace(self.policy, revision=2)
        self.write_policy(advanced)
        self.verify_result()
        for invalid in (self.policy, replace(advanced, expires_at=START + timedelta(minutes=30))):
            self.write_policy(invalid)
            with self.assertRaises(DiscoveryTrustDenied):
                self.verify_result()
        self.write_policy(self.policy)
        restarted = SignedFileDiscoveryTrustStore(self.path,
            authority_public_key=self.authority.public_key(), minimum_revision=2)
        with self.assertRaises(DiscoveryTrustDenied):
            restarted.current_policy(self.now)

    def test_live_native_read_credential_revocation_and_scope_mismatch_denied(self):
        self.verify_result()
        self.credentials.denied = True
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify_result()
        self.credentials.denied = False
        for changes in ({'collector_id': 'other'}, {'credential_reference': 'other'},
                        {'environment_id': 'other'}, {'scope': replace(SCOPE, endpoint_id='other')},
                        {'checked_at': self.now - timedelta(seconds=1)},
                        {'expires_at': self.now + timedelta(seconds=1)}):
            self.credentials.changes = changes
            with self.subTest(changes=changes), self.assertRaises(DiscoveryTrustDenied):
                self.verify_result()

    def test_policy_permissions_symlink_fifo_oversize_and_duplicate_fields_fail_closed(self):
        self.path.chmod(0o666)
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify_result()
        self.path.unlink()
        target = self.path.with_name('target.json')
        target.write_text('{}')
        self.path.symlink_to(target)
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify_result()
        self.path.unlink()
        os.mkfifo(self.path)
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify_result()
        self.path.unlink()
        self.path.write_text(' ' * 1048577)
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify_result()
        self.write_policy(self.policy)
        raw = self.path.read_text().replace('"revision": 1', '"revision": 1, "revision": 1')
        self.path.write_text(raw)
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify_result()

    def test_result_future_capture_budget_and_mutated_digest_are_denied(self):
        for value in (replace(self.result, captured_at=self.now + timedelta(seconds=1)),
                      replace(self.result, captured_at=START - timedelta(seconds=1)),
                      replace(self.result, objects=tuple(obj(f'vm-{i}') for i in range(6))),
                      replace(self.result, objects=(obj(kind='host'),))):
            with self.assertRaises(DiscoveryTrustDenied):
                self.verifier.bind(self.campaign_signature, self.sign_result(value)).verify_result(
                    self.campaign, value, 'environment-1', self.now)
        object.__setattr__(self.result, 'objects', (obj('tampered'),))
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify_result()

    def test_trust_expiry_and_invalid_policy_records_are_rejected(self):
        with self.assertRaises(DiscoveryTrustDenied):
            replace(self.policy, expires_at=START + timedelta(hours=25))
        with self.assertRaises(DiscoveryTrustDenied):
            replace(self.policy, enrollments=(self.issuer_enrollment, self.issuer_enrollment))
        with self.assertRaises(DiscoveryTrustDenied):
            replace(self.policy, enrollments=(self.issuer_enrollment,
                replace(self.collector_enrollment, public_key=self.issuer_enrollment.public_key)))
        with self.assertRaises(ValueError):
            SignedDiscoveryIngestVerifier(self.store, None)
        with self.assertRaises(DiscoveryTrustDenied):
            DiscoverySignature('key-1', encoded(b'invalid'))


if __name__ == '__main__':
    unittest.main()
