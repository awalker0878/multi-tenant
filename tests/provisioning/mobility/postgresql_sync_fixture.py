"""Actual native-engine test connections, without live-worker commissioning."""
from contextlib import contextmanager
import uuid

import psycopg
from psycopg import sql

from provisioner.migration.postgresql_sync import FORMAT,PostgresqlSyncSelection,_PostgresqlEngine
from tests.provisioning.mobility.prepare_postgresql_sync import settings,native_admin,owner_role


class EngineSession:
    """Fixture-only wrapper around a real isolated PostgreSQL connection."""
    def __init__(self,dsn,role=None):
        self.connection=psycopg.connect(dsn,autocommit=True)
        role=role or self.connection.execute('SELECT current_user').fetchone()[0]
        self.connection.execute(sql.SQL('SET ROLE {}').format(sql.Identifier(role)))
        self.connection.execute("SET statement_timeout='5s'")
        self.connection.execute("SET lock_timeout='1s'")
    def execute(self,*arguments,**options):return self.connection.execute(*arguments,**options)
    @contextmanager
    def transaction(self):
        with self.connection.transaction():yield self
    def close(self):self.connection.close()


class NativeEngineFixture:
    def __init__(self):
        self.dsns,self.parsed=settings();self.tag=uuid.uuid4().hex[:16]
        self.schema='appsync_'+self.tag;self.stream='engine-'+self.tag
        self.source=EngineSession(self.dsns['SOURCE'],owner_role(self.parsed,'SOURCE'))
        self.target=EngineSession(self.dsns['TARGET'],owner_role(self.parsed,'TARGET'))
        self.fence=EngineSession(self.dsns['FENCE'],owner_role(self.parsed,'FENCE'))
        scope=dict(organizationId='org-engine',tenantId='tenant-engine',locationId='site-engine',
            endpointId='endpoint-engine',platformFamily='vmware',nativeScopeId='native-engine',
            securityDomainId='wsd-engine')
        target_scope=dict(scope,platformFamily='openstack',endpointId='target-engine',nativeScopeId='target-engine')
        endpoints={}
        for key,session in (('SOURCE',self.source),('TARGET',self.target)):
            system=session.execute('SELECT system_identifier::text FROM pg_control_system()').fetchone()[0]
            endpoints[key.lower()]=dict(nativeDatasetId='database-'+key.lower(),database=self.parsed[key]['dbname'],
                systemIdentifier=system,host='postgres.fixture',hostaddr='127.0.0.1',port=5432,
                caFile='/fixture/explicit-unused-engine-ca.pem',caDigest='a'*64,ownerRole=owner_role(self.parsed,key),
                readRole=owner_role(self.parsed,key+'_READER'))
        endpoints['source']['fenceOwnerRole']=owner_role(self.parsed,'FENCE')
        columns=[dict(name='id',typeOid=23,typeModifier=-1,key=True,notNull=True),
                 dict(name='body',typeOid=25,typeModifier=-1,key=False,notNull=False)]
        body=dict(format=FORMAT,datasetId='data-engine',memberId='member-engine',streamId=self.stream,
            targetRef='db-target-ref',consistencyGroupId='sql-consistency',
            source_scope=scope,target_scope=target_scope,**endpoints,publication='pub_'+self.tag,
            sourceGuest=dict(native_id='vm-source',native_uuid='11111111-1111-1111-1111-111111111111',machine_id='1'*32),
            targetGuest=dict(native_id='vm-target',native_uuid='22222222-2222-2222-2222-222222222222',machine_id='2'*32),
            subscription='sub_'+self.tag,slot='slot_'+self.tag,
            tables=[dict(schema=self.schema,name=name,columns=columns) for name in ('accounts','notes')],
            maxRows=1000,maxBytes=4*1024*1024,sourceWriterRoles=[self.parsed['WRITER']['user']],
            operations={side:dict(stepId='step-'+side,operationId='op-'+side) for side in ('source','target','fence')})
        self.selection=PostgresqlSyncSelection.from_record(body);self.body=body
        self.engine=_PostgresqlEngine(self.selection,self.source,self.target)
        with native_admin(self.dsns['SETUP'],self.parsed['SOURCE']['dbname']) as admin:
            admin.execute(sql.SQL('ALTER ROLE {} LOGIN').format(sql.Identifier(self.parsed['WRITER']['user'])))
            admin.execute('INSERT INTO hosting_sync.writer_fences(stream_id,dataset_id,selection_digest,fence_role,writer_roles,enabled,valid_until) VALUES(%s,%s,%s,%s,%s,true,clock_timestamp()+interval \'1 hour\')',
                (self.stream,body['datasetId'],self.selection.sha256,owner_role(self.parsed,'FENCE'),body['sourceWriterRoles']))
            admin.execute('INSERT INTO hosting_sync.source_streams(stream_id,dataset_id,selection_digest,read_role,publication_name,slot_name,max_rows,max_bytes,enabled,valid_until) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,true,clock_timestamp()+interval \'1 hour\')',
                (self.stream,body['datasetId'],self.selection.sha256,owner_role(self.parsed,'SOURCE_READER'),body['publication'],body['slot'],body['maxRows'],body['maxBytes']))
        with native_admin(self.dsns['SETUP'],self.parsed['TARGET']['dbname']) as admin:
            admin.execute('INSERT INTO hosting_sync.streams(stream_id,dataset_id,selection_digest,login_role,read_role,subscription_name,enabled,valid_until) VALUES(%s,%s,%s,%s,%s,%s,true,clock_timestamp()+interval \'1 hour\')',
                (self.stream,body['datasetId'],self.selection.sha256,owner_role(self.parsed,'TARGET'),owner_role(self.parsed,'TARGET_READER'),body['subscription']))
        for session in (self.source,self.target):
            session.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(self.schema)))
            for table in body['tables']:
                session.execute(sql.SQL('CREATE TABLE {} (id integer PRIMARY KEY,body text)').format(sql.Identifier(self.schema,table['name'])))
        for key,session in (('SOURCE_READER',self.source),('TARGET_READER',self.target)):
            session.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(self.schema),sql.Identifier(owner_role(self.parsed,key))))
            session.execute(sql.SQL('GRANT SELECT ON ALL TABLES IN SCHEMA {} TO {}').format(sql.Identifier(self.schema),sql.Identifier(owner_role(self.parsed,key))))
        self.source.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(self.schema),sql.Identifier(self.parsed['WRITER']['user'])))
        self.source.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE,TRUNCATE ON ALL TABLES IN SCHEMA {} TO {}').format(sql.Identifier(self.schema),sql.Identifier(self.parsed['WRITER']['user'])))
        self.writer=EngineSession(self.dsns['WRITER'])

    def insert_initial(self):
        self.writer.execute(sql.SQL('INSERT INTO {} VALUES (%s,%s),(%s,%s)').format(sql.Identifier(self.schema,'accounts')),
            (1,'initial snow ☃',2,None))
        self.writer.execute(sql.SQL('INSERT INTO {} VALUES (%s,%s)').format(sql.Identifier(self.schema,'notes')),(1,'note'))

    def close(self):
        self.writer.close();self.fence.close()
        try:
            if self.target.execute('SELECT 1 FROM pg_subscription WHERE subname=%s',(self.body['subscription'],)).fetchone():
                self.target.execute(sql.SQL('ALTER SUBSCRIPTION {} SET (slot_name=NONE)').format(sql.Identifier(self.body['subscription'])))
            self.target.execute(sql.SQL('DROP SUBSCRIPTION IF EXISTS {}').format(sql.Identifier(self.body['subscription'])))
            self.source.execute('SELECT pg_drop_replication_slot(slot_name) FROM pg_replication_slots WHERE slot_name=%s',(self.body['slot'],))
            self.source.execute(sql.SQL('DROP PUBLICATION IF EXISTS {}').format(sql.Identifier(self.body['publication'])))
            for session in (self.source,self.target):session.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(self.schema)))
        finally:
            self.source.close();self.target.close()

    def source_write(self,query,*arguments):
        return self.writer.execute(sql.SQL(query).format(sql.Identifier(self.schema,'accounts')),arguments or None)
