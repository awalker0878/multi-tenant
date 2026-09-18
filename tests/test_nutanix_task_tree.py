"""Known-tree readback over real loopback TLS, not native vendor qualification."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from lab.native_readback_fixture import Fixture, TASK, VPC, TENANT
from lab.nutanix_task_tree_fixture import reset, manifest, responses, CHILD_A, CHILD_B, GRANDCHILD, SUBNET
from lab.run_readback_lab import operator_context
from tools import nutanix_observe as native, nutanix_task_tree as tree, readback_core as c, recovery_review as rr
ROOT=Path(__file__).resolve().parents[1]


def reseal(report):
    previous=None;stable=0
    for row in report['history']:
        value=c.digest(row['states']);stable=stable+1 if value==previous else 1;previous=value
        row['snapshot_sha256']=value;row['outcome']=c.outcome(row['states'],stable)
    report['outcome']=row['outcome'];report['stable_rounds']=stable
    report['content_sha256']=c.digest({k:v for k,v in report.items() if k!='content_sha256'})


class ScopeTests(unittest.TestCase):
    def setUp(self):self.m=manifest('https://pc.fixture.invalid')
    def test_explicit_profile(self):native.validate(self.m);self.assertEqual(len(native.targets(self.m)),6)
    def test_single_task_profile_not_silently_extended(self):
        self.m['profile']=native.PROFILE
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_empty_tree_rejected(self):
        self.m['task']['descendants']=[]
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_unknown_manifest_field_rejected(self):
        self.m['discover_children']=True
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_unknown_child_field_rejected(self):
        self.m['task']['descendants'][0]['href']='https://other.invalid'
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_missing_creation_window_rejected(self):
        del self.m['task']['created_before']
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_reversed_window_rejected(self):
        self.m['task']['created_before']='2000-01-01T00:00:00Z'
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_duplicate_task_rejected(self):
        self.m['task']['descendants'][1]['ext_id']=CHILD_A
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_root_repeated_as_child_rejected(self):
        self.m['task']['descendants'][0]['ext_id']=TASK
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_self_parent_rejected(self):
        self.m['task']['descendants'][0]['parent_ext_id']=CHILD_A
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_cycle_rejected(self):
        self.m['task']['descendants'][0]['parent_ext_id']=GRANDCHILD
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_unknown_parent_rejected(self):
        self.m['task']['descendants'][0]['parent_ext_id']='recorded-but-not-in-tree'
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_child_entities_cannot_expand_scope(self):
        self.m['task']['descendants'][0]['entity_ids']=[TENANT]
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_duplicate_child_entities_rejected(self):
        self.m['task']['descendants'][0]['entity_ids']=[VPC,VPC]
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_empty_child_entity_scope_is_explicit(self):
        self.m['task']['descendants'][0]['entity_ids']=[];native.validate(self.m)
    def test_missing_child_entities_rejected(self):
        del self.m['task']['descendants'][0]['entity_ids']
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_cross_native_tenant_manifest_rejected(self):
        self.m['resources'][1]['expected']['tenantId']=VPC
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_17_tasks_rejected(self):
        self.m['task']['descendants']=[{'ext_id':f'fixture-{i}','parent_ext_id':TASK,'operation':'Fixture step','entity_ids':[]} for i in range(16)]
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_16_task_limit_accepted(self):
        self.m['task']['descendants']=[{'ext_id':f'fixture-{i}','parent_ext_id':TASK,'operation':'Fixture step','entity_ids':[]} for i in range(15)]
        native.validate(self.m);self.assertEqual(len(tree.specs(self.m)),16)
    def test_five_levels_rejected(self):
        self.m['task']['descendants']=[{'ext_id':f'fixture-{i}','parent_ext_id':TASK if not i else f'fixture-{i-1}','operation':'Fixture step','entity_ids':[]} for i in range(5)]
        with self.assertRaises(ValueError):native.validate(self.m)
    def test_out_of_order_manifest_normalized(self):
        self.m['task']['descendants'].reverse();native.validate(self.m)
        self.assertEqual([x['ext_id'] for x in tree.specs(self.m)],[TASK,CHILD_A,CHILD_B,GRANDCHILD])
    def test_injected_task_path_rejected(self):
        for ident in ('../other','https://other.invalid/x','id?cancel=true','id%2fpath','path/id'):
            with self.subTest(ident=ident),self.assertRaises(ValueError):tree.target(ident)
    def test_recorded_task_encoded(self):self.assertIn('ZXJnb24%3D%3A',tree.target(TASK))


class TLSTreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.f=Fixture()
    @classmethod
    def tearDownClass(cls):cls.f.close()
    def setUp(self):self.m=reset(self.f)
    def data(self,ident=GRANDCHILD):return self.f.routes[tree.target(ident)]['body']['data']
    def observe(self,rounds=3):
        r=c.observe(self.m,self.f.client(self.m),native,rounds=rounds,interval=0)
        self.assertTrue(all(x['method']=='GET' and x['path'] in native.targets(self.m) for x in self.f.requests))
        self.assertTrue(all(r[k] is False for k in ('may_apply','may_delete','may_activate')))
        return r
    def outcome(self,value):r=self.observe();self.assertEqual(r['outcome'],value);return r
    def test_complete_nested_tree_and_resources(self):
        r=self.outcome('READBACK_MATCH_NOT_QUALIFIED');self.assertEqual(r['request_count'],20)
        self.assertEqual(rr.review(self.m,r,operator_context(self.m,r))['result'],'READY_FOR_OPERATOR_RECOVERY_REVIEW')
    def test_exact_before_resources_reverse_after_sequence(self):
        self.observe();tasks=[tree.target(n['ext_id']) for n in tree.specs(self.m)]
        expected=tasks+[native.resource_target(r) for r in self.m['resources']]+tasks[::-1]
        self.assertEqual([x['path'] for x in self.f.requests],expected*2)
    def test_tree_witness_stored_once_per_round(self):
        r=self.observe()
        for row in r['history']:
            self.assertIn('task_tree',row['states'][0]);self.assertNotIn('task_tree',row['states'][1])
            self.assertEqual(row['states'][0]['task_sha256'],row['states'][1]['task_sha256'])
    def test_parent_success_cannot_hide_running_child(self):
        self.data().update(status='RUNNING',completedTime=None,progressPercentage=100)
        r=self.outcome('HOLD_NATIVE_PENDING');self.assertEqual(r['request_count'],30)
        self.assertEqual(rr.review(self.m,r,operator_context(self.m,r))['result'],'WAIT_FOR_NATIVE_TASK')
    def test_delayed_child_needs_two_complete_rounds(self):
        def hook(path,n,spec):
            if path==tree.target(GRANDCHILD) and n<=2:spec['body']['data'].update(status='RUNNING',completedTime=None)
            return spec
        self.f.hook=hook;r=self.outcome('READBACK_MATCH_NOT_QUALIFIED')
        self.assertEqual([x['outcome'] for x in r['history']],['HOLD_NATIVE_PENDING','HOLD_UNSTABLE','READBACK_MATCH_NOT_QUALIFIED'])
    def test_suspended_is_pending(self):self.data().update(status='SUSPENDED',completedTime=None);self.outcome('HOLD_NATIVE_PENDING')
    def test_failed_grandchild_retains_partial_resources(self):
        self.data().update(status='FAILED',legacyErrorMessage='private error detail')
        r=self.outcome('HOLD_NATIVE_FAILURE');self.assertEqual(len(r['history'][0]['states']),2)
        self.assertEqual(rr.review(self.m,r,operator_context(self.m,r))['result'],'INSPECT_PARTIAL_FAILURE')
        self.assertNotIn('private error detail',json.dumps(r))
    def test_canceled_child_is_failure(self):self.data(CHILD_B)['status']='CANCELED';self.outcome('HOLD_NATIVE_FAILURE')
    def test_failure_cannot_be_erased_by_later_success(self):
        def hook(path,n,spec):
            if path==tree.target(GRANDCHILD) and n==1:spec['body']['data']['status']='FAILED'
            return spec
        self.f.hook=hook;self.outcome('HOLD_NATIVE_FAILURE');self.assertEqual(len(self.f.requests),10)
    def test_unknown_status_holds(self):self.data()['status']='NEW_FUTURE_STATUS';self.outcome('HOLD_UNCERTAIN')
    def test_missing_child_no_retry(self):
        self.f.routes[tree.target(GRANDCHILD)]['status']=404;r=self.outcome('HOLD_UNCERTAIN')
        self.assertEqual(self.f.counts[tree.target(GRANDCHILD)],1);self.assertEqual(r['request_count'],4)
    def test_redirect_never_followed(self):
        self.f.routes[tree.target(CHILD_A)].update(status=302,headers=[('Location','https://foreign.invalid/secret')])
        self.outcome('HOLD_UNCERTAIN');self.assertEqual(len(self.f.requests),2)
    def test_reply_links_not_followed_or_exported(self):
        self.data(CHILD_A)['parentTask']['href']='https://foreign.invalid/secret'
        self.data()['links']=[{'href':'https://other.invalid/private'}]
        r=self.outcome('READBACK_MATCH_NOT_QUALIFIED');self.assertNotIn('foreign.invalid',json.dumps(r));self.assertNotIn('other.invalid',json.dumps(r))
    def test_wrong_parent(self):self.data()['parentTask']['extId']=CHILD_B;self.outcome('HOLD_UNCERTAIN')
    def test_wrong_root(self):self.data()['rootTask']['extId']=CHILD_A;self.outcome('HOLD_UNCERTAIN')
    def test_child_root_required(self):del self.data()['rootTask'];self.outcome('HOLD_UNCERTAIN')
    def test_href_not_identity(self):self.data()['parentTask']={'href':'/api/prism/v4.3/config/tasks/'+CHILD_A};self.outcome('HOLD_UNCERTAIN')
    def test_root_may_not_be_child(self):self.data(TASK)['parentTask']={'extId':CHILD_A};self.outcome('HOLD_UNCERTAIN')
    def test_wrong_task_id(self):self.data()['extId']=CHILD_B;self.outcome('HOLD_UNCERTAIN')
    def test_wrong_operation(self):self.data()['operation']='another operation';self.outcome('HOLD_UNCERTAIN')
    def test_wrong_object_type(self):self.data()['$objectType']='prism.v5.Task';self.outcome('HOLD_UNCERTAIN')
    def test_missing_subtask_list_not_complete(self):self.data(TASK)['subTasks']=[];self.outcome('HOLD_UNCERTAIN')
    def test_large_native_count_truncated(self):self.data(TASK)['numberOfSubtasks']=12;self.outcome('HOLD_UNCERTAIN')
    def test_duplicate_child_reference(self):self.data(TASK)['subTasks'][1]=deepcopy(self.data(TASK)['subTasks'][0]);self.outcome('HOLD_UNCERTAIN')
    def test_unlisted_child_not_fetched(self):
        self.data(TASK)['subTasks'][0]['extId']='unexpected-task';self.outcome('HOLD_UNCERTAIN')
        self.assertFalse(any('unexpected-task' in x['path'] for x in self.f.requests))
    def test_boolean_child_count(self):self.data()['numberOfSubtasks']=False;self.outcome('HOLD_UNCERTAIN')
    def test_wrong_entity(self):self.data()['entitiesAffected'][0]['extId']=SUBNET;self.outcome('HOLD_UNCERTAIN')
    def test_incomplete_entity_count(self):self.data()['numberOfEntitiesAffected']=2;self.outcome('HOLD_UNCERTAIN')
    def test_duplicate_entity(self):
        self.data(TASK)['entitiesAffected'][1]=deepcopy(self.data(TASK)['entitiesAffected'][0]);self.outcome('HOLD_UNCERTAIN')
    def test_empty_entity_list_must_be_accepted_explicitly(self):
        self.m['task']['descendants'][2]['entity_ids']=[];self.data().update(numberOfEntitiesAffected=0,entitiesAffected=[])
        self.outcome('READBACK_MATCH_NOT_QUALIFIED')
    def test_batch_task_not_expanded(self):self.data()['batchSummary']={'numberOfJobs':1};self.outcome('HOLD_UNCERTAIN')
    def test_empty_batch_summary_not_silently_accepted(self):self.data()['batchSummary']={};self.outcome('HOLD_UNCERTAIN')
    def test_success_with_warning_holds_and_redacts(self):
        self.data()['warnings']=[{'message':'private-warning'}];r=self.outcome('HOLD_UNCERTAIN');self.assertNotIn('private-warning',json.dumps(r))
    def test_success_with_legacy_error_holds(self):self.data()['legacyErrorMessage']='error';self.outcome('HOLD_UNCERTAIN')
    def test_invalid_diagnostic_type(self):self.data()['errorMessages']='not a collection';self.outcome('HOLD_UNCERTAIN')
    def test_missing_completion(self):del self.data()['completedTime'];self.outcome('HOLD_UNCERTAIN')
    def test_future_completion(self):self.data()['completedTime']='2099-01-01T00:00:00Z';self.outcome('HOLD_UNCERTAIN')
    def test_child_completed_after_parent(self):self.data()['completedTime']=(datetime.now(timezone.utc)-timedelta(seconds=8)).isoformat();self.outcome('HOLD_UNCERTAIN')
    def test_child_created_before_parent(self):self.data()['createdTime']=(datetime.now(timezone.utc)-timedelta(seconds=110)).isoformat();self.outcome('HOLD_UNCERTAIN')
    def test_task_outside_accepted_window(self):self.data()['createdTime']='2020-01-01T00:00:00Z';self.outcome('HOLD_UNCERTAIN')
    def test_terminal_status_regression(self):
        def hook(path,n,spec):
            if path==tree.target(GRANDCHILD) and n>=2:spec['body']['data'].update(status='RUNNING',completedTime=None)
            return spec
        self.f.hook=hook;self.outcome('HOLD_UNCERTAIN')
    def test_identity_changed_between_rounds(self):
        earlier=self.data()['createdTime']
        def hook(path,n,spec):
            if path==tree.target(GRANDCHILD):
                if n<=2:spec['body']['data'].update(status='RUNNING',completedTime=None)
                else:spec['body']['data']['createdTime']=(c.timestamp(earlier)+timedelta(seconds=1)).isoformat()
            return spec
        self.f.hook=hook;self.outcome('HOLD_UNCERTAIN')
    def test_completed_tree_wrong_subnet_reference(self):
        self.f.routes[native.resource_target(self.m['resources'][1])]['body']['data']['vpcReference']=TENANT
        r=self.outcome('HOLD_DIFFERENCE');self.assertEqual(rr.review(self.m,r,operator_context(self.m,r))['result'],'RECONCILE_DIVERGENCE')
    def test_foreign_native_tenant_resource(self):
        self.f.routes[native.resource_target(self.m['resources'][0])]['body']['data']['tenantId']=SUBNET;self.outcome('HOLD_UNCERTAIN')
    def test_missing_resource_etag(self):del self.f.routes[native.resource_target(self.m['resources'][1])]['etag'];self.outcome('HOLD_UNCERTAIN')
    def test_read_failure_after_before_phase(self):
        self.f.routes[native.resource_target(self.m['resources'][0])]['status']=403;r=self.outcome('HOLD_UNCERTAIN');self.assertEqual(r['request_count'],5)
    def test_existing_containment_remains(self):
        r=self.observe();ctx=operator_context(self.m,r);ctx['containment']='ACTIVE'
        self.assertEqual(rr.review(self.m,r,ctx)['result'],'KEEP_INCIDENT_CONTAINMENT')
    def test_readback_does_not_prove_fencing(self):
        r=self.observe();ctx=operator_context(self.m,r);ctx['writer_fence']['state']='UNVERIFIED'
        self.assertEqual(rr.review(self.m,r,ctx)['result'],'HOLD_WRITER_NOT_FENCED')
    def invalid_report(self,modify):
        r=self.observe();modify(r)
        for row in r['history']:
            witness=row['states'][0].get('task_tree')
            for state in row['states']:state['task_sha256']=c.digest(witness)
        reseal(r);self.assertEqual(rr.review(self.m,r,operator_context(self.m,r))['result'],'HOLD_INVALID_EVIDENCE')
    def test_missing_child_witness_refused_after_rehash(self):
        self.invalid_report(lambda r:r['history'][0]['states'][0]['task_tree']['before'].pop())
    def test_wrong_parent_witness_refused_after_rehash(self):
        self.invalid_report(lambda r:r['history'][0]['states'][0]['task_tree']['before'][-1]['snapshot'].update(parent_id=CHILD_B))
    def test_forged_completion_reason_refused_after_rehash(self):
        self.invalid_report(lambda r:r['history'][0]['states'][0]['task_tree']['before'][-1].update(progress='COMPLETE',reason='TASK_PENDING'))
    def test_null_success_witness_refused_after_rehash(self):
        self.invalid_report(lambda r:r['history'][0]['states'][0]['task_tree']['before'][-1].update(snapshot=None))
    def test_witness_in_every_resource_refused(self):
        self.invalid_report(lambda r:r['history'][0]['states'][1].update(task_tree=deepcopy(r['history'][0]['states'][0]['task_tree'])))
    def test_malformed_witness_lists_fail_closed(self):
        self.invalid_report(lambda r:r['history'][0]['states'][0]['task_tree']['before'][-1]['snapshot'].update(children=None))
    def test_resource_summary_cannot_overrule_tree(self):
        self.invalid_report(lambda r:r['history'][0]['states'][1].update(reason='TASK_TREE_FAILURE_REPORTED'))
    def test_only_root_report_not_complete(self):
        self.invalid_report(lambda r:r['history'][0]['states'][0]['task_tree'].update(before=r['history'][0]['states'][0]['task_tree']['before'][:1]))


class CLITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.f=Fixture()
    @classmethod
    def tearDownClass(cls):cls.f.close()
    def setUp(self):self.m=reset(self.f);self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)
    def invoke(self,args):
        (self.path/'manifest.json').write_text(json.dumps(self.m))
        env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','LD_LIBRARY_PATH')}
        env.update(NUTANIX_USERNAME='fixture-reader',NUTANIX_PASSWORD='temporary-fixture-secret')
        return subprocess.run([sys.executable,str(ROOT/'tools/nutanix_observe.py'),str(self.path/'manifest.json'),*args],env=env,capture_output=True,text=True,timeout=20)
    def args(self):return ['--read-authorized-target','--expected-origin',self.f.origin,'--ca-file',str(self.f.directory/'ca.pem'),'--output',str(self.path/'report.json'),'--interval','0']
    def test_default_validation_no_contact(self):
        self.m['contact_enabled']=False;r=self.invoke([]);self.assertEqual(r.returncode,0);self.assertEqual(self.f.requests,[])
        self.assertEqual(json.loads(r.stdout)['planned_get_targets'],6)
    def test_complete_native_reader_cli_over_loopback(self):
        r=self.invoke(self.args());self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        report=json.loads((self.path/'report.json').read_text());self.assertEqual(report['request_count'],20)
        self.assertEqual((self.path/'report.json').stat().st_mode & 0o777,0o600)
        self.assertNotIn('temporary-fixture-secret',(self.path/'report.json').read_text())
    def test_disabled_contact_refused(self):
        self.m['contact_enabled']=False;r=self.invoke(self.args());self.assertNotEqual(r.returncode,0);self.assertEqual(self.f.requests,[])
    def test_existing_output_not_clobbered(self):
        (self.path/'report.json').write_text('original');r=self.invoke(self.args())
        self.assertNotEqual(r.returncode,0);self.assertEqual((self.path/'report.json').read_text(),'original');self.assertEqual(self.f.requests,[])
    def test_origin_mismatch_no_contact(self):
        args=self.args();args[2]='https://other.fixture.invalid';r=self.invoke(args)
        self.assertNotEqual(r.returncode,0);self.assertEqual(self.f.requests,[])

if __name__=='__main__':unittest.main()
