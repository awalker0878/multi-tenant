"""Effect and read-only observer credentials have distinct audiences."""

import asyncio
import hmac
import json
from collections.abc import Callable
from typing import Any

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
        status = 503
        payload: dict[str, Any] = {"error": "simulation_unavailable"}
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
                # Reject an untyped transport before consulting simulated effects.
                import re
                required = (
                    {"tenant_id", "job_id", "operation_id", "attempt_id",
                     "plan_digest", "epoch", "simulation", "id", "step",
                     "worker_id", "expires_at", "campaign_id", "scope", "adapter"}
                    if scope["path"] == "/v1/effects" else
                    {"tenant_id", "job_id", "operation_id", "attempt_id",
                     "plan_digest", "epoch", "simulation"}
                )
                if set(body) != required or body["simulation"] is not True:
                    raise ValueError("simulation_request_contract_invalid")
                for field in ("tenant_id", "job_id", "operation_id", "attempt_id", "epoch"):
                    if not isinstance(body[field], str) or not re.fullmatch(
                        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                        body[field]
                    ):
                        raise ValueError("simulation_identity_invalid")
                if not isinstance(body["plan_digest"], str) or not re.fullmatch(
                    r"[0-9a-f]{64}", body["plan_digest"]
                ):
                    raise ValueError("simulation_plan_digest_invalid")
                if scope["path"] == "/v1/effects":
                    for field in ("id", "worker_id", "campaign_id"):
                        if not isinstance(body[field], str) or not re.fullmatch(
                            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                            body[field]
                        ):
                            raise ValueError("simulation_grant_identity_invalid")
                    if (body["adapter"] != "p06-simulator-v1"
                            or not isinstance(body["step"], str)
                            or not 1 <= len(body["step"]) <= 128
                            or type(body["expires_at"]) is not int
                            or body["expires_at"] < 0
                            or not isinstance(body["scope"], dict)
                            or not body["scope"]):
                        raise ValueError("simulation_grant_contract_invalid")
                # Retries are bound to the precise operation and request bytes;
                # no arbitrary caller-chosen replay key may authorize effects.
                import hashlib
                idempotency = [v.decode("ascii") for k, v in headers
                               if k.lower() == b"idempotency-key"]
                expected_key = hashlib.sha256(json.dumps(
                    {"path": scope["path"], "body": body}, sort_keys=True,
                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()
                if len(idempotency) != 1 or not hmac.compare_digest(idempotency[0], expected_key):
                    raise ValueError("idempotency_binding_invalid")
                action = {
                    "/v1/effects": self.simulation.execute,
                    "/v1/reconciliations": self.simulation.reconcile,
                    "/v1/observations": self.simulation.observe,
                }[scope["path"]]
                payload = await asyncio.to_thread(action, body)
                # The scope of a sealed readback is the exact authenticated
                # request. A structurally valid but foreign receipt is denied.
                if scope["path"] == "/v1/effects":
                    if (not isinstance(payload, dict)
                            or set(payload) != {"accepted", "duplicate"}
                            or payload["accepted"] is not True
                            or type(payload["duplicate"]) is not bool):
                        raise ValueError("simulation_effect_receipt_invalid")
                else:
                    if (not isinstance(payload, dict) or
                            set(payload) != {
                                "tenant_id", "job_id", "operation_id", "attempt_id",
                                "plan_digest", "epoch", "simulation", "sealed",
                                "effect_count", "observed_at", "outcome",
                            } or any(payload.get(k) != body.get(k) for k in (
                                "tenant_id", "job_id", "operation_id", "attempt_id",
                                "plan_digest", "epoch", "simulation"))
                            or payload["sealed"] is not True
                            or type(payload["effect_count"]) is not int
                            or payload["effect_count"] < 0
                            or type(payload["observed_at"]) is not int
                            or payload["observed_at"] < 0
                            or payload["outcome"] not in {
                                "confirmed_succeeded", "confirmed_failed",
                            }):
                        raise ValueError("simulation_observation_receipt_invalid")
                status = 200
        except (ValueError, KeyError, TypeError, TimeoutError):
            from uuid import uuid4
            status = 403
            payload = {
                "code": "simulation_denied", "message": "Simulation request denied",
                "correlation_id": str(uuid4()), "retryable": False,
            }
        except Exception:
            from uuid import uuid4
            status = 503
            payload = {
                "code": "simulation_unavailable", "message": "Simulation unavailable",
                "correlation_id": str(uuid4()), "retryable": True,
            }
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
