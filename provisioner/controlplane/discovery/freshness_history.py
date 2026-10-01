"""Durable, historical freshness checks; never a collection or scheduling grant.

Only this trusted service creates reports, using the existing freshness reader.
Check IDs make lost-response retries return the original observation, not a new
check disguised as the same event. Independent audit custody remains necessary.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from typing import Callable

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence.store import AuditContext, TenantContext
from .freshness import DiscoveryFreshnessService, FreshnessPolicy, FreshnessUnavailable
from .model import _id, _json, _utc
from .native_credentials import decode_json
from .persistence import DiscoveryRepository
from .trust import _keys, _time

MAX_REPORT_BYTES = 8192
MAX_PAGE_BYTES = 1048576
_MAX = 2**63 - 1
_TABLE = 'hosting_controlplane.discovery_freshness_checks'
_COLUMNS = ('check_id, sequence, report_json, report_digest, recorded_by, recorded_at, '
            'previous_record_digest, changes_json, record_digest')
_SCOPE_SQL = ('organization_id=%s AND tenant_id=%s AND environment_id=%s AND site_id=%s '
              'AND security_domain_id=%s AND endpoint_id=%s AND native_scope_id=%s AND platform_family=%s')
_LOCK_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(jsonb_build_array('discovery-freshness', %s::text, %s::text, %s::text)::text, 0))"
_CHANGE_KINDS = ('INITIAL_CHECK', 'POLICY_CHANGED', 'OBSERVATION_CHANGED',
                 'FRESHNESS_CHANGED', 'COLLECTION_HEALTH_CHANGED')


class FreshnessCheckConflict(RuntimeError):
    """A retained check ID belongs to a different authenticated actor."""


def _digest(value):
    return hashlib.sha256(_json(value).encode('ascii')).hexdigest()


def _sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _integer(value, minimum=0, maximum=_MAX):
    return type(value) is int and minimum <= value <= maximum


def validate_report(report, scope, environment_id):
    """Validate the persisted wire contract, without hydrating native observations."""
    doc = _keys(report, {'format', 'environmentId', 'scope', 'checkedAt', 'policy', 'observation',
        'freshness', 'ageMicroseconds', 'refreshDue', 'issues', 'consistency', 'integrityVerification',
        'nativeVisibilityVerified', 'collectionRequested', 'executionAuthorized'})
    policy = _keys(doc['policy'], {'format', 'refreshAfterSeconds', 'maxAgeSeconds'})
    selected = FreshnessPolicy(policy['refreshAfterSeconds'], policy['maxAgeSeconds'])
    if (policy != selected.document() or doc['format'] != 'hosting-discovery-freshness/1'
            or doc['environmentId'] != environment_id or doc['scope'] != vars(scope)
            or doc['consistency'] != 'LIVE_METADATA_RECHECKS' or doc['integrityVerification'] != 'METADATA_ONLY'
            or any(doc[k] is not False for k in ('nativeVisibilityVerified', 'collectionRequested', 'executionAuthorized'))):
        raise ValueError('Freshness report identity or authority differs')
    checked = _time(doc['checkedAt'])
    observation = doc['observation']
    age, due, expected, issues = None, True, 'MISSING', []
    if observation is None:
        issues.append('INVENTORY_MISSING')
    else:
        o = _keys(observation, {'generation', 'campaignId', 'authorizationDigest', 'resultDigest',
            'capturedAt', 'completeness', 'objectCount', 'collectionErrorCount', 'missingPrivilegeCount'})
        if (not _integer(o['generation'], 1) or not _id(o['campaignId'])
                or not all(_sha(o[k]) for k in ('authorizationDigest', 'resultDigest'))
                or o['completeness'] not in ('COMPLETE', 'PARTIAL', 'UNKNOWN')
                or not _integer(o['objectCount']) or not _integer(o['collectionErrorCount'], maximum=1024)
                or not _integer(o['missingPrivilegeCount'], maximum=1024)
                or o['completeness'] == 'COMPLETE' and (o['collectionErrorCount'] or o['missingPrivilegeCount'])):
            raise ValueError('Invalid freshness observation metadata')
        delta = checked - _time(o['capturedAt'])
        microseconds = (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
        if microseconds < 0:
            expected = 'FUTURE_CAPTURE'; issues.append('INVENTORY_CAPTURE_IN_FUTURE')
        else:
            age = microseconds
            due = age >= selected.refresh_after_seconds * 1000000
            expected = 'STALE' if age > selected.max_age_seconds * 1000000 else 'FRESH'
            if expected == 'STALE': issues.append('INVENTORY_STALE')
            elif due: issues.append('INVENTORY_REFRESH_DUE')
        if o['completeness'] != 'COMPLETE': issues.append('COLLECTION_' + o['completeness'])
        if o['collectionErrorCount']: issues.append('COLLECTION_ERRORS_PRESENT')
        if o['missingPrivilegeCount']: issues.append('MISSING_PRIVILEGES')
    issues.append('NATIVE_VISIBILITY_UNVERIFIED')
    if (doc['freshness'] != expected or doc['refreshDue'] is not due
            or doc['ageMicroseconds'] != age or age is not None and type(doc['ageMicroseconds']) is not int
            or doc['issues'] != issues or len(_json(doc).encode('ascii')) > MAX_REPORT_BYTES):
        raise ValueError('Freshness status contradicts retained metadata')
    return checked


def changes_between(previous, current):
    """Deterministic monitoring differences, not verified omissions or alerts."""
    if previous is None:
        return ['INITIAL_CHECK']
    changes = []
    if previous['policy'] != current['policy']: changes.append('POLICY_CHANGED')
    def identity(doc):
        o = doc['observation']
        return None if o is None else (o['generation'], o['campaignId'], o['authorizationDigest'], o['resultDigest'], o['capturedAt'])
    def health(doc):
        o = doc['observation']
        return None if o is None else (o['completeness'], o['objectCount'], o['collectionErrorCount'], o['missingPrivilegeCount'])
    if identity(previous) != identity(current): changes.append('OBSERVATION_CHANGED')
    if (previous['freshness'], previous['refreshDue']) != (current['freshness'], current['refreshDue']):
        changes.append('FRESHNESS_CHANGED')
    if health(previous) != health(current): changes.append('COLLECTION_HEALTH_CHANGED')
    return changes


@dataclass(frozen=True, slots=True)
class StoredFreshnessCheck:
    environment_id: str
    scope: PlanScope
    check_id: str
    sequence: int
    report_json: str
    report_digest: str
    recorded_by: str
    recorded_at: datetime
    previous_record_digest: str | None
    changes_json: str
    record_digest: str

    def binding(self):
        return {'format': 'hosting-discovery-freshness-check/1', 'environmentId': self.environment_id,
            'scope': dict(vars(self.scope)), 'checkId': self.check_id, 'sequence': self.sequence,
            'reportDigest': self.report_digest, 'recordedBy': self.recorded_by,
            'recordedAt': self.recorded_at.isoformat(), 'previousRecordDigest': self.previous_record_digest,
            'changeKinds': json.loads(self.changes_json)}

    def document(self):
        return {**self.binding(), 'recordDigest': self.record_digest, 'report': json.loads(self.report_json),
            'historicalOnly': True, 'notificationAttempted': False,
            'collectionRequested': False, 'executionAuthorized': False}


class FreshnessHistoryRepository:
    """Append and read through the existing tenant-scoped transactional database."""
    def __init__(self, repository: DiscoveryRepository, *, policy: FreshnessPolicy = FreshnessPolicy()):
        if not isinstance(repository, DiscoveryRepository) or not isinstance(policy, FreshnessPolicy):
            raise TypeError('The discovery repository and server-owned policy are required')
        self._repository, self._policy = repository, policy

    @contextmanager
    def _session(self, ctx, scope, environment_id, authorize):
        DiscoveryRepository._require_scope(ctx, scope, environment_id)
        if not callable(authorize): raise TypeError('Current exact-scope authority is required')
        with self._repository._session(ctx) as con:
            if con.execute('SELECT hosting_controlplane.is_site_worker_role()').fetchone()[0]:
                raise PermissionError('Site workers cannot access freshness history')
            con.execute("SELECT set_config('TimeZone','UTC',true), set_config('lock_timeout','5s',true), "
                        "set_config('statement_timeout','10s',true)")
            last = None
            def now():
                nonlocal last
                at = con.execute('SELECT clock_timestamp()').fetchone()[0]
                if not _utc(at) or last is not None and at < last:
                    raise FreshnessUnavailable('Monitoring database clock regressed')
                last = at
                return at
            authorize(scope, now())
            yield con, now
            authorize(scope, now())

    @staticmethod
    def _row(environment_id, scope, row):
        value = StoredFreshnessCheck(environment_id, scope, *row)
        if (not _id(value.check_id) or not _integer(value.sequence, 1) or not _utc(value.recorded_at)
                or not _sha(value.report_digest) or not _sha(value.record_digest)
                or not isinstance(value.report_json, str) or not isinstance(value.changes_json, str)
                or (value.previous_record_digest is None) != (value.sequence == 1)
                or value.previous_record_digest is not None and not _sha(value.previous_record_digest)):
            raise ValueError('Invalid stored freshness identity')
        AuditContext(value.recorded_by, value.check_id)
        report = decode_json(value.report_json.encode('ascii'), MAX_REPORT_BYTES)
        checked = validate_report(report, scope, environment_id)
        changes = decode_json(value.changes_json.encode('ascii'), 512)
        if (not isinstance(changes, list) or len(changes) > len(_CHANGE_KINDS)
                or any(c not in _CHANGE_KINDS for c in changes) or len(set(changes)) != len(changes)
                or (changes == ['INITIAL_CHECK']) != (value.sequence == 1)
                or value.sequence > 1 and 'INITIAL_CHECK' in changes
                or _json(report) != value.report_json or _json(changes) != value.changes_json
                or checked > value.recorded_at or _digest(report) != value.report_digest
                or _digest(value.binding()) != value.record_digest):
            raise ValueError('Stored freshness check content has changed')
        return value

    def capture(self, ctx: TenantContext, scope: PlanScope, environment_id: str, check_id: str,
                *, audit: AuditContext, authorize: Callable) -> dict:
        if not _id(check_id) or not isinstance(audit, AuditContext):
            raise ValueError('An exact check ID and authenticated audit actor are required')
        args = DiscoveryRepository._scope_args(ctx, scope, environment_id)
        with self._session(ctx, scope, environment_id, authorize) as (con, now):
            con.execute(_LOCK_SQL, args[:3])
            authorize(scope, now())  # Lock waits must not extend an expired grant.
            row = con.execute('SELECT '+_COLUMNS+' FROM '+_TABLE+' WHERE '+_SCOPE_SQL+
                              ' AND check_id=%s', (*args, check_id)).fetchone()
            if row is not None:
                original = self._row(environment_id, scope, row)
                if original.recorded_by != audit.actor_id:
                    raise FreshnessCheckConflict('Check ID belongs to a different actor')
                return original.document()  # Never resample an uncertain original request.
            prior_row = con.execute('SELECT '+_COLUMNS+' FROM '+_TABLE+' WHERE '+_SCOPE_SQL+
                                    ' ORDER BY sequence DESC LIMIT 1', args).fetchone()
            prior = None if prior_row is None else self._row(environment_id, scope, prior_row)
            report = deepcopy(DiscoveryFreshnessService(self._repository, policy=self._policy, clock=now)
                              .inspect(ctx, scope, environment_id, authorize=authorize))
            checked = validate_report(report, scope, environment_id)
            at = now()
            if checked > at or prior is not None and (at < prior.recorded_at
                    or checked < _time(json.loads(prior.report_json)['checkedAt'])):
                raise FreshnessUnavailable('Monitoring history clock regressed')
            sequence = 1 if prior is None else prior.sequence + 1
            if sequence > _MAX: raise FreshnessUnavailable('Monitoring sequence exhausted')
            changes = changes_between(None if prior is None else json.loads(prior.report_json), report)
            values = (check_id, sequence, _json(report), _digest(report), audit.actor_id, at,
                      None if prior is None else prior.record_digest, _json(changes))
            temporary = StoredFreshnessCheck(environment_id, scope, *values, '')
            digest = _digest(temporary.binding())
            stored = self._row(environment_id, scope, (*values, digest))
            authorize(scope, now())
            con.execute('INSERT INTO '+_TABLE+' (organization_id,tenant_id,environment_id,site_id,'
                'security_domain_id,endpoint_id,native_scope_id,platform_family,'+_COLUMNS+') VALUES ('+
                ','.join(['%s']*17)+')', (*args, *values, digest))
            con.execute('INSERT INTO hosting_controlplane.audit_events '
                '(organization_id,tenant_id,actor_id,correlation_id,action,record_kind,record_id,'
                'revision,record_digest,details) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)',
                (ctx.organization_id,ctx.tenant_id,audit.actor_id,audit.correlation_id,'RECORD_CREATE',
                 'DiscoveryFreshnessCheck',check_id,sequence,digest,
                 _json({'environmentId':environment_id,'reportDigest':stored.report_digest,'changeKinds':changes})))
            return stored.document()  # Context exit rechecks authority before commit.

    def get(self, ctx, scope, environment_id, check_id, *, authorize):
        if not _id(check_id): raise ValueError('An exact check ID is required')
        with self._session(ctx, scope, environment_id, authorize) as (con, _):
            args = DiscoveryRepository._scope_args(ctx, scope, environment_id)
            row = con.execute('SELECT '+_COLUMNS+' FROM '+_TABLE+' WHERE '+_SCOPE_SQL+
                              ' AND check_id=%s', (*args,check_id)).fetchone()
            return None if row is None else self._row(environment_id,scope,row).document()

    def list_checks(self, ctx, scope, environment_id, *, after=0, limit=20, authorize):
        if not _integer(after) or not _integer(limit, 1, 50):
            raise ValueError('Bounded history cursor and page size are required')
        with self._session(ctx, scope, environment_id, authorize) as (con, _):
            args = DiscoveryRepository._scope_args(ctx, scope, environment_id)
            # Include the cursor predecessor and lookahead in the same bounded
            # statement. A separate anchor read could observe a different state.
            anchor = int(after > 0)
            lower = after - anchor
            rows = con.execute('SELECT '+_COLUMNS+' FROM '+_TABLE+' WHERE '+_SCOPE_SQL+
                ' AND sequence>%s ORDER BY sequence LIMIT %s',
                (*args, lower, limit + 1 + anchor)).fetchall()
            values = [self._row(environment_id,scope,row) for row in rows]
            for index, value in enumerate(values):
                if value.sequence != lower + index + 1:
                    raise FreshnessUnavailable('History sequence is incomplete')
                if index:
                    previous = values[index - 1]
                    if value.previous_record_digest != previous.record_digest:
                        raise FreshnessUnavailable('History predecessor differs')
                    prior_report = json.loads(previous.report_json)
                    current_report = json.loads(value.report_json)
                    if (value.recorded_at < previous.recorded_at
                            or _time(current_report['checkedAt']) < _time(prior_report['checkedAt'])):
                        raise FreshnessUnavailable('History time order differs')
                    if json.loads(value.changes_json) != changes_between(prior_report, current_report):
                        raise FreshnessUnavailable('History change kinds differ from retained reports')
            # The anchor validates continuity but is not a newly returned item.
            values = values[anchor:]
            items = values[:limit]
            result = {'format':'hosting-discovery-freshness-history/1','environmentId':environment_id,
                'scope':dict(vars(scope)),'items':[v.document() for v in items],
                'nextAfter':items[-1].sequence if len(values)>limit else None,
                'consistency':'APPEND_ONLY_PAGE','historicalOnly':True,
                'notificationAttempted':False,'collectionRequested':False,'executionAuthorized':False}
            if len(_json(result).encode('ascii')) > MAX_PAGE_BYTES:
                raise FreshnessUnavailable('History response exceeds its bound')
            return result
