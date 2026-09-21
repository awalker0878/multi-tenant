"""Compose both checked native profiles without losing either set of evidence."""
from copy import deepcopy
import json
import unittest
from lab.native_readback_fixture import Fixture
from lab.run_readback_lab import operator_context
from tests.nsx_domain_fixture import scenario
from tests.test_nsx_segment_observe import manifest as switch_fixture, Client
from tests.test_nutanix_task_tree import reseal
from tools import nsx_domain_switch_observe as n, readback_core as c, recovery_review as review


def manifest(origin='https://nsx.example.test'):
    _, _, m, _ = scenario(origin); m['profile'] = n.PROFILE
    segment = next(r for r in m['resources'] if r['kind'] == 'segment')
    segment['logical_switch'] = switch_fixture()['resources'][0]['logical_switch']
    segment['logical_switch']['intent_reference'] = [segment['path']]
    return m


class CombinedTests(unittest.TestCase):
    def setUp(self): self.m = manifest(); self.client = Client(self.m)
    def observe(self): return c.observe(self.m, self.client, n, interval=0)
    def test_matching_domain_and_switch_are_replayable_offline(self):
        report = self.observe()
        self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
        self.assertEqual(len(report['history'][-1]['states']), 5)
        self.assertEqual(review.review(self.m, report, operator_context(self.m, report))['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        n.switches.validate(n.segment_manifest(self.m))

    def test_missing_or_foreign_switch_and_partial_domain_refused(self):
        for mutate in (lambda m: m['resources'][1].pop('logical_switch'),
                       lambda m: m['resources'].pop(), lambda m: m['resources'][0].update(logical_switch={}),
                       lambda m: m['resources'][1]['logical_switch'].update(intent_reference=['/infra/segments/foreign']),
                       lambda m: m.update(profile=n.switches.PROFILE), lambda m: m.update(profile=n.domain.PROFILE)):
            m = deepcopy(self.m); mutate(m)
            with self.assertRaises(ValueError): n.targets(m)

    def test_domain_shape_cannot_be_weakened_by_switch_composition(self):
        path = '/policy/api/v1'+self.m['resources'][3]['path']
        self.client.routes[path]['body']['rules'][0]['unreviewed_selector'] = ['ANY']
        report = self.observe(); self.assertEqual(report['outcome'], 'HOLD_UNCERTAIN')
        self.assertEqual(report['history'][-1]['states'][0]['reason'], 'NSX_DOMAIN_SHAPE_UNSUPPORTED')

    def test_configuration_realization_and_switch_witnesses_all_rechecked(self):
        report = self.observe()
        for mutate in (lambda states: states[0]['shape_witness'].update(before=False),
                       lambda states: states[0]['config_witness'].update(before_sha256='a'*64),
                       lambda states: states[0]['realization_witness'].update(publish_status='UNREALIZED'),
                       lambda states: states[-1]['switch_witness']['before'][0].update(state='UNREALIZED')):
            bad = deepcopy(report); mutate(bad['history'][0]['states']); reseal(bad)
            self.assertEqual(review.review(self.m, bad, operator_context(self.m, bad))['result'], 'HOLD_INVALID_EVIDENCE')

    def test_switch_alarm_or_pending_cannot_hide_behind_matching_domain(self):
        path = n.switches.entity_target(self.m['resources'][1]['path'])
        for changes, outcome in [(dict(state='UNREALIZED'), 'HOLD_NATIVE_PENDING'),
                                  (dict(alarms=[{'text': 'PRIVATE-SENTINEL'}]), 'HOLD_NATIVE_FAILURE')]:
            self.client = Client(self.m); self.client.routes[path]['body']['results'][0].update(changes)
            report = self.observe(); self.assertEqual(report['outcome'], outcome)
            self.assertNotIn('PRIVATE-SENTINEL', json.dumps(report))

    def test_real_tls_queries_only_exact_domain_and_segment_targets(self):
        with Fixture() as f:
            m = manifest(f.origin); f.routes = Client(m).routes
            client = c.ReadClient(f.origin, f.origin, 'fixture', 'fixture', n.targets(m), str(f.directory/'ca.pem'))
            report = c.observe(m, client, n, interval=0)
            self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
            self.assertEqual({r['path'] for r in f.requests}, n.targets(m))
            self.assertTrue(all(r['method'] == 'GET' for r in f.requests))


if __name__ == '__main__': unittest.main()
