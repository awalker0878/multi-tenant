"""Capacity arithmetic over reviewed inventory.

Capacity here is an arithmetic gate, not a reservation. A reservation is a
separate reviewed act; this module only refuses to place a workload security
domain that inventory cannot already hold.
"""
from __future__ import annotations

from dataclasses import dataclass

from provisioner.inventory.model import Cluster

CAPACITY_FORMAT = 'hosting-capacity-assessment/1'


@dataclass(frozen=True)
class Demand:
    vcpu: int
    memory_gib: int
    storage_gib: int

    def to_dict(self) -> dict:
        return {'vcpu': self.vcpu, 'memory_gib': self.memory_gib, 'storage_gib': self.storage_gib}


@dataclass(frozen=True)
class Assessment:
    cluster: str
    sufficient: bool
    demand: Demand
    available: dict
    blockers: tuple[str, ...]

    def to_dict(self) -> dict:
        return {'format': CAPACITY_FORMAT, 'cluster': self.cluster, 'sufficient': self.sufficient,
                'demand': self.demand.to_dict(), 'available': dict(self.available),
                'blockers': list(self.blockers)}


def demand_for(workloads: int, compute: dict, storage: dict) -> Demand:
    """Compute the zone-level demand a resolved profile set implies."""
    if workloads < 1:
        raise ValueError('A workload security domain requires at least one workload per zone')
    return Demand(vcpu=compute['vcpu'] * workloads,
                  memory_gib=compute['memory_gib'] * workloads,
                  storage_gib=(compute['boot_disk_gib'] + storage['data_disk_gib']) * workloads)


def assess(cluster: Cluster, demand: Demand) -> Assessment:
    available = {'vcpu': cluster.capacity.vcpu_available,
                 'memory_gib': cluster.capacity.memory_gib_available,
                 'storage_gib': cluster.capacity.storage_gib_available}
    blockers: list[str] = []
    for field, required in (('vcpu', demand.vcpu), ('memory_gib', demand.memory_gib),
                            ('storage_gib', demand.storage_gib)):
        if available[field] < required:
            blockers.append(f'{field}: required {required}, available {available[field]}')
    return Assessment(cluster=cluster.id, sufficient=not blockers, demand=demand,
                      available=available, blockers=tuple(blockers))


def reserve(cluster: Cluster, demand: Demand) -> dict:
    """Return the committed-capacity delta a reservation would apply.

    This is a proposal only. Applying it requires a separate reviewed inventory
    change; the provisioner never mutates inventory.
    """
    return {'cluster': cluster.id,
            'vcpu_committed': cluster.capacity.vcpu_committed + demand.vcpu,
            'memory_gib_committed': cluster.capacity.memory_gib_committed + demand.memory_gib,
            'storage_gib_committed': cluster.capacity.storage_gib_committed + demand.storage_gib,
            'applied': False}