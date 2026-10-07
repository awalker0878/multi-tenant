#!/usr/bin/env python3
"""Publish the P05 wire schema and copy the exact Console consumer snapshot."""
import sys
import copy
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
changed=[]
def emit(path,value):
    target=ROOT/path; expected=json.dumps(value,indent=2)+'\n'
    if '--check' in sys.argv:
        if not target.exists() or target.read_text()!=expected: changed.append(path)
    else:
        target.parent.mkdir(parents=True,exist_ok=True);target.write_text(expected)
S={'type':'string'}
I={'type':'integer','minimum':0}
B={'type':'boolean'}
U={'type':'string','format':'uuid'}
H={'type':'string','pattern':'^[0-9a-f]{64}$'}
O={'type':'object'}
def array(item):return {'type':'array','items':item,'maxItems':1000}
def obj(properties,optional=()):return {'type':'object','additionalProperties':False,'properties':properties,'required':[k for k in properties if k not in optional]}
def ref(name):return {'$ref':'#/components/schemas/'+name}
scope=obj({k:U for k in ('tenant_id','site_id','environment','resource_id','endpoint_id')}|{'native_scope':S})
candidate=obj({k:U for k in ('site_id','endpoint_id','generation_id')})
finding=obj({'requirement':S,'source':S,'status':{'enum':['eligible','conditional','blocked','unknown']},'reason':S,'remediation':S,'mandatory':B})
result=obj({'site_id':U,'endpoint_id':U,'generation_id':U,'platform':{'enum':['vmware','ahv','openstack']},'status':finding['properties']['status'],'operationally_eligible':B,'findings':array(finding),'input_digests':obj({k:H for k in ('inventory','profile','policy','qualification','intent')}),'demand':obj({k:I for k in ('vcpus','memory_mib','storage_gib','addresses')}),'reserved':{'const':False},'expires_at':I})
base=json.loads((ROOT/'contracts/openapi/planning-immutable-plan-v1.json').read_text())
binding=copy.deepcopy(base['components']['schemas']['BoundPlan'])
binding['properties'].update(content_digest=H,canonicalization={'const':'p05-json-v1'},lane={'enum':['operational','isolated_campaign']})
binding['required']+=['content_digest','canonicalization','lane']
base['info']['version']='1.1.0';base['info']['description']='P05 producer binding. The semantic content digest and authority lane are included in the canonical approval digest. Version 1.0 is retained only as the historical P02 consumer contract.'
base['components']['schemas']['BoundPlan']=binding
emit('contracts/openapi/planning-immutable-plan-v1.1.json',base)
content=obj({'schema_version':{'const':1},'canonicalization':{'const':'p05-json-v1'},'scope':scope,'action':binding['properties']['action'],'method':S,'lane':binding['properties']['lane'],'executor_ids':array(U),'valid_until':I,'input_fresh_until':I,'input_digests':result['properties']['input_digests'],'intent_revision':U,'inventory_generation':U,'installed_tuple':O,'artifacts':obj({k:H for k in ('compiler','adapter','automation','contracts')}),'terraform':{'type':['object','null']},'ownership':array(O),'mappings':array(O),'effects':array(obj({'id':S,'after':array(S),'owner':S,'scope':scope,'artifact_digest':H,'destructive':B,'boundary':S,'on_unknown':{'const':'hold_and_observe_before_retry'},'authority_recheck':{'const':'immediately_before_effect'}})),'reservation_intents':array(O),'budgets':O,'recovery':O,'execution_ready':B,'holds':array(S),'native_write_authorized':{'const':False}})
validity=obj({'current':B,'holds':array(S),'evaluated_at':I,'approval_digest':H,'native_write_authorized':{'const':False}})
assessment=obj({'id':U,'tenant_id':U,'application_id':U,'environment':U,'created_at':I,'intent':O,'inputs':array(O),'results':array(result),'candidates':array(candidate),'action':binding['properties']['action'],'method':S})
plan=obj({'id':U,'assessment_id':U,'content':content,'binding':binding,'candidates':array(candidate),'candidate':I,'application_id':U,'environment':U,'tenant_id':U,'validity':validity})
receipt=obj({'id':U,'kind':{'enum':['assessment','plan']},'digest':H,'native_write_authorized':{'const':False},'binding':binding},('binding',))
diff=obj({'changes':array(obj({'path':S,'change':{'enum':['added','removed','changed']}})),'approval_reusable':B})
schemas={'BoundPlan':binding,'Content':content,'Assessment':assessment,'Plan':plan,'Validity':validity,'Receipt':receipt,'Diff':diff,'Candidate':candidate}
basepath='/v1/tenants/{tenant}/applications/{application}/environments/{environment}'
paths={}
operations=[('POST','/assessments','createAssessment','Receipt',201),('GET','/assessments/{record}','getAssessment','Assessment',200),('POST','/plans','createPlan','Receipt',201),('GET','/plans/{record}','getPlan','Plan',200),('POST','/plans/{record}/validity','checkPlanValidity','Validity',200),('POST','/plans/{record}/diff','comparePlans','Diff',200)]
for method,path,name,schema,status in operations:
    params=[{'in':'path','name':k,'required':True,'schema':U} for k in ('tenant','application','environment')]+([{'in':'path','name':'record','required':True,'schema':U}] if '{record}' in path else [])
    params += [{'in':'header','name':'X-Planning-Delegations','required':True,'schema':{'type':'string','maxLength':500}}]
    if status==201:params += [{'in':'header','name':'Idempotency-Key','required':True,'schema':U}]
    op={'operationId':name,'parameters':params,'responses':{str(status):{'description':'Current authorized result; no-store, private','content':{'application/json':{'schema':ref(schema)}}}}}
    for error in (401,403,404,409,413,422,429,503):op['responses'][str(error)]={'description':'Denied, held or unavailable; no native dispatch'}
    if method=='POST':
        if path=='/assessments':body=obj({'revision_id':U,'action':binding['properties']['action'],'method':S,'candidates':{'type':'array','minItems':1,'maxItems':3,'items':candidate}})
        elif path=='/plans':body=obj({'assessment_id':U,'candidate':{'type':'integer','minimum':0,'maximum':2},'request':obj({'action':binding['properties']['action'],'method':S,'lane':binding['properties']['lane'],'executor_ids':{'type':'array','minItems':1,'maxItems':32,'items':U},'valid_until':I})})
        elif path.endswith('/diff'):body=obj({'other_plan_id':U})
        else:body=obj({})
        op['requestBody']={'required':True,'content':{'application/json':{'schema':body}}}
    paths[basepath+path]={method.lower():op}
api={'openapi':'3.1.0','info':{'title':'Planning assessment and immutable review API','version':'1.0.0','description':'At most three exact destinations, synchronous bounded computation, tenant/actor command receipts. Every source owner rechecks current request-bound Planning authority. A plan grants no native authority.'},'security':[{'ConsoleWorkload':[]}],'paths':paths,'components':{'securitySchemes':{'ConsoleWorkload':{'type':'http','scheme':'bearer'}},'schemas':schemas}}
for path in ('contracts/openapi/planning-v1.json','apps/console/resources/contracts/planning-v1.json'):emit(path,api)
# Reservation and admission are owner contracts, not unauthenticated execution endpoints.
(ROOT/'contracts/schemas/planning').mkdir(exist_ok=True)
for name,schema in [('content-v1',content),('admission-record-v1',obj({'contract_version':{'const':1},'admissible':B,'holds':array(S),'plan_digest':H,'content_digest':H,'scope':scope,'lane':binding['properties']['lane'],'evaluated_at':I,'current_receipts_digest':H,'native_write_authorized':{'const':False},'atomic_record_required':array(S),'recheck_boundaries':array(S)})),('reservation-receipt-v1',obj({'reservation_id':U,'receipt_id':S,'owner':S,'kind':S,'amount':{'type':'integer','minimum':1},'scope':O,'plan_digest':H,'state':{'enum':['reserved','confirmed','released','denied','outcome_unknown']},'in_use':B,'observed_at':I,'expires_at':I}))]:
 emit(f'contracts/schemas/planning/{name}.json',{'$schema':'https://json-schema.org/draft/2020-12/schema',**schema})

# Owner responses have closed envelopes; extensible capability keys remain data.
capability=obj({'status':{'enum':['observed','supported','unsupported','unknown']},'expires_at':I,'values':array({}),'dependencies':array(S)})
capabilities={'type':'object','additionalProperties':capability,'maxProperties':1000}
dimensions=['installed_identity','compute_placement','storage_datasets','network_vpc','security_edge','guest_image','lifecycle_adoption','mobility','shared_services','resilience_operations','assurance_sovereignty']
artifacts=obj({k:H for k in ('compiler','adapter','automation','contracts')})
qscope=obj({k:U for k in ['tenant_id','site_id','endpoint_id']}|{'native_scope':S,'installed_tuple':O,'action':binding['properties']['action'],'method':S,'profile_digest':H,'artifacts':artifacts})
qualification=obj({'id':{'type':['string','null']},'version':{'type':'integer','minimum':1},'status':{'enum':['qualified','unknown','unsupported']},'evidence_level':{'enum':[None,'E0','E1','E2','E3','E4']},'expires_at':I,'revoked':B,'scope':qscope,'evidence_refs':array(S),'dimensions':array({'enum':dimensions}),'capabilities':capabilities})
inventory=obj({k:U for k in ['tenant_id','site_id','endpoint_id','generation_id']}|{'platform':{'enum':['vmware','ahv','openstack']},'native_scope':S,'current':B,'completion':S,'expires_at':I,'holds':array(S),'installed_provenance':{'enum':['declaration','observed','unknown']},'installed_tuple':O,'dimensions':obj({k:{'enum':['observed','unassessed','unsupported']} for k in dimensions}),'capabilities':capabilities,'capacity':{'type':'object','additionalProperties':False,'properties':{k:I for k in ['vcpus','memory_mib','storage_gib','addresses']}},'domain_bindings':O,'workload_bindings':O})
cat=json.loads((ROOT/'contracts/openapi/catalogue-v1.json').read_text())
catrevision={**obj({'id':U,'application_id':U,'digest':H,'intent':{'$ref':'#/components/schemas/Intent'}}),'components':cat['components']}
for name,schema in [('catalogue-input-v1',catrevision),('inventory-input-v1',inventory),('qualification-v1',qualification)]:
    schema={'$schema':'https://json-schema.org/draft/2020-12/schema',**schema}
    emit('contracts/schemas/planning/'+name+'.json',schema)
    emit('services/planning/src/planning/infrastructure/inputs/'+name+'.json',schema)
# Source-owner wire contract uses each receiving owner's workload identity.
delegation=json.loads((ROOT/'contracts/openapi/governance-delegation-v1.1.json').read_text())
current=copy.deepcopy(delegation['components']['schemas']['CurrentDelegation'])
current['properties'].update(source_owner={'enum':['catalogue','inventory','assurance']},source_use={'const':'planning_read_only'})
current['required']+=['source_owner','source_use']
source_scope=obj({k:U for k in ['site_id','environment','resource_id']})
source_action={'enum':['plan.read','plan.create']}
owner_schemas={**cat['components']['schemas'],**delegation['components']['schemas'],'CatalogueInput':catrevision.copy(),'InventoryInput':inventory,'Qualification':qualification,'SourceDecision':current}
owner_schemas['CatalogueInput'].pop('components')
owner_paths={}
for owner,method,path,name,response_schema,body in [
 ('governance','post','/v1/tenants/{tenant}/planning-input-checks','authorizePlanningSource','SourceDecision',obj({'action':source_action,'scope':source_scope})),
 ('catalogue','get','/v1/tenants/{tenant}/planning-inputs/{application}/{environment}/{site}/{revision}','readPlanningIntent','CatalogueInput',None),
 ('inventory','get','/v1/tenants/{tenant}/planning-inputs/{application}/{environment}/{site}/{endpoint}/{generation}','readPlanningInventory','InventoryInput',None),
 ('assurance','post','/v1/tenants/{tenant}/planning-qualification','readPlanningQualification','Qualification',obj({'scope':source_scope,'action':source_action,'qualification_scope':qscope}))]:
 import re
 params=[{'in':'path','name':k,'required':True,'schema':U} for k in re.findall(r'{(.*?)}',path)]
 params.append({'in':'header','name':'X-Actor-Delegation','required':True,'schema':H})
 if owner!='governance':params.append({'in':'header','name':'X-Planning-Action','required':True,'schema':source_action})
 operation={'operationId':name,'tags':[owner],'parameters':params,'responses':{'200':{'description':'Current owner response; no-store, private','content':{'application/json':{'schema':ref(response_schema)}}},'403':{'description':'Current scope denied'},'503':{'description':'Owner or authority unavailable'}}}
 if body:operation['requestBody']={'required':True,'content':{'application/json':{'schema':body}}}
 owner_paths[path]={method:operation}
emit('contracts/openapi/planning-inputs-v1.json',{'openapi':'3.1.0','info':{'title':'P05 independent source-owner reads','version':'1.0.0','description':'Each tagged route is hosted by its named owner. Workload credentials are separate per link. Original Planning delegation is checked again by each owner through Governance; no native authority.'},'security':[{'OwnerWorkload':[]}],'paths':owner_paths,'components':{'securitySchemes':{'OwnerWorkload':{'type':'http','scheme':'bearer'}},'schemas':owner_schemas}})
event=obj({'specversion':{'const':'1.0'},'event_id':U,'tenant_id':U,'event_type':{'enum':['planning.assessment.created','planning.plan.created']},'aggregate_id':U,'occurred_at':I,'sequence':{'type':'integer','minimum':1},'data':receipt})
emit('contracts/schemas/planning/fact-v1.json',{'$schema':'https://json-schema.org/draft/2020-12/schema',**event})
# Isolated builds must own their fixtures; exact copies are checked at repository qualification.
copies=[('contracts/fixtures/planning/synthetic-plan-v1.1.json','services/lifecycle/tests/fixtures/synthetic-plan-v1.json'),('contracts/fixtures/planning/synthetic-plan-v1.1.json','services/governance/tests/Fixtures/synthetic-plan-v1.json'),('contracts/schemas/inventory/fact-v1.1.json','services/planning/src/planning/infrastructure/facts/inventory.json'),('contracts/schemas/events/catalogue-intent-v1.json','services/planning/src/planning/infrastructure/facts/catalogue.json')]
for source,target in copies:
    if (ROOT/source).read_bytes()!=(ROOT/target).read_bytes():changed.append(target+' differs from '+source)
if changed:raise SystemExit('Contract or fixture drift: '+', '.join(changed))
print('P05 owner, review and admission contracts match their consumer snapshots.')
