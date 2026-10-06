"""Real pinned Temporal server with separate PostgreSQL schema identity, TLS and JWT."""
import importlib.util
import json
from pathlib import Path
import sys

class TemporalFixture:
    def __init__(self, root, private, run, redactions):
        sys.path.insert(0,str(root/'scripts/p01'))
        spec=importlib.util.spec_from_file_location('p06_stateful_runtime',root/'scripts/p01/stateful/runtime.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        locked=json.loads((root/'deploy/dependencies/stateful/inputs.lock.json').read_text())['images']
        images={k:locked[k]['reference'] for k in ['temporal','temporal_admin','rabbitmq']}
        images['postgres']='docker.io/library/postgres@sha256:9e73daeb439141c2b11eea2463f5f1a3b269fd90d897b41cddb7cb440f21aa5d'
        # Only these three services survive the subset; unused P01 image slots never start.
        images.update({k:images['temporal'] for k in ['probe','minio','mc']})
        self.path=module.prepare(root,private/'temporal',images)
        config=json.loads(self.path.read_text());config['services']={k:v for k,v in config['services'].items() if k in ['postgres','schema','temporal']}
        config['services']['temporal']['ports']=['127.0.0.1:17233:7233']
        config['networks']['workflow']={'internal':False} # Loopback-published TLS frontend is reached from the host campaign.
        self.path.chmod(0o600);self.path.write_text(json.dumps(config))
        self.run=run;self.command=['docker','compose','-f',str(self.path)]
        secrets=private/'temporal/secrets'
        for secret in secrets.glob('*-password'):
            redactions.append(secret.read_text().strip())
        for name in ['jwt-lifecycle','jwt-admin','jwt-foreign','jwt-expired','jwt-wrong-audience']:
            redactions.append((secrets/name).read_text().strip())
        self.environment={'TEMPORAL_TARGET':'127.0.0.1:17233','TEMPORAL_NAMESPACE':'lifecycle','TEMPORAL_SERVER_NAME':'temporal','TEMPORAL_CA_FILE':str(secrets/'ca.crt'),'TEMPORAL_CREDENTIAL_FILE':str(secrets/'jwt-lifecycle'),'P06_TEMPORAL_ADMIN_FILE':str(secrets/'jwt-admin')}
        self.images={k:images[k] for k in ['postgres','temporal','temporal_admin']}
    def start(self):
        run=self.run
        for name,reference in self.images.items():run(['docker','pull',reference],label='p06-pull-'+name)
        run([*self.command,'up','-d','--wait','postgres'],label='p06-temporal-postgres')
        run([*self.command,'run','--rm','schema'],label='p06-temporal-schema')
        run([*self.command,'up','-d','temporal'],label='p06-temporal-server')
    def restart(self):self.run([*self.command,'restart','temporal'],label='p06-temporal-restart')
    def close(self):
        self.run([*self.command,'logs','--no-color','temporal'],label='p06-temporal-server-runtime')
        self.run([*self.command,'down','--volumes','--remove-orphans'],label='p06-temporal-cleanup')
