#!/usr/bin/env python3
"""Real certificate SSH and forced worker; synthetic backup engine, no platform."""
import argparse
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import pwd
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import remote_owner,owner_worker,readback_core as c
from tools.run_files import digest,encoded,read_private,utcnow,write_new


def run(user):
    ssh,sshd,keygen=(shutil.which(name) for name in ('ssh','sshd','ssh-keygen'))
    account=pwd.getpwnam(user)
    if os.geteuid()!=0 or not all((ssh,sshd,keygen)) or account.pw_uid==0:
        raise RuntimeError('Disposable SSH fixture requires root and an existing non-root fixture account')
    with tempfile.TemporaryDirectory(prefix='hosting-worker-lab-') as tmp:
        base=Path(tmp); base.chmod(0o755)
        owner=base/'owner'; owner.mkdir(mode=0o700)
        spool=owner/'spool'; spool.mkdir(mode=0o700)
        ledger=owner/'ledger'; ledger.mkdir(mode=0o700)
        source=owner/'export'; source.mkdir(mode=0o700); (source/'data').write_bytes(b'Useful fixture data')
        engine=owner/'synthetic-restic'
        engine.write_text('''#!/usr/bin/python3
import json,sys
from pathlib import Path
if 'cat' in sys.argv:
    print(json.dumps({'id':'b'*64}))
elif 'backup' in sys.argv:
    counter=Path(__file__).with_name('captures')
    counter.write_text(str(int(counter.read_text())+1) if counter.exists() else '1')
    print(json.dumps({'message_type':'summary','snapshot_id':'d'*64}))
else:
    raise SystemExit(2)
'''); engine.chmod(0o700)
        config={'format':'hosting-restic-export/1','scope':{'environment_key':'lab','site_key':'site-01',
            'platform':'openstack','tenant_key':'tenant-01','wsd_key':'wsd-01'},'member':'guest-01',
            'machine_id':Path('/etc/machine-id').read_text().strip(),'source':str(source),
            'repository':'rest:https://backup.invalid/fixture/','repository_id':'b'*64,
            'restic_sha256':digest(engine.read_bytes()),'valid_until':(utcnow()+timedelta(minutes=5)).isoformat(),
            'consistency_ref':'LOCAL-SYNTHETIC-ONLY','max_seconds':30}
        files={}
        for name,value in {'config':config,'credentials':{'password':'fixture','username':'fixture','http_password':'fixture'}}.items():
            path=owner/(name+'.json'); write_new(path,encoded(value)); files[name]={'path':str(path),'sha256':digest(read_private(path))}
        commit=subprocess.check_output(['git','-c',f'safe.directory={ROOT}','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
        job={'format':'hosting-owner-job/1','job_id':'capture-01','machine_id':config['machine_id'],
            'source_commit':commit,'scope':config['scope'],'generation':1,'kind':'restic',
            'parameters':{'action':'backup','restic':str(engine),'restic_sha256':config['restic_sha256'],'target':None},
            'files':files,'delivery':{'plan_sha256':'a'*64,'step_id':'capture','dependencies':{}},
            'valid_from':(utcnow()-timedelta(minutes=1)).isoformat(),'valid_until':config['valid_until'],
            'dispatch_ref':'DISPOSABLE-LOCAL-FIXTURE'}
        write_new(spool/'capture-01.json',encoded(job))
        wrong=deepcopy(job); wrong['job_id']='wrong-machine'; wrong['machine_id']='0'*32
        write_new(spool/'wrong-machine.json',encoded(wrong))
        for path in [owner,*owner.rglob('*')]: os.chown(path,account.pw_uid,account.pw_gid)
        def command(argv): return subprocess.check_output(argv,stderr=subprocess.STDOUT,timeout=15,text=True)
        for name in ('host','ca','ssh_key'):
            command([keygen,'-q','-t','ed25519','-N','','-f',str(base/name)])
        command([keygen,'-q','-s',str(base/'ca'),'-I','disposable-owner-fixture','-n',user,
                 '-V','-1m:+5m',str(base/'ssh_key.pub')]); (base/'ssh_key-cert.pub').chmod(0o600)
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1',0)); port=reservation.getsockname()[1]
        forced=' '.join(shlex.quote(str(x)) for x in [sys.executable,'-I',ROOT/'tools/owner_worker.py','--spool',spool,'--ledger',ledger])
        daemon_config=base/'sshd.conf'
        daemon_config.write_text('\n'.join([f'Port {port}','ListenAddress 127.0.0.1',f'HostKey {base}/host',
            f'PidFile {base}/sshd.pid','UsePAM yes','PasswordAuthentication no','KbdInteractiveAuthentication no',
            'PermitRootLogin no','AuthorizedKeysFile none',f'TrustedUserCAKeys {base}/ca.pub',
            'PubkeyAcceptedAlgorithms ssh-ed25519-cert-v01@openssh.com',f'AllowUsers {user}',
            'AllowAgentForwarding no','AllowTcpForwarding no','AllowStreamLocalForwarding no',
            'PermitTunnel no','X11Forwarding no','PermitTTY no','PermitUserRC no','PermitUserEnvironment no',
            'ForceCommand '+forced,'']))
        command([sshd,'-t','-f',str(daemon_config)])
        target={'format':'hosting-owner-target/1','address':'127.0.0.1','port':port,'user':user,
            'host_key':' '.join((base/'host.pub').read_text().split()[:2]),'machine_id':job['machine_id'],
            'valid_from':job['valid_from'],'valid_until':job['valid_until'],'max_seconds':30}
        transport=base/'transport'; transport.mkdir(mode=0o700)
        def contact(value=job,endpoint=target,observe=False):
            return remote_owner.contact(value,endpoint,ssh,base/'ssh_key',base/'ssh_key-cert.pub',transport,observe=observe)
        with open(base/'daemon.log','wb') as log:
            daemon=subprocess.Popen([sshd,'-D','-e','-f',str(daemon_config)],stdout=log,stderr=log)
            try:
                for _ in range(30):
                    try:
                        with socket.create_connection(('127.0.0.1',port),timeout=.2): break
                    except OSError: time.sleep(.1)
                first=contact(); repeated=contact(observe=True)
                if first!=repeated or (owner/'captures').read_text()!='1': raise RuntimeError('Owner operation replayed')
                for value,endpoint in [(wrong,target|{'machine_id':'0'*32}),
                    (job,target|{'host_key':' '.join((base/'ca.pub').read_text().split()[:2])})]:
                    try: contact(value,endpoint)
                    except ValueError: pass
                    else: raise RuntimeError('Wrong machine or changed host key accepted')
                original=owner_worker.COMMAND
                try:
                    owner_worker.COMMAND='uname -a'
                    try: contact()
                    except ValueError: pass
                    else: raise RuntimeError('Worker accepted an arbitrary command')
                finally: owner_worker.COMMAND=original
                if (owner/'captures').read_text()!='1': raise RuntimeError('Negative case executed backup')
                if list(transport.glob('*/ssh_key*')): raise RuntimeError('Temporary credentials retained')
                return {'status':'PASSED_LOCAL_OWNER_SSH_ONLY','certificate_ssh':True,'forced_command':True,
                    'retained_receipt_observed_without_replay':True,'wrong_machine_and_host_key_rejected':True,
                    'arbitrary_command_rejected':True,'temporary_credentials_removed':True,
                    'backup_engine':'SYNTHETIC_FIXTURE','native_platform_contacted':False}
            finally:
                daemon.terminate()
                try: daemon.wait(timeout=3)
                except subprocess.TimeoutExpired: daemon.kill(); daemon.wait(timeout=3)


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--user',required=True); args=parser.parse_args()
    try: report,code=run(args.user),0
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
        report,code={'status':'FAILED_LOCAL_OWNER_SSH','reason':str(exc)},2
    output=ROOT/'build/reports/owner_worker_lab.json'; output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2)); return code


if __name__=='__main__': raise SystemExit(main())
