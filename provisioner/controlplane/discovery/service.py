"""Read-only assessment composition over authorized, generation-pinned inputs.

There is intentionally no default trust provider. Environment declarations,
browser fields, this service's output and the existence of a collector cannot
establish installed product provenance or native route qualification. Deployers
must supply an independently backed provider before enabling the endpoint.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence.store import TenantContext

from .assessment import (AssessmentEngine, AssessmentScopeAccess,
                         DestinationAssessment, DestinationOption, ReviewedFinding)
from .model import NativeIdentity, _utc
from .normalization import (NormalizedDiscovery, NormalizationHeld,
                            hydrate_generation, normalize_discovery)
from .persistence import StoredGeneration, StoredObservation
from .routes import InstalledTuple, METHODS, RouteCatalogue, RouteClaim, RouteKey


_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')


@dataclass(frozen=True, slots=True)
class AssessmentSelection:
    """User selection only; neither the ID nor the generation grants access."""

    environment_id: str
    generation: int

    def __post_init__(self) -> None:
        if (not isinstance(self.environment_id, str)
                or not _ID.fullmatch(self.environment_id)
                or type(self.generation) is not int or self.generation < 1):
            raise ValueError('An environment and pinned positive generation are required')


@dataclass(frozen=True, slots=True)
class AssessmentDestination:
    selection: AssessmentSelection
    capacity_kind: str | None = None
    capacity_native_id: str | None = None

    def __post_init__(self) -> None:
        if (not isinstance(self.selection, AssessmentSelection)
                or (self.capacity_kind is None) != (self.capacity_native_id is None)
                or self.capacity_kind is not None and self.capacity_kind not in
                {'pool', 'cluster', 'quota', 'datastore'}
                or self.capacity_native_id is not None and
                (not isinstance(self.capacity_native_id, str)
                 or not 0 < len(self.capacity_native_id) <= 512
                 or not self.capacity_native_id.strip()
                 or any(ord(char) < 32 or ord(char) == 127
                        for char in self.capacity_native_id))):
            raise ValueError('An exact native capacity identity or no selection is required')


@dataclass(frozen=True, slots=True)
class VerifiedAssessmentEnvironment:
    """Provider result, checked against actor, tenant, purpose and trusted time."""

    environment_id: str
    installation: InstalledTuple
    access: AssessmentScopeAccess


class AssessmentRepository(Protocol):
    def get_generation(self, ctx: TenantContext, scope: PlanScope,
                       environment_id: str, generation: int
                       ) -> StoredGeneration | None: ...

    def list_observations(self, ctx: TenantContext, scope: PlanScope,
                          environment_id: str, generation: int, *,
                          after: tuple[str, str] | None = None,
                          limit: int = 51) -> list[StoredObservation]: ...


class TrustedAssessmentInputs(Protocol):
    """Implement against live directory and independently verified evidence.

    ``resolve_environment`` must verify read permission and observed installed
    tuple provenance, including current endpoint/version identity, independently
    of the selector directory. Claims and control findings require authenticated
    issuer, signature, authority and custody checks. Findings bind normalized
    snapshot digests, with the raw inputs available for verifier reconciliation.
    Construction of these Python records is not verification.
    """

    def resolve_environment(self, ctx: TenantContext, actor_subject: str,
                            environment_id: str, purpose: str, as_of: datetime
                            ) -> VerifiedAssessmentEnvironment: ...

    def route_claims(self, ctx: TenantContext, actor_subject: str,
                     routes: tuple[RouteKey, ...], as_of: datetime
                     ) -> tuple[RouteClaim, ...]: ...

    def reviewed_findings(self, ctx: TenantContext, actor_subject: str,
                          route: RouteKey, source: NormalizedDiscovery | None,
                          destination: NormalizedDiscovery | None,
                          as_of: datetime) -> tuple[ReviewedFinding, ...]: ...


@dataclass(frozen=True, slots=True)
class AssessmentInputBinding:
    selection: AssessmentSelection
    installation: InstalledTuple
    discovery: NormalizedDiscovery | None

    def to_document(self) -> dict:
        scope = self.installation.scope
        return {'environmentId': self.selection.environment_id,
                'generation': self.selection.generation,
                'endpointId': scope.endpoint_id, 'nativeScopeId': scope.native_scope_id,
                'platformFamily': scope.platform_family,
                'productTupleId': self.installation.product_tuple_id,
                'productTupleDigest': self.installation.product_tuple_digest,
                'observation': self.discovery.binding() if self.discovery else None}


@dataclass(frozen=True, slots=True)
class AssessmentComparison:
    assessed_at: datetime
    source: AssessmentInputBinding
    destinations: tuple[AssessmentInputBinding, ...]
    assessments: tuple[DestinationAssessment, ...]

    def to_document(self) -> dict:
        return {'format': 'hosting-discovery-comparison/1',
                'assessedAt': self.assessed_at.isoformat(),
                'sourceInput': self.source.to_document(),
                'destinationInputs': [item.to_document() for item in self.destinations],
                'assessments': [item.to_document() for item in self.assessments],
                'executionAuthorized': False}


class AssessmentService:
    """No native transport, ingestion, ownership or execution capability."""

    def __init__(self, repository: AssessmentRepository,
                 trusted_inputs: TrustedAssessmentInputs, *,
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
                 max_snapshot_age: timedelta = timedelta(hours=24)):
        if (not all(callable(getattr(repository, method, None))
                    for method in ('get_generation', 'list_observations'))
                or not all(callable(getattr(trusted_inputs, method, None))
                           for method in ('resolve_environment', 'route_claims',
                                          'reviewed_findings'))
                or not callable(clock) or not isinstance(max_snapshot_age, timedelta)
                or not timedelta(0) < max_snapshot_age <= timedelta(days=7)):
            raise ValueError('Pinned repository and independent assessment provider are required')
        self._repository = repository
        self._inputs = trusted_inputs
        self._clock = clock
        self._max_age = max_snapshot_age

    def _resolve(self, ctx: TenantContext, actor: str, selection: AssessmentSelection,
                 purpose: str, now: datetime) -> VerifiedAssessmentEnvironment:
        verified = self._inputs.resolve_environment(
            ctx, actor, selection.environment_id, purpose, now)
        if (not isinstance(verified, VerifiedAssessmentEnvironment)
                or verified.environment_id != selection.environment_id
                or not isinstance(verified.installation, InstalledTuple)
                or not isinstance(verified.access, AssessmentScopeAccess)):
            raise PermissionError('Independent environment verification is unavailable')
        scope, access = verified.installation.scope, verified.access
        if ((scope.organization_id, scope.tenant_id) !=
                (ctx.organization_id, ctx.tenant_id)
                or access.scope != scope or access.actor_subject != actor
                or access.purpose != purpose
                or not access.observed_at <= now < access.expires_at):
            raise PermissionError('Current exact-scope assessment access is required')
        return verified

    def _load(self, ctx: TenantContext, selection: AssessmentSelection,
              environment: VerifiedAssessmentEnvironment) -> AssessmentInputBinding:
        scope = environment.installation.scope
        generation = self._repository.get_generation(
            ctx, scope, selection.environment_id, selection.generation)
        if generation is None:
            return AssessmentInputBinding(selection, environment.installation, None)
        if (not isinstance(generation, StoredGeneration)
                or generation.scope != scope
                or generation.environment_id != selection.environment_id
                or generation.generation != selection.generation
                or type(generation.object_count) is not int
                or not 0 <= generation.object_count <= 100000):
            raise NormalizationHeld('Repository returned another generation or scope')
        observations = []
        after = None
        while True:
            page = self._repository.list_observations(
                ctx, scope, selection.environment_id, selection.generation,
                after=after, limit=100)
            if not isinstance(page, list) or len(page) > 100:
                raise NormalizationHeld('Invalid bounded observation page')
            for item in page:
                if not isinstance(item, StoredObservation):
                    raise NormalizationHeld('Invalid stored observation')
                key = item.identity.resource_kind, item.identity.native_id
                if after is not None and key <= after:
                    raise NormalizationHeld('Observation page repeated or changed order')
                after = key
                observations.append(item)
            if len(observations) > generation.object_count:
                raise NormalizationHeld('Observation count exceeds pinned generation')
            if len(page) < 100:
                break
        result = hydrate_generation(generation, tuple(observations))
        return AssessmentInputBinding(selection, environment.installation,
                                      normalize_discovery(result))

    def compare(self, ctx: TenantContext, actor_subject: str,
                source: AssessmentSelection, workload_native_id: str,
                destinations: tuple[AssessmentDestination, ...], *,
                method: str, guest_profile: str, network_mode: str, data_mode: str
                ) -> AssessmentComparison:
        if (not isinstance(ctx, TenantContext)
                or not isinstance(actor_subject, str) or not _ID.fullmatch(actor_subject)
                or not isinstance(source, AssessmentSelection)
                or not isinstance(destinations, tuple) or not 2 <= len(destinations) <= 20
                or any(not isinstance(item, AssessmentDestination) for item in destinations)
                or len({item.selection.environment_id for item in destinations}) != len(destinations)
                or any(item.selection.environment_id == source.environment_id
                       for item in destinations)
                or method not in METHODS
                or not all(isinstance(value, str) and _ID.fullmatch(value)
                           for value in (guest_profile, network_mode, data_mode))):
            raise ValueError('Exact source, two distinct destinations and route profile required')
        now = self._clock()
        if not _utc(now):
            raise ValueError('Assessment clock must return trusted UTC time')
        origin = self._resolve(ctx, actor_subject, source, 'SOURCE_READ', now)
        targets = tuple(self._resolve(ctx, actor_subject, item.selection,
                                      'DESTINATION_READ', now) for item in destinations)
        # Authorize every scope before reading any inventory. Aliases for one
        # native scope cannot pad out a multi-destination comparison.
        scopes = (origin.installation.scope, *(item.installation.scope for item in targets))
        if len(set(scopes)) != len(scopes):
            raise ValueError('Assessment environments must name distinct native scopes')
        workload = NativeIdentity(scopes[0].endpoint_id, scopes[0].native_scope_id,
                                  scopes[0].platform_family, 'vm', workload_native_id)
        source_input = self._load(ctx, source, origin)
        destination_inputs = tuple(self._load(ctx, item.selection, target)
                                   for item, target in zip(destinations, targets))
        routes = tuple(RouteKey(origin.installation, target.installation, method,
                                guest_profile, network_mode, data_mode) for target in targets)
        claims = self._inputs.route_claims(ctx, actor_subject, routes, now)
        if (not isinstance(claims, tuple)
                or any(not isinstance(claim, RouteClaim) or claim.key not in routes
                       for claim in claims)):
            raise PermissionError('Route verifier returned unrelated claims')
        options = []
        for selection, target, binding, route in zip(
                destinations, targets, destination_inputs, routes):
            findings = self._inputs.reviewed_findings(
                ctx, actor_subject, route, source_input.discovery, binding.discovery, now)
            if (not isinstance(findings, tuple)
                    or any(not isinstance(item, ReviewedFinding) or item.route != route
                           for item in findings)):
                raise PermissionError('Review verifier returned unrelated control findings')
            scope = target.installation.scope
            capacity = (NativeIdentity(scope.endpoint_id, scope.native_scope_id,
                                       scope.platform_family, selection.capacity_kind,
                                       selection.capacity_native_id)
                        if selection.capacity_kind else None)
            options.append(DestinationOption(
                target.installation, binding.discovery.inventory if binding.discovery else None,
                capacity, findings, target.access))
        assessments = AssessmentEngine(RouteCatalogue(claims)).compare(
            origin.installation,
            source_input.discovery.inventory if source_input.discovery else None,
            workload, tuple(options), method=method, guest_profile=guest_profile,
            network_mode=network_mode, data_mode=data_mode, as_of=now,
            source_access=origin.access, max_snapshot_age=self._max_age)
        return AssessmentComparison(now, source_input, destination_inputs, assessments)
