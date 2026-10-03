#!/usr/bin/env python3
"""Install only owned permanent deny tables before an accepted network manager starts."""
import argparse
from contextlib import ExitStack,contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import sys

from hosting_resources import SOURCE_ROOT
ROOT = SOURCE_ROOT
from provisioner.execution import readback_core as c
from provisioner.execution import nft_edge as edge, edge_contain
from provisioner.execution.source_integrity import verify, verify_runtime
from provisioner.execution.run_files import digest,encoded,load_private,new_directory,private_path,read_private,require,sync_directory,write_new


def validate(config):
    c.exact_keys(config,{'format','source_commit','machine_id','network_namespace_inode','nft','nft_sha256',
        'ledger','specs','boundary_acceptance_ref','boot_ordering_ref'})
    require(config['format']=='hosting-edge-boot/1' and re.fullmatch('[0-9a-f]{40}',config['source_commit']),
            'Exact accepted boot source required')
    require(re.fullmatch('[0-9a-f]{32}',config['machine_id']) and type(config['network_namespace_inode']) is int
            and config['network_namespace_inode']>0,'Exact boot machine and namespace required')
    for key in ('boundary_acceptance_ref','boot_ordering_ref'): c.text(config[key])
    require(isinstance(config['specs'],list) and 1<=len(config['specs'])<=100,'Complete bounded edge boot scope set required')
    require(Path(config['nft']).is_absolute() and re.fullmatch('[0-9a-f]{64}',config['nft_sha256']),
            'Exact firewall executable required')
    private_path(config['ledger'],directory=True)
    specs=[]; scopes=set(); owned=set()
    for binding in config['specs']:
        c.exact_keys(binding,{'path','sha256'}); raw=read_private(binding['path'])
        require(digest(raw)==binding['sha256'],'Boot boundary input changed')
        spec=c.strict_loads(raw); _,scope=edge.validate(spec)
        require(spec['machine_id']==config['machine_id'] and spec['network_namespace_inode']==config['network_namespace_inode']
                and spec['nft_sha256']==config['nft_sha256'] and spec['flows']==[],
                'Boot policy must be an exact local boundary with no allow intent')
        require(scope not in scopes and not owned.intersection(spec['owned_interfaces']),
                'Boot scopes or owned domain interfaces overlap')
        scopes.add(scope); owned.update(spec['owned_interfaces']); specs.append(spec)
    return sorted(specs,key=lambda spec:edge.validate(spec)[1])


@contextmanager
def boundary_lock(ledger,scope):
    directory=private_path(ledger,directory=True)/scope
    if not directory.exists(): directory.mkdir(mode=0o700); sync_directory(directory.parent)
    private_path(directory,directory=True)
    fd=os.open(directory/'writer.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        private_path(directory/'writer.lock'); fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
    finally: os.close(fd)


def apply(config,operation,*,kernel=None,root=ROOT):
    specs=validate(config)
    require(Path('/etc/machine-id').read_text().strip()==config['machine_id']
            and os.stat('/proc/self/ns/net').st_ino==config['network_namespace_inode'],'Wrong edge boot host or namespace')
    require(isinstance(root,Path) and verify_runtime(root)['status']=='RUNTIME_SOURCES_MATCH',
            'Exact runtime and explicitly selected source checkout required')
    source=verify(root)
    require(source['status']=='HASHES_MATCH' and source['commit']==config['source_commit'],'Boot source changed')
    binary=Path(config['nft']).resolve(strict=True)
    require(digest(binary.read_bytes())==config['nft_sha256'],'Boot firewall executable changed')
    operation=new_directory(operation,root); kernel=kernel or edge.Kernel(binary,operation)
    with ExitStack() as locks:
        for spec in specs: locks.enter_context(boundary_lock(Path(config['ledger']),edge.validate(spec)[1]))
        before={}; sections=[]
        for spec in specs:
            current,observed=kernel.inspect(spec); scope=edge.validate(spec)[1]; before[scope]=observed
            # Permanent dual-family interface drops; no remembered allow/lease is restored.
            sections.append(edge.render(spec,'withdraw',1,exists=current is not None))
        candidate=operation/'candidate.nft'; write_new(candidate,'\n'.join(sections).encode())
        kernel.command(['--check','--file',str(candidate)])
        for spec in specs:
            require(kernel.inspect(spec)[1]==before[edge.validate(spec)[1]],'Edge policy changed while preparing boot denial')
        write_new(operation/'attempt.json',encoded({'status':'BOOT_DENIAL_OUTCOME_UNKNOWN','config_sha256':c.digest(config),
            'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'at':c.now()}))
        kernel.command(['--file',str(candidate)])
        observations={}
        for spec in specs:
            state,_=kernel.inspect(spec)
            observations[edge.validate(spec)[1]]=edge_contain.observed_withdrawal(spec,state)
        result={'format':'hosting-edge-boot-receipt/1','status':'BOOT_DENIAL_OBSERVED_REQUIRES_STARTUP_QUALIFICATION',
            'config_sha256':c.digest(config),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'machine_id':config['machine_id'],'namespace_inode':config['network_namespace_inode'],
            'observations':observations,'observed_at':c.now(),'native_acceptance':False,'production_activation':False}
        write_new(operation/'receipt.json',encoded(result)); return result


def service_files(python,source,config,output_root,ledger,manager):
    require(manager in {'systemd-networkd.service','NetworkManager.service'},'Select the actual managed networking service')
    for value in (python,source,config,output_root,ledger):
        require(isinstance(value,str) and re.fullmatch(r'/[A-Za-z0-9_./-]+',value) and '..' not in Path(value).parts,
                'Simple absolute installed paths required')
    service='\n'.join(['[Unit]','Description=Owned edge denial before network attachment',
        'DefaultDependencies=no','Wants=network-pre.target','Before=network-pre.target '+manager,
        'After=local-fs.target','Conflicts=shutdown.target','Before=shutdown.target',
        '', '[Service]','Type=oneshot','RemainAfterExit=yes','UMask=0077','TimeoutStartSec=90',
        'ExecStart='+python+' -I -B -m provisioner.execution.edge_boot apply --source-root '+source+' --config '+config+' --output-root '+output_root+' --execute',
        'NoNewPrivileges=yes','ProtectHome=yes','ProtectSystem=strict','ReadWritePaths='+output_root+' '+ledger,
        '', '[Install]','WantedBy=multi-user.target',''])
    dependency='[Unit]\nRequires=hosting-edge-boot.service\nAfter=hosting-edge-boot.service\n'
    return {'hosting-edge-boot.service':service,'network-manager.conf':dependency}


def main():
    parser=argparse.ArgumentParser(description=__doc__); commands=parser.add_subparsers(dest='action',required=True)
    boot=commands.add_parser('apply'); boot.add_argument('--source-root',type=Path,default=ROOT); boot.add_argument('--config',type=Path,required=True)
    boot.add_argument('--output-root',type=Path,required=True); boot.add_argument('--execute',action='store_true')
    render=commands.add_parser('render-service')
    for name in ('python','source','config','output_root','ledger','manager','output'):
        render.add_argument('--'+name.replace('_','-'),required=True)
    args=parser.parse_args()
    try:
        if args.action=='render-service':
            directory=new_directory(args.output,Path(__file__).resolve().parents[2])
            files=service_files(args.python,args.source,args.config,args.output_root,args.ledger,args.manager)
            for name,value in files.items(): write_new(directory/name,value.encode())
            print('{"status":"BOOT_SERVICE_FILES_RENDERED_REQUIRES_INSTALLATION"}'); return 0
        require(args.execute,'Explicit accepted boot policy execution required')
        import uuid
        result=apply(load_private(args.config),args.output_root/('boot-'+uuid.uuid4().hex),root=args.source_root)
        print(json.dumps({'status':result['status'],'native_acceptance':False})); return 0
    except Exception:
        print('{"status":"BOOT_DENIAL_UNCONFIRMED","reason":"Keep managed network attachment blocked; inspect private boot records"}')
        return 2


if __name__=='__main__': raise SystemExit(main())
