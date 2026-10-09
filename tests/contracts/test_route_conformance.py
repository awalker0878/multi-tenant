"""Synthetic canaries for actual HTTP router vs immutable published OpenAPI."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/contracts"))
from route_conformance import compare_declared, routes_in_laravel, routes_in_openapi


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

    def test_declared_paths_include_each_method(self):
        spec = {"paths": {"/v1/example": {"get": {}, "post": {}}}}
        self.assertEqual(routes_in_openapi(spec), {
            ("GET", "/v1/example"), ("POST", "/v1/example"),
        })


if __name__ == "__main__":
    unittest.main()
