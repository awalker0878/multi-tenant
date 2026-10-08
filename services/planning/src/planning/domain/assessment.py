"""Requirement-specific interpretation of separately pinned observations and evidence."""

from typing import Any

from planning.domain.capability_definitions import STRATEGIES
from planning.domain.matching import matches
from planning.domain.model import ACTIONS, DIMENSIONS, Rejected, digest, integer
from planning.domain.qualification import verified


def requirements(intent: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand structural intent, retaining arbitrary requirements as explicit unknowns."""
    rows: list[dict[str, Any]] = []

    def add(key: str, value: Any, source: str, strength: str = "required") -> None:
        rows.append({"key": key, "value": value, "source": source, "strength": strength})

    for required in intent["requirements"]:
        add(required["key"], required["value"], "application", required["strength"])
    workloads = intent["workloads"]
    if not 1 <= len(workloads) <= 50:
        raise Rejected("workload_bound")
    for w in workloads:
        source = w["id"]
        for required in w["requirements"]:
            add(required["key"], required["value"], source, required["strength"])
        for key in ("architecture",):
            add("compute." + key, w["compute"][key], source)
        for key in ("os", "image", "firmware", "secure_boot", "hardening_profile"):
            add("guest." + key, w["guest"][key], source)
        add("placement.tenant_isolation", True, source)
        add("placement.domain_isolation", True, source)
        add("placement.zone_allowed", True, source)
        add(
            "placement.failure_domain." + w["failure_domain"]["mode"],
            True,
            source,
            w["failure_domain"]["strength"],
        )
        for disk in w["disks"]:
            add("storage.class", disk["storage_class"], disk["id"])
            add("storage.encryption", disk["encryption"], disk["id"])
        for nic in w["nics"]:
            add("network.class", nic["network_class"], nic["id"])
            for family in nic["address_families"]:
                add("network.family", family, nic["id"])
            add("network.address_intent", nic["address_intent"], nic["id"])
    for d in intent["datasets"]:
        add("data.consistency", d["consistency"], d["id"])
        add("recovery.method", d["recovery"]["method"], d["id"], d["recovery"]["strength"])
        for objective in ("rpo_seconds", "rto_seconds"):
            add(
                "recovery." + objective,
                d["recovery"][objective],
                d["id"],
                d["recovery"]["strength"],
            )
    for service in intent["services"]:
        add("service." + service["name"] + ".owner", service["owner_id"], service["workload_id"])
        for required in service["requirements"]:
            add(required["key"], required["value"], service["workload_id"], required["strength"])
    for dep in intent["dependencies"]:
        if dep["kind"] == "communication":
            add(
                "network.controlled_interface"
                if dep["controlled_interface"]
                else "network.internal",
                {k: dep[k] for k in ("from", "to", "protocol", "port")},
                dep["from"],
                dep["strength"],
            )
    if len(rows) > 800:
        raise Rejected("requirement_bound")
    return rows


def assess(
    intent: dict[str, Any],
    destination: dict[str, Any],
    profile: dict[str, Any],
    policy: dict[str, Any],
    qualification: dict[str, Any],
    action: str,
    method: str,
    now: int,
) -> dict[str, Any]:
    if action not in ACTIONS or method not in STRATEGIES:
        raise Rejected("unsupported_method")
    findings: list[dict[str, Any]] = []

    def finding(
        key: str,
        status: str,
        reason: str,
        remediation: str,
        source: str = "destination",
        mandatory: bool = True,
    ) -> None:
        findings.append(
            {
                "requirement": key,
                "source": source,
                "status": status,
                "reason": reason,
                "remediation": remediation,
                "mandatory": mandatory,
            }
        )

    bindings = {
        "inventory": digest(destination),
        "profile": profile["digest"],
        "policy": digest(policy),
        "qualification": digest(qualification),
        "intent": digest(intent),
    }
    for key, ok, reason in (
        ("inventory.current", destination["current"] is True, "generation_superseded"),
        ("inventory.complete", destination["completion"] == "complete", "partial_observation"),
        ("inventory.fresh", integer(destination["expires_at"]) > now, "facts_expired"),
        ("inventory.identity", not destination["holds"], "observation_hold"),
        (
            "installed_identity",
            destination["installed_provenance"] == "observed",
            "installed_tuple_only_declared",
        ),
        ("policy.fresh", policy["expires_at"] > now, "policy_expired"),
    ):
        finding(
            key,
            "eligible" if ok else "unknown",
            "verified" if ok else reason,
            "Refresh and independently verify this exact destination input.",
        )
    if destination["platform"] != profile["platform"]:
        finding(
            "profile.platform", "blocked", "profile_tuple_mismatch", "Select the exact profile."
        )
    if not destination["installed_tuple"]:
        finding(
            "installed_identity", "unknown", "installed_tuple_missing", "Observe the full tuple."
        )
    expected = {
        "tenant_id": destination["tenant_id"],
        "site_id": destination["site_id"],
        "endpoint_id": destination["endpoint_id"],
        "native_scope": destination["native_scope"],
        "installed_tuple": destination["installed_tuple"],
        "action": action,
        "method": method,
        "profile_digest": profile["digest"],
        "artifacts": policy["artifacts"],
    }
    verification = qualification.get("verification") or {}
    qualified = (
        verified(qualification, now)
        and digest(qualification.get("scope")) == digest(expected)
        and qualification.get("status") == "qualified"
        and qualification.get("evidence_level") in {"E3", "E4"}
        and qualification.get("expires_at", 0) > now
        and qualification.get("revoked") is False
        and bool(qualification.get("evidence_refs"))
    )
    finding(
        "qualification.exact_tuple",
        "eligible" if qualified else "unknown",
        "qualified_exact_scope" if qualified else "exact_tuple_qualification_missing_or_stale",
        "Assurance must qualify the exact operation, method, tuple, scope and artifacts.",
    )
    observations = destination["dimensions"]
    for dimension in DIMENSIONS:
        declaration = next(
            row["declaration"] for row in profile["dimensions"] if row["dimension"] == dimension
        )
        status, reason = "eligible", "observed_and_qualified"
        if declaration["status"] == "unsupported":
            status, reason = "blocked", "adapter_unsupported"
        elif declaration["status"] != "declared" or action not in declaration["operations"]:
            status, reason = "unknown", "adapter_declaration_missing"
        elif observations.get(dimension) != "observed":
            status, reason = "unknown", "dimension_not_observed"
        elif not qualified or dimension not in qualification.get("dimensions", []):
            status, reason = "unknown", "dimension_not_qualified"
        finding(dimension, status, reason, "Supply current observations and exact scoped evidence.")
    requested = requirements(intent) + [dict(r, source="policy") for r in policy["requirements"]]
    # Custody/location/isolation controls cannot be omitted by an empty policy.
    requested += [
        {"key": key, "value": True, "source": "baseline", "strength": "required"}
        for key in (
            "sovereignty.location",
            "sovereignty.custody",
            "sovereignty.data_path",
            "placement.tenant_isolation",
            "placement.domain_isolation",
        )
    ]
    observed = destination["capabilities"]
    supported = qualification.get("capabilities", {}) if qualified else {}
    expiries = [
        destination["expires_at"],
        policy["expires_at"],
        min(qualification["expires_at"], verification["expires_at"])
        if qualified
        else destination["expires_at"],
    ]
    for row in requested:
        key, value = row["key"], row["value"]
        mandatory = row["strength"] == "required"
        observation, support = observed.get(key), supported.get(key)
        if matches(key, value, []) is None:
            status, reason = "unknown", "requirement_definition_unregistered"
        elif observation is None:
            status, reason = "unknown", "mandatory_evidence_missing"
        # Observation safety is evaluated independently of qualification. A lab
        # waiver must never mask stale/unsupported facts or unresolved dependencies.
        elif observation.get("status") == "unsupported":
            status, reason = "blocked", "requirement_unsupported"
        elif observation.get("status") != "observed":
            status, reason = "unknown", "requirement_evidence_unassessed"
        elif observation.get("expires_at", 0) <= now:
            status, reason = "unknown", "requirement_observation_expired"
        elif not matches(key, value, observation.get("values", [])):
            status, reason = "blocked", "constraint_not_satisfied"
        elif observation.get("dependencies"):
            status, reason = "conditional", "dependency_requires_confirmation"
        elif support is None:
            status, reason = "unknown", "requirement_not_qualified"
        elif support.get("status") == "unsupported":
            status, reason = "blocked", "requirement_unsupported"
        elif support.get("status") != "supported":
            status, reason = "unknown", "requirement_evidence_unassessed"
        elif support.get("expires_at", 0) <= now:
            status, reason = "unknown", "requirement_qualification_expired"
        elif not matches(key, value, support.get("values", [])):
            status, reason = "blocked", "constraint_not_satisfied"
        elif support.get("dependencies"):
            status, reason = "conditional", "dependency_requires_confirmation"
        else:
            status, reason = "eligible", "requirement_observed_and_qualified"
            if mandatory:
                expiries.extend((observation["expires_at"], support["expires_at"]))
        finding(
            key,
            status,
            reason,
            "Resolve this requirement with its service or evidence owner, then reassess.",
            row["source"],
            mandatory,
        )
    demand = {
        "vcpus": sum(w["compute"]["vcpus"] for w in intent["workloads"]),
        "memory_mib": sum(w["compute"]["memory_mib"] for w in intent["workloads"]),
        "storage_gib": sum(d["size_gib"] for w in intent["workloads"] for d in w["disks"]),
        "addresses": sum(len(w["nics"]) for w in intent["workloads"]),
    }
    for kind, amount in demand.items():
        capacity = destination["capacity"].get(kind)
        if capacity is not None:
            integer(capacity)
        status = "unknown" if capacity is None else "eligible" if capacity >= amount else "blocked"
        finding(
            "capacity." + kind,
            status,
            "capacity_unobserved"
            if capacity is None
            else "observed_capacity_only"
            if status == "eligible"
            else "observed_capacity_insufficient",
            "Lifecycle must acquire authoritative owner receipts.",
        )
    mandatory_states = {f["status"] for f in findings if f["mandatory"]}
    state = next(
        (s for s in ("blocked", "unknown", "conditional") if s in mandatory_states), "eligible"
    )
    return {
        "site_id": destination["site_id"],
        "endpoint_id": destination["endpoint_id"],
        "generation_id": destination["generation_id"],
        "platform": destination["platform"],
        "status": state,
        "operationally_eligible": state == "eligible",
        "findings": findings,
        "input_digests": bindings,
        "demand": demand,
        "reserved": False,
        "expires_at": min(expiries),
    }
