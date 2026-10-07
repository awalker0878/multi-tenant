"""Prevent development leakage, dropped binary extras and unknown lock semantics."""

import copy
from pathlib import Path
import tomllib
import unittest

from python_lock import production_inventory, target_marker


ROOT = Path(__file__).resolve().parents[2]


class PythonLockTest(unittest.TestCase):
    def project_lock(self, path):
        root = ROOT / path
        return (tomllib.loads((root / "pyproject.toml").read_text())["project"],
                tomllib.loads((root / "uv.lock").read_text()))

    def test_services_select_binary_extra_and_transitive_production_packages(self):
        for service in ("planning", "inventory", "lifecycle"):
            with self.subTest(service=service):
                project, lock = self.project_lock("services/" + service)
                inventory = production_inventory(project, lock)
                expected = {
                    "product-" + service: "0.1.0.dev0", "psycopg": "3.3.6",
                    "psycopg-binary": "3.3.6", "typing-extensions": "4.16.0",
                    "uvicorn": "0.53.0", "click": "8.5.0", "h11": "0.16.0",
                }
                if service == "planning":
                    expected.update({"attrs": "26.1.0", "jsonschema": "4.26.0",
                                     "jsonschema-specifications": "2025.9.1", "pika": "1.4.4",
                                     "referencing": "0.37.0", "rpds-py": "2026.9.1"})
                if service == "inventory":
                    expected["pika"] = "1.4.4"
                if service == "lifecycle":
                    expected.update({"temporalio": "1.34.0", "nexus-rpc": "1.4.0", "protobuf": "7.36.2", "types-protobuf": "7.35.1.20260906"})
                self.assertEqual(inventory, expected)

    def test_workers_keep_only_owned_distribution_and_declared_runtime(self):
        for worker in ("inventory", "lifecycle"):
            with self.subTest(worker=worker):
                project, lock = self.project_lock("workers/" + worker)
                expected = {"product-" + worker + "-worker": "0.1.0.dev0"}
                if worker == "lifecycle":
                    expected.update({"psycopg": "3.3.6", "psycopg-binary": "3.3.6", "typing-extensions": "4.16.0", "uvicorn": "0.53.0", "click": "8.5.0", "h11": "0.16.0"})
                    # Signed P09 adapters verify Ed25519 envelopes in the worker.
                    # Keep the independently expected production closure exact.
                    expected.update({"cryptography": "50.0.2", "cffi": "2.1.1", "pycparser": "3.0"})
                self.assertEqual(production_inventory(project, lock), expected)

    def test_platform_markers_select_only_accepted_linux_cpython_runtime(self):
        self.assertFalse(target_marker("sys_platform == 'win32'"))
        self.assertTrue(target_marker("implementation_name != 'pypy'"))
        for marker in ("python_version >= '3.12'", "sys_platform in 'linux'",
                       "sys_platform == 'linux' or unknown_variable == 'x'"):
            with self.subTest(marker=marker), self.assertRaises(ValueError):
                target_marker(marker)

    def test_unknown_binary_extra_missing_package_or_ambiguous_lock_fails(self):
        project, original = self.project_lock("services/planning")
        for defect in ("extra", "missing", "duplicate", "source"):
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                lock = copy.deepcopy(original)
                psycopg = next(p for p in lock["package"] if p["name"] == "psycopg")
                if defect == "extra":
                    del psycopg["optional-dependencies"]["binary"]
                elif defect == "missing":
                    lock["package"].remove(psycopg)
                elif defect == "duplicate":
                    lock["package"].append(psycopg)
                else:
                    psycopg["source"] = {"git": "https://example.invalid/source"}
                production_inventory(project, lock)


if __name__ == "__main__":
    unittest.main()
