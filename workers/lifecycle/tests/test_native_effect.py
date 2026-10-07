"""Saved-plan effect entrypoint cannot accept caller identity, commands or readiness claims."""

import asyncio
import json
from copy import deepcopy
from typing import Any
from uuid import uuid4

import pytest
from test_native import GrantClient, Journal, Observer, Tool, stage_grant
from test_native import binding as binding

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest
from lifecycle_worker.application.native_effect import NativeSavedPlanEffect
from lifecycle_worker.interfaces.native import NativeEffectApp


@pytest.fixture
def effect(binding: NativeBinding) -> tuple[NativeSavedPlanEffect, Any, Journal, Tool, list[str]]:
    client, journal = GrantClient(), Journal()
    tool = Tool(journal)
    resolutions: list[str] = []

    class Tooling:
        def resolve(self, supplied: NativeBinding) -> tuple[Tool, Observer]:
            resolutions.append(supplied.fingerprint)
            return tool, Observer()

    return (
        NativeSavedPlanEffect(client, journal, Tooling(), lambda: 100),
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
    assert tool.applies == 1 and journal.claimed
    assert client.calls == [
        "preflight",
        "preflight",
        "before_saved_plan_apply",
        "during_saved_plan_apply",
    ]
    with pytest.raises(NativeHeld):
        service.execute(binding.tenant_id, binding.executor_id, grant)
    assert tool.applies == 1


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
    assert not resolutions and not client.calls and tool.applies == 0


def test_revoked_authority_stops_before_artifact_resolution(
    binding: NativeBinding, effect: Any
) -> None:
    service, client, journal, tool, resolutions = effect
    client.fail = "preflight"
    with pytest.raises(NativeHeld):
        service.execute(binding.tenant_id, binding.executor_id, stage_grant(binding))
    assert not resolutions and tool.applies == 0


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
        assert status == 422 and tool.applies == 0
    status, result = invoke(app, body)
    assert status == 200 and result["readiness_established"] is False
    assert result["grant_sha256"] == digest(body["grant"]) and tool.applies == 1
    status, result = invoke(app, body)
    assert status == 423 and tool.applies == 1


@pytest.mark.parametrize(
    "body", [b"{}", b'{"grant":{},"grant":{}}', b'{"grant":NaN}', b"[]", b"x" * 16385]
)
def test_effect_http_malformed_body_never_executes(
    binding: NativeBinding, effect: Any, body: bytes
) -> None:
    service, client, journal, tool, resolutions = effect
    app = NativeEffectApp(service, lambda token: (binding.tenant_id, binding.executor_id))
    assert invoke(app, body)[0] in {413, 422}
    assert not client.calls and not resolutions and tool.applies == 0


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
    assert not resolutions and tool.applies == 0


def test_non_provision_grant_is_held_before_tooling(binding: NativeBinding, effect: Any) -> None:
    service, client, journal, tool, resolutions = effect
    grant = deepcopy(stage_grant(binding))
    grant["stage"] = "retire"
    with pytest.raises(NativeHeld):
        service.execute(binding.tenant_id, binding.executor_id, grant)
    assert not resolutions and not client.calls and tool.applies == 0
