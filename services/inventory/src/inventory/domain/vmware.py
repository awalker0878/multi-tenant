"""VMware destination observations and complete reviewed hardware/network mapping."""

import re
from typing import Any

from inventory.domain.discovery import Rejected, number, shape, text

FIELDS = {
    "schema_version",
    "profile_type",
    "platform",
    "project_id",
    "vcenter_uuid",
    "api_version",
    "installed",
    "observed_at",
    "observations_sha256",
    "inventory_complete",
    "disk_formats",
    "image_import_methods",
    "folders",
    "resource_pools",
    "hosts",
    "datastores",
    "networks",
    "guest_options_by_host",
    "required_capability_evidence",
    "holds",
    "native_qualification",
}
COLLECTIONS = {
    "folders": "folder",
    "resource_pools": "resource_pool",
    "hosts": "host",
    "datastores": "datastore",
    "networks": "network",
}


def validate_profile(p: dict[str, Any], stream: dict[str, Any]) -> None:
    if (
        p["api_version"] != stream["api_version"]
        or p["inventory_complete"] is not True
        or p["disk_formats"] != ["vmdk"]
        or p["image_import_methods"] != ["vi-json-nfc"]
        or not isinstance(p["installed"], dict)
        or p["installed"].get("instanceUuid") != p["vcenter_uuid"]
        or any(
            not isinstance(p["installed"].get(key), str) or not p["installed"][key]
            for key in ("version", "apiVersion", "build")
        )
    ):
        raise Rejected("invalid_vmware_target_profile")
    for field, key in COLLECTIONS.items():
        rows = p[field]
        if not isinstance(rows, list) or len(rows) > 100:
            raise Rejected("invalid_vmware_target_inventory")
        ids = set()
        for row in rows:
            if (
                not isinstance(row, dict)
                or not isinstance(row.get(key), str)
                or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,127}", row[key])
                or row[key] in ids
                or not isinstance(row.get("native_sha256"), str)
                or not re.fullmatch(r"[a-f0-9]{64}", row["native_sha256"])
            ):
                raise Rejected("invalid_vmware_target_inventory")
            if field == "folders" and row.get("type") != "VIRTUAL_MACHINE":
                raise Rejected("vmware_vm_folder_required")
            ids.add(row[key])

    options = p["guest_options_by_host"]
    if not isinstance(options, list) or len(options) > 16:
        raise Rejected("invalid_guest_catalog")
    known_hosts = {row["host"] for row in p["hosts"]}
    seen_hosts = set()
    for host in options:
        shape(host, {"host", "guest_ids", "hardware_versions", "native_sha256"})
        if host["host"] not in known_hosts or host["host"] in seen_hosts:
            raise Rejected("foreign_guest_catalog", 403)
        seen_hosts.add(host["host"])
        checksum = host["native_sha256"]
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise Rejected("invalid_guest_catalog")
        if (
            not isinstance(host["guest_ids"], list) or not 1 <= len(host["guest_ids"]) <= 128
            or len(host["guest_ids"]) != len(set(host["guest_ids"]))
            or any(not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,80}Guest", v)
                   for v in host["guest_ids"])
            or not isinstance(host["hardware_versions"], list)
            or not 1 <= len(host["hardware_versions"]) <= 32
            or len(host["hardware_versions"]) != len(set(host["hardware_versions"]))
            or any(not isinstance(v, str) or not re.fullmatch(r"vmx-[0-9]{2}", v)
                   for v in host["hardware_versions"])
        ):
            raise Rejected("invalid_guest_catalog")


def destination_input(body: dict[str, Any], source: dict[str, Any], target: dict[str, Any]) -> None:
    d = shape(
        body.get("destination"),
        {
            "platform",
            "project_id",
            "vcenter_uuid",
            "folder_id",
            "resource_pool_id",
            "host_id",
            "datastore_id",
            "guest_id",
            "hardware_version",
            "firmware",
            "disks",
            "nics",
        },
    )
    if (
        d["platform"] != "vmware"
        or d["project_id"] != target["project_id"]
        or d["vcenter_uuid"] != target["vcenter_uuid"]
        or d["firmware"] not in {"bios", "efi"}
        or d["firmware"] != source["firmware"]
    ):
        raise Rejected("vmware_destination_scope_or_firmware_changed")
    for field, collection in (
        ("folder_id", "folders"),
        ("resource_pool_id", "resource_pools"),
        ("host_id", "hosts"),
        ("datastore_id", "datastores"),
    ):
        if d[field] not in {r[COLLECTIONS[collection]] for r in target[collection]}:
            raise Rejected("vmware_destination_mapping_unobserved")
    folder = next(row for row in target["folders"] if row["folder"] == d["folder_id"])
    if folder.get("type") != "VIRTUAL_MACHINE":
        raise Rejected("vmware_vm_folder_required")
    from inventory.domain.destination_security import source_security_ids

    if source_security_ids(source) != []:
        # vCenter network discovery lacks an authoritative observed NSX
        # rule catalogue. No owner-created security IDs are permitted.
        raise Rejected("destination_security_policy_catalog_required")
    catalog = next((row for row in target["guest_options_by_host"]
                    if row["host"] == d["host_id"]), None)
    if (
        catalog is None
        or d["guest_id"] not in catalog["guest_ids"]
        or d["hardware_version"] not in catalog["hardware_versions"]
        or source.get("guest_id") in (None, "")
    ):
        raise Rejected("vmware_guest_mapping_unobserved")
    for field in ("disks", "nics"):
        rows = d[field]
        if not isinstance(rows, list) or len(rows) != len(source[field]) or len(rows) > 32:
            raise Rejected("vmware_device_mapping_incomplete")
        keys = set()
        for row in rows:
            shape(
                row,
                {"source_key", "index"}
                if field == "disks"
                else {"source_key", "quarantine_network_id", "production_network_id"},
            )
            key = number(row["source_key"], 0, 2147483647)
            if key in keys:
                raise Rejected("vmware_device_mapping_incomplete")
            keys.add(key)
            if field == "disks":
                number(row["index"], 0, 31)
            elif row["quarantine_network_id"] == row["production_network_id"] or any(
                row[k] not in {r["network"] for r in target["networks"]}
                for k in ("quarantine_network_id", "production_network_id")
            ):
                raise Rejected("vmware_network_mapping_unobserved")
        if keys != {r["key"] for r in source[field]}:
            raise Rejected("vmware_device_mapping_incomplete")
    if sorted(r["index"] for r in d["disks"]) != list(range(len(d["disks"]))):
        raise Rejected("vmware_disk_order_invalid")
