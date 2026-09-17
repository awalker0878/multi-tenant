#!/usr/bin/env python3
"""Execute only the fixed local HTTPS observation/recovery campaign; no native targets."""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import sys
if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lab.native_readback_fixture import Fixture, responses
from tools import readback_core as c, nsx_observe as nsx, nutanix_observe as nut, recovery_review as rr

ROOT=Path(__file__).resolve().parents[1]


def operator_context(m,r):
    before=(datetime.now(timezone.utc)-timedelta(seconds=30)).isoformat()
    return {'kind':'INTERRUPTED_CHANGE_CONTEXT_V1','operation_id':m['operation_id'],'tenant_id':m['tenant_id'],
      'scope_id':m['scope_id'],'manifest_sha256':c.digest(m),'report_sha256':r['content_sha256'],
      'accepted_plan_sha256':c.digest({'local_fixture_plan':4}),'change_record_ref':'LOCAL-TEST-CHANGE',
      'attempted_at':before,'last_security_change_at':before,'attempted_generation':4,'current_generation':4,
      'executor_state':'STOPPED','containment':'NONE','data_disposition':'PRESERVE',
      'writer_fence':{'state':'VERIFIED','scope_id':m['scope_id'],'observed_at':c.now(),'evidence_ref':'SIMULATED-EXTERNAL-FENCE-RECORD'},
      'quarantine':{'state':'VERIFIED','scope_id':m['scope_id'],'observed_at':c.now(),'evidence_ref':'SIMULATED-EXTERNAL-QUARANTINE-RECORD'}}


def campaign():
    rows=[]
    with Fixture() as f:
        def case(name,platform,expected,mutate=None,context_change=None,expected_review=None):
            m=f.reset(platform)
            if mutate:mutate(f,m)
            a=nsx if platform=='nsx' else nut
            r=c.observe(m,f.client(m),a,rounds=4,interval=0)
            x=operator_context(m,r)
            if context_change:context_change(x)
            decision=rr.review(m,r,x)
            ok=(r['outcome']==expected and all(q['method']=='GET' for q in f.requests)
                and not any(decision[k] for k in ('may_apply','may_delete','may_activate'))
                and (expected_review is None or decision['result']==expected_review))
            rows.append({'case':name,'result':'PASSED' if ok else 'FAILED','expected_readback':expected,
                'readback':r,'recovery_review':decision,'requests':deepcopy(f.requests),
                'operator_control_records':'SIMULATED; actual writer fencing and quarantine not proven by this fixture'})
        case('nsx-current-config-and-realization','nsx','READBACK_MATCH_NOT_QUALIFIED',expected_review='READY_FOR_OPERATOR_RECOVERY_REVIEW')
        def lag(f,m):
            status=nsx.status_target(m['resources'][0]['path'])
            def hook(path,n,s):
                if path==status and n==1:s['body']['publish_status']='UNREALIZED'
                return s
            f.hook=hook
        case('nsx-realization-lag-then-completes','nsx','READBACK_MATCH_NOT_QUALIFIED',lag)
        def race(f,m):
            path='/policy/api/v1'+m['resources'][0]['path']
            def hook(p,n,s):
                if p==path and n%2==0:s['body']['_revision']+=1
                return s
            f.hook=hook
        case('nsx-config-races-status-read','nsx','HOLD_UNCERTAIN',race)
        case('nsx-permission-drift','nsx','HOLD_DIFFERENCE',lambda f,m:f.routes['/policy/api/v1'+m['resources'][0]['path']]['body']['rules'][0].update(action='ALLOW'),expected_review='RECONCILE_DIVERGENCE')
        case('nsx-stale-intent-version','nsx','HOLD_NATIVE_PENDING',lambda f,m:f.routes[nsx.status_target(m['resources'][0]['path'])]['body'].update(intent_version='previous'),expected_review='WAIT_FOR_NATIVE_TASK')
        case('nsx-missing-realization-span','nsx','HOLD_UNCERTAIN',lambda f,m:f.routes[nsx.status_target(m['resources'][0]['path'])]['body'].update(consolidated_status_per_enforcement_point=[]))
        case('nutanix-completed-task-matching-vpc','nutanix','READBACK_MATCH_NOT_QUALIFIED',expected_review='READY_FOR_OPERATOR_RECOVERY_REVIEW')
        def pending(f,m):
            target=nut.task_target(m)
            def hook(p,n,s):
                if p==target and n<=2:s['body']['data']['status']='RUNNING'
                return s
            f.hook=hook
        case('nutanix-delayed-task-no-resubmit','nutanix','READBACK_MATCH_NOT_QUALIFIED',pending)
        case('nutanix-failed-task-with-existing-vpc','nutanix','HOLD_NATIVE_FAILURE',lambda f,m:f.routes[nut.task_target(m)]['body']['data'].update(status='FAILED'),expected_review='INSPECT_PARTIAL_FAILURE')
        case('nutanix-task-404','nutanix','HOLD_UNCERTAIN',lambda f,m:f.routes[nut.task_target(m)].update(status=404),expected_review='HOLD_NATIVE_UNCERTAINTY')
        case('nutanix-foreign-native-tenant','nutanix','HOLD_UNCERTAIN',lambda f,m:f.routes[nut.resource_target(m['resources'][0])]['body']['data'].update(tenantId='44444444-4444-4444-8444-444444444444'))
        case('nutanix-etag-conflict','nutanix','HOLD_DIFFERENCE',lambda f,m:f.routes[nut.resource_target(m['resources'][0])].update(etag='"changed"'),expected_review='RECONCILE_DIVERGENCE')
        case('nutanix-unenumerated-affected-entity','nutanix','HOLD_UNCERTAIN',lambda f,m:f.routes[nut.task_target(m)]['body']['data'].update(numberOfEntitiesAffected=2))
        case('stop-runner-is-not-proof-of-fencing','nutanix','READBACK_MATCH_NOT_QUALIFIED',context_change=lambda x:x['writer_fence'].update(state='UNVERIFIED'),expected_review='HOLD_WRITER_NOT_FENCED')
        case('incident-containment-survives-readback','nsx','READBACK_MATCH_NOT_QUALIFIED',context_change=lambda x:x.update(containment='ACTIVE'),expected_review='KEEP_INCIDENT_CONTAINMENT')
        case('new-generation-needs-new-review','nsx','READBACK_MATCH_NOT_QUALIFIED',context_change=lambda x:x.update(current_generation=5),expected_review='HOLD_SUPERSEDED_CHANGE')
    files=['tools/readback_core.py','tools/nsx_observe.py','tools/nutanix_observe.py','tools/readback_cli.py',
           'tools/recovery_review.py','lab/native_readback_fixture.py','lab/run_readback_lab.py']
    return {'kind':'LOCAL_NATIVE_READBACK_PROTOCOL_CAMPAIGN','status':'PASSED_LOCAL_HTTPS_FIXTURE' if all(r['result']=='PASSED' for r in rows) else 'FAILED',
        'completed_at':c.now(),'passed':sum(r['result']=='PASSED' for r in rows),'failed':sum(r['result']!='PASSED' for r in rows),
        'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files},'cases':rows,
        'scope':'Real localhost TLS and HTTP GET exchanges against scripted published response shapes; not a Nutanix/NSX server, native task execution, native RBAC or packet qualification.',
        'target_infrastructure_contacted':False,'production_mutations':0,'writes_to_fixture_api':0}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not a.execute:
        print('Not executed. --execute runs only the fixed disposable localhost HTTPS fixture.');return 0
    result=campaign();(ROOT/'build/reports').mkdir(parents=True,exist_ok=True);(ROOT/'build/reports/local_native_readback.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','source_sha256')},indent=2))
    return 0 if not result['failed'] else 1
if __name__=='__main__':raise SystemExit(main())
