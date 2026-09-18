#!/usr/bin/env python3
"""Compare an exact native route input to an independently controlled route record.

Read-only structural/time/scope check; does not validate signer authority, query IPAM,
contact a platform, reserve an address or authorize apply. Scope is Increment02 routes.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import ipaddress
import json
from pathlib import Path
try:
 from tools.neutron_observe import strict_loads,digest
 from tools.input_review import PLACEHOLDER
except ModuleNotFoundError:
 from neutron_observe import strict_loads,digest
 from input_review import PLACEHOLDER

FIELDS={
 'nsx-route':{'gateway_path','next_hop_address'},
 'openstack-route':{'router_id','next_hop_address'},
 'nutanix-route':{'route_table_id','vpc_id','external_subnet_id'},
}
COMMON={'tenant_key','domain_key','route_key','destination_cidr','engineering_record_ref','attachment_acceptance_ref'}
DOC_NETS=[ipaddress.ip_network(n) for n in ('192.0.2.0/24','198.51.100.0/24','203.0.113.0/24')]


def review(module:str,inputs:dict,record:dict,now:datetime|None=None)->dict:
 if module not in FIELDS:raise ValueError('Unsupported route module')
 if not isinstance(inputs,dict) or not isinstance(record,dict):raise ValueError('Objects required')
 required=COMMON|FIELDS[module]
 findings=[]
 def issue(code,field):findings.append({'code':code,'field':field})
 if inputs.get('allow_restricted_build') is not True:issue('RESTRICTED_BUILD_NOT_OPTED_IN','allow_restricted_build')
 if not inputs.get('test_authorization_ref'):issue('MISSING_TEST_RECORD','test_authorization_ref')
 for key in required:
  value=inputs.get(key)
  if not isinstance(value,str) or not value.strip() or PLACEHOLDER.search(value):issue('MISSING_OR_PLACEHOLDER',key)
 accepted=record.get('route')
 if not isinstance(accepted,dict) or set(accepted)!=required:issue('INCOMPLETE_OR_EXTRA_RECORD_FIELDS','route')
 else:
  for key in required:
   if inputs.get(key)!=accepted[key]:issue('RECORD_MISMATCH',key)
 if record.get('module')!=module:issue('TARGET_MODULE_MISMATCH','module')
 try:
  until=datetime.fromisoformat(record['valid_until'].replace('Z','+00:00'))
  effective=datetime.fromisoformat(record['valid_from'].replace('Z','+00:00'))
  current=now or datetime.now(timezone.utc)
  if until.tzinfo is None or effective.tzinfo is None or not effective<=current<until:issue('RECORD_NOT_CURRENT','validity')
 except (ValueError,KeyError,TypeError):issue('INVALID_RECORD_TIME','validity')
 try:
  network=ipaddress.ip_network(inputs['destination_cidr'],strict=True)
  if network.version!=4 or network.prefixlen==0:issue('UNSUPPORTED_FAMILY_OR_DEFAULT','destination_cidr')
  if network.version==4 and any(network.overlaps(n) for n in DOC_NETS):issue('DOCUMENTATION_ADDRESS_NOT_SITE_ALLOCATION','destination_cidr')
  if network.network_address.is_loopback or network.network_address.is_multicast or network.network_address.is_link_local:issue('UNUSABLE_ROUTE','destination_cidr')
 except (ValueError,KeyError,TypeError):issue('INVALID_ROUTE_PREFIX','destination_cidr')
 if 'next_hop_address' in FIELDS[module]:
  try:
   hop=ipaddress.ip_address(inputs['next_hop_address']);attachment=ipaddress.ip_network(record['attachment_cidr'],strict=True)
   if hop.version!=4 or attachment.version!=4 or hop not in attachment:issue('NEXT_HOP_NOT_ON_ACCEPTED_ATTACHMENT','next_hop_address')
   if attachment.prefixlen<31 and hop in (attachment.network_address,attachment.broadcast_address):issue('NON_HOST_NEXT_HOP','next_hop_address')
   if any(hop in n for n in DOC_NETS) or hop.is_loopback or hop.is_multicast or hop.is_unspecified or hop.is_link_local:issue('UNUSABLE_OR_EXAMPLE_NEXT_HOP','next_hop_address')
  except (ValueError,TypeError,KeyError):issue('INVALID_ATTACHMENT_OR_NEXT_HOP','next_hop_address')
 else:
  if record.get('external_subnet_attached_to_vpc') is not True:issue('ATTACHMENT_NOT_RECORDED','external_subnet_id')
 return {'kind':'EXACT_ROUTE_RECORD_REVIEW','status':'BLOCKED' if findings else 'RECORD_MATCH_NOT_AUTHORIZED',
         'record_sha256':digest(record),'findings':findings,
         'limitations':['Record provenance and signer authority not verified','No actual next-hop reachability or IPAM verification',
                        'No interference check against other native route owners','No apply or activation']}


def main()->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('module',choices=FIELDS);p.add_argument('inputs',type=Path);p.add_argument('record',type=Path);p.add_argument('--output',type=Path)
 a=p.parse_args()
 try:r=review(a.module,strict_loads(a.inputs.read_bytes()),strict_loads(a.record.read_bytes()))
 except (ValueError,OSError):print('{"status":"INVALID_INPUT"}');return 4
 text=json.dumps(r,indent=2)+'\n'
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
 else:print(text,end='')
 return 2 if r['findings'] else 0
if __name__=='__main__':raise SystemExit(main())
