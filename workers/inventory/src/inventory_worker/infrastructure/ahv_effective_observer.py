"""Independent scoped Prism v4 AHV VM/category snapshot (E3, never E4).

The installed VMM namespace must be explicitly qualified; missing categories
and native ports remain unknown rather than being interpreted as empty.
"""
from collections.abc import Callable
from typing import Any
from uuid import UUID

from inventory_worker.infrastructure.native import CollectionFailure, exchange, secret
from inventory_worker.infrastructure.profile_digest import fingerprint


def _uuid(value: Any) -> str:
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError
        return value
    except ValueError:
        raise CollectionFailure("invalid_native_identity") from None


def collect(
    stream: dict[str, Any], vm_ids: list[str],
    before_request: Callable[[], None],
) -> dict[str, Any]:
    version = stream.get("vmm_version")
    if (stream.get("kind") != "ahv_effective_observer"
            or stream.get("separate_observer_credential_verified") is not True
            or stream.get("native_api_qualified") is not True
            or version not in ("v4.2", "v4.3")
            or not isinstance(vm_ids, list) or not 1 <= len(vm_ids) <= 32
            or len(vm_ids) != len(set(vm_ids))):
        raise CollectionFailure("independent_native_observer_not_commissioned")
    snapshots = []
    seen = set()
    for native_id in vm_ids:
        _uuid(native_id)
        before_request()
        response = exchange(
            stream, "/api/vmm/" + version + "/ahv/config/vms/" + native_id,
            {"X-Ntnx-Api-Key": secret(stream["credential_file"])},
        )
        if not isinstance(response, dict) or not isinstance(response.get("data"), dict):
            raise CollectionFailure("ahv_effective_vm_missing")
        vm = response["data"]
        if _uuid(vm.get("extId")) != native_id or native_id in seen:
            raise CollectionFailure("ahv_effective_vm_identity_changed")
        seen.add(native_id)
        cats, nics = vm.get("categories"), vm.get("nics")
        if not isinstance(cats, list) or not isinstance(nics, list):
            raise CollectionFailure("ahv_vm_network_or_category_unobserved")
        refs = []
        for category in cats:
            if not isinstance(category, dict):
                raise CollectionFailure("ahv_vm_category_reference_unresolved")
            refs.append(_uuid(category.get("extId")))
        if len(refs) != len(set(refs)):
            raise CollectionFailure("ahv_duplicate_vm_category")
        ports = []
        for nic in nics:
            if not isinstance(nic, dict) or not nic.get("extId"):
                raise CollectionFailure("ahv_native_nic_identity_unresolved")
            ports.append(_uuid(nic["extId"]))
        snapshots.append({
            "native_vm_id": native_id, "category_ids": sorted(refs),
            "native_nic_ids": sorted(ports),
            "native_revision": fingerprint(vm),
        })
    return {
        "source": "independent_native_observer",
        "native_write_authorized": False,
        "qualification_level": "E3_observation_only",
        "vm_categories": snapshots,
        "raw_snapshot_sha256": fingerprint(snapshots),
        "holds": ["ahv_microseg_attachment_and_service_enforcement_e4_required"],
    }
