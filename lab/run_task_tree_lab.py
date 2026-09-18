#!/usr/bin/env python3
"""Execute fixed loopback-HTTPS task-tree and interrupted-change observations.

Bodies, task transitions and outside-control records are scripted. Real TLS/CLI
execution is not native Nutanix product, task-fencing or platform qualification.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lab.native_readback_fixture import Fixture, TASK
from lab.nutanix_task_tree_fixture import reset, CHILD_A, CHILD_B, GRANDCHILD
from lab.run_readback_lab import operator_context
from tools import nutanix_observe as native, nutanix_task_tree as tree, readback_core as c, recovery_review as rr
ROOT=Path(__file__).resolve().parents[1]
SOURCE_FILES=('tools/nutanix_task_tree.py','tools/nutanix_observe.py','tools/readback_core.py',
 'tools/readback_cli.py','tools/recovery_review.py','lab/native_readback_fixture.py',
 'lab/nutanix_task_tree_fixture.py','lab/run_readback_lab.py','lab/run_task_tree_lab.py')


def campaign() -> list[dict]:
    rows=[]
    with Fixture() as f:
        def case(name,expected,review,mutate=None,ctxchange=None):
            m=reset(f)
            if mutate:mutate(f,m)
            r=c.observe(m,f.client(m),native,rounds=3,interval=0)
            context=operator_context(m,r)
            if ctxchange:ctxchange(context)
            decision=rr.review(m,r,context)
            good=(r['outcome']==expected and decision['result']==review
                and all(q['method']=='GET' and q['path'] in native.targets(m) for q in f.requests)
                and r['request_count']==len(f.requests)
                and all(decision[k] is False for k in ('may_apply','may_delete','may_activate')))
            rows.append({'id':f'TREE-{len(rows)+1:03}','case':name,'status':'PASS' if good else 'FAIL',
                'expected_readback':expected,'expected_recovery_review':review,
                'readback':r,'recovery_review':decision,'requests':deepcopy(f.requests),
                'external_control_evidence':'SIMULATED_ONLY_NOT_PROOF_OF_WRITER_FENCING_OR_QUARANTINE'})
        def changed(ident,**values):
            return lambda f,m:f.routes[tree.target(ident)]['body']['data'].update(**values)
        case('complete-nested-tree-and-selected-resources','READBACK_MATCH_NOT_QUALIFIED','READY_FOR_OPERATOR_RECOVERY_REVIEW')
        case('succeeded-parent-running-grandchild','HOLD_NATIVE_PENDING','WAIT_FOR_NATIVE_TASK',changed(GRANDCHILD,status='RUNNING',completedTime=None,progressPercentage=100))
        def delayed(f,m):
            def hook(path,n,spec):
                if path==tree.target(GRANDCHILD) and n<=2:spec['body']['data'].update(status='RUNNING',completedTime=None)
                return spec
            f.hook=hook
        case('delayed-child-then-two-complete-rounds','READBACK_MATCH_NOT_QUALIFIED','READY_FOR_OPERATOR_RECOVERY_REVIEW',delayed)
        case('failed-descendant-existing-resources','HOLD_NATIVE_FAILURE','INSPECT_PARTIAL_FAILURE',changed(GRANDCHILD,status='FAILED',legacyErrorMessage='scripted sensitive failure detail'))
        case('canceled-child','HOLD_NATIVE_FAILURE','INSPECT_PARTIAL_FAILURE',changed(CHILD_B,status='CANCELED'))
        case('missing-child-task','HOLD_UNCERTAIN','HOLD_NATIVE_UNCERTAINTY',lambda f,m:f.routes[tree.target(GRANDCHILD)].update(status=404))
        case('parent-child-list-truncated','HOLD_UNCERTAIN','HOLD_NATIVE_UNCERTAINTY',changed(TASK,subTasks=[{'extId':CHILD_A}]))
        case('child-belongs-to-wrong-parent','HOLD_UNCERTAIN','HOLD_NATIVE_UNCERTAINTY',changed(GRANDCHILD,parentTask={'extId':CHILD_B}))
        case('unlisted-child-not-discovered','HOLD_UNCERTAIN','HOLD_NATIVE_UNCERTAINTY',changed(TASK,subTasks=[{'extId':CHILD_A},{'extId':'unaccepted'}]))
        case('partial-affected-entity-coverage','HOLD_UNCERTAIN','HOLD_NATIVE_UNCERTAINTY',changed(GRANDCHILD,numberOfEntitiesAffected=2))
        case('batch-summary-unsupported','HOLD_UNCERTAIN','HOLD_NATIVE_UNCERTAINTY',changed(TASK,batchSummary={'numberOfJobs':1}))
        case('success-with-diagnostics','HOLD_UNCERTAIN','HOLD_NATIVE_UNCERTAINTY',changed(GRANDCHILD,warnings=[{'message':'scripted private diagnostic'}]))
        def mismatch(f,m):f.routes[native.resource_target(m['resources'][1])]['etag']='"unexpected-version"'
        case('complete-tree-but-resource-etag-differs','HOLD_DIFFERENCE','RECONCILE_DIVERGENCE',mismatch)
        def staleidentity(f,m):
            def hook(path,n,spec):
                if path==tree.target(GRANDCHILD):
                    if n<=2:spec['body']['data'].update(status='RUNNING',completedTime=None)
                    else:spec['body']['data']['createdTime']=f.routes[tree.target(CHILD_A)]['body']['data']['createdTime']
                return spec
            f.hook=hook
        case('identity-changes-between-observations','HOLD_UNCERTAIN','HOLD_NATIVE_UNCERTAINTY',staleidentity)
        case('matched-tree-unfenced-writer','READBACK_MATCH_NOT_QUALIFIED','HOLD_WRITER_NOT_FENCED',ctxchange=lambda x:x['writer_fence'].update(state='UNVERIFIED'))
        case('matched-tree-active-containment','READBACK_MATCH_NOT_QUALIFIED','KEEP_INCIDENT_CONTAINMENT',ctxchange=lambda x:x.update(containment='ACTIVE'))
        case('matched-tree-superseded-change','READBACK_MATCH_NOT_QUALIFIED','HOLD_SUPERSEDED_CHANGE',ctxchange=lambda x:x.update(current_generation=5))
        # Execute the actual CLI and protected journal, with a real polling delay.
        with tempfile.TemporaryDirectory(prefix='task-tree-cli-') as temp:
            directory=Path(temp);m=reset(f);delayed(f,m)
            input_path=directory/'manifest.json';input_path.write_text(json.dumps(m))
            output=directory/'readback.json'
            env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','LD_LIBRARY_PATH')}
            env.update(NUTANIX_USERNAME='fixture-reader',NUTANIX_PASSWORD='temporary-fixture-secret')
            proc=subprocess.run([sys.executable,str(ROOT/'tools/nutanix_observe.py'),str(input_path),
                '--read-authorized-target','--expected-origin',f.origin,'--ca-file',str(f.directory/'ca.pem'),
                '--output',str(output),'--interval','0.1'],env=env,capture_output=True,text=True,timeout=25)
            r=c.load(output) if output.exists() else {};decision=rr.review(m,r,operator_context(m,r)) if r else {}
            good=(proc.returncode==0 and r.get('outcome')=='READBACK_MATCH_NOT_QUALIFIED'
                  and r.get('request_count')==30 and len(r.get('history',[]))==3
                  and decision.get('result')=='READY_FOR_OPERATOR_RECOVERY_REVIEW'
                  and output.stat().st_mode & 0o777==0o600)
            rows.append({'id':f'TREE-{len(rows)+1:03}','case':'actual-cli-polls-known-tree-and-records-private-result',
                'status':'PASS' if good else 'FAIL','exit_code':proc.returncode,'readback':r,
                'recovery_review':decision,'requests':deepcopy(f.requests),
                'external_control_evidence':'SIMULATED_ONLY_NOT_PROOF_OF_WRITER_FENCING_OR_QUARANTINE'})
        if any('scripted sensitive failure detail' in json.dumps(row) or 'scripted private diagnostic' in json.dumps(row) for row in rows):
            raise RuntimeError('Fixture diagnostics escaped redaction')
    return rows


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not a.execute:p.error('Explicit --execute runs only the fixed disposable loopback fixture')
    begun=c.now();rows=campaign();failed=sum(x['status']!='PASS' for x in rows)
    report={'kind':'LOCAL_NUTANIX_TASK_TREE_CAMPAIGN','status':'PASSED_LOCAL_HTTPS_ONLY' if not failed else 'FAILED_LOCAL_CAMPAIGN',
        'started_at':begun,'completed_at':c.now(),'passed':len(rows)-failed,'failed':failed,'cases':rows,
        'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCE_FILES},
        'native_target_contact':'NOT_RUN','native_apply':'NOT_RUN','native_qualification':'NOT_RUN',
        'limits':['Real loopback TLS and CLI; task/resource bodies and timing transitions are scripted',
                 'Parent/child fixture tests are not actual native composite operation proof',
                 'Writer fencing, quarantine records and change authority are simulated outside-control inputs',
                 'Only complete explicitly enumerated small trees; batch/partial/unlisted tasks remain unsupported']}
    out=ROOT/'build/reports/local_task_tree_readback.json';out.parent.mkdir(parents=True,exist_ok=True)
    with c.PrivateJournal(out) as journal:journal.write(report)
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2));return 2 if failed else 0
if __name__=='__main__':raise SystemExit(main())
