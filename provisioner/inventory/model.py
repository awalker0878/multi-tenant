"""Existing-state inventory.

Inventory is the reviewed description of what already exists: sites, cells,
clusters, host groups, prefix pools and shared-service endpoints. It is read-only
input to the provisioner. The provisioner never writes inventory and never
treats a fixture as a placement authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib.resources import as_file, files
from pathlib import Path

from provisioner.domain.request import load as load_document, digest
from provisioner.domain.capability_properties import validate_observations
from provisioner.repository import reviewed_source

INVENTORY_FORMAT = 'hosting-inventory/1'

AUTHORITATIVE = 'AUTHORITATIVE'
FIXTURE = 'FIXTURE_NOT_AUTHORITATIVE'
STATUSES = (AUTHORITATIVE, FIXTURE)

ZONES = ('OZ', 'RZ')
CLUSTER_ROLES = ('management', 'security-edge', 'shared-services', 'trust', 'workload',
                 'data', 'protection', 'recovery', 'qualification')


@dataclass(frozen=True)
class Capacity:
    vcpu_total: int
    vcpu_committed: int
    memory_gib_total: int
    memory_gib_committed: int
    storage_gib_total: int
    storage_gib_committed: int

    @property
    def vcpu_available(self) -> int:
        return self.vcpu_total - self.vcpu_committed

    @property
    def memory_gib_available(self) -> int:
        return self.memory_gib_total - self.memory_gib_committed

    @property
    def storage_gib_available(self) -> int:
        return self.storage_gib_total - self.storage_gib_committed

    def to_dict(self) -> dict:
        return {'vcpu_total': self.vcpu_total, 'vcpu_committed': self.vcpu_committed,
                'memory_gib_total': self.memory_gib_total,
                'memory_gib_committed': self.memory_gib_committed,
                'storage_gib_total': self.storage_gib_total,
                'storage_gib_committed': self.storage_gib_committed,
                'vcpu_available': self.vcpu_available,
                'memory_gib_available': self.memory_gib_available,
                'storage_gib_available': self.storage_gib_available}


@dataclass(frozen=True)
class Cluster:
    id: str
    role: str
    zone: str
    trust: str
    service_classes: tuple[str, ...]
    eligible_tenants: tuple[str, ...]
    dedicated_wsd: str | None
    host_ids: tuple[str, ...]
    native: dict
    capacity: Capacity
    capability_properties: dict = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, 'capability_properties',
                           validate_observations(dict(self.capability_properties)))

    def supports(self, trust: str, service_class: str, tenant: str, wsd: str) -> bool:
        if self.trust != trust or service_class not in self.service_classes:
            return False
        if self.eligible_tenants and tenant not in self.eligible_tenants:
            return False
        return self.dedicated_wsd in (None, wsd)

    def to_environment(self) -> dict:
        """The cluster shape the existing hosting-wsd-environment/1 contract requires."""
        return {'id': self.id, 'role': self.role, 'zone': self.zone, 'trust': self.trust,
                'service_classes': list(self.service_classes),
                'eligible_tenants': list(self.eligible_tenants),
                'dedicated_wsd': self.dedicated_wsd,
                'host_ids': list(self.host_ids), 'native': dict(self.native)}

    def to_dict(self) -> dict:
        return {**self.to_environment(), 'capacity': self.capacity.to_dict(),
                'capability_properties': dict(self.capability_properties)}


@dataclass(frozen=True)
class Cell:
    cell: str
    capabilities: tuple[str, ...]
    clusters: tuple[Cluster, ...]

    def zone_clusters(self, zone: str) -> tuple[Cluster, ...]:
        return tuple(c for c in self.clusters if c.zone == zone)

    def to_dict(self) -> dict:
        return {'cell': self.cell, 'capabilities': list(self.capabilities),
                'clusters': [c.to_dict() for c in self.clusters]}


@dataclass(frozen=True)
class Site:
    site: str
    region: str
    platform: str
    defaults: dict
    cells: tuple[Cell, ...]

    def domain_inputs(self) -> dict:
        return dict(self.defaults.get('domain_inputs', {}))

    def workload_inputs(self, flavor_class: str, storage_class: str,
                        artifact_ref: str | None = None) -> dict:
        merged = dict(self.defaults.get('workload_inputs', {}))
        merged.update(self.defaults.get('by_flavor_class', {}).get(flavor_class, {}))
        merged.update(self.defaults.get('by_storage_class', {}).get(storage_class, {}))
        if artifact_ref is not None:
            artifacts = self.defaults.get('by_artifact', {})
            if artifact_ref not in artifacts:
                raise KeyError(artifact_ref)
            merged.update(artifacts[artifact_ref])
        return merged

    def to_dict(self) -> dict:
        return {'site': self.site, 'region': self.region, 'platform': self.platform,
                'defaults': {k: dict(v) for k, v in self.defaults.items()},
                'cells': [c.to_dict() for c in self.cells]}


@dataclass(frozen=True)
class PrefixAllocation:
    tenant: str
    wsd: str
    domain: str
    cidr: str

    def to_dict(self) -> dict:
        return {'tenant': self.tenant, 'wsd': self.wsd, 'domain': self.domain, 'cidr': self.cidr}


@dataclass(frozen=True)
class PrefixPool:
    pool: str
    site: str
    zone: str
    cidr: str
    prefix_length: int
    gateway_host_number: int
    allocations: tuple[PrefixAllocation, ...] = ()

    def to_dict(self) -> dict:
        return {'pool': self.pool, 'site': self.site, 'zone': self.zone, 'cidr': self.cidr,
                'prefix_length': self.prefix_length,
                'gateway_host_number': self.gateway_host_number,
                'allocations': [a.to_dict() for a in self.allocations]}


@dataclass(frozen=True)
class ServiceEndpoint:
    service: str
    binding_class: str
    site: str
    endpoints: dict

    def to_dict(self) -> dict:
        return {'service': self.service, 'binding_class': self.binding_class,
                'site': self.site, 'endpoints': dict(self.endpoints)}


@dataclass(frozen=True)
class Inventory:
    status: str
    source: str
    sites: tuple[Site, ...]
    prefix_pools: tuple[PrefixPool, ...]
    services: tuple[ServiceEndpoint, ...]
    format: str = INVENTORY_FORMAT
    origin: str = '<in-memory>'
    document_digest: str = ''

    @property
    def authoritative(self) -> bool:
        return self.status == AUTHORITATIVE

    @property
    def reference(self) -> dict:
        """The approval-critical identity of this reviewed inventory document.

        One reviewed document is one decision, so the reference binds the document
        digest, the source the document declares about itself, its status and its
        authority — and nothing about where the file happened to be read from. The
        read location is `origin`, which is diagnostic provenance: binding it would
        make the same inventory produce a different plan identity on another
        operating system, in another checkout or under another path spelling.
        """
        return {'digest': self.document_digest, 'source': self.source,
                'status': self.status, 'authoritative': self.authoritative}

    def site(self, name: str) -> Site:
        for site in self.sites:
            if site.site == name:
                return site
        raise KeyError(name)

    def pools(self, site: str, zone: str) -> tuple[PrefixPool, ...]:
        return tuple(p for p in self.prefix_pools if p.site == site and p.zone == zone)

    def service(self, service: str, site: str) -> ServiceEndpoint | None:
        for endpoint in self.services:
            if endpoint.service == service and endpoint.site == site:
                return endpoint
        return None

    def to_dict(self) -> dict:
        return {'format': self.format, 'status': self.status, 'source': self.source,
                'sites': [s.to_dict() for s in self.sites],
                'prefix_pools': [p.to_dict() for p in self.prefix_pools],
                'services': [s.to_dict() for s in self.services]}


def _require(document: dict, keys: set[str], where: str) -> None:
    missing = keys - set(document)
    if missing:
        raise ValueError(f'{where}: missing fields {sorted(missing)}')


def diagnostic_origin(origin: str) -> str:
    """The read location, recorded for diagnostics in one platform-neutral spelling.

    A reviewer reading an artifact may want to know which file was read, but the
    location is never part of the reviewed decision, so it is normalized to POSIX
    separators here and kept out of the inventory reference.
    """
    return str(origin).replace('\\', '/')


def _capacity(raw: dict, where: str) -> Capacity:
    _require(raw, {'vcpu_total', 'vcpu_committed', 'memory_gib_total', 'memory_gib_committed',
                   'storage_gib_total', 'storage_gib_committed'}, where)
    capacity = Capacity(**{k: raw[k] for k in (
        'vcpu_total', 'vcpu_committed', 'memory_gib_total', 'memory_gib_committed',
        'storage_gib_total', 'storage_gib_committed')})
    if any(v < 0 for v in capacity.to_dict().values()):
        raise ValueError(f'{where}: capacity values cannot be negative')
    if capacity.vcpu_committed > capacity.vcpu_total or \
            capacity.memory_gib_committed > capacity.memory_gib_total or \
            capacity.storage_gib_committed > capacity.storage_gib_total:
        raise ValueError(f'{where}: committed capacity exceeds total capacity')
    return capacity


def build(document: dict, origin: str = '<in-memory>') -> Inventory:
    """Build an Inventory from a parsed document, refusing incomplete or drifting input."""
    _require(document, {'format', 'status', 'source', 'sites', 'prefix_pools', 'services'},
             'inventory')
    if document['format'] != INVENTORY_FORMAT:
        raise ValueError(f'Unsupported inventory format: {document["format"]!r}')
    if document['status'] not in STATUSES:
        raise ValueError(f'Unsupported inventory status: {document["status"]!r}')

    sites: list[Site] = []
    seen_sites: set[str] = set()
    for site_raw in document['sites']:
        _require(site_raw, {'site', 'region', 'platform', 'defaults', 'cells'}, 'inventory site')
        if site_raw['site'] in seen_sites:
            raise ValueError(f'Duplicate inventory site: {site_raw["site"]}')
        seen_sites.add(site_raw['site'])
        defaults = dict(site_raw['defaults'])
        unknown = set(defaults) - {'domain_inputs', 'workload_inputs', 'by_flavor_class', 'by_storage_class', 'by_artifact'}
        if unknown:
            raise ValueError(f'{site_raw["site"]}: unknown native default group')
        cells: list[Cell] = []
        seen_cells: set[str] = set()
        for cell_raw in site_raw['cells']:
            _require(cell_raw, {'cell', 'capabilities', 'clusters'}, 'inventory cell')
            if cell_raw['cell'] in seen_cells:
                raise ValueError(f'Duplicate inventory cell: {cell_raw["cell"]}')
            seen_cells.add(cell_raw['cell'])
            clusters: list[Cluster] = []
            seen_clusters: set[str] = set()
            for cluster_raw in cell_raw['clusters']:
                _require(cluster_raw, {'id', 'role', 'zone', 'trust', 'service_classes',
                                       'eligible_tenants', 'dedicated_wsd', 'host_ids',
                                       'native', 'capacity'}, 'inventory cluster')
                if cluster_raw['id'] in seen_clusters:
                    raise ValueError(f'Duplicate inventory cluster: {cluster_raw["id"]}')
                seen_clusters.add(cluster_raw['id'])
                if cluster_raw['role'] not in CLUSTER_ROLES:
                    raise ValueError(f'{cluster_raw["id"]}: unsupported cluster role')
                if cluster_raw['zone'] not in ZONES:
                    raise ValueError(f'{cluster_raw["id"]}: unsupported zone')
                clusters.append(Cluster(
                    id=cluster_raw['id'], role=cluster_raw['role'], zone=cluster_raw['zone'],
                    trust=cluster_raw['trust'],
                    service_classes=tuple(cluster_raw['service_classes']),
                    eligible_tenants=tuple(cluster_raw['eligible_tenants']),
                    dedicated_wsd=cluster_raw['dedicated_wsd'],
                    host_ids=tuple(cluster_raw['host_ids']),
                    native=dict(cluster_raw['native']),
                    capacity=_capacity(cluster_raw['capacity'], cluster_raw['id']),
                    capability_properties=validate_observations(
                        cluster_raw.get('capability_properties', {}))))
            cells.append(Cell(cell=cell_raw['cell'],
                              capabilities=tuple(cell_raw['capabilities']),
                              clusters=tuple(sorted(clusters, key=lambda c: c.id))))
        sites.append(Site(site=site_raw['site'], region=site_raw['region'],
                                  platform=site_raw['platform'], defaults=defaults,
                          cells=tuple(sorted(cells, key=lambda c: c.cell))))

    pools: list[PrefixPool] = []
    seen_pools: set[str] = set()
    for pool_raw in document['prefix_pools']:
        _require(pool_raw, {'pool', 'site', 'zone', 'cidr', 'prefix_length',
                            'gateway_host_number', 'allocations'}, 'inventory prefix pool')
        if pool_raw['pool'] in seen_pools:
            raise ValueError(f'Duplicate inventory prefix pool: {pool_raw["pool"]}')
        seen_pools.add(pool_raw['pool'])
        if pool_raw['site'] not in seen_sites:
            raise ValueError(f'{pool_raw["pool"]}: unknown site {pool_raw["site"]}')
        if pool_raw['zone'] not in ZONES:
            raise ValueError(f'{pool_raw["pool"]}: unsupported zone')
        allocations = []
        for allocation_raw in pool_raw['allocations']:
            _require(allocation_raw, {'tenant', 'wsd', 'domain', 'cidr'},
                     f'inventory pool {pool_raw["pool"]} allocation')
            allocations.append(PrefixAllocation(**allocation_raw))
        pools.append(PrefixPool(pool=pool_raw['pool'], site=pool_raw['site'],
                                zone=pool_raw['zone'], cidr=pool_raw['cidr'],
                                prefix_length=pool_raw['prefix_length'],
                                gateway_host_number=pool_raw['gateway_host_number'],
                                allocations=tuple(sorted(allocations,
                                                         key=lambda a: (a.tenant, a.domain)))))

    services: list[ServiceEndpoint] = []
    seen_services: set[tuple[str, str]] = set()
    for service_raw in document['services']:
        _require(service_raw, {'service', 'binding_class', 'site', 'endpoints'},
                 'inventory service')
        key = (service_raw['service'], service_raw['site'])
        if key in seen_services:
            raise ValueError(f'Duplicate inventory service binding: {key}')
        seen_services.add(key)
        if service_raw['site'] not in seen_sites:
            raise ValueError(f'inventory service {key}: unknown site {service_raw["site"]}')
        services.append(ServiceEndpoint(**service_raw))

    return Inventory(status=document['status'], source=document['source'],
                     sites=tuple(sorted(sites, key=lambda s: s.site)),
                     prefix_pools=tuple(sorted(pools, key=lambda p: p.pool)),
                     services=tuple(sorted(services, key=lambda s: (s.service, s.site))),
                     origin=diagnostic_origin(origin), document_digest=digest(document))


def load(path: Path | str) -> Inventory:
    """Read a reviewed inventory document, recording where it was read as provenance.

    The read location is recorded with `reviewed_source`, which renders a document
    inside the checkout as a POSIX repository-relative path. That keeps the
    diagnostic origin stable across checkouts and operating systems, and it is
    recorded for diagnostics only: the identity is `Inventory.reference`.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'Inventory not found: {path}')
    return build(load_document(path), origin=reviewed_source(path))


def fixture(name: str = 'openstack-reference') -> Inventory:
    if not name or Path(name).name != name or '/' in name or '\\' in name:
        raise ValueError('Fixture name must identify one packaged inventory')
    with as_file(files(__package__).joinpath('fixtures', f'{name}.json')) as path:
        return load(path)
