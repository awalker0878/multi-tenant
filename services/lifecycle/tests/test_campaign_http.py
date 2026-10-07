"""Campaign authorization, trusted plan resolution and separate observation publishers."""

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from test_campaign import member, settings
from test_migration import migration_plan
from uvicorn._types import ASGIReceiveEvent, ASGISendEvent, HTTPScope

from lifecycle.application.campaigns import Campaigns
from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected
from lifecycle.infrastructure.campaign_observers import CampaignObservers
from lifecycle.interfaces.campaign_observations import CampaignObservationApp
from lifecycle.interfaces.campaigns import CampaignApp, plan_requirements

TOKEN = "a" * 64


def request(
    app: Any,
    path: str,
    body: Any = None,
    headers: list[tuple[bytes, bytes]] | None = None,
    query: bytes = b"",
) -> tuple[int, dict[str, Any]]:
    scope: HTTPScope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "http_version": "1.1",
        "method": "GET" if body is None else "POST",
        "scheme": "https",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query,
        "root_path": "",
        "headers": headers
        if headers is not None
        else [
            (b"authorization", ("Bearer " + TOKEN).encode()),
            (b"content-type", b"application/json"),
            (b"x-actor-delegation", b"d" * 64),
            (b"idempotency-key", str(uuid4()).encode()),
        ],
        "client": ("127.0.0.1", 1234),
        "server": ("127.0.0.1", 443),
        "state": {},
    }
    events: list[ASGISendEvent] = []

    async def receive() -> ASGIReceiveEvent:
        return {"type": "http.request", "body": json.dumps(body).encode(), "more_body": False}

    async def send(event: ASGISendEvent) -> None:
        events.append(event)

    asyncio.run(app(scope, receive, send))
    start, response = events
    assert start["type"] == "http.response.start" and response["type"] == "http.response.body"
    assert b"no-store" in dict(start["headers"])[b"cache-control"]
    return start["status"], json.loads(response["body"])


def proposal() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    plan = migration_plan()
    m = member(plan)
    requirements = {k: m[k] for k in ("route_sha256", "sizes", "demands", "mode", "method")}
    ref = {k: v for k, v in m.items() if k not in requirements}
    content = {
        "action": "application.migrate",
        "execution_ready": True,
        "migration_campaign": requirements,
    }
    binding = {
        "plan_id": plan["plan_id"],
        "revision": plan["plan_revision"],
        **{k: plan["scope"][k] for k in ("tenant_id", "site_id", "environment", "resource_id")},
        "requested_by": plan["actor_id"],
        "lane": "operational",
        "content_digest": digest(content),
    }
    binding["digest"] = digest(binding)
    ref["plan_digest"] = binding["digest"]
    return {"content": content, "binding": binding, "invalidated": False}, ref, plan


def test_authenticated_plan_must_be_complete_unchanged_and_operational() -> None:
    record, ref, plan = proposal()
    tenant = plan["scope"]["tenant_id"]
    assert plan_requirements(record, ref, tenant)["requirements"]["sizes"]["transfer"] == 1024
    for bad in (
        record | {"invalidated": True},
        record | {"content": record["content"] | {"execution_ready": False}},
        record | {"binding": record["binding"] | {"lane": "isolated_campaign"}},
    ):
        with pytest.raises(Rejected):
            plan_requirements(bad, ref, tenant)
    with pytest.raises(Rejected):
        plan_requirements(record, ref, str(uuid4()))


def test_authentication_precedes_plan_and_campaign_reads() -> None:
    campaigns, authority, source = MagicMock(), MagicMock(), MagicMock()
    authority.caller.side_effect = Rejected("invalid_workload", 401)
    app = CampaignApp(campaigns, authority, source)
    status, _ = request(app, f"/v1/tenants/{uuid4()}/migration-campaigns/{uuid4()}")
    assert status == 401
    campaigns.read.assert_not_called()
    source.assert_not_called()


def test_console_cannot_publish_sizes_routes_or_observations() -> None:
    record, ref, plan = proposal()
    campaigns, authority, source = MagicMock(), MagicMock(), MagicMock()
    authority.actor.return_value = plan["actor_id"]
    source.return_value = plan_requirements(record, ref, plan["scope"]["tenant_id"])
    app = CampaignApp(campaigns, authority, source)
    path = f"/v1/tenants/{plan['scope']['tenant_id']}/migration-campaigns"
    scope = source.return_value["scope"]
    for key, value in (
        ("sizes", {}),
        ("route_sha256", "a" * 64),
        ("demands", {}),
        ("performance", []),
    ):
        status, _ = request(
            app, path, {"scope": scope, "settings": settings(), "members": [ref | {key: value}]}
        )
        assert status == 422
    campaigns.create.assert_not_called()
    source.assert_not_called()


def test_create_read_list_and_pause_require_current_scoped_actor(database: Any) -> None:
    record, ref, plan = proposal()
    tenant = plan["scope"]["tenant_id"]

    def source(t: str, r: dict[str, Any]) -> dict[str, Any]:
        return plan_requirements(record, r, t)

    authority = MagicMock()
    authority.actor.return_value = plan["actor_id"]
    app = CampaignApp(Campaigns(database, lambda: 1000), authority, source)
    scope = source(tenant, ref)["scope"]
    path = f"/v1/tenants/{tenant}/migration-campaigns"
    status, created = request(app, path, {"scope": scope, "settings": settings(), "members": [ref]})
    assert status == 202 and created["state"] == "draft"
    detail = path + "/" + created["id"]
    status, read = request(app, detail)
    assert (
        status == 200
        and read["members"][0]["specification"]["sizes"]
        == record["content"]["migration_campaign"]["sizes"]
    )
    status, rows = request(app, path, query=urlencode(scope).encode())
    assert status == 200 and rows["items"][0]["id"] == created["id"]
    assert (
        request(app, path, query=urlencode(scope | {"resource_id": str(uuid4())}).encode())[1][
            "items"
        ]
        == []
    )
    assert (
        request(app, detail + "/commands", {"action": "pause", "expected_revision": 1})[1]["state"]
        == "paused"
    )
    authority.actor.side_effect = Rejected("actor_revoked", 403)
    assert request(app, detail)[0] == 403
    assert (
        request(app, detail + "/commands", {"action": "schedule", "expected_revision": 2})[0] == 403
    )


def test_observer_grants_rotate_expire_and_never_cross_tenant_or_kind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    token, registry = tmp_path / "token", tmp_path / "registry.json"
    token.write_text(TOKEN)
    tenant, observer = str(uuid4()), str(uuid4())
    grant = {
        "tenant_id": tenant,
        "observer_id": observer,
        "kind": "performance",
        "token_file": str(token),
        "resources": [digest("route")],
        "expires_at": 2000,
    }
    registry.write_text(json.dumps({"schema_version": 1, "grants": [grant]}))
    monkeypatch.setenv("LIFECYCLE_CAMPAIGN_OBSERVERS_FILE", str(registry))
    monkeypatch.setattr("lifecycle.infrastructure.campaign_observers.time.time", lambda: 1000)
    authority = CampaignObservers()
    value = {"route_sha256": digest("route")}
    assert authority.authorize(TOKEN, tenant, "performance", value) == observer
    for t, kind, payload in (
        (str(uuid4()), "performance", value),
        (tenant, "capacity", {"pool_key": digest("route")}),
        (tenant, "performance", {"route_sha256": digest("other")}),
    ):
        with pytest.raises(Rejected, match="observation_scope_denied"):
            authority.authorize(TOKEN, t, kind, payload)
    token.write_text("b" * 64)
    with pytest.raises(Rejected, match="observation_caller_denied"):
        authority.authorize(TOKEN, tenant, "performance", value)
    registry.write_text(json.dumps({"schema_version": 1, "grants": [grant | {"expires_at": 1000}]}))
    with pytest.raises(Rejected, match="observation_scope_denied"):
        authority.authorize("b" * 64, tenant, "performance", value)


def test_observation_api_rejects_console_credential_before_publication() -> None:
    campaigns, authority = (
        MagicMock(),
        MagicMock(side_effect=Rejected("observation_caller_denied", 401)),
    )
    app = CampaignObservationApp(campaigns, authority)
    assert (
        request(
            app,
            f"/internal/tenants/{uuid4()}/migration-observations/performance",
            {"route_sha256": digest("route")},
        )[0]
        == 401
    )
    campaigns.sample.assert_not_called()
