"""P08 exact migration selection and ordered effect prerequisites.

Profiles are read from Inventory custody, not accepted as assertions of native
qualification. These contracts select effects; commissioned owners still authorize
and independently observe every effect through NativeWorkflow.
"""

from typing import Any

from lifecycle.domain.admission import digest
from lifecycle.domain.capability_definitions import AFTER as AFTER
from lifecycle.domain.capability_definitions import BEFORE as BEFORE
from lifecycle.domain.capability_definitions import (
    LEGACY_METHODS,
    METHOD_DELTA,
    RECOVERY_MODES,
    STAGES,
)
from lifecycle.domain.capability_definitions import MODES as MODES
from lifecycle.domain.capability_definitions import TERMINALS as TERMINALS
from lifecycle.domain.execution import Rejected, identity
from lifecycle.domain.native_workflow import checksum, exact, integer

METHODS = LEGACY_METHODS
RECOVERY = RECOVERY_MODES
DELTA = frozenset(
    method for method, kind in METHOD_DELTA.items() if kind in {"application", "file"}
)


def stages(migration: dict[str, Any]) -> tuple[str, ...]:
    try:
        return STAGES[(migration["mode"], migration["method"])]
    except KeyError:
        raise Rejected("unsupported_migration_recipe", 422) from None


def cases(plan: dict[str, Any], stage: str, phase: str) -> tuple[str, ...]:
    required = BEFORE[stage] if phase == "before" else AFTER[stage]
    if (
        stage == "final_sync"
        and phase == "before"
        and plan["migration"]["method"] == "VM_COLD_EXPORT"
    ):
        required = ("all_source_writers_fenced", "source_powered_off", "export_integrity")
    if stage == "fence_target" and phase == "before":
        required += ("prior_provider_requests_excluded",)
    if phase == "after":
        required += ("provider_requests_quiescent",)
    if plan["migration"]["method"] == "VM_COLD_EXPORT" and stage in {
        "export_copy",
        "convert_copy",
        "import_target",
        "transform_copy",
        "final_sync",
    }:
        required += ("source_powered_off", "all_source_writers_fenced")
    if plan["migration"]["mode"] == "rollback" and stage == "restore_source":
        required += ("no_target_divergence",)
    if plan["migration"]["mode"] == "reverse_recovery" and stage == "restore_source":
        required += ("accepted_target_changes_retained",)
    if plan["migration"].get("schema_version") == 4:
        from lifecycle.domain.migration_outcomes import requirements

        o = plan["migration"]["outcomes"]
        additional = requirements(o)
        expanded: list[str] = []
        for case in required:
            if case == "required_services":
                expanded.extend(k for k in additional if k.startswith("service_"))
            else:
                expanded.append(case)
            if case == "guest_ready":
                expanded.extend(k for k in additional if k.startswith("guest_"))
            if case == "policy_paths":
                expanded.extend(k for k in additional if k.startswith("security_rule_"))
            if case in {
                "final_integrity",
                "rehearsal_integrity",
                "recovered_integrity",
                "source_return_integrity",
            }:
                expanded.extend(k for k in additional if k.startswith("dataset_"))
        required = tuple(expanded)
        if o["source_platform"] != "vmware":
            required = tuple(
                {
                    "snapshot_bound": "source_capture_bound",
                    "ovf_bound": "source_manifest_bound",
                    "snapshot_owned": "source_capture_owned",
                    "snapshot_absent": "source_capture_absent",
                    "snapshot_consolidated": "source_capture_released",
                }.get(k, k)
                for k in required
            )
    return tuple(dict.fromkeys(required))


def validate(m: dict[str, Any], now: int) -> None:
    exact(
        m,
        {
            "schema_version",
            "review",
            "owner_inputs_sha256",
            "mode",
            "method",
            "source",
            "target",
            "datasets",
            "disks",
            "delta",
            "artifacts",
            "objectives",
            "rehearsal_sha256",
            "recovery_of_sha256",
        }
        | ({"destination_sha256"} if "destination_sha256" in m else set())
        | ({"outcomes"} if "outcomes" in m else set()),
    )
    if type(m["schema_version"]) is not int or m["schema_version"] != (
        4 if "outcomes" in m else 3 if "destination_sha256" in m else 2
    ):
        raise Rejected("invalid_migration_version", 422)
    review = exact(m["review"], {"revision", "digest"})
    integer(review["revision"], 1)
    checksum(review["digest"])
    checksum(m["owner_inputs_sha256"])
    if "destination_sha256" in m:
        checksum(m["destination_sha256"])
    if m["method"] not in METHODS or m["mode"] not in MODES:
        raise Rejected("migration_method_or_mode_not_selected", 422)
    for side in ("source", "target"):
        p = exact(
            m[side],
            {
                "profile_sha256",
                "native_identity_sha256",
                "tuple_sha256",
                "observed_at",
                "expires_at",
            },
        )
        for key in ("profile_sha256", "native_identity_sha256", "tuple_sha256"):
            checksum(p[key])
        if not 0 <= now - integer(p["observed_at"]) <= 3600 or integer(p["expires_at"]) <= now:
            raise Rejected("migration_profile_stale", 423)
    if m["source"]["native_identity_sha256"] == m["target"]["native_identity_sha256"]:
        raise Rejected("migration_copy_required", 422)
    datasets = m["datasets"]
    if (
        not isinstance(datasets, list)
        or not 1 <= len(datasets) <= 256
        or len({identity(d) for d in datasets}) != len(datasets)
    ):
        raise Rejected("migration_datasets_incomplete", 422)
    disks = m["disks"]
    if not isinstance(disks, list) or not 1 <= len(disks) <= 32:
        raise Rejected("migration_disk_inventory_required", 422)
    seen: set[str] = set()
    targets: set[str] = set()
    covered: set[str] = set()
    for d in disks:
        exact(d, {"source_disk_sha256", "target_key", "capacity_bytes", "format", "datasets"})
        checksum(d["source_disk_sha256"])
        identity(d["target_key"])
        integer(d["capacity_bytes"], 1)
        if (
            d["source_disk_sha256"] in seen
            or d["target_key"] in targets
            or d["format"] not in {"vmdk", "raw", "qcow2"}
        ):
            raise Rejected("migration_disk_mapping_ambiguous", 422)
        seen.add(d["source_disk_sha256"])
        targets.add(d["target_key"])
        if not isinstance(d["datasets"], list) or len(set(d["datasets"])) != len(d["datasets"]):
            raise Rejected("migration_dataset_mapping_invalid", 422)
        covered.update(identity(i) for i in d["datasets"])
    if covered != set(datasets):
        raise Rejected("migration_datasets_incomplete", 422)
    artifacts = exact(
        m["artifacts"], {"capture", "transfer", "conversion", "guest", "delta", "recovery"}
    )
    for value in artifacts.values():
        checksum(value)
    if "outcomes" in m:
        from lifecycle.domain.migration_outcomes import validate_outcomes

        validate_outcomes(m["outcomes"], m, artifacts)
    delta = exact(m["delta"], {"kind", "requires_running_guest", "qualification_sha256"})
    expected = METHOD_DELTA[m["method"]]
    if delta["kind"] != expected or type(delta["requires_running_guest"]) is not bool:
        raise Rejected("migration_delta_method_mismatch", 422)
    checksum(delta["qualification_sha256"])
    if expected == "none" and delta["requires_running_guest"]:
        raise Rejected("cold_source_cannot_supply_guest_delta", 422)
    objectives = exact(
        m["objectives"],
        {"owner_id", "acceptance_sha256", "max_outage_seconds", "max_data_loss_bytes"},
    )
    identity(objectives["owner_id"])
    checksum(objectives["acceptance_sha256"])
    integer(objectives["max_outage_seconds"])
    integer(objectives["max_data_loss_bytes"])
    if m["mode"] == "cutover":
        checksum(m["rehearsal_sha256"])
    elif m["rehearsal_sha256"] is not None:
        raise Rejected("unexpected_migration_rehearsal", 422)
    if m["mode"] in RECOVERY:
        checksum(m["recovery_of_sha256"])
    elif m["recovery_of_sha256"] is not None:
        raise Rejected("unexpected_migration_recovery", 422)


def recovery_matches(original: dict[str, Any], replacement: dict[str, Any]) -> bool:
    """Recovery can change authority/artifacts, but cannot switch datasets or migration method."""
    if "outcomes" in original:
        before, after = original["outcomes"], replacement.get("outcomes", {})
        if any(
            before[key] != after.get(key)
            for key in ("source_platform", "target_platform", "datasets")
        ):
            return False
        # Recovery may replace the target implementation under a fresh approval,
        # but cannot silently remove a security objective or change its meaning.
        if {r["id"]: r["semantics_sha256"] for r in before["security"]} != {
            r["id"]: r["semantics_sha256"] for r in after.get("security", [])
        }:
            return False
    keys = ("method", "datasets", "disks")
    return all(digest(original[k]) == digest(replacement[k]) for k in keys) and all(
        original[side][key] == replacement[side][key]
        for side in ("source", "target")
        for key in ("native_identity_sha256", "tuple_sha256")
    )


def current_profiles(plan: dict[str, Any], evidence: Any, now: int) -> None:
    """Check the actual authenticated Inventory input, not just a current=true assertion."""
    m = plan["migration"]
    if not isinstance(evidence, dict):
        raise Rejected("current_migration_review_required", 423)
    expected = {
        "tenant_id": plan["scope"]["tenant_id"],
        "site_id": plan["scope"]["site_id"],
        "revision": m["review"]["revision"],
        "digest": m["review"]["digest"],
        "method": m["method"],
        "source": m["source"],
        "target": m["target"],
        "objectives": m["objectives"],
        "current": True,
        "native_write_authorized": False,
    }
    if any(digest(evidence.get(k)) != digest(v) for k, v in expected.items()):
        raise Rejected("migration_review_binding_changed", 423)
    if digest(evidence.get("owner_inputs")) != m["owner_inputs_sha256"]:
        raise Rejected("migration_owner_inputs_changed", 423)
    destination = evidence.get("destination")
    if (
        (destination is not None) != ("destination_sha256" in m)
        or destination is not None
        and digest(destination) != m["destination_sha256"]
    ):
        raise Rejected("migration_destination_mapping_changed", 423)
    for side in ("source", "target"):
        if m[side]["expires_at"] <= now:
            raise Rejected("migration_profile_stale", 423)
    datasets, disks = evidence.get("datasets"), evidence.get("disks")
    if (
        not isinstance(datasets, list)
        or not isinstance(disks, list)
        or not all(isinstance(d, dict) for d in [*datasets, *disks])
    ):
        raise Rejected("migration_inventory_incomplete", 423)
    if len(datasets) != len(m["datasets"]) or {d.get("id") for d in datasets} != set(m["datasets"]):
        raise Rejected("migration_datasets_incomplete", 423)
    observed = {d.get("native_sha256"): d for d in disks}
    if len(observed) != len(disks) or set(observed) != {
        d["source_disk_sha256"] for d in m["disks"]
    }:
        raise Rejected("migration_disks_incomplete", 423)
    for d in m["disks"]:
        native = observed[d["source_disk_sha256"]]
        covered = {v["id"] for v in datasets if native.get("key") in v.get("disk_keys", [])}
        if (
            native.get("capacity_bytes") != d["capacity_bytes"]
            or covered != set(d["datasets"])
            or d["format"] not in evidence.get("target_disk_formats", [])
        ):
            raise Rejected("migration_disk_mapping_changed", 423)
