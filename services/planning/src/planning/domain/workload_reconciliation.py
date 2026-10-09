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
    source: dict[str, Any], flow: dict[str, Any] | None,
    target_sha256: str, now: int,
) -> bool:
    """Keep every native disk while attesting Catalogue datasetless disks.

    A null dataset ID is *not* an exclusion. Independently qualified E4
    attestation permits treating a separately inventoried native dataset as
    accounted for; native disk migration remains mandatory.
    """
    link = source["catalogue_binding"]
    expected = {d["id"]: d for d in workload["disks"]}
    mapping = link.get("disk_mappings")
    if (not isinstance(mapping, list) or len(mapping) != len(expected)
            or any(not isinstance(d, dict) for d in mapping)
            or {d.get("logical_device_id") for d in mapping} != set(expected)):
        return False
    native_keys = {m["logical_device_id"]: m.get("native_key") for m in mapping}
    if len(set(native_keys.values())) != len(native_keys):
        return False
    review = source.get("datasets")
    if not isinstance(review, list) or len(review) > 256:
        return False
    by_id = {d["id"]: d for d in review}
    if len(by_id) != len(review):
        return False
    declared = {d["id"] for d in intent["datasets"]}
    if len(declared) != len(intent["datasets"]):
        return False
    required = {disk.get("dataset_id") for disk in workload["disks"]
                if disk.get("dataset_id") is not None}
    if not required <= declared:
        return False
    # Dataset groups must cover every source disk exactly once. A separately
    # attested null-dataset disk may have a native reviewed group not declared
    # as a durable Catalogue dataset; no disk can disappear.
    keys = [key for item in review for key in item["disk_keys"]]
    if len(keys) != len(set(keys)) or set(keys) != set(native_keys.values()):
        return False
    dispositions = link.get("disk_dispositions", [])
    if not isinstance(dispositions, list):
        return False
    by_disk = {d.get("logical_device_id"): d for d in dispositions if isinstance(d, dict)}
    if len(by_disk) != len(dispositions):
        return False
    missing = {d["id"] for d in workload["disks"] if d.get("dataset_id") is None}
    if set(by_disk) != missing:
        return False
    qualified_cases = (
        flow.get("disk_disposition_cases") if isinstance(flow, dict)
        and flow.get("level") == "E4"
        and flow.get("decision") == "accepted"
        and flow.get("revoked") is False
        and flow.get("intent_sha256") == digest(intent)
        and type(flow.get("expires_at")) is int and flow["expires_at"] > now
        else None
    )
    if missing and (not isinstance(qualified_cases, list)
                    or len(qualified_cases) > 100):
        return False
    for disk in workload["disks"]:
        assigned = [group["id"] for group in review
                    if native_keys[disk["id"]] in group["disk_keys"]]
        if len(assigned) != 1:
            return False
        if disk.get("dataset_id") is not None:
            if assigned != [disk["dataset_id"]]:
                return False
            continue
        owner = by_disk[disk["id"]]
        case = [
            item for item in qualified_cases
            if isinstance(item, dict)
            and item.get("logical_device_id") == disk["id"]
            and item.get("workload_id") == workload["id"]
        ]
        if (len(case) != 1 or assigned[0] in declared
                or owner.get("native_key") != native_keys[disk["id"]]
                or owner.get("disposition") != "uncatalogued_attested"):
            return False
        receipt = case[0]
        if any(receipt.get(field) != owner.get(field)
               for field in ("disposition", "native_key",
                             "owner_approval_sha256", "impact_sha256")):
            return False
        if (receipt.get("source_profile_sha256") != source["source_observation"]["profile_sha256"]
                or receipt.get("target_profile_sha256") != target_sha256
                or receipt.get("level") != "E4"
                or receipt.get("decision") != "accepted"
                or receipt.get("revoked") is not False
                or type(receipt.get("observed_at")) is not int
                or not 0 <= now - receipt["observed_at"] <= 30
                or type(receipt.get("expires_at")) is not int
                or not now < receipt["expires_at"] <= flow["expires_at"]
                or not isinstance(receipt.get("evidence_sha256"), str)
                or len(receipt["evidence_sha256"]) != 64):
            return False
    return True


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
        # Independently observed guest firmware / Secure Boot can resolve
        # OpenStack's unverified server-metadata hints without promoting
        # a tenant-controlled metadata declaration to native fact.
        boot_cases = (
            flow.get("workload_boot_cases") if isinstance(flow, dict)
            and flow.get("level") == "E4"
            and flow.get("decision") == "accepted"
            and flow.get("revoked") is False
            and flow.get("intent_sha256") == catalogue["intent_sha256"]
            and flow.get("target_profile_sha256") == selected["target"]["profile_sha256"]
            and type(flow.get("expires_at")) is int
            and flow["expires_at"] > now else None
        )
        matching_boot = [
            case for case in boot_cases
            if isinstance(case, dict) and case.get("workload_id") == wid
        ] if isinstance(boot_cases, list) and len(boot_cases) <= 100 else []
        if len(matching_boot) == 1:
            proof = matching_boot[0]
            if (proof.get("source_profile_sha256") == observed["profile_sha256"]
                    and proof.get("level") == "E4"
                    and proof.get("decision") == "accepted"
                    and proof.get("revoked") is False
                    and proof.get("firmware") in {"efi", "bios"}
                    and type(proof.get("secure_boot")) is bool
                    and type(proof.get("observed_at")) is int
                    and 0 <= now - proof["observed_at"] <= 30
                    and type(proof.get("expires_at")) is int
                    and now < proof["expires_at"] <= flow["expires_at"]
                    and isinstance(proof.get("evidence_sha256"), str)
                    and len(proof["evidence_sha256"]) == 64):
                mapped["facts"] = deepcopy(mapped["facts"])
                mapped["facts"]["firmware"] = proof["firmware"]
                mapped["facts"]["secure_boot"] = proof["secure_boot"]
        mapped["owner_dataset_coverage_current"] = _dataset_coverage(
            intent, workload, source, flow, selected["target"]["profile_sha256"], now
        )
        mapped["owner_dataset_coverage_sha256"] = (
            digest(intent["datasets"]) if mapped["owner_dataset_coverage_current"] else None
        )
        # A passed allowed/denied traffic test for the selected route is NOT
        # proof of every VM's NIC placement. The independent E4 producer must
        # supply one current native-interface/path receipt per logical VM.
        cases = flow.get("workload_interface_cases") if isinstance(flow, dict) else None
        match = (
            [case for case in cases if isinstance(case, dict)
             and case.get("workload_id") == wid]
            if isinstance(cases, list) and len(cases) <= 100 else []
        )
        case = match[0] if len(match) == 1 else {}
        qualified_security = (
            isinstance(flow, dict)
            and flow.get("level") == "E4"
            and flow.get("decision") == "accepted"
            and flow.get("revoked") is False
            and flow.get("intent_sha256") == catalogue["intent_sha256"]
            and flow.get("target_profile_sha256") == selected["target"]["profile_sha256"]
            and type(flow.get("expires_at")) is int and flow["expires_at"] > now
            and len(match) == 1
            and case.get("source_profile_sha256") == observed["profile_sha256"]
            and case.get("target_profile_sha256") == selected["target"]["profile_sha256"]
            and case.get("logical_nics_sha256") == digest(workload["nics"])
            and case.get("level") == "E4"
            and case.get("decision") == "accepted"
            and case.get("revoked") is False
            and type(case.get("observed_at")) is int
            and 0 <= now - case["observed_at"] <= 30
            and type(case.get("expires_at")) is int
            and now < case["expires_at"] <= flow["expires_at"]
            and all(isinstance(case.get(key), str)
                    and len(case[key]) == 64
                    for key in ("native_path_set_sha256", "allowed_probe_sha256",
                                "denied_probe_sha256", "return_probe_sha256",
                                "isolation_probe_sha256", "evidence_sha256"))
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
            + ([case["expires_at"] for case in flow.get("workload_interface_cases", [])
                if isinstance(case, dict) and type(case.get("expires_at")) is int]
               if isinstance(flow, dict)
               and isinstance(flow.get("workload_interface_cases"), list) else [])
            + ([case["expires_at"] for case in flow.get("disk_disposition_cases", [])
                if isinstance(case, dict) and type(case.get("expires_at")) is int]
               if isinstance(flow, dict)
               and isinstance(flow.get("disk_disposition_cases"), list) else [])
            + ([case["expires_at"] for case in flow.get("workload_boot_cases", [])
                if isinstance(case, dict) and type(case.get("expires_at")) is int]
               if isinstance(flow, dict)
               and isinstance(flow.get("workload_boot_cases"), list) else [])
        ),
        "native_write_authorized": False,
    }
    record["reconciliation_sha256"] = digest(record)
    return record
