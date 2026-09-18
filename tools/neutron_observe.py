#!/usr/bin/env python3
"""Read-only, exact-ID Neutron observations over verified HTTPS.

No discovery, pagination, link following, mutations or implicit credential acquisition.
A matching API snapshot is not packet-path qualification or proof of complete inventory.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import tempfile
import urllib.error
import urllib.parse
import urllib.request

LIMIT=4*1024*1024
BASE={'id','project_id','tenant_id','revision_number','status','updated_at'}
FIELDS={
 'network':BASE|{'admin_state_up','shared','router:external','port_security_enabled','subnets','mtu'},
 'router':BASE|{'admin_state_up','routes','external_gateway_info','distributed','ha'},
 'port':BASE|{'network_id','admin_state_up','port_security_enabled','security_groups','fixed_ips','allowed_address_pairs','device_owner','device_id','binding:vif_type','binding:vnic_type'},
 'subnet':BASE|{'network_id','cidr','ip_version','gateway_ip','enable_dhcp','dns_nameservers','host_routes','ipv6_address_mode','ipv6_ra_mode'},
 'security_group':BASE|{'security_group_rules','stateful','shared'},
}
REQUIRED={
 'network':{'admin_state_up','shared','router:external','port_security_enabled'},
 'router':{'admin_state_up','routes','external_gateway_info'},
 'port':{'network_id','admin_state_up','port_security_enabled','security_groups','fixed_ips','allowed_address_pairs'},
 'subnet':{'network_id','cidr','ip_version','gateway_ip','enable_dhcp','dns_nameservers','host_routes'},
 'security_group':{'security_group_rules'},
}
COLLECTION={'network':'networks','router':'routers','port':'ports','subnet':'subnets','security_group':'security-groups'}
UUID=re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
PROJECT=re.compile(r'^[0-9a-fA-F-]{32,36}$')


def strict_loads(data: str|bytes):
 def pairs(items):
  result={}
  for k,v in items:
   if k in result:raise ValueError('Duplicate JSON key')
   result[k]=v
  return result
 return json.loads(data,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Non-finite JSON number')))


def digest(value)->str:
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def canonical(value):
 if isinstance(value,dict):return {k:canonical(v) for k,v in sorted(value.items())}
 if isinstance(value,list):return sorted((canonical(x) for x in value),key=lambda x:json.dumps(x,sort_keys=True))
 return value


def equal(actual,expected)->bool:
 # JSON boolean true is not the integer 1. Array order is immaterial for the
 # selected Neutron route/group/address collections; duplicates remain visible.
 if type(actual) is not type(expected):return False
 if isinstance(actual,dict):return set(actual)==set(expected) and all(equal(actual[k],expected[k]) for k in actual)
 if isinstance(actual,list):
  a,b=canonical(actual),canonical(expected)
  return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
 return actual==expected


def validate_manifest(manifest:dict)->None:
 if not isinstance(manifest,dict) or set(manifest)!={'project_id','engineering_record_ref','resources'}:
  raise ValueError('Exact project, engineering record and resource list required')
 if not isinstance(manifest['project_id'],str) or not PROJECT.fullmatch(manifest['project_id']):raise ValueError('Invalid project ID')
 if not isinstance(manifest['engineering_record_ref'],str) or not manifest['engineering_record_ref'].strip():raise ValueError('Engineering record required')
 resources=manifest['resources']
 if not isinstance(resources,list) or not 1<=len(resources)<=100:raise ValueError('Provide 1-100 exact resources')
 seen=set()
 for r in resources:
  if not isinstance(r,dict) or set(r)!={'kind','id','expected'}:raise ValueError('Invalid resource selector')
  if r['kind'] not in FIELDS or not isinstance(r['id'],str) or not UUID.fullmatch(r['id']):raise ValueError('Invalid resource kind/UUID')
  key=(r['kind'],r['id'])
  if key in seen:raise ValueError('Duplicate resource selector')
  seen.add(key)
  exp=r['expected']
  if not isinstance(exp,dict) or not REQUIRED[r['kind']]<=set(exp) or set(exp)-FIELDS[r['kind']]:raise ValueError('Required or unsupported expected fields')
  if set(exp)&{'id','project_id','tenant_id'}:raise ValueError('Identity is specified by the selector, not expected fields')


class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):
  raise ValueError('Redirect refused; no credentials forwarded')


class Client:
 def __init__(self,endpoint:str,expected_origin:str,token:str,ca_file:str|None=None):
  u=urllib.parse.urlsplit(endpoint)
  origin=urllib.parse.urlsplit(expected_origin)
  for x in (u,origin):
   if x.scheme!='https' or not x.hostname or x.username or x.password or x.query or x.fragment:raise ValueError('Verified HTTPS origin without credentials/query required')
  if origin.path not in ('','/') or u.netloc.lower()!=origin.netloc.lower():raise ValueError('Endpoint differs from explicitly accepted origin')
  if u.path.rstrip('/')!='/v2.0':raise ValueError('Endpoint must terminate in /v2.0; service discovery is not performed')
  if not token or '\n' in token or '\r' in token:raise ValueError('Valid scoped token must be injected')
  # Explicit context avoids SSLKEYLOGFILE causing ambient TLS session-secret export.
  context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
  context.minimum_version=ssl.TLSVersion.TLSv1_2
  context.verify_flags |= ssl.VERIFY_X509_STRICT
  if ca_file:context.load_verify_locations(cafile=ca_file)
  else:context.load_default_certs(ssl.Purpose.SERVER_AUTH)
  self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPSHandler(context=context))
  self.endpoint=endpoint.rstrip('/')
  self.token=token
 def get(self,kind:str,identity:str)->dict:
  if kind not in FIELDS or not UUID.fullmatch(identity):raise ValueError('Invalid exact resource request')
  query=urllib.parse.urlencode([('fields',x) for x in sorted(FIELDS[kind])])
  request=urllib.request.Request(f'{self.endpoint}/{COLLECTION[kind]}/{identity}?{query}',headers={'X-Auth-Token':self.token,'Accept':'application/json'},method='GET')
  with self.opener.open(request,timeout=10) as response:
   if response.status!=200:raise ValueError('Unexpected status')
   if response.headers.get_content_type()!='application/json':raise ValueError('Unexpected content type')
   raw=response.read(LIMIT+1)
   if len(raw)>LIMIT:raise ValueError('Response too large')
  document=strict_loads(raw)
  item=document.get(kind) if isinstance(document,dict) else None
  if not isinstance(item,dict):raise ValueError('Missing response object')
  return {k:v for k,v in item.items() if k in FIELDS[kind]}


def compare(resource:dict,actual:dict,project_id:str)->dict:
 checks=[]
 def check(field,expected):
  if field not in actual:status='UNKNOWN'
  else:status='MATCH' if equal(actual[field],expected) else 'DIFFERENT'
  checks.append({'field':field,'status':status})
 check('id',resource['id'])
 project=actual.get('project_id',actual.get('tenant_id'))
 checks.append({'field':'project_scope','status':'UNKNOWN' if project is None else 'MATCH' if project==project_id else 'DIFFERENT'})
 if 'tenant_id' in actual and 'project_id' in actual and actual['tenant_id']!=actual['project_id']:
  checks.append({'field':'project_alias_consistency','status':'DIFFERENT'})
 for key,value in resource['expected'].items():check(key,value)
 status='DIFFERENT' if any(c['status']=='DIFFERENT' for c in checks) else 'INCONCLUSIVE' if any(c['status']=='UNKNOWN' for c in checks) else 'MATCH'
 return {'kind':resource['kind'],'id':resource['id'],'status':status,'checks':checks,
         'observed':actual,'observed_sha256':digest(actual)}


def observe(manifest:dict,client:Client)->dict:
 validate_manifest(manifest)
 captures=[]
 start=datetime.now(timezone.utc).isoformat()
 for resource in manifest['resources']:
  try:
   first=client.get(resource['kind'],resource['id'])
   second=client.get(resource['kind'],resource['id'])
   result=compare(resource,second,manifest['project_id'])
   result['stable_two_reads']=equal(first,second)
   if not result['stable_two_reads']:result['status']='INCONCLUSIVE'
  except (OSError,ValueError,urllib.error.URLError) as exc:
   # Never store a response body, authorization header or URL error text.
   result={'kind':resource['kind'],'id':resource['id'],'status':'INCONCLUSIVE','error_class':type(exc).__name__}
   if isinstance(exc,urllib.error.HTTPError):result['http_status']=exc.code
  captures.append(result)
 status='DIFFERENCES_OBSERVED' if any(x['status']=='DIFFERENT' for x in captures) else 'INCONCLUSIVE' if any(x['status']!='MATCH' for x in captures) else 'OBSERVED_MATCH_NOT_QUALIFIED'
 return {'kind':'SCOPED_NEUTRON_READBACK','status':status,'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),
         'manifest_sha256':digest(manifest),'engineering_record_ref':manifest['engineering_record_ref'],
         'mutations_performed':False,'captures':captures,
         'limitations':['Only explicitly enumerated resources; complete inventory not established',
                        'Two stable reads are not an atomic snapshot','No native forwarding/HA/RBAC bypass verification',
                        'No approval/signature verification','No automatic activation or remediation']}


def write_private(path:Path,value:dict)->None:
 path.parent.mkdir(parents=True,exist_ok=True)
 fd,temp=tempfile.mkstemp(prefix='.readback-',dir=path.parent)
 try:
  with os.fdopen(fd,'w') as stream:json.dump(value,stream,indent=2);stream.write('\n')
  os.replace(temp,path)
 finally:
  if os.path.exists(temp):os.unlink(temp)


def main()->int:
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('manifest',type=Path);p.add_argument('--endpoint',required=True);p.add_argument('--expected-origin',required=True)
 p.add_argument('--ca-file');p.add_argument('--output',type=Path,required=True)
 p.add_argument('--read-authorized-target',action='store_true',help='Explicit consent to bounded read-only target contact')
 a=p.parse_args()
 if not a.read_authorized_target:p.error('No target contacted. --read-authorized-target is required.')
 try:
  manifest=strict_loads(a.manifest.read_bytes());validate_manifest(manifest)
  client=Client(a.endpoint,a.expected_origin,os.environ.get('OS_TOKEN',''),a.ca_file)
  result=observe(manifest,client);write_private(a.output,result)
 except (ValueError,OSError):
  print('{"status":"INVALID_INPUT_OR_TRUST_CONFIGURATION"}');return 4
 print(json.dumps({'status':result['status'],'resources':len(result['captures']),'mutations_performed':False}))
 return 0 if result['status']=='OBSERVED_MATCH_NOT_QUALIFIED' else 2 if result['status']=='DIFFERENCES_OBSERVED' else 3

if __name__=='__main__':raise SystemExit(main())
