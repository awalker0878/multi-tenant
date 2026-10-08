"""Q03 live service, source-owner, approval, delivery and browser observations."""
import copy
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import time
import uuid
import sys
from concurrent.futures import ThreadPoolExecutor
from jsonschema import Draft202012Validator
from openapi_schema_validator import OAS31Validator
from openapi_spec_validator import validate_spec
from live_fixture import InventoryContractPeer,PlanningBroker


def campaign(c, extension=None):
    root,private,out=c['root'],c['private'],c['out']
    wire,gov,run,check,sql=c['wire'],c['gov'],c['run'],c['check'],c['sql']
    fixture,credentials,envs=c['fixture'],c['credentials'],c['envs']
    tenant=fixture['tenant'];private_values=c['private_values']
    spec=importlib.util.spec_from_file_location('catalogue_ops',root/'scripts/p03/generated_operations.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    def catalogue(operation,body=None,params=None,token=None):
        op=module.OPERATIONS[operation];params={'tenant':tenant,**(params or {})}
        scope={'site_id':None,'environment':body.get('intent',{}).get('environment',{}).get('id') if body else None,'resource_id':params.get('application')}
        delegation=gov('/v1/tenants/'+tenant+'/actor-delegations',{'audience':'catalogue','action':op['action'],'scope':scope},token=token or fixture['author_token'])
        private_values.append(delegation['delegation_token'])
        status,value,_,_=wire('https://127.0.0.1:8443',op['path'].format(**params),op['method'],body,{'Authorization':'Bearer '+credentials['console-catalogue'][0],'X-Actor-Delegation':delegation['delegation_token'],'Idempotency-Key':str(uuid.uuid4())})
        check(operation+'-live-owner-result',status==op['status'])
        return value
    mapping={'00000000-0000-4000-8000-000000000002':fixture['actor_id']}
    for suffix,op,name,zone in [(10,'createEnvironment','P05 isolated fixture',None),(11,'createWsd','Frontend',None),(12,'createWsd','Data',None),(21,'createSecurityDomain','Operations','OZ'),(22,'createSecurityDomain','Restricted','RZ')]:
        body={'name':name,'owner_id':fixture['actor_id']}
        if op!='createEnvironment':body['shareable']=True
        if zone:body['zone']=zone
        result=catalogue(op,body,token=fixture['admin_token']);mapping['00000000-0000-4000-8000-'+f'{suffix:012d}']=result['id']
    raw=(root/'contracts/fixtures/planning/synthetic-inputs-v1.json').read_text()
    for old in re.findall(r'00000000-0000-4000-8000-[0-9]{12}',raw):mapping.setdefault(old,str(uuid.uuid4()))
    model=json.loads(re.sub(r'00000000-0000-4000-8000-[0-9]{12}',lambda m:mapping[m[0]],raw))
    now=int(time.time())
    def refresh(value):
        if isinstance(value,dict):return {k:refresh(v) for k,v in value.items()}
        if isinstance(value,list):return [refresh(v) for v in value]
        if type(value) is int and value>=2_000_000_000:return now+(value-2_000_000_000)
        return value
    model=refresh(model)
    accepted=catalogue('createApplication',{'name':'P05 review application','intent':model['intent']})
    application,revision,environment=accepted['application_id'],accepted['revision_id'],model['intent']['environment']['id']
    a=copy.deepcopy(model['destination']);a.update(tenant_id=tenant,site_id=c['site'],endpoint_id=c['endpoint'],generation_id=c['current'])
    b=copy.deepcopy(a);b.update(site_id=str(uuid.uuid4()),endpoint_id=str(uuid.uuid4()),generation_id=str(uuid.uuid4()));b['capacity']['vcpus']=1
    policy=model['policy'];p=model['profile']
    # Fixture IDs are rebound to the actual isolated application before compilation.
    # Rebind the exact ownership and operation digests, just as the plan producer does.
    def canonical_digest(value):
        return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True,
            allow_nan=False,separators=(',',':')).encode()).hexdigest()
    native=policy['native_api']
    native['operation_plan']['ownership_digest']=canonical_digest(policy['ownership'])
    native['operation_plan_sha256']=canonical_digest(native['operation_plan'])
    registry={'schema_version':1,'profiles':{'synthetic':{'platform':p['platform'],'version':p['version'],'declarations':{r['dimension']:r['declaration'] for r in p['dimensions']}}},'policies':{'synthetic':policy},'assignments':[{'tenant_id':tenant,'site_id':d['site_id'],'endpoint_id':d['endpoint_id'],'profile':'synthetic','policy':'synthetic'} for d in [a,b]]}
    registry_file=private/'planning-registry.json';registry_file.write_text(json.dumps(registry))
    sys.path.insert(0, str(root/'tests/contracts'))
    from native_qualification_fixture import FixtureRuntimePublisher, signed_fixture
    quals={'schema_version':2,'records':[]}
    trust={'schema_version':1,'keys':{}}
    for d in [a,b]:
        q=copy.deepcopy(model['qualification']);q['scope'].update({k:d[k] for k in ['tenant_id','site_id','endpoint_id','native_scope','installed_tuple']})
        bundle,keys=signed_fixture(q,private/('fixture-keys-'+d['site_id']))
        # Scope-specific enrolled keys; these are isolated E2 peer fixtures.
        prefix=d['site_id']+':'
        for envelope in [bundle['decision'],bundle['runtime'],*bundle['evidence']]:
            envelope['key_id']=prefix+envelope['key_id']
        trust['keys'].update({prefix+k:v for k,v in keys.items()})
        quals['records'].append(bundle)
    qualification_file=private/'qualification-registry.json';qualification_file.write_text(json.dumps(quals))
    qualification_file.chmod(0o600)
    trust_file=private/'qualification-trust.json';trust_file.write_text(json.dumps(trust));trust_file.chmod(0o600)
    envs['assurance']['ASSURANCE_QUALIFICATION_TRUST_FILE']=str(trust_file)
    runtime_file=private/'qualification-runtime.json'
    c['proxies'].append(FixtureRuntimePublisher(runtime_file,quals,private))
    envs['assurance']['ASSURANCE_QUALIFICATION_RUNTIME_FILE']=str(runtime_file)
    envs['planning']['PLANNING_REGISTRY_FILE']=str(registry_file)
    envs['assurance']['ASSURANCE_QUALIFICATION_REGISTRY_FILE']=str(qualification_file)
    for service in ['planning','assurance']:c['stop'](service);c['start'](service)
    candidates=[{k:d[k] for k in ['site_id','endpoint_id','generation_id']} for d in [a,b]]
    base=f'/v1/tenants/{tenant}/applications/{application}/environments/{environment}'
    api=json.loads((root/'contracts/openapi/planning-v1.json').read_text());validate_spec(api)
    def grants(sites,action='plan.create',token=None):
        headers=[]
        for site in dict.fromkeys(sites):
            grant=gov('/v1/tenants/'+tenant+'/actor-delegations',{'audience':'planning','action':action,'scope':{'site_id':site,'environment':environment,'resource_id':application}},token=token or fixture['author_token'])
            private_values.append(grant['delegation_token']);headers.append(site+':'+grant['delegation_token'])
        return {'Authorization':'Bearer '+credentials['console-planning'][0],'X-Planning-Delegations':','.join(headers)}
    def planning(tail,body=None,sites=None,key=None,expected=200):
        method='POST' if body is not None else 'GET';action='plan.create' if method=='POST' and not tail.endswith(('/validity','/diff')) else 'plan.read'
        headers=grants(sites or [a['site_id'],b['site_id']],action)
        if body is not None:headers['Idempotency-Key']=key or str(uuid.uuid4())
        status,value,returned,_=wire('https://127.0.0.1:8446',base+'/'+tail,method,body,headers)
        if status!=expected:raise RuntimeError('planning_'+tail+'_expected_'+str(expected)+'_got_'+str(status)+':'+json.dumps(value))
        if status<400:
            schema='Receipt' if status==201 else 'Diff' if tail.endswith('/diff') else 'Validity' if tail.endswith('/validity') else 'Plan' if tail.startswith('plans/') else 'Assessment'
            OAS31Validator({'$ref':'#/components/schemas/'+schema,'components':api['components']}).validate(value)
            check('planning-wire-'+schema+'-no-store','no-store' in returned.get('Cache-Control',''))
        return value
    create={'revision_id':revision,'action':'application.provision','method':'native_api','candidates':candidates}
    actual=planning('assessments',dict(create,candidates=candidates[:1]),sites=[a['site_id']],expected=201)
    actual_view=planning('assessments/'+actual['id'],sites=[a['site_id']])
    check('actual-P04-owner-declarations-never-imply-support',actual_view['results'][0]['operationally_eligible'] is False and any(f['reason']=='installed_tuple_only_declared' for f in actual_view['results'][0]['findings']))
    peer=InventoryContractPeer(c['certificate'],c['key'],credentials['planning-inventory'][0],credentials['inventory-governance'][0],{a['endpoint_id']:a,b['endpoint_id']:b})
    c['proxies'].append(peer)
    c['stop']('planning');envs['planning']['INVENTORY_URL']='https://127.0.0.1:8448';c['start']('planning')
    key=str(uuid.uuid4())
    with ThreadPoolExecutor(2) as pool:replies=list(pool.map(lambda _:planning('assessments',create,key=key,expected=201),range(2)))
    check('live-concurrent-idempotency-one-result',replies[0]==replies[1])
    assessment=planning('assessments/'+replies[0]['id'])
    check('two-authorized-destinations-explain-positive-and-blocked',[r['status'] for r in assessment['results']]==['eligible','blocked'])
    planning('assessments',dict(create,method='native_api_export_import'),key=key,expected=409)
    req={'action':'application.provision','method':'native_api','lane':'operational','executor_ids':[fixture['operator_id']],'valid_until':int(time.time())+900}
    first=planning('plans',{'assessment_id':assessment['id'],'candidate':0,'request':req},expected=201)
    saved=planning('plans/'+first['id'],sites=[a['site_id']])
    check('immutable-plan-is-current-without-native-authority',saved['validity']['current'] and saved['content']['native_write_authorized'] is False)
    second=planning('plans',{'assessment_id':assessment['id'],'candidate':0,'request':req},expected=201)
    check('equivalent-semantics-stable-content-distinct-review-identity',first['binding']['content_digest']==second['binding']['content_digest'] and first['binding']['digest']!=second['binding']['digest'])
    binding=first['binding']
    approval=gov('/v1/tenants/'+tenant+'/approvals',{'plan_id':first['id'],'plan_revision':1,'plan_digest':binding['digest'],'expires_at':datetime.datetime.fromtimestamp(req['valid_until'],datetime.UTC).isoformat()},token=fixture['author_token'])
    gov('/v1/tenants/'+tenant+'/approvals/'+approval['id']+'/approve',{'revision':1,'reason':'Independent E2 fixture review; no native support claim.'},token=fixture['reviewer_token'],expected=200)
    use={'plan_id':first['id'],'plan_revision':1,'plan_digest':binding['digest'],'action':binding['action'],'scope':{k:binding[k] for k in ['site_id','environment','resource_id']}}
    gov('/v1/tenants/'+tenant+'/approvals/'+approval['id']+'/validations',use,token=fixture['operator_token'],expected=200)
    gov('/v1/tenants/'+tenant+'/approvals/'+approval['id']+'/validations',dict(use,plan_digest=second['binding']['digest']),token=fixture['operator_token'],expected=403)
    check('real-governance-approval-content-binding-and-changed-digest-denial',True)
    c['stop']('planning');c['start']('planning')
    check('service-restart-preserves-immutable-plan',planning('plans/'+first['id'],sites=[a['site_id']])['content']==saved['content'])
    original_qual=copy.deepcopy(quals);quals['records'][0]['record']['revoked']=True;qualification_file.write_text(json.dumps(quals))
    held=planning('plans/'+first['id'],sites=[a['site_id']])
    check('current-qualification-revocation-holds-without-changing-plan',not held['validity']['current'] and held['content']==saved['content'])
    qualification_file.write_text(json.dumps(original_qual))
    # Browser runs before queued historical hints conservatively invalidate existing plans.
    fixture.update(ca_file=str(c['certificate']),application=application,environment=environment,revision=revision,assessment=assessment['id'],sites=[a['site_id'],b['site_id']],site=a['site_id'],qualification_file=str(qualification_file),fault_file=str(c['fault_file']),planning_api_base=base,console_workload=credentials['console-governance'][0],governance_url='https://127.0.0.1:8442')
    c['fixture_file'].write_text(json.dumps(fixture))
    before_plans=int(sql("SELECT count(*) FROM app.planning_records WHERE kind='plan';",'planning'))
    run(['npx','playwright','test','--config=tests/browser-p05/playwright.config.ts'],cwd=root/'apps/console',env=os.environ|{'P05_BROWSER_FIXTURE':str(c['fixture_file']),'CONSOLE_BASE_URL':'http://127.0.0.1:8031'},label='p05-browser')
    browser_path=root/'apps/console/test-results/p05-browser.json';browser=json.loads(browser_path.read_text());(out/'browser.json').write_text(c['redact'](browser_path.read_text()));c['report']['browser_stats']=browser['stats']
    check('required-browser-no-skips-retries-or-failures',browser['config']['projects'][0]['name']==c['engine'] and browser['stats']['expected']==1 and all(browser['stats'][k]==0 for k in ['unexpected','flaky','skipped']))
    check('uncertain-browser-retry-created-one-plan',int(sql("SELECT count(*) FROM app.planning_records WHERE kind='plan';",'planning'))==before_plans+1)
    check('post-commit-response-loss-was-injected',sum(getattr(p,'injected',0) for p in c['proxies'])==1)
    broker=PlanningBroker(root,private,run,private_values);c['proxies'].append(broker)
    envs['planning'].update(broker.environment);envs['inventory'].update(broker.environment)
    publisher=[str(root/'services/planning/.venv/bin/planning-facts'),'publish','--limit','100']
    run(publisher,env=envs['planning'],expected=1,label='planning-broker-unavailable')
    check('planning-outbox-retained-during-outage',sql('SELECT count(*) FROM app.planning_deliveries;','planning')=='0')
    broker.start()
    envs['catalogue'].update(broker.environment,CATALOGUE_BROKER_HOST='127.0.0.1',CATALOGUE_BROKER_PORT='5679',CATALOGUE_BROKER_CA_FILE=str(c['certificate']))
    run(['php','artisan','catalogue:publish-events','--limit=100'],cwd=root/'services/catalogue',env=envs['catalogue'],label='catalogue-facts-to-planning')
    run([str(root/'services/planning/.venv/bin/planning-facts'),'catalogue','--limit','100'],env=envs['planning'],label='planning-committed-catalogue-inbox')
    check('catalogue-facts-committed-in-planning',int(sql("SELECT count(*) FROM app.planning_fact_inbox WHERE envelope->>'event_type' LIKE 'catalogue.%';",'planning'))>0)
    run([str(root/'services/inventory/.venv/bin/inventory-publish'),'--limit','100'],env=envs['inventory'],label='inventory-facts-to-planning')
    run([str(root/'services/planning/.venv/bin/planning-facts'),'inventory','--limit','100'],env=envs['planning'],label='planning-committed-inventory-inbox')
    check('inventory-events-durably-invalidate-without-refresh',int(sql('SELECT count(*) FROM app.planning_fact_inbox;','planning'))>0 and int(sql('SELECT count(*) FROM app.planning_invalidations;','planning'))>0)
    probe=[str(root/'services/planning/.venv/bin/python'),'scripts/p05/broker_process.py']
    run([*probe,'uncertain'],env=envs['planning'],expected=75,label='planning-confirmed-before-receipt-loss')
    run(publisher,env=envs['planning'],label='planning-confirmed-replay')
    run([*probe,'observe',str(out/'broker-observer.json')],env=envs['planning'],label='planning-independent-broker-observer')
    events=json.loads((out/'broker-observer.json').read_text());ids=[r['body']['event_id'] for r in events]
    fact_schema=json.loads((root/'contracts/schemas/planning/fact-v1.json').read_text())
    for event in events:Draft202012Validator(fact_schema).validate(event['body'])
    check('published-planning-fact-contract',True)
    check('planning-fact-lost-receipt-replays-original-event',len(ids)>1 and ids[0]==ids[1] and len(ids)-len(set(ids))==1)
    check('planning-confirmed-outbox-drained',sql('SELECT count(*) FROM app.planning_outbox o LEFT JOIN app.planning_deliveries d ON d.id=o.id WHERE d.id IS NULL;','planning')=='0')
    (out/'owner-observations.json').write_text(json.dumps({'scope':'E2 controlled Inventory contract; no native qualification','reads':peer.reads,'assessment':assessment,'plan':saved,'actual_inventory_findings':actual_view['results']},indent=2)+'\n')

    if extension is not None:
        extension(c, locals())
