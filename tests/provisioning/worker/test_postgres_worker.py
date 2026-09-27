"""Isolated PostgreSQL worker admission, revocation and RLS contract."""
from __future__ import annotations

import json
import os
import unittest
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence import TenantContext, canonical_record_digest
from provisioner.controlplane.persistence.store import NativeBinding
from provisioner.controlplane.persistence.migrate import apply_migrations
from provisioner.controlplane.reconciliation.registry import NativeLeaseAuthority
from provisioner.controlplane.worker.runtime import SiteWorkerSettings, _require_read_only_role
from provisioner.controlplane.worker.vault import VaultDynamicRole
from provisioner.controlplane.worker import (GrantDenied, GrantRequest,
                                             EnrollmentDecision,
                                             PostgresWorkerGrants,
                                             PostgresWorkerEnrollment,
                                             VerifiedWorkerIdentity,
                                             WorkerCapability)
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


class TestWorkerVerifier:
    def verify(self, evidence):
        if not isinstance(evidence, VerifiedWorkerIdentity):
            raise GrantDenied('mTLS peer is required')
        return evidence


class TestEnrollmentAuthorizer:
    def require_enrollment(self, approval, context, identity, capabilities):
        if approval != 'approved-enrollment':
            raise GrantDenied('Administrative approval is required')
        return EnrollmentDecision('site-security-admin', 'corr-enrollment',
                                  'ticket-enrollment')

    def require_revocation(self, approval, context, worker_subject, fingerprint):
        if approval != 'approved-revocation':
            raise GrantDenied('Administrative approval is required')
        return EnrollmentDecision('site-security-admin', 'corr-revocation',
                                  'ticket-revocation')


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_ENROLLMENT_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED') == '1',
                     'Requires isolated PostgreSQL migration/runtime/enrollment roles')
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
        cls.enrollment_dsn = os.environ['HOSTING_TEST_POSTGRES_ENROLLMENT_DSN']
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
                'INSERT INTO hosting_controlplane.worker_certificate_versions '
                '(organization_id, tenant_id, worker_subject, certificate_sha256, '
                'expires_at) VALUES (%s, %s, %s, %s, %s)',
                (self.context.organization_id, self.context.tenant_id,
                 self.identity.subject, self.identity.certificate_sha256,
                 now + timedelta(hours=1)))
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
                 'DISCOVER_READ', 'vault:site-read'))
        self.lease = LockedTestLease()
        self.grants = PostgresWorkerGrants(
            lambda: self.psycopg.connect(self.runtime_dsn), self.lease)
        self.enrollment = PostgresWorkerEnrollment(
            lambda: self.psycopg.connect(self.enrollment_dsn),
            TestWorkerVerifier(), TestEnrollmentAuthorizer())

    def test_read_grant_requires_existing_job_approval_enrollment_and_b11_lease(self):
        request = replace(self.request, step_id='step-read',
                          operation_kind='DISCOVER_READ')
        grant = self.grants.issue_grant(self.context, self.identity, request)
        references = []
        self.grants.with_authorized_reference(
            self.context, self.identity, grant.grant_id,
            job_id=self.job_id, step_id=request.step_id,
            operation_id=request.operation_id, operation_kind='DISCOVER_READ',
            operation_scope=self.scope, lease_key='lease-01', lease_epoch=2,
            use=lambda reference, *_: references.append(reference))
        self.assertEqual(references, ['vault:site-read'])
        self.lease.epoch = 3
        with self.assertRaises(GrantDenied):
            self.grants.with_authorized_reference(
                self.context, self.identity, grant.grant_id,
                job_id=self.job_id, step_id=request.step_id,
                operation_id=request.operation_id, operation_kind='DISCOVER_READ',
                operation_scope=self.scope, lease_key='lease-01', lease_epoch=2,
                use=lambda *_: None)

    def test_certificate_rotation_invalidates_old_grant_and_revoke_blocks_new(self):
        old_grant = self.grants.issue_grant(self.context, self.identity, self.request)
        replacement = replace(self.identity, certificate_sha256=uuid4().hex + uuid4().hex)
        with self.assertRaises(GrantDenied):
            self.enrollment.enroll(replacement, self.context, 'unapproved')
        self.enrollment.enroll(replacement, self.context, 'approved-enrollment')
        with self.psycopg.connect(self.migration_dsn) as connection:
            self._tenant(connection)
            event = connection.execute(
                'SELECT actor_id, correlation_id, action, details '
                'FROM hosting_controlplane.audit_events '
                'WHERE organization_id = %s AND tenant_id = %s '
                "AND action = 'WORKER_CERT_ROTATE' AND record_id = %s",
                (self.context.organization_id, self.context.tenant_id,
                 replacement.certificate_sha256)).fetchone()
            self.assertEqual(event[0:3], ('site-security-admin',
                                          'corr-enrollment', 'WORKER_CERT_ROTATE'))
            self.assertEqual(event[3]['approval_id'], 'ticket-enrollment')
        with self.assertRaises(GrantDenied):
            self.grants.with_authorized_reference(
                self.context, self.identity, old_grant.grant_id,
                job_id=self.job_id, step_id='step-01', operation_id='operation-01',
                operation_kind='VM_POWER', operation_scope=self.scope,
                lease_key='lease-01', lease_epoch=2, use=lambda *_: None)
        renewed = self.grants.issue_grant(
            self.context, replacement, replace(self.request, step_id='step-02'))
        self.enrollment.revoke(self.context, 'approved-revocation',
                               worker_subject=replacement.subject,
                               certificate_sha256=replacement.certificate_sha256)
        with self.assertRaises(GrantDenied):
            self.grants.with_authorized_reference(
                self.context, replacement, renewed.grant_id,
                job_id=self.job_id, step_id='step-02', operation_id='operation-01',
                operation_kind='VM_POWER', operation_scope=self.scope,
                lease_key='lease-01', lease_epoch=2, use=lambda *_: None)

    def test_first_enrollment_needs_admin_approval_and_scope(self):
        new_identity = replace(self.identity, subject='new-worker-01',
                               certificate_sha256=uuid4().hex + uuid4().hex)
        cap = WorkerCapability(self.scope, 'VM_POWER', 'vault:site-power')
        with self.assertRaises(GrantDenied):
            self.enrollment.enroll(new_identity, self.context, 'unapproved',
                                   capabilities=(cap,))
        with self.assertRaises(GrantDenied):
            self.enrollment.enroll(replace(new_identity, site_id='wrong-site'),
                                   self.context, 'approved-enrollment', capabilities=(cap,))
        self.enrollment.enroll(new_identity, self.context, 'approved-enrollment',
                               capabilities=(cap,))
        with self.psycopg.connect(self.enrollment_dsn) as connection:
            self._tenant(connection)
            with self.assertRaises(self.psycopg.Error):
                connection.execute('INSERT INTO hosting_controlplane.worker_grants '
                                   '(organization_id) VALUES (%s)',
                                   (self.context.organization_id,))

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

    @unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_SITE_WORKER_DSN'),
                         'Requires a dedicated site PostgreSQL login')
    def test_bound_site_role_cannot_escape_tenant_or_site_with_forged_guc(self):
        from psycopg.conninfo import conninfo_to_dict

        site_dsn = os.environ['HOSTING_TEST_POSTGRES_SITE_WORKER_DSN']
        site_role = conninfo_to_dict(site_dsn)['user']
        site_connect = lambda: self.psycopg.connect(site_dsn)
        now = datetime.now(timezone.utc)
        binding = NativeBinding.from_record(
            self.workload['spec']['machines'][0]['bindings'][0]['binding'])
        other_binding = replace(binding, native_id='vm-unrelated-' + uuid4().hex[:12])
        other_lease = 'lease-unrelated-' + uuid4().hex[:12]
        other = deepcopy(self.plan)
        other['metadata']['planId'] = 'other-plan-' + uuid4().hex[:12]
        for item in (other['spec']['source'], other['spec']['destination']):
            item['locationId'] = 'site-unrelated'
        other['metadata']['planDigest'] = plan_digest(other)
        other_scope = PlanScope.from_record(other['spec']['source'])
        other_job = 'other-job-' + uuid4().hex[:12]
        foreign_workload = deepcopy(self.workload)
        foreign_workload['metadata']['tenantId'] = self.foreign.tenant_id
        foreign_workload['metadata']['workloadId'] = 'foreign-workload-' + uuid4().hex[:12]
        foreign_plan = deepcopy(self.plan)
        foreign_plan['metadata']['tenantId'] = self.foreign.tenant_id
        foreign_plan['metadata']['planId'] = 'foreign-plan-' + uuid4().hex[:12]
        foreign_plan['spec']['workloadId'] = foreign_workload['metadata']['workloadId']
        for item in (foreign_plan['spec']['source'], foreign_plan['spec']['destination']):
            item['tenantId'] = self.foreign.tenant_id
        foreign_plan['metadata']['planDigest'] = plan_digest(foreign_plan)
        foreign_job = 'foreign-job-' + uuid4().hex[:12]
        foreign_grant = 'foreign-grant-' + uuid4().hex[:12]
        with self.psycopg.connect(self.migration_dsn) as connection:
            self._tenant(connection)
            connection.execute(
                'INSERT INTO hosting_controlplane.native_ownership '
                '(platform_family, endpoint_id, native_scope_id, resource_kind, native_id, '
                'organization_id, tenant_id, security_domain_id, workload_id, worker_id, '
                'lease_epoch, lease_expires_at) VALUES '
                '(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (*binding.key(), self.context.organization_id, self.context.tenant_id,
                 self.scope.security_domain_id, self.workload['metadata']['workloadId'],
                 self.identity.subject, 2, now + timedelta(minutes=10)))
            connection.execute(
                'INSERT INTO hosting_controlplane.native_operation_leases '
                '(organization_id, tenant_id, lease_key, job_id, operation_id, '
                'platform_family, endpoint_id, native_scope_id, resource_kind, native_id, '
                'site_id, security_domain_id, worker_id, owner_epoch, expires_at) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (self.context.organization_id, self.context.tenant_id,
                 'lease-01', self.job_id, 'operation-01', *binding.key(),
                 self.scope.site_id, self.scope.security_domain_id,
                 self.identity.subject, 2, now + timedelta(minutes=5)))
            connection.execute(
                'INSERT INTO hosting_controlplane.enterprise_records '
                '(organization_id, tenant_id, record_kind, record_id, revision, '
                'record_json, record_digest) VALUES (%s, %s, %s, %s, 1, %s::jsonb, %s)',
                (self.context.organization_id, self.context.tenant_id,
                 'MigrationPlan', other['metadata']['planId'], json.dumps(other),
                 canonical_record_digest(other)))
            connection.execute(
                'INSERT INTO hosting_controlplane.audit_events '
                '(organization_id, tenant_id, actor_id, correlation_id, action, '
                'record_kind, record_id, revision, record_digest) VALUES '
                "(%s, %s, 'other-author', 'other-correlation', 'RECORD_CREATE', "
                "'MigrationPlan', %s, 1, %s)",
                (self.context.organization_id, self.context.tenant_id,
                 other['metadata']['planId'], canonical_record_digest(other)))
            connection.execute(
                'INSERT INTO hosting_controlplane.operation_jobs '
                '(organization_id, tenant_id, job_id, idempotency_key, plan_id, '
                'plan_revision, plan_digest, source_scope, destination_scope, '
                'actor_subject, approval_ids, revocation_epoch, status) VALUES '
                '(%s, %s, %s, %s, %s, 1, %s, %s::jsonb, %s::jsonb, '
                "%s, '[]'::jsonb, 0, 'STARTED')",
                (self.context.organization_id, self.context.tenant_id,
                 other_job, 'other-key-' + other_job, other['metadata']['planId'],
                 other['metadata']['planDigest'], json.dumps(other['spec']['source']),
                 json.dumps(other['spec']['destination']), 'other-operator'))
            connection.execute(
                'INSERT INTO hosting_controlplane.native_ownership '
                '(platform_family, endpoint_id, native_scope_id, resource_kind, native_id, '
                'organization_id, tenant_id, security_domain_id, workload_id, worker_id, '
                'lease_epoch, lease_expires_at) VALUES '
                '(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (*other_binding.key(), self.context.organization_id,
                 self.context.tenant_id, self.scope.security_domain_id,
                 self.workload['metadata']['workloadId'], 'other-worker', 1,
                 now + timedelta(minutes=10)))
            connection.execute(
                'INSERT INTO hosting_controlplane.native_operation_leases '
                '(organization_id, tenant_id, lease_key, job_id, operation_id, '
                'platform_family, endpoint_id, native_scope_id, resource_kind, native_id, '
                'site_id, security_domain_id, worker_id, owner_epoch, expires_at) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (self.context.organization_id, self.context.tenant_id,
                 other_lease, other_job, 'other-operation', *other_binding.key(),
                 'site-unrelated', self.scope.security_domain_id, 'other-worker',
                 1, now + timedelta(minutes=5)))
            connection.execute(
                'INSERT INTO hosting_controlplane.plan_approvals '
                '(approval_id, organization_id, tenant_id, plan_id, plan_revision, '
                'plan_digest, revocation_epoch, role, site_id, security_domain_id, '
                'endpoint_id, native_scope_id, platform_family, approver_subject, '
                'issued_at, expires_at) VALUES '
                '(%s, %s, %s, %s, 1, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                ('other-approval-' + other_job, self.context.organization_id,
                 self.context.tenant_id, other['metadata']['planId'],
                 other['metadata']['planDigest'], 'SOURCE_OWNER', other_scope.site_id,
                 other_scope.security_domain_id, other_scope.endpoint_id,
                 other_scope.native_scope_id, other_scope.platform_family,
                 'other-reviewer', now - timedelta(minutes=1),
                 now + timedelta(minutes=10)))
            connection.execute(
                "SELECT set_config('app.tenant_id', %s, true)",
                (self.foreign.tenant_id,))
            for record in (foreign_workload, foreign_plan):
                name = ('workloadId' if record['kind'] == 'Workload' else 'planId')
                connection.execute(
                    'INSERT INTO hosting_controlplane.enterprise_records '
                    '(organization_id, tenant_id, record_kind, record_id, revision, '
                    'record_json, record_digest) VALUES (%s, %s, %s, %s, 1, %s::jsonb, %s)',
                    (self.foreign.organization_id, self.foreign.tenant_id,
                     record['kind'], record['metadata'][name], json.dumps(record),
                     canonical_record_digest(record)))
            connection.execute(
                'INSERT INTO hosting_controlplane.operation_jobs '
                '(organization_id, tenant_id, job_id, idempotency_key, plan_id, '
                'plan_revision, plan_digest, source_scope, destination_scope, '
                'actor_subject, approval_ids, revocation_epoch, status) VALUES '
                '(%s, %s, %s, %s, %s, 1, %s, %s::jsonb, %s::jsonb, '
                "%s, '[]'::jsonb, 0, 'STARTED')",
                (self.foreign.organization_id, self.foreign.tenant_id,
                 foreign_job, 'key-' + foreign_job,
                 foreign_plan['metadata']['planId'], foreign_plan['metadata']['planDigest'],
                 json.dumps(foreign_plan['spec']['source']),
                 json.dumps(foreign_plan['spec']['destination']), 'foreign-operator'))
            connection.execute(
                'INSERT INTO hosting_controlplane.worker_enrollments '
                '(organization_id, tenant_id, worker_subject, site_id, '
                'certificate_sha256, expires_at) VALUES (%s, %s, %s, %s, %s, %s)',
                (self.foreign.organization_id, self.foreign.tenant_id,
                 'foreign-worker', self.scope.site_id, 'b' * 64,
                 now + timedelta(minutes=10)))
            connection.execute(
                'INSERT INTO hosting_controlplane.worker_grants '
                '(organization_id, tenant_id, grant_id, job_id, plan_id, '
                'plan_revision, plan_digest, approval_ids, revocation_epoch, '
                'worker_subject, certificate_sha256, step_id, operation_id, '
                'operation_kind, site_id, security_domain_id, endpoint_id, '
                'native_scope_id, platform_family, lease_key, lease_epoch, '
                'issued_at, expires_at) VALUES '
                '(%s, %s, %s, %s, %s, 1, %s, %s::jsonb, 0, %s, %s, %s, %s, '
                '%s, %s, %s, %s, %s, %s, %s, 2, %s, %s)',
                (self.foreign.organization_id, self.foreign.tenant_id,
                 foreign_grant, foreign_job, foreign_plan['metadata']['planId'],
                 foreign_plan['metadata']['planDigest'], '[]', 'foreign-worker',
                 'b' * 64, 'step-foreign', 'operation-foreign', 'DISCOVER_READ',
                 self.scope.site_id, self.scope.security_domain_id,
                 self.scope.endpoint_id, self.scope.native_scope_id,
                 self.scope.platform_family, 'lease-foreign', now,
                 now + timedelta(minutes=2)))
            connection.execute(
                'INSERT INTO hosting_controlplane.audit_events '
                '(organization_id, tenant_id, actor_id, correlation_id, action, '
                'record_kind, record_id, revision, record_digest) VALUES '
                "(%s, %s, 'foreign-actor', 'foreign-correlation', 'RECORD_CREATE', "
                "'Workload', 'foreign-marker', 1, %s)",
                (self.foreign.organization_id, self.foreign.tenant_id, 'a' * 64))

        read = replace(self.request, step_id='step-site-read',
                       operation_kind='DISCOVER_READ')
        grant = self.grants.issue_grant(self.context, self.identity, read)
        with site_connect() as connection:
            self._tenant(connection)
            self.assertEqual(connection.execute(
                'SELECT count(*) FROM hosting_controlplane.worker_grants '
                'WHERE grant_id = %s', (grant.grant_id,)).fetchone(), (0,))
        with self.psycopg.connect(self.migration_dsn) as connection:
            self._tenant(connection)
            connection.execute(
                'INSERT INTO hosting_controlplane.site_worker_role_bindings '
                '(role_name, organization_id, tenant_id, site_id) VALUES (%s, %s, %s, %s)',
                (site_role, self.context.organization_id,
                 self.context.tenant_id, self.scope.site_id))
        settings = SiteWorkerSettings(
            postgres_dsn=f'postgresql://{site_role}@db.example/control?'
                'sslmode=verify-full&connect_timeout=5&sslrootcert=/etc/db-ca.pem',
            postgres_role=site_role, site_id=self.scope.site_id,
            bind_ip='127.0.0.1', bind_port=8443,
            server_certificate=Path('/etc/site.pem'), server_key=Path('/etc/site.key'),
            trust_bundle=Path('/etc/site-ca.pem'), crl_bundle=Path('/etc/site.crl'),
            trust_domain='workers.example', vault_url='https://vault.example:8200',
            vault_ca=Path('/etc/vault-ca.pem'), vault_token_file=Path('/run/vault/token'),
            roles=(VaultDynamicRole('vault:site-read', 'platform/creds/site-read',
                                    self.scope, 'DISCOVER_READ', timedelta(minutes=2)),))
        _require_read_only_role(site_connect, settings)
        site_grants = PostgresWorkerGrants(site_connect, NativeLeaseAuthority(site_connect))
        references = []
        site_grants.with_authorized_reference(
            self.context, self.identity, grant.grant_id, job_id=self.job_id,
            step_id=read.step_id, operation_id=read.operation_id,
            operation_kind='DISCOVER_READ', operation_scope=self.scope,
            lease_key='lease-01', lease_epoch=2,
            use=lambda reference, *_: references.append(reference))
        self.assertEqual(references, ['vault:site-read'])

        with site_connect() as connection:
            self._tenant(connection)
            for table, column, marker in (
                    ('operation_jobs', 'job_id', other_job),
                    ('enterprise_records', 'record_id', other['metadata']['planId']),
                    ('audit_events', 'record_id', other['metadata']['planId']),
                    ('plan_approvals', 'approval_id', 'other-approval-' + other_job)):
                found = connection.execute(
                    f'SELECT count(*) FROM hosting_controlplane.{table} WHERE {column} = %s',
                    (marker,)).fetchone()[0]
                self.assertEqual(found, 0, table)
            connection.execute("SELECT set_config('app.tenant_id', %s, true)",
                               (self.foreign.tenant_id,))
            self.assertEqual(connection.execute(
                "SELECT count(*) FROM hosting_controlplane.audit_events "
                "WHERE record_id = 'foreign-marker'").fetchone(), (0,))
            self.assertEqual(connection.execute(
                'SELECT count(*) FROM hosting_controlplane.worker_grants '
                'WHERE grant_id = %s', (foreign_grant,)).fetchone(), (0,))

        with site_connect() as connection:
            self._tenant(connection)
            with self.assertRaises(self.psycopg.Error):
                connection.execute('SELECT hosting_controlplane.lock_job_scope(%s, %s, %s)',
                                   (self.context.organization_id,
                                    self.context.tenant_id, other_job))

        with site_connect() as connection:
            self._tenant(connection)
            with self.assertRaises(self.psycopg.Error):
                connection.execute(
                    'SELECT * FROM hosting_controlplane.lock_authority_scope(%s, %s, %s)',
                    (self.context.organization_id, self.context.tenant_id,
                     other['metadata']['planId'])).fetchall()

        worker_scope_sql = (
            'SELECT * FROM hosting_controlplane.lock_worker_scope('
            '%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)')
        worker_scope_args = (self.context.organization_id, self.context.tenant_id,
                             self.identity.subject, self.identity.certificate_sha256,
                             self.scope.site_id, self.scope.security_domain_id,
                             self.scope.endpoint_id, self.scope.native_scope_id,
                             self.scope.platform_family, 'DISCOVER_READ')
        for args in (worker_scope_args[:4] + ('site-unrelated',) + worker_scope_args[5:],
                     worker_scope_args[:-1] + ('VM_POWER',)):
            with site_connect() as connection:
                self._tenant(connection)
                with self.assertRaises(self.psycopg.Error):
                    connection.execute(worker_scope_sql, args).fetchall()

        with site_connect() as connection:
            self._tenant(connection)
            self.assertEqual(connection.execute(
                'SELECT * FROM hosting_controlplane.lock_native_worker_scope(%s, %s, %s)',
                (self.context.organization_id, self.context.tenant_id,
                 other_lease)).fetchall(), [])


if __name__ == '__main__':
    unittest.main()
