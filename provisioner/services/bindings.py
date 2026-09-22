"""Service binding resolution.

A service binding is a declared handoff: the provisioner states which reviewed
endpoint a workload security domain must use. It never provisions the service,
never registers the address itself and never claims the service is healthy.
"""
from __future__ import annotations

from dataclasses import dataclass

from provisioner.domain.errors import ProvisioningError
from provisioner.inventory.model import Inventory, ServiceEndpoint
from provisioner.services import backup, identity, logging, time
from provisioner.allocations import dns

BINDING_FORMAT = 'hosting-service-binding/1'
SERVICE_ORDER = ('dns', 'ntp', 'identity', 'logging', 'backup')
_VALIDATORS = {'dns': dns, 'ntp': time, 'identity': identity, 'logging': logging,
               'backup': backup}


@dataclass(frozen=True)
class Binding:
    service: str
    profile: str
    binding_class: str
    site: str
    endpoints: dict
    status: str = 'DECLARED_HANDOFF_NOT_VERIFIED'

    def to_dict(self) -> dict:
        return {'format': BINDING_FORMAT, 'service': self.service, 'profile': self.profile,
                'binding_class': self.binding_class, 'site': self.site,
                'endpoints': dict(self.endpoints), 'status': self.status,
                'limits': ['Reachability, retention and restore remain owner obligations']}


def _binding_class(catalogs, service: str, profile: str) -> str:
    entry = catalogs.get('service', profile)
    required = entry.requires.get('binding_class')
    if not required:
        raise ProvisioningError('SERVICE_UNAVAILABLE',
                                f'{profile} declares no binding class',
                                path=f'$.spec.services.{service}')
    return required


def resolve(resolution, catalogs, inventory: Inventory, site: str) -> tuple[Binding, ...]:
    """Bind every resolved service profile to a reviewed inventory endpoint."""
    bindings: list[Binding] = []
    for service in SERVICE_ORDER:
        profile = resolution.services.get(service)
        if profile is None:
            raise ProvisioningError('SERVICE_UNAVAILABLE',
                                    f'No resolved profile for service {service}',
                                    path=f'$.spec.services.{service}')
        required = _binding_class(catalogs, service, profile)
        endpoint = inventory.service(service, site)
        if endpoint is None:
            raise ProvisioningError('SERVICE_UNAVAILABLE',
                                    f'No reviewed {service} endpoint at {site}',
                                    path=f'inventory.services.{service}',
                                    details={'site': site, 'binding_class': required})
        if endpoint.binding_class != required:
            raise ProvisioningError('SERVICE_UNAVAILABLE',
                                    f'{service} binding class mismatch at {site}',
                                    path=f'inventory.services.{service}',
                                    details={'required': required,
                                             'available': endpoint.binding_class})
        _VALIDATORS[service].validate(endpoint.endpoints, site)
        bindings.append(Binding(service=service, profile=profile, binding_class=required,
                                site=site, endpoints=dict(endpoint.endpoints)))
    return tuple(bindings)


def describe(bindings: tuple[Binding, ...], resolution) -> dict:
    """Per-service declaration text, in a stable order."""
    by_service = {b.service: b for b in bindings}
    described: dict[str, dict] = {}
    if 'dns' in by_service:
        described['dns'] = dns.describe(by_service['dns'].endpoints)
    if 'ntp' in by_service:
        described['ntp'] = time.describe(by_service['ntp'].endpoints)
    if 'identity' in by_service:
        described['identity'] = identity.describe(by_service['identity'].endpoints)
    if 'logging' in by_service:
        protected = by_service['logging'].binding_class == 'logging-protected'
        described['logging'] = logging.describe(by_service['logging'].endpoints, protected)
    if 'backup' in by_service:
        described['backup'] = backup.describe(
            by_service['backup'].endpoints, bool(resolution.profiles.get('recovery')))
    return described


def endpoint_for(bindings: tuple[Binding, ...], service: str) -> ServiceEndpoint | None:
    for binding in bindings:
        if binding.service == service:
            return ServiceEndpoint(service=binding.service, binding_class=binding.binding_class,
                                   site=binding.site, endpoints=dict(binding.endpoints))
    return None


def summary(bindings: tuple[Binding, ...]) -> dict:
    return {'format': BINDING_FORMAT, 'count': len(bindings),
            'services': [b.service for b in bindings],
            'binding_classes': {b.service: b.binding_class for b in bindings},
            'status': 'DECLARED_HANDOFF_NOT_VERIFIED',
            'limits': ['A declared binding is not evidence the service is reachable']}