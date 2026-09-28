from __future__ import annotations

import base64
import copy
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provisioner.controlplane.authority.model import PlanScope, RoleGrant, VerifiedPrincipal
from provisioner.controlplane.authority.service import AuthenticationFailed, AuthorityService
from provisioner.controlplane.discovery.assessment_inputs import (
    AssessmentInputDenied, AssessmentInputRepository, DurableAssessmentInputs,
    SignedFileAssessmentTrustStore, installation_document, parse_evidence, route_document)
from provisioner.controlplane.discovery.model import _json, _scope_json
from provisioner.controlplane.discovery.routes import InstalledTuple, RouteKey
from provisioner.controlplane.persistence.environments import (
    EnvironmentDeclaration, EnvironmentRepository, RegisteredEnvironment)
from provisioner.controlplane.persistence.store import TenantContext


NOW = datetime(2026, 9, 28, 15, tzinfo=timezone.utc)
CTX = TenantContext('org', 'tenant')
SOURCE = InstalledTuple(PlanScope('org', 'tenant', 'site-a', 'wsd', 'endpoint-a',
                                  'scope-a', 'vmware'), 'product-a', 'a' * 64)
DEST = InstalledTuple(PlanScope('org', 'tenant', 'site-b', 'wsd', 'endpoint-b',
                                'scope-b', 'nutanix'), 'product-b', 'b' * 64)
ROUTE = RouteKey(SOURCE, DEST, 'COLD_VM_CONVERSION', 'linux-uefi', 'routed', 'offline')


def encoded(value):
    return base64.b64encode(value).decode('ascii')


class SignedFixture:
    def __init__(self, path):
        self.path = Path(path)
        self.root = Ed25519PrivateKey.generate()
        self.keys = {role: Ed25519PrivateKey.generate() for role in (
            'INSTALLATION', 'SOURCE_EXIT', 'TARGET_OPERATE', 'POLICY_TRANSLATION',
            'SECURITY_EQUIVALENCE', 'RECOVERY_READINESS')}
        self.policy = {'format': 'hosting-assessment-trust-policy/1', 'revision': 1,
            'issuedAt': (NOW - timedelta(hours=1)).isoformat(),
            'expiresAt': (NOW + timedelta(hours=1)).isoformat(),
            'revokedEvidenceIds': [], 'enrollments': [
                {'keyId': role + '-key', 'subjectId': role + '-reviewer', 'role': role,
                 'publicKey': encoded(key.public_key().public_bytes_raw()),
                 'environments': [{'environmentId': name, 'scope': _scope_json(item.scope)}
                                  for name, item in (('source', SOURCE), ('target', DEST))],
                 'notBefore': (NOW - timedelta(days=1)).isoformat(),
                 'expiresAt': (NOW + timedelta(days=1)).isoformat(), 'revokedAt': None}
                for role, key in self.keys.items()]}
        self.write()
        self.trust = SignedFileAssessmentTrustStore(self.path,
            authority_public_key=self.root.public_key(), minimum_revision=1)

    def write(self, *, root=None):
        self.path.write_text(_json({'policy': self.policy,
            'signature': encoded((root or self.root).sign(_json(self.policy).encode('ascii')))}))
        self.path.chmod(0o600)

    def document(self, kind='INSTALLATION'):
        if kind == 'INSTALLATION':
            payload = {'environmentId': 'source', 'installation': installation_document(SOURCE),
                       'nativeEvidenceDigest': 'c' * 64}
        elif kind == 'ROUTE':
            payload = {'sourceEnvironmentId': 'source', 'destinationEnvironmentId': 'target',
                'route': route_document(ROUTE), 'maturity': 'NATIVE_QUALIFIED',
                'evidence': [{'side': side, 'evidenceId': side + '-campaign',
                              'evidenceDigest': digit * 64,
                              'observedAt': (NOW - timedelta(hours=2)).isoformat(),
                              'expiresAt': (NOW + timedelta(hours=2)).isoformat()}
                             for side, digit in (('SOURCE_EXIT', '1'), ('TARGET_OPERATE', '2'))]}
        else:
            payload = {'sourceEnvironmentId': 'source', 'destinationEnvironmentId': 'target',
                'route': route_document(ROUTE), 'control': 'SECURITY_EQUIVALENCE', 'outcome': 'PASS',
                'evidenceDigest': '3' * 64, 'observedAt': (NOW - timedelta(minutes=2)).isoformat(),
                'sourceRawSnapshotDigest': '4' * 64, 'destinationRawSnapshotDigest': '5' * 64,
                'sourceSnapshotDigest': '6' * 64, 'destinationSnapshotDigest': '7' * 64,
                'normalizerVersion': 'hosting-assessment-normalizer/1'}
        return {'format': 'hosting-assessment-evidence/1', 'evidenceId': kind + '-evidence',
                'kind': kind, 'revision': 1, 'issuedAt': (NOW - timedelta(minutes=1)).isoformat(),
                'expiresAt': (NOW + timedelta(minutes=30)).isoformat(), 'payload': payload}

    def sign(self, document):
        roles = ('INSTALLATION',) if document['kind'] == 'INSTALLATION' else (
            ('SOURCE_EXIT', 'TARGET_OPERATE') if document['kind'] == 'ROUTE' else
            (document['payload']['control'],))
        return tuple({'keyId': role + '-key', 'signature': encoded(
            self.keys[role].sign(_json(document).encode('ascii')))} for role in roles)


class AssessmentInputTrustTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fixture = SignedFixture(Path(self.temp.name) / 'policy.json')

    def verify(self, document=None, signatures=None):
        document = document or self.fixture.document()
        return self.fixture.trust.verify(parse_evidence(document),
                                         signatures or self.fixture.sign(document), NOW)

    def test_real_signatures_verify_all_three_evidence_kinds(self):
        for kind in ('INSTALLATION', 'ROUTE', 'CONTROL'):
            policy, subjects = self.verify(self.fixture.document(kind))
            self.assertEqual(policy.revision, 1)
            self.assertEqual(len(subjects), 2 if kind == 'ROUTE' else 1)

    def test_selector_or_payload_tampering_and_wrong_signature_denied(self):
        document = self.fixture.document()
        signatures = self.fixture.sign(document)
        for field, value in (('evidenceId', 'other'), ('revision', 2)):
            changed = dict(document, **{field: value})
            with self.assertRaises(AssessmentInputDenied):
                self.verify(changed, signatures)
        document['payload']['installation']['productTupleDigest'] = 'f' * 64
        with self.assertRaises(AssessmentInputDenied):
            self.verify(document, signatures)

    def test_even_resigned_foreign_scope_and_cross_tenant_routes_are_denied(self):
        for field in ('endpointId', 'nativeScopeId', 'locationId', 'securityDomainId'):
            document = self.fixture.document()
            document['payload']['installation']['scope'][field] = 'different'
            with self.subTest(field=field), self.assertRaises(AssessmentInputDenied):
                self.verify(document)
        document = self.fixture.document('ROUTE')
        document['payload']['route']['destination']['scope']['tenantId'] = 'other'
        with self.assertRaises(AssessmentInputDenied):
            self.verify(document)

    def test_dual_route_review_requires_independent_source_and_target_signatures(self):
        document = self.fixture.document('ROUTE')
        signatures = self.fixture.sign(document)
        for invalid in ((signatures[0],), (signatures[0], signatures[0]),
                        (dict(signatures[0], keyId='TARGET_OPERATE-key'), signatures[1])):
            with self.assertRaises(AssessmentInputDenied):
                self.verify(document, invalid)

    def test_live_key_and_artifact_revocation_and_expiry_fail_closed(self):
        document = self.fixture.document()
        self.verify(document)
        self.fixture.policy['revision'] += 1
        self.fixture.policy['revokedEvidenceIds'] = [document['evidenceId']]
        self.fixture.write()
        with self.assertRaises(AssessmentInputDenied):
            self.verify(document)
        self.fixture.policy['revision'] += 1
        self.fixture.policy['revokedEvidenceIds'] = []
        self.fixture.policy['enrollments'][0]['revokedAt'] = NOW.isoformat()
        self.fixture.write()
        with self.assertRaises(AssessmentInputDenied):
            self.verify(document)
        with self.assertRaises(AssessmentInputDenied):
            self.fixture.trust.current_policy(NOW + timedelta(hours=1))

    def test_policy_cannot_roll_back_equivocate_or_reuse_reviewers(self):
        self.fixture.policy['revision'] = 2
        self.fixture.write()
        self.verify()
        self.fixture.policy['revision'] = 1
        self.fixture.write()
        with self.assertRaises(AssessmentInputDenied):
            self.verify()
        self.fixture.policy['revision'] = 2
        self.fixture.policy['expiresAt'] = (NOW + timedelta(minutes=40)).isoformat()
        self.fixture.write()
        with self.assertRaises(AssessmentInputDenied):
            self.verify()
        self.fixture.policy['revision'] = 3
        self.fixture.policy['enrollments'][1]['subjectId'] = 'INSTALLATION-reviewer'
        self.fixture.write()
        with self.assertRaises(AssessmentInputDenied):
            self.verify()

    def test_untrusted_root_file_permissions_and_missing_policy_fail_closed(self):
        self.fixture.write(root=Ed25519PrivateKey.generate())
        with self.assertRaises(AssessmentInputDenied):
            self.verify()
        self.fixture.write()
        self.fixture.path.chmod(0o666)
        with self.assertRaises(AssessmentInputDenied):
            self.verify()
        self.fixture.path.unlink()
        with self.assertRaises(AssessmentInputDenied):
            self.verify()

    def test_control_binding_changes_for_raw_generation_and_normalized_inputs(self):
        original = self.fixture.document('CONTROL')
        parsed = parse_evidence(original)
        for field in ('sourceRawSnapshotDigest', 'destinationRawSnapshotDigest',
                      'sourceSnapshotDigest', 'destinationSnapshotDigest'):
            changed = copy.deepcopy(original)
            changed['payload'][field] = 'f' * 64
            self.assertNotEqual(parse_evidence(changed).binding_digest, parsed.binding_digest)
        original['payload']['normalizerVersion'] = 'unknown/2'
        with self.assertRaises(AssessmentInputDenied):
            parse_evidence(original)

    def test_constructed_metadata_cannot_differ_from_the_signed_artifact(self):
        document = self.fixture.document()
        evidence = parse_evidence(document)
        with self.assertRaises(AssessmentInputDenied):
            self.fixture.trust.verify(replace(evidence, environments=(('other', SOURCE.scope),)),
                                      self.fixture.sign(document), NOW)


class TestIdentityProvider:
    def __init__(self):
        self.revoked = False
        self.principal = VerifiedPrincipal('operator', 'org', 'tenant', 'HUMAN',
            NOW - timedelta(hours=1), NOW + timedelta(hours=1), None,
            tuple(RoleGrant('JOB_READER', item.scope, NOW + timedelta(hours=1))
                  for item in (SOURCE, DEST)))

    def authenticate(self, credential):
        if self.revoked or credential != 'private-test-credential':
            raise AuthenticationFailed('revoked session')
        return self.principal


class TestEnvironments(EnvironmentRepository):
    def __init__(self):
        pass

    def get(self, ctx, environment_id):
        installed = {'source': SOURCE, 'target': DEST}.get(environment_id)
        if not installed:
            return None
        declaration = EnvironmentDeclaration(environment_id, environment_id, installed.scope)
        return RegisteredEnvironment(declaration, 'registrar', declaration.digest(), NOW)


class TestInputs(AssessmentInputRepository):
    def __init__(self, fixture):
        self.fixture, self.reads = fixture, []

    def latest(self, ctx, kind, binding_digest, checked_at):
        self.reads.append((ctx, kind, binding_digest))
        if kind == 'INSTALLATION':
            evidence = parse_evidence(self.fixture.document())
            self.fixture.trust.verify(evidence, self.fixture.sign(self.fixture.document()), checked_at)
            return evidence if evidence.binding_digest == binding_digest else None
        return None


class BoundAssessmentProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fixture = SignedFixture(Path(self.temp.name) / 'policy.json')
        self.identities = TestIdentityProvider()
        authority = AuthorityService(self.identities, None, None, clock=lambda: NOW)
        self.repository = TestInputs(self.fixture)
        self.bound = DurableAssessmentInputs(self.repository, authority, TestEnvironments()).bind(
            'private-test-credential')

    def test_exact_scope_access_uses_live_session_and_signed_installation(self):
        verified = self.bound.resolve_environment(CTX, 'operator', 'source', 'SOURCE_READ', NOW)
        self.assertEqual(verified.installation, SOURCE)
        self.assertEqual(verified.access.actor_subject, 'operator')
        self.assertEqual(verified.access.scope, SOURCE.scope)
        self.assertNotIn('private-test-credential', repr(verified))

    def test_revoked_session_between_method_calls_and_actor_confusion_are_rejected(self):
        self.bound.resolve_environment(CTX, 'operator', 'source', 'SOURCE_READ', NOW)
        prior_reads = len(self.repository.reads)
        self.identities.revoked = True
        with self.assertRaises(AuthenticationFailed):
            self.bound.route_claims(CTX, 'operator', (ROUTE,), NOW)
        self.assertEqual(len(self.repository.reads), prior_reads)
        self.identities.revoked = False
        with self.assertRaises(AssessmentInputDenied):
            self.bound.route_claims(CTX, 'someone-else', (ROUTE,), NOW)

    def test_removed_exact_scope_grant_blocks_before_evidence_lookup(self):
        self.identities.principal = replace(self.identities.principal, grants=())
        with self.assertRaises(AssessmentInputDenied):
            self.bound.resolve_environment(CTX, 'operator', 'source', 'SOURCE_READ', NOW)
        self.assertEqual(self.repository.reads, [])


if __name__ == '__main__':
    unittest.main()
