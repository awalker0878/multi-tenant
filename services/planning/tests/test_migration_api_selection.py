"""Immutable native API selection must not drift between plan creation and execution."""
from copy import deepcopy

import pytest

from planning.domain.migration_api_selection import pin
from planning.domain.model import Rejected, digest


def readiness() -> dict:
    return {
        "status": "eligible", "holds": [], "native_write_authorized": False,
        "expires_at": 160, "route_sha256": digest("route"),
        "release_sha256": digest("release"),
        "source": {"platform": "ahv", "profile_sha256": digest("source")},
        "target": {"platform": "openstack", "profile_sha256": digest("target")},
        "api_compatibility": {
            "operationally_eligible": True,
            "cases": [{
                "capability_id": "vm.disk.export", "side": "source",
                "criticality": "critical", "status": "eligible",
                "omission_accepted": False, "selected_api_family": "ahv.vmm",
                "selected_api_version": "v4.3",
                "evidence_sha256": digest("e3"),
                "expires_at": 130,
            }],
        },
    }


def test_exact_native_api_binding_is_stable_and_signed_into_plan_digest():
    current = readiness()
    pinned = pin(current, 100)
    assert pinned["operations"][0]["api_version"] == "v4.3"
    assert pinned["operations"][0]["evidence_sha256"] == digest("e3")
    assert pinned["selection_sha256"] == digest({
        k: v for k, v in pinned.items() if k != "selection_sha256"
    })
    assert pinned == pin(deepcopy(current), 100)
    for key, value in (
        ("selected_api_version", "v4.2"), ("evidence_sha256", digest("revoked")),
        ("expires_at", 120),
    ):
        changed = deepcopy(current)
        changed["api_compatibility"]["cases"][0][key] = value
        if key == "selected_api_version":
            with pytest.raises(Rejected, match="unimplemented"):
                pin(changed, 100)
        else:
            assert pin(changed, 100) != pinned
    with pytest.raises(Rejected, match="evidence_unbound"):
        pin(current, 130)


def test_apparent_eligible_route_cannot_pin_unqualified_native_api():
    for fault in ("status", "missing_evidence", "unqualified", "critical_omission"):
        changed = deepcopy(readiness())
        case = changed["api_compatibility"]["cases"][0]
        if fault == "status":
            changed["status"] = "held"
        elif fault == "missing_evidence":
            case["evidence_sha256"] = None
        elif fault == "unqualified":
            case["status"] = "unknown"
        else:
            case.update(omission_accepted=True, criticality="critical")
        with pytest.raises(Rejected):
            pin(changed, 100)
