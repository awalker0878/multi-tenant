"""Fail-closed contracts for the three VM migration collection manifests.

This verifies the version-controlled collection *requirements*, never native
provider support or whether a candidate field was successfully obtained.
"""

import ast
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "contracts/capabilities/migration-collection-manifest-v1.json"
SCHEMA = ROOT / "contracts/schemas/capabilities/migration-collection-manifest-v1.json"
PLATFORMS = {"vmware", "ahv", "openstack"}
METHODS = {"native_get", "native_list", "derive", "operator", "probe", "independent"}
DOCUMENTED_ONLY = {"native_field_candidate", "external_evidence_required"}
MANDATORY = {
    "application.consistency", "application.datasets", "application.dependencies",
    "application.writer_fencing", "application.outage_objective",
    "application.data_loss_objective", "guest.boot_drivers",
    "recovery.rollback_protocol", "recovery.restore_evidence",
    "network.required_paths", "network.address_ownership",
    "security.tenant_isolation", "security.credential_scope",
    "operations.backup_coverage", "operations.monitoring",
    "operations.cleanup_and_retention", "placement.native_reserved_capacity",
}
SOURCE_DISK = {
    "vmware": {"storage.disk_inventory", "storage.disk_identity", "storage.disk_size",
               "storage.disk_backing_chain", "storage.disk_encryption"},
    "ahv": {"storage.disk_inventory", "storage.disk_capacity",
            "storage.disk_backing_identity", "storage.shared_external"},
    "openstack": {"storage.volume_attachments", "storage.server_volume_refs",
                  "storage.volume_size", "storage.multiattach",
                  "storage.encrypted", "compute.swap_and_ephemeral"},
}
TARGET_MANDATORY = {
    "vmware": {"target.resource_pool", "target.datastore", "target.network_backing",
               "target.compute_capacity", "target.storage_capacity", "target.ovf_import"},
    "ahv": {"target.storage_containers", "target.storage_capacity", "target.subnets",
            "target.security_policy", "target.image_import", "target.vm_creation"},
    "openstack": {"target.flavors", "target.volume_types", "target.network_subnets",
                  "target.security_group_rules", "target.placement_inventory",
                  "target.image_import_methods"},
}


def assignment(path: Path, name: str):
    parsed = ast.parse(path.read_text(encoding="utf-8"))
    for node in parsed.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"No static {name} contract in {path}")


class MigrationCollectionManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_platforms_schema_and_registry_are_exact(self) -> None:
        data, schema = self.data, self.schema
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["manifest_version"], "1.0.0")
        self.assertEqual(data["status"], "requirements_only_not_installed_support")
        self.assertEqual(set(data["platforms"]), PLATFORMS)
        self.assertEqual(
            data["capability_registry"], "contracts/capabilities/definitions-v1.json"
        )
        self.assertTrue((ROOT / data["capability_registry"]).is_file())
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(schema["properties"]["platforms"]["additionalProperties"])
        self.assertEqual(
            set(schema["properties"]["platforms"]["required"]), PLATFORMS
        )
        for platform in PLATFORMS:
            self.assertTrue(data["documentation"][platform])
            self.assertTrue(all(
                ref.startswith("https://") for ref in data["documentation"][platform]
            ))

    def test_every_entry_is_bounded_and_retains_explicit_custody_and_freshness(self) -> None:
        fields = {
            "id", "scope", "api_family", "api_field", "owner_evidence_field",
            "collection_method", "max_age_seconds", "severity", "condition",
            "collector_source", "collection_status",
        }
        for platform, group in self.data["platforms"].items():
            with self.subTest(platform=platform):
                rows = group["attributes"]
                self.assertGreaterEqual(len(rows), 80)
                self.assertEqual(group["source_profile"], "SourceWorkloadProfile")
                self.assertEqual(group["target_profile"], "TargetCapabilityProfile")
                ids = set()
                phases = {"source": 0, "target": 0, "owner": 0}
                for row in rows:
                    self.assertEqual(set(row), fields)
                    key = row["id"]
                    self.assertRegex(key, r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,7}$")
                    self.assertNotIn(key, ids)
                    ids.add(key)
                    self.assertIn(row["scope"], phases)
                    phases[row["scope"]] += 1
                    self.assertIn(row["collection_method"], METHODS)
                    self.assertIn(row["collection_status"], DOCUMENTED_ONLY)
                    self.assertIn(row["severity"], {"critical", "optional"})
                    self.assertIs(type(row["max_age_seconds"]), int)
                    self.assertGreater(row["max_age_seconds"], 0)
                    self.assertLessEqual(row["max_age_seconds"], 86400)
                    self.assertRegex(
                        row["condition"], r"^(always|cutover|when:[a-z][a-z0-9_]*)$"
                    )
                    self.assertTrue((ROOT / row["collector_source"]).is_file())
                    if row["api_family"] is None:
                        self.assertIsNone(row["api_field"])
                        self.assertTrue(row["owner_evidence_field"])
                    else:
                        self.assertIsNone(row["owner_evidence_field"])
                        self.assertTrue(row["api_field"])
                    if row["collection_method"] in {
                        "operator", "independent", "probe"
                    }:
                        self.assertEqual(
                            row["collection_status"], "external_evidence_required"
                        )
                    if row["collection_method"] in {"operator", "independent"}:
                        # Manual and independently measured acceptance is not
                        # masquerading as a vendor API response.
                        self.assertIsNone(row["api_field"])
                        self.assertIsNone(row["api_family"])
                        self.assertTrue(row["owner_evidence_field"])
                self.assertGreaterEqual(phases["source"], 35)
                self.assertGreaterEqual(phases["target"], 14)
                self.assertGreaterEqual(phases["owner"], 23)
                self.assertTrue(MANDATORY <= ids)
                self.assertTrue(SOURCE_DISK[platform] <= ids)
                self.assertTrue(TARGET_MANDATORY[platform] <= ids)

    def test_no_critical_storage_network_security_or_recovery_is_optional(self) -> None:
        for platform, group in self.data["platforms"].items():
            rows = {row["id"]: row for row in group["attributes"]}
            for name in MANDATORY | SOURCE_DISK[platform] | TARGET_MANDATORY[platform]:
                with self.subTest(platform=platform, attribute=name):
                    self.assertEqual(rows[name]["severity"], "critical")
            self.assertEqual(rows["network.firewall_flows"]["severity"], "critical")
            optional = [row for row in rows.values() if row["severity"] == "optional"]
            for row in optional:
                self.assertNotIn(row["condition"], {"always", "cutover"})
                self.assertFalse(row["id"].startswith(("recovery.", "security.")))
            self.assertEqual(rows["compute.power_state"]["max_age_seconds"], 10)
            self.assertLessEqual(rows["network.required_paths"]["max_age_seconds"], 300)
            self.assertLessEqual(rows["security.tenant_isolation"]["max_age_seconds"], 300)
            self.assertLessEqual(
                rows["placement.native_reserved_capacity"]["max_age_seconds"], 15
            )

    def test_native_vm_and_volume_contract_field_names_are_traceable(self) -> None:
        specs = {
            "ahv": (
                ROOT / "workers/inventory/src/inventory_worker/infrastructure/"
                "ahv_source_contract.py", "FIELDS", "vm"
            ),
            "openstack": (
                ROOT / "workers/inventory/src/inventory_worker/infrastructure/"
                "openstack_source_contract.py", "FIELDS", None
            ),
        }
        for platform, (path, symbol, kind) in specs.items():
            expected = assignment(path, symbol)
            names = expected[kind] if kind else (
                *expected["server"], *expected["volume"]
            )
            collected_paths = "\n".join(
                row["api_field"] or ""
                for row in self.data["platforms"][platform]["attributes"]
                if row["scope"] == "source"
            )
            for name in names:
                with self.subTest(platform=platform, native_field=name):
                    self.assertIn(name, collected_paths)

    def test_schemas_prohibit_extra_or_unattributed_fields(self) -> None:
        platforms = self.schema["properties"]["platforms"]["properties"]
        for platform in PLATFORMS:
            record = platforms[platform]["properties"]["attributes"]["items"]
            self.assertFalse(record["additionalProperties"])
            self.assertIn("max_age_seconds", record["required"])
            self.assertIn("severity", record["required"])
            self.assertIn("api_field", record["required"])
            self.assertIn("owner_evidence_field", record["required"])
            self.assertEqual(
                record["properties"]["severity"]["enum"], ["critical", "optional"]
            )
            self.assertEqual(len(record["allOf"]), 3)


if __name__ == "__main__":
    unittest.main()
