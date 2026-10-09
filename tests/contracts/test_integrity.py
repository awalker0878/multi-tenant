"""Intentional negative canaries for the cross-service contract gate."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/contracts"))
from build import assemble, verify
from check import check_copies, check_events, check_routes, current_api, load, local_refs, unique_schema_ids

class ContractIntegrityTests(unittest.TestCase):
    def test_sources_assemble_to_current_published_bundles(self):
        sources, bundles = verify()
        self.assertGreaterEqual(sources, 6)
        self.assertGreaterEqual(bundles, 9)

    def test_active_routes_and_copies(self):
        check_routes()
        check_copies()
        self.assertGreater(unique_schema_ids(), 10)

    def test_current_openapi_operations_and_path_parameters(self):
        for name, count in (
            ("catalogue-v1.0.1.json", 18),
            ("inventory-v1.9.json", 29),
            ("planning-migration-v1.6.json", 7),
        ):
            with self.subTest(name=name):
                paths, operations = current_api(name)
                self.assertGreater(paths, 0)
                self.assertEqual(operations, count)

    def test_missing_path_parameter_is_rejected(self):
        name = "planning-migration-v1.6.json"
        spec = load("contracts/openapi/" + name)
        path = next(iter(spec["paths"]))
        operation = spec["paths"][path]["post"]
        operation["parameters"] = [
            parameter for parameter in operation["parameters"]
            if parameter.get("name") != "tenant"
        ]
        with patch("check.load", return_value=spec):
            with self.assertRaisesRegex(ValueError, "path parameters/responses"):
                current_api(name)

    def test_asyncapi_event_schema_bindings(self):
        check_events()

    def test_missing_reference_is_detected(self):
        with self.assertRaisesRegex(ValueError, "Invalid"):
            local_refs({"field":{"$ref":"#/definitions/missing"}}, "negative")

    def test_crosswalk_fragments_restore_all_canonical_fields(self):
        _, result = assemble(ROOT / "contracts/source/capabilities/migration-field-crosswalk-v1/manifest.json")
        self.assertEqual(len(result["fields"]), result["summary"]["groups"])

if __name__ == "__main__":
    unittest.main()
