"""Compare the *entire attested policy boundary*, not isolated allow/deny examples.

Only finite enumerated traffic classes with a qualified complete scope pass.
Wildcards and unknown classes are unqualified, rather than considered denied.
The provider resolver evaluates each class under source and target semantics.
An independent native receipt must confirm each predicted verdict.
"""
from typing import Any

from planning.domain.model import digest
from planning.domain.policy_resolvers import Unqualified, decision

MAX_BOUNDARY = 1024


def _scope(document: dict[str, Any], expected: str) -> bool:
    scope = document.get("boundary_scope")
    return isinstance(scope, dict) and (
        scope.get("complete") is True
        and scope.get("workload_set_sha256") == expected
        and isinstance(scope.get("native_revision"), str)
        and len(scope["native_revision"]) > 0
        and scope.get("unrestricted_wildcards") is False
        and scope.get("effective_rule_universe_complete") is True
        and scope.get("address_families") == ["ipv4", "ipv6"]
    )


def _verified(document: dict[str, Any], key: str, flow: dict[str, Any],
              verdict: str, now: int) -> bool:
    probes = document.get("boundary_probes")
    if not isinstance(probes, dict) or key not in probes:
        return False
    p = probes[key]
    return (isinstance(p, dict) and p.get("flow_sha256") == digest(flow)
            and p.get("outcome") == verdict
            and isinstance(p.get("native_receipt"), str)
            and bool(p["native_receipt"])
            and p.get("observer") == document.get("observer_principal")
            and p.get("observer") != document.get("writer_principal")
            and p.get("native_revision") == document["boundary_scope"]["native_revision"]
            and type(p.get("observed_at")) is int
            and 0 <= now - p["observed_at"] <= 30
            and type(p.get("expires_at")) is int
            and now < p["expires_at"] <= p["observed_at"] + 60)


def _partition(document: dict[str, Any], universe: str,
               class_ids: set[str]) -> bool:
    """External qualified closed-world partition bound to exact native rules.

    A few independent packet probes do not prove absence of extra permits.
    The native observer must separately attest a disjoint complete partition
    of every workload pair/port/protocol/IP-family class in the requested
    boundary. Wildcards or unenumerated ranges cannot be qualified.
    """
    proof = document.get("policy_partition")
    if not isinstance(proof, dict):
        return False
    rules = document.get("rules")
    native = {
        "rules": rules,
        "ports": document.get("ports"),
        "security_groups": document.get("security_groups"),
        "groups": document.get("groups"),
        "services": document.get("services"),
        "workloads": document.get("workloads"),
        "api_profile": document.get("api_profile"),
    }
    allowed = proof.get("permitted_class_ids")
    return (
        proof.get("schema_version") == 1
        and proof.get("mode") == "disjoint_effective_rule_partition"
        and proof.get("complete") is True
        and proof.get("independently_verified") is True
        and proof.get("observer") == document.get("observer_principal")
        and proof.get("observer") != document.get("writer_principal")
        and proof.get("universe_sha256") == universe
        and proof.get("native_rule_set_sha256") == digest(native)
        and proof.get("uncovered_classes") == 0
        and proof.get("unbounded_wildcards") is False
        and isinstance(proof.get("class_ids"), list)
        and len(proof["class_ids"]) == len(class_ids)
        and set(proof["class_ids"]) == class_ids
        and isinstance(allowed, list)
        and len(allowed) == len(set(allowed))
        and set(allowed) <= class_ids
        and proof.get("partition_sha256") == digest({
            "universe": universe,
            "native": digest(native),
            "classes": sorted(class_ids),
            "permitted": sorted(allowed),
        })
    )


def compare(source: dict[str, Any], target: dict[str, Any],
            boundary: dict[str, Any], now: int) -> dict[str, Any]:
    """Exact finite traffic universe: destination may not expand access.

    The independent observer must prove coverage completeness; no bounded
    sample is itself evidence of the absence of unknown permitted traffic.
    """
    result = {"status": "held", "native_write_authorized": False}
    if (not isinstance(boundary, dict) or boundary.get("schema_version") != 1
            or boundary.get("complete") is not True
            or not isinstance(boundary.get("classes"), list)
            or not 1 <= len(boundary["classes"]) <= MAX_BOUNDARY
            or not isinstance(boundary.get("workload_set_sha256"), str)
            or not _scope(source, boundary["workload_set_sha256"])
            or not _scope(target, boundary["workload_set_sha256"])
            or source["boundary_scope"].get("generation_id") ==
               target["boundary_scope"].get("generation_id")):
        return result | {"reason": "source_destination_boundary_not_complete"}
    class_ids = {
        row.get("id")
        for row in boundary["classes"]
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    universe = digest(sorted(class_ids))
    if not (_partition(source, universe, class_ids)
            and _partition(target, universe, class_ids)):
        return result | {"reason": "closed_world_policy_partition_unqualified"}
    seen: set[str] = set()
    allowed = []
    denied = []
    for case in boundary["classes"]:
        if (not isinstance(case, dict) or set(case) != {"id", "flow", "requirement"}
                or case.get("requirement") not in ("required", "forbidden", "observed")
                or not isinstance(case.get("flow"), dict)
                or not isinstance(case.get("id"), str)
                or case["id"] != digest(case["flow"]) or case["id"] in seen):
            return result | {"reason": "ambiguous_policy_boundary"}
        seen.add(case["id"])
        f = case["flow"]
        try:
            src_verdict, _ = decision(source, f)
            dst_verdict, _ = decision(target, f)
        except (Unqualified, KeyError, TypeError, ValueError):
            return result | {"reason": "provider_policy_boundary_unqualified"}
        if (
            (src_verdict == "allow") != (
                case["id"] in source["policy_partition"]["permitted_class_ids"]
            )
            or (dst_verdict == "allow") != (
                case["id"] in target["policy_partition"]["permitted_class_ids"]
            )
        ):
            return result | {"reason": "attested_native_partition_verdict_mismatch"}
        if (not _verified(source, case["id"], f, src_verdict, now)
                or not _verified(target, case["id"], f, dst_verdict, now)):
            return result | {"reason": "independent_policy_boundary_probe_missing"}
        if case["requirement"] == "required" and (
            src_verdict != "allow" or dst_verdict != "allow"
        ):
            return result | {"reason": "required_application_flow_not_maintained"}
        if case["requirement"] == "forbidden" and dst_verdict != "deny":
            return result | {"reason": "explicit_forbidden_flow_allowed"}
        if src_verdict == "deny" and dst_verdict == "allow":
            return result | {"reason": "destination_additional_access_detected"}
        (allowed if dst_verdict == "allow" else denied).append(case["id"])
    if not allowed or not denied:
        return result | {"reason": "positive_negative_boundary_incomplete"}
    return {"status": "qualified", "reason": None,
            "native_write_authorized": False,
            "boundary_sha256": digest(boundary),
            "allowed": sorted(allowed), "denied": sorted(denied)}
