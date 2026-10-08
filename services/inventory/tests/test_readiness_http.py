"""Readiness HTTP delegation, immutable writes and tenant isolation over PostgreSQL."""

import asyncio
import json
from dataclasses import replace
from typing import Any

from test_discovery import Campaign
from uvicorn._types import ASGIReceiveEvent, ASGISendEvent, HTTPScope

from inventory.application.discovery import uid
from inventory.domain.discovery import Actor, Rejected, Worker
from inventory.interfaces.discovery import InventoryApp

pytest_plugins = ["test_discovery"]


class Authority:
    def __init__(self, actor: Actor) -> None:
        self.current = actor
        self.denied = False

    def actor(
        self, credential: str, delegation: str, tenant: str, action: str, site: str | None
    ) -> Actor:
        if self.denied or credential != "a" * 64 or delegation != "delegated":
            raise Rejected("delegation_denied", 403)
        assert action == "inventory.admin"
        return replace(self.current, tenant=tenant, site=site, action=action)

    def worker(self, credential: str) -> Worker:
        raise Rejected("worker_denied", 403)


def request(
    app: InventoryApp, path: str, body: dict[str, Any] | None = None
) -> tuple[int, dict[str, Any]]:
    scope: HTTPScope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "http_version": "1.1",
        "method": "GET" if body is None else "POST",
        "scheme": "https",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"authorization", b"Bearer " + b"a" * 64),
            (b"x-actor-delegation", b"delegated"),
            (b"content-type", b"application/json"),
            (b"idempotency-key", uid().encode()),
        ],
        "client": ("127.0.0.1", 8000),
        "server": ("127.0.0.1", 8080),
        "state": {},
    }
    events: list[ASGISendEvent] = []

    async def receive() -> ASGIReceiveEvent:
        return {"type": "http.request", "body": json.dumps(body).encode(), "more_body": False}

    async def send(event: ASGISendEvent) -> None:
        events.append(event)

    asyncio.run(app(scope, receive, send))
    start, output = events
    assert start["type"] == "http.response.start" and output["type"] == "http.response.body"
    assert (b"cache-control", b"no-store, private") in start["headers"]
    return start["status"], json.loads(output["body"])


def test_readiness_route_saves_context_rejects_authority_and_rechecks_access(
    campaign: Campaign,
) -> None:
    c = campaign
    authority = Authority(c.actor)
    app = InventoryApp(c.service, authority)
    path = f"/v1/tenants/{c.actor.tenant}/sites/{c.actor.site}/operator-readiness"
    body = {
        "values": {"max_outage_seconds": 0},
        "configuration_digest": None,
        "context": {"operation": "migrate", "method": "VM_COLD_EXPORT"},
    }
    assert request(app, path, {**body, "native_write_authorized": True})[0] == 422
    status, saved = request(app, path, body)
    assert status == 201 and saved["native_write_authorized"] is False
    status, view = request(app, path)
    assert status == 200 and view["context"] == body["context"]
    assert view["record"]["values"]["max_outage_seconds"] == 0
    assert request(app, path, body)[0] == 428
    assert request(app, path.replace(c.actor.tenant, uid()))[1]["record"] is None
    assert request(app, path.replace(c.actor.site or "", uid()))[1]["record"] is None
    authority.denied = True
    assert request(app, path)[0] == request(app, path, body)[0] == 403
