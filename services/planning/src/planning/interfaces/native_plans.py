"""Authenticated native proposal creation; submitted values select owned records only."""

import asyncio
import json
import re

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from planning.application.native_plans import NativePlans
from planning.application.ports import Authority
from planning.domain.model import Rejected, decode, identifier, shape
from planning.interfaces.planning import UUID, single


class NativePlansApp:
    def __init__(self, authority: Authority, plans: NativePlans) -> None:
        self.authority, self.plans = authority, plans

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return
        try:
            route = re.fullmatch(
                rf"/v1/tenants/({UUID})/applications/({UUID})/environments/({UUID})/native-plans",
                scope["path"],
            )
            if route is None or scope["method"] != "POST" or scope["query_string"]:
                raise Rejected("not_found", 404)
            headers = list(scope["headers"])
            auth = single(headers, b"authorization")
            if len(headers) > 40 or not re.fullmatch(r"Bearer [A-Za-z0-9_-]{32,4096}", auth):
                raise Rejected("invalid_workload", 401)
            if single(headers, b"content-type").split(";")[0] != "application/json" or single(
                headers, b"content-encoding", True
            ):
                raise Rejected("unsupported_content_type", 415)
            await asyncio.to_thread(self.authority.caller, auth[7:])
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
            body = shape(decode(bytes(raw)), {"site_id", "base_plan_id", "recipe_id"})
            site = identifier(body["site_id"])
            delegation = single(headers, b"x-actor-delegation")
            actor = await asyncio.to_thread(
                self.authority.actor,
                auth[7:],
                delegation,
                route[1],
                "plan.create",
                route[2],
                route[3],
                site,
            )
            payload = await asyncio.to_thread(
                self.plans.create,
                actor,
                body,
                identifier(single(headers, b"idempotency-key")),
                delegation,
            )
            status = 201
        except Rejected as error:
            status, payload = error.status, {"error": error.reason}
        except (KeyError, TypeError, ValueError, TimeoutError):
            status, payload = 422, {"error": "invalid_native_proposal"}
        except Exception:
            status, payload = 503, {"error": "native_proposal_unavailable"}
        data = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode()
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
        await send({"type": "http.response.body", "body": data})
