"""Regressions for dynamically enumerated assurance and fail-closed proof admission."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/contracts"))
from assurance import assess, inventory, operation_key


class AssuranceCoverageTests(unittest.TestCase):
    def setUp(self):
        self.context = tempfile.TemporaryDirectory()
        self.addCleanup(self.context.cleanup)
        self.root = Path(self.context.name)
        for parent in ("architecture", "contracts/openapi", "contracts/schemas"):
            (self.root / parent).mkdir(parents=True, exist_ok=True)
        self.api = "contracts/openapi/example-v1.json"
        self.schema = "contracts/schemas/example-v1.json"
        self.op = "/v1/things/{thing}"
        document = {
            "openapi": "3.1.0",
            "info": {"title": "Sample", "version": "1.0.0"},
            "paths": {self.op: {"get": {
                "operationId": "getThing",
                "parameters": [{"name": "thing", "in": "path",
                                "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "OK",
                                      "content": {"application/json": {
                                          "schema": {"type": "object", "additionalProperties": False}}}}},
            }}},
            "components": {"securitySchemes": {"Caller": {
                "type": "http", "scheme": "bearer"
            }}},
            "security": [{"Caller": []}],
        }
        self.write(self.api, document)
        self.write(self.schema, {"$schema": "https://json-schema.org/draft/2020-12/schema",
                                 "$id": "https://test.invalid/example-v1",
                                 "type": "object"})
        self.registry([self.api, self.schema])

    def write(self, path, payload):
        (self.root / path).write_text(json.dumps(payload, indent=2) + "\n")

    def registry(self, paths):
        self.write("architecture/contract-consumers.json", {
            "active_releases": [
                {"path": path, "owner": "sample", "consumers": ["other"], "copies": []}
                for path in paths
            ],
        })

    def evidence(self, claim, release_hash=None, source=None):
        row = inventory(self.root)["operations"][0]
        return {
            "key": row["key"],
            "claim": claim,
            "source": source or {
                "route": "live-router",
                "producer": "live-producer",
                "consumer": "live-consumer",
                "authorization": "live-denial",
                "tenant_isolation": "live-denial",
            }[claim],
            "result": "PASS",
            "release_sha256": release_hash or row["release_sha256"],
            "test": "service-owned-executable-test",
        }

    def test_contracts_and_operations_are_independently_derived(self):
        output = inventory(self.root)
        self.assertEqual(len(output["releases"]), 2)
        self.assertEqual(len(output["operations"]), 1)
        self.assertEqual(output["operations"][0]["key"],
                         operation_key("sample", "GET", self.op))
        self.assertEqual(output["operations"][0]["consumers"], ["other"])

    def test_structural_presence_does_not_claim_producer_or_consumer(self):
        first = assess(self.root, [self.evidence("route")])
        self.assertEqual(first["summary"]["qualified_http_operations"], 0)
        self.assertEqual(first["coverage"][0]["missing"],
                         ["producer", "consumer", "authorization", "tenant_isolation"])

    def test_all_measured_claims_required_for_qualification(self):
        claims = ["route", "producer", "consumer", "authorization", "tenant_isolation"]
        data = assess(self.root, [self.evidence(claim) for claim in claims])
        self.assertEqual(data["summary"]["qualified_http_operations"], 1)
        self.assertEqual(data["summary"]["verified_claims"], 5)

    def test_stale_and_counterfeit_evidence_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Stale operation evidence"):
            assess(self.root, [self.evidence("route", release_hash="f" * 64)])
        with self.assertRaisesRegex(ValueError, "Wrong evidence source"):
            assess(self.root, [self.evidence("producer", source="live-router")])
        with self.assertRaisesRegex(ValueError, "Duplicate operation assurance evidence"):
            assess(self.root, [self.evidence("route"), self.evidence("route")])
        wrong = self.evidence("route")
        wrong["key"] = operation_key("sample", "POST", self.op)
        with self.assertRaisesRegex(ValueError, "Unregistered operation"):
            assess(self.root, [wrong])

    def test_new_owner_operation_is_not_silently_qualified(self):
        all_claims = [self.evidence(x) for x in (
            "route", "producer", "consumer", "authorization", "tenant_isolation"
        )]
        doc = json.loads((self.root / self.api).read_text())
        doc["paths"]["/v1/hidden"] = {"post": {
            "operationId": "newUnexpectedWrite",
            "responses": {"201": {"description": "Created"}},
        }}
        self.write(self.api, doc)
        output = assess(self.root)
        self.assertEqual(len(output["operations"]), 2)
        self.assertEqual(output["summary"]["qualified_http_operations"], 0)
        with self.assertRaisesRegex(ValueError, "Stale operation evidence"):
            assess(self.root, all_claims)

    def test_missing_declared_canonical_cannot_be_qualified(self):
        (self.root / self.api).unlink()
        with self.assertRaisesRegex(ValueError, "Missing canonical contract"):
            inventory(self.root)


if __name__ == "__main__":
    unittest.main()
