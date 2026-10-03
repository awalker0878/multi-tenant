"""Real database authority, plan-revision and revocation transaction tests."""
from __future__ import annotations

import os
import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from provisioner.controlplane.authority import (
    AuthorityDenied, AuthorityService, PlanScope, RoleGrant, VerifiedPrincipal)
from provisioner.controlplane.authority.postgres import (
    PostgresAuthority, revalidate_admission, revalidate_start)
from provisioner.controlplane.authority.service import (
    DESTINATION_OWNER, DESTINATION_SECURITY, EXECUTION_OPERATOR,
    SOURCE_OWNER, SOURCE_SECURITY)
from provisioner.controlplane.persistence import (
    AuditContext, EnterpriseRecordStore, TenantContext)
from provisioner.domain.enterprise_records import plan_digest
from tests.provisioning.schema.test_enterprise_records import plan, workload


class Provider:
    def __init__(self):
        self.identities = {}

    def authenticate(self, credential):
        return self.identities[credential]


class PostgresAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime_dsn = os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN')
        cls.authority_dsn = os.environ.get('HOSTING_TEST_POSTGRES_AUTHORITY_DSN')
        if not cls.runtime_dsn or not cls.authority_dsn:
            raise unittest.SkipTest('Set PostgreSQL runtime and authority DSNs')
        try:
            import psycopg
        except ImportError as exc:
            raise unittest.SkipTest('Install hosting-provisioner[controlplane]') from exc
        cls.psycopg = psycopg

    def setUp(self):
        suffix = uuid4().hex[:12]
        self.ctx = TenantContext('org-' + suffix, 'tenant-a')
        self.author_subject = 'https://idp.example.test/subjects/alice@example.test'
        self.audit = AuditContext(self.author_subject, 'test-' + suffix)
        self.store = EnterpriseRecordStore(lambda: self.psycopg.connect(self.runtime_dsn))
        self.authority = PostgresAuthority(lambda: self.psycopg.connect(self.authority_dsn))
        item = workload()
        item['metadata'].update(organizationId=self.ctx.organization_id,
                                tenantId=self.ctx.tenant_id)
        self.store.create(self.ctx, item, self.audit)
        planned = plan()
        planned['metadata'].update(organizationId=self.ctx.organization_id,
                                   tenantId=self.ctx.tenant_id)
        for scope in (planned['spec']['source'], planned['spec']['destination']):
            scope.update(organizationId=self.ctx.organization_id,
                         tenantId=self.ctx.tenant_id)
        planned['metadata']['planDigest'] = plan_digest(planned)
        self.store.create(self.ctx, planned, self.audit)
        self.workload = item
        self.plan = planned
        self.source = PlanScope.from_record(planned['spec']['source'])
        self.target = PlanScope.from_record(planned['spec']['destination'])
        self.identities = Provider()
        now = datetime.now(timezone.utc)
        self.now = now
        roles = ((SOURCE_OWNER, self.source),
                 (DESTINATION_OWNER, self.target),
                 (SOURCE_SECURITY, self.source),
                 (DESTINATION_SECURITY, self.target))
        for index, (role, scope) in enumerate(roles):
            self.identities.identities[f'reviewer-{index}'] = self._principal(
                f'reviewer-{index}', ((role, scope),))
        self.identities.identities['operator'] = self._principal(
            'operator', ((EXECUTION_OPERATOR, self.source),
                         (EXECUTION_OPERATOR, self.target)))
        self.service = AuthorityService(self.identities, self.authority,
                                        self.authority)
        self.roles = roles

    def _principal(self, subject, grants):
        return VerifiedPrincipal(
            subject, self.ctx.organization_id, self.ctx.tenant_id, 'HUMAN',
            self.now - timedelta(minutes=1), self.now + timedelta(hours=1),
            self.now,
            tuple(RoleGrant(role, scope, self.now + timedelta(hours=1))
                  for role, scope in grants))

    def _approve(self):
        for index, (role, _) in enumerate(self.roles):
            self.service.record_approval(f'reviewer-{index}', 'plan-01', role,
                                         ttl=timedelta(minutes=20),
                                         expected_revision=self.plan['metadata']['revision'],
                                         expected_digest=self.plan['metadata']['planDigest'])

    def _revalidate(self, decision, method=revalidate_admission):
        with self.psycopg.connect(self.runtime_dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('app.organization_id', %s, true), "
                    "set_config('app.tenant_id', %s, true)",
                    (self.ctx.organization_id, self.ctx.tenant_id))
                method(cursor, decision, datetime.now(timezone.utc))

    def test_approval_admission_revocation_and_plan_revision_are_transactional(self):
        self._approve()
        decision = self.service.authorize_submission('operator', 'plan-01')
        self._revalidate(decision)
        self._revalidate(decision, revalidate_start)
        with self.psycopg.connect(self.runtime_dsn) as connection:
            connection.execute(
                "SELECT set_config('app.organization_id', %s, true), "
                "set_config('app.tenant_id', %s, true)",
                (self.ctx.organization_id, self.ctx.tenant_id))
            with self.assertRaises(self.psycopg.Error):
                connection.execute(
                    'UPDATE hosting_controlplane.plan_authority_state '
                    'SET revocation_epoch = 999 WHERE plan_id = %s', ('plan-01',))
        self.service.revoke_approvals('reviewer-0', 'plan-01', 'change withdrawn')
        with self.assertRaises(AuthorityDenied):
            self._revalidate(decision)
        with self.assertRaises(AuthorityDenied):
            self._revalidate(decision, revalidate_start)
        self._approve()
        second = self.service.authorize_submission('operator', 'plan-01')
        self.assertEqual(decision.revocation_epoch + 1, second.revocation_epoch)
        self._revalidate(second)
        revised = deepcopy(self.plan)
        revised['metadata']['revision'] = 2
        revised['spec']['maxDowntimeSeconds'] += 1
        revised['metadata']['planDigest'] = plan_digest(revised)
        self.store.update(self.ctx, revised, 1, self.audit)
        with self.assertRaises(AuthorityDenied):
            self._revalidate(second, revalidate_start)
        with self.assertRaises(AuthorityDenied):
            self.service.authorize_submission('operator', 'plan-01')

    def test_wrong_tenant_and_forged_approval_id_fail(self):
        self._approve()
        decision = self.service.authorize_submission('operator', 'plan-01')
        with self.assertRaises(AuthorityDenied):
            self._revalidate(replace(decision, approval_ids=('forged',)))
        with self.assertRaises(AuthorityDenied):
            self._revalidate(replace(decision, tenant_id='foreign'))
        with self.assertRaises(AuthorityDenied):
            self._revalidate(replace(decision, source=replace(self.source,
                                                             site_id='other')))

    def test_raw_verified_subject_cannot_approve_or_execute_own_plan(self):
        self.identities.identities['author'] = self._principal(
            self.author_subject, ((SOURCE_OWNER, self.source),
                                  (EXECUTION_OPERATOR, self.source),
                                  (EXECUTION_OPERATOR, self.target)))
        with self.assertRaises(AuthorityDenied):
            self.service.record_approval('author', 'plan-01', SOURCE_OWNER,
                                         ttl=timedelta(minutes=5),
                                         expected_revision=self.plan['metadata']['revision'],
                                         expected_digest=self.plan['metadata']['planDigest'])
        self._approve()
        with self.assertRaises(AuthorityDenied):
            self.service.authorize_submission('author', 'plan-01')

    def test_workload_revision_drift_invalidates_unchanged_approved_plan(self):
        self._approve()
        decision = self.service.authorize_submission('operator', 'plan-01')
        changed = deepcopy(self.workload)
        changed['metadata']['revision'] = 2
        changed['spec']['name'] = 'inventory-review-changed'
        self.store.update(self.ctx, changed, 1, self.audit)
        with self.assertRaises(AuthorityDenied):
            self._revalidate(decision)
        with self.assertRaises(AuthorityDenied):
            self.service.authorize_submission('operator', 'plan-01')


if __name__ == '__main__':
    unittest.main()
