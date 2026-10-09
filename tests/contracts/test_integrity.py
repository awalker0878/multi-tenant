"""Intentional negative canaries for the cross-service contract gate."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/contracts"))
from build import assemble, verify
from check import check_copies, check_routes, local_refs, unique_schema_ids

class ContractIntegrityTests(unittest.TestCase):
    def test_sources_assemble_to_current_published_bundles(self):
        sources, bundles = verify()
        self.assertGreaterEqual(sources, 6)
        self.assertGreaterEqual(bundles, 9)

    def test_active_routes_and_copies(self):
        check_routes()
        check_copies()
        self.assertGreater(unique_schema_ids(), 10)

    def test_missing_reference_is_detected(self):
        with self.assertRaisesRegex(ValueError, "Invalid"):
            local_refs({"field":{"$ref":"#/definitions/missing"}}, "negative")

    def test_crosswalk_fragments_restore_all_canonical_fields(self):
        _, result = assemble(ROOT / "contracts/source/capabilities/migration-field-crosswalk-v1/manifest.json")
        self.assertEqual(len(result["fields"]), result["summary"]["groups"])

if __name__ == "__main__":
    unittest.main()
