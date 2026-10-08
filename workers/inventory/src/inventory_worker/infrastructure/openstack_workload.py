"""Nova, Cinder and Neutron source observations; no production-source writes.

Image-backed local disks and every attached volume are inventoried separately.
Native records remain attached to stable keys; a Nova snapshot is never treated
as containing attached-volume bytes. Unknown boot/guest data stays unknown.
"""

import re
from collections.abc import Callable
from typing import Any

from inventory_worker.infrastructure.native import CollectionFailure, exchange, secret
from inventory_worker.infrastructure.native_identity import native_id
from inventory_worker.infrastructure.profile_digest import fingerprint


def collect_openstack_source(
    policy: dict[str, Any],
    stream: dict[str, Any],
    vm: str,
    observed_at: int,
    before_request: Callable[[], None],
) -> dict[str, Any]:
    by_kind = {s["kind"]: s for s in policy["streams"]}
    project = policy["native_scope"]
    records: dict[str, Any] = {}

    def read(kind: str, path: str, field: str) -> Any:
        connection = stream if kind == "compute" else by_kind[kind]
        before_request()
        headers = {"X-Auth-Token": secret(connection["credential_file"])}
        if kind in {"compute", "volume"}:
            headers["OpenStack-API-Version"] = "compute 2.1" if kind == "compute" else "volume 3.0"
        result = exchange(connection, path, headers)
        if not isinstance(result, dict) or field not in result:
            raise CollectionFailure("invalid_response")
        records[kind + path] = result
        return result[field]

    server = read("compute", "/servers/" + native_id(vm), "server")
    if not isinstance(server, dict) or server.get("id") != vm or server.get("tenant_id") != project:
        raise CollectionFailure("permission_denied")
    flavor_id = server.get("flavor", {}).get("id")
    if not isinstance(flavor_id, str) or re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", flavor_id) is None:
        raise CollectionFailure("invalid_response")
    flavor = read("compute", "/flavors/" + flavor_id, "flavor")
    attachments = read("compute", f"/servers/{vm}/os-volume_attachments", "volumeAttachments")
    ports = read("network", f"/ports?device_id={vm}&project_id={project}&limit=33", "ports")
    if (
        not isinstance(flavor, dict)
        or not isinstance(attachments, list)
        or len(attachments) > 32
        or not isinstance(ports, list)
        or len(ports) > 32
    ):
        raise CollectionFailure("invalid_response")
    # Detect truncated port inventories instead of accepting incomplete NIC coverage.
    if records["network" + f"/ports?device_id={vm}&project_id={project}&limit=33"].get(
        "ports_links"
    ):
        raise CollectionFailure("invalid_response")
    volume_ids = [native_id(a.get("volumeId")) for a in attachments if isinstance(a, dict)]
    if len(volume_ids) != len(attachments) or len(set(volume_ids)) != len(volume_ids):
        raise CollectionFailure("invalid_response")
    holds: list[str] = []
    disks: list[dict[str, Any]] = []
    native_disks: list[dict[str, Any]] = []

    def disk(identity: str, capacity: Any, metadata: dict[str, Any], role: str) -> None:
        key = len(disks)
        if type(capacity) is not int or capacity <= 0:
            capacity = None
            holds.append("disk_capacity_unobserved")
        record = {"key": key, "native_id": identity, "role": role, "metadata": metadata}
        native_disks.append(record)
        disks.append(
            {
                "key": key,
                "capacity_bytes": capacity,
                "controller_key": None,
                "unit_number": key,
                "backing_chain": [],
                "native_sha256": fingerprint(record),
            }
        )

    image = server.get("image")
    if image:
        image_id = native_id(image.get("id")) if isinstance(image, dict) else native_id(None)
        size = flavor.get("disk")
        disk(
            "local-root:" + vm,
            size * 1024**3 if type(size) is int else None,
            {"image_id": image_id, "flavor_id": flavor_id},
            "root",
        )
    for field in ("OS-FLV-EXT-DATA:ephemeral", "swap"):
        size = flavor.get(field, 0)
        if size not in (0, "", None):
            holds.append("local_ephemeral_or_swap_requires_explicit_capture")
    for volume_id in sorted(volume_ids):
        volume = read("volume", "/volumes/" + volume_id, "volume")
        if (
            not isinstance(volume, dict)
            or volume.get("id") != volume_id
            or volume.get("os-vol-tenant-attr:tenant_id") not in (None, project)
        ):
            raise CollectionFailure("permission_denied")
        attached = volume.get("attachments", [])
        if (
            not isinstance(attached, list)
            or len(attached) != 1
            or attached[0].get("server_id") != vm
            or volume.get("multiattach") is True
        ):
            holds.append("shared_volume_consistency_required")
        if volume.get("encrypted") is not False:
            holds.append("volume_encryption_key_custody_required")
        size = volume.get("size")
        disk(
            volume_id,
            size * 1024**3 if type(size) is int else None,
            volume,
            "bootable_volume" if volume.get("bootable") == "true" else "data_volume",
        )
    if not disks:
        holds.append("complete_disk_inventory_required")
    nics: list[dict[str, Any]] = []
    for port in sorted(ports, key=lambda p: p.get("id", "")):
        if (
            not isinstance(port, dict)
            or port.get("device_id") != vm
            or port.get("project_id", port.get("tenant_id")) != project
        ):
            raise CollectionFailure("permission_denied")
        native_id(port.get("id"))
        nics.append(
            {
                "key": len(nics),
                "model": port.get("binding:vnic_type", "unknown"),
                "mac": port.get("mac_address"),
                "backing_sha256": fingerprint(port),
                "connectable": {
                    "connected": port.get("status") == "ACTIVE",
                    "startConnected": port.get("admin_state_up"),
                    "allowGuestControl": None,
                },
            }
        )
    metadata = server.get("metadata", {})
    if not isinstance(metadata, dict):
        raise CollectionFailure("invalid_response")
    # Metadata is an API observation of a declaration, not verified guest inspection.
    guest = metadata.get("os_distro")
    firmware = metadata.get("hw_firmware_type")
    reread = read("compute", "/servers/" + vm, "server")
    if reread != server:
        raise CollectionFailure("invalid_response")
    return {
        "schema_version": 3,
        "profile_type": "SourceWorkloadProfile",
        "platform": "openstack",
        "vm_id": vm,
        "installation_id": policy["authority"],
        "native_scope": project,
        "api_version": stream["api_version"],
        "versions": {
            "compute": "2.1",
            "volume": "3.0",
            "network": "2.0",
            "product": policy["installed"]["product"],
        },
        "config_sha256": fingerprint({"server": server, "disks": native_disks, "ports": ports}),
        "observations_sha256": fingerprint(records),
        "observed_at": observed_at,
        "power_state": server.get("status"),
        "guest_id": guest,
        "firmware": firmware,
        "cpu": flavor.get("vcpus"),
        "memory_mb": flavor.get("ram"),
        "disks": disks,
        "nics": nics,
        "controllers": [],
        "native": {
            "identity": {"vm_id": vm, "scope": project, "created": server.get("created")},
            "disk_records": native_disks,
            "metadata": {
                "server": server,
                "ports": ports,
                "flavor": flavor,
                "guest_provenance": "native_metadata_declaration",
                "firmware_provenance": "native_metadata_declaration",
            },
        },
        "required_owner_inputs": [
            "guest_boot_drivers",
            "application_consistency",
            "writer_fencing",
            "complete_disk_capture",
            "service_validation",
        ],
        "holds": sorted(set(holds)),
        "native_qualification": "not_established",
    }
