"""Static cross-context contract drift test: no owner supplies native grants.

A source-bound check, *not* native E3/E4 evidence. Does not exercise external
owner ports or claim any runtime capability has been qualified.
"""

import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "contracts/schemas/planning/migration-readiness-v1.json"
PLANNING = ROOT / "services/planning/src/planning/domain/migration_readiness.py"
LIFECYCLE = ROOT / "services/lifecycle/src/lifecycle/domain/migration_readiness.py"
CONSOLE = ROOT / "apps/console/resources/js/pages/planning/MigrationSupport.vue"


def literal_keys(path: Path, name: str) -> set[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(module):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            return set(ast.literal_eval(node.value))
        if (isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name) and node.target.id == name
                and isinstance(node.value, ast.Dict)):
            return {ast.literal_eval(key) for key in node.value.keys}
    raise AssertionError(f"No static {name} keys found in {path}")


class ResolvedMigrationReadinessContractTests(unittest.TestCase):
    def test_planning_lifecycle_and_wire_schema_share_exact_keys(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        produced = literal_keys(PLANNING, "result") | {"readiness_sha256"}
        consumed = literal_keys(LIFECYCLE, "REQUIRED")
        self.assertEqual(set(schema["required"]), produced)
        self.assertEqual(consumed, produced)
        self.assertEqual(set(schema["properties"]), produced)
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        self.assertEqual(schema["properties"]["kind"]["const"], "migration_route_readiness")

    def test_execution_authority_is_not_created_by_readiness(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        for key in ("native_write_authorized", "workload_admission_authorized"):
            self.assertEqual(schema["properties"][key]["const"], False)
        planning = PLANNING.read_text(encoding="utf-8")
        lifecycle = LIFECYCLE.read_text(encoding="utf-8")
        console = CONSOLE.read_text(encoding="utf-8")
        self.assertIn('"native_write_authorized": False', planning)
        self.assertIn('"workload_admission_authorized": False', planning)
        self.assertIn('verify_migration_readiness(', (
            ROOT / "services/lifecycle/src/lifecycle/infrastructure/native_owners.py"
        ).read_text(encoding="utf-8"))
        self.assertIn("readiness_sha256", console)
        self.assertIn("readiness.get(\"status\")", (
            ROOT / "services/planning/src/planning/application/validation.py"
        ).read_text(encoding="utf-8"))
        self.assertIn('route_api_usage_manifest_required', planning)
        self.assertIn('migration_readiness_installation_changed', lifecycle)


if __name__ == "__main__":
    unittest.main()
