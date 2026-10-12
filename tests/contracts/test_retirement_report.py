"""Retirement governance reports unresolved external obligations without inventing clearance."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/contracts"))
from retirement_report import audit


class CanonicalRetirementReviewTests(unittest.TestCase):
    def test_review_backlog_is_not_silently_promoted_to_approved(self):
        result = audit()
        self.assertEqual(result["total_retirements"], len(result["retirements"]))
        self.assertEqual(result["unresolved"] + result["recorded_approved"],
                         result["total_retirements"])
        self.assertEqual(result["can_claim_governance_closed"],
                         result["unresolved"] == 0)
        self.assertTrue(all(row["needs_independent_approval"] ==
                            (row["clearance_status"] == "unresolved")
                            for row in result["retirements"]))

    def test_cannot_count_external_clearance_by_changing_status_without_review(self):
        with patch("retirement_report.verify_retirement_decisions",
                   side_effect=ValueError("missing independent review")):
            with self.assertRaisesRegex(ValueError, "missing independent review"):
                audit()


if __name__ == "__main__":
    unittest.main()
