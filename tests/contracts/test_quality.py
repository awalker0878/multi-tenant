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
)

POLICY = json.loads((ROOT / "architecture/contract-quality-policy.json").read_text())
ERROR = json.loads((ROOT / POLICY["error_schema"]).read_text())


def response(schema=None):
    return {"description": "Expected response", **({
        "content": {"application/json": {"schema": schema}}
    } if schema else {})}


def good_api():
    api_error = {k: v for k, v in ERROR.items() if k not in ("$id", "$schema")}
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

    def test_request_must_be_structurally_strict(self):
        api = good_api()
        del api["paths"]["/v2/things"]["post"]["requestBody"]["content"]["application/json"]["schema"]["additionalProperties"]
        with self.assertRaisesRegex(ValueError, "reject unknown"):
            quality_api("contracts/openapi/things-v2.json", api, ERROR, POLICY)

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
        del new["paths"]["/v2/things"]["post"]["responses"]["409"]
        self.assertIn("response status removed", repr(api_breakages(old, new)))

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

    def test_new_event_requires_delivery_ordering_dedupe_dlq_and_schema_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "contracts/asyncapi").mkdir(parents=True)
            (root / "contracts/schemas/events").mkdir(parents=True)
            schema = {
                "type": "object", "additionalProperties": False,
                "required": POLICY["event_required_fields"],
                "properties": {key: {"type": "string"} for key in POLICY["event_required_fields"]}
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
                    "payload": {"schema": {"$ref": "../schemas/events/pulse-v2.json"}}
                }}},
                "operations": {"publish": {"action": "send", "channel": {"$ref": "#/channels/changed"}}}
            }
            quality_event("contracts/asyncapi/pulse-v2.yaml", event, POLICY, root)
            broken = copy.deepcopy(event)
            broken["channels"]["changed"]["x-delivery"]["max_attempts"] = 0
            with self.assertRaisesRegex(ValueError, "bounded ordering"):
                quality_event("contracts/asyncapi/pulse-v2.yaml", broken, POLICY, root)
            broken = copy.deepcopy(event)
            broken["channels"]["changed"]["address"] = "pulse.secret.v2"
            self.assertTrue(event_breakages(event, broken))


class GitPublicationTests(unittest.TestCase):
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
                "active_releases": [{"path": path}, {"path": replacement}]
            }))
            with self.assertRaisesRegex(ValueError, "Breaking change requires a NEW MAJOR"):
                check_new_releases(root, base)
            (root / replacement).unlink()
            new["info"]["version"] = "3.0.0"
            replacement = "contracts/openapi/things-v3.json"
            (root / replacement).write_text(json.dumps(new))
            (root / "architecture/contract-consumers.json").write_text(json.dumps({
                "active_releases": [{"path": path}, {"path": replacement}]
            }))
            result = check_new_releases(root, base)
            self.assertEqual(result["validated"], 1)
            self.assertTrue(result["new_releases"][0]["breaking_changes"])


if __name__ == "__main__":
    unittest.main()
