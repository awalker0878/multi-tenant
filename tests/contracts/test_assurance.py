"""Regressions for dynamically enumerated assurance and fail-closed proof admission."""
from __future__ import annotations

import json
import hashlib
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

    def journey_measurement(self):
        from route_conformance import HttpConformance
        validator = self.root/'scripts/contracts/route_conformance.py'
        validator.parent.mkdir(parents=True)
        validator.write_bytes((ROOT/'scripts/contracts/route_conformance.py').read_bytes())
        output = self.root/'campaign/http-conformance.json'
        output.parent.mkdir()
        probe = HttpConformance(self.root, output, {'https://sample.invalid':'sample'},
                                'scripts/p05/verify_live.py:wire')
        probe.observe('https://sample.invalid', '/v1/things/current', 'GET', None, {},
                      200, {}, {'Content-Type':'application/json'})
        report = {'result':'PASS','source_unchanged':True,
                  'source_revision':os.environ['GITHUB_SHA'],
                  'run_id':os.environ['GITHUB_RUN_ID'],'run_attempt':os.environ['GITHUB_RUN_ATTEMPT'],
                  'source_sha256':{'scripts/contracts/route_conformance.py':hashlib.sha256(validator.read_bytes()).hexdigest()},
                  'artifact_sha256':{'http-conformance.json':hashlib.sha256(output.read_bytes()).hexdigest()}}
        (output.parent/'report.json').write_text(json.dumps(report))
        return output, report

    def test_live_wire_proves_only_its_executed_producer(self):
        from journey_assurance import producers
        with patch.dict(os.environ, {'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'2','GITHUB_SHA':'a'*40}):
            output, report = self.journey_measurement()
            rows = producers(output.parent, [], self.root)
            self.assertEqual([row['claim'] for row in rows], ['producer'])
            data = assess(self.root, rows, require_provenance=True)
            self.assertEqual(data['coverage'][0]['verified'], ['producer'])
            self.assertIn('authorization', data['coverage'][0]['missing'])
            self.assertIn('tenant_isolation', data['coverage'][0]['missing'])
            self.assertIn('consumer', data['coverage'][0]['missing'])
            self.assertEqual(producers(output.parent, rows, self.root), [])
            report['result'] = 'FAIL'
            (output.parent/'report.json').write_text(json.dumps(report))
            self.assertEqual(producers(output.parent, [], self.root), [])

    def test_journey_admission_rejects_stale_tampered_and_invalid_wire(self):
        from journey_assurance import producers
        with patch.dict(os.environ, {'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'2','GITHUB_SHA':'a'*40}):
            output, report = self.journey_measurement()
            original = json.loads(output.read_text())
            report_path = output.parent/'report.json'
            for field,value in [('request_valid',False),('response_valid',False),('status_code',403),
                                ('release_sha256','f'*64),('run_attempt','1'),
                                ('path','/v1/unregistered'),('test','unexecuted-test')]:
                rows = [{**original[0],field:value}]
                output.write_text(json.dumps(rows))
                report['artifact_sha256'][output.name] = hashlib.sha256(output.read_bytes()).hexdigest()
                report_path.write_text(json.dumps(report))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    producers(output.parent, [], self.root)
            output.write_text(json.dumps(original))
            with self.assertRaisesRegex(ValueError, 'measured wire bytes differ'):
                producers(output.parent, [], self.root)
            report['artifact_sha256'][output.name] = hashlib.sha256(output.read_bytes()).hexdigest()
            report['run_attempt'] = '1'
            report_path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, 'Stale journey'):
                producers(output.parent, [], self.root)

    def security_measurement(self):
        output, report = self.journey_measurement()
        source = 'scripts/p06/live_execution.py'
        file = self.root/source
        file.parent.mkdir(parents=True)
        file.write_bytes((ROOT/source).read_bytes())
        row = self.evidence('tenant_isolation')
        row.update(test='scripts/p06/live_execution.py:security_probes',
                   authority_checked='current-effective-authority',
                   positive_status_code=200, request_valid=True, response_valid=True,
                   state_before_sha256='b'*64, state_after_sha256='b'*64,
                   revision=os.environ['GITHUB_SHA'], run_id=os.environ['GITHUB_RUN_ID'],
                   run_attempt=os.environ['GITHUB_RUN_ATTEMPT'])
        output = output.parent/'security-conformance.json'
        output.write_text(json.dumps([row]))
        report['source_sha256'][source] = hashlib.sha256(file.read_bytes()).hexdigest()
        report['artifact_sha256'][output.name] = hashlib.sha256(output.read_bytes()).hexdigest()
        (output.parent/'report.json').write_text(json.dumps(report))
        return output, report, row

    def test_security_requires_separate_authenticated_denials_and_state_controls(self):
        from journey_assurance import security
        with patch.dict(os.environ, {'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'2','GITHUB_SHA':'a'*40}):
            output, report, row = self.security_measurement()
            proofs = security(output.parent, [], self.root)
            self.assertEqual([r['claim'] for r in proofs], ['tenant_isolation'])
            self.assertEqual(security(output.parent, proofs, self.root), [])
            measured = assess(self.root, proofs, require_provenance=True)
            self.assertEqual(measured['coverage'][0]['verified'], ['tenant_isolation'])
            self.assertEqual(measured['summary']['qualified_http_operations'], 0)
            report['result'] = 'FAIL'
            (output.parent/'report.json').write_text(json.dumps(report))
            self.assertEqual(security(output.parent, [], self.root), [])

    def test_security_rejects_stale_malformed_disclosing_or_mutating_probes(self):
        from journey_assurance import security
        with patch.dict(os.environ, {'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'2','GITHUB_SHA':'a'*40}):
            output, report, original = self.security_measurement()
            for field,value in [('request_valid',False),('response_valid',False),
                                ('status_code',503),('positive_status_code',403),
                                ('positive_status_code',True),('authenticated',False),
                                ('authority_checked','cached'),('requested_tenant',original['credential_tenant']),
                                ('state_after_sha256','c'*64),('state_before_sha256',''),
                                ('unauthorized_mutation',True),('unauthorized_disclosure',True),
                                ('release_sha256','f'*64),('run_attempt','1'),
                                ('test','unexecuted-test'),('claim','consumer')]:
                output.write_text(json.dumps([{**original,field:value}]))
                report['artifact_sha256'][output.name] = hashlib.sha256(output.read_bytes()).hexdigest()
                (output.parent/'report.json').write_text(json.dumps(report))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    security(output.parent, [], self.root)
            output.write_text(json.dumps([original]))
            with self.assertRaisesRegex(ValueError, 'measured bytes differ'):
                security(output.parent, [], self.root)

    def consumer_measurement(self):
        output, report = self.journey_measurement()
        api = json.loads((self.root/self.api).read_text())
        operation = api['paths'].pop(self.op)['get']
        operation['parameters'] = [
            {'name': name, 'in': 'path', 'required': True, 'schema': {'type': 'string'}}
            for name in ('tenant', 'job')]
        api['paths']['/v1/tenants/{tenant}/jobs/{job}'] = {'get': operation}
        self.write(self.api, api)
        installed = 'apps/console/resources/contracts/lifecycle-v1.json'
        copy = self.root/installed
        copy.parent.mkdir(parents=True)
        copy.write_bytes((self.root/self.api).read_bytes())
        registry = json.loads((self.root/'architecture/contract-consumers.json').read_text())
        registry['active_releases'][0].update(owner='lifecycle', consumers=['console'], copies=[installed])
        self.write('architecture/contract-consumers.json', registry)
        sources = ['scripts/p06/verify_console_consumers.php', 'apps/console/app/Infrastructure/Jobs/JobsClient.php']
        for source in sources:
            file = self.root/source
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes((ROOT/source).read_bytes())
            report['source_sha256'][source] = hashlib.sha256(file.read_bytes()).hexdigest()
        op = inventory(self.root)['operations'][0]
        row = {'key': op['key'], 'claim': 'consumer', 'source': 'live-consumer', 'result': 'PASS',
               'consumer_id': 'console', 'release_sha256': op['release_sha256'],
               'test': sources[0]+':JobsClient', 'consumer_loader': sources[1],
               'loader_sha256': report['source_sha256'][sources[1]],
               'installed_copy': installed, 'installed_sha256': op['release_sha256'],
               'response_sha256': 'c'*64, 'positive_status_code': 200,
               'rejected_response_substitutions': ['id', 'tenant_id', 'uncontracted', 'status_code'],
               'revision': os.environ['GITHUB_SHA'], 'run_id': os.environ['GITHUB_RUN_ID'],
               'run_attempt': os.environ['GITHUB_RUN_ATTEMPT']}
        output = output.parent/'consumer-conformance.json'
        output.write_text(json.dumps([row]))
        report['artifact_sha256'][output.name] = hashlib.sha256(output.read_bytes()).hexdigest()
        (output.parent/'report.json').write_text(json.dumps(report))
        return output, report, row

    def test_live_consumer_credits_only_its_executed_registered_boundary(self):
        from journey_assurance import consumers
        with patch.dict(os.environ, {'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'2','GITHUB_SHA':'a'*40}):
            output, report, original = self.consumer_measurement()
            rows = consumers(output.parent, [], self.root)
            self.assertEqual([row['claim'] for row in rows], ['consumer'])
            self.assertEqual([row['consumer_id'] for row in rows], ['console'])
            self.assertEqual(consumers(output.parent, rows, self.root), [])
            measured = assess(self.root, rows, require_provenance=True)
            self.assertEqual(measured['coverage'][0]['verified'], ['consumer'])
            self.assertEqual(measured['summary']['qualified_http_operations'], 0)
            report['result'] = 'FAIL'
            (output.parent/'report.json').write_text(json.dumps(report))
            self.assertEqual(consumers(output.parent, [], self.root), [])

    def test_consumer_rejects_wrong_loader_copy_and_missing_negative_controls(self):
        from journey_assurance import consumers
        with patch.dict(os.environ, {'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'2','GITHUB_SHA':'a'*40}):
            output, report, original = self.consumer_measurement()
            for field,value in [('consumer_id','unexecuted'),('consumer_loader','another/loader.php'),
                                ('loader_sha256','f'*64),('installed_copy','unregistered.json'),
                                ('installed_sha256','f'*64),('response_sha256',''),
                                ('positive_status_code',403),('rejected_response_substitutions',[]),
                                ('claim','producer'),('run_attempt','1'),('release_sha256','f'*64),
                                ('test','unexecuted')]:
                output.write_text(json.dumps([{**original,field:value}]))
                report['artifact_sha256'][output.name] = hashlib.sha256(output.read_bytes()).hexdigest()
                (output.parent/'report.json').write_text(json.dumps(report))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    consumers(output.parent, [], self.root)
            output.write_text(json.dumps([original]))
            report['artifact_sha256'][output.name] = hashlib.sha256(output.read_bytes()).hexdigest()
            (output.parent/'report.json').write_text(json.dumps(report))
            (self.root/original['installed_copy']).write_text('{}')
            with self.assertRaisesRegex(ValueError, 'installed release differs'):
                consumers(output.parent, [], self.root)



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
