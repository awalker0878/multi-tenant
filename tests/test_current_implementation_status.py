"""Current implementation-status overlay regressions; not native qualification."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_current_implementation_status as current

ROOT = Path(__file__).resolve().parents[1]


class CurrentImplementationStatusTests(unittest.TestCase):
    def setUp(self):
        self.source = current.strict_json(current.STATUS_PATH)

    def test_current_source_validates_all_historical_ids(self):
        rows, summary = current.validate(self.source)
        self.assertEqual([row['id'] for row in rows], [f'I{i:02d}' for i in range(1, 11)])
        self.assertEqual(summary['items'], 10)
        self.assertEqual(summary['native_qualified_items'], 0)

    def test_checked_markdown_matches_machine_source(self):
        rows, _ = current.validate(self.source)
        self.assertEqual(current.render(self.source, rows), current.MARKDOWN_PATH.read_text())

    def test_historical_blob_identity_is_enforced(self):
        self.source['historical_backlog_git_blob_sha'] = '0' * 40
        with self.assertRaises(ValueError):
            current.validate(self.source)

    def test_missing_item_rejected(self):
        self.source['items'].pop()
        with self.assertRaises(ValueError):
            current.validate(self.source)

    def test_duplicate_or_reordered_item_rejected(self):
        self.source['items'][1] = deepcopy(self.source['items'][0])
        with self.assertRaises(ValueError):
            current.validate(self.source)

    def test_unknown_evidence_level_rejected(self):
        self.source['items'][0]['evidence_levels'] = ['NATIVE_MAGIC']
        with self.assertRaises(ValueError):
            current.validate(self.source)

    def test_broken_evidence_reference_rejected(self):
        self.source['items'][0]['evidence_refs'] = ['does/not/exist']
        with self.assertRaises(ValueError):
            current.validate(self.source)

    def test_path_traversal_evidence_reference_rejected(self):
        self.source['items'][0]['evidence_refs'] = ['../outside']
        with self.assertRaises(ValueError):
            current.validate(self.source)

    def test_state_must_remain_open_or_hold(self):
        self.source['items'][0]['current_state'] = 'COMPLETE'
        with self.assertRaises(ValueError):
            current.validate(self.source)

    def test_native_target_contact_cannot_be_claimed(self):
        self.source['items'][0]['native_target_contact'] = 'EXECUTED'
        with self.assertRaises(ValueError):
            current.validate(self.source)

    def test_native_qualification_cannot_be_claimed(self):
        self.source['items'][0]['native_qualification'] = 'NATIVE_QUALIFIED'
        with self.assertRaises(ValueError):
            current.validate(self.source)

    def test_formal_authorization_cannot_be_claimed(self):
        self.source['items'][0]['formal_authorization'] = 'ISSUED'
        with self.assertRaises(ValueError):
            current.validate(self.source)

    def test_unknown_source_field_rejected(self):
        self.source['approval'] = 'yes'
        with self.assertRaises(ValueError):
            current.validate(self.source)

    def test_cli_check_is_non_mutating_and_passes(self):
        before = current.MARKDOWN_PATH.read_bytes()
        run = subprocess.run(
            [sys.executable, str(ROOT/'scripts/check_current_implementation_status.py')],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(current.MARKDOWN_PATH.read_bytes(), before)
        result = json.loads(run.stdout)
        self.assertEqual(result['status'], 'PASSED_CURRENT_IMPLEMENTATION_STATUS')
        self.assertTrue(result['historical_backlog_preserved'])
        self.assertEqual(result['native_qualification'], 'NOT_RUN')
        self.assertEqual(result['formal_authorization'], 'NOT_ISSUED')


if __name__ == '__main__':
    unittest.main()
