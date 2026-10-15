"""Regressions for dynamically enumerated assurance and fail-closed proof admission."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
                "authentication": "live-denial",
                "authorization": "live-denial",
                "tenant_isolation": "live-denial",
            }[claim],
            "result": "PASS",
            "release_sha256": release_hash or row["release_sha256"],
            "test": "service-owned-executable-test",
            **({"consumer_id": "other"} if claim == "consumer" else {}),
            **({
                "denial_kind": "missing-credential", "status_code": 401,
            } if claim == "authentication" else {
                "denial_kind": "insufficient-authority", "authenticated": True,
                "authority_checked": "current-effective-authority", "status_code": 403,
                "unauthorized_disclosure": False, "unauthorized_mutation": False,
            } if claim == "authorization" else {
                "denial_kind": "cross-tenant", "authenticated": True,
                "credential_tenant": "10000000-0000-4000-8000-000000000001",
                "requested_tenant": "10000000-0000-4000-8000-000000000002",
                "status_code": 403,
                "unauthorized_disclosure": False, "unauthorized_mutation": False,
            } if claim == "tenant_isolation" else {}),
        }

    def test_contracts_and_operations_are_independently_derived(self):
        output = inventory(self.root)
        self.assertEqual(len(output["releases"]), 2)
        self.assertEqual(len(output["operations"]), 1)
        self.assertEqual(assess(self.root)["summary"]["unqualified_canonical_releases"], 2)
        self.assertEqual(output["operations"][0]["key"],
                         operation_key("sample", "GET", self.op))
        self.assertEqual(output["operations"][0]["consumers"], ["other"])

    def test_structural_presence_does_not_claim_producer_or_consumer(self):
        first = assess(self.root, [self.evidence("route")])
        self.assertEqual(first["summary"]["qualified_http_operations"], 0)
        self.assertEqual(first["coverage"][0]["missing"],
                         ["producer", "consumer", "authentication", "authorization", "tenant_isolation"])

    def test_all_measured_claims_required_for_qualification(self):
        claims = ["route", "producer", "consumer", "authentication", "authorization", "tenant_isolation"]
        data = assess(self.root, [self.evidence(claim) for claim in claims])
        self.assertEqual(data["summary"]["qualified_http_operations"], 1)
        self.assertEqual(data["summary"]["verified_claims"], 6)

    def test_one_executed_consumer_cannot_qualify_another_registered_caller(self):
        registry = json.loads((self.root / 'architecture/contract-consumers.json').read_text())
        for release in registry['active_releases']:
            release['consumers'].append('second')
        self.write('architecture/contract-consumers.json', registry)
        rows = [self.evidence(claim) for claim in (
            'route', 'producer', 'consumer', 'authentication', 'authorization', 'tenant_isolation')]
        output = assess(self.root, rows)
        self.assertEqual(output['coverage'][0]['missing'], ['consumer'])
        self.assertEqual(output['coverage'][0]['consumer_coverage']['missing'], ['second'])
        rows.append({**self.evidence('consumer'), 'consumer_id': 'second'})
        self.assertTrue(assess(self.root, rows)['coverage'][0]['qualified'])
        for consumer in (None, '', 'unregistered'):
            with self.assertRaisesRegex(ValueError, 'executed registered or owner-local boundary'):
                assess(self.root, [{**self.evidence('consumer'), 'consumer_id': consumer}])

    def test_non_http_consumers_are_independently_required_and_local_use_is_explicit(self):
        registry = json.loads((self.root / 'architecture/contract-consumers.json').read_text())
        registry['active_releases'][1]['consumers'] = []
        self.write('architecture/contract-consumers.json', registry)
        release = next(r for r in inventory(self.root)['releases'] if r['path'] == self.schema)
        proof = {**self.evidence('consumer'), 'key': self.schema,
                 'release_sha256': release['sha256'], 'consumer_id': 'sample'}
        with self.assertRaisesRegex(ValueError, 'owner-local boundary'):
            assess(self.root, [proof])
        proof['consumer_boundary'] = 'owner-local'
        output = assess(self.root, [proof])
        row = next(r for r in output['release_coverage'] if r['path'] == self.schema)
        self.assertEqual(row['consumer_coverage'], {'required': ['sample'], 'verified': ['sample'], 'missing': []})
        self.assertEqual(row['missing'], ['producer'])

    def test_cross_tenant_denial_with_disclosure_mutation_or_no_target_is_inadmissible(self):
        for field, value in (('requested_tenant', ''), ('unauthorized_disclosure', True),
                             ('unauthorized_mutation', True), ('unauthorized_disclosure', None),
                             ('unauthorized_mutation', None)):
            with self.assertRaisesRegex(ValueError, 'authenticated cross-tenant denial'):
                assess(self.root, [{**self.evidence('tenant_isolation'), field: value}])

    def test_release_gate_rejects_unattested_evidence(self):
        claims = ["route", "producer", "consumer", "authentication", "authorization", "tenant_isolation"]
        rows = [self.evidence(claim) for claim in claims]
        with patch.dict(os.environ, {
            "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "2",
            "GITHUB_SHA": "a" * 40
        }):
            with self.assertRaisesRegex(ValueError, "Unattested operation evidence"):
                assess(self.root, rows, require_provenance=True)
            for row in rows:
                row["run_id"] = "123"
                row["run_attempt"] = "2"
                row["revision"] = "a" * 40
            self.assertEqual(assess(self.root, rows, require_provenance=True)
                             ["summary"]["qualified_http_operations"], 1)
            rows[0]["run_attempt"] = "1"
            with self.assertRaisesRegex(ValueError, "Unattested operation evidence"):
                assess(self.root, rows, require_provenance=True)
            rows[0]["run_attempt"] = "2"
            rows[0]["revision"] = "b" * 40
            with self.assertRaisesRegex(ValueError, "Unattested operation evidence"):
                assess(self.root, rows, require_provenance=True)

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

    def test_unauthenticated_denials_cannot_substitute_for_tenant_isolation(self):
        spoofed = self.evidence("tenant_isolation")
        spoofed.update({"denial_kind": "missing-credential", "authenticated": False})
        with self.assertRaisesRegex(ValueError, "authenticated cross-tenant denial"):
            assess(self.root, [spoofed])
        spoofed = self.evidence("tenant_isolation")
        spoofed["requested_tenant"] = spoofed["credential_tenant"]
        with self.assertRaisesRegex(ValueError, "authenticated cross-tenant denial"):
            assess(self.root, [spoofed])
        spoofed = self.evidence("tenant_isolation")
        spoofed["status_code"] = 503
        with self.assertRaisesRegex(ValueError, "authenticated cross-tenant denial"):
            assess(self.root, [spoofed])
        # A 423 means an operation was held (possibly for unrelated freshness
        # or policy reasons); it is not an access-control isolation verdict.
        spoofed["status_code"] = 423
        with self.assertRaisesRegex(ValueError, "authenticated cross-tenant denial"):
            assess(self.root, [spoofed])
        spoofed = self.evidence("authentication")
        spoofed["status_code"] = 404
        with self.assertRaisesRegex(ValueError, "real credential denial"):
            assess(self.root, [spoofed])

    def test_missing_credentials_cannot_qualify_effective_authorization(self):
        forged = self.evidence("authentication")
        forged["claim"] = "authorization"
        with self.assertRaisesRegex(ValueError, "authenticated current-authority"):
            assess(self.root, [forged])
        for field, value in (
            ("authenticated", False), ("authority_checked", "cached"),
            ("denial_kind", "missing-credential"), ("status_code", 503),
            ("unauthorized_mutation", True), ("unauthorized_disclosure", True),
        ):
            forged = self.evidence("authorization")
            forged[field] = value
            with self.assertRaisesRegex(ValueError, "authenticated current-authority"):
                assess(self.root, [forged])

    def test_new_owner_operation_is_not_silently_qualified(self):
        all_claims = [self.evidence(x) for x in (
            "route", "producer", "consumer", "authentication", "authorization", "tenant_isolation"
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

    def test_not_ready_only_status_is_still_an_active_wire_operation(self):
        doc = json.loads((self.root / self.api).read_text())
        doc["paths"][self.op]["get"]["responses"] = {
            "503": {"description": "not yet commissioned"}
        }
        self.write(self.api, doc)
        op = inventory(self.root)["operations"][0]
        self.assertEqual(op["response_statuses"], ["503"])
        self.assertFalse(assess(self.root)["coverage"][0]["qualified"])

    def test_anonymous_security_alternative_does_not_demand_auth_denials(self):
        doc = json.loads((self.root / self.api).read_text())
        doc["security"] = [{"Caller": []}, {}]
        self.write(self.api, doc)
        self.assertFalse(inventory(self.root)["operations"][0]["security_required"])

    def test_shared_health_bearer_requires_auth_without_invented_tenant_scope(self):
        document = json.loads((self.root / self.api).read_text())
        document["paths"] = {
            "/health/dependencies": {
                "get": {
                    "operationId": "inspectDependencies",
                    "responses": {"200": {"description": "Ready"}},
                    "security": [{"Caller": []}],
                },
            },
        }
        self.write(self.api, document)
        self.write("architecture/contract-consumers.json", {
            "active_releases": [
                {"path": self.api, "owner": "contract-platform",
                 "consumers": ["sample"], "copies": []},
                {"path": self.schema, "owner": "sample",
                 "consumers": [], "copies": []},
            ],
        })
        operation = inventory(self.root)["operations"][0]
        self.assertTrue(operation["security_required"])
        self.assertFalse(operation["tenant_isolation_required"])
        result = assess(self.root)
        self.assertEqual(
            result["coverage"][0]["required"],
            ["route", "producer", "consumer", "authentication", "authorization"],
        )
        self.assertNotIn("tenant_isolation", result["coverage"][0]["missing"])

    def test_missing_declared_canonical_cannot_be_qualified(self):
        (self.root / self.api).unlink()
        with self.assertRaisesRegex(ValueError, "Missing canonical contract"):
            inventory(self.root)



class PlanningDenialProbeTests(unittest.TestCase):
    def test_ephemeral_invalidation_principal_is_scoped_and_cleaned_up(self):
        import asyncio
        from unittest.mock import patch

        from python_denials import probe

        async def verified_probe(owner):
            path = os.environ.get("PLANNING_ASSURANCE_INVALIDATION_CREDENTIAL_FILE")
            if owner == "planning":
                self.assertIsNotNone(path)
                self.assertTrue(Path(path).is_file())
                self.assertEqual(Path(path).stat().st_mode & 0o777, 0o600)
                self.assertTrue(Path(path).read_text().startswith(
                    "synthetic-independent-denial-principal-"
                ))
            else:
                self.assertEqual(owner, "inventory")
                self.assertIsNone(path)
            return [{"test": "scoped"}], []

        with patch.dict(os.environ, {}, clear=True), \
             patch("python_denials._probe_with_router", new=verified_probe):
            self.assertEqual(asyncio.run(probe("planning")), ([{"test": "scoped"}], []))
            self.assertNotIn(
                "PLANNING_ASSURANCE_INVALIDATION_CREDENTIAL_FILE", os.environ
            )
            self.assertEqual(asyncio.run(probe("inventory")), ([{"test": "scoped"}], []))

    def test_explicit_invalidation_mount_is_not_replaced_by_fixture(self):
        import asyncio
        from unittest.mock import patch

        from python_denials import probe

        async def verify(owner):
            self.assertEqual(
                os.environ["PLANNING_ASSURANCE_INVALIDATION_CREDENTIAL_FILE"],
                "/tmp/explicit-test-mount",
            )
            return [], []

        with patch.dict(os.environ, {
            "PLANNING_ASSURANCE_INVALIDATION_CREDENTIAL_FILE":
                "/tmp/explicit-test-mount",
        }), patch("python_denials._probe_with_router", new=verify):
            self.assertEqual(asyncio.run(probe("planning")), ([], []))


class MissingArtifactFailClosedTests(unittest.TestCase):
    def test_missing_upstream_artifacts_produce_no_proof(self):
        from combine_assurance import combine

        with tempfile.TemporaryDirectory() as directory:
            absent = Path(directory) / "never-uploaded"
            self.assertEqual(combine(absent), [])
            result = assess(observations=combine(absent))
            self.assertEqual(result["summary"]["qualified_http_operations"], 0)
            self.assertEqual(result["summary"]["qualified_canonical_releases"], 0)
            self.assertGreater(result["summary"]["unqualified_canonical_releases"], 0)


if __name__ == "__main__":
    unittest.main()
