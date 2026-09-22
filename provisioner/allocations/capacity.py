"""Allocation orchestration.

Ties the allocation inputs together into one reproducible allocation record: a
capacity reservation proposal per zone, one address prefix per zone, and the
deterministic workload addresses inside it. Nothing here is applied; every record
carries `applied: False` and names the reviewed change that would apply it.
"""
from __future__ import annotations

from dataclasses import dataclass

from provisioner.allocations import ipam, reservations
from provisioner.domain.errors import ProvisioningError
from provisioner.inventory.capacity import Demand
from provisioner.inventory.model import Cluster, Inventory

ALLOCATION_FORMAT = 'hosting-allocation/1'


@dataclass(frozen=True)
class ZoneAllocation:
    zone: str
    site: str
    cell: str
    cluster: str
    prefix: ipam.PrefixAllocation
    reservation: reservations.Reservation

    def to_dict(self) -> dict:
        return {'zone': self.zone, 'site': self.site, 'cell': self.cell,
                'cluster': self.cluster, 'prefix': self.prefix.to_dict(),
                'reservation': self.reservation.to_dict()}


@dataclass(frozen=True)
class Allocation:
    tenant: str
    wsd: str
    domains: dict
    site: str
    zones: tuple[ZoneAllocation, ...]
    demand: Demand
    format: str = ALLOCATION_FORMAT

    @property
    def addresses(self) -> dict[str, str]:
        """One deterministic workload address per zone, keyed by zone."""
        return {z.zone: z.prefix.addresses[0] for z in self.zones if z.prefix.addresses}

    def to_dict(self) -> dict:
        return {'format': self.format, 'tenant': self.tenant, 'wsd': self.wsd,
                'domains': dict(self.domains), 'site': self.site,
                'zones': [z.to_dict() for z in self.zones], 'demand': self.demand.to_dict(),
                'addresses': self.addresses(),
                'applied': False,
                'limits': ['Allocation is a proposal; reviewed inventory changes apply it']}


def allocate(inventory: Inventory, tenant: str, wsd: str, domains: dict[str, str], site: str,
             selections: dict[str, tuple[str, Cluster]], zones: tuple[str, ...], demand: Demand,
             prefix_length: int, workloads_per_zone: int) -> Allocation:
    """Allocate capacity and addressing for every zone of one domain.

    `domains` maps a zone to its native domain identity and `selections` maps a
    zone to the placed `(cell, cluster)` pair.
    """
    zone_allocations: list[ZoneAllocation] = []
    for zone in zones:
        selection = selections.get(zone)
        if selection is None:
            raise ProvisioningError('NO_ELIGIBLE_PLACEMENT',
                                    f'No selected cluster for zone {zone}',
                                    details={'zones': list(zones)})
        cell, cluster = selection
        pools = inventory.pools(site, zone)
        prefix = ipam.allocate_prefix(pools, prefix_length, tenant, wsd, domains[zone])
        prefix = ipam.allocate_addresses(prefix, workloads_per_zone)
        reservation = reservations.propose(cluster, demand, site, cell,
                                           owner=f'{tenant}/{wsd}/{domains[zone]}')
        zone_allocations.append(ZoneAllocation(zone=zone, site=site, cell=cell,
                                               cluster=cluster.id, prefix=prefix,
                                               reservation=reservation))
    reservations.assert_disjoint(tuple(z.reservation for z in zone_allocations))
    ipam.assert_disjoint(tuple(z.prefix for z in zone_allocations))
    return Allocation(tenant=tenant, wsd=wsd, domains=domains, site=site,
                      zones=tuple(zone_allocations), demand=demand)