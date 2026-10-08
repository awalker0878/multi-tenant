"""Native API effect entrypoint cannot accept caller identity, commands or readiness claims."""

import asyncio
import json
from copy import deepcopy
from typing import Any
from uuid import uuid4

import pytest
from test_native import GrantClient, Journal, Observer, Tool, stage_grant
from test_native import binding as binding

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest
from lifecycle_worker.application.native_effect import NativeApiEffect
from lifecycle_worker.interfaces.native import NativeEffectApp


@pytest.fixture
def effect(binding: NativeBinding) -> tuple[NativeApiEffect, Any, Journal, Tool, list[str]]:
    client, journal = GrantClient(), Journal()
    tool = Tool(journal)
    resolutions: list[str] = []

    class Tooling:
        def resolve(self, supplied: NativeBinding) -> tuple[Tool, Observer]:
            resolutions.append(supplied.fingerprint)
            return tool, Observer()

    return (
        NativeApiEffect(client, journal, Tooling(), lambda: 100),
        client,
        journal,
        tool,
        resolutions,
    )


def invoke(
    app: NativeEffectApp, body: Any, headers: list[tuple[bytes, bytes]] | None = None
) -> tuple[int, dict[str, Any]]:
    async def run() -> tuple[int, dict[str, Any]]:
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        events: list[Any] = []
        scope: Any = {
            "type": "http",
            "method": "POST",
            "path": "/internal/native-effects",
            "query_string": b"",
            "headers": headers
            if headers is not None
            else [
                (b"authorization", b"Bearer " + b"a" * 32),
                (b"content-type", b"application/json"),
            ],
        }

        async def receive() -> Any:
            return {"type": "http.request", "body": raw, "more_body": False}

        async def send(value: Any) -> None:
            events.append(value)

        await app(scope, receive, send)
        assert (b"cache-control", b"no-store, private") in events[0]["headers"]
        return events[0]["status"], json.loads(events[1]["body"])

    return asyncio.run(run())


def test_effect_uses_live_authority_and_never_repeats_claim(
    binding: NativeBinding, effect: Any
) -> None:
    service, client, journal, tool, resolutions = effect
    grant = stage_grant(binding)
    result = service.execute(binding.tenant_id, binding.executor_id, grant)
    assert result == {
        "grant_sha256": digest(grant),
        "submitted": True,
        "readiness_established": False,
        "retry_authorized": False,
    }
    assert tool.calls == 1 and journal.claimed
    assert client.calls == [
        "preflight",
        "preflight",
        "before_api_sequence",
        "during_api_sequence",
    ]
    with pytest.raises(NativeHeld):
        service.execute(binding.tenant_id, binding.executor_id, grant)
    assert tool.calls == 1


@pytest.mark.parametrize("foreign", ["tenant", "worker"])
def test_foreign_caller_cannot_resolve_artifacts(
    binding: NativeBinding, effect: Any, foreign: str
) -> None:
    service, client, journal, tool, resolutions = effect
    with pytest.raises(NativeHeld):
        service.execute(
            str(uuid4()) if foreign == "tenant" else binding.tenant_id,
            str(uuid4()) if foreign == "worker" else binding.executor_id,
            stage_grant(binding),
        )
    assert not resolutions and not client.calls and tool.calls == 0


def test_revoked_authority_stops_before_artifact_resolution(
    binding: NativeBinding, effect: Any
) -> None:
    service, client, journal, tool, resolutions = effect
    client.fail = "preflight"
    with pytest.raises(NativeHeld):
        service.execute(binding.tenant_id, binding.executor_id, stage_grant(binding))
    assert not resolutions and tool.calls == 0


def test_effect_http_uses_trusted_caller_and_fixed_receipt(
    binding: NativeBinding, effect: Any
) -> None:
    service, client, journal, tool, resolutions = effect

    def caller(token: str) -> tuple[str, str]:
        if token != "a" * 32:
            raise NativeHeld("not_trusted")
        return binding.tenant_id, binding.executor_id

    app = NativeEffectApp(service, caller)
    body = {"grant": stage_grant(binding)}
    for field in ("tenant_id", "worker_id", "command", "native_write_authorized"):
        status, result = invoke(app, body | {field: "caller_controlled"})
        assert status == 422 and tool.calls == 0
    status, result = invoke(app, body)
    assert status == 200 and result["readiness_established"] is False
    assert result["grant_sha256"] == digest(body["grant"]) and tool.calls == 1
    status, result = invoke(app, body)
    assert status == 423 and tool.calls == 1


@pytest.mark.parametrize(
    "body", [b"{}", b'{"grant":{},"grant":{}}', b'{"grant":NaN}', b"[]", b"x" * 16385]
)
def test_effect_http_malformed_body_never_executes(
    binding: NativeBinding, effect: Any, body: bytes
) -> None:
    service, client, journal, tool, resolutions = effect
    app = NativeEffectApp(service, lambda token: (binding.tenant_id, binding.executor_id))
    assert invoke(app, body)[0] in {413, 422}
    assert not client.calls and not resolutions and tool.calls == 0


@pytest.mark.parametrize(
    "headers",
    [
        [],
        [(b"authorization", b"Bearer " + b"a" * 32)] * 2,
        [(b"authorization", b"Bearer " + b"a" * 32), (b"content-encoding", b"gzip")],
        [(b"authorization", b"Bearer " + b"a" * 32), (b"content-type", b"text/plain")],
    ],
)
def test_effect_http_header_controls(binding: NativeBinding, effect: Any, headers: Any) -> None:
    service, client, journal, tool, resolutions = effect
    app = NativeEffectApp(service, lambda token: (binding.tenant_id, binding.executor_id))
    assert invoke(app, {"grant": stage_grant(binding)}, headers)[0] in {401, 413, 415}
    assert not resolutions and tool.calls == 0


def test_non_provision_grant_is_held_before_tooling(binding: NativeBinding, effect: Any) -> None:
    service, client, journal, tool, resolutions = effect
    grant = deepcopy(stage_grant(binding))
    grant["stage"] = "retire"
    with pytest.raises(NativeHeld):
        service.execute(binding.tenant_id, binding.executor_id, grant)
    assert not resolutions and not client.calls and tool.calls == 0


def test_continuation_reuses_live_redeemed_authority_without_new_claim_or_mutation(
    binding: NativeBinding,
) -> None:
    client, journal = GrantClient(), Journal()
    journal.claim(binding)

    class Resumable(Tool):
        def resume_transfer(self, b: NativeBinding, boundary: Any) -> None:
            boundary()
            self.calls += 1

    tool = Resumable(journal)

    class Runtime:
        def resolve(self, b: NativeBinding) -> tuple[Resumable, Observer]:
            return tool, Observer()

    service = NativeApiEffect(client, journal, Runtime(), lambda: 100)
    result = service.continue_transfer(binding.tenant_id, binding.executor_id, stage_grant(binding))
    assert result["submitted"] is True and tool.calls == 1
    assert client.calls and set(client.calls) == {"during_api_sequence"}
    client.fail = "during_api_sequence"
    with pytest.raises(NativeHeld):
        service.continue_transfer(binding.tenant_id, binding.executor_id, stage_grant(binding))
    assert tool.calls == 1


def test_progress_reads_durable_counters_without_claiming_or_running_effect(
    binding: NativeBinding,
) -> None:
    class MeasuredJournal(Journal):
        def archive_progress(self, supplied: NativeBinding) -> dict[str, Any]:
            assert supplied == binding
            return {"bytes_completed": 1048576, "disks_completed": 1, "artifact_complete": False}

    client, journal = GrantClient(), MeasuredJournal()
    tool = Tool(journal)

    class Runtime:
        def resolve(self, supplied: NativeBinding) -> tuple[Tool, Observer]:
            raise AssertionError("progress cannot resolve or run native effects")

    service = NativeApiEffect(client, journal, Runtime(), lambda: 100)
    grant = stage_grant(binding) | {
        "schema_version": 2,
        "stage": "export_copy",
        "intent_digest": binding.operation_plan_sha256,
    }
    result = service.progress(binding.tenant_id, binding.executor_id, grant)
    assert result["bytes_completed"] == 1048576 and result["disks_completed"] == 1
    assert result["measured_at"] == 100 and result["artifact_complete"] is False
    assert result["evidence_source"] == "worker_custody_journal"
    assert (
        result["grant_sha256"] == digest(grant) and result["binding_sha256"] == binding.fingerprint
    )
    assert not journal.claimed and not tool.calls
    client.fail = "during_api_sequence"
    with pytest.raises(NativeHeld):
        service.progress(binding.tenant_id, binding.executor_id, grant)
