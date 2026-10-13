"""The measured-proof runner must execute and attribute real test outcomes.

These tests assert executable proof registration and never award coverage from
the name of a test or from the presence of a contract file alone.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/contracts"))

import measured_consumers as measured


class MeasuredProofTests(unittest.TestCase):
    def test_every_claim_points_to_a_real_executable_selector(self):
        self.assertTrue(measured.TESTS)
        self.assertTrue(measured.RELEASE_TESTS)
        for registry in (measured.TESTS, measured.RELEASE_TESTS):
            for selector, bindings in registry.items():
                self.assertTrue((ROOT / selector.split("::", 1)[0]).is_file(), selector)
                self.assertTrue(bindings, selector)
                self.assertTrue(all(isinstance(binding, tuple) for binding in bindings))

    def test_successful_execution_attributes_only_explicit_current_claims(self):
        with patch.object(measured.subprocess, "run",
                          return_value=SimpleNamespace(returncode=0, stdout="", stderr="")) as execute:
            with patch.dict(os.environ, {"GITHUB_RUN_ID": "23", "GITHUB_SHA": "a" * 40}):
                proofs = measured.verified_consumers()
        execute.assert_called_once()
        self.assertTrue(proofs)
        self.assertEqual(len(proofs), len({(p["key"], p["claim"]) for p in proofs}))
        for proof in proofs:
            self.assertEqual(proof["result"], "PASS")
            self.assertEqual(proof["run_id"], "23")
            self.assertEqual(proof["revision"], "a" * 40)
            self.assertEqual(len(proof["release_sha256"]), 64)
        for operation in ("reserve", "checks", "confirm", "renew", "release"):
            key = '["lifecycle","POST","/internal/tenants/{tenant}/placement-reservations/' + operation + '"]'
            self.assertIn((key, "producer"), {(p["key"], p["claim"]) for p in proofs})

    def test_failed_executable_test_never_mints_a_pass_receipt(self):
        with patch.object(measured.subprocess, "run",
                          return_value=SimpleNamespace(returncode=1, stdout="failed", stderr="")):
            with self.assertRaisesRegex(RuntimeError, "Exact producer/consumer qualification failed"):
                measured.verified_consumers()

    def test_cli_writes_proofs_and_does_not_reference_an_undefined_case_count(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "measured.json"
            with patch.object(measured, "verified_consumers",
                              return_value=[{"key": "example", "claim": "consumer"}]), \
                    patch.object(sys, "argv", ["measured_consumers.py", "--output", str(dest)]), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                measured.main()
            self.assertEqual(json.loads(dest.read_text()),
                             [{"key": "example", "claim": "consumer"}])
            self.assertIn("Validated", output.getvalue())


if __name__ == "__main__":
    unittest.main()
