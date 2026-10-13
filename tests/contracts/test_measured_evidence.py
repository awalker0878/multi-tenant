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
        for selector, bindings in measured.TESTS.items():
            self.assertTrue((ROOT / selector.split("::", 1)[0]).is_file(), selector)
            self.assertTrue(bindings, selector)
            for owner, method, path, claims in bindings:
                self.assertTrue(owner and method and path and claims)
        for selector, (path, claims) in measured.RELEASE_TESTS.items():
            self.assertTrue((ROOT / selector.split("::", 1)[0]).is_file(), selector)
            self.assertTrue(path and claims, selector)

    @staticmethod
    def fake_passed_test_run(argv, **_kwargs):
        receipt = next(Path(arg.split("=", 1)[1]) for arg in argv
                       if arg.startswith("--junitxml="))
        cases = sorted(set(measured.TESTS) | set(measured.RELEASE_TESTS))
        elements = "".join('<testcase name="' + selector.rsplit("::", 1)[-1] + '"/>'
                           for selector in cases)
        receipt.write_text("<testsuites><testsuite>" + elements + "</testsuite></testsuites>")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def test_successful_execution_attributes_only_explicit_current_claims(self):
        with patch.object(measured.subprocess, "run",
                          side_effect=self.fake_passed_test_run) as execute:
            with patch.dict(os.environ, {"GITHUB_RUN_ID": "23", "GITHUB_SHA": "a" * 40}):
                proofs = measured.verified_consumers()
        execute.assert_called_once()
        self.assertTrue(proofs)
        self.assertEqual(len(proofs), len({(p["key"], p["claim"]) for p in proofs}))
        for proof in proofs:
            if proof["claim"] == "authorization":
                self.assertEqual(proof["source"], "live-denial")
                self.assertEqual(proof["status_code"], 403)
                self.assertEqual(proof["denial_kind"], "invalid-credential")
            self.assertEqual(proof["result"], "PASS")
            self.assertEqual(proof["run_id"], "23")
            self.assertEqual(proof["revision"], "a" * 40)
            self.assertEqual(len(proof["release_sha256"]), 64)
        for operation in ("reserve", "checks", "confirm", "renew", "release"):
            key = '["lifecycle","POST","/internal/tenants/{tenant}/placement-reservations/' + operation + '"]'
            self.assertIn((key, "producer"), {(p["key"], p["claim"]) for p in proofs})

    def test_skipped_test_cannot_mint_producer_or_consumer_proof(self):
        def skip_case(argv, **kwargs):
            response = self.fake_passed_test_run(argv, **kwargs)
            filename = next(Path(arg.split("=", 1)[1]) for arg in argv
                            if arg.startswith("--junitxml="))
            content = filename.read_text()
            filename.write_text(content.replace("/>", '><skipped/></testcase>', 1))
            return response
        with patch.object(measured.subprocess, "run", side_effect=skip_case):
            with self.assertRaisesRegex(RuntimeError, "skipped or failed"):
                measured.verified_consumers()

    def test_missing_pass_receipt_rejects_unexecuted_selector(self):
        def omit_case(argv, **kwargs):
            response = self.fake_passed_test_run(argv, **kwargs)
            filename = next(Path(arg.split("=", 1)[1]) for arg in argv
                            if arg.startswith("--junitxml="))
            content = filename.read_text()
            selector = sorted(measured.TESTS)[0].rsplit("::", 1)[-1]
            filename.write_text(content.replace('<testcase name="' + selector + '"/>', ''))
            return response
        with patch.object(measured.subprocess, "run", side_effect=omit_case):
            with self.assertRaisesRegex(RuntimeError, "did not execute"):
                measured.verified_consumers()

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
