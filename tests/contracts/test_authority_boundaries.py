"""Executable Lifecycle placement response and authorization-boundary tests."""
from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from lifecycle.application.reservations import Held
from lifecycle.interfaces.placement_reservations import PlacementReservationApp
from planning.infrastructure.owner_contracts import contract_for_operation

ROOT = Path(__file__).resolve().parents[2]
TENANT = "10000000-0000-4000-8000-000000000001"
OTHER = "10000000-0000-4000-8000-000000000002"
HEX = "a" * 64
RECEIPT = {
    "schema_version": 1, "reservation_id": TENANT, "tenant_id": TENANT,
    "plan_digest": HEX, "request_digest": HEX, "placement_sha256": HEX,
    "generation_id": OTHER, "policy_sha256": HEX,
    "allocations": [{"workload_id": TENANT, "pool_id": HEX,
                      "native_ref": "provider-host",
                      "vector": {"vcpus": 2, "memory_mib": 1024,
                                 "storage_gib": 4, "addresses": 1}}],
    "state": "reserved", "observed_at": 2000000000, "expires_at": 2000000030,
    "revision": 1, "native_write_authorized": False,
}


class Service:
    def __init__(self, receipt=None):
        self.receipt = receipt if receipt is not None else RECEIPT

    def check(self, tenant, digest):
        if tenant != TENANT or digest != HEX:
            raise Held("placement_reservation_missing")
        return self.receipt

    def reserve(self, tenant, body):
        if tenant != body.get("scope", {}).get("tenant_id"):
            raise Held("placement_scope_invalid")
        return self.receipt

    def transition(self, tenant, digest, command):
        if tenant != TENANT:
            raise Held("placement_transition_invalid")
        return self.receipt


def invoke(service, tenant=TENANT, operation="checks", bearer="fixture"):
    messages = []

    async def receive():
        return {"type": "http.request", "body": json.dumps({"plan_digest": HEX}).encode(),
                "more_body": False}

    async def send(message):
        messages.append(message)

    def authorize(token):
        if token != "fixture":
            raise Held("placement_caller_denied")

    app = PlacementReservationApp(service, authorize)
    scope = {"type": "http", "method": "POST",
             "path": f"/internal/tenants/{tenant}/placement-reservations/{operation}",
             "query_string": b"",
             "headers": [(b"authorization", ("Bearer " + bearer).encode())]}
    asyncio.run(app(scope, receive, send))
    return messages[0]["status"], json.loads(messages[-1]["body"])


class OwnerBoundaryContracts(unittest.TestCase):
    def test_real_asgi_owner_validates_a_produced_receipt(self):
        status, body = invoke(Service())
        self.assertEqual(status, 200)
        self.assertEqual(body, RECEIPT)
        schema = json.loads((ROOT / "contracts/schemas/planning/placement-reservation-v1.json").read_text())
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(body)

    def test_real_asgi_owner_never_emits_an_uncontracted_success(self):
        for poisoned in ({**RECEIPT, "native_write_authorized": True},
                         {**RECEIPT, "unexpected_authority": True},
                         {**RECEIPT, "allocations": []}):
            status, body = invoke(Service(poisoned))
            self.assertEqual(status, 503)
            self.assertEqual(body, {"error": "placement_owner_unavailable"})

    def test_real_asgi_owner_denies_a_cross_tenant_read(self):
        status, body = invoke(Service(), tenant=OTHER)
        self.assertEqual(status, 423)
        self.assertEqual(body, {"error": "placement_reservation_missing"})
        status, body = invoke(Service(), bearer="invalid")
        self.assertNotEqual(status, 200)
        self.assertEqual(body, {"error": "placement_caller_denied"})

    def test_governance_and_lifecycle_operations_have_no_untyped_bypass(self):
        self.assertEqual(contract_for_operation("GOVERNANCE", "POST",
            f"/v1/tenants/{TENANT}/delegated-authorizations"), "governance-delegation-response-v1")
        self.assertEqual(contract_for_operation("CAPACITY", "POST",
            f"/internal/tenants/{TENANT}/placement-reservations/checks"), "placement-reservation-v1")
        with self.assertRaises(ValueError):
            contract_for_operation("GOVERNANCE", "POST",
                f"/v1/tenants/{TENANT}/undocumented-authority")
