#!/usr/bin/env python3
"""Real certificate SSH and forced worker; synthetic backup engine, no platform."""
import argparse
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import pwd
import shutil
import socket
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import remote_owner,owner_worker,owner_install,readback_core as c
from tools.run_files import digest,encoded,read_private,utcnow,write_new


def run(user):
    ssh,sshd,keygen=(shutil.which(name) for name in ('ssh','sshd','ssh-keygen'))
    account=pwd.getpwnam(user)
    if os.geteuid()!=0 or not all((ssh,sshd,keygen)) or account.pw_uid==0:
        raise RuntimeError('Disposable SSH fixture requires root and an existing non-root fixture account')
    # StrictModes checks every ancestor of AuthorizedPrincipalsFile. A fixture
    # under world-writable /tmp cannot represent the root-controlled installer.
    with tempfile.TemporaryDirectory(prefix='hosting-worker-lab-',dir='/var/lib') as tmp:
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
        install_config={'format':'hosting-owner-install/1','source_commit':commit,'machine_id':job['machine_id'],
            'account':user,'uid':account.pw_uid,'gid':account.pw_gid,'listen_address':'127.0.0.1','port':port,
            'principal':user,'source':str(ROOT),'python':sys.executable,'sshd':sshd,'ssh_keygen':keygen,
            'systemctl':'/usr/bin/systemctl','host_private':{'path':str(base/'host'),'sha256':digest((base/'host').read_bytes())},
            'host_public':' '.join((base/'host.pub').read_text().split()[:2]),
            'user_ca':' '.join((base/'ca.pub').read_text().split()[:2]),'revoked_user_keys':[],
            'data_directory':'/var/lib/hosting-owner-fixture',
            'ledger_mode':'new','custody_ref':'DISPOSABLE-LOCAL-FIXTURE'}
        for name in ('python','sshd','ssh_keygen','systemctl'):
            install_config[name+'_sha256']=digest(Path(install_config[name]).read_bytes())
        for name,raw in owner_install.service_files(install_config,config_directory=base,
                data_directory=owner,runtime_directory=base).items():
            (base/name).write_bytes(raw); (base/name).chmod(0o644)
        (base/'host-key').write_bytes((base/'host').read_bytes()); (base/'host-key').chmod(0o600)
        daemon_config=base/'sshd_config'
        command([sshd,'-t','-f',str(daemon_config)])
        parsed=command([sshd,'-T','-f',str(daemon_config)])
        if 'authenticationmethods publickey' not in parsed or 'disableforwarding yes' not in parsed:
            raise RuntimeError('Native daemon did not retain the generated worker restrictions')
        analyze=shutil.which('systemd-analyze')
        if analyze: command([analyze,'verify','--man=no',str(base/owner_install.SERVICE)])
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
                try:
                    first=contact(); repeated=contact(observe=True)
                except ValueError as exc:
                    # These logs contain only disposable fixture identities.
                    # Keep native failure diagnostics before temporary cleanup.
                    errors='\n'.join(path.read_text(errors='replace')[-2000:] for path in sorted(transport.glob('*/ssh.log')))
                    raise RuntimeError(str(exc)+'\n'+(base/'daemon.log').read_text(errors='replace')[-6000:]+'\n'+errors) from None
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
                (base/'revoked-keys').write_text(' '.join((base/'ssh_key.pub').read_text().split()[:2])+'\n')
                try: contact(observe=True)
                except ValueError: pass
                else: raise RuntimeError('Revoked certificate subject retained worker access')
                if list(transport.glob('*/ssh_key*')): raise RuntimeError('Temporary credentials retained')
                return {'status':'PASSED_LOCAL_OWNER_SSH_ONLY','certificate_ssh':True,'forced_command':True,
                    'installation_profile_native_parse':True,'installation_unit_native_parse':bool(analyze),
                    'revoked_certificate_subject_rejected_without_restart':True,
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
