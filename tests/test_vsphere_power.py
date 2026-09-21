"""Power lifecycle fault injection, including real TLS native request shapes."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from lab.native_readback_fixture import Fixture
from tests.test_vsphere_observe import Client as SnapshotClient, manifest, ref
from tools import execution_journal as j, readback_core as c, vsphere_power as p
from tools import vsphere_observe as vm, vsphere_task_observe as task
from tools.run_files import encoded, replace_private, utcnow


def request(origin='https://vcenter.example.invalid', desired='poweredOff'):
    snapshot = manifest(origin); snapshot['contact_enabled'] = True
    if desired == 'poweredOn':
        snapshot['resources'][0]['expected']['runtime']['powerState'] = 'poweredOff'
        snapshot['resources'][0]['expected']['config']['hardware']['device'][-1]['connectable']['connected'] = False
    return dict(format=p.FORMAT, source_commit='a'*40, generation=1, snapshot=snapshot,
                desired_power=desired, task_manager_id='TaskManager')


def authority(req):
    return dict(format='hosting-vsphere-power-authority/1', request_sha256=c.digest(req),
        valid_from=(utcnow()-timedelta(minutes=1)).isoformat(), valid_until=(utcnow()+timedelta(minutes=5)).isoformat(),
        change_ref='TEST', writer_fence_ref='TEST', containment_ref='TEST', placement_ref='TEST',
        data_quiesce_ref='TEST' if req['desired_power'] == 'poweredOff' else None)


class FakeClient(SnapshotClient):
    def __init__(self, req):
        super().__init__(req['snapshot']); self.req = req; self.request_sha256 = c.digest(req)
        self.deadline = time.monotonic()+120; self.writes = 0; self.pending = False; self.extra = False
        self.lost = False; self.task = None
    def power(self):
        self.writes += 1
        resource = self.req['snapshot']['resources'][0]
        after = p.normalize_after(self.req, resource['expected'])
        self.routes = {vm.resource_target(resource, key): deepcopy(value) for key, value in after.items()}
        now = c.now()
        self.task = dict(_typeName='TaskInfo', key='task-1', task=ref('Task', 'task-1'), entity=ref('VirtualMachine', 'vm-1'),
            descriptionId='VirtualMachine.powerOn' if self.req['desired_power']=='poweredOn' else 'VirtualMachine.powerOff',
            eventChainId=123, queueTime=now, startTime=now, completeTime=now, state='success', cancelled=False)
        if self.lost: raise c.ObservationError('TRANSPORT_FAILED')
        return 'task-1'
    def task_info(self, identifier):
        body = deepcopy(self.task)
        if self.pending: body.update(state='running', completeTime=None)
        return task.task_witness(body)
    def activity(self, since):
        result = [self.task_info('task-1')] if self.task else []
        if self.extra: result.append({'key': 'task-2'})
        return result


class PowerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.ledger = Path(self.temp.name); self.req = request(); self.auth = authority(self.req)
        self.client = FakeClient(self.req)
        self.check = patch.object(p, 'verify', return_value={'status':'HASHES_MATCH','commit':'a'*40})
        self.check.start(); self.addCleanup(self.check.stop)
    def run_power(self, **kwargs):
        return p.execute(self.req, self.auth, self.ledger, self.client, execute_approved_change=True, **kwargs)
    def test_success_and_duplicate_return_receipt_without_second_write(self):
        result = self.run_power()
        self.assertEqual(result['status'], p.COMPLETE)
        self.assertFalse(result['production_activation']); self.assertFalse(result['native_acceptance'])
        self.assertEqual(self.run_power(), result); self.assertEqual(self.client.writes, 1)
    def test_pending_then_resume_never_reissues_power(self):
        self.client.pending = True
        with self.assertRaises(ValueError): self.run_power()
        self.client.pending = False
        with self.assertRaises(ValueError): self.run_power()
        self.assertEqual(self.run_power(resume=True)['status'], p.COMPLETE)
        self.assertEqual(self.client.writes, 1)
    def test_lost_reply_and_renamed_operation_remain_held(self):
        self.client.lost = True
        with self.assertRaises(c.ObservationError): self.run_power()
        with self.assertRaisesRegex(ValueError, 'response was lost'): self.run_power(resume=True)
        self.req['snapshot']['operation_id'] = 'renamed'; self.req['generation'] = 2
        self.auth = authority(self.req); self.client.request_sha256 = c.digest(self.req)
        with self.assertRaises(ValueError): self.run_power()
        self.assertEqual(self.client.writes, 1)
    def test_independent_lost_response_mapping_restores_observation_without_writes(self):
        self.client.lost=True
        with self.assertRaises(c.ObservationError): self.run_power()
        event=c.load(next(self.ledger.glob('*/00000001.json')))
        claim=dict(format='hosting-vsphere-power-reconciliation/1',request_sha256=c.digest(self.req),
            started_event_sha256=c.digest(event),task_id='task-1',valid_from=self.auth['valid_from'],valid_until=self.auth['valid_until'],
            task_mapping_ref='TEST-INDEPENDENT-MAPPING',writer_fence_ref='TEST',containment_ref='TEST')
        for change in ({'started_event_sha256':'0'*64},{'request_sha256':'0'*64}):
            with self.assertRaises(ValueError): p.reconcile_task(self.req,self.auth,claim|change,self.ledger,self.client)
        self.assertEqual(p.reconcile_task(self.req,self.auth,claim,self.ledger,self.client)['status'],'TASK_BOUND_FOR_READ_ONLY_RESUME')
        self.assertEqual(self.run_power(resume=True)['status'],p.COMPLETE)
        self.assertEqual(self.client.writes,1)
        kinds=[c.load(path)['kind'] for path in sorted(self.ledger.glob('*/*.json'))]
        self.assertIn('TASK_RECONCILED',kinds)
    def test_native_drift_or_competing_work_blocks_completion(self):
        for field in ('disk', 'placement', 'question', 'extra-task', 'task-entity', 'task-before-attempt'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                self.ledger = Path(temp); self.client = FakeClient(self.req)
                original = self.client.power
                def changed():
                    identifier = original(); resource = self.req['snapshot']['resources'][0]
                    if field == 'disk': self.client.routes[vm.resource_target(resource,'config')]['hardware']['device'][1]['backing']['uuid'] = 'foreign'
                    if field == 'placement': self.client.routes[vm.resource_target(resource,'runtime')]['host']['value'] = 'host-2'
                    if field == 'question': self.client.routes[vm.resource_target(resource,'runtime')]['question'] = {'text':'PRIVATE'}
                    if field == 'extra-task': self.client.extra = True
                    if field == 'task-entity': self.client.task['entity']['value'] = 'vm-2'
                    if field == 'task-before-attempt': self.client.task['queueTime'] = '2020-01-01T00:00:00Z'
                    return identifier
                self.client.power = changed
                with self.assertRaises(ValueError): self.run_power()
                self.assertEqual(self.client.writes, 1)
    def test_stale_authority_wrong_source_opt_in_and_changed_prestate_do_not_write(self):
        self.auth['valid_until'] = (utcnow()-timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError): self.run_power()
        self.auth = authority(self.req)
        with patch.object(p, 'verify', return_value={'status':'FAILED_INTEGRITY_CHECK'}):
            with self.assertRaises(ValueError): self.run_power()
        with self.assertRaises(ValueError): p.execute(self.req,self.auth,self.ledger,self.client)
        self.client.routes[next(k for k in self.client.routes if k.endswith('/runtime'))]['powerState']='poweredOff'
        with self.assertRaises(ValueError): self.run_power()
        self.assertEqual(self.client.writes, 0)
    def test_interruption_after_task_return_resumes_binding(self):
        original = self.client.task_info
        self.client.task_info = lambda _: (_ for _ in ()).throw(c.ObservationError('TRANSPORT_FAILED'))
        with self.assertRaises(c.ObservationError): self.run_power()
        self.client.task_info = original
        self.assertEqual(self.run_power(resume=True)['status'],p.COMPLETE)
        self.assertEqual(self.client.writes,1)
    def test_changed_journal_chain_and_orphan_event_hold(self):
        self.run_power()
        path = next(self.ledger.glob('*/00000002.json'))
        value = c.load(path); value['data']['task_id'] = 'task-2'; replace_private(path,encoded(value))
        with self.assertRaisesRegex(ValueError,'chain differs'): self.run_power()
    def test_power_on_and_off_use_only_exact_native_method_and_session(self):
        for desired in ('poweredOn','poweredOff'):
            with self.subTest(desired=desired), Fixture() as f:
                req = request(f.origin,desired); client=p.Client(req,'fixture-session',str(f.directory/'ca.pem'))
                method = 'PowerOnVM_Task' if desired=='poweredOn' else 'PowerOffVM_Task'
                path = vm.resource_target(req['snapshot']['resources'][0],method)
                f.post_routes[path]={'body':ref('Task','task-1')}
                self.assertEqual(client.power(),'task-1')
                self.assertEqual(f.post_bodies,[(path,{'host':ref('HostSystem','host-1')} if desired=='poweredOn' else None)])
                self.assertTrue(f.requests[0]['has_session_auth']); self.assertFalse(f.requests[0]['has_basic_auth'])
    def test_real_tls_full_execution_retains_exact_native_task(self):
        with Fixture() as f:
            req=request(f.origin); resource=req['snapshot']['resources'][0]; fake=FakeClient(req)
            f.routes={k:{'body':v} for k,v in fake.routes.items()}
            def power(_):
                fake.power()
                f.routes={k:{'body':v} for k,v in fake.routes.items()}
                f.routes[task.task_target({'moid':'task-1'})]={'body':fake.task}
                return {'body':ref('Task','task-1')}
            f.post_routes[vm.resource_target(resource,'PowerOffVM_Task')]=power
            pages=[]
            def collector(body):
                pages.clear()
                pages.extend([fake.activity(c.now())] if fake.task and body['filter']['state']==['success','error'] else [])
                pages.append([])
                return {'body':ref('TaskHistoryCollector','collector-1')}
            f.post_routes[vm.PREFIX+'TaskManager/TaskManager/CreateCollectorForTasks']=collector
            f.post_routes[vm.PREFIX+'TaskHistoryCollector/collector-1/ReadNextTasks']=lambda _: {'body':pages.pop(0)}
            f.post_routes[vm.PREFIX+'HistoryCollector/collector-1/DestroyCollector']={'status':204}
            result=p.execute(req,authority(req),self.ledger,p.Client(req,'fixture',str(f.directory/'ca.pem')),execute_approved_change=True)
            self.assertEqual(result['status'],p.COMPLETE)
            self.assertEqual(len([r for r in f.requests if r['path'].endswith('PowerOffVM_Task')]),1)
    def test_journal_lock_and_gap_cannot_be_bypassed(self):
        with j.locked(self.ledger,{'resource':'test'}) as log:
            log.append('STARTED',{})
            with self.assertRaises(BlockingIOError):
                with j.locked(self.ledger,{'resource':'test'}): pass
            (log.directory/'00000001.json').rename(log.directory/'00000002.json')
        with self.assertRaises(ValueError):
            with j.locked(self.ledger,{'resource':'test'}): pass


if __name__ == '__main__': unittest.main()
