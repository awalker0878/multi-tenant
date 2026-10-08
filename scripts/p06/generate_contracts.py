#!/usr/bin/env python3
"""P06 bounded wire contracts and exact isolated Console consumer snapshot."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def obj(p):return {'type':'object','additionalProperties':False,'properties':p,'required':list(p)}
def arr(p,n=300):return {'type':'array','items':p,'maxItems':n}
def nullable(p):return {'anyOf':[p,{'type':'null'}]}
S={'type':'string','maxLength':4096};U={'type':'string','format':'uuid'};H={'type':'string','pattern':'^[0-9a-f]{64}$'};I={'type':'integer','minimum':0};B={'type':'boolean'}
TRUE={'const':True};FALSE={'const':False}
R=lambda name:{'$ref':'#/components/schemas/'+name}
scope=obj({k:U for k in ['tenant_id','site_id','environment','resource_id','endpoint_id']}|{'native_scope':S})
observation=obj({k:U for k in ['tenant_id','job_id','operation_id','attempt_id','epoch']}|{'plan_digest':H,'simulation':TRUE,'sealed':TRUE,'effect_count':{'enum':[0,1]},'observed_at':I,'outcome':{'enum':['confirmed_succeeded','confirmed_failed']}})
evidence=obj({k:U for k in ['id','tenant_id','job_id','producer_actor_id','requested_by']}|{'plan_digest':H,'digest':H,'source_revision':{'type':'string','pattern':'^[0-9a-f]{40}$'},'evidence_level':{'const':'E2'},'state':{'const':'finalized'},'native_support':FALSE,'scope':scope,'retention_until':I,'finalized_at':I})
review=obj({k:U for k in ['id','evidence','reviewer']}|{'decision':{'enum':['accepted_simulation','rejected']},'recorded_at':I})
record=obj(evidence['properties']|{'observations':arr(observation,32),'reviews':arr(review,1000)})
job=obj({k:U for k in ['id','tenant_id','actor_id','requested_by','plan_id','approval_id']}|{'source_revision':nullable({'type':'string','pattern':'^[0-9a-f]{40}$'}),'scope':scope,'plan_digest':H,'workflow_id':S,'workflow_run_id':nullable(S),'state':{'enum':['admitted','running','held','completed','cancelled']},'reason':nullable(S),'revision':I,'observed_at':I,'updated_at':I,'simulation':TRUE,'evidence_level':{'const':'E2'},'native_write_authorized':FALSE,'cancel_requested':B,'pause_requested':B,'stop_requested':B,'resources_retained':TRUE,'evidence':nullable(evidence),'recovery_mode':{'enum':['forward_recovery_required','pre_target_write_reconciliation']},'operations':arr(obj({'id':U,'step':S,'ordinal':I,'outcome':{'enum':['not_started','attempting','outcome_unknown','confirmed_succeeded','confirmed_failed']},'revision':I,'observation':nullable(observation)}),32),'events':arr(obj({'id':U,'kind':S,'facts':{'type':'object'},'occurred_at':I}))})
action={'enum':['pause','cancel','stop','reconcile','resume','retry_unstarted']}
schemas={'Job':job,'CommandReceipt':obj({'command_id':U,'job_id':U,'action':action,'accepted':TRUE,'effect_undone':FALSE}),'Evidence':evidence,'EvidenceRecord':record,'Observation':observation,'Error':obj({'error':S})}
paths={}
for path,method,name,body,response,status in [
('/v1/tenants/{tenant}/jobs','post','admitSimulation',obj({'plan_id':U,'plan_revision':{'type':'integer','minimum':1,'maximum':999999999},'plan_digest':H,'approval_id':U,'campaign_id':U}),'Job','202'),
('/v1/tenants/{tenant}/jobs/{job}','get','readSimulation',None,'Job','200'),
('/v1/tenants/{tenant}/jobs/{job}/commands','post','controlSimulation',obj({'action':action,'expected_revision':{'type':'integer','minimum':1}}),'CommandReceipt','202')]:
    parameters=[{'in':'path','name':p,'required':True,'schema':U} for p in ('tenant','job') if '{'+p+'}' in path]
    parameters += [{'in':'header','name':'X-Actor-Delegation','required':True,'schema':H}]
    if method=='post':parameters += [{'in':'header','name':'Idempotency-Key','required':True,'schema':U}]
    op={'operationId':name,'parameters':parameters,'responses':{status:{'description':'Bounded current result; no-store, private','content':{'application/json':{'schema':R(response)}}},**{str(n):{'description':'Held or unavailable; no mutation authority','content':{'application/json':{'schema':R('Error')}}} for n in [400,401,403,404,409,413,415,422,423,503]}}}
    if body:op['requestBody']={'required':True,'content':{'application/json':{'schema':body}}}
    paths.setdefault(path,{})[method]=op
api={'openapi':'3.1.0','info':{'title':'P06 Lifecycle simulation execution','version':'1.0.0','description':'E2 isolated simulation only. Controls are requests, never proof of native undo or release. Exact live Governance authority is rechecked at each effect.'},'security':[{'Workload':[]}],'paths':paths,'components':{'securitySchemes':{'Workload':{'type':'http','scheme':'bearer'}},'schemas':schemas}}
outputs={name:api for name in ['contracts/openapi/lifecycle-v1.json','apps/console/resources/contracts/lifecycle-v1.json']}
custody_schemas={'UploadReceipt':obj({'id':U,'state':{'const':'uploaded'}}),'Evidence':evidence,'EvidenceRecord':record,'ReviewReceipt':obj(review['properties']|{'native_support':FALSE})}
custody_paths={}
for path,method,name,body,response,status,delegated in [
('/v1/tenants/{tenant}/evidence-uploads','post','uploadSimulationEvidence',obj({'job_id':U,'plan_digest':H,'source_revision':{'type':'string','pattern':'^[0-9a-f]{40}$'},'digest':H,'evidence_level':{'const':'E2'},'content_base64':{'type':'string','maxLength':90000}}),'UploadReceipt','201',False),
('/v1/tenants/{tenant}/evidence-uploads/{evidence}/finalization','post','finalizeSimulationEvidence',obj({}),'Evidence','200',False),
('/v1/tenants/{tenant}/evidence/{evidence}','get','readSimulationEvidence',None,'EvidenceRecord','200',True),
('/v1/tenants/{tenant}/evidence/{evidence}/reviews','post','reviewSimulationEvidence',obj({'decision':{'enum':['accepted_simulation','rejected']}}),'ReviewReceipt','201',True)]:
    parameters=[{'in':'path','name':p,'required':True,'schema':U} for p in ('tenant','evidence') if '{'+p+'}' in path]
    if delegated:parameters.append({'in':'header','name':'X-Actor-Delegation','required':True,'schema':H})
    op={'operationId':name,'parameters':parameters,'responses':{status:{'description':'Digest-bound E2 custody; no-store, private','content':{'application/json':{'schema':R(response)}}},**{str(n):{'description':'Access, digest, binding or owner dependency denied'} for n in [401,403,404,409,422,503]}}}
    if body is not None:op['requestBody']={'required':True,'content':{'application/json':{'schema':body}}}
    custody_paths.setdefault(path,{})[method]=op
outputs['contracts/openapi/assurance-evidence-v1.json']={'openapi':'3.1.0','info':{'title':'P06 Assurance simulation custody','version':'1.0.0','description':'E2 only. Upload/finalize require the distinct Lifecycle producer identity. Read/review require current tenant and resource-scoped Governance delegation; review cannot elevate native support.'},'security':[{'Workload':[]}],'paths':custody_paths,'components':{'securitySchemes':{'Workload':{'type':'http','scheme':'bearer'}},'schemas':custody_schemas}}
for name,document in outputs.items():
    p=ROOT/name;raw=json.dumps(document,indent=2)+'\n'
    if '--check' in sys.argv:
        if not p.exists() or p.read_text()!=raw:raise SystemExit('contract drift: '+name)
    else:p.parent.mkdir(exist_ok=True,parents=True);p.write_text(raw)
print('P06 execution, custody and isolated consumer contracts match.')
