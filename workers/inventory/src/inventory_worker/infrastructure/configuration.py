"Read-only OpenStack discovery; return bounded allowlisted fields, never response secrets."

import json
import re
import time
from typing import Any
from urllib.parse import urlencode

from inventory_worker.infrastructure.native import CollectionFailure, exchange, secret

# Paths are relative to separately trusted service bases, never to catalog-returned URLs.
QUERIES: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "compute_versions": ("/", "versions", ("status", "version", "min_version")),
    "volume_versions": ("/", "versions", ("status", "version", "min_version")),
    "image_versions": ("/", "versions", ("status",)),
    "placement_versions": ("/", "versions", ("status", "max_version", "min_version")),
    "compute_flavors": (
        "/flavors/detail?limit=100",
        "flavors",
        ("vcpus", "ram", "disk", "swap", "OS-FLV-EXT-DATA:ephemeral"),
    ),
    "compute_zones": ("/os-availability-zone", "availabilityZoneInfo", ("zoneState",)),
    "network_extensions": ("/extensions", "extensions", ("updated",)),
    "network_subnets": (
        "/subnets",
        "subnets",
        (
            "volume_backend_name",
            "replication_enabled",
            "multiattach",
            "capabilities:thin_provisioning_support",
            "capabilities:thick_provisioning_support",
            "network_id",
            "cidr",
            "ip_version",
            "gateway_ip",
            "enable_dhcp",
            "dns_nameservers",
            "allocation_pools",
        ),
    ),
    "network_ports": (
        "/ports",
        "ports",
        (
            "network_id",
            "fixed_ips",
            "security_groups",
            "port_security_enabled",
            "binding:vnic_type",
            "binding:vif_type",
            "qos_policy_id",
        ),
    ),
    "network_routers": (
        "/routers",
        "routers",
        ("admin_state_up", "external_gateway_info", "routes"),
    ),
    "network_security_groups": (
        "/security-groups",
        "security_groups",
        ("security_group_rules", "stateful"),
    ),
    "network_trunks": ("/trunks", "trunks", ("port_id", "sub_ports", "status")),
    "network_qos": ("/qos/policies", "policies", ("rules", "is_default")),
    "volume_types": ("/types?limit=100", "volume_types", ("is_public",)),
    "image_import": ("/info/import", "import-methods", ()),
    "image_stores": ("/info/stores", "stores", ("default",)),
    "identity_catalog": ("/auth/catalog", "catalog", ()),
    "placement_traits": ("/traits", "traits", ()),
}
# Nested projections prevent metadata/extensions from smuggling arbitrary provider fields.
NESTED = {
    "network_id",
    "enable_snat",
    "external_fixed_ips",
    "subnet_id",
    "ip_address",
    "destination",
    "nexthop",
    "id",
    "direction",
    "ethertype",
    "protocol",
    "port_range_min",
    "port_range_max",
    "remote_ip_prefix",
    "remote_group_id",
    "remote_address_group_id",
    "port_id",
    "segmentation_type",
    "segmentation_id",
    "type",
    "max_kbps",
    "max_burst_kbps",
    "dscp_mark",
    "min_kbps",
    "available",
    "start",
    "end",
    "security_group_id",
    "project_id",
    "tenant_id",
}


def safe_value(value: Any, depth: int = 0) -> Any:
    if depth > 5:
        raise CollectionFailure("invalid_response")
    if isinstance(value, dict):
        return {k: safe_value(v, depth + 1) for k, v in value.items() if k in NESTED}
    if isinstance(value, list):
        if len(value) > 100:
            raise CollectionFailure("invalid_response")
        return [safe_value(v, depth + 1) for v in value]
    if value is None or type(value) in {str, int, float, bool}:
        return value
    raise CollectionFailure("invalid_response")


def normalized(query: str, response: Any, scope: str) -> list[dict[str, Any]]:
    if not isinstance(response, dict):
        raise CollectionFailure("invalid_response")
    _, key, fields = QUERIES[query]
    rows = response.get(key)
    if query.endswith("_versions"):
        rows = response.get("versions", [response["version"]] if "version" in response else None)
        if isinstance(rows, dict):
            rows = rows.get("values")
    if query == "image_import" and isinstance(rows, dict):
        rows = rows.get("value")
    if not isinstance(rows, list) or len(rows) > 100:
        raise CollectionFailure("invalid_response")
    # Never treat a truncated configuration list as complete or follow returned links.
    links = response.get(key + "_links", response.get("links", []))
    if not isinstance(links, list) or any(
        not isinstance(x, dict) or x.get("rel") == "next" for x in links
    ):
        raise CollectionFailure("invalid_response")
    if len(rows) == 100:
        raise CollectionFailure("invalid_response")
    items = []
    for row in rows:
        if isinstance(row, str) and query in {"image_import", "placement_traits"}:
            row = {"id": row}
        if not isinstance(row, dict):
            raise CollectionFailure("invalid_response")
        if query.startswith("network_") and query != "network_extensions":
            if row.get("project_id", row.get("tenant_id")) != scope:
                raise CollectionFailure("permission_denied")
        identity = row.get(
            "alias"
            if query == "network_extensions"
            else "type"
            if query == "identity_catalog"
            else "zoneName"
            if query == "compute_zones"
            else "id"
        )
        name = row.get("name") or identity
        if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", identity):
            raise CollectionFailure("invalid_response")
        if not isinstance(name, str) or len(name) > 255 or any(ord(c) < 32 for c in name):
            raise CollectionFailure("invalid_response")
        attrs = []
        for field in fields:
            if field in row:
                value = json.dumps(
                    safe_value(row[field]), sort_keys=True, separators=(",", ":"), allow_nan=False
                )
                if len(value) > 2000:
                    raise CollectionFailure("invalid_response")
                attrs.append({"key": field, "value": value})
        items.append({"id": identity, "name": name, "attributes": attrs})
    # A catalog can contain multiple registrations for one service type.
    if query == "identity_catalog":
        items = list({item["id"]: item for item in items}.values())
    if len({item["id"] for item in items}) != len(items):
        raise CollectionFailure("invalid_response")
    return sorted(items, key=lambda item: item["id"])


def collect_configuration(policy: dict[str, Any], stream: dict[str, Any]) -> dict[str, Any]:
    query = stream["kind"][7:]
    if query not in QUERIES or policy["platform"] != "openstack":
        raise CollectionFailure("unsupported_api")
    if stream["api_version"] != "discovery-v1":
        raise CollectionFailure("unsupported_api")
    route = QUERIES[query][0]
    if query.startswith("network_") and query != "network_extensions":
        route += "?" + urlencode({"project_id": policy["native_scope"], "limit": "100"})
    try:
        headers = {"X-Auth-Token": secret(stream["credential_file"])}
        result = exchange(stream, route, headers, version_discovery=query.endswith("_versions"))
        fact = {
            "query": query,
            "status": "observed",
            "items": normalized(query, result, policy["native_scope"]),
        }
        if len(json.dumps(fact).encode()) > 131072:
            raise CollectionFailure("invalid_response")
    except CollectionFailure as error:
        if error.reason == "unsafe_destination":
            raise
        fact = {"query": query, "status": error.reason, "items": []}
    return {
        "observations": [],
        "next_cursor": None,
        "terminal": True,
        "coverage": bool(policy.get("coverage_reference")),
        "collected_at": time.time(),
        "error": None,
        "configuration": fact,
    }
