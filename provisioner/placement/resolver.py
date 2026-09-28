"""Deterministic placement over reviewed inventory.

Placement evaluates every reviewed site, cell and zone, records why each was
rejected, and selects the best **coherent envelope**: one site and one platform
that realize *every* required zone, with an explicit per-zone cell/cluster choice.
Zones are never ranked independently across unrelated sites, because the existing
`hosting-wsd-environment/1` contract is single-site and single-platform; a
per-zone winner set spanning two sites could not be compiled, and would only fail
later as `INVENTORY_INCOMPLETE` after placement had already reported `PLACED`.

Envelopes are ranked under one stated rule:

    highest capability count, then largest available vCPU, then lowest site key,
    then lowest cell key, then lowest cluster id

The rule is deliberately boring. It is reproducible from inventory alone and it
never consults a scheduler, a reservation service or a native platform.

Native qualification is a mandatory eligibility filter, not a note: a candidate
whose platform does not carry reviewed native qualification for the required
capability set is ineligible, so an authoritative inventory can never be placed
against an unqualified platform. Qualification is evaluated through an explicit
source (`eligibility.RepositoryQualification` by default, and only for a
non-authoritative inventory the repository's declared demonstration assumption)
so tests can inject a controlled source without touching the reviewed registry.

A hold is never a bare failure: the decision records every rejected candidate with
its exact blockers, and reports the most specific hold status that applies. When no
candidate was evaluated at all the status is `HOLD_NO_ELIGIBLE_SITE`; when every
required zone has an eligible candidate but no single site and platform realizes
them together the status is `HOLD_NO_COHERENT_ENVELOPE`; otherwise the status is
the first matching class in `_HOLD_FOR_BLOCKER`, falling back to
`HOLD_NO_ELIGIBLE_PLATFORM`.
"""
from __future__ import annotations

from dataclasses import dataclass

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.capability_properties import PropertyRequirement, evaluate
from provisioner.domain.placement import (AUTHORITATIVE, FIXTURE, HOLD_CAPACITY_INSUFFICIENT,
                                          HOLD_CAPABILITY_NOT_QUALIFIED, HOLD_NO_COHERENT_ENVELOPE,
                                          HOLD_NO_ELIGIBLE_PLATFORM, HOLD_NO_ELIGIBLE_SITE,
                                          HOLD_PLATFORM_NOT_QUALIFIED, HOLD_PREFIX_POOL_EXHAUSTED,
                                          HOLD_SERVICE_UNAVAILABLE, PLACED, CandidateEvaluation,
                                          PlacementDecision, finalize)
from provisioner.inventory.capacity import Assessment, Demand, assess
from provisioner.inventory.model import Cell, Cluster, Inventory, Site
from provisioner.placement import eligibility

SELECTION_RULE = ('highest-envelope-capability-count-then-largest-available-vcpu-then-lowest-site-'
                  'cell-and-cluster-key')
SERVICE_NAMES = ('dns', 'ntp', 'identity', 'logging', 'backup')

# Internal blocker classes. Each rejected candidate records why it failed, and the
# decision reports the most specific class that applies so a hold is actionable.
BLOCKER_RESIDENCY = 'residency'
BLOCKER_CAPABILITY = 'capability'
BLOCKER_CAPACITY = 'capacity'
BLOCKER_PREFIX_POOL = 'prefix-pool'
BLOCKER_SERVICE = 'service'
BLOCKER_QUALIFICATION = 'qualification'

# Most specific class first. A capacity, service, prefix-pool or cell capability
# failure is actionable on its own, so it outranks a platform-wide qualification
# gap; residency is a per-candidate fact and outranks qualification too.
_HOLD_FOR_BLOCKER = ((BLOCKER_CAPACITY, HOLD_CAPACITY_INSUFFICIENT),
                     (BLOCKER_SERVICE, HOLD_SERVICE_UNAVAILABLE),
                     (BLOCKER_PREFIX_POOL, HOLD_PREFIX_POOL_EXHAUSTED),
                     (BLOCKER_CAPABILITY, HOLD_CAPABILITY_NOT_QUALIFIED),
                     (BLOCKER_RESIDENCY, HOLD_NO_ELIGIBLE_PLATFORM),
                     (BLOCKER_QUALIFICATION, HOLD_PLATFORM_NOT_QUALIFIED))


def _hold_status(codes: frozenset[str]) -> str:
    """Map the blocker classes of every rejected candidate to one hold status."""
    if not codes:
        return HOLD_NO_ELIGIBLE_SITE
    for code, status in _HOLD_FOR_BLOCKER:
        if code in codes:
            return status
    return HOLD_NO_ELIGIBLE_PLATFORM


@dataclass(frozen=True)
class PlacementRequest:
    tenant: str
    wsd: str
    region: str
    platform_preference: str
    zones: tuple[str, ...]
    trust: str
    service_class: str
    required_capabilities: tuple[str, ...]
    demand: Demand
    services: dict
    request_digest: str
    prefix_length: int = 27
    site_pin: str | None = None
    cell_pin: str | None = None
    capability_constraints: tuple[PropertyRequirement, ...] = ()


@dataclass(frozen=True)
class _ZoneOption:
    site: Site
    cell: Cell
    cluster: Cluster
    score: int
    assessment: Assessment
    capability_count: int


def _option_key(option: _ZoneOption) -> tuple:
    return (-option.score, option.cell.cell, option.cluster.id)


@dataclass(frozen=True)
class _Envelope:
    """One coherent site/platform boundary with an explicit zone-to-cell choice.

    Every required zone is realized inside the same site and the same platform, so
    the envelope is compatible with the single-site `hosting-wsd-environment/1`
    contract. Zones may still sit in different cells of that site; the choice is
    recorded per zone rather than assumed.
    """

    site: Site
    options: dict[str, _ZoneOption]

    @property
    def site_key(self) -> str:
        return self.site.site

    @property
    def platform(self) -> str:
        return self.site.platform

    @property
    def capability_count(self) -> int:
        return sum(len(o.cell.capabilities) for o in self.options.values())

    @property
    def available_vcpu(self) -> int:
        return sum(o.cluster.capacity.vcpu_available for o in self.options.values())

    def rank(self, zones: tuple[str, ...]) -> tuple:
        """Deterministic envelope order: capability, then vCPU, then stable keys."""
        return (-self.capability_count, -self.available_vcpu, self.site_key,
                tuple(self.options[zone].cell.cell for zone in zones),
                tuple(self.options[zone].cluster.id for zone in zones))

    def to_dict(self, zones: tuple[str, ...]) -> dict:
        return {
            'site_key': self.site_key, 'platform': self.platform,
            'platform_family': eligibility.PLATFORM_FAMILY[self.platform],
            'capability_count': self.capability_count,
            'available_vcpu': self.available_vcpu,
            'zones': {zone: {'cell_key': self.options[zone].cell.cell,
                             'cluster_id': self.options[zone].cluster.id,
                             'cluster_key': self.cluster_key(zone),
                             'score': self.options[zone].score} for zone in zones}}

    def cluster_key(self, zone: str) -> str:
        """Unambiguous cluster identity within the selected inventory scope."""
        return f'{self.site_key}/{self.options[zone].cell.cell}/{self.options[zone].cluster.id}'


def _envelopes(request: PlacementRequest,
               options: dict[str, list[_ZoneOption]]) -> list[_Envelope]:
    """Every complete envelope, best first.

    A site/platform boundary qualifies only when it realizes *every* required
    zone; a boundary that covers a subset is not a candidate at all, so zones can
    never be combined across unrelated sites or platforms.
    """
    grouped: dict[tuple[str, str], dict[str, list[_ZoneOption]]] = {}
    for zone in request.zones:
        for option in options[zone]:
            grouped.setdefault((option.site.site, option.site.platform), {}).setdefault(
                zone, []).append(option)
    envelopes = []
    for by_zone in grouped.values():
        if set(by_zone) != set(request.zones):
            continue
        envelopes.append(_Envelope(
            site=next(iter(by_zone.values()))[0].site,
            options={zone: sorted(by_zone[zone], key=_option_key)[0] for zone in request.zones}))
    return sorted(envelopes, key=lambda envelope: envelope.rank(request.zones))


def _boundaries(request: PlacementRequest,
                options: dict[str, list[_ZoneOption]]) -> list[str]:
    """Where each required zone could have been realized, for an incoherent hold."""
    return [f'{zone} is eligible only in '
            f'{sorted({(o.site.site, o.site.platform) for o in options[zone]})}'
            for zone in request.zones]


def _pool_has_room(inventory: Inventory, site: str, zone: str, prefix_length: int) -> tuple[bool, str]:
    pools = inventory.pools(site, zone)
    if not pools:
        return False, f'no reviewed prefix pool for {site}/{zone}'
    for pool in pools:
        if pool.prefix_length != prefix_length:
            continue
        capacity = 2 ** (pool.prefix_length - int(pool.cidr.split('/')[1]))
        if len(pool.allocations) < capacity:
            return True, ''
    return False, f'no pool for {site}/{zone} can issue a /{prefix_length}'


def _services_present(inventory: Inventory, site: str, services: dict) -> tuple[str, ...]:
    missing = []
    for name in sorted(services):
        if name not in SERVICE_NAMES:
            continue
        if inventory.service(name, site) is None:
            missing.append(name)
    return tuple(missing)


def _candidate(request: PlacementRequest, site: Site, cell: Cell, cluster: Cluster,
               inventory: Inventory, qualification) -> tuple[CandidateEvaluation, frozenset[str]]:
    qualified, qualification_blockers = qualification.gate(
        site.platform, set(request.required_capabilities))
    cell_blockers = eligibility.missing_cell_capabilities(
        cell.capabilities, set(request.required_capabilities))
    assessment = assess(cluster, request.demand)
    pool_ok, pool_reason = _pool_has_room(inventory, site.site, cluster.zone,
                                              request.prefix_length)
    missing_services = _services_present(inventory, site.site, request.services)

    codes: set[str] = set()
    blockers: list[str] = []
    if not cluster.supports(request.trust, request.service_class, request.tenant, request.wsd):
        blockers.append('cluster residency does not match trust, service class or tenant eligibility')
        codes.add(BLOCKER_RESIDENCY)
    property_blockers = evaluate(request.capability_constraints, cluster.capability_properties)
    if property_blockers:
        blockers.extend(property_blockers)
        codes.add(BLOCKER_CAPABILITY)
    if cell_blockers:
        blockers.append('cell lacks capabilities: ' + ', '.join(cell_blockers))
        codes.add(BLOCKER_CAPABILITY)
    if not qualified:
        blockers.append(f'platform {site.platform} is not natively qualified for the required '
                        'capability set: ' + ', '.join(qualification_blockers))
        codes.add(BLOCKER_QUALIFICATION)
    if not assessment.sufficient:
        blockers.extend(assessment.blockers)
        codes.add(BLOCKER_CAPACITY)
    if not pool_ok:
        blockers.append(pool_reason)
        codes.add(BLOCKER_PREFIX_POOL)
    if missing_services:
        blockers.append('site lacks service bindings: ' + ', '.join(missing_services))
        codes.add(BLOCKER_SERVICE)

    score = len(cell.capabilities) * 1000 + min(cluster.capacity.vcpu_available, 999)
    return CandidateEvaluation(
        site_key=site.site, cell_key=cell.cell, platform=site.platform,
        platform_family=eligibility.PLATFORM_FAMILY[site.platform], zone=cluster.zone,
        eligible=not blockers, score=score, blockers=tuple(blockers),
        blocker_classes=tuple(sorted(codes)),
        qualification_blockers=tuple(qualification_blockers),
        cell_blockers=cell_blockers,
        product_tuple=qualification.product_tuple(site.platform)), frozenset(codes)


def place(request: PlacementRequest, inventory: Inventory,
          qualification=None) -> PlacementDecision:
    """Evaluate every reviewed candidate and return a decision or an explicit hold.

    `qualification` defaults to the reviewed capability registry for an
    authoritative inventory, and to the repository's declared demonstration
    assumption for a non-authoritative fixture. An explicit source is only for
    controlled tests: a non-authoritative source can never authorize a decision.
    """
    source = qualification if qualification is not None else eligibility.qualification_for(inventory)
    if inventory.authoritative and not source.authoritative:
        raise ValueError('An authoritative inventory cannot be placed against a '
                         'non-authoritative qualification source')
    platforms = eligibility.PLATFORMS if request.platform_preference == 'auto' \
        else (request.platform_preference,)

    qualification_blockers: list[str] = []
    for platform in platforms:
        _, blockers = source.gate(platform, set(request.required_capabilities))
        qualification_blockers.extend(f'{platform}: {b}' for b in blockers)

    options: dict[str, list[_ZoneOption]] = {zone: [] for zone in request.zones}
    evaluated: list[tuple[CandidateEvaluation, frozenset[str]]] = []
    for site in inventory.sites:
        if site.region != request.region or site.platform not in platforms:
            continue
        if request.site_pin is not None and site.site != request.site_pin:
            continue
        for cell in site.cells:
            if request.cell_pin is not None and cell.cell != request.cell_pin:
                continue
            for zone in request.zones:
                for cluster in cell.zone_clusters(zone):
                    if cluster.role != 'workload':
                        continue
                    evaluation, codes = _candidate(request, site, cell, cluster, inventory, source)
                    evaluated.append((evaluation, codes))
                    if evaluation.eligible:
                        options[zone].append(_ZoneOption(
                            site=site, cell=cell, cluster=cluster, score=evaluation.score,
                            assessment=assess(cluster, request.demand),
                            capability_count=len(cell.capabilities)))

    evaluations = [evaluation for evaluation, _ in evaluated]
    evaluations.sort(key=lambda e: (e.site_key, e.cell_key, e.zone, e.platform))
    authority = AUTHORITATIVE if inventory.authoritative else FIXTURE
    identity = source.to_dict(platforms)
    reasons: list[str] = []
    if not inventory.authoritative:
        reasons.append('inventory is a non-authoritative fixture; this decision is a demonstration only')
    if not identity['authoritative']:
        reasons.append(f'qualification is {identity["status"]} from {identity["source"]}; '
                       'this decision cannot authorize anything')

    missing_zones = [zone for zone in request.zones if not options[zone]]
    envelopes = _envelopes(request, options)
    if not envelopes:
        codes: set[str] = set()
        for zone in request.zones:
            zone_evaluated = [(e, c) for e, c in evaluated if e.zone == zone]
            if not zone_evaluated:
                pins = {'site': request.site_pin, 'cell': request.cell_pin}
                reasons.append(f'{zone}: no reviewed candidate in region {request.region} '
                               f'for platforms {sorted(platforms)}'
                               + (f' matching pins {pins}' if any(pins.values()) else ''))
                continue
            if options[zone]:
                continue
            for evaluation, evaluation_codes in zone_evaluated:
                codes.update(evaluation_codes)
                reasons.append(f'{zone}: {evaluation.site_key}/{evaluation.cell_key} '
                               f'{evaluation.platform} rejected: ' + '; '.join(evaluation.blockers))
        status = _hold_status(frozenset(codes))
        if not codes and not missing_zones:
            # Every zone has an eligible candidate, but no single site and platform
            # realizes them together. Holding here is what keeps desired-state
            # assembly from ever having to repair an incoherent selection.
            status = HOLD_NO_COHERENT_ENVELOPE
            reasons.append('no single site and platform realizes every required zone: '
                           + '; '.join(_boundaries(request, options)))
        if qualification_blockers:
            reasons.append('no candidate platform carries native qualification for the required '
                           'capability set: ' + '; '.join(sorted(qualification_blockers)))
        return finalize(PlacementDecision(
            status=status, authority=authority, request_digest=request.request_digest,
            selection_rule=SELECTION_RULE, candidates=tuple(evaluations),
            reasons=tuple(reasons), qualification=identity,
            qualification_blockers=tuple(sorted(qualification_blockers)),
            required_capabilities=request.required_capabilities))

    envelope = envelopes[0]
    selected: dict = {
        'site_key': envelope.site_key,
        'cell_key': envelope.options[request.zones[0]].cell.cell,
        'platform': envelope.platform,
        'clusters': {zone: envelope.options[zone].cluster.id for zone in request.zones},
        'cells': {zone: envelope.options[zone].cell.cell for zone in request.zones},
        'envelope': envelope.to_dict(request.zones)}
    reasons.append('the selected envelope realizes every required zone inside one site and '
                   f'one platform: {envelope.site_key}/{envelope.platform}')
    return finalize(PlacementDecision(
        status=PLACED, authority=authority, request_digest=request.request_digest,
        selection_rule=SELECTION_RULE, selected=selected, candidates=tuple(evaluations),
        reasons=tuple(reasons), qualification=identity,
        qualification_blockers=tuple(sorted(qualification_blockers)),
        required_capabilities=request.required_capabilities))


def require_placed(decision: PlacementDecision) -> PlacementDecision:
    if decision.held:
        raise ProvisioningError('NO_ELIGIBLE_PLACEMENT',
                                f'Placement held with status {decision.status}',
                                details={'reasons': list(decision.reasons),
                                         'candidates': [c.to_dict() for c in decision.candidates]})
    return decision