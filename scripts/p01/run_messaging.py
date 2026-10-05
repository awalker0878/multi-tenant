"""Measure service-owned P01 contracts, transactional delivery and crash recovery."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import uuid

from messaging.runtime import prepare
from run_local import digest
from run_stateful import StatefulCampaign


class MessagingCampaign(StatefulCampaign):
    def invoke(self, service, operation, *, expected=0, **data):
        raw=self.command(service+'-'+operation,self.dc('run','--rm','--no-deps','-T',service),data=json.dumps({'operation':operation,**data}).encode(),expected=expected,timeout=25)
        return json.loads(raw) if raw.strip() else None

    def record(self, event, expected=0, **overrides):
        data={'event':event,'payload':'synthetic-p01-fact','tenant':event['tenant_id'],'actor':event['actor_id'],**overrides}
        return self.invoke('catalogue','record',expected=expected,**data)

    def count(self, service, table):
        if table not in ('messaging_facts','messaging_outbox','messaging_inbox','messaging_projection'):
            raise ValueError('Unsupported witness table')
        return int(self.sql(service,'SELECT count(*) FROM app.'+table+';').strip())

    def consume(self, expected=0, operation='consume', tenants=('tenant_a',)):
        return self.invoke('planning',operation,tenants=list(tenants),expected=expected)

    def run(self):
        self.report['scope']='P01 Catalogue/Planning reference messaging; no product API, authority or native effects'
        self.check('exact-source',self.command('source-revision',['git','rev-parse','HEAD']).decode().strip()==self.revision)
        paths=['services/catalogue','services/planning','scripts/p01','contracts','tests/contracts','deploy','.github/workflows/p01-messaging.yml']
        self.check('clean-inputs',not self.command('source-clean',['git','status','--porcelain','--untracked-files=all','--',*paths]).strip())
        self.report['source_sha256']={str(p.relative_to(self.root)):digest(p.read_bytes()) for prefix in ('scripts/p01/messaging','contracts','tests/contracts') for p in (self.root/prefix).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        def build(name):
            target=self.output/'images'/name
            self.command(name+'-build',[sys.executable,str(self.root/'scripts/p01/run_images.py'),'--component',name,'--output',str(target),'--source-revision',self.revision],timeout=1200)
            return name,json.loads((target/'report.json').read_text())['image']['id']
        images=dict(build(name) for name in ('catalogue','planning'))
        images['rabbit']=json.loads((self.root/'deploy/dependencies/stateful/inputs.lock.json').read_text())['images']['rabbitmq']['reference']
        postgres=json.loads((self.root/'deploy/dependencies/inputs.lock.json').read_text())['images']['postgres']['reference']
        for name,ref in [('rabbit',images['rabbit']),('postgres',postgres)]:
            self.command(name+'-pull',['docker','pull','--platform','linux/amd64',ref],timeout=180)
        self.report['images']={**images,'postgres':postgres}
        self.compose=prepare(self.root,self.runtime,images,self.revision)
        rendered=json.loads(self.compose.read_text())
        self.check('no-host-ports',all(not x.get('ports') for x in rendered['services'].values()))
        self.check('private-networks',all(n['internal'] for n in rendered['networks'].values()))
        self.check('no-runtime-admin-secrets',all(not any('migrator' in s['source'] or s['source']=='postgres-password' for s in rendered['services'][n]['secrets']) for n in ('catalogue','planning')))
        (self.output/'compose.json').write_text(json.dumps(rendered,indent=2)+'\n')
        self.command('compose-valid',self.dc('config','--quiet'))
        self.check('empty-installation',not self.command('empty-installation',self.dc('ps','-aq')).strip())
        self.command('dependencies-ready',self.dc('up','-d','--wait','--wait-timeout','160','postgres','rabbit'),timeout=200)
        migration=(self.root/'deploy/dependencies/postgres/migrate.sql').read_text()
        for owner in ('catalogue','planning'):
            self.sql(owner,f'\\set owner {owner}_owner\n\\set runtime {owner}_runtime\n'+migration,identity='migrator')
            path=self.root/('services/catalogue/database/migrations/001_messaging.sql' if owner=='catalogue' else 'services/planning/migrations/001_messaging.sql')
            self.sql(owner,path.read_text(),identity='migrator')
            denied=self.sql(owner,'CREATE TABLE app.denied(id integer);',expected=None)
            # Exact permission result comes from the SQL subprocess, not a generic dependency failure.
            cmd=self.report['commands'][-1]
            error=(self.output/cmd['stderr']['path']).read_text()
            self.check(owner+'-ddl-denied',cmd['exit_code']!=0 and 'permission denied for schema app' in error)
        fixtures=json.loads((self.root/'tests/contracts/fixtures.json').read_text())
        event=fixtures[0]['value'];event['source_revision']=self.revision
        self.check('tenant-binding-denied',self.record(event,expected=2,tenant='tenant_b')['reason']=='fact_scope_or_digest_mismatch')
        self.check('actor-binding-denied',self.record(event,expected=2,actor='foreign')['reason']=='fact_scope_or_digest_mismatch')
        self.sql('catalogue','SET ROLE catalogue_owner; REVOKE INSERT ON app.messaging_outbox FROM catalogue_runtime;',identity='migrator')
        self.check('outbox-failure-rejected',self.record(event,expected=2)['result']=='rejected')
        self.check('outbox-failure-rolls-back-fact',self.count('catalogue','messaging_facts')==0 and self.count('catalogue','messaging_outbox')==0)
        self.sql('catalogue','SET ROLE catalogue_owner; GRANT INSERT ON app.messaging_outbox TO catalogue_runtime;',identity='migrator')
        self.check('fact-and-outbox-committed',self.record(event)['result']=='recorded' and self.count('catalogue','messaging_outbox')==1)
        self.check('command-retry-deduplicated',self.record(event)['result']=='duplicate' and self.count('catalogue','messaging_facts')==1)
        changed={**event,'correlation_id':str(uuid.uuid4())}
        self.check('same-id-changed-content-denied',self.record(changed,expected=2)['reason']=='idempotency_conflict')
        self.invoke('catalogue','crash-after-publish',expected=91)
        self.check('publish-crash-leaves-pending',self.sql('catalogue','SELECT count(*) FROM app.messaging_outbox WHERE published_at IS NULL;').strip()==b'1')
        result=self.consume(expected=91,operation='leave-unacked')
        self.check('consumer-commit-before-ack',result['result']=='projected' and self.count('planning','messaging_projection')==1)
        self.command('stop-durable-dependencies',self.dc('stop','-t','10','rabbit','postgres'),timeout=40)
        self.command('restart-durable-dependencies',self.dc('up','-d','--wait','--wait-timeout','160','postgres','rabbit'),timeout=200)
        self.check('relay-resumes-same-event',self.invoke('catalogue','dispatch')['result']=='published')
        self.check('redelivery-after-restart-deduplicated',self.consume()['result']=='duplicate')
        self.check('uncertain-publish-duplicate-deduplicated',self.consume()['result']=='duplicate')
        self.check('queue-drained',self.consume()['result']=='empty')
        self.check('one-logical-effect',self.count('planning','messaging_projection')==1 and self.count('planning','messaging_inbox')==1)
        second={**event,'event_id':str(uuid.uuid4()),'revision':'2'}
        self.record(second);self.invoke('catalogue','dispatch')
        self.sql('planning','SET ROLE planning_owner; REVOKE INSERT ON app.messaging_projection FROM planning_runtime;',identity='migrator')
        self.consume(expected=2)
        self.check('consumer-failure-rolls-back-inbox',self.count('planning','messaging_inbox')==1)
        self.sql('planning','SET ROLE planning_owner; GRANT INSERT ON app.messaging_projection TO planning_runtime;',identity='migrator')
        self.check('consumer-retry-after-repair',self.consume()['result']=='projected')
        foreign={**event,'event_id':str(uuid.uuid4()),'tenant_id':'tenant_b'}
        self.record(foreign);self.invoke('catalogue','dispatch')
        self.check('foreign-tenant-quarantined',self.consume()['result']=='quarantined')
        self.check('quarantine-receipt',self.consume(operation='deadletter')['result']=='quarantine_received')
        gap={**event,'event_id':str(uuid.uuid4()),'revision':'4'}
        self.record(gap);self.invoke('catalogue','dispatch')
        self.check('revision-gap-quarantined',self.consume()['result']=='quarantined')
        self.consume(operation='deadletter')
        self.check('denied-messages-have-no-effect',self.count('planning','messaging_inbox')==2 and self.count('planning','messaging_projection')==2)
        self.command('broker-outage',self.dc('stop','rabbit'))
        third={**event,'event_id':str(uuid.uuid4()),'record_id':'record_c'}
        self.record(third)
        self.check('broker-loss-keeps-pending',self.invoke('catalogue','dispatch',expected=2)['result']=='rejected')
        self.command('broker-recovery',self.dc('up','-d','--wait','--wait-timeout','160','rabbit'),timeout=200)
        self.check('broker-recovery-publishes',self.invoke('catalogue','dispatch')['result']=='published')
        self.check('broker-recovery-delivers',self.consume()['result']=='projected')
        self.command('revoke-publisher',self.dc('exec','-T','rabbit','rabbitmqctl','delete_user','catalogue'))
        fourth={**event,'event_id':str(uuid.uuid4()),'record_id':'record_d'};self.record(fourth)
        self.check('revoked-publisher-denied',self.invoke('catalogue','dispatch',expected=2)['result']=='rejected')
        self.report['event_ids']=[event['event_id'],second['event_id'],foreign['event_id'],gap['event_id'],third['event_id'],fourth['event_id']]
        self.report['limits']=['Reference fact only; no public API, delegated authorization or native effects.','Single-node quorum broker; no HA or operating acceptance.','No pruning or approval of production retry/retention windows.']
        self.report['result']='PASS';self.save()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-revision',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    c=MessagingCampaign(Path(__file__).resolve().parents[2],args.output.resolve(),args.source_revision)
    try:c.run()
    except Exception as e:c.report.update(result='FAIL',error=str(e));raise
    finally:c.cleanup()
    if c.report['result']!='PASS':raise RuntimeError('Messaging campaign or cleanup failed')
    print(json.dumps({'result':'PASS','checks':len(c.report['checks'])}))

if __name__=='__main__':main()
