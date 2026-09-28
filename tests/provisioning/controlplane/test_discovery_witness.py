"""Independent signed native-read witnesses stay current and exact in scope."""
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

from provisioner.controlplane.discovery.trust import DiscoveryTrustDenied
from provisioner.controlplane.discovery.witness import (
    NativeCredentialWitnessPolicy, NativeReadCredentialWitness,
    SignedFileDiscoveryCredentialAuthority, credential_witness_signing_bytes,
)
from tests.provisioning.controlplane.test_discovery_model import SCOPE, START


class DiscoveryCredentialWitnessTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'native-credential-witness.json'
        self.key = Ed25519PrivateKey.generate()
        self.now = START + timedelta(minutes=2)
        self.witness = NativeReadCredentialWitness(
            'vault:reader-01', 'collector-01', 'environment-01', SCOPE,
            'native-rbac-observation-01', 'a' * 64, START,
            START + timedelta(hours=1), True)
        self.policy = NativeCredentialWitnessPolicy(
            3, START, START + timedelta(minutes=5), (self.witness,))
        self.write_policy(self.policy)
        self.authority = SignedFileDiscoveryCredentialAuthority(self.path,
            authority_public_key=self.key.public_key(), minimum_revision=3)

    def write_policy(self, policy, *, key=None):
        signature = (key or self.key).sign(credential_witness_signing_bytes(policy))
        self.path.write_text(json.dumps({'policy': policy.as_dict(),
            'signature': base64.b64encode(signature).decode('ascii')}))
        self.path.chmod(0o600)

    def verify(self, **changes):
        values = dict(credential_reference=self.witness.credential_reference,
            collector_id=self.witness.collector_id,
            environment_id=self.witness.environment_id, scope=SCOPE,
            checked_at=self.now)
        values.update(changes)
        return self.authority.verify_read_only(**values)

    def test_fresh_exact_witness_returns_bound_evidence_without_native_secrets(self):
        evidence = self.verify()
        self.assertEqual(evidence.credential_reference, 'vault:reader-01')
        self.assertEqual(evidence.collector_id, 'collector-01')
        self.assertEqual(evidence.environment_id, 'environment-01')
        self.assertEqual(evidence.scope, SCOPE)
        self.assertEqual(evidence.checked_at, self.now)
        self.assertEqual(evidence.expires_at, self.witness.credential_expires_at)
        self.assertRegex(evidence.policy_digest, r'^[0-9a-f]{64}$')
        self.assertEqual(self.verify(), evidence)

    def test_only_independent_pinned_private_key_can_sign_the_policy(self):
        self.verify()
        self.write_policy(self.policy, key=Ed25519PrivateKey.generate())
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify()
        self.write_policy(self.policy)
        unrelated = SignedFileDiscoveryCredentialAuthority(self.path,
            authority_public_key=Ed25519PrivateKey.generate().public_key(),
            minimum_revision=3)
        with self.assertRaises(DiscoveryTrustDenied):
            unrelated.current_policy(self.now)

    def test_changed_policy_content_and_signature_fail_without_cached_fallback(self):
        self.verify()
        body = json.loads(self.path.read_text())
        body['policy']['witnesses'][0]['policyDigest'] = 'b' * 64
        self.path.write_text(json.dumps(body))
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify()
        self.write_policy(self.policy)
        body = json.loads(self.path.read_text())
        signature = bytearray(base64.b64decode(body['signature']))
        signature[-1] ^= 1
        body['signature'] = base64.b64encode(signature).decode('ascii')
        self.path.write_text(json.dumps(body))
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify()

    def test_revocation_and_write_permission_are_effective_on_next_check(self):
        for change in ({'revoked_at': self.now}, {'read_only': False}):
            with self.subTest(change=change):
                self.verify()
                self.policy = replace(self.policy, revision=self.policy.revision + 1,
                    witnesses=(replace(self.witness, **change),))
                self.write_policy(self.policy)
                with self.assertRaises(DiscoveryTrustDenied):
                    self.verify()
                self.policy = replace(self.policy, revision=self.policy.revision + 1,
                                      witnesses=(self.witness,))
                self.write_policy(self.policy)

    def test_scheduled_revocation_denies_at_exact_boundary(self):
        revocation = self.now + timedelta(seconds=1)
        self.write_policy(replace(self.policy,
            witnesses=(replace(self.witness, revoked_at=revocation),)))
        self.verify()
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify(checked_at=revocation)

    def test_missing_witness_does_not_reuse_prior_authorization(self):
        self.verify()
        self.write_policy(replace(self.policy, revision=4, witnesses=()))
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify()

    def test_credential_collector_environment_and_every_scope_field_must_match(self):
        for field in ('credential_reference', 'collector_id', 'environment_id'):
            with self.subTest(field=field), self.assertRaises(DiscoveryTrustDenied):
                self.verify(**{field: 'another-identity'})
        for field in SCOPE.__dataclass_fields__:
            other = 'vmware' if field == 'platform_family' else 'other'
            with self.subTest(scope_field=field), self.assertRaises(DiscoveryTrustDenied):
                self.verify(scope=replace(SCOPE, **{field: other}))

    def test_fresh_policy_cannot_refresh_stale_or_future_native_observation(self):
        for observed in (self.now - timedelta(minutes=5),
                         self.now - timedelta(minutes=5, microseconds=1),
                         self.now + timedelta(microseconds=1)):
            self.policy = replace(self.policy, revision=self.policy.revision + 1,
                issued_at=self.now - timedelta(seconds=1),
                expires_at=self.now + timedelta(minutes=4),
                witnesses=(replace(self.witness, observed_at=observed),))
            self.write_policy(self.policy)
            with self.subTest(observed=observed), self.assertRaises(DiscoveryTrustDenied):
                self.verify()

    def test_observation_just_inside_five_minute_window_is_usable(self):
        self.write_policy(replace(self.policy,
            witnesses=(replace(self.witness,
                observed_at=self.now - timedelta(minutes=5) + timedelta(microseconds=1)),)))
        self.verify()

    def test_credential_lease_expiry_is_exclusive(self):
        self.write_policy(replace(self.policy,
            witnesses=(replace(self.witness, credential_expires_at=self.now),)))
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify()

    def test_policy_future_issue_and_expiry_are_checked_on_every_use(self):
        self.verify()
        for checked in (self.policy.issued_at - timedelta(microseconds=1),
                        self.policy.expires_at,
                        self.policy.expires_at + timedelta(microseconds=1)):
            with self.subTest(checked=checked), self.assertRaises(DiscoveryTrustDenied):
                self.verify(checked_at=checked)
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify(checked_at=self.now.replace(tzinfo=None))

    def test_revision_floor_and_live_rollback_or_equivocation_are_rejected(self):
        below_floor = replace(self.policy, revision=2)
        self.write_policy(below_floor)
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify()
        advanced = replace(self.policy, revision=4)
        self.write_policy(advanced)
        self.verify()
        for changed in (self.policy, replace(advanced,
                witnesses=(replace(self.witness, observation_reference='other-observation'),))):
            self.write_policy(changed)
            with self.subTest(revision=changed.revision), self.assertRaises(DiscoveryTrustDenied):
                self.verify()
        self.write_policy(self.policy)
        restarted = SignedFileDiscoveryCredentialAuthority(self.path,
            authority_public_key=self.key.public_key(), minimum_revision=4)
        with self.assertRaises(DiscoveryTrustDenied):
            restarted.current_policy(self.now)

    def test_later_revision_retains_new_observation_custody_in_evidence(self):
        previous = self.verify()
        updated = replace(self.witness, observation_reference='native-rbac-observation-02',
                          policy_digest='b' * 64, observed_at=self.now)
        self.write_policy(replace(self.policy, revision=4, witnesses=(updated,)))
        current = self.verify()
        self.assertNotEqual(current.policy_digest, previous.policy_digest)
        self.assertEqual(current.scope, previous.scope)

    @unittest.skipUnless(os.name == 'posix', 'POSIX protected-file controls')
    def test_writable_witness_document_permissions_are_rejected(self):
        self.verify()
        for mode in (0o620, 0o602, 0o666):
            self.path.chmod(mode)
            with self.subTest(mode=oct(mode)), self.assertRaises(DiscoveryTrustDenied):
                self.verify()

    @unittest.skipUnless(os.name == 'posix', 'POSIX no-follow/nonblocking controls')
    def test_missing_symlink_directory_and_fifo_have_no_successful_cached_fallback(self):
        self.verify()
        self.path.unlink()
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify()
        target = self.path.with_name('target.json')
        target.write_text('{}')
        self.path.symlink_to(target)
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify()
        self.path.unlink()
        self.path.mkdir()
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify()
        self.path.rmdir()
        os.mkfifo(self.path)
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify()

    def test_oversized_duplicate_key_or_extra_field_document_is_rejected(self):
        self.path.write_bytes(b' ' * 1048577)
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify()
        self.write_policy(self.policy)
        raw = self.path.read_text().replace('"revision": 3',
            '"revision": 3, "revision": 3')
        self.path.write_text(raw)
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify()
        self.write_policy(self.policy)
        body = json.loads(self.path.read_text())
        body['nativeAuthorized'] = True
        self.path.write_text(json.dumps(body))
        with self.assertRaises(DiscoveryTrustDenied):
            self.verify()

    def test_unbounded_policy_and_ambiguous_witnesses_are_rejected(self):
        for changes in ({'revision': True}, {'revision': 0},
                        {'expires_at': START + timedelta(minutes=5, microseconds=1)},
                        {'witnesses': (self.witness, self.witness)}):
            with self.subTest(changes=changes), self.assertRaises(DiscoveryTrustDenied):
                replace(self.policy, **changes)
        for changes in ({'read_only': 1}, {'policy_digest': 'unknown'},
                        {'credential_expires_at': self.witness.observed_at}):
            with self.subTest(changes=changes), self.assertRaises(DiscoveryTrustDenied):
                replace(self.witness, **changes)


if __name__ == '__main__':
    unittest.main()
