"""Template clone identity, destination task tree and offline review regressions."""
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
from tests.test_nutanix_vm_observe import uid
from tests.test_vsphere_observe import ref
from tests.test_vsphere_task_tree import manifest as tree_manifest, Client as TreeClient
from tests.test_vsphere_recovery import reseal
from provisioner.execution import readback_core as c
from tools import recovery_review as rr, qualify_target as q
from tools import vsphere_task_observe as task, vsphere_task_tree_observe as tree, vsphere_observe as vm


def manifest(origin='https://vcenter.example.invalid'):
    m = tree_manifest(origin); m['profile'] = tree.CLONE_PROFILE
    m['task']['sources'] = [dict(moid='vm-9', expected=dict(_typeName='VirtualMachineConfigInfo',
        uuid=uid(9), instanceUuid=uid(10), template=True, changeVersion='accepted-template-revision'))]
    m['task']['records'][0].update(description_id=task.CLONE, source_moid='vm-9')
    return m


class Client(TreeClient):
    def __init__(self, m):
        super().__init__(m)
        self.routes[task.task_target(m['task']['records'][0])].update(entity=ref('VirtualMachine', 'vm-9'), result=ref('VirtualMachine', 'vm-1'))
        for source in m['task']['sources']: self.routes[vm.resource_target(source, 'config')] = deepcopy(source['expected'])


class CloneTreeTests(unittest.TestCase):
    def setUp(self): self.m = manifest(); self.client = Client(self.m)
    def observe(self): return c.observe(self.m, self.client, tree, interval=0)
    def test_source_result_and_children_match_for_review_only(self):
        r = self.observe()
        self.assertEqual(r['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
        self.assertEqual(rr.review(self.m, r, context(self.m, r))['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        self.assertIs(q.vsphere_adapter(self.m), tree)
        self.assertEqual({s['resource_key'] for s in r['history'][-1]['states']}, {'vm-1', 'vm-9', 'task-1', 'task-2', 'task-coverage'})
        self.assertFalse(r['may_apply'])
    def test_wrong_source_result_or_template_identity_holds(self):
        for destination, mutation in [(task.task_target(self.m['task']['records'][0]), {'result': ref('VirtualMachine', 'vm-2')}),
            (task.task_target(self.m['task']['records'][0]), {'entity': ref('VirtualMachine', 'vm-8')}),
            (vm.resource_target(self.m['task']['sources'][0], 'config'), {'uuid': uid(11)}),
            (vm.resource_target(self.m['task']['sources'][0], 'config'), {'template': False})]:
            self.client = Client(self.m); self.client.routes[destination].update(mutation)
            self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
    def test_template_revision_drift_and_missing_children_hold(self):
        path = vm.resource_target(self.m['task']['sources'][0], 'config')
        self.client.routes[path]['changeVersion'] = 'changed'
        self.assertEqual(self.observe()['outcome'], 'HOLD_DIFFERENCE')
        self.client = Client(self.m); self.client.history.clear()
        self.assertEqual(self.observe()['outcome'], 'HOLD_DIFFERENCE')
    def test_ambiguous_source_or_clone_graph_is_rejected(self):
        for mutate in (lambda m: m['task']['sources'][0].update(moid='vm-1'),
            lambda m: m['task']['sources'][0]['expected'].update(uuid=uid(1)),
            lambda m: m['task']['sources'].append(deepcopy(m['task']['sources'][0])),
            lambda m: m['task']['records'][0].update(parent_task_id='task-2'),
            lambda m: m['task']['records'][0].update(source_moid='vm-8')):
            m = deepcopy(self.m); mutate(m)
            with self.assertRaises(ValueError): tree.targets(m)
    def test_rehashed_source_or_result_witness_cannot_override_summary(self):
        for mutate in (lambda states: next(s for s in states if s['resource_key'] == 'vm-9')['source_witness']['after'].update(uuid=uid(11)),
            lambda states: next(s for s in states if s['resource_key'] == 'task-1')['task_witness']['result_reference'].update(value='vm-2')):
            report = self.observe(); x = context(self.m, report)
            for row in report['history']: mutate(row['states'])
            reseal(report, x)
            self.assertEqual(rr.review(self.m, report, x)['result'], 'HOLD_INVALID_EVIDENCE')
    def test_cli_collects_source_without_copying_unselected_template_material(self):
        with Fixture() as f, tempfile.TemporaryDirectory() as tmp:
            m = manifest(f.origin); m['contact_enabled'] = True; client = Client(m)
            client.routes[vm.resource_target(m['task']['sources'][0], 'config')]['extraConfig'] = [{'value': 'PRIVATE-TEMPLATE-SENTINEL'}]
            f.routes = {key: dict(body=value) for key, value in client.routes.items()}
            from tests.test_vsphere_history import routes
            create, read, destroy = routes(f, []); pages = []
            def collector(body):
                self.assertEqual(body, {'filter': {'parentTaskKey': ['task-1', 'task-2']}})
                pages[:] = [deepcopy(client.history), []]
                return {'body': {'type': 'TaskHistoryCollector', 'value': 'collector-1'}}
            f.post_routes[create] = collector; f.post_routes[read] = lambda _: {'body': pages.pop(0)}
            folder = Path(tmp); path = folder / 'manifest.json'; path.write_text(json.dumps(m)); output = folder / 'report.json'
            result = subprocess.run([sys.executable, str(q.ROOT / 'tools/vsphere_task_tree_observe.py'), str(path),
                '--read-authorized-target', '--expected-origin', f.origin, '--ca-file', str(f.directory / 'ca.pem'),
                '--output', str(output), '--interval', '0'], capture_output=True, text=True,
                env=dict(os.environ, VCENTER_SESSION='fixture-session'), timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn('PRIVATE-TEMPLATE-SENTINEL', output.read_text())
            self.assertEqual(sum(r['path'] == destroy for r in f.requests), 4)
            self.assertTrue(all(r['method'] == 'GET' or r['path'] in {create, read, destroy} for r in f.requests))


if __name__ == '__main__': unittest.main()
