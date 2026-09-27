"""Isolated PostgreSQL worker admission, revocation and RLS contract."""
from __future__ import annotations

import json
import os
import unittest
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence import TenantContext, canonical_record_digest
from provisioner.controlplane.persistence.migrate import apply_migrations
from provisioner.controlplane.worker import (GrantDenied, GrantRequest,
                                             PostgresWorkerGrants,
                                             VerifiedWorkerIdentity)
from provisioner.domain.enterprise_records import plan_digest
from tests.provisioning.schema.test_enterprise_records import plan, workload


class LockedTestLease:
    """Test lease authority; deployment must supply B11's database lease."""

    def __init__(self):
        self.epoch = 2

    def require_current(self, cursor, context, *, lease_key, lease_epoch,
                        job_id, operation_id, scope, worker_subject):
        if (lease_key != 'lease-01' or lease_epoch != self.epoch
                or not job_id.startswith('job-') or operation_id != 'operation-01'
                or scope.site_id != 'cluster-east' or worker_subject != 'worker-01'):
            raise GrantDenied('Native operation lease is no longer current')


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED') == '1',
                     'Requires isolated PostgreSQL migration/runtime roles')
class WorkerPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import psycopg
        except ImportError as exc:
            raise unittest.SkipTest('Install hosting-provisioner[controlplane]') from exc
        cls.psycopg = psycopg
        cls.migration_dsn = os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']
        cls.runtime_dsn = os.environ['HOSTING_TEST_POSTGRES_RUNTIME_DSN']
        apply_migrations(lambda: psycopg.connect(cls.migration_dsn))

    def _tenant(self, connection):
        connection.execute(
            "SELECT set_config('app.organization_id', %s, true), "
            "set_config('app.tenant_id', %s, true)",
            (self.context.organization_id, self.context.tenant_id))

    def setUp(self):
        suffix = uuid4().hex[:14]
        self.context = TenantContext('org-' + suffix, 'tenant-01')
        self.foreign = TenantContext('org-' + suffix, 'tenant-foreign')
        now = datetime.now(timezone.utc)
        self.workload = workload()
        self.workload['metadata'].update(
            organizationId=self.context.organization_id,
            tenantId=self.context.tenant_id,
            workloadId='workload-' + suffix)
        self.plan = plan()
        self.plan['metadata'].update(
            organizationId=self.context.organization_id,
            tenantId=self.context.tenant_id,
            planId='plan-' + suffix)
        self.plan['spec']['workloadId'] = self.workload['metadata']['workloadId']
        for scope in (self.plan['spec']['source'], self.plan['spec']['destination']):
            scope.update(organizationId=self.context.organization_id,
                         tenantId=self.context.tenant_id)
        self.plan['metadata']['planDigest'] = plan_digest(self.plan)
        self.scope = PlanScope.from_record(self.plan['spec']['source'])
        self.target = PlanScope.from_record(self.plan['spec']['destination'])
        self.job_id = 'job-' + suffix
        self.identity = VerifiedWorkerIdentity(
            self.context.organization_id, self.context.tenant_id,
            'worker-01', self.scope.site_id,
            uuid4().hex + uuid4().hex, now + timedelta(hours=1))
        self.request = GrantRequest(
            self.job_id, 'step-01', 'operation-01', 'VM_POWER', self.scope,
            'lease-01', 2, timedelta(minutes=2))
        self.approval_ids = tuple(f'approval-{suffix}-{i}' for i in range(4))
        roles = (('SOURCE_OWNER', self.scope),
                 ('DESTINATION_OWNER', self.target),
                 ('SOURCE_SECURITY', self.scope),
                 ('DESTINATION_SECURITY', self.target))
        with self.psycopg.connect(self.migration_dsn) as connection:
            self._tenant(connection)
            for record in (self.workload, self.plan):
                key = ('workloadId' if record['kind'] == 'Workload' else 'planId')
                connection.execute(
                    'INSERT INTO hosting_controlplane.enterprise_records '
                    '(organization_id, tenant_id, record_kind, record_id, revision, '
                    'record_json, record_digest) VALUES (%s, %s, %s, %s, 1, %s::jsonb, %s)',
                    (self.context.organization_id, self.context.tenant_id,
                     record['kind'], record['metadata'][key], json.dumps(record),
                     canonical_record_digest(record)))
            connection.execute(
                'INSERT INTO hosting_controlplane.audit_events '
                '(organization_id, tenant_id, actor_id, correlation_id, action, '
                'record_kind, record_id, revision, record_digest) VALUES '
                "(%s, %s, 'plan-author', %s, 'RECORD_CREATE', 'MigrationPlan', %s, 1, %s)",
                (self.context.organization_id, self.context.tenant_id,
                 'corr-' + suffix, self.plan['metadata']['planId'],
                 canonical_record_digest(self.plan)))
            for i, ((role, scope), approval_id) in enumerate(zip(roles, self.approval_ids)):
                connection.execute(
                    'INSERT INTO hosting_controlplane.plan_approvals '
                    '(approval_id, organization_id, tenant_id, plan_id, '
                    'plan_revision, plan_digest, revocation_epoch, role, '
                    'site_id, security_domain_id, endpoint_id, native_scope_id, '
                    'platform_family, approver_subject, issued_at, expires_at) '
                    'VALUES (%s, %s, %s, %s, 1, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (approval_id, self.context.organization_id, self.context.tenant_id,
                     self.plan['metadata']['planId'], self.plan['metadata']['planDigest'],
                     role, scope.site_id, scope.security_domain_id, scope.endpoint_id,
                     scope.native_scope_id, scope.platform_family, f'reviewer-{i}',
                     now - timedelta(minutes=1), now + timedelta(hours=1)))
            connection.execute(
                'INSERT INTO hosting_controlplane.operation_jobs '
                '(organization_id, tenant_id, job_id, idempotency_key, plan_id, '
                'plan_revision, plan_digest, source_scope, destination_scope, '
                'actor_subject, approval_ids, revocation_epoch, status) VALUES '
                '(%s, %s, %s, %s, %s, 1, %s, %s::jsonb, %s::jsonb, '
                "%s, %s::jsonb, 0, 'STARTED')",
                (self.context.organization_id, self.context.tenant_id,
                 self.job_id, 'key-' + suffix, self.plan['metadata']['planId'],
                 self.plan['metadata']['planDigest'], json.dumps(asdict(self.scope)),
                 json.dumps(asdict(self.target)), 'job-operator',
                 json.dumps(self.approval_ids)))
            connection.execute(
                'INSERT INTO hosting_controlplane.worker_enrollments '
                '(organization_id, tenant_id, worker_subject, site_id, '
                'certificate_sha256, expires_at) VALUES (%s, %s, %s, %s, %s, %s)',
                (self.context.organization_id, self.context.tenant_id,
                 self.identity.subject, self.scope.site_id,
                 self.identity.certificate_sha256, now + timedelta(hours=1)))
            connection.execute(
                'INSERT INTO hosting_controlplane.worker_capabilities '
                '(organization_id, tenant_id, worker_subject, site_id, '
                'security_domain_id, endpoint_id, native_scope_id, platform_family, '
                'operation_kind, credential_ref) VALUES '
                '(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (self.context.organization_id, self.context.tenant_id,
                 self.identity.subject, self.scope.site_id,
                 self.scope.security_domain_id, self.scope.endpoint_id,
                 self.scope.native_scope_id, self.scope.platform_family,
                 'VM_POWER', 'secret-ref-' + suffix))
        self.lease = LockedTestLease()
        self.grants = PostgresWorkerGrants(
            lambda: self.psycopg.connect(self.runtime_dsn), self.lease)

    def test_grant_exact_scope_certificate_site_and_revocation(self):
        with self.assertRaises(GrantDenied):
            self.grants.issue_grant(
                self.context, replace(self.identity, site_id='other-site'), self.request)
        with self.assertRaises(GrantDenied):
            self.grants.issue_grant(
                self.context, replace(self.identity, certificate_sha256='f' * 64),
                self.request)
        with self.assertRaises(GrantDenied):
            self.grants.issue_grant(
                self.context, self.identity,
                replace(self.request, operation_scope=self.target))
        grant = self.grants.issue_grant(self.context, self.identity, self.request)
        with self.assertRaises(GrantDenied):
            self.grants.with_authorized_reference(
                self.foreign, self.identity, grant.grant_id,
                job_id=self.job_id, step_id='step-01', operation_id='operation-01',
                operation_kind='VM_POWER', operation_scope=self.scope,
                lease_key='lease-01', lease_epoch=2, use=lambda *_: None)
        references = []
        def use(reference, bound, expires):
            references.append(reference)
            self.assertEqual(bound, grant)
            self.assertLessEqual(expires, grant.expires_at)
        self.grants.with_authorized_reference(
            self.context, self.identity, grant.grant_id,
            job_id=self.job_id, step_id='step-01', operation_id='operation-01',
            operation_kind='VM_POWER', operation_scope=self.scope,
            lease_key='lease-01', lease_epoch=2, use=use)
        self.assertEqual(references, ['secret-ref-' + self.context.organization_id[4:]])
        self.lease.epoch = 3
        with self.assertRaises(GrantDenied):
            self.grants.with_authorized_reference(
                self.context, self.identity, grant.grant_id,
                job_id=self.job_id, step_id='step-01', operation_id='operation-01',
                operation_kind='VM_POWER', operation_scope=self.scope,
                lease_key='lease-01', lease_epoch=2, use=lambda *_: None)
        self.lease.epoch = 2
        with self.psycopg.connect(self.migration_dsn) as connection:
            self._tenant(connection)
            connection.execute(
                'UPDATE hosting_controlplane.worker_enrollments SET revoked_at = clock_timestamp() '
                'WHERE organization_id = %s AND tenant_id = %s AND worker_subject = %s',
                (self.context.organization_id, self.context.tenant_id,
                 self.identity.subject))
        with self.assertRaises(GrantDenied):
            self.grants.with_authorized_reference(
                self.context, self.identity, grant.grant_id,
                job_id=self.job_id, step_id='step-01', operation_id='operation-01',
                operation_kind='VM_POWER', operation_scope=self.scope,
                lease_key='lease-01', lease_epoch=2, use=lambda *_: None)

    def test_approval_epoch_and_append_only_grants(self):
        grant = self.grants.issue_grant(self.context, self.identity, self.request)
        with self.psycopg.connect(self.migration_dsn) as connection:
            self._tenant(connection)
            with self.assertRaises(self.psycopg.Error):
                connection.execute(
                    'UPDATE hosting_controlplane.worker_grants SET lease_epoch = 99 '
                    'WHERE organization_id = %s AND tenant_id = %s AND grant_id = %s',
                    (self.context.organization_id, self.context.tenant_id,
                     grant.grant_id))
            connection.rollback()
        with self.psycopg.connect(self.migration_dsn) as connection:
            self._tenant(connection)
            connection.execute(
                'UPDATE hosting_controlplane.plan_authority_state '
                'SET revocation_epoch = revocation_epoch + 1 '
                'WHERE organization_id = %s AND tenant_id = %s AND plan_id = %s',
                (self.context.organization_id, self.context.tenant_id,
                 self.plan['metadata']['planId']))
        with self.assertRaises(PermissionError):
            self.grants.with_authorized_reference(
                self.context, self.identity, grant.grant_id,
                job_id=self.job_id, step_id='step-01', operation_id='operation-01',
                operation_kind='VM_POWER', operation_scope=self.scope,
                lease_key='lease-01', lease_epoch=2, use=lambda *_: None)


if __name__ == '__main__':
    unittest.main()
