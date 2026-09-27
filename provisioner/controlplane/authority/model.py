"""Immutable authority values for exact plan revisions and native scopes.

Construction of a value here is not proof of authentication or approval. Only
the service, with independently verified identity and authoritative stores, may
use these values to make an authorization decision. Never deserialize an HTTP
body into VerifiedPrincipal, PlanApproval, AuthorizedPlan or WorkerGrant.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from provisioner.domain.enterprise_records import validate_record

_DIGEST = re.compile(r'^[0-9a-f]{64}$')


def _aware(value: datetime) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


@dataclass(frozen=True)
class PlanScope:
    organization_id: str
    tenant_id: str
    site_id: str
    security_domain_id: str
    endpoint_id: str
    native_scope_id: str
    platform_family: str

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) and value.strip() for value in vars(self).values()):
            raise ValueError('A native scope requires all seven nonempty identities')

    @classmethod
    def from_record(cls, scope: dict) -> PlanScope:
        return cls(scope['organizationId'], scope['tenantId'], scope['locationId'],
                   scope['securityDomainId'], scope['endpointId'],
                   scope['nativeScopeId'], scope['platformFamily'])


@dataclass(frozen=True)
class PortfolioScope:
    """Exact tenant/WSD scope for a workload that has no native site yet."""

    organization_id: str
    tenant_id: str
    security_domain_id: str

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) and value.strip() for value in vars(self).values()):
            raise ValueError('Portfolio scope requires organization, tenant and WSD')


@dataclass(frozen=True)
class RoleGrant:
    role: str
    scope: PlanScope | PortfolioScope
    expires_at: datetime

    def __post_init__(self) -> None:
        if (not isinstance(self.role, str) or not self.role
                or not isinstance(self.scope, (PlanScope, PortfolioScope))
                or not _aware(self.expires_at)):
            raise ValueError('Invalid scoped role grant')


@dataclass(frozen=True)
class VerifiedPrincipal:
    """Result of a trusted IdP verifier, never client-submitted identity claims."""

    subject: str
    organization_id: str
    tenant_id: str
    kind: str  # HUMAN or WORKER
    issued_at: datetime
    expires_at: datetime
    step_up_at: datetime | None
    grants: tuple[RoleGrant, ...]

    def __post_init__(self) -> None:
        if (not self.subject or not self.organization_id or not self.tenant_id
                or self.kind not in ('HUMAN', 'WORKER')
                or not _aware(self.issued_at) or not _aware(self.expires_at)
                or self.expires_at <= self.issued_at
                or (self.step_up_at is not None and
                    (not _aware(self.step_up_at) or self.step_up_at > self.expires_at))
                or not isinstance(self.grants, tuple)
                or any(not isinstance(grant, RoleGrant) or
                       (grant.scope.organization_id, grant.scope.tenant_id) !=
                       (self.organization_id, self.tenant_id)
                       for grant in self.grants)):
            raise ValueError('Invalid verified principal')


@dataclass(frozen=True)
class FrozenPlan:
    organization_id: str
    tenant_id: str
    plan_id: str
    revision: int
    digest: str
    author_subject: str
    source: PlanScope
    destination: PlanScope

    @classmethod
    def from_record(cls, record: dict, *, author_subject: str) -> FrozenPlan:
        """Called only on a persisted plan with server-owned author provenance."""
        if not isinstance(record, dict) or record.get('kind') != 'MigrationPlan':
            raise ValueError('Expected a migration plan')
        if validate_record(record):
            raise ValueError('Invalid plan or content digest')
        if not isinstance(author_subject, str) or not author_subject:
            raise ValueError('A plan needs a recorded author')
        meta, spec = record['metadata'], record['spec']
        return cls(meta['organizationId'], meta['tenantId'], meta['planId'],
                   meta['revision'], meta['planDigest'], author_subject,
                   PlanScope.from_record(spec['source']),
                   PlanScope.from_record(spec['destination']))

    def __post_init__(self) -> None:
        if (not self.organization_id or not self.tenant_id or not self.plan_id
                or type(self.revision) is not int or self.revision < 1
                or not _DIGEST.fullmatch(self.digest) or not self.author_subject
                or any((scope.organization_id, scope.tenant_id) !=
                       (self.organization_id, self.tenant_id)
                       for scope in (self.source, self.destination))):
            raise ValueError('Invalid exact plan binding')


@dataclass(frozen=True)
class PlanApproval:
    approval_id: str
    organization_id: str
    tenant_id: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    role: str
    scope: PlanScope
    approver_subject: str
    issued_at: datetime
    expires_at: datetime
    revocation_epoch: int


@dataclass(frozen=True)
class ApprovalSnapshot:
    """An authoritative read of one plan's monotonic revocation epoch."""

    organization_id: str
    tenant_id: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    revocation_epoch: int
    approvals: tuple[PlanApproval, ...]


@dataclass(frozen=True)
class AuthorizedPlan:
    """Short-lived admission decision; B09 must recheck epoch atomically."""

    organization_id: str
    tenant_id: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    source: PlanScope
    destination: PlanScope
    approval_ids: tuple[str, ...]
    revocation_epoch: int
    expires_at: datetime
    actor_subject: str


@dataclass(frozen=True)
class WorkerGrant:
    """B10 grant shape; a job operation may use only the named lease and scope.

    The grant is issued and retrieved only by a trusted authority ledger. A
    serialized copy is never accepted as proof for a worker operation.
    """

    grant_id: str
    organization_id: str
    tenant_id: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    source: PlanScope
    destination: PlanScope
    worker_subject: str
    step_id: str
    operation_id: str
    operation_kind: str
    operation_scope: PlanScope
    lease_key: str
    lease_epoch: int
    approval_ids: tuple[str, ...]
    revocation_epoch: int
    issued_at: datetime
    expires_at: datetime
