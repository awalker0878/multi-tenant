"""Bounded internal effect route, separate from simulation and read-only inspection."""

import asyncio
import json
import re
from collections.abc import Callable
from typing import Any

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from lifecycle_worker.application.native import NativeHeld, decode, identity
from lifecycle_worker.application.native_effect import NativeSavedPlanEffect


class NativeEffectApp:
    def __init__(
        self, effects: NativeSavedPlanEffect, caller: Callable[[str], tuple[str, str]]
    ) -> None:
        self.effects, self.caller = effects, caller

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return
        payload: dict[str, Any]
        status, payload = 503, {"error": "native_effect_unavailable"}
        try:
            if (
                scope["method"] != "POST"
                or scope["path"] != "/internal/native-effects"
                or scope["query_string"]
            ):
                status = 404
                raise NativeHeld("native_route_denied")
            headers = list(scope["headers"])
            if len(headers) > 24 or any(k.lower() == b"content-encoding" for k, _ in headers):
                status = 413
                raise NativeHeld("native_request_bound")
            auth = [v.decode("ascii") for k, v in headers if k.lower() == b"authorization"]
            if len(auth) != 1 or not re.fullmatch(r"Bearer [A-Za-z0-9_-]{32,4096}", auth[0]):
                status = 401
                raise NativeHeld("invalid_native_caller")
            status = 403
            tenant, worker = await asyncio.to_thread(self.caller, auth[0][7:])
            identity(tenant)
            identity(worker)
            content = [v for k, v in headers if k.lower() == b"content-type"]
            status = 415
            if len(content) != 1 or content[0].split(b";")[0] != b"application/json":
                raise NativeHeld("native_content_type_denied")
            status = 422
            raw = bytearray()
            async with asyncio.timeout(5):
                while True:
                    message = await receive()
                    if message["type"] != "http.request":
                        raise NativeHeld("native_request_interrupted")
                    raw.extend(message["body"])
                    if len(raw) > 16384:
                        status = 413
                        raise NativeHeld("native_request_bound")
                    if not message.get("more_body", False):
                        break
            body = decode(bytes(raw), 16384)
            if set(body) != {"grant"} or not isinstance(body["grant"], dict):
                raise NativeHeld("invalid_native_request")
            status = 423
            payload = await asyncio.to_thread(self.effects.execute, tenant, worker, body["grant"])
            status = 200
        except NativeHeld:
            payload = {"error": "native_effect_held"}
        except (KeyError, TypeError, ValueError, UnicodeError, TimeoutError):
            status, payload = 422, {"error": "invalid_native_request"}
        except Exception:
            status, payload = 503, {"error": "native_effect_unavailable"}
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
