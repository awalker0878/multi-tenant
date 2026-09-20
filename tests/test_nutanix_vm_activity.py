"""Visible task activity through fixed native GETs; scripted loopback responses only."""
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit
from lab.native_readback_fixture import Fixture
from tests import test_nutanix_vm_task_observe as fixtures
from tests.test_nutanix_vm_observe import manifest as vm_manifest, uid
from tools import nutanix_vm_activity_observe as a, nutanix_task_tree as tree, readback_core as c


def manifest(origin='https://pc.example.invalid'):
    m = fixtures.task_manifest(vm_manifest(origin)); m['profile'] = a.PROFILE
    return m


def activity_routes(m, routes, extras=None):
    result = {}
    for r in m['resources']:
        rows = [deepcopy(routes[tree.target(n['ext_id'])]['body']['data']) for n in tree.specs(m) if r['ext_id'] in n['entity_ids']]
        rows += deepcopy(extras or []); rows.sort(key=lambda n: n['extId'])
        for page in range(max(1, (len(rows)+a.PAGE_SIZE-1)//a.PAGE_SIZE)):
            result[a.target(m, r['ext_id'], page)] = {'body': {'data': rows[page*a.PAGE_SIZE:(page+1)*a.PAGE_SIZE],
                'metadata': {'totalAvailableResults': len(rows)}}}
    return result


class ActivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.f = Fixture()
    @classmethod
    def tearDownClass(cls): cls.f.close()
    def setUp(self):
        self.m = manifest(self.f.origin); self.f.routes = fixtures.responses(self.m)
        self.f.routes.update(activity_routes(self.m, self.f.routes)); self.f.requests = []; self.f.counts = {}; self.f.hook = None
    def observe(self):
        client = c.ReadClient(self.f.origin, self.f.origin, 'fixture', 'fixture', a.targets(self.m), str(self.f.directory / 'ca.pem'))
        report = c.observe(self.m, client, a, interval=0)
        self.assertTrue(all(r['method'] == 'GET' and r['path'] in a.targets(self.m) for r in self.f.requests))
        self.assertTrue(all(report[k] is False for k in ('may_apply', 'may_delete', 'may_activate')))
        return report
    def outcome(self, expected):
        report = self.observe(); self.assertEqual(report['outcome'], expected); return report
    def page(self): return self.f.routes[a.target(self.m, uid(1), 0)]['body']
    def extra(self, *, status='RUNNING', old=True):
        row = deepcopy(self.f.routes[tree.target(fixtures.CHILD)]['body']['data'])
        row.update(extId='unrecorded-task', status=status, completedTime=None if status == 'RUNNING' else row['completedTime'])
        if old: row['createdTime'] = (c.timestamp(self.m['task']['created_after']) - timedelta(days=1)).isoformat()
        return row

    def test_success_uses_fixed_entity_filter_before_and_after_tasks_and_vm(self):
        report = self.outcome('READBACK_MATCH_NOT_QUALIFIED')
        self.assertEqual(report['request_count'], 14)
        paths = [r['path'] for r in self.f.requests]; expected = a.target(self.m, uid(1), 0)
        self.assertEqual(paths[0], expected); self.assertEqual(paths[6], expected)
        query = parse_qs(urlsplit(expected).query)
        self.assertEqual(query['$orderby'], ['extId asc']); self.assertEqual(query['$limit'], ['25'])
        self.assertIn("entitiesAffected/any(e:e/extId eq '" + uid(1) + "')", query['$filter'][0])
        self.assertNotIn('createdTime', query['$filter'][0])
        self.assertEqual(report['history'][-1]['states'][-1]['resource_key'], a.KEY)

    def test_old_pending_and_late_completed_unrecorded_roots_hold(self):
        for status in ('RUNNING', 'SUCCEEDED', 'FAILED'):
            self.setUp(); self.f.routes.update(activity_routes(self.m, self.f.routes, [self.extra(status=status)]))
            report = self.outcome('HOLD_DIFFERENCE')
            self.assertTrue(report['history'][0]['states'][0]['task_completion_observed'])
            self.assertIn('/activity/before:task_set_differs', report['history'][0]['states'][-1]['mismatch_fields'])

    def test_missing_activity_despite_successful_direct_tasks_holds(self):
        self.page()['data'].pop(); self.page()['metadata']['totalAvailableResults'] = 1
        self.outcome('HOLD_DIFFERENCE')

    def test_native_count_truncation_duplicates_filter_and_types_hold(self):
        for mutate in (lambda p: p['metadata'].update(totalAvailableResults=3),
                       lambda p: p['metadata'].update(totalAvailableResults=True),
                       lambda p: p['metadata'].update(totalAvailableResults=101),
                       lambda p: p['metadata'].update(messages=[{'message': 'PRIVATE'}]),
                       lambda p: p.pop('metadata'),
                       lambda p: p['data'].reverse(),
                       lambda p: p['data'].__setitem__(1, deepcopy(p['data'][0])),
                       lambda p: p['data'][0].update(entitiesAffected=[{'extId': uid(90)}]),
                       lambda p: p['data'][0].update(numberOfEntitiesAffected=2),
                       lambda p: p['data'][0].update(status='$REDACTED'),
                       lambda p: p['data'][0].update(completedTime='2000-01-01T00:00:00Z')):
            self.setUp(); mutate(self.page()); self.outcome('HOLD_UNCERTAIN')

    def test_pagination_reads_complete_bounded_scope_and_rejects_changed_totals(self):
        extras = [self.extra() | {'extId': f'other-{i:03d}'} for i in range(28)]
        self.f.routes.update(activity_routes(self.m, self.f.routes, extras)); self.outcome('HOLD_DIFFERENCE')
        self.assertEqual(self.f.counts[a.target(self.m, uid(1), 1)], 2)
        self.f.routes[a.target(self.m, uid(1), 1)]['body']['metadata']['totalAvailableResults'] = 29
        self.outcome('HOLD_UNCERTAIN')

    def test_missing_second_page_does_not_retry_or_follow_response_link(self):
        self.page()['metadata']['totalAvailableResults'] = 26
        self.page()['data'] = [self.extra() | {'extId': f'other-{i:03d}'} for i in range(25)]
        self.page()['metadata']['links'] = [{'rel': 'next', 'href': 'https://foreign.invalid/secret'}]
        path = a.target(self.m, uid(1), 1)
        self.outcome('HOLD_UNCERTAIN'); self.assertEqual(self.f.counts[path], 1)
        self.assertEqual(len(self.f.requests), 2)

    def test_aggregate_limit_counts_shared_rows_across_vm_queries(self):
        r = deepcopy(self.m['resources'][0]); r['ext_id'] = r['expected']['extId'] = uid(30)
        self.m['resources'].append(r); self.m['task']['entity_ids'].append(uid(30))
        self.f.routes = fixtures.responses(self.m)
        extras = [self.extra() | {'extId': f'other-{i:03d}', 'numberOfEntitiesAffected': 2,
                                  'entitiesAffected': [{'extId': uid(1)}, {'extId': uid(30)}]} for i in range(50)]
        self.f.routes.update(activity_routes(self.m, self.f.routes, extras))
        self.outcome('HOLD_UNCERTAIN')

    def test_foreign_targets_and_unbounded_pages_are_not_generated(self):
        for identity, page in ((uid(99), 0), (uid(1), -1), (uid(1), 4), (uid(1), True)):
            with self.assertRaises(ValueError): a.target(self.m, identity, page)
        for mutate in (lambda m: m.update(profile=fixtures.ahv.PROFILE),
                       lambda m: m['task'].update(created_before='2999-01-01T00:00:00Z')):
            bad = deepcopy(self.m); mutate(bad)
            with self.assertRaises(ValueError): a.validate(bad)

    def test_direct_and_list_state_disagreement_holds(self):
        self.page()['data'][0]['operation'] = 'Different operation'
        self.outcome('HOLD_DIFFERENCE')

    def test_activity_change_after_vm_snapshot_holds(self):
        def hook(path, count, spec):
            if path == a.target(self.m, uid(1), 0) and count == 2:
                spec['body']['data'].append(self.extra()); spec['body']['metadata']['totalAvailableResults'] += 1
            return spec
        self.f.hook = hook; self.outcome('HOLD_DIFFERENCE')

    def test_pending_and_failed_recorded_tasks_still_hold(self):
        for status, expected in (('RUNNING', 'HOLD_NATIVE_PENDING'), ('FAILED', 'HOLD_NATIVE_FAILURE')):
            self.setUp(); body = self.f.routes[tree.target(fixtures.CHILD)]['body']['data']; body['status'] = status
            if status == 'RUNNING': body['completedTime'] = None
            self.f.routes.update(activity_routes(self.m, self.f.routes)); self.outcome(expected)

    def test_shared_vm_task_is_bound_in_each_vm_query(self):
        r = deepcopy(self.m['resources'][0]); r['ext_id'] = r['expected']['extId'] = uid(30)
        self.m['resources'].append(r); self.m['task']['entity_ids'].append(uid(30))
        self.f.routes = fixtures.responses(self.m); self.f.routes.update(activity_routes(self.m, self.f.routes))
        self.outcome('READBACK_MATCH_NOT_QUALIFIED')
        self.f.routes[a.target(self.m, uid(30), 0)]['body'].update(data=[], metadata={'totalAvailableResults': 0})
        self.outcome('HOLD_DIFFERENCE')

    def test_offline_history_cannot_relabel_or_remove_activity_witness(self):
        report = self.observe(); states = report['history'][-1]['states']
        for mutate in (lambda s: s.pop(), lambda s: s[-1].update(config_status='DIFFERENT'),
                       lambda s: s[-1]['activity_witness']['before'].pop(uid(1)),
                       lambda s: s[-1]['activity_witness']['before'][uid(1)][0]['tasks'].clear()):
            bad = deepcopy(states); mutate(bad)
            with self.assertRaises(c.ObservationError): a.validate_observation_history(self.m, [], bad)

    def test_unselected_native_task_text_is_not_exported(self):
        for row in self.page()['data']: row['operationDescription'] = 'PRIVATE-DIAGNOSTICS'
        self.assertNotIn('PRIVATE-DIAGNOSTICS', json.dumps(self.outcome('READBACK_MATCH_NOT_QUALIFIED')))

    def test_cli_is_offline_by_default_then_uses_exact_gets(self):
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
