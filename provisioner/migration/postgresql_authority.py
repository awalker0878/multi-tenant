"""Concrete current B10/B11/mTLS/Vault authority for selected PostgreSQL commands."""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import http.client
import os
from pathlib import Path
import re
from types import MappingProxyType
from typing import Mapping

import psycopg
from psycopg import sql

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence.store import NativeBinding,OwnerLease
from provisioner.controlplane.persistence import canonical_record_digest
from provisioner.controlplane.reconciliation.registry import NativeOperationRegistry
from provisioner.controlplane.worker.command_runtime import WorkerCommandRuntime
from provisioner.controlplane.worker.grants import CredentialBroker
from provisioner.controlplane.worker.pki import MutualTlsWorkerVerifier
from provisioner.controlplane.worker.vault import VaultDynamicCredentialIssuer
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from provisioner.controlplane.worker.credential_custody import VaultNativeCredentialLeaseStore
from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.execution.run_files import digest,encoded,read_private,require,utcnow
from provisioner.execution.source_integrity import verify,verify_runtime


@dataclass(frozen=True)
class DatabaseWorkerRuntime:
    command:WorkerCommandRuntime
    registry:NativeOperationRegistry
    lease:OwnerLease
    broker:CredentialBroker

    def __post_init__(self):
        require(isinstance(self.command,WorkerCommandRuntime) and isinstance(self.registry,NativeOperationRegistry)
                and isinstance(self.lease,OwnerLease) and isinstance(self.broker,CredentialBroker)
                and self.broker._grants is self.command.grants
                and self.broker._identities is self.command.verifier
                and isinstance(self.broker._identities,MutualTlsWorkerVerifier)
                and isinstance(self.broker._issuer,VaultDynamicCredentialIssuer)
                and type(self.broker._issuer._lease_store) is VaultNativeCredentialLeaseStore
                and self.broker._issuer._lease_store.connect is self.registry._connect,
                'Actual original mTLS/B10/B11 and enrolled dynamic Vault owners required')


@dataclass(frozen=True)
class DatabaseOperationContext:
    """Exactly three approved SQL owners, never a caller exclusion list."""
    admitted:AdmittedInput
    artifact:bytes
    descriptor:object
    workers:Mapping[str,DatabaseWorkerRuntime]

    def __post_init__(self):
        from .postgresql_sync import PostgresqlSyncSelection
        from provisioner.execution.neutron_observe import strict_loads
        require(isinstance(self.admitted,AdmittedInput) and isinstance(self.artifact,bytes)
                and isinstance(self.descriptor,PostgresqlSyncSelection) and isinstance(self.workers,Mapping)
                and set(self.workers)=={'source','target','fence'}
                and all(isinstance(value,DatabaseWorkerRuntime) for value in self.workers.values()),
                'Exact actual selected source, target and database writer fence owners required')
        body=strict_loads(self.artifact)
        require(encoded(body)==self.artifact and body.get('driver')=='openstack-linux-application-database/1'
                and body.get('applicationDatabaseSelectionDigest')==self.descriptor.sha256,
                'Only the explicitly selected original database method may coordinate SQL intents')
        owner=self.workers['source']
        require(all(value.command.authority is owner.command.authority and value.command.grants is owner.command.grants
                and value.registry is owner.registry for value in self.workers.values()),
                'Coordinated SQL workers must retain the same original authority and native registry')
        selected=self.descriptor.to_dict()
        for side,worker in self.workers.items():
            native='source' if side=='fence' else side
            scope=PlanScope.from_record(selected[native+'_scope']);row=selected['operations'][side]
            grant=worker.command.grant
            binding=NativeBinding(scope.platform_family,scope.endpoint_id,scope.native_scope_id,
                                  'dataset',selected[native]['nativeDatasetId'])
            require(worker.lease.binding==binding and worker.lease.workload_id==body['workloadId']
                    and worker.lease.security_domain_id==scope.security_domain_id
                    and (grant.organization_id,grant.tenant_id,grant.worker_subject,grant.step_id,
                         grant.operation_id,grant.operation_kind,grant.operation_scope,grant.lease_epoch,
                         grant.plan_id,grant.plan_revision,grant.plan_digest,grant.revocation_epoch)==
                        (self.admitted.organization_id,self.admitted.tenant_id,worker.command.identity.subject,
                         row['stepId'],row['operationId'],'SOURCE_FENCE' if side=='fence' else 'RESTORE_DATA',
                         scope,worker.lease.epoch,self.admitted.plan_id,self.admitted.plan_revision,
                         self.admitted.plan_digest,self.admitted.revocation_epoch),
                    'A coordinated SQL original grant differs from its exact selected member or native dataset')
        object.__setattr__(self,'workers',MappingProxyType(dict(self.workers)))

    @property
    def artifact_digest(self):
        from provisioner.execution.neutron_observe import strict_loads
        return canonical_record_digest(strict_loads(self.artifact))


class DatabaseCommandAuthority:
    def __init__(self,runtime,admitted,artifact,descriptor,side,root,*,coordination):
        from .postgresql_sync import PostgresqlSyncSelection
        require(isinstance(runtime,DatabaseWorkerRuntime) and isinstance(admitted,AdmittedInput)
                and type(artifact) is dict and isinstance(descriptor,PostgresqlSyncSelection)
                and side in ('source','target','fence') and isinstance(root,Path)
                and artifact.get('applicationDatabaseSelectionDigest')==descriptor.sha256,
                'The exact approved database sync descriptor and original job are required')
        self.runtime=runtime;self.admitted=admitted;self.artifact=encoded(artifact)
        require(isinstance(coordination,DatabaseOperationContext) and coordination.admitted==admitted
                and coordination.artifact==self.artifact and coordination.descriptor==descriptor
                and coordination.workers[side] is runtime,'The actual selected coordinated SQL context is required')
        self.coordination=coordination
        self.artifact_digest=canonical_record_digest(artifact);self.descriptor=descriptor;self.side=side;self.root=root
        body=descriptor.to_dict();self.row=body['operations'][side]
        endpoint_side='source' if side=='fence' else side
        self.scope=PlanScope.from_record(body[endpoint_side+'_scope']);self.endpoint=dict(body[endpoint_side])
        if side=='fence':self.endpoint['ownerRole']=self.endpoint['fenceOwnerRole']
        self.operation_kind='SOURCE_FENCE' if side=='fence' else 'RESTORE_DATA'
        self.binding=NativeBinding(self.scope.platform_family,self.scope.endpoint_id,self.scope.native_scope_id,
                                  'dataset',self.endpoint['nativeDatasetId'])
        require(runtime.lease.binding==self.binding and runtime.lease.workload_id==artifact['workloadId']
                and runtime.lease.security_domain_id==self.scope.security_domain_id
                and (runtime.lease.worker_id,runtime.lease.epoch)==
                    (runtime.command.identity.subject,runtime.command.grant.lease_epoch)
                and runtime.command.grant.operation_scope==self.scope,
                'The SQL worker differs from its exact original owned native dataset')
        self.claimed=False;self.operation=None;self.sealed=False;self.sessions=set();self.require_current()

    def require_current(self):
        require(not self.sealed,'The original SQL writer was sealed; only its independent observer may contact native state')
        runtime=self.runtime.command;original=runtime.grant
        require(self.descriptor.to_dict()['operations'][self.side]==self.row,
                'The immutable database command purpose changed')
        require(runtime.verifier.verify(runtime.transport_evidence)==runtime.identity,
                'The current enrolled actual mTLS peer changed')
        def current(_reference,grant,deadline):
            require(grant==original,'The current database grant differs from its original');return grant,deadline
        grant,deadline=runtime.grants.with_authorized_reference(runtime.context,runtime.identity,original.grant_id,
            **runtime.grant_arguments(self.admitted),use=current)
        require((grant.step_id,grant.operation_id,grant.operation_kind)==
                (self.row['stepId'],self.row['operationId'],self.operation_kind)
                and (grant.plan_id,grant.plan_revision,grant.plan_digest,grant.revocation_epoch,
                     grant.organization_id,grant.tenant_id)==
                    (self.admitted.plan_id,self.admitted.plan_revision,self.admitted.plan_digest,
                     self.admitted.revocation_epoch,self.admitted.organization_id,self.admitted.tenant_id),
                'The SQL command changed its original admitted plan or operation')
        require(callable(getattr(runtime.authority,'require_database_current',None)),
                'The installed current coordinated SQL authority owner is unavailable')
        plan,artifact=runtime.authority.require_database_current(self.admitted,self.artifact_digest,
            self.operation_kind,coordination=self.coordination)
        body=self.descriptor.to_dict()
        require(encoded(artifact)==self.artifact and (plan['spec']['source'],plan['spec']['destination'])==
                (body['source_scope'],body['target_scope']) and (grant.source,grant.destination)==
                (PlanScope.from_record(body['source_scope']),PlanScope.from_record(body['target_scope'])),
                'Current root approval or selected exact native scopes changed')
        source=verify(self.root)
        require(source['status']=='HASHES_MATCH' and source['commit']==artifact['sourceCommit']
                and verify_runtime(self.root)['status']=='RUNTIME_SOURCES_MATCH',
                'The selected actual SQL owner source changed')
        deadline=min(deadline,grant.expires_at,runtime.identity.expires_at,self.runtime.lease.expires_at)
        require(deadline>utcnow(),'Original SQL command authority expired');return grant,deadline

    def claim(self):
        require(not self.claimed,'Database intent is already claimed; observe its original outcome')
        self.require_current();runtime=self.runtime
        operation=runtime.registry.prepare(runtime.command.context,runtime.lease,self.scope,
            job_id=self.admitted.job_id,grant_id=runtime.command.grant.grant_id,
            step_id=self.row['stepId'],lease_key=runtime.command.grant.lease_key,
            worker_identity=runtime.command.identity,operation_id=self.row['operationId'],
            operation_kind=self.operation_kind,request_digest=digest(encoded({'descriptor':self.descriptor.sha256,'side':self.side})))
        require(runtime.registry.claim_once(runtime.command.context,runtime.lease,self.scope,
            self.row['operationId'],runtime.command.identity),'Original SQL intent requires independent reconciliation')
        self.operation=operation;self.claimed=True;self.require_current();return operation

    def original_intent(self):
        require(self.claimed and self.operation is not None,'The original SQL intent was not claimed')
        operation=self.operation
        result={key:getattr(operation,key) for key in ('operation_id','grant_id','step_id','lease_key',
            'workload_id','security_domain_id','worker_id','owner_epoch','operation_kind','request_digest')}
        result.update(organization_id=self.runtime.command.context.organization_id,
                      tenant_id=self.runtime.command.context.tenant_id)
        result['binding']=vars(operation.binding)
        return result

    def uncertain(self):
        if self.claimed:self.runtime.registry.mark_uncertain(self.runtime.command.context,
            self.row['operationId'],self.runtime.command.identity.subject)


class PostgresqlSession:
    """One actual bounded native connection; no background subscription worker."""
    def __init__(self,connection,authority,credential_expires_at):
        require(isinstance(connection,psycopg.Connection) and isinstance(authority,DatabaseCommandAuthority),
                'Concrete actual SQL connection and current database authority required')
        self.connection=connection;self.authority=authority;self.expires_at=credential_expires_at
    def execute(self,query,parameters=None):
        _grant,deadline=self.authority.require_current();deadline=min(deadline,self.expires_at)
        milliseconds=min(2000,int((deadline-utcnow()).total_seconds()*1000))
        require(milliseconds>=1,'The next SQL command has no original credential window')
        self.connection.execute('SELECT set_config(%s,%s,false)',('statement_timeout',str(milliseconds)))
        result=self.connection.execute(query,parameters);self.authority.require_current()
        require(utcnow()<self.expires_at,'SQL credential expired before its observed result');return result
    @contextmanager
    def transaction(self):
        self.authority.require_current()
        with self.connection.transaction():
            yield self
            self.authority.require_current();require(utcnow()<self.expires_at,'SQL commit has no original credential window')
        self.authority.require_current()


@contextmanager
def open_database(authority:DatabaseCommandAuthority):
    require(isinstance(authority,DatabaseCommandAuthority) and authority.claimed,
            'An original claimed database intent is mandatory before native effects')
    runtime=authority.runtime.command;grant,deadline=authority.require_current();endpoint=authority.endpoint
    require(not any(key.startswith('PG') or key=='SSLKEYLOGFILE' for key in os.environ),
            'Inherited PostgreSQL connection overrides are not authorized')
    ca=read_private(Path(endpoint['caFile']))
    require(hashlib.sha256(ca).hexdigest()==endpoint['caDigest'],'The enrolled database trust bundle changed')
    handle=authority.runtime.broker.acquire(runtime.transport_evidence,runtime.context,grant.grant_id,
        **runtime.grant_arguments(authority.admitted))
    credential=VaultCredentialConsumer(authority.runtime.broker._issuer).unwrap(handle,grant)
    data=credential.data
    require(set(data)=={'username','password'} and isinstance(data['username'],str)
            and re.fullmatch('[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}',data['username'])
            and isinstance(data['password'],str) and 1<=len(data['password'])<=4096,
            'The actual enrolled Vault PostgreSQL role must return one dynamic SQL login')
    authority.require_current()
    con=None
    try:
        con=psycopg.connect(host=endpoint['host'],hostaddr=endpoint['hostaddr'],port=endpoint['port'],
            dbname=endpoint['database'],user=data['username'],password=data['password'],
            sslmode='verify-full',sslrootcert=endpoint['caFile'],connect_timeout=2,autocommit=True,
            passfile='/dev/null',sslcertmode='disable',gssencmode='disable',require_auth='scram-sha-256',
            channel_binding='require',options='-c row_security=off -c statement_timeout=2000 -c lock_timeout=1000')
        session=PostgresqlSession(con,authority,min(deadline,credential.expires_at))
        require(session.execute('SELECT session_user').fetchone()==(data['username'],),'Native SQL login differs from Vault')
        require(session.execute('SELECT rolsuper,rolbypassrls,rolcreaterole,rolcreatedb FROM pg_roles WHERE rolname=session_user').fetchone()==
                (False,False,False,False),'The actual dynamic SQL login must not be an administrator')
        session.execute(sql.SQL('SET ROLE {}').format(sql.Identifier(endpoint['ownerRole'])))
        expected_replication=authority.side=='source'
        require(session.execute('SELECT current_user,rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,rolreplication,rolcanlogin FROM pg_roles WHERE rolname=current_user').fetchone()==
                (endpoint['ownerRole'],False,False,False,False,expected_replication,False),
                'An isolated enrolled SQL owner is required; no administrator fallback')
        authority.sessions.add(con)
        yield session
    except BaseException:
        authority.uncertain();raise
    finally:
        if con is not None:
            con.close();authority.sessions.discard(con)


class DatabaseCredentialRetirer:
    """Close original B10 issuance and synchronously retire its exact Vault leases."""
    def __init__(self,authority):
        require(isinstance(authority,DatabaseCommandAuthority) and authority.claimed,
                'An original current claimed database worker is required')
        self.authority=authority;self.issuer=authority.runtime.broker._issuer
        self.store=self.issuer._lease_store

    def _request(self,path,lease_id):
        _grant,deadline=self.authority.require_current();issuer=self.issuer
        headers={'X-Vault-Token':issuer._token(),'X-Vault-Request':'true','Content-Type':'application/json','Accept':'application/json'}
        if issuer._namespace is not None:headers['X-Vault-Namespace']=issuer._namespace
        connection=http.client.HTTPSConnection(issuer._host,issuer._port,context=issuer._tls,
            timeout=min(issuer._timeout,(deadline-utcnow()).total_seconds()))
        try:
            body={'lease_id':lease_id}|({'sync':True} if path=='revoke' else {})
            connection.request('POST','/v1/sys/leases/'+path,body=encoded(body),headers=headers)
            response=connection.getresponse();raw=response.read(65537);self.authority.require_current()
            require(len(raw)<=65536,'Vault retirement response exceeds its bound')
            from provisioner.execution.neutron_observe import strict_loads
            if path=='revoke':require(response.status==204 and not raw,'The original native credential revocation was not observed')
            else:require(response.status==400 and strict_loads(raw)=={'errors':['invalid lease']},
                'The original credential lease still exists; no native acknowledgement')
        finally:connection.close()

    def close(self):
        try:return self._close()
        except BaseException:self.authority.uncertain();raise

    def _close(self):
        guard=self.authority;grant,_deadline=guard.require_current();runtime=guard.runtime.command
        require(not guard.sessions,'Actual original SQL connections must close before credential retirement')
        with self.store.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,runtime.context)
            actual=runtime.grants.verify_intent(cursor,runtime.context,grant_id=grant.grant_id,
                worker_identity=runtime.identity,**runtime.grant_arguments(guard.admitted))
            require(actual==grant,'Original SQL retirement grant changed')
            cursor.execute('SELECT hosting_controlplane.lock_native_credential_grant(%s,%s,%s)',
                (grant.organization_id,grant.tenant_id,grant.grant_id))
            require(cursor.fetchone()==(grant.grant_id,),'Original credential grant is unavailable')
            cursor.execute('INSERT INTO hosting_controlplane.native_credential_issuance_closures '
                '(organization_id,tenant_id,grant_id,operation_id,selection_digest,closed_by) VALUES(%s,%s,%s,%s,%s,%s)',
                (grant.organization_id,grant.tenant_id,grant.grant_id,grant.operation_id,guard.descriptor.sha256,grant.worker_subject))
            cursor.execute('SELECT a.issuance_id,l.lease_id,l.lease_digest FROM hosting_controlplane.native_credential_attempts a '
                'LEFT JOIN hosting_controlplane.native_credential_leases l USING(organization_id,tenant_id,issuance_id) '
                'WHERE a.organization_id=%s AND a.tenant_id=%s AND a.grant_id=%s ORDER BY a.issuance_id',
                (grant.organization_id,grant.tenant_id,grant.grant_id))
            rows=cursor.fetchall()
            require(rows and all(row[1] is not None and digest(row[1].encode())==row[2] for row in rows),
                    'An original credential issuance has no exact consumed lease; preserve uncertainty')
        # Closure is durable before any external revocation. Lost revocation
        # responses never reopen this original grant or repeat database effects.
        for row in rows:self._request('revoke',row[1]);self._request('lookup',row[1])
        guard.require_current();guard.sealed=True
        return {'format':'hosting-database-original-credentials-retired/1',
            'grantId':grant.grant_id,'operationId':grant.operation_id,'selectionDigest':guard.descriptor.sha256,
            'issuances':[{'issuanceId':row[0],'leaseDigest':row[2]} for row in rows]}
