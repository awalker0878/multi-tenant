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
        wire = [RECEIPT]
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
            self.assertEqual(AlertReceiver().deliver(ALERT), C)
            self.assertEqual(paths[0][0:3], ("POST", "/v1/lifecycle-alerts", ALERT))
            self.assertIn("Authorization", paths[0][3])
            for poisoned in (
                {**RECEIPT, "event_id": B},
                {**RECEIPT, "acknowledged": False},
                {**RECEIPT, "extra": "uncontracted"},
                {**RECEIPT, "receipt_id": "not-an-id"},
            ):
                wire[0] = poisoned
                with self.subTest(poisoned=poisoned), self.assertRaises(Rejected):
                    AlertReceiver().deliver(ALERT)
            for poisoned in (
                {**ALERT, "unexpected": True},
                {**ALERT, "simulation": False},
                {**ALERT, "job_id": "not-an-id"},
            ):
                with self.subTest(poisoned=poisoned), self.assertRaises(Rejected):
                    AlertReceiver().deliver(poisoned)
            with self.assertRaises(Rejected):
                transport.request("ALERTS", "POST", "/v1/uncontracted", ALERT)

    def test_outbound_schema_matches_immutable_installed_copy(self):
        original = ROOT / "contracts/schemas/lifecycle/alert-delivery-v1.json"
        installed = ROOT / "services/lifecycle/src/lifecycle/infrastructure/contracts/alert-delivery-v1.json"
        self.assertEqual(original.read_bytes(), installed.read_bytes())


if __name__ == "__main__":
    unittest.main()
