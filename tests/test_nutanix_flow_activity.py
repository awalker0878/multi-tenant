"""Flow task/activity composition uses scripted loopback TLS, not native acceptance."""
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from lab.native_readback_fixture import Fixture
from lab.run_readback_lab import operator_context
from tests.test_nutanix_task_tree import reseal
from tools import recovery_review as rr
from tests import test_nutanix_vm_task_observe as tasks
from tests.test_nutanix_vm_activity import activity_routes
from tests.test_nutanix_flow_observe import manifest as snapshot_manifest
from tests.test_nutanix_vm_observe import uid
from tools import nutanix_flow_activity_observe as a, nutanix_flow_observe as flow
from tools import nutanix_entity_activity as activity, nutanix_task_tree as tree, readback_core as c


def manifest(origin='https://pc.example.invalid'):
    m = tasks.task_manifest(snapshot_manifest(origin)); m['profile'] = a.PROFILE
    m['task']['operation'] = 'Fixture policy update'
    m['task']['descendants'][0]['operation'] = 'Fixture policy child'
    return m


def responses(m):
    routes = {path: spec for path, spec in tasks.responses(m).items() if path.startswith('/api/prism/')}
    routes.update({flow.resource_target(r): {'body': {'data': deepcopy(r['expected'])}, 'etag': r['expected_etag']}
                   for r in m['resources']})
    routes.update(activity_routes(m, routes)); return routes


class FlowActivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.f = Fixture()
    @classmethod
    def tearDownClass(cls): cls.f.close()
    def setUp(self):
        self.m = manifest(self.f.origin); self.f.routes = responses(self.m)
        self.f.requests = []; self.f.counts = {}; self.f.hook = None
    def observe(self):
        client = c.ReadClient(self.f.origin, self.f.origin, 'fixture', 'fixture', a.targets(self.m), str(self.f.directory/'ca.pem'))
        report = c.observe(self.m, client, a, interval=0)
        self.assertTrue(all(r['method'] == 'GET' and r['path'] in a.targets(self.m) for r in self.f.requests))
        self.assertTrue(all(report[k] is False for k in ('may_apply', 'may_delete', 'may_activate')))
        return report
    def outcome(self, expected):
        r = self.observe(); self.assertEqual(r['outcome'], expected); return r
    def page(self): return self.f.routes[activity.target(self.m, uid(20), 0)]['body']
    def policy(self): return self.f.routes[flow.resource_target(self.m['resources'][0])]['body']['data']

    def test_success_brackets_exact_policy_and_tasks_with_entity_activity(self):
        report = self.outcome('READBACK_MATCH_NOT_QUALIFIED')
        page = activity.target(self.m, uid(20), 0)
        expected = [page, tree.target(tasks.TASK), tree.target(tasks.CHILD), flow.resource_target(self.m['resources'][0]),
                    tree.target(tasks.CHILD), tree.target(tasks.TASK), page]
        self.assertEqual([r['path'] for r in self.f.requests], expected*2)
        state = report['history'][-1]['states'][0]
        self.assertTrue(state['task_completion_observed']); self.assertTrue(state['policy_witness']['policy_shape_valid'])

    def test_one_recorded_policy_task_is_supported(self):
        self.m['task']['descendants'] = []; self.f.routes = responses(self.m)
        self.assertEqual(self.outcome('READBACK_MATCH_NOT_QUALIFIED')['request_count'], 10)

    def test_profile_and_mixed_entity_manifest_are_rejected(self):
        for mutate in (lambda m: m.update(profile=flow.PROFILE), lambda m: m.pop('task'),
                       lambda m: m['task']['entity_ids'].append(uid(30)),
                       lambda m: m['task']['descendants'][0].update(entity_ids=[uid(6)]),
                       lambda m: m['task'].update(created_before='2999-01-01T00:00:00Z'),
                       lambda m: m['resources'][0].update(expected_etag='W/"weak"')):
            bad = deepcopy(self.m); mutate(bad)
            with self.assertRaises(ValueError): a.targets(bad)

    def test_pending_and_failed_child_hold_even_when_policy_matches(self):
        for status, outcome in (('RUNNING', 'HOLD_NATIVE_PENDING'), ('FAILED', 'HOLD_NATIVE_FAILURE')):
            self.setUp(); data = self.f.routes[tree.target(tasks.CHILD)]['body']['data']; data['status'] = status
            if status == 'RUNNING': data['completedTime'] = None
            self.f.routes.update(activity_routes(self.m, self.f.routes))
            report = self.outcome(outcome); self.assertFalse(report['history'][0]['states'][0]['task_completion_observed'])

    def test_unrecorded_old_pending_and_recently_completed_activity_hold(self):
        for status in ('RUNNING', 'SUCCEEDED', 'FAILED'):
            self.setUp(); extra = deepcopy(self.page()['data'][0]); extra.update(extId='unrecorded', status=status)
            extra['createdTime'] = (c.timestamp(self.m['task']['created_after']) - timedelta(days=1)).isoformat()
            if status == 'RUNNING': extra['completedTime'] = None
            self.f.routes.update(activity_routes(self.m, self.f.routes, [extra])); self.outcome('HOLD_DIFFERENCE')

    def test_missing_or_unattributable_task_activity_holds(self):
        self.page()['data'].clear(); self.page()['metadata']['totalAvailableResults'] = 0
        self.outcome('HOLD_DIFFERENCE')
        self.setUp(); data = self.f.routes[tree.target(tasks.CHILD)]['body']['data']
        data['entitiesAffected'].append({'extId': uid(6)}); data['numberOfEntitiesAffected'] += 1
        self.f.routes.update(activity_routes(self.m, self.f.routes)); self.outcome('HOLD_UNCERTAIN')

    def test_incomplete_and_unordered_native_queries_hold(self):
        for mutate in (lambda p: p['metadata'].update(totalAvailableResults=101),
                       lambda p: p['metadata'].update(totalAvailableResults=3),
                       lambda p: p['metadata'].update(messages=[{'message': 'PRIVATE'}]),
                       lambda p: p['data'].reverse()):
            self.setUp(); mutate(self.page()); self.outcome('HOLD_UNCERTAIN')

    def test_policy_drift_and_extra_unselected_selectors_hold(self):
        for mutate in (lambda p: p.update(networkFunctionReferences=[uid(90)]),
                       lambda p: p.update(securedGroups=[uid(90)]),
                       lambda p: p['rules'][2]['spec'].update(destAllowSpec='ALL')):
            self.setUp(); mutate(self.policy()); self.outcome('HOLD_DIFFERENCE')
        self.setUp(); self.f.routes[flow.resource_target(self.m['resources'][0])]['etag'] = '"other"'
        self.outcome('HOLD_DIFFERENCE')

    def test_offline_match_cannot_hide_native_shape_failure(self):
        self.policy()['networkFunctionReferences'] = [uid(90)]
        report = self.outcome('HOLD_DIFFERENCE'); states = deepcopy(report['history'][0]['states'])
        states[0].update(config_status='MATCH', mismatch_fields=[])
        self.assertEqual(states[0]['config_sha256'], c.digest(self.m['resources'][0]['expected']))
        with self.assertRaises(c.ObservationError): a.validate_observation_history(self.m, [], states)

    def test_offline_hashes_task_status_and_activity_cannot_be_relabelled(self):
        states = self.observe()['history'][-1]['states']
        for mutate in (lambda s: s[0].update(config_sha256='0'*64), lambda s: s[0].update(etag_sha256='0'*64),
                       lambda s: s[0].update(task_completion_observed=False), lambda s: s[0].pop('policy_witness'),
                       lambda s: s[-1].update(config_status='DIFFERENT'),
                       lambda s: s[-1]['activity_witness']['before'][uid(20)][0]['tasks'].clear()):
            bad = deepcopy(states); mutate(bad)
            with self.assertRaises(c.ObservationError): a.validate_observation_history(self.m, [], bad)

    def test_activity_change_after_policy_snapshot_holds(self):
        def hook(path, count, spec):
            if path == activity.target(self.m, uid(20), 0) and count == 2:
                spec['body']['data'][0]['operation'] = 'Changed operation'
            return spec
        self.f.hook = hook; self.outcome('HOLD_DIFFERENCE')

    def test_task_errors_and_unselected_policy_text_are_not_exported(self):
        self.policy()['description'] = 'PRIVATE-SENTINEL'
        self.page()['data'][0]['operationDescription'] = 'PRIVATE-SENTINEL'
        self.assertNotIn('PRIVATE-SENTINEL', json.dumps(self.outcome('READBACK_MATCH_NOT_QUALIFIED')))

    def test_recovery_replays_evidence_and_requires_independent_controls(self):
        report = self.observe(); context = operator_context(self.m, report)
        context['attempted_at'] = self.m['task']['created_after']
        self.assertEqual(rr.review(self.m, report, context)['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        for control, expected in (('writer_fence', 'HOLD_WRITER_NOT_FENCED'), ('quarantine', 'HOLD_QUARANTINE_NOT_VERIFIED')):
            bad = deepcopy(context); bad[control]['state'] = 'UNKNOWN'
            self.assertEqual(rr.review(self.m, report, bad)['result'], expected)
        for mutate in (lambda r: r['history'][0]['states'][0]['policy_witness'].update(policy_shape_valid=False),
                       lambda r: r['history'][0]['states'][-1]['activity_witness']['before'][uid(20)][0]['tasks'].clear()):
            bad = deepcopy(report); mutate(bad); reseal(bad)
            ctx = deepcopy(context); ctx['report_sha256'] = bad['content_sha256']
            self.assertEqual(rr.review(self.m, bad, ctx)['result'], 'HOLD_INVALID_EVIDENCE')

    def test_recovery_attempt_window_must_match_and_predate_readback(self):
        report = self.observe(); context = operator_context(self.m, report)
        context['attempted_at'] = self.m['task']['created_after']
        context['attempted_at'] = (c.timestamp(context['attempted_at']) - timedelta(seconds=1)).isoformat()
        self.assertEqual(rr.review(self.m, report, context)['result'], 'HOLD_INVALID_EVIDENCE')
        self.m['task']['created_before'] = c.now()
        report['manifest_sha256'] = c.digest(self.m); reseal(report)
        context.update(manifest_sha256=c.digest(self.m), report_sha256=report['content_sha256'],
                       attempted_at=self.m['task']['created_after'])
        self.assertEqual(rr.review(self.m, report, context)['result'], 'HOLD_INVALID_EVIDENCE')

    def test_cli_validates_offline_then_contacts_only_exact_gets(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'manifest'; out = Path(directory)/'report'
            self.m['contact_enabled'] = True; path.write_text(json.dumps(self.m))
            args = [sys.executable, str(Path(a.__file__)), str(path)]
            p = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout+p.stderr); self.assertFalse(self.f.requests)
            p = subprocess.run(args + ['--read-authorized-target', '--expected-origin', self.f.origin,
                '--ca-file', str(self.f.directory/'ca.pem'), '--output', str(out), '--interval', '0'],
                env=dict(os.environ, NUTANIX_USERNAME='fixture', NUTANIX_PASSWORD='fixture'), capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
            self.assertEqual(c.load(out)['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
            self.assertEqual(out.stat().st_mode & 0o777, 0o600)


if __name__ == '__main__': unittest.main()
