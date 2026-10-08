"""Internal native grant checks; the verified workload identity never comes from JSON."""

import asyncio
import json
import re
from collections.abc import Callable
from typing import Any

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from lifecycle.application.native_workflow import NativeWorkflow
from lifecycle.domain.execution import Rejected, decode, identity, shape
from lifecycle.interfaces.execution import single


class NativeBoundaryApp:
    def __init__(self, workflow: NativeWorkflow, caller: Callable[[str], tuple[str, str]]) -> None:
        self.workflow, self.caller = workflow, caller

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return
        payload: dict[str, Any]
        try:
            if (
                scope["method"] != "POST"
                or scope["path"] != "/internal/native-grants/checks"
                or scope["query_string"]
            ):
                raise Rejected("not_found", 404)
            headers = list(scope["headers"])
            if len(headers) > 24 or any(k.lower() == b"content-encoding" for k, _ in headers):
                raise Rejected("native_request_bound", 413)
            auth = single(headers, b"authorization")
            if not re.fullmatch(r"Bearer [A-Za-z0-9_-]{32,4096}", auth):
                raise Rejected("invalid_workload", 401)
            tenant, worker = await asyncio.to_thread(self.caller, auth[7:])
            identity(tenant)
            identity(worker)
            if single(headers, b"content-type").split(";")[0] != "application/json":
                raise Rejected("unsupported_content_type", 415)
            raw = bytearray()
            async with asyncio.timeout(5):
                while True:
                    message = await receive()
                    if message["type"] != "http.request":
                        raise Rejected("interrupted", 400)
                    raw.extend(message["body"])
                    if len(raw) > 16384:
                        raise Rejected("native_request_bound", 413)
                    if not message.get("more_body", False):
                        break
            body = decode(bytes(raw))
            shape(body, {"grant", "boundary"})
            if not isinstance(body["grant"], dict) or not isinstance(body["boundary"], str):
                raise Rejected("invalid_native_request", 422)
            payload = await asyncio.to_thread(
                self.workflow.boundary,
                tenant,
                body["grant"],
                worker,
                body["boundary"],
            )
            status = 200
        except Rejected as error:
            payload, status = {"error": error.reason}, error.status
        except (KeyError, ValueError, TypeError, UnicodeError, TimeoutError):
            payload, status = {"error": "invalid_native_request"}, 422
        except Exception:
            payload, status = {"error": "native_authority_unavailable"}, 503
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
