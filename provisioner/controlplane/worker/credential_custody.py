"""B10 dynamic-credential provenance and exact synchronous Vault revocation.

The existing grant database owns append-only issuance projections. No native
password or reusable wrapping token is stored. Incomplete issuance is retained
as uncertainty, never closed by lease expiry or a caller's claimed success.
"""
from __future__ import annotations

from dataclasses import asdict
import http.client
from uuid import uuid4

from provisioner.controlplane.authority.model import WorkerGrant
from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.persistence import TenantContext
from provisioner.execution.run_files import digest, encoded, load_private, private_path, require, utcnow, write_new
from provisioner.execution.neutron_observe import strict_loads
from .grants import GrantDenied


class VaultNativeCredentialLeaseStore:
    def __init__(self,connect,*,directory):
        require(callable(connect),'The existing B10 PostgreSQL custody owner is required')
        self.connect=connect; self.directory=private_path(directory,directory=True)

    @staticmethod
    def _context(grant):
        require(isinstance(grant,WorkerGrant),'An actual current broker grant is required')
        return TenantContext(grant.organization_id,grant.tenant_id)

    def begin(self,grant,role):
        context=self._context(grant); issuance='credential-'+uuid4().hex
        require(role.scope==grant.operation_scope and role.operation_kind==grant.operation_kind,
                'Credential issuance differs from the exact enrolled grant role')
        with self.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            # Serialize closure against actual issuance on this original B10
            # grant. Expiry or a local process flag cannot release credentials.
            cursor.execute('SELECT grant_id FROM hosting_controlplane.worker_grants '
                'WHERE organization_id=%s AND tenant_id=%s AND grant_id=%s FOR UPDATE',
                (context.organization_id,context.tenant_id,grant.grant_id))
            require(cursor.fetchone()==(grant.grant_id,),'Original credential grant is unavailable')
            cursor.execute('SELECT 1 FROM hosting_controlplane.native_credential_issuance_closures '
                'WHERE organization_id=%s AND tenant_id=%s AND grant_id=%s',
                (context.organization_id,context.tenant_id,grant.grant_id))
            require(cursor.fetchone() is None,'Original credential issuance is durably closed')
            cursor.execute('INSERT INTO hosting_controlplane.native_credential_attempts '
                '(organization_id,tenant_id,issuance_id,grant_id,role_reference,creation_path) '
                'SELECT %s,%s,%s,grant_id,%s,%s FROM hosting_controlplane.worker_grants '
                'WHERE organization_id=%s AND tenant_id=%s AND grant_id=%s '
                'AND worker_subject=%s AND operation_kind=%s AND expires_at=%s '
                'AND plan_id=%s AND plan_revision=%s AND plan_digest=%s AND revocation_epoch=%s '
                'AND step_id=%s AND operation_id=%s AND lease_key=%s AND lease_epoch=%s '
                'AND site_id=%s AND security_domain_id=%s AND platform_family=%s AND endpoint_id=%s '
                'AND native_scope_id=%s AND expires_at>clock_timestamp() RETURNING issuance_id',
                (context.organization_id,context.tenant_id,issuance,role.reference,role.api_path,
                 context.organization_id,context.tenant_id,grant.grant_id,grant.worker_subject,grant.operation_kind,
                 grant.expires_at,grant.plan_id,grant.plan_revision,grant.plan_digest,grant.revocation_epoch,
                 grant.step_id,grant.operation_id,grant.lease_key,grant.lease_epoch,
                 grant.operation_scope.site_id,grant.operation_scope.security_domain_id,
                 grant.operation_scope.platform_family,grant.operation_scope.endpoint_id,grant.operation_scope.native_scope_id))
            require(cursor.fetchone()==(issuance,), 'Credential custody has no exact unexpired persisted B10 grant')
        return issuance

    def wrapped(self,handle,grant):
        context=self._context(grant)
        require(handle.issuance_id is not None,'New resource credentials require custody before issuance')
        with self.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            cursor.execute('SELECT grant_id,creation_path FROM hosting_controlplane.native_credential_attempts '
                'WHERE organization_id=%s AND tenant_id=%s AND issuance_id=%s',
                (context.organization_id,context.tenant_id,handle.issuance_id))
            row=cursor.fetchone(); require(row is not None and row[0]==grant.grant_id
                and handle.creation_path in (row[1],'/v1/'+row[1]),'Wrapped credential changed its recorded grant/role')
            cursor.execute('INSERT INTO hosting_controlplane.native_credential_wrappings '
                '(organization_id,tenant_id,issuance_id,wrapping_digest,expires_at) VALUES (%s,%s,%s,%s,%s)',
                (context.organization_id,context.tenant_id,handle.issuance_id,
                 digest(handle.wrapping_token.encode()),handle.expires_at))

    def consumed(self,handle,grant,lease_id,expires_at):
        context=self._context(grant)
        require(type(lease_id) is str and 1<=len(lease_id)<=4096 and expires_at<=grant.expires_at,
                'A bounded revocable native backend lease is required')
        with self.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            cursor.execute('SELECT a.grant_id,w.wrapping_digest,w.expires_at '
                'FROM hosting_controlplane.native_credential_attempts a '
                'JOIN hosting_controlplane.native_credential_wrappings w USING (organization_id,tenant_id,issuance_id) '
                'WHERE a.organization_id=%s AND a.tenant_id=%s AND a.issuance_id=%s',
                (context.organization_id,context.tenant_id,handle.issuance_id))
            require(cursor.fetchone()==(grant.grant_id,digest(handle.wrapping_token.encode()),handle.expires_at),
                    'Unwrapped credential differs from recorded single-use custody')
            cursor.execute('INSERT INTO hosting_controlplane.native_credential_leases '
                '(organization_id,tenant_id,issuance_id,lease_digest,lease_id,expires_at) VALUES (%s,%s,%s,%s,%s,%s)',
                (context.organization_id,context.tenant_id,handle.issuance_id,digest(lease_id.encode()),lease_id,expires_at))

    @staticmethod
    def _leases(cursor,context,bundle,worker_id,recovery_job_id):
        cursor.execute('SELECT a.issuance_id,a.role_reference,a.creation_path,l.lease_digest,l.lease_id,g.grant_id,'
            'g.operation_id,g.lease_key,g.lease_epoch,g.platform_family,g.endpoint_id,g.native_scope_id,'
            'g.operation_kind,g.job_id '
            'FROM hosting_controlplane.native_credential_attempts a '
            'JOIN hosting_controlplane.worker_grants g USING (organization_id,tenant_id,grant_id) '
            'LEFT JOIN hosting_controlplane.native_credential_leases l USING (organization_id,tenant_id,issuance_id) '
            'WHERE a.organization_id=%s AND a.tenant_id=%s AND (g.job_id=%s OR g.job_id IN '
            '(SELECT recovery_job_id FROM hosting_controlplane.resource_recovery_bindings '
            'WHERE organization_id=%s AND tenant_id=%s AND original_job_id=%s AND recovery_job_id<>%s '
            'AND original_plan_digest=%s AND original_selection_digest=%s AND resource_bundle_digest=%s)) '
            'AND g.worker_subject=%s '
            "AND g.operation_kind<>'DISCOVER_READ' ORDER BY a.issuance_id FOR SHARE OF a,g",
            (context.organization_id,context.tenant_id,bundle.admitted.job_id,
             context.organization_id,context.tenant_id,bundle.admitted.job_id,recovery_job_id,
             bundle.admitted.plan_digest,bundle.selection_digest,bundle.digest,worker_id))
        rows=cursor.fetchall()
        require(rows and all(row[3] is not None and digest(row[4].encode())==row[3] for row in rows),
                'Unknown credential issuance requires independent backend custody recovery; preserve original uncertainty')
        return rows

    @staticmethod
    def _worker_excluded(cursor,context,worker_id):
        cursor.execute('SELECT revoked_at FROM hosting_controlplane.worker_enrollments '
            'WHERE organization_id=%s AND tenant_id=%s AND worker_subject=%s FOR SHARE',
            (context.organization_id,context.tenant_id,worker_id))
        row=cursor.fetchone(); require(row is not None and row[0] is not None,
                'The original worker enrollment must be explicitly revoked')
        cursor.execute('SELECT revoked_at FROM hosting_controlplane.worker_certificate_versions '
            'WHERE organization_id=%s AND tenant_id=%s AND worker_subject=%s FOR SHARE',
            (context.organization_id,context.tenant_id,worker_id))
        rows=cursor.fetchall(); require(rows and all(row[0] is not None for row in rows),
                'Every original worker certificate version must be explicitly revoked')

    def verify_owner_exclusion(self,cursor,lease,scope,evidence):
        # A captured document cannot resurrect revocation permission. The
        # concrete current revoker is retained process-locally for recontact.
        require(type(getattr(self,'revoker',None)) is VaultRecoveryRevoker,
                'Concrete newly approved Vault recovery revocation owner is required')
        self.revoker.verify_owner_exclusion(cursor,lease,scope,evidence)


class VaultRecoveryRevoker:
    """Exact leases only; no prefix, force revocation or caller-selected path."""
    def __init__(self,*,store,issuer,recovery,bundle,command_runtime):
        from .vault import VaultDynamicCredentialIssuer
        from .command_runtime import WorkerCommandRuntime
        from provisioner.controlplane.reconciliation.resource_recovery import PostgresResourceRecoveryAuthority
        require(type(store) is VaultNativeCredentialLeaseStore and type(issuer) is VaultDynamicCredentialIssuer
                and issuer._lease_store is store
                and type(recovery) is PostgresResourceRecoveryAuthority
                and isinstance(command_runtime,WorkerCommandRuntime)
                and command_runtime.grant.operation_kind=='NATIVE_CLEANUP'
                and command_runtime.context==recovery.context
                and command_runtime.grant.plan_digest==recovery.admitted.plan_digest,
                'Actual enrolled new recovery grant, issuer and native lease custody required')
        self.store,self.issuer,self.recovery,self.bundle,self.command=store,issuer,recovery,bundle,command_runtime
        require(getattr(store,'revoker',self) is self,'Credential custody already belongs to another recovery owner')
        store.revoker=self

    def _current(self,cursor):
        command=self.command; grant=command.grant
        require(command.verifier.verify(command.transport_evidence)==command.identity,
                'Recovery revoker mTLS identity changed')
        actual=command.grants.verify_intent(cursor,command.context,grant_id=grant.grant_id,
            worker_identity=command.identity,**command.grant_arguments(self.recovery.admitted))
        require(actual==grant,'Recovery revocation has no exact current B10 grant')
        return min(grant.expires_at,command.identity.expires_at)

    def _vault(self,cursor,path,lease_id):
        deadline=self._current(cursor); issuer=self.issuer
        require(deadline>utcnow(),'Recovery revocation grant expired before Vault contact')
        headers={'X-Vault-Token':issuer._token(),'X-Vault-Request':'true','Content-Type':'application/json',
                 'Accept':'application/json'}
        if issuer._namespace is not None: headers['X-Vault-Namespace']=issuer._namespace
        connection=http.client.HTTPSConnection(issuer._host,issuer._port,context=issuer._tls,
            timeout=min(issuer._timeout,(deadline-utcnow()).total_seconds()))
        try:
            body={'lease_id':lease_id}|({'sync':True} if path=='revoke' else {})
            connection.request('POST','/v1/sys/leases/'+path,body=encoded(body),headers=headers)
            response=connection.getresponse(); raw=response.read(65537); self._current(cursor)
            require(len(raw)<=65536,'Vault revocation response exceeds its bound')
            if path=='revoke':
                require(response.status==204 and not raw,
                        'Vault did not synchronously revoke the exact original native lease')
            else:
                require(response.status==400 and strict_loads(raw)=={'errors':['invalid lease']},
                        'The exact original Vault lease still exists or its revocation cannot be authenticated')
        finally: connection.close()

    def revoke_original(self,worker_id):
        context=self.recovery.context
        with self.store.connect() as connection,connection.cursor() as cursor:
            job,plan,selected,artifact,at=self.recovery.require_control(cursor,self.bundle,'cleanup')
            self._current(cursor); self.store._worker_excluded(cursor,context,worker_id)
            rows=self.store._leases(cursor,context,self.bundle,worker_id,self.recovery.admitted.job_id)
            allowed=set(selected['originalOperationIds'])
            require(all(row[6] in allowed and row[12] in {'VM_CREATE','IPAM_RESERVE','DNS_CHANGE',
                        'QUOTA_CHANGE','NATIVE_CLEANUP'} for row in rows),
                    'Credential custody escapes selected original intents or requires another native exclusion owner')
            for row in rows:
                self._vault(cursor,'revoke',row[4]); self._vault(cursor,'lookup',row[4])
            document={'format':'hosting-vault-original-writer-fence/1','original_job':asdict(self.bundle.admitted),
                'recovery_job':asdict(self.recovery.admitted),'worker_id':worker_id,
                'incident_id':selected['incidentId'],'grant_id':self.command.grant.grant_id,
                'leases':[{'issuance_id':row[0],'role_reference':row[1],'creation_path':row[2],
                    'lease_digest':row[3],'grant_id':row[5],'operation_id':row[6],
                    'lease_key':row[7],'lease_epoch':row[8],'operation_kind':row[12],
                    'job_id':row[13]} for row in rows], 'observed_at':utcnow().isoformat()}
            sha=digest(encoded(document)); write_new(self.store.directory/(sha+'.json'),encoded(document))
            return sha

    def inspect_original(self,worker_id,*,cursor=None):
        """Fresh authenticated exclusion without issuing a Vault revocation.

        A separately approved release-only admission can inspect the exact
        original and earlier recovery leases. Existing absence, explicit
        certificate revocation and complete immutable issuance custody are
        mandatory; elapsed time never stands in for revocation.
        """
        from contextlib import ExitStack
        with ExitStack() as stack:
            if cursor is None:
                connection=stack.enter_context(self.store.connect())
                cursor=stack.enter_context(connection.cursor())
            job,plan,selected,artifact,at=self.recovery.require_control(cursor,self.bundle,'inspect')
            self._current(cursor)
            self.store._worker_excluded(cursor,self.recovery.context,worker_id)
            rows=self.store._leases(cursor,self.recovery.context,self.bundle,worker_id,self.recovery.admitted.job_id)
            require(all(row[6] in selected['originalOperationIds'] and row[12] in
                    {'VM_CREATE','IPAM_RESERVE','DNS_CHANGE','QUOTA_CHANGE','NATIVE_CLEANUP'} for row in rows),
                    'Original remote/native work requires its separately enrolled exclusion owner')
            for row in rows: self._vault(cursor,'lookup',row[4])
            document={'format':'hosting-vault-original-writer-inspection/1','original_job':asdict(self.bundle.admitted),
                'recovery_job':asdict(self.recovery.admitted),'worker_id':worker_id,'incident_id':selected['incidentId'],
                'grant_id':self.command.grant.grant_id,'leases':[{'issuance_id':row[0],'lease_digest':row[3],
                    'grant_id':row[5],'operation_id':row[6],'operation_kind':row[12],'job_id':row[13]} for row in rows],
                'observed_at':at.isoformat()}
            sha=digest(encoded(document)); write_new(self.store.directory/(sha+'.json'),encoded(document))
            return sha

    def verify_owner_exclusion(self,cursor,lease,scope,evidence):
        record=load_private(self.store.directory/(evidence.worker_fence_digest+'.json'))
        job,plan,selected,artifact,at=self.recovery.require_control(cursor,self.bundle,'cleanup')
        require(record['format']=='hosting-vault-original-writer-fence/1'
                and digest(encoded(record))==evidence.worker_fence_digest
                and record['worker_id']==lease.worker_id and record['incident_id']==evidence.incident_id==selected['incidentId']
                and record['original_job']==asdict(self.bundle.admitted)
                and record['recovery_job']==asdict(self.recovery.admitted)
                and scope in (job.source,job.destination), 'Writer exclusion differs from newly approved exact recovery custody')
        self.store._worker_excluded(cursor,self.recovery.context,lease.worker_id)
        rows=self.store._leases(cursor,self.recovery.context,self.bundle,lease.worker_id,self.recovery.admitted.job_id)
        require([row[3] for row in rows]==[row['lease_digest'] for row in record['leases']],
                'A late original credential issuance invalidates the retained exclusion proof')
        require(all(row[6] in selected['originalOperationIds'] and row[12] in
                {'VM_CREATE','IPAM_RESERVE','DNS_CHANGE','QUOTA_CHANGE','NATIVE_CLEANUP'} for row in rows),
                'The recorded native credential fence cannot exclude an unrelated or remote command writer')
        for row in rows: self._vault(cursor,'lookup',row[4])
