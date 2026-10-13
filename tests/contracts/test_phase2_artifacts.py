"""Negative assurance tests for derived dependencies and actual runtime artifacts."""
from __future__ import annotations

import base64
import csv
import hashlib
import io
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
from artifact_attestation import check_image, check_wheel, check_console_frontend, compare_runtime_tree, verify_image_process
from aggregate_artifacts import aggregate
from runtime_binding_coverage import verify as verify_runtime_bindings


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

    def verified(self):
        # Synthetic contract fixtures have no executable loader; real CI does.
        with patch("dependency_graph.verify_installed_usage", return_value=1):
            return derive(self.root)

    def _save(self):
        for name, value in (
            ("architecture/contract-consumers.json", self.registry),
            ("architecture/installed-contract-usage.json", self.usage),
        ):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value))

    def test_edges_are_derived_and_typed_without_runtime_inference(self):
        graph = self.verified()
        self.assertEqual(len(graph["edges"]), 2)
        installed = next(x for x in graph["edges"] if x["consumer"] == "console")
        self.assertEqual(installed["kind"], "http")
        self.assertEqual(installed["provider"], "catalogue")
        self.assertEqual(installed["installed_copies"], [self.copy])
        other = next(x for x in graph["edges"] if x["consumer"] == "planning")
        self.assertEqual(other["evidence"], "registry-declaration")

    def test_loader_claim_rejected_without_actual_installed_usage(self):
        with self.assertRaisesRegex(ValueError, "Installed contract usage ledger is invalid"):
            derive(self.root)

    def test_producer_owned_copy_is_local_validation_not_dependency(self):
        self.registry["active_releases"][0]["owner"] = "console"
        self.registry["active_releases"][0]["consumers"] = ["planning"]
        self._save()
        graph = self.verified()
        self.assertEqual(len(graph["edges"]), 1)
        self.assertEqual(graph["summary"]["producer_local_copies"], 1)
        self.assertEqual(graph["producer_local_copies"][0]["copy"], self.copy)

    def test_no_unknown_or_orphaned_installed_copy(self):
        self.registry["active_releases"][0]["consumers"] = ["planning"]
        self._save()
        with self.assertRaisesRegex(ValueError, "Installed consumer omitted"):
            self.verified()
        self.registry["active_releases"][0]["consumers"] = ["console", "planning"]
        self.usage["copies"][0]["canonical"] = "contracts/openapi/other-v1.json"
        self._save()
        with self.assertRaisesRegex(ValueError, "Unknown installed dependency"):
            self.verified()


class ActualConsumerBindingTests(unittest.TestCase):
    def test_active_installed_consumption_uses_release_path_not_alias(self):
        from artifact_attestation import consumed_bindings
        bindings = consumed_bindings("services/planning", ROOT)
        self.assertTrue(bindings)
        self.assertTrue(any(row["evidence"] == "verified-installed-copy" for row in bindings))
        self.assertTrue(all(row["canonical"].startswith("contracts/") for row in bindings))


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
        self.wheel = self.root / "product_planning-0.1.0.dev0-py3-none-any.whl"
        self.source = self.root / "services/planning/src/planning/bootstrap/server.py"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("def serve(): pass\n")
        project = self.root / "services/planning/pyproject.toml"
        project.write_text('[project]\nname = "product-planning"\nversion = "0.1.0.dev0"\n[project.scripts]\nplanning-serve = "planning.bootstrap.server:serve"\n')
        current = self.root / "services/planning/src/planning/infrastructure/inputs/current.json"
        current.parent.mkdir(parents=True)
        current.write_bytes(self.contract)

    def wheel_contents(self, schema=None, extra=None, code=None, tamper_record=False, tamper_scripts=False):
        # A real wheel must carry a complete, correct RECORD and distribution
        # identity; the tests must never pass using a plain zip-shaped fixture.
        dist = "product_planning-0.1.0.dev0.dist-info"
        payloads = {
            "planning/bootstrap/server.py": (
                self.source.read_text() if code is None else code
            ),
            "planning/infrastructure/inputs/current.json": (
                self.contract if schema is None else schema
            ),
            dist + "/METADATA": (
                "Metadata-Version: 2.3\nName: product-planning\nVersion: 0.1.0.dev0\n"
            ),
            dist + "/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
            dist + "/entry_points.txt": (
                "[console_scripts]\nplanning-serve = " +
                ("other.bootstrap:run" if tamper_scripts else "planning.bootstrap.server:serve") +
                "\n"
            ),
        }
        if extra is not None:
            payloads["planning/infrastructure/inputs/orphan.json"] = extra
        record_rows = []
        with zipfile.ZipFile(self.wheel, "w") as archive:
            for name, value in payloads.items():
                content = value.encode("utf-8") if isinstance(value, str) else value
                archive.writestr(name, content)
                digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
                record_rows.append([name, "sha256=" + digest, str(len(content))])
            if tamper_record:
                record_rows[0][1] = "sha256=" + "A" * 43
            record_rows.append([dist + "/RECORD", "", ""])
            buffer = io.StringIO(newline="")
            csv.writer(buffer).writerows(record_rows)
            archive.writestr(dist + "/RECORD", buffer.getvalue())

    def test_wheel_contains_exact_installed_schema_bytes(self):
        self.wheel_contents()
        with patch.dict(os.environ, {"GITHUB_SHA": "a" * 40}), \
                patch("artifact_attestation.expected", return_value=([self.copy], [])), \
                patch("artifact_attestation.consumed_bindings", return_value=[]):
            report = check_wheel("services/planning", self.wheel, self.root)
        self.assertEqual(report["installed_copies"], [self.copy])
        self.assertEqual(len(report["artifact_sha256"]), 64)

    def test_missing_drifting_and_unregistered_wheel_contracts_fail(self):
        with patch.dict(os.environ, {"GITHUB_SHA": "a" * 40}), \
                patch("artifact_attestation.expected", return_value=([self.copy], [])), \
                patch("artifact_attestation.consumed_bindings", return_value=[]):
            self.wheel_contents(schema=b'{"kind":"old"}')
            with self.assertRaisesRegex(ValueError, "stale contract bytes"):
                check_wheel("services/planning", self.wheel, self.root)
            self.wheel_contents(extra=b"{}")
            with self.assertRaisesRegex(ValueError, "unregistered contract"):
                check_wheel("services/planning", self.wheel, self.root)

    def test_wheel_record_and_distribution_identity_are_verified(self):
        with patch.dict(os.environ, {"GITHUB_SHA": "a" * 40}), \
                patch("artifact_attestation.expected", return_value=([self.copy], [])), \
                patch("artifact_attestation.consumed_bindings", return_value=[]):
            wrong_name = self.wheel.with_name("wrong_name-0.1.0.dev0-py3-none-any.whl")
            self.wheel_contents()
            self.wheel.rename(wrong_name)
            with self.assertRaisesRegex(ValueError, "Wheel filename identity"):
                check_wheel("services/planning", wrong_name, self.root)
            wrong_name.rename(self.wheel)
            self.wheel_contents(tamper_scripts=True)
            with self.assertRaisesRegex(ValueError, "console scripts differ"):
                check_wheel("services/planning", self.wheel, self.root)
            self.wheel_contents(tamper_record=True)
            with self.assertRaisesRegex(ValueError, "RECORD digest/size"):
                check_wheel("services/planning", self.wheel, self.root)
            self.wheel_contents()
            with zipfile.ZipFile(self.wheel, "a") as archive:
                archive.writestr("other_module.py", "def run(): pass\n")
            with self.assertRaisesRegex(ValueError, "unreviewed distribution payload"):
                check_wheel("services/planning", self.wheel, self.root)
            self.wheel_contents()
            project = self.root / "services/planning/pyproject.toml"
            project.write_text('[project]\nname = "product-other"\nversion = "0.1.0.dev0"\n')
            with self.assertRaisesRegex(ValueError, "identity differs"):
                check_wheel("services/planning", self.wheel, self.root)

    def test_wheel_code_is_identical_to_reviewed_python_source(self):
        with patch.dict(os.environ, {"GITHUB_SHA": "a" * 40}), \
                patch("artifact_attestation.expected", return_value=([self.copy], [])), \
                patch("artifact_attestation.consumed_bindings", return_value=[]):
            self.wheel_contents(code="def serve(): return 'stale'\n")
            with self.assertRaisesRegex(ValueError, "differs from reviewed Python runtime"):
                check_wheel("services/planning", self.wheel, self.root)
            self.wheel_contents()
            self.source.unlink()
            with self.assertRaisesRegex(ValueError, "differs from reviewed Python runtime"):
                check_wheel("services/planning", self.wheel, self.root)

    def test_wheel_rejects_ambiguous_and_unsafe_zip_entries(self):
        with patch.dict(os.environ, {"GITHUB_SHA": "a" * 40}), \
                patch("artifact_attestation.expected", return_value=([self.copy], [])), \
                patch("artifact_attestation.consumed_bindings", return_value=[]):
            self.wheel_contents()
            with zipfile.ZipFile(self.wheel, "a") as archive:
                archive.writestr("planning/bootstrap/server.py", "def serve(): pass\n")
            with self.assertRaisesRegex(ValueError, "duplicate archive"):
                check_wheel("services/planning", self.wheel, self.root)
            self.wheel_contents()
            with zipfile.ZipFile(self.wheel, "a") as archive:
                archive.writestr("../other.py", "pass")
            with self.assertRaisesRegex(ValueError, "unsafe archive"):
                check_wheel("services/planning", self.wheel, self.root)
            self.wheel_contents()
            with zipfile.ZipFile(self.wheel, "a") as archive:
                link = zipfile.ZipInfo("planning/bootstrap/redirect.py")
                link.create_system = 3
                link.external_attr = 0o120777 << 16
                archive.writestr(link, "server.py")
            with self.assertRaisesRegex(ValueError, "unsafe archive"):
                check_wheel("services/planning", self.wheel, self.root)

    def test_wheel_attestation_requires_a_pinned_commit(self):
        self.wheel_contents()
        with patch.dict(os.environ, {"GITHUB_SHA": "unrecorded"}), \
                self.assertRaisesRegex(ValueError, "exact Git revision"):
            check_wheel("services/planning", self.wheel, self.root)

    def test_artifact_qualification_is_explicit_and_checks_built_image_bindings(self):
        workflow = (ROOT / ".github/workflows/qualification.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("contract-artifacts", workflow)
        self.assertIn("docker build", workflow)
        self.assertIn("aggregate_artifacts.py", workflow)

    def test_compiled_console_bundle_requires_all_manifest_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = root / "manifest.json"
            target = root / "assets/app.js"
            target.parent.mkdir()
            target.write_text("console")
            manifest.write_text(json.dumps({"resources/js/app.ts": {
                "file": "assets/app.js", "css": []}}))
            self.assertEqual(check_console_frontend(root), 1)
            target.unlink()
            with self.assertRaisesRegex(ValueError, "not present"):
                check_console_frontend(root)
            manifest.write_text(json.dumps({"resources/js/app.ts": {
                "file": "../escaped.js"}}))
            with self.assertRaisesRegex(ValueError, "not present"):
                check_console_frontend(root)
            manifest.unlink()
            with self.assertRaisesRegex(ValueError, "lacks compiled Vite manifest"):
                check_console_frontend(root)

    def test_all_shipped_runtime_files_must_match_the_reviewed_source(self):
        source = self.root / "source"
        image = self.root / "image"
        source.mkdir()
        image.mkdir()
        (source / "app.php").write_text("<?php return true;")
        (image / "app.php").write_text("<?php return true;")
        self.assertEqual(compare_runtime_tree(source, image, "php-service"), 1)
        (image / "app.php").write_text("<?php return false;")
        with self.assertRaisesRegex(ValueError, "differs from reviewed runtime source"):
            compare_runtime_tree(source, image, "php-service")
        (image / "app.php").write_text("<?php return true;")
        (image / "unreviewed.sql").write_text("select 1")
        with self.assertRaisesRegex(ValueError, "differs from reviewed runtime source"):
            compare_runtime_tree(source, image, "php-service")

    def test_runtime_extra_symlink_cannot_hide_unreviewed_code(self):
        source = self.root / "source"
        image = self.root / "image"
        source.mkdir()
        image.mkdir()
        (source / "app.php").write_text("<?php return true;")
        (image / "app.php").write_text("<?php return true;")
        (image / "runtime.php").symlink_to("app.php")
        with self.assertRaisesRegex(ValueError, "unreviewed symlink"):
            compare_runtime_tree(source, image, "php-service")

    def test_runtime_bootstrap_cache_is_not_counted_as_authored_source(self):
        source = self.root / "source"
        image = self.root / "image"
        source.mkdir()
        image.mkdir()
        (source / "app.php").write_text("<?php return true;")
        (image / "app.php").write_text("<?php return true;")
        cache = image / "cache"
        cache.mkdir()
        (cache / "services.php").write_text("<?php return [];")
        self.assertEqual(compare_runtime_tree(source, image, "bootstrap", skip_cache=True), 1)
        with self.assertRaisesRegex(ValueError, "differs from reviewed runtime source"):
            compare_runtime_tree(source, image, "bootstrap")

    def test_image_process_identity_is_independently_attested(self):
        runtime = {
            "Config": {
                "User": "10001:10001",
                "Entrypoint": ["/usr/local/bin/service-entrypoint"],
                "Cmd": ["php-fpm", "-F"],
            }
        }
        verify_image_process("apps/console", runtime, self.root)
        forged = json.loads(json.dumps(runtime))
        forged["Config"]["Entrypoint"] = ["/tmp/unreviewed"]
        with self.assertRaisesRegex(ValueError, "runtime entrypoint/command"):
            verify_image_process("apps/console", forged, self.root)
        forged = json.loads(json.dumps(runtime))
        forged["Config"]["User"] = "0:0"
        with self.assertRaisesRegex(ValueError, "runtime user"):
            verify_image_process("apps/console", forged, self.root)
        python_runtime = {
            "Config": {
                "User": "10001:10001",
                "Entrypoint": ["/opt/venv/bin/planning-health"],
                "Cmd": ["liveness"],
            }
        }
        project = self.root / "services/planning/pyproject.toml"
        project.write_text(project.read_text() +
                           'planning-health = "planning.bootstrap.health:main"\n')
        verify_image_process("services/planning", python_runtime, self.root)
        python_runtime["Config"]["Cmd"] = ["serve"]
        with self.assertRaisesRegex(ValueError, "runtime entrypoint/command"):
            verify_image_process("services/planning", python_runtime, self.root)

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




class ReleaseAggregateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.out = self.root / "artifacts"
        self.out.mkdir()
        self.sha = "a" * 40
        folder = self.root / "architecture"
        folder.mkdir()
        (folder / "contract-consumers.json").write_text(json.dumps({
            "active_releases": [{
                "path": "contracts/openapi/foundation-health-v1.json",
                "owner": "contract-platform", "consumers": ["a", "b"],
            }],
        }))
        self.owned = {
            "key": '["a","GET","/v1/owned"]',
            "release": "contracts/openapi/owned.json",
            "release_sha256": "a" * 64, "operation_id": "owned",
        }
        self.foundation = {
            "key": '["contract-platform","GET","/health/live"]',
            "release": "contracts/openapi/foundation-health-v1.json",
            "release_sha256": "b" * 64, "operation_id": "health",
        }
        self.components = {
            "services/a": ("a", "python"),
            "services/b": ("b", "php"),
        }
        self.foundation_path = "contracts/openapi/foundation-health-v1.json"
        foundation_source = self.root / self.foundation_path
        foundation_source.parent.mkdir(parents=True, exist_ok=True)
        foundation_source.write_text('{"openapi":"3.1.0"}')
        self.foundation_digest = hashlib.sha256(foundation_source.read_bytes()).hexdigest()
        self.consumed = {
            component: [{
                "canonical": self.foundation_path,
                "canonical_sha256": self.foundation_digest,
                "evidence": "declared-consumption-only",
                "operation_keys": [self.foundation["key"]],
            }] for component in self.components
        }
        self.emit("a-image.json", "services/a", "a", "oci", [self.owned])
        self.emit("a-wheel.json", "services/a", "a", "wheel", [self.owned])
        self.emit("b-image.json", "services/b", "b", "oci", [])

    def emit(self, name, component, owner, kind, operations):
        (self.out / name).write_text(json.dumps({
            "component": component,
            "owner": owner,
            "kind": kind,
            "source_revision": self.sha,
            "artifact_sha256": "c" * 64,
            "installed_copies": [],
            "owner_operations": operations,
            "consumed_releases": self.consumed.get(component, []),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        }))

    def call(self):
        rows = [dict(self.owned, owner="a"), dict(self.foundation, owner="contract-platform")]
        def owned(component, root):
            return ([], [self.owned] if component == "services/a" else [])
        with patch("aggregate_artifacts.COMPONENTS", self.components):
            with patch("aggregate_artifacts.expected", side_effect=owned):
                with patch("aggregate_artifacts.consumed_bindings", side_effect=lambda component, root: self.consumed.get(component, [])):
                    with patch("aggregate_artifacts.inventory", return_value={"operations": rows}):
                        return aggregate(self.out, self.root, self.sha)

    def test_all_images_and_wheels_are_required_and_release_bound(self):
        report = self.call()
        self.assertEqual(report["summary"]["runtime_images"], 2)
        self.assertEqual(report["summary"]["contracted_http_operations"], 2)
        self.assertEqual(report["summary"]["shared_foundation_operations"], 1)
        self.assertEqual(report["summary"]["active_releases"], 1)
        self.assertEqual(len(report["release_bindings"][0]["relationships"]), 2)
        (self.out / "a-wheel.json").unlink()
        with self.assertRaisesRegex(ValueError, "Missing/extra release runtime"):
            self.call()


    def test_non_http_releases_get_source_pinned_image_bindings(self):
        schema_path = "contracts/schemas/current-capability-v1.json"
        file = self.root / schema_path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('{"type":"object","additionalProperties":false}')
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        registry = self.root / "architecture/contract-consumers.json"
        document = json.loads(registry.read_text())
        document["active_releases"].append({
            "path": schema_path, "owner": "a", "consumers": ["b"]
        })
        registry.write_text(json.dumps(document))
        self.consumed["services/b"].append({
            "canonical": schema_path, "canonical_sha256": digest,
            "evidence": "declared-consumption-only", "operation_keys": [],
        })
        self.emit("b-image.json", "services/b", "b", "oci", [])
        result = self.call()
        self.assertEqual(result["summary"]["non_http_releases"], 1)
        release = next(row for row in result["release_bindings"]
                       if row["canonical"] == schema_path)
        self.assertEqual(release["canonical_sha256"], digest)
        self.assertEqual([row["role"] for row in release["relationships"]],
                         ["producer", "consumer"])
        self.assertTrue(all(row["binding_evidence"] == "registry-declaration-only"
                            for row in release["relationships"]))
        self.assertTrue(all(len(row["runtime_image_sha256"]) == 64
                            for row in release["relationships"]))

    def test_source_only_shared_release_is_recorded_without_fake_runtime(self):
        schema = "contracts/schemas/common/error-v2.json"
        target = self.root / schema
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('{"type":"object"}')
        registry = self.root / "architecture/contract-consumers.json"
        document = json.loads(registry.read_text())
        document["active_releases"].append({
            "path": schema, "owner": "contract-platform", "consumers": []
        })
        registry.write_text(json.dumps(document))
        result = self.call()
        release = next(item for item in result["release_bindings"]
                       if item["canonical"] == schema)
        self.assertTrue(release["source_only"])
        self.assertEqual(release["relationships"], [])
        self.assertEqual(result["summary"]["source_only_releases"], 1)

    def test_non_http_binding_refuses_unmapped_owner(self):
        schema = "contracts/schemas/orphan-v1.json"
        file = self.root / schema
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("{}")
        registry = self.root / "architecture/contract-consumers.json"
        document = json.loads(registry.read_text())
        document["active_releases"].append({
            "path": schema, "owner": "unknown-owner", "consumers": []
        })
        registry.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError, "no attested runtime"):
            self.call()

    def test_previous_ci_run_attestation_is_rejected(self):
        with patch.dict(os.environ, {
            "GITHUB_ACTIONS": "true",
            "GITHUB_RUN_ID": "991",
            "GITHUB_RUN_ATTEMPT": "2",
        }):
            with self.assertRaisesRegex(ValueError, "different CI run"):
                self.call()
            for file in self.out.glob("*.json"):
                data = json.loads(file.read_text())
                data["github_run_id"] = "991"
                data["github_run_attempt"] = "2"
                file.write_text(json.dumps(data))
            report = self.call()
            self.assertEqual(report["github_run_id"], "991")
            file = self.out / "b-image.json"
            data = json.loads(file.read_text())
            data["github_run_attempt"] = "1"
            file.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "different CI run"):
                self.call()

    def test_wrong_digest_or_revision_cannot_be_admitted(self):
        file = self.out / "a-image.json"
        changed = json.loads(file.read_text())
        changed["owner_operations"][0]["release_sha256"] = "d" * 64
        file.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, "does not match active source"):
            self.call()
        changed["owner_operations"][0]["release_sha256"] = "a" * 64
        changed["source_revision"] = "e" * 40
        file.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, "does not match active source"):
            self.call()




class PhpMigrationArtifactTests(unittest.TestCase):
    def test_all_deployed_php_owners_copy_database_into_images(self):
        from artifact_attestation import COMPONENTS
        php = [path for path, (_owner, kind) in COMPONENTS.items()
               if kind == "php"]
        self.assertEqual(set(php), {"apps/console", "services/governance",
                                    "services/catalogue", "services/assurance"})
        for component in php:
            with self.subTest(component=component):
                self.assertTrue((ROOT / component / "database/migrations").is_dir())
                dockerfile = (ROOT / component / "Dockerfile").read_text()
                self.assertIn("COPY --from=dependencies /app/database/ ./database/", dockerfile)


class RuntimeWorkflowTests(unittest.TestCase):
    def test_real_workflow_runs_builds_attestation_and_aggregation(self):
        result = verify_runtime_bindings(ROOT)
        self.assertGreater(result["bound_http_operations"], 0)
        self.assertEqual(result["unmapped_owner_operations"], [])

    def test_missing_aggregate_execution_is_rejected(self):
        import yaml
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workflow = yaml.safe_load((ROOT / ".github/workflows/qualification.yml").read_text())
            workflow["jobs"]["aggregate-bindings"]["steps"] = [
                step for step in workflow["jobs"]["aggregate-bindings"]["steps"]
                if "aggregate_artifacts.py" not in str(step.get("run", ""))
            ]
            target = root / ".github/workflows/qualification.yml"
            target.parent.mkdir(parents=True)
            target.write_text(yaml.safe_dump(workflow))
            with (patch("runtime_binding_coverage.inventory", return_value={"operations": []}),
                  patch("runtime_binding_coverage.verify_installed_usage"),
                  patch("runtime_binding_coverage.COMPONENTS", {})):
                registry = root / "architecture/contract-consumers.json"
                registry.parent.mkdir(parents=True)
                registry.write_text('{"active_releases": []}')
                with self.assertRaisesRegex(ValueError, "does not aggregate measured"):
                    verify_runtime_bindings(root)

if __name__ == "__main__":
    unittest.main()
