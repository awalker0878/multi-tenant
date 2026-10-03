"""AHV task/snapshot composition over loopback TLS; no native qualification."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from lab.native_readback_fixture import Fixture
from tests.test_nutanix_vm_observe import manifest as vm_manifest, uid
from provisioner.execution import readback_cli
from provisioner.execution import nutanix_vm_task_observe as ahv
from provisioner.execution import nutanix_vm_observe as vm
from provisioner.execution import readback_core as c
from provisioner.execution import nutanix_task_tree as tree

ROOT = Path(__file__).resolve().parents[1]
TASK = 'ZXJnb24=:88888888-8888-4888-8888-888888888888'
CHILD = 'ZXJnb24=:99999999-9999-4999-8999-999999999999'


def task_manifest(m=None):
    m = deepcopy(m) if m is not None else vm_manifest()
    now = datetime.now(timezone.utc)
    m['profile'] = ahv.PROFILE
    m['task'] = {'ext_id': TASK, 'operation': 'Fixture VM reconfigure',
        'created_after': (now - timedelta(seconds=120)).isoformat(),
        'created_before': (now - timedelta(seconds=5)).isoformat(),
        'entity_ids': [r['ext_id'] for r in m['resources']],
        'descendants': [{'ext_id': CHILD, 'parent_ext_id': TASK,
                         'operation': 'Fixture VM power on', 'entity_ids': [m['resources'][0]['ext_id']]}]}
    return m


def responses(m):
    now = datetime.now(timezone.utc)
    routes = {vm.resource_target(r): {'body': {'data': deepcopy(r['expected'])}, 'etag': r['expected_etag']}
              for r in m['resources']}
    for index, spec in enumerate(tree.specs(m)):
        children = tree.children(m, spec['ext_id'])
        data = {'$objectType': 'prism.v4.config.Task', 'extId': spec['ext_id'], 'operation': spec['operation'],
                'createdTime': (now - timedelta(seconds=90-index)).isoformat(),
                'completedTime': (now - timedelta(seconds=10+index)).isoformat(), 'status': 'SUCCEEDED',
                'numberOfSubtasks': len(children), 'subTasks': [{'extId': x} for x in children],
                'numberOfEntitiesAffected': len(spec['entity_ids']),
                'entitiesAffected': [{'extId': x} for x in spec['entity_ids']],
                'rootTask': {'extId': TASK}, 'errorMessages': [], 'warnings': []}
        if spec['parent_ext_id']: data['parentTask'] = {'extId': spec['parent_ext_id']}
        routes[tree.target(spec['ext_id'])] = {'body': {'data': data}}
    return routes


class ScopeTests(unittest.TestCase):
    def test_single_recorded_vm_task_is_explicitly_supported(self):
        m = task_manifest(); m['task']['descendants'] = []
        self.assertEqual(len(ahv.targets(m)), 2)

    def test_snapshot_profile_and_missing_task_are_rejected(self):
        m = task_manifest()
        with self.assertRaises(ValueError): vm.validate(m)
        del m['task']
        with self.assertRaises(ValueError): ahv.validate(m)
        with self.assertRaises(ValueError): ahv.validate(vm_manifest())

    def test_task_graph_and_vm_validation_both_apply(self):
        mutations = [lambda m: m['task'].update(entity_ids=[]),
                     lambda m: m['task'].update(entity_ids=[uid(1), uid(1)]),
                     lambda m: m['task'].update(entity_ids=[{}]),
                     lambda m: m['task'].update(created_before='2000-01-01T00:00:00Z'),
                     lambda m: m['task']['descendants'][0].update(parent_ext_id='foreign'),
                     lambda m: m['task']['descendants'][0].update(entity_ids=[uid(2)]),
                     lambda m: m['task'].update(descendants=m['task']['descendants'] * 16),
                     lambda m: m['task'].update(ext_id='https://other.invalid/task'),
                     lambda m: m['resources'][0].update(expected_etag='W/"weak"'),
                     lambda m: m['resources'][0]['expected'].update(isCrossClusterMigrationInProgress=True)]
        for mutate in mutations:
            m = task_manifest(); mutate(m)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): ahv.targets(m)


class TLSVMTaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.f = Fixture()
    @classmethod
    def tearDownClass(cls): cls.f.close()
    def setUp(self):
        self.m = task_manifest(vm_manifest(self.f.origin))
        self.f.routes = responses(self.m); self.f.requests = []; self.f.counts = {}; self.f.hook = None
    def data(self, ident=CHILD): return self.f.routes[tree.target(ident)]['body']['data']
    def observe(self):
        client = c.ReadClient(self.f.origin, self.f.origin, 'reader', 'fixture-only', ahv.targets(self.m),
                              str(self.f.directory / 'ca.pem'))
        r = c.observe(self.m, client, ahv, rounds=3, interval=0)
        self.assertTrue(all(q['method'] == 'GET' and q['path'] in ahv.targets(self.m) for q in self.f.requests))
        self.assertTrue(all(r[k] is False for k in ('may_apply', 'may_delete', 'may_activate')))
        return r
    def outcome(self, expected):
        r = self.observe(); self.assertEqual(r['outcome'], expected); return r

    def test_success_brackets_vm_with_tasks_in_reverse_order(self):
        r = self.outcome('READBACK_MATCH_NOT_QUALIFIED')
        self.assertEqual(r['request_count'], 10)
        expected = [tree.target(TASK), tree.target(CHILD), vm.resource_target(self.m['resources'][0]),
                    tree.target(CHILD), tree.target(TASK)]
        self.assertEqual([q['path'] for q in self.f.requests], expected * 2)
        self.assertTrue(r['history'][-1]['states'][0]['task_completion_observed'])

    def test_successful_single_task(self):
        self.m['task']['descendants'] = []; self.f.routes = responses(self.m)
        self.assertEqual(self.outcome('READBACK_MATCH_NOT_QUALIFIED')['request_count'], 6)

    def test_parent_success_cannot_hide_pending_child(self):
        self.data().update(status='RUNNING', completedTime=None)
        r = self.outcome('HOLD_NATIVE_PENDING')
        self.assertEqual(r['history'][-1]['states'][0]['config_status'], 'MATCH')
        self.assertFalse(r['history'][-1]['states'][0]['task_completion_observed'])

    def test_failed_child_cannot_be_hidden_by_vm_match(self):
        self.data().update(status='FAILED', legacyErrorMessage='PRIVATE-DIAGNOSTIC')
        r = self.outcome('HOLD_NATIVE_FAILURE')
        self.assertNotIn('PRIVATE-DIAGNOSTIC', json.dumps(r))
        self.assertFalse(r['history'][0]['states'][0]['task_completion_observed'])

    def test_vm_drift_holds_despite_completed_tasks(self):
        self.f.routes[vm.resource_target(self.m['resources'][0])]['body']['data']['powerState'] = 'OFF'
        self.outcome('HOLD_DIFFERENCE')

    def test_foreign_entity_and_truncated_children_hold(self):
        self.data().update(entitiesAffected=[{'extId': uid(2)}])
        self.outcome('HOLD_UNCERTAIN')
        self.setUp(); self.data(TASK).update(numberOfSubtasks=2)
        self.outcome('HOLD_UNCERTAIN')

    def test_missing_task_is_not_retried_and_href_is_not_followed(self):
        self.data(TASK)['href'] = 'https://other.invalid/secret'
        self.f.routes[tree.target(CHILD)] = {'status': 404, 'body': {}}
        self.outcome('HOLD_UNCERTAIN')
        self.assertEqual(self.f.counts[tree.target(CHILD)], 1)
        self.assertNotIn(vm.resource_target(self.m['resources'][0]), self.f.counts)

    def test_terminal_regression_across_reads_holds(self):
        def hook(path, count, spec):
            if path == tree.target(CHILD) and count >= 3:
                spec['body']['data'].update(status='RUNNING', completedTime=None)
            return spec
        self.f.hook = hook; self.outcome('HOLD_UNCERTAIN')

    def test_delayed_task_requires_two_complete_stable_rounds(self):
        def hook(path, count, spec):
            if path == tree.target(CHILD) and count <= 2:
                spec['body']['data'].update(status='RUNNING', completedTime=None)
            return spec
        self.f.hook = hook; r = self.outcome('READBACK_MATCH_NOT_QUALIFIED')
        self.assertEqual([row['outcome'] for row in r['history']],
                         ['HOLD_NATIVE_PENDING', 'HOLD_UNSTABLE', 'READBACK_MATCH_NOT_QUALIFIED'])

    def test_completion_flag_cannot_be_relabeled(self):
        r = self.observe(); states = deepcopy(r['history'][-1]['states'])
        states[0]['task_completion_observed'] = False
        with self.assertRaises(c.ObservationError): ahv.validate_observation_history(self.m, [], states)
        states[0]['task_completion_observed'] = 1
        with self.assertRaises(c.ObservationError): ahv.validate_observation_history(self.m, [], states)

    def test_multiple_vms_share_witness_once_and_every_identity_is_bound(self):
        second = deepcopy(self.m['resources'][0]); second['ext_id'] = second['expected']['extId'] = uid(20)
        self.m['resources'].append(second); self.m['task']['entity_ids'].append(uid(20))
        self.f.routes = responses(self.m); r = self.outcome('READBACK_MATCH_NOT_QUALIFIED')
        states = r['history'][-1]['states']
        self.assertNotIn('task_tree', states[1]); self.assertEqual(states[0]['task_sha256'], states[1]['task_sha256'])
        self.f.routes[vm.resource_target(second)]['body']['data']['tenantId'] = uid(21)
        self.outcome('HOLD_UNCERTAIN')

    def test_cli_defaults_offline_and_writes_private_evidence_only_when_enabled(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = Path(directory) / 'manifest.json'; output = Path(directory) / 'readback.json'
            args = [*readback_cli.module_command(ahv, []), str(manifest_path)]
            manifest_path.write_text(json.dumps(self.m))
            result = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)['planned_get_targets'], 3); self.assertFalse(self.f.requests)
            args += ['--read-authorized-target', '--expected-origin', self.f.origin,
                     '--ca-file', str(self.f.directory / 'ca.pem'), '--output', str(output), '--interval', '0']
            self.m['contact_enabled'] = True; manifest_path.write_text(json.dumps(self.m))
            env = dict(os.environ, NUTANIX_USERNAME='reader', NUTANIX_PASSWORD='fixture-only')
            result = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, env=env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(c.load(output)['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            count = len(self.f.requests)
            result = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, env=env)
            self.assertEqual(result.returncode, 2); self.assertEqual(len(self.f.requests), count)


if __name__ == '__main__': unittest.main()
