"""Regression tests for the stable CI selector and completion gate."""
import importlib.util
import json
import os
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/ci" / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

class ScopeTests(unittest.TestCase):
    def test_unknown_diff_is_fail_closed(self):
        self.assertTrue(all(module("scope").classify(None).values()))

    def test_docs_only_is_cheap(self):
        lanes = module("scope").classify(["docs/README.md"])
        self.assertTrue(lanes["docs"])
        self.assertFalse(any(lanes[x] for x in ("contracts", "native", "security", "routes", "authority")))

    def test_contracts_requalify_consumers(self):
        lanes = module("scope").classify(["contracts/openapi/planning-v1.2.json"])
        self.assertTrue(all(lanes.values()))

    def test_shared_ci_change_runs_all(self):
        self.assertTrue(all(module("scope").classify([".github/workflows/ci.yml"]).values()))

    def test_python_owner_change_not_laravel_only(self):
        lanes = module("scope").classify(["services/planning/src/planning/owners.py"])
        self.assertTrue(lanes["native"] and lanes["contracts"])
        self.assertFalse(lanes["routes"])

class GateTests(unittest.TestCase):
    def test_skip_only_for_unaffected(self):
        flags = {x: "false" for x in ("docs", "contracts", "security", "native", "authority", "routes")}
        good = {"scope": {"result": "success", "outputs": dict(flags, python="[]", php="[]")}}
        good.update({name: {"result": "skipped"} for name in ("architecture", "contracts", "contract-assurance", "artifact-binding-assurance", "security", "native", "authority", "laravel-routes", "python", "php")})
        check = module("check")
        self.assertEqual(check.verify(good), [])
        good["scope"]["outputs"]["contracts"] = "true"
        self.assertTrue(check.verify(good))
        good["contracts"]["result"] = "success"
        self.assertTrue(check.verify(good))
        good["contract-assurance"]["result"] = "success"
        self.assertTrue(check.verify(good))
        good["artifact-binding-assurance"]["result"] = "success"
        self.assertEqual(check.verify(good), [])
        good["artifact-binding-assurance"]["result"] = "failure"
        self.assertTrue(check.verify(good))
        good["artifact-binding-assurance"]["result"] = "success"
        good["contracts"]["result"] = "failure"
        self.assertTrue(check.verify(good))

if __name__ == "__main__":
    unittest.main()
