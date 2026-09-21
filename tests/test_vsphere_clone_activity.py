"""Clone reconciliation observes both source and result VM activity, without adoption."""
from copy import deepcopy
from datetime import timedelta
import unittest
from tests.test_vsphere_clone_tree import manifest as clone_manifest, Client as CloneClient
from tests.test_vsphere_task_activity import context
from tests.test_vsphere_observe import ref
from tests.test_vsphere_recovery import reseal
from tests.test_nutanix_vm_observe import uid
from tools import readback_core as c, recovery_review as rr, qualify_target as q
from tools import vsphere_task_tree_observe as tree, vsphere_task_activity as activity, vsphere_task_observe as task


def manifest(origin='https://vcenter.example.invalid'):
    m = clone_manifest(origin); m['profile'] = activity.CLONE_PROFILE
    m['task']['activity_since'] = (c.timestamp(m['task']['records'][0]['queued_at']) - timedelta(seconds=1)).isoformat()
    return m


class Client(CloneClient):
    def __init__(self, m):
        super().__init__(m)
        self.activity_rows = {key: {'pending': [], 'completed': []} for key in activity.entity_ids(m)}
        for record in m['task']['records']:
            row = deepcopy(self.routes[task.task_target(record)])
            self.activity_rows[row['entity']['value']]['completed'].append(row)
    def activity(self): self.request_count += 14; return deepcopy(self.activity_rows)


class CloneActivityTests(unittest.TestCase):
    def setUp(self): self.m = manifest(); self.client = Client(self.m)
    def observe(self): return c.observe(self.m, self.client, tree, interval=0)
    def test_source_and_result_tasks_match_for_review_only(self):
        report = self.observe()
        self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
        self.assertEqual(activity.entity_ids(self.m), {'vm-1', 'vm-9'})
        self.assertEqual(rr.review(self.m, report, context(self.m, report))['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        self.assertIs(q.vsphere_adapter(self.m), tree)
        self.assertFalse(report['may_apply']); self.assertFalse(report['may_activate'])
        state = next(s for s in report['history'][-1]['states'] if s['resource_key'] == activity.KEY)
        self.assertEqual(set(state['activity_witness']['after']), {'vm-1', 'vm-9'})
    def test_separate_source_or_destination_work_cannot_hide_behind_known_tree(self):
        for entity in ('vm-1', 'vm-9'):
            for pending in (True, False):
                self.client = Client(self.m)
                row = deepcopy(self.client.activity_rows[entity]['completed'][0])
                old = (c.timestamp(self.m['task']['activity_since']) - timedelta(hours=1)).isoformat()
                row.update(key='task-99', task=ref('Task', 'task-99'), queueTime=old, startTime=old)
                if pending: row.update(state='running', completeTime=None, result=None)
                self.client.activity_rows[entity]['pending' if pending else 'completed'].append(row)
                report = self.observe()
                self.assertEqual(report['outcome'], 'HOLD_DIFFERENCE')
                self.assertEqual(rr.review(self.m, report, context(self.m, report))['result'], 'RECONCILE_DIVERGENCE')
    def test_missing_source_query_wrong_entity_and_duplicate_activity_hold(self):
        for mutate in (lambda rows: rows.pop('vm-9'), lambda rows: rows['vm-9']['completed'][0].update(entity=ref('VirtualMachine', 'vm-1')),
            lambda rows: rows['vm-1']['completed'].append(deepcopy(rows['vm-9']['completed'][0])),
            lambda rows: rows['vm-9']['pending'].append(rows['vm-9']['completed'][0] | dict(state='running', completeTime=None, result=None))):
            self.client = Client(self.m); mutate(self.client.activity_rows)
            self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
        self.client = Client(self.m); self.client.activity_rows['vm-9']['completed'].clear()
        self.assertEqual(self.observe()['outcome'], 'HOLD_DIFFERENCE')
    def test_activity_must_agree_with_direct_clone_result_and_stay_stable(self):
        self.client.activity_rows['vm-9']['completed'][0]['result'] = ref('VirtualMachine', 'vm-2')
        self.assertEqual(self.observe()['outcome'], 'HOLD_DIFFERENCE')
        self.client = Client(self.m); calls = []
        def changing():
            calls.append(True); rows = deepcopy(self.client.activity_rows)
            if len(calls) > 1: rows['vm-9']['completed'].clear()
            return rows
        self.client.activity = changing
        self.assertEqual(self.observe()['outcome'], 'HOLD_DIFFERENCE')
    def test_window_must_include_the_clone_and_bind_to_attempt(self):
        m = deepcopy(self.m); m['task']['activity_since'] = c.now()
        with self.assertRaises(ValueError): tree.validate(m)
        report = self.observe(); x = context(self.m, report)
        x['attempted_at'] = (c.timestamp(x['attempted_at']) - timedelta(seconds=1)).isoformat()
        self.assertEqual(rr.review(self.m, report, x)['result'], 'HOLD_INVALID_EVIDENCE')
    def test_successful_clone_does_not_hide_pending_or_failed_destination_work(self):
        for native, outcome in (('running', 'HOLD_NATIVE_PENDING'), ('error', 'HOLD_NATIVE_FAILURE')):
            self.client = Client(self.m)
            row = self.client.activity_rows['vm-1']['completed'].pop()
            row.update(state=native)
            if native == 'running': row['completeTime'] = None
            self.client.routes[task.task_target(self.m['task']['records'][1])] = deepcopy(row)
            self.client.history = [deepcopy(row)]
            self.client.activity_rows['vm-1']['pending' if native == 'running' else 'completed'].append(row)
            self.assertEqual(self.observe()['outcome'], outcome)
    def test_matching_clone_activity_does_not_substitute_for_fencing_or_quarantine(self):
        report = self.observe()
        for control, result in (('writer_fence', 'HOLD_WRITER_NOT_FENCED'), ('quarantine', 'HOLD_QUARANTINE_NOT_VERIFIED')):
            x = context(self.m, report); x[control]['state'] = 'UNVERIFIED'
            review = rr.review(self.m, report, x)
            self.assertEqual(review['result'], result); self.assertFalse(review['may_apply'])
    def test_rehashed_activity_omission_or_foreign_result_cannot_override_summary(self):
        for mutate in (lambda w: w['after'].pop('vm-9'), lambda w: w['after']['vm-9']['completed'].clear(),
            lambda w: w['after']['vm-9']['completed'][0]['result_reference'].update(value='vm-2')):
            report = self.observe(); x = context(self.m, report)
            for row in report['history']: mutate(next(s for s in row['states'] if s['resource_key'] == activity.KEY)['activity_witness'])
            reseal(report, x)
            self.assertEqual(rr.review(self.m, report, x)['result'], 'HOLD_INVALID_EVIDENCE')
    def test_shared_template_is_queried_once_and_every_destination_is_covered(self):
        m = deepcopy(self.m); r = deepcopy(m['resources'][0]); r['moid'] = 'vm-2'
        r['expected']['config'].update(uuid=uid(20), instanceUuid=uid(21)); m['resources'].append(r)
        root = m['task']['records'][0] | dict(moid='task-3', vm_moid='vm-2', root_task_id='task-3')
        m['task']['records'].append(root); tree.validate(m)
        self.assertEqual(activity.entity_ids(m), {'vm-1', 'vm-2', 'vm-9'})
        client = Client(self.m)
        rows = deepcopy(client.activity_rows); rows['vm-2'] = {'pending': [], 'completed': []}
        cloned = deepcopy(rows['vm-9']['completed'][0]); cloned.update(key='task-3', task=ref('Task', 'task-3'), result=ref('VirtualMachine', 'vm-2'))
        rows['vm-9']['completed'].append(cloned)
        witnesses = activity.witness(rows)
        states = [task.evaluate_task(record, task.task_witness(row)) for record, row in
            [(self.m['task']['records'][0], rows['vm-9']['completed'][0]), (self.m['task']['records'][1], rows['vm-1']['completed'][0]), (root, cloned)]]
        self.assertEqual(activity.state(m, {'before': witnesses, 'after': witnesses}, states)['config_status'], 'MATCH')
        # An empty result-VM query is valid when all accepted clone work is attached to its source.
        witnesses.pop('vm-2')
        self.assertEqual(activity.state(m, {'before': witnesses, 'after': witnesses}, states)['config_status'], 'UNKNOWN')
    def test_missing_source_or_activity_window_and_excessive_combined_scope_refused(self):
        for field in ('sources', 'activity_since'):
            m = deepcopy(self.m); m['task'].pop(field)
            with self.assertRaises(ValueError): tree.validate(m)
        m = deepcopy(self.m)
        # Both halves are bounded together, before a client or collector is created.
        for i in range(2, 21): m['resources'].append({'moid': 'vm-' + str(100 + i)})
        with self.assertRaisesRegex(ValueError, 'combined activity'): activity.validate_window(m)


if __name__ == '__main__': unittest.main()
