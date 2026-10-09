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
