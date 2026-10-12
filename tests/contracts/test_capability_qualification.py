"""Phase 4 attestation gate cannot pass missing or skipped method/mode tests."""
from __future__ import annotations

import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/contracts"))
from qualify_capabilities import MANDATORY, qualify


class ExecutedCapabilityEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.xml = Path(self.tmp.name) / "real-worker.xml"
        self.declaration = json.loads(
            (ROOT / "contracts/capabilities/definitions-v1.json").read_text()
        )

    def valid_suite(self) -> ET.Element:
        suite = ET.Element("testsuite")
        for method in self.declaration["methods"]:
            for mode in self.declaration["modes"]:
                ET.SubElement(suite, "testcase", {
                    "classname": "test_capability_qualification",
                    "name": "test_current_capability_method_mode_execution_and_denial"
                            f"[MATRIX_{method}__{mode}]",
                })
        for name in MANDATORY:
            ET.SubElement(suite, "testcase", {
                "classname": "test_method_protocol", "name": name,
            })
        # Include every truly implemented native operation, not a list of
        # strings that merely happen to occur in a handler's source.
        source = (ROOT / "workers/lifecycle/src/lifecycle_worker/infrastructure/migration_method.py")
        module = ast.parse(source.read_text())
        table = next(ast.literal_eval(node.value) for node in module.body
                     if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == "OPERATIONS"
                             for target in node.targets))
        for entry in self.declaration["methods"].values():
            if not entry["implementation"]["handler"].endswith("/migration_method.py"):
                continue
            alias = entry["v1_alias"]
            for stage in table[alias]:
                ET.SubElement(suite, "testcase", {
                    "classname": "test_method_protocol",
                    "name": "test_protected_runtime_dispatches_exact_data_mechanism_in_every_direction"
                            f"[{alias}-{stage}-vmware-ahv]",
                })
        return suite

    def write(self, suite: ET.Element) -> None:
        ET.ElementTree(suite).write(self.xml, encoding="unicode")

    def test_complete_executed_e2_matrix_is_qualified_without_site_authority(self):
        self.write(self.valid_suite())
        result = qualify(ROOT, self.xml)
        self.assertEqual(result["qualified_method_modes"], 30)
        self.assertEqual(result["expected_method_modes"], 30)
        self.assertEqual(result["evidence_level"], "E2")
        self.assertFalse(result["installed_provider_qualified"])
        self.assertFalse(result["native_write_authorized"])

    def test_missing_method_mode_fails_closed(self):
        suite = self.valid_suite()
        suite.remove(suite.findall("testcase")[0])
        self.write(suite)
        with self.assertRaisesRegex(ValueError, "Missing executed method/mode"):
            qualify(ROOT, self.xml)

    def test_missing_dispatch_evidence_fails_closed(self):
        suite = self.valid_suite()
        for item in suite.findall("testcase"):
            if item.get("name", "").startswith(
                "test_protected_runtime_dispatches_exact_data_mechanism"
            ):
                suite.remove(item)
                break
        self.write(suite)
        with self.assertRaisesRegex(ValueError, "dispatch lacks executed evidence"):
            qualify(ROOT, self.xml)

    def test_skipped_native_denial_fails_closed(self):
        suite = self.valid_suite()
        test = suite.findall("testcase")[-1]
        ET.SubElement(test, "skipped")
        self.write(suite)
        with self.assertRaisesRegex(ValueError, "failed/skipped"):
            qualify(ROOT, self.xml)


if __name__ == "__main__":
    unittest.main()
