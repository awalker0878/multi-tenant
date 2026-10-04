"""Behavior of factual input completeness, not native feasibility or authority."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("p00_inputs", ROOT / "scripts/validate_p00_inputs.py")
inputs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inputs)


class P00InputTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(inputs.DEFAULT_RECORD.read_text())
        self.schema = json.loads(inputs.DEFAULT_SCHEMA.read_text())

    def observed(self, group="RT02", field="vcenter_esxi_builds", value="RESTRICTED"):
        cell = self.record["groups"][group]["fields"][field]
        cell.update(status="OBSERVED", value=value,
                    evidence=[{"kind": "protected", "uri": "evidence://unit-test-only/fixture-v1",
                               "sha256": "a" * 64, "revision": "test-version-1"}],
                    observed_at="2026-10-04T18:00:00Z", observed_by="unit-test-observer",
                    scope={"campaign": "unit-test-only", "resource_ids": ["fixture/source-1"]},
                    review={"disposition": "ACCEPTED", "reviewed_by": "unit-test-reviewer",
                            "reviewed_at": "2026-10-04T19:00:00Z"})
        return cell

    def result(self, scope="route"):
        return inputs.validate(self.record, self.schema, scope)

    def test_truthfully_incomplete_record_is_valid_and_reports_exact_missing_inputs(self):
        result = self.result()
        self.assertTrue(result["record_valid"])
        self.assertFalse(result["input_ready"])
        self.assertIn("RT10.post_write_preservation_procedure", [row["input"] for row in result["missing_inputs"]])
        self.assertEqual(self.record["groups"]["RT02"]["fields"]["vcenter_esxi_builds"]["value"], None)

    def test_missing_field_is_invalid_instead_of_silently_unknown(self):
        del self.record["groups"]["RT06"]["fields"]["writer_manifest"]
        self.assertFalse(self.result()["record_valid"])

    def test_false_observation_is_distinct_from_unknown(self):
        self.observed("RT05", "destination_key_availability", False)
        result = self.result()
        self.assertTrue(result["record_valid"])
        # Input completeness is not a compatibility or security decision.
        self.assertNotIn("RT05.destination_key_availability", [row["input"] for row in result["missing_inputs"]])
        self.assertFalse(result["authorizes_execution"])

    def test_unknown_cannot_carry_asserted_value(self):
        self.record["groups"]["RT05"]["fields"]["encryption_layers"]["value"] = False
        self.assertFalse(self.result()["record_valid"])

    def test_unknown_cannot_be_accepted(self):
        cell = self.observed()
        cell.update(status="UNKNOWN", value=None, evidence=[], observed_at=None, observed_by=None, scope=None)
        self.assertFalse(self.result()["record_valid"])

    def test_observation_requires_provenance_time_scope_and_observer(self):
        for key, value in [("evidence", []), ("observed_at", None), ("scope", None), ("observed_by", None)]:
            with self.subTest(key=key):
                cell = self.observed()
                cell[key] = value
                self.assertFalse(self.result()["record_valid"])

    def test_unreviewed_observation_is_present_but_not_ready(self):
        self.observed()["review"] = {"disposition": "NOT_REVIEWED", "reviewed_by": None, "reviewed_at": None}
        result = self.result()
        self.assertTrue(result["record_valid"])
        missing = next(row for row in result["missing_inputs"] if row["input"] == "RT02.vcenter_esxi_builds")
        self.assertEqual(missing["status"], "OBSERVED")
        self.assertEqual(missing["review"], "NOT_REVIEWED")

    def test_incompatible_finding_is_separate_from_unknown(self):
        cell = self.observed()
        cell["status"] = "BLOCKED"
        cell["review"]["disposition"] = "REJECTED"
        result = self.result()
        self.assertTrue(result["record_valid"])
        missing = next(row for row in result["missing_inputs"] if row["input"] == "RT02.vcenter_esxi_builds")
        self.assertEqual(missing["status"], "BLOCKED")

    def test_no_floating_or_endpoint_evidence_reference(self):
        for key, value in [("revision", "latest"), ("uri", "https://private.invalid/secret"),
                           ("uri", "evidence://unit-test-only/../capture"), ("sha256", "bad")]:
            with self.subTest(key=key, value=value):
                self.observed()["evidence"][0][key] = value
                self.assertFalse(self.result()["record_valid"])

    def test_actual_owner_decision_can_use_pinned_repository_evidence(self):
        cell = self.observed()
        cell["evidence"] = [{"kind": "repository", "uri": "git://awalker0878/multi-tenant/" + "b" * 40 + "/docs/example.md",
                             "sha256": "a" * 64, "revision": "b" * 40}]
        self.assertTrue(self.result()["record_valid"])
        # Syntax checking cannot tell whether a source actually contains a fact.
        self.assertFalse(self.result()["authorizes_execution"])

    def test_repository_reference_cannot_claim_a_different_revision(self):
        cell = self.record["groups"]["RT01"]["fields"]["method"]
        cell["evidence"][0]["revision"] = "c" * 40
        self.assertFalse(self.result()["record_valid"])

    def test_review_requires_actual_identity_and_zoned_time(self):
        for key, value in [("reviewed_by", None), ("reviewed_at", "2026-10-04"),
                           ("reviewed_at", "2026-10-04T19:00:00")]:
            with self.subTest(key=key):
                self.observed()["review"][key] = value
                self.assertFalse(self.result()["record_valid"])

    def test_wildcards_do_not_define_bounded_resource_scope(self):
        for wildcard in ["*", "project/*", "all", "source-?", "source-[12]"]:
            with self.subTest(wildcard=wildcard):
                self.observed()["scope"]["resource_ids"] = [wildcard]
                self.assertFalse(self.result()["record_valid"])

    def test_blanket_effect_permission_is_invalid(self):
        self.observed("RT10", "permitted_effects", "all")
        self.assertFalse(self.result()["record_valid"])

    def test_contradictory_claim_cannot_hide_missing_post_write_recovery(self):
        self.record["claimed_input_readiness"] = "READY"
        self.assertFalse(self.result()["record_valid"])
        self.assertIn("RT10.post_write_recovery_method", [row["input"] for row in self.result()["missing_inputs"]])

    def test_unknown_recovery_method_is_not_treated_as_selected(self):
        self.observed("RT10", "post_write_recovery_method", "rollback")
        self.assertFalse(self.result()["record_valid"])

    def test_fully_supplied_metadata_never_grants_authority_or_proves_execution(self):
        for group_id in self.schema["x-route-groups"]:
            for field in self.record["groups"][group_id]["fields"]:
                self.observed(group_id, field, "target_forward_recovery" if field == "post_write_recovery_method" else "RESTRICTED")
        result = self.result()
        self.assertTrue(result["record_valid"], result["errors"])
        self.assertTrue(result["input_ready"])
        self.assertFalse(result["authorizes_execution"])
        self.assertFalse(result["establishes_feasibility"])
        self.assertFalse(self.result("all")["input_ready"])
        # Withhold post-write preservation while everything else remains present.
        original = json.loads(inputs.DEFAULT_RECORD.read_text())
        self.record["groups"]["RT10"]["fields"]["post_write_preservation_procedure"] = deepcopy(
            original["groups"]["RT10"]["fields"]["post_write_preservation_procedure"])
        self.assertFalse(self.result()["input_ready"])
        self.assertEqual([row["input"] for row in self.result()["missing_inputs"]],
                         ["RT10.post_write_preservation_procedure"])

    def test_cli_reports_valid_incomplete_separately_from_require_ready_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "report.json"
            command = [sys.executable, str(ROOT / "scripts/validate_p00_inputs.py"), "--report", str(path)]
            default = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(default.returncode, 0, default.stderr)
            self.assertTrue(json.loads(path.read_text())["record_valid"])
            required = subprocess.run(command + ["--require-ready"], capture_output=True, text=True)
            self.assertEqual(required.returncode, 2, required.stderr)
            self.assertFalse(json.loads(path.read_text())["input_ready"])

    def test_cli_rejects_nonstandard_numeric_constants(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "record.json"
            for constant in ("NaN", "Infinity", "-Infinity"):
                with self.subTest(constant=constant):
                    text = json.dumps(self.record).replace('"value": null', '"value": ' + constant, 1)
                    path.write_text(text)
                    result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_p00_inputs.py"),
                                             "--record", str(path)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn("Nonstandard JSON numeric constant", result.stderr)

    def test_overflowed_json_number_cannot_be_a_valid_observation(self):
        self.observed(value=json.loads("1e999"))
        self.assertFalse(self.result()["record_valid"])


if __name__ == "__main__":
    unittest.main()
