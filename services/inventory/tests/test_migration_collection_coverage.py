"""Manifest field coverage is not synonymous with native qualification."""

from copy import deepcopy

import pytest

from inventory.domain.discovery import Rejected, digest
from inventory.domain.migration_collection_coverage import evaluate, installed_version_supported


ROW = {
    "id": "identity.vm", "scope": "source", "api_family": "vmm",
    "api_field": "vm.id", "owner_evidence_field": None,
    "collection_method": "native_get", "max_age_seconds": 60,
    "severity": "critical", "condition": "always",
    "collector_source": "test", "collection_status": "native_field_candidate",
}


def assess(manifest: dict, facts: list[dict], conditions: list[dict] | None = None,
           now: int = 100) -> dict:
    return evaluate(manifest, "ahv", "source", "installation", "generation",
                    digest("installed"), facts, conditions or [], now,
                    installed_namespaces={"vmm": ["v4.3"]})


def record(key: str = "identity.vm", when: int = 90) -> dict:
    return {
        "attribute_id": key, "scope": "source", "installation_id": "installation",
        "generation_id": "generation", "installed_tuple_sha256": digest("installed"),
        "collection_method": "native_get", "api_family": "vmm",
        "api_version": "v4.3", "observed_at": when,
        "evidence_sha256": digest("native-get"), "value_present": True,
        "native_operation": "GET /api/vmm/v4.3/ahv/config/vms/native",
        "value_sha256": digest("native-value"),
        "source_response_sha256": digest("native-response"),
    }


def manifest() -> dict:
    return {"schema_version": 1, "platforms": {"ahv": {"attributes": [deepcopy(ROW)]}}}


def test_missing_expired_cross_scope_and_valid_records() -> None:
    model = manifest()
    assert assess(model, [])["status"] == "held"
    assert assess(model, [record()])["status"] == "complete"
    assert assess(model, [record()])["expires_at"] == 150
    uninstalled = record()
    uninstalled["api_version"] = "v9.9"
    evidence = assess(model, [uninstalled])
    assert evidence["status"] == "held"
    assert evidence["attributes"][0]["reason"] == "installed_api_version_not_observed"
    assert assess(model, [record()])["independent_e3_e4_qualification"] is False
    assert assess(model, [record()], now=151)["status"] == "held"
    alien = record()
    alien["installation_id"] = "foreign"
    with pytest.raises(Rejected, match="cross_scope"):
        assess(model, [alien])
    with pytest.raises(Rejected, match="ambiguous"):
        assess(model, [record(), record()])


def test_conditional_field_needs_independent_applicability_and_native_receipt() -> None:
    model = manifest()
    model["platforms"]["ahv"]["attributes"][0]["condition"] = "when:present"
    evidence = record()
    assert assess(model, [evidence])["status"] == "held"
    condition = {
        **{k: evidence[k] for k in ("attribute_id", "scope", "installation_id",
                                    "generation_id", "installed_tuple_sha256", "observed_at")},
        "condition": "when:present", "applicable": True,
        "evidence_sha256": digest("presence"),
    }
    assert assess(model, [evidence], [condition])["status"] == "complete"
    condition["applicable"] = False
    assert assess(model, [], [condition])["attributes"][0]["status"] == "not_applicable"
    condition["observed_at"] = None
    assert assess(model, [], [condition])["status"] == "held"


def test_invalid_applicability_digest_never_upgrades_to_observed() -> None:
    model = manifest()
    model["platforms"]["ahv"]["attributes"][0]["condition"] = "when:present"
    receipt = record()
    decision = {
        **{k: receipt[k] for k in ("attribute_id", "scope", "installation_id",
                                    "generation_id", "installed_tuple_sha256", "observed_at")},
        "condition": "when:present", "applicable": True,
        "evidence_sha256": "invalid-not-a-digest",
    }
    result = assess(model, [receipt], [decision])
    assert result["status"] == "held"
    assert result["attributes"][0]["status"] == "held"
    assert result["attributes"][0]["reason"] == "applicability_evidence_stale_or_invalid"


def test_microversion_interval_is_probed_not_silently_reduced_to_maximum() -> None:
    ranges = {"nova": {"min_version": "2.1", "max_version": "2.104"},
              "cinder": {"min_version": "3.0", "max_version": "3.70"}}
    assert installed_version_supported("2.50", "nova", ranges)
    assert installed_version_supported("2.104", "nova", ranges)
    assert installed_version_supported("3.1", "cinder", ranges)
    for unsupported in ("2.105", "2.0", "3.70", "v1.30", "invalid"):
        assert not installed_version_supported(unsupported, "nova", ranges)
    assert not installed_version_supported("2.20", "glance", ranges)
    assert not installed_version_supported("2.20", "nova",
                                         {"nova": {"min_version": "2.30", "max_version": "2.1"}})
