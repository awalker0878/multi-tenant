#!/usr/bin/env python3
"""Use delegated incident authority to withdraw only an owned edge boundary."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if __package__ in (None,''): sys.path.insert(0,str(ROOT))
from tools import nft_edge as edge, readback_core as c
from tools.run_files import (current_window,digest,encoded,load_private,new_directory,
                             private_path,read_private,require,write_new)


def observed_withdrawal(spec,state):
    table,scope_hash=edge.validate(spec)
    state=edge.normalized(state); c.exact_keys(state,{'nftables'})
    require(isinstance(state['nftables'],list),'Complete native firewall observation required')
    tables=[]; chains=[]; rules=[]
    for item in state['nftables']:
        require(isinstance(item,dict) and len(item)==1 and next(iter(item)) in {'table','chain','rule'},'Unexpected object in contained edge table')
        kind=next(iter(item)); {'table':tables,'chain':chains,'rule':rules}[kind].append(item[kind])
    require(len(tables)==len(chains)==1,'Exactly one owned table and forwarding chain required')
    c.exact_keys(tables[0],{'family','name','comment'},{'flags'})
    require(tables[0]['family']=='inet' and tables[0]['name']==table and not tables[0].get('flags')
            and tables[0]['comment'].startswith('hosting:'+scope_hash+':') and tables[0]['comment'].endswith(':withdraw'),
            'Owned edge withdrawal table is absent or dormant')
    require(chains[0]==dict(family='inet',table=table,name='forward',type='filter',hook='forward',prio=-100,policy='accept'),
            'Unexpected contained forwarding hook')
    expected={(interface,direction) for interface in spec['owned_interfaces'] for direction in ('iifname','oifname')}
    dropped=set(); logged=set()
    for rule in rules:
        c.exact_keys(rule,{'family','table','chain','expr'})
        require(rule['family']=='inet' and rule['table']==table and rule['chain']=='forward','Foreign containment rule')
        expr=rule['expr']; require(isinstance(expr,list) and len(expr)==3,'Unexpected containment expression')
        c.exact_keys(expr[0],{'match'}); match=expr[0]['match']; c.exact_keys(match,{'op','left','right'})
        require(match['op']=='==' and isinstance(match['right'],str),'Exact interface selector required')
        c.exact_keys(match['left'],{'meta'}); c.exact_keys(match['left']['meta'],{'key'})
        selector=(match['right'],match['left']['meta']['key']); require(selector in expected,'Foreign interface in containment rule')
        if expr[1:]==[{'counter':{}},{'drop':None}]:
            require(selector not in dropped,'Duplicate containment drop'); dropped.add(selector)
        else:
            c.exact_keys(expr[1],{'limit'}); c.exact_keys(expr[2],{'log'})
            limit=expr[1]['limit']; c.exact_keys(limit,{'rate','per'},{'burst','inv','rate_unit','burst_unit'})
            require(limit['rate']==10 and limit['per']=='second' and limit.get('inv',False) is False,'Unexpected logging rate')
            require(expr[2]['log']=={'prefix':table[:28]+' '} and selector not in logged,'Unexpected containment logging')
            logged.add(selector)
    require(dropped==logged==expected and len(rules)==len(expected)*2,'Every owned interface requires both-direction logged drops')
    return digest(encoded(state))


def authorize(spec,authority):
    edge.validate(spec)
    c.exact_keys(authority,{'format','spec_sha256','incident_id','valid_from','valid_until','change_ref','boundary_acceptance_ref'})
    require(authority['format']=='hosting-edge-containment-authority/1' and authority['spec_sha256']==digest(encoded(spec)),
            'Containment authority differs from the exact owned boundary')
    c.identifier(authority['incident_id'])
    for key in ('change_ref','boundary_acceptance_ref'): c.text(authority[key])
    current_window(authority)


def contain(spec,authority,kernel,ledger,operation):
    table,scope_hash=edge.validate(spec); authorize(spec,authority)
    selected=dict(spec,operation_id='contain-'+c.digest(authority['incident_id'])[:32])
    # One incident has one immutable withdrawal attempt even after a lost reply.
    identity=digest(encoded([selected['operation_id'],selected['generation'],'withdraw']))
    native_ledger=private_path(ledger,directory=True)/scope_hash
    current,state_hash=kernel.inspect(selected)
    already=(native_ledger/(identity+'.started.json')).exists()
    if already:
        prior=load_private(native_ledger/(identity+'.started.json'))
        require(prior['spec_sha256']==digest(encoded(selected)) and prior['mode']=='withdraw',
                'Incident identity belongs to another withdrawal specification')
        # This observation cannot clear an uncertain owner head or replay a write.
        observed_withdrawal(selected,current)
    else:
        delegated=dict(spec_sha256=digest(encoded(selected)),mode='withdraw',expected_state_sha256=state_hash,
            valid_from=authority['valid_from'],valid_until=authority['valid_until'],change_ref=authority['change_ref'],
            boundary_acceptance_ref=authority['boundary_acceptance_ref'],readiness_ref='INCIDENT-CONTAINMENT-ONLY')
        edge.apply(selected,'withdraw',delegated,kernel,ledger,operation)
        current,_=kernel.inspect(selected)
    observed=observed_withdrawal(selected,current); current_window(authority)
    result=dict(format='hosting-edge-containment-receipt/1',status='CONTAINED_OBSERVED_NOT_QUALIFIED',
        scope=spec['scope'],spec_sha256=digest(encoded(spec)),authority_sha256=digest(encoded(authority)),
        incident_id=authority['incident_id'],observed_state_sha256=observed,observed_at=c.now(),
        write_attempted=not already,native_acceptance=False,production_activation=False)
    write_new(Path(operation)/'containment.json',encoded(result))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('spec','authority','nft','ledger','output'): parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--execute',action='store_true'); args=parser.parse_args()
    try:
        require(args.execute,'Explicit delegated incident containment required')
        spec=load_private(args.spec); edge.validate(spec)
        require(Path('/etc/machine-id').read_text().strip()==spec['machine_id'] and os.stat('/proc/self/ns/net').st_ino==spec['network_namespace_inode'],
                'Wrong native edge machine or namespace')
        require(digest(args.nft.read_bytes())==spec['nft_sha256'],'Native firewall executable changed')
        operation=new_directory(args.output,ROOT)
        result=contain(spec,load_private(args.authority),edge.Kernel(args.nft.resolve(strict=True),operation),args.ledger,operation)
        print(json.dumps({'status':result['status'],'write_attempted':result['write_attempted']})); return 0
    except (ValueError,OSError,KeyError,TypeError):
        print('{"status":"CONTAINMENT_UNCONFIRMED","reason":"Preserve native holds; inspect the private incident evidence"}'); return 2


if __name__=='__main__': raise SystemExit(main())
