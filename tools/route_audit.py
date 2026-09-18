#!/usr/bin/env python3
"""Offline engineering checks for an explicit routed topology.

Reads a versioned file, never connects to infrastructure or allocates addresses.
Models directly connected next hops and longest-prefix routing only. It deliberately
rejects ambiguous equal-prefix forwarding, recursive next hops and default routes
on routers. NAT, ECMP, PBR, native implicit rules, ARP/ND security and actual stateful
firewall implementation are not simulated. A passing result concerns this model only.
"""
from __future__ import annotations
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
from typing import Any

class ModelError(ValueError):
    """Invalid or unsupported routing model."""

DOC_NETS=tuple(ipaddress.ip_network(s) for s in ('192.0.2.0/24','198.51.100.0/24','203.0.113.0/24','2001:db8::/32'))
KINDS={'native','edge','service_edge','workload','service'}


def load_json(path: Path, max_bytes: int=10_000_000) -> Any:
    if path.stat().st_size>max_bytes: raise ModelError('Input exceeds supported size.')
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out: raise ModelError('Duplicate JSON property: '+k)
            out[k]=v
        return out
    def reject_constant(value):raise ModelError('Non-finite JSON number is unsupported.')
    return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=unique,parse_constant=reject_constant)

class Topology:
    def __init__(self, data: dict[str,Any]):
        if not isinstance(data,dict) or data.get('model_version')!=1: raise ModelError('Expected model_version 1 object.')
        self.data=data;self.nodes=data.get('nodes')
        if not isinstance(self.nodes,dict) or not self.nodes: raise ModelError('Nodes must be a nonempty object.')
        self.ips:dict[Any,tuple[str,str]]={};self.interfaces={};self.routes={};self.flows=data.get('approved_flows')
        if not isinstance(self.flows,list) or not self.flows: raise ModelError('Expected nonempty approved_flows.')
        segments={};net_segments={}
        for name,node in self.nodes.items():
            if not isinstance(name,str) or not isinstance(node,dict) or node.get('kind') not in KINDS: raise ModelError('Invalid node identity or kind.')
            if node['kind'] in {'native','edge','service_edge','workload'} and not isinstance(node.get('tenant'),str): raise ModelError('Tenant owner is missing: '+name)
            ints=node.get('interfaces');rt=node.get('routes')
            if not isinstance(ints,list) or not ints or not isinstance(rt,list):raise ModelError('Invalid interfaces/routes: '+name)
            self.interfaces[name]=[];self.routes[name]=[]
            ownnets=set()
            for entry in ints:
                if not isinstance(entry,dict) or set(entry)!={'segment','address'}:raise ModelError('Invalid interface fields: '+name)
                segment=entry['segment']
                if not isinstance(segment,str) or not segment:raise ModelError('Empty segment: '+name)
                try:intf=ipaddress.ip_interface(entry['address'])
                except (ValueError,TypeError) as e:raise ModelError('Invalid interface address: '+name) from e
                if intf.ip in self.ips:raise ModelError('Duplicate interface address: '+str(intf.ip))
                if intf.version==4 and intf.network.prefixlen<31 and intf.ip in (intf.network.network_address,intf.network.broadcast_address):raise ModelError('Unusable IPv4 host: '+name)
                if (intf.version,intf.network) in ownnets:raise ModelError('Multiple interfaces in same prefix on one modeled node: '+name)
                ownnets.add((intf.version,intf.network))
                key=(segment,intf.version)
                if key in segments and segments[key]!=intf.network:raise ModelError('Segment prefix disagrees: '+segment)
                segments[key]=intf.network
                if (intf.version,intf.network) in net_segments and net_segments[(intf.version,intf.network)]!=segment:raise ModelError('Overlapping address authority between segments.')
                net_segments[(intf.version,intf.network)]=segment
                self.ips[intf.ip]=(name,segment);self.interfaces[name].append((segment,intf))
            destinations=set()
            for entry in rt:
                if not isinstance(entry,dict) or set(entry)!={'destination','next_hop'}:raise ModelError('Invalid route fields: '+name)
                try:dest=ipaddress.ip_network(entry['destination'],strict=True);hop=ipaddress.ip_address(entry['next_hop'])
                except (ValueError,TypeError) as e:raise ModelError('Invalid route: '+name) from e
                if dest.version!=hop.version:raise ModelError('Route address families disagree: '+name)
                if dest in destinations:raise ModelError('Ambiguous duplicate route: '+name+' '+str(dest))
                destinations.add(dest)
                if dest.prefixlen==0 and node['kind'] not in {'workload','service'}:raise ModelError('Router default is not part of this reference pattern: '+name)
                self.routes[name].append((dest,hop))
        nets=list(net_segments)
        for i,(fam,a) in enumerate(nets):
            for fam2,b in nets[i+1:]:
                if fam==fam2 and a!=b and a.overlaps(b):raise ModelError('Overlapping connected prefixes are unsupported in the unique-address model.')
        for name,routes in self.routes.items():
            for dest,hop in routes:
                if hop not in self.ips:raise ModelError('Next hop has no owned interface: '+str(hop))
                target,segment=self.ips[hop]
                if target==name:raise ModelError('Self-referential next hop: '+name)
                if not any(s==segment and intf.version==hop.version and hop in intf.network for s,intf in self.interfaces[name]):raise ModelError('Next hop not directly connected on same segment: '+name)
                if self.nodes[name]['kind']=='service' and self.nodes[target]['kind']!='service_edge':raise ModelError('Service return must terminate on an owned service edge: '+name)
        ids=set()
        for f in self.flows:
            if not isinstance(f,dict) or set(f)!={'id','source','destination','protocol','port','via','stateful'}:raise ModelError('Invalid flow fields.')
            if not isinstance(f['id'],str) or f['id'] in ids:raise ModelError('Duplicate/invalid flow ID.')
            ids.add(f['id'])
            if f['source'] not in self.nodes or f['destination'] not in self.nodes:raise ModelError('Unknown flow endpoint.')
            if f['protocol'] not in {'tcp','udp'} or type(f['port']) is not int or not 1<=f['port']<=65535 or f['stateful'] is not True:raise ModelError('Unsupported flow protocol, port or session model.')
            if not isinstance(f['via'],list) or not f['via'] or any(x not in self.nodes for x in f['via']):raise ModelError('Invalid flow path.')
            if self.nodes[f['source']]['kind']!='workload':raise ModelError('Reference fixture initiator must be a workload.')
            tenant=self.nodes[f['source']]['tenant']
            if self.nodes[f['destination']]['kind']=='workload' and self.nodes[f['destination']]['tenant']!=tenant:raise ModelError('Cross-tenant permission is not in this base fixture.')
            for x in f['via']:
                if self.nodes[x]['kind'] in {'native','edge','service_edge'} and self.nodes[x]['tenant']!=tenant:raise ModelError('Path crosses a foreign tenant context.')
            if not any(self.nodes[x]['kind']=='edge' for x in f['via']):raise ModelError('A required EC is missing from the modeled flow.')

    def endpoint_ip(self,name:str,family:int):
        values=[i.ip for _,i in self.interfaces[name] if i.version==family]
        if len(values)!=1:raise ModelError('Endpoint needs exactly one address in requested family: '+name)
        return values[0]

    def trace(self,source:str,destination:str,family:int)->dict[str,Any]:
        dst=self.endpoint_ip(destination,family);node=source;path=[]
        for _ in range(len(self.nodes)+1):
            if node in path:return {'outcome':'LOOP','path':path+[node]}
            path.append(node)
            if node==destination:return {'outcome':'REACHED','path':path}
            if node!=source and self.nodes[node]['kind'] in {'workload','service'}:return {'outcome':'ENDPOINT_TRANSIT_DENIED','path':path}
            choices=[]
            for segment,intf in self.interfaces[node]:
                if intf.version==family and dst in intf.network:choices.append((intf.network.prefixlen,0,None,segment))
            for prefix,hop in self.routes[node]:
                if prefix.version==family and dst in prefix:choices.append((prefix.prefixlen,1,hop,None))
            if not choices:return {'outcome':'NO_ROUTE','path':path}
            # Connected routes win equal-length preference in this deliberately restricted model.
            chosen=sorted(choices,key=lambda x:(-x[0],x[1]))[0]
            if chosen[2] is None:
                target=self.ips.get(dst)
                if not target or target[1]!=chosen[3]:return {'outcome':'UNRESOLVED_CONNECTED_TARGET','path':path}
                node=target[0]
            else:node=self.ips[chosen[2]][0]
        return {'outcome':'HOP_LIMIT','path':path}

    def session(self,source:str,dest:str,protocol:str,port:int,family:int)->dict[str,Any]:
        forward=self.trace(source,dest,family)
        match=next((f for f in self.flows if (f['source'],f['destination'],f['protocol'],f['port'])==(source,dest,protocol,port)),None)
        if match is None:return {'outcome':'MODEL_POLICY_DENY','forward':forward}
        reverse=self.trace(dest,source,family)
        expected=[source,*match['via'],dest]
        if forward['outcome']!='REACHED' or forward['path']!=expected:return {'outcome':'FORWARD_PATH_MISMATCH','forward':forward,'reverse':reverse}
        if reverse['outcome']!='REACHED' or reverse['path']!=list(reversed(expected)):return {'outcome':'RETURN_PATH_MISMATCH','forward':forward,'reverse':reverse}
        return {'outcome':'MODEL_PATH_AND_INTENT_MATCH','forward':forward,'reverse':reverse}

    def audit(self)->dict[str,Any]:
        checks=[]
        for flow in self.flows:
            for fam in (4,6):
                s=self.session(flow['source'],flow['destination'],flow['protocol'],flow['port'],fam)
                checks.append({'id':flow['id']+f'-ipv{fam}','passed':s['outcome']=='MODEL_PATH_AND_INTENT_MATCH',**s})
                reverse=self.session(flow['destination'],flow['source'],flow['protocol'],flow['port'],fam)
                checks.append({'id':flow['id']+f'-unsolicited-reverse-ipv{fam}','passed':reverse['outcome']=='MODEL_POLICY_DENY','outcome':reverse['outcome']})
        workloads=[n for n in self.nodes if self.nodes[n]['kind']=='workload']
        for a in workloads:
            for b in workloads:
                if self.nodes[a]['tenant']==self.nodes[b]['tenant']:continue
                for fam in (4,6):
                    path=self.trace(a,b,fam)
                    checks.append({'id':a+'-to-'+b+f'-ipv{fam}','passed':path['outcome']=='NO_ROUTE',**path})
        # Named service /32 and /128 routes may exist without a selected protocol permission.
        for a in workloads:
            for dest in ('time','logs','repository'):
                for fam in (4,6):
                    s=self.session(a,dest,'tcp',443,fam)
                    checks.append({'id':a+'-unselected-'+dest+f'-ipv{fam}','passed':s['outcome']=='MODEL_POLICY_DENY','outcome':s['outcome']})
        return {'status':'MODEL_CHECKS_ONLY','checks':checks,'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),
                'live_qualification':'NOT_RUN','policy_engine':'Abstract allow-list with reply semantics; not a vendor firewall evaluation.',
                'unresolved_profiles':self.data.get('unresolved_profiles',[])}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('model',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:
        model=Topology(load_json(a.model));report=model.audit();report['source_sha256']=hashlib.sha256(a.model.read_bytes()).hexdigest()
    except (ModelError,ValueError,OSError,KeyError,TypeError) as e:
        print(json.dumps({'status':'INVALID_MODEL','reason':str(e)}));return 2
    text=json.dumps(report,indent=2)+'\n'
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
    else:print(text,end='')
    return 1 if report['failed'] else 0
if __name__=='__main__':raise SystemExit(main())
