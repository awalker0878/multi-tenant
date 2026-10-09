"""Independent read-only NSX effective VM membership and native service entries.

This is a scoped E3 evidence producer, NOT an E4 traffic-probe witness.
A separate commissioned origin and credential must be enrolled: the E2
configuration collector must not be reused as the independent observer.
"""
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from inventory_worker.infrastructure.native import CollectionFailure, exchange, secret
from inventory_worker.infrastructure.profile_digest import fingerprint

ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
MAX_OBJECTS = 16
MAX_SERVICE_PORTS = 256


def _rows(stream: dict[str, Any], url: str, credential: str,
          before_request: Callable[[], None], *, members: bool = False) -> list[dict[str, Any]]:
    before_request()
    suffix = "?page_size=100"
    if members:
        suffix += "&enforcement_point_path=" + quote(
            stream["enforcement_point_path"], safe=""
        )
    result = exchange(stream, url + suffix,
                      {"Authorization": "Basic " + credential})
    if (not isinstance(result, dict) or result.get("cursor")
            or not isinstance(result.get("results"), list)
            or (type(result.get("result_count")) is int
                and result["result_count"] != len(result["results"]))
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
            or stream.get("group_effective_member_types_verified") is not True
            or not isinstance(stream.get("group_effective_member_types"), dict)
            or stream.get("enforcement_point_qualified") is not True
            or not isinstance(stream.get("enforcement_point_path"), str)
            or not stream["enforcement_point_path"].startswith("/infra/sites/")
            or "/enforcement-points/" not in stream["enforcement_point_path"]
            or "?" in stream["enforcement_point_path"]
            or ".." in stream["enforcement_point_path"]
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
        # This API returns an empty VM list for groups whose realized
        # membership is IPs, VIFs, ports or segments. A zero result is NOT
        # proof that those groups are empty or irrelevant.
        kinds = stream["group_effective_member_types"].get(gid)
        if kinds != ["VirtualMachine"]:
            raise CollectionFailure("nsx_effective_group_member_types_unqualified")
        rows = _rows(
            stream, root + "domains/" + domain + "/groups/" + gid +
            "/members/virtual-machines", credential, before_request,
            members=True,
        )
        member_ids = []
        for item in rows:
            # NSX realized-VM records expose compute_ids, not necessarily
            # a top-level external_id. Only accept an unambiguous externalId
            # native identity from the independently realized observation.
            compute_ids = item.get("compute_ids")
            identifiers = (
                [part.partition(":")[2] for part in compute_ids
                 if isinstance(part, str) and part.startswith("externalId:")]
                if isinstance(compute_ids, list) else []
            )
            if item.get("external_id"):
                identifiers.append(item["external_id"])
            identifiers = sorted(set(identifiers))
            if (item.get("state") not in (None, "REALIZED")
                    or len(identifiers) != 1
                    or not identifiers[0]
                    or identifiers[0] in member_ids):
                raise CollectionFailure("nsx_vm_membership_identity_unresolved")
            member_ids.append(identifiers[0])
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
