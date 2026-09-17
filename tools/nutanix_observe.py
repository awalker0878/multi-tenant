#!/usr/bin/env python3
"""Exact VPC/subnet readback and single asynchronous task observation, Nutanix v4.3.

Wire profile from published networking/prism Go SDK v4.3.1. No API negotiation,
legacy fallback, task cancellation, response-link following, or inferred task IDs.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
from urllib.parse import quote
if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import readback_core as c

PROFILE='nutanix-networking-prism-v4.3'
TASK_ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_=:+.-]{0,191}$')
TYPES={'vpc':'networking.v4.config.Vpc','subnet':'networking.v4.config.Subnet'}
FIELDS={
 'vpc':{'name','tenantId','vpcType','externalSubnets','externallyRoutablePrefixes','externalRoutingDomainReference','commonDhcpOptions','snatIps'},
 'subnet':{'name','tenantId','subnetType','vpcReference','clusterReference','isExternal','isNatEnabled','ipConfig','dhcpOptions','networkId','virtualSwitchReference','externalDhcpServers'},
}
REQUIRED={
 'vpc':{'name','tenantId','vpcType','externalSubnets','externallyRoutablePrefixes'},
 'subnet':{'name','tenantId','subnetType','vpcReference','isExternal','ipConfig'},
}
BASE={'extId','$objectType'}


def validate(m):
    c.common_manifest(m,'nutanix')
    if m['profile']!=PROFILE or 'task' not in m:
        raise ValueError('This profile requires a known single task and v4.3 endpoints')
    ids=set()
    for r in m['resources']:
        c.exact_keys(r,{'kind','ext_id','expected','expected_etag'})
        if r['kind'] not in TYPES or not isinstance(r['ext_id'],str) or not c.UUID.fullmatch(r['ext_id']):
            raise ValueError('Supported exact resource UUID required')
        if r['ext_id'] in ids:raise ValueError('Duplicate resource')
        ids.add(r['ext_id'])
        e=r['expected'];kind=r['kind']
        c.exact_keys(e,BASE|REQUIRED[kind],FIELDS[kind]-REQUIRED[kind])
        if e['extId']!=r['ext_id'] or e['$objectType']!=TYPES[kind]:
            raise ValueError('Expected identity conflicts with selector')
        if not isinstance(e['tenantId'],str) or not c.UUID.fullmatch(e['tenantId']):
            raise ValueError('Native tenant identity required; not the portable tenant label')
        c.text(e['name'],'expected native name',256)
        for flag in ('isExternal','isNatEnabled'):
            if flag in e and type(e[flag]) is not bool:
                raise ValueError('Boolean subnet setting required')
        for key in ('externalSubnets','externallyRoutablePrefixes','ipConfig'):
            if key in e and not isinstance(e[key],list):
                raise ValueError('Explicit expected collection required')
        c.text(r['expected_etag'],'accepted strong ETag',512)
        if not re.fullmatch(r'"[\x21\x23-\x7e]+"',r['expected_etag']):
            raise ValueError('An exact accepted strong ETag is required')
    task=m['task']
    c.exact_keys(task,{'ext_id','operation','created_after','entity_ids'})
    if not isinstance(task['ext_id'],str) or not TASK_ID.fullmatch(task['ext_id']) or '..' in task['ext_id']:
        raise ValueError('Exact recorded task ID required; not a URL')
    c.text(task['operation'],'expected native operation',128)
    c.timestamp(task['created_after'])
    if not isinstance(task['entity_ids'],list) or any(not isinstance(i,str) for i in task['entity_ids']) or set(task['entity_ids'])!=ids or len(task['entity_ids'])!=len(ids):
        raise ValueError('This bounded task must affect exactly the enumerated resources')


def resource_target(r):
    return '/api/networking/v4.3/config/'+('vpcs' if r['kind']=='vpc' else 'subnets')+'/'+r['ext_id']


def task_target(m):
    return '/api/prism/v4.3/config/tasks/'+quote(m['task']['ext_id'],safe='')


def targets(m):
    validate(m)
    return {task_target(m)}|{resource_target(r) for r in m['resources']}


def task_progress(body,m):
    task=body.get('data')
    if not isinstance(task,dict):
        return 'UNKNOWN','TASK_BODY_MISSING',None
    if task.get('$objectType')!='prism.v4.config.Task' or task.get('extId')!=m['task']['ext_id'] or task.get('operation')!=m['task']['operation']:
        return 'UNKNOWN','TASK_IDENTITY_OR_OPERATION_MISMATCH',None
    try:
        created=c.timestamp(task.get('createdTime'))
        if created<c.timestamp(m['task']['created_after']) or created>datetime.now(timezone.utc):
            return 'UNKNOWN','TASK_TIME_OUTSIDE_OPERATION',None
    except (ValueError,TypeError):
        return 'UNKNOWN','TASK_TIME_MISSING',None
    if type(task.get('numberOfSubtasks')) is not int or task['numberOfSubtasks']!=0 or task.get('subTasks') or task.get('batchSummary'):
        return 'UNKNOWN','COMPOSITE_TASK_NOT_SUPPORTED',None
    entities=task.get('entitiesAffected');count=task.get('numberOfEntitiesAffected')
    if not isinstance(entities,list) or type(count) is not int or count!=len(entities):
        return 'UNKNOWN','TASK_ENTITY_COVERAGE_INCOMPLETE',None
    ids=[e.get('extId') if isinstance(e,dict) else None for e in entities]
    if any(not isinstance(e,str) for e in ids) or len(ids)!=len(set(ids)) or set(ids)!=set(m['task']['entity_ids']):
        return 'UNKNOWN','TASK_ENTITY_SCOPE_MISMATCH',None
    state=task.get('status')
    observation={'ext_id':task['extId'],'operation':task['operation'],'status':state,
                 'created_at':task['createdTime'],'entities':sorted(ids)}
    if state in ('QUEUED','RUNNING','CANCELING'):
        return 'PENDING','TASK_'+state,c.digest(observation)
    if state in ('FAILED','CANCELED'):
        return 'FAILED','TASK_'+state,c.digest(observation)
    if state!='SUCCEEDED':
        return 'UNKNOWN','TASK_STATUS_NOT_TERMINAL_SUCCESS',None
    try:
        complete=c.timestamp(task.get('completedTime'))
        if complete<created or complete>datetime.now(timezone.utc):
            return 'UNKNOWN','TASK_COMPLETION_TIME_INVALID',None
    except (ValueError,TypeError):
        return 'UNKNOWN','TASK_COMPLETION_TIME_MISSING',None
    if task.get('errorMessages') or task.get('legacyErrorMessage') or task.get('warnings'):
        return 'UNKNOWN','TASK_DIAGNOSTICS_REQUIRE_REVIEW',None
    observation['completed_at']=task['completedTime']
    return 'COMPLETE','TASK_SUCCESS_REPORTED',c.digest(observation)


def sample(m,client):
    before,_=client.get(task_target(m));bp,br,bd=task_progress(before,m)
    result=[]
    for r in m['resources']:
        body,etag=client.get(resource_target(r));data=body.get('data')
        if not isinstance(data,dict):
            raise c.ObservationError('NATIVE_RESOURCE_BODY_MISSING')
        actual={k:data[k] for k in r['expected'] if k in data}
        mismatch=c.differences(actual,r['expected'])
        identity=not c.differences(actual,{k:r['expected'][k] for k in ('extId','$objectType','tenantId')})
        config='UNKNOWN' if any(x.endswith(':missing') for x in mismatch) else ('DIFFERENT' if mismatch else 'MATCH')
        if etag is None:
            config='UNKNOWN';mismatch.append('/ETag:missing')
        elif etag!=r['expected_etag']:
            if config!='UNKNOWN':config='DIFFERENT'
            mismatch.append('/ETag:value')
        if not identity:config='UNKNOWN'
        result.append({'resource_key':r['ext_id'],'identity_match':identity,'config_status':config,
            'mismatch_fields':mismatch,'config_sha256':c.digest(actual),'etag_sha256':c.digest(etag)})
    after,_=client.get(task_target(m));ap,ar,ad=task_progress(after,m)
    # A changing task sample cannot count toward the consecutive completion threshold.
    p,reason,td=(ap,ar,ad) if (bp,br,bd)==(ap,ar,ad) else ('PENDING','TASK_CHANGED_DURING_READBACK',ad)
    if bp=='UNKNOWN' or ap=='UNKNOWN':p='UNKNOWN';reason=br if bp=='UNKNOWN' else ar
    for item in result:
        item.update({'progress':p,'reason':reason,'task_sha256':td})
    return result


def main():
    from tools.readback_cli import run
    return run(sys.modules[__name__],'NUTANIX')
if __name__=='__main__':raise SystemExit(main())
