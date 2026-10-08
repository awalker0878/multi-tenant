"""Bounded internal publication, authenticated independently of campaign controls."""

import asyncio
import json
import re
from collections.abc import Callable
from typing import Any

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from lifecycle.application.campaigns import Campaigns
from lifecycle.domain.execution import Rejected, decode, identity
from lifecycle.interfaces.execution import UUID, single


class CampaignObservationApp:
    def __init__(
        self, campaigns: Campaigns, authorize: Callable[[str, str, str, dict[str, Any]], str]
    ) -> None:
        self.campaigns, self.authorize = campaigns, authorize

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return
        payload: dict[str, Any]
        try:
            route = re.fullmatch(
                rf"/internal/tenants/({UUID})/migration-observations/(performance|capacity|release)",
                scope["path"],
            )
            if route is None or scope["method"] != "POST" or scope["query_string"]:
                raise Rejected("not_found", 404)
            headers = list(scope["headers"])
            if len(headers) > 40 or any(k.lower() == b"content-encoding" for k, _ in headers):
                raise Rejected("request_bound", 413)
            token = single(headers, b"authorization")
            if not re.fullmatch(r"Bearer [A-Za-z0-9_-]{32,4096}", token):
                raise Rejected("observation_caller_denied", 401)
            if single(headers, b"content-type").split(";")[0] != "application/json":
                raise Rejected("unsupported_content_type", 415)
            raw = bytearray()
            async with asyncio.timeout(5):
                while True:
                    event = await receive()
                    if event["type"] != "http.request":
                        raise Rejected("interrupted", 400)
                    raw.extend(event["body"])
                    if len(raw) > 16384:
                        raise Rejected("request_bound", 413)
                    if not event.get("more_body", False):
                        break
            value = decode(bytes(raw))
            tenant, kind = route.groups()
            observer = await asyncio.to_thread(self.authorize, token[7:], tenant, kind, value)
            if kind == "release":
                await asyncio.to_thread(self.campaigns.release, tenant, observer, value)
            else:
                key = identity(single(headers, b"idempotency-key"))
                publish = (
                    self.campaigns.sample if kind == "performance" else self.campaigns.capacity
                )
                await asyncio.to_thread(publish, tenant, observer, key, value)
            payload, status = {"accepted": True, "native_write_authorized": False}, 202
        except Rejected as error:
            payload, status = {"error": error.reason}, error.status
        except (TypeError, ValueError, KeyError, TimeoutError):
            payload, status = {"error": "invalid_observation"}, 422
        except Exception:
            payload, status = {"error": "observations_unavailable"}, 503
        response = json.dumps(payload, separators=(",", ":")).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"cache-control", b"no-store"),
                    (b"content-length", str(len(response)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": response})
