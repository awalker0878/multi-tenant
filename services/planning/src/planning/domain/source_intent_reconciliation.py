"""Compare Catalogue logical desired workloads to Inventory-observed source VMs.

The caller must obtain immutable intent and current confirmed native observations
from their respective authenticated owners. A browser-selected VM name is never
an identity join. This read-only comparison cannot alter Catalogue or Inventory.
"""

import hashlib
import json
from typing import Any

from planning.domain.model import Rejected, digest


def reconcile(
    intent: dict[str, Any], catalogue_digest: str, links: list[dict[str, Any]],
    profiles: list[dict[str, Any]], now: int,
    flow_e4: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if (not isinstance(intent, dict) or not isinstance(intent.get("workloads"), list)
            or not 1 <= len(intent["workloads"]) <= 50
            or not isinstance(links, list) or len(links) > 50
            or not isinstance(profiles, list) or len(profiles) > 50):
        raise Rejected("source_intent_reconciliation_invalid", 422)
    # The digest must identify the exact immutable Catalogue document rather
    # than a caller-supplied label that merely matches the mapping receipts.
    if hashlib.sha256(json.dumps(
        intent, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).replace("\u2028", "\\u2028").replace("\u2029", "\\u2029").encode()).hexdigest() != catalogue_digest:
        raise Rejected("source_intent_catalogue_document_changed", 423)
    desired = intent["workloads"]
    by_id = {w["id"]: w for w in desired}
    if len(by_id) != len(desired):
        raise Rejected("source_intent_workload_ambiguous", 423)
    bindings: dict[str, dict[str, Any]] = {}
    native_ids: set[str] = set()
    for item in links:
        logical = item.get("workload_id")
        native_identity = item.get("source_identity_sha256")
        if (logical not in by_id or logical in bindings
                or not isinstance(native_identity, str) or len(native_identity) != 64
                or native_identity in native_ids):
            raise Rejected("source_intent_link_ambiguous", 423)
        bindings[logical] = item
        native_ids.add(native_identity)
    observations: dict[str, dict[str, Any]] = {}
    for observation in profiles:
        identity = observation.get("source_identity_sha256")
        if (not isinstance(identity, str) or identity in observations
                or identity not in native_ids):
            raise Rejected("source_intent_native_identity_ambiguous", 423)
        observations[identity] = observation
    result_rows: list[dict[str, Any]] = []
    all_holds: list[str] = []
    for workload in desired:
        wid = workload["id"]
        holds: list[str] = []
        link = bindings.get(wid)
        p = observations.get(link["source_identity_sha256"]) if link else None
        if link is None or p is None:
            holds.append("confirmed_native_workload_link_missing")
        else:
            if (link.get("catalogue_digest") != catalogue_digest
                    or link.get("owner_confirmed") is not True
                    or link.get("native_generation_id") != p.get("generation_id")
                    or link.get("native_profile_sha256") != p.get("profile_sha256")
                    or link.get("installation_id") != p.get("installation_id")
                    or link.get("native_scope") != p.get("native_scope")
                    or not isinstance(link.get("evidence_sha256"), str)
                    or len(link["evidence_sha256"]) != 64
                    or type(link.get("expires_at")) is not int
                    or link["expires_at"] <= now):
                holds.append("source_identity_join_changed")
            if (p.get("current") is not True or type(p.get("expires_at")) is not int
                    or p["expires_at"] <= now or p.get("holds")):
                holds.append("native_source_generation_or_policy_held")
            facts = p.get("facts", {})
            if not isinstance(facts, dict):
                facts = {}
            compute = workload["compute"]
            if (facts.get("cpu") != compute["vcpus"]
                    or facts.get("memory_mb") != compute["memory_mib"]):
                holds.append("source_compute_intent_drift")
            expected_firmware = workload["guest"]["firmware"]
            if facts.get("firmware") != {"uefi": "efi", "bios": "bios"}[expected_firmware]:
                holds.append("source_guest_firmware_drift_or_unobserved")
            if facts.get("secure_boot") is not workload["guest"]["secure_boot"]:
                holds.append("source_secure_boot_setting_unobserved_or_changed")
            if (p.get("owner_dataset_coverage_sha256") != digest(intent.get("datasets", []))
                    or p.get("owner_dataset_coverage_current") is not True):
                holds.append("source_dataset_mapping_not_independently_confirmed")
            actual_disks = facts.get("disks")
            desired_disks = workload["disks"]
            native_disks = {
                row["key"]: row for row in actual_disks
                if isinstance(row, dict) and type(row.get("key")) is int
            } if isinstance(actual_disks, list) else {}
            mappings = link.get("disk_mappings")
            if (not isinstance(mappings, list)
                    or len(mappings) != len(desired_disks)
                    or not isinstance(actual_disks, list)
                    or len(native_disks) != len(actual_disks)
                    or len(actual_disks) != len(desired_disks)):
                holds.append("source_disk_set_differs_from_intent")
            else:
                logical_to_native = {
                    row.get("logical_device_id"): row.get("native_key")
                    for row in mappings if isinstance(row, dict)
                }
                if (len(logical_to_native) != len(mappings)
                        or set(logical_to_native) != {d["id"] for d in desired_disks}
                        or set(logical_to_native.values()) != set(native_disks)):
                    holds.append("source_disk_identity_ambiguous")
                else:
                    for disk in desired_disks:
                        actual = native_disks[logical_to_native[disk["id"]]]
                        if (actual.get("capacity_bytes") is None
                                or actual["capacity_bytes"] != disk["size_gib"] * 1024**3):
                            holds.append("source_disk_capacity_or_order_drift")
                            break
            nics = facts.get("nics")
            native_nics = {
                row["key"] for row in nics
                if isinstance(row, dict) and type(row.get("key")) is int
            } if isinstance(nics, list) else set()
            mappings = link.get("nic_mappings")
            if (not isinstance(nics, list)
                    or not isinstance(mappings, list)
                    or len(nics) != len(workload["nics"])
                    or len(mappings) != len(workload["nics"])):
                holds.append("source_nic_set_differs_from_intent")
            elif (len(native_nics) != len(nics)
                  or len({m.get("logical_device_id") for m in mappings
                          if isinstance(m, dict)}) != len(mappings)
                  or {m.get("logical_device_id") for m in mappings
                      if isinstance(m, dict)} != {n["id"] for n in workload["nics"]}
                  or {m.get("native_key") for m in mappings if isinstance(m, dict)}
                        != native_nics):
                holds.append("source_nic_identity_ambiguous")
            native = facts.get("native")
            identity = native.get("identity") if isinstance(native, dict) else None
            if (
                not isinstance(identity, dict)
                or identity.get("vm_id") is None
                or not any(identity.get(key) for key in (
                    "created", "generation_uuid", "instance_uuid",
                ))
            ):
                holds.append("native_incarnation_and_topology_not_observed")
            if (
                p.get("network_semantics_sha256") != digest(workload["nics"])
                or p.get("network_semantics_independently_verified") is not True
            ):
                holds.append("source_network_semantics_not_verified")
        status = "matched" if not holds else "held"
        result_rows.append({"workload_id": wid, "status": status, "holds": sorted(set(holds)),
                            "source_identity_sha256":
                            link["source_identity_sha256"] if link else None})
        all_holds += [wid + ":" + reason for reason in holds]
    if intent.get("dependencies"):
        if (not isinstance(flow_e4, dict) or flow_e4.get("level") != "E4"
                or flow_e4.get("decision") != "accepted"
                or flow_e4.get("intent_sha256") != catalogue_digest
                or flow_e4.get("revoked") is not False
                or type(flow_e4.get("expires_at")) is not int
                or flow_e4["expires_at"] <= now):
            all_holds.append("application_dependency_e4_validation_required")
    result = {
        "schema_version": 1, "catalogue_digest": catalogue_digest,
        "status": "matched" if not all_holds else "held",
        "workloads": result_rows, "holds": sorted(set(all_holds)),
        "evaluated_at": now, "native_write_authorized": False,
    }
    result["reconciliation_sha256"] = digest(result)
    return result
