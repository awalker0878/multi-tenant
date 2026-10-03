"""Task-aware AHV review and campaign integration; all services are fixtures."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
from lab.native_readback_fixture import Fixture, responses as network_responses
from lab.run_readback_lab import operator_context
from tests.test_nutanix_vm_task_observe import task_manifest, responses, CHILD
from tests.test_nutanix_vm_observe import manifest as vm_manifest
from tests.test_nutanix_task_tree import reseal
from tests.test_flow_campaign import inputs
from tests.test_target_campaign import window
from tests import test_nutanix_vm_activity as activity_fixture
from tools import nutanix_vm_task_observe as ahv, nutanix_flow_observe as flow
from provisioner.execution import readback_core as c
from tools import nutanix_task_tree as tree, recovery_review as rr, qualify_target as q
from tools.guest_inventory import build
from provisioner.execution.run_files import digest, encoded, write_new


class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.f = Fixture()
    @classmethod
    def tearDownClass(cls): cls.f.close()
    def setUp(self):
        self.m = task_manifest(vm_manifest(self.f.origin)); self.f.routes = responses(self.m)
        self.f.requests = []; self.f.counts = {}; self.f.hook = None
    def observe(self):
        client = c.ReadClient(self.f.origin, self.f.origin, 'fixture', 'fixture', ahv.targets(self.m),
                              str(self.f.directory / 'ca.pem'))
        return c.observe(self.m, client, ahv, interval=0)
    def context(self, report):
        context = operator_context(self.m, report); context['attempted_at'] = self.m['task']['created_after']
        return context
    def decision(self, report, context=None):
        result = rr.review(self.m, report, context or self.context(report))
        self.assertTrue(all(result[k] is False for k in ('may_apply', 'may_delete', 'may_activate')))
        return result['result']

    def test_success_is_only_operator_review_and_still_requires_fence_and_quarantine(self):
        report = self.observe()
        self.assertEqual(self.decision(report), 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        for mutate, expected in (
            (lambda x: x.update(executor_state='RUNNING'), 'HOLD_WRITER_NOT_FENCED'),
            (lambda x: x['writer_fence'].update(state='UNKNOWN'), 'HOLD_WRITER_NOT_FENCED'),
            (lambda x: x['quarantine'].update(state='UNKNOWN'), 'HOLD_QUARANTINE_NOT_VERIFIED'),
            (lambda x: x.update(containment='ACTIVE'), 'KEEP_INCIDENT_CONTAINMENT'),
            (lambda x: x.update(current_generation=5), 'HOLD_SUPERSEDED_CHANGE')):
            context = self.context(report); mutate(context)
            with self.subTest(expected=expected): self.assertEqual(self.decision(report, context), expected)

    def test_pending_failure_and_missing_task_hold_despite_matching_vm(self):
        for status, expected in (('RUNNING', 'WAIT_FOR_NATIVE_TASK'), ('FAILED', 'INSPECT_PARTIAL_FAILURE')):
            self.setUp(); self.f.routes[tree.target(CHILD)]['body']['data'].update(status=status, completedTime=None)
            self.assertEqual(self.decision(self.observe()), expected)
        self.setUp(); self.f.routes[tree.target(CHILD)] = {'status': 404, 'body': {}}
        self.assertEqual(self.decision(self.observe()), 'HOLD_NATIVE_UNCERTAINTY')

    def test_attempt_window_cannot_be_shifted_or_cover_future_work(self):
        report = self.observe(); context = self.context(report)
        context['attempted_at'] = (c.timestamp(context['attempted_at']) + timedelta(seconds=1)).isoformat()
        self.assertEqual(self.decision(report, context), 'HOLD_INVALID_EVIDENCE')
        self.m['task']['created_before'] = (c.timestamp(report['started_at']) + timedelta(minutes=1)).isoformat()
        report = self.observe()
        self.assertEqual(self.decision(report), 'HOLD_INVALID_EVIDENCE')

    def test_rehashed_completion_flag_or_task_witness_cannot_forge_success(self):
        report = self.observe()
        for mutate in (
            lambda s: s.update(task_completion_observed=False),
            lambda s: s['task_tree']['before'][1]['snapshot'].update(entities=[]),
            lambda s: s.pop('task_tree')):
            bad = deepcopy(report)
            for row in bad['history']: mutate(row['states'][0])
            reseal(bad)
            self.assertEqual(self.decision(bad), 'HOLD_INVALID_EVIDENCE')

    def test_snapshot_only_evidence_cannot_substitute_for_recorded_task_profile(self):
        report = self.observe(); self.m.pop('task'); self.m['profile'] = 'nutanix-ahv-v4.2-vm-snapshot'
        context = operator_context(self.m, report)
        self.assertEqual(self.decision(report, context), 'HOLD_INVALID_EVIDENCE')


class CampaignTests(unittest.TestCase):
    def test_bound_inputs_preserve_vm_and_flow_ownership_for_task_profile(self):
        plan, workload, network, outputs, access, policy, domains = inputs('https://prism.example.test')
        workload = task_manifest(workload)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); inventory, _ = build(outputs, access, str(directory / 'known_hosts'))
            values = dict(inventory=inventory, native_manifest=network, workload_manifest=workload,
                          flow_manifest=policy, domain_outputs=domains)
            for key in plan['assets']:
                raw = encoded(values.get(key, {})); path = directory / key; write_new(path, raw)
                plan['assets'][key] = dict(path=str(path), sha256=digest(raw))
            q.validate(plan); q.bound_inputs(plan, str(directory / 'known_hosts'))
            for mutate in (lambda m: m['task'].update(entity_ids=[]),
                           lambda m: m.update(profile='nutanix-unknown'),
                           lambda m: m.update(tenant_id='foreign'),
                           lambda m: m['resources'][0]['expected'].update(powerState='OFF')):
                bad = deepcopy(workload); mutate(bad)
                with self.assertRaises(ValueError): q.ahv_binding(plan['scope'], bad, outputs, access, network)
            (directory / 'workload_manifest').write_bytes(b'changed')
            with self.assertRaises(ValueError): q.bound_inputs(plan, str(directory / 'known_hosts'))

    def test_v3_and_v4_real_child_readers_bind_tasks_and_stop_on_pending_or_failed_task(self):
        with Fixture() as service:
            for version, status, expected, activity in ((3, 'RUNNING', 'HOLD_NATIVE_PENDING', False),
                    (4, 'FAILED', 'HOLD_NATIVE_FAILURE', False), (3, 'RUNNING', 'HOLD_NATIVE_PENDING', True),
                    (4, 'FAILED', 'HOLD_NATIVE_FAILURE', True)):
                with self.subTest(version=version), tempfile.TemporaryDirectory() as tmp:
                    directory = Path(tmp)
                    plan, workload, network, _, _, policy, _ = inputs(service.origin)
                    plan['format'] = 'hosting-target-campaign/' + str(version)
                    if version == 3:
                        for key in q.FLOW_ASSETS: del plan['assets'][key]
                    q.validate(plan); workload = task_manifest(workload)
                    if activity: workload['profile'] = activity_fixture.a.PROFILE
                    service.routes = network_responses(network) | responses(workload)
                    if activity: service.routes.update(activity_fixture.activity_routes(workload, service.routes))
                    service.requests = []; service.counts = {}
                    r = policy['resources'][0]
                    service.routes[flow.resource_target(r)] = dict(body={'data': r['expected']}, etag=r['expected_etag'])
                    assets = {'native_credentials': encoded(dict(username='fixture', password='fixture')),
                              'workload_manifest': encoded(workload), 'flow_manifest': encoded(policy)}
                    for key, value in (('native_manifest', encoded(network)), ('workload_manifest', encoded(workload)),
                        ('flow_manifest', encoded(policy)), ('native_ca', (service.directory / 'ca.pem').read_bytes())):
                        write_new(directory / key, value)
                    combined = q.native_readback(plan, assets, window(), directory, 'before')
                    names = [('network', 'before'), ('workloads', 'before-workloads')]
                    if version == 4: names.append(('flow', 'before-flow'))
                    self.assertEqual(combined, digest(encoded({key + '_sha256': digest((directory / (name + '.json')).read_bytes())
                                                              for key, name in names})))
                    self.assertTrue(c.load(directory / 'before-workloads.json')['history'][-1]['states'][0]['task_completion_observed'])
                    flow_reads = service.counts.get(flow.resource_target(r), 0)
                    service.routes[tree.target(CHILD)]['body']['data'].update(status=status, completedTime=None)
                    if activity:
                        if status == 'FAILED':
                            service.routes[tree.target(CHILD)]['body']['data']['completedTime'] = workload['task']['created_before']
                            # Child completion must precede the successful parent's completion.
                            service.routes[tree.target(workload['task']['ext_id'])]['body']['data']['completedTime'] = workload['task']['created_before']
                        service.routes.update(activity_fixture.activity_routes(workload, service.routes))
                    with self.assertRaises(ValueError): q.native_readback(plan, assets, window(), directory, 'after')
                    self.assertEqual(c.load(directory / 'after-workloads.json')['outcome'], expected)
                    self.assertFalse((directory / 'after-flow.json').exists())
                    self.assertEqual(service.counts.get(flow.resource_target(r), 0), flow_reads)
                    self.assertTrue(all(row['method'] == 'GET' for row in service.requests))


if __name__ == '__main__': unittest.main()
