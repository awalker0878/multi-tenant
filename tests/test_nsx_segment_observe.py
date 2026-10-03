"""Scoped realized-entity association, ambiguity and incomplete-list holds."""
from copy import deepcopy
import json
import unittest
from lab.native_readback_fixture import Fixture, manifest as base_manifest, responses
from tests.test_nutanix_vm_observe import uid
from provisioner.execution import readback_core as c
from tools import nsx_segment_observe as n
from tools import recovery_review as review
from lab.run_readback_lab import operator_context
from tests.test_nutanix_task_tree import reseal


def manifest(origin='https://nsx.example.test'):
    m = base_manifest('nsx', origin); m['profile'] = n.PROFILE
    r = dict(kind='segment', path='/infra/segments/fixture', expected=dict(id='fixture', path='/infra/segments/fixture',
        resource_type='Segment', _revision=3, connectivity_path='/infra/tier-1s/fixture', transport_zone_path='/infra/sites/default/enforcement-points/default/transport-zones/fixture',
        subnets=[], advanced_config={}), realization=dict(intent_version='fixture-version', enforcement_points=['/infra/sites/default/enforcement-points/default']))
    r['logical_switch'] = dict(resource_type='GenericPolicyRealizedResource', entity_type='RealizedLogicalSwitch', id='fixture-switch',
        path='/infra/realized-state/enforcement-points/default/logical-switches/fixture-switch', _revision=2, intent_reference=[r['path']],
        enforcement_point_path=r['realization']['enforcement_points'][0], realization_specific_identifier=uid(30), state='REALIZED')
    m['resources'] = [r]; return m


class Client:
    def __init__(self, m):
        self.origin = m['origin']; self.request_count = 0; self.transform = None
        self.routes = responses(n.policy_manifest(m))
        for r in m['resources']:
            if r['kind'] == 'segment': self.routes[n.entity_target(r['path'])] = dict(body=dict(result_count=1, results=[deepcopy(r['logical_switch']) | {'alarms': []}]))
    def get(self, path):
        self.request_count += 1; body = deepcopy(self.routes[path]['body'])
        if self.transform: self.transform(path, body, self.request_count)
        return body, None


class SegmentTests(unittest.TestCase):
    def setUp(self): self.m = manifest(); self.client = Client(self.m); self.path = n.entity_target(self.m['resources'][0]['path'])
    def observe(self): return c.observe(self.m, self.client, n, interval=0)
    def test_matching_policy_and_realized_identity(self):
        report = self.observe(); self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED'); self.assertFalse(report['may_activate'])
    def test_ambiguous_missing_truncated_or_duplicate_results_hold(self):
        for mutate in (lambda b: b.update(cursor='next'), lambda b: b.update(result_count=2), lambda b: b.update(result_count=True),
            lambda b: b.update(results=[], result_count=0), lambda b: b.update(results=b['results'] * 2, result_count=2),
            lambda b: b.update(results=b['results'] + [b['results'][0] | {'path': '/foreign', 'id': 'foreign'}], result_count=2)):
            self.client = Client(self.m); mutate(self.client.routes[self.path]['body'])
            self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
    def test_foreign_failed_pending_and_changed_native_identity_hold(self):
        for changes, expected in [(dict(realization_specific_identifier=uid(31)), 'HOLD_DIFFERENCE'),
            (dict(intent_reference=['/infra/segments/foreign']), 'HOLD_UNCERTAIN'), (dict(_revision=8), 'HOLD_DIFFERENCE'),
            (dict(state='ERROR'), 'HOLD_NATIVE_FAILURE'), (dict(state='UNREALIZED'), 'HOLD_NATIVE_PENDING'),
            (dict(alarms=[{'error_message': 'PRIVATE-SENTINEL'}]), 'HOLD_NATIVE_FAILURE')]:
            self.client = Client(self.m); self.client.routes[self.path]['body']['results'][0].update(changes)
            report = self.observe(); self.assertEqual(report['outcome'], expected); self.assertNotIn('PRIVATE-SENTINEL', json.dumps(report))
        self.client = Client(self.m)
        self.client.transform = lambda p, b, count: b['results'][0].update(_revision=8) if p == self.path and count > 1 else None
        self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
    def test_wrong_profile_duplicate_association_or_foreign_expected_scope_rejected(self):
        for mutate in (lambda m: m.update(profile='unknown'), lambda m: m['resources'][0]['logical_switch'].update(intent_reference=['foreign']),
            lambda m: m['resources'][0]['logical_switch'].update(enforcement_point_path='/infra/sites/other/enforcement-points/other'),
            lambda m: m['resources'][0]['logical_switch'].update(_revision=True)):
            m = deepcopy(self.m); mutate(m)
            with self.assertRaises(ValueError): n.targets(m)
    def test_real_tls_is_segment_scoped_get_only(self):
        with Fixture() as f:
            m = manifest(f.origin); f.routes = Client(m).routes
            http = c.ReadClient(f.origin, f.origin, 'fixture', 'fixture', n.targets(m), str(f.directory / 'ca.pem'))
            self.assertEqual(c.observe(m, http, n, interval=0)['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
            self.assertEqual({r['path'] for r in f.requests}, n.targets(m))
            self.assertTrue(all(r['method'] == 'GET' and r['has_basic_auth'] and not r['has_session_auth'] for r in f.requests))

    def test_offline_review_replays_both_switch_snapshots(self):
        report = self.observe()
        self.assertEqual(review.review(self.m, report, operator_context(self.m, report))['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        for mutate in (lambda s: s.pop('switch_witness'),
                       lambda s: s['switch_witness']['before'][0].update(state='UNREALIZED'),
                       lambda s: s['switch_witness']['after'][0].update(alarms_empty=False),
                       lambda s: s['switch_witness']['after'][0].update(alarms_empty=1),
                       lambda s: s['switch_witness']['after'][0].update(realization_specific_identifier=uid(31)),
                       lambda s: s['switch_witness'].update(before=[])):
            bad = deepcopy(report); mutate(bad['history'][0]['states'][-1]); reseal(bad)
            self.assertEqual(review.review(self.m, bad, operator_context(self.m, bad))['result'], 'HOLD_INVALID_EVIDENCE')

    def test_offline_review_retains_pending_failure_and_ambiguous_holds(self):
        for change, expected in [(dict(state='UNREALIZED'), 'WAIT_FOR_NATIVE_TASK'), (dict(state='ERROR'), 'INSPECT_PARTIAL_FAILURE'),
                                 (dict(intent_reference=['/infra/segments/foreign']), 'HOLD_NATIVE_UNCERTAINTY')]:
            self.client = Client(self.m); self.client.routes[self.path]['body']['results'][0].update(change)
            report = self.observe()
            self.assertEqual(review.review(self.m, report, operator_context(self.m, report))['result'], expected)

    def test_policy_witness_and_extra_or_reordered_switch_coverage_are_checked(self):
        report = self.observe()
        for mutate in (lambda row: row['states'][0]['config_witness'].update(before_sha256='a'*64),
                       lambda row: row['states'].reverse(), lambda row: row['states'].append(deepcopy(row['states'][-1]))):
            bad = deepcopy(report); mutate(bad['history'][0]); reseal(bad)
            self.assertEqual(review.review(self.m, bad, operator_context(self.m, bad))['result'], 'HOLD_INVALID_EVIDENCE')


if __name__ == '__main__': unittest.main()
