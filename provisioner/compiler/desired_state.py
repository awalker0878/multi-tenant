"""Desired-state assembly.

This stage joins the four independent decisions — profiles, policy, placement and
allocation — into one resolved desired state. It is the last stage that may still
refuse the request: after this point the pipeline only renders what was decided.
"""
from __future__ import annotations

from provisioner.allocations import capacity as allocation
from provisioner.compiler.environment import domain_id, realization_gaps, workload_name
from provisioner.domain.desired_state import (DomainIntent, DesiredState, WorkloadIntent,
                                               finalize)
from provisioner.domain.errors import Diagnostics, ProvisioningError
from provisioner.domain.placement import PlacementDecision
from provisioner.domain.request import Request
from provisioner.inventory.capacity import Demand, demand_for
from provisioner.inventory.model import Cluster, Inventory
from provisioner.placement import eligibility
from provisioner.services import bindings as service_bindings


def _cluster(inventory: Inventory, site_key: str, cell_key: str,
             cluster_id: str) -> tuple[str, Cluster]:
    """Resolve a placed cluster inside the cell placement actually selected.

    The cell is part of the placement decision, so cluster identity is unambiguous
    even when the same cluster id exists in another site or cell: a mismatch is a
    recorded refusal, never a silent repair.
    """
    site = inventory.site(site_key)
    for cell in site.cells:
        if cell.cell != cell_key:
            continue
        for cluster in cell.clusters:
            if cluster.id == cluster_id:
                return cell.cell, cluster
    raise ProvisioningError('INVENTORY_INCOMPLETE',
                            f'Placed cluster {cluster_id} is absent from reviewed inventory',
                            path='inventory.sites',
                            details={'site': site_key, 'cell': cell_key,
                                     'cluster': cluster_id})


def domain_ids(tenant: str, wsd: str, zones: tuple[str, ...]) -> dict[str, str]:
    """Stable native domain identities, one per zone, derived from the portable names."""
    return {zone: domain_id(wsd, zone) for zone in zones}


def build(request: Request, resolution, decision: PlacementDecision, inventory: Inventory,
          catalog=None, diagnostics: Diagnostics | None = None) -> DesiredState:
    """Assemble the resolved desired state from placement and allocation."""
    diagnostics = diagnostics or Diagnostics()
    if decision.held:
        raise ProvisioningError('NO_ELIGIBLE_PLACEMENT',
                                f'Cannot assemble desired state from a held decision: {decision.status}',
                                details={'reasons': list(decision.reasons)})
    if not decision.selected:
        raise ProvisioningError('NO_ELIGIBLE_PLACEMENT', 'Placement selected no site or cell')
    if not inventory.authoritative:
        diagnostics.add_warning(ProvisioningError(
            'INVENTORY_NOT_AUTHORITATIVE',
            f'Desired state derived from non-authoritative inventory {inventory.origin}',
            path='inventory.status',
            details={'status': inventory.status, 'origin': inventory.origin}))

    site_key = decision.selected['site_key']
    platform = decision.selected['platform']
    zone_clusters = {zone: decision.selected['clusters'][zone] for zone in resolution.zones}
    zone_cells = {zone: decision.selected['cells'][zone] for zone in resolution.zones}
    selections = {zone: _cluster(inventory, site_key, zone_cells[zone], cluster_id)
                  for zone, cluster_id in zone_clusters.items()}

    compute = resolution.compute
    demand = demand_for(compute['workloads_per_zone'], compute, resolution.storage)
    ids = domain_ids(request.tenant, request.wsd, resolution.zones)
    allocation_record = allocation.allocate(
        inventory=inventory, tenant=request.tenant, wsd=request.wsd, domains=ids,
        site=site_key, selections=selections, zones=resolution.zones, demand=demand,
        prefix_length=resolution.network['prefix_length'],
        workloads_per_zone=compute['workloads_per_zone'])

    site = inventory.site(site_key)
    bindings = (service_bindings.resolve(resolution, catalog, inventory, site_key)
                if catalog is not None else ())
    domain_inputs = site.domain_inputs()
    workload_inputs = site.workload_inputs(compute['flavor_class'],
                                          resolution.storage['storage_class'])

    domains: list[DomainIntent] = []
    for zone_allocation in allocation_record.zones:
        cell_key, cluster = selections[zone_allocation.zone]
        workloads = tuple(
            WorkloadIntent(name=workload_name(request.tenant, request.wsd,
                                              zone_allocation.zone, index),
                           address=address, vcpu=compute['vcpu'],
                           memory_gib=compute['memory_gib'],
                           boot_disk_gib=compute['boot_disk_gib'],
                           data_disk_gib=resolution.storage['data_disk_gib'],
                           inputs=dict(workload_inputs))
            for index, address in enumerate(zone_allocation.prefix.addresses))
        domains.append(DomainIntent(
            domain_id=ids[zone_allocation.zone], zone=zone_allocation.zone,
            cell_key=cell_key, cluster_id=cluster.id,
            prefix=zone_allocation.prefix.cidr,
            gateway_host_number=zone_allocation.prefix.gateway_host_number,
            inputs=dict(domain_inputs), workloads=workloads))

    state = DesiredState(
        request_digest=request.digest, api_version=request.api_version, kind=request.kind,
        tenant=request.tenant, wsd=request.wsd, owner=request.owner,
        lifecycle=resolution.lifecycle, site_key=site_key, platform=platform,
        platform_family=eligibility.PLATFORM_FAMILY[platform],
        trust=resolution.trust, service_class=resolution.service_class,
        profiles=dict(resolution.profiles),
        profile_versions=dict(resolution.profile_versions),
        catalog_versions=dict(resolution.catalog_versions),
        catalog_digest=resolution.catalog_digest,
        policy={}, placement=decision.to_dict(),
        capabilities=resolution.required_capabilities, services=dict(resolution.services),
                service_bindings=tuple(b.to_dict() for b in bindings),
                reservations={z.zone: z.reservation.to_dict() for z in allocation_record.zones},
        clusters=tuple(cluster.to_environment() for cluster in
                               sorted({c.id: c for _, c in selections.values()}.values(),
                                      key=lambda c: c.id)),
        domains=tuple(domains))
    for gap in realization_gaps(state):
        diagnostics.add_warning(ProvisioningError('REALIZATION_INPUT_UNAVAILABLE', gap,
                                                  path='$.spec.platform'))
    return finalize(state)