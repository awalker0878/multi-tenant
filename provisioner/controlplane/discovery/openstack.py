"""Bounded read-only discovery of one OpenStack project.

The caller supplies a site-verified campaign, pinned service catalog endpoints,
and a transport already bound to a project-scoped read credential. This module
never follows returned links, authenticates, opens a socket, or issues a mutating
request. Its COMPLETE marker means the three API collection page chains and
quota reads terminated without observed gaps; it is not a point-in-time native
snapshot, ownership acceptance, or permission to provision/migrate.

API routes: Nova ``GET /servers/detail`` and ``/os-quota-sets/{project}``,
Cinder v3 ``GET /volumes/detail`` and ``/os-quota-sets/{project}``, and
Neutron v2 ``GET /ports`` and ``/quotas/{project}``. Endpoint roots are pinned
to the exact project and catalog route by the trusted site integration.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Protocol
from urllib.parse import parse_qs, urlsplit

from provisioner.controlplane.authority.model import PlanScope

from .model import (DiscoveryCampaignAuthorization, DiscoveryFact, DiscoveryObject,
                    DiscoveryPage, NativeIdentity)


_PROJECT = re.compile(r'(?:[0-9a-f]{32}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})\Z')
_REQUIRED_KINDS = frozenset({'vm', 'volume', 'nic', 'quota'})
_SERVICES = ('compute', 'volume', 'network')
_COLLECTIONS = (
    ('compute', 'servers/detail', 'servers', 'servers_links', 'vm'),
    ('volume', 'volumes/detail', 'volumes', 'volumes_links', 'volume'),
    ('network', 'ports', 'ports', 'ports_links', 'nic'),
)


class OpenStackDiscoveryHeld(ValueError):
    """Scope, pagination, project ownership or response shape was ambiguous."""


class OpenStackHTTPError(RuntimeError):
    """The injected GET transport can report a native non-200 status."""

    def __init__(self, status: int):
        if type(status) is not int or not 400 <= status <= 599:
            raise ValueError('A native HTTP error needs an error status')
        self.status = status
        super().__init__(f'OpenStack read failed with HTTP {status}')


class ProjectReadTransport(Protocol):
    """Site-bound read credential; no redirects, mutations or token refresh.

    Implementations must verify the project in the credential, constrain every
    request to the pinned TLS catalog endpoint, set a finite response size and
    I/O deadline, reject redirects, and return only decoded 200 JSON objects.
    ``bound_scope`` and ``authenticated_project_id`` are verified properties,
    never values copied from the platform response or user HTTP request.
    """

    bound_scope: PlanScope
    authenticated_project_id: str

    def get_json(self, endpoint: str, path: str,
                 params: Mapping[str, str]) -> Mapping[str, object]: ...


@dataclass(frozen=True, slots=True)
class OpenStackServiceEndpoints:
    """Trusted catalog roots, e.g. /v2.1/<project>, /v3/<project>, /v2.0."""

    endpoint_id: str
    project_id: str
    compute: str
    volume: str
    network: str

    def __post_init__(self) -> None:
        if not isinstance(self.project_id, str) or not _PROJECT.fullmatch(self.project_id):
            raise ValueError('OpenStack project must have an exact UUID')
        if not isinstance(self.endpoint_id, str) or not re.fullmatch(
                r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', self.endpoint_id):
            raise ValueError('Invalid catalog endpoint identity')
        expected = {
            'compute': f'/v2.1/{self.project_id}',
            'volume': f'/v3/{self.project_id}',
            'network': '/v2.0',
        }
        for service, suffix in expected.items():
            value = getattr(self, service)
            if not isinstance(value, str):
                raise ValueError('Pinned HTTPS service endpoints are required')
            parsed = urlsplit(value)
            try:
                port = parsed.port
            except ValueError as exc:
                raise ValueError('Invalid pinned service port') from exc
            if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                    or parsed.password or parsed.query or parsed.fragment
                    or not parsed.path.endswith(suffix)
                    or parsed.path != parsed.path.rstrip('/')
                    or any(segment in ('.', '..') for segment in parsed.path.split('/'))
                    or port == 0):
                raise ValueError('Service catalog endpoint is not an exact HTTPS root')

    def for_service(self, service: str) -> str:
        if service not in _SERVICES:
            raise ValueError('Unknown OpenStack service')
        return getattr(self, service)


def _id(value: object, what: str) -> str:
    if not isinstance(value, str) or not _PROJECT.fullmatch(value):
        raise OpenStackDiscoveryHeld(f'{what} has no stable native UUID')
    return value


def _project(row: Mapping[str, object], project: str, keys: tuple[str, ...]) -> None:
    found = [row[key] for key in keys if key in row]
    if not found or any(value != project for value in found):
        raise OpenStackDiscoveryHeld('OpenStack object lacks exact project ownership')


def _fact(row: Mapping[str, object], key: str, name: str, expected: type,
          *, nullable: bool = False) -> DiscoveryFact:
    if key not in row:
        return DiscoveryFact.unknown(name, 'NOT_RETURNED')
    value = row[key]
    if value is None and nullable:
        return DiscoveryFact.known(name, None)
    if type(value) is not expected:
        raise OpenStackDiscoveryHeld(f'OpenStack {name} has an invalid type')
    return DiscoveryFact.known(name, value)


def _object(scope: PlanScope, kind: str, row: Mapping[str, object]) -> DiscoveryObject:
    native_id = _id(row.get('id'), kind)
    if kind == 'vm':
        _project(row, scope.native_scope_id, ('tenant_id', 'project_id'))
        facts = (_fact(row, 'name', 'name', str),
                 _fact(row, 'status', 'status', str))
    elif kind == 'volume':
        _project(row, scope.native_scope_id,
                 ('os-vol-tenant-attr:tenant_id', 'project_id'))
        facts = (_fact(row, 'name', 'name', str, nullable=True),
                 _fact(row, 'status', 'status', str),
                 _fact(row, 'size', 'size_gib', int))
        if 'size' in row and row['size'] < 0:
            raise OpenStackDiscoveryHeld('Volume size cannot be negative')
    else:
        _project(row, scope.native_scope_id, ('project_id', 'tenant_id'))
        facts = (_fact(row, 'network_id', 'network_id', str),
                 _fact(row, 'device_id', 'device_id', str),
                 _fact(row, 'status', 'status', str))
        if 'fixed_ips' in row:
            if not isinstance(row['fixed_ips'], list):
                raise OpenStackDiscoveryHeld('Port fixed IPs have invalid shape')
            # The API's address objects may carry extension fields. Retain only
            # the subnet and address, with no arbitrary metadata/user data.
            fixed_ips = []
            for item in row['fixed_ips']:
                if not isinstance(item, Mapping) or not isinstance(
                        item.get('ip_address'), str) or not isinstance(
                        item.get('subnet_id'), str):
                    raise OpenStackDiscoveryHeld('Port fixed IPs have invalid shape')
                fixed_ips.append({'ip_address': item['ip_address'],
                                  'subnet_id': item['subnet_id']})
            facts += (DiscoveryFact.known('fixed_ips', fixed_ips),)
        else:
            facts += (DiscoveryFact.unknown('fixed_ips', 'NOT_RETURNED'),)
    return DiscoveryObject(NativeIdentity(scope.endpoint_id, scope.native_scope_id,
                                          'openstack', kind, native_id), facts)


def _quota(scope: PlanScope, service: str, payload: Mapping[str, object]) -> DiscoveryObject:
    value = payload.get('quota_set' if service != 'network' else 'quota')
    if not isinstance(value, Mapping):
        raise OpenStackDiscoveryHeld('OpenStack quota response is missing')
    if 'id' in value and value['id'] != scope.native_scope_id:
        raise OpenStackDiscoveryHeld('Quota response belongs to another project')
    limits = {key: item for key, item in value.items()
              if key != 'id' and isinstance(key, str)
              and type(item) is int and item >= -1}
    required = {'compute': {'instances', 'cores', 'ram'},
                'volume': {'volumes', 'gigabytes'},
                'network': {'network', 'subnet', 'port'}}[service]
    if not limits or any(not isinstance(key, str) or type(item) is bool
                         for key, item in value.items()):
        raise OpenStackDiscoveryHeld('OpenStack quota values are invalid')
    facts = (DiscoveryFact.known('limits', limits)
             if required <= limits.keys() else
             DiscoveryFact.unknown('limits', 'NOT_RETURNED'),)
    return DiscoveryObject(NativeIdentity(scope.endpoint_id, scope.native_scope_id,
                                          'openstack', 'quota', service), facts)


def _next_link(response: Mapping[str, object], key: str, endpoint: str,
               path: str, last_id: str | None) -> bool:
    links = response.get(key, ())
    if not isinstance(links, (tuple, list)):
        raise OpenStackDiscoveryHeld('Invalid native pagination links')
    next_links = []
    for link in links:
        if not isinstance(link, Mapping) or link.get('rel') not in ('next', 'previous'):
            raise OpenStackDiscoveryHeld('Invalid native pagination links')
        if link['rel'] == 'next':
            next_links.append(link.get('href'))
    if len(next_links) > 1 or next_links and last_id is None:
        raise OpenStackDiscoveryHeld('Repeated or empty native next cursor')
    for href in next_links:
        if not isinstance(href, str):
            raise OpenStackDiscoveryHeld('Invalid native next URL')
        parsed, root = urlsplit(href), urlsplit(endpoint)
        query = parse_qs(parsed.query, strict_parsing=True)
        if (parsed.scheme != root.scheme or parsed.netloc != root.netloc
                or parsed.path != f'{root.path}/{path}' or parsed.fragment
                or query.get('marker') != [last_id]
                or any(len(values) != 1 for values in query.values())
                or query.get('all_tenants', ['false'])[0].lower() not in ('0', 'false')
                or 'page_reverse' in query):
            raise OpenStackDiscoveryHeld('Next link escapes the exact read route')
    return bool(next_links)


def _read(transport: ProjectReadTransport, endpoint: str, path: str,
          params: dict[str, str]) -> Mapping[str, object]:
    response = transport.get_json(endpoint, path, params)
    if not isinstance(response, Mapping):
        raise OpenStackDiscoveryHeld('Native read was not a JSON object')
    return response


def _error(service: str, exc: Exception) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if isinstance(exc, PermissionError) or isinstance(exc, OpenStackHTTPError) and exc.status in (401, 403):
        return ((f'{service}.READ_DENIED',), (f'openstack.{service}.read',))
    return ((f'{service}.READ_UNAVAILABLE',), ())


def collect_openstack_project(
    campaign: DiscoveryCampaignAuthorization,
    endpoints: OpenStackServiceEndpoints,
    transport: ProjectReadTransport,
) -> tuple[DiscoveryPage, ...]:
    """Read one bound project or return terminal PARTIAL on native service loss.

    The returned pages still require ``assemble_discovery_result`` plus trusted
    campaign/transport provenance checks at ingestion. A malformed or
    cross-project response raises with no partial result to ingest.
    """
    if (not isinstance(campaign, DiscoveryCampaignAuthorization)
            or campaign.scope.platform_family != 'openstack'
            or not _REQUIRED_KINDS <= set(campaign.allowed_kinds)
            or not isinstance(endpoints, OpenStackServiceEndpoints)
            or endpoints.endpoint_id != campaign.scope.endpoint_id
            or endpoints.project_id != campaign.scope.native_scope_id
            or getattr(transport, 'bound_scope', None) != campaign.scope
            or getattr(transport, 'authenticated_project_id', None) != endpoints.project_id
            or not callable(getattr(transport, 'get_json', None))):
        raise ValueError('Verified exact project, route and read campaign required')

    pages: list[DiscoveryPage] = []
    seen: set[tuple[str, str]] = set()
    cursor: str | None = None
    object_count = 0
    has_unknown = False

    def append(objects: tuple[DiscoveryObject, ...], next_cursor: str | None,
               *, error: str | None = None, privilege: str | None = None) -> bool:
        nonlocal cursor, object_count, has_unknown
        at = datetime.now(timezone.utc)
        if not campaign.issued_at <= at < campaign.expires_at:
            raise OpenStackDiscoveryHeld('Campaign expired during native read')
        object_count += len(objects)
        if object_count > campaign.max_objects:
            object_count -= len(objects)
            error, privilege, objects, next_cursor = 'OBJECT_BUDGET_EXCEEDED', None, (), None
        if next_cursor is not None and len(pages) + 1 >= campaign.max_pages:
            error, privilege, next_cursor = 'PAGE_BUDGET_EXCEEDED', None, None
        unknown = any(fact.state == 'UNKNOWN' for obj in objects for fact in obj.facts)
        has_unknown |= unknown
        terminal = None
        if next_cursor is None:
            terminal = ('PARTIAL' if error or privilege or has_unknown else 'COMPLETE')
        pages.append(DiscoveryPage(campaign.campaign_id, campaign.scope,
                                   len(pages) + 1, cursor, next_cursor, at, objects,
                                   terminal_completeness=terminal,
                                   collection_errors=(error,) if error else (),
                                   missing_privileges=(privilege,) if privilege else ()))
        cursor = next_cursor
        return next_cursor is not None

    for service, path, list_key, links_key, kind in _COLLECTIONS:
        marker: str | None = None
        used_markers: set[str] = set()
        while True:
            params = {'limit': str(campaign.max_page_size)}
            if marker is not None:
                params['marker'] = marker
            if service == 'compute':
                params['all_tenants'] = 'false'
            try:
                response = _read(transport, endpoints.for_service(service), path, params)
            except OpenStackDiscoveryHeld:
                raise
            except Exception as exc:
                errors, privileges = _error(service, exc)
                append((), None, error=errors[0],
                       privilege=privileges[0] if privileges else None)
                return tuple(pages)
            rows = response.get(list_key)
            if not isinstance(rows, list) or len(rows) > campaign.max_page_size:
                raise OpenStackDiscoveryHeld('OpenStack collection is missing or exceeds page size')
            objects = []
            for row in rows:
                if not isinstance(row, Mapping):
                    raise OpenStackDiscoveryHeld('Malformed native collection row')
                obj = _object(campaign.scope, kind, row)
                key = (kind, obj.identity.native_id)
                if key in seen:
                    raise OpenStackDiscoveryHeld('Repeated native object across OpenStack pages')
                seen.add(key)
                objects.append(obj)
            last_id = objects[-1].identity.native_id if objects else None
            linked = _next_link(response, links_key, endpoints.for_service(service), path,
                                last_id)
            more = linked or len(objects) == campaign.max_page_size
            if more and not objects:
                raise OpenStackDiscoveryHeld('Empty nonterminal native page')
            if more:
                if last_id == marker or last_id in used_markers:
                    raise OpenStackDiscoveryHeld('Native pagination cursor repeated')
                used_markers.add(last_id)
                next_cursor = f'openstack:{service}:{last_id}'
            else:
                index = _SERVICES.index(service)
                next_cursor = (f'openstack:{_SERVICES[index + 1]}:start'
                               if index < len(_SERVICES) - 1 else
                               'openstack:quota:compute')
            if not append(tuple(objects), next_cursor):
                return tuple(pages)
            if not more:
                break
            marker = last_id

    for index, service in enumerate(_SERVICES):
        endpoint = endpoints.for_service(service)
        path = (f'os-quota-sets/{endpoints.project_id}' if service != 'network'
                else f'quotas/{endpoints.project_id}')
        try:
            response = _read(transport, endpoint, path, {})
        except OpenStackDiscoveryHeld:
            raise
        except Exception as exc:
            errors, privileges = _error(service, exc)
            append((), None, error=errors[0],
                   privilege=privileges[0] if privileges else None)
            return tuple(pages)
        obj = _quota(campaign.scope, service, response)
        if not append((obj,), f'openstack:quota:{_SERVICES[index + 1]}'
                      if index < len(_SERVICES) - 1 else None):
            return tuple(pages)
    return tuple(pages)
