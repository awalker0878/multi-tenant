"""Openstack capabilities; platform mechanisms retain native semantics."""

from typing import Any

from inventory_worker.infrastructure.native import CollectionFailure
from inventory_worker.infrastructure.openstack_security import rule_choices, security_semantics
from inventory_worker.infrastructure.profile_digest import fingerprint


def target_profile(project_id: str, records: dict[str, Any], observed_at: int) -> dict[str, Any]:
    """Normalize observed OpenStack capabilities without inferring guest/driver support.

    Callers supply the existing commissioned discovery results for the selected
    project; catalog-returned addresses never become new request destinations.
    """
    required = {
        "image_schema",
        "image_import",
        "flavors",
        "volume_types",
        "network_extensions",
        "security_groups",
        "compute_version",
        "volume_version",
    }
    if (
        set(records) != required
        or any(not isinstance(record, dict) for record in records.values())
        or not isinstance(project_id, str)
        or not project_id
    ):
        raise CollectionFailure("invalid_response")
    schema = records["image_schema"]
    properties = schema.get("properties", {})
    import_methods = records["image_import"].get("import-methods", {})
    if not isinstance(properties, dict) or not isinstance(import_methods, dict):
        raise CollectionFailure("invalid_response")
    disk_format = properties.get("disk_format", {})
    if not isinstance(disk_format, dict):
        raise CollectionFailure("invalid_response")
    methods = import_methods.get("value")
    formats = disk_format.get("enum")
    holds = []
    if not isinstance(formats, list) or not formats or not all(isinstance(v, str) for v in formats):
        formats = []
        holds.append("image_formats_unobserved")
    if not isinstance(methods, list) or not all(isinstance(v, str) for v in methods):
        methods = []
        holds.append("image_import_methods_unobserved")
    flavors = records["flavors"].get("flavors")
    types = records["volume_types"].get("volume_types")
    extensions = records["network_extensions"].get("extensions")
    security_groups = records["security_groups"].get("security_groups")
    for response in (records["flavors"], records["volume_types"], records["network_extensions"], records["security_groups"]):
        for key, links in response.items():
            if key.endswith("links") and (
                not isinstance(links, list)
                or any(not isinstance(link, dict) or link.get("rel") == "next" for link in links)
            ):
                raise CollectionFailure("invalid_response")
    for rows in (flavors, types, extensions, security_groups):
        if (
            not isinstance(rows, list)
            or len(rows) >= 100
            or not all(isinstance(v, dict) for v in rows)
        ):
            raise CollectionFailure("invalid_response")
    for rows, identity in ((flavors, "id"), (types, "id"), (extensions, "alias"), (security_groups, "id")):
        identities = [row.get(identity) for row in rows]
        if any(not isinstance(value, str) or not value for value in identities) or len(
            set(identities)
        ) != len(identities):
            raise CollectionFailure("invalid_response")
    # Only complete, project-owned, API-discovered security groups may be offered.
    # A rule is a policy *candidate*, never independent proof of equivalent flows.
    for group in security_groups:
        if (
            group.get("project_id", group.get("tenant_id")) != project_id
            or not isinstance(group.get("security_group_rules"), list)
            or len(group["security_group_rules"]) > 512
            or not isinstance(group.get("name"), str)
        ):
            raise CollectionFailure("invalid_response")
        rule_ids = set()
        for rule in group["security_group_rules"]:
            if (
                not isinstance(rule, dict)
                or not isinstance(rule.get("id"), str)
                or rule.get("security_group_id") != group["id"]
                or rule.get("project_id", rule.get("tenant_id")) != project_id
                or rule["id"] in rule_ids
            ):
                raise CollectionFailure("invalid_response")
            rule_ids.add(rule["id"])
    # These services can hide deployment choices behind policy or custom backends.
    # The API advertises what was observed, never an assumed firmware/driver tuple.
    return {
        "schema_version": 1,
        "profile_type": "TargetCapabilityProfile",
        "platform": "openstack",
        "project_id": project_id,
        "observed_at": observed_at,
        "observations_sha256": fingerprint(records),
        "disk_formats": sorted(set(formats)),
        "image_import_methods": sorted(set(methods)),
        "flavors": [
            {k: row.get(k) for k in ("id", "vcpus", "ram", "disk", "OS-FLV-EXT-DATA:ephemeral")}
            for row in flavors
        ],
        "volume_types": [
            {
                "id": row.get("id"),
                "is_public": row.get("is_public"),
                "constraints_sha256": fingerprint(row.get("extra_specs", {})),
            }
            for row in types
        ],
        "network_extensions": sorted(row["alias"] for row in extensions),
        "security_groups": [
            {"id": group["id"], "name": group["name"], "project_id": project_id,
             "stateful": group.get("stateful"),
             "rules_sha256": fingerprint(group["security_group_rules"]),
             "semantics_sha256": security_semantics(group),
             "rules": rule_choices(group),
             "native_sha256": fingerprint(group)}
            for group in sorted(security_groups, key=lambda item: item["id"])
        ],
        "compute_version": {
            k: records["compute_version"].get(k) for k in ("min_version", "version")
        },
        "volume_version": {k: records["volume_version"].get(k) for k in ("min_version", "version")},
        "required_capability_evidence": [
            "firmware_and_device_support",
            "guest_driver_profile",
            "metadata_and_config_drive_profile",
            "security_path_qualification",
            "service_attachments",
            "capacity_and_transfer_reservations",
        ],
        "holds": holds,
        "native_qualification": "not_established",
    }
