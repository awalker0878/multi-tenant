"""E2-only shadow reconciliation: read-only, strict and never self-promoting."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from shadow_compare import document, reconcile

MODULE = Path(__file__).with_name("shadow_compare.py")


def record() -> dict:
    return {
        "scope_sha256": "a" * 64,
        "authority_epoch": 2,
        "state": "qualified",
        "decision_sha256": "b" * 64,
        "evidence_level": "E2",
        "definition_sha256": "c" * 64,
        "platform": "openstack",
        "method": "native_api",
        "expires_at": 2000000000,
    }


def manifest(rows: list[dict] | None = None) -> dict:
    return {
        "schema_version": 1,
        "source_revision": "d" * 40,
        "records": [record()] if rows is None else rows,
    }


class ShadowCompareTests(unittest.TestCase):
    def test_unchanged_has_no_diff_and_never_grants_support(self) -> None:
        before = manifest()
        after = copy.deepcopy(before)
        self.assertEqual(reconcile(before, after), [])

    def test_negative_epoch_regression_and_positive_drift_require_review(self) -> None:
        old = manifest()
        new = copy.deepcopy(old)
        new["records"][0]["authority_epoch"] = 1
        new["records"][0]["state"] = "suspended"
        new["records"][0]["evidence_level"] = "E3"
        diffs = reconcile(old, new)
        self.assertEqual(len(diffs), 1)
        self.assertIn("authority_epoch_regression", diffs[0]["reasons"])
        self.assertIn("state_changed", diffs[0]["reasons"])
        self.assertIn("evidence_level_changed_without_external_review", diffs[0]["reasons"])

    def test_positive_promotion_needs_independent_review(self) -> None:
        old, new = manifest(), manifest()
        old["records"][0]["state"] = "revoked"
        new["records"][0]["authority_epoch"] = 3
        reasons = reconcile(old, new)[0]["reasons"]
        self.assertIn("positive_support_change_requires_review", reasons)
        self.assertIn("authority_epoch_changed", reasons)

    def test_new_and_missing_scopes_cannot_silently_pass(self) -> None:
        before = manifest([])
        after = manifest()
        self.assertIn("new_scope_unreviewed", reconcile(before, after)[0]["reasons"])
        self.assertIn("removed_scope_unreviewed", reconcile(after, before)[0]["reasons"])

    def test_strict_parse_prevents_duplicates_and_unreviewed_positives(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            cases = [
                '{"schema_version":1,"schema_version":1}',
                json.dumps(manifest([record(), record()])),
                json.dumps(manifest([{**record(), "authority_epoch": True}])),
                json.dumps(manifest([{**record(), "decision_sha256": None}])),
                json.dumps(manifest([{**record(), "state": ["qualified"]}])),
            ]
            for content in cases:
                with self.subTest(content=content[:40]):
                    path.write_text(content, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        document(path)

    def test_cli_writes_bounded_non_authoritative_diff_and_returns_review_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old_path, new_path, output = (root / n for n in ("before.json", "after.json", "out.json"))
            before, after = manifest(), manifest()
            after["records"][0]["state"] = "suspended"
            old_path.write_text(json.dumps(before), encoding="utf-8")
            new_path.write_text(json.dumps(after), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable, str(MODULE), "--baseline", str(old_path),
                    "--candidate", str(new_path), "--output", str(output),
                ],
                capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 1, result.stderr.decode())
            report = json.loads(output.read_text())
            self.assertEqual(report["status"], "REVIEW_REQUIRED")
            self.assertEqual(report["authority"], "read_only_shadow_no_promotion")
            self.assertIsNone(report["independent_reviewer_decision"])
            self.assertNotIn("records", report)


if __name__ == "__main__":
    unittest.main()
