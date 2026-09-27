"""Authorizations must bind the exact tenant, site, WSD and plan revision."""
from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from provisioner.controlplane.authority import (
    ApprovalSnapshot, AuthorityDenied, AuthorityService, AuthenticationFailed,
    FrozenPlan, PlanScope, PortfolioScope, RoleGrant, VerifiedPrincipal,
    WorkerGrant, require_workload_role)
from provisioner.controlplane.authority.service import (
    DESTINATION_OWNER, DESTINATION_SECURITY, EXECUTION_OPERATOR,
    SOURCE_OWNER, SOURCE_SECURITY, WORKER, WORKLOAD_EDITOR, LeaseState)

NOW = datetime(2026, 9, 27, 1, 30, tzinfo=timezone.utc)
SOURCE = PlanScope('org', 'tenant', 'site-a', 'wsd-a', 'vc-a', 'cluster-a', 'vmware')
TARGET = PlanScope('org', 'tenant', 'site-b', 'wsd-b', 'ahv-b', 'cluster-b', 'nutanix')
PLAN = FrozenPlan('org', 'tenant', 'plan-1', 1, 'a' * 64, 'author', SOURCE, TARGET)


class Provider:
    def __init__(self):
        self.identities = {}

    def authenticate(self, credential):
        if not isinstance(credential, str) or credential not in self.identities:
            raise ValueError('Unknown bearer')
        return self.identities[credential]


class Plans:
    def __init__(self):
        self.plan = PLAN

    def current(self, organization_id, tenant_id, plan_id):
        if (organization_id, tenant_id, plan_id) != ('org', 'tenant', 'plan-1'):
            raise LookupError('Tenant-scoped plan not found')
        return self.plan


class Ledger:
    def __init__(self):
        self.epoch = 0
        self.approvals = []
        self.grants = {}

    def snapshot(self, plan):
        return ApprovalSnapshot(plan.organization_id, plan.tenant_id,
                                plan.plan_id, plan.revision, plan.digest,
                                self.epoch, tuple(self.approvals))

    def append_if_current(self, plan, approval, expected_epoch):
        if self.epoch != expected_epoch:
            raise AuthorityDenied('Concurrent revocation')
        if any(a.revocation_epoch == self.epoch and
               (a.role == approval.role or a.approver_subject == approval.approver_subject)
               for a in self.approvals):
            raise AuthorityDenied('Concurrent duplicate')
        self.approvals.append(approval)

    def revoke_if_current(self, plan, expected_epoch, actor_subject, reason):
        if self.epoch != expected_epoch:
            raise AuthorityDenied('Concurrent revocation')
        self.epoch += 1
        return self.epoch

    def worker_grant(self, grant_id):
        return self.grants.get(grant_id)


class Leases:
    def __init__(self):
        self.lease = LeaseState('binding:vm-1', 7, 'worker', NOW + timedelta(minutes=5))

    def current(self, lease_key):
        return self.lease


def identity(subject, grants, *, tenant='tenant', kind='HUMAN',
             step_up=NOW, expires=NOW + timedelta(hours=1)):
    return VerifiedPrincipal(subject, 'org', tenant, kind,
                             NOW - timedelta(minutes=1), expires, step_up,
                             tuple(RoleGrant(role, scope, expires) for role, scope in grants))


class AuthorityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.now = NOW
        self.provider = Provider()
        self.plans = Plans()
        self.ledger = Ledger()
        self.leases = Leases()
        self.service = AuthorityService(self.provider, self.plans, self.ledger,
                                        clock=lambda: self.now, leases=self.leases)
        self.roles = ((SOURCE_OWNER, SOURCE), (DESTINATION_OWNER, TARGET),
                      (SOURCE_SECURITY, SOURCE), (DESTINATION_SECURITY, TARGET))
        self.provider.identities['author'] = identity('author', self.roles)
        for index, role in enumerate(self.roles):
            self.provider.identities[f'reviewer-{index}'] = identity(
                f'reviewer-{index}', (role,))
        self.provider.identities['operator'] = identity(
            'operator', ((EXECUTION_OPERATOR, SOURCE),
                         (EXECUTION_OPERATOR, TARGET)))

    def approve_all(self):
        for index, (role, _) in enumerate(self.roles):
            self.service.record_approval(f'reviewer-{index}', 'plan-1',
                                         role, ttl=timedelta(minutes=20),
                                         expected_revision=PLAN.revision,
                                         expected_digest=PLAN.digest)

    def test_independent_quorum_and_exact_plan_admit(self):
        self.approve_all()
        decision = self.service.authorize_submission('operator', 'plan-1')
        self.assertEqual(4, len(decision.approval_ids))
        self.assertEqual((PLAN.revision, PLAN.digest, SOURCE, TARGET, 0),
                         (decision.plan_revision, decision.plan_digest,
                          decision.source, decision.destination,
                          decision.revocation_epoch))
        self.assertLessEqual(decision.expires_at, NOW + timedelta(seconds=30))

    def test_plan_review_requires_scoped_reviewer_and_approval_selected_binding(self):
        self.assertEqual(self.service.review_plan('reviewer-0', 'plan-1'), PLAN)
        with self.assertRaises(AuthorityDenied):
            self.service.review_plan('operator', 'plan-1')
        self.plans.plan = replace(PLAN, revision=2, digest='b' * 64)
        with self.assertRaises(AuthorityDenied):
            self.service.record_approval(
                'reviewer-0', 'plan-1', SOURCE_OWNER,
                ttl=timedelta(minutes=5), expected_revision=PLAN.revision,
                expected_digest=PLAN.digest)

    def test_forged_client_approval_or_identity_is_never_a_credential(self):
        with self.assertRaises(AuthenticationFailed):
            self.service.authorize_submission({'approved_by': 'reviewer-0'}, 'plan-1')
        with self.assertRaises(AuthenticationFailed):
            self.service.record_approval({'role': SOURCE_OWNER}, 'plan-1',
                                         SOURCE_OWNER, ttl=timedelta(minutes=5),
                                         expected_revision=PLAN.revision,
                                         expected_digest=PLAN.digest)

    def test_no_self_approval_or_self_execution(self):
        with self.assertRaises(AuthorityDenied):
            self.service.record_approval('author', 'plan-1', SOURCE_OWNER,
                                         ttl=timedelta(minutes=5),
                                         expected_revision=PLAN.revision,
                                         expected_digest=PLAN.digest)
        self.approve_all()
        self.provider.identities['author'] = identity(
            'author', ((EXECUTION_OPERATOR, SOURCE),
                       (EXECUTION_OPERATOR, TARGET)))
        with self.assertRaises(AuthorityDenied):
            self.service.authorize_submission('author', 'plan-1')
        self.provider.identities['reviewer-0'] = identity(
            'reviewer-0', ((EXECUTION_OPERATOR, SOURCE),
                           (EXECUTION_OPERATOR, TARGET)))
        with self.assertRaises(AuthorityDenied):
            self.service.authorize_submission('reviewer-0', 'plan-1')

    def test_wrong_tenant_site_wsd_or_endpoint_cannot_approve(self):
        with self.assertRaises(ValueError):
            identity('reviewer-0', ((SOURCE_OWNER,
                                     replace(SOURCE, tenant_id='other')),))
        for wrong_scope in (replace(SOURCE, site_id='site-x'),
                            replace(SOURCE, security_domain_id='wsd-x'),
                            replace(SOURCE, endpoint_id='vc-x'),
                            replace(SOURCE, platform_family='openstack')):
            self.provider.identities['reviewer-0'] = identity(
                'reviewer-0', ((SOURCE_OWNER, wrong_scope),))
            with self.subTest(scope=wrong_scope), self.assertRaises(AuthorityDenied):
                self.service.record_approval('reviewer-0', 'plan-1', SOURCE_OWNER,
                                             ttl=timedelta(minutes=5),
                                             expected_revision=PLAN.revision,
                                             expected_digest=PLAN.digest)

    def test_duplicate_actor_and_wrong_execution_scope_fail(self):
        self.service.record_approval('reviewer-0', 'plan-1', SOURCE_OWNER,
                                     ttl=timedelta(minutes=5),
                                     expected_revision=PLAN.revision,
                                     expected_digest=PLAN.digest)
        self.provider.identities['reviewer-0'] = identity(
            'reviewer-0', ((DESTINATION_OWNER, TARGET),))
        with self.assertRaises(AuthorityDenied):
            self.service.record_approval('reviewer-0', 'plan-1', DESTINATION_OWNER,
                                         ttl=timedelta(minutes=5),
                                         expected_revision=PLAN.revision,
                                         expected_digest=PLAN.digest)
        self.provider.identities['operator'] = identity(
            'operator', ((EXECUTION_OPERATOR, SOURCE),))
        with self.assertRaises(AuthorityDenied):
            self.service.authorize_submission('operator', 'plan-1')

    def test_expiry_step_up_and_epoch_revocation_fail_closed(self):
        self.provider.identities['reviewer-0'] = identity(
            'reviewer-0', ((SOURCE_OWNER, SOURCE),),
            step_up=NOW - timedelta(minutes=6))
        with self.assertRaises(AuthorityDenied):
            self.service.record_approval('reviewer-0', 'plan-1', SOURCE_OWNER,
                                         ttl=timedelta(minutes=5),
                                         expected_revision=PLAN.revision,
                                         expected_digest=PLAN.digest)
        self.provider.identities['reviewer-0'] = identity(
            'reviewer-0', ((SOURCE_OWNER, SOURCE),))
        self.approve_all()
        self.now += timedelta(minutes=21)
        with self.assertRaises(AuthorityDenied):
            self.service.authorize_submission('operator', 'plan-1')
        self.now = NOW
        self.assertEqual(1, self.service.revoke_approvals('reviewer-0', 'plan-1',
                                                          'review withdrawn'))
        with self.assertRaises(AuthorityDenied):
            self.service.authorize_submission('operator', 'plan-1')

    def test_plan_revision_change_invalidates_approval_quorum(self):
        self.approve_all()
        self.plans.plan = replace(PLAN, revision=2, digest='b' * 64)
        with self.assertRaises(AuthorityDenied):
            self.service.authorize_submission('operator', 'plan-1')

    def test_portfolio_roles_are_exact_wsd_scopes(self):
        scope = PortfolioScope('org', 'tenant', 'wsd-a')
        principal = identity('editor', ((WORKLOAD_EDITOR, scope),))
        require_workload_role(principal, WORKLOAD_EDITOR, scope, NOW)
        with self.assertRaises(AuthorityDenied):
            require_workload_role(principal, WORKLOAD_EDITOR,
                                  PortfolioScope('org', 'tenant', 'wsd-b'), NOW)
        with self.assertRaises(AuthorityDenied):
            require_workload_role(principal, WORKLOAD_EDITOR,
                                  PortfolioScope('org', 'other', 'wsd-a'), NOW)

    def test_worker_grant_requires_current_epoch_operation_and_lease(self):
        self.approve_all()
        decision = self.service.authorize_submission('operator', 'plan-1')
        self.provider.identities['worker'] = identity(
            'worker', ((WORKER, TARGET),), kind='WORKER', step_up=None)
        grant = WorkerGrant('grant-1', 'org', 'tenant', 'plan-1', 1, PLAN.digest,
                            SOURCE, TARGET, 'worker', 'step-1', 'op-1', 'RESTORE',
                            TARGET, 'binding:vm-1', 7, decision.approval_ids, 0,
                            NOW, NOW + timedelta(minutes=2))
        self.ledger.grants['grant-1'] = grant
        self.service.require_worker_step('worker', 'grant-1', step_id='step-1',
                                         operation_id='op-1', operation_kind='RESTORE',
                                         operation_scope=TARGET)
        with self.assertRaises(AuthorityDenied):
            self.service.require_worker_step('worker', 'grant-1', step_id='step-1',
                                             operation_id='op-2', operation_kind='RESTORE',
                                             operation_scope=TARGET)
        self.leases.lease = replace(self.leases.lease, epoch=8)
        with self.assertRaises(AuthorityDenied):
            self.service.require_worker_step('worker', 'grant-1', step_id='step-1',
                                             operation_id='op-1', operation_kind='RESTORE',
                                             operation_scope=TARGET)
        self.leases.lease = replace(self.leases.lease, epoch=7)
        self.ledger.epoch = 1
        with self.assertRaises(AuthorityDenied):
            self.service.require_worker_step('worker', 'grant-1', step_id='step-1',
                                             operation_id='op-1', operation_kind='RESTORE',
                                             operation_scope=TARGET)


if __name__ == '__main__':
    unittest.main()
