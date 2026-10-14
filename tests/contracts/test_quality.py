"""Regression matrix for strict new contract quality and semantic version admission."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/contracts"))
from quality import (
    quality_api, quality_schema, quality_event,
    api_breakages, schema_breakages, event_breakages, check_new_releases,
    quality_catalogue, declaration_breakages,
)

POLICY = json.loads((ROOT / "architecture/contract-quality-policy.json").read_text())
ERROR = json.loads((ROOT / POLICY["error_schema"]).read_text())


def response(schema=None):
    return {"description": "Expected response", **({
        "content": {"application/json": {"schema": schema}}
    } if schema else {})}


def good_api():
    api_error = {k: copy.deepcopy(v) for k, v in ERROR.items() if k not in ("$id", "$schema")}
    operation = {
        "operationId": "createThing",
        "security": [{"Caller": []}],
        "parameters": [{"name": "Idempotency-Key", "in": "header",
                        "required": True, "schema": {"type": "string", "minLength": 24, "maxLength": 128}}],
        "requestBody": {"required": True, "content": {
            "application/json": {"schema": {
                "type": "object", "additionalProperties": False,
                "properties": {"name": {"type": "string"}},
                "required": ["name"]
            }}
        }},
        "x-idempotency": {
            "scope": POLICY["idempotency_scope"], "ttl_seconds": 3600,
            "conflict_status": 409
        },
        "responses": {
            "201": response({"type": "object", "additionalProperties": False,
                             "required": ["id"], "properties": {"id": {"type": "string"}}}),
            **{status: response({"$ref": "#/components/schemas/Error"})
               for status in ("401", "403", "409", "422", "503")}
        },
    }
    return {
        "openapi": "3.1.0",
        "info": {"title": "Example API", "version": "2.0.0"},
        "security": [{"Caller": []}],
        "components": {"schemas": {"Error": api_error},
                       "securitySchemes": {"Caller": {"type": "http", "scheme": "bearer"}}},
        "paths": {"/v2/things": {"post": operation}}
    }


class HttpQualityTests(unittest.TestCase):
    def test_strict_current_profile_is_admissible(self):
        quality_api("contracts/openapi/things-v2.json", good_api(), ERROR, POLICY)

    def test_unknown_security_and_anonymous_alternatives_denied(self):
        for bad in ([], [{}], [{"Missing": []}]):
            api = good_api()
            api["paths"]["/v2/things"]["post"]["security"] = bad
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "Security requirements|Undefined security"):
                quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)

    def test_all_current_explicit_error_codes_and_payload_required(self):
        for status in ("401", "403", "409", "422", "503"):
            api = good_api()
            del api["paths"]["/v2/things"]["post"]["responses"][status]
            with self.subTest(status=status), self.assertRaisesRegex(ValueError, "response missing"):
                quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)
        api = good_api()
        api["components"]["schemas"]["Error"]["required"].remove("correlation_id")
        with self.assertRaisesRegex(ValueError, "Error v2"):
            quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)

    def test_mutations_fail_without_exact_idempotency(self):
        for change in ("header", "scope", "ttl"):
            api = good_api()
            op = api["paths"]["/v2/things"]["post"]
            if change == "header":
                op["parameters"] = []
            if change == "scope":
                op["x-idempotency"]["scope"] = ["actor_id"]
            if change == "ttl":
                op["x-idempotency"]["ttl_seconds"] = True
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "Idempotency|idempotency"):
                quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)

    def test_every_declared_http_failure_uses_the_standard_error_envelope(self):
        api = good_api()
        op = api["paths"]["/v2/things"]["post"]
        op["responses"]["404"] = response({"type": "object"})
        with self.assertRaisesRegex(ValueError, "Declared HTTP error body"):
            quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)
        op["responses"]["404"] = response({"$ref": "#/components/schemas/Error"})
        quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)
        # No response body is a distinct wire guarantee; do not pretend the
        # current owner/framework necessarily emits the Error v2 JSON body.
        op["responses"]["404"] = {"description": "Not found, no body guaranteed"}
        quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)

    def test_default_response_cannot_mask_unmodelled_failures(self):
        api = good_api()
        op = api["paths"]["/v2/things"]["post"]
        op["responses"]["default"] = response({"type": "object"})
        with self.assertRaisesRegex(ValueError, "explicit HTTP status"):
            quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)

    def test_operation_ids_must_exist_and_be_unique(self):
        for missing in (None, ""):
            api = good_api()
            api["paths"]["/v2/things"]["post"]["operationId"] = missing
            with self.assertRaisesRegex(ValueError, "operationId"):
                quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)
        api = good_api()
        api["paths"]["/v2/other"] = copy.deepcopy(api["paths"]["/v2/things"])
        with self.assertRaisesRegex(ValueError, "operationId"):
            quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)

    def test_path_variables_need_unique_required_typed_bindings(self):
        api = good_api()
        api["paths"]["/v2/things/{tenant}"] = api["paths"].pop("/v2/things")
        op = api["paths"]["/v2/things/{tenant}"]["post"]
        with self.assertRaisesRegex(ValueError, "path parameter"):
            quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)
        op["parameters"].append({
            "name": "tenant", "in": "path", "required": True,
            "schema": {"type": "string", "format": "uuid"},
        })
        quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)
        # Path revisions in actual Planning interfaces are bounded integers;
        # URL encoding does not turn their declared wire type into a string.
        integer_path = copy.deepcopy(api)
        integer_path["paths"]["/v2/things/{tenant}"]["post"]["parameters"][-1]["schema"] = {
            "type": "integer", "minimum": 1,
        }
        quality_api("contracts/openapi/things-v2.json", integer_path, ERROR, POLICY)
        for mutation in ("optional", "untyped", "extraneous"):
            invalid = copy.deepcopy(api)
            route = invalid["paths"]["/v2/things/{tenant}"]["post"]
            if mutation == "optional":
                route["parameters"][-1]["required"] = False
            elif mutation == "untyped":
                route["parameters"][-1]["schema"] = {}
            else:
                route["parameters"].append({
                    "name": "plan", "in": "path", "required": True,
                    "schema": {"type": "string"},
                })
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, "path parameter"):
                quality_api("contracts/openapi/things-v2.json", invalid, ERROR, POLICY)

    def test_empty_new_api_cannot_pass_release_admission(self):
        api = good_api()
        api["paths"] = {}
        with self.assertRaisesRegex(ValueError, "executable HTTP operations"):
            quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)

    def test_enum_and_const_compatibility_preserves_json_value_types(self):
        for prior, changed in [
            ({"enum": [1]}, {"enum": ["1"]}),
            ({"enum": [True]}, {"enum": [1]}),
            ({"const": None}, {}),
            ({"const": 1}, {"const": True}),
        ]:
            with self.subTest(prior=prior, changed=changed):
                issues = schema_breakages(prior, changed, "wire")
                self.assertTrue(issues, "a type-changing semantic release needs a new major")

    def test_non_json_requests_cannot_bypass_body_validation(self):
        api = good_api()
        operation = api["paths"]["/v2/things"]["post"]
        operation["requestBody"] = {"required": True, "content": {
            "text/plain": {"schema": {"type": "string", "minLength": 1}}
        }}
        del operation["responses"]["422"]
        with self.assertRaisesRegex(ValueError, "response missing"):
            quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)
        operation["responses"]["422"] = response({"$ref": "#/components/schemas/Error"})
        quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)
        operation["requestBody"]["content"]["text/plain"] = {}
        with self.assertRaisesRegex(ValueError, "lacks a schema"):
            quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)

    def test_request_must_be_structurally_strict(self):
        api = good_api()
        del api["paths"]["/v2/things"]["post"]["requestBody"]["content"]["application/json"]["schema"]["additionalProperties"]
        with self.assertRaisesRegex(ValueError, "reject unknown"):
            quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)

    def test_success_responses_cannot_be_opaque_or_wildcard(self):
        api = good_api()
        api["paths"]["/v2/things"]["post"]["responses"]["201"] = {"description": "Created"}
        with self.assertRaisesRegex(ValueError, "typed JSON schema"):
            quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)
        api = good_api()
        api["paths"]["/v2/things"]["post"]["responses"]["2XX"] = {"description": "Wildcard"}
        with self.assertRaisesRegex(ValueError, "explicit HTTP status"):
            quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)

    def test_all_request_and_response_media_are_checked_for_breakages(self):
        old = good_api()
        route = old["paths"]["/v2/things"]["post"]
        route["requestBody"]["content"]["text/plain"] = {
            "schema": {"type": "string", "minLength": 1}}
        route["responses"]["201"]["content"]["application/vnd.thing+json"] = {
            "schema": {"type": "object", "additionalProperties": False,
                       "required": ["receipt"], "properties": {"receipt": {"type": "string"}}}}
        changed = copy.deepcopy(old)
        changed["paths"]["/v2/things"]["post"]["requestBody"]["content"]["text/plain"]["schema"]["minLength"] = 10
        changed["paths"]["/v2/things"]["post"]["responses"]["201"]["content"]["application/vnd.thing+json"]["schema"]["required"] = []
        breakages = api_breakages(old, changed)
        self.assertTrue(any("text/plain" in item and "minimum narrowed" in item for item in breakages))
        self.assertTrue(any("application/vnd.thing+json" in item and "became optional" in item
                            for item in breakages))

    def test_new_request_property_cannot_narrow_previously_open_input(self):
        old = {"type": "object", "additionalProperties": True,
               "properties": {"stable": {"type": "string"}}}
        changed = copy.deepcopy(old)
        changed["properties"]["new"] = {"type": "integer"}
        self.assertIn("previously untyped request fields now constrained",
                      repr(schema_breakages(old, changed, "request")))
        changed = copy.deepcopy(old)
        changed["additionalProperties"] = {"type": "string"}
        self.assertIn("request additional-property constraint changed",
                      repr(schema_breakages(old, changed, "request")))

    def test_ref_sibling_assertions_cannot_bypass_semantic_major_gate(self):
        old = good_api()
        old["components"]["schemas"]["Thing"] = {
            "type": "object", "additionalProperties": False,
            "properties": {"name": {"type": "string"}}
        }
        operation = old["paths"]["/v2/things"]["post"]
        operation["requestBody"]["content"]["application/json"]["schema"] = {
            "$ref": "#/components/schemas/Thing"
        }
        operation["responses"]["201"] = response({
            "$ref": "#/components/schemas/Thing"
        })
        newer = copy.deepcopy(old)
        newer["paths"]["/v2/things"]["post"]["requestBody"]["content"]["application/json"]["schema"]["minProperties"] = 2
        newer["paths"]["/v2/things"]["post"]["responses"]["201"]["content"]["application/json"]["schema"]["unevaluatedProperties"] = True
        issues = api_breakages(old, newer)
        self.assertGreaterEqual(sum("$ref target or sibling" in issue for issue in issues), 2)
        # Pure annotations still do not change the accepted wire language.
        annotated = copy.deepcopy(old)
        annotated["paths"]["/v2/things"]["post"]["requestBody"]["content"]["application/json"]["schema"]["description"] = "clarification"
        self.assertEqual(api_breakages(old, annotated), [])

    def test_media_encoding_changes_require_new_major(self):
        old = good_api()
        old["paths"]["/v2/things"]["post"]["requestBody"]["content"]["application/json"]["encoding"] = {
            "name": {"contentType": "text/plain"}}
        changed = copy.deepcopy(old)
        changed["paths"]["/v2/things"]["post"]["requestBody"]["content"]["application/json"]["encoding"] = {
            "name": {"contentType": "application/octet-stream"}}
        self.assertIn("request media encoding changed", repr(api_breakages(old, changed)))

    def test_same_major_breaking_paths_requests_and_responses(self):
        old = good_api()
        new = copy.deepcopy(old)
        del new["paths"]["/v2/things"]
        self.assertIn("operation removed", repr(api_breakages(old, new)))
        new = copy.deepcopy(old)
        new["paths"]["/v2/things"]["post"]["requestBody"]["content"]["application/json"]["schema"]["required"].append("cost")
        self.assertIn("new required request", repr(api_breakages(old, new)))
        new = copy.deepcopy(old)
        new["paths"]["/v2/things"]["post"]["responses"]["201"]["content"]["application/json"]["schema"]["required"] = []
        self.assertIn("became optional", repr(api_breakages(old, new)))
        new = copy.deepcopy(old)
        new["paths"]["/v2/things"]["post"]["responses"]["201"]["content"]["application/json"]["schema"]["properties"] = {}
        self.assertIn("response field removed", repr(api_breakages(old, new)))
        new = copy.deepcopy(old)
        new["paths"]["/v2/things"]["post"]["responses"]["201"]["content"]["application/json"]["schema"]["properties"]["extra"] = {"type": "string"}
        self.assertIn("strict consumer sees new response fields", repr(api_breakages(old, new)))
        new = copy.deepcopy(old)
        del new["paths"]["/v2/things"]["post"]["responses"]["409"]
        self.assertIn("response status removed", repr(api_breakages(old, new)))

    def test_new_success_status_requires_a_new_major(self):
        old = good_api()
        changed = copy.deepcopy(old)
        changed["paths"]["/v2/things"]["post"]["responses"]["202"] = response({
            "type": "object", "additionalProperties": False,
            "required": ["id"], "properties": {"id": {"type": "string"}}})
        self.assertIn("new successful response status", repr(api_breakages(old, changed)))
        changed = copy.deepcopy(old)
        changed["paths"]["/v2/things"]["post"]["responses"]["429"] = response({
            "$ref": "#/components/schemas/Error"})
        self.assertNotIn("new successful response status", repr(api_breakages(old, changed)))

    def test_unclassified_constraints_and_parameter_changes_are_breaking(self):
        old = {"type": "object", "additionalProperties": False,
               "properties": {"reference": {"type": "string", "format": "uuid"}}}
        change = copy.deepcopy(old)
        change["properties"]["reference"]["format"] = "email"
        self.assertIn("unclassified schema assertion", repr(schema_breakages(old, change, "wire")))
        change = copy.deepcopy(old)
        change["properties"]["reference"]["minProperties"] = 1
        self.assertIn("unclassified schema assertion", repr(schema_breakages(old, change, "wire")))
        old_api = good_api()
        replacement = copy.deepcopy(old_api)
        route = replacement["paths"]["/v2/things"]["post"]
        route["parameters"][0]["schema"]["minLength"] = 32
        self.assertIn("parameter", repr(api_breakages(old_api, replacement)))
        replacement = copy.deepcopy(old_api)
        response = replacement["paths"]["/v2/things"]["post"]["responses"]["201"]
        response["headers"] = {"ETag": {"schema": {"type": "string"}}}
        self.assertIn("header guarantees", repr(api_breakages(old_api, replacement)))

    def test_idempotency_and_public_contract_changes_require_new_major(self):
        old = good_api()
        new = copy.deepcopy(old)
        new["paths"]["/v2/things"]["post"]["x-idempotency"]["ttl_seconds"] = 300
        self.assertIn("idempotency", repr(api_breakages(old, new)))
        new = copy.deepcopy(old)
        new["paths"]["/v2/things"]["post"]["x-public-operation"] = True
        self.assertIn("public access", repr(api_breakages(old, new)))

    def test_schema_required_and_enum_narrowing_are_breaking(self):
        old = {"type": "object", "required": ["id"], "additionalProperties": False,
               "properties": {"id": {"enum": ["a", "b"]}}}
        new = copy.deepcopy(old)
        new["required"].append("scope")
        new["properties"]["id"]["enum"] = ["a"]
        self.assertTrue(schema_breakages(old, new, "schema"))


class SchemaAndEvents(unittest.TestCase):
    def test_schema_dialect_id_and_unknown_fields(self):
        schema = {
            "$schema": POLICY["schema_dialect"], "$id": "https://example.invalid/schemas/new-v2",
            "type": "object", "additionalProperties": False,
        }
        quality_schema("contracts/schemas/new-v2.json", schema, POLICY)
        for key in ("$id", "additionalProperties"):
            broken = copy.deepcopy(schema)
            del broken[key]
            with self.assertRaises(ValueError):
                quality_schema("contracts/schemas/new-v2.json", broken, POLICY)

    def test_new_capability_catalogues_require_exact_versioned_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            schema_dir = root / "contracts/schemas/capabilities"
            schema_dir.mkdir(parents=True)
            schema = {
                "$schema": POLICY["schema_dialect"], "type": "object",
                "additionalProperties": False, "required": ["status"],
                "properties": {"status": {"const": "proposed_not_qualified"}},
            }
            (schema_dir / "candidate-v2.json").write_text(json.dumps(schema))
            path = "contracts/capabilities/candidate-v2.json"
            quality_catalogue(path, {"status": "proposed_not_qualified"}, root)
            with self.assertRaisesRegex(ValueError, "violates its canonical schema"):
                quality_catalogue(path, {"status": "qualified"}, root)
            with self.assertRaisesRegex(ValueError, "violates its canonical schema"):
                quality_catalogue(path, {"status": "proposed_not_qualified", "unknown": 1}, root)
            (schema_dir / "candidate-v2.json").unlink()
            with self.assertRaisesRegex(ValueError, "lacks its canonical schema"):
                quality_catalogue(path, {"status": "proposed_not_qualified"}, root)

    def test_capability_and_platform_semantics_require_major_for_removals(self):
        old = {
            "schema_version": 1, "version": "1.0.0", "status": "proposed_not_qualified",
            "platforms": ["vmware", "ahv"],
            "features": [{"id": "network", "mapping": "observe"},
                         {"id": "storage", "mapping": "verify"}],
            "methods": {"cold_export": {"stages": ["capture", "verify"]}},
        }
        additive = copy.deepcopy(old)
        additive["version"] = "1.1.0"
        additive["platforms"].append("openstack")
        additive["features"].append({"id": "guest", "mapping": "observe"})
        additive["methods"]["new_method"] = {"stages": ["rehearsal"]}
        self.assertEqual(declaration_breakages(old, additive, "declaration"), [])
        changed = copy.deepcopy(additive)
        changed["status"] = "qualified"
        self.assertIn("existing declaration semantics changed",
                      repr(declaration_breakages(old, changed, "declaration")))
        changed = copy.deepcopy(additive)
        changed["platforms"].remove("vmware")
        self.assertIn("declared values removed",
                      repr(declaration_breakages(old, changed, "declaration")))
        changed = copy.deepcopy(additive)
        del changed["methods"]["cold_export"]
        self.assertIn("existing declaration removed",
                      repr(declaration_breakages(old, changed, "declaration")))
        changed = copy.deepcopy(additive)
        changed["features"][0]["mapping"] = "qualified"
        self.assertIn("existing declaration semantics changed",
                      repr(declaration_breakages(old, changed, "declaration")))
        # Ordered migration stages are safety semantics: order must be retained.
        changed = copy.deepcopy(additive)
        changed["methods"]["cold_export"]["stages"] = ["verify", "capture"]
        self.assertTrue(declaration_breakages(old, changed, "declaration"))

    def test_new_event_requires_delivery_ordering_dedupe_dlq_and_schema_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "contracts/asyncapi").mkdir(parents=True)
            (root / "contracts/schemas/events").mkdir(parents=True)
            schema = {
                "type": "object", "additionalProperties": False,
                "required": POLICY["event_required_fields"],
                "properties": {key: {
                    "type": "string", **({"format": "uuid"} if key in
                        ("event_id", "tenant_id", "correlation_id") else
                        {"format": "date-time"} if key == "occurred_at" else {})
                } for key in POLICY["event_required_fields"]}
            }
            (root / "contracts/schemas/events/pulse-v2.json").write_text(json.dumps(schema))
            channel = {
                "address": "pulse.changed.v2",
                "messages": {"changed": {"$ref": "#/components/messages/Changed"}},
                "x-delivery": {"guarantee": "at-least-once", "ordering_key": "tenant_id",
                               "deduplication_key": "event_id", "dead_letter_address": "pulse.dlq.v2",
                               "max_attempts": 5, "acknowledgment": "after-commit", "backoff_strategy": "exponential-jitter", "dead_letter_retention_seconds": 604800, "deduplication_window_seconds": 86400},
            }
            event = {
                "asyncapi": "3.0.0",
                "channels": {"changed": channel},
                "components": {"messages": {"Changed": {
                    "contentType": "application/json",
                    "payload": {"schemaFormat": "application/schema+json;version=draft-2020-12",
                                "schema": {"$ref": "../schemas/events/pulse-v2.json"}}
                }}},
                "operations": {"publish": {"action": "send", "channel": {"$ref": "#/channels/changed"}}}
            }
            quality_event("contracts/asyncapi/pulse-v2.yaml", event, POLICY, root)
            malformed = copy.deepcopy(schema)
            malformed["properties"]["tenant_id"]["type"] = "number"
            (root / "contracts/schemas/events/pulse-v2.json").write_text(json.dumps(malformed))
            with self.assertRaisesRegex(ValueError, "invalid type/format"):
                quality_event("contracts/asyncapi/pulse-v2.yaml", event, POLICY, root)
            (root / "contracts/schemas/events/pulse-v2.json").write_text(json.dumps(schema))
            broken = copy.deepcopy(event)
            broken["channels"]["changed"]["x-delivery"]["max_attempts"] = 0
            with self.assertRaisesRegex(ValueError, "bounded ordering"):
                quality_event("contracts/asyncapi/pulse-v2.yaml", broken, POLICY, root)
            broken = copy.deepcopy(event)
            broken["channels"]["changed"]["messages"]["changed"]["$ref"] = "#/components/messages/Unknown"
            with self.assertRaisesRegex(ValueError, "Unknown AsyncAPI message binding"):
                quality_event("contracts/asyncapi/pulse-v2.yaml", broken, POLICY, root)
            broken = copy.deepcopy(event)
            broken["operations"]["publish"]["channel"]["$ref"] = "#/channels/unknown"
            with self.assertRaisesRegex(ValueError, "unbound channel"):
                quality_event("contracts/asyncapi/pulse-v2.yaml", broken, POLICY, root)
            broken = copy.deepcopy(event)
            broken["components"]["messages"]["Changed"]["payload"].pop("schemaFormat")
            with self.assertRaisesRegex(ValueError, "schemaFormat"):
                quality_event("contracts/asyncapi/pulse-v2.yaml", broken, POLICY, root)
            broken = copy.deepcopy(event)
            broken["channels"]["changed"]["address"] = ""
            with self.assertRaisesRegex(ValueError, "broker address"):
                quality_event("contracts/asyncapi/pulse-v2.yaml", broken, POLICY, root)
            broken = copy.deepcopy(event)
            broken["channels"]["changed"]["address"] = "pulse.secret.v2"
            self.assertTrue(event_breakages(event, broken))


class GitPublicationTests(unittest.TestCase):
    def test_new_capability_replaces_old_without_retaining_history_or_bypassing_semver(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("architecture", "contracts/capabilities",
                         "contracts/schemas/capabilities", "contracts/schemas/common"):
                (root / name).mkdir(parents=True, exist_ok=True)
            (root / POLICY["error_schema"]).write_text(json.dumps(ERROR))
            (root / "architecture/contract-quality-policy.json").write_text(json.dumps(POLICY))
            old_path = "contracts/capabilities/methods-v1.json"
            new_path = "contracts/capabilities/methods-v1.1.json"
            prior = {"schema_version": 1, "definition_version": "1.0.0",
                     "methods": {"cold": {"stages": ["capture", "verify"]},
                                 "rebuild": {"stages": ["restore"]}}}
            (root / old_path).write_text(json.dumps(prior))
            registry = root / "architecture/contract-consumers.json"
            registry.write_text(json.dumps({
                "active_releases": [{"path": old_path, "consumers": ["planning"]}]
            }))
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "quality@example.invalid"],
                           cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Quality fixture"],
                           cwd=root, check=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "Current capability"], cwd=root, check=True)
            base = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                           cwd=root, text=True).strip()
            # The checkout carries ONLY the new release; prior bytes exist
            # exclusively in Git provenance. No alias or runtime compatibility.
            (root / old_path).unlink()
            schema = {
                "$schema": POLICY["schema_dialect"], "type": "object",
                "additionalProperties": False,
                "required": ["schema_version", "definition_version", "methods"],
                "properties": {
                    "schema_version": {"const": 1},
                    "definition_version": {"type": "string"},
                    "methods": {"type": "object", "additionalProperties": {
                        "type": "object", "required": ["stages"],
                        "properties": {"stages": {"type": "array",
                                                   "items": {"type": "string"}}},
                        "additionalProperties": False,
                    }},
                },
            }
            (root / "contracts/schemas/capabilities/methods-v1.1.json").write_text(
                json.dumps(schema))
            changed = {"schema_version": 1, "definition_version": "1.1.0",
                       "methods": {"cold": {"stages": ["capture", "verify"]}}}
            (root / new_path).write_text(json.dumps(changed))
            registry.write_text(json.dumps({"active_releases": [
                {"path": new_path, "consumers": ["planning"]}
            ]}))
            with self.assertRaisesRegex(ValueError, "Breaking change requires a NEW MAJOR"):
                check_new_releases(root, base)
            new_major = "contracts/capabilities/methods-v2.json"
            major_schema = "contracts/schemas/capabilities/methods-v2.json"
            (root / new_path).unlink()
            (root / "contracts/schemas/capabilities/methods-v1.1.json").unlink()
            (root / new_major).write_text(json.dumps(changed))
            (root / major_schema).write_text(json.dumps(schema))
            registry.write_text(json.dumps({"active_releases": [
                {"path": new_major, "consumers": ["planning"]}
            ]}))
            admitted = check_new_releases(root, base)
            self.assertEqual(admitted["validated"], 1)
            self.assertTrue(admitted["new_releases"][0]["breaking_changes"])
            self.assertFalse((root / old_path).exists())

    def test_new_minor_version_cannot_hide_a_deleted_operation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("architecture", "contracts/openapi", "contracts/schemas/common"):
                (root / name).mkdir(parents=True, exist_ok=True)
            (root / POLICY["error_schema"]).write_text(json.dumps(ERROR))
            (root / "architecture/contract-quality-policy.json").write_text(json.dumps(POLICY))
            prior = good_api()
            path = "contracts/openapi/things-v2.json"
            (root / path).write_text(json.dumps(prior))
            (root / "architecture/contract-consumers.json").write_text(json.dumps({
                "active_releases": [{"path": path, "consumers": ["former-client"]}]
            }))
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "quality@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Quality fixture"], cwd=root, check=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "Existing API"], cwd=root, check=True)
            base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            new = good_api()
            new["paths"] = {"/v2/replaced": new["paths"]["/v2/things"]}
            new["info"]["version"] = "2.1.0"
            replacement = "contracts/openapi/things-v2.1.json"
            (root / replacement).write_text(json.dumps(new))
            (root / "architecture/contract-consumers.json").write_text(json.dumps({
                "active_releases": [{"path": path}, {
                    "path": replacement, "consumers": ["new-client"]
                }]
            }))
            with self.assertRaisesRegex(ValueError, "Breaking change requires a NEW MAJOR"):
                check_new_releases(root, base)
            (root / replacement).unlink()
            new["info"]["version"] = "3.0.0"
            replacement = "contracts/openapi/things-v3.json"
            (root / replacement).write_text(json.dumps(new))
            (root / "architecture/contract-consumers.json").write_text(json.dumps({
                "active_releases": [{"path": path}, {
                    "path": replacement, "consumers": ["new-client"]
                }]
            }))
            result = check_new_releases(root, base)
            self.assertEqual(result["validated"], 1)
            self.assertTrue(result["new_releases"][0]["breaking_changes"])
            self.assertEqual(result["new_releases"][0]["impacted_consumers"],
                             ["former-client", "new-client"])


if __name__ == "__main__":
    unittest.main()
