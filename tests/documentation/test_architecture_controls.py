"""Negative fixtures prove the checks fail; they are not application evidence."""

import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("architecture_validator", ROOT / "scripts/validate_architecture.py")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ArchitectureControlsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = yaml.safe_load((ROOT / "architecture/context-map.yaml").read_text())

    def write(self, path, text):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text)

    def check(self):
        self.write("architecture/context-map.yaml", yaml.safe_dump(self.registry))
        return MODULE.validate(self.root)

    def assertFails(self, fragment):
        result = self.check()
        self.assertTrue(any(fragment in error for error in result.errors), result.errors)

    def test_registry_only_reports_no_product_source(self):
        result = self.check()
        self.assertEqual([], result.errors)
        self.assertEqual(0, result.sources)
        self.assertEqual(7, result.services)

    def test_valid_python_imports_and_relative_imports(self):
        self.write("services/inventory/src/inventory/domain/model.py", "from dataclasses import dataclass\n")
        self.write("services/inventory/src/inventory/application/read.py", "from ..domain.model import Model\n")
        self.write("services/inventory/src/inventory/infrastructure/db.py", "from inventory.application.read import Read\nimport product_contracts\n")
        result = self.check()
        self.assertEqual([], result.errors)
        self.assertEqual(3, result.python_sources)

    def test_cross_context_python_import(self):
        self.write("services/inventory/src/inventory/infrastructure/bad.py", "from planning.domain import Assessment\n")
        self.assertFails("cross-context code import")

    def test_repo_namespace_cannot_bypass_context_namespace(self):
        self.write("services/inventory/src/inventory/infrastructure/bad.py", "from services.planning.src.planning.domain import Assessment\n")
        self.assertFails("bypasses registered namespace")

    def test_inverted_python_layer_import(self):
        self.write("services/inventory/src/inventory/domain/bad.py", "from ..infrastructure.db import Session\n")
        self.assertFails("inverted layer dependency")

    def test_framework_in_core(self):
        self.write("services/inventory/src/inventory/application/bad.py", "from fastapi import Depends\n")
        self.assertFails("external or unresolved import")

    def test_technical_package_cannot_share_business_models(self):
        self.write("packages/technical/python/src/product_technical/shared.py", "from inventory.domain import Workload\n")
        self.assertFails("cross-context code import")

    def test_generated_client_cannot_enter_domain(self):
        self.write("services/inventory/src/inventory/domain/bad.py", "from product_contracts import Workload\n")
        self.assertFails("core layer cannot import")

    def test_unknown_source_root(self):
        self.write("services/unregistered/src/main.py", "pass\n")
        self.assertFails("unregistered source")

    def test_source_cannot_escape_to_unscanned_top_level_directory(self):
        self.write("unregistered/escape.py", "pass\n")
        self.assertFails("unregistered source")

    def test_nested_build_directory_cannot_hide_foreign_import(self):
        self.write("services/inventory/src/inventory/domain/build/escape.py", "from planning.domain import Assessment\n")
        self.assertFails("cross-context code import")

    def test_misplaced_source_inside_registered_service(self):
        self.write("services/governance/app/Models/Grant.php", "<?php class Grant {}\n")
        self.assertFails("outside registered layers/host roots")

    def test_registry_escape(self):
        self.registry["services"][0]["root"] = "../outside"
        self.assertFails("path escapes")

    def test_duplicate_registration(self):
        self.registry["services"].append(copy.deepcopy(self.registry["services"][0]))
        self.assertFails("duplicate registration")

    def test_overlapping_source_roots(self):
        self.registry["workers"][0]["root"] = "workers"
        self.assertFails("Overlapping registered roots")

    def test_package_dependency_cycle(self):
        self.registry["packages"][0]["dependencies"] = ["php-technical"]
        self.registry["packages"][3]["dependencies"] = ["php-contracts"]
        self.assertFails("dependency cycle")

    def test_layer_cycle(self):
        self.registry["layer_policies"]["python"]["domain"]["depends_on"] = ["application"]
        self.assertFails("layer dependency cycle")

    def test_unregistered_dependency(self):
        self.registry["services"][0]["allowed_packages"] += ["governance"]
        self.assertFails("unknown/duplicate package dependency")

    def test_worker_requires_matching_owner(self):
        self.registry["workers"][0]["owner_service_id"] = "planning"
        self.assertFails("invalid worker context ownership")

    def test_worker_can_import_explicitly_included_owner_artifact(self):
        self.write("workers/inventory/src/inventory_worker/execute.py", "from inventory.application import Collect\n")
        self.assertEqual([], self.check().errors)

    def test_worker_cannot_import_foreign_context(self):
        self.write("workers/inventory/src/inventory_worker/execute.py", "from lifecycle.domain import Job\n")
        self.assertFails("cross-context code import")

    def test_owner_source_requires_explicit_inclusion(self):
        self.registry["workers"][0]["include_owner_source"] = False
        self.write("workers/inventory/src/inventory_worker/execute.py", "from inventory.application import Collect\n")
        self.assertFails("cross-context code import")

    def test_php_eloquent_domain_and_framework_action_are_allowed(self):
        self.write("services/governance/app/Domain/Access/Grant.php", """<?php
namespace App\\Domain\\Access;
use Illuminate\\Database\\Eloquent\\Model;
class Grant extends Model { public function revoke(): void {} }
""")
        self.write("services/governance/app/Application/Access/Actions/RevokeGrant.php", """<?php
namespace App\\Application\\Access\\Actions;
use App\\Domain\\Access\\Grant;
use Illuminate\\Support\\Facades\\DB;
use Illuminate\\Support\\Facades\\Gate;
class RevokeGrant { public function handle(int $id): void { Gate::authorize('revoke', Grant::findOrFail($id)); } }
""")
        result = self.check()
        self.assertEqual([], result.errors)
        self.assertEqual(2, result.php_sources)

    def test_php_services_have_independent_local_app_namespaces(self):
        for service in ("governance", "catalogue"):
            self.write(f"services/{service}/app/Application/Access/Actions/ReadGrant.php", """<?php
namespace App\\Application\\Access\\Actions;
use App\\Domain\\Access\\Grant;
class ReadGrant { public function handle(): void {} }
""")
            self.write(f"services/{service}/composer.json", json.dumps({"autoload": {"psr-4": {"App\\": "app/"}}}))
        self.assertEqual([], self.check().errors)

    def test_php_standard_laravel_entrypoints_are_allowed(self):
        entries = {
            "Http/Controllers/GrantController": "use App\\Domain\\Access\\Grant;",
            "Console/Commands/ExpireGrants": "use App\\Application\\Access\\Actions\\RevokeGrant;",
            "Jobs/RevokeGrantJob": "use App\\Application\\Access\\Actions\\RevokeGrant;",
            "Listeners/GrantRevokedListener": "use App\\Application\\Access\\Actions\\RevokeGrant;",
            "Policies/GrantPolicy": "use App\\Domain\\Access\\Grant;",
            "Providers/AppServiceProvider": "use App\\Infrastructure\\Billing\\Gateway;",
        }
        for location, imports in entries.items():
            namespace = "App\\" + location.rsplit("/", 1)[0].replace("/", "\\")
            self.write(f"services/governance/app/{location}.php", f"<?php\nnamespace {namespace};\n{imports}\n")
        self.assertEqual([], self.check().errors)

    def test_php_cross_capability_domain_collaboration_is_allowed(self):
        self.write("services/governance/app/Domain/Access/Grant.php", "<?php\nnamespace App\\Domain\\Access;\nuse App\\Domain\\Tenancy\\Tenant;\n")
        self.assertEqual([], self.check().errors)

    def test_php_domain_cannot_import_application(self):
        self.write("services/governance/app/Domain/Access/Grant.php", "<?php\nnamespace App\\Domain\\Access;\nuse App\\Application\\Access\\Actions\\RevokeGrant;\n")
        self.assertFails("inverted layer dependency domain -> application")

    def test_php_domain_cannot_import_infrastructure(self):
        self.write("services/governance/app/Domain/Access/Grant.php", "<?php\nnamespace App\\Domain\\Access;\nuse App\\Infrastructure\\Billing\\Gateway;\n")
        self.assertFails("inverted layer dependency domain -> infrastructure")

    def test_php_application_cannot_import_infrastructure(self):
        self.write("services/governance/app/Application/Access/Actions/RevokeGrant.php", "<?php\nnamespace App\\Application\\Access\\Actions;\nuse App\\Infrastructure\\Billing\\Gateway;\n")
        self.assertFails("inverted layer dependency application -> infrastructure")

    def test_php_domain_cannot_import_delivery(self):
        self.write("services/governance/app/Domain/Access/Grant.php", "<?php\nnamespace App\\Domain\\Access;\nuse App\\Http\\Controllers\\GrantController;\n")
        self.assertFails("inverted layer dependency domain -> delivery")

    def test_php_application_cannot_import_delivery(self):
        self.write("services/governance/app/Application/Access/Actions/RevokeGrant.php", "<?php\nnamespace App\\Application\\Access\\Actions;\nuse App\\Policies\\GrantPolicy;\n")
        self.assertFails("inverted layer dependency application -> delivery")

    def test_php_shared_package_cannot_import_private_app(self):
        self.write("packages/technical/php/src/Leak.php", "<?php\nnamespace Product\\Technical;\nuse App\\Domain\\Access\\Grant;\n")
        self.assertFails("cross-context code import")

    def test_php_private_service_namespace_is_rejected(self):
        self.write("services/governance/app/Application/Access/Actions/Read.php", "<?php\nnamespace App\\Application\\Access\\Actions;\nuse Product\\Contexts\\Catalogue\\Domain\\Application;\n")
        self.assertFails("private service import bypasses")

    def test_php_source_cannot_claim_foreign_namespace(self):
        self.write("services/governance/app/Domain/Access/Grant.php", "<?php\nnamespace Foreign\\Domain\\Access;\n")
        self.assertFails("namespace does not match")

    def test_php_registry_cannot_hide_domain_in_host_roots(self):
        self.registry["services"][0]["host_roots"].append("app/Domain")
        self.assertFails("host root hides context source")

    def test_php_packages_cannot_claim_local_app_namespace(self):
        self.registry["packages"][0]["namespace"] = "App\\"
        self.assertFails("cannot claim service-local")

    def test_php_capability_directory_is_required(self):
        self.write("services/governance/app/Domain/Grant.php", "<?php\nnamespace App\\Domain;\n")
        self.assertFails("requires a capability directory")

    def test_php_declared_generated_client_is_allowed_in_infrastructure(self):
        self.write("services/governance/app/Infrastructure/Catalogue/Gateway.php", "<?php\nnamespace App\\Infrastructure\\Catalogue;\nuse Product\\Contracts\\Catalogue\\Client;\n")
        self.assertEqual([], self.check().errors)

    def test_php_framework_allowance_does_not_allow_generated_client_in_core(self):
        self.write("services/governance/app/Application/Access/Actions/Read.php", "<?php\nnamespace App\\Application\\Access\\Actions;\nuse Product\\Contracts\\Catalogue\\Client;\n")
        self.assertFails("core layer cannot import")

    def test_php_core_cannot_import_laravel_transport_dependencies(self):
        imports = [
            "Illuminate\\Http\\Request", "Illuminate\\Foundation\\Http\\FormRequest",
            "Illuminate\\Console\\Command", "Illuminate\\Support\\Facades\\Http",
            "Illuminate\\Support\\Facades\\Request", "Illuminate\\Support\\Facades\\Response",
            "Illuminate\\Support\\Facades\\Route",
        ]
        for layer in ("Domain", "Application"):
            for dependency in imports:
                with self.subTest(layer=layer, dependency=dependency):
                    self.write(f"services/governance/app/{layer}/Access/Transport.php", f"<?php\nnamespace App\\{layer}\\Access;\nuse {dependency};\n")
                    self.assertFails("transport dependency is forbidden")
                    (self.root / f"services/governance/app/{layer}/Access/Transport.php").unlink()

    def test_php_transport_dependencies_are_allowed_in_adapters(self):
        self.write("services/governance/app/Infrastructure/Catalogue/Gateway.php", "<?php\nnamespace App\\Infrastructure\\Catalogue;\nuse Illuminate\\Support\\Facades\\Http;\n")
        self.write("services/governance/app/Http/Controllers/GrantController.php", "<?php\nnamespace App\\Http\\Controllers;\nuse Illuminate\\Http\\Request;\n")
        self.assertEqual([], self.check().errors)

    def test_php_undeclared_shared_package_import_is_rejected(self):
        service = next(s for s in self.registry["services"] if s["id"] == "governance")
        service["allowed_packages"] = []
        self.write("services/governance/app/Infrastructure/Catalogue/Gateway.php", "<?php\nnamespace App\\Infrastructure\\Catalogue;\nuse Product\\Contracts\\Catalogue\\Client;\n")
        self.assertFails("undeclared shared package import")

    def test_composer_requires_standard_local_app_mapping(self):
        self.write("services/governance/composer.json", json.dumps({"autoload": {"psr-4": {"App\\": "src/"}}}))
        self.assertFails("PSR-4 mapping required")

    def test_composer_path_dependency_cannot_cross_services(self):
        self.write("services/governance/composer.json", json.dumps({
            "autoload": {"psr-4": {"App\\": "app/"}},
            "repositories": [{"type": "path", "url": "../catalogue"}],
        }))
        self.assertFails("cross-service local dependency")

    def test_composer_path_dependency_accepts_declared_package(self):
        self.write("services/governance/composer.json", json.dumps({
            "autoload": {"psr-4": {"App\\": "app/"}},
            "repositories": [{"type": "path", "url": "../../packages/generated/php"}],
        }))
        self.assertEqual([], self.check().errors)

    def test_manifest_cannot_declare_foreign_service_package(self):
        self.write("services/inventory/pyproject.toml", '[project]\nname = "product-inventory"\ndependencies = ["product-planning>=1"]\n')
        self.assertFails("direct service package dependency")

    def test_optional_dependency_group_cannot_import_foreign_service(self):
        self.write("services/inventory/pyproject.toml", '[project.optional-dependencies]\ndev = ["product-planning"]\n')
        self.assertFails("direct service package dependency")

    def test_python_distribution_alias_cannot_hide_foreign_service(self):
        self.write("services/inventory/pyproject.toml", '[project]\ndependencies = ["Product.Planning>=1"]\n')
        self.assertFails("direct service package dependency")

    def test_duplicate_normalized_python_distribution_registration(self):
        package = next(p for p in self.registry["packages"] if p["id"] == "python-technical")
        package["package_name"] = "Product.Contracts_Python"
        self.assertFails("Duplicate normalized Python package_name")

    def test_setuptools_source_mapping_cannot_escape(self):
        self.write("services/inventory/pyproject.toml", '[tool.setuptools.package-dir]\nplanning = "../planning/src/planning"\n')
        self.assertFails("source mapping escapes")

    def test_versioned_shared_package_dependency_requires_declaration(self):
        service = next(s for s in self.registry["services"] if s["id"] == "governance")
        service["allowed_packages"] = []
        self.write("services/governance/composer.json", json.dumps({
            "autoload": {"psr-4": {"App\\": "app/"}},
            "require": {"product/contracts-php": "^1.0"},
        }))
        self.assertFails("undeclared shared package dependency")

    def test_worker_manifest_can_include_owner_artifact(self):
        self.write("workers/inventory/pyproject.toml", '[project]\nname = "inventory-worker"\ndependencies = ["product-inventory==1.0"]\n')
        self.assertEqual([], self.check().errors)

    def test_composer_autoload_cannot_escape(self):
        self.write("services/governance/composer.json", json.dumps({
            "autoload": {"psr-4": {"App\\": "app/", "Foreign\\": "../catalogue/src/"}},
        }))
        self.assertFails("autoload source escapes")

    def test_manifest_dependency_cannot_escape_repository(self):
        self.write("services/inventory/pyproject.toml", '[project]\nname = "inventory"\ndependencies = ["foreign @ file:../../../outside"]\n')
        self.assertFails("dependency path escapes repository")

    def test_dynamic_loading_rejected(self):
        self.write("services/inventory/src/inventory/infrastructure/bad.py", 'import importlib\nimportlib.import_module("planning.domain")\n')
        self.assertFails("dynamic loading")

    def test_aliased_dynamic_loader_rejected(self):
        self.write("services/inventory/src/inventory/infrastructure/bad.py", 'from importlib import import_module as load\nload("planning.domain")\n')
        self.assertFails("dynamic loading")

    def test_source_symlink_cannot_mount_sibling(self):
        self.write("services/planning/src/planning/domain/item.py", "pass\n")
        link = self.root / "services/inventory/src/inventory/domain"
        link.parent.mkdir(parents=True)
        link.symlink_to(self.root / "services/planning/src/planning/domain", target_is_directory=True)
        self.assertFails("symlinks are forbidden")


if __name__ == "__main__":
    unittest.main()
