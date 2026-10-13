"""Synthetic canaries for actual HTTP router vs immutable published OpenAPI."""
import json
import tempfile
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/contracts"))
from route_conformance import compare_declared, compare_inventory_discovery_routes, compare_inventory_worker_routes, routes_in_laravel, routes_in_openapi, verify_app, verify_lifecycle_native_jobs, verify_lifecycle_worker_effect_routes


class HttpRouteConformanceTests(unittest.TestCase):
    def test_must_match_method_and_full_path(self):
        spec = {"paths": {
            "/v1/tenants/{tenant}/approvals": {
                "post": {"operationId": "requestApproval", "responses": {"200": {}}}
            }
        }}
        runtime = routes_in_laravel([{
            "method": "POST", "uri": "v1/tenants/{tenant}/approvals"
        }])
        self.assertEqual(runtime, {("POST", "/v1/tenants/{tenant}/approvals")})
        compare_declared(spec, runtime, "synthetic")
        with self.assertRaisesRegex(ValueError, "without implemented routes"):
            compare_declared(spec, {("GET", "/v1/tenants/{tenant}/approvals")}, "synthetic")
        with self.assertRaisesRegex(ValueError, "without implemented routes"):
            compare_declared(spec, {("POST", "/v1/tenants/{tenant}/approval")}, "synthetic")

    def test_get_head_and_optional_path_handling(self):
        actual = routes_in_laravel([{
            "method": "GET|HEAD",
            "uri": "v1/tenants/{tenant}/approvals/{approval?}",
        }])
        self.assertEqual(actual, {("GET", "/v1/tenants/{tenant}/approvals/{approval}")})

    def test_unregistered_runtime_operations_fail_in_every_laravel_owner(self):
        for owner in ("governance", "catalogue", "assurance"):
            with self.subTest(owner=owner), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "architecture").mkdir()
                path = f"contracts/openapi/{owner}-test-v1.json"
                target = root / path
                target.parent.mkdir(parents=True)
                route = ("GET", "/v1/tenants/{tenant}/current-owner-read")
                doc = {"paths": {route[1]: {"get": {"operationId": "readCurrentOwner",
                        "responses": {"200": {"description": "OK"}}}}}}
                target.write_text(json.dumps(doc))
                (root / "architecture/contract-consumers.json").write_text(json.dumps(
                    {"active_releases": [{"path": path, "owner": owner}]}))
                self.assertEqual(verify_app(owner, {route}, root), 1)
                with self.assertRaisesRegex(ValueError, f"Undocumented {owner}"):
                    verify_app(owner, {route, ("GET", "/internal/tenants/{tenant}/x")}, root)
                with self.assertRaisesRegex(ValueError, f"Undocumented {owner}"):
                    verify_app(owner, {route, ("POST", "/v1/tenants/{tenant}/surprise")}, root)

    def test_retired_unversioned_qualification_alias_is_not_exempt(self):
        spec = json.loads((ROOT / "contracts/openapi/assurance-qualification-v1.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "architecture").mkdir()
            path = "contracts/openapi/assurance-qualification-v1.json"
            target = root / path
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(spec))
            (root / "architecture/contract-consumers.json").write_text(json.dumps(
                {"active_releases": [{"path": path, "owner": "assurance"}]}))
            with self.assertRaisesRegex(ValueError, "Undocumented assurance"):
                verify_app("assurance", routes_in_openapi(spec) | {
                    ("POST", "/v1/tenants/{tenant}/planning-qualification")}, root)

    def test_inventory_reverse_route_negative_injection(self):
        segment = r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
        real = ("GET", rf"/v1/tenants/({segment})/sites", "sites", "inventory.read")
        declared = {("GET", "/v1/tenants/{tenant}/sites")}
        compare_inventory_discovery_routes((real,), declared)
        dummy = ("GET", rf"/internal/tenants/({segment})/x", "undocumented", "inventory.read")
        with self.assertRaisesRegex(ValueError, "Undocumented Inventory"):
            compare_inventory_discovery_routes((real, dummy), declared)

    def test_unregistered_inventory_worker_route_fails(self):
        declared = {("POST", "/internal/collections/claim")}
        compare_inventory_worker_routes(frozenset({"/internal/collections/claim"}), declared)
        with self.assertRaisesRegex(ValueError, "Undocumented Inventory worker"):
            compare_inventory_worker_routes(frozenset({"/internal/collections/claim", "/internal/collections/hidden"}), declared)

    def test_planning_migration_suffix_catalogue_is_exact(self):
        import ast
        from route_conformance import routes_in_openapi
        source = ast.parse((ROOT / "services/planning/src/planning/bootstrap/server.py").read_text())
        variants = next(ast.literal_eval(assignment.value)
                        for assignment in source.body
                        if isinstance(assignment, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == "MIGRATION_SUFFIXES"
                                for t in assignment.targets))
        api = json.loads((ROOT / "contracts/openapi/planning-migration-v1.6.json").read_text())
        contracted = {"/" + path.rsplit("/", 1)[-1]
                      for method, path in routes_in_openapi(api) if method == "POST"}
        self.assertEqual(set(variants), contracted)
        self.assertNotIn("/legacy-migration-inputs", variants)

    def test_composed_python_route_negative_injection(self):
        from route_conformance import compare_composed_routes
        base = {("GET", "/v1/tenants/{tenant}/jobs")}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "contracts/openapi").mkdir(parents=True)
            (root / "contracts/openapi/example.json").write_text(json.dumps({
                "paths": {"/v1/tenants/{tenant}/jobs": {"get": {"responses": {"200": {}}}}}
            }))
            self.assertEqual(compare_composed_routes("Lifecycle", base, ("example.json",), root), 1)
            with self.assertRaisesRegex(ValueError, "Undocumented Lifecycle"):
                compare_composed_routes("Lifecycle", base | {("POST", "/internal/hidden")}, ("example.json",), root)

    def test_actual_native_job_and_worker_effect_route_handlers(self):
        from assurance_routes import prove

        self.assertEqual(verify_lifecycle_native_jobs(ROOT), 4)
        self.assertEqual(verify_lifecycle_worker_effect_routes(ROOT), 2)
        for app, expected in (("lifecycle-native-jobs", 4),
                              ("lifecycle-worker-effects", 2)):
            observations = prove(app, root=ROOT)
            denials = [row for row in observations if row["claim"] == "authorization"]
            self.assertEqual(len(denials), expected)
            self.assertEqual(len([row for row in observations if row["claim"] == "route"]),
                             expected)
            for denial in denials:
                self.assertEqual(denial["source"], "live-denial")
                self.assertEqual(denial["denial_kind"], "invalid-credential")
                self.assertEqual(denial["status_code"], 401)
            self.assertFalse(any(row["claim"] == "tenant_isolation"
                                 for row in observations))


    def test_declared_paths_include_each_method(self):
        spec = {"paths": {"/v1/example": {"get": {}, "post": {}}}}
        self.assertEqual(routes_in_openapi(spec), {
            ("GET", "/v1/example"), ("POST", "/v1/example"),
        })


if __name__ == "__main__":
    unittest.main()
