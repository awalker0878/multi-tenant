"""Input-review faults must never confer native authority or leak protected material."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from lifecycle.bootstrap.commissioning import main
from lifecycle.domain.admission import digest
from lifecycle.domain.commissioning import BINDING_HASHES, INPUTS, SCOPE_KEYS, assess
from lifecycle.domain.execution import Rejected

NOW = 2_000_000_000


def record() -> dict[str, Any]:
    binding = {
        **{k: digest(k) for k in BINDING_HASHES},
        "scope": {k: "fixture-" + k for k in SCOPE_KEYS},
        "campaign_id": "fixture-Q05",
        "valid_until": NOW + 600,
    }
    return {
        "schema_version": 1,
        "record_id": "P07-NATIVE-INPUTS",
        "binding": binding,
        "inputs": [
            {
                "id": key,
                "status": "OBSERVED",
                "owner_identity": "fixture-owner",
                "observer_identity": "fixture-observer",
                "observed_at": NOW - 60,
                "expires_at": NOW + 300,
                "evidence": [
                    {
                        "uri": f"evidence://fixture/{key}/receipt",
                        "sha256": digest(key),
                        "revision": "fixture-v1",
                        "level": "E3",
                        "binding_sha256": digest(binding),
                    }
                ],
                "review": {
                    "disposition": "ACCEPTED",
                    "reviewer": "fixture-reviewer",
                    "reviewed_at": NOW - 30,
                },
            }
            for key in INPUTS
        ],
    }


def test_complete_record_is_not_authenticated_or_authorized() -> None:
    source = record()
    original = deepcopy(source)
    result = assess(source, NOW)
    assert result["record_complete"] and not result["native_write_authorized"]
    assert not result["native_qualification_established"]
    assert result["result"] == "COMPLETE_REQUIRES_INDEPENDENT_VERIFICATION"
    assert source == original
    serialized = json.dumps(result)
    assert "fixture-owner" not in serialized and "evidence://" not in serialized


@pytest.mark.parametrize("key", sorted(INPUTS))
def test_every_missing_input_has_an_owner_and_blocks_readiness(key: str) -> None:
    source = record()
    cell = next(i for i in source["inputs"] if i["id"] == key)
    cell.update(
        status="UNKNOWN",
        owner_identity=None,
        observer_identity=None,
        observed_at=None,
        expires_at=None,
        evidence=[],
        review={"disposition": "NOT_REVIEWED", "reviewer": None, "reviewed_at": None},
    )
    result = assess(source, NOW)
    assert not result["record_complete"]
    assert len(result["holds"]) == 1
    assert result["holds"][0]["input_id"] == key
    assert result["holds"][0]["owner_role"] == INPUTS[key][0]
    assert result["holds"][0]["case_ids"] and result["holds"][0]["package_ids"]


@pytest.mark.parametrize(
    "fault,reason",
    [
        ("expired", "input_expired_or_future"),
        ("rejected", "input_rejected"),
        ("self_review", "independent_review_missing"),
        ("same_observer", "independent_observer_missing"),
        ("simulation", "native_observation_missing"),
        ("unreviewed", "input_not_reviewed"),
        ("binding_expired", "campaign_binding_missing_or_expired"),
    ],
)
def test_valid_but_unready_inputs_are_held(fault: str, reason: str) -> None:
    source = record()
    cell = source["inputs"][0]
    if fault == "expired":
        cell["expires_at"] = NOW
    elif fault == "rejected":
        cell["review"]["disposition"] = "REJECTED"
    elif fault == "self_review":
        cell["review"]["reviewer"] = cell["owner_identity"]
    elif fault == "same_observer":
        cell["observer_identity"] = cell["owner_identity"]
    elif fault == "simulation":
        cell["evidence"][0]["level"] = "E2"
    elif fault == "unreviewed":
        cell["review"] = {"disposition": "NOT_REVIEWED", "reviewer": None, "reviewed_at": None}
    else:
        source["binding"]["valid_until"] = NOW
        for item in source["inputs"]:
            item["evidence"][0]["binding_sha256"] = digest(source["binding"])
    result = assess(source, NOW)
    assert result["holds"][0]["reason"] == reason
    assert not result["native_write_authorized"]


@pytest.mark.parametrize(
    "fault",
    [
        "bool_version",
        "duplicate_input",
        "missing_input",
        "unknown_input",
        "extra_field",
        "raw_secret",
        "wildcard_scope",
        "foreign_scope",
        "foreign_plan",
        "unknown_with_evidence",
        "empty_evidence",
        "mutable_revision",
        "credential_uri",
        "traversal_uri",
        "bad_hash",
        "duplicate_evidence",
        "bool_time",
        "future_review",
        "review_before_observation",
        "unattributed",
        "unsupported_level",
        "empty_binding",
        "bool_expiry",
    ],
)
def test_malformed_or_forged_records_fail_closed(fault: str) -> None:
    source = record()
    cell = source["inputs"][0]
    evidence = cell["evidence"][0]
    match fault:
        case "bool_version":
            source["schema_version"] = True
        case "duplicate_input":
            source["inputs"][-1] = deepcopy(cell)
        case "missing_input":
            source["inputs"].pop()
        case "unknown_input":
            cell["id"] = "N99"
        case "extra_field":
            source["native_write_authorized"] = True
        case "raw_secret":
            cell["password"] = "must-not-be-printed"
        case "wildcard_scope":
            source["binding"]["scope"]["native_scope"] = "*"
        case "foreign_scope":
            source["binding"]["scope"]["tenant_id"] = "foreign"
        case "foreign_plan":
            source["binding"]["plan_digest"] = digest("changed")
        case "unknown_with_evidence":
            cell["status"] = "UNKNOWN"
        case "empty_evidence":
            cell["evidence"] = []
        case "mutable_revision":
            evidence["revision"] = "latest"
        case "credential_uri":
            evidence["uri"] = "https://user:secret@example.test/record"
        case "traversal_uri":
            evidence["uri"] = "evidence://fixture/../record"
        case "bad_hash":
            evidence["sha256"] = "bad"
        case "duplicate_evidence":
            cell["evidence"].append(deepcopy(evidence))
        case "bool_time":
            cell["observed_at"] = True
        case "future_review":
            cell["review"]["reviewed_at"] = NOW + 1
        case "review_before_observation":
            cell["review"]["reviewed_at"] = NOW - 61
        case "unattributed":
            cell["observer_identity"] = ""
        case "unsupported_level":
            evidence["level"] = "PASSED"
        case "empty_binding":
            source["binding"] = None
        case "bool_expiry":
            source["binding"]["valid_until"] = True
    with pytest.raises(Rejected):
        assess(source, NOW)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema_version":1,"schema_version":2}',
        b'{"secret":"do-not-echo",',
        b'{"value":NaN}',
        b'{"value":Infinity}',
        b"[]",
        b"\xff",
        b"{" * 2000,
        b" " * 262145,
    ],
)
def test_cli_malformed_inputs_are_redacted(
    raw: bytes, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "private-input.json"
    path.write_bytes(raw)
    assert main(["--input", str(path)]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["native_write_authorized"] is False
    assert not output["record_valid"]
    assert "do-not-echo" not in json.dumps(output) and str(path) not in json.dumps(output)


def test_cli_unknown_record_and_strict_exit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = record()
    source["binding"] = None
    for cell in source["inputs"]:
        cell.update(
            status="UNKNOWN",
            owner_identity=None,
            observer_identity=None,
            observed_at=None,
            expires_at=None,
            evidence=[],
            review={"disposition": "NOT_REVIEWED", "reviewer": None, "reviewed_at": None},
        )
    path = tmp_path / "inputs.json"
    path.write_text(json.dumps(source))
    assert main(["--input", str(path)]) == 0
    assert len(json.loads(capsys.readouterr().out)["holds"]) == 15
    assert main(["--input", str(path), "--require-complete"]) == 2
    assert json.loads(capsys.readouterr().out)["record_complete"] is False
    link = tmp_path / "symlink"
    link.symlink_to(path)
    assert main(["--input", str(link)]) == 1
    assert main(["--input", str(tmp_path)]) == 1
