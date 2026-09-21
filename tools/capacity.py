#!/usr/bin/env python3
"""Authoritative, transactional capacity reservations on one recoverable owner host."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
if __package__ in (None,''): sys.path.insert(0,str(ROOT))
from tools import readback_core as c
from tools.run_files import current_window, encoded, load_private, private_path, require, sync_directory, write_new

UNITS={'vcpu','memory_mb','storage_gb'}
LIVE={'RESERVED','CONFIRMED'}


def units(value):
    c.exact_keys(value,UNITS)
    require(all(type(n) is int and 0<=n<=10**15 for n in value.values()),'Nonnegative integral capacity units required')


def validate_envelope(value):
    c.exact_keys(value,{'format','owner_id','revision','valid_from','valid_until','acceptance_ref','pools','tenants'})
    require(value['format']=='hosting-capacity-envelope/1' and type(value['revision']) is int and value['revision']>0,
            'Versioned capacity envelope required')
    c.identifier(value['owner_id']); c.text(value['acceptance_ref']); current_window(value)
    require(isinstance(value['pools'],dict) and 1<=len(value['pools'])<=1000
            and isinstance(value['tenants'],dict) and 1<=len(value['tenants'])<=10000,'Bounded pools and tenant entitlements required')
    native=set()
    for key,pool in value['pools'].items():
        c.identifier(key); c.exact_keys(pool,{'origin','native_id','platform','site_key','capacity','reserve','capabilities','qualification_ref'})
        require(c.origin(pool['origin'])==pool['origin'] and pool['platform'] in {'nutanix','vmware','openstack'},'Exact qualified platform origin required')
        c.text(pool['native_id']); c.identifier(pool['site_key']); c.text(pool['qualification_ref'])
        identity=(pool['origin'],pool['native_id'])
        require(identity not in native,'A native pool cannot be counted twice'); native.add(identity)
        units(pool['capacity']); units(pool['reserve'])
        require(all(pool['reserve'][k]<=pool['capacity'][k] for k in UNITS),'Failure reserve exceeds pool capacity')
        require(isinstance(pool['capabilities'],list) and pool['capabilities'] and len(pool['capabilities'])==len(set(pool['capabilities'])),
                'Exact qualified capability set required')
        for capability in pool['capabilities']: c.identifier(capability)
    for tenant,entitlement in value['tenants'].items():
        c.identifier(tenant); c.exact_keys(entitlement,{'limit','pools','entitlement_ref'}); units(entitlement['limit']); c.text(entitlement['entitlement_ref'])
        require(isinstance(entitlement['pools'],list) and entitlement['pools'] and len(entitlement['pools'])==len(set(entitlement['pools']))
                and set(entitlement['pools'])<=value['pools'].keys(),'Tenant must name exact eligible pools')


def validate_request(request):
    c.exact_keys(request,{'format','owner_id','reservation_id','operation_id','generation','scope','pool_id','units','capabilities'})
    require(request['format']=='hosting-capacity-request/1' and type(request['generation']) is int and request['generation']>0,'Exact reservation generation required')
    for key in ('owner_id','reservation_id','operation_id','pool_id'): c.identifier(request[key])
    c.exact_keys(request['scope'],{'environment_key','site_key','platform','tenant_key','wsd_key'})
    for value in request['scope'].values(): c.identifier(value)
    units(request['units']); require(any(request['units'].values()),'Empty reservations are not supported')
    require(isinstance(request['capabilities'],list) and request['capabilities']
            and len(request['capabilities'])==len(set(request['capabilities'])),'Requested capabilities must be explicit')
    for capability in request['capabilities']: c.identifier(capability)


@contextmanager
def database(path):
    path=private_path(path); require(not path.resolve().is_relative_to(ROOT.resolve()),'Capacity database must be outside the checkout')
    private_path(path.parent,directory=True)
    connection=sqlite3.connect(path,timeout=0,isolation_level=None)
    try:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA synchronous=FULL')
        connection.execute('BEGIN IMMEDIATE')
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback(); raise
    finally: connection.close()


def initialize(path,envelope):
    validate_envelope(envelope); path=Path(path).absolute()
    require(not path.resolve().is_relative_to(ROOT.resolve()),'Private capacity database required')
    write_new(path,b'')
    with database(path) as db:
        db.execute('CREATE TABLE envelope (singleton INTEGER PRIMARY KEY CHECK(singleton=1), body TEXT NOT NULL)')
        db.execute('CREATE TABLE reservation (id TEXT PRIMARY KEY, request TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN (\'RESERVED\',\'CONFIRMED\',\'RELEASED\')), native TEXT NOT NULL, receipt TEXT NOT NULL)')
        db.execute('CREATE TABLE event (sequence INTEGER PRIMARY KEY, body TEXT NOT NULL, digest TEXT NOT NULL)')
        db.execute('INSERT INTO envelope VALUES (1,?)',(encoded(envelope).decode(),))
        event(db,'INITIALIZED',{'envelope_sha256':c.digest(envelope),'revision':envelope['revision']})
    sync_directory(path.parent)


def event(db,kind,data):
    previous=db.execute('SELECT sequence,digest FROM event ORDER BY sequence DESC LIMIT 1').fetchone()
    body=dict(kind=kind,at=c.now(),data=data,previous_sha256=previous[1] if previous else None)
    db.execute('INSERT INTO event VALUES (?,?,?)',((previous[0]+1 if previous else 1),encoded(body).decode(),c.digest(body)))


def verify_events(db):
    previous=None; expected={}; envelope_sha=None
    for number,row in enumerate(db.execute('SELECT sequence,body,digest FROM event ORDER BY sequence'),1):
        body=c.strict_loads(row[1]); c.exact_keys(body,{'kind','at','data','previous_sha256'})
        require(row[0]==number and row[2]==c.digest(body) and body['previous_sha256']==previous,'Capacity event chain changed')
        if body['kind'] in {'INITIALIZED','ENVELOPE_UPDATED'}:
            require((number==1)==(body['kind']=='INITIALIZED'),'Invalid capacity initialization ordering')
            if number>1: require(body['data']['previous_envelope_sha256']==envelope_sha,'Capacity envelope history changed')
            envelope_sha=body['data']['envelope_sha256']
        else:
            require(body['kind'] in {'RESERVE','CONFIRM','RELEASE'},'Unknown capacity event')
            receipt=body['data']['receipt']; identity=receipt['reservation_id']
            state={'RESERVE':'RESERVED','CONFIRM':'CONFIRMED','RELEASE':'RELEASED'}[body['kind']]
            require(receipt['status']==state and receipt['request_sha256']==body['data']['request_sha256'], 'Capacity event receipt changed')
            require((identity not in expected) if state=='RESERVED' else (identity in expected and expected[identity]['status'] in LIVE),
                    'Capacity transition history changed')
            expected[identity]=receipt
        previous=row[2]
    require(previous is not None,'Capacity owner initialization is missing')
    rows=db.execute('SELECT id,request,status,native,receipt FROM reservation ORDER BY id').fetchall()
    require({row[0] for row in rows}==expected.keys(),'Capacity allocation membership differs from its journal')
    for row in rows:
        request=c.strict_loads(row[1]); validate_request(request); receipt=expected[row[0]]
        require(c.digest(request)==receipt['request_sha256'] and c.digest(c.strict_loads(row[4]))==c.digest(receipt)
                and row[2]==receipt['status'] and c.strict_loads(row[3])==receipt['native_ids'],'Capacity allocation differs from its journal')
    envelope=c.strict_loads(db.execute('SELECT body FROM envelope WHERE singleton=1').fetchone()[0])
    require(c.digest(envelope)==envelope_sha,'Capacity envelope differs from its journal')
    return rows


def update_envelope(path,envelope,authority):
    validate_envelope(envelope)
    c.exact_keys(authority,{'format','envelope_sha256','previous_envelope_sha256','valid_from','valid_until','change_ref'})
    require(authority['format']=='hosting-capacity-envelope-authority/1' and authority['envelope_sha256']==c.digest(envelope),
            'Capacity envelope authority differs')
    c.text(authority['change_ref']); current_window(authority)
    with database(path) as db:
        rows=verify_events(db); previous=c.strict_loads(db.execute('SELECT body FROM envelope WHERE singleton=1').fetchone()[0])
        require(authority['previous_envelope_sha256']==c.digest(previous) and envelope['owner_id']==previous['owner_id']
                and envelope['revision']==previous['revision']+1,'Exact next capacity envelope revision required')
        for row in rows:
            if row[2] not in LIVE: continue
            request=c.strict_loads(row[1]); pool_id=request['pool_id']
            require(pool_id in envelope['pools'] and all(envelope['pools'][pool_id][key]==previous['pools'][pool_id][key]
                    for key in ('origin','native_id','platform','site_key')),'Live capacity cannot move to another native pool')
            admitted(envelope,request,[other for other in rows if other[0]!=row[0]])
        current_window(authority)
        db.execute('UPDATE envelope SET body=? WHERE singleton=1',(encoded(envelope).decode(),))
        event(db,'ENVELOPE_UPDATED',{'envelope_sha256':c.digest(envelope),'previous_envelope_sha256':c.digest(previous),
                                   'revision':envelope['revision'],'change_ref':authority['change_ref']})
    return {'status':'ENVELOPE_UPDATED','envelope_sha256':c.digest(envelope)}


def usage(rows,pool=None,tenant=None):
    total={key:0 for key in UNITS}
    for row in rows:
        request=c.strict_loads(row[1])
        if row[2] not in LIVE or (pool is not None and request['pool_id']!=pool) or (tenant is not None and request['scope']['tenant_key']!=tenant): continue
        for key in UNITS: total[key]+=request['units'][key]
    return total


def admitted(envelope,request,rows):
    validate_envelope(envelope); validate_request(request)
    require(request['owner_id']==envelope['owner_id'],'Capacity owner differs')
    tenant=request['scope']['tenant_key']; pool_id=request['pool_id']
    require(tenant in envelope['tenants'] and pool_id in envelope['tenants'][tenant]['pools'],'Tenant is not entitled to this pool')
    pool=envelope['pools'][pool_id]
    require(pool['platform']==request['scope']['platform'] and pool['site_key']==request['scope']['site_key']
            and set(request['capabilities'])<=set(pool['capabilities']),'Reservation exceeds qualified placement capabilities')
    pooled=usage(rows,pool=pool_id); owned=usage(rows,tenant=tenant)
    for key in UNITS:
        require(pooled[key]+request['units'][key]<=pool['capacity'][key]-pool['reserve'][key], 'Qualified pool capacity exhausted')
        require(owned[key]+request['units'][key]<=envelope['tenants'][tenant]['limit'][key], 'Tenant capacity entitlement exhausted')


def operate(path,request,action,authority,native_ids=None):
    validate_request(request)
    require(action in {'reserve','confirm','release','inspect'},'Unknown capacity operation')
    native_ids=[] if native_ids is None else native_ids
    require(isinstance(native_ids,list) and len(native_ids)==len(set(native_ids)),'Unique exact native allocation IDs required')
    for identity in native_ids: c.text(identity)
    if action=='confirm': require(native_ids,'Confirmation requires observed native resource identities')
    else: require(not native_ids,'Native identities may only be supplied during confirmation')
    if action!='inspect':
        c.exact_keys(authority,{'format','request_sha256','action','native_ids_sha256','envelope_sha256','previous_receipt_sha256','valid_from','valid_until','change_ref','evidence_ref'})
        require(authority['format']=='hosting-capacity-authority/1' and authority['request_sha256']==c.digest(request)
                and authority['action']==action and authority['native_ids_sha256']==c.digest(sorted(native_ids)), 'Capacity authority differs')
        current_window(authority); c.text(authority['change_ref']); c.text(authority['evidence_ref'])
    with database(path) as db:
        rows=verify_events(db)
        envelope=c.strict_loads(db.execute('SELECT body FROM envelope WHERE singleton=1').fetchone()[0])
        require(envelope['owner_id']==request['owner_id'],'Wrong capacity owner database')
        if action!='inspect': require(authority['envelope_sha256']==c.digest(envelope),'Capacity envelope changed since approval')
        existing=next((row for row in rows if row[0]==request['reservation_id']),None)
        if existing:
            require(c.digest(c.strict_loads(existing[1]))==c.digest(request),'Reservation ID cannot be rebound to another request')
        if action=='inspect':
            require(existing is not None,'No reservation found'); return c.strict_loads(existing[4])
        if action=='reserve':
            if existing:
                require(existing[2] in LIVE,'Released capacity cannot be reclaimed with an old request')
                return c.strict_loads(existing[4])
            require(not any(c.strict_loads(row[1])['operation_id']==request['operation_id'] and
                c.strict_loads(row[1])['generation']==request['generation'] and
                c.strict_loads(row[1])['scope']==request['scope'] for row in rows), 'Operation generation already reserved capacity')
            admitted(envelope,request,rows); state='RESERVED'; native=[]
        else:
            require(existing is not None,'Capacity must be reserved before transition')
            native=c.strict_loads(existing[3])
            if action=='confirm':
                require(existing[2] in LIVE,'Released reservation cannot be confirmed')
                if existing[2]=='CONFIRMED':
                    require(native==sorted(native_ids),'Confirmed native identities cannot change'); return c.strict_loads(existing[4])
                occupied={identity for row in rows if row[2] in LIVE for identity in c.strict_loads(row[3])}
                require(not occupied.intersection(native_ids),'Native resource already belongs to another capacity reservation')
                state='CONFIRMED'; native=sorted(native_ids)
            else:
                if existing[2]=='RELEASED': return c.strict_loads(existing[4])
                state='RELEASED'
        require(authority['previous_receipt_sha256']==(c.digest(c.strict_loads(existing[4])) if existing else None),
                'Capacity allocation changed since exact transition approval')
        current_window(authority)
        receipt=dict(format='hosting-capacity-receipt/1',request_sha256=c.digest(request),owner_id=request['owner_id'],
            reservation_id=request['reservation_id'],scope=request['scope'],pool_id=request['pool_id'],units=request['units'],
            status=state,native_ids=native,envelope_sha256=c.digest(envelope),change_ref=authority['change_ref'],
            evidence_ref=authority['evidence_ref'],observed_at=c.now(),native_acceptance=False,production_activation=False)
        db.execute('INSERT INTO reservation VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,native=excluded.native,receipt=excluded.receipt',
                   (request['reservation_id'],encoded(request).decode(),state,encoded(native).decode(),encoded(receipt).decode()))
        event(db,action.upper(),{'request_sha256':c.digest(request),'receipt':receipt})
        return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['initialize','update-envelope','reserve','confirm','release','inspect'])
    parser.add_argument('--database',required=True,type=Path)
    for name in ('envelope','request','authority','native_ids','output'): parser.add_argument('--'+name.replace('_','-'),type=Path)
    parser.add_argument('--execute',action='store_true'); args=parser.parse_args()
    try:
        require(args.execute,'Explicit capacity owner execution required')
        if args.action=='initialize': initialize(args.database,load_private(args.envelope)); result={'status':'INITIALIZED'}
        elif args.action=='update-envelope': result=update_envelope(args.database,load_private(args.envelope),load_private(args.authority))
        else:
            result=operate(args.database,load_private(args.request),args.action,load_private(args.authority) if args.authority else None,
                           load_private(args.native_ids) if args.native_ids else None)
        if args.output: write_new(args.output,encoded(result))
        print(json.dumps({'status':result['status']})); return 0
    except (ValueError,OSError,KeyError,TypeError,sqlite3.Error):
        print('{"status":"CAPACITY_HELD","reason":"Inspect the private capacity owner record; do not duplicate the reservation"}'); return 2


if __name__=='__main__': raise SystemExit(main())
