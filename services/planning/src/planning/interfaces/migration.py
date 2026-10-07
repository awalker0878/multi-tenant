"""Authenticated migration preparation; returns bindings, never execution authority."""

import asyncio
import json
import re
from collections.abc import Callable
from typing import Any

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from planning.application.ports import Authority
from planning.domain.model import Rejected, decode, identifier, integer, sha, shape
from planning.interfaces.planning import UUID, single


class MigrationPreparationApp:
    def __init__(self, authority: Authority, prepare: Callable[..., dict[str, Any]]) -> None:
        self.authority, self.prepare = authority, prepare

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return
        try:
            route = re.fullmatch(
                rf"/v1/tenants/({UUID})/applications/({UUID})/environments/({UUID})/migration-preparations",
                scope["path"],
            )
            if route is None or scope["method"] != "POST" or scope["query_string"]:
                raise Rejected("not_found", 404)
            headers = list(scope["headers"])
            auth = single(headers, b"authorization")
            if len(headers) > 40 or not re.fullmatch(r"Bearer [A-Za-z0-9_-]{32,4096}", auth):
                raise Rejected("invalid_workload", 401)
            if single(headers, b"content-type").split(";")[0] != "application/json" or single(
                headers, b"content-encoding", True
            ):
                raise Rejected("unsupported_content_type", 415)
            await asyncio.to_thread(self.authority.caller, auth[7:])
            chunks = bytearray()
            async with asyncio.timeout(5):
                while True:
                    event = await receive()
                    if event["type"] != "http.request":
                        raise Rejected("interrupted", 400)
                    chunks.extend(event["body"])
                    if len(chunks) > 32768:
                        raise Rejected("request_bound", 413)
                    if not event.get("more_body", False):
                        break
            body = shape(decode(bytes(chunks)), {"site_id", "review", "disks"})
            review = shape(body["review"], {"revision", "digest"})
            site = identifier(body["site_id"])
            tenant, application, environment = route.groups()
            delegation = single(headers, b"x-actor-delegation")
            await asyncio.to_thread(
                self.authority.actor,
                auth[7:],
                delegation,
                tenant,
                "plan.create",
                application,
                environment,
                site,
            )
            binding = await asyncio.to_thread(
                self.prepare,
                tenant,
                application,
                environment,
                site,
                integer(review["revision"], 1),
                sha(review["digest"]),
                delegation,
                body["disks"],
            )
            payload = {"binding": binding, "native_write_authorized": False}
            status = 200
        except Rejected as e:
            status, payload = e.status, {"error": e.reason}
        except Exception:
            status, payload = 503, {"error": "migration_preparation_unavailable"}
        raw = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"cache-control", b"no-store, private"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": raw})
