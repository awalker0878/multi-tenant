"""Prism Central source inventory with complete disks, NICs and native identities."""

from collections.abc import Callable
from typing import Any

from inventory_worker.infrastructure.ahv_source_contract import configuration
from inventory_worker.infrastructure.native import CollectionFailure, exchange, secret
from inventory_worker.infrastructure.native_identity import native_id
from inventory_worker.infrastructure.profile_digest import fingerprint

VM_FIELDS = (
    "extId",
    "name",
    "createTime",
    "updateTime",
    "generationUuid",
    "biosUuid",
    "project",
    "projectExtId",
    "cluster",
    "host",
    "categories",
    "numSockets",
    "numCoresPerSocket",
    "numThreadsPerCore",
    "memorySizeBytes",
    "powerState",
    "bootConfig",
    "vtpmConfig",
    "disks",
    "nics",
    "cdRoms",
    "gpus",
    "pcieDevices",
    "storageConfig",
    "guestTools",
)


def read_vm(stream: dict[str, Any], vm: str, scope: str) -> dict[str, Any]:
    document = exchange(
        stream,
        "/api/vmm/v4.3/ahv/config/vms/" + native_id(vm),
        {"X-Ntnx-Api-Key": secret(stream["credential_file"])},
    )
    result = document.get("data") if isinstance(document, dict) else None
    if (
        not isinstance(result, dict)
        or not isinstance(result.get("project", {}), dict)
        or not isinstance(result.get("cluster"), dict)
        or result.get("extId") != vm
        or result.get("projectExtId", result.get("project", {}).get("extId")) != scope
        or result.get("project", {}).get("extId", scope) != scope
        or result.get("cluster", {}).get("extId") != stream["cluster_id"]
    ):
        raise CollectionFailure("permission_denied")
    return {k: result[k] for k in VM_FIELDS if k in result}


def collect_ahv_source(
    policy: dict[str, Any],
    stream: dict[str, Any],
    vm: str,
    observed_at: int,
    before_request: Callable[[], None],
) -> dict[str, Any]:
    before_request()
    row = read_vm(stream, vm, policy["native_scope"])
    installed = {}
    for kind, path, key in (
        ("cluster", "/api/clustermgmt/v4.3/config/clusters/", "cluster_id"),
        ("prism_central", "/api/prism/v4.3/config/domain-managers/", "prism_central_id"),
    ):
        before_request()
        document = exchange(
            stream, path + stream[key], {"X-Ntnx-Api-Key": secret(stream["credential_file"])}
        )
        if (
            not isinstance(document, dict)
            or not isinstance(document.get("data"), dict)
            or document["data"].get("extId") != stream[key]
            or not isinstance(document["data"].get("config", {}), dict)
        ):
            raise CollectionFailure("invalid_response")
        installed[kind] = document["data"].get("config", {})
    disks: list[dict[str, Any]] = []
    native_disks: list[dict[str, Any]] = []
    nics: list[dict[str, Any]] = []
    controllers: list[dict[str, Any]] = []
    holds: list[str] = []
    cluster_config = installed["cluster"]
    hypervisors = cluster_config.get("hypervisorTypes", [])
    if not isinstance(hypervisors, list) or any(not isinstance(v, str) for v in hypervisors):
        raise CollectionFailure("invalid_response")
    if (
        not cluster_config.get("buildInfo")
        or not cluster_config.get("clusterSoftwareMap")
        or not installed["prism_central"].get("buildInfo")
    ):
        holds.append("ahv_installed_versions_incomplete")
    if "AHV" not in hypervisors:
        holds.append("ahv_hypervisor_unobserved")
    if (
        not isinstance(row.get("disks"), list)
        or len(row["disks"]) > 32
        or not isinstance(row.get("nics"), list)
        or len(row["nics"]) > 32
    ):
        raise CollectionFailure("invalid_response")
    for field in ("disks", "nics"):
        identities = [
            native_id(device.get("extId")) for device in row[field] if isinstance(device, dict)
        ]
        if len(identities) != len(row[field]) or len(set(identities)) != len(identities):
            raise CollectionFailure("invalid_response")
    for index, d in enumerate(sorted(row["disks"], key=lambda d: d.get("extId", ""))):
        native_id(d.get("extId"))
        address, backing = d.get("diskAddress", {}), d.get("backingInfo", {})
        if not isinstance(address, dict) or not isinstance(backing, dict):
            raise CollectionFailure("invalid_response")
        if backing.get("$objectType") != "vmm.v4.ahv.config.VmDisk":
            holds.append("unsupported_or_shared_disk_backing")
        record = {"key": index, "native_id": d["extId"], "role": "vm_disk", "metadata": d}
        capacity = backing.get("diskSizeBytes")
        if type(capacity) is not int or capacity <= 0:
            capacity = None
            holds.append("disk_capacity_unobserved")
        native_disks.append(record)
        disks.append(
            {
                "key": index,
                "capacity_bytes": capacity,
                "controller_key": None,
                "unit_number": address.get("index"),
                "backing_chain": [],
                "native_sha256": fingerprint(record),
            }
        )
        controllers.append(
            {
                "key": index,
                "model": address.get("busType", "unknown"),
                "bus": index,
                "sharing": None,
            }
        )
    if not disks:
        holds.append("complete_disk_inventory_required")
    for index, nic in enumerate(sorted(row["nics"], key=lambda n: n.get("extId", ""))):
        native_id(nic.get("extId"))
        backing = nic.get("backingInfo", {})
        if not isinstance(backing, dict):
            raise CollectionFailure("invalid_response")
        nics.append(
            {
                "key": index,
                "model": backing.get("model", "unknown"),
                "mac": backing.get("macAddress"),
                "backing_sha256": fingerprint(nic),
                "connectable": {
                    "connected": backing.get("isConnected"),
                    "startConnected": None,
                    "allowGuestControl": None,
                },
            }
        )
    for field in ("gpus", "pcieDevices", "vtpmConfig"):
        if row.get(field):
            holds.append("native_device_or_key_portability_required")
    if not row.get("generationUuid") or not row.get("biosUuid"):
        holds.append("source_incarnation_unobserved")
    before_request()
    if read_vm(stream, vm, policy["native_scope"]) != row:
        raise CollectionFailure("invalid_response")
    boot_config = row.get("bootConfig", {})
    if not isinstance(boot_config, dict):
        raise CollectionFailure("invalid_response")
    boot = boot_config.get("$objectType")
    if boot_config.get("isSecureBootEnabled") is True:
        holds.append("secure_boot_requires_separate_qualification")
    firmware = (
        {"vmm.v4.ahv.config.LegacyBoot": "bios", "vmm.v4.ahv.config.UefiBoot": "efi"}.get(boot)
        if isinstance(boot, str)
        else None
    )
    if firmware is None:
        holds.append("firmware_unknown")
    if row.get("powerState") not in ("ON", "OFF"):
        holds.append("source_power_state_unsupported")
    cores = [row.get(k) for k in ("numSockets", "numCoresPerSocket", "numThreadsPerCore")]
    cpu = 1
    for core in cores:
        if type(core) is not int or core <= 0:
            raise CollectionFailure("invalid_response")
        cpu *= core
    memory = row.get("memorySizeBytes")
    if type(memory) is not int or memory < 1024**2:
        raise CollectionFailure("invalid_response")
    return {
        "schema_version": 3,
        "profile_type": "SourceWorkloadProfile",
        "platform": "ahv",
        "vm_id": vm,
        "installation_id": stream["prism_central_id"],
        "native_scope": policy["native_scope"],
        "api_version": "v4.3",
        "versions": {
            "vmm": "v4.3",
            "prism": "v4.3",
            "clustermgmt": "v4.3",
            "product": policy["installed"]["product"],
        },
        "config_sha256": fingerprint(configuration("vm", row)),
        "observations_sha256": fingerprint([row, installed]),
        "observed_at": observed_at,
        "power_state": row.get("powerState"),
        "guest_id": None,
        "firmware": firmware,
        "cpu": cpu,
        "memory_mb": memory // 1024**2 if type(memory) is int else None,
        "disks": disks,
        "nics": nics,
        "controllers": controllers,
        "native": {
            "identity": {
                "vm_id": vm,
                "scope": policy["native_scope"],
                "cluster_id": stream["cluster_id"],
                "generation_uuid": row.get("generationUuid"),
                "bios_uuid": row.get("biosUuid"),
            },
            "disk_records": native_disks,
            "metadata": {"vm": row, "installed": installed},
        },
        "required_owner_inputs": [
            "guest_identity_and_drivers",
            "application_consistency",
            "writer_fencing",
            "service_validation",
        ],
        "holds": sorted(set(holds)),
        "native_qualification": "not_established",
    }
