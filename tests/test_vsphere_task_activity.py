"""Known task success cannot hide separate or older in-flight VM operations."""
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
from tests.test_native_readback import context as base_context
from tests.test_vsphere_task_tree import manifest as tree_manifest, Client as TreeClient
from tests.test_vsphere_observe import ref
from tests.test_vsphere_recovery import reseal
from tools import readback_core as c, recovery_review as rr, qualify_target as q
from tools import vsphere_task_observe as task, vsphere_task_tree_observe as tree, vsphere_task_activity as activity


def manifest(origin='https://vcenter.example.invalid'):
    m = tree_manifest(origin); m['profile'] = activity.PROFILE
    m['task']['activity_since'] = (c.timestamp(m['task']['records'][0]['queued_at']) - timedelta(seconds=1)).isoformat()
    return m


def context(m, report):
    x = base_context(m, report); x['attempted_at'] = m['task']['activity_since']
    return x


class Client(TreeClient):
    def __init__(self, m):
        super().__init__(m)
        self.activity_rows = {r['moid']: {'pending': [], 'completed': []} for r in m['resources']}
        for record in m['task']['records']:
            self.activity_rows[record['vm_moid']]['completed'].append(deepcopy(self.routes[task.task_target(record)]))
    def activity(self): self.request_count += 7; return deepcopy(self.activity_rows)


class TaskActivityTests(unittest.TestCase):
    def setUp(self): self.m = manifest(); self.client = Client(self.m)
    def observe(self): return c.observe(self.m, self.client, tree, interval=0)
    def test_exact_vm_activity_matches_but_does_not_authorize_change(self):
        report = self.observe()
        self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
        self.assertEqual(rr.review(self.m, report, context(self.m, report))['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        self.assertIs(q.vsphere_adapter(self.m), tree); self.assertIn(activity.KEY, tree.observation_keys(self.m))
        self.assertFalse(report['may_apply']); self.assertFalse(report['may_activate'])
    def test_unrecorded_root_older_pending_or_late_completion_holds(self):
        for pending in (False, True):
            self.client = Client(self.m)
            other = deepcopy(self.client.activity_rows['vm-1']['completed'][0])
            old = (c.timestamp(self.m['task']['activity_since']) - timedelta(hours=1)).isoformat()
            other.update(key='task-99', task=ref('Task', 'task-99'), queueTime=old, startTime=old)
            if pending: other.update(state='running', completeTime=None)
            self.client.activity_rows['vm-1']['pending' if pending else 'completed'].append(other)
            report = self.observe()
            self.assertEqual(report['outcome'], 'HOLD_DIFFERENCE')
            self.assertEqual(rr.review(self.m, report, context(self.m, report))['result'], 'RECONCILE_DIVERGENCE')
    def test_missing_root_is_detected_even_when_children_match(self):
        self.client.activity_rows['vm-1']['completed'].pop(0)
        self.assertEqual(self.observe()['outcome'], 'HOLD_DIFFERENCE')
    def test_duplicate_transition_wrong_entity_and_filter_contradictions_hold(self):
        for mutate in (lambda rows: rows['completed'].append(deepcopy(rows['completed'][0])),
            lambda rows: rows['pending'].append(rows['completed'][0] | dict(state='running', completeTime=None)),
            lambda rows: rows['completed'][0].update(entity=ref('VirtualMachine', 'vm-9')),
            lambda rows: rows['completed'][0].update(state='running'),
            lambda rows: rows['completed'][0].update(completeTime='2020-01-01T00:00:00Z')):
            self.client = Client(self.m); mutate(self.client.activity_rows['vm-1'])
            self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
    def test_changed_scan_or_direct_get_disagreement_holds(self):
        self.client.activity_rows['vm-1']['completed'][0]['eventChainId'] += 1
        self.assertEqual(self.observe()['outcome'], 'HOLD_DIFFERENCE')
        self.client = Client(self.m); calls = []
        def changing():
            calls.append(True); rows = deepcopy(self.client.activity_rows)
            if len(calls) > 1: rows['vm-1']['completed'].pop()
            return rows
        self.client.activity = changing
        self.assertEqual(self.observe()['outcome'], 'HOLD_DIFFERENCE')
    def test_window_cannot_exclude_recorded_tasks_or_differ_from_attempt(self):
        m = deepcopy(self.m); m['task']['activity_since'] = c.now()
        with self.assertRaises(ValueError): tree.validate(m)
        report = self.observe(); x = context(self.m, report)
        x['attempted_at'] = (c.timestamp(x['attempted_at']) - timedelta(seconds=1)).isoformat()
        self.assertEqual(rr.review(self.m, report, x)['result'], 'HOLD_INVALID_EVIDENCE')
    def test_rehashed_activity_summary_cannot_hide_omitted_or_future_work(self):
        for mutate in (lambda w: w['after']['vm-1']['completed'].pop(),
            lambda w: w['after']['vm-1']['completed'][0].update(completeTime='2099-01-01T00:00:00Z')):
            report = self.observe(); x = context(self.m, report)
            for row in report['history']: mutate(next(s for s in row['states'] if s['resource_key'] == activity.KEY)['activity_witness'])
            reseal(report, x)
            self.assertEqual(rr.review(self.m, report, x)['result'], 'HOLD_INVALID_EVIDENCE')
    def test_cli_queries_scoped_activity_and_destroys_every_collector(self):
        with Fixture() as f, tempfile.TemporaryDirectory() as tmp:
            m = manifest(f.origin); m['contact_enabled'] = True; client = Client(m)
            f.routes = {key: {'body': value} for key, value in client.routes.items()}
            from tests.test_vsphere_history import routes
            create, read, destroy = routes(f, []); pages = []; filters = []
            def collect(body):
                selected = body['filter']; filters.append(selected)
                if 'entity' in selected:
                    self.assertEqual(selected['entity'], {'entity': {'type': 'VirtualMachine', 'value': 'vm-1'}, 'recursion': 'self'})
                    if selected['state'] == ['queued', 'running']: rows = client.activity_rows['vm-1']['pending']
                    else:
                        self.assertEqual(selected['time'], {'timeType': 'completedTime', 'beginTime': m['task']['activity_since']})
                        rows = client.activity_rows['vm-1']['completed']
                else:
                    self.assertEqual(selected, {'parentTaskKey': ['task-1', 'task-2']}); rows = client.history
                pages[:] = [deepcopy(rows), []] if rows else [[]]
                return {'body': {'type': 'TaskHistoryCollector', 'value': 'collector-1'}}
            f.post_routes[create] = collect; f.post_routes[read] = lambda _: {'body': pages.pop(0)}
            folder = Path(tmp); path = folder / 'manifest.json'; path.write_text(json.dumps(m)); output = folder / 'report.json'
            result = subprocess.run([sys.executable, str(q.ROOT / 'tools/vsphere_task_tree_observe.py'), str(path),
                '--read-authorized-target', '--expected-origin', f.origin, '--ca-file', str(f.directory / 'ca.pem'),
                '--output', str(output), '--interval', '0'], capture_output=True, text=True,
                env=dict(os.environ, VCENTER_SESSION='fixture-session'), timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(len(filters), 12); self.assertEqual(sum(r['path'] == destroy for r in f.requests), 12)
            self.assertTrue(all(r['method'] == 'GET' or r['path'] in {create, read, destroy} for r in f.requests))


if __name__ == '__main__': unittest.main()
