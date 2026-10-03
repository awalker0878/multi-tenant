"""Read-only assessment composition over authorized, generation-pinned inputs.

There is intentionally no default trust provider. Environment declarations,
browser fields, this service's output and the existence of a collector cannot
establish installed product provenance or native route qualification. Deployers
must supply an independently backed provider before enabling the endpoint.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence.store import TenantContext

from .assessment import (AssessmentEngine, AssessmentIssue, AssessmentScopeAccess,
                         DestinationAssessment, DestinationOption, ReviewedFinding)
from .model import NativeIdentity, _utc
from .normalization import (NormalizedDiscovery, NormalizationHeld,
                            hydrate_generation, normalize_discovery)
from .persistence import StoredGeneration, StoredObservation
from .routes import InstalledTuple, METHODS, RouteCatalogue, RouteClaim, RouteKey, native_scope_key


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
class AssessmentMember:
    """An exact VM and guest profile, not an inferred application member."""

    native_id: str
    guest_profile: str

    def __post_init__(self) -> None:
        if (not isinstance(self.native_id, str) or not 1 <= len(self.native_id) <= 512
                or not self.native_id.strip()
                or any(ord(char) < 32 or ord(char) == 127 for char in self.native_id)
                or not isinstance(self.guest_profile, str) or not _ID.fullmatch(self.guest_profile)):
            raise ValueError('An exact native VM and guest profile are required')


@dataclass(frozen=True, slots=True)
class VerifiedAssessmentEnvironment:
    """Provider result, checked against actor, tenant, purpose and trusted time."""

    environment_id: str
    installation: InstalledTuple
    access: AssessmentScopeAccess


class AssessmentRepository(Protocol):
    def latest_generation(self, ctx: TenantContext, scope: PlanScope,
                          environment_id: str) -> StoredGeneration | None: ...

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
    latest: StoredGeneration | None = None

    @property
    def superseded(self) -> bool:
        return self.latest is not None and self.latest.generation > self.selection.generation

    def to_document(self) -> dict:
        if self.latest is None:
            raise NormalizationHeld('Current generation metadata was not verified')
        scope = self.installation.scope
        return {'environmentId': self.selection.environment_id,
                'generation': self.selection.generation,
                'endpointId': scope.endpoint_id, 'nativeScopeId': scope.native_scope_id,
                'platformFamily': scope.platform_family,
                'productTupleId': self.installation.product_tuple_id,
                'productTupleDigest': self.installation.product_tuple_digest,
                'observation': self.discovery.binding() if self.discovery else None,
                'superseded': self.superseded,
                'latestObservation': {
                    'generation': self.latest.generation,
                    'rawSnapshotDigest': self.latest.result_digest,
                    'capturedAt': self.latest.captured_at.isoformat(),
                    'collectionCompleteness': self.latest.completeness,
                    'collectionErrors': list(self.latest.collection_errors),
                    'missingPrivileges': list(self.latest.missing_privileges)}}


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
                    for method in ('get_generation', 'list_observations', 'latest_generation'))
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

    def _with_latest(self, ctx: TenantContext, binding: AssessmentInputBinding,
                     now: datetime) -> AssessmentInputBinding:
        """Retain historical inputs while independently checking their currency.

        The latest header is metadata only. Its facts never replace or fill in
        the immutable selected generation, even after a partial collection.
        """
        scope, selection = binding.installation.scope, binding.selection
        latest = self._repository.latest_generation(ctx, scope, selection.environment_id)
        if (not isinstance(latest, StoredGeneration)
                or latest.environment_id != selection.environment_id or latest.scope != scope
                or type(latest.generation) is not int or latest.generation < 1
                or not isinstance(latest.result_digest, str)
                or re.fullmatch(r'[0-9a-f]{64}', latest.result_digest) is None
                or not isinstance(latest.authorization_digest, str)
                or re.fullmatch(r'[0-9a-f]{64}', latest.authorization_digest) is None
                or not isinstance(latest.campaign_id, str) or not _ID.fullmatch(latest.campaign_id)
                or not _utc(latest.captured_at) or latest.captured_at > now
                or latest.completeness not in ('COMPLETE', 'PARTIAL', 'UNKNOWN')
                or type(latest.object_count) is not int or not 0 <= latest.object_count <= 100000
                or not isinstance(latest.collection_errors, tuple)
                or not isinstance(latest.missing_privileges, tuple)
                or len(latest.collection_errors) > 64 or len(latest.missing_privileges) > 64
                or any(not isinstance(value, str) or not _ID.fullmatch(value)
                       for value in latest.collection_errors)
                or any(not isinstance(value, str)
                       or re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,127}', value) is None
                       for value in latest.missing_privileges)
                or latest.completeness == 'COMPLETE'
                and (latest.collection_errors or latest.missing_privileges)):
            raise NormalizationHeld('Current exact-scope generation metadata is unavailable')
        if binding.discovery is not None:
            raw = binding.discovery.original
            pinned = StoredGeneration(selection.environment_id, selection.generation,
                raw.campaign_id, raw.scope, raw.authorization_digest, raw.digest,
                raw.captured_at, raw.completeness, raw.collection_errors,
                raw.missing_privileges, len(raw.objects))
            if latest.generation < selection.generation or (
                    latest.generation == selection.generation and latest != pinned):
                raise NormalizationHeld('Current generation contradicts the selected observation')
        elif latest.generation == selection.generation:
            raise NormalizationHeld('Current generation is missing its selected observation')
        return replace(binding, latest=latest)

    @staticmethod
    def _supersession_issue(binding: AssessmentInputBinding, side: str) -> AssessmentIssue:
        return AssessmentIssue('UNKNOWN', side + '_SNAPSHOT_SUPERSEDED',
            f'The pinned {side.lower()} generation {binding.selection.generation} is historical; '
            f'latest generation {binding.latest.generation} is {binding.latest.completeness}. '
            'Current eligibility has not been established.',
            'Load and assess the latest generation, resolve incomplete collection or missing '
            'privileges, and renew reviews against its exact observation digests.')

    def compare(self, ctx: TenantContext, actor_subject: str,
                source: AssessmentSelection, workload_native_id: str,
                destinations: tuple[AssessmentDestination, ...], *,
                method: str, guest_profile: str, network_mode: str, data_mode: str
                ) -> AssessmentComparison:
        return self._compare(ctx, actor_subject, source, workload_native_id, destinations,
            method=method, guest_profile=guest_profile, network_mode=network_mode,
            data_mode=data_mode, snapshots={}, proofs=None)

    def compare_many(self, ctx: TenantContext, actor_subject: str,
                     source: AssessmentSelection, members: tuple[AssessmentMember, ...],
                     destinations: tuple[AssessmentDestination, ...], *,
                     method: str, network_mode: str, data_mode: str
                     ) -> tuple[AssessmentComparison, ...]:
        """Compare every exact member without repeatedly hydrating inventories.

        At most 200 member/destination cells are evaluated. Results are advice
        over immutable pins with live currency checks, not one native snapshot,
        a capacity reservation, or permission for any later effect.
        """
        if (not isinstance(members, tuple) or not 1 <= len(members) <= 100
                or any(not isinstance(member, AssessmentMember) for member in members)
                or len({member.native_id for member in members}) != len(members)
                or not isinstance(destinations, tuple) or not 2 <= len(destinations) <= 20
                or len(members) * len(destinations) > 200):
            raise ValueError('Unique members and at most 200 comparison cells are required')
        snapshots, proofs = {}, {}
        comparisons = tuple(self._compare(ctx, actor_subject, source, member.native_id,
            destinations, method=method, guest_profile=member.guest_profile,
            network_mode=network_mode, data_mode=data_mode, snapshots=snapshots, proofs=proofs)
            for member in members)
        # A generation published while another member is assessed cannot leave
        # an earlier member eligible. Recheck all current tuple/access selections
        # before the final metadata reads; immutable facts are never replaced.
        now = self._clock()
        if not _utc(now) or any(now < comparison.assessed_at for comparison in comparisons):
            raise NormalizationHeld('Application assessment clock regressed')
        first = comparisons[0]
        pins = (first.source, *first.destinations)
        for pin in pins:
            purpose = 'SOURCE_READ' if pin is first.source else 'DESTINATION_READ'
            if self._resolve(ctx, actor_subject, pin.selection, purpose, now).installation != pin.installation:
                raise PermissionError('Installed tuple changed during application assessment')
        for (kind, identity), proof in proofs.items():
            if kind == 'routes':
                if self._inputs.route_claims(ctx, actor_subject, identity, now) != proof:
                    raise PermissionError('Signed route evidence changed during application assessment')
                if any(first.assessed_at < item.expires_at <= now
                       for claim in proof for item in claim.evidence):
                    raise PermissionError('Route evidence expired during application assessment')
            else:
                route, observed_source, observed_target, findings = proof
                if self._inputs.reviewed_findings(ctx, actor_subject, route,
                        observed_source, observed_target, now) != findings:
                    raise PermissionError('Signed control evidence changed during application assessment')
                if any(first.assessed_at < item.expires_at <= now for item in findings):
                    raise PermissionError('Control evidence expired during application assessment')
        current = tuple(self._with_latest(ctx, pin, now) for pin in pins)
        result = []
        for comparison in comparisons:
            if (comparison.source.installation != first.source.installation
                    or tuple(pin.installation for pin in comparison.destinations) !=
                       tuple(pin.installation for pin in first.destinations)):
                raise PermissionError('Application assessment tuple changed between members')
            assessments = []
            for item, target in zip(comparison.assessments, current[1:]):
                extra = tuple(self._supersession_issue(pin, side)
                    for pin, side in ((current[0], 'SOURCE'), (target, 'DESTINATION'))
                    if pin.superseded)
                extra += tuple(AssessmentIssue('UNKNOWN', side + '_SNAPSHOT_STALE',
                    'The selected observation is no longer fresh at the final application check.',
                    'Collect current observations and renew the exact source and destination reviews.')
                    for pin, side in ((current[0], 'SOURCE'), (target, 'DESTINATION'))
                    if pin.discovery is not None and
                    not now - self._max_age <= pin.discovery.inventory.captured_at <= now)
                assessments.append(replace(item, status='UNKNOWN',
                    issues=tuple(dict.fromkeys((*item.issues, *extra)))) if extra else item)
            result.append(replace(comparison, source=current[0], destinations=current[1:],
                                  assessments=tuple(assessments)))
        return tuple(result)

    def _compare(self, ctx: TenantContext, actor_subject: str,
                source: AssessmentSelection, workload_native_id: str,
                destinations: tuple[AssessmentDestination, ...], *,
                method: str, guest_profile: str, network_mode: str, data_mode: str,
                snapshots: dict, proofs: dict | None
                ) -> AssessmentComparison:
        if (not isinstance(ctx, TenantContext)
                or not isinstance(actor_subject, str) or not 1 <= len(actor_subject) <= 256
                or any(ord(char) < 32 or ord(char) == 127 for char in actor_subject)
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
        if len({native_scope_key(scope) for scope in scopes}) != len(scopes):
            raise ValueError('Assessment environments must name distinct native scopes')
        workload = NativeIdentity(scopes[0].endpoint_id, scopes[0].native_scope_id,
                                  scopes[0].platform_family, 'vm', workload_native_id)
        def load(selection, verified):
            # Only immutable generation hydration is cached within this call.
            # Read permission, installed tuples, latest generations and signed
            # route/control evidence are always reverified, never cached here.
            key = (ctx, selection, verified.installation)
            if key not in snapshots:
                snapshots[key] = self._load(ctx, selection, verified)
            return snapshots[key]
        source_input = load(source, origin)
        destination_inputs = tuple(load(item.selection, target)
                                   for item, target in zip(destinations, targets))
        routes = tuple(RouteKey(origin.installation, target.installation, method,
                                guest_profile, network_mode, data_mode)
                       if method != 'SAME_PLATFORM_RELOCATION' or
                       origin.installation.scope.platform_family == target.installation.scope.platform_family
                       else None for target in targets)
        claims = self._inputs.route_claims(ctx, actor_subject, tuple(r for r in routes if r is not None), now)
        if (not isinstance(claims, tuple)
                or any(not isinstance(claim, RouteClaim) or claim.key not in routes
                       for claim in claims)):
            raise PermissionError('Route verifier returned unrelated claims')
        def retain_proof(key, value):
            if proofs is not None:
                if key in proofs and proofs[key] != value:
                    raise PermissionError('Signed evidence changed between application members')
                proofs[key] = value
        retain_proof(('routes', tuple(r for r in routes if r is not None)), claims)
        options = []
        for selection, target, binding, route in zip(
                destinations, targets, destination_inputs, routes):
            findings = self._inputs.reviewed_findings(
                ctx, actor_subject, route, source_input.discovery, binding.discovery, now) if route is not None else ()
            if (not isinstance(findings, tuple)
                    or any(not isinstance(item, ReviewedFinding) or item.route != route
                           for item in findings)):
                raise PermissionError('Review verifier returned unrelated control findings')
            if route is not None:
                retain_proof(('findings', route), (route, source_input.discovery, binding.discovery, findings))
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
        # The pure engine sorts native tuples for deterministic comparison. The
        # transport's generation bindings retain the operator's selection order;
        # restore that same order before presenting the two arrays together.
        by_destination = {item.destination: item for item in assessments}
        if (len(by_destination) != len(targets)
                or set(by_destination) != {item.installation for item in targets}):
            raise RuntimeError('Assessment destinations differ from the pinned selections')
        ordered = tuple(by_destination[item.installation] for item in targets)
        # Check currency after assembling the historical comparison. All exact
        # scopes were authorized before either historical or latest reads.
        source_input = self._with_latest(ctx, source_input, now)
        destination_inputs = tuple(self._with_latest(ctx, binding, now)
                                   for binding in destination_inputs)
        current_assessments = []
        for assessment, binding in zip(ordered, destination_inputs):
            superseded = tuple(self._supersession_issue(item, side)
                               for item, side in ((source_input, 'SOURCE'), (binding, 'DESTINATION'))
                               if item.superseded)
            current_assessments.append(replace(assessment, status='UNKNOWN',
                issues=assessment.issues + superseded) if superseded else assessment)
        return AssessmentComparison(now, source_input, destination_inputs, tuple(current_assessments))
