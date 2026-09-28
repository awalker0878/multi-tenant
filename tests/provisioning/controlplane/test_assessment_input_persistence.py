"""Real PostgreSQL signed-input retention, RLS and dedicated writer coverage."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.assessment_inputs import (
    AssessmentInputDenied, AssessmentInputRepository, parse_evidence)
from provisioner.controlplane.persistence.environments import (
    EnvironmentDeclaration, EnvironmentRepository)
from provisioner.controlplane.persistence.store import AuditContext, TenantContext
from tests.provisioning.discovery.test_assessment_inputs import NOW, SignedFixture


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_ASSESSMENT_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN'),
                     'Requires dedicated disposable PostgreSQL assessment roles')
class AssessmentInputPersistenceTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        self.psycopg = psycopg
        self.runtime_dsn = os.environ['HOSTING_TEST_POSTGRES_RUNTIME_DSN']
        self.ingest_dsn = os.environ['HOSTING_TEST_POSTGRES_ASSESSMENT_DSN']
        self.ctx = TenantContext('org-' + uuid4().hex[:12], 'tenant')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fixture = SignedFixture(Path(self.temp.name) / 'assessment-policy.json')
        self.delta = datetime.now(timezone.utc) - NOW
        self.fixture.policy = self.adjust(self.fixture.policy)
        self.fixture.write()
        self.writer = AssessmentInputRepository(lambda: psycopg.connect(self.ingest_dsn),
            self.fixture.trust, ingest_role='hosting_assessment_ingest')
        self.reader = AssessmentInputRepository(lambda: psycopg.connect(self.runtime_dsn),
                                                self.fixture.trust)
        environments = EnvironmentRepository(lambda: psycopg.connect(self.runtime_dsn))
        for name, endpoint, native, family in (('source', 'endpoint-a', 'scope-a', 'vmware'),
                                                ('target', 'endpoint-b', 'scope-b', 'nutanix')):
            scope = PlanScope(self.ctx.organization_id, self.ctx.tenant_id,
                               'site-a' if name == 'source' else 'site-b', 'wsd', endpoint, native, family)
            environments.create(self.ctx, EnvironmentDeclaration(name, name, scope),
                                AuditContext('test-registrar', 'assessment-test'))

    def adjust(self, value):
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if key == 'organizationId':
                    result[key] = self.ctx.organization_id
                elif key in ('issuedAt', 'expiresAt', 'observedAt', 'notBefore', 'revokedAt') and item:
                    result[key] = (datetime.fromisoformat(item) + self.delta).isoformat()
                else:
                    result[key] = self.adjust(item)
            return result
        if isinstance(value, list):
            return [self.adjust(item) for item in value]
        return value

    def document(self, kind='INSTALLATION'):
        return self.adjust(self.fixture.document(kind))

    def read(self, document, *, ctx=None):
        evidence = parse_evidence(document)
        return self.reader.latest(ctx or self.ctx, evidence.kind, evidence.binding_digest,
                                  datetime.now(timezone.utc))

    def test_signed_ingest_roundtrip_exact_retry_and_monotonic_revisions(self):
        for kind in ('INSTALLATION', 'ROUTE', 'CONTROL'):
            with self.subTest(kind=kind):
                document = self.document(kind)
                signatures = self.fixture.sign(document)
                digest = self.writer.ingest(self.ctx, document, signatures)
                self.assertEqual(self.writer.ingest(self.ctx, document, signatures), digest)
                actual = self.read(document)
                self.assertEqual(actual.digest, digest)
                newer = dict(document, evidenceId=kind + '-new-evidence', revision=2)
                self.writer.ingest(self.ctx, newer, self.fixture.sign(newer))
                self.assertEqual(self.read(document).revision, 2)
                with self.assertRaises(AssessmentInputDenied):
                    self.writer.ingest(self.ctx, document, signatures)
                self.assertIsNone(self.read(document, ctx=TenantContext('another-org', 'tenant')))

    def test_runtime_has_no_ingest_and_rows_are_append_only(self):
        document = self.document()
        with self.assertRaises(AssessmentInputDenied):
            self.reader.ingest(self.ctx, document, self.fixture.sign(document))
        self.writer.ingest(self.ctx, document, self.fixture.sign(document))
        for dsn in (self.runtime_dsn, self.ingest_dsn):
            with self.psycopg.connect(dsn) as connection:
                connection.execute("SELECT set_config('app.organization_id', %s, true), "
                                   "set_config('app.tenant_id', %s, true)",
                                   (self.ctx.organization_id, self.ctx.tenant_id))
                with self.assertRaises(self.psycopg.Error), connection.transaction():
                    connection.execute("DELETE FROM hosting_controlplane.assessment_inputs")
                with self.assertRaises(self.psycopg.Error), connection.transaction():
                    connection.execute("UPDATE hosting_controlplane.assessment_inputs SET revision = 9")

    def test_live_revocation_invalidates_previously_persisted_inputs(self):
        document = self.document()
        self.writer.ingest(self.ctx, document, self.fixture.sign(document))
        self.assertIsNotNone(self.read(document))
        self.fixture.policy['revision'] += 1
        self.fixture.policy['revokedEvidenceIds'] = [document['evidenceId']]
        self.fixture.write()
        with self.assertRaises(AssessmentInputDenied):
            self.read(document)

    def test_raw_sql_forgery_cannot_become_trusted_evidence(self):
        document = self.document()
        self.writer.ingest(self.ctx, document, self.fixture.sign(document))
        forged = dict(document, evidenceId='forged-installation', revision=99)
        evidence = parse_evidence(forged)
        with self.psycopg.connect(self.ingest_dsn) as connection:
            connection.execute("SELECT set_config('app.organization_id', %s, true), "
                               "set_config('app.tenant_id', %s, true)",
                               (self.ctx.organization_id, self.ctx.tenant_id))
            connection.execute('INSERT INTO hosting_controlplane.assessment_inputs '
                '(organization_id, tenant_id, evidence_id, kind, binding_digest, revision, '
                'evidence_json, evidence_digest, signatures_json, policy_json, policy_signature, '
                'policy_revision, policy_digest, verified_at, verified_subjects) '
                'SELECT organization_id, tenant_id, %s, kind, binding_digest, 99, %s, %s, '
                'signatures_json, policy_json, policy_signature, policy_revision, policy_digest, '
                'verified_at, verified_subjects FROM hosting_controlplane.assessment_inputs '
                'WHERE organization_id = %s AND tenant_id = %s AND evidence_id = %s',
                (evidence.evidence_id, evidence.canonical_json, evidence.digest,
                 self.ctx.organization_id, self.ctx.tenant_id, document['evidenceId']))
        with self.assertRaises(AssessmentInputDenied):
            self.read(document)

    def test_policy_and_signatures_are_retained_with_issuer_time_proof(self):
        document = self.document('ROUTE')
        self.writer.ingest(self.ctx, document, self.fixture.sign(document))
        with self.psycopg.connect(self.runtime_dsn) as connection:
            connection.execute("SELECT set_config('app.organization_id', %s, true), "
                               "set_config('app.tenant_id', %s, true)",
                               (self.ctx.organization_id, self.ctx.tenant_id))
            row = connection.execute('SELECT policy_json, policy_signature, policy_revision, '
                'signatures_json, verified_subjects, verified_at FROM hosting_controlplane.assessment_inputs '
                'WHERE evidence_id = %s', (document['evidenceId'],)).fetchone()
        self.assertEqual(json.loads(row[0]), self.fixture.policy)
        self.assertEqual(len(row[1]), 88)
        self.assertEqual(row[2], 1)
        self.assertEqual(len(json.loads(row[3])), 2)
        self.assertEqual(set(row[4]), {'SOURCE_EXIT-reviewer', 'TARGET_OPERATE-reviewer'})
        self.assertIsNotNone(row[5].tzinfo)

    def test_site_worker_cannot_read_even_with_an_accidental_table_grant(self):
        site_dsn = os.environ.get('HOSTING_TEST_POSTGRES_SITE_WORKER_DSN')
        owner_dsn = os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN')
        if not site_dsn or not owner_dsn:
            self.skipTest('Requires disposable site worker and migration roles')
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict
        site_role = conninfo_to_dict(site_dsn)['user']
        document = self.document()
        self.writer.ingest(self.ctx, document, self.fixture.sign(document))
        with self.psycopg.connect(owner_dsn) as owner:
            had_select = owner.execute("SELECT has_table_privilege(%s, "
                "'hosting_controlplane.assessment_inputs', 'SELECT')", (site_role,)).fetchone()[0]
            owner.execute(sql.SQL('GRANT SELECT ON hosting_controlplane.assessment_inputs TO {}')
                          .format(sql.Identifier(site_role)))
        try:
            with self.psycopg.connect(site_dsn) as site:
                site.execute("SELECT set_config('app.organization_id', %s, true), "
                             "set_config('app.tenant_id', %s, true)",
                             (self.ctx.organization_id, self.ctx.tenant_id))
                self.assertEqual(site.execute(
                    'SELECT evidence_id FROM hosting_controlplane.assessment_inputs').fetchall(), [])
        finally:
            if not had_select:
                with self.psycopg.connect(owner_dsn) as owner:
                    owner.execute(sql.SQL('REVOKE SELECT ON hosting_controlplane.assessment_inputs FROM {}')
                                  .format(sql.Identifier(site_role)))


if __name__ == '__main__':
    unittest.main()
