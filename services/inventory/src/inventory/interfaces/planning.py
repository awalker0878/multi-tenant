"""Read-only Planning source route with its own caller credential and current actor check."""

import asyncio
import json
import re
from collections.abc import Callable

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from inventory.application.discovery import Discovery
from inventory.application.planning import planning_input
from inventory.application.workload import WorkloadProfiles
from inventory.domain.discovery import Rejected
from inventory.interfaces.discovery import UUID, single


class PlanningInputApp:
    def __init__(
        self,
        discovery: Discovery,
        authority: Callable[[str, str, str, str, str, str, str], None],
        native_authority: Callable[[str, str, str, str, str, int, str], None] | None = None,
    ) -> None:
        self.discovery, self.authority = discovery, authority
        self.native_authority = native_authority

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
            migration = re.fullmatch(
                rf"/(?:v1|internal)/tenants/({UUID})/migration-inputs/({UUID})/({UUID})/({UUID})/([1-9][0-9]{{0,8}})/([0-9a-f]{{64}})",
                scope["path"],
            )
            if not (route or migration) or scope["method"] != "GET" or scope["query_string"]:
                raise Rejected("not_found", 404)
            selected = migration or route
            assert selected is not None
            tenant, application, environment, site, endpoint, generation = selected.groups()
            headers = list(scope["headers"])
            if len(headers) > 40 or any(k.lower() == b"content-encoding" for k, _ in headers):
                raise Rejected("request_bound", 413)
            auth = single(headers, b"authorization")
            if not re.fullmatch(r"Bearer [A-Za-z0-9_-]{32,4096}", auth):
                raise Rejected("invalid_workload", 401)
            if scope["path"].startswith("/internal/"):
                if self.native_authority is None:
                    raise Rejected("native_reader_not_commissioned", 423)
                await asyncio.to_thread(
                    self.native_authority,
                    auth[7:],
                    tenant,
                    application,
                    environment,
                    site,
                    int(endpoint),
                    generation,
                )
            else:
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
            if migration:
                payload = await asyncio.to_thread(
                    WorkloadProfiles(self.discovery).planning,
                    tenant,
                    site,
                    int(endpoint),
                    generation,
                )
            else:
                payload = await asyncio.to_thread(
                    planning_input, self.discovery, tenant, site, endpoint, generation
                )
            if scope["path"].startswith("/internal/"):
                assert self.native_authority is not None
                await asyncio.to_thread(
                    self.native_authority,
                    auth[7:],
                    tenant,
                    application,
                    environment,
                    site,
                    int(endpoint),
                    generation,
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
                    (b"content-length", str(len(raw)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": raw})
