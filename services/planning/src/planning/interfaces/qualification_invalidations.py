"""Private authenticated Assurance invalidation inbox (no native write authority)."""

import asyncio
import hmac
import json
import os
from typing import Any

import psycopg
from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from planning.application.qualification_invalidations import QualificationInvalidations
from planning.domain.model import Rejected, decode
from planning.infrastructure.foundation import mounted_secret


class QualificationInvalidationApp:
    def __init__(self, inbox: QualificationInvalidations) -> None:
        self.inbox = inbox

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return
        status = 503
        reply: dict[str, Any] = {"error": "qualification_invalidation_unavailable"}
        try:
            if scope["method"] != "POST":
                raise Rejected("method_not_allowed", 405)
            headers = list(scope["headers"])
            if len(headers) > 40 or scope.get("query_string"):
                raise Rejected("request_bound", 413)
            # The read-only Assurance and outgoing Governance credentials cannot
            # stand in for a separately enrolled inbound invalidation principal.
            expected = mounted_secret("PLANNING_ASSURANCE_INVALIDATION_CREDENTIAL_FILE")
            for other in (
                "PLANNING_ASSURANCE_CREDENTIAL_FILE",
                "PLANNING_GOVERNANCE_CREDENTIAL_FILE",
                "PLANNING_CONSOLE_CREDENTIAL_FILE",
            ):
                if os.environ.get(other) and hmac.compare_digest(
                    expected, mounted_secret(other)
                ):
                    raise Rejected("invalidation_authority_not_independent", 503)
            authorization = [v for k, v in headers if k.lower() == b"authorization"]
            if (
                len(authorization) != 1
                or not hmac.compare_digest(
                    authorization[0], b"Bearer " + expected.encode("ascii")
                )
            ):
                raise Rejected("invalidation_unauthorized", 401)
            content_type = [v for k, v in headers if k.lower() == b"content-type"]
            if (
                len(content_type) != 1
                or content_type[0].split(b";")[0].strip() != b"application/json"
                or any(k.lower() == b"content-encoding" for k, _ in headers)
            ):
                raise Rejected("unsupported_content_type", 415)
            chunks = bytearray()
            async with asyncio.timeout(5):
                while True:
                    part = await receive()
                    if part["type"] != "http.request":
                        raise Rejected("interrupted_request", 400)
                    chunks.extend(part.get("body", b""))
                    if len(chunks) > 8192:
                        raise Rejected("request_bound", 413)
                    if not part.get("more_body", False):
                        break
            event = decode(bytes(chunks))
            reply = await asyncio.to_thread(self.inbox.accept, event)
            status = 200
        except Rejected as error:
            status, reply = error.status, {"error": error.reason}
        except (KeyError, ValueError, OSError, UnicodeError, psycopg.Error, TimeoutError):
            status, reply = 503, {"error": "qualification_invalidation_unavailable"}

        body = json.dumps(reply, sort_keys=True, separators=(",", ":")).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"cache-control", b"no-store, private"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
