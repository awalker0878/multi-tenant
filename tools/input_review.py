#!/usr/bin/env python3
"""Read-only review of non-secret, single-root implementation inputs.

Rejects missing/extra inputs, wrong primitive types, placeholders, documentation
addresses and inconsistent gateway offsets. It neither allocates addresses nor
verifies external approvals, signatures, capability records or cloud credentials.
Credentials belong in the protected execution environment, never this JSON file.
"""
from __future__ import annotations
import argparse
import ipaddress
import json
import re
from pathlib import Path
try:
 from tools.route_audit import DOC_NETS, load_json
except ModuleNotFoundError:
 from route_audit import DOC_NETS, load_json

PLACEHOLDER=re.compile(r'(REQUIRED|MOCK|EXAMPLE|NOT-ASSIGNED|REPLACE|<|>)',re.I)
REPEATED_UUID=re.compile(r'^([a-fA-F0-9])\1{7}-')
SECRET_NAMES={'platform_password','password','api_key','token','secret','admin_pass'}


def review_inputs(root:dict,inputs:dict)->dict:
 if not isinstance(root,dict) or not isinstance(inputs,dict):raise ValueError('Objects required.')
 variables=root.get('variable')
 if not isinstance(variables,dict) or not variables:raise ValueError('Root variable definitions required.')
 errors=[];notes=[]
 def error(code,field):errors.append({'code':code,'field':field})
 for key in inputs:
  if key in SECRET_NAMES or (key in variables and variables[key].get('sensitive') is True):error('SECRET_IN_INPUT_FILE',key)
  if key not in variables:error('UNKNOWN_INPUT',key)
 resolved={}
 for key,spec in variables.items():
  if spec.get('sensitive') is True:
   notes.append({'code':'SECRET_INJECTION_NOT_VERIFIED','field':key});continue
  if key not in inputs:
   if 'default' not in spec:error('MISSING_REQUIRED_INPUT',key);continue
   value=spec['default']
  else:value=inputs[key]
  resolved[key]=value;typ=spec.get('type')
  if (typ=='string' and not isinstance(value,str)) or (typ=='bool' and type(value) is not bool) or (typ=='number' and (type(value) not in {int,float})):
   error('WRONG_INPUT_TYPE',key);continue
  if isinstance(value,str):
   if not value.strip():error('EMPTY_REQUIRED_VALUE',key)
   elif PLACEHOLDER.search(value) or value.lower().endswith('.example') or REPEATED_UUID.match(value):error('PLACEHOLDER_NOT_SITE_VALUE',key)
  if key in {'tenant_key','workload_key'} and isinstance(value,str) and not re.fullmatch(r'[a-z][a-z0-9-]{1,40}',value):error('INVALID_LOGICAL_ID',key)
  if key=='domain_key' and isinstance(value,str) and not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]{1,23}',value):error('INVALID_LOGICAL_ID',key)
  if key in {'ipv4_cidr','ipv4_address'}:
   try:
    addr=ipaddress.ip_network(value,strict=True) if key=='ipv4_cidr' else ipaddress.ip_address(value)
    if addr.version!=4:error('UNSUPPORTED_ADDRESS_FAMILY',key)
    else:
     if any(addr.subnet_of(n) if isinstance(addr,ipaddress.IPv4Network) else addr in n for n in DOC_NETS if n.version==4):error('DOCUMENTATION_ADDRESS_NOT_DEPLOYABLE',key)
     ip=addr.network_address if isinstance(addr,ipaddress.IPv4Network) else addr
     if ip.is_loopback or ip.is_multicast or ip.is_link_local or ip.is_unspecified:error('UNUSABLE_INFRASTRUCTURE_ADDRESS',key)
   except (ValueError,TypeError):error('INVALID_ADDRESS',key)
 for key in ('vcpu','memory_gib','boot_disk_gib','data_disk_gib','gateway_host_number','quarantine_sequence'):
  if key not in resolved:continue
  value=resolved[key];minimum=0 if key=='data_disk_gib' else 1
  if type(value) not in {int,float} or value!=int(value) or value<minimum:error('INVALID_CAPACITY_OR_INDEX',key)
 if resolved.get('allow_restricted_build') is not True:error('RESTRICTED_BUILD_NOT_OPTED_IN','allow_restricted_build')
 if 'ipv4_cidr' in resolved:
  try:
   net=ipaddress.ip_network(resolved['ipv4_cidr']);host=resolved.get('gateway_host_number',1)
   if type(host) not in {int,float} or host!=int(host) or host<=0 or host>=net.num_addresses-1:error('GATEWAY_NOT_USABLE_IN_PREFIX','gateway_host_number')
  except (TypeError,ValueError):pass
 return {'status':'BLOCKED_INPUTS' if errors else 'INPUT_SHAPE_CHECKED_NOT_AUTHORIZED','errors':errors,'notes':notes,
         'scope':'No target was contacted. Cross-root uniqueness, IPAM authority, project scope, images, policy and qualification must be independently verified.'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('root_config',type=Path);p.add_argument('inputs',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 try:report=review_inputs(load_json(a.root_config),load_json(a.inputs))
 except (ValueError,TypeError,KeyError,OSError):print('{"status":"INVALID_INPUT"}');return 4
 text=json.dumps(report,indent=2)+'\n'
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
 else:print(text,end='')
 return 2 if report['errors'] else 0
if __name__=='__main__':raise SystemExit(main())
