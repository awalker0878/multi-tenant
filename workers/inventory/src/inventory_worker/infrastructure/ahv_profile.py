"""Bounded Prism Central v4 destination discovery; absence is never qualification."""

from collections.abc import Callable
from typing import Any

from inventory_worker.infrastructure.native import CollectionFailure, exchange, secret
from inventory_worker.infrastructure.workload_profile import fingerprint

# Independently versioned namespaces. No SDK negotiation or fallback to legacy APIs.
VERSIONS = dict.fromkeys(("vmm", "prism", "clustermgmt", "networking", "microseg"), "v4.3")
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
    ),
}


def complete_list(document: Any) -> list[dict[str, Any]]:
    if not isinstance(document, dict):
        raise CollectionFailure("invalid_response")
    rows, metadata = document.get("data"), document.get("metadata", {})
    if (
        not isinstance(rows, list)
        or len(rows) >= 100
        or not isinstance(metadata, dict)
        or type(metadata.get("totalAvailableResults")) is not int
        or metadata["totalAvailableResults"] != len(rows)
        or not isinstance(metadata.get("links", []), list)
        or any(not isinstance(r, dict) or not isinstance(r.get("extId"), str) for r in rows)
        or len({r["extId"] for r in rows}) != len(rows)
        or any(
            not isinstance(link, dict) or link.get("rel") == "next"
            for link in metadata.get("links", [])
        )
    ):
        # One leased profile has seven separately budgeted reads. Never truncate a
        # larger inventory, follow native links, or claim a partial list is complete.
        raise CollectionFailure("invalid_response")
    return rows


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
        "storage_containers": "/api/clustermgmt/v4.3/config/storage-containers?$limit=100",
        "subnets": "/api/networking/v4.3/config/subnets?$limit=100",
        "vpcs": "/api/networking/v4.3/config/vpcs?$limit=100",
        "categories": "/api/prism/v4.3/config/categories?$limit=100",
        "policies": "/api/microseg/v4.3/config/policies?$limit=100",
    }
    for key, path in routes.items():
        before_request()
        records[key] = exchange(stream, path, {"X-Ntnx-Api-Key": secret(stream["credential_file"])})
    cluster, pc = (records[k].get("data", {}) for k in ("cluster", "prism_central"))
    if (
        cluster.get("extId") != stream["cluster_id"]
        or pc.get("extId") != stream["prism_central_id"]
    ):
        raise CollectionFailure("invalid_response")
    inventory = {k: complete_list(records[k]) for k in FIELDS}
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
    projected = {
        k: [{f: r.get(f) for f in fields} | {"native_sha256": fingerprint(r)} for r in inventory[k]]
        for k, fields in FIELDS.items()
    }
    config = cluster.get("config", {})
    installed = {
        "prism_central": pc.get("config", {}).get("buildInfo", {}),
        "aos": config.get("buildInfo", {}),
        "cluster_software": config.get("clusterSoftwareMap", []),
        "hypervisors": config.get("hypervisorTypes", []),
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
