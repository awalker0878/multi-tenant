"""Intentional negative canaries for the cross-service contract gate."""
from pathlib import Path
import json
import tempfile
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/contracts"))
from build import assemble, verify
from check import (
    check_consumer_registry, check_copies, check_events, check_readiness_projection,
    check_routes, check_schema_dialects, current_api, load, local_refs,
    unique_schema_ids,
)

class ContractIntegrityTests(unittest.TestCase):
    def test_sources_assemble_to_current_published_bundles(self):
        sources, bundles = verify()
        self.assertGreaterEqual(sources, 6)
        self.assertGreaterEqual(bundles, 9)

    def test_published_bundle_cannot_be_rewritten_by_source_builder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "contracts/source/example-v1"
            source.mkdir(parents=True)
            (source / "base.json").write_text('{"title": "immutable"}')
            (source / "properties.json").write_text('{"name": {"type": "string"}}')
            (source / "manifest.json").write_text(json.dumps({
                "schema_version": 1,
                "target": "contracts/schemas/example-v1.json",
                "base": "base.json",
                "parts": {"properties": {
                    "kind": "object", "files": ["properties.json"],
                }},
                "copies": ["apps/example/resources/contracts/example-v1.json"],
            }))
            target = root / "contracts/schemas/example-v1.json"
            target.parent.mkdir(parents=True)
            original = '{"title":"immutable","properties":{"name":{"type":"string"}}}\n'
            target.write_text(original)
            with patch("build.ROOT", root), patch("build.SOURCE", root / "contracts/source"):
                verify(write=True)
                consumer = root / "apps/example/resources/contracts/example-v1.json"
                self.assertEqual(target.read_text(), original)
                self.assertEqual(consumer.read_bytes(), target.read_bytes())
                (source / "properties.json").write_text('{"name": {"type": "integer"}}')
                with self.assertRaisesRegex(ValueError, "Published contract requires a new version"):
                    verify(write=True)
                self.assertEqual(target.read_text(), original)

    def test_active_routes_and_copies(self):
        check_routes()
        check_copies()
        self.assertGreater(unique_schema_ids(), 10)

    def test_all_declared_active_openapi_versions(self):
        from check import current_api
        releases = load("architecture/contract-consumers.json")["active_releases"]
        for entry in releases:
            if entry["path"].startswith("contracts/openapi/"):
                with self.subTest(contract=entry["path"]):
                    self.assertGreater(current_api(entry["path"].split("/")[-1])[1], 0)

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
            with self.assertRaisesRegex(ValueError, "operation parameters/responses"):
                current_api(name)

    def test_asyncapi_event_schema_bindings(self):
        check_events()

    def test_all_schema_dialects_and_active_projections(self):
        self.assertGreaterEqual(check_schema_dialects(), 40)
        check_readiness_projection()
        check_consumer_registry()

    def test_new_schema_without_unique_identifier_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            schema_dir = root / "contracts/schemas/new"
            schema_dir.mkdir(parents=True)
            (schema_dir / "readiness-v99.json").write_text(json.dumps({
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
            }))
            with patch("check.ROOT", root):
                with self.assertRaisesRegex(ValueError, "Schema identity required"):
                    check_schema_dialects()

    def test_missing_reference_is_detected(self):
        with self.assertRaisesRegex(ValueError, "Invalid"):
            local_refs({"field":{"$ref":"#/definitions/missing"}}, "negative")

    def test_crosswalk_fragments_restore_all_canonical_fields(self):
        _, result = assemble(ROOT / "contracts/source/capabilities/migration-field-crosswalk-v1/manifest.json")
        self.assertEqual(len(result["fields"]), result["summary"]["groups"])

if __name__ == "__main__":
    unittest.main()

    def test_e4_field_provenance_requires_exact_independent_binding(self):
        from jsonschema import Draft202012Validator, FormatChecker

        schema = load("contracts/schemas/planning/independent-e4-field-provenance-v1.json")
        validate = Draft202012Validator(schema, format_checker=FormatChecker())
        uid = "10000000-0000-4000-8000-000000000001"
        proof = {
            "schema_version": 1, "kind": "independent_e4_field_provenance",
            "tenant_id": uid, "application_id": uid, "environment_id": uid,
            "catalogue_revision_id": uid, "catalogue_sha256": "a" * 64,
            "workload_id": uid, "field": "guest.firmware",
            "source_profile_sha256": "b" * 64,
            "intent_field_sha256": "c" * 64, "observed_field_sha256": "d" * 64,
            "disposition": "qualified_transformation", "level": "E4",
            "decision": "accepted", "revoked": False, "evidence_sha256": "e" * 64,
            "transformation_plan_sha256": "f" * 64,
            "independent_acceptance_sha256": "0" * 64,
            "observed_at": 100, "expires_at": 120,
        }
        self.assertTrue(validate.is_valid(proof))
        self.assertFalse(validate.is_valid({**proof, "revoked": True}))
        self.assertFalse(validate.is_valid({**proof, "level": "E2"}))
        self.assertFalse(validate.is_valid({**proof, "transformation_plan_sha256": "bad"}))
