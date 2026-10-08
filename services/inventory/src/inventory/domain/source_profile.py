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
    if {r.get("key") for r in records if isinstance(r, dict)} != keys:
        raise Rejected("invalid_disk_inventory")
    for record in records:
        text(record.get("native_id"))
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
            [p["versions"], p["api_version"], p["guest_id"], p["firmware"]],
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
