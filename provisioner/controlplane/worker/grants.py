"""Exact, short-lived worker grants backed by PostgreSQL authority.

Only the trusted control service has the grant-writer database role. Workers
authenticate at the mTLS edge; the edge's verifier supplies an independently
verified certificate fingerprint and subject. Never accept an HTTP body as a
VerifiedWorkerIdentity. B11 supplies the lease authority and must lock the
current native-operation epoch in the same transaction. There is deliberately
no native platform call or local secret-store fallback here.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Protocol, TypeVar
from uuid import uuid4

from provisioner.controlplane.authority import postgres as authority_postgres
from provisioner.controlplane.authority.model import PlanScope, WorkerGrant
from provisioner.controlplane.jobs.repository import _JOB_SELECT, _job
from provisioner.controlplane.persistence import TenantContext

ALLOWED_OPERATIONS = frozenset({
    'DISCOVER_READ', 'VM_CREATE', 'VM_POWER', 'DISK_ATTACH', 'NETWORK_ATTACH',
    'SNAPSHOT_CREATE', 'SNAPSHOT_EXPORT', 'SNAPSHOT_IMPORT', 'RESTORE_DATA',
    'SOURCE_FENCE', 'DESTINATION_ACTIVATE', 'DNS_CHANGE', 'IPAM_RESERVE',
    'GUEST_CONFIG', 'POLICY_APPLY', 'QUOTA_CHANGE',
})
_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_FINGERPRINT = re.compile(r'^[0-9a-f]{64}$')
MAX_GRANT_TTL = timedelta(minutes=5)
T = TypeVar('T')


class GrantDenied(PermissionError):
    """Worker, site, approval, job, scope or lease is no longer authorized."""


def _aware(value: datetime) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


@dataclass(frozen=True)
class VerifiedWorkerIdentity:
    """Result of independent certificate-chain and mTLS peer verification."""

    organization_id: str
    tenant_id: str
    subject: str
    site_id: str
    certificate_sha256: str
    expires_at: datetime

    def __post_init__(self) -> None:
        if (not all(isinstance(value, str) and _ID.fullmatch(value)
                    for value in (self.organization_id, self.tenant_id,
                                  self.subject, self.site_id))
                or not isinstance(self.certificate_sha256, str)
                or not _FINGERPRINT.fullmatch(self.certificate_sha256)
                or not _aware(self.expires_at)):
            raise ValueError('Invalid verified worker identity')


@dataclass(frozen=True)
class GrantRequest:
    job_id: str
    step_id: str
    operation_id: str
    operation_kind: str
    operation_scope: PlanScope
    lease_key: str
    lease_epoch: int
    ttl: timedelta

    def __post_init__(self) -> None:
        if (not all(isinstance(value, str) and _ID.fullmatch(value)
                    for value in (self.job_id, self.step_id, self.operation_id,
                                  self.lease_key))
                or self.operation_kind not in ALLOWED_OPERATIONS
                or not isinstance(self.operation_scope, PlanScope)
                or type(self.lease_epoch) is not int or self.lease_epoch < 1
                or not isinstance(self.ttl, timedelta)
                or not timedelta(0) < self.ttl <= MAX_GRANT_TTL):
            raise ValueError('Invalid exact worker operation')


class LeaseAuthority(Protocol):
    def require_current(self, cursor, context: TenantContext, *, lease_key: str,
                        lease_epoch: int, job_id: str, operation_id: str,
                        scope: PlanScope, worker_subject: str) -> None:
        """Lock and validate the authoritative B11 lease in caller's transaction."""


class WorkerIdentityVerifier(Protocol):
    def verify(self, transport_evidence: object) -> VerifiedWorkerIdentity:
        """Authenticate a current mTLS peer and its certificate chain/status."""


class EphemeralCredentialIssuer(Protocol):
    def issue(self, reference: str, *, grant: WorkerGrant,
              expires_at: datetime) -> object:
        """Mint an externally revocable, operation-limited secret handle.

        A deployment's secret manager must enforce the scope, action and expiry
        in the grant. Neither a static shared secret nor a raw secret in workflow
        history fulfills this interface.
        """


def _context(cursor, context: TenantContext) -> None:
    if not isinstance(context, TenantContext):
        raise GrantDenied('Verified tenant context is required')
    authority_postgres._runtime_role(cursor)
    authority_postgres._tenant(cursor, context.organization_id, context.tenant_id)


def _identity(context: TenantContext, identity: VerifiedWorkerIdentity,
              at: datetime) -> None:
    if (not isinstance(identity, VerifiedWorkerIdentity)
            or (identity.organization_id, identity.tenant_id) !=
            (context.organization_id, context.tenant_id)
            or identity.expires_at <= at):
        raise GrantDenied('A current worker certificate in this tenant is required')


def _enrollment(cursor, context: TenantContext, identity: VerifiedWorkerIdentity,
                scope: PlanScope, kind: str, at: datetime) -> tuple[str, datetime]:
    if (scope.organization_id, scope.tenant_id, scope.site_id) != (
            context.organization_id, context.tenant_id, identity.site_id):
        raise GrantDenied('Worker is not enrolled at the operation site')
    cursor.execute(
        'SELECT credential_ref, enrollment_expires_at FROM '
        'hosting_controlplane.lock_worker_scope('
        '%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (context.organization_id, context.tenant_id, identity.subject,
         identity.certificate_sha256, scope.site_id, scope.security_domain_id,
         scope.endpoint_id, scope.native_scope_id, scope.platform_family, kind))
    row = cursor.fetchone()
    if row is None or row[1] <= at:
        raise GrantDenied('Worker certificate or exact operation capability is unavailable')
    return row


class PostgresWorkerGrants:
    """Grant writer/verifier; no worker receives this database credential.

    `lease_authority` is mandatory. It must lock the B11 epoch row, not merely
    trust the worker's claimed number. All authority checks run in one DB
    transaction with grant insert or credential issue.
    """

    def __init__(self, connect: Callable, lease_authority: LeaseAuthority):
        if (not callable(connect) or lease_authority is None
                or not callable(getattr(lease_authority, 'require_current', None))):
            raise ValueError('A database and authoritative locking lease source are required')
        self._connect = connect
        self._leases = lease_authority

    @staticmethod
    def _job(cursor, context: TenantContext, job_id: str):
        cursor.execute(
            'SELECT hosting_controlplane.lock_job_scope(%s, %s, %s)',
            (context.organization_id, context.tenant_id, job_id))
        if cursor.fetchone() != (True,):
            raise GrantDenied('Job is unavailable in the worker tenant')
        cursor.execute(
            f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
            'WHERE organization_id = %s AND tenant_id = %s AND job_id = %s',
            (context.organization_id, context.tenant_id, job_id))
        row = cursor.fetchone()
        if row is None:
            raise GrantDenied('Job is unavailable in the worker tenant')
        job = _job(row)
        if job.status not in ('STARTED', 'RUNNING'):
            raise GrantDenied('A started, unheld workflow is required')
        return job

    def _authorize(self, cursor, context: TenantContext, identity: VerifiedWorkerIdentity,
                   job, *, operation_id: str, operation_kind: str,
                   operation_scope: PlanScope, lease_key: str, lease_epoch: int,
                   at: datetime) -> tuple[str, datetime, datetime]:
        _identity(context, identity, at)
        if operation_scope not in (job.source, job.destination):
            raise GrantDenied('Operation scope differs from the approved job')
        credential_ref, enrollment_expiry = _enrollment(
            cursor, context, identity, operation_scope, operation_kind, at)
        authority_postgres.revalidate_start(cursor, job, at)
        self._leases.require_current(
            cursor, context, lease_key=lease_key, lease_epoch=lease_epoch,
            job_id=job.job_id, operation_id=operation_id,
            scope=operation_scope, worker_subject=identity.subject)
        # The locks above may have waited past a certificate, approval, lease
        # or grant deadline. Re-read the database clock under those locks.
        cursor.execute('SELECT clock_timestamp()')
        current = cursor.fetchone()[0]
        _identity(context, identity, current)
        if enrollment_expiry <= current:
            raise GrantDenied('Worker enrollment expired while waiting for authority')
        authority_postgres.revalidate_start(cursor, job, current)
        self._leases.require_current(
            cursor, context, lease_key=lease_key, lease_epoch=lease_epoch,
            job_id=job.job_id, operation_id=operation_id,
            scope=operation_scope, worker_subject=identity.subject)
        return credential_ref, min(identity.expires_at, enrollment_expiry), current

    def issue_grant(self, context: TenantContext, identity: VerifiedWorkerIdentity,
                    request: GrantRequest) -> WorkerGrant:
        """Called only by trusted workflow activity after lease acquisition."""
        if not isinstance(request, GrantRequest):
            raise GrantDenied('A bound operation request is required')
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _context(cursor, context)
                cursor.execute('SELECT clock_timestamp()')
                at = cursor.fetchone()[0]
                job = self._job(cursor, context, request.job_id)
                _, identity_expiry, issued_at = self._authorize(
                    cursor, context, identity, job,
                    operation_id=request.operation_id,
                    operation_kind=request.operation_kind,
                    operation_scope=request.operation_scope,
                    lease_key=request.lease_key, lease_epoch=request.lease_epoch, at=at)
                # The authority check verifies every approval's validity at
                # issue time. Grant lifetime remains short and is rechecked
                # against approvals at each subsequent use.
                expires = min(issued_at + request.ttl, identity_expiry)
                if expires <= issued_at:
                    raise GrantDenied('Worker identity expired before grant issue')
                grant_id = uuid4().hex
                scope = request.operation_scope
                cursor.execute(
                    'INSERT INTO hosting_controlplane.worker_grants '
                    '(organization_id, tenant_id, grant_id, job_id, plan_id, '
                    'plan_revision, plan_digest, approval_ids, revocation_epoch, '
                    'worker_subject, certificate_sha256, step_id, operation_id, '
                    'operation_kind, site_id, security_domain_id, endpoint_id, '
                    'native_scope_id, platform_family, lease_key, lease_epoch, '
                    'issued_at, expires_at) VALUES '
                    '(%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, '
                    '%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (context.organization_id, context.tenant_id, grant_id,
                     job.job_id, job.plan_id, job.plan_revision, job.plan_digest,
                     json.dumps(job.approval_ids), job.revocation_epoch,
                     identity.subject, identity.certificate_sha256,
                     request.step_id, request.operation_id, request.operation_kind,
                     scope.site_id, scope.security_domain_id, scope.endpoint_id,
                     scope.native_scope_id, scope.platform_family,
                     request.lease_key, request.lease_epoch, issued_at, expires))
                return WorkerGrant(
                    grant_id, context.organization_id, context.tenant_id,
                    job.plan_id, job.plan_revision, job.plan_digest,
                    job.source, job.destination, identity.subject,
                    request.step_id, request.operation_id,
                    request.operation_kind, scope, request.lease_key,
                    request.lease_epoch, job.approval_ids,
                    job.revocation_epoch, issued_at, expires)

    @staticmethod
    def _load(cursor, context: TenantContext, grant_id: str):
        cursor.execute(
            'SELECT job_id, plan_id, plan_revision, plan_digest, approval_ids, '
            'revocation_epoch, worker_subject, certificate_sha256, step_id, '
            'operation_id, operation_kind, site_id, security_domain_id, '
            'endpoint_id, native_scope_id, platform_family, lease_key, '
            'lease_epoch, issued_at, expires_at '
            'FROM hosting_controlplane.worker_grants '
            'WHERE organization_id = %s AND tenant_id = %s AND grant_id = %s',
            (context.organization_id, context.tenant_id, grant_id))
        return cursor.fetchone()

    def with_authorized_reference(self, context: TenantContext,
                                  identity: VerifiedWorkerIdentity, grant_id: str,
                                  *, job_id: str, step_id: str,
                                  operation_id: str, operation_kind: str,
                                  operation_scope: PlanScope, lease_key: str,
                                  lease_epoch: int,
                                  use: Callable[[str, WorkerGrant, datetime], T]) -> T:
        """Recheck immediately before the external broker mints a handle.

        The callback runs under the database locks so a concurrent revocation,
        worker disable or epoch change cannot precede issuance. The native
        operation still needs B11's separate intent/reconciliation gate.
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                return self._verify_common(
                    cursor, context, identity, grant_id, job_id=job_id,
                    step_id=step_id, operation_id=operation_id,
                    operation_kind=operation_kind, operation_scope=operation_scope,
                    lease_key=lease_key, lease_epoch=lease_epoch, use=use)

    def _verify_common(self, cursor, context, identity, grant_id, *, job_id,
                       step_id, operation_id, operation_kind,
                       operation_scope, lease_key, lease_epoch, use):
        if (not isinstance(identity, VerifiedWorkerIdentity)
                or not isinstance(grant_id, str) or not _ID.fullmatch(grant_id)
                or not isinstance(job_id, str) or not _ID.fullmatch(job_id)
                or not isinstance(step_id, str) or not _ID.fullmatch(step_id)
                or not isinstance(operation_id, str) or not _ID.fullmatch(operation_id)
                or operation_kind not in ALLOWED_OPERATIONS
                or not isinstance(operation_scope, PlanScope)
                or not isinstance(lease_key, str) or not _ID.fullmatch(lease_key)
                or type(lease_epoch) is not int or lease_epoch < 1
                or not callable(use)):
            raise GrantDenied('Exact grant and operation binding are required')
        _context(cursor, context)
        cursor.execute('SELECT clock_timestamp()')
        at = cursor.fetchone()[0]
        row = self._load(cursor, context, grant_id)
        if row is None:
            raise GrantDenied('No worker grant is visible')
        (stored_job, plan_id, revision, digest, approvals, epoch,
         subject, fingerprint, stored_step, stored_operation,
         stored_kind, site, wsd, endpoint, native, family,
         stored_lease, stored_epoch, issued, expires) = row
        approvals = tuple(json.loads(approvals) if isinstance(approvals, str) else approvals)
        if (stored_job, subject, fingerprint, stored_step,
            stored_operation, stored_kind, site, wsd, endpoint,
            native, family, stored_lease, stored_epoch) != (
                job_id, identity.subject, identity.certificate_sha256,
                step_id, operation_id, operation_kind,
                operation_scope.site_id, operation_scope.security_domain_id,
                operation_scope.endpoint_id, operation_scope.native_scope_id,
                operation_scope.platform_family, lease_key, lease_epoch):
            raise GrantDenied('Grant belongs to another worker, scope or operation')
        _identity(context, identity, at)
        if not _aware(issued) or not _aware(expires) or issued > at or expires <= at:
            raise GrantDenied('Worker grant is expired or not yet active')
        job = self._job(cursor, context, job_id)
        if (job.plan_id, job.plan_revision, job.plan_digest,
            job.approval_ids, job.revocation_epoch) != (
                plan_id, revision, digest, approvals, epoch):
            raise GrantDenied('Grant differs from the immutable job authority')
        reference, identity_expiry, checked_at = self._authorize(
            cursor, context, identity, job, operation_id=operation_id,
            operation_kind=operation_kind, operation_scope=operation_scope,
            lease_key=lease_key, lease_epoch=lease_epoch, at=at)
        if expires <= checked_at:
            raise GrantDenied('Worker grant expired while waiting for authority')
        grant = WorkerGrant(grant_id, context.organization_id,
                            context.tenant_id, plan_id, revision, digest,
                            job.source, job.destination, subject, step_id,
                            operation_id, operation_kind, operation_scope,
                            lease_key, lease_epoch, approvals, epoch,
                            issued, expires)
        return use(reference, grant, min(expires, identity_expiry))

    def verify_intent(self, cursor, context: TenantContext, *, grant_id: str,
                      job_id: str, step_id: str, operation_id: str,
                      operation_kind: str, operation_scope: PlanScope,
                      worker_identity: VerifiedWorkerIdentity,
                      lease_key: str, lease_epoch: int) -> WorkerGrant:
        """B11 may call under its transaction before recording an intent.

        Construction requires B11's lease authority. The caller owns the
        transaction, including the native intent write and all row locks.
        """
        def capture(_reference: str, grant: WorkerGrant, _expiry: datetime):
            return grant

        # A B11 caller needs to use its own cursor and transaction. Reuse the
        # same verification path without starting another database connection.
        return self._verify_common(
            cursor, context, worker_identity, grant_id, job_id=job_id,
            step_id=step_id, operation_id=operation_id,
            operation_kind=operation_kind, operation_scope=operation_scope,
            lease_key=lease_key, lease_epoch=lease_epoch, use=capture)

class CredentialBroker:
    """Adapter boundary; no static credentials, secret strings or native calls."""

    def __init__(self, identities: WorkerIdentityVerifier,
                 grants: PostgresWorkerGrants,
                 issuer: EphemeralCredentialIssuer):
        if any(port is None for port in (identities, grants, issuer)):
            raise ValueError('Identity verifier, grant store and issuer are mandatory')
        self._identities = identities
        self._grants = grants
        self._issuer = issuer

    def acquire(self, transport_evidence: object, context: TenantContext,
                grant_id: str, *, job_id: str, step_id: str,
                operation_id: str, operation_kind: str,
                operation_scope: PlanScope, lease_key: str,
                lease_epoch: int) -> object:
        identity = self._identities.verify(transport_evidence)
        if not isinstance(identity, VerifiedWorkerIdentity):
            raise GrantDenied('Independent worker identity verification is required')
        return self._grants.with_authorized_reference(
            context, identity, grant_id, job_id=job_id, step_id=step_id,
            operation_id=operation_id, operation_kind=operation_kind,
            operation_scope=operation_scope, lease_key=lease_key,
            lease_epoch=lease_epoch,
            use=lambda reference, grant, expiry: self._issuer.issue(
                reference, grant=grant, expires_at=expiry))
