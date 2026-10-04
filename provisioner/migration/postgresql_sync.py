"""Selected PostgreSQL17 application sync with owned bounded native SQL effects.

The subscription remains disabled. Actual pgoutput is peeked, each whole source
transaction is committed with the native target journal, and only then is the
source slot acknowledged. No RAM migration or background writer is implied.
"""
from dataclasses import dataclass
from contextlib import contextmanager
import hashlib
import ipaddress
from importlib import resources
from pathlib import Path
import re

from psycopg import sql

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence import canonical_record_digest
from provisioner.execution import execution_journal
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import encoded,require
from .postgresql_pgoutput import SUPPORTED_TYPES,UNCHANGED,decode_transactions,lsn_number

FORMAT='hosting-postgresql17-sync-selection/1'
_IDENTIFIER=re.compile('[a-z][a-z0-9_]{0,62}')
_ID=re.compile('[A-Za-z0-9][A-Za-z0-9._:-]{0,127}')
_SHA=re.compile('[0-9a-f]{64}')
# Public metadata only: never a Vault/source credential. PostgreSQL17 requires
# a nonempty password even for connect=false under a nonsuperuser owner. The
# pinned loopback port and empty TLS trust file cannot reach/authenticate a
# source, including if someone enables this originally disabled subscription.
DISABLED_SUBSCRIPTION_CONNECTION=('hostaddr=127.0.0.1 port=1 '
    'dbname=hosting_disabled_subscription user=hosting_disabled_subscription '
    'password=hosting_disabled_subscription sslmode=verify-full '
    'sslrootcert=/dev/null passfile=/dev/null connect_timeout=1')


def _identifier(value):return isinstance(value,str) and _IDENTIFIER.fullmatch(value) is not None


@dataclass(frozen=True)
class PostgresqlSyncSelection:
    canonical:bytes

    def __post_init__(self):
        require(isinstance(self.canonical,bytes) and len(self.canonical)<=65536,'Bounded original database sync selection required')
        body=strict_loads(self.canonical)
        require(type(body) is dict and set(body)=={'format','datasetId','memberId','streamId','targetRef','consistencyGroupId','source_scope','target_scope',
            'source','target','sourceGuest','targetGuest','publication','subscription','slot','tables','maxRows','maxBytes','operations','sourceWriterRoles'}
            and body['format']==FORMAT and encoded(body)==self.canonical,'Exact canonical PostgreSQL17 sync descriptor required')
        require(all(isinstance(body[key],str) and _ID.fullmatch(body[key]) for key in ('datasetId','memberId','streamId','targetRef','consistencyGroupId')),
                'Exact application member, dataset and stream identities required')
        source,target=(PlanScope.from_record(body[side+'_scope']) for side in ('source','target'))
        require((source.organization_id,source.tenant_id)==(target.organization_id,target.tenant_id),
                'Database sync cannot cross tenants')
        for side in ('source','target'):
            guest=body[side+'Guest']
            require(type(guest) is dict and set(guest)=={'native_id','native_uuid','machine_id'}
                    and isinstance(guest['native_id'],str) and _ID.fullmatch(guest['native_id'])
                    and isinstance(guest['native_uuid'],str) and re.fullmatch('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',guest['native_uuid'])
                    and isinstance(guest['machine_id'],str) and re.fullmatch('[0-9a-f]{32}',guest['machine_id']),
                    'The actual approved source and target guest hosting the SQL engine must be bound')
            endpoint=body[side]
            require(type(endpoint) is dict and set(endpoint)=={'nativeDatasetId','database','systemIdentifier','host','hostaddr',
                'port','caFile','caDigest','ownerRole','readRole'}|({'fenceOwnerRole'} if side=='source' else set())
                and isinstance(endpoint['nativeDatasetId'],str) and _ID.fullmatch(endpoint['nativeDatasetId'])
                and _identifier(endpoint['database']) and _identifier(endpoint['ownerRole'])
                and _identifier(endpoint['readRole']) and endpoint['readRole']!=endpoint['ownerRole']
                and isinstance(endpoint['systemIdentifier'],str) and re.fullmatch('[1-9][0-9]{0,19}',endpoint['systemIdentifier'])
                and isinstance(endpoint['host'],str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9.-]{0,252}',endpoint['host'])
                and type(endpoint['port']) is int and 1<=endpoint['port']<=65535
                and isinstance(endpoint['caFile'],str) and Path(endpoint['caFile']).is_absolute()
                and str(Path(endpoint['caFile']))==endpoint['caFile']
                and '..' not in Path(endpoint['caFile']).parts
                and isinstance(endpoint['caDigest'],str) and _SHA.fullmatch(endpoint['caDigest']),
                'An exact protected native database endpoint is required')
            address=ipaddress.ip_address(endpoint['hostaddr'])
            require(str(address)==endpoint['hostaddr'] and not address.is_unspecified and not address.is_multicast,
                    'Native database address must be pinned')
        require(all(_identifier(body[key]) for key in ('publication','subscription','slot'))
                and body['slot']==body['slot'].lower(),'Exact fixed publication, subscription and slot required')
        require(type(body['maxRows']) is int and 1<=body['maxRows']<=1000
                and type(body['maxBytes']) is int and 1<=body['maxBytes']<=4*1024*1024,
                'Finite application snapshot and transaction ceilings required')
        tables=body['tables'];require(isinstance(tables,list) and 1<=len(tables)<=16,'One to sixteen selected ordinary tables required')
        seen=set()
        for table in tables:
            require(type(table) is dict and set(table)=={'schema','name','columns'} and _identifier(table['schema'])
                    and not table['schema'].startswith(('pg_','hosting_')) and table['schema']!='information_schema'
                    and _identifier(table['name']) and (table['schema'],table['name']) not in seen,
                    'Exact nonoverlapping application tables required')
            seen.add((table['schema'],table['name']));columns=table['columns']
            require(isinstance(columns,list) and 1<=len(columns)<=64,'Bounded selected table columns required')
            names=set()
            for column in columns:
                require(type(column) is dict and set(column)=={'name','typeOid','typeModifier','key','notNull'}
                        and _identifier(column['name']) and column['name'] not in names
                        and type(column['typeOid']) is int and column['typeOid'] in SUPPORTED_TYPES
                        and type(column['typeModifier']) is int and column['typeModifier']>=-1
                        and type(column['key']) is bool and type(column['notNull']) is bool
                        and (not column['key'] or column['notNull']),'Selected builtin types and nonnull primary keys required')
                names.add(column['name'])
            require(any(column['key'] for column in columns),'Ordinary primary-key replica identity required')
        require(_identifier(body['source']['fenceOwnerRole']) and len({body['source'][key] for key in ('fenceOwnerRole','ownerRole','readRole')})==3
                and isinstance(body['sourceWriterRoles'],list) and 1<=len(body['sourceWriterRoles'])<=16
                and all(_identifier(value) and value not in (body['source']['ownerRole'],body['source']['fenceOwnerRole'],body['source']['readRole']) for value in body['sourceWriterRoles'])
                and len(set(body['sourceWriterRoles']))==len(body['sourceWriterRoles']),'Separate exact database writer fence and application roles required')
        require(type(body['operations']) is dict and set(body['operations'])=={'source','target','fence'},'Separate exact source/target/fence worker operations required')
        for row in body['operations'].values():
            require(type(row) is dict and set(row)=={'stepId','operationId'}
                    and all(isinstance(value,str) and _ID.fullmatch(value) for value in row.values()),'Exact original database step and operation required')
        require(all(len({row[key] for row in body['operations'].values()})==3 for key in ('stepId','operationId')),
                'Separate immutable original SQL step and operation identities required')

    @classmethod
    def from_record(cls,body):return cls(encoded(body))
    def to_dict(self):return strict_loads(self.canonical)
    @property
    def sha256(self):return canonical_record_digest(self.to_dict())


def _table(row):return sql.Identifier(row['schema'],row['name'])


class _PostgresqlEngine:
    """Fixed native SQL implementation; installed callers use the typed runner."""
    def __init__(self,selection,source,target):
        require(isinstance(selection,PostgresqlSyncSelection),'An exact database selection is required')
        self.selection=selection;self.body=selection.to_dict();self.source=source;self.target=target;self.generations=None

    def retain_generations(self,generations):
        require(type(generations) is dict and set(generations)=={'publication','subscription','sourceTables','targetTables'}
                and all(type(generations[key]) is int and generations[key]>0 for key in ('publication','subscription'))
                and all(type(generations[key]) is dict and set(generations[key])=={
                    table['schema']+'.'+table['name'] for table in self.body['tables']}
                    and all(type(value) is int and value>0 for value in generations[key].values())
                    for key in ('sourceTables','targetTables')),'Exact originally observed native SQL object generations required')
        self.generations=strict_loads(encoded(generations))

    def validate(self,*,sides=('source','target')):
        require(sides in (('source','target'),('source',)),'The fixed selected native schema reader changed')
        for side,session in ((side,getattr(self,side)) for side in sides):
            endpoint=self.body[side]
            self.validate_helpers(session)
            native_identity=session.execute('SELECT current_database(),current_setting(%s),system_identifier::text FROM pg_control_system()',
                ('server_version_num',)).fetchone()
            require(native_identity is not None and (native_identity[0],native_identity[2])==
                    (endpoint['database'],endpoint['systemIdentifier']),'Native database system identity changed')
            version=int(native_identity[1])
            require(170000<=version<180000,'Only separately selected PostgreSQL17 is implemented')
            require(session.execute("SELECT current_setting('server_encoding')").fetchone()==('UTF8',),'Selected UTF8 database required')
            for table in self.body['tables']:
                row=session.execute('SELECT c.oid,c.relkind,c.relpersistence,c.relreplident,c.relrowsecurity,c.relforcerowsecurity,pg_get_userbyid(c.relowner) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relname=%s',
                    (table['schema'],table['name'])).fetchone()
                require(row is not None and row[1:]==('r','p','d',False,False,endpoint['ownerRole']),
                        'Selected tables must be ordinary permanent owned primary-key tables without RLS')
                if self.generations is not None:
                    require(row[0]==self.generations[side+'Tables'][table['schema']+'.'+table['name']],
                            'The original native application table was replaced')
                native=session.execute('SELECT a.attname,a.atttypid,a.atttypmod,a.attnotnull,a.attidentity,a.attgenerated,a.atthasdef,coalesce(a.attnum=ANY(i.indkey),false) FROM pg_attribute a LEFT JOIN pg_index i ON i.indrelid=a.attrelid AND i.indisprimary WHERE a.attrelid=%s AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum',(row[0],)).fetchall()
                actual=[{'name':value[0],'typeOid':value[1],'typeModifier':value[2],'notNull':value[3],'key':value[7]} for value in native]
                require(actual==table['columns'] and all(value[4:7]==('','',False) for value in native),
                        'Source/target schema differs; sequences, defaults and generated values are excluded')
                require(session.execute("SELECT (SELECT count(*) FROM pg_trigger WHERE tgrelid=%s),(SELECT count(*) FROM pg_constraint WHERE conrelid=%s AND contype<>'p'),(SELECT count(*) FROM pg_index WHERE indrelid=%s AND NOT indisprimary)",
                    (row[0],row[0],row[0])).fetchone()==(0,0,0),'Triggers, foreign/check/secondary constraints or expression indexes are excluded')
            schemas=list({table['schema'] for table in self.body['tables']})
            unsupported=session.execute("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=ANY(%s) AND c.relkind IN ('S','p','f','v','m')",(schemas,)).fetchone()[0]
            require(unsupported==0,'Selected schemas contain unsupported sequences, partitions, views or foreign tables')
            require(session.execute('SELECT count(*) FROM pg_largeobject_metadata').fetchone()==(0,),'Large objects are excluded from this selected database method')
            require(session.execute('SELECT count(*) FROM pg_prepared_xacts WHERE database=current_database()').fetchone()==(0,),
                    'Prepared transactions must be independently contained')
        require(self.source.execute("SELECT current_setting('wal_level')").fetchone()==('logical',),'Source must commission wal_level=logical')

    def validate_helpers(self,session):
        """Read actual fixed installed definitions, never an asserted revision."""
        packaged=resources.files('provisioner.controlplane.persistence').joinpath(
            'migrations/0033_postgresql_sync_journal.sql').read_text(encoding='utf-8')
        bodies={name:body for name,body in re.findall(
            r'CREATE FUNCTION hosting_sync\.([a-z_]+)\([^;]*?\).*?AS \$\$(.*?)\$\$;',packaged,re.DOTALL)}
        signatures={'immutable':'','current_fence':'text,text','fence_application_writers':'text,text',
            'inspect_writer_fence':'text,text','current_stream':'text','record_commit':'text,text,text,text,text',
            'inspect_commit':'text,text','inspect_subscription':'text','peek_source':'text,text','inspect_directory':'text,text'}
        require(set(bodies)==set(signatures),'The packaged original native SQL helper set changed')
        owner=session.execute("SELECT n.nspowner,r.rolcanlogin,r.rolsuper,r.rolbypassrls,EXISTS(SELECT 1 FROM aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner))) a WHERE a.grantee=0) FROM pg_namespace n JOIN pg_roles r ON r.oid=n.nspowner WHERE n.nspname='hosting_sync'").fetchone()
        require(owner is not None and owner[1:]==(False,False,False,False),
                'The fixed native helper must retain its private nonlogin nonadministrator owner')
        require(session.execute("SELECT count(*) FROM pg_roles WHERE rolcanlogin AND NOT rolsuper AND pg_has_role(oid,%s,'SET')",
            (owner[0],)).fetchone()==(0,),'A native login may assume the privileged helper owner')
        for name,arguments in signatures.items():
            native=session.execute("SELECT p.prosrc,p.prosecdef,p.provolatile,p.proparallel,p.proleakproof,p.proconfig,l.lanname,p.proowner,EXISTS(SELECT 1 FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a WHERE a.grantee=0) FROM pg_proc p JOIN pg_language l ON l.oid=p.prolang WHERE p.oid=to_regprocedure(%s)",
                ('hosting_sync.'+name+'('+arguments+')',)).fetchone()
            require(native is not None and native[:5]==(bodies[name],name!='immutable','v','u',False)
                    and native[6:]==('plpgsql',owner[0],False) and isinstance(native[5],list) and len(native[5])==1
                    and native[5][0].startswith('search_path=')
                    and [part.strip() for part in native[5][0].partition('=')[2].split(',')]==['pg_catalog','hosting_sync'],
                    'The actual installed native SQL helper definition, ownership or exposure changed')
        for name in ('streams','commits','writer_fences','source_streams'):
            require(session.execute('SELECT relkind,relpersistence,relowner,relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid=to_regclass(%s)',
                ('hosting_sync.'+name,)).fetchone()==('r','p',owner[0],True,True),
                    'The private original native SQL custody table changed ownership or row security')
            require(session.execute("SELECT count(*) FROM pg_trigger WHERE tgrelid=to_regclass(%s) AND tgfoid='hosting_sync.immutable()'::regprocedure AND tgtype=27 AND tgenabled='O'",
                ('hosting_sync.'+name,)).fetchone()==(1,),'The original native SQL custody immutability trigger changed')

    def publication(self):
        body=self.body
        require(self.source.execute('SELECT count(*) FROM pg_publication WHERE pubname=%s',(body['publication'],)).fetchone()==(0,),
                'Original publication already exists; independently reconcile it')
        self.source.execute(sql.SQL("CREATE PUBLICATION {} FOR TABLE {} WITH (publish='insert,update,delete,truncate',publish_via_partition_root=false)").format(
            sql.Identifier(body['publication']),sql.SQL(',').join(_table(table) for table in body['tables'])))

    def observe_publication(self):
        body=self.body
        require(self.generations is not None and self.source.execute('SELECT oid FROM pg_publication WHERE pubname=%s',
            (body['publication'],)).fetchone()==(self.generations['publication'],),'The original native publication was replaced')
        require(self.source.execute('SELECT puballtables,pubinsert,pubupdate,pubdelete,pubtruncate,pubviaroot FROM pg_publication WHERE pubname=%s',
            (body['publication'],)).fetchone()==(False,True,True,True,True,False),'Original exact publication options changed')
        native=self.source.execute('SELECT n.nspname,c.relname,p.prqual IS NULL,p.prattrs IS NULL FROM pg_publication_rel p JOIN pg_publication b ON b.oid=p.prpubid JOIN pg_class c ON c.oid=p.prrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE b.pubname=%s ORDER BY n.nspname,c.relname',
            (body['publication'],)).fetchall()
        require(native==sorted((table['schema'],table['name'],True,True) for table in body['tables']),
                'Original publication table set, filter or column list changed')

    @contextmanager
    def locked_source(self):
        with self.source.transaction():
            self.source.execute(sql.SQL('LOCK TABLE {} IN SHARE MODE').format(sql.SQL(',').join(_table(table) for table in self.body['tables'])))
            yield

    def rows(self,session):
        rows=[];size=0;count=0
        for table in self.body['tables']:
            identifiers=[sql.Identifier(column['name']) for column in table['columns']]
            columns=sql.SQL(',').join(sql.SQL('{}::text').format(value) for value in identifiers)
            sizes=sql.SQL('+').join(sql.SQL('coalesce(octet_length({}),0)').format(value) for value in identifiers)
            bounded=sql.SQL('coalesce(sum({}) OVER(),0)<={}').format(sizes,sql.Literal(self.body['maxBytes']))
            values=sql.SQL(',').join(sql.SQL('CASE WHEN {} THEN {} ELSE NULL END').format(bounded,value) for value in identifiers)
            found=session.execute(sql.SQL('WITH selected AS (SELECT {} FROM {} LIMIT {}) SELECT {},{} FROM selected').format(
                columns,_table(table),sql.Literal(self.body['maxRows']+1),bounded,values)).fetchall()
            require(all(value[0] is True for value in found),'Selected snapshot exceeds its native wire byte ceiling')
            found=[value[1:] for value in found]
            require(all(value is None or len(value.encode('utf-8'))<=1024*1024 for row in found for value in row),
                    'A selected SQL field exceeds the fixed one MiB pgoutput decoder ceiling')
            count+=len(found);require(count<=self.body['maxRows'],'Selected snapshot exceeds its row ceiling')
            values=sorted([list(value) for value in found],key=encoded);size+=len(encoded(values))
            require(size<=self.body['maxBytes'],'Selected snapshot exceeds its byte ceiling')
            rows.append({'schema':table['schema'],'table':table['name'],'rows':values})
        return rows

    def initial_snapshot(self):
        self.validate();self.publication()
        with self.locked_source():
            require(self.source.execute('SELECT count(*) FROM pg_replication_slots WHERE slot_name=%s',(self.body['slot'],)).fetchone()==(0,),
                    'Original slot already exists; no snapshot restart')
            slot,point=self.source.execute("SELECT slot_name,lsn::text FROM pg_create_logical_replication_slot(%s,'pgoutput',false,false,false)",(self.body['slot'],)).fetchone()
            require(slot==self.body['slot'],'Original slot identity changed');lsn_number(point)
            source=self.rows(self.source)
            with self.target.transaction():
                require(all(not table['rows'] for table in self.rows(self.target)),'Initial target must be independently empty')
                for table,contents in zip(self.body['tables'],source):
                    for values in contents['rows']:self._insert(table,values)
                sha=digest_snapshot(source)
                self.target.execute('SELECT hosting_sync.record_commit(%s,%s,%s,%s,%s)',
                    (self.body['streamId'],point,sha,self.selection.sha256,'INITIAL'))
            # Fixed disabled metadata subscription carries no source credential,
            # opens no native connection, and creates no apply worker.
            self.target.execute(sql.SQL("CREATE SUBSCRIPTION {} CONNECTION {} PUBLICATION {} WITH (connect=false,enabled=false,create_slot=false,copy_data=false,slot_name={},binary=false,streaming='off',two_phase=false,disable_on_error=true,password_required=true,run_as_owner=false,origin='none',failover=false)").format(
                sql.Identifier(self.body['subscription']),sql.Literal(DISABLED_SUBSCRIPTION_CONNECTION),
                sql.Identifier(self.body['publication']),sql.Literal(self.body['slot'])))
            generations={'publication':self.source.execute('SELECT oid FROM pg_publication WHERE pubname=%s',(self.body['publication'],)).fetchone()[0],
                'subscription':self.target.execute('SELECT oid FROM pg_subscription WHERE subname=%s',(self.body['subscription'],)).fetchone()[0]}
            for side,session in (('source',self.source),('target',self.target)):
                generations[side+'Tables']={table['schema']+'.'+table['name']:session.execute(
                    'SELECT %s::regclass::oid',(table['schema']+'.'+table['name'],)).fetchone()[0] for table in self.body['tables']}
            self.retain_generations(generations)
            return {'status':'INITIAL_SNAPSHOT_COMMITTED','sourcePosition':point,'snapshotDigest':sha,
                'rowCount':sum(len(table['rows']) for table in source),'backgroundApplyEnabled':False,'nativeGenerations':generations}

    def observe_stream(self):
        self.validate();self.observe_publication()
        confirmed=self.observe_source_slot()
        sub=self.target.execute('SELECT hosting_sync.inspect_subscription(%s)',(self.body['streamId'],)).fetchone()[0]
        require(sub==[False,self.body['slot'],[self.body['publication']],False,'f','d',True,True,False,'none',False,'0/0',True,self.body['target']['ownerRole'],self.generations['subscription']],
                'Original subscription was enabled, skipped, streamed or replaced')
        require(self.target.execute('SELECT count(pid) FROM pg_stat_subscription WHERE subid=%s',
            (self.generations['subscription'],)).fetchone()==(0,),
                'An original subscription worker remains active outside command authority')
        return confirmed

    def observe_source_slot(self):
        slot=self.source.execute('SELECT plugin,slot_type,database,temporary,active,wal_status,invalidation_reason,two_phase,failover,synced,confirmed_flush_lsn::text FROM pg_replication_slots WHERE slot_name=%s',
            (self.body['slot'],)).fetchone()
        require(slot is not None and slot[:5]==('pgoutput','logical',self.body['source']['database'],False,False)
                and slot[5] in ('reserved','extended') and slot[6:10]==(None,False,False,False),
                'Original source slot is unavailable, lost, active elsewhere or changed')
        return slot[-1]

    def capture(self):
        confirmed=self.observe_stream()
        if callable(getattr(self.source,'peek_selected',None)):
            rows=self.source.peek_selected(self.selection)
        else:rows=self.source.execute("SELECT lsn::text,xid,CASE WHEN sum(octet_length(data)) OVER()<=%s THEN data ELSE NULL END FROM (SELECT * FROM pg_logical_slot_peek_binary_changes(%s,NULL,%s,'proto_version','1','publication_names',%s,'binary','false','messages','false','streaming','false','two_phase','false') LIMIT %s) bounded",
            (self.body['maxBytes'],self.body['slot'],self.body['maxRows'],self.body['publication'],self.body['maxRows']*4+65)).fetchall()
        require(all(row[2] is not None for row in rows),'Original pgoutput exceeds its native wire byte ceiling')
        transactions=decode_transactions(rows,self.body['tables'],max_changes=self.body['maxRows'],max_bytes=self.body['maxBytes'])
        require(all(lsn_number(tx.commit_lsn)>lsn_number(confirmed) for tx in transactions),'Original stream position regressed')
        return transactions

    def _insert(self,table,values):
        result=self.target.execute(sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(_table(table),
            sql.SQL(',').join(sql.Identifier(column['name']) for column in table['columns']),
            sql.SQL(',').join(sql.Placeholder() for _ in values)),values)
        require(result.rowcount==1,'Target insert outcome differs from original source')

    def apply(self,transaction):
        known=self.target.execute('SELECT hosting_sync.inspect_commit(%s,%s)',(self.body['streamId'],transaction.end_lsn)).fetchone()[0]
        require(known is None,'Original source transaction already has target state; independent reconciliation required')
        tables={(row['schema'],row['name']):row for row in self.body['tables']}
        with self.target.transaction():
            for operation in transaction.operations:
                if operation['kind']=='T':
                    self.target.execute(sql.SQL('TRUNCATE TABLE {}').format(sql.SQL(',').join(sql.Identifier(*pair) for pair in operation['tables'])));continue
                table=tables[operation['schema'],operation['table']];columns=table['columns']
                if operation['kind']=='I':self._insert(table,operation['new']);continue
                old=operation['old'] if operation['old'] is not None else operation['new']
                keys=[index for index,column in enumerate(columns) if column['key']]
                condition=sql.SQL(' AND ').join(sql.SQL('{}={}').format(sql.Identifier(columns[index]['name']),sql.Placeholder()) for index in keys)
                parameters=[old[index] for index in keys]
                if operation['kind']=='D':query=sql.SQL('DELETE FROM {} WHERE {}').format(_table(table),condition)
                else:
                    changed=[index for index,value in enumerate(operation['new']) if value!=UNCHANGED]
                    query=sql.SQL('UPDATE {} SET {} WHERE {}').format(_table(table),sql.SQL(',').join(
                        sql.SQL('{}={}').format(sql.Identifier(columns[index]['name']),sql.Placeholder()) for index in changed),condition)
                    parameters=[operation['new'][index] for index in changed]+parameters
                require(self.target.execute(query,parameters).rowcount==1,'Target diverged from the exact source primary key')
            self.target.execute('SELECT hosting_sync.record_commit(%s,%s,%s,%s,%s)',
                (self.body['streamId'],transaction.end_lsn,transaction.digest,self.selection.sha256,'INCREMENTAL'))
        return {'status':'SOURCE_TRANSACTION_COMMITTED','commitPosition':transaction.commit_lsn,
                'endPosition':transaction.end_lsn,'transactionDigest':transaction.digest,'changes':len(transaction.operations)}

    def acknowledge(self,transaction):
        known=self.target.execute('SELECT hosting_sync.inspect_commit(%s,%s)',(self.body['streamId'],transaction.end_lsn)).fetchone()[0]
        require(known is not None and (known['transactionDigest'],known['selectionDigest'],known['kind'])==
                (transaction.digest,self.selection.sha256,'INCREMENTAL'),'Exact native target commit must precede source acknowledgement')
        point=self.source.execute('SELECT end_lsn::text FROM pg_replication_slot_advance(%s,%s::pg_lsn)',
            (self.body['slot'],transaction.end_lsn)).fetchone()[0]
        require(lsn_number(point)==lsn_number(transaction.end_lsn),'Source acknowledgement outcome differs; do not replay')
        return point

    def lag(self):
        confirmed=self.observe_stream()
        point,difference=self.source.execute('SELECT pg_current_wal_flush_lsn()::text,pg_wal_lsn_diff(pg_current_wal_flush_lsn(),%s::pg_lsn)',
            (confirmed,)).fetchone()
        require(difference>=0,'Original source WAL position regressed')
        return {'confirmedSourcePosition':confirmed,'sourceWalFlushPosition':point,
                'retainedWalBytes':int(difference),'globalWalBytesIncludeUnpublishedWork':True}

    def writer_fence_observation(self):
        roles=self.body['sourceWriterRoles']
        native=self.source.execute('SELECT rolname,rolcanlogin,rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,rolreplication FROM pg_roles WHERE rolname=ANY(%s) ORDER BY rolname',
            (roles,)).fetchall()
        require(native==sorted((role,False,False,False,False,False,False) for role in roles),
                'The selected original application writer login was restored or widened')
        require(self.source.execute("SELECT count(*) FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.roleid JOIN pg_roles u ON u.oid=m.member WHERE u.rolname=ANY(%s) OR (r.rolname=ANY(%s) AND NOT(m.member=(SELECT proowner FROM pg_proc WHERE oid='hosting_sync.fence_application_writers(text,text)'::regprocedure) AND m.admin_option AND NOT m.inherit_option AND NOT m.set_option))",
            (roles,roles)).fetchone()==(0,),'Original application writer authority was delegated after fencing')
        require(self.source.execute('SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND usename=ANY(%s)',
            (roles,)).fetchone()==(0,),'Original application writer sessions remain active')
        require(self.source.execute('SELECT count(*) FROM pg_prepared_xacts WHERE database=current_database()').fetchone()==(0,),
                'Prepared database transactions are not contained')
        return {'state':'SELECTED_APPLICATION_WRITERS_FENCED','writerRoles':roles,
                'applicationLoginAllowed':False,'activeApplicationSessions':0,'preparedTransactions':0,
                'databaseRunning':True,'datasetId':self.body['datasetId'],'selectionDigest':self.selection.sha256}

    def compare_locked(self):
        self.observe_stream()
        with self.locked_source():
            pending=self.capture()
            require(not pending,'Final selected source transactions remain unapplied')
            source=self.rows(self.source);target=self.rows(self.target)
            require(source==target,'Final application table values diverged')
            lag=self.lag()
            commit=self.target.execute('SELECT hosting_sync.inspect_commit(%s,%s)',
                (self.body['streamId'],lag['confirmedSourcePosition'])).fetchone()[0]
            require(commit is not None and commit['selectionDigest']==self.selection.sha256
                    and commit['kind'] in {'INITIAL','INCREMENTAL'},'The original acknowledged source position has no native target commit')
            return {'status':'LOCKED_SELECTED_TABLES_EQUAL',**lag,'snapshotDigest':digest_snapshot(source),
                    'rowCount':sum(len(table['rows']) for table in source),'pendingSelectedTransactions':0,
                    'sourcePersistentFenceVerified':False,'nativeGenerations':self.generations,
                    'targetCommitTransactionDigest':commit['transactionDigest'],'targetCommitKind':commit['kind']}


def digest_snapshot(rows):return hashlib.sha256(encoded(rows)).hexdigest()


class PostgresqlSyncRunner:
    def __init__(self,selection,source,target,*,ledger,evidence,native_readback=None):
        from .postgresql_authority import PostgresqlSession
        from .lifecycle_evidence import ApplicationEvidenceReader
        require(isinstance(selection,PostgresqlSyncSelection) and isinstance(source,PostgresqlSession)
                and isinstance(target,PostgresqlSession) and isinstance(evidence,ApplicationEvidenceReader)
                and source.authority.descriptor==target.authority.descriptor==selection
                and (source.authority.side,target.authority.side)==('source','target')
                and source.authority.admitted==target.authority.admitted,
                'Actual original SQL workers and independent native evidence owner required')
        self.selection=selection;self.source=source;self.target=target;self.ledger=ledger;self.evidence=evidence
        self.engine=_PostgresqlEngine(selection,source,target)
        body=selection.to_dict();scope={'job':source.authority.admitted.job_id,'dataset':body['datasetId'],'selection':selection.sha256}
        with execution_journal.locked(ledger,scope) as log:
            if len(log.events)>=2 and log.events[0]['kind']=='DATABASE_SYNC_STARTED' and log.events[0]['data']['stage']=='INITIAL' and log.events[1]['kind']=='DATABASE_SYNC_COMPLETED':
                self.engine.retain_generations(log.events[1]['data']['result']['nativeGenerations'])
        from .postgresql_readback import PostgresqlReadbackOwner
        require(native_readback is None or type(native_readback) is PostgresqlReadbackOwner,
                'The actual current independent PostgreSQL readback owner is required')
        self.native_readback=native_readback

    def _require_fence(self,receipt):
        if self.native_readback is not None:
            return self.native_readback.require_current_acknowledgment(receipt,self.source.authority.runtime.registry)
        return self.evidence.require_resolved(receipt,self.source.authority.scope)

    def _run(self,stage,effect):
        body=self.selection.to_dict();admitted=self.source.authority.admitted
        scope={'job':admitted.job_id,'dataset':body['datasetId'],'selection':self.selection.sha256}
        with execution_journal.locked(self.ledger,scope) as journal:
            started=[event for event in journal.events if event['kind']=='DATABASE_SYNC_STARTED']
            complete=[event for event in journal.events if event['kind']=='DATABASE_SYNC_COMPLETED']
            require(len(started)==len(complete),'Original database effect outcome is unknown; independently observe it')
            require(all(event['kind'] in {'DATABASE_SYNC_STARTED','DATABASE_SYNC_COMPLETED'} for event in journal.events),
                    'The original database stage journal changed')
            stages=[event['data']['stage'] for event in started]
            if stage in {'INITIAL','FINAL'} and stage in stages:
                self.source.authority.require_current();self.target.authority.require_current()
                return complete[stages.index(stage)]['data']['result']
            require((not stages and stage=='INITIAL') or (stages and stages[0]=='INITIAL'
                    and stage!='INITIAL' and 'FINAL' not in stages),
                    'Database stages require the original initial snapshot and cannot continue after final acceptance')
            journal.append('DATABASE_SYNC_STARTED',{'stage':stage})
            try:
                result=effect();self.source.authority.require_current();self.target.authority.require_current()
                journal.append('DATABASE_SYNC_COMPLETED',{'result':result});return result
            except BaseException:
                self.source.authority.uncertain();self.target.authority.uncertain();raise

    def initialize(self):return self._run('INITIAL',self.engine.initial_snapshot)
    def synchronize(self):
        def run():
            transactions=self.engine.capture();receipts=[]
            for transaction in transactions:
                receipt=self.engine.apply(transaction);self.engine.acknowledge(transaction);receipts.append(receipt)
            return {'status':'OWNED_SOURCE_TRANSACTIONS_SYNCHRONIZED','transactions':receipts,
                    **self.engine.lag(),'backgroundApplyEnabled':False,'nativeQualification':False}
        return self._run('INCREMENTAL',run)

    def final(self,receipt):
        body=self.selection.to_dict();authority=self.source.authority
        require(type(receipt) is dict and receipt.get('phase')=='SOURCE_DATABASE_WRITER_FENCE'
                and receipt.get('job_id')==authority.admitted.job_id and receipt.get('member_id')==body['memberId']
                and receipt.get('selection_sha256')==self.selection.sha256
                and receipt.get('original_intent',{}).get('operation_kind')=='SOURCE_FENCE'
                and receipt.get('original_intent',{}).get('binding')==vars(authority.binding),
                'The exact independent database-writer fence is required; VM-off/file fences cannot substitute')
        def run():
            self._require_fence(receipt)
            self.engine.writer_fence_observation()
            for transaction in self.engine.capture():
                self.engine.apply(transaction);self.engine.acknowledge(transaction)
            result=self.engine.compare_locked();self.engine.writer_fence_observation()
            self._require_fence(receipt)
            result['sourcePersistentFenceVerified']=True;result['nativeQualification']=False;return result
        return self._run('FINAL',run)
