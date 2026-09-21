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
    'capacity': ({'action','database'}, {'request','authority'}, {'native_ids'}),
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
    for binary in ('terraform','python','ssh','nft'):
        if binary in values:
            path=Path(values[binary])
            require(path.is_absolute() and path.is_file() and os.access(path,os.X_OK)
                    and digest(path.read_bytes())==values[binary+'_sha256'], 'Delivery executable changed')
    if kind in {'terraform_apply','guest_apply'}:
        upstream=dependency(step,values['prepared_step'], 'terraform_plan' if kind=='terraform_apply' else 'guest_plan',plan,base)
        require(read_private(upstream/'bundle.json')==read_private(upstream/'execution/bundle.json'), 'Prepared owner bundle changed')
        bundle=load_private(upstream/'bundle.json'); match_scope(bundle['scope'],plan)
        require(bundle['source_commit']==plan['source_commit'],'Prepared owner source changed')
    if kind=='guest_plan':
        dependency(step,values['workload_step'],'terraform_apply',plan,base)
        match_scope(load_private(files['access'])['scope'],plan)
        require(values['mode'] in {'check','configure'} and type(values['max_seconds']) is int
                and 30<=values['max_seconds']<=3600, 'Invalid guest execution bounds')
    if kind=='terraform_plan':
        from tools.terraform_run import select_scope
        from tools.delivery_run import ROOT
        _,scope,_=select_scope(ROOT,values['catalog_id'],load_private(files['inputs']))
        match_scope(scope,plan)
    if kind=='acceptance':
        require(values['purpose'] in {'admission','domain','bootstrap','services','activation','post_activation','recovery','retirement'}, 'Unknown acceptance gate')
        accepted=load_private(files['acceptance'])
        c.exact_keys(accepted, {'format','plan_sha256','step_id','scope','dependencies','purpose','valid_from','valid_until','acceptance_ref'})
        require(accepted['format']=='hosting-delivery-acceptance/1' and accepted['plan_sha256']==c.digest(plan)
                and accepted['step_id']==step['id'] and accepted['dependencies']==packet['dependencies']
                and accepted['purpose']==values['purpose'], 'Acceptance does not bind this delivery gate')
        match_scope(accepted['scope'],plan); c.text(accepted['acceptance_ref']); current_window(accepted)
    if kind in {'edge_policy','target_campaign','ipam','dns','capacity'}:
        field={'edge_policy':'spec','target_campaign':'plan','ipam':'request','dns':'allocation','capacity':'request'}[kind]
        value=load_private(files[field]); match_scope(value['scope'],plan)
        if kind=='target_campaign': require(value['source_commit']==plan['source_commit'], 'Foreign campaign source')
        if kind=='edge_policy': require(values['mode'] in {'withdraw','bootstrap','active'}, 'Unknown edge transition')
        if kind=='ipam':
            from tools.netbox_ipam import ACTIONS
            require(values['action'] in ACTIONS,'Unknown IPAM operation')
        if kind=='dns':
            from tools.netbox_dns import ACTIONS
            require(values['action'] in ACTIONS,'Unknown DNS operation')
        if kind=='capacity':
            require(values['action'] in {'reserve','confirm','release'},'Unknown capacity transition')
            private_path(values['database'])
    if kind=='vsphere_power':
        from tools.vsphere_power import validate
        request=load_private(files['request']); validate(request)
        require(plan['scope']['platform']=='vmware' and request['source_commit']==plan['source_commit']
                and request['snapshot']['tenant_id']==plan['scope']['tenant_key']
                and request['snapshot']['scope_id']==plan['scope']['wsd_key'], 'Foreign native power handoff')


def owner_ledger(base, owner):
    # Native owner ledgers are shared across all delivery scopes/generations.
    # A new operation directory must never reset an owner's uncertainty hold.
    parent=base.parents[2]/'owners'
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
    if kind=='capacity':
        from tools.capacity import operate
        result=operate(values['database'],load_private(files['request']),values['action'],load_private(files['authority']),
                       load_private(files['native_ids']) if 'native_ids' in files else None)
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
    from tools.delivery_run import artifact_receipt
    completion={'format':'hosting-delivery-owner-completion/1','plan_sha256':c.digest(plan),'step_id':step['id'],
                'packet_sha256':c.digest(packet),'status':result['status'],'artifacts':artifact_receipt(directory,names)}
    write_new(directory/'owner-completion.json',encoded(completion))
    return result,names+['owner-completion.json']


def recover(step, packet, directory, base, plan, root):
    """Only recover durable completion; never rerun an uncertain owner operation."""
    from tools.delivery_run import artifact_receipt
    completed=load_private(directory/'owner-completion.json')
    c.exact_keys(completed,{'format','plan_sha256','step_id','packet_sha256','status','artifacts'})
    require(completed['format']=='hosting-delivery-owner-completion/1' and completed['plan_sha256']==c.digest(plan)
            and completed['step_id']==step['id'] and completed['packet_sha256']==c.digest(packet), 'Owner completion binding differs')
    require(artifact_receipt(directory,list(completed['artifacts']))==completed['artifacts'], 'Owner completion artifacts changed')
    return {'status':completed['status']},list(completed['artifacts'])+['owner-completion.json']
