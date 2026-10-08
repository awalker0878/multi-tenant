"""Install, deny, restart and recover disposable P01 stateful dependencies."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import time
import urllib.request

from run_local import Campaign, digest
from stateful.runtime import prepare


class StatefulCampaign(Campaign):
    def __init__(self, root, output, revision):
        super().__init__(root, output, revision)
        self.report.update(scope='P01 isolated broker/workflow/evidence dependencies; synthetic effects only',started_at=datetime.now(timezone.utc).isoformat())

    def probe(self, service, stage, state=None, timeout=150):
        raw=self.command(stage,self.dc('run','--rm','--no-deps','-T',service,stage),data=None if state is None else json.dumps(state).encode(),timeout=timeout)
        result=json.loads(raw)
        self.check(stage+'-complete',result['result']=='PASS' and bool(result['checks']),{'checks':result['checks']})
        return result['state']

    def build(self, name, directory, dockerfile, arguments=(), timeout=1000):
        iid=self.output/(name+'-image-id.txt')
        self.command(name+'-image-build',['docker','build','--platform','linux/amd64','--pull','--iidfile',str(iid),'--build-arg','SOURCE_REVISION='+self.revision,*arguments,'-f',str(dockerfile),str(directory)],timeout=timeout)
        image=iid.read_text().strip()
        self.check(name+'-immutable-image',bool(re.fullmatch(r'sha256:[0-9a-f]{64}',image)),image)
        return image

    def run(self):
        self.check('exact-source',self.command('source-revision',['git','rev-parse','HEAD']).decode().strip()==self.revision)
        prefixes=['scripts/p01','deploy/fixtures/stateful','deploy/dependencies/stateful','deploy/dependencies/inputs.lock.json','deploy/build/inputs.lock.json','.github/workflows/p01-stateful-integration.yml']
        self.check('clean-source',not self.command('source-clean',['git','status','--porcelain','--untracked-files=all','--',*prefixes]).strip())
        self.report['source_sha256']={str(p.relative_to(self.root)):digest(p.read_bytes()) for prefix in prefixes for p in ([self.root/prefix] if (self.root/prefix).is_file() else sorted((self.root/prefix).rglob('*'))) if p.is_file() and '__pycache__' not in p.parts}
        lock=json.loads((self.root/'deploy/dependencies/stateful/inputs.lock.json').read_text())
        self.check('reviewed-candidates-bound',lock['candidate_sha256']==digest((self.root/'deploy/dependencies/stateful/candidates.json').read_bytes()))
        self.check('client-closure-bound',lock['client_lock_sha256']==digest((self.root/'scripts/p01/stateful/requirements.txt').read_bytes()) and lock['client_input_sha256']==digest((self.root/'scripts/p01/stateful/requirements.in').read_bytes()))
        self.report['inputs']=lock
        images={n:v['reference'] for n,v in lock['images'].items()}
        images['postgres']=json.loads((self.root/'deploy/dependencies/inputs.lock.json').read_text())['images']['postgres']['reference']
        for name,image in images.items():
            self.command(name+'-pull',['docker','pull','--platform','linux/amd64',image],timeout=300)
        client_dir=self.root/'scripts/p01/stateful'
        images['probe']=self.build('probe',client_dir,client_dir/'Dockerfile',timeout=500)
        for name in ('minio','mc'):
            source=lock[name+'_source']
            context=self.runtime.parent/(name+'-source-build');context.mkdir()
            with urllib.request.urlopen(source['url'],timeout=120) as response:
                archive=response.read(64*1024*1024+1)
            self.check(name+'-source-archive-bound',len(archive)==source['bytes'] and digest(archive)==source['sha256'],{'bytes':len(archive),'sha256':digest(archive)})
            (context/'source.tar.gz').write_bytes(archive)
            shutil.copyfile(client_dir/'Minio.Dockerfile',context/'Dockerfile')
            images[name]=self.build(name,context,context/'Dockerfile',['--build-arg','GO_IMAGE='+images['golang'],'--build-arg','BINARY='+name,'--build-arg','SOURCE_SHA256='+source['sha256']])
            self.command(name+'-module-provenance',['docker','run','--rm','--network','none','--entrypoint','sh',images[name],'-ec','cat /usr/local/bin/build-info.txt /usr/local/bin/module-digests.txt; sha256sum /usr/local/bin/'+name])
        self.report['installed_images']=images
        self.compose=prepare(self.root,self.runtime,images)
        rendered=json.loads(self.compose.read_text())
        self.command('compose-valid',self.dc('config','--quiet'))
        self.check('empty-installation',not self.command('compose-empty',self.dc('ps','-aq')).strip())
        self.check('no-host-published-ports',all(not s.get('ports') for s in rendered['services'].values()))
        self.check('isolated-private-networks',all(n.get('internal') is True for n in rendered['networks'].values()))
        self.check('runtime-does-not-mount-bootstrap-authority',all(not any(x['source'] in ('jwt-admin','temporal-migrator-password','visibility-migrator-password','root-password','restore-root-password') for x in rendered['services'][name].get('secrets',[])) for name in ('temporal','workflow-client','broker-client','evidence-client','restore-evidence-client','database-client')))
        (self.output/'compose.json').write_text(json.dumps(rendered,indent=2)+'\n')
        self.command('database-and-broker-start',self.dc('up','-d','--wait','--wait-timeout','160','postgres','rabbit'),timeout=200)
        self.command('schema-setup',self.dc('run','--rm','--no-deps','-T','schema'),timeout=180)
        self.admin('GRANT EXECUTE ON FUNCTION public.convert_ts(character varying) TO visibility_runtime;',database='temporal_visibility')
        self.probe('database-client','database')
        # Disable migrator login after setup and prove server runtime remains functional.
        self.admin('ALTER ROLE temporal_migrator NOLOGIN; ALTER ROLE visibility_migrator NOLOGIN;')
        self.check('migrators-disabled',self.admin("SELECT count(*) FROM pg_roles WHERE rolname IN ('temporal_migrator','visibility_migrator') AND rolcanlogin;").strip()==b'0')
        self.command('stateful-services-start',self.dc('up','-d','temporal','evidence','evidence-restore'))
        self.probe('workflow-admin','temporal-bootstrap')
        self.probe('evidence-admin','evidence-bootstrap')
        self.probe('restore-evidence-admin','evidence-bootstrap')
        self.command('evidence-policy-bootstrap',self.dc('run','--rm','--no-deps','-T','evidence-iam'))
        self.command('restore-policy-bootstrap',self.dc('run','--rm','--no-deps','-T','restore-evidence-iam'))
        self.probe('broker-client','broker-before')
        workflow=self.probe('workflow-client','temporal-before')
        capture=self.probe('evidence-client','evidence-before')
        self.probe('evidence-admin','evidence-admin-denial',capture)
        self.command('stop-dependencies',self.dc('stop','-t','10','rabbit','temporal','postgres','evidence'),timeout=70)
        self.probe('broker-client','broker-outage')
        self.probe('workflow-client','temporal-outage')
        self.probe('evidence-client','evidence-outage')
        self.command('restart-database-broker',self.dc('up','-d','--wait','--wait-timeout','160','postgres','rabbit'),timeout=200)
        self.command('restart-workflow-evidence',self.dc('up','-d','temporal','evidence'))
        self.probe('broker-client','broker-after')
        # Let membership finish through a bounded client readiness loop, not a fixed sleep.
        self.probe('workflow-client','temporal-after',workflow)
        capture=self.probe('evidence-client','evidence-capture',capture)
        self.report['capture']={k:v for k,v in capture.items() if k!='base64'}
        (self.output/'evidence-capture.json').write_text(json.dumps(capture,indent=2)+'\n')
        restore=self.probe('restore-evidence-client','evidence-restore',capture)
        self.probe('restore-evidence-admin','evidence-admin-denial',restore)
        self.command('restart-restored-evidence',self.dc('restart','evidence-restore'))
        self.probe('restore-evidence-client','evidence-after',restore)
        self.report['restored_evidence']=restore
        self.command('revoke-broker-principal',self.dc('exec','-T','rabbit','rabbitmqctl','delete_user','publisher'))
        self.probe('broker-client','broker-revoked')
        self.command('stop-revoked-broker',self.dc('stop','rabbit'))
        self.command('restart-revoked-broker',self.dc('up','-d','--wait','--wait-timeout','160','rabbit'),timeout=200)
        self.probe('broker-client','broker-revoked')
        self.command('revoke-evidence-principal',self.dc('run','--rm','--no-deps','-T','evidence-iam','revoke'))
        self.probe('evidence-client','evidence-revoked')
        self.command('restart-revoked-evidence',self.dc('restart','evidence'))
        self.probe('evidence-admin','evidence-ready')
        self.probe('evidence-client','evidence-revoked')
        jwks=self.runtime/'config/jwks.json';jwks.chmod(0o644);jwks.write_text('{"keys":[]}');jwks.chmod(0o444)
        # Restart proves removal of trust applies deterministically, without claiming hot revocation latency.
        self.command('reload-revoked-workflow-trust',self.dc('restart','temporal'))
        self.probe('workflow-client','temporal-revoked')
        self.report['workflow']=workflow
        self.report['limits']=['Single-node disposable Compose dependencies and synthetic identities; no operated adoption or availability claim.', 'Probe owns its clients; product contracts/outbox/inbox, shared Console sessions/cache and alert receipt remain separate.', 'Workflow issuer-key removal is tested on server restart; no hot revocation SLA is measured.', 'Evidence restore preserves pinned bytes and source identity metadata in a fresh store with a new version ID and equal-or-longer retention.', 'No native platform calls, promotion trust, gate acceptance, RPO or RTO claims.']
        self.report['result']='PASS';self.save()

    def cleanup(self):
        success=True
        if self.compose:
            try:
                self.command('runtime-state',self.dc('ps','--all','--format','json'),expected=None)
                containers=self.command('runtime-containers',self.dc('ps','-aq')).decode().split()
                for identifier in containers:
                    self.command('container-state',['docker','inspect','--format','{{json .State}}',identifier],expected=None)
                self.command('runtime-logs',self.dc('logs','--no-color','--tail','80'),expected=None)
                self.command('remove-owned-installation',self.dc('down','--volumes','--remove-orphans'),timeout=90)
                self.check('no-remaining-containers',not self.command('removed-containers',self.dc('ps','-aq')).strip())
                project=json.loads(self.compose.read_text())['name']
                for kind in ('volume','network'):
                    self.check('no-remaining-'+kind,not self.command('removed-'+kind,['docker',kind,'ls','-q','--filter','label=com.docker.compose.project='+project]).strip())
            except Exception as error:
                success=False;self.report['cleanup_error']=str(error)
            # Any accidental secret output fails before artifact upload; do not retain leaked bytes.
            values=[p.read_bytes().strip() for p in (self.runtime/'secrets').iterdir() if p.is_file() and (p.name.endswith('-password') or p.name.startswith('jwt-') or p.suffix=='.key')]
            contaminated=[]
            for p in self.output.iterdir():
                if p.is_file() and any(value and value in p.read_bytes() for value in values):
                    p.write_text('WITHHELD: generated credential appeared in output.\n');contaminated.append(p.name)
            if contaminated:
                success=False;self.report.update(result='FAIL',withheld_outputs=contaminated)
        self.report['cleanup_complete']=success
        if success: shutil.rmtree(self.runtime.parent)
        else: self.report['result']='FAIL'
        self.report['finished_at']=datetime.now(timezone.utc).isoformat();self.save()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source-revision',required=True)
    args=parser.parse_args()
    campaign=StatefulCampaign(args.workspace.resolve(),args.output.resolve(),args.source_revision)
    try: campaign.run()
    except Exception as error:
        campaign.report.update(result='FAIL',error=str(error));raise
    finally: campaign.cleanup()
    if campaign.report['result']!='PASS': raise RuntimeError('Campaign or cleanup failed')
    print(json.dumps({'result':'PASS','checks':len(campaign.report['checks'])}))


if __name__=='__main__':main()
