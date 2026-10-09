"""Resolved migration-readiness contract is fail-closed and deterministic."""

from planning.domain.migration_readiness import resolve
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
    api = {"cases": [{"status": "eligible", "omission_accepted": False}],
           "operationally_eligible": True}
    return route, native, api


def assess(route: dict, native: dict, api: dict, now: int = 100) -> dict:
    return resolve(route, native, api, {"tenant_id": "t", "site_id": "s"},
                   digest("tranche"), digest("release"), 200, now)


def test_exact_independent_e3_e4_and_api_evidence_required() -> None:
    route, native, api = fixture()
    good = assess(route, native, api)
    assert good["status"] == "eligible"
    assert good["native_write_authorized"] is False
    assert good["workload_admission_authorized"] is False
    assert good["readiness_sha256"] == digest({
        k: v for k, v in good.items() if k != "readiness_sha256"
    })
    for changed, expected in [
        ({**native, "native_qualified": False}, "independent_e3_route_qualification_required"),
        ({**native, "operationally_accepted": False}, "independent_e4_receiving_acceptance_required"),
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
