"""Signed loopback mTLS ingress through real PostgreSQL, without verifier doubles.

These tests exercise the deployed components together. The native IAM witness
is signed test evidence; no native platform or site qualification is implied.
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import ssl
import tempfile
import threading
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.ingest import (
    DiscoveryIngestServer, DiscoveryIngestService, PrivateDiscoveryEvidenceSink,
    campaign_document, result_document,
)
from provisioner.controlplane.discovery.model import (
    DiscoveryCampaignAuthorization, DiscoveryFact, DiscoveryObject,
    DiscoveryResult, NativeIdentity,
)
from provisioner.controlplane.discovery.persistence import DiscoveryRepository
from provisioner.controlplane.discovery.trust import (
    DiscoveryKeyEnrollment, DiscoveryTrustPolicy, SignedDiscoveryIngestVerifier,
    SignedFileDiscoveryTrustStore, campaign_signing_bytes, result_signing_bytes,
    trust_policy_signing_bytes,
)
from provisioner.controlplane.discovery.witness import (
    NativeCredentialWitnessPolicy, NativeReadCredentialWitness,
    SignedFileDiscoveryCredentialAuthority, credential_witness_signing_bytes,
)
from provisioner.controlplane.persistence.environments import (
    EnvironmentDeclaration, EnvironmentRepository,
)
from provisioner.controlplane.persistence.store import AuditContext, TenantContext
from provisioner.controlplane.worker.pki import MutualTlsWorkerVerifier
from tests.provisioning.worker.tls_fixtures import TestPki


def _encoded(value):
    return base64.b64encode(value).decode('ascii')


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_DISCOVERY_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN'),
                     'Requires dedicated disposable PostgreSQL discovery roles')
class DiscoveryIngestPostgresTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        self.connect = lambda: psycopg.connect(os.environ['HOSTING_TEST_POSTGRES_RUNTIME_DSN'])
        self.ingest_connect = lambda: psycopg.connect(os.environ['HOSTING_TEST_POSTGRES_DISCOVERY_DSN'])
        self.context = TenantContext('org-' + uuid4().hex[:12], 'tenant-01')
        self.scope = PlanScope(self.context.organization_id, self.context.tenant_id,
                               'site-01', 'wsd-01', 'endpoint-01', 'project-01', 'openstack')
        self.environment = 'environment-01'
        EnvironmentRepository(self.connect).create(self.context,
            EnvironmentDeclaration(self.environment, 'Loopback ingress test', self.scope),
            AuditContext('test-registrar', uuid4().hex))
        self.reader = DiscoveryRepository(self.connect)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.evidence = self.root / 'evidence'
        self.evidence.mkdir(mode=0o700)
        self.pki = TestPki()
        self.addCleanup(self.pki.close)
        self.pki.issue('server')
        uri = (f'spiffe://workers.example/org/{self.context.organization_id}'
               '/tenant/tenant-01/site/site-01/worker/collector-01')
        self.pki.issue('collector', client=True, uri=uri)
        self.pki.issue('foreign', client=True, uri=uri.replace('/tenant-01/', '/foreign/'))
        self.tls = MutualTlsWorkerVerifier(
            server_certificate=self.pki.root / 'server.pem',
            server_key=self.pki.root / 'server.key',
            trust_bundle=self.pki.root / 'ca.pem', crl_bundle=self.pki.root / 'crl.pem',
            trust_domain='workers.example')
        self.root_key, self.witness_key, self.issuer_key, self.collector_key = (
            Ed25519PrivateKey.generate() for _ in range(4))
        now = datetime.now(timezone.utc)
        before, after = now - timedelta(seconds=10), now + timedelta(hours=1)
        self.campaign = DiscoveryCampaignAuthorization('campaign-01', self.scope,
            'read-approval-01', 'collector-01', ('vm',), before,
            now + timedelta(minutes=10), 2, 5, 5)
        self.result = DiscoveryResult(self.campaign.campaign_id, self.campaign.digest(),
            self.scope, now - timedelta(seconds=1), 'COMPLETE',
            (DiscoveryObject(NativeIdentity('endpoint-01', 'project-01', 'openstack',
                'vm', 'vm-01'), (DiscoveryFact.known('name', 'Observed VM'),)),), (), ())
        self.policy = DiscoveryTrustPolicy(1, before, after, (
            DiscoveryKeyEnrollment('issuer-key', 'campaign-issuer', 'issuer',
                _encoded(self.issuer_key.public_key().public_bytes_raw()),
                self.environment, self.scope, before, after),
            DiscoveryKeyEnrollment('collector-key', 'collector-01', 'collector',
                _encoded(self.collector_key.public_key().public_bytes_raw()),
                self.environment, self.scope, before, after, 'vault:read-only'),
        ))
        self.trust_path = self.root / 'trust.json'
        self.write_policy(self.trust_path, self.policy, self.root_key, trust_policy_signing_bytes)
        witness = NativeReadCredentialWitness('vault:read-only', 'collector-01',
            self.environment, self.scope, 'native-rbac-test', 'a' * 64, before, after, True)
        witness_policy = NativeCredentialWitnessPolicy(1, before,
            now + timedelta(minutes=4), (witness,))
        witness_path = self.root / 'witness.json'
        self.write_policy(witness_path, witness_policy, self.witness_key,
                          credential_witness_signing_bytes)
        verifier = SignedDiscoveryIngestVerifier(
            SignedFileDiscoveryTrustStore(self.trust_path,
                authority_public_key=self.root_key.public_key(), minimum_revision=1),
            SignedFileDiscoveryCredentialAuthority(witness_path,
                authority_public_key=self.witness_key.public_key(), minimum_revision=1))
        service = DiscoveryIngestService(connect=self.ingest_connect,
            ingest_role='hosting_discovery_ingest', tls_verifier=self.tls,
            signature_verifier=verifier, evidence_sink=PrivateDiscoveryEvidenceSink(self.evidence))
        self.server = DiscoveryIngestServer(('127.0.0.1', 0), service)
        self.thread = threading.Thread(target=self.server.serve_forever,
            kwargs={'poll_interval': 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    @staticmethod
    def write_policy(path, policy, key, signing_bytes):
        path.write_text(json.dumps({'policy': policy.as_dict(),
            'signature': _encoded(key.sign(signing_bytes(policy)))}))
        path.chmod(0o600)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def document(self, result=False, *, campaign=None, value=None):
        campaign = campaign or self.campaign
        body = {'environmentId': self.environment, 'campaign': campaign_document(campaign),
            'campaignSignature': {'keyId': 'issuer-key', 'signature': _encoded(
                self.issuer_key.sign(campaign_signing_bytes(campaign, self.environment)))}}
        if result:
            value = value or self.result
            body.update(result=result_document(value), resultSignature={
                'keyId': 'collector-key', 'signature': _encoded(self.collector_key.sign(
                    result_signing_bytes(campaign, value, self.environment)))})
        return body

    def request(self, result=False, *, document=None, worker='collector'):
        context = ssl.create_default_context(cafile=str(self.pki.root / 'ca.pem'))
        context.load_cert_chain(str(self.pki.root / (worker + '.pem')),
                                str(self.pki.root / (worker + '.key')))
        connection = http.client.HTTPSConnection('localhost', self.server.server_port,
                                                  context=context, timeout=10)
        try:
            connection.request('POST', '/v1/discovery/' + ('results' if result else 'campaigns'),
                body=json.dumps(document or self.document(result)).encode(),
                headers={'Content-Type': 'application/json'})
            response = connection.getresponse()
            self.assertEqual(response.getheader('Cache-Control'), 'no-store')
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def query(self, statement):
        with self.connect() as connection:
            connection.execute("SELECT set_config('app.organization_id', %s, true), "
                "set_config('app.tenant_id', %s, true)",
                (self.context.organization_id, self.context.tenant_id))
            return connection.execute(statement).fetchall()

    def test_signed_tls_roundtrip_has_one_generation_and_retained_original_evidence(self):
        self.assertEqual(self.request()[0], 200)
        self.assertEqual(self.request()[0], 200)
        status, published = self.request(True)
        self.assertEqual(status, 200)
        self.assertFalse(published['executionAuthorized'])
        self.assertEqual(self.request(True), (status, published))
        generations = self.reader.list_generations(self.context, self.scope, self.environment)
        self.assertEqual(len(generations), 1)
        self.assertEqual(generations[0].result_digest, self.result.digest)
        observed = self.reader.list_observations(self.context, self.scope, self.environment, 1)
        self.assertEqual(observed[0].identity.native_id, 'vm-01')
        self.assertEqual(observed[0].facts[0]['value'], 'Observed VM')
        self.assertEqual(self.reader.list_generations(self.context,
            replace(self.scope, security_domain_id='foreign'), self.environment), [])
        rows = self.query('SELECT verification_reference FROM hosting_controlplane.discovery_campaigns '
                          'UNION ALL SELECT verification_reference FROM hosting_controlplane.discovery_generations')
        self.assertEqual(len(rows), 2)
        for reference, in rows:
            prefix, digest = reference.split(':', 1)
            self.assertEqual(prefix, 'discovery-admission-v1')
            paths = list(self.evidence.rglob(digest))
            self.assertEqual(len(paths), 1)
            raw = paths[0].read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
            receipt = json.loads(raw)
            request = list(self.evidence.rglob(receipt['requestDigest']))
            self.assertEqual(len(request), 1)
            self.assertEqual(hashlib.sha256(request[0].read_bytes()).hexdigest(), receipt['requestDigest'])
            self.assertIn('campaignSignature', json.loads(request[0].read_bytes()))
        actions = self.query('SELECT record_kind FROM hosting_controlplane.audit_events ORDER BY audit_sequence')
        self.assertEqual(actions, [('EnvironmentRegistration',), ('DiscoveryCampaign',), ('DiscoveryGeneration',)])

    def test_signed_conflicts_and_live_revocation_cannot_publish_or_repeat(self):
        self.assertEqual(self.request()[0], 200)
        changed = replace(self.campaign, max_objects=4)
        self.assertEqual(self.request(document=self.document(campaign=changed))[0], 409)
        self.assertEqual(self.request(True)[0], 200)
        enrollments = tuple(replace(entry, revoked_at=datetime.now(timezone.utc))
                            if entry.role == 'collector' else entry for entry in self.policy.enrollments)
        self.write_policy(self.trust_path, replace(self.policy, revision=2, enrollments=enrollments),
                          self.root_key, trust_policy_signing_bytes)
        self.assertEqual(self.request(True)[0], 403)
        self.assertEqual(len(self.reader.list_generations(self.context, self.scope, self.environment)), 1)

    def test_foreign_transport_and_forged_signature_leave_no_campaign_or_generation(self):
        self.assertEqual(self.request(worker='foreign')[0], 403)
        document = self.document()
        document['campaignSignature']['signature'] = _encoded(b'\x00' * 64)
        self.assertEqual(self.request(document=document)[0], 403)
        self.assertEqual(self.query('SELECT campaign_id FROM hosting_controlplane.discovery_campaigns'), [])
        self.assertEqual(self.reader.list_generations(self.context, self.scope, self.environment), [])
        self.assertEqual(list(self.evidence.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
