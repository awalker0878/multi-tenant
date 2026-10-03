#!/usr/bin/env python3
"""Monotonic worker subject-key revocation with durable intent and atomic publication.

New authentications only: revocation does not terminate sessions or fence jobs.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None,''): sys.path.insert(0,str(ROOT))
from provisioner.execution import readback_core as c
from tools import owner_install as install, execution_journal as journal
from provisioner.execution.run_files import current_window,digest,encoded,load_private,private_path,require,utcnow,write_new


def validate(config, request):
    install.validate(config)
    c.exact_keys(request,{'format','config_sha256','operation_id','keys','identity_ref'})
    require(request['format']=='hosting-owner-revocation/1' and request['config_sha256']==c.digest(config),
            'Revocation must bind the installed worker identity')
    c.identifier(request['operation_id']); c.text(request['identity_ref'])
    require(isinstance(request['keys'],list) and 1<=len(request['keys'])<=256,'Exact bounded revoked subject keys required')
    for key in request['keys']: install.public_key(key)
    require(request['keys']==sorted(set(request['keys'])),'Revoked subject keys must be sorted and unique')


def authorize(request, authority, *, now=None):
    c.exact_keys(authority,{'format','request_sha256','valid_from','valid_until','change_ref','recovery_access_ref'})
    require(authority['format']=='hosting-owner-revocation-authority/1' and authority['request_sha256']==c.digest(request),
            'Exact revocation authority required')
    current_window(authority,now=now)
    for name in ('change_ref','recovery_access_ref'): c.text(authority[name])


def effective(config, host):
    """Caller holds the shared installation lock; every intent adds only denial."""
    directory=host.directory(install.STATE/'revocations')
    log=journal.Journal(directory,{'owner':'worker-revocation','machine_id':config['machine_id'],
                                   'config_sha256':c.digest(config)})
    keys=set(config['revoked_user_keys']); seen=set()
    def rendered(): return ('\n'.join(sorted(keys))+'\n').encode()
    prefixes=[rendered()]
    for event in log.events:
        require(event['kind']=='REVOCATION_REQUIRED','Unknown worker revocation history event')
        c.exact_keys(event['data'],{'request','authority'})
        request,authority=event['data']['request'],event['data']['authority']
        validate(config,request); authorize(request,authority,now=c.timestamp(event['at']))
        require(request['operation_id'] not in seen,'Duplicate revocation operation in history')
        seen.add(request['operation_id']); keys.update(request['keys'])
        require(len(keys)<=16384,'Worker revocation capacity requires a separately accepted identity transition')
        prefixes.append(rendered())
    return log,prefixes


def reconcile(host, prefixes):
    """Restore the strongest recorded denial; never adopt or erase unknown keys."""
    path=host.path(install.CONFIG/'revoked-keys')
    require(path.is_file() and not path.is_symlink(),'Retained revocation policy is missing; keep authentication held')
    current=path.read_bytes()
    require(current in prefixes,'Unrecognized revocation policy; preserve independent identity controls')
    host.verify_file(install.CONFIG/'revoked-keys',current,0o644)
    if current!=prefixes[-1]: host.replace_revocations(current,prefixes[-1])
    return prefixes[-1]


def revoke(config, request, authority, *, host=None, root=ROOT):
    validate(config,request); authorize(request,authority); host=host or install.Host(); host.identity(config,root)
    state=host.directory(install.STATE,create=False)
    fd=os.open(state/'writer.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        private_path(state/'writer.lock'); fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        original=load_private(state/'intent.json')
        expected=install.service_files(config)
        expected_hashes={name:digest(raw) for name,raw in expected.items()}
        expected_hashes['host-key']=config['host_private']['sha256']
        require(original=={'format':'hosting-owner-install-intent/1','config':config,'files':expected_hashes},
                'Worker installation identity changed')
        for name,raw in expected.items():
            if name=='revoked-keys': continue
            path=install.UNIT if name==install.SERVICE else install.TMPFILES if name=='hosting-owner.tmpfiles' else install.CONFIG/name
            host.verify_file(path,raw,0o600 if name=='sshd_config' else 0o644)
        private_key=host.path(install.CONFIG/'host-key').read_bytes()
        require(digest(private_key)==config['host_private']['sha256'],'Installed worker host identity changed')
        host.verify_file(install.CONFIG/'host-key',private_key,0o600)
        log,prefixes=effective(config,host)
        # Reconcile an older interrupted denial before accepting a subsequent one.
        reconcile(host,prefixes)
        prior=next((e['data']['request'] for e in log.events
                    if e['data']['request']['operation_id']==request['operation_id']),None)
        if prior is not None:
            require(prior==request,'Revocation operation identity cannot change its subjects')
        else:
            total=set(prefixes[-1].decode().splitlines())|set(request['keys']); total.discard('')
            require(len(total)<=16384,'Worker revocation capacity exceeded')
            authorize(request,authority)
            log.append('REVOCATION_REQUIRED',{'request':request,'authority':authority})
            _,prefixes=effective(config,host)
        authorize(request,authority); result_bytes=reconcile(host,prefixes)
        result={'format':'hosting-owner-revocation-receipt/1','status':'SUBJECTS_REVOKED_FOR_NEW_AUTHENTICATION',
            'request_sha256':c.digest(request),'config_sha256':c.digest(config),'authority_sha256':c.digest(authority),
            'revoked_policy_sha256':digest(result_bytes),'revocation_events':len(log.events),'observed_at':utcnow().isoformat(),
            'existing_sessions_terminated':False,'native_fencing':False,'production_activation':False}
        write_new(state/('revocation-receipt-'+digest(encoded(result))+'.json'),encoded(result))
        return result
    finally: os.close(fd)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('config','request'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--authority',type=Path); parser.add_argument('--execute',action='store_true'); args=parser.parse_args()
    try:
        config,request=load_private(args.config),load_private(args.request); validate(config,request)
        if not args.execute: print('{"status":"VALIDATED_NO_HOST_CHANGE"}'); return 0
        require(args.authority is not None,'Current revocation authority required')
        result=revoke(config,request,load_private(args.authority)); print(json.dumps({'status':result['status']})); return 0
    except Exception:
        print('{"status":"WORKER_REVOCATION_HELD","reason":"Preserve identity and native-job records; do not remove revocations or restart work"}')
        return 2


if __name__=='__main__': raise SystemExit(main())
