"""Reconcile the complete application against authenticated Catalogue/Inventory/E4.

An application-wide match requires a distinct, current, owner-confirmed native
identity for every logical VM. One reviewed VM cannot imply its peers are ready.
"""

from copy import deepcopy
from typing import Any

from planning.domain.model import Rejected, digest
from planning.domain.source_intent_reconciliation import reconcile


def _dataset_coverage(
    intent: dict[str, Any], workload: dict[str, Any],
    source: dict[str, Any],
) -> bool:
    link = source["catalogue_binding"]
    mapping = link["disk_mappings"]
    expected = {d["id"]: d for d in workload["disks"]}
    if (not isinstance(mapping, list) or len(mapping) != len(expected)
            or {d["logical_device_id"] for d in mapping} != set(expected)):
        return False
    native_keys = {m["logical_device_id"]: m["native_key"] for m in mapping}
    review = source["datasets"]
    if not isinstance(review, list) or len(review) > 256:
        return False
    by_id = {d["id"]: d for d in review}
    if len(by_id) != len(review):
        return False
    required = {d["id"] for d in intent["datasets"]
                if d["owner_id"] == workload["id"]}
    if set(by_id) != required:
        return False
    # Check that the owner confirmed precisely one dataset for every mapped
    # disk. A reused native disk in two datasets is not independent coverage.
    return all(
        disk["dataset_id"] in by_id
        and [d["id"] for d in review
             if native_keys[disk["id"]] in d["disk_keys"]] == [disk["dataset_id"]]
        for disk in workload["disks"]
    ) and {
        key for d in review for key in d["disk_keys"]
    } == set(native_keys.values())


def evaluate(
    scope: dict[str, str], catalogue: dict[str, Any],
    inventory: dict[str, Any], selected: dict[str, Any],
    flow: dict[str, Any] | None, now: int,
) -> dict[str, Any]:
    intent = catalogue["intent"]
    reviews = inventory.get("source_associations")
    selected_link = inventory.get("catalogue_binding")
    if (not isinstance(reviews, list) or not 1 <= len(reviews) <= 100
            or not isinstance(selected_link, dict)):
        raise Rejected("catalogue_native_application_associations_required", 423)
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
    workloads = {row["id"]: row for row in intent["workloads"]}
    if len(workloads) != len(intent["workloads"]):
        raise Rejected("catalogue_native_logical_workload_ambiguous", 423)
    connections = []
    observations = []
    selected_seen = 0
    for source in reviews:
        link = source["catalogue_binding"]
        if (link.get("application_id") != scope["application_id"]
                or link.get("environment_id") != scope["environment_id"]
                or link.get("revision_id") != catalogue["revision_id"]
                or link.get("intent_sha256") != catalogue["intent_sha256"]):
            raise Rejected("catalogue_native_workload_scope_changed", 423)
        wid = link["workload_id"]
        if wid not in workloads:
            raise Rejected("catalogue_native_logical_workload_missing", 423)
        observed = source["source_observation"]
        owner_binding = source["source_binding"]
        if (
            not isinstance(observed, dict)
            or observed.get("observation_sha256") != digest({
                k: v for k, v in observed.items() if k != "observation_sha256"
            })
            or observed.get("source_identity_sha256") != owner_binding["native_identity_sha256"]
            or observed.get("profile_sha256") != owner_binding["profile_sha256"]
            or observed.get("installed_tuple_sha256") != owner_binding["tuple_sha256"]
            or observed.get("native_write_authorized") is not False
        ):
            raise Rejected("inventory_source_observation_changed", 423)
        if (source["revision"] == inventory["revision"]
                and source["digest"] == inventory["digest"]):
            selected_seen += 1
            if (wid != selected_link["workload_id"]
                    or observed["source_identity_sha256"]
                        != inventory["source"]["native_identity_sha256"]):
                raise Rejected("catalogue_native_selected_source_changed", 423)
        workload = workloads[wid]
        mapped = deepcopy(observed)
        mapped["current"] = observed["current"] is True and source["current"] is True
        mapped["owner_dataset_coverage_current"] = _dataset_coverage(
            intent, workload, source
        )
        mapped["owner_dataset_coverage_sha256"] = (
            digest(intent["datasets"]) if mapped["owner_dataset_coverage_current"] else None
        )
        qualified_security = (
            isinstance(flow, dict)
            and flow.get("level") == "E4"
            and flow.get("decision") == "accepted"
            and flow.get("revoked") is False
            and flow.get("intent_sha256") == catalogue["intent_sha256"]
            and flow.get("source_profile_sha256") == observed["profile_sha256"]
            and flow.get("target_profile_sha256") == selected["target"]["profile_sha256"]
            and type(flow.get("expires_at")) is int and flow["expires_at"] > now
        )
        mapped["network_semantics_independently_verified"] = qualified_security
        mapped["network_semantics_sha256"] = (
            digest(workload["nics"]) if qualified_security else None
        )
        connections.append({
            "workload_id": wid, "catalogue_digest": catalogue["intent_sha256"],
            "source_identity_sha256": observed["source_identity_sha256"],
            "owner_confirmed": source["current"] is True
                               and isinstance(source["confirmed_by"], str),
            "native_generation_id": observed["generation_id"],
            "native_profile_sha256": observed["profile_sha256"],
            "installation_id": observed["installation_id"],
            "native_scope": observed["native_scope"],
            "evidence_sha256": digest({
                "review": [source["revision"], source["digest"]],
                "confirmed_by": source["confirmed_by"],
                "mapping": link, "observation": observed["observation_sha256"],
            }),
            "expires_at": observed["expires_at"],
            "disk_mappings": link["disk_mappings"],
            "nic_mappings": link["nic_mappings"],
        })
        observations.append(mapped)
    if selected_seen != 1:
        raise Rejected("catalogue_native_selected_review_ambiguous", 423)
    resolved = reconcile(
        intent, catalogue["intent_sha256"], connections, observations, now, flow
    )
    profile = inventory["source_observation"]
    record = {
        "schema_version": 1,
        "catalogue_revision_id": catalogue["revision_id"],
        "catalogue_sha256": catalogue["intent_sha256"],
        "source_identity_sha256": profile["source_identity_sha256"],
        "source_generation_id": profile["generation_id"],
        "source_profile_sha256": profile["profile_sha256"],
        "source_observation_sha256": profile["observation_sha256"],
        "native_review_sha256": inventory["digest"],
        "status": resolved["status"],
        "workloads": resolved["workloads"],
        "holds": resolved["holds"],
        "expires_at": min(
            [row["expires_at"] for row in observations]
            + ([flow["expires_at"]] if isinstance(flow, dict)
               and type(flow.get("expires_at")) is int else [])
        ),
        "native_write_authorized": False,
    }
    record["reconciliation_sha256"] = digest(record)
    return record
