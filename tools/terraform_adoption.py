#!/usr/bin/env python3
"""Prepare and execute explicit Terraform brownfield state adoption with durable holds."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
if __package__ in (None,''):
    sys.path.insert(0,str(ROOT))

from tools import adoption, readback_core as c
from tools.check_release import verify
from tools.plan_review import review as review_plan
from tools.run_files import (current_window,digest,encoded,file_map,load_private,new_directory,
                             private_path,read_private,replace_private,require,sync_directory,
                             utcnow,write_new,OperatorError)
from tools.terraform_run import (authorized_command,backend_settings,cloud_config,process_environment,
                                 runtime_environment,select_scope,snapshot)

CONTACT_FIELDS={
    'format','source_commit','scope','operation_id','generation','input_sha256','backend_sha256',
    'environment_sha256','cloud_sha256','ca_sha256','adoption_review_sha256',
    'valid_from','valid_until','change_ref',
}
APPROVAL_FIELDS={
    'format','bundle_sha256','adoption_review_sha256','pre_plan_sha256','pre_review_sha256',
    'operation_id','generation','valid_from','valid_until','change_ref',
}
START_FIELDS={'format','status','bundle_sha256','scope','operation_id','generation','change_ref','started_at'}


def base_scope(scope):
    return {k:v for k,v in scope.items() if k!='phase'}


def contact_authority(authority,source,scope,operation_id,generation,input_bytes,backend_bytes,
                      environment_bytes,cloud_bytes,ca_bytes,adoption_review):
    c.exact_keys(authority,CONTACT_FIELDS)
    require(authority['format']=='hosting-terraform-adoption-contact/1'
            and authority['source_commit']==source and authority['scope']==scope
            and authority['operation_id']==operation_id and authority['generation']==generation,
            'Adoption contact authority scope or operation differs')
    bindings={
        'input_sha256':digest(input_bytes),'backend_sha256':digest(backend_bytes),
        'environment_sha256':digest(environment_bytes),
        'cloud_sha256':digest(cloud_bytes) if cloud_bytes is not None else None,
        'ca_sha256':digest(ca_bytes) if ca_bytes is not None else None,
        'adoption_review_sha256':c.digest(adoption_review),
    }
    require(all(authority[k]==v for k,v in bindings.items()),'Adoption contact authority artifacts differ')
    c.text(authority['change_ref'])
    current_window(authority)


def imports_by_address(adoption_review):
    require(adoption_review['status']=='ADOPTION_READY_FOR_EXPLICIT_IMPORT_AND_PLAN_REVIEW',
            'Adoption ownership review is not ready')
    rows={}
    for row in adoption_review['imports']:
        require(row['address'] not in rows,'Duplicate adoption import address')
        rows[row['address']]=row
    require(rows,'At least one explicit Terraform import is required')
    return rows


def validate_plan_common(plan):
    require(plan.get('format_version')=='1.2' and plan.get('complete') is True
            and not plan.get('errored') and not plan.get('deferred_changes')
            and not plan.get('resource_drift'),'Complete drift-free Terraform plan required')
    require(all(isinstance(check,dict) and check.get('status')=='pass'
                for check in plan.get('checks',[])),'Terraform checks must pass')
    changes=plan.get('resource_changes')
    require(isinstance(changes,list),'Terraform resource changes required')
    return changes


def validate_pre_plan(plan,adoption_review):
    """Before import, exact handover addresses must be creates and everything else a no-op."""
    wanted=imports_by_address(adoption_review)
    seen=set()
    for item in validate_plan_common(plan):
        require(isinstance(item,dict),'Malformed Terraform resource change')
        if item.get('mode')=='data':
            continue
        require(item.get('mode')=='managed' and isinstance(item.get('address'),str)
                and isinstance(item.get('change'),dict),'Unsupported pre-import resource')
        address=item['address']; change=item['change']; actions=change.get('actions')
        require(not item.get('previous_address') and not item.get('deposed')
                and not change.get('importing'),'Moved/deposed/importing plan is not a pre-import baseline')
        if address in wanted:
            expected=wanted[address]
            require(address not in seen and item.get('type')==expected['type']
                    and actions==['create'],'Import target is not an exact absent configured resource')
            after=change.get('after')
            require(isinstance(after,dict) and c.digest(after)==expected['desired_sha256'],
                    'Import target desired configuration differs from adoption review')
            seen.add(address)
        else:
            require(actions==['no-op'],'Unrelated managed change must be no-op before adoption')
    require(seen==set(wanted),'Pre-import plan does not cover every explicit import')
    return sorted(seen)


def changed_fields(change):
    before,after=change.get('before'),change.get('after')
    require(isinstance(before,dict) and isinstance(after,dict),'Post-import before/after configuration required')
    return {key for key in set(before)|set(after) if c.digest(before.get(key))!=c.digest(after.get(key))}


def validate_post_plan(plan,adoption_review):
    """After import there may be only reviewed no-ops or bounded explicit updates."""
    wanted=imports_by_address(adoption_review)
    allowed={row['address']:row for row in adoption_review['explicit_deltas']}
    seen=set()
    for item in validate_plan_common(plan):
        if item.get('mode')=='data':
            continue
        require(item.get('mode')=='managed' and isinstance(item.get('address'),str)
                and isinstance(item.get('change'),dict),'Unsupported post-import resource')
        address=item['address']; change=item['change']; actions=change.get('actions')
        require(not item.get('previous_address') and not item.get('deposed')
                and not change.get('importing'),'Post-import ownership is not stable')
        if address in wanted:
            require(address not in seen and item.get('type')==wanted[address]['type'],
                    'Imported resource identity/type changed')
            if address in allowed:
                require(actions==['update'],'Reviewed adoption delta did not remain an explicit update')
                require(changed_fields(change)<=set(allowed[address]['allowed_update_fields']),
                        'Post-import update exceeds reviewed adoption fields')
            else:
                require(actions==['no-op'],'No-op adoption produced an unreviewed delta')
            seen.add(address)
        else:
            require(actions==['no-op'],'Unrelated managed change appeared after adoption')
    require(seen==set(wanted),'Post-import plan does not cover every adopted resource')
    return sorted(seen)


def prepare(args,root=ROOT):
    require(args.read_authorized_target is True,'Explicit adoption read/contact opt-in required')
    source=verify(root)
    require(source['status']=='HASHES_MATCH','A clean committed checkout is required')
    input_bytes,backend_bytes=read_private(args.inputs),read_private(args.backend)
    environment_bytes=read_private(args.environment)
    cloud_bytes=read_private(args.cloud) if args.cloud else None
    ca_bytes=read_private(args.ca_bundle) if args.ca_bundle else None
    inputs=load_private(args.inputs); backend=load_private(args.backend)
    entry,scope,state_key=select_scope(root,args.catalog_id,inputs)
    backend_settings(backend,state_key)

    adoption_plan=load_private(args.adoption_plan); adoption_evidence=load_private(args.adoption_evidence)
    adoption_review=adoption.evaluate(adoption_plan,adoption_evidence)
    require(adoption_plan['source_commit']==source['commit'] and adoption_plan['scope']==base_scope(scope),
            'Adoption plan belongs to another source or WSD scope')
    require(adoption_plan['state']['backend_sha256']==digest(backend_bytes)
            and adoption_plan['state']['state_key']==state_key,
            'Adoption state boundary differs from the exact Terraform backend')

    authority=load_private(args.authority)
    contact_authority(authority,source['commit'],scope,adoption_plan['operation_id'],adoption_plan['generation'],
                      input_bytes,backend_bytes,environment_bytes,cloud_bytes,ca_bytes,adoption_review)
    credentials=load_private(args.environment)
    process_environment(credentials)
    require((entry['platform']=='openstack')==(cloud_bytes is not None),
            'Cloud profile required only for OpenStack')
    cloud=cloud_config(cloud_bytes,inputs['openstack_cloud']) if cloud_bytes else None

    binary=Path(args.terraform).resolve(strict=True)
    require(binary.is_file() and os.access(binary,os.X_OK),'Explicit Terraform executable required')
    operation=new_directory(args.output,root)
    (operation/'tmp').mkdir(mode=0o700)
    write_new(operation/'terraform.rc',b'disable_checkpoint = true\n')
    snapshot(root,operation/'source')
    directory=operation/'source'/entry['root']
    if ca_bytes is not None:
        write_new(operation/'ca.pem',ca_bytes)
    if cloud is not None:
        if ca_bytes is not None:
            cloud['clouds'][inputs['openstack_cloud']]['cacert']=str(operation/'ca.pem')
        write_new(directory/'clouds.yaml',encoded(cloud))
        write_new(directory/'secure.yaml',b'{"clouds": {}}\n')
        write_new(directory/'clouds-public.yaml',b'{"public-clouds": {}}\n')

    env=runtime_environment(operation,credentials,entry['platform'],directory)
    for name,data in {
        'inputs.json':input_bytes,'backend.json':backend_bytes,'environment.json':environment_bytes,
        'contact.json':encoded(authority),'adoption-plan.json':encoded(adoption_plan),
        'adoption-evidence.json':encoded(adoption_evidence),'adoption-review.json':encoded(adoption_review),
        'references.json':encoded(load_private(args.references) if args.references else {}),
    }.items():
        write_new(operation/name,data)
    settings=backend_settings(backend,state_key)
    write_new(operation/'backend.hcl',''.join(f'{k} = {json.dumps(v)}\n' for k,v in sorted(settings.items())).encode())

    authorized_command(authority,binary,directory,['version','-json'],env,operation/'version.json')
    version=load_private(operation/'version.json')['terraform_version']
    require(version==json.loads((root/'config/toolchain.json').read_text())['terraform'],
            'Terraform version differs from pinned toolchain')
    authorized_command(authority,binary,directory,['init','-input=false','-no-color','-lockfile=readonly',
        '-reconfigure',f'-backend-config={operation/"backend.hcl"}'],env,operation/'init.log')
    authorized_command(authority,binary,directory,['plan','-input=false','-no-color','-lock=true',
        '-lock-timeout=60s','-detailed-exitcode',f'-var-file={operation/"inputs.json"}',
        f'-out={operation/"pre-import.tfplan"}'],env,operation/'pre-import-plan.log',ok=(0,2))
    authorized_command(authority,binary,directory,['show','-json',str(operation/'pre-import.tfplan')],
        env,operation/'pre-import-plan.json')
    pre_plan=load_private(operation/'pre-import-plan.json')
    validate_pre_plan(pre_plan,adoption_review)
    pre_review=review_plan(pre_plan,load_private(operation/'references.json'))
    require(pre_review['status']!='BLOCKED','Pre-import plan violates restricted resource controls')
    write_new(operation/'pre-import-review.json',encoded(pre_review))

    protected=['inputs.json','backend.json','backend.hcl','environment.json','contact.json',
               'adoption-plan.json','adoption-evidence.json','adoption-review.json','references.json',
               'terraform.rc','version.json','pre-import.tfplan','pre-import-plan.json',
               'pre-import-review.json']
    if ca_bytes is not None:
        protected.append('ca.pem')
    bundle={
        'format':'hosting-terraform-adoption-bundle/1','status':'AWAITING_EXPLICIT_IMPORT_APPROVAL',
        'source_commit':source['commit'],'catalog_id':entry['id'],'root':entry['root'],
        'scope':scope,'state_key':state_key,'operation_id':adoption_plan['operation_id'],
        'generation':adoption_plan['generation'],'created_at':utcnow().isoformat(),
        'terraform_version':version,'terraform_sha256':digest(binary.read_bytes()),
        'source_files':file_map(operation/'source'),
        'artifacts':{name:digest(read_private(operation/name)) for name in protected},
    }
    write_new(operation/'bundle.json',encoded(bundle))
    return {'status':bundle['status'],'bundle_sha256':c.digest(bundle),
            'imports':len(adoption_review['imports']),'native_mutation':False}


def validate_bundle(operation,approval,binary,root=ROOT):
    operation=private_path(operation,directory=True)
    bundle_bytes=read_private(operation/'bundle.json'); bundle=load_private(operation/'bundle.json')
    require(bundle['format']=='hosting-terraform-adoption-bundle/1'
            and bundle['status']=='AWAITING_EXPLICIT_IMPORT_APPROVAL','Unsupported adoption bundle')
    c.exact_keys(approval,APPROVAL_FIELDS)
    require(approval['format']=='hosting-terraform-adoption-approval/1'
            and approval['bundle_sha256']==digest(bundle_bytes)
            and approval['operation_id']==bundle['operation_id']
            and approval['generation']==bundle['generation'],'Adoption approval does not bind exact bundle')
    c.text(approval['change_ref']); current_window(approval)
    created=c.timestamp(bundle['created_at'])
    require(0<=(utcnow()-created).total_seconds()<=3600,'Adoption bundle is stale or future-dated')
    source=verify(root)
    require(source['status']=='HASHES_MATCH' and source['commit']==bundle['source_commit'],
            'Execute adoption from exact clean source revision')
    require(digest(Path(binary).read_bytes())==bundle['terraform_sha256'],'Terraform executable changed')
    require(file_map(operation/'source')==bundle['source_files'],'Adoption source/runtime changed')
    for name,expected in bundle['artifacts'].items():
        require(Path(name).name==name and digest(read_private(operation/name))==expected,
                'Adoption bundle artifact changed')
    plan=load_private(operation/'adoption-plan.json')
    evidence=load_private(operation/'adoption-evidence.json')
    adoption_review=adoption.evaluate(plan,evidence)
    require(adoption_review==load_private(operation/'adoption-review.json')
            and approval['adoption_review_sha256']==c.digest(adoption_review),
            'Adoption ownership review changed')
    pre_plan=load_private(operation/'pre-import-plan.json')
    validate_pre_plan(pre_plan,adoption_review)
    pre_review=review_plan(pre_plan,load_private(operation/'references.json'))
    require(pre_review==load_private(operation/'pre-import-review.json')
            and approval['pre_plan_sha256']==c.digest(pre_plan)
            and approval['pre_review_sha256']==c.digest(pre_review),
            'Approved pre-import plan or review changed')
    entry,scope,state_key=select_scope(root,bundle['catalog_id'],load_private(operation/'inputs.json'))
    require((entry['root'],scope,state_key)==(bundle['root'],bundle['scope'],bundle['state_key'])
            and plan['scope']==base_scope(scope),'Adoption bundle scope differs')
    backend=load_private(operation/'backend.json')
    backend_settings(backend,state_key)
    require(plan['state']['backend_sha256']==digest(read_private(operation/'backend.json')),
            'Adoption backend binding changed')
    return bundle,adoption_review


def completed_adoption_history(scope,expected_scope=None):
    """Refuse new Terraform writers while a prior state-adoption outcome is unknown."""
    records={}
    for path in scope.glob('*.adoption-started.json'):
        started=load_private(path); c.exact_keys(started,START_FIELDS)
        require(started['format']=='hosting-terraform-adoption-attempt/1'
                and started['status']=='STARTED_OUTCOME_UNKNOWN','Unknown Terraform adoption start')
        require(expected_scope is None or started['scope']==expected_scope,'Adoption ledger belongs to another scope')
        identity=digest(encoded({'operation':started['operation_id'],'generation':started['generation']}))
        require(path.name==identity+'.adoption-started.json','Adoption attempt filename differs')
        result_path=scope/(identity+'.adoption-result.json')
        require(result_path.exists(),'Terraform adoption outcome remains unknown; reconcile state before another writer')
        result=load_private(result_path)
        c.exact_keys(result,START_FIELDS|{'completed_at','post_plan_sha256','post_review_sha256','imported_addresses'})
        require(result['status']=='ADOPTED_REQUIRES_EXACT_DELTA_PLAN_REVIEW'
                and not c.differences({k:result[k] for k in START_FIELDS-{'status'}},
                                      {k:started[k] for k in START_FIELDS-{'status'}}),
                'Terraform adoption result remains held or changed')
        require(isinstance(result['post_plan_sha256'],str) and c.HEX.fullmatch(result['post_plan_sha256'])
                and isinstance(result['post_review_sha256'],str) and c.HEX.fullmatch(result['post_review_sha256'])
                and isinstance(result['imported_addresses'],list)
                and result['imported_addresses']==sorted(set(result['imported_addresses'])),
                'Invalid completed adoption evidence')
        require(c.timestamp(started['started_at'])<=c.timestamp(result['completed_at'])<=utcnow(),
                'Invalid adoption completion chronology')
        records[identity]=result
    require({p.name for p in scope.glob('*.adoption-result.json')}==
            {key+'.adoption-result.json' for key in records},
            'Orphan Terraform adoption result requires reconciliation')
    ordered=sorted(records.values(),key=lambda x:c.timestamp(x['started_at']))
    for previous,current in zip(ordered,ordered[1:]):
        require(c.timestamp(previous['completed_at'])<=c.timestamp(current['started_at']),
                'Overlapping Terraform adoption history')
    head=scope/'adoption-head.json'
    if head.exists():
        require(ordered and c.digest(load_private(head))==c.digest(ordered[-1]),
                'Terraform adoption head differs from latest complete attempt')
    else:
        require(not records,'Terraform adoption head is missing')
    return records


def approved_command(approval,binary,directory,argv,env,output,*,ok=(0,),timeout=900):
    current_window(approval)
    remaining=(c.timestamp(approval['valid_until'])-utcnow()).total_seconds()
    require(remaining>0,'Adoption approval expired')
    from tools.terraform_run import command
    return command(binary,directory,argv,env,output,timeout=min(timeout,remaining),ok=ok)


def execute(args,root=ROOT):
    require(args.execute_approved_import is True,'Explicit Terraform import opt-in required')
    operation=private_path(args.bundle,directory=True)
    approval=load_private(args.approval)
    binary=Path(args.terraform).resolve(strict=True)
    bundle,adoption_review=validate_bundle(operation,approval,binary,root)
    credentials=load_private(operation/'environment.json')
    directory=operation/'source'/bundle['root']
    env=runtime_environment(operation,credentials,bundle['scope']['platform'],directory)
    backend=load_private(operation/'backend.json')
    identity=digest(encoded({'operation':bundle['operation_id'],'generation':bundle['generation']}))

    from tools.terraform_apply import scope_ledger
    with scope_ledger(args.ledger,backend['address'],bundle['scope']) as ledger:
        completed_adoption_history(ledger,bundle['scope'])
        started_path=ledger/(identity+'.adoption-started.json')
        require(not started_path.exists(),'This adoption operation/generation was already attempted')
        receipt={
            'format':'hosting-terraform-adoption-attempt/1','status':'STARTED_OUTCOME_UNKNOWN',
            'bundle_sha256':approval['bundle_sha256'],'scope':bundle['scope'],
            'operation_id':bundle['operation_id'],'generation':bundle['generation'],
            'change_ref':approval['change_ref'],'started_at':utcnow().isoformat(),
        }
        write_new(started_path,encoded(receipt))
        replace_private(ledger/'adoption-head.json',encoded(receipt))
        write_new(operation/'approval.json',encoded(approval))
        imported=[]
        try:
            for index,row in enumerate(adoption_review['imports'],1):
                approved_command(approval,binary,directory,
                    ['import','-input=false','-no-color','-lock=true','-lock-timeout=60s',
                     f'-var-file={operation/"inputs.json"}',row['address'],row['import_id']],
                    env,operation/f'import-{index:03d}.log',timeout=1800)
                imported.append(row['address'])
            approved_command(approval,binary,directory,
                ['plan','-input=false','-no-color','-lock=true','-lock-timeout=60s',
                 '-detailed-exitcode',f'-var-file={operation/"inputs.json"}',
                 f'-out={operation/"post-import.tfplan"}'],
                env,operation/'post-import-plan.log',ok=(0,2))
            approved_command(approval,binary,directory,
                ['show','-json',str(operation/'post-import.tfplan')],
                env,operation/'post-import-plan.json')
            post_plan=load_private(operation/'post-import-plan.json')
            validate_post_plan(post_plan,adoption_review)
            post_review=review_plan(post_plan,load_private(operation/'references.json'))
            require(post_review['status']!='BLOCKED','Post-import plan violates restricted resource controls')
            write_new(operation/'post-import-review.json',encoded(post_review))
            receipt.update(
                status='ADOPTED_REQUIRES_EXACT_DELTA_PLAN_REVIEW',
                completed_at=utcnow().isoformat(),
                post_plan_sha256=c.digest(post_plan),
                post_review_sha256=c.digest(post_review),
                imported_addresses=sorted(imported),
            )
        except BaseException:
            receipt.update(status='HOLD_ADOPTION_RECONCILIATION_REQUIRED',
                           stopped_at=utcnow().isoformat(),imported_addresses=sorted(imported))
            write_new(ledger/(identity+'.adoption-result.json'),encoded(receipt))
            replace_private(ledger/'adoption-head.json',encoded(receipt))
            write_new(operation/'result.json',encoded(receipt))
            raise
        write_new(ledger/(identity+'.adoption-result.json'),encoded(receipt))
        replace_private(ledger/'adoption-head.json',encoded(receipt))
        write_new(operation/'result.json',encoded(receipt))
    return {'status':receipt['status'],'imported_addresses':receipt['imported_addresses'],
            'may_apply':False,'native_acceptance':False,'production_activation':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    prepare_parser=sub.add_parser('prepare')
    for name in ('catalog-id','inputs','backend','authority','environment','adoption-plan',
                 'adoption-evidence','terraform','output'):
        prepare_parser.add_argument('--'+name,required=True,type=Path if name not in {'catalog-id'} else str)
    for name in ('references','cloud','ca-bundle'):
        prepare_parser.add_argument('--'+name,type=Path)
    prepare_parser.add_argument('--read-authorized-target',action='store_true')
    execute_parser=sub.add_parser('execute')
    for name in ('bundle','approval','terraform','ledger'):
        execute_parser.add_argument('--'+name,required=True,type=Path)
    execute_parser.add_argument('--execute-approved-import',action='store_true')
    args=parser.parse_args()
    try:
        result=prepare(args) if args.action=='prepare' else execute(args)
        print(json.dumps(result)); return 0
    except OperatorError as exc:
        print(json.dumps({'status':'STOPPED','reason':str(exc),'native_acceptance':False})); return 2
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):
        print(json.dumps({'status':'HOLD_ADOPTION_RECONCILIATION','may_apply':False,
                          'native_acceptance':False,'production_activation':False})); return 2


if __name__=='__main__':
    raise SystemExit(main())
