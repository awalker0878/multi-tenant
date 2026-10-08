"""Role-neutral workload facts with explicit native identities and metadata.

Legacy VMware profiles remain version 1. Version 3 adds independently discovered
OpenStack/AHV sources without manufacturing vCenter identifiers.
"""

import re
from typing import Any

from inventory.domain.discovery import Rejected, canonical, digest, number, shape, text

FIELDS = {
    "schema_version",
    "profile_type",
    "platform",
    "vm_id",
    "installation_id",
    "native_scope",
    "api_version",
    "versions",
    "config_sha256",
    "observations_sha256",
    "observed_at",
    "power_state",
    "guest_id",
    "firmware",
    "cpu",
    "memory_mb",
    "disks",
    "nics",
    "controllers",
    "native",
    "required_owner_inputs",
    "holds",
    "native_qualification",
}


def checksum(value: Any) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise Rejected("invalid_profile_digest")
    return value


def validate_devices(p: dict[str, Any]) -> None:
    """Require unambiguous reviewed NIC and controller identities on every source."""
    for field, required in (
        ("nics", {"key", "model", "mac", "backing_sha256", "connectable"}),
        ("controllers", {"key", "model", "bus", "sharing"}),
    ):
        rows = p[field]
        if not isinstance(rows, list) or len(rows) > 128:
            raise Rejected("invalid_workload_profile")
        keys = set()
        for row in rows:
            shape(row, required)
            key = number(row["key"], 0, 2147483647)
            if key in keys:
                raise Rejected("duplicate_source_device")
            keys.add(key)
            text(row["model"], 160)
            if field == "nics":
                checksum(row["backing_sha256"])
                if row["mac"] is not None:
                    text(row["mac"], 80)
                connectable = shape(
                    row["connectable"], {"connected", "startConnected", "allowGuestControl"}
                )
                if any(
                    value is not None and type(value) is not bool for value in connectable.values()
                ):
                    raise Rejected("invalid_nic_connectivity")
            else:
                number(row["bus"], 0, 2147483647)
                if row["sharing"] is not None:
                    text(row["sharing"], 80)


def validate_source(
    value: Any, stream: dict[str, Any], scope: str, platform: str
) -> dict[str, Any]:
    p = shape(value, FIELDS)
    if (
        type(p["schema_version"]) is not int
        or p["schema_version"] != 3
        or p["profile_type"] != "SourceWorkloadProfile"
        or p["platform"] != platform
        or platform not in {"openstack", "ahv"}
        or p["native_scope"] != scope
        or p["vm_id"] not in stream["vm_ids"]
        or p["api_version"] != stream["api_version"]
        or p["native_qualification"] != "not_established"
        or len(canonical(p).encode()) > 131072
    ):
        raise Rejected("invalid_workload_profile")
    text(p["installation_id"])
    number(p["observed_at"], 1, 9007199254740991)
    for key in ("config_sha256", "observations_sha256"):
        checksum(p[key])
    if not isinstance(p["versions"], dict) or not 1 <= len(p["versions"]) <= 12:
        raise Rejected("invalid_installed_identity")
    for version_key, version in p["versions"].items():
        text(version_key, 40)
        text(version, 160)
    for key in ("guest_id", "power_state", "firmware"):
        if p[key] is not None:
            text(p[key], 160)
    for key in ("cpu", "memory_mb"):
        if p[key] is not None:
            number(p[key], 1, 9007199254740991)
    for field, maximum in (
        ("disks", 32),
        ("nics", 32),
        ("controllers", 32),
        ("required_owner_inputs", 64),
        ("holds", 64),
    ):
        if not isinstance(p[field], list) or len(p[field]) > maximum:
            raise Rejected("invalid_workload_profile")
    for field in ("required_owner_inputs", "holds"):
        for item in p[field]:
            text(item, 100)
    validate_devices(p)
    keys, identities = set(), set()
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
        disk_key = number(disk["key"], 0, 2147483647)
        fingerprint = checksum(disk["native_sha256"])
        if disk_key in keys or fingerprint in identities:
            raise Rejected("invalid_disk_inventory")
        keys.add(disk_key)
        identities.add(fingerprint)
        if disk["capacity_bytes"] is not None:
            number(disk["capacity_bytes"], 1, 9007199254740991)
    native = shape(p["native"], {"identity", "disk_records", "metadata"})
    identity = native["identity"]
    if (
        not isinstance(identity, dict)
        or identity.get("vm_id") != p["vm_id"]
        or identity.get("scope") != scope
    ):
        raise Rejected("foreign_profile_scope", 403)
    records = native["disk_records"]
    if not isinstance(records, list) or len(records) != len(keys):
        raise Rejected("invalid_disk_inventory")
    native_ids = set()
    record_keys = set()
    for record in records:
        shape(record, {"key", "native_id", "role", "metadata"})
        record_key = number(record["key"], 0, 2147483647)
        if record_key not in keys or record_key in record_keys:
            raise Rejected("invalid_disk_inventory")
        record_keys.add(record_key)
        text(record.get("native_id"))
        if record["native_id"] in native_ids or not isinstance(record["metadata"], dict):
            raise Rejected("invalid_disk_inventory")
        native_ids.add(record["native_id"])
        text(record["role"], 80)
        disk = next(d for d in p["disks"] if d["key"] == record["key"])
        if digest(record) != disk["native_sha256"]:
            raise Rejected("native_disk_mapping_changed")
    if not isinstance(native["metadata"], dict):
        raise Rejected("invalid_workload_profile")
    return p


def source_identity(p: dict[str, Any]) -> tuple[Any, Any]:
    if p["schema_version"] == 3:
        return (
            [p["platform"], p["installation_id"], p["native"]["identity"]],
            [
                p["versions"],
                p["api_version"],
                p["guest_id"],
                p["firmware"],
                p["native"]["metadata"].get("installed"),
            ],
        )
    return (
        [p.get(k) for k in ("vcenter_uuid", "vm_id", "instance_uuid")],
        [
            p.get(k)
            for k in (
                "vcenter_version",
                "native_api_version",
                "api_version",
                "guest_id",
                "firmware",
            )
        ],
    )
