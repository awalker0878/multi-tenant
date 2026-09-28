"""Loopback mTLS admission verifies signatures and retains evidence before writes.

The repository recorder stands in for PostgreSQL only. TLS, independent authority
keys, policy/witness files, signature checks and durable evidence are real here.
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import json
import ssl
import tempfile
import threading
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provisioner.controlplane.discovery.ingest import (
    MAX_BODY, DiscoveryIngestServer, DiscoveryIngestService,
    PrivateDiscoveryEvidenceSink, campaign_document, result_document,
)
from provisioner.controlplane.discovery.model import (
    DiscoveryCampaignAuthorization, DiscoveryFact, DiscoveryObject,
    DiscoveryResult, NativeIdentity,
)
from provisioner.controlplane.discovery.persistence import DiscoveryConflict
from provisioner.controlplane.discovery.trust import (
    DiscoveryKeyEnrollment, DiscoveryTrustPolicy, SignedDiscoveryIngestVerifier,
    SignedFileDiscoveryTrustStore, campaign_signing_bytes, result_signing_bytes,
    trust_policy_signing_bytes,
)
from provisioner.controlplane.discovery.witness import (
    NativeCredentialWitnessPolicy, NativeReadCredentialWitness,
    SignedFileDiscoveryCredentialAuthority, credential_witness_signing_bytes,
)
from provisioner.controlplane.worker.pki import MutualTlsWorkerVerifier
from tests.provisioning.controlplane.test_discovery_model import SCOPE
from tests.provisioning.worker.tls_fixtures import TestPki


def encoded(value):
    return base64.b64encode(value).decode('ascii')


class RecordingRepository:
    """Invoke the real verifier before simulating a committed repository write."""

    def __init__(self, test, verifier):
        self.test, self.verifier = test, verifier

    def register_verified_campaign(self, context, environment, campaign):
        proof = self.verifier.verify_campaign(campaign, environment,
                                             datetime.now(timezone.utc))
        self.test.assert_retained(proof, context, campaign, None)
        key = (context.organization_id, context.tenant_id, environment, campaign.campaign_id)
        current = self.test.campaigns.get(key)
        if current is not None and current.digest() != campaign.digest():
            raise DiscoveryConflict('Campaign ID already has another digest')
        self.test.campaigns[key] = campaign
        self.test.events.append(('campaign-commit', proof))

    def publish_verified_result(self, context, environment, result):
        key = (context.organization_id, context.tenant_id, environment, result.campaign_id)
        campaign = self.test.campaigns.get(key)
        if campaign is None:
            raise DiscoveryConflict('Campaign is not registered')
        proof = self.verifier.verify_result(campaign, result, environment,
                                           datetime.now(timezone.utc))
        self.test.assert_retained(proof, context, campaign, result)
        self.test.events.append(('result-commit', proof))
        return SimpleNamespace(environment_id=environment, generation=1,
                               result_digest=result.digest, completeness=result.completeness)


class DiscoveryIngestTlsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.evidence = self.root / 'evidence'
        self.evidence.mkdir(mode=0o700)
        self.pki = TestPki()
        self.addCleanup(self.pki.close)
        self.pki.issue('server')
        uri = 'spiffe://workers.example/org/org-01/tenant/tenant-01/site/site-01/worker/collector-01'
        self.pki.issue('collector', client=True, uri=uri)
        for name, old, new in (('other-worker', 'collector-01', 'other-collector'),
                               ('other-site', 'site-01', 'site-02'),
                               ('other-tenant', 'tenant-01', 'tenant-02'),
                               ('other-org', 'org-01', 'org-02')):
            self.pki.issue(name, client=True, uri=uri.replace(old, new))
        self.tls = MutualTlsWorkerVerifier(
            server_certificate=self.pki.root / 'server.pem',
            server_key=self.pki.root / 'server.key',
            trust_bundle=self.pki.root / 'ca.pem', crl_bundle=self.pki.root / 'crl.pem',
            trust_domain='workers.example')
        self.root_key = Ed25519PrivateKey.generate()
        self.witness_key = Ed25519PrivateKey.generate()
        self.issuer_key = Ed25519PrivateKey.generate()
        self.collector_key = Ed25519PrivateKey.generate()
        self.now = datetime.now(timezone.utc)
        before = self.now - timedelta(seconds=10)
        after = self.now + timedelta(hours=1)
        self.campaign = DiscoveryCampaignAuthorization('campaign-01', SCOPE,
            'read-approval-01', 'collector-01', ('vm',), before,
            self.now + timedelta(minutes=10), 2, 5, 5)
        self.result = DiscoveryResult(self.campaign.campaign_id, self.campaign.digest(),
            SCOPE, self.now - timedelta(seconds=1), 'COMPLETE',
            (DiscoveryObject(NativeIdentity('endpoint-01', 'project-01', 'openstack',
                'vm', 'vm-01'), (DiscoveryFact.known('name', 'workload-one'),)),), (), ())
        enrollments = (
            DiscoveryKeyEnrollment('issuer-key', 'campaign-issuer', 'issuer',
                encoded(self.issuer_key.public_key().public_bytes_raw()),
                'environment-01', SCOPE, before, after),
            DiscoveryKeyEnrollment('collector-key', 'collector-01', 'collector',
                encoded(self.collector_key.public_key().public_bytes_raw()),
                'environment-01', SCOPE, before, after, 'vault:read-only'),
        )
        self.trust = DiscoveryTrustPolicy(1, before, after, enrollments)
        trust_path = self.root / 'trust.json'
        self.write_signed(trust_path, self.trust, self.root_key, trust_policy_signing_bytes)
        self.witness = NativeReadCredentialWitness('vault:read-only', 'collector-01',
            'environment-01', SCOPE, 'native-rbac-01', 'a' * 64, before, after, True)
        self.witness_policy = NativeCredentialWitnessPolicy(1, before,
            self.now + timedelta(minutes=4), (self.witness,))
        self.witness_path = self.root / 'witness.json'
        self.write_signed(self.witness_path, self.witness_policy,
                          self.witness_key, credential_witness_signing_bytes)
        verifier = SignedDiscoveryIngestVerifier(
            SignedFileDiscoveryTrustStore(trust_path,
                authority_public_key=self.root_key.public_key(), minimum_revision=1),
            SignedFileDiscoveryCredentialAuthority(self.witness_path,
                authority_public_key=self.witness_key.public_key(), minimum_revision=1))
        self.events, self.campaigns, self.retained_requests = [], {}, []
        self.repository_calls = []
        self.repository_patch = patch(
            'provisioner.controlplane.discovery.ingest.DiscoveryRepository',
            side_effect=self.repository)
        self.repository_patch.start()
        self.addCleanup(self.repository_patch.stop)
        self.sink = PrivateDiscoveryEvidenceSink(self.evidence)
        self.service = DiscoveryIngestService(connect=lambda: None,
            ingest_role='discovery_ingest', tls_verifier=self.tls,
            signature_verifier=verifier, evidence_sink=self.sink)
        self.repository_calls.clear()  # Constructor validation is not a write.
        self.server = DiscoveryIngestServer(('127.0.0.1', 0), self.service)
        self.thread = threading.Thread(target=self.server.serve_forever,
            kwargs={'poll_interval': 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    @staticmethod
    def write_signed(path, policy, key, signing_bytes):
        path.write_text(json.dumps({'policy': policy.as_dict(),
            'signature': encoded(key.sign(signing_bytes(policy)))}))
        path.chmod(0o600)

    def repository(self, connect, *, ingest_role=None, ingest_verifier=None):
        self.assertEqual(ingest_role, 'discovery_ingest')
        self.repository_calls.append(ingest_verifier)
        return RecordingRepository(self, ingest_verifier)

    def assert_retained(self, proof, context, campaign, result):
        prefix, digest = proof.verification_reference.split(':', 1)
        self.assertEqual(prefix, 'discovery-admission-v1')
        matches = list(self.evidence.rglob(digest))
        self.assertEqual(len(matches), 1, 'SQL write preceded durable proof')
        content = matches[0].read_bytes()
        self.assertEqual(hashlib.sha256(content).hexdigest(), digest)
        record = json.loads(content)
        self.assertEqual(record['authorizationDigest'], campaign.digest())
        self.assertEqual(record['resultDigest'], result.digest if result else None)
        self.assertEqual(record['organizationId'], context.organization_id)
        self.assertEqual(record['tenantId'], context.tenant_id)
        self.assertEqual(record['peerSubject'], 'collector-01')
        self.assertRegex(record['peerCertificateSha256'], r'^[0-9a-f]{64}$')
        request_files = list(self.evidence.rglob(record['requestDigest']))
        self.assertEqual(len(request_files), 1, 'SQL write preceded original signed request')
        raw = request_files[0].read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), record['requestDigest'])
        document = json.loads(raw)
        self.assertIn('campaignSignature', document)
        if result is not None:
            self.assertIn('resultSignature', document)
        self.retained_requests.append(raw)
        self.events.append(('retained', proof))

    def document(self, *, result=False, campaign=None, value=None, result_key=None):
        campaign = campaign or self.campaign
        body = {'environmentId': 'environment-01', 'campaign': campaign_document(campaign),
            'campaignSignature': {'keyId': 'issuer-key', 'signature': encoded(
                self.issuer_key.sign(campaign_signing_bytes(campaign, 'environment-01')))}}
        if result:
            value = value or self.result
            body.update(result=result_document(value), resultSignature={
                'keyId': 'collector-key', 'signature': encoded((result_key or self.collector_key).sign(
                    result_signing_bytes(campaign, value, 'environment-01')))})
        return body

    def request(self, body=None, *, result=False, worker='collector', client_pki=None,
                headers=None, raw=None, path=None):
        tls = ssl.create_default_context(cafile=str(self.pki.root / 'ca.pem'))
        if worker is not None:
            root = (client_pki or self.pki).root
            tls.load_cert_chain(str(root / (worker + '.pem')), str(root / (worker + '.key')))
        connection = http.client.HTTPSConnection('localhost', self.server.server_port,
                                                 context=tls, timeout=3)
        if raw is None:
            raw = json.dumps(body if body is not None else self.document(result=result)).encode('utf-8')
        try:
            connection.request('POST', path or ('/v1/discovery/results' if result else
                '/v1/discovery/campaigns'), body=raw,
                headers={'Content-Type': 'application/json', **(headers or {})})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), json.loads(response.read())
        finally:
            connection.close()

    def test_signed_campaign_and_result_are_retained_before_repository_commit(self):
        status, headers, campaign = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(campaign['status'], 'CAMPAIGN_REGISTERED')
        self.assertFalse(campaign['executionAuthorized'])
        self.assertEqual(campaign['authorizationDigest'], self.campaign.digest())
        status, _, result = self.request(result=True)
        self.assertEqual(status, 200)
        self.assertEqual(result['status'], 'RESULT_PUBLISHED')
        self.assertEqual(result['resultDigest'], self.result.digest)
        self.assertEqual(result['generation'], 1)
        self.assertFalse(result['executionAuthorized'])
        self.assertEqual([event for event, _ in self.events],
            ['retained', 'campaign-commit', 'retained', 'result-commit'])
        self.assertEqual(len(self.retained_requests), 2)

    def test_tls_trust_rotation_during_admission_rejects_old_socket_before_custody(self):
        original = RecordingRepository.register_verified_campaign
        def rotate_then_verify(repository, context, environment, campaign):
            self.tls.reload_trust()
            return original(repository, context, environment, campaign)
        with patch.object(RecordingRepository, 'register_verified_campaign', rotate_then_verify):
            status, _headers, body = self.request()
        self.assertEqual(status, 403)
        self.assertEqual(body['error'], 'DISCOVERY_AUTHORITY_DENIED')
        self.assertEqual(self.events, [])
        self.assertEqual(list(self.evidence.iterdir()), [])

    def test_missing_or_untrusted_client_certificate_fails_tls_before_repository(self):
        with self.assertRaises((ssl.SSLError, OSError, http.client.HTTPException)):
            self.request(worker=None)
        outsider = TestPki()
        self.addCleanup(outsider.close)
        outsider.issue('collector', client=True, uri=(
            'spiffe://workers.example/org/org-01/tenant/tenant-01/site/site-01/worker/collector-01'))
        with self.assertRaises((ssl.SSLError, OSError, http.client.HTTPException)):
            self.request(client_pki=outsider)
        self.assertFalse(self.repository_calls)
        self.assertFalse(self.events)

    def test_wrong_cert_subject_or_tenant_site_cannot_submit_even_valid_signatures(self):
        for worker in ('other-worker', 'other-site', 'other-tenant', 'other-org'):
            with self.subTest(worker=worker):
                self.assertEqual(self.request(worker=worker)[0], 403)
        self.assertFalse(self.repository_calls)
        self.assertFalse(self.events)

    def test_independently_signed_foreign_scope_is_not_enrolled(self):
        for field in ('security_domain_id', 'endpoint_id', 'native_scope_id'):
            campaign = replace(self.campaign, scope=replace(SCOPE, **{field: 'foreign'}))
            with self.subTest(field=field):
                self.assertEqual(self.request(self.document(campaign=campaign))[0], 403)
        self.assertFalse(self.events)

    def test_campaign_tamper_and_forged_result_signature_never_persist(self):
        body = self.document()
        body['campaign']['maxObjects'] = 4
        self.assertEqual(self.request(body)[0], 403)
        self.assertFalse(self.events)
        self.assertEqual(self.request()[0], 200)
        self.events.clear()
        body = self.document(result=True, result_key=Ed25519PrivateKey.generate())
        self.assertEqual(self.request(body, result=True)[0], 403)
        body = self.document(result=True)
        body['result']['objects'][0]['facts'][0]['value'] = 'tampered-name'
        self.assertEqual(self.request(body, result=True)[0], 403)
        self.assertFalse(self.events)

    def test_wrong_result_campaign_digest_and_scope_are_rejected(self):
        self.assertEqual(self.request()[0], 200)
        self.events.clear()
        for field, value in (('campaignId', 'other-campaign'),
                             ('authorizationDigest', '0' * 64)):
            body = self.document(result=True)
            body['result'][field] = value
            with self.subTest(field=field):
                self.assertEqual(self.request(body, result=True)[0], 403)
        body = self.document(result=True)
        body['result']['scope']['securityDomainId'] = 'another-domain'
        self.assertEqual(self.request(body, result=True)[0], 403)
        self.assertFalse(self.events)

    def test_duplicate_nested_fields_unknown_fields_and_nonfinite_values_reject(self):
        raw = json.dumps(self.document()).replace('"campaignId": "campaign-01"',
            '"campaignId": "campaign-01", "campaignId": "campaign-01"').encode()
        self.assertEqual(self.request(raw=raw)[0], 400)
        body = self.document()
        body['campaign']['nativeContactAuthorized'] = True
        self.assertEqual(self.request(body)[0], 403)
        raw = json.dumps(self.document()).replace('"maxObjects": 5',
            '"maxObjects": NaN').encode()
        self.assertEqual(self.request(raw=raw)[0], 400)
        self.assertFalse(self.events)

    def test_forwarded_identity_and_alternate_authorization_are_rejected(self):
        for name in ('Forwarded', 'X-Forwarded-For', 'X-Forwarded-Client-Cert',
                     'Authorization', 'X-Client-Cert', 'X-SSL-Client-Cert'):
            with self.subTest(header=name):
                self.assertEqual(self.request(headers={name: 'forged-identity'})[0], 400)
        self.assertFalse(self.repository_calls)
        self.assertFalse(self.events)

    def test_body_at_one_mib_retains_original_bytes_and_larger_length_is_rejected(self):
        raw = json.dumps(self.document()).encode()
        padded = raw + b' ' * (MAX_BODY - len(raw))
        self.assertEqual(self.request(raw=padded)[0], 200)
        self.assertEqual(self.retained_requests[-1], padded)
        prior = len(self.events)
        self.assertEqual(self.request(raw=b'{}', headers={
            'Content-Length': str(MAX_BODY + 1)})[0], 400)
        self.assertEqual(len(self.events), prior)

    def test_content_encoding_chunking_and_non_json_media_type_are_rejected(self):
        for headers in ({'Content-Encoding': 'gzip'}, {'Transfer-Encoding': 'chunked'},
                        {'Content-Type': 'text/plain'}, {'Content-Length': '0'},
                        {'Content-Length': '-1'}):
            with self.subTest(headers=headers):
                self.assertEqual(self.request(raw=b'{}', headers=headers)[0], 400)
        self.assertFalse(self.repository_calls)

    def test_evidence_write_failure_does_not_register_campaign_or_publish_result(self):
        with patch.object(self.sink, 'retain', side_effect=OSError('private disk unavailable')):
            self.assertEqual(self.request()[0], 503)
        self.assertFalse(self.campaigns)
        self.assertFalse(self.events)
        self.assertEqual(self.request()[0], 200)
        self.events.clear()
        with patch.object(self.sink, 'retain', side_effect=OSError('private disk unavailable')):
            self.assertEqual(self.request(result=True)[0], 503)
        self.assertFalse(self.events)

    def test_credential_revocation_between_admission_and_publication_denies_result(self):
        self.assertEqual(self.request()[0], 200)
        self.events.clear()
        revised = replace(self.witness_policy, revision=2, witnesses=(
            replace(self.witness, revoked_at=datetime.now(timezone.utc)),))
        self.write_signed(self.witness_path, revised,
                          self.witness_key, credential_witness_signing_bytes)
        self.assertEqual(self.request(result=True)[0], 403)
        self.assertFalse(self.events)

    def test_unregistered_campaign_result_and_unknown_route_cannot_write(self):
        self.assertEqual(self.request(result=True)[0], 409)
        self.assertEqual(self.request(path='/v1/discovery/campaigns?token=untrusted')[0], 404)
        self.assertFalse(self.events)


if __name__ == '__main__':
    unittest.main()
