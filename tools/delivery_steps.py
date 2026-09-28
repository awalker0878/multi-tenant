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
    'restic': ({'action','restic','restic_sha256','target'}, {'config','credentials'}, {'ca_bundle','receipt','manifest','restore_authority','transfer_manifest'}),
    'dataset_restore': ({'action','restic','restic_sha256','target','transfer_manifest_sha256','dataset_id','target_ref','consistency_group_id','source_scope'},
                        {'config','credentials','receipt','manifest','restore_authority','transfer_manifest'}, {'ca_bundle'}),
    'dataset_acceptance': ({'group_id','datasets'}, set(), set()),
    'platform_transition': ({'prior_step','stage'}, {'inputs','acceptance'}, set()),
    'workload_inputs': ({'domain_steps','selected_input'}, {'environment'}, {'vmware_bindings'}),
    'capacity': ({'action','database'}, {'request','authority'}, {'native_ids','inputs','sizing'}),
    'acceptance': ({'purpose'}, {'acceptance'}, set()),
    'retirement_review': (set(), {'plan','evidence'}, set()),
    'operations_review': (set(), {'review'}, set()),
    'operations_alerts': (set(), {'review', 'result', 'acknowledgements'}, {'release'}),
    'terraform_plan': ({'catalog_id','terraform','terraform_sha256'}, {'inputs','backend','environment','authority'}, {'references','cloud','ca_bundle','transition'}),
    'terraform_apply': ({'prepared_step'}, {'approval'}, set()),
    'terraform_approval': ({'prepared_step'}, {'approval'}, set()),
    'guest_plan': ({'workload_step','python','python_sha256','ssh','ssh_sha256','mode','max_seconds'}, {'access','references','ssh_key','ssh_certificate'}, set()),
    'guest_apply': ({'prepared_step'}, {'approval'}, set()),
    'vsphere_power': ({'workload_step','member'}, {'request','authority','session'}, {'ca_file'}),
    'target_campaign': ({'ssh','ssh_sha256'}, {'plan','authority'}, set()),
    'edge_policy': ({'nft','nft_sha256','mode'}, {'spec','authority'}, set()),
    'ipam': ({'action'}, {'request','authority','token_file'}, {'ca_bundle','release_evidence'}),
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
    if kind in {'restic','dataset_restore'}:
        from tools.restic_run import validate
        config=load_private(files['config']); validate(config)
        transfer=restic_transfer(packet,files,plan)
        if kind=='dataset_restore': dataset_binding(values,transfer)
        require(config['restic_sha256']==values['restic_sha256'],'Backup executable binding changed')
        require(values['action'] in {'backup','restore'},'Unknown backup transition')
        restore_files={'receipt','manifest','restore_authority'}
        if values['action']=='backup':
            require(values['target'] is None and not (restore_files|{'transfer_manifest'}).intersection(files),'Backup cannot carry restore inputs')
        else:
            require(restore_files.issubset(files) and isinstance(values['target'],str)
                    and Path(values['target']).is_absolute(),'Exact restore input set required')
    if kind in {'terraform_apply','terraform_approval','guest_apply'}:
        upstream=dependency(step,values['prepared_step'], 'terraform_plan' if kind in {'terraform_apply','terraform_approval'} else 'guest_plan',plan,base)
        require(read_private(upstream/'bundle.json')==read_private(upstream/'execution/bundle.json'), 'Prepared owner bundle changed')
        bundle=load_private(upstream/'bundle.json'); match_scope(bundle['scope'],plan)
        require(bundle['source_commit']==plan['source_commit'],'Prepared owner source changed')
        if kind=='terraform_approval':
            from tools.terraform_apply import validate_bundle
            from tools.delivery_run import ROOT
            prior=load_private(upstream/'packet.json')['parameters']
            validate_bundle(upstream/'execution',load_private(files['approval']),Path(prior['terraform']),ROOT)
        if kind=='terraform_apply':
            approvals=[item for item in plan['steps'] if item['id'] in step['needs']
                       and item['kind']=='terraform_approval']
            for approval_step in approvals:
                approved=base/'steps'/approval_step['id']
                accepted=load_private(approved/'result.json')
                require(accepted['status']=='EXACT_TERRAFORM_PLAN_APPROVAL_RECORDED'
                        and accepted['bundle_sha256']==digest(read_private(upstream/'bundle.json'))
                        and read_private(approved/'approval.json')==read_private(files['approval']),
                        'Apply approval differs from its explicit reviewed-plan gate')
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
        transitions=[item for item in plan['steps'] if item['id'] in step['needs']
                     and item['kind']=='platform_transition']
        require(len(transitions)<=1,'One exact lifecycle transition per saved plan required')
        if transitions:
            require('transition' in files,'Lifecycle plan requires its prepared transition')
            original=base/'steps'/transitions[0]['id']/'transition.json'
            require(read_private(original)==read_private(files['transition']),
                    'Lifecycle plan changed its prepared transition')
            from tools.lifecycle_transition import validate as validate_transition
            validate_transition(load_private(original),scope,read_private(files['inputs']))
        if scope['phase']=='workloads':
            from tools.capacity_demand import check_ancestors
            check_ancestors(step,plan,base,load_private(files['inputs']),
                            cloud_sha256=digest(read_private(files['cloud'])) if 'cloud' in files else None)
    if kind=='dataset_acceptance': dataset_group(step,packet,base,plan)
    if kind=='retirement_review':
        from tools.retirement import validate_evidence
        retirement_plan=load_private(files['plan'])
        require(retirement_plan['source_commit']==plan['source_commit']
                and retirement_plan['scope']==plan['scope'], 'Foreign retirement review')
        validate_evidence(retirement_plan,load_private(files['evidence']))
    if kind=='operations_review':
        from tools.operations_review import validate
        operations=load_private(files['review']); validate(operations)
        require(operations['source_commit']==plan['source_commit']
                and operations['scope']==plan['scope'], 'Foreign operations review')
    if kind=='operations_alerts':
        from tools.operations_alerts import validate_acknowledgement,validate_release,validate_result
        from tools.operations_review import validate as validate_review
        review=load_private(files['review']); result=load_private(files['result'])
        validate_review(review); validate_result(result)
        require(review['source_commit']==plan['source_commit']
                and result['review_sha256']==c.digest(review) and result['scope']==plan['scope'],
                'Foreign operations alert review')
        for record in load_private(files['acknowledgements']): validate_acknowledgement(result,record)
        if 'release' in files: validate_release(result,load_private(files['release']))
    if kind=='acceptance':
        require(values['purpose'] in {'admission','domain','bootstrap','services','activation','post_activation','recovery','retirement'}, 'Unknown acceptance gate')
        accepted=load_private(files['acceptance'])
        c.exact_keys(accepted, {'format','plan_sha256','step_id','scope','dependencies','purpose','valid_from','valid_until','acceptance_ref'})
        require(accepted['format']=='hosting-delivery-acceptance/1' and accepted['plan_sha256']==c.digest(plan)
                and accepted['step_id']==step['id'] and accepted['dependencies']==packet['dependencies']
                and accepted['purpose']==values['purpose'], 'Acceptance does not bind this delivery gate')
        match_scope(accepted['scope'],plan); c.text(accepted['acceptance_ref']); current_window(accepted)
        if values['purpose']=='bootstrap': bootstrap_postconditions(step,plan,base)
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
            from tools.netbox_ipam import ACTIONS, RELEASE_ACTIONS
            require(values['action'] in ACTIONS,'Unknown IPAM operation')
            require(('release_evidence' in files)==(values['action'] in RELEASE_ACTIONS),
                    'Reuse quarantine evidence is required exactly for quarantine and release')
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
        request=load_private(files['request']); resource=validate(request)
        upstream=dependency(step,values['workload_step'],'terraform_apply',plan,base)
        execution=terraform_execution(values['workload_step'],plan,base)
        from tools.wsd_handoff import execution_outputs
        outputs,_,_=execution_outputs(execution,'workloads')
        member=outputs['members']['value'].get(values['member'])
        require(member is not None and resource['expected']['config']['uuid']==member['vm_id']
                and request['desired_power']=='poweredOn',
                'Bootstrap power must bind the exact applied workload UUID and power-on intent')
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


def dispatch(step, packet, directory, base, plan, root, *, transfer_guard=None):
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
    elif kind in {'restic','dataset_restore'}:
        from tools.restic_run import execute
        if kind=='dataset_restore':
            from tools.restic_transfer import TransferGuard
            require(isinstance(transfer_guard,TransferGuard) and transfer_guard.step_id==step['id'],
                    'Dataset restore requires live trusted worker authority for this exact child step')
        result=execute(values['action'],load_private(files['config']),load_private(files['credentials']),
            values['restic'],directory/'execution',ca_file=files.get('ca_bundle'),
            receipt=load_private(files['receipt']) if 'receipt' in files else None,
            expected=load_private(files['manifest']) if 'manifest' in files else None,target=values['target'],
            authority=load_private(files['restore_authority']) if 'restore_authority' in files else None,
            transfer=load_private(files['transfer_manifest']) if 'transfer_manifest' in files else None,
            transfer_guard=transfer_guard)
        if 'transfer_manifest' in files:
            result=load_private(directory/'execution/transfer-receipt.json')
        for name in (('receipt.json','context.json') + (('manifest.json',) if values['action']=='backup' else ())
                     + (('transfer-manifest.json','transfer-receipt.json') if 'transfer_manifest' in files else ())):
            write_new(directory/name,read_private(directory/'execution'/name)); names.append(name)
    elif kind=='platform_transition':
        from tools.lifecycle_transition import prepare
        prior=terraform_execution(values['prior_step'],plan,base)
        record=prepare(prior,files['inputs'],files['acceptance'],values['stage'])
        match_scope(record['scope'],plan)
        write_new(directory/'transition.json',encoded(record)); names=['transition.json']
        result={'status':'TRANSITION_REQUIRES_EXACT_PLAN_REVIEW'}
    elif kind=='workload_inputs':
        from tools.wsd_handoff import compile_scope_runs
        records=[terraform_execution(selected,plan,base) for selected in values['domain_steps']]
        outputs,scopes,provenance=compile_scope_runs(load_private(files['environment']),records,plan['scope'],
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
    elif kind=='dataset_acceptance':
        result=dataset_group(step,packet,base,plan)
        write_new(directory/'result.json',encoded(result)); names=['result.json']
    elif kind=='retirement_review':
        from tools.retirement import evaluate
        result=evaluate(load_private(files['plan']),load_private(files['evidence']))
        write_new(directory/'retirement-review.json',encoded(result))
        names=['retirement-review.json']
    elif kind=='operations_review':
        from tools.operations_review import enforce,evaluate
        result=evaluate(load_private(files['review']))
        alerts={'format':'hosting-operations-alerts/1','review_sha256':result['review_sha256'],
                'alerts':result['alerts']}
        write_new(directory/'operations-review.json',encoded(result))
        write_new(directory/'alerts.json',encoded(alerts))
        names=['operations-review.json','alerts.json']
        enforce(result)
    elif kind=='operations_alerts':
        from tools.operations_alerts import enforce,evaluate
        review=load_private(files['review']); report=load_private(files['result'])
        require(report['format']=='hosting-operations-review-result/1'
                and report['review_sha256']==c.digest(review) and report['scope']==plan['scope'],
                'Foreign operations alert review')
        result=evaluate(review,report,load_private(files['acknowledgements']),
                        release=load_private(files['release']) if 'release' in files else None)
        write_new(directory/'alert-accounting.json',encoded(result))
        names=['alert-accounting.json']
        enforce(result)
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
    elif kind=='terraform_approval':
        upstream=dependency(step,values['prepared_step'],'terraform_plan',plan,base)
        approval=load_private(files['approval'])
        write_new(directory/'approval.json',encoded(approval))
        result={'status':'EXACT_TERRAFORM_PLAN_APPROVAL_RECORDED',
                'bundle_sha256':digest(read_private(upstream/'bundle.json')),
                'approval_sha256':digest(encoded(approval))}
        write_new(directory/'result.json',encoded(result)); names=['approval.json','result.json']
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
            require(result.get('allocation_status') in {'reserved','active','deprecated','QUARANTINED','RELEASED'},'IPAM allocation remains held')
    if not names:
        write_new(directory/'result.json',encoded(result)); names=['result.json']
    return complete(step,packet,directory,plan,result,names)


def complete(step,packet,directory,plan,result,names):
    from tools.delivery_run import artifact_receipt
    typed_postcondition(step,result,directory,packet,plan)
    completion={'format':'hosting-delivery-owner-completion/1','plan_sha256':c.digest(plan),'step_id':step['id'],
                'packet_sha256':c.digest(packet),'status':result['status'],'artifacts':artifact_receipt(directory,names)}
    write_new(directory/'owner-completion.json',encoded(completion))
    return result,names+['owner-completion.json']


def dataset_binding(values,transfer):
    require(values['action']=='restore' and transfer is not None,
            'Dataset restore requires an exact cross-scope transfer')
    spec=transfer['transfer']['spec']
    require(values['source_scope']==transfer['source_execution_scope']
            and values['transfer_manifest_sha256']==digest(encoded(transfer))
            and (values['dataset_id'],values['target_ref'],values['consistency_group_id'])==
                (spec['datasetId'],spec['targetRef'],spec['consistencyGroupId']),
            'Dataset restore differs from the reviewed manifest or mapping')


def dataset_group(step,packet,base,plan):
    from tools.dataset_acceptance import validate_group
    values=packet['parameters']; datasets=values['datasets']
    require(isinstance(datasets,list) and datasets,'A dataset group requires every declared member')
    require(set(step['needs'])=={row['step_id'] for row in datasets},
            'Dataset group must depend on exactly its declared restore steps')
    records={}
    for row in datasets:
        path=dependency(step,row['step_id'],'dataset_restore',plan,base)
        records[row['step_id']]={
            'transfer_manifest':load_private(path/'transfer-manifest.json'),
            'transfer_receipt':load_private(path/'transfer-receipt.json'),
            'restore_receipt':load_private(path/'receipt.json')}
    return validate_group(values['group_id'],datasets,records,plan['scope'])


def restic_transfer(packet,files,plan):
    """Separate source ownership from the destination transfer evidence.

    The envelope is evidence, not authority. The owner still requires a trusted
    runtime TransferGuard before any cross-scope restore can contact restic.
    """
    config=load_private(files['config'])
    if 'transfer_manifest' not in files:
        match_scope(config['scope'],plan)
        return None
    from tools.restic_transfer import validate
    require(packet['parameters']['action']=='restore', 'Backup cannot carry a transfer manifest')
    require({'receipt','manifest','restore_authority'}<=set(files),'Exact transfer restore inputs required')
    transfer=load_private(files['transfer_manifest'])
    validate(transfer,config,load_private(files['receipt']),load_private(files['manifest']),
             packet['parameters']['target'])
    match_scope(transfer['destination_execution_scope'],plan)
    return transfer


def campaign_postcondition(result, campaign, raw):
    """A collection status alone cannot discharge native/traffic verification."""
    from tools.qualify_target import validate
    cases=validate(campaign)
    require(isinstance(result,dict)
            and result.get('status')=='COLLECTED_REQUIRES_INDEPENDENT_ACCEPTANCE'
            and result.get('scope')==campaign['scope']
            and result.get('source_commit')==campaign['source_commit']
            and result.get('plan_sha256')==digest(raw)
            and result.get('production_qualified') is False,
            'Campaign completion is not bound to the exact native observation plan')
    for key in ('native_before_sha256','native_after_sha256'):
        require(isinstance(result.get(key),str) and c.HEX.fullmatch(result[key]),
                'Campaign requires native observations before and after traffic')
    observations=result.get('cases')
    require(isinstance(observations,list) and len(observations)==len(cases)
            and {row.get('id') for row in observations}==set(cases)
            and all(row.get('passed') is True for row in observations),
            'Campaign requires every exact traffic case to pass')
    require(c.timestamp(result['started_at'])<=c.timestamp(result['completed_at'])<=c.timestamp(c.now()),
            'Campaign completion chronology is invalid')


def typed_postcondition(step,result,directory,packet,plan):
    """Validate the owner's typed result before publishing a completion marker.

    These statuses keep planning, application, observation and independent
    acceptance distinct. None grants production activation.
    """
    expected={
        'platform_transition':'TRANSITION_REQUIRES_EXACT_PLAN_REVIEW',
        'workload_inputs':'BOUND_WORKLOAD_DRAFT_REQUIRES_REVIEW',
        'terraform_plan':'AWAITING_EXACT_PLAN_REVIEW',
        'terraform_approval':'EXACT_TERRAFORM_PLAN_APPROVAL_RECORDED',
        'terraform_apply':'APPLIED_REQUIRES_NATIVE_ACCEPTANCE',
        'vsphere_power':'POWER_CHANGED_REQUIRES_NATIVE_ACCEPTANCE',
        'dataset_restore':'RESTORED_FILE_BYTES_VERIFIED_NOT_APPLICATION_ACCEPTED',
        'dataset_acceptance':'DATASET_GROUP_FILE_BYTES_VERIFIED_NOT_APPLICATION_ACCEPTED',
    }
    if step['kind'] in expected:
        require(result.get('status')==expected[step['kind']],
                'Delivery owner has not met its typed postcondition')
    if step['kind']=='target_campaign':
        raw=read_private(packet['files']['plan']['path'])
        campaign_postcondition(result,c.strict_loads(raw),raw)
    if step['kind']=='vsphere_power':
        request=load_private(packet['files']['request']['path'])
        require(result.get('request_sha256')==c.digest(request)
                and result.get('native_acceptance') is False
                and result.get('production_activation') is False,
                'Power result changed its exact operation binding')


def bootstrap_postconditions(step,plan,base):
    """Refuse external bootstrap acceptance until real native effects exist.

    Transition preparation is only a review input. Require successful exact-plan
    applies, every VMware power operation, and a native/traffic campaign, all as
    explicit dependencies with the same workload outputs.
    """
    from tools.wsd_handoff import execution_outputs
    dependencies=[item for item in plan['steps'] if item['id'] in step['needs']]
    require(not any(item['kind']=='platform_transition' for item in dependencies),
            'A transition draft cannot satisfy bootstrap acceptance')
    applies=[item for item in dependencies if item['kind']=='terraform_apply']
    executions={}
    for item in applies:
        directory=terraform_execution(item['id'],plan,base)
        bundle=load_private(directory/'bundle.json')
        outputs,_,_=execution_outputs(directory,bundle['scope']['phase'])
        require('transition.json' in bundle['artifacts'],
                'Bootstrap requires applied lifecycle plans, not initial creation')
        transition=load_private(directory/'transition.json')
        require(transition['scope']==bundle['scope'] and transition['target_stage']=='bootstrap'
                and digest(read_private(directory/'transition.json'))==bundle['artifacts']['transition.json'],
                'Bootstrap apply lacks its exact sealed transition')
        require(bundle['scope']['phase'] not in executions,'Duplicate bootstrap phase')
        executions[bundle['scope']['phase']]=outputs
    require('domains' in executions,'Bootstrap needs an applied native domain transition')
    powers=[item for item in dependencies if item['kind']=='vsphere_power']
    if plan['scope']['platform']=='vmware':
        require(powers and 'workloads' not in executions,'Every VMware workload needs its fenced power owner')
        identities=set()
        for item in powers:
            directory=base/'steps'/item['id']; packet=load_private(directory/'packet.json')
            result=load_private(directory/'result.json')
            typed_postcondition(item,result,directory,packet,plan)
            request=load_private(packet['files']['request']['path'])
            identities.add(request['snapshot']['resources'][0]['expected']['config']['uuid'])
            outputs,_,_=execution_outputs(terraform_execution(packet['parameters']['workload_step'],plan,base),'workloads')
            if 'workloads' in executions:
                require(executions['workloads']==outputs,'Power operations reference different workload applies')
            executions['workloads']=outputs
        require(len(identities)==len(powers) and identities==
                {member['vm_id'] for member in executions['workloads']['members']['value'].values()},
                'Power results must cover every applied VM exactly once')
    else:
        require('workloads' in executions and not powers,'Bootstrap needs applied workload power and NIC transitions')
    campaigns=[item for item in dependencies if item['kind']=='target_campaign']
    require(len(campaigns)==1,'Bootstrap requires one exact native observation campaign')
    directory=base/'steps'/campaigns[0]['id']; packet=load_private(directory/'packet.json')
    raw=read_private(packet['files']['plan']['path']); campaign=c.strict_loads(raw)
    result=load_private(directory/'result.json'); campaign_postcondition(result,campaign,raw)
    require(campaign['format']=={'openstack':'hosting-target-campaign/2',
                                'nutanix':'hosting-target-campaign/4',
                                'vmware':'hosting-target-campaign/8'}[plan['scope']['platform']],
            'Bootstrap campaign must observe native workload and domain bindings')
    asset=campaign['assets']['inventory']; inventory=read_private(asset['path'])
    require(digest(inventory)==asset['sha256'] and
            c.strict_loads(inventory)['all']['vars']['hosting_workload_outputs']==executions['workloads'],
            'Bootstrap campaign observed another workload execution')
    if 'domain_outputs' in campaign['assets']:
        asset=campaign['assets']['domain_outputs']; raw=read_private(asset['path'])
        require(digest(raw)==asset['sha256'] and c.strict_loads(raw)==executions['domains'],
                'Bootstrap campaign observed another domain execution')


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
        if kind=='dataset_acceptance':
            result=dataset_group(step,packet,base,plan)
            retain(directory/'result.json',encoded(result))
            return complete(step,packet,directory,plan,result,['result.json'])
        if kind=='openstack_quota':
            return quota_dispatch(step,packet,directory,base,plan,root,observe=True,recovery_authority=recovery_authority)
        if kind=='dns_propagation':
            return dns_observation(step,packet,directory,base,plan,recovery_authority=recovery_authority)
        if kind=='operations_review':
            from tools.operations_review import OperationsHold
            files=file_paths(packet); review=load_private(files['review'])
            result=load_private(directory/'operations-review.json')
            alerts=load_private(directory/'alerts.json')
            require(result['format']=='hosting-operations-review-result/1'
                    and result['review_sha256']==c.digest(review)
                    and result['scope']==plan['scope']
                    and alerts=={'format':'hosting-operations-alerts/1',
                                 'review_sha256':result['review_sha256'],'alerts':result['alerts']},
                    'Interrupted operations review artifacts changed')
            if result['status']!='OPERATIONS_HEALTHY':
                raise OperationsHold('Operations evidence remains held',
                                     containment_required=result['containment_required'])
            return complete(step,packet,directory,plan,result,['operations-review.json','alerts.json'])
        if kind=='operations_alerts':
            from tools.operations_alerts import AlertHold,validate_acknowledgement
            files=file_paths(packet); review=load_private(files['review'])
            result=load_private(files['result'])
            records=load_private(files['acknowledgements'])
            outcome=load_private(directory/'alert-accounting.json')
            require(outcome['format']=='hosting-operations-alert-accounting/1'
                    and outcome['review_sha256']==c.digest(review)
                    and result['review_sha256']==c.digest(review)
                    and outcome['scope']==plan['scope']
                    and [row['observation_id'] for row in outcome['alerts']]
                    ==[alert['observation_id'] for alert in result['alerts']],
                    'Interrupted operations alert artifacts changed')
            for record in records:
                validate_acknowledgement(result,record)
                row=next((item for item in outcome['alerts']
                          if item['observation_id']==record['observation_id']),None)
                require(row is not None and row['acknowledged_by']==record['acknowledged_by']
                        and row['acknowledged_at']==record['acknowledged_at'],
                        'Interrupted operations alert acknowledgement changed')
            if outcome['status'] not in {'ALERTS_ACKNOWLEDGED','ALERTS_NONE'}:
                raise AlertHold('Operations alert escalation requires accountable resolution',
                                escalate=outcome['status']=='ALERTS_ESCALATED')
            if outcome['release_requested'] and not outcome['containment_release_authorized']:
                raise AlertHold(f"Containment release is not authorized: {outcome['release_blocked_reason']}")
            return complete(step,packet,directory,plan,outcome,['alert-accounting.json'])
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
        if kind in {'restic','dataset_restore'}:
            files=file_paths(packet); values=packet['parameters']; config=load_private(files['config'])
            transfer=restic_transfer(packet,files,plan)
            if kind=='dataset_restore': dataset_binding(values,transfer)
            context=load_private(directory/'execution/context.json')
            original=load_private(files['receipt']) if 'receipt' in files else None
            expected=load_private(files['manifest']) if 'manifest' in files else None
            authority=load_private(files['restore_authority']) if 'restore_authority' in files else None
            require(context=={'action':values['action'],'config_sha256':digest(encoded(config)),
                'receipt_sha256':digest(encoded(original)) if original is not None else None,
                'manifest_sha256':digest(encoded(expected)) if expected is not None else None,
                'authority_sha256':digest(encoded(authority)) if authority is not None else None,
                'machine_id':config['machine_id'] if values['action']=='backup' else authority['machine_id'],
                'target':values['target']} | ({'transfer_manifest_sha256':digest(encoded(transfer))}
                                            if transfer is not None else {}),
                    'Interrupted backup execution context differs')
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
            if transfer is not None:
                from tools.restic_transfer import destination_receipt
                require(load_private(directory/'execution/transfer-manifest.json')==transfer,
                        'Interrupted transfer manifest changed')
                destination=load_private(directory/'execution/transfer-receipt.json')
                require(destination==destination_receipt(transfer,original,result),
                        'Interrupted destination receipt changed')
                result=destination
                names.extend(['transfer-manifest.json','transfer-receipt.json'])
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
    result=load_private(directory/'result.json') if (directory/'result.json').exists() else {'status':completed['status']}
    require(result.get('status')==completed['status'],'Retained owner status changed')
    typed_postcondition(step,result,directory,packet,plan)
    if step['kind']=='dataset_acceptance':
        require(result==dataset_group(step,packet,base,plan),'Retained dataset group evidence changed')
    if step['kind']=='acceptance' and packet['parameters']['purpose']=='bootstrap':
        bootstrap_postconditions(step,plan,base)
    return result,list(completed['artifacts'])+['owner-completion.json']
