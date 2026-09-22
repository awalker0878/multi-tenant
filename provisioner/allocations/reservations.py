"""Capacity reservation proposals.

A reservation is never applied here. The provisioner states the delta a
reservation would require and leaves the act of reserving to a reviewed inventory
change owned by the site owner.
"""
from __future__ import annotations

from dataclasses import dataclass

from provisioner.domain.errors import ProvisioningError
from provisioner.inventory.capacity import Demand, assess
from provisioner.inventory.model import Cluster

RESERVATION_FORMAT = 'hosting-capacity-reservation/1'


@dataclass(frozen=True)
class Reservation:
    owner: str
    cluster: str
    site: str
    cell: str
    zone: str
    demand: Demand
    committed_after: dict
    status: str = 'PROPOSED_NOT_APPLIED'

    def to_dict(self) -> dict:
        return {'format': RESERVATION_FORMAT, 'owner': self.owner, 'cluster': self.cluster,
                'site': self.site, 'cell': self.cell, 'zone': self.zone,
                'demand': self.demand.to_dict(),
                'committed_after': dict(self.committed_after), 'status': self.status,
                'applied': False,
                'limits': ['A reservation proposal grants no capacity; the site owner applies it']}


def propose(cluster: Cluster, demand: Demand, site: str, cell: str, owner: str) -> Reservation:
    """Propose a reservation, refusing to propose one inventory cannot hold."""
    assessment = assess(cluster, demand)
    if not assessment.sufficient:
        raise ProvisioningError('CAPACITY_INSUFFICIENT',
                                f'{cluster.id} cannot hold the resolved demand',
                                path=f'inventory.{cluster.id}.capacity',
                                details={'blockers': list(assessment.blockers),
                                         'available': assessment.available,
                                         'demand': demand.to_dict()})
    return Reservation(owner=owner, cluster=cluster.id, site=site, cell=cell, zone=cluster.zone,
                       demand=demand,
                       committed_after={
                           'vcpu_committed': cluster.capacity.vcpu_committed + demand.vcpu,
                           'memory_gib_committed': cluster.capacity.memory_gib_committed + demand.memory_gib,
                           'storage_gib_committed': cluster.capacity.storage_gib_committed + demand.storage_gib})


def assert_disjoint(reservations: tuple[Reservation, ...]) -> None:
    """Refuse two proposals for the same owner, cluster and zone."""
    seen: set[tuple[str, str, str]] = set()
    for reservation in reservations:
        key = (reservation.owner, reservation.cluster, reservation.zone)
        if key in seen:
            raise ProvisioningError('CAPACITY_RESERVATION_CONFLICT',
                                    f'Two reservations target {reservation.cluster}/{reservation.zone} '
                                    f'for {reservation.owner}',
                                    details={'owner': reservation.owner,
                                             'cluster': reservation.cluster,
                                             'zone': reservation.zone})
        seen.add(key)