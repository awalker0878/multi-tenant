"""Certificate SSH transport; only a fixed forced command and staged job digest."""
import base64
import ipaddress
import os
from pathlib import Path
import re
import struct
import subprocess
import uuid
from provisioner.execution import readback_core as c
from tools import owner_worker as worker
from provisioner.execution.run_files import current_window,digest,encoded,load_private,private_path,read_private,require,sync_directory,write_new


def validate(target,job):
    c.exact_keys(target,{'format','address','port','user','host_key','machine_id','valid_from','valid_until','max_seconds'})
    require(target['format']=='hosting-owner-target/1','Unknown remote owner target')
    address=ipaddress.ip_address(target['address'])
    require(str(address)==target['address'] and not(address.is_multicast or address.is_unspecified),
            'Exact remote owner address required')
    require(type(target['port']) is int and 1<=target['port']<=65535
            and isinstance(target['user'],str) and re.fullmatch('[a-z_][a-z0-9_-]{0,31}',target['user']),
            'Exact remote owner SSH identity required')
    require(target['machine_id']==job['machine_id'],'Remote owner machine binding differs')
    require(type(target['max_seconds']) is int and 10<=target['max_seconds']<=3600,'Bounded owner transport required')
    key=target['host_key'].split(' ')
    require(len(key)==2 and key[0]=='ssh-ed25519','Exact pinned Ed25519 host key required')
    raw=base64.b64decode(key[1],validate=True)
    require(len(raw)==51 and raw[:19]==struct.pack('>I',11)+b'ssh-ed25519'+struct.pack('>I',32),
            'Malformed owner host key')
    current_window(target)


def recovery_access(record,job,original):
    c.exact_keys(record,{'format','job_sha256','files','access_ref'})
    require(record['format']=='hosting-owner-recovery-access/1' and record['job_sha256']==c.digest(job),
            'Recovery access must bind the original remote job')
    c.text(record['access_ref']); c.exact_keys(record['files'],{'target','ssh_key','ssh_certificate'})
    paths={}
    for name,binding in record['files'].items():
        c.exact_keys(binding,{'path','sha256'})
        require(digest(read_private(binding['path']))==binding['sha256'],'Recovery access input bytes changed')
        paths[name]=Path(binding['path'])
    target=load_private(paths['target']); validate(target,job)
    require({k:v for k,v in target.items() if k not in {'valid_from','valid_until'}}==
            {k:v for k,v in original.items() if k not in {'valid_from','valid_until'}},
            'Recovery access cannot change the original owner endpoint or transport bounds')
    return target,paths


def contact(job,target,binary,key,certificate,directory,*,observe=False):
    worker.validate(job); validate(target,job)
    if not observe: current_window(job)
    directory=private_path(directory,directory=True)
    attempt=directory/('transport-'+uuid.uuid4().hex); attempt.mkdir(mode=0o700)
    try:
        return exchange(job,target,binary,key,certificate,attempt,observe=observe)
    finally:
        (attempt/'ssh_key').unlink(missing_ok=True); (attempt/'ssh_key-cert.pub').unlink(missing_ok=True)
        sync_directory(attempt)


def exchange(job,target,binary,key,certificate,attempt,*,observe):
    """Setup and transport are both inside the credential cleanup boundary."""
    private_path(key); private_path(certificate)
    for name,raw in {'ssh_key':read_private(key),'ssh_key-cert.pub':read_private(certificate)}.items(): write_new(attempt/name,raw)
    host=target['address']; port=target['port']
    pins=f'[{host}]:{port} {target["host_key"]}\n'
    if port==22: pins+=f'{host} {target["host_key"]}\n'
    write_new(attempt/'known_hosts',pins.encode())
    options=['BatchMode=yes','StrictHostKeyChecking=yes','UpdateHostKeys=no','GlobalKnownHostsFile=/dev/null',
        'UserKnownHostsFile='+str(attempt/'known_hosts'),'IdentitiesOnly=yes','IdentityAgent=none',
        'PubkeyAcceptedAlgorithms=ssh-ed25519-cert-v01@openssh.com','ForwardAgent=no','ClearAllForwardings=yes',
        'ProxyCommand=none','ProxyJump=none','ConnectionAttempts=1','ConnectTimeout=5','ServerAliveInterval=5',
        'ServerAliveCountMax=1','LogLevel=ERROR','ControlMaster=no','ControlPath=none','RequestTTY=no']
    argv=[str(binary),'-F','/dev/null','-T','-i',str(attempt/'ssh_key'),'-p',str(port),'-l',target['user']]
    for option in options: argv+=['-o',option]
    argv+=[host,worker.COMMAND]
    request={'format':'hosting-owner-request/1','action':'observe' if observe else 'execute',
             'job_id':job['job_id'],'job_sha256':c.digest(job)}
    budget=min(target['max_seconds'],(c.timestamp(target['valid_until'])-c.timestamp(c.now())).total_seconds())
    output=attempt/'response.json'
    with os.fdopen(os.open(attempt/'ssh.log',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb') as err, \
         os.fdopen(os.open(output,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb') as out:
        result=subprocess.run(argv,input=encoded(request),stdout=out,stderr=err,
            env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},timeout=budget,umask=0o077)
        out.flush(); os.fsync(out.fileno()); err.flush(); os.fsync(err.fileno())
    require(result.returncode==0 and output.stat().st_size<=worker.MAX_RESULT,'Remote owner remains held; observe its retained job')
    value=c.strict_loads(read_private(output)); worker.check_result(value,job)
    return value
