"""Bounded no-store API. The Console cannot supply approval decisions or owner snapshots."""

import asyncio
import json
import re
from typing import Any

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from lifecycle.application.execution import Execution
from lifecycle.application.execution_ports import RequestAuthority
from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected, decode, identity, shape

UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"


def single(headers: list[tuple[bytes, bytes]], key: bytes) -> str:
    values = [v for k, v in headers if k.lower() == key]
    if len(values) != 1:
        raise Rejected("invalid_headers", 400)
    return values[0].decode("ascii")


class ExecutionApp:
    def __init__(self, execution: Execution, authority: RequestAuthority) -> None:
        self.execution, self.authority = execution, authority

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return
        payload: dict[str, Any]
        try:
            headers = list(scope["headers"])
            if len(headers) > 40 or scope["query_string"]:
                raise Rejected("request_bound", 413)
            token = single(headers, b"authorization")
            if not re.fullmatch(r"Bearer [A-Za-z0-9_-]{32,4096}", token):
                raise Rejected("invalid_workload", 401)
            body: dict[str, Any] = {}
            if scope["method"] == "POST":
                if single(headers, b"content-type").split(";")[0] != "application/json" or any(
                    k == b"content-encoding" for k, _ in headers
                ):
                    raise Rejected("unsupported_content_type", 415)
                raw = bytearray()
                async with asyncio.timeout(5):
                    while True:
                        message = await receive()
                        if message["type"] != "http.request":
                            raise Rejected("interrupted", 400)
                        raw.extend(message["body"])
                        if len(raw) > 262144:
                            raise Rejected("request_bound", 413)
                        if not message.get("more_body", False):
                            break
                body = decode(bytes(raw))
            if (
                scope["path"] == "/internal/simulation-grants/redemptions"
                and scope["method"] == "POST"
            ):
                await asyncio.to_thread(self.authority.caller, token[7:], "simulator")
                payload = await asyncio.to_thread(self.execution.redeem, body, "sim-worker")
                status = 200
            else:
                internal = re.fullmatch(
                    rf"/internal/evidence-bindings/({UUID})/({UUID})", scope["path"]
                )
                if internal and scope["method"] == "GET":
                    await asyncio.to_thread(self.authority.caller, token[7:], "assurance")
                    job = await asyncio.to_thread(self.execution.read, internal[1], internal[2])
                    observations = [o["observation"] for o in job["operations"]]
                    if not all(o["outcome"] == "confirmed_succeeded" for o in job["operations"]):
                        raise Rejected("evidence_not_ready")
                    payload = {
                        "tenant_id": internal[1],
                        "job_id": internal[2],
                        "plan_digest": job["plan_digest"],
                        "digest": digest(observations),
                        "source_revision": job["source_revision"],
                        "scope": job["scope"],
                        "observations": observations,
                        "evidence_level": "E2",
                        "producer_actor_id": job["actor_id"],
                        "requested_by": job["requested_by"],
                    }
                    status = 200
                else:
                    await asyncio.to_thread(self.authority.caller, token[7:], "console")
                    route = re.fullmatch(
                        rf"/v1/tenants/({UUID})/jobs(?:/({UUID}))?(?:/(commands))?", scope["path"]
                    )
                    if not route:
                        raise Rejected("not_found", 404)
                    tenant, job_id, tail = route.groups()
                    if job_id:
                        public = await asyncio.to_thread(self.execution.read, tenant, job_id)
                        action = (
                            "operation.read" if scope["method"] == "GET" else "operation.control"
                        )
                        requested_scope = public["scope"]
                    else:
                        if scope["method"] != "POST":
                            raise Rejected("method_not_allowed", 405)
                        shape(
                            body,
                            {
                                "plan_id",
                                "plan_revision",
                                "plan_digest",
                                "approval_id",
                                "campaign_id",
                            },
                        )
                        if (
                            type(body["plan_revision"]) is not int
                            or not 1 <= body["plan_revision"] <= 999999999
                        ):
                            raise Rejected("invalid_revision", 422)
                        plan = await asyncio.to_thread(
                            self.execution.prior_admission,
                            tenant,
                            identity(single(headers, b"idempotency-key")),
                        )
                        if plan is None:
                            plan = await asyncio.to_thread(
                                self.authority.plan,
                                tenant,
                                identity(body["plan_id"]),
                                body["plan_revision"],
                            )
                        elif (
                            plan["binding"]["plan_id"] != body["plan_id"]
                            or plan["binding"]["revision"] != body["plan_revision"]
                        ):
                            raise Rejected("command_key_conflict")
                        if (
                            plan.get("invalidated") is not False
                            or plan["binding"]["digest"] != body["plan_digest"]
                        ):
                            raise Rejected("plan_changed")
                        requested_scope = plan["content"]["scope"]
                        action = "operation.admit"
                    actor = await asyncio.to_thread(
                        self.authority.actor,
                        single(headers, b"x-actor-delegation"),
                        tenant,
                        action,
                        requested_scope,
                    )
                    if scope["method"] == "GET" and job_id and not tail:
                        payload, status = public, 200
                    elif scope["method"] == "POST" and job_id and tail:
                        shape(body, {"action", "expected_revision"})
                        payload = await asyncio.to_thread(
                            self.execution.command,
                            tenant,
                            job_id,
                            actor,
                            identity(single(headers, b"idempotency-key")),
                            body["action"],
                            body["expected_revision"],
                        )
                        status = 202
                    elif scope["method"] == "POST" and not job_id:
                        if plan is None:
                            raise Rejected("plan_unavailable", 503)
                        payload = await asyncio.to_thread(
                            self.execution.admit,
                            tenant,
                            actor,
                            identity(single(headers, b"idempotency-key")),
                            plan["content"],
                            plan["binding"],
                            identity(body["approval_id"]),
                            identity(body["campaign_id"]),
                        )
                        status = 202
                    else:
                        raise Rejected("method_not_allowed", 405)
        except Rejected as e:
            payload, status = {"error": e.reason}, e.status
        except (ValueError, TypeError, KeyError, UnicodeError, TimeoutError):
            payload, status = {"error": "invalid_request"}, 422
        except Exception as error:
            print("lifecycle_request_failed:" + type(error).__name__, flush=True)
            payload, status = {"error": "lifecycle_unavailable"}, 503
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
