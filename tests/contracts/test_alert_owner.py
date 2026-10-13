"""Lifecycle's external alert sink has a single typed, fail-closed wire boundary.

The transport fixture exercises the installed response decoder, not an external
production receiver. It is eligible for consumer proof, not producer or tenant
isolation assurance.
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from lifecycle.domain.execution import Rejected
from lifecycle.application.execution import Execution
from jsonschema import Draft202012Validator, FormatChecker
from lifecycle.infrastructure.execution_owners import AlertReceiver
from lifecycle.infrastructure import execution_owners as transport

ROOT = Path(__file__).resolve().parents[2]
A = "10000000-0000-4000-8000-000000000001"
B = "10000000-0000-4000-8000-000000000002"
C = "10000000-0000-4000-8000-000000000003"
ALERT = {"id": A, "job_id": B, "reason": "simulation_held", "simulation": True}
RECEIPT = {"event_id": A, "acknowledged": True, "receipt_id": C}


class AlertOwnerContracts(unittest.TestCase):
    def test_installed_alert_contract_fences_external_receipts(self):
        # Exercise the actual Lifecycle alert producer, not an assembled
        # example or a static JSON fixture.
        captured = []

        class Tx:
            def one(self, sql, parameters):
                if "SELECT state,reason" in sql:
                    return {"state": "running", "reason": None}
                if "SELECT revision" in sql:
                    return {"revision": 2}
                raise AssertionError("unexpected SQL read")

            def execute(self, sql, parameters):
                if "INSERT INTO app.execution_alerts" in sql:
                    captured.append(json.loads(parameters[-1]))

        Execution(None, None, None, None, lambda: 123).project(
            Tx(), B, "held", "simulation_held"
        )
        self.assertEqual(len(captured), 1)
        event = captured[0]
        self.assertEqual(event["job_id"], B)
        published = json.loads((ROOT / "contracts/schemas/lifecycle/alert-delivery-v1.json").read_text())
        command = {"$ref": "#/$defs/Command", "$defs": published["$defs"]}
        Draft202012Validator(command, format_checker=FormatChecker()).validate(event)
        receipt = {**RECEIPT, "event_id": event["id"]}
        wire = [receipt]
        paths = []
        class Response:
            status = 200

            def read(self, limit):
                return json.dumps(wire[0]).encode("utf-8")

            def getheader(self, name, default=None):
                return "identity"

        class Connection:
            def __init__(self, *args, **kwargs):
                pass

            def request(self, method, path, body, headers):
                paths.append((method, path, json.loads(body), headers))

            def getresponse(self):
                return Response()

            def close(self):
                pass

        with (
            patch.dict(os.environ, {
                "ALERTS_URL": "https://commissioned-alert-sink.example",
                "ALERTS_CA_FILE": "/tmp/commissioned-alert-ca",
            }),
            patch.object(transport, "mounted_secret", return_value="synthetic-alert-token"),
            patch.object(transport.ssl, "create_default_context", return_value=object()),
            patch.object(transport.http.client, "HTTPSConnection", Connection),
        ):
            self.assertEqual(AlertReceiver().deliver(event), C)
            self.assertEqual(paths[0][0:3], ("POST", "/v1/lifecycle-alerts", event))
            self.assertIn("Authorization", paths[0][3])
            for poisoned in (
                {**receipt, "event_id": B},
                {**receipt, "acknowledged": False},
                {**receipt, "extra": "uncontracted"},
                {**receipt, "receipt_id": "not-an-id"},
            ):
                wire[0] = poisoned
                with self.subTest(poisoned=poisoned), self.assertRaises(Rejected):
                    AlertReceiver().deliver(event)
            for poisoned in (
                {**event, "unexpected": True},
                {**event, "simulation": False},
                {**event, "job_id": "not-an-id"},
            ):
                with self.subTest(poisoned=poisoned), self.assertRaises(Rejected):
                    AlertReceiver().deliver(poisoned)
            with self.assertRaises(Rejected):
                transport.request("ALERTS", "POST", "/v1/uncontracted", event)

    def test_outbound_schema_matches_immutable_installed_copy(self):
        original = ROOT / "contracts/schemas/lifecycle/alert-delivery-v1.json"
        installed = ROOT / "services/lifecycle/src/lifecycle/infrastructure/contracts/alert-delivery-v1.json"
        self.assertEqual(original.read_bytes(), installed.read_bytes())


if __name__ == "__main__":
    unittest.main()
