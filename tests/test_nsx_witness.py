"""Offline NSX summaries must agree with both configuration reads and realization."""
from copy import deepcopy
import json
import unittest
from lab.native_readback_fixture import Fixture
from lab.run_readback_lab import operator_context
from tests.test_nutanix_task_tree import reseal
from tools import nsx_observe as nsx, readback_core as c, recovery_review as rr


class WitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.f = Fixture()
    @classmethod
    def tearDownClass(cls): cls.f.close()
    def setUp(self): self.m = self.f.reset('nsx')
    def observe(self): return c.observe(self.m, self.f.client(self.m), nsx, interval=0)

    def test_complete_witnesses_are_recomputed_offline(self):
        report = self.observe(); ctx = operator_context(self.m, report)
        self.assertEqual(rr.review(self.m, report, ctx)['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        state = report['history'][-1]['states'][0]
        self.assertEqual(state['config_witness']['before_sha256'], c.digest(self.m['resources'][0]['expected']))

    def test_rehashed_summaries_cannot_hide_either_snapshot_or_realization(self):
        report = self.observe()
        for mutate in (lambda s: s['config_witness'].update(before_sha256='a'*64),
                       lambda s: s['config_witness'].update(after_sha256='a'*64),
                       lambda s: s['config_witness'].update(identity_match=False),
                       lambda s: s['config_witness'].update(revision=True),
                       lambda s: s['realization_witness'].update(publish_status='UNREALIZED'),
                       lambda s: s['realization_witness'].update(intent_version='different'),
                       lambda s: s['realization_witness']['consolidated_status_per_enforcement_point'].clear(),
                       lambda s: s.pop('realization_witness')):
            bad = deepcopy(report); mutate(bad['history'][0]['states'][0]); reseal(bad)
            self.assertEqual(rr.review(self.m, bad, operator_context(self.m, bad))['result'], 'HOLD_INVALID_EVIDENCE')

    def test_pending_failure_and_unknown_are_not_promoted(self):
        target = nsx.status_target(self.m['resources'][0]['path'])
        for publication, expected in [('UNREALIZED', 'WAIT_FOR_NATIVE_TASK'), ('ERROR', 'INSPECT_PARTIAL_FAILURE'),
                                      ('UNAVAILABLE', 'HOLD_NATIVE_UNCERTAINTY')]:
            self.f.routes[target]['body']['publish_status'] = publication
            report = self.observe(); result = rr.review(self.m, report, operator_context(self.m, report))
            self.assertEqual(result['result'], expected)
            self.assertFalse(result['may_apply'])

    def test_diagnostic_bodies_are_not_copied_into_witness(self):
        target = nsx.status_target(self.m['resources'][0]['path'])
        self.f.routes[target]['body']['alarms'] = [{'text': 'PRIVATE-SENTINEL'}]
        self.assertNotIn('PRIVATE-SENTINEL', json.dumps(self.observe()))


if __name__ == '__main__': unittest.main()
