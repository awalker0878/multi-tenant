"""Progress is derived from durable stage observations, never speculative byte rates."""

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from test_native_workflow import plan

from lifecycle.application.native_workflow import NativeWorkflow
from lifecycle.domain.admission import digest
from lifecycle.domain.native_workflow import stages_for


@pytest.mark.parametrize("state", ["prepared", "running", "observed"])
def test_read_exposes_actual_stage_times_and_independent_completion(state: str) -> None:
    p = plan()
    job = str(uuid4())
    database = MagicMock()
    tx = database.transaction.return_value.__enter__.return_value
    tx.one.return_value = {
        "plan": p,
        "state": "running",
        "revision": 3,
        "stopped": False,
        "reason": None,
        "created_at": 900,
        "fingerprint": digest(p),
    }
    operation: dict[str, Any] = {
        "id": str(uuid4()),
        "stage": stages_for(p)[0],
        "created_at": 940,
        "redeemed": str(uuid4()) if state != "prepared" else None,
        "redeemed_at": 950 if state != "prepared" else None,
        "observation_digest": digest("observed") if state == "observed" else None,
        "observed_at": 970 if state == "observed" else None,
    }
    tx.all.return_value = [operation]
    workflow = NativeWorkflow(database, MagicMock(), lambda: 1000)
    measurements = workflow.read(p["scope"]["tenant_id"], job)["measurements"]
    assert measurements["started_at"] == 900
    assert measurements["observed_at"] == 1000
    assert measurements["total_stages"] == len(stages_for(p))
    assert measurements["completed_stages"] == (1 if state == "observed" else 0)
    stage = measurements["operations"][0]
    assert stage["prepared_at"] == 940
    assert stage["started_at"] == operation["redeemed_at"]
    assert stage["observed_at"] == operation["observed_at"]
    assert stage["elapsed_seconds"] == {"prepared": None, "running": 50, "observed": 20}[state]
    assert "percent" not in measurements and "estimated_seconds" not in measurements


@pytest.mark.parametrize("fault", ["", "stopped", "expired", "foreign", "stale", "unavailable"])
def test_transfer_measurements_require_current_original_redeemed_grant(fault: str) -> None:
    p = plan()
    database, reader = MagicMock(), MagicMock()
    tx = database.transaction.return_value.__enter__.return_value
    binding = {
        "operation_id": str(uuid4()),
        "expires_at": 1200,
        "native_binding": {"operation_id": str(uuid4())},
    }
    if fault == "expired":
        binding["expires_at"] = 1000
    tx.one.side_effect = [
        {"state": "running", "stopped": fault == "stopped"},
        {"binding": binding},
    ]
    reader.return_value = {
        "grant_sha256": digest(binding),
        "binding_sha256": digest(binding["native_binding"]),
        "measured_at": 1000,
        "bytes_completed": 4096,
        "disks_completed": 1,
        "artifact_complete": False,
        "evidence_source": "worker_custody_journal",
    }
    if fault == "foreign":
        reader.return_value["grant_sha256"] = digest("different-grant")
    if fault == "stale":
        reader.return_value["measured_at"] = 900
    if fault == "unavailable":
        reader.side_effect = OSError("unavailable")
    workflow = NativeWorkflow(database, MagicMock(), lambda: 1000)
    value = workflow.transfer_progress(p["scope"]["tenant_id"], str(uuid4()), reader)
    if fault:
        assert value is None
        if fault in {"stopped", "expired"}:
            reader.assert_not_called()
    else:
        assert value is not None
        assert value["operation_id"] == binding["operation_id"]
        assert value["bytes_completed"] == 4096
        reader.assert_called_once_with(binding)
