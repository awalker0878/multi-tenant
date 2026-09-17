"""Local HTTPS and contract regressions for Increment 04 candidate native readers."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from tools import readback_core as c, nsx_observe as nsx, nutanix_observe as nut, recovery_review as rr
from lab.native_readback_fixture import Fixture, manifest, responses, VPC, EP

ROOT=Path(__file__).resolve().parents[1]


def seal(report):
    report['content_sha256']=c.digest({k:v for k,v in report.items() if k!='content_sha256'})
    return report


def context(m,r):
    when=(datetime.fromisoformat(r['started_at'].replace('Z','+00:00'))-timedelta(seconds=1)).isoformat()
    return {'kind':'INTERRUPTED_CHANGE_CONTEXT_V1','operation_id':m['operation_id'],'tenant_id':m['tenant_id'],
      'scope_id':m['scope_id'],'manifest_sha256':c.digest(m),'report_sha256':r['content_sha256'],
      'accepted_plan_sha256':c.digest({'plan':'LOCAL EXAMPLE ONLY'}),'change_record_ref':'LAB-CHANGE',
      'attempted_at':when,'last_security_change_at':when,'attempted_generation':4,'current_generation':4,
      'executor_state':'STOPPED','containment':'NONE','data_disposition':'PRESERVE',
      'writer_fence':{'state':'VERIFIED','scope_id':m['scope_id'],'observed_at':datetime.now(timezone.utc).isoformat(),'evidence_ref':'LAB-FENCE'},
      'quarantine':{'state':'VERIFIED','scope_id':m['scope_id'],'observed_at':datetime.now(timezone.utc).isoformat(),'evidence_ref':'LAB-QUARANTINE'}}


class NativeWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=Fixture()
    @classmethod
    def tearDownClass(cls):cls.fixture.close()
    def setUp(self):
        self.m=self.fixture.reset('nsx')
    def run_observation(self,platform='nsx',rounds=4):
        adapter=nsx if platform=='nsx' else nut
        return c.observe(self.m,self.fixture.client(self.m),adapter,rounds=rounds,interval=0)
    def test_nsx_completed_stable_gets_only(self):
        r=self.run_observation()
        self.assertEqual(r['outcome'],'READBACK_MATCH_NOT_QUALIFIED');self.assertEqual(r['request_count'],6)
        self.assertTrue(all(x['method']=='GET' and x['has_basic_auth'] for x in self.fixture.requests))
        self.assertFalse(r['may_apply']);self.assertFalse(r['may_activate'])
    def test_nutanix_complete_encoded_task(self):
        self.m=self.fixture.reset('nutanix');r=self.run_observation('nutanix')
        self.assertEqual(r['outcome'],'READBACK_MATCH_NOT_QUALIFIED')
        self.assertTrue(any('%3D%3A' in x['path'] for x in self.fixture.requests))
        self.assertTrue(all(x['method']=='GET' for x in self.fixture.requests))
    def test_nsx_realization_lags_then_finishes(self):
        st=nsx.status_target(self.m['resources'][0]['path'])
        def hook(path,n,s):
            if path==st and n==1:s['body']['publish_status']='UNREALIZED'
            return s
        self.fixture.hook=hook;r=self.run_observation()
        self.assertEqual(r['outcome'],'READBACK_MATCH_NOT_QUALIFIED');self.assertEqual(len(r['history']),3)
    def test_nutanix_delayed_task_finishes_no_replay(self):
        self.m=self.fixture.reset('nutanix');t=nut.task_target(self.m)
        def hook(path,n,s):
            if path==t and n<=2:s['body']['data']['status']='RUNNING'
            return s
        self.fixture.hook=hook;r=self.run_observation('nutanix')
        self.assertEqual(r['outcome'],'READBACK_MATCH_NOT_QUALIFIED');self.assertEqual(len(r['history']),3)
        self.assertEqual({x['method'] for x in self.fixture.requests},{'GET'})
    def test_nsx_changed_config_during_realization(self):
        t='/policy/api/v1'+self.m['resources'][0]['path']
        def hook(path,n,s):
            if path==t and n%2==0:s['body']['_revision']=8
            return s
        self.fixture.hook=hook;r=self.run_observation()
        self.assertEqual(r['outcome'],'HOLD_UNCERTAIN')
        self.assertEqual(r['history'][0]['states'][0]['reason'],'CONFIG_CHANGED_DURING_REALIZATION_READ')
    def test_nsx_rule_order_is_not_sorted_away(self):
        e=self.m['resources'][0]['expected'];second=deepcopy(e['rules'][0]);second.update(id='second',sequence_number=20,action='ALLOW')
        e['rules'].append(second);self.fixture.routes=responses(self.m)
        self.fixture.routes['/policy/api/v1'+e['path']]['body']['rules'].reverse()
        self.assertEqual(self.run_observation()['outcome'],'HOLD_DIFFERENCE')
    def test_nsx_same_revision_different_rule_detected(self):
        s=self.fixture.routes['/policy/api/v1'+self.m['resources'][0]['path']]
        s['body']['rules'][0]['action']='ALLOW'
        self.assertEqual(self.run_observation()['outcome'],'HOLD_DIFFERENCE')
    def test_unknown_response_fields_are_not_exposed(self):
        for spec in self.fixture.routes.values():spec['body']['password']='SERVER_SECRET_SENTINEL'
        r=self.run_observation();self.assertEqual(r['outcome'],'READBACK_MATCH_NOT_QUALIFIED')
        self.assertNotIn('SERVER_SECRET_SENTINEL',json.dumps(r));self.assertNotIn('temporary-fixture-secret',json.dumps(r))
    def test_no_ambient_proxy(self):
        with patch.dict(os.environ,{'HTTPS_PROXY':'https://unreachable.invalid','HTTP_PROXY':'https://unreachable.invalid'}):
            self.assertEqual(self.run_observation()['outcome'],'READBACK_MATCH_NOT_QUALIFIED')
    def test_no_ambient_keylog(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'SSLKEYLOGFILE':d+'/leaked.keys'}):
            client=self.fixture.client(self.m);self.assertIsNone(client.context.keylog_filename)
            self.assertEqual(c.observe(self.m,client,nsx,interval=0)['outcome'],'READBACK_MATCH_NOT_QUALIFIED')
            self.assertFalse(Path(d,'leaked.keys').exists())
    def test_untrusted_certificate(self):
        client=c.ReadClient(self.m['origin'],self.m['origin'],'user','secret',nsx.targets(self.m))
        r=c.observe(self.m,client,nsx,interval=0)
        self.assertEqual(r['outcome'],'HOLD_UNCERTAIN');self.assertEqual(r['history'][0]['states'][0]['reason'],'TLS_CERTIFICATE_REJECTED')
    def test_unlisted_request_refused_before_contact(self):
        client=self.fixture.client(self.m)
        with self.assertRaises(c.ObservationError):client.get('/api/v1/trust-management/certificates')
        self.assertEqual(self.fixture.requests,[])
    def test_output_exclusive_before_contact(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d,'report.json');path.write_text('preserve')
            with self.assertRaises(FileExistsError):c.PrivateJournal(path)
            self.assertEqual(path.read_text(),'preserve');self.assertEqual(self.fixture.requests,[])
    def test_forged_expected_boolean_is_distinct(self):
        self.fixture.routes['/policy/api/v1'+self.m['resources'][0]['path']]['body']['stateful']=1
        self.assertEqual(self.run_observation()['outcome'],'HOLD_DIFFERENCE')
    def test_tls_response_newline_secret_never_error_echo(self):
        for x in self.fixture.routes.values():x.update(status=503,body={'error':'SECRET:'+os.environ.get('HOME','')})
        r=self.run_observation();self.assertNotIn('SECRET:',json.dumps(r));self.assertEqual(r['outcome'],'HOLD_UNCERTAIN')


def wire_case(name,platform,mutator,expected):
    def test(self):
        self.m=self.fixture.reset(platform)
        mutator(self.fixture,self.m)
        r=self.run_observation(platform)
        self.assertEqual(r['outcome'],expected)
        self.assertFalse(r['may_activate']);self.assertFalse(r['may_apply']);self.assertFalse(r['may_delete'])
        self.assertTrue(all(x['method']=='GET' for x in self.fixture.requests))
    test.__name__='test_'+name
    setattr(NativeWireTests,test.__name__,test)


def change_status(f,m,key,value):f.routes[nsx.status_target(m['resources'][0]['path'])]['body'][key]=value

def change_task(f,m,key,value):f.routes[nut.task_target(m)]['body']['data'][key]=value

def change_resource(f,m,key,value):f.routes[nut.resource_target(m['resources'][0])]['body']['data'][key]=value

for status in (301,302,307,308,401,403,404,409,429,500,503):
    def mutate(f,m,status=status):
        for s in f.routes.values():s.update(status=status,headers=[('Location','https://other.invalid/steal')])
    wire_case('http_'+str(status)+'_never_follows_or_retries','nsx',mutate,'HOLD_UNCERTAIN')

for name,key,val,expect in [
 ('wrong_path','intent_path','/infra/segments/foreign','HOLD_UNCERTAIN'),
 ('old_intent_version','intent_version','older','HOLD_NATIVE_PENDING'),
 ('unknown_publish','publish_status','FUTURE_STATUS','HOLD_UNCERTAIN'),
 ('publication_error','publish_status','ERROR','HOLD_NATIVE_FAILURE'),
 ('not_published','publish_status','UNREALIZED','HOLD_NATIVE_PENDING'),
 ('missing_span','consolidated_status_per_enforcement_point',[],'HOLD_UNCERTAIN'),
 ('unknown_span_state','consolidated_status',{'consolidated_status':'UNKNOWN'},'HOLD_UNCERTAIN'),
 ('wrong_span','consolidated_status_per_enforcement_point',[{'enforcement_point_path':EP+'2','consolidated_status':{'consolidated_status':'SUCCESS'}}],'HOLD_UNCERTAIN'),
 ('duplicate_span','consolidated_status_per_enforcement_point',[{'enforcement_point_path':EP,'consolidated_status':{'consolidated_status':'SUCCESS'}}]*2,'HOLD_UNCERTAIN'),
 ('numeric_version','intent_version',7,'HOLD_UNCERTAIN')]:
    wire_case('nsx_'+name,'nsx',lambda f,m,k=key,v=val:change_status(f,m,k,v),expect)

for name,key,val,expect in [
 ('running','status','RUNNING','HOLD_NATIVE_PENDING'),('canceling','status','CANCELING','HOLD_NATIVE_PENDING'),
 ('failed','status','FAILED','HOLD_NATIVE_FAILURE'),('canceled','status','CANCELED','HOLD_NATIVE_FAILURE'),
 ('suspended','status','SUSPENDED','HOLD_UNCERTAIN'),('unknown','status','$UNKNOWN','HOLD_UNCERTAIN'),
 ('future_status','status','ALMOST_SUCCEEDED','HOLD_UNCERTAIN'),('wrong_task','extId','different-task','HOLD_UNCERTAIN'),
 ('wrong_operation','operation','Delete VPC','HOLD_UNCERTAIN'),('batch','numberOfSubtasks',1,'HOLD_UNCERTAIN'),
 ('truncated_entities','numberOfEntitiesAffected',2,'HOLD_UNCERTAIN'),
 ('unscoped_entity','entitiesAffected',[{'extId':'44444444-4444-4444-8444-444444444444'}],'HOLD_UNCERTAIN'),
 ('diagnostics','warnings',[{'message':'SENSITIVE_ERROR'}],'HOLD_UNCERTAIN'),
 ('missing_completion','completedTime',None,'HOLD_UNCERTAIN'),
 ('old_task','createdTime','2020-01-01T00:00:00Z','HOLD_UNCERTAIN')]:
    wire_case('nutanix_'+name,'nutanix',lambda f,m,k=key,v=val:change_task(f,m,k,v),expect)

wire_case('nutanix_native_tenant_mismatch','nutanix',lambda f,m:change_resource(f,m,'tenantId','foreign'),'HOLD_UNCERTAIN')
wire_case('nutanix_vpc_mismatch','nutanix',lambda f,m:change_resource(f,m,'extId','foreign'),'HOLD_UNCERTAIN')
wire_case('nutanix_external_attachment_diff','nutanix',lambda f,m:change_resource(f,m,'externalSubnets',[{'subnetReference':'unapproved'}]),'HOLD_DIFFERENCE')
wire_case('nutanix_weak_etag','nutanix',lambda f,m:f.routes[nut.resource_target(m['resources'][0])].update(etag='W/"weak"'),'HOLD_UNCERTAIN')
wire_case('nutanix_changed_etag','nutanix',lambda f,m:f.routes[nut.resource_target(m['resources'][0])].update(etag='"new"'),'HOLD_DIFFERENCE')
wire_case('nutanix_no_etag','nutanix',lambda f,m:f.routes[nut.resource_target(m['resources'][0])].pop('etag'),'HOLD_UNCERTAIN')
wire_case('duplicate_json','nsx',lambda f,m:[s.update(raw=b'{"a":1,"a":2}') for s in f.routes.values()],'HOLD_UNCERTAIN')
wire_case('overflow_json_number','nsx',lambda f,m:[s.update(raw=b'{"a":1e999}') for s in f.routes.values()],'HOLD_UNCERTAIN')
wire_case('wrong_json_type','nsx',lambda f,m:[s.update(raw=b'[]') for s in f.routes.values()],'HOLD_UNCERTAIN')
wire_case('wrong_content_type','nsx',lambda f,m:[s.update(content_type='text/html') for s in f.routes.values()],'HOLD_UNCERTAIN')
wire_case('response_oversize','nsx',lambda f,m:[s.update(length=c.LIMIT+1) for s in f.routes.values()],'HOLD_UNCERTAIN')
wire_case('response_truncated','nsx',lambda f,m:[s.update(length=1000,raw=b'{"x":1}') for s in f.routes.values()],'HOLD_UNCERTAIN')


class ManifestAndJournalTests(unittest.TestCase):
    def test_disabled_examples_make_no_contact(self):
        for platform in ('nsx','nutanix'):
            m=manifest(platform,'https://management.invalid');m['contact_enabled']=False
            with tempfile.TemporaryDirectory() as d:
                p=Path(d,'m.json');p.write_text(json.dumps(m))
                out=subprocess.run([sys.executable,str(ROOT/'tools'/f'{platform}_observe.py'),str(p)],capture_output=True,text=True)
                self.assertEqual(out.returncode,0,out.stdout);self.assertFalse(json.loads(out.stdout)['target_contacted'])
    def test_explicit_read_flag_still_needs_contact_enabled(self):
        m=manifest('nsx','https://management.invalid');m['contact_enabled']=False
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,'m.json');p.write_text(json.dumps(m))
            out=subprocess.run([sys.executable,str(ROOT/'tools/nsx_observe.py'),str(p),'--read-authorized-target'],capture_output=True,text=True)
            self.assertEqual(out.returncode,2)
    def test_new_journal_is_private_and_incomplete_until_written(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,'evidence')
            with c.PrivateJournal(p):
                self.assertEqual(p.stat().st_mode & 0o777,0o600)
                self.assertEqual(json.loads(p.read_text())['outcome'],'HOLD_INCOMPLETE')
    def test_symlink_journal_refused(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d,'target');target.write_text('untouched');link=Path(d,'link');link.symlink_to(target)
            with self.assertRaises(FileExistsError):c.PrivateJournal(link)
            self.assertEqual(target.read_text(),'untouched')
    def test_ordered_arrays_and_missing_fields(self):
        self.assertTrue(c.differences([1,2],[2,1]));self.assertTrue(c.differences({}, {'x':False}))
    def test_origin_mismatch(self):
        with self.assertRaises(ValueError):c.ReadClient('https://a.invalid','https://b.invalid','x','x',{'/x'})
    def test_no_task_url_or_double_encoded_path(self):
        for value in ('https://x.invalid/task','a/../b','%2e%2e','task?cancel=true'):
            m=manifest('nutanix','https://management.invalid');m['task']['ext_id']=value
            with self.assertRaises(ValueError):nut.validate(m)
    def test_no_nsx_wildcard_or_project_scope_expansion(self):
        for path in ('/infra/segments/*','/infra/segments/a/../b','/infra/segments/a%2fb','/global-infra/segments/a'):
            m=manifest('nsx','https://management.invalid');m['resources'][0]['path']=path
            with self.assertRaises(ValueError):nsx.validate(m)
    def test_credentials_cannot_enter_manifest(self):
        m=manifest('nsx','https://management.invalid');m['resources'][0]['expected']['rules'][0]['password']='no'
        with self.assertRaises(ValueError):nsx.validate(m)
    def test_duplicate_native_resources_rejected(self):
        for platform,a in [('nsx',nsx),('nutanix',nut)]:
            m=manifest(platform,'https://management.invalid');m['resources'].append(deepcopy(m['resources'][0]))
            with self.assertRaises(ValueError):a.validate(m)
    def test_exhausted_budget_no_request(self):
        with Fixture() as f:
            m=f.reset('nsx');cl=f.client(m);cl.deadline=0
            with self.assertRaises(c.ObservationError):cl.get(next(iter(nsx.targets(m))))
            self.assertEqual(f.requests,[])


class RecoveryReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f=Fixture();cls.m=cls.f.reset('nutanix')
        cls.report=c.observe(cls.m,cls.f.client(cls.m),nut,rounds=3,interval=0)
    @classmethod
    def tearDownClass(cls):cls.f.close()
    def setUp(self):
        self.m=deepcopy(self.__class__.m);self.r=deepcopy(self.__class__.report);self.x=context(self.m,self.r)
    def review(self):return rr.review(self.m,self.r,self.x)
    def test_matching_is_review_only(self):
        r=self.review();self.assertEqual(r['result'],'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        self.assertFalse(r['may_apply']);self.assertFalse(r['may_delete']);self.assertFalse(r['may_activate'])
    def test_containment_overrides_ordinary_state(self):
        self.x['containment']='ACTIVE';self.assertEqual(self.review()['result'],'KEEP_INCIDENT_CONTAINMENT')
    def test_stopped_runner_without_fencing_is_not_enough(self):
        self.x['writer_fence']['state']='UNVERIFIED';self.assertEqual(self.review()['result'],'HOLD_WRITER_NOT_FENCED')
    def test_running_runner(self):
        self.x['executor_state']='RUNNING';self.assertEqual(self.review()['result'],'HOLD_WRITER_NOT_FENCED')
    def test_superseded_generation(self):
        self.x['current_generation']+=1;self.assertEqual(self.review()['result'],'HOLD_SUPERSEDED_CHANGE')
    def test_missing_quarantine_proof(self):
        self.x['quarantine']['state']='UNKNOWN';self.assertEqual(self.review()['result'],'HOLD_QUARANTINE_NOT_VERIFIED')
    def test_foreign_fence_scope(self):
        self.x['writer_fence']['scope_id']='D02O';self.assertEqual(self.review()['result'],'HOLD_WRITER_NOT_FENCED')
    def test_wrong_report_digest(self):
        self.x['report_sha256']='a'*64;self.assertEqual(self.review()['result'],'HOLD_INVALID_EVIDENCE')
    def test_wrong_manifest_generation_digest(self):
        self.m['engineering_record_ref']='another';self.assertEqual(self.review()['result'],'HOLD_INVALID_EVIDENCE')
    def test_future_observation(self):
        self.r['completed_at']=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat();seal(self.r);self.x['report_sha256']=self.r['content_sha256']
        self.assertEqual(self.review()['result'],'HOLD_INVALID_EVIDENCE')
    def test_expired_observation(self):
        r=rr.review(self.m,self.r,self.x,current=datetime.now(timezone.utc)+timedelta(hours=1))
        self.assertEqual(r['result'],'HOLD_INVALID_EVIDENCE')
    def test_new_security_change_invalidates_old_reads(self):
        self.x['last_security_change_at']=datetime.now(timezone.utc).isoformat();self.assertEqual(self.review()['result'],'HOLD_INVALID_EVIDENCE')
    def test_forged_summary_recomputed(self):
        self.r['stable_rounds']=999;seal(self.r);self.x['report_sha256']=self.r['content_sha256']
        self.assertEqual(self.review()['result'],'HOLD_INVALID_EVIDENCE')
    def test_removed_resource_coverage(self):
        self.r['history'][-1]['states']=[];seal(self.r);self.x['report_sha256']=self.r['content_sha256']
        self.assertEqual(self.review()['result'],'HOLD_INVALID_EVIDENCE')
    def test_duplicate_round(self):
        self.r['history'][1]['round']=1;seal(self.r);self.x['report_sha256']=self.r['content_sha256']
        self.assertEqual(self.review()['result'],'HOLD_INVALID_EVIDENCE')
    def test_modified_sample_digest(self):
        self.r['history'][-1]['snapshot_sha256']='a'*64;seal(self.r);self.x['report_sha256']=self.r['content_sha256']
        self.assertEqual(self.review()['result'],'HOLD_INVALID_EVIDENCE')
    def test_data_destruction_never_authorized(self):
        self.x['data_disposition']='DELETE';self.assertEqual(self.review()['result'],'HOLD_INVALID_EVIDENCE')
    def test_forged_activate_flag(self):
        self.r['may_activate']=True;seal(self.r);self.x['report_sha256']=self.r['content_sha256']
        self.assertEqual(self.review()['result'],'HOLD_INVALID_EVIDENCE')
    def test_native_pending_is_not_replay_permission(self):
        m=self.f.reset('nutanix');self.f.routes[nut.task_target(m)]['body']['data']['status']='RUNNING'
        r=c.observe(m,self.f.client(m),nut,interval=0)
        self.assertEqual(rr.review(m,r,context(m,r))['result'],'WAIT_FOR_NATIVE_TASK')
    def test_failed_task_is_partial_failure_not_rollback(self):
        m=self.f.reset('nutanix');self.f.routes[nut.task_target(m)]['body']['data']['status']='FAILED'
        r=c.observe(m,self.f.client(m),nut,interval=0)
        self.assertEqual(rr.review(m,r,context(m,r))['result'],'INSPECT_PARTIAL_FAILURE')
    def test_completed_task_with_wrong_actual_resource_is_divergence(self):
        m=self.f.reset('nutanix');self.f.routes[nut.resource_target(m['resources'][0])]['body']['data']['externalSubnets']=[{'subnetReference':'unexpected'}]
        r=c.observe(m,self.f.client(m),nut,interval=0)
        self.assertEqual(rr.review(m,r,context(m,r))['result'],'RECONCILE_DIVERGENCE')
    def test_context_credentials_rejected(self):
        self.x['writer_fence']['secret']='no';self.assertEqual(self.review()['result'],'HOLD_INVALID_EVIDENCE')


class AdditionalKindTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.f=Fixture()
    @classmethod
    def tearDownClass(cls):cls.f.close()
    def nsx_kind(self,kind,path,values):
        m=self.f.reset('nsx');r=m['resources'][0]
        r.update(kind=kind,path=path,expected={'id':path.rsplit('/',1)[1],'path':path,
            'resource_type':nsx.TYPES[kind],'_revision':9,**values})
        self.f.routes=responses(m)
        out=c.observe(m,self.f.client(m),nsx,interval=0)
        self.assertEqual(out['outcome'],'READBACK_MATCH_NOT_QUALIFIED')
    def test_segment(self):
        self.nsx_kind('segment','/infra/segments/seg-01',{'connectivity_path':None,'transport_zone_path':'/infra/sites/default/enforcement-points/default/transport-zones/tz1','subnets':[], 'advanced_config':{'connectivity':'OFF'}})
    def test_tier1(self):
        self.nsx_kind('tier1','/infra/tier-1s/t1-01',{'tier0_path':None,'route_advertisement_types':[]})
    def test_static_route(self):
        self.nsx_kind('static_route','/infra/tier-1s/t1-01/static-routes/rt1',{'network':'192.0.2.0/24','next_hops':[{'ip_address':'192.0.2.2','admin_distance':1}]})
    def test_group(self):
        self.nsx_kind('group','/infra/domains/default/groups/group-01',{'expression':[{'resource_type':'PathExpression','paths':['/infra/segments/seg-01']}]})
    def test_security_policy(self):
        m=self.f.reset('nsx');r=m['resources'][0];r['kind']='security_policy';r['path']='/infra/domains/default/security-policies/p1'
        r['expected'].update(id='p1',path=r['path'],resource_type='SecurityPolicy')
        self.f.routes=responses(m)
        self.assertEqual(c.observe(m,self.f.client(m),nsx,interval=0)['outcome'],'READBACK_MATCH_NOT_QUALIFIED')
    def test_nutanix_subnet(self):
        m=self.f.reset('nutanix');r=m['resources'][0];r['kind']='subnet';r['expected']={
            '$objectType':'networking.v4.config.Subnet','extId':r['ext_id'],'tenantId':'33333333-3333-4333-8333-333333333333',
            'name':'subnet-01','subnetType':'OVERLAY','vpcReference':'55555555-5555-4555-8555-555555555555',
            'isExternal':False,'ipConfig':[{'ipv4':{'ipSubnet':{'ip':'192.0.2.0','prefixLength':24},'defaultGatewayIp':'192.0.2.1'}}]}
        m['task']['operation']='Create Subnet';self.f.routes=responses(m)
        self.assertEqual(c.observe(m,self.f.client(m),nut,interval=0)['outcome'],'READBACK_MATCH_NOT_QUALIFIED')
    def test_missing_optional_return_field_is_not_assumed_empty(self):
        m=self.f.reset('nutanix');del self.f.routes[nut.resource_target(m['resources'][0])]['body']['data']['externalSubnets']
        self.assertEqual(c.observe(m,self.f.client(m),nut,interval=0)['outcome'],'HOLD_UNCERTAIN')
    def test_task_changes_to_success_mid_snapshot_needs_later_stable_pair(self):
        m=self.f.reset('nutanix');target=nut.task_target(m)
        def hook(p,n,s):
            if p==target and n==1:s['body']['data']['status']='RUNNING'
            return s
        self.f.hook=hook;r=c.observe(m,self.f.client(m),nut,rounds=4,interval=0)
        self.assertEqual(r['outcome'],'READBACK_MATCH_NOT_QUALIFIED');self.assertEqual(len(r['history']),3)
    def test_untrusted_callback_links_never_followed(self):
        m=self.f.reset('nutanix')
        for spec in self.f.routes.values():spec['body']['links']=[{'href':'https://foreign.invalid/credentials'}]
        r=c.observe(m,self.f.client(m),nut,interval=0)
        self.assertEqual(r['outcome'],'READBACK_MATCH_NOT_QUALIFIED')
        self.assertTrue(all(q['path'] in nut.targets(m) for q in self.f.requests))

class ExtraGuardTests(unittest.TestCase):
    def test_expected_redaction_is_not_an_acceptable_value(self):
        m=manifest('nutanix','https://management.invalid');m['resources'][0]['expected']['vpcType']='$REDACTED'
        with self.assertRaises(ValueError):nut.validate(m)
    def test_native_enum_unknown_is_not_accepted_expectation(self):
        m=manifest('nutanix','https://management.invalid');m['resources'][0]['expected']['vpcType']='$UNKNOWN'
        with self.assertRaises(ValueError):nut.validate(m)
    def test_string_boolean_manifest_rejected(self):
        m=manifest('nsx','https://management.invalid');m['resources'][0]['expected']['stateful']='true'
        with self.assertRaises(ValueError):nsx.validate(m)
    def test_new_policy_no_empty_scope(self):
        m=manifest('nsx','https://management.invalid');m['resources'][0]['expected']['rules'][0]['scope']=[]
        with self.assertRaises(ValueError):nsx.validate(m)
    def test_slow_trickle_cannot_extend_body_budget_indefinitely(self):
        import time
        with Fixture() as f:
            m=f.reset('nsx')
            for spec in f.routes.values():spec['chunk_delay']=0.02
            client=f.client(m,timeout=0.2,budget=1)
            start=time.monotonic();r=c.observe(m,client,nsx,interval=0)
            self.assertEqual(r['outcome'],'HOLD_UNCERTAIN');self.assertLess(time.monotonic()-start,2.5)
    def test_duplicate_expected_rule_identifier_rejected(self):
        m=manifest('nsx','https://management.invalid');m['resources'][0]['expected']['rules']*=2
        with self.assertRaises(ValueError):nsx.validate(m)
    def test_bad_native_api_version_is_rejected_before_reads(self):
        m=manifest('nutanix','https://management.invalid');m['profile']='nutanix-v4-latest'
        with self.assertRaises(ValueError):nut.validate(m)


class RuleCompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.f=Fixture()
    @classmethod
    def tearDownClass(cls):cls.f.close()
    def assert_actual_change(self, key, value):
        m=self.f.reset('nsx')
        self.f.routes['/policy/api/v1'+m['resources'][0]['path']]['body']['rules'][0][key]=value
        self.assertEqual(c.observe(m,self.f.client(m),nsx,interval=0)['outcome'],'HOLD_DIFFERENCE')
    def test_source_negation_is_observed(self):self.assert_actual_change('sources_excluded',True)
    def test_destination_negation_is_observed(self):self.assert_actual_change('destinations_excluded',True)
    def test_inline_service_change_is_observed(self):self.assert_actual_change('service_entries',[{'resource_type':'L4PortSetServiceEntry','l4_protocol':'TCP','destination_ports':['8443']}])
    def test_l7_profile_change_is_observed(self):self.assert_actual_change('profiles',['/infra/context-profiles/other'])
    def test_missing_negation_is_unknown_not_false(self):
        m=self.f.reset('nsx')
        del self.f.routes['/policy/api/v1'+m['resources'][0]['path']]['body']['rules'][0]['sources_excluded']
        self.assertEqual(c.observe(m,self.f.client(m),nsx,interval=0)['outcome'],'HOLD_UNCERTAIN')
    def test_nondeterministic_equal_sequences_rejected(self):
        m=manifest('nsx','https://management.invalid');rules=m['resources'][0]['expected']['rules']
        second=deepcopy(rules[0]);second['id']='other';rules.append(second)
        with self.assertRaises(ValueError):nsx.validate(m)

if __name__=='__main__':unittest.main()
