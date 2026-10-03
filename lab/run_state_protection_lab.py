#!/usr/bin/env python3
"""Real TLS state export and restic restore, with disposable GitLab-shaped data."""
import argparse
from datetime import timedelta
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab.native_readback_fixture import Fixture
from provisioner.execution import readback_core as c
from tools import state_export as exports, state_project as projects
from provisioner.execution.source_integrity import verify
from tools.restic_run import Restic,backup,restore,sha_file
from provisioner.execution.run_files import digest,encoded,require,utcnow
from tools.state_backend import compile_backend


def export_fixture(base,commit):
    with Fixture() as server:
        ca=server.directory/'ca.pem'; ca.chmod(0o600)
        scope=dict(environment_key='test',site_key='lab-site',platform='openstack',tenant_key='tenant-a',wsd_key='science')
        project=dict(format='hosting-state-project/1',enabled=True,source_commit=commit,operation_id='fixture-project',
            origin=server.origin,gitlab_version='18.10.4-ee',namespace_id=10,namespace_path='state',path='tenant-a',actor_id=1,
            members=[dict(id=1,access_level=50)],scopes=[scope|{'phase':'domains'}],
            service_acceptance_ref='SYNTHETIC-GITLAB-NOT-QUALIFIED',recovery_ref='DISPOSABLE-FIXTURE')
        row=projects.payload(project)|dict(id=20,namespace=dict(id=10,kind='group',full_path='state'),creator_id=1,
            path_with_namespace='state/tenant-a',archived=False,marked_for_deletion_on=None,shared_with_groups=[],
            forked_from_project=None,import_status='none')
        member=dict(id=1,access_level=50,state='active',expires_at=None)
        bodies={'/api/v4/version':{'version':project['gitlab_version']},'/api/v4/user':{'id':1,'state':'active'},
                '/api/v4/projects/20':row,'/api/v4/projects/20/members/all?per_page=100&page=1':[member]}
        backend=compile_backend(server.origin,20,project['scopes'][0]); key=backend['state_key']
        state=dict(version=4,terraform_version='1.13.5',lineage='11111111-1111-4111-8111-111111111111',serial=7,
            outputs={'fixture':{'value':'Useful synthetic state data','type':'string','sensitive':True}},resources=[])
        path=urlsplit(backend['address']).path; bodies[path]=state; bodies[path+'/versions/7']=state
        server.routes={path:dict(status=200,body=value) for path,value in bodies.items()}
        observed=projects.project_observation(project,row,lambda method,path,body=None:bodies[path],20)
        receipt=dict(format='hosting-state-project-receipt/1',status='PRIVATE_STATE_PROJECT_OBSERVED_REQUIRES_COMMISSIONING',
            request_sha256=c.digest(project),project=observed,backends={key:backend},production_activation=False)
        request=dict(format='hosting-state-export/1',enabled=True,source_commit=commit,operation_id='fixture-export',
            project_request_sha256=c.digest(project),project_receipt_sha256=c.digest(receipt),reader_id=1,
            states=[dict(state_key=key,lineage=state['lineage'],minimum_serial=7)],consistency_ref='IMMUTABLE-SYNTHETIC-FIXTURE',
            protection_ref='DISPOSABLE-RESTIC-FIXTURE',output=str(base/'state-export'))
        token=b'disposable-state-reader'
        authority=dict(format='hosting-state-export-authority/1',request_sha256=c.digest(request),
            valid_from=(utcnow()-timedelta(minutes=1)).isoformat(),valid_until=(utcnow()+timedelta(minutes=10)).isoformat(),
            change_ref='DISPOSABLE-FIXTURE',token_sha256=digest(token),ca_sha256=digest(ca.read_bytes()))
        result=exports.capture(request,project,receipt,authority,token,ca_file=ca)
        require(all(item['method']=='GET' for item in server.requests),'State fixture received a write')
        return result,scope,len(server.requests)


def run(binary):
    source=verify(ROOT); require(source['status']=='HASHES_MATCH','Exact clean source required')
    with tempfile.TemporaryDirectory(prefix='hosting-state-protection-') as temporary:
        base=Path(temporary); exported,scope,reads=export_fixture(base,source['commit'])
        directory=Path(exported['export']); original={p.name:p.read_bytes() for p in directory.iterdir()}
        repository=base/'repository'; password='disposable-'+os.urandom(24).hex()
        env={'PATH':'/usr/bin:/bin','RESTIC_PASSWORD':password,'GOMAXPROCS':'2'}
        subprocess.run([str(binary),'--no-cache','--repo',str(repository),'init'],env=env,check=True,capture_output=True,timeout=45)
        native=json.loads(subprocess.check_output([str(binary),'--no-cache','--repo',str(repository),'cat','config'],env=env,timeout=20))
        config=dict(format='hosting-restic-export/1',scope=scope,member='state-project',machine_id='a'*32,
            source=str(directory),repository=str(repository),repository_id=native['id'],restic_sha256=sha_file(binary),
            valid_until=(utcnow()+timedelta(minutes=10)).isoformat(),consistency_ref='state-export:'+c.digest(exported),max_seconds=120)
        credentials=dict(password=password,username='fixture',http_password='fixture')
        capture=base/'capture'; capture.mkdir(mode=0o700)
        receipt,manifest=backup(config,Restic(binary,config,credentials,capture),capture,fixture=True)
        for path in directory.iterdir(): path.write_bytes(b'Changed after independent capture')
        recovery=base/'recovery'; recovery.mkdir(mode=0o700); target=base/'isolated-target'
        restored=restore(config,receipt,manifest,Restic(binary,config,credentials,recovery),recovery,target,fixture=True)
        actual=target/str(directory).lstrip('/')
        require({p.name:p.read_bytes() for p in actual.iterdir()}==original,'Restored state or index differs')
        return dict(status='PASSED_STATE_EXPORT_RESTIC_ENGINE_ONLY',source_commit=source['commit'],state_service_reads=reads,
            file_count=restored['file_count'],original_lineage_serial_and_index_recovered=True,source_changed_after_capture=True,
            state_service_written=False,live_gitlab_qualified=False,remote_append_only_service_tested=False,
            native_target_contacted=False,production_activation=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--execute',action='store_true')
    parser.add_argument('--restic',type=Path,default=shutil.which('restic')); args=parser.parse_args()
    if not args.execute: print('{"status":"NOT_RUN_USE_EXECUTE_FOR_DISPOSABLE_LAB"}'); return 0
    try:
        require(args.restic is not None,'Actual restic engine required'); report=run(args.restic.resolve()); code=0
    except Exception:
        report=dict(status='FAILED_STATE_EXPORT_RESTIC_ENGINE',native_target_contacted=False); code=2
        raise
    finally:
        if 'report' in locals():
            path=ROOT/'build/reports/state_protection_lab.json'; path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(encoded(report)); print(json.dumps(report,indent=2))
    return code


if __name__=='__main__': raise SystemExit(main())
