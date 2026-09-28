"""Durable, signed assessment inputs and request-bound live read authority.

This is an internal evidence ingest, never a browser submission interface.
Offline authorities enroll exact roles/scopes in a short-lived signed policy;
readers recheck that policy and the artifact signatures at every use. SQL rows,
environment declarations and a valid user session cannot confer qualification.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock
from typing import Callable, Iterator

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.authority.service import (
    AuthorityDenied, AuthorityService, require_scoped_role)
from provisioner.controlplane.persistence.environments import EnvironmentRepository
from provisioner.controlplane.persistence.store import TenantContext

from .assessment import AssessmentScopeAccess, ReviewedFinding
from .model import _digest, _id, _json, _scope, _scope_json, _unique_pairs, _utc
from .normalization import NORMALIZER_VERSION, NormalizedDiscovery
from .routes import InstalledTuple, QualificationEvidence, RouteClaim, RouteKey
from .service import VerifiedAssessmentEnvironment
from .trust import _decode


_DIGEST = re.compile(r'^[0-9a-f]{64}$')
_ROLE = re.compile(r'^[a-z][a-z0-9_]{0,62}$')
_ROLES = {'INSTALLATION', 'SOURCE_EXIT', 'TARGET_OPERATE', 'POLICY_TRANSLATION',
          'SECURITY_EQUIVALENCE', 'RECOVERY_READINESS'}


class AssessmentInputDenied(PermissionError):
    """Current, independent assessment evidence or operator access is unavailable."""


def _keys(value: object, fields: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise AssessmentInputDenied('Assessment evidence fields are invalid')
    return value


def _time(value: object) -> datetime:
    try:
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else None
        if not _utc(parsed):
            raise ValueError('not UTC')
        return parsed
    except ValueError as exc:
        raise AssessmentInputDenied('Evidence requires UTC timestamps') from exc


def _hash(value: object) -> str:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise AssessmentInputDenied('An exact evidence digest is required')
    return value


def _parse_scope(value: object) -> PlanScope:
    body = _keys(value, {'organizationId', 'tenantId', 'locationId', 'securityDomainId',
                         'endpointId', 'nativeScopeId', 'platformFamily'})
    scope = PlanScope.from_record(body)
    if not _scope(scope):
        raise AssessmentInputDenied('Invalid exact evidence scope')
    return scope


def installation_document(value: InstalledTuple) -> dict:
    return {'scope': _scope_json(value.scope), 'productTupleId': value.product_tuple_id,
            'productTupleDigest': value.product_tuple_digest}


def _installation(value: object) -> InstalledTuple:
    body = _keys(value, {'scope', 'productTupleId', 'productTupleDigest'})
    return InstalledTuple(_parse_scope(body['scope']), body['productTupleId'], body['productTupleDigest'])


def route_document(value: RouteKey) -> dict:
    return {'source': installation_document(value.source),
            'destination': installation_document(value.destination), 'method': value.method,
            'guestProfile': value.guest_profile, 'networkMode': value.network_mode,
            'dataMode': value.data_mode}


def _route(value: object) -> RouteKey:
    body = _keys(value, {'source', 'destination', 'method', 'guestProfile', 'networkMode', 'dataMode'})
    return RouteKey(_installation(body['source']), _installation(body['destination']),
                    body['method'], body['guestProfile'], body['networkMode'], body['dataMode'])


def _qualification(value: object, route: RouteKey) -> QualificationEvidence:
    body = _keys(value, {'side', 'evidenceId', 'evidenceDigest', 'observedAt', 'expiresAt'})
    installed = route.source if body['side'] == 'SOURCE_EXIT' else route.destination
    return QualificationEvidence(body['side'], installed, route.method, route.guest_profile,
        route.network_mode, route.data_mode, body['evidenceId'], body['evidenceDigest'],
        _time(body['observedAt']), _time(body['expiresAt']))


@dataclass(frozen=True, slots=True)
class AssessmentEvidence:
    canonical_json: str
    evidence_id: str
    kind: str
    revision: int
    binding_digest: str
    issued_at: datetime
    expires_at: datetime
    environments: tuple[tuple[str, PlanScope], ...]
    value: InstalledTuple | RouteClaim | ReviewedFinding
    required_roles: tuple[tuple[str, tuple[str, ...]], ...]

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json.encode('ascii')).hexdigest()


def parse_evidence(document: dict) -> AssessmentEvidence:
    """Strict bounded data parsing only. Callers must still verify signatures."""
    try:
        body = _keys(document, {'format', 'evidenceId', 'kind', 'revision', 'issuedAt',
                                'expiresAt', 'payload'})
        encoded = _json(body)
        if (len(encoded) > 65536 or body['format'] != 'hosting-assessment-evidence/1'
                or not _id(body['evidenceId']) or type(body['revision']) is not int
                or not 1 <= body['revision'] <= 2**63 - 1):
            raise AssessmentInputDenied('Invalid bounded assessment evidence')
        body = json.loads(encoded)
        issued, expires = _time(body['issuedAt']), _time(body['expiresAt'])
        if not timedelta(0) < expires - issued <= timedelta(days=30):
            raise AssessmentInputDenied('Evidence validity is outside the allowed window')
        kind, payload = body['kind'], body['payload']
        if kind == 'INSTALLATION':
            payload = _keys(payload, {'environmentId', 'installation', 'nativeEvidenceDigest'})
            _hash(payload['nativeEvidenceDigest'])
            installed = _installation(payload['installation'])
            environment = payload['environmentId']
            environments = ((environment, installed.scope),)
            roles = (('INSTALLATION', (environment,)),)
            binding = {'kind': kind, 'environmentId': environment}
            value = installed
        elif kind in ('ROUTE', 'CONTROL'):
            fields = {'sourceEnvironmentId', 'destinationEnvironmentId', 'route'}
            fields |= ({'maturity', 'evidence'} if kind == 'ROUTE' else
                       {'control', 'outcome', 'evidenceDigest', 'observedAt',
                        'sourceRawSnapshotDigest', 'destinationRawSnapshotDigest',
                        'sourceSnapshotDigest', 'destinationSnapshotDigest', 'normalizerVersion'})
            payload = _keys(payload, fields)
            route = _route(payload['route'])
            source, destination = payload['sourceEnvironmentId'], payload['destinationEnvironmentId']
            environments = ((source, route.source.scope), (destination, route.destination.scope))
            if source == destination or ((route.source.scope.organization_id, route.source.scope.tenant_id)
                    != (route.destination.scope.organization_id, route.destination.scope.tenant_id)):
                raise AssessmentInputDenied('Assessment evidence cannot cross tenants or alias scopes')
            binding = {'kind': kind, 'route': route_document(route)}
            if kind == 'ROUTE':
                if not isinstance(payload['evidence'], list) or len(payload['evidence']) > 2:
                    raise AssessmentInputDenied('Invalid independent qualification evidence')
                value = RouteClaim(route, payload['maturity'], tuple(
                    _qualification(item, route) for item in payload['evidence']))
                roles = (('SOURCE_EXIT', (source,)), ('TARGET_OPERATE', (destination,)))
            else:
                for name in ('sourceRawSnapshotDigest', 'destinationRawSnapshotDigest',
                             'sourceSnapshotDigest', 'destinationSnapshotDigest'):
                    _hash(payload[name])
                if payload['normalizerVersion'] != NORMALIZER_VERSION:
                    raise AssessmentInputDenied('Control finding uses an unsupported normalizer')
                value = ReviewedFinding(payload['control'], route, payload['sourceSnapshotDigest'],
                    payload['destinationSnapshotDigest'], payload['outcome'], body['evidenceId'],
                    payload['evidenceDigest'], _time(payload['observedAt']), expires)
                if value.observed_at > issued:
                    raise AssessmentInputDenied('Review observation occurs after signing')
                binding.update(control=value.control,
                    sourceRawSnapshotDigest=payload['sourceRawSnapshotDigest'],
                    destinationRawSnapshotDigest=payload['destinationRawSnapshotDigest'],
                    sourceSnapshotDigest=value.source_snapshot_digest,
                    destinationSnapshotDigest=value.destination_snapshot_digest,
                    normalizerVersion=NORMALIZER_VERSION)
                roles = ((value.control, (source, destination)),)
        else:
            raise AssessmentInputDenied('Unknown assessment evidence kind')
        if any(not _id(environment) for environment, _ in environments):
            raise AssessmentInputDenied('Evidence needs exact registered environments')
        return AssessmentEvidence(encoded, body['evidenceId'], kind, body['revision'],
            _digest(binding), issued, expires, environments, value, roles)
    except (TypeError, ValueError, KeyError, OverflowError) as exc:
        raise AssessmentInputDenied('Invalid assessment evidence document') from exc


@dataclass(frozen=True, slots=True)
class VerifiedAssessmentPolicy:
    canonical_json: str
    signature: str
    revision: int
    digest: str


class SignedFileAssessmentTrustStore:
    """Live offline-root-signed enrollment and revocation with no stale fallback."""

    def __init__(self, path: str | Path, *, authority_public_key: Ed25519PublicKey,
                 minimum_revision: int):
        if (not isinstance(authority_public_key, Ed25519PublicKey)
                or type(minimum_revision) is not int or minimum_revision < 1):
            raise ValueError('Pinned assessment root key and revision floor are required')
        self._path, self._key = Path(path), authority_public_key
        self._revision, self._digest = minimum_revision, None
        self._lock = RLock()

    def _policy(self, document: dict, checked_at: datetime) -> VerifiedAssessmentPolicy:
        _keys(document, {'policy', 'signature'})
        body = _keys(document['policy'], {'format', 'revision', 'issuedAt', 'expiresAt',
                                          'enrollments', 'revokedEvidenceIds'})
        issued, expires = _time(body['issuedAt']), _time(body['expiresAt'])
        if (body['format'] != 'hosting-assessment-trust-policy/1'
                or type(body['revision']) is not int or not 1 <= body['revision'] <= 2**63 - 1
                or not issued <= checked_at < expires
                or not timedelta(0) < expires - issued <= timedelta(hours=24)
                or not isinstance(body['enrollments'], list) or len(body['enrollments']) > 1000
                or not isinstance(body['revokedEvidenceIds'], list)
                or len(body['revokedEvidenceIds']) > 10000
                or any(not _id(item) for item in body['revokedEvidenceIds'])):
            raise AssessmentInputDenied('Invalid or expired assessment trust policy')
        keys, role_keys = set(), {}
        for entry in body['enrollments']:
            _keys(entry, {'keyId', 'subjectId', 'role', 'publicKey', 'environments',
                          'notBefore', 'expiresAt', 'revokedAt'})
            if (not _id(entry['keyId']) or not _id(entry['subjectId'])
                    or entry['keyId'] in keys or entry['role'] not in _ROLES
                    or not isinstance(entry['environments'], list)
                    or not 1 <= len(entry['environments']) <= 100
                    or _time(entry['notBefore']) >= _time(entry['expiresAt'])):
                raise AssessmentInputDenied('Invalid assessment reviewer enrollment')
            _decode(entry['publicKey'], 32)
            if entry['revokedAt'] is not None:
                _time(entry['revokedAt'])
            keys.add(entry['keyId'])
            for selector in entry['environments']:
                _keys(selector, {'environmentId', 'scope'})
                if not _id(selector['environmentId']):
                    raise AssessmentInputDenied('Reviewer environment is invalid')
                _parse_scope(selector['scope'])
            # Rotation may retain a subject in the same role; separate roles
            # require distinct people and keys, including all control reviewers.
            for identity in (entry['publicKey'], entry['subjectId']):
                if identity in role_keys and role_keys[identity] != entry['role']:
                    raise AssessmentInputDenied('Assessment reviewer roles are not independent')
                role_keys[identity] = entry['role']
        canonical = _json(body)
        self._key.verify(_decode(document['signature'], 64), canonical.encode('ascii'))
        return VerifiedAssessmentPolicy(canonical, document['signature'], body['revision'],
                                         hashlib.sha256(canonical.encode('ascii')).hexdigest())

    def current_policy(self, checked_at: datetime) -> VerifiedAssessmentPolicy:
        if not _utc(checked_at):
            raise AssessmentInputDenied('Trusted UTC verification time is required')
        with self._lock:
            try:
                descriptor = os.open(self._path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
                try:
                    info = os.fstat(descriptor)
                    if (not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, os.geteuid())
                            or info.st_mode & 0o022 or info.st_size > 1048576):
                        raise AssessmentInputDenied('Assessment trust file is not protected')
                    with os.fdopen(descriptor, 'rb', closefd=False) as stream:
                        raw = stream.read(1048577)
                finally:
                    os.close(descriptor)
                if len(raw) > 1048576:
                    raise AssessmentInputDenied('Assessment trust file exceeds its bound')
                policy = self._policy(json.loads(raw, object_pairs_hook=_unique_pairs), checked_at)
                if (policy.revision < self._revision or policy.revision == self._revision
                        and self._digest is not None and policy.digest != self._digest):
                    raise AssessmentInputDenied('Assessment trust rollback or equivocation')
                self._revision, self._digest = policy.revision, policy.digest
                return policy
            except (OSError, ValueError, TypeError, KeyError, InvalidSignature) as exc:
                raise AssessmentInputDenied('Live assessment trust is unavailable') from exc

    def verify(self, evidence: AssessmentEvidence, signatures: tuple[dict, ...],
               checked_at: datetime) -> tuple[VerifiedAssessmentPolicy, tuple[str, ...]]:
        if (not isinstance(evidence, AssessmentEvidence)
                or parse_evidence(json.loads(evidence.canonical_json,
                                              object_pairs_hook=_unique_pairs)) != evidence):
            raise AssessmentInputDenied('Assessment evidence differs from its signed content')
        policy = self.current_policy(checked_at)
        return policy, self._verify_with_policy(evidence, signatures, checked_at, policy)

    def _verify_with_policy(self, evidence, signatures, checked_at, policy) -> tuple[str, ...]:
        body = json.loads(policy.canonical_json)
        if (not evidence.issued_at <= checked_at < evidence.expires_at
                or evidence.evidence_id in body['revokedEvidenceIds']
                or not isinstance(signatures, tuple)
                or len(signatures) != len(evidence.required_roles)):
            raise AssessmentInputDenied('Assessment evidence is expired, revoked or unsigned')
        subjects, used_keys = [], set()
        for role, environment_ids in evidence.required_roles:
            candidates = []
            for signature in signatures:
                _keys(signature, {'keyId', 'signature'})
                for entry in body['enrollments']:
                    authorized = {(item['environmentId'], _parse_scope(item['scope']))
                                  for item in entry['environments']}
                    needed = {(name, scope) for name, scope in evidence.environments
                              if name in environment_ids}
                    if (entry['keyId'] == signature['keyId'] and entry['role'] == role
                            and needed <= authorized
                            and _time(entry['notBefore']) <= evidence.issued_at
                            and evidence.expires_at <= _time(entry['expiresAt'])
                            and (entry['revokedAt'] is None or checked_at < _time(entry['revokedAt']))):
                        candidates.append((entry, signature))
            if len(candidates) != 1:
                raise AssessmentInputDenied('An exact current reviewer role is unavailable')
            entry, signature = candidates[0]
            if entry['keyId'] in used_keys or entry['subjectId'] in subjects:
                raise AssessmentInputDenied('Assessment signatures are not independent')
            try:
                Ed25519PublicKey.from_public_bytes(_decode(entry['publicKey'], 32)).verify(
                    _decode(signature['signature'], 64), evidence.canonical_json.encode('ascii'))
            except (InvalidSignature, ValueError) as exc:
                raise AssessmentInputDenied('Assessment artifact signature is invalid') from exc
            used_keys.add(entry['keyId'])
            subjects.append(entry['subjectId'])
        return tuple(subjects)

    def verify_retained_policy(self, policy_json: str, signature: str,
                               checked_at: datetime) -> VerifiedAssessmentPolicy:
        """Reverify original custody proof at its recorded ingest time."""
        try:
            return self._policy({'policy': json.loads(policy_json, object_pairs_hook=_unique_pairs),
                                 'signature': signature}, checked_at)
        except (ValueError, TypeError, InvalidSignature) as exc:
            raise AssessmentInputDenied('Retained assessment trust proof is invalid') from exc


class AssessmentInputRepository:
    """Separate append-only evidence writer; ordinary runtime instances only read."""

    def __init__(self, connect: Callable, trust: SignedFileAssessmentTrustStore, *,
                 ingest_role: str | None = None):
        if (not callable(connect) or not isinstance(trust, SignedFileAssessmentTrustStore)
                or ingest_role is not None and (not isinstance(ingest_role, str)
                                                 or not _ROLE.fullmatch(ingest_role))):
            raise ValueError('Assessment database and pinned signed-file trust are required')
        self._connect, self._trust, self._ingest_role = connect, trust, ingest_role

    @contextmanager
    def _session(self, ctx: TenantContext, *, write=False) -> Iterator:
        if not isinstance(ctx, TenantContext) or write and self._ingest_role is None:
            raise AssessmentInputDenied('Dedicated assessment ingest authority is required')
        with self._connect() as connection:
            if connection.autocommit:
                raise AssessmentInputDenied('Assessment access requires a transaction')
            row = connection.execute('SELECT current_user, rolsuper, rolbypassrls '
                'FROM pg_catalog.pg_roles WHERE rolname = current_user').fetchone()
            if row is None or row[1] or row[2] or write and row[0] != self._ingest_role:
                raise AssessmentInputDenied('Assessment role must enforce RLS and writer separation')
            if write and connection.execute(
                    'SELECT hosting_controlplane.is_site_worker_role()').fetchone()[0]:
                raise AssessmentInputDenied('Site workers cannot ingest assessment evidence')
            connection.execute("SELECT set_config('app.organization_id', %s, true), "
                               "set_config('app.tenant_id', %s, true)",
                               (ctx.organization_id, ctx.tenant_id))
            yield connection

    @staticmethod
    def _tenant(ctx: TenantContext, evidence: AssessmentEvidence):
        if any((scope.organization_id, scope.tenant_id) != (ctx.organization_id, ctx.tenant_id)
               for _, scope in evidence.environments):
            raise AssessmentInputDenied('Assessment evidence is outside the exact tenant')

    def ingest(self, ctx: TenantContext, document: dict, signatures: tuple[dict, ...]) -> str:
        evidence = parse_evidence(document)
        self._tenant(ctx, evidence)
        if not isinstance(signatures, tuple):
            raise AssessmentInputDenied('Assessment signatures must be an immutable tuple')
        for signature in signatures:
            _keys(signature, {'keyId', 'signature'})
            if not _id(signature['keyId']):
                raise AssessmentInputDenied('Assessment signing key ID is invalid')
        signatures = tuple(sorted(json.loads(_json(signatures)), key=lambda item: item['keyId']))
        with self._session(ctx, write=True) as connection:
            now = connection.execute('SELECT clock_timestamp()').fetchone()[0]
            policy, subjects = self._trust.verify(evidence, signatures, now)
            for environment_id, scope in evidence.environments:
                found = connection.execute('SELECT 1 FROM hosting_controlplane.environment_registrations '
                    'WHERE organization_id = %s AND tenant_id = %s AND environment_id = %s '
                    'AND site_id = %s AND security_domain_id = %s AND endpoint_id = %s '
                    'AND native_scope_id = %s AND platform_family = %s',
                    (ctx.organization_id, ctx.tenant_id, environment_id, scope.site_id,
                     scope.security_domain_id, scope.endpoint_id, scope.native_scope_id,
                     scope.platform_family)).fetchone()
                if found is None:
                    raise AssessmentInputDenied('Evidence does not match a registered exact environment')
            connection.execute('SELECT pg_advisory_xact_lock(%s::bigint)',
                (int.from_bytes(hashlib.sha256((ctx.organization_id + ':' + ctx.tenant_id + ':' +
                     evidence.binding_digest).encode()).digest()[:8], 'big', signed=True),))
            prior = connection.execute('SELECT revision, evidence_digest, evidence_id, signatures_json '
                'FROM hosting_controlplane.assessment_inputs WHERE organization_id = %s AND tenant_id = %s '
                'AND kind = %s AND binding_digest = %s ORDER BY revision DESC LIMIT 1',
                (ctx.organization_id, ctx.tenant_id, evidence.kind, evidence.binding_digest)).fetchone()
            if prior == (evidence.revision, evidence.digest, evidence.evidence_id, _json(signatures)):
                return evidence.digest  # Exact retry after lost response; signatures reverified above.
            if prior is not None and evidence.revision <= prior[0]:
                raise AssessmentInputDenied('Assessment revision was replayed or rolled back')
            connection.execute('INSERT INTO hosting_controlplane.assessment_inputs '
                '(organization_id, tenant_id, evidence_id, kind, binding_digest, revision, '
                'evidence_json, evidence_digest, signatures_json, policy_json, policy_signature, '
                'policy_revision, policy_digest, verified_at, verified_subjects) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (ctx.organization_id, ctx.tenant_id, evidence.evidence_id, evidence.kind,
                 evidence.binding_digest, evidence.revision, evidence.canonical_json, evidence.digest,
                 _json(signatures), policy.canonical_json, policy.signature, policy.revision,
                 policy.digest, now, list(subjects)))
            connection.execute('INSERT INTO hosting_controlplane.audit_events '
                '(organization_id, tenant_id, actor_id, correlation_id, action, record_kind, '
                'record_id, revision, record_digest, details) VALUES '
                "(%s, %s, %s, %s, 'RECORD_CREATE', 'AssessmentInput', %s, %s, %s, %s::jsonb)",
                (ctx.organization_id, ctx.tenant_id, 'assessment-review:' + subjects[0],
                 evidence.evidence_id, evidence.evidence_id, evidence.revision, evidence.digest,
                 _json({'policyDigest': policy.digest, 'policyRevision': policy.revision,
                        'reviewerSubjects': subjects, 'bindingDigest': evidence.binding_digest})))
        return evidence.digest

    def latest(self, ctx: TenantContext, kind: str, binding_digest: str,
               checked_at: datetime) -> AssessmentEvidence | None:
        if kind not in ('INSTALLATION', 'ROUTE', 'CONTROL') or not _utc(checked_at):
            raise AssessmentInputDenied('Exact assessment lookup and UTC time required')
        _hash(binding_digest)
        with self._session(ctx) as connection:
            row = connection.execute('SELECT evidence_json, evidence_digest, signatures_json, '
                'policy_json, policy_signature, policy_revision, policy_digest, verified_at, '
                'verified_subjects, evidence_id, revision FROM hosting_controlplane.assessment_inputs '
                'WHERE organization_id = %s AND tenant_id = %s AND kind = %s AND binding_digest = %s '
                'ORDER BY revision DESC LIMIT 1',
                (ctx.organization_id, ctx.tenant_id, kind, binding_digest)).fetchone()
        if row is None:
            return None
        evidence = parse_evidence(json.loads(row[0], object_pairs_hook=_unique_pairs))
        self._tenant(ctx, evidence)
        if (evidence.digest != row[1] or evidence.kind != kind or evidence.binding_digest != binding_digest
                or evidence.evidence_id != row[9] or evidence.revision != row[10]
                or evidence.canonical_json != row[0] or row[7] > checked_at):
            raise AssessmentInputDenied('Stored assessment evidence binding has changed')
        signatures = tuple(json.loads(row[2], object_pairs_hook=_unique_pairs))
        retained = self._trust.verify_retained_policy(row[3], row[4], row[7])
        original_subjects = self._trust._verify_with_policy(evidence, signatures, row[7], retained)
        if (retained.revision != row[5] or retained.digest != row[6]
                or original_subjects != tuple(row[8])):
            raise AssessmentInputDenied('Stored assessment custody proof has changed')
        self._trust.verify(evidence, signatures, checked_at)
        return evidence


class DurableAssessmentInputs:
    """Startup composition. Bind bearer credentials only for one server request."""

    def __init__(self, repository: AssessmentInputRepository, authority: AuthorityService,
                 environments: EnvironmentRepository):
        if (not isinstance(repository, AssessmentInputRepository)
                or not isinstance(authority, AuthorityService)
                or not isinstance(environments, EnvironmentRepository)):
            raise ValueError('Durable assessment, authority and environment services are required')
        self._repository, self._authority, self._environments = repository, authority, environments

    def bind(self, credential: str) -> BoundAssessmentInputs:
        if not isinstance(credential, str) or not credential:
            raise AssessmentInputDenied('A verified request credential is required')
        return BoundAssessmentInputs(self, credential)


class BoundAssessmentInputs:
    """Credential stays in memory; never put this object into logs or artifacts."""

    def __init__(self, owner: DurableAssessmentInputs, credential: str):
        self._owner, self._credential = owner, credential

    def _principal(self, ctx, actor):
        principal = self._owner._authority.authenticate(self._credential)
        if (principal.kind != 'HUMAN' or principal.subject != actor
                or (principal.organization_id, principal.tenant_id) !=
                (ctx.organization_id, ctx.tenant_id)):
            raise AssessmentInputDenied('Authenticated assessment actor does not match this tenant')
        return principal

    def _authorize(self, ctx, actor, environment_id, checked_at):
        principal = self._principal(ctx, actor)
        row = self._owner._environments.get(ctx, environment_id)
        if row is None:
            raise AssessmentInputDenied('Assessment environment is unavailable')
        for role in ('JOB_READER', 'EXECUTION_OPERATOR'):
            try:
                grant = require_scoped_role(principal, role, row.scope, checked_at)
                return row, min(grant.expires_at, principal.expires_at)
            except AuthorityDenied:
                pass
        raise AssessmentInputDenied('Exact native-scope assessment read permission is missing')

    def resolve_environment(self, ctx, actor_subject, environment_id, purpose, as_of):
        if purpose not in ('SOURCE_READ', 'DESTINATION_READ'):
            raise AssessmentInputDenied('Invalid assessment read purpose')
        environment, expires = self._authorize(ctx, actor_subject, environment_id, as_of)
        evidence = self._owner._repository.latest(ctx, 'INSTALLATION',
            _digest({'kind': 'INSTALLATION', 'environmentId': environment_id}), as_of)
        if (evidence is None or evidence.environments != ((environment_id, environment.scope),)
                or not isinstance(evidence.value, InstalledTuple)):
            raise AssessmentInputDenied('Current independently observed installation is unavailable')
        access = AssessmentScopeAccess(environment.scope, purpose, actor_subject,
            'directory-read:' + _digest({'actor': actor_subject, 'scope': _scope_json(environment.scope)}),
            as_of, min(expires, evidence.expires_at))
        return VerifiedAssessmentEnvironment(environment_id, evidence.value, access)

    def _authorize_evidence(self, ctx, actor, evidence, as_of):
        for environment_id, scope in evidence.environments:
            environment, _ = self._authorize(ctx, actor, environment_id, as_of)
            if environment.scope != scope:
                raise AssessmentInputDenied('Evidence environment selector no longer matches')
            installed = self._owner._repository.latest(ctx, 'INSTALLATION',
                _digest({'kind': 'INSTALLATION', 'environmentId': environment_id}), as_of)
            route = evidence.value.key if isinstance(evidence.value, RouteClaim) else evidence.value.route
            expected = route.source if route.source.scope == scope else route.destination
            if (installed is None or installed.environments != ((environment_id, scope),)
                    or installed.value != expected):
                raise AssessmentInputDenied('Route evidence no longer matches the current installation')

    def route_claims(self, ctx, actor_subject, routes, as_of):
        self._principal(ctx, actor_subject)
        claims = []
        for route in routes:
            # Require exact grants before even querying a route's evidence.
            principal = self._principal(ctx, actor_subject)
            for scope in (route.source.scope, route.destination.scope):
                if not any(grant.role in ('JOB_READER', 'EXECUTION_OPERATOR')
                           and grant.scope == scope and grant.expires_at > as_of
                           for grant in principal.grants):
                    raise AssessmentInputDenied('Assessment route scope is no longer authorized')
            evidence = self._owner._repository.latest(ctx, 'ROUTE',
                _digest({'kind': 'ROUTE', 'route': route_document(route)}), as_of)
            if evidence is not None:
                self._authorize_evidence(ctx, actor_subject, evidence, as_of)
                if not isinstance(evidence.value, RouteClaim) or evidence.value.key != route:
                    raise AssessmentInputDenied('Assessment route evidence does not match')
                claims.append(evidence.value)
        return tuple(claims)

    def reviewed_findings(self, ctx, actor_subject, route,
                          source: NormalizedDiscovery | None,
                          destination: NormalizedDiscovery | None, as_of):
        principal = self._principal(ctx, actor_subject)
        for scope in (route.source.scope, route.destination.scope):
            if not any(grant.role in ('JOB_READER', 'EXECUTION_OPERATOR') and grant.scope == scope
                       and grant.expires_at > as_of for grant in principal.grants):
                raise AssessmentInputDenied('Assessment review scope is no longer authorized')
        if source is None or destination is None:
            return ()
        findings = []
        for control in ('POLICY_TRANSLATION', 'SECURITY_EQUIVALENCE', 'RECOVERY_READINESS'):
            binding = {'kind': 'CONTROL', 'route': route_document(route), 'control': control,
                'sourceRawSnapshotDigest': source.original.digest,
                'destinationRawSnapshotDigest': destination.original.digest,
                'sourceSnapshotDigest': source.inventory.digest,
                'destinationSnapshotDigest': destination.inventory.digest,
                'normalizerVersion': NORMALIZER_VERSION}
            evidence = self._owner._repository.latest(ctx, 'CONTROL', _digest(binding), as_of)
            if evidence is not None:
                self._authorize_evidence(ctx, actor_subject, evidence, as_of)
                if not isinstance(evidence.value, ReviewedFinding) or evidence.value.route != route:
                    raise AssessmentInputDenied('Assessment finding route does not match')
                findings.append(evidence.value)
        return tuple(findings)
