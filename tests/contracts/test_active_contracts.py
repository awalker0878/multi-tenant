"""Current-phase assurance acceptance across the entire active contract inventory."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/contracts"))
from assurance import inventory, assess


class ActiveReleaseAcceptance(unittest.TestCase):
    def test_active_registry_has_complete_unqualified_by_default_assurance_inventory(self):
        registry = json.loads((ROOT / "architecture/contract-consumers.json").read_text())
        actual = inventory(ROOT)
        self.assertEqual(
            {entry["path"] for entry in actual["releases"]},
            {entry["path"] for entry in registry["active_releases"]},
        )
        expected_operations = 0
        for entry in registry["active_releases"]:
            if not entry["path"].startswith("contracts/openapi/"):
                continue
            spec = json.loads((ROOT / entry["path"]).read_text())
            expected_operations += sum(
                verb in {"get", "post", "put", "patch", "delete"}
                for operations in spec["paths"].values() for verb in operations
            )
        self.assertEqual(len(actual["operations"]), expected_operations)
        no_evidence = assess(ROOT)
        self.assertEqual(no_evidence["summary"]["qualified_http_operations"], 0)
        self.assertEqual(no_evidence["summary"]["qualified_canonical_releases"], 0)

    def test_current_source_generated_authority_releases_are_byte_semantically_equal(self):
        from generate_authority_releases import verify
        self.assertEqual(verify(ROOT), 3)

    def test_root_level_passthrough_field_matches_current_published_crosswalk_schema(self):
        from jsonschema import Draft202012Validator
        schema = json.loads((ROOT / (
            "contracts/schemas/capabilities/migration-field-crosswalk-v1.json"
        )).read_text())
        crosswalk = json.loads((ROOT / (
            "contracts/capabilities/migration-field-crosswalk-v1.json"
        )).read_text())
        Draft202012Validator.check_schema(schema)
        self.assertFalse(list(Draft202012Validator(schema).iter_errors(crosswalk)))
        self.assertIn("source.passthrough", {field["canonical_id"]
                                            for field in crosswalk["fields"]})


if __name__ == "__main__":
    unittest.main()
