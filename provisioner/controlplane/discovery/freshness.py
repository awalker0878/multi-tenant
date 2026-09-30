"""Read-only inventory age and collection-health projection, not qualification.

The newest persisted generation is used even when an older one reported better
coverage. Age, reported collection completeness and independent native visibility
remain separate; none authorizes scheduling, collection or execution.
"""
from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence.store import TenantContext
from .model import _id, _utc
from .persistence import DiscoveryRepository, StoredGeneration


_SHA = re.compile(r'^[0-9a-f]{64}$')

def _sha(value):
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


class FreshnessUnavailable(RuntimeError):
    """Stored metadata or the monitoring clock could not be verified."""


class FreshnessChanged(RuntimeError):
    """Inventory changed between the two bounded metadata reads."""


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    """Server-owned monitoring intervals, not an SLA or a placement override."""
    refresh_after_seconds: int = 3600
    max_age_seconds: int = 86400

    def __post_init__(self):
        if (type(self.refresh_after_seconds) is not int
                or type(self.max_age_seconds) is not int
                or not 1 <= self.refresh_after_seconds <= self.max_age_seconds <= 604800):
            raise ValueError('Bounded server-owned freshness intervals are required')

    def document(self) -> dict:
        return {'format': 'hosting-discovery-freshness-policy/1',
                'refreshAfterSeconds': self.refresh_after_seconds,
                'maxAgeSeconds': self.max_age_seconds}


def _metadata(row, ctx, scope, environment_id):
    if row is None:
        return
    if (not isinstance(row, StoredGeneration) or row.scope != scope
            or row.environment_id != environment_id
            or (row.scope.organization_id, row.scope.tenant_id) !=
               (ctx.organization_id, ctx.tenant_id)
            or type(row.generation) is not int or not 1 <= row.generation < 2**63
            or not _id(row.campaign_id) or not _sha(row.authorization_digest)
            or not _sha(row.result_digest) or not _utc(row.captured_at)
            or row.completeness not in ('COMPLETE', 'PARTIAL', 'UNKNOWN')
            or type(row.object_count) is not int or not 0 <= row.object_count < 2**63):
        raise FreshnessUnavailable('Invalid exact-scope generation metadata')
    for values in (row.collection_errors, row.missing_privileges):
        if (not isinstance(values, tuple) or len(values) > 1024
                or any(not isinstance(v, str) or not 1 <= len(v) <= 512
                       or any(ord(c) < 32 or ord(c) == 127 for c in v) for v in values)):
            raise FreshnessUnavailable('Invalid collection-health metadata')
    if row.completeness == 'COMPLETE' and (row.collection_errors or row.missing_privileges):
        raise FreshnessUnavailable('Complete collection contradicts its error metadata')


class DiscoveryFreshnessService:
    def __init__(self, repository: DiscoveryRepository, *,
                 policy: FreshnessPolicy = FreshnessPolicy(),
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        if (not isinstance(repository, DiscoveryRepository)
                or not isinstance(policy, FreshnessPolicy) or not callable(clock)):
            raise TypeError('A discovery repository, policy and clock are required')
        self._repository, self._policy, self._clock = repository, policy, clock

    def inspect(self, ctx: TenantContext, scope: PlanScope, environment_id: str, *,
                authorize: Callable[[PlanScope, datetime], None]) -> dict:
        """Two reads with live access checks; no silent retry or older fallback.

        Equal metadata is a bounded live recheck, not an atomic snapshot of trust,
        inventory and native systems. No raw observation hydration is performed.
        """
        DiscoveryRepository._require_scope(ctx, scope, environment_id)
        if not callable(authorize):
            raise TypeError('A current exact-scope authorizer is required')
        previous = None

        def now():
            nonlocal previous
            at = self._clock()
            if not _utc(at) or previous is not None and at < previous:
                raise FreshnessUnavailable('Freshness clock is invalid or regressed')
            previous = at
            return at

        authorize(scope, now())
        # Freeze values before callbacks: a reused repository object must not
        # change either side of the comparison or the validated response later.
        first = deepcopy(self._repository.latest_generation(ctx, scope, environment_id))
        authorize(scope, now())
        _metadata(first, ctx, scope, environment_id)
        latest = deepcopy(self._repository.latest_generation(ctx, scope, environment_id))
        authorize(scope, now())  # Includes missing inventories and unchanged rows.
        _metadata(latest, ctx, scope, environment_id)
        checked = now()
        if first != latest:
            raise FreshnessChanged('Inventory changed; explicitly inspect again')

        observation = None
        age = None
        issues = []
        due = True
        if latest is None:
            freshness = 'MISSING'
            issues.append('INVENTORY_MISSING')
        else:
            observation = {'generation': latest.generation, 'campaignId': latest.campaign_id,
                'authorizationDigest': latest.authorization_digest, 'resultDigest': latest.result_digest,
                'capturedAt': latest.captured_at.isoformat(), 'completeness': latest.completeness,
                'objectCount': latest.object_count, 'collectionErrorCount': len(latest.collection_errors),
                'missingPrivilegeCount': len(latest.missing_privileges)}
            delta = checked - latest.captured_at
            if delta < timedelta(0):
                freshness = 'FUTURE_CAPTURE'
                issues.append('INVENTORY_CAPTURE_IN_FUTURE')
            else:
                age = ((delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds)
                freshness = 'STALE' if delta > timedelta(seconds=self._policy.max_age_seconds) else 'FRESH'
                due = delta >= timedelta(seconds=self._policy.refresh_after_seconds)
                if freshness == 'STALE':
                    issues.append('INVENTORY_STALE')
                elif due:
                    issues.append('INVENTORY_REFRESH_DUE')
            if latest.completeness != 'COMPLETE':
                issues.append('COLLECTION_' + latest.completeness)
            if latest.collection_errors:
                issues.append('COLLECTION_ERRORS_PRESENT')
            if latest.missing_privileges:
                issues.append('MISSING_PRIVILEGES')
        issues.append('NATIVE_VISIBILITY_UNVERIFIED')
        return {'format': 'hosting-discovery-freshness/1', 'environmentId': environment_id,
            'scope': dict(vars(scope)), 'checkedAt': checked.isoformat(), 'policy': self._policy.document(),
            'observation': observation, 'freshness': freshness, 'ageMicroseconds': age,
            'refreshDue': due, 'issues': issues, 'consistency': 'LIVE_METADATA_RECHECKS',
            'integrityVerification': 'METADATA_ONLY', 'nativeVisibilityVerified': False,
            'collectionRequested': False, 'executionAuthorized': False}
