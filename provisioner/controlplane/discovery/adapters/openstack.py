"""Bounded read-only discovery of one OpenStack project.

The caller supplies a site-verified campaign, pinned service catalog endpoints,
and a transport already bound to a project-scoped read credential. This module
never follows returned links, authenticates, opens a socket, or issues a mutating
request. Its COMPLETE marker means the three project collection page chains, quota reads,
and referenced-image reads terminated without observed gaps; it is not a point-in-time native
snapshot, ownership acceptance, or permission to provision/migrate.

API routes: Nova ``GET /servers/detail`` and ``/os-quota-sets/{project}``,
Cinder v3 ``GET /volumes/detail`` and ``/os-quota-sets/{project}``, and
Neutron v2 ``GET /ports`` and ``/quotas/{project}``. Endpoint roots are pinned
to the exact project and catalog route by the trusted site integration.
"""
from __future__ import annotations

import re
import ipaddress
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping, Protocol
from urllib.parse import parse_qs, urlsplit

from provisioner.controlplane.authority.model import PlanScope

from ..model import (DiscoveryCampaignAuthorization, DiscoveryFact, DiscoveryObject,
                    DiscoveryPage, NativeIdentity, _utc)


_PROJECT = re.compile(r'(?:[0-9a-f]{32}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})\Z')
_REQUIRED_KINDS = frozenset({'vm', 'volume', 'nic', 'quota', 'image'})
_CORE_SERVICES = ('compute', 'volume', 'network')
_SERVICES = (*_CORE_SERVICES, 'image')
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
    image: str

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
            'image': '/v2',
        }
        for service, suffix in expected.items():
            value = getattr(self, service)
            if (not isinstance(value, str) or len(value) > 1024
                    or any(not 33 <= ord(c) <= 126 for c in value)
                    or any(char in value for char in '%\\?#')):
                raise ValueError('Pinned HTTPS service endpoints are required')
            parsed = urlsplit(value)
            try:
                port = parsed.port
            except ValueError as exc:
                raise ValueError('Invalid pinned service port') from exc
            if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                    or parsed.password is not None or parsed.query or parsed.fragment
                    or parsed.netloc.endswith(':')
                    or parsed.username is not None
                    or not re.fullmatch(r'[a-z0-9.:-]+', parsed.hostname)
                    or not re.fullmatch(r'(?:/[A-Za-z0-9._~-]+)+', parsed.path)
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


def _native_list(row: Mapping[str, object], name: str) -> DiscoveryFact:
    """Observe a bounded native relationship set; never manufacture an empty set."""
    if name not in row:
        return DiscoveryFact.unknown(name, 'NOT_RETURNED')
    items = row[name]
    if not isinstance(items, list) or len(items) > 64:
        raise OpenStackDiscoveryHeld('Native relationship list exceeds its bounded shape')
    values = [_id(item, name) for item in items]
    if len(values) != len(set(values)):
        raise OpenStackDiscoveryHeld('Duplicate native relationship identity')
    return DiscoveryFact.known(name, sorted(values))


def _nullable_id(row: Mapping[str, object], name: str) -> DiscoveryFact:
    fact = _fact(row, name, name, str, nullable=True)
    if fact.state == 'KNOWN' and fact.value() is not None:
        _id(fact.value(), name)
    return fact


def _address(value: object, *, cidr: bool = False) -> str:
    if not isinstance(value, str) or len(value) > 64 or '%' in value:
        raise OpenStackDiscoveryHeld('Invalid native IP address')
    try:
        # Keep hosts as hosts, and explicit CIDR policies as networks. Reject
        # masked host bits rather than silently broadening an anti-spoof rule.
        parsed = (ipaddress.ip_network(value, strict=True) if cidr and '/' in value
                  else ipaddress.ip_address(value))
    except ValueError as exc:
        raise OpenStackDiscoveryHeld('Invalid native IP address') from exc
    return str(parsed)


def _mac(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}', value):
        raise OpenStackDiscoveryHeld('Invalid native MAC address')
    return value.lower()


def _pairs(row: Mapping[str, object]) -> DiscoveryFact:
    name = 'allowed_address_pairs'
    if name not in row:
        return DiscoveryFact.unknown(name, 'NOT_RETURNED')
    items = row[name]
    if not isinstance(items, list) or len(items) > 32:
        raise OpenStackDiscoveryHeld('Allowed address pairs exceed their bounded shape')
    pairs = []
    for item in items:
        if not isinstance(item, Mapping):
            raise OpenStackDiscoveryHeld('Invalid allowed address pair')
        # Native response requires both values; arbitrary extension data is not retained.
        pair = {'ip_address': _address(item.get('ip_address'), cidr=True),
                'mac_address': _mac(item.get('mac_address'))}
        if pair in pairs:
            raise OpenStackDiscoveryHeld('Duplicate allowed address pair')
        pairs.append(pair)
    return DiscoveryFact.known(name, sorted(pairs, key=lambda p: (p['ip_address'], p['mac_address'])))



def _flavor_facts(row: Mapping[str, object]) -> tuple[DiscoveryFact, ...]:
    """Read Nova >=2.47's embedded allocation, never a mutable flavor lookup.

    Flavor disk sizes are nominal allocations, not observed root/total storage.
    Missing fields (including partial down-cell responses) stay UNKNOWN.
    """
    flavor = row.get('flavor', {})
    if not isinstance(flavor, Mapping):
        raise OpenStackDiscoveryHeld('Embedded server flavor has an invalid shape')
    result = []
    for key, name, scale, minimum in (
            ('vcpus', 'vcpuCount', 1, 1),
            ('ram', 'memorySizeBytes', 1024**2, 1),
            ('disk', 'flavorRootDiskBytes', 1024**3, 0),
            ('ephemeral', 'flavorEphemeralDiskBytes', 1024**3, 0),
            ('swap', 'flavorSwapBytes', 1024**2, 0)):
        if key not in flavor:
            result.append(DiscoveryFact.unknown(name, 'NOT_RETURNED'))
            continue
        value = flavor[key]
        if type(value) is not int or not minimum <= value <= (2**63 - 1) // scale:
            raise OpenStackDiscoveryHeld('Embedded server allocation exceeds its typed bounds')
        result.append(DiscoveryFact.known(name, value * scale))
    return tuple(result)


def _server_storage_facts(row: Mapping[str, object]) -> tuple[DiscoveryFact, ...]:
    """Retain observed references, not guessed boot volume or deletion authority."""
    if 'image' not in row:
        image = DiscoveryFact.unknown('imageId', 'NOT_RETURNED')
    elif row['image'] == '':
        # Nova explicitly returns an empty string for volume-backed boot.
        image = DiscoveryFact.known('imageId', None)
    elif isinstance(row['image'], Mapping):
        image = (DiscoveryFact.known('imageId', _id(row['image']['id'], 'image'))
                 if 'id' in row['image'] else
                 DiscoveryFact.unknown('imageId', 'NOT_RETURNED'))
    else:
        raise OpenStackDiscoveryHeld('Server image reference has an invalid shape')
    key = 'os-extended-volumes:volumes_attached'
    if key not in row:
        return (image, DiscoveryFact.unknown('attachedVolumeIds', 'NOT_RETURNED'),
                DiscoveryFact.unknown('volumeDeleteOnTermination', 'NOT_RETURNED'))
    items = row[key]
    if not isinstance(items, list) or len(items) > 64:
        raise OpenStackDiscoveryHeld('Server volume relationships exceed their bounded shape')
    identities, disposition, missing = set(), [], False
    for item in items:
        if not isinstance(item, Mapping):
            raise OpenStackDiscoveryHeld('Invalid server volume relationship')
        volume_id = _id(item.get('id'), 'attached volume')
        if volume_id in identities:
            raise OpenStackDiscoveryHeld('Duplicate server volume relationship')
        identities.add(volume_id)
        if 'delete_on_termination' not in item:
            missing = True
        elif type(item['delete_on_termination']) is not bool:
            raise OpenStackDiscoveryHeld('Volume deletion disposition must be a native boolean')
        else:
            disposition.append({'volumeId': volume_id,
                                'deleteOnTermination': item['delete_on_termination']})
    return (image, DiscoveryFact.known('attachedVolumeIds', sorted(identities)),
            DiscoveryFact.unknown('volumeDeleteOnTermination', 'NOT_RETURNED') if missing else
            DiscoveryFact.known('volumeDeleteOnTermination',
                                sorted(disposition, key=lambda item: item['volumeId'])))


def _volume_attachment_fact(row: Mapping[str, object], volume_id: str) -> DiscoveryFact:
    """Cinder /volumes/detail relationships; never copy connector secrets.

    IDs are observations in this project, not proof of a complete consistency
    group, device order, native path authority or exclusion of another writer.
    """
    if 'attachments' not in row:
        return DiscoveryFact.unknown('volumeAttachments', 'NOT_RETURNED')
    items = row['attachments']
    if not isinstance(items, list) or len(items) > 32:
        raise OpenStackDiscoveryHeld('Volume attachments exceed their bounded shape')
    identities, bindings = set(), []
    for item in items:
        if not isinstance(item, Mapping):
            raise OpenStackDiscoveryHeld('Invalid volume attachment')
        attachment_id = _id(item.get('attachment_id'), 'attachment')
        if attachment_id in identities:
            raise OpenStackDiscoveryHeld('Duplicate volume attachment identity')
        identities.add(attachment_id)
        if _id(item.get('volume_id'), 'attachment volume') != volume_id:
            raise OpenStackDiscoveryHeld('Attachment refers to a different volume')
        binding = {'attachmentId': attachment_id, 'volumeId': volume_id,
                   'serverId': _id(item.get('server_id'), 'attachment server')}
        # The guest device label is neither a host path nor an ordering contract.
        # Null/missing during attachment transitions is not an invented device.
        if 'device' in item:
            device = item['device']
            if device is not None and (not isinstance(device, str)
                    or not 1 <= len(device) <= 128
                    or any(not 32 <= ord(c) <= 126 for c in device)):
                raise OpenStackDiscoveryHeld('Invalid native guest device label')
            binding['device'] = device
        bindings.append(binding)
    try:
        return DiscoveryFact.known('volumeAttachments',
                                   sorted(bindings, key=lambda item: item['attachmentId']))
    except ValueError as exc:
        raise OpenStackDiscoveryHeld('Volume attachment fact exceeds the evidence bound') from exc



def _bounded_image_integer(row: Mapping[str, object], key: str, name: str, *, scale: int = 1) -> DiscoveryFact:
    if key not in row:
        return DiscoveryFact.unknown(name, 'NOT_RETURNED')
    value = row[key]
    if value is None:
        return DiscoveryFact.known(name, None)
    if type(value) is not int or not 0 <= value <= (2**63 - 1) // scale:
        raise OpenStackDiscoveryHeld(f'Image {name} exceeds its typed bounds')
    return DiscoveryFact.known(name, value * scale)


def _image_hash_facts(row: Mapping[str, object]) -> tuple[DiscoveryFact, DiscoveryFact]:
    present = ('os_hash_algo' in row, 'os_hash_value' in row)
    if present == (False, False):
        return (DiscoveryFact.unknown('hashAlgorithm', 'NOT_RETURNED'),
                DiscoveryFact.unknown('hashValue', 'NOT_RETURNED'))
    if present != (True, True):
        raise OpenStackDiscoveryHeld('Image secure hash fields are incomplete')
    algorithm, value = row['os_hash_algo'], row['os_hash_value']
    if algorithm is None and value is None:
        return DiscoveryFact.known('hashAlgorithm', None), DiscoveryFact.known('hashValue', None)
    if (not isinstance(algorithm, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,31}', algorithm)
            or not isinstance(value, str) or not 32 <= len(value) <= 256
            or re.fullmatch(r'[0-9a-f]+', value) is None):
        raise OpenStackDiscoveryHeld('Image secure hash fields have an invalid shape')
    return DiscoveryFact.known('hashAlgorithm', algorithm), DiscoveryFact.known('hashValue', value)



def _image_property(row: Mapping[str, object], key: str, name: str,
                    *, allowed: frozenset[str] | None = None) -> DiscoveryFact:
    """Retain one Glance custom property exactly as the v2 API returns it.

    Glance additional image properties are strings.  We validate bounded printable
    text and, where Nova documents a closed vocabulary, reject an unexpected value
    rather than coercing it into a compatibility claim.
    """
    if key not in row:
        return DiscoveryFact.unknown(name, 'NOT_RETURNED')
    value = row[key]
    if (not isinstance(value, str) or not 1 <= len(value) <= 128
            or any(not 32 <= ord(char) <= 126 for char in value)):
        raise OpenStackDiscoveryHeld(f'Image {name} has an invalid custom-property value')
    if allowed is not None and value not in allowed:
        raise OpenStackDiscoveryHeld(f'Image {name} is outside the documented vocabulary')
    return DiscoveryFact.known(name, value)

def _image(scope: PlanScope, row: Mapping[str, object]) -> DiscoveryObject:
    """Retain bounded Glance metadata for a VM-referenced image only.

    Image ownership/visibility is observed rather than constrained to the workload
    project because public/shared images can legitimately be referenced. Metadata is
    not interpreted as guest-driver, boot, key or migration compatibility.
    """
    native_id = _id(row.get('id'), 'image')
    facts = (
        _fact(row, 'name', 'name', str, nullable=True),
        _fact(row, 'status', 'status', str),
        _fact(row, 'disk_format', 'diskFormat', str, nullable=True),
        _fact(row, 'container_format', 'containerFormat', str, nullable=True),
        _bounded_image_integer(row, 'size', 'sizeBytes'),
        _bounded_image_integer(row, 'virtual_size', 'virtualSizeBytes'),
        _bounded_image_integer(row, 'min_disk', 'minDiskBytes', scale=1024**3),
        _bounded_image_integer(row, 'min_ram', 'minRamBytes', scale=1024**2),
        _fact(row, 'visibility', 'visibility', str),
        _fact(row, 'owner', 'ownerId', str, nullable=True),
        _fact(row, 'protected', 'protected', bool),
        _fact(row, 'os_hidden', 'hidden', bool),
        *_image_hash_facts(row),
        _fact(row, 'architecture', 'architecture', str, nullable=True),
        _fact(row, 'os_distro', 'osDistro', str, nullable=True),
        _fact(row, 'hw_machine_type', 'hwMachineType', str, nullable=True),
        _fact(row, 'hw_firmware_type', 'hwFirmwareType', str, nullable=True),
        _fact(row, 'hw_disk_bus', 'hwDiskBus', str, nullable=True),
        _image_property(row, 'hw_vif_model', 'hwVifModel'),
        _image_property(row, 'hw_scsi_model', 'hwScsiModel',
                        allowed=frozenset({'virtio-scsi'})),
        _image_property(row, 'hw_qemu_guest_agent', 'hwQemuGuestAgent',
                        allowed=frozenset({'yes', 'no'})),
        _image_property(row, 'hw_vif_multiqueue_enabled', 'hwVifMultiqueueEnabled',
                        allowed=frozenset({'true', 'false'})),
        _image_property(row, 'os_secure_boot', 'osSecureBoot',
                        allowed=frozenset({'required', 'disabled', 'optional'})),
    )
    if 'owner' in row and row['owner'] is not None:
        _id(row['owner'], 'image owner')
    return DiscoveryObject(NativeIdentity(scope.endpoint_id, scope.native_scope_id,
                           'openstack', 'image', native_id), facts)


def _object(scope: PlanScope, kind: str, row: Mapping[str, object]) -> DiscoveryObject:
    native_id = _id(row.get('id'), kind)
    if kind == 'vm':
        _project(row, scope.native_scope_id, ('tenant_id', 'project_id'))
        facts = (_fact(row, 'name', 'name', str),
                 _fact(row, 'status', 'status', str),
                 _fact(row,'locked','locked',bool),
                 _fact(row,'OS-EXT-STS:vm_state','nativeVmState',str),
                 _fact(row,'OS-EXT-STS:task_state','nativeTaskState',str,nullable=True),
                 _fact(row,'OS-EXT-STS:power_state','nativePowerState',int),
                 _fact(row,'OS-EXT-AZ:availability_zone','availabilityZone',str)) + _flavor_facts(row) + _server_storage_facts(row)
        if 'OS-EXT-STS:power_state' in row and row['OS-EXT-STS:power_state'] not in (0,1,3,4,6,7):
            raise OpenStackDiscoveryHeld('Native power state is outside the selected API vocabulary')
    elif kind == 'volume':
        _project(row, scope.native_scope_id,
                 ('os-vol-tenant-attr:tenant_id', 'project_id'))
        facts = (_fact(row, 'name', 'name', str, nullable=True),
                 _fact(row, 'status', 'status', str),
                 _fact(row, 'size', 'size_gib', int),
                 _fact(row, 'encrypted', 'encrypted', bool),
                 _fact(row, 'multiattach', 'multiattach', bool),
                 _fact(row, 'volume_type', 'volume_type', str, nullable=True),
                 _volume_attachment_fact(row, native_id))
        if 'size' in row and not 0 <= row['size'] <= (2**63 - 1) // 1024**3:
            raise OpenStackDiscoveryHeld('Volume size exceeds the supported byte range')
    else:
        _project(row, scope.native_scope_id, ('project_id', 'tenant_id'))
        facts = (_fact(row, 'network_id', 'network_id', str),
                 _fact(row, 'device_id', 'device_id', str),
                 _fact(row, 'status', 'status', str),
                 _fact(row, 'port_security_enabled', 'port_security_enabled', bool),
                 _fact(row, 'binding:vnic_type', 'binding_vnic_type', str),
                 _fact(row, 'binding:vif_type', 'binding_vif_type', str),
                 _native_list(row, 'security_groups'),
                 _nullable_id(row, 'qos_policy_id'),
                 _pairs(row))
        if 'mac_address' in row:
            facts += (DiscoveryFact.known('mac_address', _mac(row['mac_address'])),)
        else:
            facts += (DiscoveryFact.unknown('mac_address', 'NOT_RETURNED'),)
        if 'fixed_ips' in row:
            if not isinstance(row['fixed_ips'], list) or len(row['fixed_ips']) > 32:
                raise OpenStackDiscoveryHeld('Port fixed IPs have invalid shape')
            # The API's address objects may carry extension fields. Retain only
            # the subnet and address, with no arbitrary metadata/user data.
            fixed_ips = []
            for item in row['fixed_ips']:
                if not isinstance(item, Mapping) or not isinstance(
                        item.get('ip_address'), str) or not isinstance(
                        item.get('subnet_id'), str):
                    raise OpenStackDiscoveryHeld('Port fixed IPs have invalid shape')
                address = {'ip_address': _address(item['ip_address']),
                           'subnet_id': _id(item['subnet_id'], 'subnet')}
                if address in fixed_ips:
                    raise OpenStackDiscoveryHeld('Duplicate native fixed address')
                fixed_ips.append(address)
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
    *, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
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
            or not callable(getattr(transport, 'get_json', None))
            or not callable(clock)):
        raise ValueError('Verified exact project, route and read campaign required')

    previous_time = campaign.issued_at

    def current_time() -> datetime:
        nonlocal previous_time
        at = clock()
        if (not _utc(at) or not previous_time <= at < campaign.expires_at):
            raise OpenStackDiscoveryHeld('Campaign expired or discovery clock regressed')
        previous_time = at
        return at

    def read(endpoint: str, path: str, params: Mapping[str, str]):
        # No first request, next page or quota read may begin after expiry.
        current_time()
        try:
            return _read(transport, endpoint, path, params)
        finally:
            # A late success/error is not publishable discovery evidence.
            current_time()

    current_time()
    pages: list[DiscoveryPage] = []
    seen: set[tuple[str, str]] = set()
    cursor: str | None = None
    object_count = 0
    has_unknown = False
    image_ids: set[str] = set()

    def append(objects: tuple[DiscoveryObject, ...], next_cursor: str | None,
               *, error: str | None = None, privilege: str | None = None) -> bool:
        nonlocal cursor, object_count, has_unknown
        at = current_time()
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
                response = read(endpoints.for_service(service), path, params)
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
                if kind == 'vm':
                    image_fact = next(f for f in obj.facts if f.name == 'imageId')
                    if image_fact.state == 'KNOWN' and image_fact.value() is not None:
                        image_ids.add(image_fact.value())
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
                index = _CORE_SERVICES.index(service)
                next_cursor = (f'openstack:{_CORE_SERVICES[index + 1]}:start'
                               if index < len(_CORE_SERVICES) - 1 else
                               'openstack:quota:compute')
            if not append(tuple(objects), next_cursor):
                return tuple(pages)
            if not more:
                break
            marker = last_id

    for index, service in enumerate(_CORE_SERVICES):
        endpoint = endpoints.for_service(service)
        path = (f'os-quota-sets/{endpoints.project_id}' if service != 'network'
                else f'quotas/{endpoints.project_id}')
        try:
            response = read(endpoint, path, {})
        except OpenStackDiscoveryHeld:
            raise
        except Exception as exc:
            errors, privileges = _error(service, exc)
            append((), None, error=errors[0],
                   privilege=privileges[0] if privileges else None)
            return tuple(pages)
        obj = _quota(campaign.scope, service, response)
        if index < len(_CORE_SERVICES) - 1:
            next_cursor = f'openstack:quota:{_CORE_SERVICES[index + 1]}'
        else:
            next_cursor = 'openstack:image:start' if image_ids else None
        if not append((obj,), next_cursor):
            return tuple(pages)

    ordered_images = sorted(image_ids)
    for index, image_id in enumerate(ordered_images):
        try:
            response = read(endpoints.for_service('image'), f'images/{image_id}', {})
        except OpenStackDiscoveryHeld:
            raise
        except Exception as exc:
            errors, privileges = _error('image', exc)
            append((), None, error=errors[0], privilege=privileges[0] if privileges else None)
            return tuple(pages)
        obj = _image(campaign.scope, response)
        if obj.identity.native_id != image_id:
            raise OpenStackDiscoveryHeld('Glance image response differs from the referenced image')
        next_cursor = (f'openstack:image:{ordered_images[index + 1]}'
                       if index < len(ordered_images) - 1 else None)
        if not append((obj,), next_cursor):
            return tuple(pages)
    return tuple(pages)
