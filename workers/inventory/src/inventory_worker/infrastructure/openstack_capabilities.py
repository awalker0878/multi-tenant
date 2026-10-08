"""Openstack capabilities; platform mechanisms retain native semantics."""

from typing import Any

from inventory_worker.infrastructure.native import CollectionFailure
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
        "compute_version",
        "volume_version",
    }
    if set(records) != required or not isinstance(project_id, str) or not project_id:
        raise CollectionFailure("invalid_response")
    schema = records["image_schema"]
    methods = records["image_import"].get("import-methods", {}).get("value")
    formats = schema.get("properties", {}).get("disk_format", {}).get("enum")
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
    for response in (records["flavors"], records["volume_types"], records["network_extensions"]):
        for key, links in response.items():
            if key.endswith("links") and (
                not isinstance(links, list)
                or any(not isinstance(link, dict) or link.get("rel") == "next" for link in links)
            ):
                raise CollectionFailure("invalid_response")
    for rows in (flavors, types, extensions):
        if (
            not isinstance(rows, list)
            or len(rows) >= 100
            or not all(isinstance(v, dict) for v in rows)
        ):
            raise CollectionFailure("invalid_response")
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
        "network_extensions": sorted(str(row["alias"]) for row in extensions if "alias" in row),
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
