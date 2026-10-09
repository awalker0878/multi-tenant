"""Independent read-only NSX effective VM membership and native service entries.

This is a scoped E3 evidence producer, NOT an E4 traffic-probe witness.
A separate commissioned origin and credential must be enrolled: the E2
configuration collector must not be reused as the independent observer.
"""
import re
from collections.abc import Callable
from typing import Any

from inventory_worker.infrastructure.native import CollectionFailure, exchange, secret
from inventory_worker.infrastructure.profile_digest import fingerprint

ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
MAX_OBJECTS = 16
MAX_SERVICE_PORTS = 256


def _rows(stream: dict[str, Any], url: str, credential: str,
          before_request: Callable[[], None]) -> list[dict[str, Any]]:
    before_request()
    result = exchange(stream, url + "?page_size=100",
                      {"Authorization": "Basic " + credential})
    if (not isinstance(result, dict) or result.get("cursor")
            or not isinstance(result.get("results"), list)
            or len(result["results"]) > 100
            or any(not isinstance(v, dict) for v in result["results"])):
        raise CollectionFailure("incomplete_effective_security_api")
    return result["results"]


def _ports(values: Any) -> list[int]:
    if not isinstance(values, list) or len(values) > 15:
        raise CollectionFailure("unsupported_native_service_ports")
    ports: set[int] = set()
    for token in values:
        if not isinstance(token, str):
            raise CollectionFailure("unsupported_native_service_ports")
        parts = token.split("-")
        if not 1 <= len(parts) <= 2 or any(not x.isascii() or not x.isdigit()
                                            for x in parts):
            raise CollectionFailure("unsupported_native_service_ports")
        low, high = int(parts[0]), int(parts[-1])
        if not 0 <= low <= high <= 65535 or high-low > MAX_SERVICE_PORTS:
            raise CollectionFailure("unsupported_native_service_ports")
        ports.update(range(low, high+1))
        if len(ports) > MAX_SERVICE_PORTS:
            raise CollectionFailure("unsupported_native_service_ports")
    return sorted(ports)


def collect(
    stream: dict[str, Any], domain: str,
    group_ids: list[str], service_ids: list[str],
    before_request: Callable[[], None],
) -> dict[str, Any]:
    if (stream.get("kind") != "nsx_effective_observer"
            or stream.get("domain_id") != domain
            or not isinstance(domain, str) or not ID.fullmatch(domain)
            or stream.get("separate_observer_credential_verified") is not True
            or stream.get("native_api_qualified") is not True
            or any(not isinstance(items, list) or len(items) > MAX_OBJECTS
                   or len(items) != len(set(items))
                   or any(not isinstance(s, str) or not ID.fullmatch(s)
                          for s in items)
                   for items in (group_ids, service_ids))):
        raise CollectionFailure("independent_native_observer_not_commissioned")
    credential = secret(stream["credential_file"])
    root = "/policy/api/v1/infra/"
    groups: dict[str, Any] = {}
    services: dict[str, Any] = {}
    for gid in group_ids:
        rows = _rows(
            stream, root + "domains/" + domain + "/groups/" + gid +
            "/members/virtual-machines", credential, before_request,
        )
        member_ids = []
        for item in rows:
            identity = item.get("external_id")
            if not isinstance(identity, str) or not identity or identity in member_ids:
                raise CollectionFailure("nsx_vm_membership_identity_unresolved")
            member_ids.append(identity)
        groups["/infra/domains/" + domain + "/groups/" + gid] = {
            "resolution": "effective_native_members", "complete": True,
            "members": sorted(member_ids), "native_revision": fingerprint(rows),
        }
    for sid in service_ids:
        entries = _rows(
            stream, root + "services/" + sid + "/service-entries",
            credential, before_request,
        )
        if len(entries) != 1:
            # Mixed protocols and nested service references cannot be represented
            # by one logical-port service; the E4 resolver must use a proven
            # set-expansion adapter instead of quietly discarding entries.
            raise CollectionFailure("nsx_nested_or_multiple_services_unqualified")
        entry = entries[0]
        if (entry.get("resource_type") != "L4PortSetServiceEntry"
                or entry.get("l4_protocol") not in ("TCP", "UDP")):
            raise CollectionFailure("nsx_service_type_unqualified")
        services["/infra/services/" + sid] = {
            "resolution": "native_expanded", "complete": True,
            "protocol": entry["l4_protocol"].lower(),
            "ports": _ports(entry.get("destination_ports")),
            "native_revision": fingerprint(entries),
        }
    return {
        "groups": groups, "services": services,
        "source": "independent_native_observer",
        "native_write_authorized": False,
        "qualification_level": "E3_observation_only",
        "raw_snapshot_sha256": fingerprint({"groups": groups, "services": services}),
    }
