"""Negative assurance tests for derived dependencies and actual runtime artifacts."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/contracts"))
from dependency_graph import derive
from artifact_attestation import check_image, check_wheel


class DependencyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = "contracts/openapi/source-v1.json"
        self.copy = "apps/console/resources/contracts/source-v1.json"
        for filename in (self.path, self.copy):
            item = self.root / filename
            item.parent.mkdir(parents=True, exist_ok=True)
            item.write_text('{"openapi":"3.1.0"}')
        self.registry = {"active_releases": [{
            "path": self.path, "owner": "catalogue",
            "consumers": ["console", "planning"],
            "copies": [self.copy],
        }]}
        self.usage = {"copies": [{"copy": self.copy, "canonical": self.path}]}
        self._save()

    def _save(self):
        for name, value in (
            ("architecture/contract-consumers.json", self.registry),
            ("architecture/installed-contract-usage.json", self.usage),
        ):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value))

    def test_edges_are_derived_and_typed_without_runtime_inference(self):
        graph = derive(self.root)
        self.assertEqual(len(graph["edges"]), 2)
        installed = next(x for x in graph["edges"] if x["consumer"] == "console")
        self.assertEqual(installed["kind"], "http")
        self.assertEqual(installed["provider"], "catalogue")
        self.assertEqual(installed["installed_copies"], [self.copy])
        other = next(x for x in graph["edges"] if x["consumer"] == "planning")
        self.assertEqual(other["evidence"], "registry-declaration")

    def test_producer_owned_copy_is_local_validation_not_dependency(self):
        self.registry["active_releases"][0]["owner"] = "console"
        self.registry["active_releases"][0]["consumers"] = ["planning"]
        self._save()
        graph = derive(self.root)
        self.assertEqual(len(graph["edges"]), 1)
        self.assertEqual(graph["summary"]["producer_local_copies"], 1)
        self.assertEqual(graph["producer_local_copies"][0]["copy"], self.copy)

    def test_no_unknown_or_orphaned_installed_copy(self):
        self.registry["active_releases"][0]["consumers"] = ["planning"]
        self._save()
        with self.assertRaisesRegex(ValueError, "Installed consumer omitted"):
            derive(self.root)
        self.registry["active_releases"][0]["consumers"] = ["console", "planning"]
        self.usage["copies"][0]["canonical"] = "contracts/openapi/other-v1.json"
        self._save()
        with self.assertRaisesRegex(ValueError, "Unknown installed dependency"):
            derive(self.root)


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.contract = b'{"kind":"current"}'
        self.copy = {
            "path": "services/planning/src/planning/infrastructure/inputs/current.json",
            "canonical": "contracts/schemas/current.json",
            "sha256": hashlib.sha256(self.contract).hexdigest(),
        }
        self.wheel = self.root / "product_planning-0.1.0-py3-none-any.whl"

    def wheel_contents(self, schema=None, extra=None):
        with zipfile.ZipFile(self.wheel, "w") as archive:
            archive.writestr("planning/bootstrap/server.py", "def serve(): pass\n")
            archive.writestr("planning/infrastructure/inputs/current.json",
                             self.contract if schema is None else schema)
            if extra is not None:
                archive.writestr("planning/infrastructure/inputs/orphan.json", extra)

    def test_wheel_contains_exact_installed_schema_bytes(self):
        self.wheel_contents()
        with patch("artifact_attestation.expected", return_value=([self.copy], [])), \
                patch("artifact_attestation.consumed_bindings", return_value=[]):
            report = check_wheel("services/planning", self.wheel, self.root)
        self.assertEqual(report["installed_copies"], [self.copy])
        self.assertEqual(len(report["artifact_sha256"]), 64)

    def test_missing_drifting_and_unregistered_wheel_contracts_fail(self):
        with patch("artifact_attestation.expected", return_value=([self.copy], [])), \
                patch("artifact_attestation.consumed_bindings", return_value=[]):
            self.wheel_contents(schema=b'{"kind":"old"}')
            with self.assertRaisesRegex(ValueError, "stale contract bytes"):
                check_wheel("services/planning", self.wheel, self.root)
            self.wheel_contents(extra=b"{}")
            with self.assertRaisesRegex(ValueError, "unregistered contract"):
                check_wheel("services/planning", self.wheel, self.root)

    def test_oci_image_requires_exact_source_sha_label(self):
        fake = [{
            "Id": "sha256:" + "e" * 64,
            "Config": {"Labels": {
                "org.opencontainers.image.revision": "a" * 40,
            }},
        }]
        with patch("artifact_attestation.expected", return_value=([], [])):
            with patch("artifact_attestation.run", return_value=json.dumps(fake)):
                with patch.dict(os.environ, {"GITHUB_SHA": "b" * 40}):
                    with self.assertRaisesRegex(ValueError, "revision does not match"):
                        check_image("services/inventory", "test-image", self.root)


if __name__ == "__main__":
    unittest.main()
