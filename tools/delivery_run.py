#!/usr/bin/env python3
"""Resume an exact delivery graph through registered owners and durable receipts."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''): sys.path.insert(0, str(ROOT))
from tools import execution_journal as journal, readback_core as c
from tools.check_release import verify
from tools.run_files import (current_window, digest, encoded, load_private, private_path,
                             read_private, require, sync_directory, write_new)


def validate(plan):
    from tools.delivery_steps import KINDS
    c.exact_keys(plan, {'format', 'source_commit', 'operation_id', 'generation', 'scope', 'steps'})
    require(plan['format'] == 'hosting-delivery/1' and isinstance(plan['source_commit'], str)
            and re.fullmatch(r'[0-9a-f]{40}', plan['source_commit']), 'Exact delivery source required')
    c.identifier(plan['operation_id'])
    require(type(plan['generation']) is int and plan['generation'] > 0, 'Positive delivery generation required')
    c.exact_keys(plan['scope'], {'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key'})
    for value in plan['scope'].values(): c.identifier(value)
    require(plan['scope']['platform'] in {'nutanix', 'vmware', 'openstack'}, 'Unknown delivery platform')
    require(isinstance(plan['steps'], list) and 1 <= len(plan['steps']) <= 100, 'Bounded delivery graph required')
    seen = set()
    for step in plan['steps']:
        c.exact_keys(step, {'id', 'kind', 'needs'})
        c.identifier(step['id'])
        require(step['id'] not in seen and step['kind'] in KINDS, 'Duplicate or unsupported delivery step')
        require(isinstance(step['needs'], list) and len(step['needs']) == len(set(step['needs']))
                and set(step['needs']) <= seen, 'Delivery graph must be topologically ordered without missing dependencies')
        if seen: require(step['needs'], 'Every subsequent step must retain a dependency')
        seen.add(step['id'])


def safe_name(value):
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', value), 'Simple artifact filename required')
    return value


def packet(path, plan, step, receipts):
    value = load_private(path)
    c.exact_keys(value, {'format', 'plan_sha256', 'step_id', 'dependencies', 'parameters', 'files'})
    require(value['format'] == 'hosting-delivery-step/1' and value['plan_sha256'] == c.digest(plan)
            and value['step_id'] == step['id'], 'Stage packet belongs to another delivery')
    require(value['dependencies'] == {key: c.digest(receipts[key]) for key in step['needs']},
            'Stage packet does not bind all exact predecessor receipts')
    require(isinstance(value['parameters'], dict) and isinstance(value['files'], dict), 'Typed stage inputs required')
    for name, binding in value['files'].items():
        c.identifier(name)
        c.exact_keys(binding, {'path', 'sha256'})
        require(isinstance(binding['path'], str) and Path(binding['path']).is_absolute(), 'Absolute private stage file required')
        require(digest(read_private(binding['path'])) == binding['sha256'], 'Stage input bytes changed')
    return value


def artifact_receipt(directory, names):
    require(names and len(names) == len(set(names)), 'Exact stage artifact set required')
    return {safe_name(name): digest(read_private(directory / name)) for name in sorted(names)}


def gate_binding(original, renewed):
    c.exact_keys(renewed,set(original))
    require({k:v for k,v in renewed.items() if k not in {'valid_from','valid_until','acceptance_ref'}}==
            {k:v for k,v in original.items() if k not in {'valid_from','valid_until','acceptance_ref'}},
            'Renewed acceptance changed the original gate or dependency scope')
    c.text(renewed['acceptance_ref'])


def replay(log, plan):
    starts, receipts = {}, {}
    active=None; closed=False; renewals={}
    for event in log.events:
        data = event['data']
        if event['kind'] == 'DELIVERY_STARTED':
            c.exact_keys(data,{'plan'}); validate(data['plan'])
            require(data['plan']['scope']==plan['scope'], 'Foreign delivery journal scope')
            if active is not None:
                require(closed and data['plan']['generation']>active['generation'], 'Another delivery owns the held scope')
            active=data['plan']; closed=False; starts={}; receipts={}; renewals={}
        else:
            require(active is not None and not closed, 'Delivery start record is missing or already completed')
            if event['kind'] == 'STEP_STARTED':
                c.exact_keys(data, {'step_id', 'packet', 'packet_sha256'})
                step = next((s for s in active['steps'] if s['id'] == data['step_id']), None)
                require(step is not None and step['id'] not in starts and set(step['needs']) <= receipts.keys()
                        and c.digest(data['packet']) == data['packet_sha256'], 'Invalid delivery start ordering or binding')
                saved = data['packet']
                require(saved['plan_sha256'] == c.digest(active) and saved['step_id'] == step['id']
                        and saved['dependencies'] == {key:c.digest(receipts[key]) for key in step['needs']},
                        'Saved stage dependency binding differs')
                starts[step['id']] = data
            elif event['kind'] == 'STEP_COMPLETED':
                c.exact_keys(data, {'step_id', 'packet_sha256', 'status', 'artifacts', 'native_acceptance', 'production_activation'})
                identity = data['step_id']
                require(identity in starts and identity not in receipts
                        and data['packet_sha256'] == starts[identity]['packet_sha256']
                        and data['native_acceptance'] is False and data['production_activation'] is False,
                        'Invalid delivery completion binding')
                require(isinstance(data['status'], str) and isinstance(data['artifacts'], dict) and data['artifacts'],
                        'Incomplete delivery receipt')
                directory = log.directory / 'runs' / c.digest(active) / 'steps' / identity
                require(artifact_receipt(directory, list(data['artifacts'])) == data['artifacts'], 'Completed delivery evidence changed')
                receipts[identity] = data
            elif event['kind']=='GATE_RENEWED':
                c.exact_keys(data,{'step_id','receipt_sha256','acceptance'})
                identity=data['step_id']
                require(identity in receipts and any(s['id']==identity and s['kind']=='acceptance' for s in active['steps'])
                        and data['receipt_sha256']==c.digest(receipts[identity]),'Renewal does not bind a completed acceptance gate')
                original=load_private(log.directory/'runs'/c.digest(active)/'steps'/identity/'acceptance.json')
                gate_binding(original,data['acceptance']); current_window(data['acceptance'],c.timestamp(event['at']))
                renewals[identity]=data['acceptance']
            elif event['kind']=='DELIVERY_COMPLETED':
                require(set(receipts)=={s['id'] for s in active['steps']}
                        and data=={'plan_sha256':c.digest(active),'receipts':{k:c.digest(v) for k,v in receipts.items()}},
                        'Delivery closure does not cover every exact receipt')
                closed=True
            else:
                raise ValueError('Unknown delivery event')
    if active is not None and active!=plan:
        require(closed and plan['generation']>active['generation'], 'Another delivery owns the held scope')
        return {},{},True,False,{}
    return starts,receipts,active is None,closed,renewals


def run(plan, inbox, ledger, *, execute=False, root=ROOT):
    from tools.delivery_steps import dispatch, recover, validate_packet
    validate(plan)
    source = verify(root)
    require(source['status'] == 'HASHES_MATCH' and source['commit'] == plan['source_commit'], 'Exact clean delivery source required')
    inbox = private_path(inbox, directory=True)
    ledger=private_path(ledger,directory=True)
    require(not ledger.resolve().is_relative_to(root.resolve()) and not inbox.resolve().is_relative_to(root.resolve()),
            'Private delivery storage must be outside the source checkout')
    require(execute is True, 'Explicit delivery execution opt-in required')
    # Stable resource scope prevents a renamed workflow from evading uncertainty.
    with journal.locked(ledger, {'owner':'delivery', **plan['scope']}) as log:
        starts, receipts, new, closed, renewals = replay(log, plan)
        if new:
            log.append('DELIVERY_STARTED', {'plan':plan})
        base=log.directory/'runs'/c.digest(plan)
        for path in (log.directory/'runs',base,base/'steps'):
            if not path.exists(): path.mkdir(mode=0o700); sync_directory(path.parent)
            private_path(path, directory=True)
        for step in plan['steps']:
            identity = step['id']
            if identity in receipts: continue
            require(set(step['needs']) <= receipts.keys(), 'Incomplete delivery dependency')
            directory = base / 'steps' / identity
            # Gate records remain current through every dependent operation,
            # including a transitive handoff. Historical completion is no lease.
            ancestors=set(step['needs'])
            for predecessor in reversed(plan['steps']):
                if predecessor['id'] in ancestors: ancestors.update(predecessor['needs'])
            for predecessor in plan['steps']:
                if predecessor['id'] in ancestors and predecessor['kind']=='acceptance':
                    gate=predecessor['id']; original=load_private(base/'steps'/gate/'acceptance.json')
                    renewal=inbox/(gate+'.renewal.json')
                    if renewal.exists():
                        renewed=load_private(renewal); gate_binding(original,renewed); current_window(renewed)
                        if renewals.get(gate)!=renewed:
                            log.append('GATE_RENEWED',{'step_id':gate,'receipt_sha256':c.digest(receipts[gate]),'acceptance':renewed})
                            renewals[gate]=renewed
                    current_window(renewals.get(gate,original))
            if identity in starts:
                saved = starts[identity]['packet']
                recovery_authority=inbox/(identity+'.recovery-authority.json')
                result, names = recover(step, saved, directory, base, plan, root,
                                        recovery_authority=recovery_authority if recovery_authority.exists() else None)
            else:
                incoming = inbox / (identity + '.json')
                if not incoming.exists():
                    return dict(status='WAITING_STAGE_INPUTS', step_id=identity, plan_sha256=c.digest(plan),
                                dependencies={key:c.digest(receipts[key]) for key in step['needs']},
                                completed_steps=list(receipts), native_acceptance=False, production_activation=False)
                saved = packet(incoming, plan, step, receipts)
                source=verify(root)
                require(source['status']=='HASHES_MATCH' and source['commit']==plan['source_commit'],'Delivery source changed before execution')
                validate_packet(step, saved, plan, base)
                if directory.exists():
                    private_path(directory,directory=True)
                    require(set(p.name for p in directory.iterdir())<={'packet.json'},'Unrecorded stage artifacts require reconciliation')
                else: directory.mkdir(mode=0o700); sync_directory(directory.parent)
                if (directory/'packet.json').exists(): require(load_private(directory/'packet.json')==saved,'Interrupted stage packet changed')
                else: write_new(directory/'packet.json', encoded(saved))
                log.append('STEP_STARTED', {'step_id':identity, 'packet':saved, 'packet_sha256':c.digest(saved)})
                result, names = dispatch(step, saved, directory, base, plan, root)
            receipt = dict(step_id=identity, packet_sha256=c.digest(saved), status=result['status'],
                           artifacts=artifact_receipt(directory,names), native_acceptance=False, production_activation=False)
            log.append('STEP_COMPLETED',receipt)
            receipts[identity] = receipt
        if not closed:
            log.append('DELIVERY_COMPLETED',{'plan_sha256':c.digest(plan),'receipts':{k:c.digest(v) for k,v in receipts.items()}})
        return dict(status='DELIVERY_EXECUTED_REQUIRES_ACCEPTANCE', plan_sha256=c.digest(plan),
                    completed_steps=list(receipts), native_acceptance=False, production_activation=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','inbox','ledger'): parser.add_argument('--'+name, required=True, type=Path)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    try:
        result=run(load_private(args.plan),args.inbox,args.ledger,execute=args.execute)
        print(json.dumps(result)); return 0
    except Exception:
        # Native subprocess/transport exceptions can contain private material.
        print(json.dumps({'status':'HOLD_DELIVERY_RECONCILIATION','native_acceptance':False,
                          'production_activation':False,'reason':'Inspect private owner and delivery journals; do not replay uncertain writes'}))
        return 2


if __name__=='__main__': raise SystemExit(main())
