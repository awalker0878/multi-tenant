"""A10/A11/A13: current native evidence and a live owner receipt are both required."""

from copy import deepcopy
from typing import Any
from unittest.mock import Mock

import pytest
from planning_fixture import NOW, inputs

from planning.domain.compilation import compile_plan
from planning.domain.model import Rejected, digest
from planning.domain.placement import fit
from planning.infrastructure.owners import qualification_current


@pytest.mark.parametrize(
    "fault", ["none", "missing_receipt", "released", "vector", "restore", "network", "legacy"]
)
def test_every_unattended_read_rechecks_evidence_and_reserved_vectors(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    from planning_fixture import assessment, request

    intent, destination, profile, policy, qualification = inputs()
    content = compile_plan(assessment(), 0, request())
    plan: dict[str, Any] = {
        "content": content,
        "binding": {"digest": "e" * 64},
        "inputs": [{
            "destination": destination, "profile": profile, "policy": policy,
            "qualification": qualification,
        }],
        "source_intent": intent,
    }
    current_destination = deepcopy(destination)
    allocations = fit(intent, destination["capability_snapshot"]["data"]["pools"], policy, NOW)[
        "allocations"
    ]
    receipt = {
        "state": "reserved", "tenant_id": destination["tenant_id"],
        "plan_digest": plan["binding"]["digest"],
        "placement_sha256": digest(allocations), "allocations": allocations,
        "generation_id": destination["generation_id"], "policy_sha256": digest(policy),
        "observed_at": NOW, "expires_at": NOW + 30,
    }
    if fault == "missing_receipt":
        receipt = {}
    elif fault == "released":
        receipt["state"] = "released"
    elif fault == "vector":
        receipt["placement_sha256"] = "f" * 64
    elif fault == "restore":
        current_destination["capability_snapshot"]["data"]["recovery_measurements"][0][
            "outcome"
        ] = "failed"
    elif fault == "network":
        current_destination["capability_snapshot"]["data"]["network"]["measurements"][0][
            "outcome"
        ] = "deny"
    elif fault == "legacy":
        qualification["version"] = 1
    reads = Mock(side_effect=[qualification, current_destination, receipt])
    monkeypatch.setattr("planning.infrastructure.owners.request", reads)
    monkeypatch.setattr("planning.infrastructure.owners.time.time", lambda: NOW)
    if fault == "none":
        qualification_current(plan)
        assert reads.call_count == 3
    else:
        with pytest.raises(Rejected):
            qualification_current(plan)
