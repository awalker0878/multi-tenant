"""Append-only, exact-scope inventory storage for an internal discovery ingest.

This repository is not an HTTP submission interface. A separate service must
verify the signed campaign issuer, currently active collector enrollment,
read-only credential and result provenance independently at *each* call. The
configured verifier is mandatory for writes; without one publication refuses.
Only a separately provisioned ingestion SQL login receives INSERT privileges.
No B10 native ownership, job grant or mutation lock is an inventory grant.
"""
from __future__ import annotations

import hashlib
import json
import re
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterator, Protocol

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence.store import TenantContext

from .model import (DiscoveryCampaignAuthorization, DiscoveryResult,
                    NativeIdentity, _digest, _json, _object_json)


_ROLE = re.compile(r'^[a-z][a-z0-9_]{0,62}$')
_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_DIGEST = re.compile(r'^[0-9a-f]{64}$')


class DiscoveryConflict(RuntimeError):
    """The campaign or generation was already published, or its scope changed."""


@dataclass(frozen=True, slots=True)
class VerificationEvidence:
    """Result of an external verifier; this value alone is not authentication."""

    authorization_digest: str
    result_digest: str | None
    verified_by: str
    verification_reference: str

    def __post_init__(self) -> None:
        if (not isinstance(self.authorization_digest, str)
                or _DIGEST.fullmatch(self.authorization_digest) is None
                or self.result_digest is not None
                and (not isinstance(self.result_digest, str)
                     or _DIGEST.fullmatch(self.result_digest) is None)
                or not isinstance(self.verified_by, str)
                or not 1 <= len(self.verified_by) <= 512
                or not isinstance(self.verification_reference, str)
                or not 1 <= len(self.verification_reference) <= 512):
            raise ValueError('Invalid verifier evidence')


class DiscoveryIngestVerifier(Protocol):
    """Production implementations must consult independent authority systems.

    A verifier must validate the issuer signature and authorization for the
    exact environment, live collector enrollment, read credential restrictions,
    and cryptographic provenance of the collector result on every publication.
    It must use its own trusted clocks and sources, not browser-supplied fields.
    External signed evidence checkpoints still gate site release after ingest;
    an in-database hash chain alone does not prove custody after a whole restore.
    """

    def verify_campaign(self, campaign: DiscoveryCampaignAuthorization,
                        environment_id: str, checked_at: datetime
                        ) -> VerificationEvidence: ...

    def verify_result(self, campaign: DiscoveryCampaignAuthorization,
                      result: DiscoveryResult, environment_id: str,
                      checked_at: datetime) -> VerificationEvidence: ...


@dataclass(frozen=True, slots=True)
class StoredGeneration:
    environment_id: str
    generation: int
    campaign_id: str
    scope: PlanScope
    authorization_digest: str
    result_digest: str
    captured_at: datetime
    completeness: str
    collection_errors: tuple[str, ...]
    missing_privileges: tuple[str, ...]
    object_count: int


@dataclass(frozen=True, slots=True)
class StoredObservation:
    generation: int
    identity: NativeIdentity
    facts: tuple[dict, ...]
    object_digest: str


class DiscoveryRepository:
    """Read access plus optional privileged, independently verified ingestion.

    The supplied writer role must be a dedicated NOSUPERUSER/NOBYPASSRLS login
    with no site-worker group membership. The verifier and role are both absent
    by default, so ordinary API construction has no publication capability.
    """

    def __init__(self, connection_factory: Callable, *,
                 ingest_verifier: DiscoveryIngestVerifier | None = None,
                 ingest_role: str | None = None):
        if not callable(connection_factory):
            raise TypeError('A PostgreSQL connection factory is required')
        if ingest_role is not None and (not isinstance(ingest_role, str)
                                        or _ROLE.fullmatch(ingest_role) is None):
            raise ValueError('Invalid dedicated discovery ingest role')
        self._connect = connection_factory
        self._verifier = ingest_verifier
        self._ingest_role = ingest_role

    @contextmanager
    def _session(self, ctx: TenantContext, *, write: bool = False) -> Iterator:
        if not isinstance(ctx, TenantContext):
            raise TypeError('A trusted tenant context is required')
        if write and (self._verifier is None or self._ingest_role is None):
            raise RuntimeError('Discovery ingestion requires a trusted verifier and role')
        with self._connect() as connection:
            if connection.autocommit:
                raise RuntimeError('Discovery access requires a transaction')
            role = connection.execute(
                'SELECT current_user, rolsuper, rolbypassrls FROM pg_catalog.pg_roles '
                'WHERE rolname = current_user').fetchone()
            if role is None or role[1] or role[2]:
                raise RuntimeError('Discovery role must enforce RLS')
            if write and role[0] != self._ingest_role:
                raise RuntimeError('Only the dedicated discovery ingest role may publish')
            if write and connection.execute(
                    'SELECT hosting_controlplane.is_site_worker_role()'
            ).fetchone()[0]:
                raise RuntimeError('Site worker SQL logins may not publish discovery')
            connection.execute(
                "SELECT set_config('app.organization_id', %s, true), "
                "set_config('app.tenant_id', %s, true)",
                (ctx.organization_id, ctx.tenant_id))
            yield connection

    @staticmethod
    def _require_scope(ctx: TenantContext, scope: PlanScope,
                       environment_id: str) -> None:
        if (not isinstance(ctx, TenantContext) or not isinstance(scope, PlanScope)
                or (scope.organization_id, scope.tenant_id) !=
                (ctx.organization_id, ctx.tenant_id)
                or not isinstance(environment_id, str)
                or _ID.fullmatch(environment_id) is None):
            raise ValueError('Discovery requires one exact trusted tenant and environment')

    @staticmethod
    def _scope_args(ctx: TenantContext, scope: PlanScope,
                    environment_id: str) -> tuple:
        return (ctx.organization_id, ctx.tenant_id, environment_id,
                scope.site_id, scope.security_domain_id, scope.endpoint_id,
                scope.native_scope_id, scope.platform_family)

    def register_verified_campaign(self, ctx: TenantContext, environment_id: str,
                                   campaign: DiscoveryCampaignAuthorization) -> None:
        if not isinstance(campaign, DiscoveryCampaignAuthorization):
            raise TypeError('An immutable discovery campaign is required')
        self._require_scope(ctx, campaign.scope, environment_id)
        with self._session(ctx, write=True) as connection:
            environment = connection.execute(
                'SELECT 1 FROM hosting_controlplane.environment_registrations '
                'WHERE organization_id = %s AND tenant_id = %s AND environment_id = %s '
                'AND site_id = %s AND security_domain_id = %s AND endpoint_id = %s '
                'AND native_scope_id = %s AND platform_family = %s',
                self._scope_args(ctx, campaign.scope, environment_id)).fetchone()
            if environment is None:
                raise ValueError('No exact declared environment selector exists')
            # A competing admission may hold this lock past expiry or revocation.
            # Check live authority only after the serialization wait has finished.
            key = hashlib.sha256(_json(('campaign', ctx.organization_id,
                                       ctx.tenant_id, campaign.campaign_id)).encode()).digest()
            connection.execute('SELECT pg_advisory_xact_lock(%s::bigint)',
                               (int.from_bytes(key[:8], 'big', signed=True),))
            checked_at = connection.execute('SELECT clock_timestamp()').fetchone()[0]
            if not campaign.issued_at <= checked_at < campaign.expires_at:
                raise ValueError('Discovery campaign is outside its validity window')
            # The verifier must independently recheck active enrollment and the
            # campaign issuer now. A constructible evidence object is not passed
            # by a web caller and is not accepted without this callback.
            proof = self._verifier.verify_campaign(campaign, environment_id, checked_at)
            if (not isinstance(proof, VerificationEvidence)
                    or proof.authorization_digest != campaign.digest()
                    or proof.result_digest is not None):
                raise ValueError('Campaign verifier did not bind exact authorization')
            # Live authority is checked even when identical bytes already exist.
            existing = connection.execute(
                'SELECT environment_id, authorization_digest '
                'FROM hosting_controlplane.discovery_campaigns '
                'WHERE organization_id = %s AND tenant_id = %s AND campaign_id = %s',
                (ctx.organization_id, ctx.tenant_id, campaign.campaign_id)).fetchone()
            if existing is not None:
                if existing != (environment_id, campaign.digest()):
                    raise DiscoveryConflict('Campaign identity has different content or scope')
                return
            try:
                connection.execute(
                    'INSERT INTO hosting_controlplane.discovery_campaigns '
                    '(organization_id, tenant_id, campaign_id, environment_id, site_id, '
                    'security_domain_id, endpoint_id, native_scope_id, platform_family, '
                    'authority_reference, collector_id, allowed_kinds, issued_at, '
                    'expires_at, max_pages, max_objects, max_page_size, '
                    'authorization_digest, verified_by, verification_reference) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '
                    '%s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (ctx.organization_id, ctx.tenant_id, campaign.campaign_id,
                     environment_id, campaign.scope.site_id,
                     campaign.scope.security_domain_id, campaign.scope.endpoint_id,
                     campaign.scope.native_scope_id, campaign.scope.platform_family,
                     campaign.authority_reference, campaign.collector_id,
                     list(campaign.allowed_kinds), campaign.issued_at,
                     campaign.expires_at, campaign.max_pages, campaign.max_objects,
                     campaign.max_page_size, campaign.digest(), proof.verified_by,
                     proof.verification_reference))
            except Exception as exc:
                if getattr(exc, 'sqlstate', None) == '23505':
                    raise DiscoveryConflict('Campaign ID was already registered') from exc
                raise
            connection.execute(
                'INSERT INTO hosting_controlplane.audit_events '
                '(organization_id, tenant_id, actor_id, correlation_id, action, '
                'record_kind, record_id, revision, record_digest, details) VALUES '
                "(%s, %s, %s, %s, 'RECORD_CREATE', 'DiscoveryCampaign', "
                '%s, 1, %s, %s::jsonb)',
                (ctx.organization_id, ctx.tenant_id, proof.verified_by,
                 campaign.campaign_id, campaign.campaign_id, campaign.digest(),
                 _json({'environmentId': environment_id,
                        'verificationReference': proof.verification_reference})))

    @staticmethod
    def _campaign_from_row(ctx: TenantContext, campaign_id: str, row
                           ) -> DiscoveryCampaignAuthorization:
        (site, wsd, endpoint, native_scope, family, authority_ref, collector,
         kinds, issued, expires, max_pages, max_objects, max_page_size,
         digest) = row
        campaign = DiscoveryCampaignAuthorization(
            campaign_id, PlanScope(ctx.organization_id, ctx.tenant_id, site, wsd,
                                   endpoint, native_scope, family), authority_ref,
            collector, tuple(kinds), issued, expires, max_pages, max_objects,
            max_page_size)
        if campaign.digest() != digest:
            raise RuntimeError('Stored discovery campaign digest has changed')
        return campaign

    def publish_verified_result(self, ctx: TenantContext, environment_id: str,
                                result: DiscoveryResult) -> StoredGeneration:
        if not isinstance(result, DiscoveryResult):
            raise TypeError('An immutable discovery result is required')
        self._require_scope(ctx, result.scope, environment_id)
        # Rebuild to detect a Python object changed after construction.
        rebuilt = DiscoveryResult(result.campaign_id, result.authorization_digest,
                                  result.scope, result.captured_at,
                                  result.completeness, result.objects,
                                  result.collection_errors,
                                  result.missing_privileges)
        if rebuilt.digest != result.digest:
            raise ValueError('Discovery result digest is stale')
        with self._session(ctx, write=True) as connection:
            row = connection.execute(
                'SELECT site_id, security_domain_id, endpoint_id, native_scope_id, '
                'platform_family, authority_reference, collector_id, allowed_kinds, '
                'issued_at, expires_at, max_pages, max_objects, max_page_size, '
                'authorization_digest '
                'FROM hosting_controlplane.discovery_campaigns '
                'WHERE organization_id = %s AND tenant_id = %s '
                'AND environment_id = %s AND campaign_id = %s',
                (ctx.organization_id, ctx.tenant_id, environment_id,
                 result.campaign_id)).fetchone()
            if row is None:
                raise ValueError('Campaign was not registered for this environment')
            campaign = self._campaign_from_row(ctx, result.campaign_id, row)
            # Serialize all campaigns for this scope before reading trusted time
            # or verifying live authority. A lock wait must not preserve stale
            # enrollment, witness, revocation or campaign validity decisions.
            key = hashlib.sha256(_json(self._scope_args(
                ctx, campaign.scope, environment_id)).encode('utf-8')).digest()
            connection.execute('SELECT pg_advisory_xact_lock(%s::bigint)',
                               (int.from_bytes(key[:8], 'big', signed=True),))
            checked_at = connection.execute('SELECT clock_timestamp()').fetchone()[0]
            if (campaign.scope != result.scope
                    or result.authorization_digest != campaign.digest()
                    or not campaign.issued_at <= result.captured_at <= checked_at
                    or checked_at >= campaign.expires_at
                    or len(result.objects) > campaign.max_objects
                    or any(obj.identity.resource_kind not in campaign.allowed_kinds
                           for obj in result.objects)):
                raise ValueError('Result is outside exact campaign scope or bounds')
            proof = self._verifier.verify_result(campaign, result,
                                                 environment_id, checked_at)
            if (not isinstance(proof, VerificationEvidence)
                    or proof.authorization_digest != campaign.digest()
                    or proof.result_digest != result.digest):
                raise ValueError('Result verifier did not bind exact provenance')
            # A response lost after commit must not create another generation.
            # Changed bytes under the same campaign remain a hard conflict.
            existing = connection.execute(
                'SELECT generation, campaign_id, authorization_digest, result_digest, '
                'captured_at, completeness, collection_errors, missing_privileges, '
                'object_count FROM hosting_controlplane.discovery_generations '
                'WHERE organization_id = %s AND tenant_id = %s AND environment_id = %s '
                'AND site_id = %s AND security_domain_id = %s AND endpoint_id = %s '
                'AND native_scope_id = %s AND platform_family = %s AND campaign_id = %s',
                (*self._scope_args(ctx, campaign.scope, environment_id),
                 campaign.campaign_id)).fetchone()
            if existing is not None:
                if existing[2] != campaign.digest() or existing[3] != result.digest:
                    raise DiscoveryConflict('Campaign result has different immutable content')
                return self._generation_row(environment_id, campaign.scope, existing)
            generation = connection.execute(
                'SELECT COALESCE(MAX(generation), 0) + 1 '
                'FROM hosting_controlplane.discovery_generations '
                'WHERE organization_id = %s AND tenant_id = %s AND environment_id = %s',
                (ctx.organization_id, ctx.tenant_id, environment_id)).fetchone()[0]
            try:
                connection.execute(
                    'INSERT INTO hosting_controlplane.discovery_generations '
                    '(organization_id, tenant_id, environment_id, generation, campaign_id, '
                    'site_id, security_domain_id, endpoint_id, native_scope_id, '
                    'platform_family, authorization_digest, result_digest, captured_at, '
                    'completeness, collection_errors, missing_privileges, object_count, '
                    'published_by, verification_reference) VALUES '
                    '(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '
                    '%s, %s, %s, %s, %s)',
                    (ctx.organization_id, ctx.tenant_id, environment_id,
                     generation, campaign.campaign_id, campaign.scope.site_id,
                     campaign.scope.security_domain_id, campaign.scope.endpoint_id,
                     campaign.scope.native_scope_id, campaign.scope.platform_family,
                     campaign.digest(), result.digest, result.captured_at,
                     result.completeness, list(result.collection_errors),
                     list(result.missing_privileges), len(result.objects),
                     proof.verified_by, proof.verification_reference))
            except Exception as exc:
                if getattr(exc, 'sqlstate', None) == '23505':
                    raise DiscoveryConflict('Campaign result already published') from exc
                raise
            for obj in result.objects:
                payload = _object_json(obj)
                connection.execute(
                    'INSERT INTO hosting_controlplane.discovery_observations '
                    '(organization_id, tenant_id, environment_id, generation, '
                    'endpoint_id, native_scope_id, platform_family, resource_kind, '
                    'native_id, facts_json, object_digest) VALUES '
                    '(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (ctx.organization_id, ctx.tenant_id, environment_id, generation,
                     *obj.identity.key(), _json(payload['facts']), _digest(payload)))
            # Only COMPLETE results may propose absence. PARTIAL and UNKNOWN
            # generations are historical observations and cannot remove a
            # previously seen resource, including after restricted read errors.
            if result.completeness == 'COMPLETE':
                for kind in campaign.allowed_kinds:
                    prior = connection.execute(
                        'SELECT g.generation FROM hosting_controlplane.discovery_generations g '
                        'JOIN hosting_controlplane.discovery_campaigns c USING '
                        '(organization_id, tenant_id, campaign_id) '
                        'WHERE g.organization_id = %s AND g.tenant_id = %s '
                        'AND g.environment_id = %s AND g.generation < %s '
                        "AND g.completeness = 'COMPLETE' AND %s = ANY(c.allowed_kinds) "
                        'ORDER BY g.generation DESC LIMIT 1',
                        (ctx.organization_id, ctx.tenant_id, environment_id,
                         generation, kind)).fetchone()
                    if prior is not None:
                        connection.execute(
                            'INSERT INTO hosting_controlplane.discovery_absence_candidates '
                            '(organization_id, tenant_id, environment_id, generation, '
                            'resource_kind, native_id, prior_generation) '
                            'SELECT o.organization_id, o.tenant_id, o.environment_id, '
                            '%s, o.resource_kind, o.native_id, o.generation '
                            'FROM hosting_controlplane.discovery_observations o '
                            'WHERE o.organization_id = %s AND o.tenant_id = %s '
                            'AND o.environment_id = %s AND o.generation = %s '
                            'AND o.resource_kind = %s AND NOT EXISTS '
                            '(SELECT 1 FROM hosting_controlplane.discovery_observations now '
                            ' WHERE now.organization_id = o.organization_id '
                            ' AND now.tenant_id = o.tenant_id '
                            ' AND now.environment_id = o.environment_id '
                            ' AND now.generation = %s AND now.resource_kind = o.resource_kind '
                            ' AND now.native_id = o.native_id)',
                            (generation, ctx.organization_id, ctx.tenant_id,
                             environment_id, prior[0], kind, generation))
            connection.execute(
                'INSERT INTO hosting_controlplane.audit_events '
                '(organization_id, tenant_id, actor_id, correlation_id, action, '
                'record_kind, record_id, revision, record_digest, details) VALUES '
                "(%s, %s, %s, %s, 'RECORD_CREATE', 'DiscoveryGeneration', "
                '%s, %s, %s, %s::jsonb)',
                (ctx.organization_id, ctx.tenant_id, proof.verified_by,
                 campaign.campaign_id, environment_id + ':' + str(generation),
                 generation, result.digest,
                 _json({'campaignId': campaign.campaign_id,
                        'environmentId': environment_id,
                        'completeness': result.completeness,
                        'verificationReference': proof.verification_reference})))
            return StoredGeneration(environment_id, generation, campaign.campaign_id,
                                    campaign.scope, campaign.digest(), result.digest,
                                    result.captured_at, result.completeness,
                                    result.collection_errors,
                                    result.missing_privileges, len(result.objects))

    def list_generations(self, ctx: TenantContext, scope: PlanScope,
                         environment_id: str, *, after: int = 0,
                         limit: int = 51) -> list[StoredGeneration]:
        self._require_scope(ctx, scope, environment_id)
        if (type(after) is not int or after < 0 or type(limit) is not int
                or not 1 <= limit <= 101):
            raise ValueError('Invalid bounded generation page')
        with self._session(ctx) as connection:
            rows = connection.execute(
                'SELECT generation, campaign_id, authorization_digest, result_digest, '
                'captured_at, completeness, collection_errors, missing_privileges, '
                'object_count FROM hosting_controlplane.discovery_generations '
                'WHERE organization_id = %s AND tenant_id = %s AND environment_id = %s '
                'AND site_id = %s AND security_domain_id = %s AND endpoint_id = %s '
                'AND native_scope_id = %s AND platform_family = %s '
                'AND generation > %s ORDER BY generation LIMIT %s',
                (*self._scope_args(ctx, scope, environment_id), after, limit)).fetchall()
        return [self._generation_row(environment_id, scope, row) for row in rows]

    @staticmethod
    def _generation_row(environment_id: str, scope: PlanScope, row
                        ) -> StoredGeneration:
        return StoredGeneration(environment_id, row[0], row[1], scope, row[2],
                                row[3], row[4], row[5], tuple(row[6]),
                                tuple(row[7]), row[8])

    def latest_generation(self, ctx: TenantContext, scope: PlanScope,
                          environment_id: str) -> StoredGeneration | None:
        """Return only the latest generation of this exact native selector."""
        self._require_scope(ctx, scope, environment_id)
        with self._session(ctx) as connection:
            row = connection.execute(
                'SELECT generation, campaign_id, authorization_digest, result_digest, '
                'captured_at, completeness, collection_errors, missing_privileges, '
                'object_count FROM hosting_controlplane.discovery_generations '
                'WHERE organization_id = %s AND tenant_id = %s AND environment_id = %s '
                'AND site_id = %s AND security_domain_id = %s AND endpoint_id = %s '
                'AND native_scope_id = %s AND platform_family = %s '
                'ORDER BY generation DESC LIMIT 1',
                self._scope_args(ctx, scope, environment_id)).fetchone()
        return self._generation_row(environment_id, scope, row) if row else None

    def get_generation(self, ctx: TenantContext, scope: PlanScope,
                       environment_id: str, generation: int) -> StoredGeneration | None:
        """Read one exact generation without silently advancing a saved selection."""
        self._require_scope(ctx, scope, environment_id)
        if type(generation) is not int or generation < 1:
            raise ValueError('An exact positive generation is required')
        with self._session(ctx) as connection:
            row = connection.execute(
                'SELECT generation, campaign_id, authorization_digest, result_digest, '
                'captured_at, completeness, collection_errors, missing_privileges, '
                'object_count FROM hosting_controlplane.discovery_generations '
                'WHERE organization_id = %s AND tenant_id = %s AND environment_id = %s '
                'AND site_id = %s AND security_domain_id = %s AND endpoint_id = %s '
                'AND native_scope_id = %s AND platform_family = %s AND generation = %s',
                (*self._scope_args(ctx, scope, environment_id), generation)).fetchone()
        return self._generation_row(environment_id, scope, row) if row else None

    def list_observations(self, ctx: TenantContext, scope: PlanScope,
                          environment_id: str, generation: int, *,
                          after: tuple[str, str] | None = None,
                          limit: int = 51) -> list[StoredObservation]:
        self._require_scope(ctx, scope, environment_id)
        if (type(generation) is not int or generation < 1
                or type(limit) is not int or not 1 <= limit <= 101
                or after is not None and (not isinstance(after, tuple)
                    or len(after) != 2 or not all(isinstance(x, str) for x in after)
                    or len(after[1]) > 512)):
            raise ValueError('Invalid bounded observation page')
        with self._session(ctx) as connection:
            rows = connection.execute(
                'SELECT o.resource_kind, o.native_id, o.facts_json, o.object_digest '
                'FROM hosting_controlplane.discovery_observations o '
                'JOIN hosting_controlplane.discovery_generations g USING '
                '(organization_id, tenant_id, environment_id, generation) '
                'WHERE g.organization_id = %s AND g.tenant_id = %s '
                'AND g.environment_id = %s AND g.site_id = %s '
                'AND g.security_domain_id = %s AND g.endpoint_id = %s '
                'AND g.native_scope_id = %s AND g.platform_family = %s '
                'AND g.generation = %s AND (o.resource_kind, o.native_id) > (%s, %s) '
                'ORDER BY o.resource_kind, o.native_id LIMIT %s',
                (*self._scope_args(ctx, scope, environment_id), generation,
                 *(after or ('', '')), limit)).fetchall()
        observations = []
        for kind, native_id, facts_json, digest in rows:
            facts = json.loads(facts_json)
            identity = NativeIdentity(scope.endpoint_id, scope.native_scope_id,
                                      scope.platform_family, kind, native_id)
            payload = {'binding': dict(zip(('endpointId', 'nativeScopeId',
                                            'platformFamily', 'resourceKind', 'nativeId'),
                                           identity.key())), 'facts': facts}
            if _digest(payload) != digest:
                raise RuntimeError('Stored discovery observation digest has changed')
            observations.append(StoredObservation(generation, identity,
                                                  tuple(facts), digest))
        return observations

    def list_absence_candidates(self, ctx: TenantContext, scope: PlanScope,
                                environment_id: str, generation: int, *,
                                after: tuple[str, str] | None = None,
                                limit: int = 51) -> list[tuple[str, str, int]]:
        self._require_scope(ctx, scope, environment_id)
        if (type(generation) is not int or generation < 1
                or type(limit) is not int or not 1 <= limit <= 101
                or after is not None and (not isinstance(after, tuple)
                    or len(after) != 2 or not all(isinstance(x, str) for x in after)
                    or len(after[1]) > 512)):
            raise ValueError('Invalid bounded absence page')
        with self._session(ctx) as connection:
            rows = connection.execute(
                'SELECT a.resource_kind, a.native_id, a.prior_generation '
                'FROM hosting_controlplane.discovery_absence_candidates a '
                'JOIN hosting_controlplane.discovery_generations g USING '
                '(organization_id, tenant_id, environment_id, generation) '
                'WHERE g.organization_id = %s AND g.tenant_id = %s '
                'AND g.environment_id = %s AND g.site_id = %s '
                'AND g.security_domain_id = %s AND g.endpoint_id = %s '
                'AND g.native_scope_id = %s AND g.platform_family = %s '
                'AND g.generation = %s AND (a.resource_kind, a.native_id) > (%s, %s) '
                'ORDER BY a.resource_kind, a.native_id LIMIT %s',
                (*self._scope_args(ctx, scope, environment_id), generation,
                 *(after or ('', '')), limit)).fetchall()
        return [(kind, native_id, prior) for kind, native_id, prior in rows]
