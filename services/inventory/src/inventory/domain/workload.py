"""Native observations are immutable; owners describe datasets and interpretation only."""

import re
from typing import Any

from inventory.domain.discovery import Rejected, canonical, identifier, number, shape, text

METHODS = (
    "APPLICATION_REBUILD_RESTORE",
    "VM_SNAPSHOT_BASELINE_APP_DELTA",
    "VM_SNAPSHOT_BASELINE_FILE_DELTA",
    "VM_COLD_EXPORT",
    "EXTERNAL_BLOCK_REPLICATION",
)
OWNER_FIELDS = (
    "application_consistency",
    "dependencies",
    "guest_transformation_profile",
    "delta_protocol",
    "recovery_protocol",
    "service_and_policy_validation",
    "writer_fencing",
    "retention_and_cleanup",
)
SOURCE_FIELDS = {
    "schema_version",
    "profile_type",
    "platform",
    "vm_id",
    "instance_uuid",
    "bios_uuid",
    "vcenter_uuid",
    "vcenter_version",
    "api_version",
    "native_api_version",
    "config_sha256",
    "observations_sha256",
    "observed_at",
    "power_state",
    "guest_id",
    "tools_status",
    "tools_version",
    "firmware",
    "cpu",
    "memory_mb",
    "disks",
    "nics",
    "controllers",
    "snapshot_tree_sha256",
    "key_custody_sha256",
    "required_owner_inputs",
    "holds",
    "native_qualification",
}
TARGET_FIELDS = {
    "schema_version",
    "profile_type",
    "platform",
    "project_id",
    "observed_at",
    "observations_sha256",
    "disk_formats",
    "image_import_methods",
    "flavors",
    "volume_types",
    "network_extensions",
    "compute_version",
    "volume_version",
    "required_capability_evidence",
    "holds",
    "native_qualification",
}


def checksum(value: Any) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise Rejected("invalid_profile_digest")
    return value


def profile_payload(value: Any, stream: dict[str, Any], scope: str) -> dict[str, Any]:
    source = stream["kind"] == "source_profile"
    p = shape(value, SOURCE_FIELDS if source else TARGET_FIELDS)
    if (
        type(p["schema_version"]) is not int
        or p["schema_version"] != 1
        or p["profile_type"] != ("SourceWorkloadProfile" if source else "TargetCapabilityProfile")
        or p["platform"] != ("vmware" if source else "openstack")
        or p["native_qualification"] != "not_established"
        or len(canonical(p).encode()) > 131072
    ):
        raise Rejected("invalid_workload_profile")
    checksum(p["observations_sha256"])
    number(p["observed_at"], 1, 9007199254740991)
    if not isinstance(p["holds"], list) or len(p["holds"]) > 64:
        raise Rejected("invalid_workload_profile")
    for hold in p["holds"]:
        text(hold, 100)
    if source:
        if p["vm_id"] not in stream["vm_ids"] or p["api_version"] != stream["api_version"]:
            raise Rejected("foreign_profile_scope", 403)
        for field in ("config_sha256", "snapshot_tree_sha256", "key_custody_sha256"):
            checksum(p[field])
        if not isinstance(p["disks"], list) or len(p["disks"]) > 32:
            raise Rejected("invalid_disk_inventory")
        keys = set()
        for disk in p["disks"]:
            shape(
                disk,
                {
                    "key",
                    "capacity_bytes",
                    "controller_key",
                    "unit_number",
                    "backing_chain",
                    "native_sha256",
                },
            )
            key = number(disk["key"], 0, 2147483647)
            checksum(disk["native_sha256"])
            if key in keys:
                raise Rejected("invalid_disk_inventory")
            keys.add(key)
        for field in ("nics", "controllers"):
            if not isinstance(p[field], list) or len(p[field]) > 128:
                raise Rejected("invalid_workload_profile")
    elif p["project_id"] != scope:
        raise Rejected("foreign_profile_scope", 403)
    return p


def review_input(body: dict[str, Any], source: dict[str, Any]) -> None:
    shape(
        body,
        {
            "source_profile_id",
            "target_profile_id",
            "method",
            "datasets",
            "owner_inputs",
            "objectives",
            "overrides",
        },
    )
    identifier(body["source_profile_id"])
    identifier(body["target_profile_id"])
    if body["method"] not in METHODS:
        raise Rejected("migration_method_required")
    inputs = shape(body["owner_inputs"], set(OWNER_FIELDS))
    for value in inputs.values():
        text(value, 240)
    obj = shape(
        body["objectives"],
        {"owner_id", "acceptance_sha256", "max_outage_seconds", "max_data_loss_bytes"},
    )
    identifier(obj["owner_id"])
    checksum(obj["acceptance_sha256"])
    number(obj["max_outage_seconds"], 1, 31536000)
    number(obj["max_data_loss_bytes"], 0, 9007199254740991)
    datasets = body["datasets"]
    if not isinstance(datasets, list) or not 1 <= len(datasets) <= 256:
        raise Rejected("migration_datasets_incomplete")
    seen, covered = set(), set()
    for d in datasets:
        shape(d, {"id", "name", "disk_keys", "mounts", "consistency_group", "validation_reference"})
        identity = identifier(d["id"])
        if identity in seen:
            raise Rejected("duplicate_dataset")
        seen.add(identity)
        for key in ("name", "consistency_group", "validation_reference"):
            text(d[key], 240)
        for field in ("disk_keys", "mounts"):
            if not isinstance(d[field], list) or not 1 <= len(d[field]) <= 32:
                raise Rejected("migration_dataset_mapping_invalid")
        disk_keys = [number(k, 0, 2147483647) for k in d["disk_keys"]]
        if len(set(disk_keys)) != len(disk_keys):
            raise Rejected("migration_dataset_mapping_invalid")
        covered.update(disk_keys)
        for mount in d["mounts"]:
            text(mount, 240)
    if covered != {d["key"] for d in source["disks"]}:
        raise Rejected("migration_datasets_incomplete")
    if not isinstance(body["overrides"], list) or len(body["overrides"]) > 8:
        raise Rejected("invalid_interpretation")
    seen_overrides = set()
    for override in body["overrides"]:
        shape(override, {"field", "interpretation", "reason"})
        if override["field"] not in OWNER_FIELDS or override["field"] in seen_overrides:
            raise Rejected("native_facts_cannot_be_overridden")
        seen_overrides.add(override["field"])
        text(override["interpretation"], 240)
        text(override["reason"], 240)
