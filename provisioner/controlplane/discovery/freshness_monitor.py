"""Periodic inventory-health evaluation over retained freshness checks.

This module does not collect inventory and does not deliver notifications.  It reuses
``FreshnessHistoryRepository`` as the sole durable monitoring record.  A deterministic
check ID per target/time slot makes process restarts idempotent: repeating a slot reads
the original retained check instead of resampling it.  Alert intents are pure
projections of that retained check and therefore can be recreated without another
native read or database write.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import time
from typing import Callable, Iterable

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence.store import AuditContext, TenantContext
from .freshness_history import FreshnessHistoryRepository
from .model import _id, _json, _utc

_MAX_SLOT = 2**63 - 1
_ACTIONABLE = {
    'INVENTORY_MISSING': 'CRITICAL',
    'INVENTORY_CAPTURE_IN_FUTURE': 'CRITICAL',
    'INVENTORY_STALE': 'CRITICAL',
    'MISSING_PRIVILEGES': 'CRITICAL',
    'INVENTORY_REFRESH_DUE': 'WARNING',
    'COLLECTION_PARTIAL': 'WARNING',
    'COLLECTION_UNKNOWN': 'WARNING',
    'COLLECTION_ERRORS_PRESENT': 'WARNING',
}
_SEVERITY = {'WARNING': 1, 'CRITICAL': 2}


@dataclass(frozen=True, slots=True)
class FreshnessMonitorPolicy:
    """Finite local cadence controls, not an SLA or an alert-delivery contract."""

    interval_seconds: int = 300
    max_targets: int = 256
    max_cycles: int = 288

    def __post_init__(self):
        if (type(self.interval_seconds) is not int or not 30 <= self.interval_seconds <= 86400
                or type(self.max_targets) is not int or not 1 <= self.max_targets <= 2048
                or type(self.max_cycles) is not int or not 1 <= self.max_cycles <= 2016):
            raise ValueError('Bounded freshness-monitor cadence and work limits are required')

    def document(self):
        return {'format': 'hosting-discovery-freshness-monitor-policy/1',
                'intervalSeconds': self.interval_seconds,
                'maxTargets': self.max_targets,
                'maxCycles': self.max_cycles}


@dataclass(frozen=True, slots=True)
class FreshnessMonitorTarget:
    environment_id: str
    scope: PlanScope

    def __post_init__(self):
        if not _id(self.environment_id) or not isinstance(self.scope, PlanScope):
            raise ValueError('An exact environment and native scope are required')

    def identity(self):
        return {'environmentId': self.environment_id, 'scope': dict(vars(self.scope))}


def _slot(at: datetime, interval: int) -> int:
    if not _utc(at):
        raise ValueError('UTC monitor time is required')
    microseconds = ((at - datetime(1970, 1, 1, tzinfo=timezone.utc)).days * 86400
                    + (at - datetime(1970, 1, 1, tzinfo=timezone.utc)).seconds) * 1000000
    microseconds += at.microsecond
    if microseconds < 0:
        raise ValueError('Monitor time predates the supported epoch')
    value = microseconds // (interval * 1000000)
    if not 0 <= value <= _MAX_SLOT:
        raise ValueError('Monitor slot exceeds its bound')
    return value


def check_id(target: FreshnessMonitorTarget, policy: FreshnessMonitorPolicy,
             scheduled_at: datetime) -> str:
    """Stable ID for one target/interval; retrying the slot cannot resample it."""
    slot = _slot(scheduled_at, policy.interval_seconds)
    binding = {'format': 'hosting-discovery-freshness-monitor-slot/1',
               'target': target.identity(), 'intervalSeconds': policy.interval_seconds,
               'slot': slot}
    suffix = hashlib.sha256(_json(binding).encode('ascii')).hexdigest()[:24]
    value = f'monitor-{slot}-{suffix}'
    if not _id(value):
        raise ValueError('Derived monitor check ID is invalid')
    return value


def alert_projection(check: dict) -> dict | None:
    """Derive a notification intent from one retained check, without sending it."""
    if (not isinstance(check, dict) or check.get('format') != 'hosting-discovery-freshness-check/1'
            or check.get('historicalOnly') is not True or check.get('notificationAttempted') is not False
            or check.get('collectionRequested') is not False or check.get('executionAuthorized') is not False
            or not _id(check.get('checkId')) or not isinstance(check.get('report'), dict)
            or not isinstance(check.get('changeKinds'), list)):
        raise ValueError('A retained freshness check is required')
    report = check['report']
    issues = report.get('issues')
    if not isinstance(issues, list) or any(not isinstance(value, str) for value in issues):
        raise ValueError('Freshness issues are invalid')
    record_digest = check.get('recordDigest')
    report_digest = check.get('reportDigest')
    if (not isinstance(record_digest, str) or len(record_digest) != 64
            or any(char not in '0123456789abcdef' for char in record_digest)
            or not isinstance(report_digest, str) or len(report_digest) != 64
            or any(char not in '0123456789abcdef' for char in report_digest)):
        raise ValueError('Freshness report and record digests are required')
    if hashlib.sha256(_json(report).encode('ascii')).hexdigest() != report_digest:
        raise ValueError('Freshness report differs from its retained digest')
    binding = {key: check.get(key) for key in ('format', 'environmentId', 'scope', 'checkId',
        'sequence', 'reportDigest', 'recordedBy', 'recordedAt', 'previousRecordDigest', 'changeKinds')}
    if hashlib.sha256(_json(binding).encode('ascii')).hexdigest() != record_digest:
        raise ValueError('Freshness record differs from its retained digest')
    selected = sorted({value for value in issues if value in _ACTIONABLE})
    if not selected:
        return None
    severity = max((_ACTIONABLE[value] for value in selected), key=_SEVERITY.__getitem__)
    alert_id = hashlib.sha256(_json({'recordDigest': record_digest,
        'issues': selected}).encode('ascii')).hexdigest()
    return {'format': 'hosting-discovery-freshness-alert-intent/1',
        'alertId': alert_id, 'environmentId': check['environmentId'],
        'scope': check['scope'], 'checkId': check['checkId'],
        'checkRecordDigest': record_digest, 'severity': severity,
        'issueCodes': selected, 'changeKinds': list(check['changeKinds']),
        'detectedAt': check['recordedAt'], 'notificationRequired': True,
        'notificationAttempted': False, 'deliveryOwner': 'EXTERNAL',
        'collectionRequested': False, 'executionAuthorized': False}


class FreshnessMonitor:
    """Finite periodic runner over the existing durable freshness-history owner."""

    def __init__(self, history: FreshnessHistoryRepository, *,
                 policy: FreshnessMonitorPolicy = FreshnessMonitorPolicy(),
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
                 sleeper: Callable[[float], None] = time.sleep):
        if (not isinstance(history, FreshnessHistoryRepository)
                or not isinstance(policy, FreshnessMonitorPolicy)
                or not callable(clock) or not callable(sleeper)):
            raise TypeError('Freshness history, finite policy, clock and sleeper are required')
        self._history, self._policy, self._clock, self._sleep = history, policy, clock, sleeper
        self._last_clock = None

    def _now(self):
        at = self._clock()
        if not _utc(at) or self._last_clock is not None and at < self._last_clock:
            raise ValueError('Freshness-monitor clock is invalid or regressed')
        self._last_clock = at
        return at

    @staticmethod
    def _targets(values: Iterable[FreshnessMonitorTarget], maximum: int):
        items = tuple(values)
        if not 1 <= len(items) <= maximum or any(not isinstance(v, FreshnessMonitorTarget) for v in items):
            raise ValueError('A bounded nonempty monitor target set is required')
        keys = [_json(v.identity()) for v in items]
        if len(keys) != len(set(keys)):
            raise ValueError('Duplicate freshness-monitor target')
        return tuple(v for _, v in sorted(zip(keys, items), key=lambda pair: pair[0]))

    def run_cycle(self, ctx: TenantContext, targets: Iterable[FreshnessMonitorTarget], *,
                  actor_id: str, scheduled_at: datetime, authorize: Callable) -> dict:
        if not isinstance(ctx, TenantContext) or not _id(actor_id) or not callable(authorize):
            raise ValueError('Tenant context, service actor and current authorizer are required')
        selected = self._targets(targets, self._policy.max_targets)
        slot = _slot(scheduled_at, self._policy.interval_seconds)
        items = []
        for target in selected:
            identity = check_id(target, self._policy, scheduled_at)
            try:
                stored = self._history.capture(ctx, target.scope, target.environment_id, identity,
                    audit=AuditContext(actor_id, identity), authorize=authorize)
                alert = alert_projection(stored)
                items.append({'environmentId': target.environment_id, 'scope': dict(vars(target.scope)),
                    'checkId': identity, 'status': 'CHECK_RETAINED', 'recordDigest': stored['recordDigest'],
                    'alert': alert, 'historicalOnly': True, 'collectionRequested': False,
                    'notificationAttempted': False, 'executionAuthorized': False})
            except Exception:
                items.append({'environmentId': target.environment_id, 'scope': dict(vars(target.scope)),
                    'checkId': identity, 'status': 'CHECK_HELD', 'recordDigest': None, 'alert': None,
                    'historicalOnly': True, 'collectionRequested': False,
                    'notificationAttempted': False, 'executionAuthorized': False})
        return {'format': 'hosting-discovery-freshness-monitor-cycle/1',
            'scheduledAt': scheduled_at.isoformat(), 'slot': slot, 'policy': self._policy.document(),
            'items': items, 'notificationDelivery': 'EXTERNAL_NOT_ATTEMPTED',
            'collectionRequested': False, 'executionAuthorized': False}

    def run(self, ctx: TenantContext, targets: Iterable[FreshnessMonitorTarget], *, actor_id: str,
            authorize: Callable, duration_seconds: int) -> list[dict]:
        """Run bounded periodic cycles; restarts repeat slot IDs rather than resample."""
        if type(duration_seconds) is not int or not 1 <= duration_seconds <= 604800:
            raise ValueError('A bounded monitor runtime is required')
        selected = self._targets(targets, self._policy.max_targets)
        started = self._now()
        deadline = started + timedelta(seconds=duration_seconds)
        results, prior_slot = [], None
        while len(results) < self._policy.max_cycles:
            now = self._now()
            if now >= deadline:
                break
            slot = _slot(now, self._policy.interval_seconds)
            if slot != prior_slot:
                results.append(self.run_cycle(ctx, selected, actor_id=actor_id,
                                              scheduled_at=now, authorize=authorize))
                prior_slot = slot
            next_boundary = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(
                seconds=(slot + 1) * self._policy.interval_seconds)
            wait = min((next_boundary - self._now()).total_seconds(),
                       (deadline - self._last_clock).total_seconds())
            if wait > 0:
                self._sleep(wait)
            elif self._now() <= now:
                break
        return results
