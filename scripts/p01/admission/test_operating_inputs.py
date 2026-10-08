from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from operating_inputs import assess

ROOT = Path(__file__).resolve().parents[3]


class OperatingInputTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT / 'release/operating-inputs.json').read_bytes())
        self.carried = json.loads((ROOT / 'docs/qualification/feasibility/p00-input-record.json').read_bytes())
        self.now = datetime(2026, 10, 6, tzinfo=timezone.utc)

    def observed(self):
        for item in self.record['inputs']:
            item.update(status='OBSERVED', value='synthetic fixture only', owner_identity='fixture-owner',
                        evidence=[{'uri': 'git://awalker0878/multi-tenant/' + 'a'*40 + '/record.json',
                                   'revision': 'a'*40, 'sha256': 'b'*64}],
                        review={'disposition': 'ACCEPTED', 'reviewed_by': 'fixture-reviewer',
                                'reviewed_at': '2026-10-05T00:00:00Z'})
        self.record['status'] = 'RECORD_COMPLETE_REQUIRES_INDEPENDENT_VERIFICATION'

    def check(self):
        return assess(self.record, self.carried, self.now)

    def test_actual_unknown_inputs_are_held(self):
        self.assertEqual(len(self.check()['missing_or_unreviewed']), 7)

    def test_complete_fixture_never_authorizes_promotion(self):
        self.observed()
        self.assertFalse(self.check()['promotion_authorized'])

    def test_scope_cannot_be_removed_or_redirected(self):
        self.record['inputs'][0]['carried_fields'] = ['IP01.criterion_reviewers']
        with self.assertRaisesRegex(ValueError, 'operating_input_scope_changed'):
            self.check()

    def test_unknown_record_cannot_hide_owner_or_evidence(self):
        self.record['inputs'][0]['owner_identity'] = 'fixture'
        with self.assertRaisesRegex(ValueError, 'unknown_input_cannot_be_accepted'):
            self.check()

    def test_duplicate_input_denied(self):
        self.record['inputs'][-1] = deepcopy(self.record['inputs'][0])
        with self.assertRaisesRegex(ValueError, 'invalid_operating_input_inventory'):
            self.check()

    def test_mutable_or_mismatched_revision_denied(self):
        self.observed()
        evidence = self.record['inputs'][0]['evidence'][0]
        for revision in ['main', 'latest', 'c'*40]:
            with self.subTest(revision=revision):
                evidence['revision'] = revision
                with self.assertRaisesRegex(ValueError, 'unbound_operating_evidence|git_evidence_revision_mismatch'):
                    self.check()

    def test_future_naive_and_non_utc_review_denied(self):
        self.observed()
        for value in ['2027-01-01T00:00:00Z', '2026-10-04T00:00:00', '2026-10-04T00:00:00-04:00']:
            with self.subTest(value=value):
                self.record['inputs'][0]['review']['reviewed_at'] = value
                with self.assertRaisesRegex(ValueError, 'unattributed_operating_review'):
                    self.check()

    def test_rejected_input_cannot_claim_complete(self):
        self.observed()
        self.record['inputs'][0]['review']['disposition'] = 'REJECTED'
        with self.assertRaisesRegex(ValueError, 'operating_readiness_overclaim'):
            self.check()
        self.record['status'] = 'HELD'
        self.assertEqual(self.check()['missing_or_unreviewed'], ['OP01'])

    def test_unknown_disposition_denied(self):
        self.observed()
        self.record['inputs'][0]['review']['disposition'] = 'APPROVE'
        with self.assertRaisesRegex(ValueError, 'invalid_operating_review_disposition'):
            self.check()

    def test_credentials_in_evidence_uri_denied(self):
        self.observed()
        self.record['inputs'][0]['evidence'][0]['uri'] = 'evidence://user:password@host/file'
        with self.assertRaisesRegex(ValueError, 'use_sanitized_immutable_evidence_reference'):
            self.check()


if __name__ == '__main__':
    unittest.main()
