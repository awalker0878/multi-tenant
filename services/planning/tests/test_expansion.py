"""Directed support, guest constraints and expiry never inherit adjacent-route evidence."""

from copy import deepcopy
from itertools import product
from typing import Any
from uuid import uuid4

import pytest

from planning.domain.expansion import (
    GUESTS,
    METHODS,
    RETEST,
    matrix,
    qualification_plan,
    route,
    tranche,
)
from planning.domain.model import DIMENSIONS, PLATFORMS, Rejected, digest


def tuple_for(platform: str) -> dict[str, Any]:
    return {
        "platform": platform,
        "installation_id": str(uuid4()),
        "profile_sha256": "a" * 64,
        "versions": {
            "platform": "synthetic",
            "api": "synthetic",
            "network": "synthetic",
            "storage": "synthetic",
        },
        "dimensions": {d: digest(d) for d in DIMENSIONS},
    }


def route_for(
    source: str = "vmware",
    target: str = "openstack",
    guest: str = "linux",
    method: str = "cold_export",
) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "source": tuple_for(source),
        "target": tuple_for(target),
        "guest": guest,
        "method": method,
        **{
            k + "_sha256": digest(k)
            for k in (
                "guest_profile",
                "topology",
                "data",
                "policy",
                "services",
                "recovery",
                "artifacts",
            )
        },
        "constraints": {
            "boot": "uefi",
            "disk_format": "qcow2",
            "driver_profile": "synthetic",
            "encryption": "synthetic",
            "guest_mutation": "prohibited" if guest == "appliance" else "copy_only",
            "data_consistency": "application",
            "writer_fencing": "a" * 64,
            "target_write_recovery": "b" * 64,
            "maximum_outage_seconds": 60,
            "maximum_data_loss_seconds": 0,
        },
        "requirement_ids": ["R26", "R27"],
        "exclusions": ["No native platform qualification"],
    }


def baseline() -> dict[str, Any]:
    rows = [route_for(a, b) for a, b in product(PLATFORMS, repeat=2)]
    return {
        "schema_version": 1,
        "id": str(uuid4()),
        "revision": 1,
        "release_sha256": "f" * 64,
        "owner_role": "synthetic qualification owner",
        "expires_at": 200,
        "routes": rows,
        "operations": ["power_on"],
        "deferred_directions": [],
        "retest_triggers": list(RETEST),
    }


@pytest.mark.parametrize(
    ("source", "target", "guest", "method"), product(PLATFORMS, PLATFORMS, GUESTS, METHODS)
)
def test_every_direction_guest_and_method_has_separate_plan(
    source: str, target: str, guest: str, method: str
) -> None:
    row = route_for(source, target, guest, method)
    plan = qualification_plan(row)
    assert plan["route_sha256"] == digest(row)
    assert plan["native_write_authorized"] is False
    assert ("Q08.05" in plan["cases"]) == (source == target)
    assert ("no_guest_mutation" in plan["checks"]) == (guest == "appliance")


def test_qualification_cannot_cross_direction_or_guest() -> None:
    value = baseline()
    selected = value["routes"][1]
    proof = {
        "route_sha256": digest(selected),
        "tranche_sha256": digest(value),
        "release_sha256": value["release_sha256"],
        "level": "E3",
        "decision": "accepted",
        "revoked": False,
        "expires_at": 180,
        "evidence_sha256": "d" * 64,
    }
    results = matrix(value, [proof], 100)
    qualified = [r for d in results for r in d["routes"] if r["native_qualified"]]
    assert len(qualified) == 1 and qualified[0]["route_id"] == selected["id"]
    assert not qualified[0]["operationally_accepted"]
    for change in (
        {"revoked": True},
        {"expires_at": 100},
        {"level": "E2"},
        {"release_sha256": "0" * 64},
    ):
        assert not any(
            r["native_qualified"] for d in matrix(value, [proof | change], 100) for r in d["routes"]
        )
    assert not any(
        r["native_qualified"] for d in matrix(value, [proof, proof], 100) for r in d["routes"]
    )
    changed = deepcopy(value)
    changed["routes"][1]["guest"] = "windows"
    assert not any(
        r["native_qualified"] for d in matrix(changed, [proof], 100) for r in d["routes"]
    )


def test_all_unselected_directions_must_be_explicit() -> None:
    value = baseline()
    removed = value["routes"].pop()
    with pytest.raises(Rejected, match="direction_coverage"):
        tranche(value)
    value["deferred_directions"] = [
        removed["source"]["platform"] + "->" + removed["target"]["platform"]
    ]
    assert matrix(value, [], 100)[-1]["state"] == "deferred"
    value["routes"].append(deepcopy(value["routes"][0]))
    with pytest.raises(Rejected, match="duplicate"):
        tranche(value)


def test_unsupported_mutation_and_incomplete_profiles_fail() -> None:
    row = route_for(guest="appliance")
    row["constraints"]["guest_mutation"] = "copy_only"
    with pytest.raises(Rejected, match="appliance"):
        route(row)
    row = route_for()
    del row["source"]["dimensions"]["security_edge"]
    with pytest.raises(Rejected, match="shape"):
        route(row)
