#!/usr/bin/env python3
"""Create one private GitLab state project, then observe exact retained identity.

Single POST with durable intent. Never writes Terraform state, grants membership,
changes existing projects, retries uncertain creation, or deletes anything.
"""
import argparse
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
if __package__ in (None,''): sys.path.insert(0,str(ROOT))
from tools import readback_core as c, execution_journal as journal
from provisioner.execution.source_integrity import verify
from tools.run_files import current_window,digest,encoded,load_private,private_path,read_private,require,utcnow,write_new
from tools.service_http import JsonService
from tools.state_backend import compile_backend

# One project is one accepted state credential boundary, with inherited group
# membership. Pipeline/repository execution and unrelated services stay disabled.
SETTINGS=dict(visibility='private',builds_access_level='disabled',repository_access_level='private',
    infrastructure_access_level='private',issues_access_level='disabled',merge_requests_access_level='disabled',
    wiki_access_level='disabled',snippets_access_level='disabled',forking_access_level='disabled',
    container_registry_access_level='disabled',package_registry_access_level='disabled',packages_enabled=False,
    shared_runners_enabled=False,group_runners_enabled=False,auto_devops_enabled=False,
    public_jobs=False,request_access_enabled=False,lfs_enabled=False)


def positive(value): require(type(value) is int and value>0,'Positive native identity required')


def validate(request):
    c.exact_keys(request,{'format','enabled','source_commit','operation_id','origin','gitlab_version',
        'namespace_id','namespace_path','path','actor_id','members','scopes','service_acceptance_ref','recovery_ref'})
    require(request['format']=='hosting-state-project/1' and type(request['enabled']) is bool,'Exact state project profile required')
    require(isinstance(request['source_commit'],str) and re.fullmatch('[0-9a-f]{40}',request['source_commit']),'Exact state owner source required')
    c.identifier(request['operation_id']); positive(request['namespace_id']); positive(request['actor_id'])
    for key in ('namespace_path','path'):
        require(isinstance(request[key],str) and len(request[key])<=255,'Exact GitLab path required')
        parts=request[key].split('/')
        require((key=='namespace_path' or len(parts)==1) and all(re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',v) for v in parts),
                'Canonical lower-case GitLab namespace/project path required')
    require(isinstance(request['gitlab_version'],str) and re.fullmatch(r'(18|19)\.[0-9]+\.[0-9]+(?:-ee)?',request['gitlab_version']),
            'Exact accepted GitLab REST v4 version required')
    version=tuple(map(int,request['gitlab_version'].split('-')[0].split('.')))
    require(version>=(18,5,0),'State project profile requires GitLab 18.5 or later supported major')
    members=request['members']
    require(isinstance(members,list) and 1<=len(members)<=1000,'Exact bounded inherited membership required')
    ids=[]
    for member in members:
        c.exact_keys(member,{'id','access_level'}); positive(member['id'])
        require(type(member['access_level']) is int and member['access_level'] in {10,20,30,40,50},'Standard accepted GitLab member role required')
        ids.append(member['id'])
    require(ids==sorted(set(ids)) and {'id':request['actor_id'],'access_level':50} in members,
            'Sorted unique membership including the namespace owner required')
    scopes=request['scopes']; require(isinstance(scopes,list) and 1<=len(scopes)<=100,'Explicit bounded state scopes required')
    keys=[]; boundary=None
    for scope in scopes:
        backend=compile_backend(request['origin'],1,scope); keys.append(backend['state_key'])
        current={k:scope[k] for k in ('environment_key','site_key','platform','tenant_key')}
        require(boundary is None or boundary==current,'A state project cannot mix tenant/site/environment credential boundaries')
        boundary=current
    require(keys==sorted(set(keys)),'State scopes must be sorted and unique')
    require(request['origin']==request['origin'].rstrip('/'),'Canonical GitLab origin required')
    for key in ('service_acceptance_ref','recovery_ref'): c.text(request[key])


def authorize(request,authority,action,token,ca):
    c.exact_keys(authority,{'format','request_sha256','action','valid_from','valid_until','change_ref','token_sha256','ca_sha256'})
    require(action in {'create','observe'} and authority['format']=='hosting-state-project-authority/1'
            and authority['request_sha256']==c.digest(request) and authority['action']==action,'Exact state project authority required')
    require(authority['token_sha256']==digest(token) and authority['ca_sha256']==(digest(ca) if ca else None),
            'State project credential or trust binding changed')
    current_window(authority); c.text(authority['change_ref'])


def payload(request):
    return SETTINGS|dict(name=request['path'],path=request['path'],namespace_id=request['namespace_id'],
        description='hosting-state-project:'+c.digest(request),initialize_with_readme=False)


def members(call,path):
    result={}
    # Offset pages are read only. Bound all pages and require a final short page;
    # never silently accept a truncated member set or follow server-supplied URLs.
    for page in range(1,12):
        rows=call('GET',path+f'/members/all?per_page=100&page={page}')
        require(isinstance(rows,list) and len(rows)<=100,'Unexpected GitLab membership page')
        for row in rows:
            positive(row['id'])
            require(row['id'] not in result and row.get('state')=='active' and row.get('member_role_id') is None,
                    'Duplicate, inactive or custom-role membership requires separate acceptance')
            require(row.get('expires_at') is None,'Expiring state membership requires a separately accepted handoff')
            result[row['id']]={'id':row['id'],'access_level':row['access_level']}
        require(len(result)<=1000,'GitLab membership exceeds accepted bound')
        if len(rows)<100: return [result[key] for key in sorted(result)]
    raise ValueError('GitLab membership did not terminate')


def group_observation(request,call):
    version=call('GET','/api/v4/version')
    require(version.get('version')==request['gitlab_version'],'GitLab installed version changed')
    actor=call('GET','/api/v4/user')
    # GitLab's non-admin /user representation can omit is_admin; an explicit
    # administrator response is never accepted as this namespace owner profile.
    require(actor.get('id')==request['actor_id'] and actor.get('state')=='active'
            and (actor.get('is_admin') is None or actor['is_admin'] is False),
            'Expected active non-administrator namespace owner required')
    path=f"/api/v4/groups/{request['namespace_id']}"
    group=call('GET',path+'?with_projects=false')
    require(group.get('id')==request['namespace_id'] and group.get('full_path')==request['namespace_path']
            and group.get('visibility')=='private' and group.get('shared_with_groups')==[],
            'State namespace identity, visibility or group sharing differs')
    require(members(call,path)==request['members'],'Namespace membership differs from accepted state custody')
    return {'id':group['id'],'full_path':group['full_path'],'version':version['version'],'actor_id':actor['id']}


def project_observation(request,row,call,expected_id=None):
    positive(row['id'])
    require(expected_id is None or row['id']==expected_id,'State project native identity changed')
    require(row.get('path_with_namespace')==request['namespace_path']+'/'+request['path']
            and row.get('namespace',{}).get('id')==request['namespace_id'] and row['namespace'].get('kind')=='group'
            and row.get('namespace',{}).get('full_path')==request['namespace_path']
            and row.get('creator_id')==request['actor_id'] and row.get('description')==payload(request)['description'],
            'State project identity or ownership marker differs')
    require(all(row.get(key)==value and type(row.get(key)) is type(value) for key,value in SETTINGS.items()),
            'State project restrictions differ')
    require(row.get('archived') is False and row.get('marked_for_deletion_on') is None
            and row.get('shared_with_groups')==[] and row.get('forked_from_project') is None
            and row.get('import_status')=='none','Unaccepted state project lifecycle or sharing')
    observed=members(call,f"/api/v4/projects/{row['id']}")
    require(observed==request['members'],'Project membership differs from accepted state custody')
    return dict(id=row['id'],path_with_namespace=row['path_with_namespace'],namespace_id=request['namespace_id'],
                description=row['description'],settings={key:row[key] for key in SETTINGS},members=observed)


def replay(log,request):
    started=False; project_id=None
    for event in log.events:
        data=event['data']
        if event['kind']=='CREATE_STARTED':
            require(not started and data=={'request':request,'payload':payload(request)},'State project creation identity changed')
            started=True
        elif event['kind']=='PROJECT_IDENTIFIED':
            c.exact_keys(data,{'id'}); positive(data['id'])
            require(started and project_id is None,'Invalid state project identity history'); project_id=data['id']
        elif event['kind']=='PROJECT_OBSERVED':
            require(started and project_id is not None and data['request_sha256']==c.digest(request)
                    and data['project']['id']==project_id,'Invalid state project observation history')
        else: raise ValueError('Unknown state project history')
    return started,project_id


def operate(request,authority,token,ledger,*,action='observe',ca_file=None,root=ROOT,client=None):
    validate(request); require(request['enabled'],'State project operation is disabled')
    ca=read_private(ca_file) if ca_file else None; authorize(request,authority,action,token,ca)
    source=verify(root)
    require(source['status']=='HASHES_MATCH' and source['commit']==request['source_commit'],'State project source changed')
    client=client or JsonService(request['origin'],'Bearer '+token.decode().strip(),ca_file)
    require(client.origin==request['origin'],'Wrong state service origin')
    def call(method,path,body=None,*,absent=False):
        authorize(request,authority,action,token,ca)
        require(method=='GET' or (action=='create' and method=='POST' and path=='/api/v4/projects'),
                'Unsupported state project write')
        remaining=(c.timestamp(authority['valid_until'])-utcnow()).total_seconds()
        try: return client.request(method,path,body,timeout=min(10,remaining))[0]
        except HTTPError as error:
            if absent and error.code==404: return None
            raise
    parent=private_path(ledger,directory=True)
    require(not parent.resolve().is_relative_to(root.resolve()),'Private state-owner ledger must be outside source')
    scope={'owner':'gitlab-state-project','origin':request['origin'],
           'namespace_path':request['namespace_path'],'path':request['path']}
    with journal.locked(parent,scope) as log:
        started,project_id=replay(log,request)
        require(started or action=='create','Observation cannot start state project creation')
        group=group_observation(request,call)
        path='/api/v4/projects/'+quote(request['namespace_path']+'/'+request['path'],safe='')
        if not started:
            require(call('GET',path,absent=True) is None,'Existing state project requires separate accepted adoption')
            authorize(request,authority,action,token,ca)
            log.append('CREATE_STARTED',{'request':request,'payload':payload(request)})
            row=call('POST','/api/v4/projects',payload(request))
            # Record the returned identity even if later settings/readback fail.
            positive(row['id']); project_id=row['id']; log.append('PROJECT_IDENTIFIED',{'id':project_id})
        else:
            require(action=='observe','Retained creation requires read-only observation; never repeat POST')
        row=call('GET',path,absent=True)
        require(row is not None,'Uncertain state project remains absent; preserve the creation hold')
        observed=project_observation(request,row,call,project_id)
        if project_id is None:
            project_id=observed['id']; log.append('PROJECT_IDENTIFIED',{'id':project_id})
        # Bracket membership observations with a second exact project/group read.
        second=project_observation(request,call('GET',f'/api/v4/projects/{project_id}'),call,project_id)
        require(second==observed and group_observation(request,call)==group,'State project changed during observation')
        authorize(request,authority,action,token,ca)
        result={'format':'hosting-state-project-receipt/1','status':'PRIVATE_STATE_PROJECT_OBSERVED_REQUIRES_COMMISSIONING',
            'request_sha256':c.digest(request),'observed_at':utcnow().isoformat(),'group':group,'project':observed,
            'backends':{compile_backend(request['origin'],project_id,s)['state_key']:compile_backend(request['origin'],project_id,s) for s in request['scopes']},
            'state_written':False,'locking_qualified':False,'service_recovery_qualified':False,'production_activation':False}
        log.append('PROJECT_OBSERVED',result)
        write_new(log.directory/('receipt-'+digest(encoded(result))+'.receipt'),encoded(result))
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--action',choices=['create','observe'],default='observe')
    for name in ('authority','token-file','ca-file','ledger'): parser.add_argument('--'+name,type=Path)
    parser.add_argument('--execute',action='store_true'); args=parser.parse_args()
    try:
        request=load_private(args.request); validate(request)
        if not args.execute: print('{"status":"VALIDATED_NO_STATE_SERVICE_CONTACT"}'); return 0
        require(all((args.authority,args.token_file,args.ledger)),'Exact state project execution inputs required')
        result=operate(request,load_private(args.authority),read_private(args.token_file),args.ledger,action=args.action,ca_file=args.ca_file)
        print(json.dumps({'status':result['status'],'request_sha256':result['request_sha256']})); return 0
    except Exception:
        print('{"status":"STATE_PROJECT_HELD","reason":"Retain native identity and creation journal; never retry uncertain project creation or replace state"}')
        return 2


if __name__=='__main__': raise SystemExit(main())
