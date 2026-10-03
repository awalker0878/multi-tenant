"""Exact task observations remain evidence, never permission to replay an apply."""
from copy import deepcopy
from datetime import timedelta
import json
import unittest
from lab.native_readback_fixture import Fixture
from tests.test_vsphere_observe import Client, manifest as vm_manifest, ref
from provisioner.execution import readback_core as c
from provisioner.execution import vsphere_task_observe as t
from provisioner.execution.run_files import utcnow


def manifest(origin='https://vcenter.example.invalid'):
    m = vm_manifest(origin); m['profile'] = t.PROFILE
    queued = (utcnow() - timedelta(minutes=1)).isoformat()
    m['task'] = {'execution_record_ref': 'FIXTURE-NO-AUTHORITY', 'records': [dict(moid='task-1', vm_moid='vm-1',
        description_id='VirtualMachine.powerOn', queued_at=queued, event_chain_id=123)]}
    return m


def task_body(m):
    record = m['task']['records'][0]
    return dict(_typeName='TaskInfo', key='task-1', task=ref('Task', 'task-1'), entity=ref('VirtualMachine', 'vm-1'),
        descriptionId=record['description_id'], eventChainId=record['event_chain_id'], queueTime=record['queued_at'],
        startTime=record['queued_at'], completeTime=(utcnow() - timedelta(seconds=1)).isoformat(), state='success', cancelled=False)


class VsphereTaskTests(unittest.TestCase):
    def setUp(self):
        self.m = manifest(); self.client = Client(self.m); self.path = t.task_target(self.m['task']['records'][0])
        self.client.routes[self.path] = task_body(self.m)
    def observe(self): return c.observe(self.m, self.client, t, interval=0)
    def test_success_binds_vm_task_and_chronology_but_never_authorizes_replay(self):
        report = self.observe()
        self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
        self.assertTrue(report['history'][-1]['states'][-1]['task_completion_observed'])
        self.assertFalse(report['may_apply']); self.assertFalse(report['may_activate']); self.assertFalse(report['may_delete'])
    def test_pending_failure_and_cancelled_remain_held_without_error_text(self):
        for change, outcome in [({'state': 'running', 'completeTime': None}, 'HOLD_NATIVE_PENDING'),
                                ({'state': 'error', 'error': {'message': 'SECRET-SENTINEL'}}, 'HOLD_NATIVE_FAILURE'),
                                ({'cancelled': True}, 'HOLD_NATIVE_FAILURE')]:
            self.client.routes[self.path] = task_body(self.m) | change
            report = self.observe(); self.assertEqual(report['outcome'], outcome)
            self.assertNotIn('SECRET-SENTINEL', json.dumps(report))
    def test_foreign_replayed_composite_or_incomplete_task_holds(self):
        for change in ({'key': 'task-2'}, {'entity': ref('VirtualMachine', 'vm-2')}, {'eventChainId': 124},
            {'queueTime': '2020-01-01T00:00:00Z'}, {'descriptionId': 'VirtualMachine.destroy'},
            {'cancelled': 0}, {'parentTaskKey': 'task-2'}, {'rootTaskKey': 'task-2'}, {'completeTime': None},
            {'completeTime': '2020-01-01T00:00:00Z'}, {'result': {'type': 'VirtualMachine', 'value': 'vm-2'}},
            {'error': {'message': 'unexpected'}}):
            self.client.routes[self.path] = task_body(self.m) | change
            with self.subTest(change=change): self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
    def test_terminal_regression_held_and_task_success_does_not_mask_vm_drift(self):
        self.client.transform = lambda path, body, count: body.update(state='running', completeTime=None) if path == self.path and count > 1 else None
        self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
        self.client.transform = None
        self.client.routes[next(k for k in self.client.routes if k.endswith('/runtime'))]['powerState'] = 'poweredOff'
        self.assertEqual(self.observe()['outcome'], 'HOLD_DIFFERENCE')
    def test_manifest_must_cover_exact_vms_and_tasks(self):
        for mutate in (lambda m: m['task']['records'][0].update(vm_moid='vm-2'),
            lambda m: m['task']['records'][0].update(description_id='VirtualMachine.destroy'),
            lambda m: m['task']['records'].append(deepcopy(m['task']['records'][0]))):
            m = deepcopy(self.m); mutate(m)
            with self.assertRaises(ValueError): t.targets(m)
    def test_real_tls_queries_only_exact_properties_and_task_info(self):
        with Fixture() as f:
            m = manifest(f.origin); routes = Client(m).routes
            routes[t.task_target(m['task']['records'][0])] = task_body(m)
            f.routes = {key: {'body': value} for key, value in routes.items()}
            client = c.ReadClient(f.origin, f.origin, None, None, t.targets(m), str(f.directory / 'ca.pem'), session_token='fixture')
            self.assertEqual(c.observe(m, client, t, interval=0)['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
            self.assertEqual({x['path'] for x in f.requests}, t.targets(m))
            self.assertTrue(all(x['method'] == 'GET' and x['has_session_auth'] for x in f.requests))


if __name__ == '__main__': unittest.main()
