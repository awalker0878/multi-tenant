#!/usr/bin/env python3
"""Apply exact accepted project quotas once; recover uncertain writes by reading."""
import argparse
from datetime import datetime
import http.client
import json
from pathlib import Path
import re
import ssl
import sys
import time
from urllib.parse import urlsplit

from hosting_resources import SOURCE_ROOT
ROOT = SOURCE_ROOT
from provisioner.execution import readback_core as c
from provisioner.execution import execution_journal as journal
from provisioner.execution.source_integrity import verify, verify_runtime
from provisioner.execution.run_files import current_window,digest,encoded,load_private,private_path,read_private,require,utcnow,write_new

PROFILES={
    'compute':('compute 2.79','quota_set','in_use',{'cores','instances','ram','server_groups','server_group_members'}),
    'volume':('volume 3.60','quota_set','in_use',{'volumes','snapshots','gigabytes','backups','backup_gigabytes','groups'}),
    'network':(None,'quota','used',{'network','subnet','port','router','floatingip','security_group','security_group_rule','rbac_policy','subnetpool'}),
}


def native_id(value):
    require(isinstance(value,str) and (re.fullmatch('[0-9a-f]{32}',value) or c.UUID.fullmatch(value)), 'Exact native identity required')


def domain_id(value):
    if value!='default': native_id(value)


def endpoint(value):
    require(isinstance(value,str),'Explicit service endpoint required'); parsed=urlsplit(value)
    c.origin('https://'+parsed.netloc)
    require(parsed.scheme=='https' and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
            and re.fullmatch(r'/[A-Za-z0-9_./-]+',parsed.path) and '..' not in parsed.path and not value.endswith('/'),
            'Exact HTTPS catalog endpoint without discovery or redirects required')
    return parsed


def validate(request):
    c.exact_keys(request,{'format','enabled','source_commit','operation_id','generation','scope','service',
        'identity_endpoint','endpoint','project','caller','before','after','entitlement_ref','enforcement_ref'})
    require(request['format']=='hosting-openstack-quota/1' and type(request['enabled']) is bool
            and isinstance(request['source_commit'],str) and re.fullmatch('[0-9a-f]{40}',request['source_commit']), 'Exact quota owner source required')
    c.identifier(request['operation_id'])
    require(type(request['generation']) is int and 1<=request['generation']<=2**31-1,'Positive quota generation required')
    c.exact_keys(request['scope'],{'environment_key','site_key','platform','tenant_key'})
    for value in request['scope'].values(): c.identifier(value)
    require(request['scope']['platform']=='openstack' and request['service'] in PROFILES,'Supported project quota service required')
    project=request['project']; c.exact_keys(project,{'id','domain_id','parent_id','name'})
    native_id(project['id']); domain_id(project['domain_id'])
    if project['parent_id'] is not None: domain_id(project['parent_id'])
    c.text(project['name'])
    caller=request['caller']; c.exact_keys(caller,{'user_id','user_domain_id','project_id','project_domain_id','role_ids','region','interface'})
    for name in ('user_id','project_id'): native_id(caller[name])
    for name in ('user_domain_id','project_domain_id'): domain_id(caller[name])
    require(caller['project_id']!=project['id'],'Separate accepted quota-administration project required')
    require(isinstance(caller['role_ids'],list) and 1<=len(caller['role_ids'])<=32
            and caller['role_ids']==sorted(set(caller['role_ids'])),'Exact sorted quota role identities required')
    for value in caller['role_ids']: native_id(value)
    c.text(caller['region']); require(caller['interface'] in {'internal','admin'},'Explicit administrative service interface required')
    identity=endpoint(request['identity_endpoint']); target=endpoint(request['endpoint'])
    require(identity.path.endswith('/v3'),'Identity v3 endpoint required')
    suffix={'compute':'/v2.1/'+caller['project_id'],'volume':'/v3/'+caller['project_id'],'network':'/v2.0'}[request['service']]
    require(target.path.endswith(suffix) or request['service']=='compute' and target.path.endswith('/v2.1'),'Exact quota service version/scope required')
    before,after=request['before'],request['after']
    require(isinstance(before,dict) and isinstance(after,dict) and before and set(before)==set(after)
            and set(before)<=PROFILES[request['service']][3],'Enumerate supported owned quota fields')
    require(all(type(v) is int and -1<=v<=2**53-1 for v in before.values())
            and all(type(v) is int and 0<=v<=2**53-1 for v in after.values()),'Finite nonnegative target quotas required')
    for name in ('entitlement_ref','enforcement_ref'): c.text(request[name])


def authorize(request,authority,token,ca,*,now=None):
    c.exact_keys(authority,{'format','request_sha256','action','token_sha256','ca_sha256','valid_from','valid_until',
        'change_ref','writer_exclusion_ref'})
    require(authority['format']=='hosting-openstack-quota-authority/1' and authority['request_sha256']==c.digest(request)
            and authority['action'] in {'apply','observe'} and authority['token_sha256']==digest(token)
            and authority['ca_sha256']==digest(ca),'Exact quota operation, credential and trust authority required')
    current_window(authority,now=now)
    for name in ('change_ref','writer_exclusion_ref'): c.text(authority[name])


def quota_path(request,detail=False):
    value=('/quotas/' if request['service']=='network' else '/os-quota-sets/')+request['project']['id']
    if detail: value+={'compute':'/detail','volume':'?usage=True','network':'/details.json'}[request['service']]
    return value


class Client:
    def __init__(self,request,authority,token,ca):
        self.request,self.authority,self.token,self.ca=request,authority,token,ca
        self.secret=token.decode().strip(); c.text(self.secret,'injected token',8192); self.deadline=time.monotonic()+120
        self.context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); self.context.minimum_version=ssl.TLSVersion.TLSv1_2
        self.context.verify_flags|=ssl.VERIFY_X509_STRICT; self.context.load_verify_locations(cadata=ca.decode('ascii'))

    def call(self,operation):
        r=self.request; authorize(r,self.authority,self.token,self.ca)
        require(operation in {'identity','project','read','write'},'Unsupported quota operation')
        require(operation!='write' or self.authority['action']=='apply','Read-only quota recovery cannot write')
        method='PUT' if operation=='write' else 'GET'
        address=endpoint(r['identity_endpoint'] if operation in {'identity','project'} else r['endpoint'])
        path={'identity':'/auth/tokens','project':'/projects/'+r['project']['id'],
              'read':quota_path(r,True),'write':quota_path(r)}[operation]
        body=encoded({PROFILES[r['service']][1]:r['after']}) if operation=='write' else None
        version=PROFILES[r['service']][0] if operation in {'read','write'} else None
        headers={'X-Auth-Token':self.secret,'Accept':'application/json','Accept-Encoding':'identity','Connection':'close'}
        if operation=='identity': headers['X-Subject-Token']=self.secret
        if version: headers['OpenStack-API-Version']=version
        if body is not None: headers['Content-Type']='application/json'
        def remaining():
            authorize(r,self.authority,self.token,self.ca)
            value=min(self.deadline-time.monotonic(),(c.timestamp(self.authority['valid_until'])-utcnow()).total_seconds())
            require(value>0,'Quota service contact budget exhausted'); return min(5,value)
        connection=http.client.HTTPSConnection(address.hostname,address.port or 443,context=self.context,timeout=remaining())
        try:
            connection.request(method,address.path+path,body=body,headers=headers); sock=connection.sock; response=connection.getresponse()
            require(response.status==200 and response.getheader('Content-Type','').split(';')[0]=='application/json'
                    and response.getheader('Content-Encoding','identity')=='identity','Quota service response rejected')
            if version: require(response.getheader('OpenStack-API-Version')==version,'Quota service microversion differs')
            sizes=response.headers.get_all('Content-Length',[])
            require(len(sizes)<=1 and (not sizes or sizes[0].isdigit() and int(sizes[0])<=c.LIMIT)
                    and not (sizes and response.getheader('Transfer-Encoding')),'Ambiguous quota response framing')
            raw=bytearray()
            while True:
                timeout=remaining()
                if sock and sock.fileno()>=0: sock.settimeout(timeout)
                part=response.read1(min(65536,c.LIMIT+1-len(raw)))
                if not part: break
                raw.extend(part); require(len(raw)<=c.LIMIT,'Quota response exceeds bound')
            require(not sizes or len(raw)==int(sizes[0]),'Truncated quota response')
            return c.strict_loads(raw)
        finally: connection.close()


def identities(request,client):
    token=client.call('identity')['token']; caller=request['caller']; project=request['project']
    require(token['user']['id']==caller['user_id'] and token['user']['domain']['id']==caller['user_domain_id']
            and token['project']['id']==caller['project_id'] and token['project']['domain']['id']==caller['project_domain_id']
            and not token.get('system') and not token.get('domain'),'Quota credential scope differs')
    require(c.timestamp(token['issued_at'])<=utcnow()<c.timestamp(token['expires_at']),'Quota credential expired or future-dated')
    require(isinstance(token['roles'],list) and sorted(row['id'] for row in token['roles'])==caller['role_ids'],'Quota role identities differ')
    service_type={'compute':'compute','volume':'volumev3','network':'network'}[request['service']]
    matches=[value for service in token['catalog'] if service['type']==service_type for value in service['endpoints']
             if value['interface']==caller['interface'] and value.get('region_id',value.get('region'))==caller['region']
             and value['url'].rstrip('/')==request['endpoint']]
    require(len(matches)==1,'Quota endpoint is absent or ambiguous in the accepted token catalog')
    observed=client.call('project')['project']
    require(all(observed.get(key)==value for key,value in project.items()) and observed.get('enabled') is True
            and observed.get('is_domain') is False,'Target project identity, domain or lifecycle differs')


def quotas(request,document,expected):
    _,envelope,used,_=PROFILES[request['service']]; rows=document[envelope]
    require(isinstance(rows,dict),'Quota detail object required')
    if request['service']!='network': require(rows.get('id')==request['project']['id'],'Quota project identity differs')
    result={}
    for name,limit in expected.items():
        row=rows[name]; c.exact_keys(row,{'limit',used,'reserved'})
        require(type(row['limit']) is int and row['limit']==limit
                and all(type(row[key]) is int and row[key]>=0 for key in (used,'reserved')),'Quota limit or usage differs')
        require(row[used]+row['reserved']<=request['after'][name],'Target quota is below allocated or reserved usage')
        result[name]={'limit':row['limit'],'used':row[used],'reserved':row['reserved']}
    return result


def owner_scope(request):
    base=request['endpoint']; caller=request['caller']['project_id']
    if request['service'] in {'compute','volume'} and base.endswith('/'+caller): base=base[:-(len(caller)+1)]
    return {'owner':'openstack-quota','service':request['service'],'endpoint':base,'project_id':request['project']['id']}


def history(log,scope):
    operations=[]
    for event in log.events:
        data=event['data']
        if event['kind']=='QUOTA_CHANGE_STARTED':
            c.exact_keys(data,{'request','before'}); request=data['request']; validate(request)
            require(owner_scope(request)==log.scope and request['scope']==scope and request['generation']==len(operations)+1
                    and (not operations or operations[-1]['completed'] and operations[-1]['request']['after']==request['before'])
                    and request['operation_id'] not in {value['request']['operation_id'] for value in operations},
                    'Quota history identity, generation or prior hold differs')
            require(set(data['before'])==set(request['before']) and all(data['before'][k]['limit']==v for k,v in request['before'].items()),
                    'Quota initial observation changed')
            operations.append({'request':request,'completed':False})
        elif event['kind']=='QUOTA_CHANGE_OBSERVED':
            c.exact_keys(data,{'request_sha256','after'})
            require(operations and not operations[-1]['completed'] and data['request_sha256']==c.digest(operations[-1]['request'])
                    and {k:v['limit'] for k,v in data['after'].items()}==operations[-1]['request']['after'],'Quota completion history differs')
            operations[-1]['completed']=True
        else: raise ValueError('Unknown quota history event')
    return operations


def operate(request,authority,token,ca,ledger,*,root=ROOT,client=None):
    validate(request); require(request['enabled'],'Quota operation is disabled'); authorize(request,authority,token,ca)
    require(isinstance(root,Path) and verify_runtime(root)['status']=='RUNTIME_SOURCES_MATCH',
            'Exact runtime and explicitly selected source checkout required')
    source=verify(root)
    require(source['status']=='HASHES_MATCH' and source['commit']==request['source_commit'],'Quota owner source changed')
    client=client or Client(request,authority,token,ca)
    scope=owner_scope(request)
    with journal.locked(ledger,scope) as log:
        operations=history(log,request['scope'])
        prior=next((row for row in operations if row['request']['operation_id']==request['operation_id']),None)
        if prior:
            require(prior['request']==request and prior is operations[-1],'Quota operation changed or was superseded')
            require(prior['completed'] or authority['action']=='observe','Unknown quota write requires read-only recovery')
        else:
            require(authority['action']=='apply' and request['generation']==len(operations)+1
                    and (not operations or operations[-1]['completed'] and operations[-1]['request']['after']==request['before']),
                    'Quota generation, previous limits or pending native outcome differs')
        identities(request,client)
        expected=request['after'] if prior else request['before']
        before=quotas(request,client.call('read'),expected)
        require(quotas(request,client.call('read'),expected)==before,'Quota usage changed during preflight')
        if prior is None:
            authorize(request,authority,token,ca)
            log.append('QUOTA_CHANGE_STARTED',{'request':request,'before':before})
            if request['before']!=request['after']:
                response=client.call('write')[PROFILES[request['service']][1]]
                require(all(type(response.get(k)) is int and response[k]==v for k,v in request['after'].items()),'Quota update response differs')
        after=quotas(request,client.call('read'),request['after'])
        identities(request,client)
        require(quotas(request,client.call('read'),request['after'])==after,'Quota usage changed during verification')
        authorize(request,authority,token,ca)
        if prior is None or not prior['completed']:
            log.append('QUOTA_CHANGE_OBSERVED',{'request_sha256':c.digest(request),'after':after})
        result={'format':'hosting-openstack-quota-receipt/1','status':'PROJECT_QUOTAS_OBSERVED_REQUIRES_ENFORCEMENT_ACCEPTANCE',
            'request_sha256':c.digest(request),'authority_sha256':c.digest(authority),'scope':request['scope'],
            'project_id':request['project']['id'],'service':request['service'],'generation':request['generation'],
            'quotas':after,'observed_at':utcnow().isoformat(),'native_fencing':False,'delegated_rbac_qualified':False,
            'capacity_reserved':False,'production_activation':False}
        write_new(log.directory/('receipt-'+digest(encoded(result))+'.receipt'),encoded(result)); return result


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--request',type=Path,required=True)
    for name in ('authority','token','ca','ledger'): parser.add_argument('--'+name,type=Path)
    parser.add_argument('--source-root',type=Path,default=ROOT)
    parser.add_argument('--execute',action='store_true'); args=parser.parse_args()
    try:
        request=load_private(args.request); validate(request)
        if not args.execute: print('{"status":"VALIDATED_NO_CONTACT"}'); return 0
        require(all((args.authority,args.token,args.ca,args.ledger)),'Exact private quota custody required')
        result=operate(request,load_private(args.authority),read_private(args.token),read_private(args.ca),args.ledger,root=args.source_root)
        print(json.dumps({'status':result['status']})); return 0
    except Exception:
        print('{"status":"OPENSTACK_QUOTA_HELD","reason":"Preserve quota intent and writer exclusion; observe uncertain writes without repeating them"}')
        return 2


if __name__=='__main__': raise SystemExit(main())
