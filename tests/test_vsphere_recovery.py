"""Replay-safe offline review of witnessed vSphere tasks and exact VM coverage."""
from copy import deepcopy
import json
import unittest
from tests.test_native_readback import context
from tests.test_vsphere_observe import Client
from tests.test_vsphere_task_observe import manifest, task_body
from provisioner.execution import readback_core as c
from tools import recovery_review as rr, vsphere_task_observe as t


def fixture():
    m = manifest(); client = Client(m); client.routes[t.task_target(m['task']['records'][0])] = task_body(m)
    report = c.observe(m, client, t, interval=0)
    return m, report, context(m, report)


def reseal(report, context):
    previous = None; stable = 0
    for row in report['history']:
        row['snapshot_sha256'] = c.digest(row['states'])
        stable = stable + 1 if row['snapshot_sha256'] == previous else 1
        previous = row['snapshot_sha256']; row['outcome'] = c.outcome(row['states'], stable)
    report.update(outcome=row['outcome'], stable_rounds=stable)
    report['content_sha256'] = c.digest({k: v for k, v in report.items() if k != 'content_sha256'})
    context['report_sha256'] = report['content_sha256']


class VsphereRecoveryTests(unittest.TestCase):
    def test_rehashed_vm_drift_cannot_be_promoted_to_matching_task_evidence(self):
        for mutate in (lambda body: body['hardware']['device'][1]['backing'].update(uuid='foreign-disk'),
                       lambda body: body.update(changeVersion='different-revision')):
            m = manifest(); client = Client(m)
            client.routes[t.task_target(m['task']['records'][0])] = task_body(m)
            mutate(client.routes[t.vm.resource_target(m['resources'][0], 'config')])
            report = c.observe(m, client, t, interval=0); x = context(m, report)
            self.assertEqual(report['outcome'], 'HOLD_DIFFERENCE')
            for row in report['history']:
                row['states'][0].update(config_status='MATCH', identity_match=True, mismatch_fields=[])
            report['history'].append(deepcopy(report['history'][0]) | {'round': 2})
            reseal(report, x)
            self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
            self.assertEqual(rr.review(m, report, x)['result'], 'HOLD_INVALID_EVIDENCE')

    def test_pending_runtime_question_is_rechecked_without_exporting_its_text(self):
        m = manifest(); client = Client(m); client.routes[t.task_target(m['task']['records'][0])] = task_body(m)
        client.routes[t.vm.resource_target(m['resources'][0], 'runtime')]['question'] = {'text': 'PRIVATE-QUESTION-SENTINEL'}
        report = c.observe(m, client, t, interval=0); x = context(m, report)
        self.assertNotIn('PRIVATE-QUESTION-SENTINEL', json.dumps(report))
        for row in report['history']: row['states'][0].update(config_status='MATCH', mismatch_fields=[])
        report['history'].append(deepcopy(report['history'][0]) | {'round': 2}); reseal(report, x)
        self.assertEqual(rr.review(m, report, x)['result'], 'HOLD_INVALID_EVIDENCE')

    def test_missing_or_contradictory_vm_snapshot_witness_remains_invalid(self):
        for change in (lambda state: state.pop('vm_witness'), lambda state: state.update(task_completion_observed=True),
            lambda state: state['vm_witness']['before'].update(selected_sha256='f' * 64),
            lambda state: state['vm_witness']['after'].update(runtime_question=0)):
            m, report, x = fixture()
            for row in report['history']: change(row['states'][0])
            reseal(report, x)
            self.assertEqual(rr.review(m, report, x)['result'], 'HOLD_INVALID_EVIDENCE')

    def test_unselected_native_device_fields_are_hashed_without_export(self):
        m = manifest(); client = Client(m); client.routes[t.task_target(m['task']['records'][0])] = task_body(m)
        client.routes[t.vm.resource_target(m['resources'][0], 'config')]['hardware']['device'][2]['unselected'] = 'PRIVATE-DEVICE-SENTINEL'
        report = c.observe(m, client, t, interval=0)
        self.assertEqual(report['outcome'], 'HOLD_DIFFERENCE')
        self.assertNotIn('PRIVATE-DEVICE-SENTINEL', json.dumps(report))

    def test_matching_tasks_still_need_fence_and_containment_evidence(self):
        m, report, x = fixture()
        self.assertEqual(rr.review(m, report, x)['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        x['writer_fence']['state'] = 'UNVERIFIED'
        self.assertEqual(rr.review(m, report, x)['result'], 'HOLD_WRITER_NOT_FENCED')
        x['containment'] = 'ACTIVE'
        result = rr.review(m, report, x)
        self.assertEqual(result['result'], 'KEEP_INCIDENT_CONTAINMENT')
        self.assertFalse(result['may_apply'])
    def test_rehashed_forged_task_summary_or_missing_coverage_is_rejected(self):
        for mutate in (lambda states: states.pop(), lambda states: states[-1].pop('task_witness'),
            lambda states: states[-1]['task_witness'].update(state='running', completeTime=None),
            lambda states: states[-1]['task_witness'].update(completeTime='2099-01-01T00:00:00Z'),
            lambda states: states[-1].update(task_completion_observed=False)):
            m, report, x = fixture()
            for row in report['history']: mutate(row['states'])
            reseal(report, x)
            with self.subTest(mutate=mutate): self.assertEqual(rr.review(m, report, x)['result'], 'HOLD_INVALID_EVIDENCE')
    def test_snapshot_alone_cannot_enter_completion_review(self):
        from tools import vsphere_observe as vm
        m, _, _ = fixture(); m = t.vm_manifest(m)
        report = c.observe(m, Client(m), vm, interval=0)
        self.assertEqual(rr.review(m, report, context(m, report))['result'], 'HOLD_INVALID_EVIDENCE')
    def test_invalid_native_metadata_and_fault_text_are_not_journaled(self):
        m = manifest(); client = Client(m); path = t.task_target(m['task']['records'][0])
        client.routes[path] = task_body(m) | {'error': {'message': 'SECRET-SENTINEL'}}
        client.routes[path]['entity']['extra'] = 'SECRET-SENTINEL'
        report = c.observe(m, client, t, interval=0)
        self.assertEqual(report['outcome'], 'HOLD_UNCERTAIN')
        self.assertNotIn('SECRET-SENTINEL', json.dumps(report))


if __name__ == '__main__': unittest.main()
