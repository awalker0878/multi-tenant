"""Prefix and address allocation.

Allocation is deterministic and reproducible from reviewed inventory alone. The
lowest usable prefix and the lowest usable host addresses are chosen so that two
runs over the same inventory produce the same answer, and so that a human can
verify the answer by hand.
"""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from provisioner.domain.errors import ProvisioningError
from provisioner.inventory.model import PrefixPool

IPAM_FORMAT = 'hosting-ipam-allocation/1'
MAX_PREFIX_LENGTH = 29


@dataclass(frozen=True)
class PrefixAllocation:
    pool: str
    zone: str
    cidr: str
    prefix_length: int
    gateway_host_number: int
    addresses: tuple[str, ...]
    reused: bool = False

    def to_dict(self) -> dict:
        return {'format': IPAM_FORMAT, 'pool': self.pool, 'zone': self.zone, 'cidr': self.cidr,
                'prefix_length': self.prefix_length,
                'gateway_host_number': self.gateway_host_number,
                'gateway': str(ipaddress.IPv4Network(self.cidr)[self.gateway_host_number]),
                'addresses': list(self.addresses), 'reused': self.reused,
                'applied': False}


def _network(cidr: str) -> ipaddress.IPv4Network:
    try:
        return ipaddress.IPv4Network(cidr, strict=True)
    except ValueError as exc:
        raise ProvisioningError('ADDRESS_CONFLICT', f'Invalid reviewed prefix {cidr!r}: {exc}',
                                path='inventory.prefix_pools') from exc


def _require_pool_prefix_length(pool: PrefixPool, prefix_length: int) -> None:
    if prefix_length > MAX_PREFIX_LENGTH:
        raise ProvisioningError('UNSUPPORTED_FEATURE',
                                f'A /{prefix_length} cannot hold the internal composition',
                                path=f'inventory.prefix_pools.{pool.pool}',
                                details={'max_prefix_length': MAX_PREFIX_LENGTH})
    if prefix_length < _network(pool.cidr).prefixlen:
        raise ProvisioningError('PREFIX_POOL_EXHAUSTED',
                                f'A /{prefix_length} does not fit inside {pool.cidr}',
                                path=f'inventory.prefix_pools.{pool.pool}')


def allocate_prefix(pools: tuple[PrefixPool, ...], prefix_length: int,
                    tenant: str, wsd: str, domain: str) -> PrefixAllocation:
    """Return the lowest free prefix in the reviewed pools for one domain."""
    if not pools:
        raise ProvisioningError('PREFIX_POOL_EXHAUSTED',
                                'No reviewed prefix pool is available for the selected site and zone')
    errors: list[str] = []
    for pool in sorted(pools, key=lambda p: p.pool):
        _require_pool_prefix_length(pool, prefix_length)
        for existing in pool.allocations:
            if existing.tenant == tenant and existing.wsd == wsd and existing.domain == domain:
                network = _network(existing.cidr)
                return PrefixAllocation(
                    pool=pool.pool, zone=pool.zone, cidr=existing.cidr,
                    prefix_length=network.prefixlen,
                    gateway_host_number=pool.gateway_host_number,
                    addresses=_addresses(network, pool.gateway_host_number, 0), reused=True)
        taken = [_network(a.cidr) for a in pool.allocations]
        candidate = _lowest_free(_network(pool.cidr), prefix_length, taken)
        if candidate is None:
            errors.append(f'{pool.pool} has no free /{prefix_length}')
            continue
        return PrefixAllocation(pool=pool.pool, zone=pool.zone, cidr=str(candidate),
                                prefix_length=prefix_length,
                                gateway_host_number=pool.gateway_host_number,
                                addresses=())
    raise ProvisioningError('PREFIX_POOL_EXHAUSTED',
                            'Every reviewed prefix pool for this site and zone is exhausted',
                            details={'pools': errors})


def _lowest_free(supernet: ipaddress.IPv4Network, prefix_length: int,
                 taken: list[ipaddress.IPv4Network]) -> ipaddress.IPv4Network | None:
    for candidate in supernet.subnets(new_prefix=prefix_length):
        if not any(candidate.overlaps(existing) for existing in taken):
            return candidate
    return None


def _addresses(network: ipaddress.IPv4Network, gateway_host_number: int, count: int) -> tuple[str, ...]:
    reserved = {network.network_address, network.broadcast_address,
                network.network_address + gateway_host_number}
    addresses: list[str] = []
    for host in network.hosts():
        if host in reserved:
            continue
        addresses.append(str(host))
        if len(addresses) == count:
            break
    return tuple(addresses)


def allocate_addresses(allocation: PrefixAllocation, count: int) -> PrefixAllocation:
    """Extend an allocation with `count` deterministic workload addresses."""
    network = _network(allocation.cidr)
    return PrefixAllocation(pool=allocation.pool, zone=allocation.zone, cidr=allocation.cidr,
                            prefix_length=allocation.prefix_length,
                            gateway_host_number=allocation.gateway_host_number,
                            addresses=_addresses(network, allocation.gateway_host_number, count),
                            reused=allocation.reused)


def assert_disjoint(allocations: tuple[PrefixAllocation, ...]) -> None:
    networks = [_network(a.cidr) for a in allocations]
    for index, network in enumerate(networks):
        for other in networks[index + 1:]:
            if network.overlaps(other):
                raise ProvisioningError('ADDRESS_CONFLICT',
                                        f'Allocated prefixes overlap: {network} and {other}',
                                        details={'prefixes': [str(n) for n in networks]})