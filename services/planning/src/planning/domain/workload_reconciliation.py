"""Compose authenticated Catalogue, Inventory and Assurance evidence for one VM.

No browser-selected identity or API-declared capability is treated as proof.
Collection coverage and E3/E4 still have distinct owners and must be re-read
before effects; this projection cannot grant a native operation.
"""

from copy import deepcopy
from typing import Any

from planning.domain.model import Rejected, digest
from planning.domain.source_intent_reconciliation import reconcile


def evaluate(
    scope: dict[str, str], catalogue: dict[str, Any],
    inventory: dict[str, Any], selected: dict[str, Any],
    flow: dict[str, Any] | None, now: int,
) -> dict[str, Any]:
    current = catalogue["intent"]
    link = inventory.get("catalogue_binding")
    if not isinstance(link, dict):
        raise Rejected("catalogue_native_workload_link_required", 423)
    if (link.get("application_id") != scope["application_id"]
            or link.get("environment_id") != scope["environment_id"]
            or link.get("revision_id") != catalogue["revision_id"]
            or link.get("intent_sha256") != catalogue["intent_sha256"]):
        raise Rejected("catalogue_native_workload_scope_changed", 423)
    if (
        inventory.get("current") is not True
        or not isinstance(inventory.get("confirmed_by"), str)
        or not inventory["confirmed_by"]
        or selected.get("review") != {
            "revision": inventory.get("revision"), "digest": inventory.get("digest")
        }
        or any(inventory.get(side, {}).get("profile_sha256")
               != selected.get(side, {}).get("profile_sha256")
               for side in ("source", "target"))
    ):
        raise Rejected("catalogue_native_review_not_current", 423)
    observed = inventory.get("source_observation")
    if not isinstance(observed, dict):
        raise Rejected("inventory_source_observation_required", 423)
    if observed.get("observation_sha256") != digest({
        key: value for key, value in observed.items()
        if key != "observation_sha256"
    }):
        raise Rejected("inventory_source_observation_changed", 423)
    if (observed.get("source_identity_sha256")
            != inventory["source"]["native_identity_sha256"]
            or observed.get("profile_sha256") != inventory["source"]["profile_sha256"]
            or observed.get("installed_tuple_sha256") != inventory["source"]["tuple_sha256"]
            or observed.get("native_write_authorized") is not False):
        raise Rejected("inventory_native_profile_identity_changed", 423)
    matches = [
        row for row in current["workloads"] if row["id"] == link.get("workload_id")
    ]
    if len(matches) != 1:
        raise Rejected("catalogue_native_logical_workload_missing", 423)
    workload = matches[0]
    disk_bindings, nic_bindings = link["disk_mappings"], link["nic_mappings"]
    if (not isinstance(disk_bindings, list) or not isinstance(nic_bindings, list)
            or {row["logical_device_id"] for row in disk_bindings}
                != {row["id"] for row in workload["disks"]}
            or {row["logical_device_id"] for row in nic_bindings}
                != {row["id"] for row in workload["nics"]}):
        raise Rejected("catalogue_native_logical_devices_changed", 423)
    # Inventory's confirmed review independently maps native disks to named
    # datasets. Catalogue supplies the logical dataset owner and membership.
    # One dataset may cover several native disks; every disk must be covered.
    expected_datasets = {
        row["id"] for row in current["datasets"]
        if row["owner_id"] == workload["id"]
    }
    reviewed_datasets = inventory["datasets"]
    by_dataset = {row["id"]: row for row in reviewed_datasets}
    disk_keys = {row["logical_device_id"]: row["native_key"] for row in disk_bindings}
    data_ok = (
        len(by_dataset) == len(reviewed_datasets)
        and set(by_dataset) == expected_datasets
        and all(
            disk["dataset_id"] in by_dataset
            and disk_keys[disk["id"]] in by_dataset[disk["dataset_id"]]["disk_keys"]
            for disk in workload["disks"]
        )
        and all(
            key in set(disk_keys.values()) for row in reviewed_datasets
            for key in row["disk_keys"]
        )
    )
    # Reuse the exact, independent flow E4 approval from the application-flow
    # admission verifier. An assertion without source and target profile binds
    # is never enough to establish effective network equivalence.
    flow_current = (
        isinstance(flow, dict)
        and flow.get("level") == "E4"
        and flow.get("decision") == "accepted"
        and flow.get("revoked") is False
        and flow.get("intent_sha256") == catalogue["intent_sha256"]
        and flow.get("source_profile_sha256") == selected["source"]["profile_sha256"]
        and flow.get("target_profile_sha256") == selected["target"]["profile_sha256"]
        and type(flow.get("expires_at")) is int
        and flow["expires_at"] > now
    )
    profile = deepcopy(observed)
    profile["owner_dataset_coverage_sha256"] = digest(current["datasets"]) if data_ok else None
    profile["owner_dataset_coverage_current"] = data_ok
    profile["network_semantics_sha256"] = (
        digest(workload["nics"]) if flow_current else None
    )
    profile["network_semantics_independently_verified"] = flow_current
    association = {
        "workload_id": workload["id"],
        "catalogue_digest": catalogue["intent_sha256"],
        "source_identity_sha256": observed["source_identity_sha256"],
        "owner_confirmed": True,
        "native_generation_id": observed["generation_id"],
        "native_profile_sha256": observed["profile_sha256"],
        "installation_id": observed["installation_id"],
        "native_scope": observed["native_scope"],
        "evidence_sha256": digest({
            "review": selected["review"], "confirmed_by": inventory["confirmed_by"],
            "mapping": link, "observation": observed["observation_sha256"],
        }),
        "expires_at": observed["expires_at"],
        "disk_mappings": disk_bindings,
        "nic_mappings": nic_bindings,
    }
    result = reconcile(current, catalogue["intent_sha256"], [association], [profile], now, flow)
    # Reconcile the selected VM only, not a fabricated match for every other
    # Catalogue workload. Multi-VM applications require one confirmed native
    # association and current review per workload before application admission.
    selected_result = next(
        (row for row in result["workloads"] if row["workload_id"] == workload["id"]), None
    )
    if selected_result is None:
        raise Rejected("catalogue_native_workload_resolution_missing", 423)
    other_holds = [row for row in result["holds"]
                   if not row.startswith(workload["id"] + ":")]
    record = {
        "schema_version": 1, "workload_id": workload["id"],
        "catalogue_revision_id": catalogue["revision_id"],
        "catalogue_sha256": catalogue["intent_sha256"],
        "source_identity_sha256": observed["source_identity_sha256"],
        "source_generation_id": observed["generation_id"],
        "source_profile_sha256": observed["profile_sha256"],
        "source_observation_sha256": observed["observation_sha256"],
        "native_review_sha256": inventory["digest"],
        "status": "matched" if selected_result["status"] == "matched"
                  and not other_holds else "held",
        "holds": sorted(set(selected_result["holds"] + other_holds)),
        "expires_at": min(observed["expires_at"], flow["expires_at"])
                      if flow_current else observed["expires_at"],
        "native_write_authorized": False,
    }
    record["reconciliation_sha256"] = digest(record)
    return record
