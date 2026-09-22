"""Canonical resolved desired state.

Resolved desired state is the boundary between portable intent and platform
realization. It is fully resolved (no remaining "auto" values), fully expanded
(every domain and workload is enumerated) and carries no native mutation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from provisioner.domain.request import digest

DESIRED_STATE_FORMAT = 'hosting-resolved-desired-state/1'
STATUS = 'RESOLVED_DISABLED_NOT_AUTHORIZED'


@dataclass(frozen=True)
class WorkloadIntent:
    name: str
    address: str
    vcpu: int
    memory_gib: int
    boot_disk_gib: int
    data_disk_gib: int
    inputs: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {'name': self.name, 'address': self.address, 'vcpu': self.vcpu,
                'memory_gib': self.memory_gib, 'boot_disk_gib': self.boot_disk_gib,
                'data_disk_gib': self.data_disk_gib, 'inputs': dict(self.inputs)}


@dataclass(frozen=True)
class DomainIntent:
    domain_id: str
    zone: str
    cell_key: str
    cluster_id: str
    prefix: str
    gateway_host_number: int
    inputs: dict = field(default_factory=dict)
    workloads: tuple[WorkloadIntent, ...] = ()

    def to_dict(self) -> dict:
        return {'id': self.domain_id, 'zone': self.zone, 'cell': self.cell_key,
                'cluster': self.cluster_id, 'prefix': self.prefix,
                'gateway_host_number': self.gateway_host_number,
                'inputs': dict(self.inputs),
                'workloads': [w.to_dict() for w in self.workloads]}


@dataclass(frozen=True)
class DesiredState:
    """Fully resolved, deterministic desired state for one WSD request."""

    request_digest: str
    api_version: str
    kind: str
    tenant: str
    wsd: str
    owner: str
    lifecycle: str
    site_key: str
    platform: str
    platform_family: str
    trust: str
    service_class: str
    profiles: dict = field(default_factory=dict)
    profile_versions: dict = field(default_factory=dict)
    catalog_versions: dict = field(default_factory=dict)
    catalog_digest: str = ''
    policy: dict = field(default_factory=dict)
    placement: dict = field(default_factory=dict)
    capabilities: tuple[str, ...] = ()
    services: dict = field(default_factory=dict)
    service_bindings: tuple[dict, ...] = ()
    reservations: dict = field(default_factory=dict)
    clusters: tuple[dict, ...] = ()
    domains: tuple[DomainIntent, ...] = ()
    status: str = STATUS
    native_contact: bool = False
    format: str = DESIRED_STATE_FORMAT
    digest: str = ''
    limits: tuple[str, ...] = (
        'Resolved intent is not a deployment, a reservation confirmation or an authorization',
        'Capacity, address and service bindings are declared, not confirmed by their owners',
        'Native qualification and separate production approval remain required',
    )

    def to_dict(self) -> dict:
        return {
            'format': self.format,
            'status': self.status,
            'request_digest': self.request_digest,
            'apiVersion': self.api_version,
            'kind': self.kind,
            'tenant': self.tenant,
            'wsd': self.wsd,
            'owner': self.owner,
            'environment': self.lifecycle,
            'site': self.site_key,
            'platform': self.platform,
            'platform_family': self.platform_family,
            'trust': self.trust,
            'service_class': self.service_class,
            'profiles': dict(self.profiles),
            'profile_versions': dict(self.profile_versions),
            'catalog_versions': dict(self.catalog_versions),
            'catalog_digest': self.catalog_digest,
            'policy': dict(self.policy),
            'placement': dict(self.placement),
            'capabilities': list(self.capabilities),
            'services': dict(self.services),
            'service_bindings': [dict(b) for b in self.service_bindings],
            'reservations': dict(self.reservations),
            'clusters': [dict(c) for c in self.clusters],
            'domains': [d.to_dict() for d in self.domains],
            'native_contact': self.native_contact,
            'digest': self.digest,
            'limits': list(self.limits),
        }


def finalize(state: DesiredState) -> DesiredState:
    body = state.to_dict()
    body.pop('digest')
    return DesiredState(**{**state.__dict__, 'digest': digest(body)})