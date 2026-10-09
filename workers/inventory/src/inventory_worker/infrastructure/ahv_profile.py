"""Bounded Prism Central v4 destination discovery; absence is never qualification."""

from collections.abc import Callable
from typing import Any

from inventory_worker.infrastructure.native import CollectionFailure, exchange, secret
from inventory_worker.infrastructure.profile_digest import fingerprint

# Independently versioned namespaces. No SDK negotiation or fallback to legacy APIs.
VERSIONS = dict.fromkeys(("vmm", "prism", "clustermgmt", "networking", "microseg"), "v4.3")
PAGE_SIZE = 100
MAX_LIST_PAGES = 10
FIELDS = {
    "storage_containers": (
        "extId",
        "name",
        "clusterExtId",
        "isMarkedForRemoval",
        "isInternal",
        "maxCapacityBytes",
        "isEncrypted",
        "replicationFactor",
    ),
    "subnets": (
        "extId",
        "name",
        "subnetType",
        "clusterReference",
        "clusterReferenceList",
        "vpcReference",
        "projectExtId",
        "sharedWithProjects",
        "isExternal",
        "ipConfig",
    ),
    "vpcs": ("extId", "name", "projectExtId"),
    "categories": ("extId", "key", "value"),
    "policies": (
        "extId",
        "name",
        "state",
        "type",
        "projectExtId",
        "isSharedWithAllProjects",
        "scope",
        "scopeReferences",
        "vpcReferences",
        "securedGroups",
        "rules",
    ),
}


def collect_list(
    stream: dict[str, Any],
    route: str,
    max_pages: int,
    before_request: Callable[[], None],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Collect numbered pages within the enrolled budget; never follow response URLs.

    This is a bounded observation window, not a transactional native snapshot.
    Changed totals, repeated identities or short pages invalidate the whole profile.
    """
    rows: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    identities: set[str] = set()
    total: int | None = None
    for page in range(max_pages):
        before_request()
        document = exchange(
            stream,
            f"{route}?$limit={PAGE_SIZE}&$page={page}",
            {"X-Ntnx-Api-Key": secret(stream["credential_file"])},
        )
        if not isinstance(document, dict) or not isinstance(document.get("metadata"), dict):
            raise CollectionFailure("invalid_response")
        count = document["metadata"].get("totalAvailableResults")
        items = document.get("data")
        if (
            type(count) is not int
            or not 0 <= count <= max_pages * PAGE_SIZE
            or (total is not None and count != total)
            or not isinstance(items, list)
            or len(items) != min(PAGE_SIZE, count - page * PAGE_SIZE)
            or any(
                not isinstance(item, dict)
                or not isinstance(item.get("extId"), str)
                or not item["extId"]
                for item in items
            )
        ):
            raise CollectionFailure("invalid_response")
        total = count
        for item in items:
            if item["extId"] in identities:
                raise CollectionFailure("invalid_response")
            identities.add(item["extId"])
        rows.extend(items)
        documents.append(document)
        if len(rows) == total:
            return rows, documents
    raise CollectionFailure("invalid_response")


def collect_ahv(
    policy: dict[str, Any],
    stream: dict[str, Any],
    observed_at: int,
    before_request: Callable[[], None],
) -> dict[str, Any]:
    records: dict[str, Any] = {}
    routes = {
        "cluster": "/api/clustermgmt/v4.3/config/clusters/" + stream["cluster_id"],
        "prism_central": "/api/prism/v4.3/config/domain-managers/" + stream["prism_central_id"],
        "storage_containers": "/api/clustermgmt/v4.3/config/storage-containers",
        "subnets": "/api/networking/v4.3/config/subnets",
        "vpcs": "/api/networking/v4.3/config/vpcs",
        "categories": "/api/prism/v4.3/config/categories",
        "policies": "/api/microseg/v4.3/config/policies",
    }
    inventory: dict[str, list[dict[str, Any]]] = {}
    maximum = policy.get("max_pages", 1)
    if type(maximum) is not int or not 1 <= maximum <= 100:
        raise CollectionFailure("invalid_response")
    for key, path in routes.items():
        if key in FIELDS:
            inventory[key], records[key] = collect_list(
                stream, path, min(maximum, MAX_LIST_PAGES), before_request
            )
        else:
            before_request()
            records[key] = exchange(
                stream, path, {"X-Ntnx-Api-Key": secret(stream["credential_file"])}
            )
            if not isinstance(records[key], dict) or not isinstance(records[key].get("data"), dict):
                raise CollectionFailure("invalid_response")
    cluster, pc = (records[k].get("data", {}) for k in ("cluster", "prism_central"))
    if (
        cluster.get("extId") != stream["cluster_id"]
        or pc.get("extId") != stream["prism_central_id"]
    ):
        raise CollectionFailure("invalid_response")
    config, pc_config = cluster.get("config", {}), pc.get("config", {})
    if not isinstance(config, dict) or not isinstance(pc_config, dict):
        raise CollectionFailure("invalid_response")
    hypervisors = config.get("hypervisorTypes", [])
    if not isinstance(hypervisors, list) or any(not isinstance(v, str) for v in hypervisors):
        raise CollectionFailure("invalid_response")
    inventory["storage_containers"] = [
        r
        for r in inventory["storage_containers"]
        if r.get("clusterExtId") == stream["cluster_id"]
        and r.get("isMarkedForRemoval") is False
        and r.get("isInternal") is False
    ]
    # Project assignment is commissioned, not inferred from returned display names.
    for key in ("subnets", "vpcs", "policies"):
        inventory[key] = [
            r
            for r in inventory[key]
            if r.get("projectExtId") == policy["native_scope"]
            or r["extId"] in stream["shared_resource_ids"]
        ]
    # Prism's policy list may include native rule bodies; absence is UNKNOWN.
    # Never infer rules from policy names, ENFORCE state or category memberships.
    # Referenced service/address/category groups need independent resolution.
    for policy_row in inventory["policies"]:
        rules = policy_row.get("rules")
        if rules is None:
            continue
        if not isinstance(rules, list) or len(rules) > 512:
            raise CollectionFailure("invalid_response")
        seen_rule_ids: set[str] = set()
        for rule in rules:
            if (
                not isinstance(rule, dict)
                or not isinstance(rule.get("extId"), str)
                or not rule["extId"]
                or rule["extId"] in seen_rule_ids
                or not isinstance(rule.get("type"), str)
                or not isinstance(rule.get("spec"), dict)
            ):
                raise CollectionFailure("invalid_response")
            seen_rule_ids.add(rule["extId"])
    projected = {
        k: [{f: r.get(f) for f in fields} | {"native_sha256": fingerprint(r)} for r in inventory[k]]
        for k, fields in FIELDS.items()
    }
    installed = {
        "prism_central": pc_config.get("buildInfo", {}),
        "aos": config.get("buildInfo", {}),
        "cluster_software": config.get("clusterSoftwareMap", []),
        "hypervisors": hypervisors,
    }
    holds = []
    if config.get("isAvailable") is not True:
        holds.append("ahv_cluster_unavailable")
    if "AHV" not in installed["hypervisors"]:
        holds.append("ahv_hypervisor_unobserved")
    if not all(installed.values()):
        holds.append("ahv_installed_versions_incomplete")
    if not projected["storage_containers"] or not projected["subnets"]:
        holds.append("ahv_destination_resources_incomplete")
    if any(row.get("state") == "ENFORCE" and row.get("rules") is None
           for row in projected["policies"]):
        holds.append("ahv_security_rule_catalog_incomplete")
    # Even complete native rule bodies are discovery evidence, not independent
    # end-to-end flow or isolation qualification.
    return {
        "schema_version": 2,
        "profile_type": "TargetCapabilityProfile",
        "platform": "ahv",
        "project_id": policy["native_scope"],
        "prism_central_id": stream["prism_central_id"],
        "cluster_id": stream["cluster_id"],
        "cluster_name": cluster.get("name") or "",
        "api_versions": VERSIONS,
        "installed": installed,
        "observed_at": observed_at,
        "observations_sha256": fingerprint(records),
        "inventory_complete": True,
        # Candidate adapter formats, explicitly NOT capabilities asserted by a GET.
        "disk_formats": ["raw"],
        "image_import_methods": ["prism-image-url"],
        **projected,
        "required_capability_evidence": [
            "q08_linux_cold_export",
            "guest_boot_drivers",
            "image_https_reachability",
            "project_authorization",
            "capacity_reservation",
            "security_allow_and_deny",
            "service_validation",
            "recovery_and_cleanup",
        ],
        "holds": holds,
        "native_qualification": "not_established",
    }
