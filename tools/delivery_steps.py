"""Typed delivery adapters. Authority and native ownership stay with each executor."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from tools import readback_core as c
from tools.run_files import (current_window, digest, encoded, load_private, private_path,
                             read_private, require, sync_directory, write_new)

# Parameters, mandatory file bindings, optional file bindings. No shell command,
# arbitrary module, executable arguments or environment overlay is accepted.
KINDS = {
    'openstack_quota': (set(), {'request','authority','token','ca'}, set()),
    'edge_containment': ({'nft','nft_sha256'}, {'spec','authority'}, set()),
    'remote_owner': ({'ssh','ssh_sha256'}, {'job','target','ssh_key','ssh_certificate'}, set()),
    'restic': ({'action','restic','restic_sha256','target'}, {'config','credentials'}, {'ca_bundle','receipt','manifest','restore_authority'}),
    'platform_transition': ({'prior_step','stage'}, {'inputs','acceptance'}, set()),
    'workload_inputs': ({'domain_steps','selected_input'}, {'environment'}, {'vmware_bindings'}),
    'capacity': ({'action','database'}, {'request','authority'}, {'native_ids','inputs','sizing'}),
    'acceptance': ({'purpose'}, {'acceptance'}, set()),
    'terraform_plan': ({'catalog_id','terraform','terraform_sha256'}, {'inputs','backend','environment','authority'}, {'references','cloud','ca_bundle','transition'}),
    'terraform_apply': ({'prepared_step'}, {'approval'}, set()),
    'guest_plan': ({'workload_step','python','python_sha256','ssh','ssh_sha256','mode','max_seconds'}, {'access','references','ssh_key','ssh_certificate'}, set()),
    'guest_apply': ({'prepared_step'}, {'approval'}, set()),
    'vsphere_power': (set(), {'request','authority','session'}, {'ca_file'}),
    'target_campaign': ({'ssh','ssh_sha256'}, {'plan','authority'}, set()),
    'edge_policy': ({'nft','nft_sha256','mode'}, {'spec','authority'}, set()),
    'ipam': ({'action'}, {'request','authority','token_file'}, {'ca_bundle'}),
    'dns': ({'action'}, {'allocation','confirmation','job','scope','authority','token_file','tsig_file'}, {'ca_bundle','registration_job','registration_scope'}),
    'dns_propagation': ({'dns_step'}, {'config','secrets'}, set()),
}


def file_paths(packet):
    result = {}
    for name, binding in packet['files'].items():
        require(digest(read_private(binding['path'])) == binding['sha256'], 'Delivery input bytes changed')
        result[name] = Path(binding['path'])
    return result


def match_scope(value, plan):
    require(isinstance(value, dict) and {k:v for k,v in value.items() if k!='phase'} == plan['scope'], 'Foreign delivery scope')


def dependency(step, selected, expected, plan, base):
    require(selected in step['needs'], 'Owner handoff must be an explicit dependency')
    upstream = next(s for s in plan['steps'] if s['id']==selected)
    require(upstream['kind'] == expected, 'Wrong delivery owner handoff')
    return base/'steps'/selected


def validate_packet(step, packet, plan, base):
    params, required, optional = KINDS[step['kind']]
    c.exact_keys(packet['parameters'], params)
    c.exact_keys(packet['files'], required, optional)
    files = file_paths(packet); values=packet['parameters']; kind=step['kind']
    if kind=='openstack_quota':
        from tools.openstack_quota import validate
        request=load_private(files['request']); validate(request)
        require(request['scope']=={key:plan['scope'][key] for key in request['scope']}
                and request['source_commit']==plan['source_commit'], 'Foreign tenant quota handoff')
    if kind=='dns_propagation':
        from tools.dns_propagation import validate
        job,scope,receipt=dns_handoff(step,packet,plan,base)
        validate(load_private(files['config']),job,scope,receipt,load_private(files['secrets']))
    for binary in ('terraform','python','ssh','nft','restic'):
        if binary in values:
            path=Path(values[binary])
            require(path.is_absolute() and path.is_file() and os.access(path,os.X_OK)
                    and digest(path.read_bytes())==values[binary+'_sha256'], 'Delivery executable changed')
    if kind=='remote_owner':
        from tools import owner_worker,remote_owner
        job=load_private(files['job']); owner_worker.validate(job); match_scope(job['scope'],plan)
        require(job['source_commit']==plan['source_commit'] and job['delivery']=={
            'plan_sha256':c.digest(plan),'step_id':step['id'],'dependencies':packet['dependencies']},
            'Remote owner job belongs to another coordinator handoff')
        remote_owner.validate(load_private(files['target']),job)
    if kind=='restic':
        from tools.restic_run import validate
        config=load_private(files['config']); validate(config); match_scope(config['scope'],plan)
        require(config['restic_sha256']==values['restic_sha256'],'Backup executable binding changed')
        require(values['action'] in {'backup','restore'},'Unknown backup transition')
        restore_files={'receipt','manifest','restore_authority'}
        if values['action']=='backup':
            require(values['target'] is None and not restore_files.intersection(files),'Backup cannot carry restore inputs')
        else:
            require(restore_files.issubset(files) and isinstance(values['target'],str)
                    and Path(values['target']).is_absolute(),'Exact restore input set required')
    if kind in {'terraform_apply','guest_apply'}:
        upstream=dependency(step,values['prepared_step'], 'terraform_plan' if kind=='terraform_apply' else 'guest_plan',plan,base)
        require(read_private(upstream/'bundle.json')==read_private(upstream/'execution/bundle.json'), 'Prepared owner bundle changed')
        bundle=load_private(upstream/'bundle.json'); match_scope(bundle['scope'],plan)
        require(bundle['source_commit']==plan['source_commit'],'Prepared owner source changed')
        if kind=='terraform_apply' and bundle['scope']['phase']=='workloads':
            from tools.capacity_demand import check_ancestors
            cloud_sha=load_private(upstream/'execution/contact.json')['cloud_sha256'] if plan['scope']['platform']=='openstack' else None
            check_ancestors(step,plan,base,load_private(upstream/'execution/inputs.json'),cloud_sha256=cloud_sha)
    if kind=='guest_plan':
        dependency(step,values['workload_step'],'terraform_apply',plan,base)
        match_scope(load_private(files['access'])['scope'],plan)
        require(values['mode'] in {'check','configure'} and type(values['max_seconds']) is int
                and 30<=values['max_seconds']<=3600, 'Invalid guest execution bounds')
    if kind=='platform_transition':
        dependency(step,values['prior_step'],'terraform_apply',plan,base)
        require(values['stage'] in {'prepared','bootstrap'},'Unknown native lifecycle stage')
    if kind=='workload_inputs':
        require(isinstance(values['domain_steps'],list) and values['domain_steps']
                and len(values['domain_steps'])==len(set(values['domain_steps'])),'Exact domain execution dependency set required')
        for selected in values['domain_steps']: dependency(step,selected,'terraform_apply',plan,base)
        c.text(values['selected_input'],length=1024)
    if kind=='terraform_plan':
        from tools.terraform_run import select_scope
        from tools.delivery_run import ROOT
        _,scope,_=select_scope(ROOT,values['catalog_id'],load_private(files['inputs']))
        match_scope(scope,plan)
        if scope['phase']=='workloads':
            from tools.capacity_demand import check_ancestors
            check_ancestors(step,plan,base,load_private(files['inputs']),
                            cloud_sha256=digest(read_private(files['cloud'])) if 'cloud' in files else None)
    if kind=='acceptance':
        require(values['purpose'] in {'admission','domain','bootstrap','services','activation','post_activation','recovery','retirement'}, 'Unknown acceptance gate')
        accepted=load_private(files['acceptance'])
        c.exact_keys(accepted, {'format','plan_sha256','step_id','scope','dependencies','purpose','valid_from','valid_until','acceptance_ref'})
        require(accepted['format']=='hosting-delivery-acceptance/1' and accepted['plan_sha256']==c.digest(plan)
                and accepted['step_id']==step['id'] and accepted['dependencies']==packet['dependencies']
                and accepted['purpose']==values['purpose'], 'Acceptance does not bind this delivery gate')
        match_scope(accepted['scope'],plan); c.text(accepted['acceptance_ref']); current_window(accepted)
    if kind in {'edge_policy','edge_containment','target_campaign','ipam','dns','capacity'}:
        field={'edge_policy':'spec','edge_containment':'spec','target_campaign':'plan','ipam':'request','dns':'allocation','capacity':'request'}[kind]
        value=load_private(files[field]); match_scope(value['scope'],plan)
        if kind=='target_campaign': require(value['source_commit']==plan['source_commit'], 'Foreign campaign source')
        if kind=='edge_policy': require(values['mode'] in {'withdraw','bootstrap','active'}, 'Unknown edge transition')
        if kind=='edge_containment':
            from tools.edge_contain import authorize
            authorize(value,load_private(files['authority']))
            require(value['nft_sha256']==values['nft_sha256'],'Incident executable binding changed')
        if kind=='ipam':
            from tools.netbox_ipam import ACTIONS
            require(values['action'] in ACTIONS,'Unknown IPAM operation')
        if kind=='dns':
            from tools.netbox_dns import ACTIONS
            require(values['action'] in ACTIONS,'Unknown DNS operation')
        if kind=='capacity':
            require(values['action'] in {'reserve','confirm','release'},'Unknown capacity transition')
            private_path(values['database'])
            require(('inputs' in files)==('sizing' in files),'Workload inputs and sizing catalogue must be paired')
            if 'inputs' in files:
                from tools.capacity_demand import bind_request,owner_binding
                require(values['action']=='reserve','Workload sizing is bound at reservation')
                sizing=load_private(files['sizing'])
                bind_request(value,load_private(files['inputs']),sizing)
                owner_binding(values['database'],value,sizing,require_live=False)
    if kind=='vsphere_power':
        from tools.vsphere_power import validate
        request=load_private(files['request']); validate(request)
        require(plan['scope']['platform']=='vmware' and request['source_commit']==plan['source_commit']
                and request['snapshot']['tenant_id']==plan['scope']['tenant_key']
                and request['snapshot']['scope_id']==plan['scope']['wsd_key'], 'Foreign native power handoff')


def owner_ledger(base, owner):
    # Native owner ledgers are shared across all delivery scopes/generations.
    # A new operation directory must never reset an owner's uncertainty hold.
    return native_owner_ledger(base.parents[2],owner)


def native_owner_ledger(ledger,owner):
    parent=ledger/'owners'
    if not parent.exists(): parent.mkdir(mode=0o700); sync_directory(parent.parent)
    private_path(parent,directory=True)
    path=parent/owner
    if not path.exists(): path.mkdir(mode=0o700); sync_directory(path.parent)
    return private_path(path,directory=True)


def prepared_directory(step, packet, plan, base):
    kind='terraform_plan' if step['kind']=='terraform_apply' else 'guest_plan'
    return dependency(step,packet['parameters']['prepared_step'],kind,plan,base)/'execution'


def terraform_execution(selected, plan, base):
    upstream=next(s for s in plan['steps'] if s['id']==selected)
    packet=load_private(base/'steps'/selected/'packet.json')
    directory=prepared_directory(upstream,packet,plan,base)
    for name in ('result.json','outputs.json'):
        require(read_private(base/'steps'/selected/name)==read_private(directory/name),'Native workload handoff changed')
    return directory


def child(root, module, arguments, directory, *, timeout):
    with os.fdopen(os.open(directory/'owner.log',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb') as log:
        result=subprocess.run([sys.executable,str(root/'tools'/module),*map(str,arguments)],stdin=subprocess.DEVNULL,
            stdout=log,stderr=log,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'},
            timeout=timeout,umask=0o077)
    require(result.returncode==0,'Delivery owner did not complete; inspect its private journal')


def dispatch(step, packet, directory, base, plan, root):
    validate_packet(step,packet,plan,base)
    files=file_paths(packet); values=packet['parameters']; kind=step['kind']; names=[]
    if kind=='openstack_quota':
        return quota_dispatch(step,packet,directory,base,plan,root)
    if kind=='remote_owner':
        return remote_dispatch(step,packet,directory,plan)
    elif kind=='dns_propagation':
        return dns_observation(step,packet,directory,base,plan)
    elif kind=='edge_containment':
        from tools.edge_contain import execute
        result=execute(load_private(files['spec']),load_private(files['authority']),values['nft'],
                       owner_ledger(base,'edge_policy'),directory/'execution')
        write_new(directory/'containment.json',read_private(directory/'execution/containment.json'))
        names=['containment.json']
    elif kind=='restic':
        from tools.restic_run import execute
        result=execute(values['action'],load_private(files['config']),load_private(files['credentials']),
            values['restic'],directory/'execution',ca_file=files.get('ca_bundle'),
            receipt=load_private(files['receipt']) if 'receipt' in files else None,
            expected=load_private(files['manifest']) if 'manifest' in files else None,target=values['target'],
            authority=load_private(files['restore_authority']) if 'restore_authority' in files else None)
        for name in ('receipt.json','context.json') + (('manifest.json',) if values['action']=='backup' else ()):
            write_new(directory/name,read_private(directory/'execution'/name)); names.append(name)
    elif kind=='platform_transition':
        from tools.lifecycle_transition import prepare
        prior=terraform_execution(values['prior_step'],plan,base)
        record=prepare(prior,files['inputs'],files['acceptance'],values['stage'])
        match_scope(record['scope'],plan)
        write_new(directory/'transition.json',encoded(record)); names=['transition.json']
        result={'status':'TRANSITION_REQUIRES_EXACT_PLAN_REVIEW'}
    elif kind=='workload_inputs':
        from tools.wsd_handoff import compile_runs
        records=[terraform_execution(selected,plan,base) for selected in values['domain_steps']]
        outputs,scopes,provenance=compile_runs(load_private(files['environment']),records,
            load_private(files['vmware_bindings']) if 'vmware_bindings' in files else None)
        require(values['selected_input'] in outputs,'Requested workload input is absent from the compiled handoff')
        selected=[row for row in scopes['scopes'] if row['input']==values['selected_input']]
        require(len(selected)==1,'Exact workload draft scope required'); match_scope(selected[0]['scope'],plan)
        for name,value in {'inputs.json':outputs[values['selected_input']],'scopes.json':scopes,'handoff.json':provenance}.items():
            write_new(directory/name,encoded(value)); names.append(name)
        result={'status':'BOUND_WORKLOAD_DRAFT_REQUIRES_REVIEW'}
    elif kind=='capacity':
        from tools.capacity import operate
        result=operate(values['database'],load_private(files['request']),values['action'],load_private(files['authority']),
                       load_private(files['native_ids']) if 'native_ids' in files else None)
        if 'inputs' in files:
            from tools.capacity_demand import bind_request
            request=load_private(files['request']); sizing=load_private(files['sizing'])
            for name,value in {'result.json':result,'capacity-request.json':request,'sizing.json':sizing,
                               'demand.json':bind_request(request,load_private(files['inputs']),sizing)}.items():
                write_new(directory/name,encoded(value)); names.append(name)
    elif kind=='acceptance':
        accepted=load_private(files['acceptance'])
        write_new(directory/'acceptance.json',encoded(accepted))
        result={'status':'EXTERNAL_ACCEPTANCE_RECORDED','acceptance_ref':accepted['acceptance_ref']}
        names=['acceptance.json']
    elif kind=='terraform_plan':
        from tools.terraform_run import prepare
        args={name:files.get(name) for name in ('inputs','backend','environment','authority','references','cloud','ca_bundle','transition')}
        result=prepare(argparse.Namespace(**args,catalog_id=values['catalog_id'],terraform=Path(values['terraform']),
                       output=directory/'execution',read_authorized_target=True),root)
        write_new(directory/'bundle.json',read_private(directory/'execution/bundle.json'))
        write_new(directory/'review.json',read_private(directory/'execution/review.json'))
        names=['bundle.json','review.json']
    elif kind=='terraform_apply':
        from tools.terraform_apply import apply
        from tools.wsd_handoff import execution_outputs
        prepared=prepared_directory(step,packet,plan,base)
        prior=load_private(prepared.parent/'packet.json')['parameters']
        require(digest(Path(prior['terraform']).read_bytes())==prior['terraform_sha256'],'Terraform executable changed')
        result=apply(argparse.Namespace(bundle=prepared,approval=files['approval'],terraform=Path(prior['terraform']),
                    ledger=owner_ledger(base,'terraform'),execute_approved_change=True),root)
        bundle=load_private(prepared/'bundle.json'); match_scope(bundle['scope'],plan)
        execution_outputs(prepared,bundle['scope']['phase'])
        for name in ('result.json','outputs.json'): write_new(directory/name,read_private(prepared/name))
        names=['result.json','outputs.json']
    elif kind=='guest_plan':
        from tools.guest_run import prepare
        workload=terraform_execution(values['workload_step'],plan,base)
        result=prepare(argparse.Namespace(workload_run=workload,workload_outputs=None,**files,
            python=Path(values['python']),ssh=Path(values['ssh']),mode=values['mode'],max_seconds=values['max_seconds'],
            operation_id='delivery-'+c.digest([plan['operation_id'],step['id']])[:32],generation=plan['generation'],
            output=directory/'execution'),root)
        write_new(directory/'bundle.json',read_private(directory/'execution/bundle.json')); names=['bundle.json']
    elif kind=='guest_apply':
        from tools.guest_apply import apply
        prepared=prepared_directory(step,packet,plan,base)
        result=apply(argparse.Namespace(bundle=prepared,approval=files['approval'],ledger=owner_ledger(base,'guest'),execute=True),root)
        for name,original in [('result.json','result.json'),('stats.json','runtime/stats.json')]:
            write_new(directory/name,read_private(prepared/original))
        names=['result.json','stats.json']
    elif kind=='vsphere_power':
        from tools.vsphere_power import Client,execute
        request=load_private(files['request'])
        client=Client(request,read_private(files['session']).decode().strip(),files.get('ca_file'))
        result=execute(request,load_private(files['authority']),owner_ledger(base,'power'),client,execute_approved_change=True,root=root)
    else:
        output=directory/'execution' if kind in {'target_campaign','edge_policy'} else directory/'result.json'
        arguments=[]
        module={'target_campaign':'qualify_target.py','edge_policy':'nft_edge.py','ipam':'netbox_ipam.py','dns':'netbox_dns.py'}[kind]
        if kind=='target_campaign': arguments=[files['plan'],'--ssh',values['ssh']]
        elif kind=='edge_policy': arguments=['apply','--nft',values['nft'],'--mode',values['mode']]
        elif kind=='ipam': arguments=[files['request'],'--action',values['action']]
        elif kind=='dns': arguments=['--action',values['action']]
        for name,path in files.items():
            if (kind=='target_campaign' and name=='plan') or (kind=='ipam' and name=='request'): continue
            arguments+=['--'+name.replace('_','-'),path]
        if kind!='target_campaign': arguments+=['--ledger',owner_ledger(base,'ipam' if kind=='dns' else kind)]
        arguments+=['--output',output,'--execute']
        authority=load_private(files['authority']); current_window(authority)
        budget=(c.timestamp(authority['valid_until'])-c.timestamp(c.now())).total_seconds()
        child(root,module,arguments,directory,timeout=min(3600,budget))
        if kind in {'target_campaign','edge_policy'}:
            original=output/('result.json' if kind=='target_campaign' else 'receipt.json')
            write_new(directory/'result.json',read_private(original))
        result=load_private(directory/'result.json')
        names=['result.json']
        accepted={'target_campaign':{'COLLECTED_REQUIRES_INDEPENDENT_ACCEPTANCE'},
                  'edge_policy':{'APPLIED_EXPIRING_POLICY_NOT_QUALIFIED'},
                  'dns':{'AUTHORITATIVE_REGISTRATION_OBSERVED','AUTHORITATIVE_TOMBSTONE_OBSERVED'}}
        if kind in accepted: require(result['status'] in accepted[kind],'Delivery owner outcome remains held')
        if kind=='ipam':
            require(result.get('allocation_status') in {'reserved','active','deprecated'},'IPAM allocation remains held')
    if not names:
        write_new(directory/'result.json',encoded(result)); names=['result.json']
    return complete(step,packet,directory,plan,result,names)


def complete(step,packet,directory,plan,result,names):
    from tools.delivery_run import artifact_receipt
    completion={'format':'hosting-delivery-owner-completion/1','plan_sha256':c.digest(plan),'step_id':step['id'],
                'packet_sha256':c.digest(packet),'status':result['status'],'artifacts':artifact_receipt(directory,names)}
    write_new(directory/'owner-completion.json',encoded(completion))
    return result,names+['owner-completion.json']


def retain(path,raw):
    if path.exists(): require(read_private(path)==raw,'Interrupted owner handoff copy changed')
    else: write_new(path,raw)



def quota_dispatch(step,packet,directory,base,plan,root,*,observe=False,recovery_authority=None):
    from tools import openstack_quota as quota
    original=file_paths({'files':{'request':packet['files']['request']}})
    request=load_private(original['request']); quota.validate(request)
    require(request['scope']=={key:plan['scope'][key] for key in request['scope']}
            and request['source_commit']==plan['source_commit'],'Foreign tenant quota handoff')
    if (directory/'result.json').exists():
        result=load_private(directory/'result.json')
        sha=result.get('authority_sha256')
        require(isinstance(sha,str) and c.HEX.fullmatch(sha),'Invalid retained quota authority digest')
        authority_name='quota-authority-'+sha+'.json'; authority=load_private(directory/authority_name)
    else:
        if recovery_authority is not None:
            require(observe,'Renewed quota access is observation-only')
            access=load_private(recovery_authority)
            c.exact_keys(access,{'format','request_sha256','files'})
            require(access['format']=='hosting-openstack-quota-recovery/1'
                    and access['request_sha256']==c.digest(request),'Quota recovery belongs to another request')
            c.exact_keys(access['files'],{'authority','token','ca'})
            for binding in access['files'].values():
                c.exact_keys(binding,{'path','sha256'})
                require(isinstance(binding['path'],str) and Path(binding['path']).is_absolute()
                        and isinstance(binding['sha256'],str) and c.HEX.fullmatch(binding['sha256']), 'Exact private quota recovery artifact required')
            files=file_paths({'files':access['files']})
        else: files=file_paths({'files':{name:packet['files'][name] for name in ('authority','token','ca')}})
        authority=load_private(files['authority'])
        require(not observe or authority['action']=='observe','Interrupted quota handoff requires explicit read-only authority')
        authority_name='quota-authority-'+c.digest(authority)+'.json'; retain(directory/authority_name,encoded(authority))
        result=quota.operate(request,authority,read_private(files['token']),read_private(files['ca']),
                             owner_ledger(base,'openstack_quota'),root=root)
        retain(directory/'result.json',encoded(result))
    require(result['format']=='hosting-openstack-quota-receipt/1'
            and result['status']=='PROJECT_QUOTAS_OBSERVED_REQUIRES_ENFORCEMENT_ACCEPTANCE'
            and result['request_sha256']==c.digest(request) and result['authority_sha256']==c.digest(authority)
            and authority['request_sha256']==c.digest(request) and authority['action'] in {'apply','observe'}
            and result['scope']==request['scope'] and result['project_id']==request['project']['id']
            and result['service']==request['service'] and result['generation']==request['generation']
            and {key:value['limit'] for key,value in result['quotas'].items()}==request['after'],
            'Retained quota owner handoff differs')
    current_window(authority,now=c.timestamp(result['observed_at']))
    with quota.journal.locked(owner_ledger(base,'openstack_quota'),quota.owner_scope(request)) as log:
        operations=quota.history(log,request['scope'])
        require(operations and operations[-1]['completed'] and operations[-1]['request']==request,
                'Quota native history is missing, pending or superseded')
        return complete(step,packet,directory,plan,result,['result.json',authority_name])


def dns_handoff(step,packet,plan,base):
    upstream=dependency(step,packet['parameters']['dns_step'],'dns',plan,base)
    parent=load_private(upstream/'packet.json')
    files=file_paths({'files':{key:parent['files'][key] for key in ('allocation','job','scope')}})
    match_scope(load_private(files['allocation'])['scope'],plan)
    return load_private(files['job']),load_private(files['scope']),load_private(upstream/'result.json')


def dns_observation(step,packet,directory,base,plan,*,recovery_authority=None):
    from tools import dns_propagation as dns
    files=file_paths(packet); job,scope,receipt=dns_handoff(step,packet,plan,base)
    secrets=load_private(files['secrets']); config=load_private(files['config'])
    if (directory/'result.json').exists():
        result=load_private(directory/'result.json')
        selected=result.get('config_sha256')
        require(isinstance(selected,str) and len(selected)==64 and all(x in '0123456789abcdef' for x in selected),
                'Invalid retained DNS observation configuration digest')
        name='observation-'+selected+'.json'; observed_config=load_private(directory/name)
        dns.validate(observed_config,job,scope,receipt,secrets,current=False)
        dns.validate_result(result,observed_config,job,scope,receipt)
    else:
        observed_config=load_private(recovery_authority) if recovery_authority else config
        name='observation-'+c.digest(observed_config)+'.json'
    require({k:v for k,v in observed_config.items() if k not in {'valid_from','valid_until','observation_ref'}}==
            {k:v for k,v in config.items() if k not in {'valid_from','valid_until','observation_ref'}},
            'DNS observation renewal cannot change the original job, keys or views')
    if not (directory/'result.json').exists():
        retain(directory/name,encoded(observed_config))
        result=dns.observe(observed_config,job,scope,receipt,secrets)
        dns.validate_result(result,observed_config,job,scope,receipt)
        retain(directory/'result.json',encoded(result))
    return complete(step,packet,directory,plan,result,['result.json',name])


def remote_dispatch(step,packet,directory,plan,*,observe=False,recovery_authority=None):
    from tools import owner_worker,remote_owner
    files=file_paths({'files':{'job':packet['files']['job']}}); values=packet['parameters']; job=load_private(files['job'])
    result_path=directory/'remote-result.json'
    if result_path.exists(): result=load_private(result_path)
    else:
        require(digest(Path(values['ssh']).read_bytes())==values['ssh_sha256'],'Remote transport executable changed')
        original=file_paths({'files':{'target':packet['files']['target']}})
        target=load_private(original['target'])
        if recovery_authority is not None:
            require(observe,'Renewed remote access is observation-only')
            record=load_private(recovery_authority)
            target,files=remote_owner.recovery_access(record,job,target)
            retain(directory/('recovery-access-'+c.digest(record)+'.json'),encoded(record))
        else: files=file_paths({'files':{name:packet['files'][name] for name in ('ssh_key','ssh_certificate')}})
        result=remote_owner.contact(job,target,values['ssh'],files['ssh_key'],
                                   files['ssh_certificate'],directory,observe=observe)
        write_new(result_path,encoded(result))
    artifacts=owner_worker.check_result(result,job)
    for name,raw in artifacts.items(): retain(directory/name,raw)
    return complete(step,packet,directory,plan,result,['remote-result.json',*artifacts])


def recover(step, packet, directory, base, plan, root, *, recovery_authority=None):
    """Only recover durable completion; never rerun an uncertain owner operation."""
    from tools.delivery_run import artifact_receipt
    if not (directory/'owner-completion.json').exists():
        kind=step['kind']
        if kind=='openstack_quota':
            return quota_dispatch(step,packet,directory,base,plan,root,observe=True,recovery_authority=recovery_authority)
        if kind=='dns_propagation':
            return dns_observation(step,packet,directory,base,plan,recovery_authority=recovery_authority)
        if kind=='capacity':
            from tools.capacity import operate
            files=file_paths(packet); values=packet['parameters']; request=load_private(files['request'])
            authority=load_private(files['authority']); result=operate(values['database'],request,'inspect',None)
            require(result['status']=={'reserve':'RESERVED','confirm':'CONFIRMED','release':'RELEASED'}[values['action']]
                    and authority['format']=='hosting-capacity-authority/1'
                    and authority['request_sha256']==c.digest(request) and authority['action']==values['action']
                    and all(result[key]==authority[key] for key in ('envelope_sha256','change_ref','evidence_ref'))
                    and c.timestamp(authority['valid_from'])<=c.timestamp(result['observed_at'])<c.timestamp(authority['valid_until']),
                    'Capacity owner receipt no longer matches the interrupted action')
            if values['action']=='confirm':
                require(result['native_ids']==sorted(load_private(files['native_ids'])),'Recovered capacity native identities differ')
            artifacts={'result.json':result}
            if 'inputs' in files:
                from tools.capacity_demand import bind_request
                sizing=load_private(files['sizing'])
                artifacts.update({'capacity-request.json':request,'sizing.json':sizing,
                    'demand.json':bind_request(request,load_private(files['inputs']),sizing,current=False)})
            for name,value in artifacts.items(): retain(directory/name,encoded(value))
            return complete(step,packet,directory,plan,result,list(artifacts))
        if kind=='remote_owner':
            return remote_dispatch(step,packet,directory,plan,observe=True,recovery_authority=recovery_authority)
        if kind=='edge_containment':
            from tools.edge_contain import execute
            import uuid
            files=file_paths(packet); values=packet['parameters']
            original=directory/'execution/containment.json'
            if not original.exists():
                folder=directory/('observation-'+uuid.uuid4().hex)
                execute(load_private(files['spec']),load_private(files['authority']),values['nft'],
                        owner_ledger(base,'edge_policy'),folder,observe_only=True)
                original=folder/'containment.json'
            result=load_private(original)
            require(result['status']=='CONTAINED_OBSERVED_NOT_QUALIFIED' and result['scope']==plan['scope']
                    and result['spec_sha256']==digest(encoded(load_private(files['spec'])))
                    and result['authority_sha256']==digest(encoded(load_private(files['authority']))),
                    'Recovered incident receipt changed')
            retain(directory/'containment.json',read_private(original))
            return complete(step,packet,directory,plan,result,['containment.json'])
        if kind=='restic':
            files=file_paths(packet); values=packet['parameters']; config=load_private(files['config'])
            match_scope(config['scope'],plan)
            context=load_private(directory/'execution/context.json')
            original=load_private(files['receipt']) if 'receipt' in files else None
            expected=load_private(files['manifest']) if 'manifest' in files else None
            authority=load_private(files['restore_authority']) if 'restore_authority' in files else None
            require(context=={'action':values['action'],'config_sha256':digest(encoded(config)),
                'receipt_sha256':digest(encoded(original)) if original is not None else None,
                'manifest_sha256':digest(encoded(expected)) if expected is not None else None,
                'authority_sha256':digest(encoded(authority)) if authority is not None else None,
                'machine_id':config['machine_id'] if values['action']=='backup' else authority['machine_id'],
                'target':values['target']},'Interrupted backup execution context differs')
            result=load_private(directory/'execution/receipt.json')
            require(result['scope']==config['scope'] and result['member']==config['member'],
                    'Interrupted backup receipt scope differs')
            names=['receipt.json','context.json']
            if values['action']=='backup':
                manifest=load_private(directory/'execution/manifest.json')
                require(result['status']=='CAPTURED_REQUIRES_RESTORE_TEST'
                        and result['repository_id']==config['repository_id'] and result['source']==config['source']
                        and result['manifest_path']==str(directory/'execution/manifest.json')
                        and result['manifest_sha256']==digest(encoded(manifest))
                        and result['file_count']==len(manifest['files']),'Interrupted backup completion differs')
                names.append('manifest.json')
            else:
                require(result['status']=='RESTORED_FILE_BYTES_VERIFIED_NOT_APPLICATION_ACCEPTED'
                        and result['snapshot_id']==original['snapshot_id'] and result['file_count']==len(expected['files'])
                        and result['production_activation'] is False,'Interrupted restore completion differs')
            for name in names: retain(directory/name,read_private(directory/'execution'/name))
            return complete(step,packet,directory,plan,result,names)
        if kind in {'terraform_apply','guest_apply'}:
            prepared=prepared_directory(step,packet,plan,base)
            require(read_private(prepared/'bundle.json')==read_private(prepared.parent/'bundle.json'),'Interrupted bundle changed')
            bundle=load_private(prepared/'bundle.json'); result=load_private(prepared/'result.json')
            match_scope(bundle['scope'],plan)
            require(bundle['source_commit']==plan['source_commit'] and result['bundle_sha256']==digest(read_private(prepared/'bundle.json'))
                    and result['operation_id']==bundle['operation_id'] and result['generation']==bundle['generation'],
                    'Interrupted owner completion binding changed')
            if kind=='terraform_apply':
                from tools.terraform_apply import scope_ledger
                from tools.wsd_handoff import execution_outputs
                execution_outputs(prepared,bundle['scope']['phase'])
                address=load_private(prepared/'backend.json')['address']
                with scope_ledger(owner_ledger(base,'terraform'),address,bundle['scope']) as owned:
                    require(c.digest(load_private(owned/'head.json'))==c.digest(result),'Later Terraform work superseded this handoff')
                originals={'result.json':'result.json','outputs.json':'outputs.json'}
            else:
                from tools.guest_apply import scope_ledger
                require(result['mode']==bundle['mode'] and result['source_commit']==bundle['source_commit'],'Guest execution identity changed')
                with scope_ledger(owner_ledger(base,'guest'),bundle['scope']) as owned:
                    require(c.digest(load_private(owned/'head.json'))==c.digest(result),'Later guest work superseded this handoff')
                require(digest(read_private(prepared/'runtime/stats.json'))==result['stats_sha256'],'Interrupted guest statistics changed')
                originals={'result.json':'result.json','stats.json':'runtime/stats.json'}
            for name,original in originals.items(): retain(directory/name,read_private(prepared/original))
            return complete(step,packet,directory,plan,result,list(originals))
        if kind=='vsphere_power':
            from tools.vsphere_power import Client,execute
            # This path can only resume observation. Renewing authority never
            # grants permission to redispatch the original power POST.
            files=file_paths(packet); request=load_private(files['request'])
            authority=load_private(recovery_authority or files['authority'])
            client=Client(request,read_private(files['session']).decode().strip(),files.get('ca_file'))
            result=execute(request,authority,owner_ledger(base,'power'),client,resume=True,root=root)
            retain(directory/'result.json',encoded(result))
            return complete(step,packet,directory,plan,result,['result.json'])
    completed=load_private(directory/'owner-completion.json')
    c.exact_keys(completed,{'format','plan_sha256','step_id','packet_sha256','status','artifacts'})
    require(completed['format']=='hosting-delivery-owner-completion/1' and completed['plan_sha256']==c.digest(plan)
            and completed['step_id']==step['id'] and completed['packet_sha256']==c.digest(packet), 'Owner completion binding differs')
    require(artifact_receipt(directory,list(completed['artifacts']))==completed['artifacts'], 'Owner completion artifacts changed')
    return {'status':completed['status']},list(completed['artifacts'])+['owner-completion.json']
