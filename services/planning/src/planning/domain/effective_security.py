"""Canonical E4 evaluation interface; native policy behavior lives in resolvers.

Only independent, current, version-scoped E4 source/target native documents are
eligible. In particular, v1's generic first-match implementation is removed:
NSX, AHV Microseg and Neutron do not share priority or attachment semantics.
"""
from typing import Any

from planning.domain.model import digest
from planning.domain.packet_paths import PathUnqualified, qualify as qualify_paths
from planning.domain.policy_resolvers import Unqualified, decision


def hold(reason: str) -> dict[str, Any]:
    return {"status": "held", "reason": reason, "native_write_authorized": False}


def fresh(document: dict[str, Any], now: int) -> bool:
    return (
        type(document.get("observed_at")) is int
        and type(document.get("expires_at")) is int
        and 0 <= now - document["observed_at"] <= 30
        and now < document["expires_at"] <= document["observed_at"] + 60
    )


def qualify(document: Any, flow: dict[str, Any], now: int) -> dict[str, Any]:
    """Return observed existing destination controls; this grants no write."""
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != 2
        or document.get("source") != "independent_native_observer"
        or not isinstance(document.get("observer_principal"), str)
        or not document["observer_principal"]
        or not isinstance(document.get("writer_principal"), str)
        or not document["writer_principal"]
        or document["observer_principal"] == document["writer_principal"]
        or not isinstance(document.get("topology_sha256"), str)
        or not document["topology_sha256"]
        or not fresh(document, now)
    ):
        return hold("independent_effective_security_v2_required")
    try:
        verdict, native_ref = decision(document, flow)
        if verdict != "allow" or not native_ref:
            return hold("native_effective_policy_denies_required_flow")
        path = qualify_paths(document, flow, now)
    except (Unqualified, PathUnqualified, TypeError, KeyError, ValueError) as exc:
        return hold(str(exc) if str(exc) else "native_policy_or_path_unqualified")
    return {
        "status": "qualified", "reason": None,
        "native_write_authorized": False,
        "effective_rule_native_ref": native_ref,
        "path_sha256": path["path_sha256"],
        "native_route_refs": path["native_route_refs"],
        "evidence_sha256": digest(document),
    }
