"""Q04 actual TLS owners, PostgreSQL stores, Temporal histories and Console journey."""
import copy
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import time
import uuid
from temporal_fixture import TemporalFixture


def effect_headers(grant, credential):
    material={'path':'/v1/effects','body':grant}
    replay=hashlib.sha256(json.dumps(material,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return {'Authorization':'Bearer '+credential,'Idempotency-Key':replay}


def epoch_isolation(grant, lifecycle_epoch, simulator_epoch, send, effect_count, check):
    """Use the same fresh durable grant for two independent fences and a positive control.

    This is an isolated simulation fault injection before the restore exercise.
    Never use it to re-enable a restored journal or extend a grant's authority.
    """
    original=grant['epoch']
    if lifecycle_epoch.read_text()!=original or simulator_epoch.read_text()!=original:
        raise RuntimeError('epoch_probe_requires_current_custody')
    before=effect_count()
    rows=[]
    try:
        for name,file in [('effect-owner',simulator_epoch),('journal-owner',lifecycle_epoch)]:
            file.write_text(str(uuid.uuid4()))
            check('p06-'+name+'-epoch-probe-unexpired-before',grant['expires_at']>int(time.time()))
            status=send(grant)[0]
            check('p06-'+name+'-epoch-probe-unexpired-after',grant['expires_at']>int(time.time()))
            after=effect_count()
            check('p06-'+name+'-epoch-alone-denies',status==403 and after==before)
            rows.append({'owner':name,'status_code':status,'unexpired':True,'effects_before':before,'effects_after':after})
            file.write_text(original)
        check('p06-same-grant-positive-control-unexpired',grant['expires_at']>int(time.time()))
        positive=send(grant)
        check('p06-same-grant-positive-control',positive[0]==200 and positive[1]=={'accepted':True,'duplicate':False} and effect_count()==before+1)
        duplicate=send(grant)
        check('p06-same-grant-duplicate-control',duplicate[0]==200 and duplicate[1]=={'accepted':True,'duplicate':True} and effect_count()==before+1)
        return {'simulation':True,'grant_sha256':hashlib.sha256(json.dumps(grant,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                'negative_controls':rows,'same_grant_positive_status':positive[0],'same_grant_duplicate_status':duplicate[0],
                'effects_after_positive':effect_count(),'restore_reenable_authorized':False}
    finally:
        lifecycle_epoch.write_text(original)
        simulator_epoch.write_text(original)


def security_probes(c, base, tenant, foreign, scope, job, admission, admission_key):
    """Execute authenticated current-authority denials with unchanged durable state.

    Positive controls use these exact requests and the same service credential.
    Every negative request is also validated by the independent wire observer.
    """
    from assurance import inventory, operation_key
    operations={op['key']:op for op in inventory(c['root'])['operations']}
    wire,gov,check=c['wire'],c['gov'],c['check']
    prefix='/v1/tenants/'+tenant
    tables=['execution_jobs','execution_projection','execution_operations','execution_dispatch',
            'execution_holds','execution_commands','execution_events','execution_alerts']
    def state():
        return [c['sql']("SELECT md5(coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)::text,'[]')) FROM app."+table+' t;','lifecycle') for table in tables]+[
            c['sql']("SELECT md5(coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)::text,'[]')) FROM sim.observations t;",'simulation')]
    def grant(action, requested_scope):
        reply=gov(prefix+'/actor-delegations',{'audience':'lifecycle','action':action,'scope':{k:requested_scope[k] for k in ['site_id','environment','resource_id']}},token=c['fixture']['operator_token'])
        c['private_values'].append(reply['delegation_token'])
        return {'Authorization':'Bearer '+c['credentials']['console-lifecycle'][0],
                'X-Actor-Delegation':reply['delegation_token']}
    rows=[]
    # Read a current revision before the positive command changes it.
    read_path=prefix+'/jobs/'+job['id']
    current=wire(base,read_path,headers=grant('operation.read',scope))[1]
    cases=[('POST',prefix+'/jobs','/v1/tenants/{tenant}/jobs','operation.admit',admission,admission_key,202),
           ('GET',read_path,'/v1/tenants/{tenant}/jobs/{job}','operation.read',None,None,200),
           ('POST',read_path+'/commands','/v1/tenants/{tenant}/jobs/{job}/commands','operation.control',
            {'action':'reconcile','expected_revision':current['revision']},str(uuid.uuid4()),202)]
    for method,path,template,action,body,key,expected in cases:
        headers=grant(action,scope)
        if key:headers['Idempotency-Key']=key
        positive=wire(base,path,method,body,headers)
        check('p06-security-positive-'+action,positive[0]==expected)
        wrong_scope=dict(scope,resource_id=str(uuid.uuid4()))
        for kind,target,denied_headers in [
            ('wrong-scope',path,grant(action,wrong_scope)),
            ('cross-tenant',path.replace('/tenants/'+tenant+'/', '/tenants/'+foreign+'/'),grant(action,scope)),
        ]:
            if key:denied_headers['Idempotency-Key']=key
            before=state()
            reply=wire(base,target,method,body,denied_headers)
            measured=c['conformance'].rows[-1]
            after=state()
            # Errors may contain a correlation ID, but never the protected job,
            # immutable plan binding, or its owner scope.
            disclosed=any(value in json.dumps(reply[1]) for value in [job['id'],admission['plan_id'],admission['plan_digest']])
            check('p06-security-'+kind+'-'+action,
                  reply[0] in (403,404) and not disclosed and before==after
                  and measured['request_valid'] is True and measured['response_valid'] is True
                  and measured['owner']=='lifecycle' and measured['path']==template)
            op=operations[operation_key('lifecycle',method,template)]
            rows.append({'key':op['key'],'claim':'authorization' if kind=='wrong-scope' else 'tenant_isolation',
                         'source':'live-denial','result':'PASS','release_sha256':op['release_sha256'],
                         'test':'scripts/p06/live_execution.py:security_probes','denial_kind':kind,
                         'authenticated':True,'authority_checked':'current-effective-authority',
                         'status_code':reply[0],'positive_status_code':positive[0],
                         'credential_tenant':tenant,'requested_tenant':foreign if kind=='cross-tenant' else tenant,
                         'unauthorized_disclosure':False,'unauthorized_mutation':False,
                         'request_valid':True,'response_valid':True,
                         'state_before_sha256':hashlib.sha256(json.dumps(before).encode()).hexdigest(),
                         'state_after_sha256':hashlib.sha256(json.dumps(after).encode()).hexdigest(),
                         'revision':os.environ['GITHUB_SHA'],'run_id':os.environ['GITHUB_RUN_ID'],
                         'run_attempt':os.environ['GITHUB_RUN_ATTEMPT']})
    (c['out']/'security-conformance.json').write_text(json.dumps(rows,indent=2)+'\n')
    return [{'method':method,'tail':path.removeprefix(prefix+'/'),'path':template,
             'body':body or {},'key':key} for method,path,template,_,body,key,_ in cases]


def _campaign(c,p):
    from fault_peers import TlsProxy, AlertReceiver
    root,private,out=c['root'],c['private'],c['out']
    run,sql,gov,wire,check=c['run'],c['sql'],c['gov'],c['wire'],c['check']
    fixture,credentials,envs=c['fixture'],c['credentials'],c['envs'];tenant=fixture['tenant']
    report=c['report'];report['phase']='P06';report['evidence_level']='E2'
    c['conformance'].register_origin('https://127.0.0.1:8450', 'lifecycle')
    c['conformance'].register_origin('https://127.0.0.1:8449', 'lifecycle-workers')
    report['limitations'].append('P06 uses the shipped simulation adapter and separate PostgreSQL effect owner. No native execution, E3 qualification, operated dependency acceptance or human G06 receiving is claimed.')
    links=['lifecycle-governance','console-lifecycle','lifecycle-planning','lifecycle-assurance','assurance-lifecycle','console-assurance','lifecycle-simulator','assurance-simulator','simulator-lifecycle','lifecycle-alerts']
    for name in links:
        value=secrets.token_urlsafe(32);path=private/(name+'.secret');path.write_text(value);path.chmod(0o600)
        credentials[name]=(value,str(path));c['private_values'].append(value)
    epoch=str(uuid.uuid4());epoch_file=private/'execution-epoch';epoch_file.write_text(epoch);epoch_file.chmod(0o600)
    simulator_epoch_file=private/'simulation-epoch';simulator_epoch_file.write_text(epoch);simulator_epoch_file.chmod(0o600)
    simulation_worker_id=str(uuid.uuid4())
    registry_file=private/'simulation-campaigns.json';registry={'schema_version':1,'records':[]};registry_file.write_text(json.dumps(registry))
    common={'LIFECYCLE_URL':'https://127.0.0.1:8450','LIFECYCLE_CA_FILE':str(c['certificate']),'SIMULATOR_URL':'https://127.0.0.1:8449','SIMULATOR_CA_FILE':str(c['certificate']),
        'LIFECYCLE_CUSTODY_EPOCH_FILE':str(epoch_file),'SIMULATION_CUSTODY_EPOCH_FILE':str(simulator_epoch_file),'LIFECYCLE_SOURCE_REVISION':os.environ['GITHUB_SHA'],'LIFECYCLE_SIMULATION_CAMPAIGNS_FILE':str(registry_file),'LIFECYCLE_SIMULATION_WORKER_ID':simulation_worker_id,
        'GOVERNANCE_URL':'https://127.0.0.1:8442','GOVERNANCE_CA_FILE':str(c['certificate']),'PLANNING_URL':'https://127.0.0.1:8446','PLANNING_CA_FILE':str(c['certificate']),'ASSURANCE_URL':'https://127.0.0.1:8447','ASSURANCE_CA_FILE':str(c['certificate'])}
    for name in links:common[name.upper().replace('-','_')+'_CREDENTIAL_FILE']=credentials[name][1]
    common.update(LIFECYCLE_CONSOLE_CALLER_FILE=credentials['console-lifecycle'][1],LIFECYCLE_SIMULATOR_CALLER_FILE=credentials['simulator-lifecycle'][1],LIFECYCLE_ASSURANCE_CALLER_FILE=credentials['assurance-lifecycle'][1],PLANNING_LIFECYCLE_READER_CREDENTIAL_FILE=credentials['lifecycle-planning'][1],ASSURANCE_GOVERNANCE_CREDENTIAL_FILE=credentials['assurance-governance'][1])
    for name in envs:envs[name].update(common)
    for name,relative,role in [('lifecycle','services/lifecycle','lifecycle'),('simulation','workers/lifecycle','simulation')]:
        password=secrets.token_urlsafe(32);migrator=secrets.token_urlsafe(32);c['private_values'] += [password,migrator]
        password_file=private/(name+'-db.secret');password_file.write_text(password);password_file.chmod(0o600)
        sql(f"CREATE ROLE {role}_owner NOLOGIN; CREATE ROLE {role}_runtime LOGIN NOINHERIT PASSWORD '{password}'; CREATE ROLE {role}_migrator LOGIN NOINHERIT PASSWORD '{migrator}'; GRANT {role}_owner TO {role}_migrator WITH INHERIT FALSE, SET TRUE; CREATE DATABASE {name} OWNER {role}_owner;")
        sql(f'REVOKE ALL ON DATABASE {name} FROM PUBLIC; GRANT CONNECT ON DATABASE {name} TO {role}_runtime,{role}_migrator; REVOKE ALL ON SCHEMA public FROM PUBLIC;',name)
        if name=='lifecycle':sql('CREATE SCHEMA app AUTHORIZATION lifecycle_owner; GRANT USAGE ON SCHEMA app TO lifecycle_runtime;',name)
        for migration in sorted((root/relative/'migrations').glob('*.sql')):sql(migration.read_text(),name,role+'_migrator',migrator)
        envs[name]=os.environ|common|{'DB_HOST':'127.0.0.1','DB_PORT':'5432','DB_DATABASE':name,'DB_USERNAME':role+'_runtime','DB_PASSWORD_FILE':str(password_file),'DB_SSLMODE':'verify-full','DB_SSLROOTCERT':str(c['certificate'])}
    sql(f"INSERT INTO app.execution_control VALUES(1,'{epoch}',false);",'lifecycle')
    envs['simulation'].update(SIMULATION_TLS_CERT_FILE=str(c['certificate']),SIMULATION_TLS_KEY_FILE=str(c['key']))
    # P05 revoked the author during its browser access test. Regrant explicitly for new plans.
    revision=int(sql("SELECT revision FROM app.tenant_memberships WHERE actor_id='"+fixture['actor_id']+"' AND tenant_id='"+tenant+"';",'governance'))
    gov('/v1/tenants/'+tenant+'/memberships',{'revision':revision,'subject':'p03-author','role':'author','state':'active','site_id':None,'environment':None,'expires_at':None},expected=200)
    p['qualification_file'].write_text(json.dumps(p['original_qual']))
    for name in ['governance','planning','assurance','console']:c['stop'](name);c['start'](name)
    fault_file=private/'lifecycle-fault.json';proxy=TlsProxy(8450,8037,c['certificate'],c['key'],fault_file);c['proxies'].append(proxy)
    def spawn(name,command):
        handle=(private/(name+'.log')).open('ab');c['handles'].append(handle)
        c['processes'][name]=subprocess.Popen(command,cwd=root,env=envs['lifecycle' if name=='workflow' else name],stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
    def wait_for(name,fn,seconds=90):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            result=fn()
            if result:return result
            time.sleep(.3)
        raise RuntimeError(name+'_timed_out')
    lifecycle_command=[str(root/'services/lifecycle/.venv/bin/lifecycle-serve'),'--host','127.0.0.1','--port','8037']
    simulator_command=[str(root/'workers/lifecycle/.venv/bin/lifecycle-simulator')]
    spawn('lifecycle',lifecycle_command);spawn('simulation',simulator_command)
    def ready(base):
        try:return wire(base,'/health/live')[0]==200
        except OSError:return False
    wait_for('lifecycle_ready',lambda:ready(common['LIFECYCLE_URL']),15);wait_for('simulation_ready',lambda:ready(common['SIMULATOR_URL']),15)
    temporal=TemporalFixture(root,private,run,c['private_values']);c['p06_temporal']=temporal;temporal.start();envs['lifecycle'].update(temporal.environment)
    witness=[str(root/'services/lifecycle/.venv/bin/python'),'scripts/p06/temporal_process.py']
    run([*witness,'initialize'],env=envs['lifecycle'],label='p06-real-temporal-namespace')
    alert=AlertReceiver(c['certificate'],c['key'],credentials['lifecycle-alerts'][0],out/'alert-receipts.json');c['proxies'].append(alert)
    envs['lifecycle'].update(ALERTS_URL='https://127.0.0.1:8451',ALERTS_CA_FILE=str(c['certificate']))
    workflows=[];jobs=[];plans=[]
    schema=json.loads((root/'contracts/openapi/lifecycle-v1.json').read_text())
    custody_schema=json.loads((root/'contracts/openapi/assurance-evidence-v1.json').read_text())
    from openapi_schema_validator import OAS31Validator
    def custody_contract(name,value):
        OAS31Validator({'$ref':'#/components/schemas/'+name,'components':custody_schema['components']}).validate(value)
    def lifecycle(tail,scope,body=None,key=None,token=None,expected=200):
        action='operation.read' if body is None else 'operation.admit' if tail=='jobs' else 'operation.control'
        grant=gov('/v1/tenants/'+tenant+'/actor-delegations',{'audience':'lifecycle','action':action,'scope':{k:scope[k] for k in ['site_id','environment','resource_id']}},token=token or fixture['operator_token'])
        c['private_values'].append(grant['delegation_token'])
        headers={'Authorization':'Bearer '+credentials['console-lifecycle'][0],'X-Actor-Delegation':grant['delegation_token']}
        if body is not None:headers['Idempotency-Key']=key or str(uuid.uuid4())
        status,value,returned,size=wire(common['LIFECYCLE_URL'],'/v1/tenants/'+tenant+'/'+tail,'GET' if body is None else 'POST',body,headers)
        if status!=expected:raise RuntimeError('p06_wire_'+tail+'_'+str(status)+':'+json.dumps(value))
        check('p06-'+tail.split('/')[-1]+'-bounded-no-store',size<310000 and 'no-store' in returned.get('Cache-Control',''))
        if status<400:OAS31Validator({'$ref':'#/components/schemas/'+('CommandReceipt' if tail.endswith('commands') else 'Job'),'components':schema['components']}).validate(value)
        return value
    read_token=fixture['operator_token']
    def current(index):return lifecycle('jobs/'+jobs[index]['id'],plans[index]['content']['scope'],token=read_token)
    def command(index,action):
        view=current(index)
        return lifecycle('jobs/'+view['id']+'/commands',view['scope'],{'action':action,'expected_revision':view['revision']},expected=202)
    def simulator_effect(grant):
        return wire(common['SIMULATOR_URL'],'/v1/effects','POST',grant,
                    effect_headers(grant,credentials['lifecycle-simulator'][0]))
    for action,method in [('provision','native_api'),('migrate','native_api_export_import'),('recover','forward_recovery'),('retire','owned_retirement')]:
        dest=copy.deepcopy(p['a']);dest.update(site_id=str(uuid.uuid4()),endpoint_id=str(uuid.uuid4()),generation_id=str(uuid.uuid4()))
        p['peer'].destinations[dest['endpoint_id']]=dest
        p['registry']['assignments'].append({'tenant_id':tenant,'site_id':dest['site_id'],'endpoint_id':dest['endpoint_id'],'profile':'synthetic','policy':'synthetic'})
        p['registry_file'].write_text(json.dumps(p['registry']))
        p['publish_qualification'](dest,'application.'+action,method)
        body={'revision_id':p['revision'],'action':'application.'+action,'method':method,'candidates':[{k:dest[k] for k in ['site_id','endpoint_id','generation_id']}]}
        assessment=p['planning']('assessments',body,sites=[dest['site_id']],expected=201)
        req={'action':body['action'],'method':method,'lane':'isolated_campaign','executor_ids':[fixture['operator_id']],'valid_until':int(time.time())+900}
        created=p['planning']('plans',{'assessment_id':assessment['id'],'candidate':0,'request':req},sites=[dest['site_id']],expected=201)
        plan=p['planning']('plans/'+created['id'],sites=[dest['site_id']]);content,binding=plan['content'],plan['binding'];plans.append(plan)
        (out/('p06-'+action+'-plan-inputs.json')).write_text(json.dumps({
            'holds':content['holds'],'validity':plan['validity'],'action':content['action'],
            'method':content['method'],'evidence_level':'E2',
        },indent=2)+'\n')
        approval=gov('/v1/tenants/'+tenant+'/approvals',{'plan_id':plan['id'],'plan_revision':1,'plan_digest':binding['digest'],'expires_at':datetime.datetime.fromtimestamp(req['valid_until'],datetime.UTC).isoformat()},token=fixture['author_token'])
        gov('/v1/tenants/'+tenant+'/approvals/'+approval['id']+'/approve',{'revision':1,'reason':'Independent isolated P06 simulation review.'},token=fixture['reviewer_token'],expected=200)
        campaign_id=str(uuid.uuid4());scope=content['scope'];expires=int(time.time())+900
        snapshot={'scope':scope,'input_digests':content['input_digests'],'artifacts':content['artifacts'],'lane':'isolated_campaign','environment_class':'isolated_lab','simulation':True,
            **{k:True for k in ['entitled','commissioned','ownership_current','state_current','change_window','emergency_stop_clear']},
            'actor_id':fixture['operator_id'],'endpoints':[common['SIMULATOR_URL']],'credential_scope_refs':['isolated-p06-simulator'],
            'reservations':[dict(r,state='reserved',plan_digest=binding['digest'],expires_at=expires,receipt_id=str(uuid.uuid4())) for r in content['reservation_intents']]}
        snapshot['campaign']={k:snapshot[k] for k in ['scope','actor_id','environment_class','credential_scope_refs']}
        snapshot['campaign'].update(id=campaign_id,adapter='p06-simulator-v1',custody_epoch=epoch,worker_ids=[simulation_worker_id],action=content['action'],method=content['method'],installed_tuple=content['installed_tuple'],artifacts=content['artifacts'],plan_digest=binding['digest'],expires_at=expires,revoked=False,endpoint_allowlist=snapshot['endpoints'],data_scope=['synthetic-data'],cleanup_owner='disposable-campaign-owner',max_effects=32)
        registry['records'].append(snapshot);registry_file.write_text(json.dumps(registry))
        admission={'plan_id':plan['id'],'plan_revision':1,'plan_digest':binding['digest'],'approval_id':approval['id'],'campaign_id':campaign_id}
        idem=str(uuid.uuid4())
        if action=='provision':
            fault_file.write_text(json.dumps({'path':'/v1/tenants/'+tenant+'/jobs'}))
            lifecycle('jobs',scope,admission,key=idem,expected=503)
            check('p06-admission-response-lost-after-commit',proxy.injected==1)
        job=lifecycle('jobs',scope,admission,key=idem,expected=202);jobs.append(job);workflows.append(job['workflow_id'])
        check('p06-'+action+'-one-logical-job',lifecycle('jobs',scope,admission,key=idem,expected=202)['id']==job['id'])
    consumer_calls=security_probes(c,common['LIFECYCLE_URL'],tenant,fixture['foreign_tenant'],scope,jobs[-1],admission,idem)
    consumer_input=private/'console-consumer.json'
    consumer_input.write_text(json.dumps({'session':fixture['operator_token'],'tenant':tenant,
                                        'scope':{k:scope[k] for k in ['site_id','environment','resource_id']},
                                        'job_id':jobs[-1]['id'],'fault_file':str(fault_file),'calls':consumer_calls}))
    consumer_input.chmod(0o600)
    injected_before=proxy.injected
    run(['php','scripts/p06/verify_console_consumers.php',str(consumer_input),str(out/'consumer-conformance.json')],
        env=envs['console'],label='p06-real-console-contract-consumers')
    check('p06-console-rejects-twelve-substituted-owner-responses',proxy.injected-injected_before==12 and not fault_file.exists())
    check('p06-distinct-services-own-stores',sql("SELECT has_table_privilege('assurance_runtime','app.evidence_uploads','UPDATE') OR has_table_privilege('assurance_runtime','app.evidence_records','DELETE');",'assurance')=='f')
    backup=private/'lifecycle-before-effects.sql'
    with backup.open('wb') as stream:
        dumped=subprocess.run(['docker','exec',c['container'],'pg_dump','-U','postgres','--clean','--if-exists','lifecycle'],stdout=stream,stderr=subprocess.PIPE,timeout=30)
    check('p06-pre-effect-database-backup',dumped.returncode==0)
    backup.chmod(0o600)
    backup_hash=hashlib.sha256(backup.read_bytes()).hexdigest()
    # Process dies after grant commit, before simulated acceptance. A later process seals absence.
    grant_file=private/'late-grant.json'
    run([*witness,'crash_before',tenant,jobs[0]['id'],'reserve',str(grant_file)],env=envs['lifecycle'],expected=75,label='p06-crash-before-acceptance')
    c['stop']('lifecycle');spawn('lifecycle',lifecycle_command);wait_for('lifecycle_restart',lambda:ready(common['LIFECYCLE_URL']),15)
    run([*witness,'reconcile',tenant,jobs[0]['id']],env=envs['lifecycle'],label='p06-new-process-seals-absence')
    late=json.loads(grant_file.read_text())
    check('p06-delayed-worker-probe-is-still-unexpired',late['expires_at']>int(time.time()))
    check('p06-delayed-worker-cannot-cross-seal',simulator_effect(late)[0]==403)
    command(0,'retry_unstarted')
    # The original attempt was sealed; use a new, actually acquired grant.
    # Each owner sees the other owner's epoch unchanged, then the exact same
    # grant succeeds. A timeout, expiry, malformed transport or revoked grant
    # cannot masquerade as isolated epoch enforcement.
    run([*witness,'crash_before',tenant,jobs[0]['id'],'reserve',str(grant_file)],env=envs['lifecycle'],expected=75,label='p06-fresh-epoch-control-grant')
    fresh=json.loads(grant_file.read_text())
    isolated=epoch_isolation(fresh,epoch_file,simulator_epoch_file,simulator_effect,
                            lambda:int(sql('SELECT count(*) FROM sim.observations WHERE effect_count=1;','simulation')),check)
    (out/'epoch-isolation-observations.json').write_text(json.dumps(isolated,indent=2)+'\n')
    run([*witness,'reconcile',tenant,jobs[0]['id']],env=envs['lifecycle'],label='p06-epoch-control-reconciles-acceptance')
    # Process dies after target write acceptance. Journal remains uncertain; no source return.
    for effect in plans[1]['content']['effects']:
        if effect['id']=='activate_target':break
        run([*witness,'effect',tenant,jobs[1]['id'],effect['id']],env=envs['lifecycle'],label='p06-migrate-'+effect['id'])
    run([*witness,'crash_after',tenant,jobs[1]['id'],'activate_target',str(grant_file)],env=envs['lifecycle'],expected=75,label='p06-crash-after-target-write')
    view=current(1);check('p06-unknown-target-write-is-forward-recovery',view['recovery_mode']=='forward_recovery_required' and any(o['outcome']=='attempting' for o in view['operations']))
    # Browser exercises unknown state, stale controls, stop, cancel, history and revoked access.
    fixture['reader_member']=gov('/v1/tenants/'+tenant+'/memberships',{'revision':0,'subject':'p03-outsider','role':'reader','state':'active','site_id':None,'environment':None,'expires_at':None},expected=200)
    fixture['reader_token']=fixture['foreign_token']
    fixture.update(p06_jobs=jobs,p06_plans=plans,p06_fault_file=str(fault_file),p06_registry_file=str(registry_file),p06_api_url=common['LIFECYCLE_URL'])
    c['fixture_file'].write_text(json.dumps(fixture));run(['php','scripts/p06/seed_console.php',str(c['fixture_file'])],env=envs['console'],label='p06-browser-sessions')
    fixture.update(json.loads(c['fixture_file'].read_text()));c['private_values'] += [fixture[a+'_cookie']['value'] for a in ['operator','reviewer','reader']]
    run(['npx','playwright','test','--config=tests/browser-p06/playwright.config.ts'],cwd=root/'apps/console',env=os.environ|{'P06_BROWSER_FIXTURE':str(c['fixture_file']),'CONSOLE_BASE_URL':'http://127.0.0.1:8031'},label='p06-browser-controls')
    browser=root/'apps/console/test-results/p06-browser.json';result=json.loads(browser.read_text());(out/'p06-browser.json').write_text(c['redact'](browser.read_text()))
    check('p06-browser-no-skips-retries-failures',result['stats']['expected']==1 and all(result['stats'][k]==0 for k in ['unexpected','flaky','skipped']))
    # UI cancellation leaves accepted target effects intact and does not release ownership.
    run([*witness,'reconcile',tenant,jobs[1]['id']],env=envs['lifecycle'],label='p06-after-crash-observation')
    view=current(1);check('p06-target-acceptance-observed-once',next(o for o in view['operations'] if o['step']=='activate_target')['observation']['effect_count']==1)
    command(1,'cancel')
    # Outbox loses its first start acknowledgement. Real Temporal retains the original ID/run.
    run([*witness,'dispatch_lost'],env=envs['lifecycle'],expected=75,label='p06-lost-temporal-start-response')
    check('p06-lost-start-retains-outbox',int(sql('SELECT count(*) FROM app.execution_dispatch WHERE NOT dispatched;','lifecycle'))==4)
    run([*witness,'dispatch'],env=envs['lifecycle'],label='p06-recover-original-temporal-start')
    c['stop']('assurance')
    worker_command=[str(root/'services/lifecycle/.venv/bin/lifecycle-workflows')];spawn('workflow',worker_command)
    wait_for('evidence_held',lambda:sql("SELECT count(*) FROM app.execution_projection WHERE reason='evidence_pending';",'lifecycle')=='3')
    check('p06-no-evidence-no-completion',sql("SELECT count(*) FROM app.execution_projection WHERE state='completed';",'lifecycle')=='0')
    operator_revision=int(sql("SELECT revision FROM app.tenant_memberships WHERE actor_id='"+fixture['operator_id']+"' AND tenant_id='"+tenant+"';",'governance'))
    gov('/v1/tenants/'+tenant+'/memberships',{'revision':operator_revision,'subject':'p05-operator','role':'operator','state':'revoked','site_id':None,'environment':None,'expires_at':None},expected=200)
    read_token=fixture['reviewer_token']
    binding=plans[0]['binding']
    denied=wire('https://127.0.0.1:8442','/v1/tenants/'+tenant+'/execution-approval-checks','POST',{'actor_id':fixture['operator_id'],'approval_id':jobs[0]['approval_id'],'plan_id':binding['plan_id'],'plan_revision':1,'plan_digest':binding['digest']},{'Authorization':'Bearer '+credentials['lifecycle-governance'][0]})
    # Governance deliberately masks absent/revoked tenant membership as not_found.
    check('p06-revoked-executor-cannot-authorize-another-effect',denied[0]==404)
    # Restart the actual worker and engine while journal/effect stores survive.
    c['stop']('workflow');temporal.restart();spawn('workflow',worker_command)
    c['start']('assurance')
    wait_for('completed_journeys',lambda:sql("SELECT count(*) FROM app.execution_projection WHERE state='completed';",'lifecycle')=='3',120)
    check('p06-cancellation-keeps-effects-and-holds',current(1)['state']=='cancelled' and current(1)['resources_retained'])
    for i in [0,2,3]:
        view=current(i);check('p06-'+plans[i]['content']['action']+'-complete-e2-custody',view['state']=='completed' and view['evidence']['native_support'] is False and view['evidence']['source_revision']==os.environ['GITHUB_SHA'])
    wait_for('alert_acknowledgement',lambda:sql('SELECT count(*) FROM app.execution_alerts WHERE receipt IS NULL;','lifecycle')=='0')
    check('p06-independent-alert-delivery-and-receipt',len(alert.receipts)>0)
    check('p06-retirement-has-no-writer',sql("SELECT source_writer OR target_writer FROM sim.writers WHERE job='"+jobs[3]['id']+"';",'simulation')=='f')
    check('p06-no-simultaneous-writers',sql('SELECT count(*) FROM sim.writers WHERE source_writer AND target_writer;','simulation')=='0')
    # Custody finalized committed effects after executor revocation; live retrieval stays authorized.
    completed=current(0);evidence=completed['evidence'];observations=[o['observation'] for o in completed['operations']]
    raw=json.dumps(observations,sort_keys=True,ensure_ascii=True,separators=(',',':')).encode()
    upload={'job_id':completed['id'],'plan_digest':completed['plan_digest'],'source_revision':os.environ['GITHUB_SHA'],'evidence_level':'E2','digest':hashlib.sha256(raw).hexdigest(),'content_base64':base64.b64encode(raw).decode()}
    producer={'Authorization':'Bearer '+credentials['lifecycle-assurance'][0]};assurance=common['ASSURANCE_URL'];prefix='/v1/tenants/'+tenant
    upload_reply=wire(assurance,prefix+'/evidence-uploads','POST',upload,producer)
    check('p06-upload-idempotent-after-revocation',upload_reply[0]==201 and upload_reply[1]['id']==evidence['id'])
    custody_contract('UploadReceipt',upload_reply[1]);custody_contract('Evidence',evidence)
    check('p06-tampered-upload-rejected',wire(assurance,prefix+'/evidence-uploads','POST',dict(upload,digest='0'*64),producer)[0]==422)
    check('p06-source-substitution-rejected',wire(assurance,prefix+'/evidence-uploads','POST',dict(upload,source_revision='f'*40),producer)[0]==409)
    def evidence_headers(action):
        grant=gov(prefix+'/actor-delegations',{'audience':'assurance','action':action,'scope':{k:completed['scope'][k] for k in ['site_id','environment','resource_id']}},token=fixture['reviewer_token'])
        c['private_values'].append(grant['delegation_token']);return {'Authorization':'Bearer '+credentials['console-assurance'][0],'X-Actor-Delegation':grant['delegation_token']}
    evidence_path=prefix+'/evidence/'+evidence['id']
    review=wire(assurance,evidence_path+'/reviews','POST',{'decision':'accepted_simulation'},evidence_headers('evidence.review'))
    check('p06-independent-evidence-review-is-simulation-only',review[0]==201 and review[1]['native_support'] is False)
    custody_contract('ReviewReceipt',review[1])
    check('p06-wrong-tenant-evidence-denied',wire(assurance,'/v1/tenants/'+fixture['foreign_tenant']+'/evidence/'+evidence['id'],headers=evidence_headers('evidence.read'))[0]==404)
    sql("UPDATE app.evidence_uploads SET content='[]' WHERE id='"+evidence['id']+"';",'assurance')
    check('p06-persisted-tamper-denied-on-read',wire(assurance,evidence_path,headers=evidence_headers('evidence.read'))[0]==409)
    sql("UPDATE app.evidence_uploads SET content=convert_from(decode('"+base64.b64encode(raw).decode()+"','base64'),'UTF8') WHERE id='"+evidence['id']+"';",'assurance')
    restored_custody=wire(assurance,evidence_path,headers=evidence_headers('evidence.read'))
    check('p06-custody-restored-digest-valid',restored_custody[0]==200)
    custody_contract('EvidenceRecord',restored_custody[1])
    fixture.update(p06_completed=completed);c['fixture_file'].write_text(json.dumps(fixture))
    run(['npx','playwright','test','--config=tests/browser-p06/playwright.evidence.config.ts'],cwd=root/'apps/console',env=os.environ|{'P06_BROWSER_FIXTURE':str(c['fixture_file']),'CONSOLE_BASE_URL':'http://127.0.0.1:8031'},label='p06-browser-evidence')
    evidence_browser=root/'apps/console/test-results/p06-evidence-browser.json';browser_result=json.loads(evidence_browser.read_text());(out/'p06-evidence-browser.json').write_text(c['redact'](evidence_browser.read_text()))
    check('p06-evidence-browser-no-skips-retries-failures',browser_result['stats']['expected']==1 and all(browser_result['stats'][k]==0 for k in ['unexpected','flaky','skipped']))
    file=private/'workflow-ids.json';file.write_text(json.dumps(workflows));run([*witness,'replay',str(file),str(out/'temporal-replay.json')],env=envs['lifecycle'],label='p06-version-one-history-replay')
    (out/'execution-observations.json').write_text(json.dumps({'simulation':True,'jobs':[current(i) for i in range(4)],'effect_count':int(sql('SELECT count(*) FROM sim.observations WHERE effect_count=1;','simulation'))},indent=2)+'\n')
    # Restore an older journal while Temporal and the independent effect owner retain acceptance.
    c['stop']('workflow');c['stop']('lifecycle')
    recovered_epoch=str(uuid.uuid4());epoch_file.write_text(recovered_epoch);simulator_epoch_file.write_text(recovered_epoch)
    before_restore_count=sql('SELECT count(*) FROM sim.observations WHERE effect_count=1;','simulation')
    run(['psql','-X','-v','ON_ERROR_STOP=1','-d','lifecycle','-f',str(backup)],env=c['pg_env'],label='p06-restore-older-journal')
    spawn('lifecycle',lifecycle_command);wait_for('restored_lifecycle',lambda:ready(common['LIFECYCLE_URL']),15)
    run([*witness,'effect',tenant,jobs[0]['id'],'reserve'],env=envs['lifecycle'],expected=1,label='p06-restored-worker-denied')
    check('p06-old-database-starts-without-new-write-authority',current(0)['state']=='held' and current(0)['resources_retained'])
    late=json.loads(grant_file.read_text())
    check('p06-old-worker-grant-remains-denied-after-restore',simulator_effect(late)[0]==403)
    report['limitations'].append('The post-restore old-grant denial proves continued denial and may include expiry. Separate pre-restore, fresh-grant controls isolate the effect-owner and journal-owner epoch fences; neither authorizes re-enabling the restored journal.')
    check('p06-restore-independent-accepted-effects-preserved',sql('SELECT count(*) FROM sim.observations WHERE effect_count=1;','simulation')==before_restore_count)
    check('p06-restore-does-not-invent-completion',sql("SELECT count(*) FROM app.execution_projection WHERE state='completed';",'lifecycle')=='0')
    (out/'restore-observations.json').write_text(json.dumps({'backup_sha256':backup_hash,'restored_jobs':4,'independent_effect_count':int(before_restore_count),'external_epoch_changed':True,'read_only_hold':True,'re_enable_decision':'DENIED: restored journal and current epoch require independent reconciliation and newly bound authority; no automatic release or old-epoch restoration'},indent=2)+'\n')
    for name in ['lifecycle','simulation','workflow']:
        log=(private/(name+'.log')).read_text();(out/(name+'-http.log')).write_text(c['redact'](log));check('p06-'+name+'-redacted',all(value not in log for value in c['private_values']))


def campaign(c,p):
    try:
        _campaign(c,p)
    finally:
        c['stop']('workflow')
        if c.get('p06_temporal') is not None:
            c['p06_temporal'].close()
        for name in ['lifecycle','simulation','workflow']:
            log=c['private']/(name+'.log')
            if log.exists():(c['out']/(name+'-http.log')).write_text(c['redact'](log.read_text()))
        for name in ['p06-browser.json','p06-evidence-browser.json']:
            log=c['root']/'apps/console/test-results'/name
            if log.exists():(c['out']/name).write_text(c['redact'](log.read_text()))
        try:
            data=c['sql']("SELECT coalesce(json_agg(row_to_json(p)), '[]'::json) FROM app.execution_projection p;",'lifecycle')
            (c['out']/'final-projection.json').write_text(data+'\n')
        except Exception:pass
