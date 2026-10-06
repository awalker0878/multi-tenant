"""Byte, state, scope and uncertainty comparisons for the first native campaign."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from test_commissioning import NOW, record

from lifecycle.bootstrap.native_preflight import main
from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected
from lifecycle.domain.native_preflight import STATE_KEYS, assess_saved_plan

SAVED = b"synthetic opaque saved plan; not a Terraform plan or native evidence"


def inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    envelope = json.loads((Path(__file__).parent / "fixtures/synthetic-plan-v1.json").read_text())
    plan = {key: envelope[key] for key in ("content", "binding")}
    content = plan["content"]
    toolchain = {
        "schema_version": 1,
        "terraform": {"version": "1.0.0", "sha256": digest("fixture-terraform")},
        "providers": [
            {
                "source": "registry.invalid/fixture/openstack",
                "version": "1.0.0",
                "sha256": digest("fixture-provider"),
            }
        ],
        "modules": [
            {
                "id": "fixture-module",
                "uri": "evidence://fixture/modules/v1",
                "revision": "fixture-v1",
                "sha256": digest("fixture-module"),
            }
        ],
        "dependency_lock_sha256": digest("fixture-lock"),
        "worker_image_digest": "sha256:" + digest("fixture-worker"),
    }
    content["lane"] = "isolated_campaign"
    content["terraform"]["backend_ref"] = "evidence://fixture/backend"
    content["terraform"]["toolchain_sha256"] = digest(toolchain)
    content["terraform"]["saved_plan_sha256"] = hashlib.sha256(SAVED).hexdigest()
    for owner in content["ownership"]:
        owner["state_ref"] = content["terraform"]["backend_ref"]
    commissioning = record()
    rebind(plan, commissioning)
    snapshot = {
        **{
            key: deepcopy(content[key])
            for key in ("scope", "installed_tuple", "artifacts", "ownership")
        },
        "terraform": {
            **{key: content["terraform"][key] for key in STATE_KEYS},
            "lock_id": "fixture-lock",
            "fence": 7,
            "lease_expires_at": NOW + 60,
            "held": True,
        },
        "toolchain_sha256": digest(toolchain),
        "observed_at": NOW,
        "observer_id": "fixture-observer",
        "executor_id": content["executor_ids"][0],
        "outstanding_operation_ids": [],
    }
    return plan, commissioning, toolchain, snapshot


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
            "toolchain_sha256": content["terraform"]["toolchain_sha256"],
            "state_binding_sha256": digest({k: content["terraform"][k] for k in STATE_KEYS}),
        }
    )
    for cell in commissioning["inputs"]:
        cell["evidence"][0]["binding_sha256"] = digest(commissioning["binding"])


def check(
    values: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
    raw: bytes = SAVED,
) -> dict[str, Any]:
    return assess_saved_plan(*values, hashlib.sha256(raw).hexdigest(), NOW)


def test_matching_preflight_never_authorizes_apply_or_retry() -> None:
    values = inputs()
    original = deepcopy(values)
    result = check(values)
    assert result["holds"] == []
    assert not result["native_write_authorized"] and not result["retry_authorized"]
    assert result["result"] == "PRECHECK_PASSED_REQUIRES_CURRENT_AUTHORITY"
    assert values == original
    assert "evidence://" not in json.dumps(result) and "fixture-observer" not in json.dumps(result)


@pytest.mark.parametrize("field", sorted(STATE_KEYS))
def test_changed_backend_workspace_lineage_serial_or_owner_is_held(field: str) -> None:
    values = inputs()
    state = values[3]["terraform"]
    state[field] = (
        2
        if field == "state_serial"
        else ("evidence://fixture/other" if field == "backend_ref" else "changed")
    )
    assert "terraform_state_changed" in check(values)["holds"]


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
        ("changed_bytes", "saved_plan_bytes_changed"),
        ("manifest", "toolchain_changed"),
        ("observed_toolchain", "toolchain_changed"),
        ("stale", "native_snapshot_stale"),
        ("future", "native_snapshot_stale"),
        ("lock_expiry", "current_state_lock_missing"),
        ("not_locked", "current_state_lock_missing"),
        ("bool_fence", "current_state_lock_missing"),
        ("missing_lock", "current_state_lock_missing"),
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
    plan, commissioning, toolchain, snapshot = values
    raw = SAVED
    match fault:
        case "changed_bytes":
            raw += b"altered"
        case "manifest":
            toolchain["terraform"]["sha256"] = digest("other")
        case "observed_toolchain":
            snapshot["toolchain_sha256"] = digest("other")
        case "stale":
            snapshot["observed_at"] = NOW - 6
        case "future":
            snapshot["observed_at"] = NOW + 1
        case "lock_expiry":
            snapshot["terraform"]["lease_expires_at"] = NOW
        case "not_locked":
            snapshot["terraform"]["held"] = False
        case "bool_fence":
            snapshot["terraform"]["fence"] = True
        case "missing_lock":
            snapshot["terraform"]["lock_id"] = ""
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
        "changed_unapproved_content",
        "changed_envelope_digest",
        "bool_version",
        "missing_pin",
        "mutable_tool",
        "mutable_provider",
        "duplicate_provider",
        "empty_providers",
        "mutable_module",
        "duplicate_module",
        "empty_modules",
        "tagged_worker",
        "bad_lock_digest",
        "overlap",
        "duplicate_field",
        "wildcard_field",
        "other_state",
        "negative_serial",
        "bool_serial",
    ],
)
def test_malformed_and_colliding_records_are_rejected(fault: str) -> None:
    values = inputs()
    plan, commissioning, toolchain, _ = values
    match fault:
        case "changed_unapproved_content":
            plan["content"]["artifacts"]["adapter"] = digest("other")
        case "changed_envelope_digest":
            plan["binding"]["digest"] = digest("other")
        case "bool_version":
            toolchain["schema_version"] = True
        case "missing_pin":
            del toolchain["terraform"]["sha256"]
        case "mutable_tool":
            toolchain["terraform"]["version"] = ">=1.0.0"
        case "mutable_provider":
            toolchain["providers"][0]["version"] = "latest"
        case "duplicate_provider":
            toolchain["providers"].append(deepcopy(toolchain["providers"][0]))
        case "empty_providers":
            toolchain["providers"] = []
        case "mutable_module":
            toolchain["modules"][0]["revision"] = "main"
        case "duplicate_module":
            toolchain["modules"].append(deepcopy(toolchain["modules"][0]))
        case "empty_modules":
            toolchain["modules"] = []
        case "tagged_worker":
            toolchain["worker_image_digest"] = "worker:latest"
        case "bad_lock_digest":
            toolchain["dependency_lock_sha256"] = "missing"
        case "overlap":
            plan["content"]["ownership"].append(deepcopy(plan["content"]["ownership"][0]))
        case "duplicate_field":
            plan["content"]["ownership"][0]["fields"] *= 2
        case "wildcard_field":
            plan["content"]["ownership"][0]["fields"] = ["*"]
        case "other_state":
            plan["content"]["ownership"][0]["state_ref"] = "evidence://other/state"
        case "negative_serial":
            plan["content"]["terraform"]["state_serial"] = -1
        case "bool_serial":
            plan["content"]["terraform"]["state_serial"] = True
    if fault in {
        "overlap",
        "duplicate_field",
        "wildcard_field",
        "other_state",
        "negative_serial",
        "bool_serial",
    }:
        rebind(plan, commissioning)
    with pytest.raises(Rejected):
        check(values)


def test_cli_hashes_actual_bytes_and_redacts_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("lifecycle.bootstrap.native_preflight.time.time", lambda: NOW)
    arguments = []
    for name, value in zip(
        ("plan", "commissioning", "toolchain", "snapshot"), inputs(), strict=True
    ):
        path = tmp_path / (name + ".json")
        path.write_text(json.dumps(value))
        arguments += ["--" + name, str(path)]
    saved = tmp_path / "protected-saved-plan"
    saved.write_bytes(SAVED)
    arguments += ["--saved-plan", str(saved)]
    assert main(arguments) == 0
    assert not json.loads(capsys.readouterr().out)["native_write_authorized"]
    saved.write_bytes(SAVED + b"changed")
    assert main(arguments) == 2
    assert "saved_plan_bytes_changed" in json.loads(capsys.readouterr().out)["holds"]
    (tmp_path / "snapshot.json").write_text('{"secret":"must-not-escape",')
    assert main(arguments) == 1
    error = capsys.readouterr().out
    assert "must-not-escape" not in error and str(tmp_path) not in error
