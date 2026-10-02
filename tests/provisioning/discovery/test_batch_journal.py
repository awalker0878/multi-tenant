"""Actual journal files/process locks and signed loopback collectors, not fleet qualification."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from provisioner.controlplane.discovery import batch_journal, batch_runtime, collector_runtime
from provisioner.controlplane.discovery.batch_journal import BatchJournal
from provisioner.controlplane.discovery.batch_runtime import DiscoveryBatch, inspect_batch, run_batch
from provisioner.controlplane.discovery.model import _json
from tests.provisioning.discovery import test_batch_runtime as batches
from tests.provisioning.discovery import test_collector_runtime as runtime
from tests.provisioning.discovery.process_fixture import start_prepared, activate


class BatchJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / 'state'; self.directory.mkdir(mode=0o700)
        self.path = self.root / 'batch.json'
        self.at = datetime.now(timezone.utc)
        self.doc = {'format': 'hosting-discovery-batch/1', 'batchId': 'test-batch',
            'maxParallelCollections': 2, 'maxDurationSeconds': 5,
            'endpoints': [{'policyId': 'local', 'organizationId': 'org', 'siteId': 'site',
                'platformFamily': 'nutanix', 'endpointId': 'endpoint',
                'maxConcurrentReads': 1, 'minReadIntervalMilliseconds': 1}],
            'tasks': [{'taskId': f'task-{n}', 'environmentId': 'env', 'campaignDigest': f'{n:064x}',
                'collectorConfigFile': str(self.root / f'collector-{n}.json'),
                'collectorConfigDigest': 'a'*64, 'policyId': 'local',
                'notBefore': (self.at-timedelta(seconds=2)).isoformat(),
                'notAfter': (self.at+timedelta(seconds=60)).isoformat()} for n in (1,2)]}
        runtime.write_json(self.path, self.doc)
        self.spec = DiscoveryBatch.from_file(self.path)

    def journal(self, enroll=True):
        return BatchJournal(self.directory, self.spec, manifest_path=self.path,
                            clock=lambda: self.at, enroll=enroll)

    def files(self):
        return {p.name: p.read_bytes() for p in self.directory.iterdir() if p.is_file()}

    @staticmethod
    def outcome():
        return {'format': 'hosting-discovery-collector-outcome/1', 'status': 'STAGED',
            'campaignId': 'campaign-1', 'environmentId': 'env', 'requestDigest': 'b'*64,
            'resultDigest': 'c'*64, 'completeness': 'PARTIAL', 'objectCount': 4,
            'collectionRequested': True, 'publicationAttempted': False, 'executionAuthorized': False}

    def test_enrollment_and_results_survive_reopen_with_exact_digest_chain(self):
        with self.journal() as state:
            self.assertIsNone(state.summary('task-1'))
            start = state.start('task-1')
            done = state.finish('task-1', self.outcome())
            self.assertEqual(done['previousRecordDigest'], start['recordDigest'])
        before = self.files()
        with self.journal(False) as state:
            self.assertEqual(state.summary('task-1')['recordedEvent'], 'TASK_STAGED')
            self.assertTrue(state.summary('task-1')['historicalOnly'])
            self.assertIsNone(state.summary('task-2'))
        self.assertEqual(before, self.files())

    def test_failed_or_started_tasks_cannot_be_restarted(self):
        with self.journal() as state:
            state.start('task-1')
            with self.assertRaises(ValueError): state.start('task-1')
            state.finish('task-1')
            with self.assertRaises(ValueError): state.start('task-1')
            self.assertEqual(state.summary('task-1')['status'], 'OUTCOME_UNKNOWN')
            with self.assertRaises(ValueError): state.finish('task-1')

    def test_only_original_inspection_can_resolve_an_unfinished_start(self):
        with self.journal() as state:
            state.start('task-1'); state.finish('task-1')
            with self.assertRaises(ValueError): state.finish('task-1', self.outcome(), recovered=True)
            result = self.outcome(); result['collectionRequested'] = False
            state.finish('task-1', result, recovered=True)
            with self.assertRaises(ValueError): state.start('task-1')
            with self.assertRaises(ValueError): state.finish('task-2', result, recovered=True)
            self.assertEqual(state.summary('task-1')['recordedEvent'], 'TASK_RECONCILED')

    def test_future_and_expired_windows_cannot_start(self):
        with self.journal() as state:
            self.at += timedelta(seconds=61)
            with self.assertRaises(ValueError): state.start('task-1')
            state.expire('task-1')
            with self.assertRaises(ValueError): state.start('task-1')
            self.assertEqual(state.summary('task-1')['recordedEvent'], 'TASK_EXPIRED')
        self.at -= timedelta(seconds=120)
        with self.assertRaises(ValueError):
            with self.journal(): pass

    def test_manifest_drift_on_open_or_during_work_holds_without_relabeling(self):
        with self.journal() as state:
            runtime.write_json(self.path, {**self.doc, 'maxDurationSeconds': 4})
            with self.assertRaises(ValueError): state.start('task-1')
        self.spec = DiscoveryBatch.from_file(self.path)
        with self.assertRaises(ValueError):
            with self.journal(): pass
        self.assertEqual(len(self.files()), 2)

    def test_clock_regression_behind_retained_event_is_refused(self):
        with self.journal() as state:
            state.start('task-1')
            self.at -= timedelta(microseconds=1)
            with self.assertRaises(ValueError): state.now()
        with self.assertRaises(ValueError):
            with self.journal(False): pass

    def test_inspect_missing_state_never_enrolls_or_creates_files(self):
        with self.assertRaises(FileNotFoundError):
            inspect_batch(self.path, self.directory, clock=lambda: self.at)
        self.assertEqual(self.files(), {})

    def test_unexpected_partial_or_missing_internal_records_hold(self):
        with self.journal() as state: state.start('task-1')
        record = self.directory / '000001.json'; original = record.read_bytes()
        record.unlink()
        with self.assertRaises(ValueError):
            with self.journal(False): pass
        record.write_bytes(original); record.chmod(0o600)
        extra = self.directory / '.review-partial'; extra.write_bytes(b'partial')
        with self.assertRaises(ValueError):
            with self.journal(False): pass
        extra.unlink()
        record.write_bytes(b'{"format":1,"format":2}')
        with self.assertRaises(ValueError):
            with self.journal(False): pass

    def test_valid_json_with_changed_content_fails_its_record_digest(self):
        with self.journal() as state: state.start('task-1')
        p = self.directory/'000002.json'; doc=json.loads(p.read_bytes()); doc['taskId']='task-2'
        p.write_bytes(_json(doc).encode('ascii'))
        with self.assertRaises(ValueError):
            with self.journal(False): pass

    def test_valid_digest_cannot_authorize_invalid_event_transition(self):
        with self.journal(): pass
        p = self.directory/'000001.json'; doc=json.loads(p.read_bytes())
        doc.update(sequence=2, previousRecordDigest=doc['recordDigest'], event='TASK_STAGED',
                   taskId='task-1', outcome=self.outcome())
        doc['recordDigest']=batch_journal._digest({k:v for k,v in doc.items() if k!='recordDigest'})
        runtime.write_json(self.directory/'000002.json',doc)
        with self.assertRaises(ValueError):
            with self.journal(False): pass

    def test_bad_staged_result_never_commits_a_completion(self):
        with self.journal() as state:
            state.start('task-1'); before=self.files()
            changes = [{'environmentId':'other'}, {'publicationAttempted':True}, {'executionAuthorized':True},
                       {'objectCount':True}, {'requestDigest':'not-a-digest'}, {'status':'PUBLISHED'}, {'unexpected':1}]
            for change in changes:
                with self.subTest(change=change), self.assertRaises(ValueError):
                    state.finish('task-1', {**self.outcome(), **change})
            self.assertEqual(before,self.files())

    def test_state_paths_links_permissions_and_hardlinks_are_refused(self):
        with self.journal(): pass
        lock=self.directory/'batch.lock'; actual=self.root/'actual-lock'
        lock.rename(actual); lock.symlink_to(actual)
        with self.assertRaises(OSError):
            with self.journal(False): pass
        lock.unlink(); actual.rename(lock)
        os.link(lock,actual)
        with self.assertRaises(ValueError):
            with self.journal(False): pass
        actual.unlink(); self.directory.chmod(0o755)
        with self.assertRaises(ValueError):
            with self.journal(False): pass
        self.directory.chmod(0o700)

    def test_state_directory_replacement_during_work_is_refused(self):
        with self.journal() as state:
            moved=self.root/'old'; self.directory.rename(moved); self.directory.mkdir(mode=0o700)
            (self.directory/'batch.lock').touch(mode=0o600)
            with self.assertRaises(ValueError): state.start('task-1')
            self.assertEqual(sorted(self.files()),['batch.lock'])

    def test_lock_is_shared_between_real_processes_and_is_never_unlinked(self):
        program = '''
import sys
from provisioner.controlplane.discovery.batch_runtime import DiscoveryBatch
from provisioner.controlplane.discovery.batch_journal import BatchJournal
from datetime import datetime,timezone
fixture_ready()
try:
    with BatchJournal(sys.argv[2],DiscoveryBatch.from_file(sys.argv[1]),manifest_path=sys.argv[1],
                      clock=lambda:datetime.now(timezone.utc),enroll=True):
        sys.exit(9)
except BlockingIOError:
    sys.exit(0)
'''
        with self.journal():
            child=start_prepared(program,[str(self.path),str(self.directory)])
            try:
                activate(child)
                output,errors=child.communicate(timeout=10)
                self.assertEqual(child.returncode,0,output+errors)
            finally:
                if child.poll() is None:child.kill()
                child.communicate(timeout=5)
        self.assertTrue((self.directory/'batch.lock').is_file())
        with self.journal(False): pass

    def test_process_exit_after_start_leaves_unknown_and_no_automatic_retry(self):
        program='''
import os,sys
from datetime import datetime,timezone
from provisioner.controlplane.discovery.batch_runtime import DiscoveryBatch
from provisioner.controlplane.discovery.batch_journal import BatchJournal
fixture_ready()
with BatchJournal(sys.argv[2],DiscoveryBatch.from_file(sys.argv[1]),manifest_path=sys.argv[1],
                  clock=lambda:datetime.now(timezone.utc),enroll=True) as state:
    state.start('task-1')
    os._exit(7)
'''
        child=start_prepared(program,[str(self.path),str(self.directory)])
        try:
            activate(child)
            child.communicate(timeout=10)
            self.assertEqual(child.returncode,7)
        finally:
            if child.poll() is None:child.kill()
            child.communicate(timeout=5)
        self.at=datetime.now(timezone.utc)
        with self.journal(False) as state:
            self.assertEqual(state.summary('task-1')['status'],'OUTCOME_UNKNOWN')
            with self.assertRaises(ValueError):state.start('task-1')

    def test_postpublication_error_keeps_final_record_and_poisoned_instance(self):
        original=batch_journal.publish_once
        def failed(*args,**kwargs):
            original(*args,**kwargs)
            raise OSError('post-link uncertainty')
        with self.journal() as state:
            with patch.object(batch_journal,'publish_once',failed):
                with self.assertRaises(OSError):state.start('task-1')
            with self.assertRaises(ValueError):state.start('task-2')
        with self.journal(False) as state:
            self.assertEqual(state.summary('task-1')['status'],'OUTCOME_UNKNOWN')
            self.assertIsNone(state.summary('task-2'))

    def test_repeated_due_tick_runs_each_preselected_task_at_most_once(self):
        calls=[]
        def execute(path,action,**kwargs):
            self.assertEqual(action,'stage'); calls.append(path)
            return self.outcome()
        with patch.object(batch_runtime,'execute',execute):
            first=run_batch(self.path,state_directory=self.directory,clock=lambda:self.at)
            second=run_batch(self.path,state_directory=self.directory,clock=lambda:self.at)
        self.assertEqual(first['stagedCount'],2)
        self.assertEqual(second['stagedCount'],0)
        self.assertEqual(len(calls),2)
        self.assertTrue(second['durableSchedule'])
        self.assertTrue(all(item['historicalOnly'] for item in second['items']))
        self.assertEqual(second['journalSequence'],5)
        self.assertEqual(second['limitScope'],'THIS_PROCESS_ONLY')

    def test_later_tick_runs_future_work_without_replaying_earlier_work(self):
        self.doc['tasks'][1]['notBefore']=(self.at+timedelta(seconds=20)).isoformat()
        runtime.write_json(self.path,self.doc)
        with patch.object(batch_runtime,'execute',return_value=self.outcome()) as execute:
            first=run_batch(self.path,state_directory=self.directory,clock=lambda:self.at)
            self.assertEqual([i['status'] for i in first['items']],['STAGED','NOT_DUE'])
            self.at+=timedelta(seconds=21)
            second=run_batch(self.path,state_directory=self.directory,clock=lambda:self.at)
            self.assertEqual([i['status'] for i in second['items']],['ALREADY_RECORDED','STAGED'])
            self.assertEqual(execute.call_count,2)

    def test_failed_execution_is_held_across_ticks_and_inspect_never_executes(self):
        with patch.object(batch_runtime,'execute',side_effect=RuntimeError('secret:private-token')) as execute:
            first=run_batch(self.path,state_directory=self.directory,clock=lambda:self.at)
            self.assertEqual(execute.call_count,2)
            again=run_batch(self.path,state_directory=self.directory,clock=lambda:self.at)
            inspected=inspect_batch(self.path,self.directory,clock=lambda:self.at)
            self.assertEqual(execute.call_count,2)
        self.assertEqual(first['status'],'BATCH_HELD')
        self.assertEqual(again['unresolvedTaskCount'],2)
        self.assertEqual(inspected['unresolvedTaskCount'],2)
        self.assertNotIn('secret',json.dumps([first,again,inspected]))

    def test_no_expired_unstarted_work_is_replayed(self):
        with self.journal():pass
        self.at+=timedelta(seconds=61)
        with patch.object(batch_runtime,'execute',side_effect=AssertionError('must not execute')):
            first=run_batch(self.path,state_directory=self.directory,clock=lambda:self.at)
            second=run_batch(self.path,state_directory=self.directory,clock=lambda:self.at)
        self.assertEqual(first['status'],'BATCH_HELD')
        self.assertEqual(second['status'],'BATCH_HELD')
        self.assertTrue(all(i['recordedEvent']=='TASK_EXPIRED' for i in second['items']))


    def test_refused_start_publication_never_invokes_a_collector(self):
        original=batch_journal.publish_once
        def refuse_start(path, raw, check):
            if json.loads(raw)['event']=='TASK_STARTED':
                raise OSError('private-storage-unavailable')
            return original(path,raw,check)
        with patch.object(batch_journal,'publish_once',refuse_start), \
             patch.object(batch_runtime,'execute',side_effect=AssertionError('effect before durable start')) as execute:
            result=run_batch(self.path,state_directory=self.directory,clock=lambda:self.at)
        self.assertEqual(result['status'],'BATCH_HELD')
        self.assertEqual(execute.call_count,0)
        self.assertNotIn('private-storage',json.dumps(result))
        with self.journal(False) as state:
            self.assertIsNone(state.state('task-1'))
            self.assertIsNone(state.state('task-2'))

    def test_journal_byte_and_record_count_limits_hold_before_replay(self):
        with self.journal():pass
        record=self.directory/'000001.json';saved=record.read_bytes()
        record.write_bytes(b' '*(batch_journal.MAX_RECORD_BYTES+1))
        with self.assertRaises(ValueError):
            with self.journal(False):pass
        record.write_bytes(saved)
        with patch.object(batch_journal,'MAX_RECORDS',0):
            with self.assertRaises(ValueError):
                with self.journal(False):pass

    def test_inspection_requires_literal_boolean_reconciliation_selection(self):
        for value in ('false','true',0,1,[],{},None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                inspect_batch(self.path,self.directory,reconcile=value,clock=lambda:self.at)
        self.assertEqual(self.files(),{})


class CheckpointedBatchNativeTests(runtime.RuntimeFixture, unittest.TestCase):
    def setUp(self):
        self.configure()
        self.batch_path=self.native.root/'batch.json'
        self.batch=batches.specification(self.config_path,self.native.campaign,self.native.environment,now=self.native.now)
        runtime.write_json(self.batch_path,self.batch)
        self.state_path=self.native.root/'schedule-state';self.state_path.mkdir(mode=0o700)

    def run_tick(self):
        return run_batch(self.batch_path,state_directory=self.state_path,clock=lambda:self.native.now)

    def test_actual_signed_collection_is_staged_once_and_history_does_not_claim_fresh_authority(self):
        first=self.run_tick()
        self.assertEqual(first['stagedCount'],1,first)
        self.assertEqual(len(self.native.calls),2)
        self.native.revoke_witness()
        second=self.run_tick()
        self.assertEqual(second['stagedCount'],0)
        self.assertTrue(second['items'][0]['historicalOnly'])
        self.assertEqual(len(self.native.calls),2)
        self.assertNotIn(self.native.token,json.dumps(first))

    def test_lost_completion_is_reconciled_only_from_verified_original(self):
        original=BatchJournal.finish
        failed=False
        def fail_first(state,task_id,outcome=None,**kwargs):
            nonlocal failed
            if not failed and outcome is not None:
                failed=True
                raise OSError('interrupted completion')
            return original(state,task_id,outcome,**kwargs)
        with patch.object(BatchJournal,'finish',fail_first):
            self.assertEqual(self.run_tick()['status'],'BATCH_HELD')
        self.assertEqual(len(self.native.calls),2)
        self.assertEqual(self.run_tick()['items'][0]['status'],'OUTCOME_UNKNOWN')
        self.native.credential_path.unlink();self.signer_path.unlink()
        with patch.object(collector_runtime,'create_native_collector',side_effect=AssertionError('must not recollect')):
            result=inspect_batch(self.batch_path,self.state_path,reconcile=True,clock=lambda:self.native.now)
        self.assertEqual(result['status'],'JOURNAL_INSPECTED',result)
        self.assertEqual(result['items'][0]['recordedEvent'],'TASK_RECONCILED')
        self.assertFalse(result['collectionRequested'])
        self.assertEqual(len(self.native.calls),2)
        self.assertEqual(self.run_tick()['stagedCount'],0)

    def test_unknown_start_without_original_is_not_reset_or_recollected(self):
        spec=DiscoveryBatch.from_file(self.batch_path)
        with BatchJournal(self.state_path,spec,manifest_path=self.batch_path,clock=lambda:self.native.now,enroll=True) as state:
            state.start('task-1')
        before={p.name:p.read_bytes() for p in self.state_path.iterdir()}
        result=inspect_batch(self.batch_path,self.state_path,reconcile=True,clock=lambda:self.native.now)
        self.assertEqual(result['status'],'JOURNAL_HELD')
        self.assertFalse(self.native.calls)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.state_path.iterdir()})
        self.assertEqual(self.run_tick()['status'],'BATCH_HELD')

    def test_revoked_original_cannot_close_unknown_task(self):
        with patch.object(BatchJournal,'finish',side_effect=OSError('lost journal')):
            self.run_tick()
        self.native.revoke_witness()
        result=inspect_batch(self.batch_path,self.state_path,reconcile=True,clock=lambda:self.native.now)
        self.assertEqual(result['status'],'JOURNAL_HELD')
        self.assertEqual(len(self.native.calls),2)

    def test_fresh_process_cli_stages_then_inspects_without_duplicate_contact(self):
        command=[sys.executable,'-m','provisioner.controlplane.discovery.collector_runtime',
            'batch-stage','--config',str(self.batch_path),'--state-directory',str(self.state_path)]
        first=subprocess.run(command,capture_output=True,text=True,timeout=20)
        self.assertEqual(first.returncode,0,first.stdout+first.stderr)
        self.assertEqual(json.loads(first.stdout)['stagedCount'],1)
        command[3]='batch-inspect'
        viewed=subprocess.run(command,capture_output=True,text=True,timeout=20)
        self.assertEqual(viewed.returncode,0,viewed.stdout+viewed.stderr)
        self.assertEqual(json.loads(viewed.stdout)['items'][0]['recordedEvent'],'TASK_STAGED')
        self.assertEqual(len(self.native.calls),2)

    def test_state_argument_never_adds_journaling_to_publish_or_single_stage(self):
        for action in ('stage','publish','inspect'):
            stream=io.StringIO()
            with redirect_stdout(stream):
                code=collector_runtime.main([action,'--config',str(self.config_path),'--state-directory',str(self.state_path)])
            self.assertEqual(code,2)
            self.assertEqual(json.loads(stream.getvalue())['status'],'HELD')
        self.assertFalse(self.native.calls)
        self.assertFalse(list(self.state_path.iterdir()))




class CheckpointedOtherPlatformsTests(runtime.RuntimeFixture, unittest.TestCase):
    def stage(self):
        path=self.native.root/'batch.json'
        runtime.write_json(path,batches.specification(self.config_path,self.native.campaign,
                                                     self.native.environment,now=self.native.now))
        state=self.native.root/'state';state.mkdir(mode=0o700)
        first=run_batch(path,state_directory=state,clock=lambda:self.native.now)
        second=run_batch(path,state_directory=state,clock=lambda:self.native.now)
        self.assertEqual(first['stagedCount'],1,first)
        self.assertEqual(second['stagedCount'],0,second)
        self.assertEqual(second['items'][0]['recordedEvent'],'TASK_STAGED')

    def test_vmware_checkpoint_uses_existing_signed_folder_reader(self):
        fixture=runtime.vmware_fixture
        selection=fixture.SELECTION
        self.configure(fixture.VmwareHttpsTests(),selection={
            'folderIds':list(selection.folder_ids),'coverageDigest':selection.coverage_digest})
        self.stage()
        self.assertEqual(len(self.native.calls),2)

    def test_openstack_checkpoint_uses_three_existing_service_routes(self):
        from tests.provisioning.discovery import test_openstack_https as fixture
        self.configure(fixture.OpenStackHttpsTests())
        self.config['native']['selection']={s:self.native.endpoints.for_service(s) for s in fixture.API_VERSIONS}
        self.config['native']['caBundles']={s:str(self.native.root/'ca.pem') for s in fixture.API_VERSIONS}
        self.save();self.stage()
        self.assertEqual([c[0] for c in self.native.calls],['compute','volume','network']*2)




class WaitingBatchTests(unittest.TestCase):
    setUp=BatchJournalTests.setUp
    outcome=staticmethod(BatchJournalTests.outcome)

    def test_waiting_run_starts_future_tasks_with_one_continuing_read_gate(self):
        import time
        origin=time.monotonic();base=self.at
        self.doc['endpoints'][0]['minReadIntervalMilliseconds']=200
        for n,task in enumerate(self.doc['tasks']):
            task['notBefore']=(base+timedelta(seconds=.05+n*.03)).isoformat()
        runtime.write_json(self.path,self.doc)
        gates=[];starts=[]
        def execute(path, action, *, read_gate, clock, **kwargs):
            gates.append(read_gate)
            with read_gate.permit(time.monotonic()+2,clock):
                starts.append(time.monotonic())
            return self.outcome()
        with patch.object(batch_runtime,'execute',execute):
            result=run_batch(self.path,state_directory=self.directory,wait_for_due=True,
                             clock=lambda:base+timedelta(seconds=time.monotonic()-origin))
        self.assertEqual(result['stagedCount'],2,result)
        self.assertEqual(result['pendingTaskCount'],0)
        self.assertTrue(result['waitedForDue'])
        self.assertIs(gates[0],gates[1])
        self.assertGreaterEqual(starts[1]-starts[0],.19)

    def test_wait_limit_leaves_future_tasks_unstarted_without_credential_reads(self):
        import time
        self.doc['maxDurationSeconds']=1
        for task in self.doc['tasks']:
            task['notBefore']=(self.at+timedelta(minutes=1)).isoformat()
            task['notAfter']=(self.at+timedelta(minutes=2)).isoformat()
        runtime.write_json(self.path,self.doc)
        begin=time.monotonic()
        with patch.object(batch_runtime,'execute',side_effect=AssertionError('not due')):
            result=run_batch(self.path,state_directory=self.directory,wait_for_due=True,clock=lambda:self.at)
        self.assertLess(time.monotonic()-begin,3)
        self.assertEqual(result['stagedCount'],0)
        self.assertEqual(result['pendingTaskCount'],2)
        self.assertTrue(all(i['status']=='NOT_DUE' for i in result['items']))
        self.assertEqual(result['journalSequence'],1)

    def test_wait_mode_cannot_be_selected_without_a_durable_journal(self):
        with self.assertRaises(ValueError):run_batch(self.path,wait_for_due=True)
        output=io.StringIO()
        with redirect_stdout(output):
            code=collector_runtime.main(['batch-run','--config',str(self.path)])
        self.assertEqual(code,2)
        self.assertNotIn(str(self.path),output.getvalue())

    def test_clock_regression_between_nonmutating_wait_checks_is_rejected(self):
        state=BatchJournal(self.directory,self.spec,manifest_path=self.path,clock=lambda:self.at,enroll=True)
        with state:
            self.at+=timedelta(seconds=10);state.now()
            self.at-=timedelta(seconds=1)
            with self.assertRaises(ValueError):state.now()


    def test_manifest_change_while_waiting_cannot_admit_future_collection(self):
        import threading
        for task in self.doc['tasks']:
            task['notBefore']=(self.at+timedelta(seconds=30)).isoformat()
        runtime.write_json(self.path,self.doc)
        def replace_manifest():
            runtime.write_json(self.path,{**self.doc,'maxDurationSeconds':4})
        timer=threading.Timer(.1,replace_manifest)
        timer.start()
        try:
            with patch.object(batch_runtime,'execute',side_effect=AssertionError('changed schedule')) as execute:
                with self.assertRaises(ValueError):
                    run_batch(self.path,state_directory=self.directory,wait_for_due=True,clock=lambda:self.at)
            self.assertEqual(execute.call_count,0)
        finally:
            timer.join()


if __name__=='__main__':unittest.main()
