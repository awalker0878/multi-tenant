"""Git-backed negative tests for active contract immutability and staged retirement."""
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from compatibility import approved_clearance, check, compare

PATH = "contracts/openapi/current-v1.json"
NEW = "contracts/openapi/current-v2.json"


class ActiveContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Contract fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.write(PATH, "{}\n")
        self.registry([PATH])
        self.retirement([])
        self.write("architecture/retirement-clearances.json",
                   json.dumps({"schema_version": 1, "clearances": {}}))
        self.base = self.commit()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value)

    def registry(self, paths):
        self.write("architecture/contract-consumers.json",
                   json.dumps({"active_releases": [{"path": p} for p in paths]}))

    def retirement(self, paths, reviewed=False):
        self.write("architecture/retired-contract-releases.json", json.dumps({
            "retired": paths,
            "reviews": {p: {
                "external_consumer_review": ("verified_no_external_consumers" if reviewed
                                             else "not-independently-verified"),
                "compatibility_commitments": "none",
                "external_review_evidence": "https://example.invalid/consumer-inventory",
            } for p in paths}
        }))

    def approval(self, reviewer="independent-reviewer", digest=None):
        return {
            "status": "approved",
            "owner": "service-owner",
            "reviewed_by": reviewer,
            "review_url": "https://github.com/awalker0878/multi-tenant/pull/123",
            "reviewed_at": "2026-10-11T12:00:00Z",
            "consumer_inventory_evidence": "https://example.invalid/consumer-inventory",
            "compatibility_evidence": "https://example.invalid/compatibility-disposition",
            "compatibility_commitments": "none",
            "contract_sha256": digest or hashlib.sha256(b"{}\n").hexdigest(),
            "assessed_consumers": [],
            "decision": "retire",
        }

    def clearances(self, approval):
        self.write("architecture/retirement-clearances.json", json.dumps({
            "schema_version": 1,
            "clearances": {PATH: approval},
        }))

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-m", "Reviewed snapshot")
        return self.git("rev-parse", "HEAD")

    def remove_current(self, reviewed=False, record=True):
        self.registry([])
        (self.root / PATH).unlink()
        self.retirement([PATH] if record else [], reviewed=reviewed)

    def test_existing_version_immutable_and_new_version_permitted(self):
        self.assertEqual(compare({"a": b"one"}, {"a": b"one"}), [])
        self.write(PATH, '{"added":true}\n')
        with self.assertRaisesRegex(ValueError, "Active published contract removed or changed"):
            check(self.root, self.base)
        self.write(PATH, "{}\n")
        self.write(NEW, "{}\n")
        self.registry([PATH, NEW])
        self.assertEqual(check(self.root, self.base)["added"], [NEW])

    def test_missing_current_file_fails_even_if_registry_claims_active(self):
        (self.root / PATH).unlink()
        with self.assertRaisesRegex(ValueError, "Canonical inventory does not match"):
            check(self.root, self.base)

    def test_removed_from_both_registry_and_tree_without_retirement_is_rejected(self):
        self.remove_current(record=False)
        with self.assertRaisesRegex(ValueError, "Canonical deleted without retirement record"):
            check(self.root, self.base)

    def test_retirement_cannot_be_self_declared_in_same_change(self):
        self.remove_current(reviewed=True)
        self.clearances(self.approval())
        with self.assertRaisesRegex(ValueError, "must be approved in an earlier reviewed base"):
            check(self.root, self.base)

    def test_prelisted_retirement_cannot_bypass_deletion_review(self):
        self.retirement([PATH])
        prior = self.commit()
        self.remove_current(reviewed=True)
        with self.assertRaisesRegex(ValueError, "Reviewed retirement clearance missing"):
            check(self.root, prior)

    def test_unreviewed_retirement_fails_even_with_manifest_entry(self):
        self.remove_current(reviewed=False)
        with self.assertRaisesRegex(ValueError, "Reviewed retirement clearance missing"):
            check(self.root, self.base)

    def test_valid_staged_clearance_must_be_committed_before_removal(self):
        self.clearances(self.approval())
        stage = self.commit()
        self.remove_current(reviewed=True)
        with patch("compatibility.verify_github_approval") as remote_review:
            result = check(self.root, stage)
        remote_review.assert_called_once()
        self.assertEqual(result["removed_from_review_base"], [PATH])
        self.assertEqual(result["staged_new_retirements"], [PATH])

    def test_approved_record_fails_closed_without_github_verification(self):
        self.clearances(self.approval())
        stage = self.commit()
        self.remove_current(reviewed=True)
        with patch("compatibility.verify_github_approval",
                   side_effect=ValueError("independent GitHub review unavailable")):
            with self.assertRaisesRegex(ValueError, "independent GitHub review unavailable"):
                check(self.root, stage)

    def test_approved_clearance_checks_hash_and_independent_review(self):
        approval = self.approval()
        with self.assertRaisesRegex(ValueError, "independent reviewer"):
            approved_clearance(PATH, self.approval(reviewer="service-owner"),
                               hashlib.sha256(b"{}\n").hexdigest())
        with self.assertRaisesRegex(ValueError, "reviewed contract bytes"):
            approved_clearance(PATH, approval, "f" * 64)
        with self.assertRaisesRegex(ValueError, "review timestamp"):
            approved_clearance(PATH, {**approval, "reviewed_at": "today"},
                               hashlib.sha256(b"{}\n").hexdigest())

    def test_reviewed_clearance_cannot_be_changed_in_removal_commit(self):
        self.clearances(self.approval())
        stage = self.commit()
        self.clearances(self.approval(reviewer="another-reviewer"))
        self.remove_current(reviewed=True)
        with self.assertRaisesRegex(ValueError, "earlier reviewed base"):
            check(self.root, stage)

    def test_base_revision_must_exist(self):
        with self.assertRaisesRegex(ValueError, "explicit existing base"):
            check(self.root, "0" * 40)


if __name__ == "__main__":
    unittest.main()
