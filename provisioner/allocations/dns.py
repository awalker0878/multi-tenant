"""DNS service declaration and registration intent.

DNS is a registration handoff. The provisioner states which names must exist and
which addresses they must resolve to, derived from the allocated addresses. It
does not write to the resolver and does not confirm the write.
"""
from __future__ import annotations

from provisioner.domain.errors import ProvisioningError

SERVICE = 'dns'
REQUIRED_ENDPOINTS = ('resolvers', 'zone')


def validate(endpoints: dict, site: str) -> None:
    missing = [name for name in REQUIRED_ENDPOINTS if not endpoints.get(name)]
    if missing:
        raise ProvisioningError('SERVICE_UNAVAILABLE',
                                f'{SERVICE} binding at {site} is incomplete: {missing}',
                                path=f'inventory.services.{SERVICE}',
                                details={'required_endpoints': list(REQUIRED_ENDPOINTS)})


def describe(endpoints: dict) -> dict:
    return {'resolvers': list(endpoints['resolvers']), 'zone': endpoints['zone'],
            'registration': 'DECLARED_NOT_WRITTEN',
            'obligations': ['The resolver writer performs the registration',
                            'Confirmation of the written record remains external']}


def records(zone: str, tenant: str, wsd: str, addresses: dict[str, str]) -> tuple[dict, ...]:
    """Return the records the owner must publish, one per zone-qualified member."""
    if not zone:
        raise ProvisioningError('SERVICE_UNAVAILABLE', 'DNS binding declares no zone',
                                path='inventory.services.dns')
    return tuple({'name': f'{tenant}-{wsd}-{domain}.{zone}', 'type': 'A', 'value': address}
                 for domain, address in sorted(addresses.items()))