"""PostgreSQL authority ledger and transactional job-admission rechecks.

Migrations/0003_authority.sql is required. The connection factory must use a
non-superuser, non-BYPASSRLS role. Approval writes need a dedicated authority
writer credential; HTTP and worker roles receive read-only authority access.
Every operation uses tenant RLS context. Admission/start methods use the caller's
cursor and transaction to serialize with plan edits and revocation.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Callable

from provisioner.domain.enterprise_records import validate_record

from .model import (ApprovalSnapshot, AuthorizedPlan, FrozenPlan, PlanApproval,
                    PlanScope, WorkerGrant)
from .service import AuthorityDenied, _valid_approvals


def _json(value):
    return json.loads(value) if isinstance(value, str) else value


def _tenant(cursor, organization_id: str, tenant_id: str) -> None:
    if not organization_id or not tenant_id:
        raise AuthorityDenied('Verified tenant context is required')
    cursor.execute(
        "SELECT set_config('app.organization_id', %s, true), "
        "set_config('app.tenant_id', %s, true)",
        (organization_id, tenant_id))


def _runtime_role(cursor) -> None:
    cursor.execute('SELECT rolsuper, rolbypassrls FROM pg_catalog.pg_roles '
                   'WHERE rolname = current_user')
    role = cursor.fetchone()
    if role is None or role[0] or role[1]:
        raise RuntimeError('Authority runtime role must enforce PostgreSQL RLS')


def _locked_plan(cursor, organization_id: str, tenant_id: str,
                 plan_id: str, *, write_epoch: bool = False) -> tuple[FrozenPlan, int]:
    """Lock the authority epoch, then verify current plan and workload.

    Read transactions use a narrowly granted SECURITY DEFINER lock function;
    writer transactions take FOR UPDATE on the mutable epoch row directly.
    Approvals are append-only and need no row-level lock. Plan edits update the
    state row in their trigger; workload reads are locked by the definer helper.
    """
    if write_epoch:
        cursor.execute(
            'SELECT plan_revision, plan_digest, revocation_epoch '
            'FROM hosting_controlplane.plan_authority_state '
            'WHERE organization_id = %s AND tenant_id = %s AND plan_id = %s '
            'FOR UPDATE',
            (organization_id, tenant_id, plan_id))
    else:
        cursor.execute(
            'SELECT plan_revision, plan_digest, revocation_epoch '
            'FROM hosting_controlplane.lock_authority_scope(%s, %s, %s)',
            (organization_id, tenant_id, plan_id))
    state = cursor.fetchone()
    if state is None:
        raise AuthorityDenied('Current authority state is unavailable')
    state_revision, state_digest, epoch = state
    cursor.execute(
        'SELECT revision, record_json, record_digest '
        'FROM hosting_controlplane.enterprise_records '
        'WHERE organization_id = %s AND tenant_id = %s '
        "AND record_kind = 'MigrationPlan' AND record_id = %s",
        (organization_id, tenant_id, plan_id))
    row = cursor.fetchone()
    if row is None:
        raise AuthorityDenied('Current plan and revocation state are unavailable')
    revision, raw, record_digest = row
    record = _json(raw)
    try:
        canonical = json.dumps(record, sort_keys=True, separators=(',', ':'),
                               ensure_ascii=False, allow_nan=False).encode('utf-8')
        if (not isinstance(record, dict) or validate_record(record)
                or hashlib.sha256(canonical).hexdigest() != record_digest
                or revision != state_revision
                or record['metadata']['planDigest'] != state_digest):
            raise AuthorityDenied('Persisted plan and authority state disagree')
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthorityDenied('Persisted plan is invalid') from exc
    # The plan digest binds the selected workload revision, but an unchanged
    # plan must not remain actionable after that workload advances. Lock the
    # current workload in the same transaction and revalidate source bindings,
    # WSD membership and every selected machine/dataset mapping.
    try:
        workload_id = record['spec']['workloadId']
        workload_revision = record['spec']['workloadRevision']
    except (KeyError, TypeError) as exc:
        raise AuthorityDenied('Plan lacks a bound workload revision') from exc
    cursor.execute(
        'SELECT revision, record_json, record_digest '
        'FROM hosting_controlplane.enterprise_records '
        'WHERE organization_id = %s AND tenant_id = %s '
        "AND record_kind = 'Workload' AND record_id = %s",
        (organization_id, tenant_id, workload_id))
    workload_row = cursor.fetchone()
    if workload_row is None:
        raise AuthorityDenied('Bound workload is unavailable')
    current_revision, workload_raw, workload_digest = workload_row
    workload = _json(workload_raw)
    try:
        canonical_workload = json.dumps(
            workload, sort_keys=True, separators=(',', ':'),
            ensure_ascii=False, allow_nan=False).encode('utf-8')
        if (current_revision != workload_revision
                or hashlib.sha256(canonical_workload).hexdigest() != workload_digest
                or validate_record(workload)
                or validate_record(record, workload=workload)):
            raise AuthorityDenied('Bound workload revision or mapping changed')
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthorityDenied('Bound workload cannot be verified') from exc
    cursor.execute(
        'SELECT actor_id FROM hosting_controlplane.audit_events '
        'WHERE organization_id = %s AND tenant_id = %s '
        "AND action = 'RECORD_CREATE' AND record_kind = 'MigrationPlan' "
        'AND record_id = %s ORDER BY event_id LIMIT 1',
        (organization_id, tenant_id, plan_id))
    author = cursor.fetchone()
    if author is None:
        raise AuthorityDenied('Author provenance for the plan is missing')
    try:
        plan = FrozenPlan.from_record(record, author_subject=author[0])
    except (ValueError, KeyError, TypeError) as exc:
        raise AuthorityDenied('Current plan cannot be bound') from exc
    if (plan.organization_id, plan.tenant_id, plan.plan_id) != (
            organization_id, tenant_id, plan_id):
        raise AuthorityDenied('Plan is outside the verified tenant')
    return plan, epoch


def _approval_snapshot(cursor, plan: FrozenPlan, epoch: int) -> ApprovalSnapshot:
    cursor.execute(
        'SELECT approval_id, plan_revision, plan_digest, role, site_id, '
        'security_domain_id, endpoint_id, native_scope_id, platform_family, '
        'approver_subject, issued_at, expires_at, revocation_epoch '
        'FROM hosting_controlplane.plan_approvals '
        'WHERE organization_id = %s AND tenant_id = %s AND plan_id = %s '
        'AND revocation_epoch = %s ORDER BY role',
        (plan.organization_id, plan.tenant_id, plan.plan_id, epoch))
    approvals = []
    for row in cursor.fetchall():
        (approval_id, revision, digest, role, site, wsd, endpoint, native, family,
         actor, issued, expires, approval_epoch) = row
        scope = PlanScope(plan.organization_id, plan.tenant_id, site, wsd,
                          endpoint, native, family)
        approvals.append(PlanApproval(
            approval_id, plan.organization_id, plan.tenant_id, plan.plan_id,
            revision, digest, role, scope, actor, issued, expires, approval_epoch))
    return ApprovalSnapshot(plan.organization_id, plan.tenant_id, plan.plan_id,
                            plan.revision, plan.digest, epoch, tuple(approvals))


def _revalidate(cursor, decision, at: datetime) -> None:
    if (not isinstance(at, datetime) or at.tzinfo is None
            or at.utcoffset() is None
            or not isinstance(decision.approval_ids, tuple)):
        raise AuthorityDenied('Current authority proof is required')
    # JobRepository already sets tenant RLS inside this transaction. Check the
    # GUC as a defense against calling this helper with a different tenant.
    cursor.execute("SELECT current_setting('app.organization_id', true), "
                   "current_setting('app.tenant_id', true)")
    tenant = cursor.fetchone()
    if tenant != (decision.organization_id, decision.tenant_id):
        raise AuthorityDenied('Database tenant context differs from decision')
    plan, epoch = _locked_plan(cursor, decision.organization_id,
                               decision.tenant_id, decision.plan_id)
    if (plan.revision, plan.digest, plan.source, plan.destination, epoch) != (
            decision.plan_revision, decision.plan_digest, decision.source,
            decision.destination, decision.revocation_epoch):
        raise AuthorityDenied('Plan revision, scopes or revocation epoch changed')
    approvals = _valid_approvals(plan, _approval_snapshot(cursor, plan, epoch), at)
    if (tuple(a.approval_id for a in approvals) != decision.approval_ids
            or decision.actor_subject in {plan.author_subject,
                                          *(a.approver_subject for a in approvals)}):
        raise AuthorityDenied('Approval set or operator separation changed')


def revalidate_admission(cursor, decision: AuthorizedPlan, at: datetime) -> None:
    """Called by B09 before INSERT, with its cursor and locked transaction."""
    if (not isinstance(decision, AuthorizedPlan)
            or not isinstance(at, datetime) or at.tzinfo is None
            or at.utcoffset() is None
            or not isinstance(decision.expires_at, datetime)
            or decision.expires_at.tzinfo is None
            or decision.expires_at.utcoffset() is None
            or decision.expires_at <= at):
        raise AuthorityDenied('Admission decision expired or is untrusted')
    _revalidate(cursor, decision, at)


def revalidate_start(cursor, job, at: datetime) -> None:
    """Called before outbox dispatch; a worker rechecks before every mutation."""
    _revalidate(cursor, job, at)


class PostgresAuthority:
    """Trusted PlanSource and ApprovalLedger backed by the same PostgreSQL DB.

    The constructor takes a privileged authority-writer factory for append and
    revoke; callers are responsible for keeping that credential server-side.
    Reads may use a separate read-only factory. B10 supplies grant persistence.
    """

    def __init__(self, connect: Callable):
        if not callable(connect):
            raise TypeError('A transaction-capable connection factory is required')
        self._connect = connect

    def current(self, organization_id: str, tenant_id: str,
                plan_id: str) -> FrozenPlan:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _runtime_role(cursor)
                _tenant(cursor, organization_id, tenant_id)
                plan, _ = _locked_plan(cursor, organization_id, tenant_id, plan_id)
                return plan

    def snapshot(self, plan: FrozenPlan) -> ApprovalSnapshot:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _runtime_role(cursor)
                _tenant(cursor, plan.organization_id, plan.tenant_id)
                current, epoch = _locked_plan(cursor, plan.organization_id,
                                              plan.tenant_id, plan.plan_id)
                if current != plan:
                    raise AuthorityDenied('Plan revision changed')
                return _approval_snapshot(cursor, plan, epoch)

    def append_if_current(self, plan: FrozenPlan, approval: PlanApproval,
                          expected_epoch: int) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _runtime_role(cursor)
                _tenant(cursor, plan.organization_id, plan.tenant_id)
                current, epoch = _locked_plan(cursor, plan.organization_id,
                                              plan.tenant_id, plan.plan_id,
                                              write_epoch=True)
                if current != plan or epoch != expected_epoch:
                    raise AuthorityDenied('Approval plan is stale')
                required = {'SOURCE_OWNER': plan.source,
                            'DESTINATION_OWNER': plan.destination,
                            'SOURCE_SECURITY': plan.source,
                            'DESTINATION_SECURITY': plan.destination}
                if (approval.role not in required
                        or approval.scope != required[approval.role]
                        or (approval.organization_id, approval.tenant_id,
                            approval.plan_id, approval.plan_revision,
                            approval.plan_digest, approval.revocation_epoch) != (
                            plan.organization_id, plan.tenant_id, plan.plan_id,
                            plan.revision, plan.digest, expected_epoch)
                        or approval.approver_subject == plan.author_subject):
                    raise AuthorityDenied('Approval actor, role or scope is invalid')
                scope = approval.scope
                cursor.execute(
                    'INSERT INTO hosting_controlplane.plan_approvals '
                    '(approval_id, organization_id, tenant_id, plan_id, '
                    'plan_revision, plan_digest, revocation_epoch, role, '
                    'site_id, security_domain_id, endpoint_id, native_scope_id, '
                    'platform_family, approver_subject, issued_at, expires_at) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '
                    '%s, %s, %s, %s, %s)',
                    (approval.approval_id, plan.organization_id, plan.tenant_id,
                     plan.plan_id, plan.revision, plan.digest, expected_epoch,
                     approval.role, scope.site_id, scope.security_domain_id,
                     scope.endpoint_id, scope.native_scope_id,
                     scope.platform_family, approval.approver_subject,
                     approval.issued_at, approval.expires_at))

    def revoke_if_current(self, plan: FrozenPlan, expected_epoch: int,
                          actor_subject: str, reason: str) -> int:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _runtime_role(cursor)
                _tenant(cursor, plan.organization_id, plan.tenant_id)
                current, epoch = _locked_plan(cursor, plan.organization_id,
                                              plan.tenant_id, plan.plan_id,
                                              write_epoch=True)
                if current != plan or epoch != expected_epoch:
                    raise AuthorityDenied('Revocation epoch or plan revision advanced')
                cursor.execute(
                    'UPDATE hosting_controlplane.plan_authority_state '
                    'SET revocation_epoch = revocation_epoch + 1, '
                    'updated_at = clock_timestamp() '
                    'WHERE organization_id = %s AND tenant_id = %s AND plan_id = %s '
                    'RETURNING revocation_epoch',
                    (plan.organization_id, plan.tenant_id, plan.plan_id))
                next_epoch = cursor.fetchone()[0]
                cursor.execute(
                    'INSERT INTO hosting_controlplane.plan_revocations '
                    '(organization_id, tenant_id, plan_id, from_epoch, '
                    'to_epoch, actor_subject, reason) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                    (plan.organization_id, plan.tenant_id, plan.plan_id,
                     expected_epoch, next_epoch, actor_subject, reason))
                return next_epoch

    def worker_grant(self, grant_id: str) -> WorkerGrant:
        # B10 must add a durable enrolled-worker grant table and broker. There
        # is no compatibility path that treats an arbitrary JSON grant as real.
        raise AuthorityDenied('Durable worker grants are not configured')

    revalidate_admission = staticmethod(revalidate_admission)
    revalidate_start = staticmethod(revalidate_start)
