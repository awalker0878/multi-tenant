"""Service-only resource owner commands and readback; receipts grant no native effects."""

import asyncio
import json
import re
from collections.abc import Callable
from typing import Any

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from lifecycle.application.placement_reservations import PlacementReservations
from lifecycle.application.reservations import Held


class PlacementReservationApp:
    def __init__(self, service: PlacementReservations, authorize: Callable[[str], None]) -> None:
        self.service, self.authorize = service, authorize

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        payload: dict[str, Any]
        try:
            route = re.fullmatch(
                r"/internal/tenants/([0-9a-f-]{36})/placement-reservations/"
                r"(reserve|checks|confirm|renew|release)",
                scope["path"],
            )
            if route is None or scope["method"] != "POST" or scope["query_string"]:
                raise Held("placement_route_invalid")
            tenant, operation = route.groups()
            incoming = [v.decode() for k, v in scope["headers"] if k.lower() == b"authorization"]
            if len(incoming) != 1 or not incoming[0].startswith("Bearer "):
                raise Held("placement_caller_denied")
            await asyncio.to_thread(self.authorize, incoming[0][7:])
            raw = bytearray()
            while True:
                message = await receive()
                if message["type"] != "http.request":
                    raise Held("placement_request_disconnected")
                raw.extend(message.get("body", b""))
                if len(raw) > 262144:
                    raise Held("placement_request_bound")
                if not message.get("more_body"):
                    break
            body = json.loads(raw)
            if operation == "reserve":
                payload = await asyncio.to_thread(self.service.reserve, tenant, body)
            elif operation == "checks":
                payload = await asyncio.to_thread(self.service.check, tenant, body["plan_digest"])
            else:
                payload = await asyncio.to_thread(
                    self.service.transition, tenant, body["plan_digest"], operation
                )
            status = 200
        except Held as error:
            status, payload = 423, {"error": str(error)}
        except Exception:
            status, payload = 503, {"error": "placement_owner_unavailable"}
        raw_response = json.dumps(payload, separators=(",", ":")).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"cache-control", b"no-store, private"),
                    (b"content-length", str(len(raw_response)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": raw_response})
