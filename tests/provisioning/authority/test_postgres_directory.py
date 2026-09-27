"""Signed IAM enrollment and pre-tenant OIDC lookup on isolated PostgreSQL."""
from __future__ import annotations

import json
import os
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provisioner.controlplane.authority.directory import (
    DirectorySyncRefused, PostgresRoleDirectory, SignedDirectorySync)
from provisioner.controlplane.persistence import AuditContext, EnterpriseRecordStore, TenantContext
from provisioner.controlplane.persistence.migrate import apply_migrations
from provisioner.domain.enterprise_records import plan_digest
from tests.provisioning.schema.test_enterprise_records import plan, workload


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_DIRECTORY_RESOLVER_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_DIRECTORY_WRITER_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_AUTHORITY_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED') == '1',
                     'Requires isolated PostgreSQL directory and authority roles')
class DirectoryPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        cls.psycopg = psycopg
        apply_migrations(lambda: psycopg.connect(
            os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']))
        cls.reader_dsn = os.environ['HOSTING_TEST_POSTGRES_DIRECTORY_RESOLVER_DSN']
        cls.writer_dsn = os.environ['HOSTING_TEST_POSTGRES_DIRECTORY_WRITER_DSN']
        cls.authority_dsn = os.environ['HOSTING_TEST_POSTGRES_AUTHORITY_DSN']
        cls.runtime_dsn = os.environ['HOSTING_TEST_POSTGRES_RUNTIME_DSN']

    def setUp(self):
        suffix = uuid4().hex[:12]
        self.ctx = TenantContext('org-' + suffix, 'tenant-' + suffix)
        self.issuer = 'https://iam.example.test/realm'
        self.audience = 'urn:hosting:directory-sync'
        self.subject = 'subject-' + suffix
        self.session = 'session-' + suffix
        self.key = Ed25519PrivateKey.generate()
        self.sync = SignedDirectorySync(
            lambda: self.psycopg.connect(self.writer_dsn),
            issuer=self.issuer, audience=self.audience,
            public_key=self.key.public_key())
        self.directory = PostgresRoleDirectory(
            lambda: self.psycopg.connect(self.reader_dsn))
        self.now = datetime.now(timezone.utc)

    def payload(self, generation=1):
        return {
            'format': 'hosting-directory-snapshot/1', 'issuer': self.issuer,
            'audience': self.audience, 'subject': self.subject,
            'organizationId': self.ctx.organization_id,
            'tenantId': self.ctx.tenant_id, 'identityKind': 'HUMAN',
            'active': True, 'generation': generation,
            'issuedAt': int(self.now.timestamp()),
            'grants': [{'role': 'SOURCE_OWNER', 'scope': {
                'organizationId': self.ctx.organization_id,
                'tenantId': self.ctx.tenant_id,
                'locationId': 'site-1', 'securityDomainId': 'wsd-01',
                'endpointId': 'endpoint-1', 'nativeScopeId': 'native-1',
                'platformFamily': 'vmware'},
                'expiresAt': int((self.now + timedelta(minutes=20)).timestamp())}],
            'sessions': [{'sessionId': self.session,
                          'expiresAt': int((self.now + timedelta(minutes=20)).timestamp())}],
        }

    def signed(self, payload):
        raw = json.dumps(payload, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False).encode()
        return raw, self.key.sign(raw)

    def test_signed_snapshot_replay_session_and_role_revocation(self):
        raw, signature = self.signed(self.payload())
        with self.assertRaises(DirectorySyncRefused):
            self.sync.apply(raw, b'0' * 64)
        self.assertTrue(self.sync.apply(raw, signature))
        self.assertFalse(self.sync.apply(raw, signature))
        identity = self.directory.resolve(self.issuer, self.subject, self.session)
        self.assertEqual((identity.organization_id, identity.tenant_id),
                         (self.ctx.organization_id, self.ctx.tenant_id))
        self.assertEqual([grant.role for grant in identity.grants], ['SOURCE_OWNER'])
        with self.assertRaises(PermissionError):
            self.directory.resolve(self.issuer, self.subject, 'not-enrolled')
        with self.assertRaises(DirectorySyncRefused):
            self.sync.apply(*self.signed(dict(self.payload(),
                                              generation=1, grants=[])))
        revoked = self.payload(2)
        revoked.update(active=False, grants=[], sessions=[])
        self.assertTrue(self.sync.apply(*self.signed(revoked)))
        with self.assertRaises(PermissionError):
            self.directory.resolve(self.issuer, self.subject, self.session)
        with self.assertRaises(DirectorySyncRefused):
            self.sync.apply(raw, signature)

    def test_cross_tenant_scope_or_unsigned_claim_cannot_enroll(self):
        bad = self.payload()
        bad['grants'][0]['scope']['tenantId'] = 'foreign'
        with self.assertRaises(DirectorySyncRefused):
            self.sync.apply(*self.signed(bad))
        raw, signature = self.signed(self.payload())
        with self.assertRaises(DirectorySyncRefused):
            self.sync.apply(raw + b' ', signature)

    def test_role_generation_invalidates_existing_plan_authority(self):
        self.sync.apply(*self.signed(self.payload()))
        w, p = deepcopy(workload()), deepcopy(plan())
        for record in (w, p):
            record['metadata']['organizationId'] = self.ctx.organization_id
            record['metadata']['tenantId'] = self.ctx.tenant_id
        w['metadata']['workloadId'] = 'directory-workload-' + uuid4().hex
        p['spec']['workloadId'] = w['metadata']['workloadId']
        p['metadata']['planId'] = 'directory-plan-' + uuid4().hex
        for scope in (p['spec']['source'], p['spec']['destination']):
            scope['organizationId'] = self.ctx.organization_id
            scope['tenantId'] = self.ctx.tenant_id
        p['metadata']['planDigest'] = plan_digest(p)
        store = EnterpriseRecordStore(lambda: self.psycopg.connect(self.runtime_dsn))
        store.create(self.ctx, w, AuditContext('author', 'directory-test-' + uuid4().hex))
        store.create(self.ctx, p, AuditContext('author', 'directory-test-' + uuid4().hex))
        with self.psycopg.connect(self.authority_dsn) as connection:
            connection.execute("SELECT set_config('app.organization_id', %s, true), "
                               "set_config('app.tenant_id', %s, true)",
                               (self.ctx.organization_id, self.ctx.tenant_id))
            source = p['spec']['source']
            connection.execute(
                'INSERT INTO hosting_controlplane.plan_approvals '
                '(approval_id, organization_id, tenant_id, plan_id, plan_revision, '
                'plan_digest, revocation_epoch, role, site_id, security_domain_id, '
                'endpoint_id, native_scope_id, platform_family, approver_subject, '
                'issued_at, expires_at) VALUES '
                '(%s, %s, %s, %s, 1, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                ('approval-' + uuid4().hex, self.ctx.organization_id,
                 self.ctx.tenant_id, p['metadata']['planId'],
                 p['metadata']['planDigest'], 'SOURCE_OWNER',
                 source['locationId'], source['securityDomainId'],
                 source['endpointId'], source['nativeScopeId'],
                 source['platformFamily'], self.subject, self.now,
                 self.now + timedelta(minutes=20)))
        update = self.payload(2)
        update['grants'] = []
        self.sync.apply(*self.signed(update))
        with self.psycopg.connect(self.authority_dsn) as connection:
            connection.execute("SELECT set_config('app.organization_id', %s, true), "
                               "set_config('app.tenant_id', %s, true)",
                               (self.ctx.organization_id, self.ctx.tenant_id))
            epoch = connection.execute(
                'SELECT revocation_epoch FROM hosting_controlplane.plan_authority_state '
                'WHERE plan_id = %s', (p['metadata']['planId'],)).fetchone()[0]
        self.assertEqual(epoch, 1)


if __name__ == '__main__':
    unittest.main()
