"""Static source-to-capability traceability for all three disk migration adapters."""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ADAPTERS = {
    "vmware": {
        "source": "workers/lifecycle/src/lifecycle_worker/infrastructure/vmware_export.py",
        "target": "workers/lifecycle/src/lifecycle_worker/infrastructure/vmware_import.py",
    },
    "openstack": {
        "source": "workers/lifecycle/src/lifecycle_worker/infrastructure/openstack_capture.py",
        "target": "workers/lifecycle/src/lifecycle_worker/infrastructure/openstack_image_import.py",
    },
    "ahv": {
        "source": "workers/lifecycle/src/lifecycle_worker/infrastructure/ahv_capture.py",
        "target": "workers/lifecycle/src/lifecycle_worker/infrastructure/ahv_destination.py",
    },
}


class MigrationApiUsageTests(unittest.TestCase):
    def test_disk_transfer_capability_tags_are_present_in_real_adapter_code(self) -> None:
        self.assertEqual(set(ADAPTERS), {"vmware", "openstack", "ahv"})
        for platform, roles in ADAPTERS.items():
            self.assertEqual(set(roles), {"source", "target"})
            for role, relative in roles.items():
                with self.subTest(platform=platform, role=role):
                    source = ROOT / relative
                    module = ast.parse(source.read_text(encoding="utf-8"))
                    tags = [
                        node.value for node in module.body
                        if isinstance(node, ast.Assign)
                        and any(
                            isinstance(target, ast.Name)
                            and target.id == "MIGRATION_API_CAPABILITIES"
                            for target in node.targets
                        )
                    ]
                    self.assertEqual(len(tags), 1)
                    tag = tags[0]
                    self.assertIsInstance(tag, ast.Call)
                    self.assertIsInstance(tag.func, ast.Name)
                    self.assertEqual(tag.func.id, "frozenset")
                    self.assertEqual(
                        ast.literal_eval(tag.args[0]),
                        {"vm.disk.export" if role == "source" else "vm.disk.import"},
                    )
                    self.assertTrue(
                        any(
                            isinstance(node, ast.Call)
                            and (
                                isinstance(node.func, ast.Attribute)
                                and node.func.attr in {
                                    "request", "post", "submit", "read", "call",
                                    "execute", "get", "create", "import_image",
                                }
                                or isinstance(node.func, ast.Name)
                                and node.func.id in {
                                    "read", "submit", "execute", "create",
                                }
                            )
                            for node in ast.walk(module)
                        ),
                        "No native operation remains in tagged module",
                    )


if __name__ == "__main__":
    unittest.main()
