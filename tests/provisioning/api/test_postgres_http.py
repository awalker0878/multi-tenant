"""HTTP contract through real PostgreSQL records, authority, jobs and IAM.

CI supplies disposable, separate runtime/authority/directory roles. The only
local substitution is a pinned JWKS response for self-signed test JWTs and a
test-only exemption from the production PostgreSQL TLS DSN requirement: the
GitHub Actions service is isolated plaintext localhost. No repository, role
probe, identity decision or database write is mocked.
"""
from __future__ import annotations

import json
import os
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from provisioner.controlplane.api.server import ServiceSettings, create_postgres_app
from provisioner.controlplane.authority.directory import SignedDirectorySync
from provisioner.controlplane.persistence import AuditContext, EnterpriseRecordStore, TenantContext
from provisioner.controlplane.persistence.migrate import apply_migrations
from provisioner.domain.enterprise_records import plan_digest
from tests.provisioning.schema.test_enterprise_records import plan, workload

_REQUIRED = (
    'HOSTING_TEST_POSTGRES_MIGRATION_DSN',
    'HOSTING_TEST_POSTGRES_RUNTIME_DSN',
    'HOSTING_TEST_POSTGRES_AUTHORITY_DSN',
    'HOSTING_TEST_POSTGRES_DIRECTORY_RESOLVER_DSN',
    'HOSTING_TEST_POSTGRES_DIRECTORY_WRITER_DSN',
)
_ISSUER = 'https://local-identity.example.test/realm'
_JWKS_URI = _ISSUER + '/keys'
_API_AUDIENCE = 'urn:hosting:controlplane'
_SYNC_AUDIENCE = 'urn:hosting:directory-sync'
_STEP_UP_ACR = 'urn:hosting:step-up'


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED') == '1'
                     and all(os.environ.get(name) for name in _REQUIRED),
                     'Requires disposable PostgreSQL runtime, authority and directory roles')
class PostgresHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        cls.psycopg = psycopg
        apply_migrations(lambda: psycopg.connect(
            os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']))

    def setUp(self):
        suffix = uuid4().hex[:12]
        self.ctx = TenantContext('org-' + suffix, 'tenant-' + suffix)
        self.foreign_tenant = 'other-' + suffix
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.rsa_key.public_key()))
        jwk.update(kid='local-key', alg='RS256', use='sig', key_ops=['verify'])
        self.jwk = jwk
        self.iam_key = Ed25519PrivateKey.generate()
        self.sessions = {}
        self.snapshots = {}
        self.store = EnterpriseRecordStore(lambda: self.psycopg.connect(
            os.environ['HOSTING_TEST_POSTGRES_RUNTIME_DSN']))
        self.sync = SignedDirectorySync(
            lambda: self.psycopg.connect(os.environ['HOSTING_TEST_POSTGRES_DIRECTORY_WRITER_DSN']),
            issuer=_ISSUER, audience=_SYNC_AUDIENCE,
            public_key=self.iam_key.public_key())

        observed = deepcopy(workload())
        observed['metadata'].update(
            organizationId=self.ctx.organization_id,
            tenantId=self.ctx.tenant_id,
            workloadId='workload-' + suffix)
        selected = deepcopy(plan())
        selected['metadata'].update(
            organizationId=self.ctx.organization_id,
            tenantId=self.ctx.tenant_id,
            planId='plan-' + suffix)
        selected['spec']['workloadId'] = observed['metadata']['workloadId']
        for scope in (selected['spec']['source'], selected['spec']['destination']):
            scope.update(organizationId=self.ctx.organization_id,
                         tenantId=self.ctx.tenant_id)
        selected['metadata']['planDigest'] = plan_digest(selected)
        self.observed, self.selected = observed, selected
        self.author_subject = 'plan-author-' + suffix
        self.store.create(self.ctx, observed, AuditContext(
            self.author_subject, 'http-workload-' + suffix))
        self.store.create(self.ctx, selected, AuditContext(
            self.author_subject, 'http-plan-' + suffix))

        source, destination = selected['spec']['source'], selected['spec']['destination']
        portfolio = {'organizationId': self.ctx.organization_id,
                     'tenantId': self.ctx.tenant_id, 'securityDomainId': 'wsd-01'}
        self._enroll('reader', [('WORKLOAD_READER', portfolio)])
        self._enroll('editor', [('WORKLOAD_EDITOR', portfolio)])
        self._enroll('author', [('SOURCE_OWNER', source)], subject=self.author_subject)
        foreign_portfolio = dict(portfolio, tenantId=self.foreign_tenant)
        self._enroll('foreign', [('WORKLOAD_READER', foreign_portfolio)],
                     tenant=self.foreign_tenant)
        for name, role, scope in (
                ('source-owner', 'SOURCE_OWNER', source),
                ('destination-owner', 'DESTINATION_OWNER', destination),
                ('source-security', 'SOURCE_SECURITY', source),
                ('destination-security', 'DESTINATION_SECURITY', destination)):
            self._enroll(name, [(role, scope)])
        self._enroll('operator', [('EXECUTION_OPERATOR', source),
                                  ('EXECUTION_OPERATOR', destination)])
        self._enroll('one-sided', [('JOB_READER', source)])

        # Production requires verify-full TLS. The disposable CI PostgreSQL
        # service listens only on localhost and has no server certificate.
        # test_server.py separately proves that its DSN is refused normally.
        with patch('provisioner.controlplane.api.server._secure_dsn',
                   side_effect=lambda value, _name: value):
            settings = ServiceSettings(
                runtime_dsn=os.environ['HOSTING_TEST_POSTGRES_RUNTIME_DSN'],
                authority_dsn=os.environ['HOSTING_TEST_POSTGRES_AUTHORITY_DSN'],
                directory_dsn=os.environ['HOSTING_TEST_POSTGRES_DIRECTORY_RESOLVER_DSN'],
                oidc_issuer=_ISSUER, oidc_audience=_API_AUDIENCE,
                oidc_jwks_uri=_JWKS_URI,
                step_up_acr=frozenset({_STEP_UP_ACR}))

        def local_jwks(url):
            if url != _JWKS_URI:
                raise ValueError('Unexpected JWKS location')
            return {'keys': [self.jwk]}

        with patch('provisioner.controlplane.authority.oidc._download_jwks',
                   new=local_jwks):
            self.app = create_postgres_app(settings)
        self.client = TestClient(self.app)

    def _enroll(self, name, roles, *, tenant=None, subject=None):
        subject = subject or name + '-' + self.ctx.organization_id
        session = 'session-' + name + '-' + self.ctx.organization_id
        payload = {
            'format': 'hosting-directory-snapshot/1', 'issuer': _ISSUER,
            'audience': _SYNC_AUDIENCE, 'subject': subject,
            'organizationId': self.ctx.organization_id,
            'tenantId': tenant or self.ctx.tenant_id,
            'identityKind': 'HUMAN', 'active': True, 'generation': 1,
            'issuedAt': int(self.now.timestamp()),
            'grants': [
                {'role': role, 'scope': deepcopy(scope),
                 'expiresAt': int((self.now + timedelta(minutes=30)).timestamp())}
                for role, scope in roles],
            'sessions': [{'sessionId': session,
                          'expiresAt': int((self.now + timedelta(minutes=30)).timestamp())}],
        }
        self._apply(payload)
        self.sessions[name] = (subject, session)
        self.snapshots[name] = payload

    def _apply(self, payload):
        raw = json.dumps(payload, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.assertTrue(self.sync.apply(raw, self.iam_key.sign(raw)))

    def _token(self, name, *, step_up=False):
        subject, session = self.sessions[name]
        claims = {
            'iss': _ISSUER, 'aud': _API_AUDIENCE, 'sub': subject, 'sid': session,
            'iat': int(self.now.timestamp()), 'nbf': int(self.now.timestamp()),
            'exp': int((self.now + timedelta(minutes=10)).timestamp()),
            # These caller-controlled claims must not override the IAM directory.
            'organizationId': 'forged-org', 'tenantId': 'forged-tenant',
            'roles': ['EXECUTION_OPERATOR'],
        }
        if step_up:
            claims['acr'] = _STEP_UP_ACR
            claims['auth_time'] = int(self.now.timestamp())
        return jwt.encode(claims, self.rsa_key, algorithm='RS256',
                          headers={'kid': 'local-key', 'typ': 'at+jwt'})

    def _auth(self, name, *, step_up=False):
        return {'Authorization': 'Bearer ' + self._token(name, step_up=step_up)}

    def test_signed_oidc_and_live_directory_bind_http_to_postgres(self):
        workload_id = self.observed['metadata']['workloadId']
        plan_id = self.selected['metadata']['planId']
        workload_url = f'/v1/wsds/wsd-01/workloads/{workload_id}'
        self.assertEqual(self.client.get(workload_url).status_code, 401)
        read = self.client.get(workload_url, headers=self._auth('reader'))
        self.assertEqual(read.status_code, 200, read.text)
        self.assertEqual(read.json()['record']['metadata']['workloadId'], workload_id)
        for name in ('foreign', 'one-sided'):
            self.assertEqual(self.client.get(workload_url,
                                             headers=self._auth(name)).status_code, 404)
        self.assertEqual(self.client.get(
            f'/v1/wsds/wsd-02/workloads/{workload_id}',
            headers=self._auth('reader')).status_code, 404)

        planned = deepcopy(self.observed)
        planned['metadata']['workloadId'] = 'draft-' + uuid4().hex
        planned['spec']['state'] = 'PLANNED'
        for machine in planned['spec']['machines']:
            for resource in (machine, *machine['disks'], *machine['nics']):
                resource['bindings'] = []
        for dataset in planned['spec']['datasets']:
            dataset['sourceBindings'] = []
        created = self.client.post('/v1/wsds/wsd-01/workloads',
                                   headers=self._auth('editor'), json=planned)
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(self.client.get(
            '/v1/wsds/wsd-01/workloads/' + planned['metadata']['workloadId'],
            headers=self._auth('reader')).status_code, 200)

        review_url = f'/v1/plans/{plan_id}/review'
        self.assertEqual(self.client.get(
            review_url, headers=self._auth('reader')).status_code, 404)
        reviewed = self.client.get(review_url, headers=self._auth('source-owner'))
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        binding = reviewed.json()
        self.assertEqual((binding['planRevision'], binding['planDigest']),
                         (1, self.selected['metadata']['planDigest']))
        self.assertEqual(binding['eligibleRoles'], ['SOURCE_OWNER'])
        self.assertEqual(binding['destination']['securityDomainId'], 'wsd-02')
        self.assertNotIn('machineMappings', reviewed.text)
        self.assertNotIn('authorSubject', reviewed.text)

        approval_url = f'/v1/plans/{plan_id}/approvals'
        self_approval = self.client.post(
            approval_url, headers=self._auth('author', step_up=True),
            json={'role': 'SOURCE_OWNER', 'ttlSeconds': 300,
                  'expectedPlanRevision': binding['planRevision'],
                  'expectedPlanDigest': binding['planDigest']})
        self.assertEqual(self_approval.status_code, 403, self_approval.text)
        stale = self.client.post(approval_url, headers=self._auth('source-owner', step_up=True),
                                 json={'role': 'SOURCE_OWNER', 'ttlSeconds': 300,
                                       'expectedPlanRevision': 1,
                                       'expectedPlanDigest': '0' * 64})
        self.assertEqual(stale.status_code, 409, stale.text)
        for name, role in (
                ('source-owner', 'SOURCE_OWNER'),
                ('destination-owner', 'DESTINATION_OWNER'),
                ('source-security', 'SOURCE_SECURITY'),
                ('destination-security', 'DESTINATION_SECURITY')):
            approved = self.client.post(
                approval_url, headers=self._auth(name, step_up=True),
                json={'role': role, 'ttlSeconds': 600,
                      'expectedPlanRevision': binding['planRevision'],
                      'expectedPlanDigest': binding['planDigest']})
            self.assertEqual(approved.status_code, 201, approved.text)
            self.assertEqual(approved.json()['planDigest'], binding['planDigest'])

        submit_url = f'/v1/plans/{plan_id}/jobs'
        reader_submit = self.client.post(
            submit_url, headers=self._auth('reader') | {'Idempotency-Key': 'reader-attempt'})
        self.assertEqual(reader_submit.status_code, 403)
        admitted = self.client.post(
            submit_url, headers=self._auth('operator') | {'Idempotency-Key': 'admit-' + uuid4().hex})
        self.assertEqual(admitted.status_code, 202, admitted.text)
        job_id = admitted.json()['jobId']
        self.assertEqual(admitted.json()['status'], 'QUEUED')
        self.assertEqual(self.client.get('/v1/jobs/' + job_id,
                                         headers=self._auth('operator')).status_code, 200)
        self.assertEqual(self.client.get('/v1/jobs/' + job_id,
                                         headers=self._auth('one-sided')).status_code, 404)
        self.assertEqual(self.client.get('/v1/jobs/' + job_id,
                                         headers=self._auth('foreign')).status_code, 404)
        events = self.client.get('/v1/jobs/' + job_id + '/events',
                                 headers=self._auth('operator'))
        self.assertEqual(events.status_code, 200, events.text)
        self.assertEqual(events.json()['items'][0]['eventType'], 'JOB_ADMITTED')
        self.assertEqual(events.json()['items'][0]['status'], 'QUEUED')
        with self.psycopg.connect(os.environ['HOSTING_TEST_POSTGRES_RUNTIME_DSN']) as connection:
            connection.execute(
                "SELECT set_config('app.organization_id', %s, true), "
                "set_config('app.tenant_id', %s, true)",
                (self.ctx.organization_id, self.ctx.tenant_id))
            approvals = connection.execute(
                'SELECT count(*) FROM hosting_controlplane.plan_approvals '
                'WHERE organization_id = %s AND tenant_id = %s AND plan_id = %s',
                (self.ctx.organization_id, self.ctx.tenant_id, plan_id)).fetchone()[0]
            outbox = connection.execute(
                'SELECT count(*) FROM hosting_controlplane.job_outbox '
                'WHERE organization_id = %s AND tenant_id = %s AND job_id = %s',
                (self.ctx.organization_id, self.ctx.tenant_id, job_id)).fetchone()[0]
            persisted_events = connection.execute(
                'SELECT count(*) FROM hosting_controlplane.job_events '
                'WHERE organization_id = %s AND tenant_id = %s AND job_id = %s',
                (self.ctx.organization_id, self.ctx.tenant_id, job_id)).fetchone()[0]
        self.assertEqual((approvals, outbox, persisted_events), (4, 1, 1))

        revoked = deepcopy(self.snapshots['reader'])
        revoked.update(generation=2, active=False, grants=[], sessions=[],
                       issuedAt=int(datetime.now(timezone.utc).timestamp()))
        self._apply(revoked)
        self.assertEqual(self.client.get(workload_url,
                                         headers=self._auth('reader')).status_code, 401)


if __name__ == '__main__':
    unittest.main()
