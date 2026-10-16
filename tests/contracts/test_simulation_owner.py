"""Execute the real simulator ASGI HTTP boundary and Lifecycle installed consumer.

This tests producer, consumer and route behavior only; workload bearer is not
tenant-scoped, so these tests must never claim tenant-isolation assurance.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers/lifecycle/src"))
from lifecycle_worker.interfaces.simulation import SimulationApp
from lifecycle.domain.execution import Rejected
from lifecycle.infrastructure import execution_owners as client

TENANT = "10000000-0000-4000-8000-000000000001"
FOREIGN = "10000000-0000-4000-8000-000000000002"
SHA = "a" * 64
BINDING = {
    "tenant_id": TENANT, "job_id": FOREIGN,
    "operation_id": TENANT, "attempt_id": FOREIGN, "plan_digest": SHA,
    "epoch": TENANT, "simulation": True,
}
GRANT = {
    **BINDING, "id": FOREIGN, "step": "capture",
    "worker_id": FOREIGN, "expires_at": 2000000000,
    "campaign_id": TENANT, "scope": {"site_id": TENANT},
    "adapter": "p06-simulator-v1",
}
OBSERVATION = {
    **BINDING, "sealed": True, "effect_count": 1,
    "observed_at": 2000000000, "outcome": "confirmed_succeeded",
}
API = json.loads((ROOT / "contracts/openapi/worker-simulation-v1.json").read_text())


class Effects:
    def execute(self, grant):
        if grant != GRANT:
            raise ValueError("unknown_simulation_grant")
        return {"accepted": True, "duplicate": False}

    def reconcile(self, data):
        return {**OBSERVATION, **{k: data[k] for k in BINDING}}

    def observe(self, data):
        return self.reconcile(data)


def request_worker(path, body, *, bearer="effect-only", service=None, supplied_headers=None):
    service = service or Effects()
    credentials = {
        "LIFECYCLE_SIMULATOR_CREDENTIAL_FILE": "effect-only",
        "ASSURANCE_SIMULATOR_CREDENTIAL_FILE": "observation-only",
        "SIMULATOR_LIFECYCLE_CREDENTIAL_FILE": "callback-only",
    }
    key = hashlib.sha256(json.dumps(
        {"path": path, "body": body}, sort_keys=True,
        separators=(",", ":"), allow_nan=False
    ).encode()).hexdigest()
    emitted = []

    async def receive():
        return {"type": "http.request", "body": json.dumps(body).encode(),
                "more_body": False}

    async def send(message):
        emitted.append(message)

    headers = supplied_headers or {'Authorization': 'Bearer ' + bearer, 'Idempotency-Key': key}
    scope = {
        "type": "http", "method": "POST", "path": path, "query_string": b"",
        "headers": [(b"authorization", headers['Authorization'].encode()),
                    (b"content-type", b"application/json"),
                    (b"idempotency-key", headers['Idempotency-Key'].encode())],
    }
    asyncio.run(SimulationApp(service, credentials.__getitem__)(
        scope, receive, send))
    return emitted[0]["status"], json.loads(emitted[-1]["body"])


class SimulationOwnerContracts(unittest.TestCase):
    def test_live_fencing_probe_headers_reach_the_actual_effect_owner(self):
        sys.path.insert(0, str(ROOT/'scripts/p06'))
        from live_execution import effect_headers
        headers = effect_headers(GRANT, 'effect-only')
        status, payload = request_worker('/v1/effects', GRANT, supplied_headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(payload, {'accepted':True, 'duplicate':False})
        stale = effect_headers({**GRANT, 'attempt_id':TENANT}, 'effect-only')
        status, _ = request_worker('/v1/effects', GRANT, supplied_headers=stale)
        self.assertEqual(status, 403)

    def test_authenticated_worker_and_lifecycle_consumer(self):
        for route, body, response_name in (
            ("/v1/effects", GRANT, "EffectReceipt"),
            ("/v1/reconciliations", BINDING, "ObservationReceipt"),
        ):
            status, denied = request_worker(route, body, bearer="wrong-audience")
            self.assertEqual(status, 403)
            self.assertEqual(denied["code"], "simulation_denied")
            status, payload = request_worker(route, body)
            self.assertEqual(status, 200)
            Draft202012Validator(
                {"$ref": "#/components/schemas/" + response_name,
                 "components": API["components"]},
                format_checker=FormatChecker()).validate(payload)
            wire = [payload]

            class Response:
                status = 200

                def read(self, limit):
                    return json.dumps(wire[0]).encode()

                def getheader(self, name, default=None):
                    return "identity"

            class Connection:
                def __init__(self, *args, **kwargs):
                    pass

                def request(self, method, path, data, headers):
                    self_headers.append(headers)
                    self_paths.append(path)

                def getresponse(self):
                    return Response()

                def close(self):
                    pass

            self_headers, self_paths = [], []
            with (
                patch.dict(os.environ, {
                    "SIMULATOR_URL": "https://simulator.example",
                    "SIMULATOR_CA_FILE": "/tmp/synthetic-ca",
                }),
                patch.object(client, "mounted_secret", return_value="synthetic-token"),
                patch.object(client.ssl, "create_default_context", return_value=object()),
                patch.object(client.http.client, "HTTPSConnection", Connection),
            ):
                self.assertEqual(client.request("SIMULATOR", "POST", route, body), payload)
                self.assertEqual(self_paths[-1], route)
                self.assertEqual(len(self_headers[-1]["Idempotency-Key"]), 64)
                if route == "/v1/reconciliations":
                    wire[0] = {**payload, "tenant_id": FOREIGN}
                else:
                    wire[0] = {**payload, "uncontracted": True}
                with self.assertRaises(Rejected):
                    client.request("SIMULATOR", "POST", route, body)
                with self.assertRaises(Rejected):
                    client.request("SIMULATOR", "POST", "/uncontracted", body)
            status, rejected = request_worker(route, {**body, "uncontracted": True})
            self.assertEqual(status, 403)
            class ExtraReceipt(Effects):
                def execute(self, grant):
                    return {"accepted": True, "duplicate": False, "uncontracted": True}

                def reconcile(self, data):
                    return {**OBSERVATION, "uncontracted": True}

            status, denied = request_worker(route, body, service=ExtraReceipt())
            self.assertEqual(status, 403)
            self.assertEqual(denied["code"], "simulation_denied")
            Draft202012Validator(
                {"$ref": "#/components/schemas/Error",
                 "components": API["components"]},
                format_checker=FormatChecker()).validate(rejected)

    def test_independent_observation_audience_and_payload(self):
        status, payload = request_worker(
            "/v1/observations", BINDING, bearer="observation-only")
        self.assertEqual(status, 200)
        Draft202012Validator(
            {"$ref": "#/components/schemas/ObservationReceipt",
             "components": API["components"]},
            format_checker=FormatChecker()).validate(payload)
        status, refusal = request_worker(
            "/v1/observations", BINDING, bearer="effect-only")
        self.assertEqual(status, 403)
        self.assertEqual(refusal["code"], "simulation_denied")

        class PoisonedEffects(Effects):
            def observe(self, data):
                return {**OBSERVATION, "tenant_id": FOREIGN}

        status, refusal = request_worker(
            "/v1/observations", BINDING, bearer="observation-only",
            service=PoisonedEffects())
        self.assertEqual(status, 403)
        self.assertEqual(refusal["code"], "simulation_denied")


if __name__ == "__main__":
    unittest.main()
