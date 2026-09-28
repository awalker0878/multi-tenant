#!/usr/bin/env python3
"""Read exact GitLab state lineages into a private export for independent backup.

No state upload, lock, unlock, delete or rollback. Partial reads are retained;
recovery may collect new reads, and completed reuse verifies historical bytes.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.parse import urlsplit
import uuid

ROOT=Path(__file__).resolve().parents[1]
if __package__ in (None,''): sys.path.insert(0,str(ROOT))
from provisioner.repository import asset_path
from tools import readback_core as c,state_project as projects
from tools.check_release import verify
from tools.run_files import (current_window,digest,encoded,file_map,load_private,new_directory,private_path,
    read_private,require,sync_directory,utcnow,write_new)
from tools.service_http import JsonService
from tools.state_backend import compile_backend


def validate(request,project,receipt):
    projects.validate(project)
    c.exact_keys(request,{'format','enabled','source_commit','operation_id','project_request_sha256',
        'project_receipt_sha256','reader_id','states','consistency_ref','protection_ref','output'})
    require(request['format']=='hosting-state-export/1' and type(request['enabled']) is bool,'Exact state export profile required')
    require(isinstance(request['source_commit'],str) and re.fullmatch('[0-9a-f]{40}',request['source_commit']),'Exact export source required')
    c.identifier(request['operation_id']); projects.positive(request['reader_id'])
    require(any(m['id']==request['reader_id'] and m['access_level']>=30 for m in project['members']),
            'Accepted state reader must belong to the original custody boundary')
    require(request['project_request_sha256']==c.digest(project) and request['project_receipt_sha256']==c.digest(receipt),
            'Exact original state project handoff required')
    require(receipt.get('format')=='hosting-state-project-receipt/1' and receipt.get('request_sha256')==c.digest(project)
            and receipt.get('status')=='PRIVATE_STATE_PROJECT_OBSERVED_REQUIRES_COMMISSIONING'
            and receipt.get('production_activation') is False,'Unexpected project receipt')
    identifier=receipt['project']['id']; projects.positive(identifier)
    backends={compile_backend(project['origin'],identifier,s)['state_key']:compile_backend(project['origin'],identifier,s) for s in project['scopes']}
    require(receipt['backends']==backends,'Project backend handoff differs')
    states=request['states']; require(isinstance(states,list) and len(states)==len(backends),'Every accepted project state slot must be explicit')
    names=[]
    for state in states:
        c.exact_keys(state,{'state_key','lineage','minimum_serial'}); names.append(state['state_key'])
        if state['lineage'] is None: require(state['minimum_serial'] is None,'Unused state must explicitly lack a lineage and serial')
        else:
            require(isinstance(state['lineage'],str) and str(uuid.UUID(state['lineage']))==state['lineage'],'Canonical accepted state lineage required')
            require(type(state['minimum_serial']) is int and state['minimum_serial']>=0,'Accepted minimum state serial required')
    require(names==sorted(backends),'State slots must be complete, sorted and unique')
    for name in ('consistency_ref','protection_ref'): c.text(request[name])
    require(isinstance(request['output'],str) and Path(request['output']).is_absolute(),'Absolute private state export destination required')
    return backends


def authorize(request,authority,token,ca):
    c.exact_keys(authority,{'format','request_sha256','valid_from','valid_until','change_ref','token_sha256','ca_sha256'})
    require(authority['format']=='hosting-state-export-authority/1' and authority['request_sha256']==c.digest(request),
            'Exact read-only state export authority required')
    require(authority['token_sha256']==digest(token) and authority['ca_sha256']==(digest(ca) if ca else None),
            'State export credential or trust binding changed')
    c.text(authority['change_ref']); current_window(authority)


def state_identity(value,expected,version):
    require(isinstance(value,dict) and value.get('version')==4 and type(value.get('version')) is int
            and value.get('terraform_version')==version and value.get('lineage')==expected['lineage'],
            'State format, Terraform version or lineage changed')
    serial=value.get('serial')
    require(type(serial) is int and serial>=expected['minimum_serial'],'State serial regressed or is unknown')
    require(isinstance(value.get('outputs'),dict) and isinstance(value.get('resources'),list),'Incomplete Terraform state')
    return serial


def retained(output,request,project,receipt):
    require(load_private(output/'intent.json')=={'request':request,'project':project,'receipt':receipt},'Export operation identity changed')
    result=load_private(output/'receipt.json')
    require(result.get('format')=='hosting-state-export-receipt/1' and result.get('request_sha256')==c.digest(request)
            and result.get('status')=='STATE_EXPORT_OBSERVED_REQUIRES_PROTECTION','State export completion differs')
    actual=file_map(output); actual.pop('receipt.json'); actual.pop('writer.lock')
    require(actual==result['files'],'Retained state export bytes changed')
    for name in actual: private_path(output/name)
    return result


def capture(request,project,receipt,authority,token,*,ca_file=None,client=None,root=ROOT):
    backends=validate(request,project,receipt); require(request['enabled'],'State export is disabled')
    ca=read_private(ca_file) if ca_file else None; authorize(request,authority,token,ca)
    source=verify(root)
    require(source['status']=='HASHES_MATCH' and source['commit']==request['source_commit'],'Export source changed')
    output=Path(request['output']); require(not output.resolve().is_relative_to(root.resolve()),'State exports must stay outside source')
    if not output.exists(): new_directory(output,root)
    private_path(output,directory=True)
    fd=os.open(output/'writer.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        private_path(output/'writer.lock'); fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        intent={'request':request,'project':project,'receipt':receipt}
        if (output/'intent.json').exists(): require(load_private(output/'intent.json')==intent,'Export operation identity changed')
        else:
            require(set(p.name for p in output.iterdir())=={'writer.lock'},'Unmanaged export destination')
            write_new(output/'intent.json',encoded(intent))
        if (output/'receipt.json').exists(): return retained(output,request,project,receipt)
        attempts=output/'attempts'
        if not attempts.exists(): attempts.mkdir(mode=0o700); sync_directory(output)
        private_path(attempts,directory=True)
        previous=sorted(attempts.iterdir())
        require([p.name for p in previous]==[f'{n:04d}' for n in range(1,len(previous)+1)] and len(previous)<32,
                'Export attempt history is unknown or exhausted')
        for path in previous: private_path(path,directory=True)
        attempt=attempts/f'{len(previous)+1:04d}'; attempt.mkdir(mode=0o700); sync_directory(attempts)
        write_new(attempt/'authority.json',encoded(authority))
        export=attempt/'export'; export.mkdir(mode=0o700); sync_directory(attempt)
        client=client or JsonService(project['origin'],'Bearer '+token.decode().strip(),ca_file)
        require(client.origin==project['origin'],'Wrong state export origin')
        def get(path,*,absent=False):
            authorize(request,authority,token,ca)
            remaining=(c.timestamp(authority['valid_until'])-utcnow()).total_seconds()
            try: return client.request('GET',path,timeout=min(10,remaining))[0]
            except HTTPError as error:
                if absent and error.code==404: return None
                raise
        def call(method,path,body=None):
            require(method=='GET' and body is None,'State export cannot mutate the service'); return get(path)
        identifier=receipt['project']['id']; project_path=f'/api/v4/projects/{identifier}'
        def observe_project():
            require(get('/api/v4/version').get('version')==project['gitlab_version'],'GitLab installed version changed')
            actor=get('/api/v4/user')
            require(actor.get('id')==request['reader_id'] and actor.get('state')=='active','Wrong state export reader')
            return projects.project_observation(project,get(project_path),call,identifier)
        before=observe_project()
        require(before==receipt['project'],'Project identity, restrictions or custody changed since acceptance')
        toolchain = asset_path('config/toolchain.json') if root == ROOT else root/'config/toolchain.json'
        version=json.loads(toolchain.read_text(encoding='utf-8'))['terraform']
        states=[]
        for expected in request['states']:
            key=expected['state_key']; path=urlsplit(backends[key]['address']).path
            value=get(path,absent=True)
            if expected['lineage'] is None:
                require(value is None,'An explicitly unused state slot now contains state')
                states.append({'state_key':key,'status':'UNUSED_ABSENCE_OBSERVED','file':None,'serial':None,'lineage':None})
                continue
            require(value is not None,'Required state is missing')
            serial=state_identity(value,expected,version)
            versioned=get(path+f'/versions/{serial}')
            require(value==versioned,'Latest state and retained GitLab version differ')
            name=digest(key.encode())+'.tfstate'; write_new(export/name,encoded(value))
            states.append({'state_key':key,'status':'VERSION_EXPORTED','file':name,'serial':serial,'lineage':expected['lineage']})
        # A second complete sweep catches observed changes without acquiring or
        # claiming a native writer fence. These finite reads are not a transaction.
        for result in states:
            path=urlsplit(backends[result['state_key']]['address']).path; value=get(path,absent=True)
            if result['file'] is None: require(value is None,'Unused state changed during export')
            else: require(value==load_private(export/result['file']),'State changed during export')
        require(observe_project()==before,'State project changed during export')
        authorize(request,authority,token,ca)
        write_new(export/'index.json',encoded({'format':'hosting-state-export-index/1','request_sha256':c.digest(request),
            'project_id':identifier,'states':states,'observed_at':utcnow().isoformat()}))
        files=file_map(output); files.pop('writer.lock')
        for name in files: private_path(output/name)
        result={'format':'hosting-state-export-receipt/1','status':'STATE_EXPORT_OBSERVED_REQUIRES_PROTECTION',
            'request_sha256':c.digest(request),'project_id':identifier,'observed_at':utcnow().isoformat(),
            'export':str(export),'states':states,'files':files,'state_written':False,'native_fencing':False,
            'cross_state_atomicity':False,'independent_backup_verified':False,'production_activation':False}
        write_new(output/'receipt.json',encoded(result)); return retained(output,request,project,receipt)
    finally: os.close(fd)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('request','project-request','project-receipt'): parser.add_argument('--'+name,type=Path,required=True)
    for name in ('authority','token-file','ca-file'): parser.add_argument('--'+name,type=Path)
    parser.add_argument('--execute',action='store_true'); args=parser.parse_args()
    try:
        request,project,receipt=(load_private(path) for path in (args.request,args.project_request,args.project_receipt))
        validate(request,project,receipt)
        if not args.execute: print('{"status":"VALIDATED_NO_STATE_SERVICE_CONTACT"}'); return 0
        require(args.authority is not None and args.token_file is not None,'Exact state export execution authority required')
        result=capture(request,project,receipt,load_private(args.authority),read_private(args.token_file),ca_file=args.ca_file)
        print(json.dumps({'status':result['status'],'request_sha256':result['request_sha256']})); return 0
    except Exception:
        print('{"status":"STATE_EXPORT_HELD","reason":"Preserve private capture attempts; reconcile actual state and custody without uploading or rolling back state"}')
        return 2


if __name__=='__main__': raise SystemExit(main())
