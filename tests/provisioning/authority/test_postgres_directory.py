"""Signed IAM enrollment and pre-tenant OIDC lookup on isolated PostgreSQL."""
from __future__ import annotations

import json
import os
import hashlib
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

    def test_signed_monitor_service_enrollment_and_live_revocation_preserve_role_separation(self):
        payload=self.payload()
        payload['identityKind']='SERVICE';payload['grants'][0]['role']='DISCOVERY_MONITOR'
        raw,signature=self.signed(payload)
        with self.assertRaises(DirectorySyncRefused):self.sync.apply(raw,b'0'*64)
        self.assertTrue(self.sync.apply(raw,signature))
        identity=self.directory.resolve(self.issuer,self.subject,self.session)
        self.assertEqual(identity.kind,'SERVICE')
        self.assertEqual([grant.role for grant in identity.grants],['DISCOVERY_MONITOR'])
        for kind,role in [('SERVICE','EXECUTION_OPERATOR'),('SERVICE','SOURCE_OWNER'),
                          ('SERVICE','WORKER'),('HUMAN','DISCOVERY_MONITOR'),('WORKER','DISCOVERY_MONITOR')]:
            changed=deepcopy(payload);changed.update(generation=2,identityKind=kind)
            changed['grants'][0]['role']=role
            with self.subTest(kind=kind,role=role),self.assertRaises(DirectorySyncRefused):
                self.sync.apply(*self.signed(changed))
        revoked=deepcopy(payload);revoked.update(generation=2,active=False,grants=[],sessions=[])
        self.assertTrue(self.sync.apply(*self.signed(revoked)))
        with self.assertRaises(PermissionError):self.directory.resolve(self.issuer,self.subject,self.session)
        with self.assertRaises(DirectorySyncRefused):self.sync.apply(raw,signature)

    def test_historical_backfill_requires_fresh_signed_generation(self):
        historical = self.payload()
        raw, signature = self.signed(historical)
        digest = hashlib.sha256(raw).hexdigest()
        with self.psycopg.connect(os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']) as owner:
            owner.execute("SELECT set_config('app.organization_id', %s, true), "
                          "set_config('app.tenant_id', %s, true)",
                          (self.ctx.organization_id, self.ctx.tenant_id))
            owner.execute(
                'INSERT INTO hosting_controlplane.directory_subjects '
                '(issuer, subject, organization_id, tenant_id, identity_kind, '
                'active, grants, generation, signed_digest) VALUES '
                '(%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)',
                (self.issuer, self.subject, self.ctx.organization_id,
                 self.ctx.tenant_id, 'HUMAN', True,
                 json.dumps(historical['grants']), 1, digest))
            owner.execute(
                'INSERT INTO hosting_controlplane.directory_sessions '
                '(issuer, subject, session_id, expires_at) VALUES (%s, %s, %s, %s)',
                (self.issuer, self.subject, self.session,
                 datetime.fromtimestamp(historical['sessions'][0]['expiresAt'],
                                        timezone.utc)))
            owner.execute(
                'INSERT INTO hosting_controlplane.directory_sync_events '
                '(issuer, subject, generation, signed_digest) VALUES (%s, %s, %s, %s)',
                (self.issuer, self.subject, 1, digest))
            state_digest = owner.execute(
                'SELECT hosting_controlplane.directory_state_digest(%s, %s)',
                (self.issuer, self.subject)).fetchone()[0]
            owner.execute(
                'INSERT INTO hosting_controlplane.audit_events '
                '(organization_id, tenant_id, actor_id, correlation_id, action, '
                'record_kind, record_id, revision, record_digest, details, occurred_at) VALUES '
                "(%s, %s, %s, %s, 'DIRECTORY_SYNC', 'DirectorySubject', "
                '%s, 1, %s, %s::jsonb, %s)',
                (self.ctx.organization_id, self.ctx.tenant_id,
                 'iam-sync:' + self.issuer, digest, self.subject, digest,
                 json.dumps({'stateDigest': state_digest}),
                 self.now - timedelta(minutes=1)))
        # The migration's backfilled digest matches current state, yet cannot
        # attest that the old materialization came from the signed IAM feed.
        with self.assertRaises(PermissionError):
            self.directory.resolve(self.issuer, self.subject, self.session)
        self.assertFalse(self.sync.apply(raw, signature))
        with self.assertRaises(PermissionError):
            self.directory.resolve(self.issuer, self.subject, self.session)
        stale = self.payload(2)
        stale['issuedAt'] = int((self.now - timedelta(minutes=2)).timestamp())
        with self.assertRaises(DirectorySyncRefused):
            self.sync.apply(*self.signed(stale))
        with self.assertRaises(PermissionError):
            self.directory.resolve(self.issuer, self.subject, self.session)
        self.assertTrue(self.sync.apply(*self.signed(self.payload(2))))
        self.assertEqual([grant.role for grant in self.directory.resolve(
            self.issuer, self.subject, self.session).grants], ['SOURCE_OWNER'])

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

    def test_audit_binding_rejects_selective_directory_rollback(self):
        first, first_signature = self.signed(self.payload())
        self.sync.apply(first, first_signature)
        second_payload = self.payload(2)
        second_payload['grants'] = []
        second_payload['sessions'].append({
            'sessionId': 'spare-' + self.session,
            'expiresAt': int((self.now + timedelta(minutes=20)).timestamp())})
        second, second_signature = self.signed(second_payload)
        self.sync.apply(second, second_signature)
        self.assertEqual(self.directory.resolve(
            self.issuer, self.subject, self.session).grants, ())
        with self.psycopg.connect(self.runtime_dsn) as connection:
            connection.execute("SELECT set_config('app.organization_id', %s, true), "
                               "set_config('app.tenant_id', %s, true)",
                               (self.ctx.organization_id, self.ctx.tenant_id))
            audit_rows = connection.execute(
                'SELECT revision, record_digest, details::text '
                'FROM hosting_controlplane.audit_events '
                "WHERE action = 'DIRECTORY_SYNC' AND record_id = %s "
                'ORDER BY audit_sequence', (self.subject,)).fetchall()
        self.assertEqual([(row[0], row[1]) for row in audit_rows], [
            (1, hashlib.sha256(first).hexdigest()),
            (2, hashlib.sha256(second).hexdigest())])
        self.assertTrue(all(
            len(json.loads(row[2])['stateDigest']) == 64 and
            json.loads(row[2])['provenance'] == 'signed-iam-full-subject/1'
            for row in audit_rows))
        self.assertNotIn(self.session, repr(audit_rows))

        # Changing another session invalidates this otherwise valid session:
        # the marker binds the complete live materialization.
        with self.psycopg.connect(os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']) as owner:
            owner.execute(
                'DELETE FROM hosting_controlplane.directory_sessions '
                'WHERE issuer = %s AND subject = %s AND session_id = %s',
                (self.issuer, self.subject, 'spare-' + self.session))
        with self.assertRaises(PermissionError):
            self.directory.resolve(self.issuer, self.subject, self.session)

        with self.psycopg.connect(os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']) as owner:
            owner.execute(
                'INSERT INTO hosting_controlplane.directory_sessions '
                '(issuer, subject, session_id, expires_at) VALUES (%s, %s, %s, %s)',
                (self.issuer, self.subject, 'spare-' + self.session,
                 datetime.fromtimestamp(
                     second_payload['sessions'][1]['expiresAt'], timezone.utc)))
        self.assertEqual(self.directory.resolve(
            self.issuer, self.subject, self.session).grants, ())

        with self.psycopg.connect(os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']) as owner:
            owner.execute(
                'UPDATE hosting_controlplane.directory_subjects SET grants = %s::jsonb '
                'WHERE issuer = %s AND subject = %s',
                (json.dumps(self.payload()['grants']), self.issuer, self.subject))
        with self.assertRaises(PermissionError):
            self.directory.resolve(self.issuer, self.subject, self.session)
        with self.psycopg.connect(os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']) as owner:
            owner.execute(
                "UPDATE hosting_controlplane.directory_subjects SET grants = '[]'::jsonb "
                'WHERE issuer = %s AND subject = %s',
                (self.issuer, self.subject))
        self.assertEqual(self.directory.resolve(
            self.issuer, self.subject, self.session).grants, ())

        # Simulate restoration of just mutable directory state while the
        # independently checkpointed audit stream still records generation 2.
        with self.psycopg.connect(os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']) as owner:
            owner.execute(
                'UPDATE hosting_controlplane.directory_subjects '
                'SET generation = 1, signed_digest = %s, grants = %s::jsonb '
                'WHERE issuer = %s AND subject = %s',
                (hashlib.sha256(first).hexdigest(),
                 json.dumps(self.payload()['grants']), self.issuer, self.subject))
        with self.assertRaises(PermissionError):
            self.directory.resolve(self.issuer, self.subject, self.session)


if __name__ == '__main__':
    unittest.main()
