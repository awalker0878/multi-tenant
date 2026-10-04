"""Retire exact credentials after independently resolved current native work.

The existing B10 custody and SQL0033 append-only closure own this transition.
Closure prevents a second mint on the original grant. Only authenticated exact
lease revocation and lookup establish retirement; expiry never completes it.
"""
import http.client

from provisioner.controlplane.jobs.repository import _tenant,_digest,_json
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.reconciliation.planned import NativeCreationObservation
from provisioner.controlplane.reconciliation.registry import NativeObservation
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import digest,encoded,require,utcnow,write_new
from .credential_custody import VaultNativeCredentialLeaseStore
from .grants import CredentialBroker,PostgresWorkerGrants,GrantDenied
from .vault import VaultDynamicCredentialIssuer


_KINDS=frozenset({'VM_CREATE','IPAM_RESERVE','DNS_CHANGE','QUOTA_CHANGE','NATIVE_CLEANUP'})


def _exchange(issuer,current,path,lease_id):
    require(type(issuer) is VaultDynamicCredentialIssuer and path in {'revoke','lookup'}
            and type(lease_id) is str and 1<=len(lease_id)<=4096,
            'Only the exact enrolled original backend lease can be retired or inspected')
    deadline=current()
    require(deadline>utcnow(),'The original native credential retirement authority expired')
    headers={'X-Vault-Token':issuer._token(),'X-Vault-Request':'true','Content-Type':'application/json',
             'Accept':'application/json'}
    if issuer._namespace is not None:headers['X-Vault-Namespace']=issuer._namespace
    connection=http.client.HTTPSConnection(issuer._host,issuer._port,context=issuer._tls,
        timeout=min(issuer._timeout,(deadline-utcnow()).total_seconds()))
    try:
        body={'lease_id':lease_id}|({'sync':True} if path=='revoke' else {})
        connection.request('POST','/v1/sys/leases/'+path,body=encoded(body),headers=headers)
        response=connection.getresponse();raw=response.read(65537);current()
        require(len(raw)<=65536 and response.getheader('Content-Encoding','identity')=='identity',
                'Native credential retirement response exceeded its authenticated bound')
        if path=='revoke':
            require(response.status==204 and not raw,'The exact original backend lease was not synchronously revoked')
        else:
            require(response.status==400 and response.headers.get_content_type()=='application/json'
                    and c.strict_loads(raw)=={'errors':['invalid lease']},
                    'Original backend credential remains valid or its absence cannot be authenticated')
    finally:connection.close()


class CompletedNativeGrantRetirement:
    def __init__(self,*,store,issuer,grants):
        require(type(store) is VaultNativeCredentialLeaseStore and type(issuer) is VaultDynamicCredentialIssuer
                and issuer._lease_store is store and type(grants) is PostgresWorkerGrants
                and grants._connect is store.connect,
                'The same actual native broker, B10 grant and append-only custody owners are required')
        self.store,self.issuer,self.grants=store,issuer,grants

    def retire(self,runtime,admitted,selection):
        # Closed, concrete runtime types are supplied by enrollment. No module
        # name, arbitrary executor or success flag enters this method.
        from provisioner.controlplane.reconciliation.planned_terraform import PlannedTerraformRuntime
        from provisioner.controlplane.reconciliation.service_runtime import EnrolledServiceProvisioningRuntime
        from provisioner.controlplane.reconciliation.adapters.openstack_cleanup import EnrolledOpenStackCleanupRuntime
        require(type(runtime) in {PlannedTerraformRuntime,EnrolledServiceProvisioningRuntime,EnrolledOpenStackCleanupRuntime},
                'Only an actual enrolled independently resolved native owner may retire its original credentials')
        planned=type(runtime) is PlannedTerraformRuntime
        command=runtime if planned else runtime.command_runtime
        grant=command.grant; broker=runtime.broker
        require(type(broker) is CredentialBroker and broker._grants is self.grants and broker._issuer is self.issuer
                and command.grants is self.grants and grant.operation_kind in _KINDS
                and (grant.organization_id,grant.tenant_id,grant.plan_id,grant.plan_revision,grant.plan_digest,grant.revocation_epoch)==
                    (admitted.organization_id,admitted.tenant_id,admitted.plan_id,admitted.plan_revision,
                     admitted.plan_digest,admitted.revocation_epoch),
                'Credential retirement differs from the original concrete current native grant')
        context=command.context
        def current(cursor=None):
            require(broker._identities.verify(command.transport_evidence)==command.identity,
                    'Original native completion worker no longer has its actual mTLS identity')
            arguments=runtime.grant_arguments() if planned else command.grant_arguments(admitted)
            if cursor is None:
                def checked(_reference,actual,deadline):
                    require(actual==grant,'The original completion grant changed');return deadline
                return self.grants.with_authorized_reference(context,command.identity,grant.grant_id,**arguments,use=checked)
            actual=self.grants.verify_intent(cursor,context,grant_id=grant.grant_id,worker_identity=command.identity,**arguments)
            require(actual==grant,'The original completion grant changed')
            return min(actual.expires_at,command.identity.expires_at)
        actual_plan,actual_selection=command.authority.require_current(admitted,_digest(selection),grant.operation_kind)
        require(actual_selection==selection,'Original completed native selection changed before credential retirement')
        with self.store.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context);current(cursor)
            cursor.execute('SELECT state,outcome,job_id,grant_id,request_digest FROM '
                'hosting_controlplane.native_operation_intents WHERE organization_id=%s AND tenant_id=%s '
                'AND operation_id=%s FOR SHARE',(context.organization_id,context.tenant_id,grant.operation_id))
            intent=cursor.fetchone()
            require(intent is not None and intent[:4]==('RESOLVED','EFFECT_PRESENT',admitted.job_id,grant.grant_id),
                    'The actual original native intent must be independently resolved before credential retirement')
            cursor.execute('SELECT observation_id,evidence_digest,observer_subject,native_task_id,outcome,'
                'native_quiesced,observed_at,created_native_bindings FROM hosting_controlplane.native_operation_observations '
                'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s '
                "AND outcome='EFFECT_PRESENT' AND native_quiesced ORDER BY recorded_at DESC LIMIT 1",
                (context.organization_id,context.tenant_id,grant.operation_id))
            observed=cursor.fetchone();require(observed is not None,'Independent original native evidence is unavailable')
            observation=NativeObservation(*observed[:7])
            if planned:
                from provisioner.controlplane.persistence import NativeBinding
                operation=runtime.registry._get(cursor,context,grant.operation_id)
                native=tuple(NativeBinding(**row) for row in _json(observed[7]))
                runtime.registry._evidence.verify_creation_observation(cursor,operation,
                    NativeCreationObservation(observation,native))
            elif type(runtime) is EnrolledServiceProvisioningRuntime:
                operation=runtime.registry._get(cursor,context,grant.operation_id)
                runtime.registry.evidence.verify_service_observation(cursor,context,runtime.lease,operation,observation)
            else:
                operation=runtime.registry._get(cursor,context,grant.operation_id)
                runtime.registry._evidence.verify_native_observation(cursor,operation,observation)
            current(cursor)
            cursor.execute('SELECT grant_id FROM hosting_controlplane.worker_grants WHERE organization_id=%s '
                'AND tenant_id=%s AND grant_id=%s FOR UPDATE',(context.organization_id,context.tenant_id,grant.grant_id))
            require(cursor.fetchone()==(grant.grant_id,),'Original completed grant is unavailable')
            cursor.execute('INSERT INTO hosting_controlplane.native_credential_issuance_closures '
                '(organization_id,tenant_id,grant_id,operation_id,selection_digest,closed_by) '
                'VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                (context.organization_id,context.tenant_id,grant.grant_id,grant.operation_id,_digest(selection),grant.worker_subject))
            cursor.execute('SELECT operation_id,selection_digest,closed_by FROM '
                'hosting_controlplane.native_credential_issuance_closures WHERE organization_id=%s AND tenant_id=%s AND grant_id=%s',
                (context.organization_id,context.tenant_id,grant.grant_id))
            require(cursor.fetchone()==(grant.operation_id,_digest(selection),grant.worker_subject),
                    'Original grant already closed under another selected native purpose')
            cursor.execute('SELECT a.issuance_id,l.lease_id,l.lease_digest FROM hosting_controlplane.native_credential_attempts a '
                'LEFT JOIN hosting_controlplane.native_credential_leases l USING(organization_id,tenant_id,issuance_id) '
                'WHERE a.organization_id=%s AND a.tenant_id=%s AND a.grant_id=%s ORDER BY a.issuance_id FOR SHARE OF a',
                (context.organization_id,context.tenant_id,grant.grant_id))
            leases=cursor.fetchall()
        # Closure commits before outside contact. Incomplete/lost issuance
        # stays visible and cannot be papered over by a new wrapped credential.
        require(leases and all(row[1] is not None and digest(row[1].encode())==row[2] for row in leases),
                'Incomplete original native issuance requires independent custody recovery; preserve charge and uncertainty')
        for _issuance,lease_id,_sha in leases:
            _exchange(self.issuer,current,'revoke',lease_id);_exchange(self.issuer,current,'lookup',lease_id)
        record={'format':'hosting-completed-native-credentials-retired/1','job_id':admitted.job_id,
            'selection_digest':_digest(selection),'operation_id':grant.operation_id,'grant_id':grant.grant_id,
            'worker_subject':grant.worker_subject,'native_observation_digest':observation.evidence_digest,
            'leases':[{'issuance_id':row[0],'lease_digest':row[2]} for row in leases],'observed_at':utcnow().isoformat()}
        sha=c.digest(record);write_new(self.store.directory/(sha+'.json'),encoded(record));return sha


class StagedNativeWriterExclusion:
    """Fresh independent lookup of every original sealed native credential."""
    def __init__(self,*,store,issuer,enrollment):
        from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
        require(type(store) is VaultNativeCredentialLeaseStore and type(issuer) is VaultDynamicCredentialIssuer
                and issuer._lease_store is store and type(enrollment) is NativeReadEnrollment,
                'Actual completed native custody, pinned Vault and separate enrolled read identity required')
        self.store,self.issuer,self.enrollment=store,issuer,enrollment

    def verify(self,cursor,bundle):
        context=TenantContext(bundle.admitted.organization_id,bundle.admitted.tenant_id);_tenant(cursor,context)
        current=lambda:self.enrollment.require_current(cursor=cursor)[1]
        current()
        cursor.execute('SELECT operation_id,state,grant_id,worker_id,operation_kind FROM '
            'hosting_controlplane.native_operation_intents WHERE organization_id=%s AND tenant_id=%s '
            'AND job_id=%s ORDER BY operation_id FOR SHARE',
            (context.organization_id,context.tenant_id,bundle.admitted.job_id))
        intents=cursor.fetchall()
        require(intents and all(row[1]=='RESOLVED' and row[4] in _KINDS for row in intents),
                'Original staging still owns uncertain work or requires another native/remote writer exclusion owner')
        cursor.execute('SELECT g.grant_id,g.operation_id,g.worker_subject,x.operation_id,x.selection_digest,x.closed_by '
            'FROM hosting_controlplane.worker_grants g LEFT JOIN hosting_controlplane.native_credential_issuance_closures x '
            'USING(organization_id,tenant_id,grant_id) WHERE g.organization_id=%s AND g.tenant_id=%s AND g.job_id=%s '
            "AND g.operation_kind<>'DISCOVER_READ' ORDER BY g.grant_id FOR SHARE OF g",
            (context.organization_id,context.tenant_id,bundle.admitted.job_id))
        grants=cursor.fetchall();known={row[0]:row for row in intents}
        require(grants and all(row[1] in known and known[row[1]][2:4]==row[:1]+row[2:3] for row in grants),
                'An original staging grant has no matching independently resolved immutable native intent')
        proof=[]
        for grant_id,operation_id,worker,closed_operation,selection,closed_by in grants:
            require((closed_operation,selection,closed_by)==(operation_id,bundle.selection_digest,worker),
                    'Every old mutation grant must be durably sealed under its original selected staging purpose')
            cursor.execute('SELECT a.issuance_id,l.lease_id,l.lease_digest FROM hosting_controlplane.native_credential_attempts a '
                'LEFT JOIN hosting_controlplane.native_credential_leases l USING(organization_id,tenant_id,issuance_id) '
                'WHERE a.organization_id=%s AND a.tenant_id=%s AND a.grant_id=%s ORDER BY a.issuance_id FOR SHARE OF a',
                (context.organization_id,context.tenant_id,grant_id))
            rows=cursor.fetchall()
            require(rows and all(row[1] is not None and digest(row[1].encode())==row[2] for row in rows),
                    'Original staging has incomplete credential issuance; no resource handover is authorized')
            for row in rows:_exchange(self.issuer,current,'lookup',row[1])
            proof.append({'grant_id':grant_id,'operation_id':operation_id,
                'leases':[{'issuance_id':row[0],'lease_digest':row[2]} for row in rows]})
        return c.digest({'format':'hosting-staged-native-writer-exclusion/1','original_job_id':bundle.admitted.job_id,
            'selection_digest':bundle.selection_digest,'grants':proof})
