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
from check_schema import (
    check_readiness_projection,
    check_schema_dialects, current_api, load, local_refs, unique_schema_ids,
)
from check_events import check_events
from check_registry import check_consumer_registry
from check_http import check_error_policy

class ContractIntegrityTests(unittest.TestCase):
    def test_only_registered_active_canonical_releases_are_shipped(self):
        active = {row["path"] for row in load("architecture/contract-consumers.json")["active_releases"]}
        files = {
            str(path.relative_to(ROOT))
            for area in ("openapi", "schemas", "capabilities", "platforms", "asyncapi")
            for pattern in ("*.json", "*.yaml", "*.yml")
            for path in (ROOT / "contracts" / area).rglob(pattern)
        }
        self.assertEqual(files, active)

    def test_owner_operation_regex_widening_is_rejected(self):
        import runpy
        from check_registry import check_owner_operation_bindings
        source = ROOT / "services/planning/src/planning/infrastructure/owner_contracts.py"
        operations = list(runpy.run_path(str(source))["OWNER_OPERATIONS"])
        owner, verb, _, schema = operations[1]
        operations[1] = (owner, verb, r"/internal/tenants/.+/placement-reservations/checks", schema)
        with patch("runpy.run_path", return_value={"OWNER_OPERATIONS": tuple(operations)}):
            with self.assertRaisesRegex(ValueError, "Runtime owner-operation routing drift"):
                check_owner_operation_bindings()

    def test_catalogue_embedded_schema_references_rebase_to_active_release(self):
        canonical = load("contracts/openapi/catalogue-internal-v1.json")
        local_refs(canonical, "catalogue-internal-v1.json")
        broken = json.loads(json.dumps(canonical))
        broken["components"]["schemas"]["CurrentPlanningIntent"]["properties"]["intent"]["$ref"] = "#/$defs/Intent"
        with self.assertRaisesRegex(ValueError, "Invalid catalogue-internal-v1.json local"):
            local_refs(broken, "catalogue-internal-v1.json")

    def test_new_authority_releases_use_common_error(self):
        check_error_policy()
        from check_http import check_error_policy as check
        from check_schema import load as real_load
        original = real_load("contracts/openapi/assurance-qualification-v2.json")
        altered = json.loads(json.dumps(original))
        altered["paths"]["/internal/tenants/{tenant}/qualification-publications"]["post"]["responses"]["409"].pop("content")
        with patch("check_http.load", side_effect=lambda path: altered if path == "contracts/openapi/assurance-qualification-v2.json" else real_load(path)):
            with self.assertRaisesRegex(ValueError, "Owner error body not contracted"):
                check()

    def test_delegate_headers_and_native_digest_conflict_are_part_of_owner_contracts(self):
        from check_http import check_implemented_api_contracts
        check_implemented_api_contracts()
        source = load("contracts/openapi/governance-service-checks-v1.json")
        source["paths"]["/v1/tenants/{tenant}/planning-input-checks"]["post"]["parameters"] = [
            p for p in source["paths"]["/v1/tenants/{tenant}/planning-input-checks"]["post"]["parameters"]
            if p["in"] != "header"
        ]
        original = load
        with patch("check_http.load", side_effect=lambda name:
                   source if name == "contracts/openapi/governance-service-checks-v1.json"
                   else original(name)):
            with self.assertRaisesRegex(ValueError, "Missing delegated authority header"):
                check_implemented_api_contracts()

    def test_owner_release_components_are_rebuilt_from_source_contracts(self):
        from generate_authority_releases import verify as verify_authority, assemble
        self.assertEqual(verify_authority(), 5)
        generated = assemble("inventory-native-input-v1.3.json")
        modified = load("contracts/openapi/inventory-native-input-v1.3.json")
        modified["components"]["schemas"]["CapabilityInput"]["properties"].pop("capability_snapshot")
        self.assertNotEqual(generated, modified)

    def test_current_uuid_policy_rejects_noncanonical_new_routes_without_legacy_allowlist(self):
        from check_http import check_uuid_policy
        self.assertEqual(check_uuid_policy(), 0)
        self.assertFalse((ROOT / "scripts/contracts/uuid-legacy-v1.json").exists())
        original = load
        api = load("contracts/openapi/inventory-collection-worker-v1.json")
        api["paths"]["/internal/collections/receipts"]["post"]["requestBody"][
            "content"]["application/json"]["schema"]["properties"]["tenant_id"][
                "pattern"] = r"^[0-9a-f-]{36}$"
        with patch("check_http.load", side_effect=lambda path:
                   api if path == "contracts/openapi/inventory-collection-worker-v1.json"
                   else original(path)):
            with self.assertRaisesRegex(ValueError, "Noncanonical UUID"):
                check_uuid_policy()

    def test_retired_internal_planning_input_alias_is_not_published(self):
        registry = load("architecture/contract-consumers.json")
        self.assertNotIn(
            "/internal/tenants/{tenant}/planning-inputs/{application}/{environment}/{site}/{endpoint}/{generation}",
            load("contracts/openapi/inventory-native-input-v1.3.json")["paths"],
        )
        self.assertNotIn("scripts/contracts/uuid-legacy-v1.json", registry["contracts"])

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

    def test_active_schema_identifiers_and_full_installed_inventory(self):
        self.assertGreater(unique_schema_ids(), 10)
        check_consumer_registry()

    def test_all_declared_active_openapi_versions(self):
        from check_schema import current_api
        releases = load("architecture/contract-consumers.json")["active_releases"]
        for entry in releases:
            if entry["path"].startswith("contracts/openapi/"):
                with self.subTest(contract=entry["path"]):
                    self.assertGreater(current_api(entry["path"].split("/")[-1])[1], 0)

    def test_current_openapi_operations_and_path_parameters(self):
        for name, count in (
            ("catalogue-v1.0.1.json", 18),
            ("inventory-v1.9.json", 29),
            ("planning-migration-v2.json", 7),
        ):
            with self.subTest(name=name):
                paths, operations = current_api(name)
                self.assertGreater(paths, 0)
                self.assertEqual(operations, count)

    def test_missing_path_parameter_is_rejected(self):
        name = "planning-migration-v2.json"
        spec = load("contracts/openapi/" + name)
        path = next(iter(spec["paths"]))
        operation = spec["paths"][path]["post"]
        operation["parameters"] = [
            parameter for parameter in operation["parameters"]
            if parameter.get("name") != "tenant"
        ]
        with patch("check_schema.load", return_value=spec):
            with self.assertRaisesRegex(ValueError, "operation parameters/responses"):
                current_api(name)

    def test_asyncapi_event_schema_bindings(self):
        check_events()

    def test_all_schema_dialects_and_active_projections(self):
        self.assertEqual(check_schema_dialects(), len(list((ROOT / "contracts/schemas").rglob("*.json"))))
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
            with patch("check_schema.ROOT", root):
                with self.assertRaisesRegex(ValueError, "Schema identity required"):
                    check_schema_dialects()

    def test_declared_active_contract_omission_is_detected(self):
        registry = load("architecture/contract-consumers.json")
        registry["active_releases"].pop()
        original = load
        with patch("check_registry.load", side_effect=lambda name:
                   registry if name == "architecture/contract-consumers.json"
                   else original(name)):
            with self.assertRaisesRegex(ValueError, "does not cover every declared"):
                check_consumer_registry()

    def test_asyncapi_operation_without_a_declared_channel_is_rejected(self):
        from check_events import check_events

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            api = root / "contracts/asyncapi"
            api.mkdir(parents=True)
            (api / "broken.yaml").write_text("""
asyncapi: 3.0.0
info:
  title: Synthetic broken operation
  version: 1.0.0
channels:
  present:
    address: present.event.v1
    messages:
      recorded:
        $ref: '#/components/messages/Recorded'
operations:
  publish:
    action: send
    channel:
      $ref: '#/channels/absent'
components:
  messages:
    Recorded:
      contentType: application/json
      payload:
        schemaFormat: application/schema+json;version=draft-2020-12
        schema:
          $ref: ../schemas/events/recorded.json
""")
            with patch("check_events.ROOT", root):
                with self.assertRaisesRegex(ValueError, "Invalid"):
                    check_events()

    def test_missing_reference_is_detected(self):
        with self.assertRaisesRegex(ValueError, "Invalid"):
            local_refs({"field":{"$ref":"#/definitions/missing"}}, "negative")

    def test_asyncapi_cannot_disappear_from_both_registries(self):
        registry = load("architecture/contract-consumers.json")
        missing = "contracts/asyncapi/identity.yaml"
        registry["contracts"].pop(missing)
        registry["active_releases"] = [
            entry for entry in registry["active_releases"] if entry["path"] != missing
        ]
        original = load
        with patch("check_registry.load", side_effect=lambda name:
                   registry if name == "architecture/contract-consumers.json"
                   else original(name)):
            with self.assertRaisesRegex(ValueError, "Deployed AsyncAPI missing"):
                check_consumer_registry()

    def test_planning_lifecycle_contract_is_required_and_derived_from_producer(self):
        from check_http import check_implemented_api_contracts
        check_implemented_api_contracts()
        registry = load("architecture/contract-consumers.json")
        path = "contracts/openapi/planning-lifecycle-reads-v1.json"
        registry["contracts"].pop(path)
        registry["active_releases"] = [
            row for row in registry["active_releases"] if row["path"] != path
        ]
        original = load
        with patch("check_http.load", side_effect=lambda name:
                   registry if name == "architecture/contract-consumers.json"
                   else original(name)):
            with self.assertRaisesRegex(ValueError, "Implemented OpenAPI release not registered"):
                check_implemented_api_contracts()

    def test_implemented_openapi_release_and_v4_response_parity(self):
        from check_http import check_implemented_api_contracts
        check_implemented_api_contracts()

    def test_implemented_api_cannot_be_removed_from_both_registry_maps(self):
        from check_http import check_implemented_api_contracts
        registry = load("architecture/contract-consumers.json")
        missing = "contracts/openapi/assurance-evidence-v1.json"
        registry["contracts"].pop(missing)
        registry["active_releases"] = [
            row for row in registry["active_releases"] if row["path"] != missing
        ]
        original = load
        with patch("check_http.load", side_effect=lambda name:
                   registry if name == "architecture/contract-consumers.json"
                   else original(name)):
            with self.assertRaisesRegex(ValueError, "Implemented OpenAPI release not registered"):
                check_implemented_api_contracts()

    def test_native_input_api_response_drift_is_detected(self):
        from check_http import check_implemented_api_contracts
        original = load
        path = "contracts/openapi/inventory-native-input-v1.3.json"
        broken = original(path)
        endpoint = next(iter(broken["paths"].values()))["get"]
        envelope = broken["components"]["schemas"]["MigrationInput"]
        envelope["properties"].pop("collection_coverages")
        with patch("check_http.load", side_effect=lambda name:
                   broken if name == path else original(name)):
            with self.assertRaisesRegex(ValueError, "producer/consumer v4 schema mismatch"):
                check_implemented_api_contracts()

    def test_embedded_owner_schema_must_match_canonical_and_installed(self):
        from check_http import check_implemented_api_contracts
        original = load
        path = "contracts/openapi/inventory-native-input-v1.3.json"
        changed = load(path)
        changed["components"]["schemas"]["CapabilityInput"]["properties"].pop("capability_snapshot")
        with patch("check_http.load", side_effect=lambda name:
                   changed if name == path else original(name)):
            with self.assertRaisesRegex(ValueError, "Inventory native CapabilityInput"):
                check_implemented_api_contracts()

    def test_all_dynamic_owner_operations_resolve_to_active_copies(self):
        from check_registry import check_owner_operation_bindings
        check_owner_operation_bindings()

    def test_removing_dynamic_owner_contract_from_both_maps_fails(self):
        from check_registry import check_owner_operation_bindings
        registry = load("architecture/contract-consumers.json")
        source = "contracts/schemas/planning/catalogue-current-v2.json"
        registry["contracts"].pop(source)
        registry["active_releases"] = [
            entry for entry in registry["active_releases"] if entry["path"] != source
        ]
        original = load
        with patch("check_registry.load", side_effect=lambda name:
                   registry if name == "architecture/contract-consumers.json"
                   else original(name)):
            with self.assertRaisesRegex(ValueError, "owner-operation contract missing"):
                check_owner_operation_bindings()

    def test_catalogue_current_projection_cannot_diverge_from_source_intent(self):
        from check_registry import check_owner_operation_bindings
        original = load
        bad = load("contracts/schemas/planning/catalogue-current-v2.json")
        bad["$defs"]["Intent"]["properties"]["workloads"] = {"type": "string"}
        with patch("check_registry.load", side_effect=lambda name:
                   bad if name == "contracts/schemas/planning/catalogue-current-v2.json"
                   else original(name)):
            with self.assertRaisesRegex(ValueError, "intent projection differs"):
                check_owner_operation_bindings()

    def test_planning_event_copy_is_in_runtime_coverage(self):
        from runtime_inventory import discover_runtime_copies
        observed = discover_runtime_copies()
        self.assertIn(
            "services/planning/src/planning/infrastructure/messaging/foundation-event.json",
            observed,
        )

    def test_runtime_copies_cannot_disappear_from_both_registries(self):
        from runtime_inventory import verify_runtime_inventory
        registry = load("architecture/contract-consumers.json")
        source = "contracts/schemas/events/identity-change-v1.json"
        registry["contracts"].pop(source)
        registry["active_releases"] = [
            entry for entry in registry["active_releases"] if entry["path"] != source
        ]
        with self.assertRaisesRegex(ValueError, "Shipped contract copies missing"):
            verify_runtime_inventory(registry)

    def test_unreferenced_packaged_contract_is_rejected(self):
        from runtime_inventory import verify_runtime_inventory
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "apps/demo/resources/contracts/retired-v1.json"
            package.parent.mkdir(parents=True)
            package.write_text("{}")
            with self.assertRaisesRegex(ValueError, "Shipped contract copies missing"):
                verify_runtime_inventory({"active_releases": []}, root)

    def test_installed_copy_ledger_requires_real_loader_and_packaging(self):
        from installed_usage import verify_installed_usage
        reg = load("architecture/contract-consumers.json")
        active_installed = sum(len(release.get("copies", []))
                               for release in reg["active_releases"])
        self.assertEqual(verify_installed_usage(ROOT, reg), active_installed)
        source = load("architecture/installed-contract-usage.json")
        changed = json.loads(json.dumps(source))
        changed["copies"][0]["loader"] = "apps/console/app/Nonexistent.php"
        with patch("installed_usage.json.loads", return_value=changed):
            with self.assertRaisesRegex(ValueError, "loader outside bounded component"):
                verify_installed_usage(ROOT, reg)
        changed = json.loads(json.dumps(source))
        changed["copies"][0]["packaging_marker"] = "COPY nothing-and-never-check-it"
        with patch("installed_usage.json.loads", return_value=changed):
            with self.assertRaisesRegex(ValueError, "not included in runtime image"):
                verify_installed_usage(ROOT, reg)
        changed = json.loads(json.dumps(source))
        changed["copies"] = changed["copies"][:-1]
        with patch("installed_usage.json.loads", return_value=changed):
            with self.assertRaisesRegex(ValueError, "does not cover active installed copies"):
                verify_installed_usage(ROOT, reg)

    def test_registered_but_unused_package_fails(self):
        from runtime_inventory import verify_runtime_inventory
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = root / "contracts/openapi/demo-v1.json"
            consumer = root / "apps/demo/resources/contracts/demo-v1.json"
            canonical.parent.mkdir(parents=True)
            consumer.parent.mkdir(parents=True)
            canonical.write_text("{}")
            consumer.write_text("{}")
            registry = {"active_releases": [{
                "path": "contracts/openapi/demo-v1.json",
                "copies": ["apps/demo/resources/contracts/demo-v1.json"],
            }]}
            with self.assertRaisesRegex(ValueError, "no executable consumer"):
                verify_runtime_inventory(registry, root)

    def test_native_api_cannot_double_claim_endpoint_across_owner_names(self):
        from check_registry import check_consumer_registry
        from check_schema import load as original
        path = "contracts/openapi/worker-migration-method-v2.json"
        altered = json.loads(json.dumps(original(path)))
        altered["paths"]["/internal/native-effects"] = {
            "post": {"responses": {"200": {"description": "duplicate"}}}
        }
        with patch("check_registry.load", side_effect=lambda name:
                   altered if name == path else original(name)):
            with self.assertRaisesRegex(ValueError, "Overlapping native wire operation"):
                check_consumer_registry()

    def test_runtime_discovery_is_bounded_to_own_product(self):
        from runtime_inventory import discover_runtime_copies
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src = root / "services/alpha/app/Infrastructure/EventEncoder.php"
            src.parent.mkdir(parents=True)
            src.write_text("<?php file_get_contents(resource_path('contracts/example-v1.json'));")
            copy = root / "services/alpha/resources/contracts/example-v1.json"
            copy.parent.mkdir(parents=True)
            copy.write_text("{}")
            other = root / "services/beta/resources/contracts/example-v1.json"
            other.parent.mkdir(parents=True)
            other.write_text("{}")
            observed = discover_runtime_copies(root)
            self.assertIn(str(copy.relative_to(root)), observed)
            self.assertNotIn(str(other.relative_to(root)), observed)

    def test_literal_filename_without_executable_loader_does_not_count(self):
        from runtime_inventory import verify_runtime_inventory
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = root / "contracts/openapi/demo-v1.json"
            copy = root / "apps/demo/resources/contracts/demo-v1.json"
            code = root / "apps/demo/app/Demo.php"
            for file in (canonical, copy, code):
                file.parent.mkdir(parents=True, exist_ok=True)
            canonical.write_text("{}")
            copy.write_text("{}")
            code.write_text("<?php // file_get_contents(resource_path('contracts/demo-v1.json'));")
            registry = {"active_releases": [{
                "path": "contracts/openapi/demo-v1.json",
                "copies": ["apps/demo/resources/contracts/demo-v1.json"],
            }]}
            with self.assertRaisesRegex(ValueError, "no executable consumer"):
                verify_runtime_inventory(registry, root)

    def test_channel_specific_discriminator_rejects_other_valid_event_type(self):
        from check_events import event_discriminator
        from jsonschema import Draft202012Validator
        schema = {
            "type": "object",
            "required": ["event_type"],
            "properties": {
                "event_type": {"enum": ["identity.login.denied", "identity.session.revoked"]}
            },
        }
        profile = event_discriminator(schema, "identity.login.denied.v1", "identity.yaml")
        validator = Draft202012Validator(profile)
        self.assertTrue(validator.is_valid({"event_type": "identity.login.denied"}))
        self.assertFalse(validator.is_valid({"event_type": "identity.session.revoked"}))
        with self.assertRaisesRegex(ValueError, "no event_type binding"):
            event_discriminator(schema, "identity.undeclared.v1", "identity.yaml")

    def test_manifest_cannot_escape_source_or_deployment_roots(self):
        from build import safe_destination, safe_source_file
        with self.assertRaisesRegex(ValueError, "Unsafe contract source"):
            safe_source_file(ROOT / "contracts/source", "../secret.json")
        with self.assertRaisesRegex(ValueError, "Unsafe contract destination"):
            safe_destination("contracts/schemas/../../secrets.json", canonical=True)
        with self.assertRaisesRegex(ValueError, "Unapproved contract destination"):
            safe_destination("services/planning/composer.json", canonical=False)
        with self.assertRaisesRegex(ValueError, "Unapproved contract destination"):
            safe_destination("contracts/source/manifest.json", canonical=True)

    def test_crosswalk_fragments_restore_all_canonical_fields(self):
        _, result = assemble(ROOT / "contracts/source/capabilities/migration-field-crosswalk-v1/manifest.json")
        self.assertEqual(len(result["fields"]), result["summary"]["groups"])


if __name__ == "__main__":
    unittest.main()
