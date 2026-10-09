"""Native observations are immutable; owners describe datasets and interpretation only."""

import re
from typing import Any

from inventory.domain.ahv import AHV_FIELDS, validate_profile
from inventory.domain.capability_definitions import LEGACY_METHODS
from inventory.domain.discovery import Rejected, canonical, identifier, number, shape, text
from inventory.domain.source_profile import validate_devices, validate_source
from inventory.domain.vmware import FIELDS as VMWARE_FIELDS
from inventory.domain.vmware import validate_profile as validate_vmware_profile

METHODS = LEGACY_METHODS
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
    "security_groups",
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


def profile_payload(
    value: Any, stream: dict[str, Any], scope: str, platform: str | None = None
) -> dict[str, Any]:
    source = stream["kind"] == "source_profile"
    if source and isinstance(value, dict) and value.get("schema_version") == 3:
        return validate_source(value, stream, scope, platform or value.get("platform", ""))
    ahv = not source and isinstance(value, dict) and value.get("platform") == "ahv"
    vmware = not source and isinstance(value, dict) and value.get("platform") == "vmware"
    if not source and isinstance(value, dict) and value.get("platform") == "vmware":
        # Older observations cannot supply editable compatibility guesses.
        value = {**value, "guest_options_by_host": value.get("guest_options_by_host", []),
                 "nsx_policy_observation": value.get("nsx_policy_observation")}
    p = shape(
        value,
        SOURCE_FIELDS
        if source
        else AHV_FIELDS
        if ahv
        else VMWARE_FIELDS
        if vmware
        else TARGET_FIELDS,
    )
    if (
        type(p["schema_version"]) is not int
        or p["schema_version"] != (3 if vmware else 2 if ahv else 1)
        or p["profile_type"] != ("SourceWorkloadProfile" if source else "TargetCapabilityProfile")
        or p["platform"] != ("vmware" if source or vmware else "ahv" if ahv else "openstack")
        or (platform is not None and p["platform"] != platform)
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
        validate_devices(p)
    elif p["project_id"] != scope:
        raise Rejected("foreign_profile_scope", 403)
    if not source and not ahv and not vmware:
        groups = p["security_groups"]
        if not isinstance(groups, list) or len(groups) >= 100:
            raise Rejected("invalid_openstack_security_inventory")
        seen_groups = set()
        for group in groups:
            shape(group, {"id", "name", "project_id", "stateful", "rules_sha256", "semantics_sha256", "rules", "native_sha256"})
            if (not isinstance(group["id"], str) or not group["id"]
                or group["id"] in seen_groups or group["project_id"] != p["project_id"]
                or type(group["name"]) is not str
                or group["stateful"] not in (None, True, False)
            ):
                raise Rejected("foreign_openstack_security_inventory", 403)
            checksum(group["rules_sha256"])
            if group["semantics_sha256"] is not None:
                checksum(group["semantics_sha256"])
            rules = group["rules"]
            if rules is not None:
                if not isinstance(rules, list) or len(rules) > 512:
                    raise Rejected("invalid_openstack_security_inventory")
                rule_ids = set()
                for rule in rules:
                    shape(rule, {
                        "id", "direction", "ethertype", "protocol", "port_range_min",
                        "port_range_max", "remote_ip_prefix", "semantic_sha256",
                    })
                    if (
                        not isinstance(rule["id"], str) or not rule["id"]
                        or rule["id"] in rule_ids
                        or rule["direction"] not in ("ingress", "egress")
                        or rule["ethertype"] not in ("IPv4", "IPv6")
                    ):
                        raise Rejected("invalid_openstack_security_inventory")
                    checksum(rule["semantic_sha256"])
                    rule_ids.add(rule["id"])
            if rules is None and group["semantics_sha256"] is not None:
                raise Rejected("missing_openstack_security_rules")
            checksum(group["native_sha256"])
            seen_groups.add(group["id"])
    if ahv:
        validate_profile(p, stream)
    if vmware:
        validate_vmware_profile(p, stream)
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
        }
        | ({"destination"} if "destination" in body else set()),
    )
    identifier(body["source_profile_id"])
    identifier(body["target_profile_id"])
    if body["method"] not in METHODS:
        raise Rejected("migration_method_required")
    inputs = shape(body["owner_inputs"], set(OWNER_FIELDS))
    for field, value in inputs.items():
        if field == "delta_protocol" and body["method"] == "VM_COLD_EXPORT" and value == "":
            continue
        text(value, 240)
    obj = shape(
        body["objectives"],
        {"owner_id", "acceptance_sha256", "max_outage_seconds", "max_data_loss_bytes"},
    )
    identifier(obj["owner_id"])
    checksum(obj["acceptance_sha256"])
    number(obj["max_outage_seconds"], 0, 31536000)
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
