"""Adversarial qualification tests. Every positive review/owner record here is synthetic."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from dossier import CASES, candidate_digest, reconcile, reviewed_input_digest
from evidence import Held, bounded_file, canonical, decode, digest, reference
from metrics import summarize
from mirror import verify_closure
from recovery import DEPENDENCIES, assess_restore


class Qualification(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "deploy/build").mkdir(parents=True)
        registry = b'{"components":[{"id":"example"}]}'
        (self.root / "deploy/build/components.json").write_bytes(registry)
        self.candidate = {
            "schema_version": 2,
            "source_revision": "a" * 40,
            "source_bindings": {
                "services/a.py": "b" * 64,
                "deploy/build/components.json": digest(registry),
            },
            "source_modes": {
                "services/a.py": "100644",
                "deploy/build/components.json": "100644",
            },
            "component_registry_sha256": digest(registry),
        }
        self.candidate["candidate_sha256"] = candidate_digest(self.candidate)
        self.sha = self.candidate["candidate_sha256"]
        self.sequence = 0

    def save(self, value):
        self.sequence += 1
        path = "evidence-" + str(self.sequence) + ".json"
        raw = canonical(value)
        (self.root / path).write_bytes(raw)
        return {"path": path, "sha256": digest(raw)}

    def test_bounded_integrity_duplicate_keys_and_symlink_escape(self):
        ref = self.save({"result": "PASSED"})
        self.assertEqual(reference(self.root, ref), {"result": "PASSED"})
        (self.root / ref["path"]).write_text("{}")
        with self.assertRaises(Held):
            reference(self.root, ref)
        with self.assertRaises(Held):
            decode(b'{"result":"PASSED","result":"FAILED"}')
        with self.assertRaises(Held):
            decode(b'{"timing":NaN}')
        for path in ("../escape", "/etc/passwd", "x/../file", "./file"):
            with self.subTest(path=path), self.assertRaises(Held):
                bounded_file(self.root, path)
        (self.root / "link").symlink_to(self.root / ref["path"])
        with self.assertRaises(Held):
            bounded_file(self.root, "link")

    def test_metrics_include_failures_and_unserved_tenants(self):
        rows = [
            {
                "id": str(i),
                "tenant_id": "first",
                "start_ns": i * 1000000,
                "end_ns": (i + 1) * 1000000,
                "outcome": "succeeded" if i < 3 else "failed",
            }
            for i in range(4)
        ]
        result = summarize(rows, ["first", "unserved"], 0, 10000000)
        self.assertEqual(result["samples"], 4)
        self.assertEqual(result["error_fraction"], 0.25)
        self.assertEqual(result["jain_fairness"], 0.5)
        self.assertEqual(result["latency_ms"]["p95"], 1)
        self.assertEqual(result["unserved_tenants"], ["unserved"])
        self.assertEqual(result["slo_result"], "NOT_EVALUATED")
        targets = {
            "p95_ms": 10,
            "maximum_error_fraction": 1,
            "minimum_fairness": 0.1,
            "minimum_samples": 1,
            "approved_model_sha256": "a" * 64,
        }
        self.assertEqual(
            summarize(rows, ["first", "unserved"], 0, 10000000, targets)["slo_result"],
            "FAILED",
        )
        for broken in (
            [rows[0], rows[0]],
            [rows[0] | {"end_ns": 20000000}],
            [rows[0] | {"start_ns": True}],
        ):
            with self.subTest(broken=broken), self.assertRaises(Held):
                summarize(broken, ["first"], 0, 10000000)

    def packet(self):
        p = {
            "schema_version": 2,
            "candidate_sha256": self.sha,
            "selected_tuples": ["c" * 64],
            "evidence": [],
            "receiving_reviews": [],
        }
        docs = {
            "prerequisite_reviews": {
                "gates": {g: "ACCEPTED" for g in ("G07", "G08", "G09")},
                "tuple_digests": p["selected_tuples"],
            },
            "workload_model": {
                "approved_by": "synthetic_owner",
                "approved_at": "2026-10-07T22:00:00Z",
                "targets": {"p95": 10},
                "scope": {"fixture": "synthetic-only"},
            },
            "artifact_set": {
                "components": {
                    "example": {
                        key: "d" * 64
                        for key in (
                            "image_sha256",
                            "lock_sha256",
                            "sbom_sha256",
                            "provenance_sha256",
                            "signature_sha256",
                            "trust_root_sha256",
                        )
                    }
                },
                "trust_verification": "PASSED",
                "restricted_install": "PASSED",
            },
            "security_findings": {
                "verification_standard": "synthetic-version",
                "applicability_review": "fixture",
                "open_required_findings": [],
                "custody_review": "fixture",
            },
            "operating_receipts": {
                "receiving_owner": "fixture",
                "support_scope": "fixture",
                "retention_review": "fixture",
                "incident_id": "fixture",
                "alert_id": "fixture",
                "acknowledged_at": "2026-10-07T23:01:00Z",
                "delivered_at": "2026-10-07T23:00:00Z",
            },
        }
        for key, value in docs.items():
            p[key] = self.save(value | {"candidate_sha256": self.sha})
        for case in sorted({c for cases in CASES.values() for c in cases}):
            p["evidence"].append(
                self.save(
                    {
                        "case_id": case,
                        "candidate_sha256": self.sha,
                        "source_bindings": self.candidate["source_bindings"],
                        "tuple_digests": p["selected_tuples"],
                        "native_write_authorized": False,
                        "result": "PASSED",
                        "checks": 1,
                        "failed": 0,
                        "errors": 0,
                        "skipped": 0,
                        "evidence_level": "E4",
                        "environment": "representative_preproduction",
                        "observed_at": "2026-10-07T23:00:00Z",
                        "observer_id": "synthetic-observer",
                        "scope": {"fixture": "synthetic-only"},
                        "observations": [self.save({"synthetic": True, "case": case})],
                    }
                )
            )
        self.fixture_reviews(p)
        return p

    def fixture_reviews(self, p):
        p["receiving_reviews"] = []
        for package in CASES:
            p["receiving_reviews"].append(
                self.save(
                    {
                        "package_id": package,
                        "candidate_sha256": self.sha,
                        "reviewed_input_sha256": reviewed_input_digest(p),
                        "decision": "ACCEPTED",
                        "reviewed_at": "2026-10-07T23:02:00Z",
                        "reviewer_id": "reviewer",
                        "implementer_id": "implementer",
                    }
                )
            )

    def test_complete_synthetic_packet_cannot_authorize_release_or_establish_authenticity(
        self,
    ):
        result = reconcile(self.root, self.candidate, self.packet())
        self.assertEqual(
            result["status"], "PACKET_COMPLETE_REQUIRES_AUTHENTICITY_REVIEW"
        )
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["evidence_authenticity_established"])

    def test_empty_actual_packet_is_held_in_all_six_packages(self):
        packet = json.loads(
            (
                Path(__file__).resolve().parents[2] / "release/p10-inputs.json"
            ).read_text()
        )
        result = reconcile(self.root, self.candidate, packet)
        self.assertEqual(result["status"], "HELD")
        self.assertEqual(len(result["packages"]), 6)
        self.assertTrue(all(p["status"] == "HELD" for p in result["packages"]))

    def test_e2_skipped_failed_or_unreviewed_claims_cannot_satisfy_p10(self):
        p = self.packet()
        for change in (
            {"evidence_level": "E2"},
            {"skipped": 1},
            {"errors": 1},
            {"result": "FAILED"},
            {"environment": "synthetic"},
        ):
            changed = copy.deepcopy(p)
            observation = reference(self.root, p["evidence"][0]) | change
            changed["evidence"][0] = self.save(observation)
            self.fixture_reviews(changed)
            self.assertEqual(
                reconcile(self.root, self.candidate, changed)["status"], "HELD"
            )
        p["receiving_reviews"] = []
        self.assertEqual(reconcile(self.root, self.candidate, p)["status"], "HELD")

    def test_changed_candidate_or_duplicate_evidence_requires_rerun(self):
        p = self.packet()
        changed = copy.deepcopy(p)
        observation = reference(self.root, p["evidence"][0]) | {"source_bindings": {}}
        changed["evidence"][0] = self.save(observation)
        with self.assertRaisesRegex(Held, "rerun"):
            reconcile(self.root, self.candidate, changed)
        p["evidence"].append(p["evidence"][0])
        with self.assertRaisesRegex(Held, "duplicate"):
            reconcile(self.root, self.candidate, p)

    def test_case_claim_requires_nonempty_originals_valid_counts_scope_and_time(self):
        p = self.packet()
        for change in (
            {"checks": 0},
            {"checks": True},
            {"failed": None},
            {"errors": -1},
            {"skipped": False},
            {"errors": 2},
            {"observations": []},
            {"scope": {}},
            {"observer_id": " "},
            {"observed_at": "2026-10-07T23:00:00"},
        ):
            changed = copy.deepcopy(p)
            changed["evidence"][0] = self.save(
                reference(self.root, p["evidence"][0]) | change
            )
            self.fixture_reviews(changed)
            with self.subTest(change=change), self.assertRaises(Held):
                reconcile(self.root, self.candidate, changed)
        report = reference(self.root, p["evidence"][0])
        (self.root / report["observations"][0]["path"]).write_text("changed original")
        with self.assertRaisesRegex(Held, "changed_evidence"):
            reconcile(self.root, self.candidate, p)

    def test_receiving_review_cannot_transfer_to_replaced_evidence_or_operating_input(
        self,
    ):
        p = self.packet()
        for key in ("evidence", "workload_model"):
            changed = copy.deepcopy(p)
            ref = changed[key][0] if key == "evidence" else changed[key]
            doc = reference(self.root, ref)
            doc.update(scope={"fixture": "changed-scope"})
            if key == "evidence":
                changed[key][0] = self.save(doc)
            else:
                changed[key] = self.save(doc)
            with self.subTest(key=key), self.assertRaisesRegex(Held, "changed_review"):
                reconcile(self.root, self.candidate, changed)

    def test_e3_operational_review_cannot_substitute_for_exercising_native_case(self):
        p = self.packet()
        first = reference(self.root, p["evidence"][0])
        p["evidence"][0] = self.save(
            first | {"evidence_level": "E3", "environment": "operational_review"}
        )
        self.fixture_reviews(p)
        self.assertEqual(reconcile(self.root, self.candidate, p)["status"], "HELD")

    def test_evidence_may_be_mounted_separately_from_candidate_source(self):
        import shutil

        p = self.packet()
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory)
            shutil.move(str(self.root / "deploy"), source_root / "deploy")
            self.assertEqual(
                reconcile(self.root, self.candidate, p, source_root=source_root)[
                    "status"
                ],
                "PACKET_COMPLETE_REQUIRES_AUTHENTICITY_REVIEW",
            )

    def test_artifact_names_without_exact_identities_cannot_complete_the_packet(self):
        p = self.packet()
        for components in (
            ["example"],
            {"example": {}},
            {"example": {"image_sha256": "d" * 64}},
        ):
            changed = copy.deepcopy(p)
            changed["artifact_set"] = self.save(
                reference(self.root, p["artifact_set"]) | {"components": components}
            )
            with (
                self.subTest(components=components),
                self.assertRaisesRegex(Held, "artifact_set_incomplete"),
            ):
                reconcile(self.root, self.candidate, changed)
        (self.root / "deploy/build/components.json").write_text('{"components":[]}')
        with self.assertRaisesRegex(Held, "candidate_registry_changed"):
            reconcile(self.root, self.candidate, p)

    def test_alert_acknowledgement_must_follow_delivery_in_absolute_time(self):
        p = self.packet()
        p["operating_receipts"] = self.save(
            reference(self.root, p["operating_receipts"])
            | {
                "delivered_at": "2026-10-07T23:00:00-04:00",
                "acknowledged_at": "2026-10-07T23:30:00Z",
            }
        )
        with self.assertRaisesRegex(Held, "operations_receipt_incomplete"):
            reconcile(self.root, self.candidate, p)

    def restore(self):
        packet = {
            "candidate_sha256": self.sha,
            "recovery_point": "fixture",
            "dependencies": {},
            "old_epoch": "old",
            "new_epoch": "new",
            "native_effects": [],
        }
        for name in DEPENDENCIES:
            packet["dependencies"][name] = self.save(
                {
                    "component": name,
                    "candidate_sha256": self.sha,
                    "recovery_point": "fixture",
                    "integrity": "VERIFIED",
                    "mode": "read_only",
                }
            )
        packet["isolation"] = self.save(
            {
                "candidate_sha256": self.sha,
                "old_writers_fenced": True,
                "restore_network_isolated": True,
                "old_epoch": "old",
                "new_epoch": "new",
            }
        )
        packet["native_effects"] = [
            self.save(
                {
                    "candidate_sha256": self.sha,
                    "operation_id": "fixture",
                    "provider_requests_quiescent": True,
                    "outcome": "succeeded",
                    "observer_id": "reader",
                    "executor_id": "writer",
                    "reconciled_epoch": "new",
                }
            )
        ]
        packet["native_inventory"] = self.save(
            {
                "candidate_sha256": self.sha,
                "reconciled_epoch": "new",
                "inventory_complete": True,
                "operation_ids": ["fixture"],
            }
        )
        packet["upgrade"] = self.save(
            {
                "candidate_sha256": self.sha,
                "migration_state_verified": True,
                "old_workers_drained": True,
                "mixed_contracts": "PASSED",
                "workflow_replay": "PASSED",
                "backfill_restart": "PASSED",
                "retained_key_decryption": "PASSED",
                "recovery_path": "reviewed_forward_recovery",
            }
        )
        return packet

    def test_restore_requires_all_dependencies_and_cannot_enable_writes(self):
        packet = self.restore()
        self.assertFalse(assess_restore(self.root, packet)["write_reenable_authorized"])
        for dependency in DEPENDENCIES:
            broken = copy.deepcopy(packet)
            del broken["dependencies"][dependency]
            with self.subTest(dependency=dependency), self.assertRaises(Held):
                assess_restore(self.root, broken)
        omitted = copy.deepcopy(packet)
        omitted["native_effects"] = []
        with self.assertRaisesRegex(Held, "inventory_incomplete"):
            assess_restore(self.root, omitted)

    def test_restore_holds_stale_epochs_unknown_effects_keys_and_undrained_workers(
        self,
    ):
        p = self.restore()
        for key, changes in (
            ("isolation", {"old_writers_fenced": False}),
            ("isolation", {"new_epoch": "old"}),
            ("upgrade", {"retained_key_decryption": "FAILED"}),
            ("upgrade", {"old_workers_drained": False}),
            ("upgrade", {"backfill_restart": "NOT_RUN"}),
        ):
            broken = copy.deepcopy(p)
            broken[key] = self.save(reference(self.root, p[key]) | changes)
            with self.subTest(changes=changes), self.assertRaises(Held):
                assess_restore(self.root, broken)
        p["native_effects"][0] = self.save(
            reference(self.root, p["native_effects"][0]) | {"outcome": "unknown"}
        )
        with self.assertRaises(Held):
            assess_restore(self.root, p)

    def test_restricted_closure_requires_exact_component_artifacts_without_network(
        self,
    ):
        manifest = {
            "candidate_sha256": self.sha,
            "components": ["fixture"],
            "artifacts": [],
        }
        for kind in ("image", "lock", "sbom", "provenance", "signature", "trust_root"):
            raw = ("synthetic_" + kind).encode()
            (self.root / kind).write_bytes(raw)
            manifest["artifacts"].append(
                {
                    "component": "fixture",
                    "kind": kind,
                    "path": kind,
                    "sha256": digest(raw),
                    "bytes": len(raw),
                }
            )
        result = verify_closure(self.root, manifest, ["fixture"])
        self.assertEqual(result["network_requests"], 0)
        self.assertFalse(result["signature_trust_established"])
        for fault in ("omitted", "changed", "escape", "duplicate"):
            broken = copy.deepcopy(manifest)
            if fault == "omitted":
                broken["artifacts"].pop()
            if fault == "changed":
                broken["artifacts"][0]["sha256"] = "f" * 64
            if fault == "escape":
                broken["artifacts"][0]["path"] = "../outside"
            if fault == "duplicate":
                broken["artifacts"].append(broken["artifacts"][0])
            with self.subTest(fault=fault), self.assertRaises(Held):
                verify_closure(self.root, broken, ["fixture"])


if __name__ == "__main__":
    unittest.main()
