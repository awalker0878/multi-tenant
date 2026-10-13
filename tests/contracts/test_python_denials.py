"""Fail-closed behavior of executable Python HTTP denial evidence."""
from __future__ import annotations

import asyncio
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/contracts"))

import python_denials


class PythonDenialExecutionTests(unittest.TestCase):
    def test_missing_router_never_mints_denial_evidence(self):
        operations = {"operations": [
            {"owner": "planning", "security_required": True,
             "release": "contracts/openapi/planning-v1.2.json",
             "method": "GET", "path": "/v1/tenants/{tenant}/plans",
             "key": "planning-get", "release_sha256": "a" * 64},
        ]}
        with patch.object(python_denials, "inventory", return_value=operations), \
                patch.object(python_denials, "get_app", side_effect=RuntimeError("unavailable")):
            evidence, unresolved = asyncio.run(python_denials.probe("planning"))
        self.assertEqual(evidence, [])
        self.assertTrue(any("router-unavailable" in item for item in unresolved))

    def test_wrong_status_is_unresolved_not_a_pass(self):
        operation = {
            "owner": "inventory", "security_required": True,
            "release": "contracts/openapi/inventory-v1.9.json",
            "method": "GET", "path": "/v1/tenants/{tenant}/resources",
            "key": "inventory-get", "release_sha256": "a" * 64,
        }
        with patch.object(python_denials, "inventory",
                          return_value={"operations": [operation]}), \
                patch.object(python_denials, "get_app", return_value=object()), \
                patch.object(python_denials, "exchange",
                             new_callable=AsyncMock, return_value=404):
            evidence, unresolved = asyncio.run(python_denials.probe("inventory"))
        self.assertFalse(evidence)
        self.assertEqual(unresolved, ["inventory-get unsupported-denial:404"])

    def test_no_eligible_secured_routes_is_unresolved(self):
        with patch.object(python_denials, "inventory", return_value={"operations": []}), \
                patch.object(python_denials, "get_app", return_value=object()):
            evidence, unresolved = asyncio.run(python_denials.probe("planning"))
        self.assertEqual(evidence, [])
        self.assertEqual(unresolved, ["planning no-secured-runtime-operations-exercised"])

    def test_cli_returns_failure_and_preserves_diagnostics_on_partial_proof(self):
        qualified = {"key": "verified", "claim": "authorization"}
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "denials.json"
            for observations, unresolved, expected_exit in (
                ([qualified], ["route-not-found"], 1),
                ([], ["router-unavailable"], 1),
                ([qualified], [], 0),
            ):
                with patch.object(python_denials, "probe",
                                  new_callable=AsyncMock,
                                  return_value=(observations, unresolved)), \
                        patch.object(sys, "argv", [
                            "python_denials.py", "--owner", "inventory",
                            "--output", str(output),
                        ]), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(python_denials.main(), expected_exit)
                self.assertEqual(json.loads(output.read_text()), observations)


if __name__ == "__main__":
    unittest.main()
