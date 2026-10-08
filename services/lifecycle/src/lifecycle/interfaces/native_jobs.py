"""Native job admission from approved immutable references, never caller-supplied plans."""

import asyncio
import json
import re
from collections.abc import Callable
from typing import Any

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from lifecycle.application.execution_ports import RequestAuthority
from lifecycle.application.native_workflow import NativeWorkflow
from lifecycle.domain.execution import Rejected, decode, identity, shape
from lifecycle.domain.native_workflow import checksum, integer
from lifecycle.interfaces.execution import UUID, single


class NativeJobsApp:
    def __init__(
        self,
        workflow: NativeWorkflow,
        authority: RequestAuthority,
        resolve: Callable[[str, dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.workflow, self.authority, self.resolve = workflow, authority, resolve

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return
        payload: dict[str, Any]
        try:
            route = re.fullmatch(
                rf"/v1/tenants/({UUID})/native-jobs(?:/({UUID}))?(?:/(stop))?", scope["path"]
            )
            if route is None or scope["query_string"]:
                raise Rejected("not_found", 404)
            tenant, job, command = route.groups()
            if not (
                (job is None and scope["method"] == "POST")
                or (job and command is None and scope["method"] == "GET")
                or (job and command == "stop" and scope["method"] == "POST")
            ):
                raise Rejected("not_found", 404)
            headers = list(scope["headers"])
            auth = single(headers, b"authorization")
            if len(headers) > 40 or not re.fullmatch(r"Bearer [A-Za-z0-9_-]{32,4096}", auth):
                raise Rejected("invalid_workload", 401)
            if any(k.lower() == b"content-encoding" for k, _ in headers):
                raise Rejected("unsupported_content_type", 415)
            await asyncio.to_thread(self.authority.caller, auth[7:], "console")
            body: dict[str, Any] = {}
            if scope["method"] == "POST":
                if single(headers, b"content-type").split(";")[0] != "application/json":
                    raise Rejected("unsupported_content_type", 415)
                raw = bytearray()
                async with asyncio.timeout(5):
                    while True:
                        event = await receive()
                        if event["type"] != "http.request":
                            raise Rejected("interrupted", 400)
                        raw.extend(event["body"])
                        if len(raw) > 4096:
                            raise Rejected("request_bound", 413)
                        if not event.get("more_body", False):
                            break
                body = decode(bytes(raw))
            if job:
                existing = await asyncio.to_thread(self.workflow.read, tenant, job)
                selected_scope = existing["scope"]
                action = "operation.control" if command else "operation.read"
            else:
                shape(body, {"plan_id", "plan_revision", "plan_digest", "approval_id"})
                identity(body["plan_id"])
                identity(body["approval_id"])
                integer(body["plan_revision"], 1)
                checksum(body["plan_digest"])
                plan = await asyncio.to_thread(self.resolve, tenant, body)
                if plan["purpose"] not in {"provision", "retire"}:
                    raise Rejected("migration_campaign_required", 423)
                selected_scope = plan["scope"]
                action = "operation.admit"
            actor = await asyncio.to_thread(
                self.authority.actor,
                single(headers, b"x-actor-delegation"),
                tenant,
                action,
                {k: selected_scope[k] for k in ("site_id", "environment", "resource_id")},
            )
            if job:
                if command:
                    shape(body, {"expected_revision"})
                    await asyncio.to_thread(
                        self.workflow.stop, tenant, job, integer(body["expected_revision"], 1)
                    )
                    existing = await asyncio.to_thread(self.workflow.read, tenant, job)
                payload, status = existing, 202 if command else 200
            else:
                if actor != plan["actor_id"]:
                    raise Rejected("native_executor_scope_denied", 403)
                admitted = await asyncio.to_thread(
                    self.workflow.admit, plan, identity(single(headers, b"idempotency-key"))
                )
                payload, status = await asyncio.to_thread(self.workflow.read, tenant, admitted), 202
        except Rejected as error:
            status, payload = error.status, {"error": error.reason}
        except (KeyError, TypeError, ValueError, TimeoutError):
            status, payload = 422, {"error": "invalid_native_job_request"}
        except Exception:
            status, payload = 503, {"error": "native_jobs_unavailable"}
        raw_response = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode()
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
        await send({"type": "http.response.body", "body": raw_response})
