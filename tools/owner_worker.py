#!/usr/bin/env python3
"""Forced-command worker for exact, privately staged edge and restic jobs."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
if __package__ in (None,''): sys.path.insert(0,str(ROOT))
from tools import delivery_run as delivery, readback_core as c
from tools.run_files import (current_window,digest,encoded,load_private,private_path,read_private,
                             require,sync_directory,write_new)

KINDS={'edge_policy','restic','edge_containment'}
MAX_RESULT=8*1024*1024
COMMAND='hosting-owner/1'


def validate(job):
    c.exact_keys(job,{'format','job_id','machine_id','source_commit','scope','generation','kind',
        'parameters','files','delivery','valid_from','valid_until','dispatch_ref'})
    require(job['format']=='hosting-owner-job/1' and job['kind'] in KINDS,'Unsupported remote owner job')
    require(isinstance(job['job_id'],str) and re.fullmatch(r'[a-z][a-z0-9-]{1,63}',job['job_id']),
            'Simple owner job identity required')
    require(isinstance(job['machine_id'],str) and re.fullmatch('[0-9a-f]{32}',job['machine_id']),
            'Exact owner machine identity required')
    c.text(job['dispatch_ref']); c.exact_keys(job['delivery'],{'plan_sha256','step_id','dependencies'})
    require(re.fullmatch('[0-9a-f]{64}',job['delivery']['plan_sha256']),'Exact coordinator plan binding required')
    c.identifier(job['delivery']['step_id'])
    require(isinstance(job['delivery']['dependencies'],dict),'Exact predecessor binding required')
    for key,value in job['delivery']['dependencies'].items():
        c.identifier(key); require(re.fullmatch('[0-9a-f]{64}',value),'Exact predecessor receipt required')
    plan={'format':'hosting-delivery/2','source_commit':job['source_commit'],'scope':job['scope'],
          'operation_id':job['job_id'],'generation':job['generation'],
          'reviewed_plan_digest':job['delivery']['plan_sha256'],
          'steps':[{'id':'owner','kind':job['kind'],'needs':[]}],
          'operation_bindings':{'owner':'owner'},
          'reviewed_parameters':{'owner':dict(job['parameters'])},
          'compiled_catalog_ids':{}}
    delivery.validate(plan)
    from tools.delivery_steps import KINDS as schemas
    params,required,optional=schemas[job['kind']]
    c.exact_keys(job['parameters'],params); c.exact_keys(job['files'],required,optional)
    for item in job['files'].values():
        c.exact_keys(item,{'path','sha256'})
        require(isinstance(item['path'],str) and Path(item['path']).is_absolute()
                and re.fullmatch('[0-9a-f]{64}',item['sha256']),'Exact remote private input binding required')
    # Check shape/window duration separately from freshness: historical receipt
    # retrieval never renews or implies current execution authority.
    current_window(job,c.timestamp(job['valid_from']))
    return plan


def exports(job):
    if job['kind']=='edge_containment': return {'containment.json'}
    if job['kind']=='edge_policy': return {'result.json'}
    require(job['parameters']['action'] in {'backup','restore'},'Unknown remote backup action')
    return {'receipt.json','context.json'} | ({'manifest.json'} if job['parameters']['action']=='backup' else set())


def check_result(value,job):
    c.exact_keys(value,{'format','job_id','job_sha256','machine_id','source_commit','status','owner_status',
                       'artifacts','native_acceptance','production_activation'})
    require(value['format']=='hosting-owner-result/1' and value['job_id']==job['job_id']
            and value['job_sha256']==c.digest(job) and value['machine_id']==job['machine_id']
            and value['source_commit']==job['source_commit'] and value['status']=='OWNER_COMPLETED_REQUIRES_ACCEPTANCE'
            and value['native_acceptance'] is False and value['production_activation'] is False,
            'Remote owner response identity differs')
    require(set(value['artifacts'])==exports(job),'Remote owner artifact set differs')
    decoded={}
    for name,artifact in value['artifacts'].items():
        c.exact_keys(artifact,{'sha256','base64'})
        raw=base64.b64decode(artifact['base64'],validate=True)
        require(digest(raw)==artifact['sha256'],'Remote owner artifact digest differs')
        decoded[name]=raw
    receipt=c.strict_loads(decoded[{'edge_policy':'result.json','edge_containment':'containment.json','restic':'receipt.json'}[job['kind']]])
    require(receipt['status']==value['owner_status'],'Remote owner status differs from its receipt')
    allowed={'edge_policy':{'APPLIED_EXPIRING_POLICY_NOT_QUALIFIED'},'edge_containment':{'CONTAINED_OBSERVED_NOT_QUALIFIED'},
             'restic':{'CAPTURED_REQUIRES_RESTORE_TEST'} if job['parameters'].get('action')=='backup'
                      else {'RESTORED_FILE_BYTES_VERIFIED_NOT_APPLICATION_ACCEPTED'}}
    require(value['owner_status'] in allowed[job['kind']],'Remote native outcome remains held')
    return decoded


def response(job,status,directory):
    artifacts={}
    for name in sorted(exports(job)):
        raw=read_private(directory/name)
        artifacts[name]={'sha256':digest(raw),'base64':base64.b64encode(raw).decode('ascii')}
    value={'format':'hosting-owner-result/1','job_id':job['job_id'],'job_sha256':c.digest(job),
        'machine_id':job['machine_id'],'source_commit':job['source_commit'],'status':'OWNER_COMPLETED_REQUIRES_ACCEPTANCE',
        'owner_status':status,'artifacts':artifacts,'native_acceptance':False,'production_activation':False}
    check_result(value,job); require(len(encoded(value))<=MAX_RESULT,'Owner result exceeds transport budget')
    return value


def serve(request,spool,ledger,*,root=ROOT):
    c.exact_keys(request,{'format','action','job_id','job_sha256'})
    require(request['format']=='hosting-owner-request/1' and request['action'] in {'execute','observe'}
            and isinstance(request['job_id'],str) and re.fullmatch(r'[a-z][a-z0-9-]{1,63}',request['job_id'])
            and re.fullmatch('[0-9a-f]{64}',request['job_sha256']),'Invalid owner request')
    spool=private_path(spool,directory=True); ledger=private_path(ledger,directory=True)
    job=load_private(spool/(request['job_id']+'.json')); plan=validate(job)
    require(c.digest(job)==request['job_sha256'],'Staged owner job differs from request')
    require(Path('/etc/machine-id').read_text().strip()==job['machine_id'],'Owner machine identity changed')
    source=delivery.verify(root)
    require(source['status']=='HASHES_MATCH' and source['commit']==job['source_commit'],'Exact clean owner source required')
    inbox=spool/c.digest(job)
    if not inbox.exists(): inbox.mkdir(mode=0o700); sync_directory(spool)
    private_path(inbox,directory=True)
    if job['kind']=='edge_containment':
        # Incident authority outranks a held forward delivery. The native edge
        # ledger remains shared, and only this withdrawal-only owner takes this path.
        from tools.delivery_steps import file_paths,native_owner_ledger
        from tools.edge_contain import execute
        if request['action']=='execute': current_window(job)
        files=file_paths(job); values=job['parameters']
        spec=load_private(files['spec']); require(spec['scope']==job['scope'],'Foreign incident boundary')
        require(spec['nft_sha256']==values['nft_sha256'],'Incident executable binding differs')
        directory=inbox/('incident-'+uuid.uuid4().hex)
        result=execute(spec,load_private(files['authority']),values['nft'],native_owner_ledger(ledger,'edge_policy'),
                       directory,observe_only=request['action']=='observe')
        value=response(job,result['status'],directory)
        write_new(directory/'response.json',encoded(value)); return value
    result_path=inbox/'result.json'
    if result_path.exists():
        value=load_private(result_path); check_result(value,job); return value
    if request['action']=='execute': current_window(job)
    packet={'format':'hosting-delivery-step/1','plan_sha256':c.digest(plan),'step_id':'owner','dependencies':{},
            'parameters':job['parameters'],'files':job['files']}
    packet_path=inbox/'owner.json'
    if packet_path.exists(): require(load_private(packet_path)==packet,'Staged owner execution packet changed')
    else: write_new(packet_path,encoded(packet))
    delivery.run(plan,inbox,ledger,execute=True,root=root,resume_only=request['action']=='observe')
    scope={'owner':'delivery',**plan['scope']}
    directory=ledger/digest(encoded(scope))/'runs'/c.digest(plan)/'steps/owner'
    completion=load_private(directory/'owner-completion.json')
    for name in sorted(exports(job)):
        raw=read_private(directory/name)
        require(digest(raw)==completion['artifacts'][name],'Owner receipt changed before transmission')
    value=response(job,completion['status'],directory)
    write_new(result_path,encoded(value))
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spool',type=Path,required=True); parser.add_argument('--ledger',type=Path,required=True)
    args=parser.parse_args()
    try:
        require(os.environ.get('SSH_ORIGINAL_COMMAND')==COMMAND,'Only the installed forced command is accepted')
        raw=sys.stdin.buffer.read(4097); require(len(raw)<=4096,'Owner request too large')
        result=serve(c.strict_loads(raw),args.spool,args.ledger)
        print(json.dumps(result)); return 0
    except Exception:
        print('{"status":"HOLD_OWNER_RECONCILIATION","native_acceptance":false,"production_activation":false}')
        return 2


if __name__=='__main__': raise SystemExit(main())
