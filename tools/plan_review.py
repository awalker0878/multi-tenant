#!/usr/bin/env python3
"""Read-only review of a Terraform show -json plan for restricted quarantine and exact-route preparation.

This is not a general policy engine, signature verifier, authorization system or
native-state discovery tool. Output never includes before/after data or secret
values. It blocks known violations and treats unknown security-sensitive fields,
updates, imports and unbound references as requiring an independent review.
"""
from __future__ import annotations
import argparse
import hashlib
import ipaddress
import json
import re
from pathlib import Path
from typing import Any
try:
    from tools.route_audit import load_json
except ModuleNotFoundError:
    from route_audit import load_json

class PlanError(ValueError):pass

SCALAR_RULES={
 'nutanix_routes_v2':{'route_type':'STATIC'},
 'nsxt_policy_gateway_policy':{'category':'Emergency','stateful':True,'tcp_strict':True},
 'nutanix_vpc_v2':{'vpc_type':'REGULAR'},
 'nutanix_subnet_v2':{'subnet_type':'OVERLAY','is_external':False},
 'nutanix_network_security_policy_v2':{'type':'APPLICATION','state':'ENFORCE','scope':'VPC_LIST','is_hitlog_enabled':True,'is_ipv6_traffic_allowed':False},
 'nutanix_virtual_machine_v2':{'power_state':'OFF'},
 'nsxt_policy_tier1_gateway':{'ha_mode':'NONE'},
 'nsxt_policy_security_policy':{'category':'Emergency','stateful':True},
 'openstack_networking_network_v2':{'admin_state_up':False,'shared':False,'external':False,'port_security_enabled':True},
 'openstack_networking_subnet_v2':{'enable_dhcp':False,'ip_version':4},
 'openstack_networking_router_v2':{'admin_state_up':False},
 'openstack_networking_secgroup_v2':{'delete_default_rules':True},
 'openstack_networking_port_v2':{'admin_state_up':False,'port_security_enabled':True},
 'openstack_compute_instance_v2':{'power_state':'shutoff'},
}
EMPTY_RULES={
 'nutanix_vpc_v2':('external_subnets','externally_routable_prefixes'),
 'nsxt_policy_tier1_gateway':('tier0_path','route_advertisement_types','route_advertisement_rule'),
 'nsxt_policy_segment':('bridge_config','vlan_ids','l2_extension','metadata_proxy_paths'),
 'openstack_networking_router_v2':('external_network_id','external_fixed_ip'),
 'openstack_networking_subnet_v2':('host_routes',),
 'openstack_networking_port_v2':('allowed_address_pairs',),
 'nutanix_virtual_machine_v2':('guest_customization','gpus'),
 'vsphere_virtual_machine':('pci_device_id',),
}
ALLOWED=set(SCALAR_RULES)|{'nsxt_policy_static_route','openstack_networking_router_route_v2','nutanix_category_v2','nsxt_policy_segment','nsxt_policy_group','openstack_networking_router_interface_v2','openstack_blockstorage_volume_v3','openstack_compute_volume_attach_v2','vsphere_virtual_machine'}
PREFIX_PROVIDER={'nutanix_':'registry.terraform.io/nutanix/nutanix','nsxt_':'registry.terraform.io/vmware/nsxt','openstack_':'registry.terraform.io/terraform-provider-openstack/openstack','vsphere_':'registry.terraform.io/hashicorp/vsphere'}
REF_FIELDS={'tenant_id','network_id','subnet_id','security_group_ids','resource_pool_id','datastore_id','storage_policy_id','flavor_id','volume_type','transport_zone_path','gateway_path','router_id','route_table_ext_id','vpc_reference'}
SAFE_ADDRESS=re.compile(r'^[A-Za-z0-9_.\[\]"-]{1,240}$')

def has_true(value:Any)->bool:
    if value is True:return True
    if isinstance(value,dict):return any(has_true(x) for x in value.values())
    if isinstance(value,list):return any(has_true(x) for x in value)
    return False

def walk(value:Any,path:tuple=()):
    if isinstance(value,dict):
        for k,v in value.items():
            yield path+(k,),v
            yield from walk(v,path+(k,))
    elif isinstance(value,list):
        for i,v in enumerate(value):yield from walk(v,path+(i,))

def empty(value:Any)->bool:return value is None or value=='' or value==[] or value=={}


def review(plan:dict[str,Any], approved_references:dict[str,list[Any]]|None=None)->dict[str,Any]:
    if not isinstance(plan,dict):raise PlanError('Expected a JSON object.')
    if not re.fullmatch(r'1\.[0-9]+',str(plan.get('format_version',''))):raise PlanError('Unsupported or missing plan format_version.')
    changes=plan.get('resource_changes')
    if not isinstance(changes,list):raise PlanError('Expected a saved plan with resource_changes, not a state snapshot.')
    bindings=approved_references or {}
    if not isinstance(bindings,dict) or any(not isinstance(v,list) for v in bindings.values()):raise PlanError('Approved reference input must map field names to lists.')
    findings=[];seen=set();managed=0
    def finding(level:str,code:str,address:str='plan',field:str=''):
        # Never echo attribute values, expressions, provider credentials or plan metadata.
        safe=address if SAFE_ADDRESS.fullmatch(address) else 'REDACTED_RESOURCE_ADDRESS'
        findings.append({'severity':level,'code':code,'resource':safe,'field':field})
    if plan.get('errored') is True:finding('BLOCK','PLAN_ERRORED')
    if plan.get('complete') is False or plan.get('deferred_changes'):finding('REVIEW','PLAN_INCOMPLETE')
    if plan.get('resource_drift'):finding('REVIEW','DRIFT_PRESENT')
    for path,value in walk(plan.get('configuration',{})):
        if path[-1] in {'provisioner','provisioners'} and value:finding('BLOCK','UNMANAGED_PROVISIONER')
    for check in plan.get('checks',[]):
        if not isinstance(check,dict):raise PlanError('Malformed check status.')
        if check.get('status') in {'fail','error'}:finding('BLOCK','TERRAFORM_CHECK_FAILED')
        elif check.get('status') not in {'pass'}:finding('REVIEW','TERRAFORM_CHECK_UNKNOWN')
    for item in changes:
        if not isinstance(item,dict):raise PlanError('Malformed resource change.')
        address=item.get('address');kind=item.get('type');change=item.get('change')
        if not isinstance(address,str) or not isinstance(kind,str) or not isinstance(change,dict):raise PlanError('Resource identity/change is missing.')
        key=(address,item.get('deposed'))
        if key in seen:raise PlanError('Duplicate resource/deposed identity.')
        seen.add(key)
        mode=item.get('mode')
        if mode!='managed':
            finding('REVIEW','NON_MANAGED_READ_OUTSIDE_DELIVERED_MODULES',address);continue
        managed+=1
        actions=change.get('actions')
        if not isinstance(actions,list) or not actions or any(not isinstance(a,str) for a in actions):raise PlanError('Invalid action list.')
        if 'delete' in actions:
            finding('BLOCK','DELETE_OR_REPLACEMENT',address);continue
        if actions not in (['create'],['update'],['no-op']):finding('BLOCK','UNSUPPORTED_ACTION',address);continue
        if kind not in ALLOWED:finding('BLOCK','RESOURCE_TYPE_OUTSIDE_INCREMENT',address);continue
        expected_provider=next((v for k,v in PREFIX_PROVIDER.items() if kind.startswith(k)),None)
        if item.get('provider_name')!=expected_provider:finding('BLOCK','UNEXPECTED_PROVIDER_SOURCE',address)
        if actions==['update']:finding('REVIEW','UPDATE_REQUIRES_CHANGE_AND_DATA_REVIEW',address)
        if item.get('previous_address') or change.get('importing') or item.get('deposed'):finding('REVIEW','OWNERSHIP_ADOPTION_OR_DEPOSED_OBJECT',address)
        after=change.get('after');unknown=change.get('after_unknown',{})
        if not isinstance(after,dict) or not isinstance(unknown,(dict,bool)):raise PlanError('Malformed planned resource values.')
        if unknown is True:
            finding('REVIEW','WHOLE_RESOURCE_UNKNOWN',address);continue
        if unknown is False:unknown={}
        def scalar(field,expected):
            if has_true(unknown.get(field)):finding('REVIEW','SECURITY_FIELD_UNKNOWN',address,field)
            elif field not in after:finding('REVIEW','SECURITY_FIELD_MISSING',address,field)
            elif type(after[field]) is not type(expected) or after[field]!=expected:finding('BLOCK','QUARANTINE_VALUE_CHANGED',address,field)
        for field,value in SCALAR_RULES.get(kind,{}).items():scalar(field,value)
        for field in EMPTY_RULES.get(kind,()):
            if has_true(unknown.get(field)):finding('REVIEW','FORBIDDEN_PATH_FIELD_UNKNOWN',address,field)
            elif not empty(after.get(field)):finding('BLOCK','UNEXPECTED_CONNECTIVITY_OR_DEVICE',address,field)
        # Conservatively require review of all non-identity unknown values, including nested collections.
        for field,value in unknown.items():
            if field not in {'id','ext_id','path','revision','created_at','updated_at','created_time','update_time','create_time','all_tags','all_metadata','status'} and has_true(value):
                finding('REVIEW','NONIDENTITY_VALUE_UNKNOWN',address,field)
        for field in REF_FIELDS & set(after):
            value=after[field]
            if empty(value):continue
            values=value if isinstance(value,list) else [value]
            if field not in bindings:finding('REVIEW','REFERENCE_NOT_BOUND_TO_ACCEPTED_INVENTORY',address,field)
            elif any(x not in bindings[field] for x in values):finding('BLOCK','REFERENCE_OUTSIDE_ACCEPTED_INVENTORY',address,field)
        if kind in {'nutanix_routes_v2','nsxt_policy_static_route','openstack_networking_router_route_v2'}:
            finding('REVIEW','EXACT_ROUTE_ENGINEERING_AND_NATIVE_ATTACHMENT_REQUIRED',address)
            destination=None
            if kind=='nutanix_routes_v2':
                try:
                    family=after['destination'][0]['ipv4'][0]
                    destination=f"{family['ip'][0]['value']}/{family['prefix_length']}"
                    hops=after['next_hop']
                    if len(hops)!=1 or hops[0]['next_hop_type']!='EXTERNAL_SUBNET':
                        finding('BLOCK','NUTANIX_ROUTE_NEXT_HOP_TYPE_CHANGED',address)
                    elif hops[0].get('next_hop_reference') not in bindings.get('external_subnet_id',[]):
                        finding('REVIEW','EXTERNAL_SUBNET_NOT_BOUND_TO_ACCEPTED_ATTACHMENT',address)
                except (KeyError,IndexError,TypeError):
                    finding('REVIEW','ROUTE_DESTINATION_OR_NEXT_HOP_UNRESOLVED',address)
            else:
                destination=after.get('network' if kind=='nsxt_policy_static_route' else 'destination_cidr')
                if kind=='nsxt_policy_static_route':
                    hops=after.get('next_hop')
                    hop=hops[0].get('ip_address') if isinstance(hops,list) and len(hops)==1 and isinstance(hops[0],dict) else None
                else:hop=after.get('next_hop')
                try:
                    if ipaddress.ip_address(hop).version!=4:raise ValueError()
                except (ValueError,TypeError):finding('BLOCK','ROUTE_NEXT_HOP_INVALID',address)
            try:
                network=ipaddress.ip_network(destination,strict=True)
                if network.version!=4 or network.prefixlen==0:
                    finding('BLOCK','DEFAULT_OR_UNSUPPORTED_ROUTE',address)
            except (ValueError,TypeError):finding('REVIEW','ROUTE_DESTINATION_UNRESOLVED',address)
        if kind=='nsxt_policy_gateway_policy':
            rules=after.get('rule')
            if not isinstance(rules,list) or len(rules)!=1:
                finding('BLOCK','GATEWAY_QUARANTINE_RULE_SET_CHANGED',address)
            else:
                rule=rules[0]
                if not isinstance(rule,dict):raise PlanError('Malformed gateway rule.')
                scope=rule.get('scope')
                if not isinstance(scope,list) or len(scope)!=1 or not scope[0] or scope[0]=='ANY':
                    finding('BLOCK','GATEWAY_POLICY_SCOPE_NOT_BOUNDED',address)
                elif scope[0] not in bindings.get('gateway_path',[]):
                    finding('REVIEW','GATEWAY_NOT_BOUND_TO_ACCEPTED_SCOPE',address)
                if rule.get('action')!='DROP' or rule.get('logged') is not True or rule.get('disabled') is not False or rule.get('direction')!='IN_OUT' or rule.get('ip_version')!='IPV4_IPV6':
                    finding('BLOCK','GATEWAY_QUARANTINE_RULE_CHANGED',address)
                if any(not empty(rule.get(key)) for key in ('source_groups','destination_groups','services','service_entries')):
                    finding('BLOCK','GATEWAY_DROP_NARROWED',address)
            finding('REVIEW','ACTUAL_GATEWAY_FIREWALL_PATH_PRECEDENCE_REQUIRED',address)
        if kind=='nsxt_policy_segment':
            blocks=after.get('advanced_config')
            if not isinstance(blocks,list) or len(blocks)!=1:finding('REVIEW','SEGMENT_CONNECTIVITY_UNRESOLVED',address)
            elif not isinstance(blocks[0],dict):raise PlanError('Malformed NSX advanced configuration.')
            elif blocks[0].get('connectivity')!='OFF' or blocks[0].get('urpf_mode')!='STRICT':finding('BLOCK','SEGMENT_QUARANTINE_CHANGED',address)
        if kind=='nsxt_policy_security_policy':
            scope=after.get('scope');rules=after.get('rule')
            if not isinstance(scope,list) or len(scope)!=1 or not scope[0] or scope[0]=='ANY':finding('BLOCK','POLICY_SCOPE_NOT_BOUNDED',address)
            if not isinstance(rules,list) or not rules:finding('REVIEW','DROP_RULE_UNRESOLVED',address)
            else:
                for rule in rules:
                    if not isinstance(rule,dict):raise PlanError('Malformed NSX rule.')
                    if rule.get('action')!='DROP' or rule.get('logged') is not True or rule.get('disabled') is not False or rule.get('direction')!='IN_OUT' or rule.get('ip_version')!='IPV4_IPV6':finding('BLOCK','NSX_QUARANTINE_RULE_CHANGED',address)
                    if not empty(rule.get('source_groups')) or not empty(rule.get('destination_groups')) or not empty(rule.get('services')) or not empty(rule.get('service_entries')):finding('BLOCK','DROP_RULE_NARROWED',address)
            finding('REVIEW','NATIVE_DFW_PRECEDENCE_AND_EXCLUSIONS_NOT_OBSERVED',address)
        if kind=='nutanix_network_security_policy_v2':
            refs=after.get('vpc_reference')
            if not isinstance(refs,list) or len(refs)!=1 or not refs[0]:finding('REVIEW','VPC_POLICY_SCOPE_UNRESOLVED',address)
            rules=after.get('rules')
            if not isinstance(rules,list) or len(rules)!=2:finding('REVIEW','NUTANIX_RULE_SET_UNRESOLVED',address)
            else:
                ruletypes={}
                for rule in rules:
                    if not isinstance(rule,dict):raise PlanError('Malformed Nutanix rule.')
                    ruletypes[rule.get('type')]=rule
                if set(ruletypes)!={'APPLICATION','INTRA_GROUP'}:finding('BLOCK','NUTANIX_RULE_TYPES_CHANGED',address)
                for path,value in walk(rules):
                    if path[-1] in {'src_allow_spec','dest_allow_spec'} and value!='NONE':finding('BLOCK','NUTANIX_ALLOW_ENABLED',address,str(path[-1]))
                    if path[-1]=='secured_group_action' and value!='DENY':finding('BLOCK','NUTANIX_INTRAGROUP_ALLOW',address)
                    if path[-1] in {'src_category_references','dest_category_references','src_subnet','dest_subnet','service_group_references','src_address_group_references','dest_address_group_references','tcp_services','udp_services','icmp_services','secured_group_service_references'} and not empty(value):finding('BLOCK','NUTANIX_QUARANTINE_RULE_EXPANDED',address,str(path[-1]))
            finding('REVIEW','NATIVE_CATEGORY_AUTHORITY_AND_EFFECTIVE_POLICY_NOT_OBSERVED',address)
        if kind=='nutanix_virtual_machine_v2':
            nics=after.get('nics')
            if not isinstance(nics,list) or len(nics)!=1:finding('REVIEW','NIC_SET_UNRESOLVED',address)
            else:
                connected=[value for path,value in walk(nics) if path[-1]=='is_connected']
                if connected!=[False]:finding('BLOCK','NIC_NOT_EXPLICITLY_DISCONNECTED',address)
            finding('REVIEW','ACTUAL_CLUSTER_IMAGE_STORAGE_AND_POLICY_HANDOFF_REQUIRED',address)
        if kind=='openstack_networking_port_v2':
            groups=after.get('security_group_ids')
            if not isinstance(groups,list) or len(groups)!=1 or not groups[0]:finding('REVIEW','QUARANTINE_GROUP_UNRESOLVED',address)
            if after.get('no_security_groups') is True:finding('BLOCK','SECURITY_GROUPS_DISABLED',address)
        if kind=='openstack_compute_instance_v2':
            blocks=after.get('block_device')
            if not isinstance(blocks,list) or len(blocks)!=1:finding('REVIEW','BOOT_ATTACHMENT_UNRESOLVED',address)
            elif not isinstance(blocks[0],dict):raise PlanError('Malformed boot-device configuration.')
            elif blocks[0].get('delete_on_termination') is not False:finding('BLOCK','BOOT_DATA_DELETION_ENABLED',address)
            finding('REVIEW','INITIAL_BOOT_POSSIBLE_VERIFY_PORT_AND_PROJECT_SCOPE',address)
        if kind=='vsphere_virtual_machine':
            finding('REVIEW','VMWARE_MAY_POWER_ON_VERIFY_ACCEPTED_NETWORK_AND_TEMPLATE',address)
            nics=after.get('network_interface')
            if not isinstance(nics,list) or len(nics)!=1:finding('REVIEW','VMWARE_NIC_MAPPING_UNRESOLVED',address)
            else:
                if not isinstance(nics[0],dict):raise PlanError('Malformed vSphere NIC configuration.')
                net=nics[0].get('network_id')
                if net not in bindings.get('network_id',[]):finding('BLOCK','VMWARE_NETWORK_NOT_IN_ACCEPTED_MAPPING',address)
            disks=after.get('disk',[])
            if not isinstance(disks,list):raise PlanError('Malformed vSphere disk list.')
            for disk in disks:
                if not isinstance(disk,dict) or disk.get('keep_on_remove') is not True:finding('BLOCK','VMWARE_DISK_RETENTION_CHANGED',address)
        # Check dangerous actual values anywhere in planned nested resources.
        for path,value in walk(after):
            field=path[-1]
            if field in {'user_data','admin_pass','customization_spec'} and not empty(value):finding('REVIEW','SECRET_OR_CUSTOMIZATION_SURFACE_REQUIRES_REVIEW',address,str(field))
    if managed==0:finding('REVIEW','EMPTY_PLAN_IS_NOT_A_DEPLOYMENT')
    level='BLOCKED' if any(x['severity']=='BLOCK' for x in findings) else 'REVIEW_REQUIRED' if findings else 'NO_STATIC_VIOLATIONS'
    return {'status':level,'managed_resources':managed,'findings':findings,'authorization':'NOT_EVALUATED','live_qualification':'NOT_RUN',
            'limitations':['No signature or approval validation','No current device/API state','No actual policy precedence or packet testing','No Terraform/provider schema validation']}


def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('--approved-references',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:
        refs=load_json(a.approved_references) if a.approved_references else None
        result=review(load_json(a.plan),refs);result['plan_sha256']=hashlib.sha256(a.plan.read_bytes()).hexdigest()
    except (PlanError,ValueError,TypeError,KeyError,OSError) as e:
        # Structural exception descriptions never contain planned attribute values.
        print(json.dumps({'status':'INVALID_INPUT','reason':type(e).__name__}));return 4
    text=json.dumps(result,indent=2)+'\n'
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
    else:print(text,end='')
    return {'NO_STATIC_VIOLATIONS':0,'BLOCKED':2,'REVIEW_REQUIRED':3}[result['status']]
if __name__=='__main__':raise SystemExit(main())
