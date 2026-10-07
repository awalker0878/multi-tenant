"""Byte, state, scope and uncertainty comparisons for the first native campaign."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from test_commissioning import NOW, record

from lifecycle.bootstrap.native_preflight import main
from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected
from lifecycle.domain.native_preflight import CUSTODY_KEYS, assess_native_plan


def inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    envelope = json.loads((Path(__file__).parent / "fixtures/synthetic-plan-v1.json").read_text())
    plan = {key: envelope[key] for key in ("content", "binding")}
    content = plan["content"]
    api_contracts = {
        "schema_version": 1,
        "api_versions": {"compute": "2.1", "network": "2.0", "volume": "3.0"},
        "adapter_sha256": content["artifacts"]["adapter"],
        "worker_image_digest": "sha256:" + digest("fixture-worker"),
    }
    content["lane"] = "isolated_campaign"
    content["native_api"]["custody_ref"] = "evidence://fixture/backend"
    content["native_api"]["api_contracts_sha256"] = digest(api_contracts)
    for owner in content["ownership"]:
        owner["custody_ref"] = content["native_api"]["custody_ref"]
    content["native_api"]["operation_plan"]["ownership_digest"] = digest(content["ownership"])
    content["native_api"]["operation_plan_sha256"] = digest(content["native_api"]["operation_plan"])
    commissioning = record()
    rebind(plan, commissioning)
    snapshot = {
        **{
            key: deepcopy(content[key])
            for key in ("scope", "installed_tuple", "artifacts", "ownership")
        },
        "native_api": {
            **{key: content["native_api"][key] for key in CUSTODY_KEYS},
            "lock_id": "fixture-lock",
            "fence": 7,
            "lease_expires_at": NOW + 60,
            "held": True,
        },
        "api_contracts_sha256": digest(api_contracts),
        "observed_at": NOW,
        "observer_id": "fixture-observer",
        "executor_id": content["executor_ids"][0],
        "outstanding_operation_ids": [],
    }
    return plan, commissioning, api_contracts, snapshot


def rebind(plan: dict[str, Any], commissioning: dict[str, Any]) -> None:
    content, binding = plan["content"], plan["binding"]
    for key in ("action", "lane", "executor_ids", "valid_until"):
        binding[key] = content[key]
    binding["content_digest"] = digest(content)
    binding["digest"] = digest({k: v for k, v in binding.items() if k != "digest"})
    commissioning["binding"].update(
        {
            "scope": deepcopy(content["scope"]),
            "plan_digest": binding["digest"],
            "installed_tuple_sha256": digest(content["installed_tuple"]),
            "artifact_set_sha256": digest(content["artifacts"]),
            "ownership_sha256": digest(content["ownership"]),
            "api_contracts_sha256": content["native_api"]["api_contracts_sha256"],
            "custody_binding_sha256": digest({k: content["native_api"][k] for k in CUSTODY_KEYS}),
        }
    )
    for cell in commissioning["inputs"]:
        cell["evidence"][0]["binding_sha256"] = digest(commissioning["binding"])


def check(
    values: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
    raw: str | None = None,
) -> dict[str, Any]:
    return assess_native_plan(
        *values, raw or values[0]["content"]["native_api"]["operation_plan_sha256"], NOW
    )


def test_matching_preflight_never_authorizes_apply_or_retry() -> None:
    values = inputs()
    original = deepcopy(values)
    result = check(values)
    assert result["holds"] == []
    assert not result["native_write_authorized"] and not result["retry_authorized"]
    assert result["result"] == "PRECHECK_PASSED_REQUIRES_CURRENT_AUTHORITY"
    assert values == original
    assert "evidence://" not in json.dumps(result) and "fixture-observer" not in json.dumps(result)


@pytest.mark.parametrize("field", sorted(CUSTODY_KEYS))
def test_changed_backend_ownership_digest_lineage_serial_or_owner_is_held(field: str) -> None:
    values = inputs()
    state = values[3]["native_api"]
    state[field] = (
        2
        if field == "custody_generation"
        else ("evidence://fixture/other" if field == "custody_ref" else "changed")
    )
    assert "native_custody_changed" in check(values)["holds"]


@pytest.mark.parametrize("field", ["scope", "installed_tuple", "artifacts", "ownership"])
def test_changed_native_owner_records_are_held(field: str) -> None:
    values = inputs()
    if field == "ownership":
        values[3][field][0]["writer"] = "foreign-writer"
    else:
        values[3][field][next(iter(values[3][field]))] = "changed"
    assert field + "_changed" in check(values)["holds"]


@pytest.mark.parametrize(
    "fault,reason",
    [
        ("changed_bytes", "native_operation_plan_changed"),
        ("manifest", "api_contracts_changed"),
        ("observed_api_contracts", "api_contracts_changed"),
        ("stale", "native_snapshot_stale"),
        ("future", "native_snapshot_stale"),
        ("lock_expiry", "current_custody_lock_missing"),
        ("not_locked", "current_custody_lock_missing"),
        ("bool_fence", "current_custody_lock_missing"),
        ("missing_lock", "current_custody_lock_missing"),
        ("unknown", "outstanding_effect_requires_reconciliation"),
        ("observer", "independent_native_observer_missing"),
        ("executor", "executor_changed"),
        ("plan_expiry", "plan_or_facts_expired"),
        ("facts_expiry", "plan_or_facts_expired"),
        ("retire", "outside_initial_native_campaign"),
        ("operational", "outside_initial_native_campaign"),
        ("other_platform", "outside_initial_native_campaign"),
        ("method", "outside_initial_native_campaign"),
        ("foreign_packet", "commissioning_plan_mismatch"),
        ("unreviewed", "commissioning_not_complete"),
    ],
)
def test_preflight_denials(fault: str, reason: str) -> None:
    values = inputs()
    plan, commissioning, api_contracts, snapshot = values
    raw = None
    match fault:
        case "changed_bytes":
            raw = digest("altered")
        case "manifest":
            api_contracts["adapter_sha256"] = digest("other")
        case "observed_api_contracts":
            snapshot["api_contracts_sha256"] = digest("other")
        case "stale":
            snapshot["observed_at"] = NOW - 6
        case "future":
            snapshot["observed_at"] = NOW + 1
        case "lock_expiry":
            snapshot["native_api"]["lease_expires_at"] = NOW
        case "not_locked":
            snapshot["native_api"]["held"] = False
        case "bool_fence":
            snapshot["native_api"]["fence"] = True
        case "missing_lock":
            snapshot["native_api"]["lock_id"] = ""
        case "unknown":
            snapshot["outstanding_operation_ids"] = ["accepted-response-lost"]
        case "observer":
            snapshot["observer_id"] = snapshot["executor_id"]
        case "executor":
            snapshot["executor_id"] = "foreign"
        case "plan_expiry":
            plan["content"]["valid_until"] = NOW
        case "facts_expiry":
            plan["content"]["input_fresh_until"] = NOW
        case "retire":
            plan["content"]["action"] = "application.retire"
        case "operational":
            plan["content"]["lane"] = "operational"
        case "other_platform":
            plan["content"]["installed_tuple"]["platform"] = "vmware"
        case "method":
            plan["content"]["method"] = "replan_at_apply"
        case "foreign_packet":
            commissioning["binding"]["artifact_set_sha256"] = digest("other")
        case "unreviewed":
            commissioning["inputs"][0]["review"] = {
                "disposition": "NOT_REVIEWED",
                "reviewer": None,
                "reviewed_at": None,
            }
    if fault in {
        "plan_expiry",
        "facts_expiry",
        "retire",
        "operational",
        "other_platform",
        "method",
    }:
        rebind(plan, commissioning)
    if fault == "foreign_packet":
        for cell in commissioning["inputs"]:
            cell["evidence"][0]["binding_sha256"] = digest(commissioning["binding"])
    result = check(values, raw)
    assert reason in result["holds"]
    assert not result["native_write_authorized"] and not result["retry_authorized"]


@pytest.mark.parametrize(
    "fault",
    [
        "changed_content",
        "bool_version",
        "mutable_api",
        "missing_adapter",
        "tagged_worker",
        "extra",
        "ownership",
        "bool_generation",
    ],
)
def test_invalid_native_contracts_are_rejected(fault: str) -> None:
    values = inputs()
    plan, commissioning, contracts, _ = values
    if fault == "changed_content":
        plan["content"]["artifacts"]["adapter"] = digest("other")
    elif fault == "bool_version":
        contracts["schema_version"] = True
    elif fault == "mutable_api":
        contracts["api_versions"]["compute"] = "latest"
    elif fault == "missing_adapter":
        del contracts["adapter_sha256"]
    elif fault == "tagged_worker":
        contracts["worker_image_digest"] = "worker:latest"
    elif fault == "extra":
        contracts["command"] = "arbitrary"
    elif fault == "ownership":
        plan["content"]["ownership"] *= 2
        rebind(plan, commissioning)
    else:
        plan["content"]["native_api"]["custody_generation"] = True
        rebind(plan, commissioning)
    with pytest.raises(Rejected):
        check(values)


def test_cli_hashes_actual_bytes_and_redacts_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("lifecycle.bootstrap.native_preflight.time.time", lambda: NOW)
    arguments = []
    for name, value in zip(
        ("plan", "commissioning", "api-contracts", "snapshot"), inputs(), strict=True
    ):
        path = tmp_path / (name + ".json")
        path.write_text(json.dumps(value))
        arguments += ["--" + name, str(path)]
    saved = tmp_path / "operation.json"
    saved.write_text(json.dumps(inputs()[0]["content"]["native_api"]["operation_plan"]))
    arguments += ["--operation-plan", str(saved)]
    assert main(arguments) == 0
    assert not json.loads(capsys.readouterr().out)["native_write_authorized"]
    saved.write_text(json.dumps({"changed": True}))
    assert main(arguments) == 2
    assert "native_operation_plan_changed" in json.loads(capsys.readouterr().out)["holds"]
    (tmp_path / "snapshot.json").write_text('{"secret":"must-not-escape",')
    assert main(arguments) == 1
    error = capsys.readouterr().out
    assert "must-not-escape" not in error and str(tmp_path) not in error
