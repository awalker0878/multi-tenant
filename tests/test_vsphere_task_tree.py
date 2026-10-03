"""Parent success never hides child work or incomplete native history."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from lab.native_readback_fixture import Fixture
from tests.test_native_readback import context
from tests.test_vsphere_observe import Client as VmClient, ref
from tests.test_vsphere_task_observe import manifest as flat_manifest, task_body
from tests.test_vsphere_recovery import reseal
from provisioner.execution import readback_core as c
from provisioner.execution import recovery_review as rr
from provisioner.execution import vsphere_task_observe as task
from provisioner.execution import vsphere_task_tree_observe as tree
from provisioner.execution import qualify_target as q
from provisioner.execution.readback_cli import module_command


def manifest(origin='https://vcenter.example.invalid'):
    m = flat_manifest(origin); m['profile'] = tree.PROFILE
    m['task'].update(task_manager_id='TaskManager', coverage_ref='FIXTURE-VISIBILITY-NOT-QUALIFIED')
    root = m['task']['records'][0]; root.update(parent_task_id=None, root_task_id='task-1')
    m['task']['records'].append(root | dict(moid='task-2', parent_task_id='task-1', description_id='VirtualMachine.reconfigVm'))
    return m


class Client(VmClient):
    def __init__(self, m):
        super().__init__(m); root = task_body(m)
        child = root | dict(key='task-2', task=ref('Task', 'task-2'), descriptionId='VirtualMachine.reconfigVm',
                            parentTaskKey='task-1', rootTaskKey='task-1')
        self.routes.update({task.task_target(r): deepcopy(root if r['moid'] == 'task-1' else child) for r in m['task']['records']})
        self.history = [child]
    def children(self): self.request_count += 3; return deepcopy(self.history)


class TaskTreeTests(unittest.TestCase):
    def setUp(self): self.m = manifest(); self.client = Client(self.m)
    def observe(self): return c.observe(self.m, self.client, tree, interval=0)
    def test_tree_and_visible_child_set_match_for_review_only(self):
        report = self.observe()
        self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
        self.assertEqual(rr.review(self.m, report, context(self.m, report))['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        self.assertFalse(report['may_apply']); self.assertIs(q.vsphere_adapter(self.m), tree)
    def test_successful_parent_with_pending_or_failed_child_cannot_complete(self):
        path = task.task_target(self.m['task']['records'][1])
        for state, expected in [('running', 'HOLD_NATIVE_PENDING'), ('error', 'HOLD_NATIVE_FAILURE')]:
            self.client = Client(self.m)
            self.client.routes[path].update(state=state, completeTime=None)
            self.client.history[0].update(state=state, completeTime=None)
            self.assertEqual(self.observe()['outcome'], expected)
    def test_missing_unexpected_or_mismatched_history_holds(self):
        for mutate in (lambda rows: rows.clear(), lambda rows: rows.append(rows[0] | dict(key='task-3', task=ref('Task', 'task-3'))),
                       lambda rows: rows[0].update(parentTaskKey='task-9')):
            self.client = Client(self.m); mutate(self.client.history)
            with self.subTest(mutate=mutate): self.assertEqual(self.observe()['outcome'], 'HOLD_DIFFERENCE')
    def test_foreign_parent_and_cycle_rejected_before_contact(self):
        for mutate in (lambda m: m['task']['records'][1].update(parent_task_id='task-9'),
                       lambda m: m['task']['records'][0].update(parent_task_id='task-2'),
                       lambda m: m['task']['records'][1].update(root_task_id='task-2')):
            m = deepcopy(self.m); mutate(m)
            with self.assertRaises(ValueError): tree.targets(m)
    def test_rehashed_history_omission_or_success_flags_rejected_offline(self):
        for mutate in (lambda s: s[-1]['history_witness']['after'].clear(),
                       lambda s: s[2]['task_witness'].update(parentTaskKey='task-9')):
            report = self.observe(); x = context(self.m, report)
            for row in report['history']: mutate(row['states'])
            reseal(report, x)
            self.assertEqual(rr.review(self.m, report, x)['result'], 'HOLD_INVALID_EVIDENCE')
    def test_cli_real_tls_queries_children_and_cleans_collectors(self):
        with Fixture() as f, tempfile.TemporaryDirectory() as tmp:
            m = manifest(f.origin); m['contact_enabled'] = True; client = Client(m)
            f.routes = {key: dict(body=value) for key, value in client.routes.items()}
            from tests.test_vsphere_history import routes
            create, read, destroy = routes(f, [])
            pages = []; created = []
            def collector(body):
                self.assertEqual(body, {'filter': {'parentTaskKey': ['task-1', 'task-2']}})
                pages[:] = [deepcopy(client.history), []]; created.append(True)
                return {'body': {'type': 'TaskHistoryCollector', 'value': 'collector-1'}}
            f.post_routes[create] = collector; f.post_routes[read] = lambda _: {'body': pages.pop(0)}
            folder = Path(tmp); path = folder / 'manifest.json'; path.write_text(json.dumps(m))
            output = folder / 'report.json'
            result = subprocess.run(module_command(tree, [str(path),
                '--read-authorized-target', '--expected-origin', f.origin, '--ca-file', str(f.directory / 'ca.pem'),
                '--output', str(output), '--interval', '0']), capture_output=True, text=True,
                env=dict(os.environ, VCENTER_SESSION='fixture-session'), timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(output.read_text()); self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
            self.assertEqual(len(created), 4)
            self.assertEqual(sum(r['path'] == destroy for r in f.requests), 4)
            self.assertTrue(all(r['method'] == 'GET' or r['path'] in {create, read, destroy} for r in f.requests))


if __name__ == '__main__': unittest.main()
