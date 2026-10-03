"""Optional predelegated failure containment, independent of forward-stage success."""
from contextlib import contextmanager
from pathlib import Path
import uuid
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import current_window,digest,encoded,load_private,private_path,read_private,require,sync_directory,write_new


def validate(config,plan):
    remote=config.get('format')=='hosting-delivery-containment/2'
    common={'format','plan_sha256','trigger_steps'}
    c.exact_keys(config,common|({'job','target','ssh_key','ssh_certificate','ssh','ssh_sha256'} if remote
                              else {'spec','authority','nft','nft_sha256'}))
    require(config['format'] in {'hosting-delivery-containment/1','hosting-delivery-containment/2'}
            and config['plan_sha256']==c.digest(plan),
            'Incident containment belongs to another delivery')
    require(isinstance(config['trigger_steps'],list) and config['trigger_steps']
            and len(config['trigger_steps'])==len(set(config['trigger_steps']))
            and set(config['trigger_steps'])<={s['id'] for s in plan['steps']}, 'Exact bounded failure trigger set required')
    for name in ('job','target','ssh_key','ssh_certificate') if remote else ('spec','authority'):
        c.exact_keys(config[name],{'path','sha256'})
        require(digest(read_private(config[name]['path']))==config[name]['sha256'],'Incident containment input changed')
    if remote:
        from tools import owner_worker,remote_owner
        job=load_private(config['job']['path']); owner_worker.validate(job)
        require(job['kind']=='edge_containment' and job['scope']==plan['scope']
                and job['source_commit']==plan['source_commit'] and job['delivery']=={
                    'plan_sha256':c.digest(plan),'step_id':'incident-containment','dependencies':{}},
                'Remote incident job must bind only this delivery boundary')
        current_window(job)
        target=load_private(config['target']['path']); remote_owner.validate(target,job)
        binary=Path(config['ssh'])
        require(binary.is_absolute() and binary.is_file() and digest(binary.read_bytes())==config['ssh_sha256'],
                'Incident transport executable changed')
        return target
    binary=Path(config['nft'])
    require(binary.is_absolute() and binary.is_file() and digest(binary.read_bytes())==config['nft_sha256'],'Incident containment executable changed')
    spec=load_private(config['spec']['path']); authority=load_private(config['authority']['path'])
    from tools.nft_edge import validate as validate_edge
    validate_edge(spec)
    require(spec['scope']==plan['scope'] and spec['nft_sha256']==config['nft_sha256'],'Foreign incident edge boundary')
    require(authority['format']=='hosting-edge-containment-authority/1' and authority['spec_sha256']==digest(encoded(spec)),
            'Incident authority must permit only exact owned-boundary containment')
    from tools.edge_contain import authorize
    authorize(spec,authority)
    return authority


def execute(config,plan,step_id,base,root):
    from tools.delivery_steps import child,owner_ledger
    parent=base/'containment'
    if not parent.exists(): parent.mkdir(mode=0o700); sync_directory(parent.parent)
    private_path(parent,directory=True)
    directory=parent/('attempt-'+uuid.uuid4().hex); directory.mkdir(mode=0o700); sync_directory(parent)
    write_new(directory/'trigger.json',encoded({'plan_sha256':c.digest(plan),'step_id':step_id,
        'containment_sha256':c.digest(config),'at':c.now()}))
    try:
        authority=validate(config,plan); current_window(authority)
        if config['format']=='hosting-delivery-containment/2':
            from tools import remote_owner,owner_worker
            job=load_private(config['job']['path'])
            response=remote_owner.contact(job,authority,config['ssh'],config['ssh_key']['path'],
                                          config['ssh_certificate']['path'],directory)
            write_new(directory/'remote-result.json',encoded(response))
            raw=owner_worker.check_result(response,job)['containment.json']
            write_new(directory/'containment.json',raw); result=c.strict_loads(raw)
            require(abs((c.timestamp(c.now())-c.timestamp(result['observed_at'])).total_seconds())<=5,
                    'Remote containment observation is stale or clocks disagree')
        else:
            remaining=(c.timestamp(authority['valid_until'])-c.timestamp(c.now())).total_seconds()
            child(root,'edge_contain.py',['--spec',config['spec']['path'],'--authority',config['authority']['path'],
                '--nft',config['nft'],'--ledger',owner_ledger(base,'edge_policy'),'--output',directory/'execution','--execute'],
                directory,timeout=min(60,remaining))
            result=load_private(directory/'execution/containment.json')
        require(result['status']=='CONTAINED_OBSERVED_NOT_QUALIFIED' and result['scope']==plan['scope'],
                'Incident containment was not observed')
        write_new(directory/'result.json',encoded(result))
        return result
    except BaseException as exc:
        write_new(directory/'failure.json',encoded({'status':'CONTAINMENT_UNCONFIRMED','error_class':type(exc).__name__,
                                                  'at':c.now(),'production_activation':False}))
        raise


@contextmanager
def guard(config,plan,context,root):
    try:
        yield
    except BaseException as exc:
        # Run inside the delivery scope lock. Failure never advances the graph,
        # authorizes rollback, clears an owner hold or enables a new flow.
        # Read-only reviewers can explicitly hold ordinary reconciliation
        # without requesting withdrawal; all other failures remain
        # containment-eligible by default.
        containment_required=getattr(exc,'containment_required',True)
        if (containment_required and config is not None and not context.get('containment_attempted')
                and context.get('base') is not None and context.get('step_id') in config['trigger_steps']):
            try: execute(config,plan,context['step_id'],context['base'],root)
            except BaseException: pass  # Preserve the original failure and private containment evidence.
        raise
