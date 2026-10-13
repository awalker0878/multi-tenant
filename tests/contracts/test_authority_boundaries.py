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


def invoke(service, tenant=TENANT, operation="checks", bearer="fixture", command=None):
    messages = []

    async def receive():
        return {"type": "http.request", "body": json.dumps({"plan_digest": HEX} if command is None else command).encode(),
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
                         {**RECEIPT, "allocations": []},
                         {**RECEIPT, "tenant_id": OTHER},
                         {**RECEIPT, "plan_digest": "b" * 64}):
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

    def test_actual_owner_denies_invalid_and_unbounded_commands(self):
        for request_body in ({"plan_digest": "not-a-digest"},
                             {"plan_digest": HEX, "unexpected": "scope_override"},
                             {"plan_digest": HEX, "tenant_id": OTHER}):
            status, body = invoke(Service(), command=request_body)
            self.assertEqual(status, 423)
            self.assertEqual(body, {"error": "placement_request_invalid"})

    def test_governance_and_lifecycle_operations_have_no_untyped_bypass(self):
        self.assertEqual(contract_for_operation("GOVERNANCE", "POST",
            f"/v1/tenants/{TENANT}/delegated-authorizations"), "governance-delegation-response-v1")
        self.assertEqual(contract_for_operation("CAPACITY", "POST",
            f"/internal/tenants/{TENANT}/placement-reservations/checks"), "placement-reservation-v1")
        with self.assertRaises(ValueError):
            contract_for_operation("GOVERNANCE", "POST",
                f"/v1/tenants/{TENANT}/undocumented-authority")


    def test_all_placement_owner_operations_use_strict_openapi(self):
        document = json.loads((ROOT / "contracts/openapi/lifecycle-internal-authority-v1.json").read_text())
        canonical = json.loads((ROOT / "contracts/schemas/planning/placement-reservation-v1.json").read_text())
        # OpenAPI normalizes UUID lexical patterns while retaining canonical semantics.
        def without_uuid_patterns(value):
            if isinstance(value, list):
                return [without_uuid_patterns(v) for v in value]
            if isinstance(value, dict):
                return {
                    k: without_uuid_patterns(v) for k, v in value.items()
                    if not (k == "pattern" and value.get("format") == "uuid")
                }
            return value
        self.assertEqual(without_uuid_patterns(
            document["components"]["schemas"]["PlacementReceipt"]), canonical)
        for operation in ("reserve", "checks", "confirm", "renew", "release"):
            uri = f"/internal/tenants/{{tenant}}/placement-reservations/{operation}"
            published = document["paths"][uri]["post"]
            body_ref = published["requestBody"]["content"]["application/json"]["schema"]["$ref"]
            expected = "PlacementReserveCommand" if operation == "reserve" else "PlacementDigestCommand"
            self.assertEqual(body_ref, "#/components/schemas/" + expected)
            self.assertEqual(
                published["responses"]["200"]["content"]["application/json"]["schema"],
                {"$ref": "#/components/schemas/PlacementReceipt"},
            )
            command = (
                {"scope": {"tenant_id": TENANT}, "plan_digest": HEX, "generation_id": OTHER,
                 "policy_sha256": HEX, "placement_sha256": HEX,
                 "allocations": RECEIPT["allocations"]}
                if operation == "reserve" else {"plan_digest": HEX}
            )
            status, receipt = invoke(Service(), operation=operation, command=command)
            self.assertEqual(status, 200)
            self.assertEqual(receipt, RECEIPT)
            Draft202012Validator(canonical, format_checker=FormatChecker()).validate(receipt)
            status, denial = invoke(Service(), operation=operation,
                                    command={**command, "uncontracted": True})
            self.assertEqual(status, 423)
            self.assertEqual(denial["error"], "placement_request_invalid")
            # Exercise the same authenticated HTTP boundary with another
            # tenant route. A service-owned credential is not treated as a
            # tenant-scoped credential for assurance reporting.
            status, refusal = invoke(Service(), tenant=OTHER, operation=operation,
                                     command=command)
            self.assertEqual(status, 423)
            self.assertIn(refusal["error"],
                          {"placement_scope_invalid", "placement_reservation_missing",
                           "placement_transition_invalid"})

    def test_real_asgi_owner_and_planning_consumer_roundtrip(self):
        import os
        from unittest.mock import patch
        from planning.domain.model import Rejected
        from planning.infrastructure import owners

        status, produced = invoke(Service())
        self.assertEqual(status, 200)
        wire = [produced]

        class Response:
            status = 200

            def read(self, size):
                return json.dumps(wire[0]).encode()

            def getheader(self, name, default=None):
                return "identity"

        class Connection:
            def __init__(self, *args, **kwargs):
                pass

            def request(self, method, path, data, headers):
                assert method == "POST" and path.endswith("/placement-reservations/checks")

            def getresponse(self):
                return Response()

            def close(self):
                pass

        path = f"/internal/tenants/{TENANT}/placement-reservations/checks"
        with (
            patch.dict(os.environ, {"CAPACITY_URL": "https://capacity.example",
                                    "CAPACITY_CA_FILE": "/tmp/synthetic-ca"}),
            patch.object(owners, "mounted_secret", return_value="synthetic-token"),
            patch.object(owners.ssl, "create_default_context", return_value=object()),
            patch.object(owners.http.client, "HTTPSConnection", Connection),
        ):
            self.assertEqual(owners.request("CAPACITY", "POST", path, {"plan_digest": HEX}), produced)
            for poisoned in (
                {**produced, "tenant_id": OTHER},
                {**produced, "plan_digest": "b" * 64},
                {**produced, "unexpected_authority": True},
            ):
                wire[0] = poisoned
                with self.assertRaises(Rejected) as caught:
                    owners.request("CAPACITY", "POST", path, {"plan_digest": HEX})
                self.assertEqual(caught.exception.status, 503)


class LifecycleOwnerTransportContracts(unittest.TestCase):
    def test_real_lifecycle_consumer_validates_current_assurance_receipt(self):
        import os
        from unittest.mock import patch
        from lifecycle.domain.execution import Rejected
        from lifecycle.infrastructure import execution_owners

        wire = [{"id": TENANT, "state": "uploaded"}]
        code = [201]

        class Response:
            def read(self, limit):
                return json.dumps(wire[0]).encode()

            def getheader(self, name, default=None):
                return "identity"

            @property
            def status(self):
                return code[0]

        class Connection:
            def __init__(self, *args, **kwargs):
                pass

            def request(self, method, path, data, headers):
                self.method, self.path = method, path

            def getresponse(self):
                return Response()

            def close(self):
                pass

        with (
            patch.dict(os.environ, {"ASSURANCE_URL": "https://assurance.example",
                                    "ASSURANCE_CA_FILE": "/tmp/synthetic-ca"}),
            patch.object(execution_owners, "mounted_secret", return_value="synthetic-token"),
            patch.object(execution_owners.ssl, "create_default_context", return_value=object()),
            patch.object(execution_owners.http.client, "HTTPSConnection", Connection),
        ):
            path = f"/v1/tenants/{TENANT}/evidence-uploads"
            self.assertEqual(execution_owners.request("ASSURANCE", "POST", path, {}), wire[0])
            for invalid in ({"id": TENANT, "state": "uploaded", "unexpected": True},
                            {"id": TENANT, "state": "finalized"},
                            {"id": "not-a-uuid", "state": "uploaded"}):
                wire[0] = invalid
                with self.assertRaises(Rejected) as error:
                    execution_owners.request("ASSURANCE", "POST", path, {})
                self.assertEqual(error.exception.status, 503)
            wire[0] = {"id": TENANT, "state": "uploaded"}
            code[0] = 200
            with self.assertRaises(Rejected):
                execution_owners.request("ASSURANCE", "POST", path, {})
            with self.assertRaises(Rejected):
                execution_owners.request("ASSURANCE", "POST", f"/v1/tenants/{OTHER}/unregistered", {})
            # An unknown owner must never bypass the installed response contract.
            with self.assertRaises(Rejected) as untyped:
                execution_owners.request("CAPACITY", "POST",
                    f"/internal/tenants/{TENANT}/placement-reservations/checks", {})
            self.assertEqual(untyped.exception.status, 503)

