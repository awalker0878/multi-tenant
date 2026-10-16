"""Reject worker identities that the effect owner cannot accept before issuing grants."""

import asyncio
import json
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import pytest
from temporalio.client import Client
from uvicorn._types import Scope

from lifecycle.application.execution import Execution
from lifecycle.bootstrap import workflow
from lifecycle.domain.execution import Rejected
from lifecycle.interfaces.execution import ExecutionApp

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


@pytest.mark.parametrize("worker", [WORKER, "sim-worker"])
def test_redemption_http_passes_only_the_canonical_grant_worker(worker: str) -> None:
    execution, authority = Mock(), Mock()
    execution.redeem.return_value = {"allowed": True, "simulation": True}
    emitted: list[Any] = []

    async def receive() -> Any:
        return {
            "type": "http.request",
            "body": json.dumps({"worker_id": worker}).encode(),
            "more_body": False,
        }

    async def send(message: Any) -> None:
        emitted.append(message)

    scope = cast(
        Scope,
        {
            "type": "http",
            "method": "POST",
            "query_string": b"",
            "path": "/internal/simulation-grants/redemptions",
            "headers": [
                (b"authorization", b"Bearer " + b"s" * 64),
                (b"content-type", b"application/json"),
            ],
        },
    )
    asyncio.run(ExecutionApp(execution, authority)(scope, receive, send))
    authority.caller.assert_called_once_with("s" * 64, "simulator")
    if worker == WORKER:
        assert emitted[0]["status"] == 200
        execution.redeem.assert_called_once_with({"worker_id": WORKER}, WORKER)
    else:
        assert emitted[0]["status"] == 422
        execution.redeem.assert_not_called()
