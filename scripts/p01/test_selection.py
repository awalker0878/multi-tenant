"""Exercise selection boundaries that could accidentally skip affected builds."""
import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location("p01_selection", Path(__file__).with_name("select_components.py"))
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
COMPONENTS = {
    "console": {"path": "apps/console"},
    "governance": {"path": "services/governance"},
    "inventory": {"path": "services/inventory"},
    "inventory-workers": {"path": "workers/inventory"},
    "planning": {"path": "services/planning"},
    "lifecycle": {"path": "services/lifecycle"},
    "lifecycle-workers": {"path": "workers/lifecycle"},
}


class SelectionTest(unittest.TestCase):
    def test_private_change_does_not_select_other_services(self):
        self.assertEqual(MODULE.select(["services/governance/app/Http/Health.php"], COMPONENTS)[0], ["governance"])

    def test_owner_change_selects_its_worker(self):
        self.assertEqual(MODULE.select(["services/inventory/src/inventory/domain/model.py"], COMPONENTS)[0], ["inventory", "inventory-workers"])

    def test_worker_change_does_not_select_owner_or_peer_worker(self):
        self.assertEqual(MODULE.select(["workers/lifecycle/uv.lock"], COMPONENTS)[0], ["lifecycle-workers"])

    def test_global_inputs_never_skip_registered_components(self):
        for path in ["scripts/p01/candidates.json", "deploy/build/inputs.lock.json", "architecture/context-map.yaml", ".github/workflows/p01-foundations.yml", "scripts/validate_architecture.py"]:
            with self.subTest(path=path):
                self.assertEqual(MODULE.select([path], COMPONENTS)[0], sorted(COMPONENTS))

    def test_deleted_owner_files_and_cross_component_rename_are_both_selected(self):
        paths = ["services/lifecycle/src/lifecycle/old.py", "services/planning/src/planning/new.py"]
        self.assertEqual(MODULE.select(paths, COMPONENTS)[0], ["lifecycle", "lifecycle-workers", "planning"])

    def test_prefix_collision_is_not_an_owned_component(self):
        selected, reason = MODULE.select(["services/planning-extra/source.py"], COMPONENTS)
        self.assertEqual(selected, sorted(COMPONENTS))
        self.assertIn("unregistered", reason)

    def test_docs_only_changes_require_no_package_build(self):
        self.assertEqual(MODULE.select(["next_work.md", "docs/implementation/phases/p01.md"], COMPONENTS)[0], [])

    def test_shared_package_change_selects_consumers_conservatively(self):
        self.assertEqual(MODULE.select(["packages/technical/python/pyproject.toml"], COMPONENTS)[0], sorted(COMPONENTS))

    def test_traversal_and_absolute_inputs_rejected(self):
        for path in ["/services/planning/x.py", "../services/planning/x.py", "services\\planning\\x.py"]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                MODULE.select([path], COMPONENTS)


if __name__ == "__main__":
    unittest.main()
