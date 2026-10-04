"""Actual independent PostgreSQL contacts and original current acknowledgement.

Read grants and Vault leases belong to distinct enrolled peers. The original SQL
writer connections and credentials close before their synchronous effects can
be acknowledged. Unknown operations retain the existing recovery path.
"""
from contextlib import contextmanager
from datetime import datetime,timedelta
import http.client
import os
from pathlib import Path
import re
from types import MappingProxyType
from uuid import uuid4

import psycopg
from psycopg import sql

from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.persistence import TenantContext,canonical_record_digest
from provisioner.controlplane.authority import PlanScope
from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.controlplane.reconciliation.registry import NativeObservation,RecoveryHeld,NativeOperationRegistry,_SELECT,_row
from provisioner.controlplane.worker.vault import VaultDynamicCredentialIssuer
from provisioner.controlplane.worker.credential_custody import VaultNativeCredentialLeaseStore
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import digest,encoded,load_private,private_path,read_private,require,utcnow,write_new
from .postgresql_sync import PostgresqlSyncSelection,_PostgresqlEngine,digest_snapshot


_AVAILABLE_WRITERS="""SELECT count(*) FROM pg_roles login WHERE login.rolcanlogin AND NOT login.rolsuper
    AND EXISTS(SELECT 1 FROM pg_roles effective
        WHERE has_table_privilege(effective.oid,%s,'INSERT,UPDATE,DELETE,TRUNCATE')
        AND pg_has_role(login.oid,effective.oid,'SET'))"""
# Restricted statistics may hide backend_type. A hidden writer session remains
# uncertain; NOLOGIN or lack of statistics visibility never excludes it.
_ACTIVE_WRITERS="""SELECT count(*) FROM pg_stat_activity backend
    LEFT JOIN pg_roles login ON login.oid=backend.usesysid
    WHERE backend.datname=current_database()
    AND (backend.backend_type IS NULL OR backend.backend_type IN ('client backend','walsender'))
    AND (login.oid IS NULL OR (NOT login.rolsuper
        AND EXISTS(SELECT 1 FROM pg_roles effective
            WHERE has_table_privilege(effective.oid,%s,'INSERT,UPDATE,DELETE,TRUNCATE')
            AND pg_has_role(login.oid,effective.oid,'SET'))))"""


def _no_other_writers(session,table):
    name=table['schema']+'.'+table['name']
    require(session.execute(_AVAILABLE_WRITERS,(name,)).fetchone()==(0,),
            'Another native application table writer remains available')
    require(session.execute(_ACTIVE_WRITERS,(name,)).fetchone()==(0,),
            'Another native application table writer session remains active')


class PostgresqlReadSession:
    def __init__(self,connection,enrollment,material,selection,side,*,cursor=None):
        require(isinstance(connection,psycopg.Connection) and type(enrollment) is NativeReadEnrollment
                and isinstance(selection,PostgresqlSyncSelection) and side in {'source','target'},
                'An actual independently enrolled native SQL connection is required')
        self.connection=connection;self.enrollment=enrollment;self.material=material
        self.selection=selection;self.side=side;self.cursor=cursor
    def current(self):
        _grant,deadline=self.enrollment.require_current(cursor=self.cursor)
        deadline=min(deadline,self.material.expires_at)
        require(deadline>utcnow(),'The next independent SQL read has no current original permission')
        return deadline
    def execute(self,query,parameters=None):
        milliseconds=min(2000,int((self.current()-utcnow()).total_seconds()*1000))
        require(milliseconds>=1,'Independent SQL read window expired')
        self.connection.execute('SELECT set_config(%s,%s,false)',('statement_timeout',str(milliseconds)))
        result=self.connection.execute(query,parameters);self.current();return result
    def peek_selected(self,selection):
        require(selection==self.selection and self.side=='source','The native readonly stream selector changed')
        return self.execute('SELECT * FROM hosting_sync.peek_source(%s,%s)',
            (selection.to_dict()['streamId'],selection.sha256)).fetchall()


@contextmanager
def _open_read(enrollment,selection,side,*,cursor=None):
    require(type(enrollment) is NativeReadEnrollment and enrollment.scope==PlanScope.from_record(selection.to_dict()[side+'_scope']),
            'The independent SQL peer belongs to another native scope')
    require(not any(key.startswith('PG') or key=='SSLKEYLOGFILE' for key in os.environ),'Unenrolled native SQL environment override')
    endpoint=selection.to_dict()[side]
    require(digest(read_private(endpoint['caFile']))==endpoint['caDigest'],'The native SQL reader trust bundle changed')
    material=enrollment.acquire(cursor=cursor);data=material.data
    require(set(data)=={'username','password'} and isinstance(data['username'],str)
            and re.fullmatch('[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}',data['username'])
            and isinstance(data['password'],str) and 1<=len(data['password'])<=4096,
            'The independent Vault role must return a fixed dynamic PostgreSQL login')
    connection=None
    try:
        connection=psycopg.connect(host=endpoint['host'],hostaddr=endpoint['hostaddr'],port=endpoint['port'],
            dbname=endpoint['database'],user=data['username'],password=data['password'],sslmode='verify-full',
            sslrootcert=endpoint['caFile'],connect_timeout=2,autocommit=True,passfile='/dev/null',
            sslcertmode='disable',gssencmode='disable',require_auth='scram-sha-256',channel_binding='require',
            options='-c default_transaction_read_only=on -c statement_timeout=2000 -c lock_timeout=1000')
        session=PostgresqlReadSession(connection,enrollment,material,selection,side,cursor=cursor)
        require(session.execute('SELECT session_user,rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,rolreplication FROM pg_roles WHERE rolname=session_user').fetchone()==
                (data['username'],False,False,False,False,False),'The actual independent SQL login is privileged')
        session.execute(sql.SQL('SET ROLE {}').format(sql.Identifier(endpoint['readRole'])))
        require(session.execute('SELECT current_user,rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,rolreplication,rolcanlogin FROM pg_roles WHERE rolname=current_user').fetchone()==
                (endpoint['readRole'],False,False,False,False,False,False),'The actual SQL reader is not an isolated readonly role')
        for table in selection.to_dict()['tables']:
            name=table['schema']+'.'+table['name']
            require(session.execute("SELECT has_table_privilege(current_user,%s,'SELECT'),has_table_privilege(current_user,%s,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",
                (name,name)).fetchone()==(True,False),'The independent SQL reader has a native table write capability')
        yield session
    finally:
        if connection is not None:connection.close()


class PostgresqlReadbackOwner:
    def __init__(self,*,selections,source,target,issuers,directory,outputs_directory,exclusion_owner):
        from .postgresql_activities import FilePostgresqlSelectionStore
        require(isinstance(selections,FilePostgresqlSelectionStore) and type(source) is NativeReadEnrollment
                and type(target) is NativeReadEnrollment and type(issuers) is dict and set(issuers)=={'source','target','fence'}
                and all(type(issuer) is VaultDynamicCredentialIssuer
                    and type(issuer._lease_store) is VaultNativeCredentialLeaseStore for issuer in issuers.values())
                and callable(getattr(exclusion_owner,'verify_owner_exclusion',None)),
                'Actual independent SQL readers, original credential custody and recovery exclusion owner required')
        self.selections=selections;self.source=source;self.target=target
        self.issuers=MappingProxyType(dict(issuers));self.directory=private_path(directory,directory=True)
        self.outputs=private_path(outputs_directory,directory=True);self.exclusion_owner=exclusion_owner

    def _selection(self,receipt):
        descriptor=self.selections.load(receipt['selection_sha256'])
        require(receipt['member_id']==descriptor.to_dict()['memberId'],'The independent SQL result selects another member')
        return descriptor

    def _lookup(self,side,enrollment,lease_id,*,cursor=None):
        _grant,deadline=enrollment.require_current(cursor=cursor);issuer=self.issuers[side]
        headers={'X-Vault-Token':issuer._token(),'X-Vault-Request':'true','Content-Type':'application/json','Accept':'application/json'}
        if issuer._namespace is not None:headers['X-Vault-Namespace']=issuer._namespace
        connection=http.client.HTTPSConnection(issuer._host,issuer._port,context=issuer._tls,
            timeout=min(issuer._timeout,(deadline-utcnow()).total_seconds()))
        try:
            connection.request('POST','/v1/sys/leases/lookup',body=encoded({'lease_id':lease_id}),headers=headers)
            response=connection.getresponse();raw=response.read(65537);enrollment.require_current(cursor=cursor)
            require(response.status==400 and len(raw)<=65536 and strict_loads(raw)=={'errors':['invalid lease']},
                    'An original SQL credential is still usable or its revocation is unobserved')
        finally:connection.close()

    def _retired(self,receipt,side,retirement,*,cursor=None):
        original=receipt['original_intent'];enrollment=self.source if side in {'source','fence'} else self.target
        require(type(retirement) is dict and retirement.get('format')=='hosting-database-original-credentials-retired/1'
                and retirement['grantId']==original['grant_id'] and retirement['operationId']==original['operation_id']
                and retirement['selectionDigest']==receipt['selection_sha256'],
                'The exact original SQL credential retirement is required')
        store=self.issuers[side]._lease_store
        def inspect(held):
            _tenant(held,TenantContext(original['organization_id'],original['tenant_id']))
            held.execute('SELECT operation_id,selection_digest,closed_by FROM hosting_controlplane.native_credential_issuance_closures '
                'WHERE organization_id=%s AND tenant_id=%s AND grant_id=%s',
                (original['organization_id'],original['tenant_id'],original['grant_id']))
            require(held.fetchone()==(original['operation_id'],receipt['selection_sha256'],original['worker_id']),
                    'The actual original credential issuance is not durably closed')
            held.execute('SELECT a.issuance_id,l.lease_id,l.lease_digest FROM hosting_controlplane.native_credential_attempts a '
                'LEFT JOIN hosting_controlplane.native_credential_leases l USING(organization_id,tenant_id,issuance_id) '
                'WHERE a.organization_id=%s AND a.tenant_id=%s AND a.grant_id=%s ORDER BY a.issuance_id',
                (original['organization_id'],original['tenant_id'],original['grant_id']))
            rows=held.fetchall()
            require(rows and all(row[1] is not None and digest(row[1].encode())==row[2] for row in rows)
                    and retirement['issuances']==[{'issuanceId':row[0],'leaseDigest':row[2]} for row in rows],
                    'Late or unknown credential issuance invalidates the native completion proof')
            for row in rows:self._lookup(side,enrollment,row[1],cursor=held)
        if cursor is None:
            with store.connect() as connection,connection.cursor() as held:inspect(held)
        else:inspect(cursor)

    def _read(self,descriptor,phase,expected,*,cursor=None):
        body=descriptor.to_dict()
        with _open_read(self.source,descriptor,'source',cursor=cursor) as source,_open_read(self.target,descriptor,'target',cursor=cursor) as target:
            engine=_PostgresqlEngine(descriptor,source,target);engine.retain_generations(expected['nativeGenerations'])
            engine.validate();confirmed=engine.observe_stream()
            fence=engine.writer_fence_observation()
            directories={side:session.execute('SELECT hosting_sync.inspect_directory(%s,%s)',
                (body['streamId'],descriptor.sha256)).fetchone()[0]
                for side,session in (('source',source),('target',target))}
            require(all(isinstance(value,str) and Path(value).is_absolute() and str(Path(value))==value
                        and '..' not in Path(value).parts for value in directories.values()),
                    'Actual current source and target PostgreSQL data directories are unavailable')
            if phase=='SOURCE_DATABASE_WRITER_FENCE':
                return dict(source_system_identifier=body['source']['systemIdentifier'],
                    target_system_identifier=body['target']['systemIdentifier'],selected_writer_exclusion=fence,
                    sourceDataDirectory=directories['source'],targetDataDirectory=directories['target'],
                    subscription_background_apply_enabled=False)
            pending=engine.capture()
            source_rows=engine.rows(source);target_rows=engine.rows(target)
            snapshot=digest_snapshot(source_rows)
            equal=source_rows==target_rows
            if phase in {'DATABASE_FINAL_SOURCE','DATABASE_FINAL_TARGET'}:
                require(not pending and equal and snapshot==expected['snapshotDigest']
                        and confirmed==expected['confirmedSourcePosition'],
                        'The independent native final database state is pending, changed or divergent')
                commit=target.execute('SELECT hosting_sync.inspect_commit(%s,%s)',(body['streamId'],confirmed)).fetchone()[0]
                require(commit is not None and (commit['transactionDigest'],commit['selectionDigest'],commit['kind'])==
                        (expected['targetCommitTransactionDigest'],descriptor.sha256,expected['targetCommitKind']),
                        'The original native target commit journal changed')
                # Both original data writer credentials are retired before
                # either final acknowledgment. Unknown additional native table
                # writers cannot be inferred harmless from an equal row set.
                for session in (source,target):
                    for table in body['tables']:
                        _no_other_writers(session,table)
            return dict(source_system_identifier=body['source']['systemIdentifier'],target_system_identifier=body['target']['systemIdentifier'],
                confirmed_source_position=confirmed,pending_selected_transactions=len(pending),tables_equal=equal,
                source_snapshot_digest=snapshot,target_snapshot_digest=digest_snapshot(target_rows),
                sourceDataDirectory=directories['source'],targetDataDirectory=directories['target'],
                selected_writer_exclusion=fence,subscription_background_apply_enabled=False)

    def observe(self,receipt,*,side,retirement,context):
        from .postgresql_authority import DatabaseOperationContext
        require(isinstance(context,DatabaseOperationContext) and side in {'source','target','fence'}
                and context.descriptor.sha256==receipt['selection_sha256']
                and context.admitted.job_id==receipt['job_id'],'The actual selected SQL original context is required')
        original=receipt['original_intent'];descriptor=self._selection(receipt)
        observer=self.source if side in {'source','fence'} else self.target
        require(observer.subject not in {worker.command.identity.subject for worker in context.workers.values()}
                and observer.command.grant.grant_id not in {worker.command.grant.grant_id for worker in context.workers.values()},
                'The native SQL observer reuses a writer identity or grant')
        require(all(self.issuers[key] is context.workers[key].broker._issuer for key in context.workers),
                'The independent readback lost its original credential issuer custody')
        self._retired(receipt,side,retirement);facts=self._read(descriptor,receipt['phase'],receipt['observations']);at=utcnow()
        sha=canonical_record_digest(receipt)
        require(load_private(self.outputs/(sha+'.json'))==receipt,'The original SQL effect receipt was not retained by its owner')
        record=dict(format='hosting-independent-postgresql-native-observation/1',receiptDigest=sha,selectionDigest=descriptor.sha256,
            side=side,operationId=original['operation_id'],observerSubject=observer.subject,readGrantId=observer.command.grant.grant_id,
            observedAt=at.isoformat(),retirement=retirement,facts=facts)
        evidence=canonical_record_digest(record);write_new(self.directory/(evidence+'.json'),encoded(record))
        return NativeObservation('postgresql-observation-'+uuid4().hex,evidence,observer.subject,None,'EFFECT_PRESENT',True,at)

    def verify_native_observation(self,cursor,operation,observation):
        record,receipt,side,observer,descriptor=self._retained_observation(operation,observation)
        observer.require_current(cursor=cursor)
        self._retired(receipt,side,record['retirement'],cursor=cursor)
        require(self._read(descriptor,receipt['phase'],receipt['observations'],cursor=cursor)==record['facts'],
                'The actual original SQL state changed during independent acknowledgment')

    def _retained_observation(self,operation,observation):
        record=load_private(self.directory/(observation.evidence_digest+'.json'))
        receipt=load_private(self.outputs/(record['receiptDigest']+'.json'));side=record['side']
        observer=self.source if side in {'source','fence'} else self.target
        descriptor=self._selection(receipt);original=receipt['original_intent']
        require(canonical_record_digest(record)==observation.evidence_digest
                and canonical_record_digest(receipt)==record['receiptDigest'] and record['format']=='hosting-independent-postgresql-native-observation/1'
                and record['selectionDigest']==descriptor.sha256 and record['observerSubject']==observation.observer_subject==observer.subject
                and record['readGrantId']==observer.command.grant.grant_id and record['observedAt']==observation.observed_at.isoformat()
                and record['operationId']==operation.operation_id==original['operation_id']
                and observation.native_task_id is operation.native_task_id is None and observation.outcome=='EFFECT_PRESENT'
                and observation.native_quiesced and operation.worker_id!=observer.subject
                and operation.binding.__dict__==original['binding']
                and all(getattr(operation,key)==original[key] for key in ('grant_id','step_id','lease_key','workload_id',
                    'security_domain_id','worker_id','owner_epoch','operation_kind','request_digest')),
                'The current independent SQL observation differs from its original effect or actor')
        return record,receipt,side,observer,descriptor

    def _read_source_exclusion(self,descriptor,expected,*,cursor):
        body=descriptor.to_dict()
        with _open_read(self.source,descriptor,'source',cursor=cursor) as source,_open_read(self.target,descriptor,'target',cursor=cursor) as target:
            engine=_PostgresqlEngine(descriptor,source,target);engine.retain_generations(expected['nativeGenerations'])
            confirmed=engine.observe_stream();engine.writer_fence_observation()
            require(confirmed==expected['confirmedSourcePosition'],
                    'The original final source WAL slot position changed')
            # Target business rows may legitimately change after ACTIVATE.
            # The immutable native target commit, source values, original slot
            # and source credential exclusion remain exact original facts.
            commit=target.execute('SELECT hosting_sync.inspect_commit(%s,%s)',
                (body['streamId'],expected['confirmedSourcePosition'])).fetchone()[0]
            require(commit is not None and (commit['transactionDigest'],commit['selectionDigest'],commit['kind'])==
                    (expected['targetCommitTransactionDigest'],descriptor.sha256,expected['targetCommitKind']),
                    'The original selected target atomic commit is unavailable')
            require(digest_snapshot(engine.rows(source))==expected['snapshotDigest'],
                    'Original fenced source committed database values changed')
            # The peek is nonconsuming and cannot advance or replay the slot.
            require(not source.peek_selected(descriptor),'Source selected transactions changed after final fencing')
            for table in body['tables']:
                _no_other_writers(source,table)
            return {side+'DataDirectory':session.execute('SELECT hosting_sync.inspect_directory(%s,%s)',
                (body['streamId'],descriptor.sha256)).fetchone()[0] for side,session in (('source',source),('target',target))}

    def acknowledge(self,receipt,*,side,retirement,context):
        worker=context.workers[side];registry=worker.registry
        require(self.registered_with(registry),'The original registry must actually use this independent SQL verifier')
        observation=self.observe(receipt,side=side,retirement=retirement,context=context)
        try:
            registry.acknowledge_current(worker.command.context,worker.lease,
                worker.command.grant.operation_scope,worker.command.grant.operation_id,worker.command.identity,observation)
        except BaseException:
            registry.mark_uncertain(worker.command.context,worker.command.grant.operation_id,worker.command.identity.subject)
            raise
        return self.require_current_acknowledgment(receipt,registry)

    def require_current_acknowledgment(self,receipt,registry):
        return self._current_acknowledgment(receipt,registry,source_exclusion=False)

    def require_source_exclusion(self,receipt,registry):
        require(receipt.get('phase')=='DATABASE_FINAL_SOURCE','The original final source database result is required')
        return self._current_acknowledgment(receipt,registry,source_exclusion=True)

    def _current_acknowledgment(self,receipt,registry,*,source_exclusion):
        require(isinstance(registry,NativeOperationRegistry) and self.registered_with(registry),
                'The actual original current native registry verifier is required')
        original=receipt['original_intent'];context=TenantContext(original['organization_id'],original['tenant_id'])
        with registry._connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            cursor.execute(f'SELECT {_SELECT} FROM hosting_controlplane.native_operation_intents '
                'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s FOR SHARE',
                (context.organization_id,context.tenant_id,original['operation_id']))
            row=cursor.fetchone();require(row is not None,'The original SQL operation is unavailable');operation=_row(row)
            require(operation.state=='RESOLVED' and operation.outcome=='EFFECT_PRESENT',
                    'The original SQL operation has no independent current acknowledgment')
            cursor.execute('SELECT observation_id,evidence_digest,observer_subject,native_task_id,outcome,native_quiesced,observed_at '
                'FROM hosting_controlplane.native_operation_observations WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s ORDER BY observed_at DESC',
                (context.organization_id,context.tenant_id,original['operation_id']))
            rows=cursor.fetchall();require(len(rows)==1,'The original current SQL acknowledgment is not unique')
            observation=NativeObservation(*rows[0]);cursor.execute('SELECT clock_timestamp()');now=cursor.fetchone()[0]
            require(now-timedelta(minutes=5)<=observation.observed_at<=now,'Current original SQL readback expired')
            if source_exclusion:
                record,original_receipt,side,observer,descriptor=self._retained_observation(operation,observation)
                require(side=='source' and original_receipt==receipt,'Source writer exclusion names another original receipt')
                observer.require_current(cursor=cursor)
                self._retired(receipt,side,record['retirement'],cursor=cursor)
                directories=self._read_source_exclusion(descriptor,receipt['observations'],cursor=cursor)
                require(all(directories[key]==record['facts'][key] for key in directories),
                        'The current actual database engine placement changed')
            else:self.verify_native_observation(cursor,operation,observation)
            cursor.execute('SELECT resolution_evidence_digest FROM hosting_controlplane.native_operation_intents '
                'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s',
                (context.organization_id,context.tenant_id,operation.operation_id))
            import hashlib,json
            expected=hashlib.sha256(json.dumps(dict(format='hosting-current-native-acknowledgment/1',
                operation_id=operation.operation_id,request_digest=operation.request_digest,grant_id=operation.grant_id,
                owner_epoch=operation.owner_epoch,observation_id=observation.observation_id,
                evidence_digest=observation.evidence_digest,observer_subject=observation.observer_subject,
                native_task_id=observation.native_task_id,observed_at=observation.observed_at.isoformat()),
                sort_keys=True,separators=(',',':')).encode()).hexdigest()
            require(cursor.fetchone()==(expected,),'The original native current acknowledgment digest changed')
            record=load_private(self.directory/(observation.evidence_digest+'.json'))
        return dict(original_job_id=receipt['job_id'],original_operation_id=operation.operation_id,
            original_request_digest=operation.request_digest,phase_receipt_digest=canonical_record_digest(receipt),
            native_observation_digest=observation.evidence_digest,observed_at=observation.observed_at.isoformat(),
            sourceDataDirectory=record['facts']['sourceDataDirectory'],targetDataDirectory=record['facts']['targetDataDirectory'],
            outcome='EFFECT_PRESENT',acknowledgment='CURRENT_ORIGINAL_NATIVE_EFFECT',
            source_writer_exclusion_only=source_exclusion)

    def registered_with(self,registry):
        return registry._evidence is self or (type(registry._evidence) is PostgresqlNativeEvidenceMux
            and self in registry._evidence.databases.values())

    def verify_owner_exclusion(self,cursor,lease,scope,evidence):
        self.exclusion_owner.verify_owner_exclusion(cursor,lease,scope,evidence)


class PostgresqlNativeEvidenceMux:
    """Fixed database/job dispatch around the existing platform proof owner."""
    def __init__(self,*,databases,existing):
        require(type(databases) is dict and databases and all(isinstance(key,str)
                and type(value) is PostgresqlReadbackOwner for key,value in databases.items())
                and callable(getattr(existing,'verify_native_observation',None))
                and callable(getattr(existing,'verify_owner_exclusion',None)),
                'Actual commissioned database and existing platform proof owners required')
        self.databases=MappingProxyType(dict(databases));self.existing=existing
    def verify_native_observation(self,cursor,operation,observation):
        reader=self.databases.get(operation.job_id)
        if operation.binding.resource_kind=='dataset' and reader is not None:
            reader.verify_native_observation(cursor,operation,observation)
        else:self.existing.verify_native_observation(cursor,operation,observation)
    def verify_owner_exclusion(self,cursor,lease,scope,evidence):
        # The separately approved existing recovery owner owns actual unknown
        # worker/credential exclusion. Current known SQL completion retires
        # exact credentials through its fixed native owner above.
        self.existing.verify_owner_exclusion(cursor,lease,scope,evidence)
