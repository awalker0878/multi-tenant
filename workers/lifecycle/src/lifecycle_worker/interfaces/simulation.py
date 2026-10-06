"""Effect and read-only observer credentials have distinct audiences."""

import asyncio
import hmac
import json
from collections.abc import Callable

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from lifecycle_worker.application.simulation import Simulation


class SimulationApp:
    def __init__(self, simulation: Simulation, credential: Callable[[str], str]) -> None:
        self.simulation, self.credential = simulation, credential

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return
        status, payload = 503, {"error": "simulation_unavailable"}
        try:
            if scope["path"] == "/health/live" and scope["method"] == "GET":
                status, payload = 200, {"status": "alive"}
            else:
                if scope["method"] != "POST" or scope["path"] not in {
                    "/v1/effects",
                    "/v1/reconciliations",
                    "/v1/observations",
                }:
                    raise ValueError("unknown_route")
                headers = list(scope["headers"])
                if scope["query_string"] or len(headers) > 40:
                    raise ValueError("request_bound")
                values = [v.decode("ascii") for k, v in headers if k == b"authorization"]
                producer = self.credential("LIFECYCLE_SIMULATOR_CREDENTIAL_FILE")
                observer = self.credential("ASSURANCE_SIMULATOR_CREDENTIAL_FILE")
                callback = self.credential("SIMULATOR_LIFECYCLE_CREDENTIAL_FILE")
                if len({producer, observer, callback}) != 3:
                    raise ValueError("credential_reuse")
                expected = observer if scope["path"] == "/v1/observations" else producer
                if len(values) != 1 or not hmac.compare_digest(values[0], "Bearer " + expected):
                    raise ValueError("audience_denied")
                content = [v for k, v in headers if k == b"content-type"]
                if (
                    len(content) != 1
                    or content[0].split(b";")[0] != b"application/json"
                    or any(k == b"content-encoding" for k, _ in headers)
                ):
                    raise ValueError("invalid_content_type")
                raw = bytearray()
                async with asyncio.timeout(5):
                    while True:
                        message = await receive()
                        if message["type"] != "http.request":
                            raise ValueError("interrupted")
                        raw.extend(message["body"])
                        if len(raw) > 16384:
                            raise ValueError("request_bound")
                        if not message.get("more_body", False):
                            break

                def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
                    result: dict[str, object] = {}
                    for key, value in items:
                        if key in result:
                            raise ValueError("duplicate_key")
                        result[key] = value
                    return result

                body = json.loads(raw, object_pairs_hook=pairs)
                if not isinstance(body, dict):
                    raise ValueError("invalid_shape")
                action = {
                    "/v1/effects": self.simulation.execute,
                    "/v1/reconciliations": self.simulation.reconcile,
                    "/v1/observations": self.simulation.observe,
                }[scope["path"]]
                payload = await asyncio.to_thread(action, body)
                status = 200
        except (ValueError, KeyError, TypeError, TimeoutError):
            status, payload = 403, {"error": "simulation_denied"}
        except Exception:
            pass
        encoded = json.dumps(payload, separators=(",", ":")).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"cache-control", b"no-store"),
                    (b"content-length", str(len(encoded)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": encoded})
