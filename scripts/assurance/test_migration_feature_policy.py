"""Contract tests for nine-direction migration feature mapping and Console owner input split.

These are E2 catalogue tests; passing does not grant migration eligibility.
"""

import copy
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPABILITIES = ROOT / "contracts/capabilities"
SOURCE = CAPABILITIES / "migration-collection-manifest-v1.json"
CROSSWALK = CAPABILITIES / "migration-field-crosswalk-v1.json"
POLICY = CAPABILITIES / "migration-feature-policy-v1.json"
CONSOLE = ROOT / "apps/console/resources/contracts/migration-feature-policy-v1.json"
PAGE = ROOT / "apps/console/resources/js/pages/inventory/Migration.vue"
BACKEND = ROOT / "services/inventory/src/inventory/domain/workload.py"
READINESS = ROOT / "services/inventory/src/inventory/domain/operator_inputs.py"
CRITICAL_FEATURES = {
    "vm.power", "vm.compute", "vm.placement", "guest.firmware", "guest.drivers",
    "storage.disks", "storage.controller", "storage.sharing", "storage.encryption",
    "storage.target", "storage.transfer", "network.nics", "network.routing",
    "network.flows", "network.security", "security.scope", "app.datasets",
    "app.consistency", "app.dependencies", "app.objectives", "app.validation",
    "cutover.writer", "recovery.restore", "recovery.retention",
}
SAFETY_OWNER = {
    "application.consistency", "application.datasets", "application.dependencies",
    "application.writer_fencing", "application.outage_objective",
    "application.data_loss_objective", "guest.boot_drivers",
    "recovery.rollback_protocol", "recovery.restore_evidence",
    "network.required_paths", "network.firewall_flows",
    "security.tenant_isolation", "security.credential_scope",
    "placement.native_reserved_capacity",
}
PLATFORMS = ("vmware", "ahv", "openstack")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(policy, crosswalk, manifest):
    if (
        policy["schema_version"] != 1
        or policy["version"] != "1.0.0"
        or policy["status"] != "proposed_not_qualified"
    ):
        raise ValueError("policy_identity_or_qualification_changed")
    feature_ids = set()
    seen = set()
    by_feature = {}
    by_crosswalk = {row["canonical_id"]: row for row in crosswalk["fields"]}
    for feature in policy["features"]:
        key = feature["id"]
        if key in feature_ids:
            raise ValueError("duplicate_feature")
        feature_ids.add(key)
        by_feature[key] = feature
        if feature["qualification"] != "unqualified":
            raise ValueError("feature_cannot_self_qualify")
        rows = feature["crosswalk_groups"]
        if not rows or len(rows) != len(set(rows)):
            raise ValueError("feature_unmapped")
        for name in rows:
            if name not in by_crosswalk or name in seen:
                raise ValueError("crosswalk_missing_or_duplicate")
            seen.add(name)
        expected = (
            "critical" if any(by_crosswalk[n]["criticality"] == "critical" for n in rows)
            else "optional"
        )
        if feature["criticality"] != expected:
            raise ValueError("criticality_downgrade")
    if seen != set(by_crosswalk):
        raise ValueError("crosswalk_coverage_incomplete")
    owner_rows = {
        row["canonical_id"].removeprefix("owner."): row
        for row in crosswalk["fields"] if row["scope"] == "owner"
    }
    operator_ids = set()
    backend = BACKEND.read_text(encoding="utf-8")
    readiness = READINESS.read_text(encoding="utf-8")
    # Fields are maintained by the existing Inventory owners. Reference only
    # exact reviewed names and do not introduce unimplemented Console answers.
    for obligation in policy["operator_requirements"]:
        key = obligation["attribute_id"]
        if key in operator_ids or key not in owner_rows:
            raise ValueError("operator_owner_field_missing_or_duplicate")
        operator_ids.add(key)
        canonical = owner_rows[key]
        if obligation["feature_id"] not in by_feature or (
            canonical["canonical_id"] not in by_feature[obligation["feature_id"]][
                "crosswalk_groups"
            ]
        ):
            raise ValueError("operator_feature_binding_changed")
        if (
            obligation["criticality"] != canonical["criticality"]
            or obligation["max_age_seconds"] != canonical["maximum_age_seconds"]
            or obligation["condition"] != canonical["platforms"]["vmware"]["conditions"][0]
        ):
            raise ValueError("operator_criticality_freshness_or_condition_changed")
        review = obligation["review_field"]
        readiness_field = obligation["readiness_field"]
        if review is not None and review != "datasets":
            family, name = review.split(".", 1)
            if family not in {"owner_inputs", "objectives"} or (
                family == "owner_inputs" and f'"{name}"' not in backend
            ) or (family == "objectives" and f'"{name}"' not in backend):
                raise ValueError("console_review_input_not_implemented")
        if readiness_field is not None and f'"{readiness_field}"' not in readiness:
            raise ValueError("console_readiness_input_not_implemented")
        if obligation["evidence_owner"] == "independent" and (
            obligation["verification"] != "independent_verification"
            or readiness_field is None
        ):
            raise ValueError("independent_review_cannot_be_operator_asserted")
        if obligation["evidence_owner"] == "optional_e4_omission" and (
            obligation["criticality"] != "optional"
            or obligation["review_field"] is not None
            or obligation["readiness_field"] is not None
            or obligation["verification"] != "e4_approved_suppression"
        ):
            raise ValueError("unsafe_optional_omission")
    if set(owner_rows) != operator_ids:
        raise ValueError("operator_obligations_uncovered")
    for f in policy["features"]:
        ids = [x["attribute_id"] for x in policy["operator_requirements"]
               if x["feature_id"] == f["id"]]
        if ids != f["operator_attributes"]:
            raise ValueError("operator_feature_summary_drift")
    by_platform = {
        p: {x["id"] for x in manifest["platforms"][p]["attributes"]}
        for p in PLATFORMS
    }
    keys = set()
    for direction in policy["directions"]:
        source, target = direction["source"], direction["target"]
        if source not in PLATFORMS or target not in PLATFORMS:
            raise ValueError("direction_invalid")
        pair = (source, target)
        if pair in keys:
            raise ValueError("direction_duplicate")
        keys.add(pair)
        plans = direction["features"]
        if set(f["feature_id"] for f in plans) != feature_ids or len(plans) != len(feature_ids):
            raise ValueError("direction_feature_coverage")
        for item in plans:
            feature = by_feature[item["feature_id"]]
            rows = [by_crosswalk[n] for n in feature["crosswalk_groups"]]
            expected_source = [
                id for row in rows if row["scope"] == "source"
                for id in ((row["platforms"][source] or {}).get("manifest_attribute_ids") or [])
            ]
            expected_target = [
                id for row in rows if row["scope"] == "target"
                for id in ((row["platforms"][target] or {}).get("manifest_attribute_ids") or [])
            ]
            if item["source_attributes"] != expected_source or item["target_attributes"] != expected_target:
                raise ValueError("direction_field_provenance_changed")
            if set(item["source_attributes"]) - by_platform[source] or (
                set(item["target_attributes"]) - by_platform[target]
            ):
                raise ValueError("direction_cross_tenant_field")
            missing = (
                (any(row["scope"] == "source" for row in rows) and not expected_source)
                or (any(row["scope"] == "target" for row in rows) and not expected_target)
            )
            proposal = (
                "no_direct_field_qualified_alternative_required" if missing
                else "normalize_data_revalidate" if feature["mapping"] == "normalize_with_recheck"
                else "optional_requires_e4_if_omitted" if feature["mapping"] == "conditional_optional"
                else "operator_plus_native_proof" if feature["mapping"] == "operator_and_native"
                else "qualified_adapter_required"
            )
            if item["mapping_proposal"] != proposal or item["admission"] != (
                "unknown_requires_installed_qualification"
            ):
                raise ValueError("direction_cannot_grant_support")
    if keys != {(source, target) for source in PLATFORMS for target in PLATFORMS}:
        raise ValueError("nine_directions_not_covered")
    return len(feature_ids), len(operator_ids)


class FeaturePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load(POLICY)
        cls.crosswalk = load(CROSSWALK)
        cls.manifest = load(SOURCE)

    def test_mandatory_feature_classification_and_every_direction(self):
        features, operator = validate(self.policy, self.crosswalk, self.manifest)
        self.assertEqual((features, operator), (30, 27))
        rows = {x["id"]: x for x in self.policy["features"]}
        self.assertTrue(all(rows[x]["criticality"] == "critical" for x in CRITICAL_FEATURES))
        self.assertEqual(rows["metadata.optional"]["criticality"], "optional")

    def test_console_projection_stays_exactly_in_sync(self):
        self.assertEqual(POLICY.read_bytes(), CONSOLE.read_bytes())
        page = PAGE.read_text(encoding="utf-8")
        for value in (
            "migration-feature-policy-v1.json",
            "operatorObligations",
            "requiredReviewMissing",
            "reviewInputSupplied",
            "operator-inputs",
        ):
            self.assertIn(value, page)

    def test_mandatory_operator_evidence_cannot_be_downgraded(self):
        lookup = {x["attribute_id"]: x for x in self.policy["operator_requirements"]}
        for key in SAFETY_OWNER:
            self.assertEqual(lookup[key]["criticality"], "critical")
        for key in ("security.tenant_isolation", "network.firewall_flows",
                    "placement.native_reserved_capacity", "recovery.restore_evidence"):
            self.assertEqual(lookup[key]["evidence_owner"], "independent")

    def test_cold_export_delta_is_conditional_not_silently_approved(self):
        delta = next(x for x in self.policy["operator_requirements"]
                     if x["attribute_id"] == "application.final_delta")
        self.assertEqual(delta["review_field"], "owner_inputs.delta_protocol")
        self.assertEqual(delta["condition"], "when:delta_method")
        self.assertEqual(delta["criticality"], "critical")

    def test_unknown_or_unmapped_native_feature_does_not_inherit_qualification(self):
        for direction in self.policy["directions"]:
            self.assertTrue(all(x["admission"] == "unknown_requires_installed_qualification"
                                for x in direction["features"]))
        data = copy.deepcopy(self.policy)
        data["directions"][0]["features"][0]["admission"] = "eligible"
        with self.assertRaises(ValueError):
            validate(data, self.crosswalk, self.manifest)

    def test_missing_or_changed_operator_requirement_fails_closed(self):
        for name in ("missing", "downgrade", "spoof_native", "mapping"):
            altered = copy.deepcopy(self.policy)
            target = altered["operator_requirements"][0]
            if name == "missing":
                altered["operator_requirements"].pop()
            elif name == "downgrade":
                target["criticality"] = "optional"
            elif name == "spoof_native":
                target["review_field"] = "owner_inputs.native_disk_api"
            else:
                target["feature_id"] = "platform.api"
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate(altered, self.crosswalk, self.manifest)


if __name__ == "__main__":
    unittest.main()
