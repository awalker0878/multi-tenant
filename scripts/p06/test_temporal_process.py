"""Unit checks of the replay witness's executor lifetime, without a Temporal server."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import temporal_process


@pytest.mark.parametrize("fail_replay", [False, True])
def test_replay_shares_and_closes_executor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_replay: bool
) -> None:
    workflows = ["first-workflow", "second-workflow"]
    source = tmp_path / "workflows.json"
    source.write_text(json.dumps(workflows))
    output = tmp_path / "replay.json"
    histories = [SimpleNamespace(events=[1]), SimpleNamespace(events=[1, 2])]
    handles = [
        SimpleNamespace(fetch_history=AsyncMock(return_value=h)) for h in histories
    ]
    client = SimpleNamespace(get_workflow_handle=Mock(side_effect=handles))
    monkeypatch.setattr(temporal_process, "client", AsyncMock(return_value=client))
    monkeypatch.setattr(
        temporal_process.sys, "argv", ["witness", "replay", str(source), str(output)]
    )
    executors: list[ThreadPoolExecutor] = []
    replayed = []

    class ReplayWitness:
        def __init__(self, *, workflows, workflow_task_executor):
            executors.append(workflow_task_executor)
            self.executor = workflow_task_executor

        async def replay_workflow(self, history):
            # Exercise an actual worker thread so shutdown is observable. This
            # stub checks ownership only; it does not qualify Temporal replay.
            replayed.append(
                await asyncio.wrap_future(self.executor.submit(lambda: history))
            )
            assert not output.exists()
            if fail_replay and len(replayed) == 2:
                raise RuntimeError("replay_failed")

    monkeypatch.setattr(temporal_process, "Replayer", ReplayWitness)
    if fail_replay:
        with pytest.raises(RuntimeError, match="replay_failed"):
            asyncio.run(temporal_process.main())
        assert not output.exists()
    else:
        asyncio.run(temporal_process.main())
        assert json.loads(output.read_text()) == [
            {"workflow_id": workflow, "events": len(history.events), "replay": "PASS"}
            for workflow, history in zip(workflows, histories, strict=True)
        ]

    assert replayed == histories
    assert client.get_workflow_handle.call_count == 2
    assert len(executors) == 1
    with pytest.raises(
        RuntimeError, match="cannot schedule new futures after shutdown"
    ):
        executors[0].submit(lambda: None)
