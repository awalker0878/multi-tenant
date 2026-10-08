"""Acceptance is independent for every guest, service, security rule and dataset."""

from copy import deepcopy
from typing import Any
from uuid import uuid4

import pytest
from test_migration import migration_plan

from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected
from lifecycle.domain.migration import cases, current_profiles, recovery_matches, validate
from lifecycle.domain.migration_outcomes import requirements
from lifecycle.domain.native_workflow import observations, validate_plan


def selected() -> dict[str, Any]:
    p = migration_plan()
    m = p["migration"]
    m.update(
        schema_version=4,
        outcomes={
            "source_platform": "ahv",
            "target_platform": "vmware",
            "owner_inputs_sha256": m["owner_inputs_sha256"],
            "route_sha256": digest("route"),
            "guest_profile_sha256": m["artifacts"]["guest"],
            "guest": {k: digest(k) for k in ("boot", "drivers", "storage", "network", "identity")},
            "services": {
                k: digest(k)
                for k in (
                    "ipam",
                    "dns",
                    "identity",
                    "time",
                    "trust",
                    "logging",
                    "monitoring",
                    "backup",
                )
            },
            "security": [
                {
                    "id": "application",
                    "source_rule_sha256": digest("source-rule"),
                    "target_rule_sha256": digest("target-rule"),
                    "semantics_sha256": digest("intent"),
                }
            ],
            "datasets": {key: digest(key) for key in m["datasets"]},
        },
    )
    return p


def test_native_acceptance_never_collapses_required_outcomes() -> None:
    p = selected()
    validate(p["migration"], 1000)
    required = cases(p, "admit_writes", "before")
    assert "required_services" not in required
    assert {f"service_{k}" for k in p["migration"]["outcomes"]["services"]} <= set(required)
    assert "guest_drivers" in required and "security_rule_application" in required
    assert "dataset_" + p["migration"]["datasets"][0] in required
    assert "source_capture_bound" in cases(p, "capture", "after")
    assert "ovf_bound" not in cases(p, "export_copy", "after")


@pytest.mark.parametrize(
    "fault", ["", "omission", "old_boolean", "requirement", "observer", "stale"]
)
def test_every_receipt_is_independent_fresh_and_bound(fault: str) -> None:
    p = selected()
    binding = {"stage": "admit_writes", "operation_id": str(uuid4())}
    expected = requirements(p["migration"]["outcomes"])
    records = [
        {
            "case": case,
            "phase": "before",
            "binding_sha256": digest(binding),
            "intent_digest": p["intents"]["admit_writes"],
            "observer_id": str(uuid4()),
            "observed_at": 1000,
            "expires_at": 1030,
            "outcome": "passed",
            "evidence_sha256": digest(case),
            "policy_results": {c["id"]: c["expectation"] for c in p["policy_cases"]}
            if case == "policy_paths"
            else {},
            **({"requirement_sha256": expected[case]} if case in expected else {}),
        }
        for case in cases(p, "admit_writes", "before")
    ]
    service = next(r for r in records if r["case"] == "service_backup")
    if fault == "omission":
        records.remove(service)
    if fault == "old_boolean":
        service["case"] = "required_services"
    if fault == "requirement":
        service["requirement_sha256"] = digest("unrelated-backup")
    if fault == "observer":
        service["observer_id"] = p["executor_id"]
    if fault == "stale":
        service["observed_at"] = 900
    if fault:
        with pytest.raises(Rejected):
            observations(p, binding, "before", records, 1000)
    else:
        assert observations(p, binding, "before", records, 1000) == digest(records)


@pytest.mark.parametrize("source", ["vmware", "openstack", "ahv"])
@pytest.mark.parametrize("target", ["vmware", "openstack", "ahv"])
def test_every_direction_requires_all_independent_activation_outcomes(
    source: str, target: str
) -> None:
    p = selected()
    p["migration"]["outcomes"].update(source_platform=source, target_platform=target)
    validate(p["migration"], 1000)
    expected = requirements(p["migration"]["outcomes"])
    assert set(expected) <= set(cases(p, "admit_writes", "before"))
    capture = cases(p, "capture", "after")
    assert ("snapshot_bound" in capture) == (source == "vmware")
    assert ("source_capture_bound" in capture) == (source != "vmware")


@pytest.mark.parametrize(
    "fault", ["downgrade", "source", "target", "dataset", "policy", "removed_policy"]
)
def test_recovery_preserves_platform_data_and_security_acceptance(fault: str) -> None:
    original = selected()["migration"]
    recovery = deepcopy(original)
    assert recovery_matches(original, recovery)
    if fault == "downgrade":
        recovery.pop("outcomes")
        recovery["schema_version"] = 2
    elif fault in {"source", "target"}:
        recovery["outcomes"][fault + "_platform"] = "openstack"
    elif fault == "dataset":
        recovery["outcomes"]["datasets"][original["datasets"][0]] = digest("weaker-integrity")
    elif fault == "policy":
        recovery["outcomes"]["security"][0]["semantics_sha256"] = digest("weaker-security")
    else:
        recovery["outcomes"]["security"] = []
    assert not recovery_matches(original, recovery)


def test_current_destination_mapping_is_checked_at_every_native_boundary() -> None:
    from test_migration import migration_input

    p = selected()
    evidence = migration_input(p)
    evidence["destination"] = {"platform": "vmware", "network": "quarantine"}
    p["migration"]["destination_sha256"] = digest(evidence["destination"])
    current_profiles(p, evidence, 1000)
    evidence["destination"]["network"] = "production"
    with pytest.raises(Rejected, match="destination_mapping_changed"):
        current_profiles(p, evidence, 1000)


@pytest.mark.parametrize("target", ["vmware", "openstack", "ahv"])
def test_vmware_datacenter_scope_is_accepted_only_for_vmware_destination(target: str) -> None:
    p = selected()
    p["scope"]["project_id"] = "datacenter-1"
    p["migration"]["outcomes"]["target_platform"] = target
    if target == "vmware":
        validate_plan(p, 1000)
    else:
        with pytest.raises(Rejected):
            validate_plan(p, 1000)
