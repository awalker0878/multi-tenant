"""Independent dependency and retirement discovery bypass regressions."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/contracts"))
from discovery import canonical_dependencies, verify_dependencies, verify_manifests
from runtime_inventory import verify_runtime_inventory, discover_runtime_copies, executable_contract_loads


class IndependentDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, name, value):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value if isinstance(value, str) else json.dumps(value))
        return target

    def registry(self, dependencies):
        return {"active_releases": [{"path": path, "depends_on": edges}
                                    for path, edges in dependencies.items()]}

    def test_yaml_payload_reference_is_discovered_without_registry(self):
        schema = "contracts/schemas/events/current-v1.json"
        spec = "contracts/asyncapi/current.yaml"
        self.write(schema, {"type": "object"})
        self.write(spec, "components:\n  messages:\n    current:\n      payload:\n        schema:\n          $ref: ../schemas/events/current-v1.json\n")
        self.assertEqual(canonical_dependencies(self.root)[spec], {schema})
        with self.assertRaisesRegex(ValueError, "missing="):
            verify_dependencies(self.root, self.registry({schema: [], spec: []}))

    def test_uri_schema_reference_resolves_to_enrolled_local_canonical(self):
        source = "contracts/schemas/current-v1.json"
        target = "contracts/schemas/reference-v1.json"
        self.write(source, {"$id": "urn:current:v1", "$defs": {"Value": {"type": "string"}}})
        self.write(target, {"$ref": "urn:current:v1#/$defs/Value"})
        self.assertEqual(canonical_dependencies(self.root)[target], {source})

    def test_undeclared_remote_schema_is_not_silently_skipped(self):
        self.write("contracts/schemas/current-v1.json", {"$ref": "https://unknown.invalid/schema"})
        with self.assertRaisesRegex(ValueError, "Unresolved external"):
            canonical_dependencies(self.root)

    def test_broken_external_pointer_is_rejected(self):
        self.write("contracts/schemas/one-v1.json", {"type": "object"})
        self.write("contracts/schemas/two-v1.json", {"$ref": "one-v1.json#/$defs/Absent"})
        with self.assertRaisesRegex(ValueError, "Unresolved contract pointer"):
            canonical_dependencies(self.root)

    def test_embedded_schema_without_id_has_independent_dependency(self):
        source = "contracts/schemas/current-v1.json"
        target = "contracts/openapi/current-v1.json"
        self.write(source, {"$id": "urn:current:v1", "title": "Current", "type": "string"})
        self.write(target, {"components": {"schemas": {"Current": {"type": "string"}}}})
        self.assertEqual(canonical_dependencies(self.root)[target], {source})

    def test_phantom_dependency_is_rejected(self):
        one, two = "contracts/schemas/one-v1.json", "contracts/schemas/two-v1.json"
        self.write(one, {"type": "object"})
        self.write(two, {"type": "string"})
        with self.assertRaisesRegex(ValueError, "orphaned="):
            verify_dependencies(self.root, self.registry({one: [two], two: []}))

    def test_duplicate_dependency_is_rejected(self):
        one, two = "contracts/schemas/one-v1.json", "contracts/schemas/two-v1.json"
        self.write(one, {"$ref": "two-v1.json"})
        self.write(two, {"type": "object"})
        with self.assertRaisesRegex(ValueError, "Duplicate or invalid"):
            verify_dependencies(self.root, self.registry({one: [two, two], two: []}))

    def test_cross_release_cycle_rejected_local_recursive_schema_allowed(self):
        one, two = "contracts/schemas/one-v1.json", "contracts/schemas/two-v1.json"
        self.write(one, {"$ref": "two-v1.json"})
        self.write(two, {"$ref": "one-v1.json"})
        with self.assertRaisesRegex(ValueError, "Circular canonical"):
            verify_dependencies(self.root, self.registry({one: [two], two: [one]}))
        self.write(two, {"$defs": {"Item": {"type": "object", "properties": {"child": {"$ref": "#/$defs/Item"}}}}})
        self.assertEqual(verify_dependencies(self.root, self.registry({one: [two], two: []}))[two], set())

    def test_missing_copy_and_declaration_do_not_hide_executable_loader(self):
        self.write("services/demo/src/demo/infrastructure/loader.py",
                   'def load():\n    return files("demo.infrastructure.inputs").joinpath("current-v1.json").read_text()\n')
        with self.assertRaisesRegex(ValueError, "Undeclared executable contract loader"):
            verify_runtime_inventory({"active_releases": []}, self.root)

    def test_nested_unregistered_installed_copy_is_rejected(self):
        self.write("services/demo/resources/contracts/hidden/current-v1.json", {})
        with self.assertRaisesRegex(ValueError, "Shipped contract copies missing"):
            verify_runtime_inventory({"active_releases": []}, self.root)

    def test_undeclared_schema_in_unknown_package_namespace_is_rejected(self):
        self.write("services/demo/src/demo/domain/private/current.json", {"$schema": "https://json-schema.org/draft/2020-12/schema"})
        with self.assertRaisesRegex(ValueError, "Shipped contract copies missing"):
            verify_runtime_inventory({"active_releases": []}, self.root)

    def test_dynamic_immutable_filename_map_discovers_both_fact_loaders(self):
        source = self.write("services/demo/src/demo/infrastructure/facts/broker.py",
                            'from types import MappingProxyType\nFILES = MappingProxyType({"one": "one.json", "two": "two.json"})\n'
                            'def load(owner):\n    return files(__package__).joinpath(FILES[owner]).read_text()\n')
        for name in ("one", "two"):
            self.write(f"services/demo/src/demo/infrastructure/facts/{name}.json", {"type": "object"})
        self.assertEqual(executable_contract_loads(source), {"one.json", "two.json"})
        self.assertEqual(len(discover_runtime_copies(self.root)), 2)
        with self.assertRaisesRegex(ValueError, "Shipped contract copies missing"):
            verify_runtime_inventory({"active_releases": []}, self.root)

    def test_source_manifest_cannot_be_orphaned_or_undeclared(self):
        canonical = "contracts/schemas/current-v1.json"
        manifest = "contracts/source/current/manifest.json"
        self.write(canonical, {"type": "object"})
        self.write("contracts/source/current/base.json", {"type": "object"})
        self.write(manifest, {"schema_version": 1, "target": canonical, "base": "base.json", "parts": {}, "copies": []})
        with self.assertRaisesRegex(ValueError, "undeclared source manifest"):
            verify_manifests(self.root, self.registry({canonical: []}))
        registry = {"active_releases": [{"path": canonical, "source_manifest": manifest, "copies": []}]}
        self.assertIn(canonical, verify_manifests(self.root, registry))
        self.write("contracts/source/current/unused.json", {})
        with self.assertRaisesRegex(ValueError, "Orphaned contract source fragments"):
            verify_manifests(self.root, registry)

    def test_new_deployable_context_requires_artifact_ownership_and_ci(self):
        from artifact_attestation import COMPONENTS
        from runtime_binding_coverage import verify_deployable_inventory
        for component in COMPONENTS:
            self.write(component + "/Dockerfile", "FROM scratch\n")
        verify_deployable_inventory(self.root)
        self.write("services/undeclared/Dockerfile", "FROM scratch\n")
        with self.assertRaisesRegex(ValueError, "Deployable components"):
            verify_deployable_inventory(self.root)


if __name__ == "__main__":
    unittest.main()
