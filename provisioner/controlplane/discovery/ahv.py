"""Bounded Prism Central VMM v4.0 AHV VM enumeration, with no native writes.

The injected transport must already be pinned by the site worker to the
campaign's endpoint, tenant and native cluster, a read-only credential and an
installed API profile. This collector never follows a server-provided URL.
The campaign value alone is not proof of admission. A trusted worker must
verify its issuer and current epoch before invoking this code.

Nutanix VMM v4.0 documents GET /vmm/v4.0/ahv/config/vms, $page (zero based),
$limit (1..100), cluster/extId filtering, and the extId/cluster/disks/nics
fields. The REST service is mounted below /api on Prism Central. The metadata
includes totalAvailableResults and may include pagination links. Keep an
independent native qualification gate for the actual installed PC/AOS tuple.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Mapping, Protocol
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

from provisioner.controlplane.authority.model import PlanScope

from .model import (DiscoveryCampaignAuthorization, DiscoveryFact,
                    DiscoveryObject, DiscoveryPage, NativeIdentity,
                    assemble_discovery_result)


API_VERSION = 'v4.0'
COLLECTOR_ID = 'nutanix-ahv-v4.0'
VM_PATH = '/api/vmm/v4.0/ahv/config/vms'
_MAX_NATIVE_PAGE = 100


class AhvGetTransport(Protocol):
    """Site-owned transport: an exact-scope GET, no arbitrary URL input.

    Implementations must enforce TLS peer verification, timeouts, response
    byte limits, an installed Prism Central endpoint allowlist and a native
    read-only role. ``api_version`` is a verified installed API profile, not
    a value copied from an untrusted collection request.
    """

    scope: PlanScope
    api_version: str
    read_only: bool

    def get(self, path: str, *, params: Mapping[str, str | int]) -> tuple[int, Mapping]: ...


def _uuid(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError):
        return None
    return str(parsed) if str(parsed) == value.lower() else None


def _positive(value: object) -> int | None:
    return value if type(value) is int and value > 0 else None


def _ref_id(value: object) -> str | None:
    return _uuid(value.get('extId')) if isinstance(value, dict) else None


def _field(name: str, raw: object, *, valid: Callable[[object], bool]) -> DiscoveryFact:
    if raw is None:
        return DiscoveryFact.unknown(name, 'NOT_RETURNED')
    return (DiscoveryFact.known(name, raw) if valid(raw)
            else DiscoveryFact.unknown(name, 'COLLECTION_ERROR'))


def _disk_facts(raw: object) -> tuple[DiscoveryFact, DiscoveryFact]:
    if raw is None:
        return (DiscoveryFact.unknown('disks', 'NOT_RETURNED'),
                DiscoveryFact.unknown('diskCapacityBytes', 'NOT_RETURNED'))
    if not isinstance(raw, list) or len(raw) > 256:
        return (DiscoveryFact.unknown('disks', 'COLLECTION_ERROR'),
                DiscoveryFact.unknown('diskCapacityBytes', 'COLLECTION_ERROR'))
    disks: list[dict] = []
    ids: set[str] = set()
    total = 0
    missing_capacity = False
    for disk in raw:
        if not isinstance(disk, dict) or not (disk_id := _uuid(disk.get('extId'))):
            return (DiscoveryFact.unknown('disks', 'COLLECTION_ERROR'),
                    DiscoveryFact.unknown('diskCapacityBytes', 'COLLECTION_ERROR'))
        if disk_id in ids:
            return (DiscoveryFact.unknown('disks', 'COLLECTION_ERROR'),
                    DiscoveryFact.unknown('diskCapacityBytes', 'COLLECTION_ERROR'))
        ids.add(disk_id)
        # backingInfo is a tagged VmDisk or ADSF volume-group union. Only the
        # VmDisk member has a diskSizeBytes field; a volume group is unknown.
        vm_disk = disk.get('backingInfo')
        size = vm_disk.get('diskSizeBytes') if isinstance(vm_disk, dict) else None
        if _positive(size) is None:
            missing_capacity = True
            size = None
        else:
            total += size
        container = (vm_disk.get('storageContainer')
                     if isinstance(vm_disk, dict) else None)
        disks.append({'extId': disk_id, 'diskSizeBytes': size,
                      'storageContainerExtId': _ref_id(container)})
    return (DiscoveryFact.known('disks', disks),
            DiscoveryFact.unknown('diskCapacityBytes', 'NOT_RETURNED')
            if missing_capacity else DiscoveryFact.known('diskCapacityBytes', total))


def _nic_facts(raw: object) -> tuple[DiscoveryFact, DiscoveryFact]:
    if raw is None:
        return (DiscoveryFact.unknown('nics', 'NOT_RETURNED'),
                DiscoveryFact.unknown('networkBindings', 'NOT_RETURNED'))
    if not isinstance(raw, list) or len(raw) > 256:
        return (DiscoveryFact.unknown('nics', 'COLLECTION_ERROR'),
                DiscoveryFact.unknown('networkBindings', 'COLLECTION_ERROR'))
    nics: list[dict] = []
    ids: set[str] = set()
    missing_network = False
    for nic in raw:
        if not isinstance(nic, dict) or not (nic_id := _uuid(nic.get('extId'))):
            return (DiscoveryFact.unknown('nics', 'COLLECTION_ERROR'),
                    DiscoveryFact.unknown('networkBindings', 'COLLECTION_ERROR'))
        if nic_id in ids:
            return (DiscoveryFact.unknown('nics', 'COLLECTION_ERROR'),
                    DiscoveryFact.unknown('networkBindings', 'COLLECTION_ERROR'))
        ids.add(nic_id)
        network = nic.get('networkInfo')
        subnet = network.get('subnet') if isinstance(network, dict) else None
        subnet_id = _ref_id(subnet)
        if subnet_id is None:
            missing_network = True
        nics.append({'extId': nic_id, 'subnetExtId': subnet_id})
    return (DiscoveryFact.known('nics', nics),
            DiscoveryFact.unknown('networkBindings', 'NOT_RETURNED')
            if missing_network else DiscoveryFact.known('networkBindings', nics))


def _vm(value: object, scope: PlanScope) -> DiscoveryObject:
    if not isinstance(value, dict) or not (vm_id := _uuid(value.get('extId'))):
        raise ValueError('VM_ID_UNAVAILABLE')
    if _ref_id(value.get('cluster')) != scope.native_scope_id:
        raise ValueError('VM_OUTSIDE_NATIVE_SCOPE')
    disks, capacity = _disk_facts(value.get('disks'))
    nics, networks = _nic_facts(value.get('nics'))
    facts = (
        _field('displayName', value.get('name'),
               valid=lambda v: isinstance(v, str) and 0 < len(v) <= 80),
        _field('powerState', value.get('powerState'),
               valid=lambda v: isinstance(v, str) and 0 < len(v) <= 40),
        _field('numSockets', value.get('numSockets'), valid=lambda v: _positive(v) is not None),
        _field('numCoresPerSocket', value.get('numCoresPerSocket'),
               valid=lambda v: _positive(v) is not None),
        _field('memorySizeBytes', value.get('memorySizeBytes'),
               valid=lambda v: _positive(v) is not None),
        DiscoveryFact.known('clusterExtId', scope.native_scope_id),
        disks, capacity, nics, networks,
    )
    return DiscoveryObject(NativeIdentity(scope.endpoint_id, scope.native_scope_id,
                                          'nutanix', 'vm', vm_id), facts)


def _next_page(metadata: dict, expected: int, limit: int, filter_value: str) -> bool:
    links = metadata.get('links', [])
    if not isinstance(links, list):
        return False
    next_links = [link for link in links
                  if isinstance(link, dict) and link.get('rel') == 'next']
    if not next_links:
        return True
    if len(next_links) != 1 or not isinstance(next_links[0].get('href'), str):
        return False
    # The link is checked only for consistency. Never follow server URLs.
    href = next_links[0]['href']
    if len(href) > 4096:
        return False
    try:
        parts = urlsplit(href)
        query = parse_qs(parts.query, strict_parsing=True)
    except ValueError:
        return False
    if parts.path != VM_PATH or parts.fragment:
        return False
    return (set(query) == {'$page', '$limit', '$filter'}
            and query.get('$page') == [str(expected)]
            and query.get('$limit') == [str(limit)]
            and query.get('$filter') == [filter_value])


def collect_ahv_vms(
    campaign: DiscoveryCampaignAuthorization, transport: AhvGetTransport,
    *, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> tuple[DiscoveryPage, ...]:
    """Enumerate one installed cluster, returning incomplete terminal evidence on gaps.

    The caller must separately verify campaign issuance, worker/credential
    binding and privilege coverage. An API error or changed page set cannot
    be mistaken for an empty complete inventory. This function does no I/O
    other than invoking the supplied GET transport.
    """
    if (not isinstance(campaign, DiscoveryCampaignAuthorization)
            or campaign.scope.platform_family != 'nutanix'
            or campaign.collector_id != COLLECTOR_ID
            or 'vm' not in campaign.allowed_kinds
            or _uuid(campaign.scope.native_scope_id) != campaign.scope.native_scope_id
            or getattr(transport, 'scope', None) != campaign.scope
            or getattr(transport, 'api_version', None) != API_VERSION
            or getattr(transport, 'read_only', None) is not True
            or not callable(getattr(transport, 'get', None))):
        raise ValueError('Unsupported AHV API version or unbound read-only native scope')
    limit = min(campaign.max_page_size, _MAX_NATIVE_PAGE, campaign.max_objects)
    filter_value = f"cluster/extId eq '{campaign.scope.native_scope_id}'"
    pages: list[DiscoveryPage] = []
    identities: set[tuple[str, str, str, str, str]] = set()
    observed_total: int | None = None
    count = 0
    missing_fields = False

    def terminal(error: str | None = None, *, privilege: str | None = None) -> None:
        timestamp = clock()
        if (timestamp.tzinfo is None or timestamp.utcoffset() is None
                or not campaign.issued_at <= timestamp < campaign.expires_at):
            raise ValueError('Expired or invalid campaign cannot issue a page')
        page = len(pages) + 1
        cursor = str(page - 1) if page > 1 else None
        pages.append(DiscoveryPage(
            campaign.campaign_id, campaign.scope, page, cursor, None, timestamp,
            (), 'UNKNOWN' if error else 'PARTIAL',
            (error,) if error else (), (privilege,) if privilege else ()))

    for page_no in range(campaign.max_pages):
        timestamp = clock()
        if (timestamp.tzinfo is None or timestamp.utcoffset() is None
                or not campaign.issued_at <= timestamp < campaign.expires_at):
            terminal('CAMPAIGN_EXPIRED')
            break
        try:
            status, response = transport.get(VM_PATH, params={
                '$page': page_no, '$limit': limit, '$filter': filter_value})
        except Exception:
            terminal('NATIVE_READ_ERROR')
            break
        if status in (401, 403):
            terminal('VM_LIST_PERMISSION_DENIED', privilege='VM_LIST_READ')
            break
        if status != 200 or not isinstance(response, dict):
            terminal('NATIVE_READ_ERROR')
            break
        if response.get('$objectType') not in (None, 'vmm.v4.ahv.config.ListVmsApiResponse'):
            terminal('API_RESPONSE_VERSION_MISMATCH')
            break
        metadata, data = response.get('metadata'), response.get('data')
        if (not isinstance(metadata, dict) or not isinstance(data, list)
                or len(data) > limit
                or not isinstance(metadata.get('links', []), list)):
            terminal('MALFORMED_VM_PAGE')
            break
        messages = metadata.get('messages', [])
        if (not isinstance(messages, list)
                or any(not isinstance(message, dict) or
                       message.get('severity') not in ('INFO', 'INFORMATION')
                       for message in messages)):
            terminal('NATIVE_PAGE_WARNING_OR_ERROR')
            break
        total = metadata.get('totalAvailableResults')
        if type(total) is not int or not 0 <= total <= campaign.max_objects:
            terminal('INVALID_TOTAL_OR_OBJECT_BUDGET')
            break
        if observed_total is None:
            observed_total = total
        elif observed_total != total:
            terminal('INCONSISTENT_TOTAL')
            break
        if not data and count < total:
            terminal('TRUNCATED_VM_PAGE')
            break
        objects = []
        try:
            for row in data:
                obj = _vm(row, campaign.scope)
                if obj.identity.key() in identities:
                    raise ValueError('DUPLICATE_NATIVE_ID')
                identities.add(obj.identity.key())
                objects.append(obj)
                missing_fields |= any(f.state == 'UNKNOWN' for f in obj.facts)
        except ValueError as exc:
            terminal(str(exc) if str(exc) in (
                'VM_ID_UNAVAILABLE', 'VM_OUTSIDE_NATIVE_SCOPE', 'DUPLICATE_NATIVE_ID')
                else 'MALFORMED_VM_PAGE')
            break
        count += len(objects)
        if count > total or count > campaign.max_objects:
            terminal('INCONSISTENT_TOTAL')
            break
        more = count < total
        if more and not _next_page(metadata, page_no + 1, limit, filter_value):
            terminal('REPEATED_OR_CROSS_SCOPE_CURSOR')
            break
        if not more and any(isinstance(link, dict) and link.get('rel') == 'next'
                            for link in metadata.get('links', [])):
            terminal('INCONSISTENT_CURSOR')
            break
        collected = clock()
        if not campaign.issued_at <= collected < campaign.expires_at:
            terminal('CAMPAIGN_EXPIRED')
            break
        if more and page_no + 1 >= campaign.max_pages:
            pages.append(DiscoveryPage(
                campaign.campaign_id, campaign.scope, page_no + 1,
                None if page_no == 0 else str(page_no), None, collected,
                tuple(objects), 'UNKNOWN', ('PAGE_BUDGET_EXCEEDED',)))
            break
        pages.append(DiscoveryPage(
            campaign.campaign_id, campaign.scope, page_no + 1,
            None if page_no == 0 else str(page_no), str(page_no + 1) if more else None,
            collected, tuple(objects),
            None if more else ('PARTIAL' if missing_fields else 'COMPLETE')))
        if not more:
            break
    # Validate the emitted chain before it can be persisted or displayed. The
    # clock may cross expiry while assembling; use the terminal timestamp.
    assemble_discovery_result(campaign, tuple(pages), checked_at=pages[-1].collected_at)
    return tuple(pages)
