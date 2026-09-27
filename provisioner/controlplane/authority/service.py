"""Fail-closed authorization policy for enterprise migration control-plane work.

The identity provider must validate signature, issuer, audience, nonce/session,
subject status, role assignment and required authentication assurance against
enterprise SSO. The plan source and approval ledger are trusted server-side
ports, not request data. A deployment must provide those ports; this package
does not pretend to validate an SSO token or persist approvals on its own.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol
from uuid import uuid4

from .model import (ApprovalSnapshot, AuthorizedPlan, FrozenPlan, PlanApproval,
                    PlanScope, PortfolioScope, RoleGrant, VerifiedPrincipal,
                    WorkerGrant)

SOURCE_OWNER = 'SOURCE_OWNER'
DESTINATION_OWNER = 'DESTINATION_OWNER'
SOURCE_SECURITY = 'SOURCE_SECURITY'
DESTINATION_SECURITY = 'DESTINATION_SECURITY'
EXECUTION_OPERATOR = 'EXECUTION_OPERATOR'
WORKER = 'WORKER'
JOB_READER = 'JOB_READER'
WORKLOAD_READER = 'WORKLOAD_READER'
WORKLOAD_EDITOR = 'WORKLOAD_EDITOR'
INVENTORY_READER = 'INVENTORY_READER'
MAX_STEP_UP_AGE = timedelta(minutes=5)
MAX_APPROVAL_TTL = timedelta(hours=8)
MAX_ADMISSION_TTL = timedelta(seconds=30)
MAX_WORKER_GRANT_TTL = timedelta(minutes=5)


class AuthenticationFailed(PermissionError):
    """No valid independent enterprise identity was established."""


class AuthorityDenied(PermissionError):
    """Identity, scope, plan, approval or lease failed the authority policy."""


class IdentityProvider(Protocol):
    def authenticate(self, credential: object) -> VerifiedPrincipal:
        """Verify externally issued identity, role scopes and session assurance."""


class PlanSource(Protocol):
    def current(self, organization_id: str, tenant_id: str, plan_id: str) -> FrozenPlan:
        """Load the current persisted revision and server-owned author provenance."""


class ApprovalLedger(Protocol):
    """Durable, append-only authority ledger.

    The implementation MUST enforce current plan digest/revision, epoch, approval
    ID/actor uniqueness, and compare-and-swap within the same transaction as its
    append or revocation. B09 admission MUST recheck plan and epoch in its own
    transaction. A cached or client-supplied snapshot is insufficient.
    """

    def snapshot(self, plan: FrozenPlan) -> ApprovalSnapshot: ...

    def append_if_current(self, plan: FrozenPlan, approval: PlanApproval,
                          expected_epoch: int) -> None: ...

    def revoke_if_current(self, plan: FrozenPlan, expected_epoch: int,
                          actor_subject: str, reason: str) -> int: ...

    def worker_grant(self, grant_id: str) -> WorkerGrant: ...


@dataclass(frozen=True)
class LeaseState:
    """Read from the authoritative native-owner lease store, never the worker."""

    lease_key: str
    epoch: int
    owner_subject: str
    expires_at: datetime


class LeaseSource(Protocol):
    def current(self, lease_key: str) -> LeaseState: ...


def _now(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('The authority clock must be timezone-aware')
    return value


def _authenticated(principal: VerifiedPrincipal, at: datetime) -> None:
    if (principal.issued_at > at or at >= principal.expires_at
            or not principal.subject or not principal.organization_id or not principal.tenant_id):
        raise AuthenticationFailed('Identity session has expired or is not yet valid')


def require_scoped_role(principal: VerifiedPrincipal, role: str,
                        scope: PlanScope, at: datetime) -> RoleGrant:
    """Exact org, tenant, site, WSD, endpoint and native scope; no wildcards."""
    _authenticated(principal, at)
    if ((principal.organization_id, principal.tenant_id) !=
            (scope.organization_id, scope.tenant_id)):
        raise AuthorityDenied('Identity lies outside this tenant')
    for grant in principal.grants:
        if grant.role == role and grant.scope == scope and grant.expires_at > at:
            return grant
    raise AuthorityDenied('Required role is missing for the exact native scope')


def require_workload_role(principal: VerifiedPrincipal, role: str,
                          scope: PortfolioScope, at: datetime) -> RoleGrant:
    """Require exact tenant/WSD authority for pre-placement workload records.

    The API must require a WSD filter when listing; a tenant-wide read cannot
    be authorized by one WSD-scoped role. Updates must authorize both the old
    persisted WSD and the new WSD if membership is changing.
    """
    _authenticated(principal, at)
    if role not in (WORKLOAD_READER, WORKLOAD_EDITOR, INVENTORY_READER):
        raise AuthorityDenied('Unknown portfolio role')
    if ((principal.organization_id, principal.tenant_id) !=
            (scope.organization_id, scope.tenant_id)):
        raise AuthorityDenied('Identity lies outside this tenant')
    for grant in principal.grants:
        if grant.role == role and grant.scope == scope and grant.expires_at > at:
            return grant
    raise AuthorityDenied('Required role is missing for the exact workload WSD')


def require_portfolio_role(principal: VerifiedPrincipal, role: str,
                           scope: PortfolioScope, at: datetime) -> RoleGrant:
    """Alias for API terminology; same exact WSD check."""
    return require_workload_role(principal, role, scope, at)


def _requirements(plan: FrozenPlan) -> tuple[tuple[str, PlanScope], ...]:
    return ((SOURCE_OWNER, plan.source), (DESTINATION_OWNER, plan.destination),
            (SOURCE_SECURITY, plan.source), (DESTINATION_SECURITY, plan.destination))


def _snapshot(plan: FrozenPlan, snapshot: ApprovalSnapshot) -> None:
    if (not isinstance(snapshot, ApprovalSnapshot)
            or (snapshot.organization_id, snapshot.tenant_id, snapshot.plan_id,
                snapshot.plan_revision, snapshot.plan_digest) !=
            (plan.organization_id, plan.tenant_id, plan.plan_id,
             plan.revision, plan.digest)
            or type(snapshot.revocation_epoch) is not int
            or snapshot.revocation_epoch < 0):
        raise AuthorityDenied('Authority snapshot is not the current exact plan')


def _valid_approvals(plan: FrozenPlan, snapshot: ApprovalSnapshot,
                     at: datetime) -> tuple[PlanApproval, ...]:
    _snapshot(plan, snapshot)
    by_requirement: dict[tuple[str, PlanScope], PlanApproval] = {}
    subjects = {plan.author_subject}
    ids: set[str] = set()
    for approval in snapshot.approvals:
        if not isinstance(approval, PlanApproval):
            raise AuthorityDenied('Authority ledger returned an invalid approval')
        if approval.revocation_epoch != snapshot.revocation_epoch:
            continue  # A prior epoch was revoked; it grants nothing.
        requirement = (approval.role, approval.scope)
        if (requirement not in _requirements(plan)
                or (approval.organization_id, approval.tenant_id, approval.plan_id,
                    approval.plan_revision, approval.plan_digest) !=
                (plan.organization_id, plan.tenant_id, plan.plan_id,
                 plan.revision, plan.digest)
                or not approval.approval_id or approval.approval_id in ids
                or not approval.approver_subject or approval.approver_subject in subjects
                or approval.issued_at > at or approval.expires_at <= at
                or requirement in by_requirement):
            raise AuthorityDenied('Approval quorum is stale, duplicated or out of scope')
        ids.add(approval.approval_id)
        subjects.add(approval.approver_subject)
        by_requirement[requirement] = approval
    if set(by_requirement) != set(_requirements(plan)):
        raise AuthorityDenied('Source, destination and security approvals are required')
    return tuple(by_requirement[item] for item in _requirements(plan))


class AuthorityService:
    """Server-side authority entrypoint. No request may supply a principal or approval."""

    def __init__(self, identities: IdentityProvider, plans: PlanSource,
                 ledger: ApprovalLedger, *, clock: Callable[[], datetime] | None = None,
                 leases: LeaseSource | None = None) -> None:
        self._identities = identities
        self._plans = plans
        self._ledger = ledger
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._leases = leases

    def authenticate(self, credential: object) -> VerifiedPrincipal:
        """Only an injected enterprise verifier can establish identity."""
        try:
            principal = self._identities.authenticate(credential)
            if not isinstance(principal, VerifiedPrincipal):
                raise TypeError('Verifier did not return a verified principal')
            _authenticated(principal, _now(self._clock))
            return principal
        except (AuthenticationFailed, AuthorityDenied):
            raise
        except Exception as exc:
            raise AuthenticationFailed('Independent identity verification failed') from exc

    def _plan(self, principal: VerifiedPrincipal, plan_id: str) -> FrozenPlan:
        if not isinstance(plan_id, str) or not plan_id:
            raise AuthorityDenied('Plan identity is required')
        try:
            plan = self._plans.current(principal.organization_id, principal.tenant_id,
                                       plan_id)
        except Exception as exc:
            raise AuthorityDenied('Current plan cannot be verified') from exc
        if (not isinstance(plan, FrozenPlan)
                or (plan.organization_id, plan.tenant_id, plan.plan_id) !=
                (principal.organization_id, principal.tenant_id, plan_id)):
            raise AuthorityDenied('Plan lies outside the verified tenant')
        return plan

    def record_approval(self, credential: object, plan_id: str, role: str,
                        *, ttl: timedelta) -> PlanApproval:
        principal = self.authenticate(credential)
        at = _now(self._clock)
        if principal.kind != 'HUMAN' or principal.step_up_at is None or not (
                at - MAX_STEP_UP_AGE <= principal.step_up_at <= at):
            raise AuthorityDenied('A recent independent human step-up is required')
        if not isinstance(ttl, timedelta) or not (timedelta(0) < ttl <= MAX_APPROVAL_TTL):
            raise AuthorityDenied('Approval lifetime is out of bounds')
        plan = self._plan(principal, plan_id)
        if principal.subject == plan.author_subject:
            raise AuthorityDenied('Plan author cannot approve this revision')
        required = dict(_requirements(plan))
        if role not in required:
            raise AuthorityDenied('Approval role is not in this plan policy')
        grant = require_scoped_role(principal, role, required[role], at)
        snapshot = self._ledger.snapshot(plan)
        _snapshot(plan, snapshot)
        if any(a.revocation_epoch == snapshot.revocation_epoch and
               (a.approver_subject == principal.subject or a.role == role)
               for a in snapshot.approvals):
            raise AuthorityDenied('Approver and role must each be distinct')
        approval = PlanApproval(
            approval_id=str(uuid4()), organization_id=plan.organization_id,
            tenant_id=plan.tenant_id, plan_id=plan.plan_id,
            plan_revision=plan.revision, plan_digest=plan.digest,
            role=role, scope=required[role], approver_subject=principal.subject,
            issued_at=at, expires_at=min(at + ttl, grant.expires_at),
            revocation_epoch=snapshot.revocation_epoch)
        if approval.expires_at <= at:
            raise AuthorityDenied('Scoped authority has expired')
        self._ledger.append_if_current(plan, approval, snapshot.revocation_epoch)
        return approval

    def authorize_submission(self, credential: object, plan_id: str) -> AuthorizedPlan:
        """Admission hint; B09 must compare exact plan and epoch atomically."""
        principal = self.authenticate(credential)
        at = _now(self._clock)
        if principal.kind != 'HUMAN':
            raise AuthorityDenied('A human execution operator must submit this job')
        plan = self._plan(principal, plan_id)
        if principal.subject == plan.author_subject:
            raise AuthorityDenied('Plan author cannot execute this revision')
        source_grant = require_scoped_role(principal, EXECUTION_OPERATOR, plan.source, at)
        target_grant = require_scoped_role(principal, EXECUTION_OPERATOR, plan.destination, at)
        snapshot = self._ledger.snapshot(plan)
        approvals = _valid_approvals(plan, snapshot, at)
        if principal.subject in {a.approver_subject for a in approvals}:
            raise AuthorityDenied('Approver cannot execute this revision')
        expires = min(at + MAX_ADMISSION_TTL, principal.expires_at,
                      source_grant.expires_at, target_grant.expires_at,
                      *(a.expires_at for a in approvals))
        return AuthorizedPlan(plan.organization_id, plan.tenant_id, plan.plan_id,
                              plan.revision, plan.digest, plan.source, plan.destination,
                              tuple(a.approval_id for a in approvals),
                              snapshot.revocation_epoch,
                              expires, principal.subject)

    def revoke_approvals(self, credential: object, plan_id: str, reason: str) -> int:
        """An owner or security reviewer may invalidate every current approval."""
        principal = self.authenticate(credential)
        at = _now(self._clock)
        plan = self._plan(principal, plan_id)
        if (principal.kind != 'HUMAN' or principal.step_up_at is None
                or not (at - MAX_STEP_UP_AGE <= principal.step_up_at <= at)
                or not isinstance(reason, str) or not reason.strip()):
            raise AuthorityDenied('Recent human step-up and reason are required')
        permitted = any(
            any(g.role == role and g.scope == scope and g.expires_at > at
                for g in principal.grants)
            for role, scope in _requirements(plan))
        if not permitted:
            raise AuthorityDenied('No revocation authority for either plan scope')
        snapshot = self._ledger.snapshot(plan)
        _snapshot(plan, snapshot)
        next_epoch = self._ledger.revoke_if_current(
            plan, snapshot.revocation_epoch, principal.subject, reason.strip())
        if type(next_epoch) is not int or next_epoch <= snapshot.revocation_epoch:
            raise AuthorityDenied('Revocation epoch did not advance')
        return next_epoch

    def require_worker_step(self, credential: object, grant_id: str, *, step_id: str,
                            operation_id: str, operation_kind: str,
                            operation_scope: PlanScope) -> WorkerGrant:
        """Revalidate current grant, plan, approvals and owner lease before a step.

        B10 must supply enrolled worker identities, a durable grant ledger and a
        fenced lease source. This method refuses when any of them is missing.
        """
        worker = self.authenticate(credential)
        at = _now(self._clock)
        if worker.kind != 'WORKER' or self._leases is None:
            raise AuthorityDenied('Enrolled worker and authoritative lease are required')
        grant = self._ledger.worker_grant(grant_id)
        if not isinstance(grant, WorkerGrant):
            raise AuthorityDenied('Worker grant is not authoritative')
        plan = self._plan(worker, grant.plan_id)
        snapshot = self._ledger.snapshot(plan)
        approvals = _valid_approvals(plan, snapshot, at)
        if (grant.organization_id, grant.tenant_id, grant.plan_id,
            grant.plan_revision, grant.plan_digest, grant.source, grant.destination) != (
                plan.organization_id, plan.tenant_id, plan.plan_id,
                plan.revision, plan.digest, plan.source, plan.destination):
            raise AuthorityDenied('Grant names another plan revision or native scopes')
        if (grant.revocation_epoch != snapshot.revocation_epoch
                or tuple(a.approval_id for a in approvals) != grant.approval_ids
                or grant.worker_subject != worker.subject
                or (grant.step_id, grant.operation_id, grant.operation_kind,
                    grant.operation_scope) != (step_id, operation_id,
                                               operation_kind, operation_scope)
                or grant.operation_scope not in (plan.source, plan.destination)
                or grant.issued_at > at or grant.expires_at <= at
                or grant.expires_at - grant.issued_at > MAX_WORKER_GRANT_TTL):
            raise AuthorityDenied('Grant is expired, revoked or for another operation')
        require_scoped_role(worker, WORKER, grant.operation_scope, at)
        lease = self._leases.current(grant.lease_key)
        if (not isinstance(lease, LeaseState)
                or (lease.lease_key, lease.epoch, lease.owner_subject) !=
                (grant.lease_key, grant.lease_epoch, worker.subject)
                or lease.expires_at <= at):
            raise AuthorityDenied('Owner lease is stale or held by another worker')
        return grant
