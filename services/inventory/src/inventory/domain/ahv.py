"""AHV profile and explicit, complete source-device destination mappings."""

import re
from typing import Any
from uuid import UUID

from inventory.domain.discovery import Rejected, number, shape, text
from inventory.domain.destination_security import source_security_ids

AHV_FIELDS = {
    "schema_version",
    "profile_type",
    "platform",
    "project_id",
    "prism_central_id",
    "cluster_id",
    "cluster_name",
    "api_versions",
    "installed",
    "observed_at",
    "observations_sha256",
    "inventory_complete",
    "disk_formats",
    "image_import_methods",
    "storage_containers",
    "subnets",
    "vpcs",
    "categories",
    "policies",
    "required_capability_evidence",
    "holds",
    "native_qualification",
}


def native_uuid(value: Any) -> str:
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError
        return value
    except ValueError:
        raise Rejected("invalid_ahv_native_identity") from None


def validate_profile(p: dict[str, Any], stream: dict[str, Any]) -> None:
    if (
        p["cluster_id"] != stream["cluster_id"]
        or p["prism_central_id"] != stream["prism_central_id"]
        or p["api_versions"]
        != dict.fromkeys(("vmm", "prism", "clustermgmt", "networking", "microseg"), "v4.3")
        or p["inventory_complete"] is not True
        or p["disk_formats"] != ["raw"]
        or p["image_import_methods"] != ["prism-image-url"]
    ):
        raise Rejected("invalid_ahv_profile")
    for field in ("storage_containers", "subnets", "vpcs", "categories", "policies"):
        rows = p[field]
        if not isinstance(rows, list) or len(rows) > 1000:
            raise Rejected("invalid_ahv_inventory")
        ids = []
        for row in rows:
            if not isinstance(row, dict):
                raise Rejected("invalid_ahv_inventory")
            ids.append(native_uuid(row.get("extId")))
            if re.fullmatch(r"[a-f0-9]{64}", text(row.get("native_sha256"), 64)) is None:
                raise Rejected("invalid_ahv_inventory")
            if field == "storage_containers" and (
                row.get("clusterExtId") != p["cluster_id"]
                or row.get("isMarkedForRemoval") is not False
                or row.get("isInternal") is not False
            ):
                raise Rejected("foreign_ahv_inventory", 403)
            if field in {"subnets", "vpcs", "policies"} and (
                row.get("projectExtId") != p["project_id"]
                and row["extId"] not in stream["shared_resource_ids"]
            ):
                raise Rejected("foreign_ahv_inventory", 403)
            if field == "policies":
                # Project-scoped policy list is not a rule-equivalence guarantee.
                # Rule bodies may be present, but any unsupported reference
                # semantics remain unqualified by this profile.
                rules = row.get("rules")
                if rules is not None:
                    if not isinstance(rules, list) or len(rules) > 512:
                        raise Rejected("invalid_ahv_policy_rules")
                    seen_rule_ids = set()
                    for rule in rules:
                        if (
                            not isinstance(rule, dict)
                            or not isinstance(rule.get("extId"), str)
                            or not rule["extId"]
                            or rule["extId"] in seen_rule_ids
                            or not isinstance(rule.get("type"), str)
                            or not isinstance(rule.get("spec_sha256"), str)
                            or re.fullmatch(r"[a-f0-9]{64}", rule["spec_sha256"]) is None
                            or set(rule) != {"extId", "type", "spec_sha256"}
                        ):
                            raise Rejected("invalid_ahv_policy_rules")
                        seen_rule_ids.add(rule["extId"])
        if len(ids) != len(set(ids)):
            raise Rejected("invalid_ahv_inventory")


def destination_input(body: dict[str, Any], source: dict[str, Any], target: dict[str, Any]) -> None:
    if target["platform"] != "ahv":
        raise Rejected("ahv_target_required")
    d = shape(
        body.get("destination"),
        {
            "platform",
            "project_id",
            "prism_central_id",
            "cluster_id",
            "vpc_id",
            "storage_container_id",
            "category_ids",
            "policy_ids",
            "security_mappings",
            "disks",
            "nics",
            "firmware",
        },
    )
    if (
        d["platform"] != "ahv"
        or body["method"] != "VM_COLD_EXPORT"
        or d["firmware"] not in {"bios", "efi"}
        or source["firmware"] != d["firmware"]
    ):
        raise Rejected("ahv_route_requires_matching_firmware_cold_export")
    for key in ("project_id", "prism_central_id", "cluster_id"):
        if native_uuid(d[key]) != target[key]:
            raise Rejected("foreign_ahv_destination", 403)
    inventories = {
        field: {r["extId"]: r for r in target[field]}
        for field in ("storage_containers", "subnets", "vpcs", "categories", "policies")
    }
    if d["storage_container_id"] not in inventories["storage_containers"]:
        raise Rejected("ahv_storage_mapping_unobserved")
    if d["vpc_id"] is not None and d["vpc_id"] not in inventories["vpcs"]:
        raise Rejected("ahv_vpc_mapping_unobserved")
    # Source categories are optional only when they were actually observed.
    # No source category => no destination category selector or assignment.
    native = source.get("native")
    metadata = native.get("metadata") if isinstance(native, dict) else None
    vm = metadata.get("vm") if isinstance(metadata, dict) else None
    source_categories = vm.get("categories") if isinstance(vm, dict) else None
    if not isinstance(d["category_ids"], list) or len(d["category_ids"]) > 32 or (
        len(d["category_ids"]) != len(set(d["category_ids"]))
    ):
        raise Rejected("ahv_category_selection_invalid")
    if (
        (not isinstance(source_categories, list) or not source_categories) and d["category_ids"]
    ) or not set(d["category_ids"]) <= inventories["categories"].keys():
        raise Rejected("unobserved_source_or_destination_category")
    source_ids = source_security_ids(source)
    # Prism ENFORCE is only a deployment state. Neither group membership
    # nor raw policy identity proves cross-platform rule semantics. Owners
    # must not select a potentially unsafe policy merely because it exists.
    # Preserve an empty draft; a mandatory review hold is set in WorkloadProfiles.
    if d["security_mappings"] != [] or d["policy_ids"] != []:
        raise Rejected("destination_security_rule_qualification_required")
    if source_ids:
        # The source policy requirement exists, but no qualified AHV rule
        # crosswalk currently authorizes a destination policy choice.
        pass

    for field in ("disks", "nics"):
        rows = d[field]
        if not isinstance(rows, list) or len(rows) != len(source[field]) or len(rows) > 32:
            raise Rejected("ahv_device_mapping_incomplete")
        keys = []
        for row in rows:
            shape(
                row,
                {"source_key", "index"}
                if field == "disks"
                else {"source_key", "quarantine_subnet_id", "production_subnet_id"},
            )
            keys.append(number(row["source_key"], 0, 2147483647))
            if field == "disks":
                number(row["index"], 0, 31)
            else:
                for network in ("quarantine_subnet_id", "production_subnet_id"):
                    subnet = inventories["subnets"].get(row[network])
                    if subnet is None or subnet.get("vpcReference") != d["vpc_id"]:
                        raise Rejected("ahv_network_mapping_unobserved")
                    if d["vpc_id"] is None and target["cluster_id"] not in {
                        subnet.get("clusterReference"),
                        *(subnet.get("clusterReferenceList") or []),
                    }:
                        raise Rejected("ahv_subnet_cluster_mismatch")
                if row["quarantine_subnet_id"] == row["production_subnet_id"]:
                    raise Rejected("ahv_distinct_quarantine_required")
        if len(set(keys)) != len(keys) or set(keys) != {r["key"] for r in source[field]}:
            raise Rejected("ahv_device_mapping_incomplete")
    if sorted(r["index"] for r in d["disks"]) != list(range(len(d["disks"]))):
        raise Rejected("ahv_disk_order_invalid")
