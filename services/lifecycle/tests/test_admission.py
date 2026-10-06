import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from lifecycle.domain.admission import evaluate

NOW = 2_000_000_000


def fixture() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    plan = json.loads(
        (
            Path(__file__).resolve().parents[3]
            / "contracts/fixtures/planning/synthetic-plan-v1.json"
        ).read_text()
    )
    c, b = plan["content"], plan["binding"]
    current = {
        "scope": c["scope"],
        "input_digests": c["input_digests"],
        "artifacts": c["artifacts"],
        "actor_id": b["executor_ids"][0],
        "evaluated_at": NOW,
        "lane": "operational",
        "exact_tuple_qualified": True,
        "qualification_level": "E3",
        **{
            k: True
            for k in (
                "entitled",
                "commissioned",
                "ownership_current",
                "state_current",
                "change_window",
                "emergency_stop_clear",
            )
        },
        "approval": {
            "state": "approved",
            "revoked": False,
            "plan_digest": b["digest"],
            "plan_id": b["plan_id"],
            "plan_revision": 1,
            "scope": c["scope"],
            "approver_grant_current": True,
            "expires_at": NOW + 200,
            "approver_id": "independent-reviewer",
        },
        "reservations": [
            {
                **r,
                "state": "reserved",
                "plan_digest": b["digest"],
                "expires_at": NOW + 200,
                "receipt_id": "receipt-" + r["kind"],
            }
            for r in c["reservation_intents"]
        ],
    }
    return c, b, current


def test_complete_current_receipts_contract_only() -> None:
    c, b, current = fixture()
    result = evaluate(c, b, current, NOW)
    assert result["admissible"] and not result["native_write_authorized"]
    assert "dispatch_outbox" in result["atomic_record_required"]


@pytest.mark.parametrize(
    "fault",
    [
        "revoked",
        "expired",
        "approver_revoked",
        "same_approver",
        "scope",
        "input",
        "artifact",
        "entitlement",
        "ownership",
        "state",
        "emergency",
        "reservation",
        "qualification",
        "E2",
        "lane",
        "actor",
        "stale",
        "content",
        "digest",
        "expiry",
    ],
)
def test_admission_denies(fault: str) -> None:
    c, b, current = deepcopy(fixture())
    match fault:
        case "revoked":
            current["approval"]["revoked"] = True
        case "expired":
            current["approval"]["expires_at"] = NOW
        case "approver_revoked":
            current["approval"]["approver_grant_current"] = False
        case "same_approver":
            current["approval"]["approver_id"] = b["requested_by"]
        case "scope":
            current["scope"]["native_scope"] = "extra-project"
        case "input":
            current["input_digests"]["policy"] = "a" * 64
        case "artifact":
            current["artifacts"]["adapter"] = "a" * 64
        case "entitlement":
            current["entitled"] = False
        case "ownership":
            current["ownership_current"] = False
        case "state":
            current["state_current"] = False
        case "emergency":
            current["emergency_stop_clear"] = False
        case "reservation":
            current["reservations"][0]["state"] = "outcome_unknown"
        case "qualification":
            current["exact_tuple_qualified"] = False
        case "E2":
            current["qualification_level"] = "E2"
        case "lane":
            current["lane"] = "isolated_campaign"
        case "actor":
            current["actor_id"] = "other"
        case "stale":
            current["evaluated_at"] = NOW - 6
        case "content":
            c["effects"][0]["destructive"] = True
        case "digest":
            b["digest"] = "b" * 64
        case "expiry":
            c["valid_until"] = NOW
    assert not evaluate(c, b, current, NOW)["admissible"]
