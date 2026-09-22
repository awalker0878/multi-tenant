"""Deterministic placement over reviewed inventory.

Placement evaluates every reviewed site, cell and zone, records why each was
rejected, and selects the best eligible candidate under one stated rule:

    highest capability count, then largest available vCPU, then lowest cell key

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
candidate was evaluated at all the status is `HOLD_NO_ELIGIBLE_SITE`; otherwise the
status is the first matching class in `_HOLD_FOR_BLOCKER`, falling back to
`HOLD_NO_ELIGIBLE_PLATFORM`.
"""
from __future__ import annotations

from dataclasses import dataclass

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.placement import (AUTHORITATIVE, FIXTURE, HOLD_CAPACITY_INSUFFICIENT,
                                          HOLD_CAPABILITY_NOT_QUALIFIED, HOLD_NO_ELIGIBLE_PLATFORM,
                                          HOLD_NO_ELIGIBLE_SITE, HOLD_PLATFORM_NOT_QUALIFIED,
                                          HOLD_PREFIX_POOL_EXHAUSTED, HOLD_SERVICE_UNAVAILABLE,
                                          PLACED, CandidateEvaluation, PlacementDecision, finalize)
from provisioner.inventory.capacity import Assessment, Demand, assess
from provisioner.inventory.model import Cell, Cluster, Inventory, Site
from provisioner.placement import eligibility

SELECTION_RULE = 'highest-capability-count-then-largest-available-vcpu-then-lowest-cell-key'
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


@dataclass(frozen=True)
class _ZoneOption:
    site: Site
    cell: Cell
    cluster: Cluster
    score: int
    assessment: Assessment
    capability_count: int


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
    if missing_zones:
        codes: set[str] = set()
        for zone in missing_zones:
            rejected = [(e, c) for e, c in evaluated if e.zone == zone]
            if not rejected:
                pins = {'site': request.site_pin, 'cell': request.cell_pin}
                reasons.append(f'{zone}: no reviewed candidate in region {request.region} '
                               f'for platforms {sorted(platforms)}'
                               + (f' matching pins {pins}' if any(pins.values()) else ''))
                continue
            for evaluation, evaluation_codes in rejected:
                codes.update(evaluation_codes)
                reasons.append(f'{zone}: {evaluation.site_key}/{evaluation.cell_key} '
                               f'{evaluation.platform} rejected: ' + '; '.join(evaluation.blockers))
        status = _hold_status(frozenset(codes))
        if qualification_blockers:
            reasons.append('no candidate platform carries native qualification for the required '
                           'capability set: ' + '; '.join(sorted(qualification_blockers)))
        return finalize(PlacementDecision(
            status=status, authority=authority, request_digest=request.request_digest,
            selection_rule=SELECTION_RULE, candidates=tuple(evaluations),
            reasons=tuple(reasons), qualification=identity,
            qualification_blockers=tuple(sorted(qualification_blockers)),
            required_capabilities=request.required_capabilities))

    selected: dict = {'site_key': None, 'cell_key': None, 'platform': None,
                      'clusters': {}, 'cells': {}}
    for zone in request.zones:
        best = sorted(options[zone], key=lambda o: (-o.score, o.cell.cell, o.cluster.id))[0]
        selected['clusters'][zone] = best.cluster.id
        selected['cells'][zone] = best.cell.cell
        if selected['site_key'] is None:
            selected['site_key'] = best.site.site
            selected['cell_key'] = best.cell.cell
            selected['platform'] = best.site.platform
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