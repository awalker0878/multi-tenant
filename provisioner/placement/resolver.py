"""Deterministic placement over reviewed inventory.

Placement evaluates every reviewed site, cell and zone, records why each was
rejected, and selects the best eligible candidate under one stated rule:

    highest capability count, then largest available vCPU, then lowest cell key

The rule is deliberately boring. It is reproducible from inventory alone and it
never consults a scheduler, a reservation service or a native platform.
"""
from __future__ import annotations

from dataclasses import dataclass

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.placement import (AUTHORITATIVE, FIXTURE, CandidateEvaluation,
                                          PlacementDecision, finalize)
from provisioner.inventory.capacity import Assessment, Demand, assess
from provisioner.inventory.model import Cell, Cluster, Inventory, Site
from provisioner.placement import eligibility

SELECTION_RULE = 'highest-capability-count-then-largest-available-vcpu-then-lowest-cell-key'
SERVICE_NAMES = ('dns', 'ntp', 'identity', 'logging', 'backup')


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
               inventory: Inventory) -> CandidateEvaluation:
    _, platform_blockers = eligibility.gate(
        site.platform, set(request.required_capabilities))
    cell_blockers = eligibility.missing_cell_capabilities(
        cell.capabilities, set(request.required_capabilities))
    assessment = assess(cluster, request.demand)
    pool_ok, pool_reason = _pool_has_room(inventory, site.site, cluster.zone,
                                              request.prefix_length)
    missing_services = _services_present(inventory, site.site, request.services)

    blockers: list[str] = []
    if not cluster.supports(request.trust, request.service_class, request.tenant, request.wsd):
        blockers.append('cluster residency does not match trust, service class or tenant eligibility')
    if cell_blockers:
        blockers.append('cell lacks capabilities: ' + ', '.join(cell_blockers))
    if not assessment.sufficient:
        blockers.extend(assessment.blockers)
    if not pool_ok:
        blockers.append(pool_reason)
    if missing_services:
        blockers.append('site lacks service bindings: ' + ', '.join(missing_services))

    capability_blockers = tuple(platform_blockers) + tuple('cell:' + c for c in cell_blockers)
    score = len(cell.capabilities) * 1000 + min(cluster.capacity.vcpu_available, 999)
    return CandidateEvaluation(
        site_key=site.site, cell_key=cell.cell, platform=site.platform,
        platform_family=eligibility.PLATFORM_FAMILY[site.platform], zone=cluster.zone,
        eligible=not blockers, score=score, blockers=tuple(blockers),
        capability_blockers=capability_blockers,
        product_tuple=eligibility.product_tuple(site.platform))


def place(request: PlacementRequest, inventory: Inventory) -> PlacementDecision:
    """Evaluate every reviewed candidate and return a decision or an explicit hold."""
    platforms = eligibility.PLATFORMS if request.platform_preference == 'auto' \
        else (request.platform_preference,)

    registry_blockers: list[str] = []
    for platform in platforms:
        _, blockers = eligibility.gate(platform, set(request.required_capabilities))
        registry_blockers.extend(f'{platform}: {b}' for b in blockers)

    options: dict[str, list[_ZoneOption]] = {zone: [] for zone in request.zones}
    evaluations: list[CandidateEvaluation] = []
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
                    evaluation = _candidate(request, site, cell, cluster, inventory)
                    evaluations.append(evaluation)
                    if evaluation.eligible:
                        options[zone].append(_ZoneOption(
                            site=site, cell=cell, cluster=cluster, score=evaluation.score,
                            assessment=assess(cluster, request.demand),
                            capability_count=len(cell.capabilities)))

    evaluations.sort(key=lambda e: (e.site_key, e.cell_key, e.zone, e.platform))
    authority = AUTHORITATIVE if inventory.authoritative else FIXTURE
    reasons: list[str] = []
    if not inventory.authoritative:
        reasons.append('inventory is a non-authoritative fixture; this decision is a demonstration only')

    missing_zones = [zone for zone in request.zones if not options[zone]]
    if missing_zones:
        status = 'HOLD_NO_ELIGIBLE_PLATFORM'
        if registry_blockers and not inventory.authoritative:
            reasons.append('no platform is natively qualified; fixture inventory was used to demonstrate the path')
        for zone in missing_zones:
            rejected = [e for e in evaluations if e.zone == zone]
            if not rejected:
                pins = {'site': request.site_pin, 'cell': request.cell_pin}
                reasons.append(f'{zone}: no reviewed candidate in region {request.region} '
                               f'for platforms {sorted(platforms)}'
                               + (f' matching pins {pins}' if any(pins.values()) else ''))
            else:
                for evaluation in rejected:
                    reasons.append(f'{zone}: {evaluation.site_key}/{evaluation.cell_key} '
                                   f'{evaluation.platform} rejected: ' + '; '.join(evaluation.blockers))
        return finalize(PlacementDecision(
            status=status, authority=authority, request_digest=request.request_digest,
            selection_rule=SELECTION_RULE, candidates=tuple(evaluations),
            reasons=tuple(reasons), registry_blockers=tuple(sorted(registry_blockers)),
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
    if registry_blockers:
        reasons.append('capability registry records no native qualification for the required set: '
                       + '; '.join(sorted(registry_blockers)))
    return finalize(PlacementDecision(
        status='PLACED', authority=authority, request_digest=request.request_digest,
        selection_rule=SELECTION_RULE, selected=selected, candidates=tuple(evaluations),
        reasons=tuple(reasons), registry_blockers=tuple(sorted(registry_blockers)),
        required_capabilities=request.required_capabilities))


def require_placed(decision: PlacementDecision) -> PlacementDecision:
    if decision.held:
        raise ProvisioningError('NO_ELIGIBLE_PLACEMENT',
                                f'Placement held with status {decision.status}',
                                details={'reasons': list(decision.reasons),
                                         'candidates': [c.to_dict() for c in decision.candidates]})
    return decision