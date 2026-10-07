"""Compile migration profile bindings from an authenticated current Inventory review."""

from typing import Any

from planning.domain.model import Rejected, digest, identifier, integer, sha, shape


def bind_migration(
    inputs: dict[str, Any], mapping: list[dict[str, Any]], now: int
) -> dict[str, Any]:
    if inputs.get("current") is not True or inputs.get("native_write_authorized") is not False:
        raise Rejected("current_migration_review_required", 409)
    for side in ("source", "target"):
        profile = inputs[side]
        if (
            not 0 <= now - integer(profile["observed_at"]) <= 3600
            or integer(profile["expires_at"]) <= now
        ):
            raise Rejected("migration_profile_stale", 409)
    observed = {sha(d["native_sha256"]): d for d in inputs["disks"]}
    if not isinstance(mapping, list) or len(mapping) != len(observed) or not mapping:
        raise Rejected("migration_disks_incomplete", 422)
    seen, targets, disks = set(), set(), []
    for item in mapping:
        shape(item, {"source_disk_sha256", "target_key", "format"})
        key, target = sha(item["source_disk_sha256"]), identifier(item["target_key"])
        if (
            key not in observed
            or key in seen
            or target in targets
            or item["format"] not in {"raw", "qcow2", "vmdk"}
            or item["format"] not in inputs["target_disk_formats"]
        ):
            raise Rejected("migration_disk_mapping_invalid", 422)
        seen.add(key)
        targets.add(target)
        disk = observed[key]
        datasets = [d["id"] for d in inputs["datasets"] if disk["key"] in d["disk_keys"]]
        if not datasets:
            raise Rejected("migration_datasets_incomplete", 422)
        disks.append(
            {
                **item,
                "capacity_bytes": integer(disk["capacity_bytes"], 1),
                "datasets": sorted(datasets),
            }
        )
    return {
        "review": {"revision": integer(inputs["revision"], 1), "digest": sha(inputs["digest"])},
        "method": inputs["method"],
        "source": inputs["source"],
        "target": inputs["target"],
        "datasets": sorted(d["id"] for d in inputs["datasets"]),
        "disks": sorted(disks, key=lambda d: d["source_disk_sha256"]),
        "objectives": inputs["objectives"],
        "owner_inputs_sha256": digest(inputs["owner_inputs"]),
    }
