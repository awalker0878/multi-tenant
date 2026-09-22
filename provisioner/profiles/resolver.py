"""Deterministic profile resolution.

Resolution converts portable profile names into one concrete, fully expanded
profile set. It refuses deferred profiles explicitly instead of silently
downgrading them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from provisioner.domain.errors import ProvisioningError
from provisioner.profiles.loader import Catalog, Profile

RESOLUTION_FORMAT = 'hosting-profile-resolution/1'

SERVICES = ('dns', 'ntp', 'identity', 'logging', 'backup')
DEFAULT_SERVICE_PROFILES = {'dns': 'default', 'ntp': 'default', 'identity': 'enterprise',
                            'logging': 'standard', 'backup': 'standard'}
DEFAULT_NETWORK_PROFILE = 'internal-ipv4'


@dataclass(frozen=True)
class Resolution:
    profiles: dict
    lifecycle: str
    zones: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    compute: dict = field(default_factory=dict)
    storage: dict = field(default_factory=dict)
    network: dict = field(default_factory=dict)
    services: dict = field(default_factory=dict)
    platform_inputs: dict = field(default_factory=dict)
    limits: tuple[str, ...] = ()
    trust: str = ''
    service_class: str = ''
    format: str = RESOLUTION_FORMAT

    def to_dict(self) -> dict:
        return {'format': self.format, 'profiles': dict(self.profiles),
                'lifecycle': self.lifecycle, 'zones': list(self.zones),
                'required_capabilities': list(self.required_capabilities),
                'compute': dict(self.compute), 'storage': dict(self.storage),
                'network': dict(self.network), 'services': dict(self.services),
                'platform_inputs': dict(self.platform_inputs),
                'trust': self.trust, 'service_class': self.service_class,
                'limits': list(self.limits)}


def _require_implemented(profile: Profile, path: str) -> Profile:
    if not profile.implemented:
        raise ProvisioningError('UNSUPPORTED_FEATURE',
                                f'{profile.family} profile {profile.profile} is deferred and not implemented',
                                path=path, details={'status': profile.status,
                                                    'limits': list(profile.limits)})
    return profile


def _merge_capabilities(target: set, profile: Profile) -> None:
    for capability in profile.requires.get('capabilities', []):
        target.add(capability)


def resolve(spec: dict, catalogs: Catalog) -> Resolution:
    """Resolve one normalized request spec into a concrete profile set."""
    environment = _require_implemented(
        catalogs.get('environment', spec['environment']), '$.spec.environment')
    security = _require_implemented(
        catalogs.get('security', spec['security']['profile']), '$.spec.security.profile')
    assurance_name = spec.get('assurance', {}).get('profile', 'standard')
    assurance = _require_implemented(
        catalogs.get('assurance', assurance_name), '$.spec.assurance.profile')
    availability = _require_implemented(
        catalogs.get('availability', spec['availability']['profile']), '$.spec.availability.profile')
    region = _require_implemented(
        catalogs.get('placement', spec['placement']['region']), '$.spec.placement.region')
    network = _require_implemented(
        catalogs.get('network', spec.get('network', {}).get('profile', DEFAULT_NETWORK_PROFILE)),
        '$.spec.network.profile')
    capacity = spec.get('capacity', {})
    compute = _require_implemented(
        catalogs.get('compute', capacity.get('computeProfile', 'medium')), '$.spec.capacity.computeProfile')
    storage = _require_implemented(
        catalogs.get('storage', capacity.get('storageProfile', 'standard')), '$.spec.capacity.storageProfile')
    recovery_spec = spec.get('recovery', {})
    recovery = None
    if recovery_spec.get('enabled'):
        recovery = _require_implemented(
            catalogs.get('recovery', recovery_spec.get('profile', 'standard')), '$.spec.recovery.profile')

    services: dict[str, str] = {}
    requested = spec.get('services', {})
    for name in SERVICES:
        requested_name = requested.get(name, DEFAULT_SERVICE_PROFILES[name])
        profile = _require_implemented(catalogs.get('service', f'{name}/{requested_name}'),
                                       f'$.spec.services.{name}')
        services[name] = profile.profile

    capabilities: set[str] = set()
    for profile in (environment, security, assurance, availability, network, compute, storage, region):
        _merge_capabilities(capabilities, profile)
    for name in SERVICES:
        _merge_capabilities(capabilities, catalogs.get('service', services[name]))
    if recovery is not None:
        _merge_capabilities(capabilities, recovery)

    zones = tuple(availability.requires.get('zones', ('OZ',)))
    limits = tuple(dict.fromkeys(list(environment.limits) + list(security.limits)
                                 + list(availability.limits) + list(network.limits)))
    return Resolution(
        profiles={
            'environment': environment.profile,
            'security': security.profile,
            'assurance': assurance.profile,
            'availability': availability.profile,
            'recovery': recovery.profile if recovery else None,
            'network': network.profile,
            'placement': region.profile,
            'compute': compute.profile,
            'storage': storage.profile,
            'services': dict(services),
        },
        lifecycle=environment.requires.get('lifecycle', environment.profile),
        zones=zones,
        required_capabilities=tuple(sorted(capabilities)),
        compute={'vcpu': compute.requires['vcpu'], 'memory_gib': compute.requires['memory_gib'],
                 'boot_disk_gib': compute.requires['boot_disk_gib'],
                 'workloads_per_zone': compute.requires['workloads_per_zone'],
                 'flavor_class': compute.requires['flavor_class'],
                 'profile': compute.profile},
        storage={'data_disk_gib': storage.requires['data_disk_gib'],
                 'storage_class': storage.requires['storage_class'],
                 'profile': storage.profile},
        network={'address_family': network.requires['address_family'],
                 'prefix_length': network.requires['prefix_length'],
                 'gateway_host_number': network.requires['gateway_host_number'],
                 'profile': network.profile},
        services=dict(services),
        platform_inputs={'compute': dict(compute.platform_inputs),
                         'storage': dict(storage.platform_inputs)},
                trust=security.trust or '',
                service_class=security.service_class or '',
                limits=limits)