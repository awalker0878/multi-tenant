"""Reject worker identities that the effect owner cannot accept before issuing grants."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from temporalio.client import Client

from lifecycle.application.execution import Execution
from lifecycle.bootstrap import workflow
from lifecycle.domain.execution import Rejected

WORKER = "30000000-0000-4000-8000-000000000001"


@pytest.mark.parametrize("worker", ["sim-worker", "", "30000000-0000-4000-8000-00000000000G"])
def test_non_uuid_worker_cannot_acquire_or_redeem_durable_authority(worker: str) -> None:
    database = Mock()
    execution = Execution(database, Mock(), Mock(), Mock(), lambda: 0)
    with pytest.raises(Rejected, match="invalid_identity"):
        execution.acquire(WORKER, WORKER, "reserve", worker)
    with pytest.raises(Rejected, match="invalid_identity"):
        execution.redeem({"worker_id": WORKER}, worker)
    with pytest.raises(Rejected, match="invalid_identity"):
        execution.redeem({"worker_id": worker}, WORKER)
    database.transaction.assert_not_called()


def test_poller_rejects_missing_or_non_uuid_configuration_before_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connect = AsyncMock()
    monkeypatch.setattr(Client, "connect", connect)
    monkeypatch.delenv("LIFECYCLE_SIMULATION_WORKER_ID", raising=False)
    with pytest.raises(KeyError):
        asyncio.run(workflow.run())
    monkeypatch.setenv("LIFECYCLE_SIMULATION_WORKER_ID", "sim-worker")
    with pytest.raises(Rejected, match="invalid_identity"):
        asyncio.run(workflow.run())
    connect.assert_not_called()
