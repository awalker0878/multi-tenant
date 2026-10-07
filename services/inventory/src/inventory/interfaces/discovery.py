"Bounded HTTP boundary for delegated actors and independently authenticated workers."

import asyncio
import json
import re
from typing import Any
from urllib.parse import parse_qs

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from inventory.application.configuration import PortingConfiguration
from inventory.application.discovery import Discovery
from inventory.application.ports import Authority
from inventory.application.views import InventoryViews
from inventory.domain.discovery import Rejected

UUID = "[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
ROUTES = (
    (
        "POST",
        rf"/v1/tenants/({UUID})/sites/({UUID})/endpoints/({UUID})/configuration-pulls",
        "configuration_pull",
        "inventory.admin",
    ),
    (
        "GET",
        rf"/v1/tenants/({UUID})/sites/({UUID})/porting-configuration",
        "configuration",
        "inventory.admin",
    ),
    (
        "POST",
        rf"/v1/tenants/({UUID})/sites/({UUID})/porting-configuration",
        "configuration_save",
        "inventory.admin",
    ),
    (
        "POST",
        rf"/v1/tenants/({UUID})/sites/({UUID})/porting-configuration/confirmations",
        "configuration_confirm",
        "inventory.admin",
    ),
    ("GET", rf"/v1/tenants/({UUID})/sites", "sites", "inventory.read"),
    ("GET", rf"/v1/tenants/({UUID})/sites/({UUID})/policies", "policies", "inventory.admin"),
    ("GET", rf"/v1/tenants/({UUID})/sites/({UUID})/endpoints", "endpoints", "inventory.read"),
    ("GET", rf"/v1/tenants/({UUID})/sites/({UUID})/health", "health", "inventory.read"),
    (
        "GET",
        rf"/v1/tenants/({UUID})/sites/({UUID})/endpoints/({UUID})/discoveries",
        "discoveries",
        "inventory.read",
    ),
    (
        "GET",
        rf"/v1/tenants/({UUID})/sites/({UUID})/generations/({UUID})/resources",
        "resources",
        "inventory.read",
    ),
    ("POST", rf"/v1/tenants/({UUID})/sites/({UUID})/endpoints", "enroll", "inventory.admin"),
    (
        "POST",
        rf"/v1/tenants/({UUID})/sites/({UUID})/endpoints/({UUID})/discoveries",
        "discover",
        "inventory.discover",
    ),
    (
        "POST",
        rf"/v1/tenants/({UUID})/sites/({UUID})/endpoints/({UUID})/renewals",
        "renew",
        "inventory.admin",
    ),
    (
        "POST",
        rf"/v1/tenants/({UUID})/sites/({UUID})/endpoints/({UUID})/revocation",
        "revoke",
        "inventory.admin",
    ),
    (
        "POST",
        rf"/v1/tenants/({UUID})/sites/({UUID})/endpoints/({UUID})/matches",
        "match",
        "inventory.match",
    ),
)


def single(headers: list[tuple[bytes, bytes]], key: bytes, optional: bool = False) -> str:
    values = [v for k, v in headers if k.lower() == key]
    if not values and optional:
        return ""
    if len(values) != 1:
        raise Rejected("invalid_headers", 400)
    try:
        return values[0].decode("ascii")
    except UnicodeError:
        raise Rejected("invalid_headers", 400) from None


def decode(raw: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for k, v in items:
            if k in result:
                raise Rejected("duplicate_json_key")
            result[k] = v
        return result

    try:
        value = json.loads(
            raw,
            object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (ValueError, RecursionError, UnicodeError):
        raise Rejected("invalid_json") from None


class InventoryApp:
    def __init__(self, discovery: Discovery, authority: Authority) -> None:
        self.discovery = discovery
        self.authority = authority
        self.views = InventoryViews(discovery)
        self.configuration = PortingConfiguration(discovery)

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return
        status = 200
        headers = list(scope["headers"])
        try:
            if len(scope["query_string"]) > 200 or len(headers) > 40:
                raise Rejected("request_bound", 413)
            header = single(headers, b"authorization")
            if not re.fullmatch(r"Bearer [A-Za-z0-9_-]{32,4096}", header):
                raise Rejected("invalid_workload", 401)
            credential = header[7:]
            worker_route = scope["path"] in {
                "/internal/collections/claim",
                "/internal/collections/pages",
            }
            selected = next(
                (
                    (m, op, action)
                    for method, pattern, op, action in ROUTES
                    if scope["method"] == method and (m := re.fullmatch(pattern, scope["path"]))
                ),
                None,
            )
            if worker_route:
                if scope["method"] != "POST":
                    raise Rejected("method_not_allowed", 405)
                worker = await asyncio.to_thread(self.authority.worker, credential)
                actor = None
            elif selected:
                matched, operation, action = selected
                values = matched.groups()
                actor = await asyncio.to_thread(
                    self.authority.actor,
                    credential,
                    single(headers, b"x-actor-delegation"),
                    values[0],
                    action,
                    values[1] if len(values) > 1 else None,
                )
            else:
                raise Rejected("not_found", 404)
            body: dict[str, Any] = {}
            if scope["method"] == "POST":
                if single(headers, b"content-type").split(";")[0] != "application/json" or single(
                    headers, b"content-encoding", True
                ):
                    raise Rejected("unsupported_content_type", 415)
                chunks = bytearray()
                async with asyncio.timeout(5):
                    while True:
                        event = await receive()
                        if event["type"] != "http.request":
                            raise Rejected("request_interrupted", 400)
                        chunks.extend(event["body"])
                        if len(chunks) > 262144:
                            raise Rejected("request_bound", 413)
                        if not event.get("more_body", False):
                            break
                body = decode(bytes(chunks))
            if worker_route:
                if scope["query_string"]:
                    raise Rejected("invalid_query")
                if scope["path"].endswith("/claim"):
                    if body:
                        raise Rejected("invalid_shape")
                    payload = await asyncio.to_thread(self.discovery.claim, worker)
                else:
                    payload = await asyncio.to_thread(self.discovery.submit, worker, body)
            else:
                assert selected is not None and actor is not None
                params = parse_qs(scope["query_string"].decode("ascii"), strict_parsing=True)
                if params.keys() - {"cursor"} or any(len(v) != 1 for v in params.values()):
                    raise Rejected("invalid_query")
                target = values[2] if len(values) > 2 else None
                if scope["method"] == "GET":
                    if operation == "configuration":
                        if params:
                            raise Rejected("invalid_query")
                        payload = await asyncio.to_thread(self.configuration.read, actor)
                    else:
                        payload = await asyncio.to_thread(
                            self.views.read,
                            actor,
                            operation,
                            target,
                            params.get("cursor", [None])[0],
                        )
                else:
                    if params:
                        raise Rejected("invalid_query")
                    expected = single(headers, b"if-match", True)
                    if expected and not re.fullmatch(r'"[1-9][0-9]{0,8}"', expected):
                        raise Rejected("invalid_revision")
                    payload = await asyncio.to_thread(
                        self.configuration.command
                        if operation in {"configuration_save", "configuration_confirm"}
                        else self.discovery.command,
                        actor,
                        operation,
                        body,
                        single(headers, b"idempotency-key"),
                        target,
                        int(expected[1:-1]) if expected else None,
                    )
                    status = 202 if operation in {"discover", "configuration_pull"} else 201
        except Rejected as error:
            status, payload = error.status, {"error": error.reason}
        except (TimeoutError, UnicodeError, ValueError):
            status, payload = 400, {"error": "invalid_request"}
        except Exception:
            # Driver/configuration/transport details and credentials never enter the wire/log.
            status, payload = 503, {"error": "inventory_unavailable"}
        encoded = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"cache-control", b"no-store, private"),
                    (b"content-length", str(len(encoded)).encode()),
                    (b"x-content-type-options", b"nosniff"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": encoded})
