"""Cross-platform field crosswalk coverage and unsafe-equivalence regression."""

import copy
import unittest

from validate_migration_field_crosswalk import CROSSWALK, MANIFEST, load, validate

PLATFORMS = ("vmware", "ahv", "openstack")


class MigrationFieldCrosswalkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = load(MANIFEST)
        cls.crosswalk = load(CROSSWALK)
        cls.by_id = {
            row["canonical_id"]: row for row in cls.crosswalk["fields"]
        }

    def test_exact_source_attribute_coverage(self) -> None:
        report = validate(self.source, self.crosswalk)
        self.assertEqual(report, {"fields": 278, "groups": 115})
        self.assertEqual(
            set(self.crosswalk["summary"]["manifest_fields"]), set(PLATFORMS)
        )

    def test_cpu_memory_power_have_explicit_normalization(self) -> None:
        fields = {
            "source.vm.vcpu_total": "ahv_cpu_topology_product",
            "source.vm.memory_mib": "bytes_to_mib_exact",
            "source.vm.power_state": "power_state_to_on_off",
            "source.nic.mac": "canonical_mac_and_collision_check",
        }
        for key, strategy in fields.items():
            with self.subTest(key=key):
                row = self.by_id[key]
                self.assertEqual(row["relationship"], "normalize")
                self.assertEqual(row["normalization"], strategy)
                self.assertEqual(set(row["platforms"]), set(PLATFORMS))
                self.assertTrue(all(row["platforms"][p] for p in PLATFORMS))
                self.assertEqual(row["qualification"], "not_qualified")

    def test_disks_security_and_incarnation_do_not_claim_equivalence(self) -> None:
        names = (
            "source.vm.incarnation", "source.vm.disk.backing",
            "source.disk.capture_method", "source.disk.encryption",
            "source.nic.attachment", "target.network.security_policy",
            "target.network.isolation", "target.storage.free_bytes",
            "target.vm.create",
        )
        for name in names:
            with self.subTest(name=name):
                row = self.by_id[name]
                self.assertEqual(row["relationship"], "conditional")
                self.assertEqual(row["criticality"], "critical")
                self.assertEqual(
                    row["migration_policy"], "independent_qualification_required"
                )
                self.assertEqual(row["qualification"], "not_qualified")
                self.assertGreaterEqual(len(row["semantic_constraints"]), 25)

    def test_missing_platform_fields_are_explicit_unknown(self) -> None:
        self.assertIsNone(
            self.by_id["source.guest.secure_boot"]["platforms"]["openstack"]
        )
        self.assertIsNone(
            self.by_id["source.vm.bios_uuid"]["platforms"]["openstack"]
        )
        self.assertIsNone(
            self.by_id["source.vm.host"]["platforms"]["openstack"]
        )
        self.assertIsNone(
            self.by_id["target.image.ingest"]["platforms"]["vmware"]
        )
        self.assertEqual(
            self.by_id["source.nic.security"]["relationship"],
            "platform_specific",
        )
        self.assertEqual(
            self.by_id["source.nic.security"]["criticality"], "critical"
        )

    def test_policy_flow_and_capacity_owner_review_is_not_optional(self) -> None:
        for key in (
            "owner.network.firewall_flows",
            "owner.network.required_paths",
            "owner.security.tenant_isolation",
            "owner.placement.native_reserved_capacity",
        ):
            row = self.by_id[key]
            self.assertEqual(row["criticality"], "critical")
            self.assertEqual(row["relationship"], "owner_common")
            self.assertTrue(all(row["platforms"][p] for p in PLATFORMS))
        self.assertEqual(
            self.by_id["owner.placement.native_reserved_capacity"][
                "maximum_age_seconds"
            ],
            15,
        )

    def test_bad_reference_and_duplicate_field_fail_closed(self) -> None:
        for corruption in ("missing", "duplicate", "changed_api_field", "less_strict_age",
                           "silent_qualification", "downgrade_criticality"):
            with self.subTest(corruption=corruption):
                rows = copy.deepcopy(self.crosswalk)
                item = rows["fields"][0]
                vm = item["platforms"]["vmware"]
                if corruption == "missing":
                    item["platforms"]["vmware"] = None
                elif corruption == "duplicate":
                    vm["manifest_attribute_ids"].append(vm["manifest_attribute_ids"][0])
                elif corruption == "changed_api_field":
                    vm["api_fields"][0] = "fabricated.native.property"
                elif corruption == "less_strict_age":
                    vm["max_age_seconds"] += 1
                elif corruption == "silent_qualification":
                    item["qualification"] = "supported"
                else:
                    item["criticality"] = "optional"
                with self.assertRaises(ValueError):
                    validate(self.source, rows)

    def test_platform_specific_entries_do_not_claim_target_support(self) -> None:
        for row in self.crosswalk["fields"]:
            if row["relationship"] != "platform_specific":
                continue
            self.assertEqual(
                sum(row["platforms"][p] is not None for p in PLATFORMS), 1
            )
            self.assertEqual(row["qualification"], "not_qualified")
        for platform in PLATFORMS:
            self.assertEqual(
                self.crosswalk["summary"]["manifest_fields"][platform]["matched"],
                len(self.source["platforms"][platform]["attributes"]),
            )


if __name__ == "__main__":
    unittest.main()
