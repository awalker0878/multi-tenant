"API-observed configuration and explicitly attributed administrator interpretation."

from typing import Any

from inventory.domain.discovery import Rejected, canonical, shape, text

# Each optional stream is one fixed, budgeted GET. A missing stream stays unknown.
CONFIGURATION_QUERIES = (
    "compute_versions",
    "compute_flavors",
    "compute_zones",
    "network_extensions",
    "network_subnets",
    "network_ports",
    "network_routers",
    "network_security_groups",
    "network_trunks",
    "network_qos",
    "volume_versions",
    "volume_types",
    "image_versions",
    "image_import",
    "image_stores",
    "identity_catalog",
    "placement_versions",
    "placement_traits",
)
MANUAL_FIELDS = {
    "source_distribution": "Source distribution and package release (not exposed by standard APIs)",
    "target_distribution": "Target distribution and package release (not exposed by standard APIs)",
    "backend_release_reference": "Backend software release evidence reference",
    "support_entitlement_reference": "Support and entitlement evidence reference",
    "ownership_reference": "Application and integration owners reference",
    "network_mapping_reference": "Network, IPAM and DNS mapping reference",
    "guest_mapping_reference": "Guest image and driver conversion requirements reference",
    "service_mapping_reference": "Identity, monitoring and shared service mapping reference",
    "automation_reference": "Automation ownership and integration contract reference",
    "backup_reference": "Backup, restore and retention requirements reference",
    "activation_reference": "Activation and cutover approval reference",
    "retirement_reference": "Source retirement and rollback retention reference",
    "campaign_reference": "Approved native qualification campaign reference",
}
VERSIONS = [
    {
        "release": release,
        "name": name,
        "nova_max": maximum,
        "documentation": "reviewed" if release in {"2026.2", "2026.1"} else "baseline_listed",
        "native_qualification": "not_qualified",
        "source": "https://docs.openstack.org/nova/"
        + release
        + "/reference/api-microversion-history.html",
    }
    for release, name, maximum in (
        ("2026.2", "Hibiscus", "2.104"),
        ("2026.1", "Gazpacho", "2.103"),
        ("2025.2", "Flamingo", "2.100"),
        ("2025.1", "Epoxy", "2.100"),
    )
]
CAPABILITIES = [
    {"id": id_, "label": label, "query": query, "match": match, "meaning": meaning}
    for id_, label, query, match, meaning in (
        ("compute", "Compute flavors", "compute_flavors", "", "configured"),
        ("zones", "Availability zones", "compute_zones", "", "configured"),
        ("volumes", "Volume types", "volume_types", "", "configured"),
        ("subnets", "Subnets and address allocation", "network_subnets", "", "configured"),
        ("ports", "Ports and bindings", "network_ports", "", "configured"),
        ("routers", "Routing", "network_routers", "", "configured"),
        ("security_groups", "Security group policy", "network_security_groups", "", "configured"),
        ("trunks", "Trunk networks", "network_trunks", "", "configured"),
        ("qos", "Network quality of service", "network_qos", "", "configured"),
        (
            "port_security",
            "Port security extension",
            "network_extensions",
            "port-security",
            "advertised",
        ),
        (
            "provider_networks",
            "Provider network extension",
            "network_extensions",
            "provider",
            "advertised",
        ),
        ("image_import", "Image import methods", "image_import", "", "advertised"),
        ("image_stores", "Image stores", "image_stores", "", "configured"),
        ("placement", "Placement traits", "placement_traits", "", "advertised"),
        (
            "load_balancer",
            "Load balancing (Octavia)",
            "identity_catalog",
            "load-balancer",
            "advertised",
        ),
        ("dns", "DNS (Designate)", "identity_catalog", "dns", "advertised"),
        (
            "key_manager",
            "Key management (Barbican)",
            "identity_catalog",
            "key-manager",
            "advertised",
        ),
        (
            "shared_files",
            "Shared filesystems (Manila)",
            "identity_catalog",
            "sharev2",
            "advertised",
        ),
        (
            "object_store",
            "Object storage (Swift)",
            "identity_catalog",
            "object-store",
            "advertised",
        ),
        (
            "orchestration",
            "Orchestration (Heat)",
            "identity_catalog",
            "orchestration",
            "advertised",
        ),
    )
]


def configuration_fact(value: Any, query: str) -> dict[str, Any]:
    fact = shape(value, {"query", "status", "items"})
    if fact["query"] != query or query not in CONFIGURATION_QUERIES:
        raise Rejected("invalid_configuration_query")
    if fact["status"] not in {
        "observed",
        "permission_denied",
        "unsupported_api",
        "transport_unavailable",
        "throttled",
        "invalid_response",
    }:
        raise Rejected("invalid_configuration_status")
    if not isinstance(fact["items"], list) or len(fact["items"]) > 100:
        raise Rejected("configuration_bound")
    if fact["status"] != "observed" and fact["items"]:
        raise Rejected("invalid_configuration_status")
    seen = set()
    for item in fact["items"]:
        shape(item, {"id", "name", "attributes"})
        key = text(item["id"], 200)
        text(item["name"], 255)
        if key in seen:
            raise Rejected("duplicate_configuration_item")
        seen.add(key)
        if not isinstance(item["attributes"], list) or len(item["attributes"]) > 20:
            raise Rejected("configuration_bound")
        for attr in item["attributes"]:
            shape(attr, {"key", "value"})
            text(attr["key"], 80)
            text(attr["value"], 2000)
    if len(canonical(fact).encode()) > 131072:
        raise Rejected("configuration_bound")
    return fact


def manual_input(body: dict[str, Any]) -> None:
    shape(body, {"source_endpoint", "target_endpoint", "manual", "choices"})
    shape(body["manual"], set(), set(MANUAL_FIELDS))
    for value in body["manual"].values():
        text(value, 240)
    if not isinstance(body["choices"], list) or len(body["choices"]) != len(CAPABILITIES):
        raise Rejected("invalid_capability_choices")
    seen = set()
    for choice in body["choices"]:
        shape(choice, {"id", "required", "interpretation", "reason"})
        if choice["id"] not in {c["id"] for c in CAPABILITIES} or choice["id"] in seen:
            raise Rejected("invalid_capability_choices")
        seen.add(choice["id"])
        if type(choice["required"]) is not bool or choice["interpretation"] not in {
            "observed",
            "include",
            "exclude",
        }:
            raise Rejected("invalid_capability_choices")
        if choice["interpretation"] != "observed":
            text(choice["reason"], 240)
        elif choice["reason"] != "":
            raise Rejected("unexpected_override_reason")
