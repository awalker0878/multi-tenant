"""Scoped P09 control API; clients submit plan references, never owner proof or budgets."""

import asyncio
import json
import re
from collections.abc import Callable
from typing import Any

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from lifecycle.application.adoption import Adoptions
from lifecycle.application.enterprise import Enterprise
from lifecycle.application.execution_ports import RequestAuthority
from lifecycle.domain.execution import Rejected, decode, identity
from lifecycle.domain.expansion import scope as native_scope
from lifecycle.domain.native_workflow import checksum, exact, integer
from lifecycle.interfaces.execution import UUID, single


class ExpansionApp:
    def __init__(
        self,
        adoptions: Adoptions,
        enterprise: Enterprise,
        authority: RequestAuthority,
        plans: Callable[[str, dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.adoptions, self.enterprise, self.authority, self.plans = (
            adoptions,
            enterprise,
            authority,
            plans,
        )

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return
        try:
            match = re.fullmatch(
                rf"/v1/tenants/({UUID})/expansion/(adoptions|waves)(?:/({UUID}))?(?:/(commands))?",
                scope["path"],
            )
            if match is None or scope["method"] not in {"GET", "POST"} or scope["query_string"]:
                raise Rejected("not_found", 404)
            tenant, kind, subject, command = match.groups()
            headers = list(scope["headers"])
            auth = single(headers, b"authorization")
            if len(headers) > 40 or not re.fullmatch(r"Bearer [A-Za-z0-9_-]{32,4096}", auth):
                raise Rejected("invalid_workload", 401)
            await asyncio.to_thread(self.authority.caller, auth[7:], "console")
            body: dict[str, Any] = {}
            if scope["method"] == "POST":
                if single(headers, b"content-type").split(";")[0] != "application/json" or any(
                    k.lower() == b"content-encoding" for k, _ in headers
                ):
                    raise Rejected("unsupported_content_type", 415)
                raw = bytearray()
                async with asyncio.timeout(5):
                    while True:
                        event = await receive()
                        if event["type"] != "http.request":
                            raise Rejected("interrupted", 400)
                        raw.extend(event["body"])
                        if len(raw) > 262144:
                            raise Rejected("expansion_request_bound", 413)
                        if not event.get("more_body", False):
                            break
                body = decode(bytes(raw))
            action = (
                "operation.read"
                if scope["method"] == "GET"
                else "operation.control"
                if subject
                else "operation.admit"
            )
            scopes: list[dict[str, Any]] = []
            specs: list[dict[str, Any]] = []
            if subject:
                if kind == "adoptions":
                    current = await asyncio.to_thread(self.adoptions.read, tenant, subject)
                    scopes = [current["scope"]]
                else:
                    current = await asyncio.to_thread(self.enterprise.read, tenant, subject)
                    specs = await asyncio.to_thread(self.enterprise.specifications, tenant, subject)
                    scopes = [s["scope"] for s in specs]
            elif scope["method"] == "POST" and not command:
                if kind == "adoptions":
                    exact(body, {"scope", "fields"})
                    scopes = [native_scope(body["scope"])]
                else:
                    exact(body, {"plans"})
                    if not isinstance(body["plans"], list) or not 1 <= len(body["plans"]) <= 100:
                        raise Rejected("enterprise_plan_bound", 422)
                    for ref in body["plans"]:
                        exact(ref, {"id", "revision", "sha256"})
                        identity(ref["id"])
                        integer(ref["revision"], 1)
                        checksum(ref["sha256"])
                        specs.append(await asyncio.to_thread(self.plans, tenant, ref))
                    scopes = [s["scope"] for s in specs]
            else:
                raise Rejected("not_found", 404)
            actors = set()
            for bound in scopes:
                grant_scope = {k: bound[k] for k in ("site_id", "environment", "resource_id")}
                actors.add(
                    await asyncio.to_thread(
                        self.authority.actor,
                        single(headers, b"x-actor-delegation"),
                        tenant,
                        action,
                        grant_scope,
                    )
                )
            if len(actors) != 1:
                raise Rejected("expansion_actor_scope_denied", 403)
            actor = actors.pop()
            if scope["method"] == "GET" and subject and not command:
                payload, status = current, 200
            elif scope["method"] == "POST" and subject and command:
                expected = {"action", "expected_revision"} | (
                    {"proposed_fields"} if kind == "adoptions" else set()
                )
                exact(body, expected)
                key = identity(single(headers, b"idempotency-key"))
                revision = integer(body["expected_revision"], 1)
                if kind == "adoptions":
                    payload = await asyncio.to_thread(
                        self.adoptions.command,
                        tenant,
                        subject,
                        actor,
                        key,
                        revision,
                        body["action"],
                        body["proposed_fields"],
                    )
                else:
                    payload = await asyncio.to_thread(
                        self.enterprise.control,
                        tenant,
                        subject,
                        actor,
                        key,
                        revision,
                        body["action"],
                    )
                status = 202
            elif scope["method"] == "POST" and not subject:
                key = identity(single(headers, b"idempotency-key"))
                if kind == "adoptions":
                    payload = await asyncio.to_thread(
                        self.adoptions.create, tenant, actor, key, body["scope"], body["fields"]
                    )
                else:
                    payload = await asyncio.to_thread(
                        self.enterprise.create, tenant, actor, key, specs
                    )
                status = 201
            else:
                raise Rejected("not_found", 404)
        except Rejected as error:
            status, payload = error.status, {"error": error.reason}
        except (ValueError, KeyError, TypeError):
            status, payload = 422, {"error": "invalid_expansion_request"}
        except Exception:
            status, payload = 503, {"error": "expansion_unavailable"}
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"cache-control", b"no-store"),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": json.dumps(payload, allow_nan=False, default=str).encode(),
            }
        )
