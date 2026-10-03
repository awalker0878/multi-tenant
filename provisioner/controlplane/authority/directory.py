"""Durable OIDC directory with signed, full-subject IAM snapshots.

The IAM connector signs canonical JSON with a pinned Ed25519 key. Only the
dedicated sync writer can apply snapshots; only the dedicated resolver can read
enrollment before tenant identity is known. Neither DB credential is a user
credential or exposed through a generic SQL/API endpoint.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .model import PlanScope, PortfolioScope, RoleGrant
from .oidc import DirectoryIdentity
from .service import AuthenticationFailed

_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_PLAN_ROLES = frozenset({'SOURCE_OWNER', 'DESTINATION_OWNER',
                         'SOURCE_SECURITY', 'DESTINATION_SECURITY',
                         'EXECUTION_OPERATOR', 'JOB_READER', 'WORKER', 'DISCOVERY_MONITOR'})
_PORTFOLIO_ROLES = frozenset({'WORKLOAD_READER', 'WORKLOAD_EDITOR',
                              'INVENTORY_READER'})
_PLAN_SCOPE = frozenset({'organizationId', 'tenantId', 'locationId',
                         'securityDomainId', 'endpointId', 'nativeScopeId',
                         'platformFamily'})
_PORTFOLIO_SCOPE = frozenset({'organizationId', 'tenantId', 'securityDomainId'})
_SIGNED_PROVENANCE = 'signed-iam-full-subject/1'


class DirectorySyncRefused(ValueError):
    """Signature, replay, scope or IAM snapshot was not acceptable."""


def _runtime_role(cursor) -> None:
    if cursor.connection.autocommit:
        raise RuntimeError('Directory access requires a transaction')
    cursor.execute('SELECT rolsuper, rolbypassrls FROM pg_catalog.pg_roles '
                   'WHERE rolname = current_user')
    row = cursor.fetchone()
    if row is None or row[0] or row[1]:
        raise RuntimeError('Directory role must be NOSUPERUSER NOBYPASSRLS')


def _scope(record: dict, role: str, organization: str, tenant: str):
    if not isinstance(record, dict):
        raise DirectorySyncRefused('Role scope must be an object')
    if role in _PLAN_ROLES and set(record) == _PLAN_SCOPE:
        scope = PlanScope.from_record(record)
    elif role in _PORTFOLIO_ROLES and set(record) == _PORTFOLIO_SCOPE:
        scope = PortfolioScope(record['organizationId'], record['tenantId'],
                               record['securityDomainId'])
    else:
        raise DirectorySyncRefused('Unknown role or mismatched exact scope')
    if (scope.organization_id, scope.tenant_id) != (organization, tenant):
        raise DirectorySyncRefused('Cross-tenant grant is forbidden')
    if (not _ID.fullmatch(scope.security_domain_id)
            or (isinstance(scope, PlanScope)
                and (not _ID.fullmatch(scope.site_id)
                     or not _ID.fullmatch(scope.endpoint_id)
                     or scope.platform_family not in ('vmware', 'nutanix', 'openstack')))):
        raise DirectorySyncRefused('Role scope has an invalid identity')
    return scope


def _timestamp(value, *, now: datetime, max_lifetime: timedelta) -> datetime:
    if type(value) is not int:
        raise DirectorySyncRefused('IAM timestamp must be an integer')
    try:
        expires = datetime.fromtimestamp(value, timezone.utc)
    except (OSError, OverflowError, ValueError) as exc:
        raise DirectorySyncRefused('IAM timestamp is out of range') from exc
    if not now < expires <= now + max_lifetime:
        raise DirectorySyncRefused('IAM enrollment or grant has an invalid lifetime')
    return expires


def _snapshot(payload: dict, *, issuer: str, audience: str,
              now: datetime) -> tuple[tuple[RoleGrant, ...], tuple[tuple[str, datetime], ...]]:
    expected = {'format', 'issuer', 'audience', 'subject', 'organizationId',
                'tenantId', 'identityKind', 'active', 'generation', 'issuedAt',
                'grants', 'sessions'}
    if (not isinstance(payload, dict) or set(payload) != expected
            or payload['format'] != 'hosting-directory-snapshot/1'
            or payload['issuer'] != issuer or payload['audience'] != audience
            or not isinstance(payload['subject'], str)
            or not 0 < len(payload['subject']) <= 256
            or any(not isinstance(payload[name], str) or
                   _ID.fullmatch(payload[name]) is None
                   for name in ('organizationId', 'tenantId'))
            or payload['identityKind'] not in ('HUMAN', 'WORKER', 'SERVICE')
            or type(payload['active']) is not bool
            or type(payload['generation']) is not int or payload['generation'] < 1
            or type(payload['issuedAt']) is not int
            or not 0 <= int(now.timestamp()) - payload['issuedAt'] <= 300
            or not isinstance(payload['grants'], list)
            or len(payload['grants']) > 100
            or not isinstance(payload['sessions'], list)
            or len(payload['sessions']) > 16):
        raise DirectorySyncRefused('IAM snapshot has invalid exact identity or freshness')
    organization, tenant = payload['organizationId'], payload['tenantId']
    grants = []
    distinct = set()
    for item in payload['grants']:
        if not isinstance(item, dict) or set(item) != {'role', 'scope', 'expiresAt'}:
            raise DirectorySyncRefused('IAM grant must be exact')
        role = item['role']
        if not isinstance(role, str):
            raise DirectorySyncRefused('IAM role is invalid')
        scope = _scope(item['scope'], role, organization, tenant)
        expires = _timestamp(item['expiresAt'], now=now, max_lifetime=timedelta(days=1))
        identity_kind = payload['identityKind']
        matched_kind = ('WORKER' if role == 'WORKER' else
                        'SERVICE' if role == 'DISCOVERY_MONITOR' else 'HUMAN')
        if (role, scope) in distinct or identity_kind != matched_kind:
            raise DirectorySyncRefused('IAM grant is duplicated or mismatched to identity kind')
        distinct.add((role, scope))
        grants.append(RoleGrant(role, scope, expires))
    sessions = []
    seen = set()
    for item in payload['sessions']:
        if (not isinstance(item, dict) or set(item) != {'sessionId', 'expiresAt'}
                or not isinstance(item['sessionId'], str)
                or not 0 < len(item['sessionId']) <= 256
                or item['sessionId'] in seen):
            raise DirectorySyncRefused('IAM session is invalid or duplicated')
        seen.add(item['sessionId'])
        sessions.append((item['sessionId'], _timestamp(
            item['expiresAt'], now=now, max_lifetime=timedelta(days=1))))
    if not payload['active'] and (grants or sessions):
        raise DirectorySyncRefused('A disabled identity cannot retain active grants or sessions')
    return tuple(grants), tuple(sessions)


def _grants_json(payload: dict) -> str:
    return json.dumps(payload['grants'], sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


class PostgresRoleDirectory:
    """Live OIDC lookup using a dedicated global read-only directory role."""

    def __init__(self, connect: Callable):
        if not callable(connect):
            raise TypeError('Directory resolver connection factory required')
        self._connect = connect

    def resolve(self, issuer: str, subject: str, session_id: str) -> DirectoryIdentity:
        if (not all(isinstance(value, str) and value for value in
                    (issuer, subject, session_id))):
            raise AuthenticationFailed('Directory identity is incomplete')
        with self._connect() as connection, connection.cursor() as cursor:
            # Both reads must see the same committed generation while an IAM
            # replacement may be racing this authentication request.
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            _runtime_role(cursor)
            cursor.execute(
                'SELECT d.organization_id, d.tenant_id, d.identity_kind, '
                'd.active, d.grants, d.generation, d.signed_digest '
                'FROM hosting_controlplane.directory_subjects d '
                'JOIN hosting_controlplane.directory_sessions s '
                'ON s.issuer = d.issuer AND s.subject = d.subject '
                'WHERE d.issuer = %s AND d.subject = %s AND s.session_id = %s '
                'AND s.expires_at > clock_timestamp()',
                (issuer, subject, session_id))
            row = cursor.fetchone()
            if row is None or row[3] is not True:
                raise AuthenticationFailed('Session is not enrolled or has been revoked')
            organization, tenant, kind, _, raw, generation, signed_digest = row
            cursor.execute(
                "SELECT set_config('app.organization_id', %s, true), "
                "set_config('app.tenant_id', %s, true)", (organization, tenant))
            cursor.execute(
                'SELECT revision, record_digest, details '
                'FROM hosting_controlplane.audit_events '
                'WHERE organization_id = %s AND tenant_id = %s '
                "AND action = 'DIRECTORY_SYNC' AND record_kind = 'DirectorySubject' "
                'AND record_id = %s AND actor_id = %s '
                'ORDER BY audit_sequence DESC LIMIT 1',
                (organization, tenant, subject, 'iam-sync:' + issuer))
            marker = cursor.fetchone()
            cursor.execute('SELECT hosting_controlplane.directory_state_digest(%s, %s)',
                           (issuer, subject))
            state_digest = cursor.fetchone()[0]
            # Migration 0012 backfilled a marker for historical materialized
            # rows without re-verifying the IAM signature. Only a fresh signed
            # full-subject generation applied by this writer establishes the
            # post-cutover provenance required to authenticate.
            trusted_details = {
                'stateDigest': state_digest,
                'provenance': _SIGNED_PROVENANCE,
            }
            if (state_digest is None or
                    marker != (generation, signed_digest, trusted_details)):
                raise AuthenticationFailed('Directory generation lacks a matching audit marker')
        items = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(items, list):
            raise AuthenticationFailed('Persisted directory grants are invalid')
        grants = []
        for item in items:
            try:
                role = item['role']
                scope = _scope(item['scope'], role, organization, tenant)
                expiry = datetime.fromtimestamp(item['expiresAt'], timezone.utc)
                grants.append(RoleGrant(role, scope, expiry))
            except (KeyError, TypeError, ValueError, OverflowError, OSError) as exc:
                raise AuthenticationFailed('Persisted directory grants are invalid') from exc
        now = datetime.now(timezone.utc)
        return DirectoryIdentity(subject, session_id, organization, tenant,
                                 kind, True, tuple(g for g in grants if g.expires_at > now))


class SignedDirectorySync:
    """Apply signed full-subject IAM state using a dedicated writer credential.

    Every new generation replaces all sessions and scoped grants for the
    subject. A second signature over an old generation cannot restore access.
    A change also revokes plan approvals and admitted jobs involving that
    subject, inside the same transaction.
    """

    def __init__(self, connect: Callable, *, issuer: str, audience: str,
                 public_key: Ed25519PublicKey):
        if (not callable(connect) or not isinstance(issuer, str) or
                not issuer.startswith('https://') or not isinstance(audience, str)
                or not audience or not isinstance(public_key, Ed25519PublicKey)):
            raise ValueError('Pinned IAM signer, issuer, audience and writer required')
        self._connect = connect
        self._issuer = issuer
        self._audience = audience
        self._key = public_key

    def apply(self, payload_bytes: bytes, signature: bytes) -> bool:
        if (not isinstance(payload_bytes, bytes) or len(payload_bytes) > 131072
                or not isinstance(signature, bytes) or len(signature) != 64):
            raise DirectorySyncRefused('Bounded signed IAM snapshot required')
        try:
            self._key.verify(signature, payload_bytes)
            payload = json.loads(payload_bytes)
            canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                   ensure_ascii=False, allow_nan=False).encode('utf-8')
            if canonical != payload_bytes:
                raise DirectorySyncRefused('IAM snapshot must use canonical JSON')
        except (ValueError, TypeError, UnicodeError) as exc:
            raise DirectorySyncRefused('IAM snapshot signature or encoding is invalid') from exc
        except Exception as exc:
            raise DirectorySyncRefused('IAM signature is not trusted') from exc
        now = datetime.now(timezone.utc)
        _, sessions = _snapshot(payload, issuer=self._issuer,
                                audience=self._audience, now=now)
        digest = hashlib.sha256(payload_bytes).hexdigest()
        subject = payload['subject']
        with self._connect() as connection, connection.cursor() as cursor:
            _runtime_role(cursor)
            cursor.execute(
                "SELECT set_config('app.organization_id', %s, true), "
                "set_config('app.tenant_id', %s, true)",
                (payload['organizationId'], payload['tenantId']))
            # Serialize concurrent first enrollment and all replacements.
            cursor.execute('SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))',
                           (self._issuer, subject))
            cursor.execute(
                'SELECT organization_id, tenant_id, generation, signed_digest '
                'FROM hosting_controlplane.directory_subjects '
                'WHERE issuer = %s AND subject = %s FOR UPDATE',
                (self._issuer, subject))
            prior = cursor.fetchone()
            if prior is not None:
                if prior[:2] != (payload['organizationId'], payload['tenantId']):
                    raise DirectorySyncRefused('Directory tenant reassignment needs a separate reviewed transfer')
                if prior[2] == payload['generation'] and prior[3] == digest:
                    return False
                if prior[2] >= payload['generation']:
                    raise DirectorySyncRefused('IAM snapshot generation was replayed or conflicted')
                cursor.execute(
                    'SELECT revision, record_digest, details, occurred_at '
                    'FROM hosting_controlplane.audit_events '
                    'WHERE organization_id = %s AND tenant_id = %s '
                    "AND action = 'DIRECTORY_SYNC' AND record_kind = 'DirectorySubject' "
                    'AND record_id = %s AND actor_id = %s '
                    'ORDER BY audit_sequence DESC LIMIT 1',
                    (payload['organizationId'], payload['tenantId'], subject,
                     'iam-sync:' + self._issuer))
                marker = cursor.fetchone()
                cursor.execute('SELECT hosting_controlplane.directory_state_digest(%s, %s)',
                               (self._issuer, subject))
                prior_state_digest = cursor.fetchone()[0]
                if (marker is None or marker[:2] != (prior[2], prior[3])
                        or prior_state_digest is None):
                    raise DirectorySyncRefused('Prior IAM generation lacks its audit binding')
                legacy_details = {'stateDigest': prior_state_digest}
                signed_details = dict(legacy_details, provenance=_SIGNED_PROVENANCE)
                if marker[2] == legacy_details:
                    # The 0012 backfill attested only old database state. A
                    # pre-cutover signed snapshot, even of a higher generation,
                    # cannot authorize this subject after the cutover.
                    issued_at = datetime.fromtimestamp(payload['issuedAt'], timezone.utc)
                    if issued_at <= marker[3]:
                        raise DirectorySyncRefused('IAM snapshot predates directory cutover')
                elif marker[2] != signed_details:
                    raise DirectorySyncRefused('Prior IAM materialization differs from audit')
            cursor.execute(
                'INSERT INTO hosting_controlplane.directory_subjects '
                '(issuer, subject, organization_id, tenant_id, identity_kind, active, '
                'grants, generation, signed_digest) VALUES '
                '(%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s) '
                'ON CONFLICT (issuer, subject) DO UPDATE SET '
                'identity_kind = EXCLUDED.identity_kind, active = EXCLUDED.active, '
                'grants = EXCLUDED.grants, generation = EXCLUDED.generation, '
                'signed_digest = EXCLUDED.signed_digest, updated_at = clock_timestamp()',
                (self._issuer, subject, payload['organizationId'], payload['tenantId'],
                 payload['identityKind'], payload['active'], _grants_json(payload),
                 payload['generation'], digest))
            cursor.execute('DELETE FROM hosting_controlplane.directory_sessions '
                           'WHERE issuer = %s AND subject = %s', (self._issuer, subject))
            for session, expires in sessions:
                cursor.execute(
                    'INSERT INTO hosting_controlplane.directory_sessions '
                    '(issuer, subject, session_id, expires_at) VALUES (%s, %s, %s, %s)',
                    (self._issuer, subject, session, expires))
            cursor.execute(
                'INSERT INTO hosting_controlplane.directory_sync_events '
                '(issuer, subject, generation, signed_digest) VALUES (%s, %s, %s, %s)',
                (self._issuer, subject, payload['generation'], digest))
            cursor.execute('SELECT hosting_controlplane.directory_state_digest(%s, %s)',
                           (self._issuer, subject))
            state_digest = cursor.fetchone()[0]
            if state_digest is None:
                raise DirectorySyncRefused('IAM state was not persisted in this transaction')
            cursor.execute(
                'INSERT INTO hosting_controlplane.audit_events '
                '(organization_id, tenant_id, actor_id, correlation_id, action, '
                'record_kind, record_id, revision, record_digest, details) VALUES '
                "(%s, %s, %s, %s, 'DIRECTORY_SYNC', 'DirectorySubject', %s, %s, %s, %s::jsonb)",
                (payload['organizationId'], payload['tenantId'],
                 'iam-sync:' + self._issuer, digest, subject,
                 payload['generation'], digest,
                 json.dumps({'stateDigest': state_digest,
                             'provenance': _SIGNED_PROVENANCE})))
            if prior is not None:
                cursor.execute(
                    'SELECT plan_id, revocation_epoch FROM '
                    'hosting_controlplane.plan_authority_state s WHERE '
                    's.organization_id = %s AND s.tenant_id = %s AND '
                    '(EXISTS (SELECT 1 FROM hosting_controlplane.plan_approvals a '
                    'WHERE a.organization_id = s.organization_id '
                    'AND a.tenant_id = s.tenant_id AND a.plan_id = s.plan_id '
                    'AND a.approver_subject = %s) OR EXISTS '
                    '(SELECT 1 FROM hosting_controlplane.operation_jobs j '
                    'WHERE j.organization_id = s.organization_id '
                    'AND j.tenant_id = s.tenant_id AND j.plan_id = s.plan_id '
                    'AND j.actor_subject = %s)) ORDER BY plan_id FOR UPDATE',
                    (payload['organizationId'], payload['tenantId'], subject, subject))
                for plan_id, epoch in cursor.fetchall():
                    cursor.execute(
                        'UPDATE hosting_controlplane.plan_authority_state '
                        'SET revocation_epoch = revocation_epoch + 1, '
                        'updated_at = clock_timestamp() WHERE organization_id = %s '
                        'AND tenant_id = %s AND plan_id = %s',
                        (payload['organizationId'], payload['tenantId'], plan_id))
                    cursor.execute(
                        'INSERT INTO hosting_controlplane.plan_revocations '
                        '(organization_id, tenant_id, plan_id, from_epoch, to_epoch, '
                        'actor_subject, reason) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                        (payload['organizationId'], payload['tenantId'], plan_id,
                         epoch, epoch + 1, 'iam-sync:' + self._issuer,
                         'Signed IAM subject generation changed'))
            return True
