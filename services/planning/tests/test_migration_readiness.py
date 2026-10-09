"""Resolved migration-readiness contract is fail-closed and deterministic."""

from planning.domain.migration_readiness import resolve, resolve_workload
from planning.domain.model import digest


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
            "scope": side, "status": "complete", "holds": [],
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
