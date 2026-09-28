"""Administrator-authorized enrollment of enterprise-issued worker certificates.

The worker proves possession through a completed mTLS handshake with the pinned
PKI verifier. An independent operator authorization is required to add or
revoke its persisted identity; self-registration is never available.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Protocol

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence import TenantContext

from .grants import (ALLOWED_OPERATIONS, GrantDenied, VerifiedWorkerIdentity,
                     WorkerIdentityVerifier, _ID, _context, _identity)


@dataclass(frozen=True)
class WorkerCapability:
    scope: PlanScope
    operation_kind: str
    credential_ref: str

    def __post_init__(self) -> None:
        if (not isinstance(self.scope, PlanScope)
                or self.operation_kind not in ALLOWED_OPERATIONS
                or not isinstance(self.credential_ref, str)
                or not self.credential_ref.startswith('vault:')
                or not _ID.fullmatch(self.credential_ref[6:])):
            raise ValueError('An exact scope and opaque Vault role reference are required')


@dataclass(frozen=True)
class EnrollmentDecision:
    """Identity and ticket reference returned by the trusted IAM authorizer."""

    actor_id: str
    correlation_id: str
    approval_id: str

    def __post_init__(self) -> None:
        if any(not isinstance(item, str) or not _ID.fullmatch(item)
               for item in (self.actor_id, self.correlation_id, self.approval_id)):
            raise ValueError('Administrative audit references must be bounded identifiers')


class EnrollmentAuthorizer(Protocol):
    def require_enrollment(self, approval: object, context: TenantContext,
                           identity: VerifiedWorkerIdentity,
                           capabilities: tuple[WorkerCapability, ...]) -> EnrollmentDecision:
        """Verify an independent, audited administrative enrollment approval."""

    def require_revocation(self, approval: object, context: TenantContext,
                           worker_subject: str,
                           certificate_sha256: str | None) -> EnrollmentDecision:
        """Verify an independent, audited administrative revocation approval."""


def _audit(cursor, context: TenantContext, decision: EnrollmentDecision,
           action: str, record_kind: str, record_id: str, revision: int,
           details: dict) -> None:
    safe_details = {'approval_id': decision.approval_id, **details}
    digest = hashlib.sha256(json.dumps(
        [action, record_kind, record_id, revision, safe_details],
        sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    cursor.execute(
        'INSERT INTO hosting_controlplane.audit_events '
        '(organization_id, tenant_id, actor_id, correlation_id, action, '
        'record_kind, record_id, revision, record_digest, details) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)',
        (context.organization_id, context.tenant_id, decision.actor_id,
         decision.correlation_id, action, record_kind, record_id, revision,
         digest, json.dumps(safe_details, sort_keys=True)))


class PostgresWorkerEnrollment:
    """Write identities with a dedicated enrollment role, never the worker role.

    ``approval`` is an opaque ticket validated by the injected enterprise IAM
    authorizer. The SQL role must have only the enrollment table privileges in
    the migration README; credentials and tickets are absent from job history.
    """

    def __init__(self, connect: Callable, verifier: WorkerIdentityVerifier,
                 authorizer: EnrollmentAuthorizer):
        if (not callable(connect) or verifier is None or authorizer is None
                or not callable(getattr(verifier, 'verify', None))
                or not callable(getattr(authorizer, 'require_enrollment', None))
                or not callable(getattr(authorizer, 'require_revocation', None))):
            raise ValueError('Enrollment database, mTLS verifier and IAM authorizer are required')
        self._connect = connect
        self._verifier = verifier
        self._authorizer = authorizer

    def enroll(self, transport_evidence: object, context: TenantContext,
               approval: object, *, capabilities: tuple[WorkerCapability, ...] = ()) -> VerifiedWorkerIdentity:
        """Add a first certificate or rotate one for the same worker subject.

        Capabilities may be granted on the first enrollment only. An existing
        worker retains its scoped capabilities during rotation; privilege
        changes require revocation and explicit re-enrollment with a new
        subject, never an implicit certificate update.
        """
        identity = self._verifier.verify(transport_evidence)
        if not isinstance(identity, VerifiedWorkerIdentity):
            raise GrantDenied('A PKI-verified worker mTLS peer is required')
        if (not isinstance(context, TenantContext)
                or (context.organization_id, context.tenant_id) !=
                (identity.organization_id, identity.tenant_id)
                or not isinstance(capabilities, tuple)
                or any(not isinstance(cap, WorkerCapability)
                       or (cap.scope.organization_id, cap.scope.tenant_id,
                           cap.scope.site_id) !=
                       (identity.organization_id, identity.tenant_id, identity.site_id)
                       for cap in capabilities)
                or len({(cap.scope, cap.operation_kind) for cap in capabilities}) != len(capabilities)):
            raise GrantDenied('Worker capabilities must match the mTLS tenant and site')
        decision = self._authorizer.require_enrollment(
            approval, context, identity, capabilities)
        if not isinstance(decision, EnrollmentDecision):
            raise GrantDenied('A verified administrative decision is required')
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _context(cursor, context)
                cursor.execute('SELECT clock_timestamp()')
                now: datetime = cursor.fetchone()[0]
                _identity(context, identity, now)
                cursor.execute(
                    'SELECT site_id, revoked_at FROM hosting_controlplane.worker_enrollments '
                    'WHERE organization_id = %s AND tenant_id = %s AND worker_subject = %s '
                    'FOR UPDATE',
                    (context.organization_id, context.tenant_id, identity.subject))
                existing = cursor.fetchone()
                if existing is None:
                    if not capabilities:
                        raise GrantDenied('Initial enrollment needs explicit capabilities')
                    cursor.execute(
                        'INSERT INTO hosting_controlplane.worker_enrollments '
                        '(organization_id, tenant_id, worker_subject, site_id, '
                        'certificate_sha256, expires_at) VALUES (%s, %s, %s, %s, %s, %s)',
                        (context.organization_id, context.tenant_id, identity.subject,
                         identity.site_id, identity.certificate_sha256, identity.expires_at))
                    for cap in capabilities:
                        scope = cap.scope
                        cursor.execute(
                            'INSERT INTO hosting_controlplane.worker_capabilities '
                            '(organization_id, tenant_id, worker_subject, site_id, '
                            'security_domain_id, endpoint_id, native_scope_id, '
                            'platform_family, operation_kind, credential_ref) '
                            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                            (context.organization_id, context.tenant_id, identity.subject,
                             identity.site_id, scope.security_domain_id, scope.endpoint_id,
                             scope.native_scope_id, scope.platform_family,
                             cap.operation_kind, cap.credential_ref))
                elif existing != (identity.site_id, None) or capabilities:
                    raise GrantDenied('Rotation cannot change site or capabilities or revive a revoked worker')
                else:
                    # Lock all active versions before revoking, so grant issue
                    # cannot cross this transaction with the old certificate.
                    cursor.execute(
                        'UPDATE hosting_controlplane.worker_certificate_versions '
                        'SET revoked_at = clock_timestamp() '
                        'WHERE organization_id = %s AND tenant_id = %s '
                        'AND worker_subject = %s AND revoked_at IS NULL',
                        (context.organization_id, context.tenant_id, identity.subject))
                cursor.execute(
                    'INSERT INTO hosting_controlplane.worker_certificate_versions '
                    '(organization_id, tenant_id, worker_subject, certificate_sha256, '
                    'expires_at) VALUES (%s, %s, %s, %s, %s)',
                    (context.organization_id, context.tenant_id, identity.subject,
                     identity.certificate_sha256, identity.expires_at))
                _audit(cursor, context, decision,
                       'WORKER_CERT_ENROLL' if existing is None else 'WORKER_CERT_ROTATE',
                       'WorkerCertificate', identity.certificate_sha256, 1,
                       {'worker_subject': identity.subject, 'site_id': identity.site_id,
                        **({'capability_count': len(capabilities)}
                           if existing is None else {})})
        return identity

    def revoke(self, context: TenantContext, approval: object, *,
               worker_subject: str, certificate_sha256: str | None = None) -> None:
        if (not isinstance(context, TenantContext)
                or not isinstance(worker_subject, str) or not _ID.fullmatch(worker_subject)
                or (certificate_sha256 is not None and
                    (not isinstance(certificate_sha256, str)
                     or len(certificate_sha256) != 64
                     or any(c not in '0123456789abcdef' for c in certificate_sha256)))):
            raise GrantDenied('Exact worker identity is required for revocation')
        decision = self._authorizer.require_revocation(
            approval, context, worker_subject, certificate_sha256)
        if not isinstance(decision, EnrollmentDecision):
            raise GrantDenied('A verified administrative decision is required')
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _context(cursor, context)
                if certificate_sha256 is None:
                    cursor.execute(
                        'UPDATE hosting_controlplane.worker_enrollments '
                        'SET revoked_at = clock_timestamp() '
                        'WHERE organization_id = %s AND tenant_id = %s '
                        'AND worker_subject = %s AND revoked_at IS NULL',
                        (context.organization_id, context.tenant_id, worker_subject))
                else:
                    cursor.execute(
                        'UPDATE hosting_controlplane.worker_certificate_versions '
                        'SET revoked_at = clock_timestamp() '
                        'WHERE organization_id = %s AND tenant_id = %s '
                        'AND worker_subject = %s AND certificate_sha256 = %s '
                        'AND revoked_at IS NULL',
                        (context.organization_id, context.tenant_id, worker_subject,
                         certificate_sha256))
                if cursor.rowcount != 1:
                    raise GrantDenied('Worker or active certificate is unavailable')
                _audit(cursor, context, decision,
                       'WORKER_REVOKE' if certificate_sha256 is None else
                       'WORKER_CERT_REVOKE',
                       'Worker' if certificate_sha256 is None else 'WorkerCertificate',
                       worker_subject if certificate_sha256 is None else certificate_sha256,
                       1 if certificate_sha256 is None else 2,
                       {'worker_subject': worker_subject})
