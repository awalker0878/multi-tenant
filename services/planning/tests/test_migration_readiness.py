"""Resolved migration-readiness contract is fail-closed and deterministic."""

import pytest

from planning.application.migration_support import validate_workload_contract
from planning.domain.migration_readiness import resolve, resolve_workload
from planning.domain.model import Rejected, digest


def fixture() -> tuple[dict, dict, dict]:
    route = {
        "id": "a", "method": "cold_export",
        "source": {"platform": "vmware", "installation_id": "one",
                   "profile_sha256": digest("src"), "versions": {"api": "8.0"}},
        "target": {"platform": "ahv", "installation_id": "two",
                   "profile_sha256": digest("tgt"), "versions": {"api": "v4.3"}},
        "api_usage": [{"capability_id": "vm.disk.read", "side": "source",
                       "criticality": "critical", "reason": "all bytes"}],
    }
    native = {"blockers": [], "route_sha256": digest(route),
              "native_qualified": True, "operationally_accepted": True}
    api = {"cases": [{"status": "eligible", "omission_accepted": False,
                      "expires_at": 200}],
           "operationally_eligible": True}
    return route, native, api


def assess(route: dict, native: dict, api: dict, now: int = 100) -> dict:
    return resolve(route, native, api, {"tenant_id": "t", "site_id": "s"},
                   digest("tranche"), digest("release"), 200, now)


def test_exact_independent_e3_e4_and_api_evidence_required() -> None:
    route, native, api = fixture()
    good = assess(route, native, api)
    assert good["status"] == "eligible"
    assert good["expires_at"] == 200
    assert good["native_write_authorized"] is False
    assert good["workload_admission_authorized"] is False
    assert good["readiness_sha256"] == digest({
        k: v for k, v in good.items() if k != "readiness_sha256"
    })
    for changed, expected in [
        ({**native, "native_qualified": False}, "independent_e3_route_qualification_required"),
        ({**native, "operationally_accepted": False},
         "independent_e4_receiving_acceptance_required"),
        ({**native, "route_sha256": "other"}, "route_qualification_binding_changed"),
    ]:
        result = assess(route, changed, api)
        assert result["status"] == "held" and expected in result["holds"]


def test_legacy_route_and_stale_or_unqualified_api_are_held() -> None:
    route, native, api = fixture()
    del route["api_usage"]
    native["route_sha256"] = digest(route)
    assert "route_api_usage_manifest_required" in assess(route, native, api)["holds"]
    route["api_usage"] = []
    native["route_sha256"] = digest(route)
    assert assess(route, native, api)["status"] == "held"
    api["cases"][0]["status"] = "unknown"
    assert "api_feature_unresolved" in assess(route, native, api)["holds"]
    assert "migration_tranche_expired" in assess(route, native, api, 201)["holds"]


def test_earliest_per_operation_qualification_expiry_controls_route() -> None:
    route, native, api = fixture()
    api["cases"][0]["expires_at"] = 130
    assert assess(route, native, api)["expires_at"] == 130
    api["cases"][0]["expires_at"] = 100
    preview = assess(route, native, api)
    assert preview["status"] == "held"
    assert "api_capability_evidence_expired_or_unbounded" in preview["holds"]


def test_workload_coverage_requires_release_pinned_full_attribute_set() -> None:
    route, native, api = fixture()
    route_result = assess(route, native, api)
    now = 100
    reconciliation = {
        "status": "matched", "holds": [], "expires_at": 180,
        "native_write_authorized": False,
    }
    reconciliation.setdefault("workloads", [{"status": "matched", "holds": []}])
    reconciliation["reconciliation_sha256"] = digest(reconciliation)
    manifest = {
        "release_sha256": route_result["release_sha256"],
        "manifest_sha256": digest("manifest"),
        "platforms": {
            "vmware": {"source": ["src.vm"], "owner": ["owner.intent"]},
            "ahv": {"target": ["tgt.vm"]},
        },
    }
    scopes = []
    for side, platform, installation, attribute in (
        ("source", "vmware", "one", "src.vm"),
        ("target", "ahv", "two", "tgt.vm"),
        ("owner", "vmware", "one", "owner.intent"),
    ):
        coverage = {
            "scope": side, "platform": platform, "status": "complete", "holds": [],
            "attributes": [{"attribute_id": attribute, "status": "observed"}],
            "installation_id": installation,
            "manifest_sha256": manifest["manifest_sha256"],
            "expires_at": 160,
            "evaluated_at": now,
            "independent_e3_e4_qualification": False,
            "native_write_authorized": False,
        }
        coverage["coverage_sha256"] = digest(coverage)
        scopes.append(coverage)
    assert resolve_workload(route_result, reconciliation, scopes, now,
                            manifest)["status"] == "eligible"
    assert resolve_workload(route_result, reconciliation, scopes, now,
                            None)["status"] == "held"
    altered = [dict(row) for row in scopes]
    altered[0]["manifest_sha256"] = digest("other")
    altered[0]["coverage_sha256"] = digest({
        k: v for k, v in altered[0].items() if k != "coverage_sha256"
    })
    result = resolve_workload(route_result, reconciliation, altered, now, manifest)
    assert "migration_collection_manifest_attributes_changed" in result["holds"]


def test_incomplete_eligible_readiness_must_not_leave_planning() -> None:
    """The resolver's hold logic alone is not the published schema."""
    route, native, api = fixture()
    route_result = assess(route, native, api)
    reconciliation = {
        "status": "matched", "holds": [], "expires_at": 180,
        "native_write_authorized": False,
    }
    reconciliation.setdefault("workloads", [{"status": "matched", "holds": []}])
    reconciliation["reconciliation_sha256"] = digest(reconciliation)
    manifest = {
        "release_sha256": route_result["release_sha256"],
        "manifest_sha256": digest("manifest"),
        "platforms": {
            "vmware": {"source": ["src.vm"], "owner": ["owner.intent"]},
            "ahv": {"target": ["tgt.vm"]},
        },
    }
    rows = []
    for scope, platform, installation, attribute in (
        ("source", "vmware", "one", "src.vm"),
        ("target", "ahv", "two", "tgt.vm"),
        ("owner", "vmware", "one", "owner.intent"),
    ):
        item = {
            "scope": scope, "platform": platform, "status": "complete",
            "holds": [], "attributes": [{"attribute_id": attribute, "status": "observed"}],
            "installation_id": installation, "manifest_sha256": manifest["manifest_sha256"],
            "expires_at": 160, "evaluated_at": 100,
            "independent_e3_e4_qualification": False, "native_write_authorized": False,
        }
        item["coverage_sha256"] = digest(item)
        rows.append(item)
    result = resolve_workload(route_result, reconciliation, rows, 100, manifest)
    assert result["status"] == "eligible"
    with pytest.raises(Rejected, match="migration_workload_contract_invalid"):
        validate_workload_contract(result)


def test_complete_workload_readiness_contract_is_accepted_and_nested_drift_denied() -> None:
    """Synthetic wire-conformance example, never native E3/E4 qualification."""
    from copy import deepcopy

    uid = "10000000-0000-4000-8000-000000000001"
    def h(text: str) -> str:
        return digest(text)

    source = {"platform": "vmware", "installation_id": "source-installation",
              "profile_sha256": h("source"), "versions": {"vcenter": "8.0"}}
    target = {"platform": "ahv", "installation_id": "target-installation",
              "profile_sha256": h("target"), "versions": {"prism": "v4.3"}}
    reconciliation = {
        "schema_version": 1,
        "catalogue_revision_id": uid,
        "catalogue_sha256": h("catalogue"),
        "source_identity_sha256": h("identity"),
        "source_generation_id": uid,
        "source_profile_sha256": source["profile_sha256"],
        "source_observation_sha256": h("source-observation"),
        "native_review_sha256": h("native-review"),
        "status": "matched",
        "workloads": [{
            "workload_id": uid, "status": "matched", "holds": [],
            "source_identity_sha256": h("identity"),
            "field_dispositions": [{
                "field": "cpu.count", "disposition": "matched", "required": True,
                "desired_value": "2", "observed_value": "2",
                "evidence_source": "inventory_native_profile",
                "evidence_age_seconds": 1, "next_action": "none",
            }],
        }],
        "holds": [], "expires_at": 2000000000,
        "native_write_authorized": False,
    }
    reconciliation["reconciliation_sha256"] = h(reconciliation)
    coverage = []
    for scope, platform, installation in (
        ("source", "vmware", source["installation_id"]),
        ("target", "ahv", target["installation_id"]),
        ("owner", "vmware", source["installation_id"]),
    ):
        observation = {
            "schema_version": 1, "platform": platform, "scope": scope,
            "installation_id": installation, "generation_id": uid,
            "installed_tuple_sha256": h(platform + "installed"),
            "manifest_sha256": h("collection-manifest"),
            "evaluated_at": 100, "status": "complete",
            "attributes": [{
                "attribute_id": scope + ".vm", "status": "observed",
                "reason": "native", "severity": "critical",
            }],
            "holds": [], "independent_e3_e4_qualification": False,
            "native_write_authorized": False, "expires_at": 2000000000,
        }
        observation["coverage_sha256"] = h(observation)
        coverage.append(observation)
    result = {
        "schema_version": 2, "kind": "migration_workload_readiness",
        "scope": {"tenant_id": uid, "application_id": uid,
                  "environment_id": uid, "site_id": uid},
        "route_sha256": h("route"), "tranche_sha256": h("tranche"),
        "release_sha256": h("release"),
        "source": source, "target": target, "method": "cold_export",
        "api_compatibility": {
            "status": "eligible", "operationally_eligible": True,
            "cases": [{
                "capability_id": "vm.disk.read", "side": "source",
                "criticality": "critical", "status": "eligible",
                "reason": "synthetic conformance example",
                "evidence_sha256": h("api-evidence"),
                "selected_api_family": "vcenter",
                "selected_api_version": "8.0",
                "omission_accepted": False, "expires_at": 2000000000,
            }],
            "administrator_alerts": [], "native_write_authorized": False,
        },
        "native_e3_qualified": True, "receiving_e4_accepted": True,
        "status": "eligible", "holds": [], "expires_at": 2000000000,
        "evaluated_at": 100, "workload_admission_authorized": False,
        "native_write_authorized": False,
        "workload_reconciliation": reconciliation,
        "collection_coverages": coverage,
    }
    result["readiness_sha256"] = h(result)
    validate_workload_contract(result)
    invalid = deepcopy(result)
    invalid["workload_reconciliation"]["workloads"][0]["field_dispositions"][0][
        "evidence_source"
    ] = "unrecognized"
    with pytest.raises(Rejected, match="migration_workload_contract_invalid"):
        validate_workload_contract(invalid)
    duplicate_scope = deepcopy(result)
    duplicate_scope["collection_coverages"][2]["scope"] = "source"
    with pytest.raises(Rejected, match="migration_workload_contract_invalid"):
        validate_workload_contract(duplicate_scope)

def test_held_child_workload_cannot_be_masked_by_matched_parent() -> None:
    route, native, api = fixture()
    readiness = assess(route, native, api)
    reconciliation = {
        "status": "matched", "holds": [], "expires_at": 180,
        "workloads": [{"status": "held", "holds": ["disk_not_observed"]}],
        "native_write_authorized": False,
    }
    reconciliation["reconciliation_sha256"] = digest(reconciliation)
    result = resolve_workload(readiness, reconciliation, None, 100, None)
    assert result["status"] == "held"
    assert "catalogue_native_nested_workload_reconciliation_required" in result["holds"]


def test_missing_admission_wiring_cannot_publish_route_only_eligibility() -> None:
    from planning.application.migration_support import MigrationSupport

    service = MigrationSupport(lambda *_: {}, lambda *_: [], lambda: 100)
    with pytest.raises(Rejected, match="migration_workload_admission_not_commissioned"):
        service.require(None, "site", {})

def test_eligible_parent_cannot_override_unobserved_required_field() -> None:
    route, native, api = fixture()
    readiness = assess(route, native, api)
    recon = {
        "status": "matched", "holds": [], "expires_at": 180,
        "native_write_authorized": False,
        "workloads": [{
            "workload_id": "10000000-0000-4000-8000-000000000001",
            "status": "matched", "holds": [],
            "field_dispositions": [{
                "field": "guest.firmware", "required": True,
                "disposition": "unobserved", "evidence_source": "unobserved",
                "evidence_age_seconds": None,
            }],
        }],
    }
    recon["reconciliation_sha256"] = digest(recon)
    result = resolve_workload(readiness, recon, None, 100, None)
    assert "catalogue_native_nested_workload_reconciliation_required" in result["holds"]


def test_duplicate_workload_ids_hold_even_with_matched_rows() -> None:
    from planning.domain.migration_readiness import eligible_field_dispositions

    row = {
        "workload_id": "10000000-0000-4000-8000-000000000001",
        "status": "matched", "holds": [], "field_dispositions": [],
    }
    assert not eligible_field_dispositions([row, dict(row)])
    assert eligible_field_dispositions([row])
