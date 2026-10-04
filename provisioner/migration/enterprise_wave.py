"""One independently enrolled budget and fair turn over existing tenant waves.

The pool contains no jobs, outbox or independent native queue. Admission still
commits through B09 and the original wave member. A short eligibility ticket
holds only a scheduling turn; admitted/uncertain charges never expire with it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

from provisioner.controlplane.jobs.repository import _digest
from provisioner.controlplane.persistence import TenantContext

from .wave_schedule import (WaveBudget, WaveDomain, WaveHeld, _identifier,
                            _instant, _parse_instant, _require, _sha)

FORMAT = 'hosting-enterprise-wave-pool/1'
MAX_DOMAINS = 256
TICKET_SECONDS = 30


@dataclass(frozen=True)
class PoolDomain:
    organization_id: str
    tenant_id: str
    domain_id: str
    domain_digest: str
    risk_groups: tuple[tuple[str, str], ...]

    def __post_init__(self):
        for value in (self.organization_id, self.tenant_id, self.domain_id):
            _identifier(value)
        _sha(self.domain_digest)
        _require(type(self.risk_groups) is tuple and 1 <= len(self.risk_groups) <= 64,
                 'Every pooled native domain needs an explicit physical risk map')
        local = set()
        for source, destination in self.risk_groups:
            _identifier(source)
            _identifier(destination)
            _require(source not in local, 'A native risk group cannot be enrolled twice')
            local.add(source)

    @classmethod
    def from_domain(cls, domain: WaveDomain, risk_groups: dict[str, str]):
        _require(isinstance(domain, WaveDomain) and type(risk_groups) is dict
                 and set(risk_groups) == set(dict(domain.shared_risk_limits)),
                 'The pool must map every independently enrolled native risk group')
        return cls(domain.organization_id, domain.tenant_id, domain.domain_id,
                   domain.digest, tuple(sorted(risk_groups.items())))

    @property
    def key(self):
        return self.organization_id, self.tenant_id, self.domain_id

    def to_record(self):
        return {'organizationId': self.organization_id, 'tenantId': self.tenant_id,
                'domainId': self.domain_id, 'domainDigest': self.domain_digest,
                'riskGroups': dict(sorted(self.risk_groups))}


@dataclass(frozen=True)
class EnterpriseWavePool:
    pool_id: str
    domains: tuple[PoolDomain, ...]
    budget: WaveBudget
    shared_risk_limits: tuple[tuple[str, int], ...]
    native_budget_evidence_digest: str
    observed_at: datetime
    expires_at: datetime

    def __post_init__(self):
        _identifier(self.pool_id)
        _require(type(self.domains) is tuple and 2 <= len(self.domains) <= MAX_DOMAINS
                 and all(isinstance(row, PoolDomain) for row in self.domains),
                 'An enterprise pool needs a bounded complete domain inventory')
        _require(len({row.key for row in self.domains}) == len(self.domains),
                 'Duplicate pooled domain')
        _require(len({row.key[:2] for row in self.domains}) >= 2,
                 'Enterprise fairness needs at least two distinct tenant authorities')
        _require(isinstance(self.budget, WaveBudget), 'Exact aggregate wave budget required')
        groups = {group for row in self.domains for _, group in row.risk_groups}
        _require(type(self.shared_risk_limits) is tuple
                 and len(self.shared_risk_limits) == len(groups)
                 and set(dict(self.shared_risk_limits)) == groups,
                 'Every physical risk group needs exactly one aggregate cap')
        for group, cap in self.shared_risk_limits:
            _identifier(group)
            _require(type(cap) is int and 1 <= cap <= self.budget.risk_units,
                     'A physical risk cap must fit the aggregate risk budget')
        _sha(self.native_budget_evidence_digest)
        _instant(self.observed_at)
        _instant(self.expires_at)
        _require(self.observed_at < self.expires_at
                 <= self.observed_at + timedelta(days=31),
                 'The enterprise native budget needs a finite reviewed lifetime')

    def to_record(self):
        return {'format': FORMAT, 'poolId': self.pool_id,
                'domains': [row.to_record() for row in sorted(self.domains, key=lambda d: d.key)],
                'budget': asdict(self.budget),
                'sharedRiskLimits': dict(sorted(self.shared_risk_limits)),
                'nativeBudgetEvidenceDigest': self.native_budget_evidence_digest,
                'observedAt': self.observed_at.isoformat(),
                'expiresAt': self.expires_at.isoformat()}

    @property
    def digest(self):
        return _digest(self.to_record())

    @classmethod
    def from_record(cls, value):
        _require(type(value) is dict and set(value) == {
            'format', 'poolId', 'domains', 'budget', 'sharedRiskLimits',
            'nativeBudgetEvidenceDigest', 'observedAt', 'expiresAt'}
            and value['format'] == FORMAT, 'Exact enterprise pool record required')
        _require(type(value['domains']) is list and type(value['budget']) is dict
                 and set(value['budget']) == set(WaveBudget.__dataclass_fields__)
                 and type(value['sharedRiskLimits']) is dict,
                 'Malformed enterprise pool budget or domain inventory')
        rows = []
        for row in value['domains']:
            _require(type(row) is dict and set(row) == {
                'organizationId', 'tenantId', 'domainId', 'domainDigest', 'riskGroups'}
                and type(row['riskGroups']) is dict, 'Exact pooled native domain required')
            rows.append(PoolDomain(row['organizationId'], row['tenantId'],
                row['domainId'], row['domainDigest'], tuple(sorted(row['riskGroups'].items()))))
        return cls(value['poolId'], tuple(rows), WaveBudget(**value['budget']),
            tuple(sorted(value['sharedRiskLimits'].items())), value['nativeBudgetEvidenceDigest'],
            _parse_instant(value['observedAt']), _parse_instant(value['expiresAt']))


def fair_tenant_order(tenants, last_tenant=None):
    """One turn per verified tenant, independent of its domain/wave count."""
    _require(type(tenants) in (tuple, list) and len(tenants) <= MAX_DOMAINS,
             'Bounded tenant fairness inventory required')
    keys = set()
    for tenant in tenants:
        _require(type(tenant) is tuple and len(tenant) == 2,
                 'Exact organization and tenant authority required')
        for value in tenant:
            _identifier(value)
        keys.add(tenant)
    if last_tenant is not None:
        _require(type(last_tenant) is tuple and len(last_tenant) == 2,
                 'Exact prior tenant turn required')
        for value in last_tenant:
            _identifier(value)
    return tuple(sorted(key for key in keys if last_tenant is not None and key > last_tenant)
                 + sorted(key for key in keys if last_tenant is None or key <= last_tenant))


def require_pool_turn(cursor, context: TenantContext, domain: WaveDomain, state,
                      principal, authorization, now: datetime) -> bool:
    """Refresh eligibility only after current member proof and exact IAM checks.

    The database validates the immutable pool/domain/member, current window,
    aggregate retained charges and tenant turn again during the member UPDATE.
    Returning False commits no job or native claim, only the bounded ticket.
    """
    _require(isinstance(context, TenantContext) and isinstance(domain, WaveDomain),
             'Actual tenant and native scheduling owners required')
    expiry = min(now + timedelta(seconds=TICKET_SECONDS), principal.expires_at,
                 authorization.expires_at, domain.expires_at, state.member.window_end)
    _require(expiry > now, 'Current wave admission authority has expired')
    cursor.execute('SELECT hosting_controlplane.migration_wave_pool_turn(%s,%s,%s,%s,%s,%s,%s)',
        (context.organization_id, context.tenant_id, domain.domain_id,
         state.schedule_digest, state.member.member_id, principal.subject, expiry))
    row = cursor.fetchone()
    _require(row is not None and type(row[0]) is bool, 'Enterprise scheduling owner is unavailable')
    return row[0]
