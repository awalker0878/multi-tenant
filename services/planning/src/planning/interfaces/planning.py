"""Narrow authenticated, bounded planning API; native dispatch is absent."""

import asyncio
import json
import re
from typing import Any

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from planning.application.planning import Planning
from planning.application.ports import Authority
from planning.domain.compilation import diff
from planning.domain.model import Actor, Rejected, decode, identifier, integer, shape

UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
ROUTE = (
    rf"/v1/tenants/({UUID})/applications/({UUID})/environments/({UUID})/"
    rf"(assessments|plans)(?:/({UUID}))?(?:/(validity|diff))?"
)


def single(headers: list[tuple[bytes, bytes]], key: bytes, optional: bool = False) -> str:
    values = [v for k, v in headers if k.lower() == key]
    if not values and optional:
        return ""
    if len(values) != 1:
        raise Rejected("invalid_headers", 400)
    return values[0].decode("ascii")


class PlanningApp:
    def __init__(self, planning: Planning, authority: Authority) -> None:
        self.planning, self.authority = planning, authority

    def authorize(
        self,
        credential: str,
        tokens: dict[str, str],
        tenant: str,
        action: str,
        application: str,
        environment: str,
        candidates: list[dict[str, Any]],
    ) -> Actor:
        if not isinstance(candidates, list) or not 1 <= len(candidates) <= 3:
            raise Rejected("candidate_bound")
        actors = []
        scopes = set()
        for c in candidates:
            shape(c, {"site_id", "endpoint_id", "generation_id"})
            for value in c.values():
                identifier(value)
            if c["endpoint_id"] in scopes:
                raise Rejected("duplicate_candidate")
            scopes.add(c["endpoint_id"])
            actors.append(
                self.authority.actor(
                    credential,
                    tokens.get(c["site_id"], ""),
                    tenant,
                    action,
                    application,
                    environment,
                    c["site_id"],
                )
            )
        if any(a != actors[0] for a in actors):
            raise Rejected("actor_mismatch", 403)
        return actors[0]

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return
        try:
            headers = list(scope["headers"])
            if len(headers) > 40 or scope["query_string"]:
                raise Rejected("request_bound", 413)
            authorization = single(headers, b"authorization")
            if not re.fullmatch(r"Bearer [A-Za-z0-9_-]{32,4096}", authorization):
                raise Rejected("invalid_workload", 401)
            credential = authorization[7:]
            immutable = re.fullmatch(
                rf"/v1/plans/({UUID})/revisions/([1-9][0-9]{{0,8}})", scope["path"]
            )
            execution = re.fullmatch(
                rf"/v1/tenants/({UUID})/execution-plans/({UUID})/revisions/([1-9][0-9]{{0,8}})",
                scope["path"],
            )
            placement = re.fullmatch(
                rf"/internal/tenants/({UUID})/placement-proposals/({UUID})/"
                rf"revisions/([1-9][0-9]{{0,8}})",
                scope["path"],
            )
            if placement and scope["method"] == "GET":
                await asyncio.to_thread(self.authority.caller, credential, "lifecycle_reader")
                payload = await asyncio.to_thread(
                    self.planning.placement_proposal, placement[1], placement[2], int(placement[3])
                )
                status = 200
            elif execution and scope["method"] == "GET":
                await asyncio.to_thread(self.authority.caller, credential, "lifecycle_reader")
                payload = await asyncio.to_thread(
                    self.planning.execution_plan, execution[1], execution[2], int(execution[3])
                )
                status = 200
            elif immutable and scope["method"] == "GET":
                await asyncio.to_thread(self.authority.caller, credential, "governance_reader")
                payload = await asyncio.to_thread(
                    self.planning.bound_plan, immutable[1], int(immutable[2])
                )
                status = 200
            else:
                await asyncio.to_thread(self.authority.caller, credential)
                route = re.fullmatch(ROUTE, scope["path"])
                if not route:
                    raise Rejected("not_found", 404)
                tenant, application, environment, kind, identity, view = route.groups()
                method = scope["method"]
                if (method == "GET" and identity is None) or method not in {"GET", "POST"}:
                    raise Rejected("method_not_allowed", 405)
                body: dict[str, Any] = {}
                if method == "POST":
                    if single(headers, b"content-type").split(";")[
                        0
                    ] != "application/json" or single(headers, b"content-encoding", True):
                        raise Rejected("unsupported_content_type", 415)
                    chunks = bytearray()
                    async with asyncio.timeout(5):
                        while True:
                            message = await receive()
                            if message["type"] != "http.request":
                                raise Rejected("interrupted", 400)
                            chunks.extend(message["body"])
                            if len(chunks) > 262144:
                                raise Rejected("request_bound", 413)
                            if not message.get("more_body", False):
                                break
                    body = decode(bytes(chunks))
                raw = single(headers, b"x-planning-delegations")
                if len(raw) > 500:
                    raise Rejected("delegation_bound")
                tokens = {}
                for pair in raw.split(","):
                    site, token = pair.split(":")
                    if site in tokens:
                        raise Rejected("duplicate_delegation")
                    tokens[site] = token
                record = None
                if identity:
                    record = await asyncio.to_thread(
                        self.planning.get,
                        tenant,
                        application,
                        environment,
                        identity,
                        "assessment" if kind == "assessments" else "plan",
                    )
                    candidates = record["candidates"]
                elif kind == "plans":
                    shape(body, {"assessment_id", "candidate", "request"})
                    record = await asyncio.to_thread(
                        self.planning.get,
                        tenant,
                        application,
                        environment,
                        body["assessment_id"],
                        "assessment",
                    )
                    candidates = record["candidates"]
                else:
                    candidates = body.get("candidates", [])
                action = "plan.create" if method == "POST" and view is None else "plan.read"
                actor = await asyncio.to_thread(
                    self.authorize,
                    credential,
                    tokens,
                    tenant,
                    action,
                    application,
                    environment,
                    candidates,
                )
                if method == "GET":
                    if view or record is None:
                        raise Rejected("not_found", 404)
                    payload = record
                    if kind == "plans":
                        payload = {
                            **record,
                            "validity": await asyncio.to_thread(
                                self.planning.validity, actor, record, tokens
                            ),
                        }
                    status = 200
                elif view == "validity" and kind == "plans" and record:
                    if body:
                        raise Rejected("invalid_shape")
                    payload = await asyncio.to_thread(self.planning.validity, actor, record, tokens)
                    status = 200
                elif view == "diff" and kind == "plans" and record:
                    shape(body, {"other_plan_id"})
                    other = await asyncio.to_thread(
                        self.planning.get,
                        tenant,
                        application,
                        environment,
                        identifier(body["other_plan_id"]),
                        "plan",
                    )
                    other_actor = await asyncio.to_thread(
                        self.authorize,
                        credential,
                        tokens,
                        tenant,
                        action,
                        application,
                        environment,
                        other["candidates"],
                    )
                    if other_actor != actor:
                        raise Rejected("actor_mismatch", 403)
                    payload = {
                        "changes": diff(record["content"], other["content"]),
                        "approval_reusable": record["binding"]["digest"]
                        == other["binding"]["digest"],
                    }
                    status = 200
                elif identity or view:
                    raise Rejected("method_not_allowed", 405)
                else:
                    key = identifier(single(headers, b"idempotency-key"))
                    if kind == "assessments":
                        payload = await asyncio.to_thread(
                            self.planning.assessment, actor, key, body, tokens
                        )
                    else:
                        assert record is not None
                        integer(body["candidate"], 0, len(record["results"]) - 1)
                        payload = await asyncio.to_thread(
                            self.planning.plan, actor, key, body, record
                        )
                    status = 201
        except Rejected as e:
            status, payload = e.status, {"error": e.reason}
        except (ValueError, TypeError, KeyError, UnicodeError, TimeoutError):
            status, payload = 422, {"error": "invalid_request"}
        except Exception:
            status, payload = 503, {"error": "planning_unavailable"}
        encoded = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"cache-control", b"no-store, private"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"content-length", str(len(encoded)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": encoded})
