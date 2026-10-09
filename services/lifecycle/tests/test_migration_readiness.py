"""Lifecycle consumes, but never trusts, Planning's route-readiness projection."""

from copy import deepcopy

import pytest

from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected
from lifecycle.domain.migration_readiness import verify


def specimen() -> tuple[dict, dict]:
    scope = {"tenant_id": "10000000-0000-4000-8000-000000000001", "resource_id": "10000000-0000-4000-8000-000000000001",
             "environment": "10000000-0000-4000-8000-000000000001", "site_id": "10000000-0000-4000-8000-000000000001"}
    src, tgt, route = digest("source"), digest("target"), digest("route")
    content = {
        "scope": scope, "migration_campaign": {"route_sha256": route},
        "native_migration": {"migration": {
            "method": "VM_COLD_EXPORT",
            "source": {"profile_sha256": src, "tuple_sha256": digest("source-installed")},
            "target": {"profile_sha256": tgt, "tuple_sha256": digest("target-installed")},
            "outcomes": {"route_sha256": route},
            "review": {"revision": 1, "digest": digest("review")},
        }},
    }
    data = {
        "schema_version": 2, "kind": "migration_workload_readiness",
        "scope": {"tenant_id": "10000000-0000-4000-8000-000000000001", "application_id": "10000000-0000-4000-8000-000000000001",
                  "environment_id": "10000000-0000-4000-8000-000000000001", "site_id": "10000000-0000-4000-8000-000000000001"},
        "route_sha256": route, "tranche_sha256": digest("tranche"),
        "release_sha256": digest("release"),
        "source": {"platform": "vmware", "profile_sha256": src, "installation_id": "src",
                   "versions": {"vmm": "v4.2"}},
        "target": {"platform": "ahv", "profile_sha256": tgt, "installation_id": "dst",
                   "versions": {"vmm": "v4.3"}},
        "method": "cold_export",
        "api_compatibility": {
            "status": "eligible", "operationally_eligible": True,
            "administrator_alerts": [], "native_write_authorized": False,
            "cases": [{
                "capability_id": "vm.disk.read", "side": "source", "criticality": "critical",
                "status": "eligible", "reason": "independent evidence",
                "evidence_sha256": digest("api"), "selected_api_family": "vim",
                "selected_api_version": "8.0", "omission_accepted": False, "expires_at": 200,
            }],
        },
        "native_e3_qualified": True, "receiving_e4_accepted": True,
        "status": "eligible", "holds": [], "expires_at": 200,
        "evaluated_at": 100, "workload_admission_authorized": False,
        "native_write_authorized": False,
    }
    reconciliation = {
        "schema_version": 1, "catalogue_revision_id": "10000000-0000-4000-8000-000000000001",
        "catalogue_sha256": digest("catalogue"),
        "source_identity_sha256": digest("identity"),
        "source_generation_id": "10000000-0000-4000-8000-000000000001",
        "source_profile_sha256": src,
        "source_observation_sha256": digest("source-observation"),
        "native_review_sha256": digest("review"),
        "status": "matched", "holds": [], "workloads": [
            {"workload_id": "10000000-0000-4000-8000-000000000001", "status": "matched", "holds": [],
             "source_identity_sha256": digest("identity"),
             "field_dispositions": [{
                 "field": "cpu.count", "disposition": "matched", "required": True,
                 "desired_value": "2", "observed_value": "2",
                 "evidence_source": "inventory_native_profile",
                 "evidence_age_seconds": 1, "next_action": "none",
             }]}
        ],
        "expires_at": 200, "native_write_authorized": False,
    }
    reconciliation["reconciliation_sha256"] = digest(reconciliation)
    coverage = []
    for side, installation, tuple_sha, generation in (
        ("source", "src", digest("source-installed"), "10000000-0000-4000-8000-000000000001"),
        ("target", "dst", digest("target-installed"), "10000000-0000-4000-8000-000000000001"),
        ("owner", "src", digest("source-installed"), "10000000-0000-4000-8000-000000000001"),
    ):
        row = {
            "schema_version": 1, "platform": "vmware", "scope": side,
            "installation_id": installation, "generation_id": generation,
            "installed_tuple_sha256": tuple_sha,
            "manifest_sha256": digest("manifest"),
            "evaluated_at": 100, "expires_at": 200,
            "status": "complete", "holds": [],
            "attributes": [{"attribute_id": "identity", "status": "observed",
                            "reason": "native", "severity": "critical"}],
            "independent_e3_e4_qualification": False,
            "native_write_authorized": False,
        }
        row["coverage_sha256"] = digest(row)
        coverage.append(row)
    data["workload_reconciliation"] = reconciliation
    data["collection_coverages"] = coverage
    data["readiness_sha256"] = digest(data)
    return data, content


def test_lifecycle_checks_current_scope_and_integrity() -> None:
    value, content = specimen()
    verify(value, content, "10000000-0000-4000-8000-000000000001", 101)
    for edit in (
        lambda v: v.update(status="held"),
        lambda v: v.update(receiving_e4_accepted=False),
        lambda v: v["scope"].update(site_id="foreign"),
        lambda v: v.update(native_write_authorized=True),
    ):
        bad = deepcopy(value)
        edit(bad)
        with pytest.raises(Rejected):
            verify(bad, content, "10000000-0000-4000-8000-000000000001", 101)
    with pytest.raises(Rejected, match="migration_readiness_not_current"):
        verify(value, content, "10000000-0000-4000-8000-000000000001", 109)


def test_even_integrity_preserving_route_or_source_swap_is_held() -> None:
    value, content = specimen()
    for key, replacement in (("route_sha256", digest("other")),
                             ("source", {**value["source"], "profile_sha256": digest("alien")})):
        bad = deepcopy(value)
        bad[key] = replacement
        bad["readiness_sha256"] = digest({k: v for k, v in bad.items()
                                           if k != "readiness_sha256"})
        with pytest.raises(Rejected):
            verify(bad, content, "10000000-0000-4000-8000-000000000001", 101)


def test_route_only_v1_contract_is_never_effect_admissible() -> None:
    value, content = specimen()
    value["schema_version"] = 1
    value["kind"] = "migration_route_readiness"
    value.pop("workload_reconciliation")
    value.pop("collection_coverages")
    value["readiness_sha256"] = digest({
        k: v for k, v in value.items() if k != "readiness_sha256"
    })
    with pytest.raises(Rejected, match="migration_readiness_missing"):
        verify(value, content, "10000000-0000-4000-8000-000000000001", 101)


def test_empty_collection_cannot_be_attested_by_matching_checksums() -> None:
    value, content = specimen()
    value["collection_coverages"][0]["attributes"] = []
    cover = value["collection_coverages"][0]
    cover["coverage_sha256"] = digest({
        k: v for k, v in cover.items() if k != "coverage_sha256"
    })
    value["readiness_sha256"] = digest({
        k: v for k, v in value.items() if k != "readiness_sha256"
    })
    with pytest.raises(Rejected, match="coverage_not_current"):
        verify(value, content, "10000000-0000-4000-8000-000000000001", 101)

def test_nested_workload_status_and_coverage_expiry_are_independent_gates() -> None:
    value, content = specimen()
    held = deepcopy(value)
    held["workload_reconciliation"]["workloads"][0]["status"] = "held"
    held["workload_reconciliation"]["reconciliation_sha256"] = digest({
        k: v for k, v in held["workload_reconciliation"].items()
        if k != "reconciliation_sha256"
    })
    held["readiness_sha256"] = digest({
        k: v for k, v in held.items() if k != "readiness_sha256"
    })
    with pytest.raises(Rejected, match="migration_nested_workload_reconciliation_held"):
        verify(held, content, "10000000-0000-4000-8000-000000000001", 101)

    expired = deepcopy(value)
    expired["collection_coverages"][0]["expires_at"] = 101
    cover = expired["collection_coverages"][0]
    cover["coverage_sha256"] = digest({
        k: v for k, v in cover.items() if k != "coverage_sha256"
    })
    expired["readiness_sha256"] = digest({
        k: v for k, v in expired.items() if k != "readiness_sha256"
    })
    with pytest.raises(Rejected, match="migration_collection_coverage_not_current"):
        verify(expired, content, "10000000-0000-4000-8000-000000000001", 101)
