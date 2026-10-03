"""Tenant-scoped native intent journal, uncertainty and fenced owner recovery.

This module never calls a platform. Claiming an intent is a one-time handoff to
a worker; a lost response stays IN_FLIGHT or UNCERTAIN until independently
observed and reviewed. The injected grant verifier must check B10's current
grant/worker/plan/approval epoch in *this transaction*. Evidence verification
must independently check native task state and that the old worker is fenced.
Neither a lease timeout nor a string supplied by a client is proof of safety.
"""
from __future__ import annotations

import re
import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Callable, Protocol

from provisioner.controlplane.authority.model import PlanScope, VerifiedPrincipal
from provisioner.controlplane.authority.service import (DESTINATION_SECURITY,
    EXECUTION_OPERATOR, MAX_STEP_UP_AGE, SOURCE_SECURITY, AuthorityDenied,
    require_scoped_role)
from provisioner.controlplane.jobs.repository import _json, _tenant
from provisioner.controlplane.persistence.store import (NativeBinding,
    OwnerLease, TenantContext)
from provisioner.controlplane.worker.grants import VerifiedWorkerIdentity

_KEY = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_DIGEST = re.compile(r'^[0-9a-f]{64}$')
_MUTATIONS = frozenset({
    'VM_POWER', 'DISK_ATTACH', 'NETWORK_ATTACH',
    'SNAPSHOT_CREATE', 'SNAPSHOT_EXPORT', 'SNAPSHOT_IMPORT',
    'RESTORE_DATA', 'SOURCE_FENCE', 'DESTINATION_ACTIVATE', 'DNS_CHANGE',
    'GUEST_CONFIG', 'POLICY_APPLY', 'QUOTA_CHANGE',
})
_FRESHNESS = timedelta(minutes=5)


class OperationConflict(RuntimeError):
    """Identity, grant, live lease, state or operation binding is not current."""


class RecoveryHeld(RuntimeError):
    """Native work, containment or independently verified exclusion is uncertain."""


class GrantVerifier(Protocol):
    def verify_intent(self, cursor, context: TenantContext, *, grant_id: str,
                      job_id: str, step_id: str, operation_id: str,
                      operation_kind: str, operation_scope: PlanScope,
                      worker_identity: VerifiedWorkerIdentity,
                      lease_key: str, lease_epoch: int) -> object:
        """Lock and recheck current B10 grant and revocation epoch or raise."""


class EvidenceVerifier(Protocol):
    def verify_native_observation(self, cursor, operation: 'NativeOperation',
                                  observation: 'NativeObservation') -> None:
        """Check authentic native/task state against a fresh platform readback.

        This is called again under the resolution transaction after old-worker
        exclusion. A previously signed observation alone is not a current
        no-effect result when a platform request might arrive late.
        """

    def verify_owner_exclusion(self, cursor, lease: OwnerLease, scope: PlanScope,
                               evidence: 'OwnerRecoveryEvidence') -> None:
        """Check current native quiescence and actual old-worker/credential fencing.

        The proof must exclude delayed platform requests by the old worker,
        including requests already handed to a queue or an accepted task.
        """


@dataclass(frozen=True)
class NativeOperation:
    operation_id: str
    job_id: str
    grant_id: str
    step_id: str
    lease_key: str
    binding: NativeBinding
    workload_id: str
    security_domain_id: str
    worker_id: str
    owner_epoch: int
    operation_kind: str
    request_digest: str
    state: str
    native_task_id: str | None
    outcome: str | None


@dataclass(frozen=True)
class NativeObservation:
    observation_id: str
    evidence_digest: str
    observer_subject: str
    native_task_id: str | None
    outcome: str  # UNKNOWN, IN_PROGRESS, NO_EFFECT, EFFECT_PRESENT
    native_quiesced: bool
    observed_at: datetime

    def __post_init__(self) -> None:
        if (not _key(self.observation_id) or not _digest(self.evidence_digest)
                or not self.observer_subject or self.outcome not in
                {'UNKNOWN', 'IN_PROGRESS', 'NO_EFFECT', 'EFFECT_PRESENT'}
                or type(self.native_quiesced) is not bool
                or (self.native_task_id is not None and not _text(self.native_task_id))
                or not _aware(self.observed_at)):
            raise ValueError('Invalid independently collected native observation')


@dataclass(frozen=True)
class OwnerRecoveryEvidence:
    native_evidence_digest: str
    worker_fence_digest: str
    observed_at: datetime
    incident_id: str

    def __post_init__(self) -> None:
        if (not _digest(self.native_evidence_digest)
                or not _digest(self.worker_fence_digest)
                or not _aware(self.observed_at) or not _key(self.incident_id)):
            raise ValueError('Invalid owner recovery evidence')


def _aware(value) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _key(value) -> bool:
    return isinstance(value, str) and _KEY.fullmatch(value) is not None


def _text(value) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 512


def _digest(value) -> bool:
    return isinstance(value, str) and _DIGEST.fullmatch(value) is not None


def _fresh(observed_at: datetime, now: datetime) -> bool:
    return _aware(observed_at) and now - _FRESHNESS <= observed_at <= now


def _resolution_digest(observation: NativeObservation,
                       exclusion: OwnerRecoveryEvidence) -> str:
    """Bind both reviewers to one native observation and one exclusion proof."""
    evidence = {
        'purpose': 'native-operation-resolution-v1',
        'observation_id': observation.observation_id,
        'native_digest': observation.evidence_digest,
        'native_observed_at': observation.observed_at.isoformat(),
        'exclusion_native_digest': exclusion.native_evidence_digest,
        'worker_fence_digest': exclusion.worker_fence_digest,
        'exclusion_observed_at': exclusion.observed_at.isoformat(),
        'incident_id': exclusion.incident_id,
    }
    return hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(',', ':'))
                          .encode('utf-8')).hexdigest()


def _identity(principal: VerifiedPrincipal, role: str,
              scope: PlanScope, now: datetime) -> str:
    if (not isinstance(principal, VerifiedPrincipal)
            or principal.kind != 'HUMAN' or principal.step_up_at is None
            or not now - MAX_STEP_UP_AGE <= principal.step_up_at <= now):
        raise AuthorityDenied('Recent verified human step-up is required')
    require_scoped_role(principal, role, scope, now)
    return principal.subject


def _security_identity(principal: VerifiedPrincipal, scope: PlanScope,
                       now: datetime) -> str:
    try:
        return _identity(principal, SOURCE_SECURITY, scope, now)
    except AuthorityDenied:
        return _identity(principal, DESTINATION_SECURITY, scope, now)


def _scope(ctx: TenantContext, scope: PlanScope, binding: NativeBinding,
           security_domain_id: str) -> None:
    if (not isinstance(scope, PlanScope)
            or (scope.organization_id, scope.tenant_id,
                scope.security_domain_id, scope.platform_family,
                scope.endpoint_id, scope.native_scope_id) !=
               (ctx.organization_id, ctx.tenant_id, security_domain_id,
                binding.platform_family, binding.endpoint_id,
                binding.native_scope_id)):
        raise OperationConflict('Exact native scope differs from owner and tenant')


def _row(row) -> NativeOperation:
    return NativeOperation(row[0], row[1], row[2], row[3], row[4],
                           NativeBinding(*row[5:10]), row[10], row[11], row[12],
                           row[13], row[14], row[15], row[16], row[17], row[18])


def _stored_job_scope(value) -> PlanScope:
    """Decode B09's persisted dataclass scope, not a canonical plan record."""
    try:
        return PlanScope(**_json(value))
    except (TypeError, ValueError) as exc:
        raise OperationConflict('The persisted job scope is invalid') from exc


_SELECT = ('operation_id, job_id, grant_id, step_id, lease_key, '
           'platform_family, endpoint_id, '
           'native_scope_id, resource_kind, native_id, workload_id, '
           'security_domain_id, worker_id, owner_epoch, operation_kind, '
           'request_digest, state, native_task_id, outcome')


class NativeLeaseAuthority:
    """B10's exact lease-key lookup for an *existing* B06 native binding.

    The mapping is immutable and cannot reassign an expired worker. Unbound
    VM_CREATE has no observed native identity and is intentionally not admitted
    by this slice; its planned-resource lease requires a later plan graph gate.
    """

    def __init__(self, connection_factory: Callable):
        if not callable(connection_factory):
            raise TypeError('PostgreSQL connection factory required')
        self._connect = connection_factory

    def register(self, ctx: TenantContext, lease: OwnerLease, scope: PlanScope,
                 *, lease_key: str, job_id: str, operation_id: str,
                 worker_identity: VerifiedWorkerIdentity,
                 ttl_seconds: int = 300) -> None:
        if not all(map(_key, (lease_key, job_id, operation_id))):
            raise ValueError('Stable lease, job and operation IDs required')
        if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 300:
            raise ValueError('Operation lease TTL must be 1–300 seconds')
        _scope(ctx, scope, lease.binding, lease.security_domain_id)
        if (not isinstance(worker_identity, VerifiedWorkerIdentity)
                or (worker_identity.organization_id, worker_identity.tenant_id,
                    worker_identity.subject, worker_identity.site_id) !=
                   (ctx.organization_id, ctx.tenant_id, lease.worker_id,
                    scope.site_id)):
            raise OperationConflict('Verified worker does not match current owner/site')
        with self._connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, ctx)
            cursor.execute(
                'SELECT status, source_scope, destination_scope FROM '
                'hosting_controlplane.operation_jobs WHERE organization_id = %s '
                'AND tenant_id = %s AND job_id = %s FOR SHARE',
                (ctx.organization_id, ctx.tenant_id, job_id))
            job = cursor.fetchone()
            if job is None or job[0] not in ('STARTED', 'RUNNING'):
                raise OperationConflict('A started job is required')
            if scope not in (_stored_job_scope(job[1]),
                             _stored_job_scope(job[2])):
                raise OperationConflict('Scope is not selected by the job')
            NativeOperationRegistry._owner(cursor, ctx, lease, live=True)
            NativeOperationRegistry._containment(cursor, lease.binding)
            now = NativeOperationRegistry._clock(cursor)
            if worker_identity.expires_at <= now:
                raise OperationConflict('Worker identity has expired')
            cursor.execute(
                'INSERT INTO hosting_controlplane.native_operation_leases '
                '(organization_id, tenant_id, lease_key, job_id, operation_id, '
                'platform_family, endpoint_id, native_scope_id, resource_kind, '
                'native_id, site_id, security_domain_id, worker_id, owner_epoch, '
                'expires_at) VALUES '
                '(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '
                'LEAST(%s, %s, clock_timestamp() + make_interval(secs => %s)))',
                (ctx.organization_id, ctx.tenant_id, lease_key, job_id,
                 operation_id, *lease.binding.key(), scope.site_id,
                 lease.security_domain_id, lease.worker_id, lease.epoch,
                 lease.expires_at, worker_identity.expires_at, ttl_seconds))

    def require_current(self, cursor, context: TenantContext, *, lease_key: str,
                        lease_epoch: int, job_id: str, operation_id: str,
                        scope: PlanScope, worker_subject: str) -> None:
        """Lock key and B06 owner in the caller's transaction; fail closed."""
        _tenant(cursor, context)
        cursor.execute(
            'SELECT job_id, operation_id, platform_family, endpoint_id, '
            'native_scope_id, resource_kind, native_id, site_id, '
            'security_domain_id, worker_id, owner_epoch, expires_at, '
            'owner_organization_id, owner_tenant_id, '
            'owner_security_domain_id, owner_worker_id, '
            'owner_lease_epoch, owner_lease_expires_at '
            'FROM hosting_controlplane.lock_native_worker_scope(%s, %s, %s)',
            (context.organization_id, context.tenant_id, lease_key))
        row = cursor.fetchone()
        if row is None:
            raise OperationConflict('No exact operation lease mapping is visible')
        binding = NativeBinding(*row[2:7])
        _scope(context, scope, binding, row[8])
        now = NativeOperationRegistry._clock(cursor)
        if (row[0], row[1], row[7], row[9], row[10]) != (
                job_id, operation_id, scope.site_id, worker_subject,
                lease_epoch) or row[11] <= now:
            raise OperationConflict('Operation lease expired or belongs to another worker')
        if (tuple(row[12:17]) !=
                (context.organization_id, context.tenant_id,
                 scope.security_domain_id, worker_subject, lease_epoch)
                or row[17] is None or row[17] <= now):
            raise OperationConflict('Native owner is stale or held by another worker')
        NativeOperationRegistry._containment(cursor, binding)


class NativeOperationRegistry:
    """One PostgreSQL transaction for each state transition; no native actions."""

    def __init__(self, connection_factory: Callable, *, grants: GrantVerifier,
                 evidence: EvidenceVerifier):
        if (not callable(connection_factory) or grants is None
                or not callable(getattr(grants, 'verify_intent', None))
                or evidence is None
                or not callable(getattr(evidence, 'verify_native_observation', None))
                or not callable(getattr(evidence, 'verify_owner_exclusion', None))):
            raise TypeError('PostgreSQL, live grant and independent evidence verifiers required')
        self._connect = connection_factory
        self._grants = grants
        self._evidence = evidence

    @staticmethod
    def _clock(cursor) -> datetime:
        cursor.execute('SELECT clock_timestamp()')
        return cursor.fetchone()[0]

    @staticmethod
    def _owner(cursor, ctx: TenantContext, lease: OwnerLease,
               *, live: bool | None) -> datetime:
        if not isinstance(lease, OwnerLease) or (
                lease.organization_id, lease.tenant_id) != (
                ctx.organization_id, ctx.tenant_id):
            raise OperationConflict('Trusted owner lease is required in this tenant')
        cursor.execute(
            'SELECT organization_id, tenant_id, security_domain_id, workload_id, '
            'worker_id, lease_epoch, lease_expires_at FROM hosting_controlplane.native_ownership '
            'WHERE platform_family = %s AND endpoint_id = %s AND native_scope_id = %s '
            'AND resource_kind = %s AND native_id = %s FOR UPDATE',
            lease.binding.key())
        row = cursor.fetchone()
        now = NativeOperationRegistry._clock(cursor)
        if (row is None or tuple(row[:6]) !=
                (ctx.organization_id, ctx.tenant_id, lease.security_domain_id,
                 lease.workload_id, lease.worker_id, lease.epoch)
                or row[6] is None
                or (live is True and row[6] <= now)
                or (live is False and row[6] > now)):
            raise OperationConflict('Owner epoch, worker or lease state changed')
        return row[6]

    @staticmethod
    def _containment(cursor, binding: NativeBinding) -> None:
        cursor.execute(
            'SELECT 1 FROM hosting_controlplane.native_containment_holds '
            'WHERE platform_family = %s AND endpoint_id = %s AND native_scope_id = %s '
            'AND resource_kind = %s AND native_id = %s', binding.key())
        if cursor.fetchone() is not None:
            raise RecoveryHeld('Incident containment prohibits new work and recovery')

    @staticmethod
    def _get(cursor, ctx: TenantContext, operation_id: str) -> NativeOperation:
        cursor.execute(
            f'SELECT {_SELECT} FROM hosting_controlplane.native_operation_intents '
            'WHERE organization_id = %s AND tenant_id = %s AND operation_id = %s FOR UPDATE',
            (ctx.organization_id, ctx.tenant_id, operation_id))
        row = cursor.fetchone()
        if row is None:
            raise OperationConflict('Operation is not visible in this tenant')
        return _row(row)

    @staticmethod
    def _bound(operation: NativeOperation, lease: OwnerLease) -> None:
        if (operation.binding != lease.binding or operation.owner_epoch != lease.epoch
                or operation.worker_id != lease.worker_id
                or operation.workload_id != lease.workload_id
                or operation.security_domain_id != lease.security_domain_id):
            raise OperationConflict('Operation belongs to another owner epoch or worker')

    def prepare(self, ctx: TenantContext, lease: OwnerLease, scope: PlanScope,
                *, job_id: str, grant_id: str, step_id: str, lease_key: str,
                worker_identity: VerifiedWorkerIdentity, operation_id: str,
                operation_kind: str, request_digest: str) -> NativeOperation:
        if not all(map(_key, (job_id, grant_id, step_id, lease_key, operation_id))):
            raise ValueError('Stable job, grant, step, lease and operation IDs are required')
        if operation_kind not in _MUTATIONS or not _digest(request_digest):
            raise ValueError('Unknown native mutation or invalid immutable digest')
        _scope(ctx, scope, lease.binding, lease.security_domain_id)
        with self._connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, ctx)
            cursor.execute(
                'SELECT source_scope, destination_scope, status FROM '
                'hosting_controlplane.operation_jobs WHERE organization_id = %s '
                'AND tenant_id = %s AND job_id = %s FOR SHARE',
                (ctx.organization_id, ctx.tenant_id, job_id))
            job = cursor.fetchone()
            if job is None or job[2] not in ('STARTED', 'RUNNING'):
                raise OperationConflict('Only a started and current job may prepare native work')
            if scope not in (_stored_job_scope(job[0]),
                             _stored_job_scope(job[1])):
                raise OperationConflict('Native scope is not selected by this job')
            # B10 takes job -> enrollment -> authority -> operation lease ->
            # owner locks. Preserve that order before touching intent rows.
            self._grants.verify_intent(cursor, ctx, grant_id=grant_id, job_id=job_id,
                                       step_id=step_id, operation_id=operation_id,
                                       operation_kind=operation_kind,
                                       operation_scope=scope,
                                       worker_identity=worker_identity,
                                       lease_key=lease_key,
                                       lease_epoch=lease.epoch)
            self._owner(cursor, ctx, lease, live=True)
            self._containment(cursor, lease.binding)
            cursor.execute(
                'INSERT INTO hosting_controlplane.native_operation_intents '
                '(organization_id, tenant_id, operation_id, job_id, grant_id, '
                'step_id, lease_key, '
                'platform_family, endpoint_id, native_scope_id, resource_kind, native_id, '
                'workload_id, security_domain_id, worker_id, owner_epoch, '
                'operation_kind, request_digest) VALUES '
                '(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '
                '%s, %s, %s, %s) '
                'ON CONFLICT (organization_id, tenant_id, operation_id) DO NOTHING',
                (ctx.organization_id, ctx.tenant_id, operation_id, job_id,
                 grant_id, step_id, lease_key,
                 *lease.binding.key(), lease.workload_id, lease.security_domain_id,
                 lease.worker_id, lease.epoch, operation_kind, request_digest))
            operation = self._get(cursor, ctx, operation_id)
            if (operation.job_id, operation.grant_id, operation.step_id,
                operation.lease_key, operation.binding,
                operation.workload_id, operation.security_domain_id,
                operation.worker_id, operation.owner_epoch,
                operation.operation_kind, operation.request_digest) != (
                job_id, grant_id, step_id, lease_key, lease.binding, lease.workload_id,
                lease.security_domain_id, lease.worker_id, lease.epoch,
                operation_kind, request_digest):
                raise OperationConflict('Operation ID is already bound to another intent')
            return operation

    def claim_once(self, ctx: TenantContext, lease: OwnerLease,
                   scope: PlanScope, operation_id: str,
                   worker_identity: VerifiedWorkerIdentity) -> bool:
        """Exactly one cooperative worker may begin sending this intent.

        A crash after claim can leave IN_FLIGHT without any platform request.
        That ambiguity is deliberate: reconciliation must observe before retry.
        """
        _scope(ctx, scope, lease.binding, lease.security_domain_id)
        with self._connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, ctx)
            # Match B10's job -> operation lease -> owner lock order.
            cursor.execute(
                'SELECT status FROM hosting_controlplane.operation_jobs '
                'WHERE organization_id = %s AND tenant_id = %s AND job_id = '
                '(SELECT job_id FROM hosting_controlplane.native_operation_intents '
                'WHERE organization_id = %s AND tenant_id = %s AND operation_id = %s) '
                'FOR SHARE',
                (ctx.organization_id, ctx.tenant_id, ctx.organization_id,
                 ctx.tenant_id, operation_id))
            job = cursor.fetchone()
            if job is None or job[0] not in ('STARTED', 'RUNNING'):
                raise OperationConflict('Job has stopped before native mutation')
            cursor.execute(
                f'SELECT {_SELECT} FROM hosting_controlplane.native_operation_intents '
                'WHERE organization_id = %s AND tenant_id = %s AND operation_id = %s',
                (ctx.organization_id, ctx.tenant_id, operation_id))
            previous = cursor.fetchone()
            if previous is None:
                raise OperationConflict('Operation is not visible in this tenant')
            proposed = _row(previous)
            self._grants.verify_intent(cursor, ctx, grant_id=proposed.grant_id,
                                       job_id=proposed.job_id, step_id=proposed.step_id,
                                       operation_id=proposed.operation_id,
                                       operation_kind=proposed.operation_kind,
                                       operation_scope=scope,
                                       worker_identity=worker_identity,
                                       lease_key=proposed.lease_key,
                                       lease_epoch=proposed.owner_epoch)
            self._owner(cursor, ctx, lease, live=True)
            self._containment(cursor, lease.binding)
            op = self._get(cursor, ctx, operation_id)
            self._bound(op, lease)
            if op != proposed:
                raise OperationConflict('Operation changed during authorization')
            if op.state != 'PREPARED':
                return False
            cursor.execute(
                "UPDATE hosting_controlplane.native_operation_intents SET state = 'IN_FLIGHT', "
                'updated_at = clock_timestamp() WHERE organization_id = %s '
                'AND tenant_id = %s AND operation_id = %s',
                (ctx.organization_id, ctx.tenant_id, operation_id))
            return True

    def task_accepted(self, ctx: TenantContext, operation_id: str,
                      worker_id: str, native_task_id: str) -> bool:
        """Record a late native receipt, even if the lease has expired."""
        if not _key(operation_id) or not _key(worker_id) or not _text(native_task_id):
            raise ValueError('Task receipt needs exact operation, worker and native task ID')
        with self._connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, ctx)
            op = self._get(cursor, ctx, operation_id)
            if op.worker_id != worker_id:
                raise OperationConflict('Native receipt came from another worker')
            if op.state == 'TASK_ACCEPTED' and op.native_task_id == native_task_id:
                return False
            if op.state != 'IN_FLIGHT':
                raise OperationConflict('Late or conflicting receipt requires observation')
            cursor.execute(
                "UPDATE hosting_controlplane.native_operation_intents SET state = 'TASK_ACCEPTED', "
                'native_task_id = %s, updated_at = clock_timestamp() '
                'WHERE organization_id = %s AND tenant_id = %s AND operation_id = %s',
                (native_task_id, ctx.organization_id, ctx.tenant_id, operation_id))
            return True

    def mark_uncertain(self, ctx: TenantContext, operation_id: str,
                       worker_id: str) -> bool:
        """Timeout/crash recovery records ambiguity without resending."""
        with self._connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, ctx)
            op = self._get(cursor, ctx, operation_id)
            if op.worker_id != worker_id:
                raise OperationConflict('Only the bound worker may report uncertainty')
            if op.state == 'UNCERTAIN':
                return False
            if op.state not in ('IN_FLIGHT', 'TASK_ACCEPTED'):
                raise OperationConflict('Only sent or accepted work may be uncertain')
            cursor.execute(
                "UPDATE hosting_controlplane.native_operation_intents SET state = 'UNCERTAIN', "
                'updated_at = clock_timestamp() WHERE organization_id = %s '
                'AND tenant_id = %s AND operation_id = %s',
                (ctx.organization_id, ctx.tenant_id, operation_id))
            return True

    def observe(self, ctx: TenantContext, operation_id: str,
                observation: NativeObservation) -> None:
        if not isinstance(observation, NativeObservation):
            raise TypeError('Independent native observation is required')
        with self._connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, ctx)
            op = self._get(cursor, ctx, operation_id)
            if op.state == 'PREPARED' or op.state == 'RESOLVED':
                raise OperationConflict('Operation is not awaiting native observation')
            if (observation.observer_subject == op.worker_id
                    or (op.native_task_id is not None and
                        observation.native_task_id != op.native_task_id)):
                raise RecoveryHeld('Observation is not independent or task ID differs')
            self._evidence.verify_native_observation(cursor, op, observation)
            cursor.execute(
                'INSERT INTO hosting_controlplane.native_operation_observations '
                '(organization_id, tenant_id, observation_id, operation_id, '
                'evidence_digest, observer_subject, native_task_id, outcome, '
                'native_quiesced, observed_at) VALUES '
                '(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (ctx.organization_id, ctx.tenant_id, observation.observation_id,
                 operation_id, observation.evidence_digest,
                 observation.observer_subject, observation.native_task_id,
                 observation.outcome, observation.native_quiesced,
                 observation.observed_at))

    def review_outcome(self, ctx: TenantContext, operation_id: str,
                       observation_id: str, principal: VerifiedPrincipal,
                       scope: PlanScope, *, decision: str,
                       exclusion: OwnerRecoveryEvidence) -> bool:
        """Two reviewers attest one fresh readback and old-worker exclusion.

        A native no-effect result alone cannot release an uncertain request:
        the expired owner must first be fenced from submitting it late.
        """
        if decision not in ('NO_EFFECT', 'EFFECT_PRESENT'):
            raise ValueError('A concrete outcome is required')
        if not isinstance(exclusion, OwnerRecoveryEvidence):
            raise TypeError('Independent owner exclusion evidence is required')
        with self._connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, ctx)
            # Read the immutable binding, then lock owner before intent. Other
            # paths take this same lock order; reversal can deadlock recovery.
            cursor.execute(
                f'SELECT {_SELECT} FROM hosting_controlplane.native_operation_intents '
                'WHERE organization_id = %s AND tenant_id = %s AND operation_id = %s',
                (ctx.organization_id, ctx.tenant_id, operation_id))
            previous = cursor.fetchone()
            if previous is None:
                raise OperationConflict('Operation is not visible in this tenant')
            proposed = _row(previous)
            _scope(ctx, scope, proposed.binding, proposed.security_domain_id)
            now = self._clock(cursor)
            # The owner lock serializes review with containment and owner
            # transitions. An expired cooperative lease is not itself a fence.
            lease = OwnerLease(proposed.binding, ctx.organization_id, ctx.tenant_id,
                               proposed.security_domain_id, proposed.workload_id,
                               proposed.worker_id, proposed.owner_epoch, now)
            lease = replace(lease, expires_at=self._owner(cursor, ctx, lease,
                                                           live=False))
            self._containment(cursor, proposed.binding)
            op = self._get(cursor, ctx, operation_id)
            if op != proposed:
                raise OperationConflict('Operation changed during recovery')
            if op.state not in ('IN_FLIGHT', 'TASK_ACCEPTED', 'UNCERTAIN'):
                raise RecoveryHeld('Operation cannot be resolved from this state')
            now = self._clock(cursor)
            actor = _identity(principal, EXECUTION_OPERATOR, scope, now)
            if not _fresh(exclusion.observed_at, now):
                raise RecoveryHeld('Fresh worker exclusion evidence is required')
            self._evidence.verify_owner_exclusion(cursor, lease, scope, exclusion)
            cursor.execute(
                'SELECT evidence_digest, observer_subject, native_task_id, outcome, '
                'native_quiesced, observed_at FROM '
                'hosting_controlplane.native_operation_observations '
                'WHERE organization_id = %s AND tenant_id = %s AND '
                'operation_id = %s AND observation_id = %s',
                (ctx.organization_id, ctx.tenant_id, operation_id, observation_id))
            observed = cursor.fetchone()
            if (observed is None or observed[3] != decision or not observed[4]
                    or not _fresh(observed[5], now) or actor in
                    (op.worker_id, observed[1])):
                raise RecoveryHeld('Fresh independent quiesced outcome is required')
            observation = NativeObservation(observation_id, observed[0], observed[1],
                                            observed[2], observed[3], observed[4],
                                            observed[5])
            self._evidence.verify_native_observation(cursor, op, observation)
            resolution_digest = _resolution_digest(observation, exclusion)
            cursor.execute(
                'INSERT INTO hosting_controlplane.native_operation_reviews '
                '(organization_id, tenant_id, operation_id, reviewer_subject, '
                'observation_id, evidence_digest, decision, incident_id) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING',
                (ctx.organization_id, ctx.tenant_id, operation_id, actor,
                 observation_id, resolution_digest, decision,
                 exclusion.incident_id))
            cursor.execute(
                'SELECT reviewer_subject, observation_id, evidence_digest, '
                'decision, incident_id FROM hosting_controlplane.native_operation_reviews '
                'WHERE organization_id = %s AND tenant_id = %s AND operation_id = %s',
                (ctx.organization_id, ctx.tenant_id, operation_id))
            reviews = cursor.fetchall()
            if len(reviews) > 2 or any(row[1:] !=
                                       (observation_id, resolution_digest, decision,
                                        exclusion.incident_id) for row in reviews):
                raise RecoveryHeld('Conflicting operator review holds the operation')
            if len(reviews) != 2:
                return False
            cursor.execute(
                "UPDATE hosting_controlplane.native_operation_intents SET state = 'RESOLVED', "
                'outcome = %s, resolution_evidence_digest = %s, '
                'updated_at = clock_timestamp() WHERE organization_id = %s '
                'AND tenant_id = %s AND operation_id = %s',
                (decision, resolution_digest, ctx.organization_id, ctx.tenant_id,
                 operation_id))
            return True

    def contain(self, ctx: TenantContext, lease: OwnerLease, principal: VerifiedPrincipal,
                scope: PlanScope, *, incident_id: str, reason: str) -> None:
        """Append a sticky incident hold; routine reconciliation cannot clear it."""
        _scope(ctx, scope, lease.binding, lease.security_domain_id)
        if not _key(incident_id) or not isinstance(reason, str) or not reason.strip():
            raise ValueError('Incident ID and reason are required')
        with self._connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, ctx)
            self._owner(cursor, ctx, lease, live=None)
            actor = _security_identity(principal, scope, self._clock(cursor))
            cursor.execute(
                'INSERT INTO hosting_controlplane.native_containment_holds '
                '(platform_family, endpoint_id, native_scope_id, resource_kind, '
                'native_id, organization_id, tenant_id, incident_id, actor_subject, reason) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (*lease.binding.key(), ctx.organization_id, ctx.tenant_id,
                 incident_id, actor, reason.strip()))

    def review_expired_owner(self, ctx: TenantContext, lease: OwnerLease,
                             scope: PlanScope, principal: VerifiedPrincipal,
                             evidence: OwnerRecoveryEvidence) -> None:
        """Record one reviewed proof of native quiescence and old-worker fencing."""
        _scope(ctx, scope, lease.binding, lease.security_domain_id)
        if not isinstance(evidence, OwnerRecoveryEvidence):
            raise TypeError('Independent owner recovery evidence is required')
        with self._connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, ctx)
            self._owner(cursor, ctx, lease, live=False)
            self._containment(cursor, lease.binding)
            now = self._clock(cursor)
            actor = _security_identity(principal, scope, now)
            if not _fresh(evidence.observed_at, now) or actor == lease.worker_id:
                raise RecoveryHeld('Fresh independent exclusion proof is required')
            self._evidence.verify_owner_exclusion(cursor, lease, scope, evidence)
            cursor.execute(
                'INSERT INTO hosting_controlplane.native_owner_recovery_reviews '
                '(organization_id, tenant_id, platform_family, endpoint_id, '
                'native_scope_id, resource_kind, native_id, owner_epoch, '
                'reviewer_subject, old_worker_id, native_evidence_digest, '
                'worker_fence_digest, observed_at, incident_id) VALUES '
                '(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (ctx.organization_id, ctx.tenant_id, *lease.binding.key(),
                 lease.epoch, actor, lease.worker_id,
                 evidence.native_evidence_digest, evidence.worker_fence_digest,
                 evidence.observed_at, evidence.incident_id))

    def clear_expired_owner(self, ctx: TenantContext, lease: OwnerLease,
                            scope: PlanScope, evidence: OwnerRecoveryEvidence) -> int:
        """Advance epoch and clear an expired worker only after quorum and proof.

        This does not acquire a new lease or authorize any native action.
        """
        _scope(ctx, scope, lease.binding, lease.security_domain_id)
        if not isinstance(evidence, OwnerRecoveryEvidence):
            raise TypeError('Independent owner recovery evidence is required')
        with self._connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, ctx)
            self._owner(cursor, ctx, lease, live=False)
            self._containment(cursor, lease.binding)
            now = self._clock(cursor)
            if not _fresh(evidence.observed_at, now):
                raise RecoveryHeld('Native and worker exclusion evidence expired')
            self._evidence.verify_owner_exclusion(cursor, lease, scope, evidence)
            cursor.execute(
                'SELECT 1 FROM hosting_controlplane.native_operation_intents '
                'WHERE organization_id = %s AND tenant_id = %s AND '
                'platform_family = %s AND endpoint_id = %s AND native_scope_id = %s '
                'AND resource_kind = %s AND native_id = %s AND '
                "state != 'RESOLVED' LIMIT 1",
                (ctx.organization_id, ctx.tenant_id, *lease.binding.key()))
            if cursor.fetchone() is not None:
                raise RecoveryHeld('Unresolved native work prevents owner recovery')
            cursor.execute(
                'SELECT reviewer_subject, native_evidence_digest, '
                'worker_fence_digest, observed_at, incident_id FROM '
                'hosting_controlplane.native_owner_recovery_reviews '
                'WHERE organization_id = %s AND tenant_id = %s AND '
                'platform_family = %s AND endpoint_id = %s AND native_scope_id = %s '
                'AND resource_kind = %s AND native_id = %s AND owner_epoch = %s',
                (ctx.organization_id, ctx.tenant_id, *lease.binding.key(),
                 lease.epoch))
            reviews = cursor.fetchall()
            if (len(reviews) != 2 or any((row[1], row[2], row[3], row[4]) !=
                                          (evidence.native_evidence_digest,
                                           evidence.worker_fence_digest,
                                           evidence.observed_at, evidence.incident_id)
                                          for row in reviews)):
                raise RecoveryHeld('Two matching distinct operator attestations are required')
            cursor.execute(
                'UPDATE hosting_controlplane.native_ownership SET worker_id = NULL, '
                'lease_expires_at = NULL, lease_epoch = lease_epoch + 1, '
                'updated_at = clock_timestamp() WHERE platform_family = %s '
                'AND endpoint_id = %s AND native_scope_id = %s AND resource_kind = %s '
                'AND native_id = %s AND organization_id = %s AND tenant_id = %s '
                'AND worker_id = %s AND lease_epoch = %s RETURNING lease_epoch',
                (*lease.binding.key(), ctx.organization_id, ctx.tenant_id,
                 lease.worker_id, lease.epoch))
            result = cursor.fetchone()
            if result is None:
                raise OperationConflict('Owner advanced during recovery')
            return result[0]
