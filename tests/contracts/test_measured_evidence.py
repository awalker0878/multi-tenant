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

    def test_external_alert_receiver_is_not_claimed_as_executed_producer(self):
        # A synthetic acknowledgement injected into Lifecycle's HTTP client
        # cannot establish producer behavior for the external alert sink.
        selector = ("tests/contracts/test_alert_owner.py::"
                    "AlertOwnerContracts::test_installed_alert_contract_fences_external_receipts")
        path, claims = measured.RELEASE_TESTS[selector]
        self.assertEqual(path, "contracts/schemas/lifecycle/alert-delivery-v1.json")
        self.assertEqual(claims, ("consumer",))

    @staticmethod
    def fake_passed_test_run(argv, **_kwargs):
        receipt = next(Path(arg.split("=", 1)[1]) for arg in argv
                       if arg.startswith("--junitxml="))
        cases = sorted(set(measured.TESTS) | set(measured.RELEASE_TESTS))
        def testcase(selector):
            path, *parts = selector.split("::")
            classname = ".".join(Path(path).with_suffix("").parts)
            if len(parts) > 1:
                classname += "." + ".".join(parts[:-1])
            return '<testcase classname="' + classname + '" name="' + parts[-1] + '"/>'
        elements = "".join(testcase(selector) for selector in cases)
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
            from xml.etree import ElementTree
            root = ElementTree.fromstring(content)
            suite = root.find("testsuite")
            suite.remove(list(suite)[0])
            filename.write_text(ElementTree.tostring(root, encoding="unicode"))
            return response
        with patch.object(measured.subprocess, "run", side_effect=omit_case):
            with self.assertRaisesRegex(RuntimeError, "did not execute"):
                measured.verified_consumers()

    def test_importlib_top_level_function_without_classname_has_unique_identity(self):
        # Pytest 9 may write an empty classname for an explicitly selected
        # module-level function. The exact selector plus unique test name
        # provides independently attributable evidence in that case.
        from xml.etree import ElementTree

        def empty_top_level_classname(argv, **kwargs):
            result = self.fake_passed_test_run(argv, **kwargs)
            receipt = next(Path(arg.split("=", 1)[1]) for arg in argv
                           if arg.startswith("--junitxml="))
            tree = ElementTree.parse(receipt)
            node = next(node for node in tree.iter("testcase")
                        if node.attrib["name"] ==
                        "test_real_inventory_planning_response_validates_installed_strict_schema")
            node.set("classname", "")
            tree.write(receipt, encoding="unicode")
            return result

        with patch.object(measured.subprocess, "run",
                          side_effect=empty_top_level_classname):
            self.assertTrue(measured.verified_consumers())

    def test_importlib_shorthand_requires_unique_selected_module(self):
        from xml.etree import ElementTree

        def abbreviated_module(argv, **kwargs):
            result = self.fake_passed_test_run(argv, **kwargs)
            receipt = next(Path(arg.split("=", 1)[1]) for arg in argv
                           if arg.startswith("--junitxml="))
            tree = ElementTree.parse(receipt)
            node = next(node for node in tree.iter("testcase")
                        if node.attrib["name"] ==
                        "test_capacity_and_governance_owner_responses_are_schema_and_scope_validated")
            node.set("classname", "test_owner_operation_contracts")
            tree.write(receipt, encoding="unicode")
            return result

        with patch.object(measured.subprocess, "run", side_effect=abbreviated_module):
            proofs = measured.verified_consumers()
        self.assertTrue(any(
            proof["key"] == '["governance","POST","/v1/tenants/{tenant}/delegated-authorizations"]'
            and proof["claim"] == "consumer"
            for proof in proofs
        ))

    def test_actual_pytest_junit_module_and_class_abbreviations_are_unambiguous(self):
        from xml.etree import ElementTree

        def abbreviated(argv, **kwargs):
            result = self.fake_passed_test_run(argv, **kwargs)
            receipt = next(Path(arg.split("=", 1)[1]) for arg in argv
                           if arg.startswith("--junitxml="))
            tree = ElementTree.parse(receipt)
            for node in tree.iter("testcase"):
                classname = node.attrib["classname"]
                if "test_owner_operation_contracts" in classname:
                    node.set("classname", "tests.test_owner_operation_contracts")
                elif "test_alert_owner." in classname:
                    node.set("classname", ".AlertOwnerContracts")
                elif "test_authority_boundaries." in classname:
                    node.set("classname", "." + classname.rsplit(".", 1)[-1])
                elif "test_simulation_owner." in classname:
                    node.set("classname", ".SimulationOwnerContracts")
            tree.write(receipt, encoding="unicode")
            return result

        with patch.object(measured.subprocess, "run", side_effect=abbreviated):
            proofs = measured.verified_consumers()
        self.assertTrue(any(
            proof["key"] == "contracts/schemas/lifecycle/alert-delivery-v1.json"
            and proof["claim"] == "consumer" for proof in proofs
        ))
        self.assertTrue(any(
            proof["key"] == '["lifecycle-workers","POST","/v1/effects"]'
            and proof["claim"] == "consumer" for proof in proofs
        ))

    def test_class_receipt_from_unselected_class_is_not_credited(self):
        from xml.etree import ElementTree

        def fake_wrong_class(argv, **kwargs):
            result = self.fake_passed_test_run(argv, **kwargs)
            receipt = next(Path(arg.split("=", 1)[1]) for arg in argv
                           if arg.startswith("--junitxml="))
            tree = ElementTree.parse(receipt)
            node = next(node for node in tree.iter("testcase")
                        if node.attrib["name"] ==
                        "test_installed_alert_contract_fences_external_receipts")
            node.set("classname", ".WrongAlertOwnerContracts")
            tree.write(receipt, encoding="unicode")
            return result

        with patch.object(measured.subprocess, "run", side_effect=fake_wrong_class):
            with self.assertRaisesRegex(RuntimeError, "selector did not execute"):
                measured.verified_consumers()

    def test_same_short_name_from_wrong_module_cannot_mint_proof(self):
        from xml.etree import ElementTree

        def replace_module(argv, **kwargs):
            response = self.fake_passed_test_run(argv, **kwargs)
            receipt = next(Path(arg.split("=", 1)[1]) for arg in argv
                           if arg.startswith("--junitxml="))
            root = ElementTree.parse(receipt)
            one = next(root.iter("testcase"))
            one.set("classname", "a.different.module")
            root.write(receipt, encoding="unicode")
            return response

        with patch.object(measured.subprocess, "run", side_effect=replace_module):
            with self.assertRaisesRegex(RuntimeError, "selector did not execute"):
                measured.verified_consumers()

    def test_duplicate_execution_record_cannot_mint_proof(self):
        from xml.etree import ElementTree

        def duplicate(argv, **kwargs):
            response = self.fake_passed_test_run(argv, **kwargs)
            receipt = next(Path(arg.split("=", 1)[1]) for arg in argv
                           if arg.startswith("--junitxml="))
            root = ElementTree.parse(receipt)
            suite = root.find("testsuite")
            source = list(suite)[0]
            suite.append(ElementTree.fromstring(ElementTree.tostring(source)))
            root.write(receipt, encoding="unicode")
            return response

        with patch.object(measured.subprocess, "run", side_effect=duplicate):
            with self.assertRaisesRegex(RuntimeError, "Duplicated producer/consumer"):
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
