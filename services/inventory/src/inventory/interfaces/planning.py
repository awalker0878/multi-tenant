"""Read-only Planning source route with its own caller credential and current actor check."""

import asyncio
import json
import re
from collections.abc import Callable

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from inventory.application.discovery import Discovery
from inventory.application.planning import planning_input
from inventory.domain.discovery import Rejected
from inventory.interfaces.discovery import UUID, single


class PlanningInputApp:
    def __init__(
        self, discovery: Discovery, authority: Callable[[str, str, str, str, str, str, str], None]
    ) -> None:
        self.discovery, self.authority = discovery, authority

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return
        try:
            route = re.fullmatch(
                rf"/v1/tenants/({UUID})/planning-inputs/({UUID})/({UUID})/({UUID})/({UUID})/({UUID})",
                scope["path"],
            )
            if not route or scope["method"] != "GET" or scope["query_string"]:
                raise Rejected("not_found", 404)
            tenant, application, environment, site, endpoint, generation = route.groups()
            headers = list(scope["headers"])
            auth = single(headers, b"authorization")
            if not re.fullmatch(r"Bearer [A-Za-z0-9_-]{32,4096}", auth):
                raise Rejected("invalid_workload", 401)
            await asyncio.to_thread(
                self.authority,
                auth[7:],
                single(headers, b"x-actor-delegation"),
                tenant,
                single(headers, b"x-planning-action"),
                application,
                environment,
                site,
            )
            payload = await asyncio.to_thread(
                planning_input, self.discovery, tenant, site, endpoint, generation
            )
            status = 200
        except Rejected as e:
            status, payload = e.status, {"error": e.reason}
        except Exception:
            status, payload = 503, {"error": "inventory_unavailable"}
        raw = json.dumps(payload, separators=(",", ":")).encode()
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
