"""New approved recovery admission over an original capacity-owner charge.

The original job, requests, intents and resource selection are retained. Only
the new job's current approvals and epoch authorize recovery. This owner does
not renew the old job or convert terminal state into a native safety proof.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from datetime import timedelta

from provisioner.allocations.transactions import ResourceAuthorityWindow, ResourceBundle, ResourceTransactions
from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.jobs.repository import _JOB_SELECT, _digest, _ensure_plan, _job, _payload_from_job, _tenant
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import require
from .planned import reservation_identity_digest


_FIELDS=frozenset({'format','originalJobId','originalPlanDigest','originalSelectionDigest',
    'resourceBundleDigest','reservationDigest','originalOperationIds','actions','incidentId'})


def validate_recovery_selection(value):
    """Pure exact-field selection parser; it authors no admission or proof."""
    c.exact_keys(value,_FIELDS)
    require(value['format']=='hosting-resource-recovery-selection/1', 'Unknown retained resource recovery format')
    for key in ('originalJobId','incidentId'): c.identifier(value[key])
    for key in ('originalPlanDigest','originalSelectionDigest','resourceBundleDigest','reservationDigest'):
        require(type(value[key]) is str and c.HEX.fullmatch(value[key]), 'Exact retained resource digests required')
    ids=value['originalOperationIds']; actions=value['actions']
    require(type(ids) is list and 1<=len(ids)<=1000 and ids==sorted(set(ids)),
            'Recovery binds a sorted unique nonempty set of original intents')
    for identity in ids: c.identifier(identity)
    require(type(actions) is list and 1<=len(actions)<=2 and actions==sorted(set(actions))
            and set(actions)<={'cleanup','release'}, 'Only fixed cleanup and release recovery actions are supported')
    return value


class PostgresResourceRecoveryAuthority:
    """Restricted recovery projection in the existing B09/B10 PostgreSQL owner."""
    def __init__(self,*,connect,authority,execution_authority,selections,resources,evidence,admitted,lease_seconds=300):
        from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
        require(callable(connect) and callable(getattr(authority,'revalidate_start',None))
                and callable(getattr(selections,'load_verified',None))
                and isinstance(resources,ResourceTransactions) and isinstance(admitted,AdmittedInput)
                and callable(getattr(evidence,'verify_resource_observation',None))
                and isinstance(execution_authority,PostgresExecutionAuthority)
                and type(lease_seconds) is int and 1<=lease_seconds<=300,
                'New admitted recovery, existing resource owner and independent observations required')
        self.connect,self.authority,self.selections=connect,authority,selections
        self.execution_authority=execution_authority
        self.resources,self.evidence,self.admitted=resources,evidence,admitted
        self.context=TenantContext(admitted.organization_id,admitted.tenant_id)
        self.lease_seconds=lease_seconds

    @staticmethod
    def _admitted(job):
        return AdmittedInput(job.job_id,job.organization_id,job.tenant_id,job.plan_id,
            job.plan_revision,job.plan_digest,job.revocation_epoch,_digest(_payload_from_job(job)))

    def require_control(self,cursor,bundle,action,*,resolved=False):
        """Validate new approval even while old writers require fencing.

        This method alone permits no platform effect. The concrete revoker also
        requires its actual current B10 grant. Native cleanup/refund use the
        resolved path, which retains every original B11 uncertainty boundary.
        """
        require(isinstance(bundle,ResourceBundle) and action in {'inspect','cleanup','confirm','release'},
                'Only an exact original recovery resource transaction is supported')
        requested=self.admitted; context=self.context
        require((bundle.admitted.organization_id,bundle.admitted.tenant_id)==
                (context.organization_id,context.tenant_id) and bundle.admitted.job_id!=requested.job_id,
                'Recovery must be a different newly admitted job in the original tenant')
        _tenant(cursor,context)
        cursor.execute('SELECT hosting_controlplane.lock_job_scope(%s,%s,%s)',
            (context.organization_id,context.tenant_id,requested.job_id))
        require(cursor.fetchone()==(True,), 'New recovery job is unavailable')
        cursor.execute(f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
            'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s',
            (context.organization_id,context.tenant_id,requested.job_id))
        row=cursor.fetchone(); require(row is not None,'New recovery job is unavailable')
        job=_job(row)
        require(self._admitted(job)==requested and job.status in {'STARTED','RUNNING'},
                'New recovery admission changed or is no longer running')
        cursor.execute('SELECT clock_timestamp()'); at=cursor.fetchone()[0]
        self.authority.revalidate_start(cursor,job,at)
        cursor.execute('SELECT start_payload_digest,start_run_id FROM hosting_controlplane.job_outbox '
            'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s AND delivered_at IS NOT NULL FOR SHARE',
            (context.organization_id,context.tenant_id,requested.job_id))
        started=cursor.fetchone()
        require(started is not None and started[0]==requested.payload_digest and started[1],
                'New recovery has no exact acknowledged admitted workflow run')
        cursor.execute('SELECT revision,record_digest,record_json FROM hosting_controlplane.enterprise_records '
            "WHERE organization_id=%s AND tenant_id=%s AND record_kind='MigrationPlan' AND record_id=%s",
            (context.organization_id,context.tenant_id,job.plan_id))
        plan=_ensure_plan(cursor.fetchone(),context,job)
        selection=validate_recovery_selection(plan['spec'].get('resourceRecovery',{}))
        execution=plan['spec'].get('execution',{})
        artifact=self.selections.load_verified(execution.get('artifactDigest'))
        original=self.selections.load_verified(bundle.selection_digest)
        require(selection['originalJobId']==bundle.admitted.job_id
                and selection['originalPlanDigest']==bundle.admitted.plan_digest
                and selection['originalSelectionDigest']==bundle.selection_digest
                and selection['resourceBundleDigest']==bundle.digest
                and (plan['spec']['workloadId'],plan['spec']['workloadRevision'])==
                    (bundle.workload_id,bundle.workload_revision)
                and execution.get('format')=='hosting-execution-selection/1'
                and _digest(artifact)==execution['artifactDigest']
                and artifact.get('resourceRecoverySelectionDigest')==c.digest(selection)
                and all(document.get('resourceBundleDigest')==bundle.digest
                        and (document.get('workloadId'),document.get('workloadRevision'),
                             document.get('source'),document.get('destination'))==
                            (bundle.workload_id,bundle.workload_revision,
                             plan['spec']['source'],plan['spec']['destination'])
                        for document in (original,artifact))
                and all(pool.scope in (job.source,job.destination) for pool in bundle.pools),
                'New approved recovery differs from the exact original workload, resource selection or native scopes')
        require(action=='inspect' or ('release' if action=='release' else 'cleanup') in selection['actions'],
                'This recovery effect was not selected by the new plan')
        cursor.execute(f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
            'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s FOR SHARE',
            (context.organization_id,context.tenant_id,bundle.admitted.job_id))
        old=cursor.fetchone(); require(old is not None,'Original job custody is unavailable')
        old=_job(old)
        require(self._admitted(old)==bundle.admitted and (old.source,old.destination)==(job.source,job.destination)
                , 'Original admission changed or names another approved native scope')
        self._require_stopped_original(cursor,old)
        # Read the same SQLite authority, including expired speculative holds.
        # It remains charged; expiry is never proof of native cleanup.
        from provisioner.allocations import capacity_owner as owner
        with owner.database(self.resources.database) as database:
            owner.verify_events(database)
            envelope=c.strict_loads(database.execute('SELECT body FROM envelope WHERE singleton=1').fetchone()[0])
            receipts=[]
            for request in bundle.requests(envelope['owner_id'],current=False):
                row=database.execute('SELECT receipt FROM reservation WHERE id=?',(request['reservation_id'],)).fetchone()
                require(row is not None,'Original native capacity charge is unavailable')
                receipt=c.strict_loads(row[0]); require(receipt['request_sha256']==c.digest(request),
                    'Original reservation request changed; preserve the charge')
                receipts.append(receipt)
        require(reservation_identity_digest(receipts)==selection['reservationDigest'],
                'The newly approved recovery names another immutable reservation identity')
        if action!='inspect':
            from provisioner.controlplane.conversion.handover import require_write_admission
            for pool in bundle.pools:
                require_write_admission(cursor,context,security_domain_id=pool.scope.security_domain_id,
                                        workload_id=bundle.workload_id)
            execution_owner=self.execution_authority
            execution_owner.evidence.require(context)
            execution_owner._require_instance(cursor,context,artifact,'NATIVE_CLEANUP')
            execution_owner.qualification.require_action(cursor,self.admitted,artifact,'NATIVE_CLEANUP')
        cursor.execute('SELECT operation_id,job_id,state,request_digest,grant_id,lease_key,worker_id,owner_epoch,'
            'platform_family,endpoint_id,native_scope_id FROM hosting_controlplane.native_operation_intents '
            'WHERE organization_id=%s AND tenant_id=%s AND (job_id=%s OR job_id IN '
            '(SELECT recovery_job_id FROM hosting_controlplane.resource_recovery_bindings '
            'WHERE organization_id=%s AND tenant_id=%s AND original_job_id=%s AND recovery_job_id<>%s)) '
            'ORDER BY operation_id FOR SHARE',
            (context.organization_id,context.tenant_id,bundle.admitted.job_id,
             context.organization_id,context.tenant_id,bundle.admitted.job_id,requested.job_id))
        operations=cursor.fetchall()
        require([row[0] for row in operations]==selection['originalOperationIds'],
                'Recovery must preserve every original native/service intent, including late uncertainty')
        for related_id in sorted({row[1] for row in operations}-{bundle.admitted.job_id}):
            cursor.execute(f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s FOR SHARE',
                (context.organization_id,context.tenant_id,related_id))
            row=cursor.fetchone(); require(row is not None,'Earlier related cleanup job custody is unavailable')
            related=_job(row)
            require((related.source,related.destination)==(job.source,job.destination),
                    'Earlier cleanup escapes the exact original recovery scopes')
            self._require_stopped_original(cursor,related)
        require(all((row[8],row[9],row[10]) in {(pool.scope.platform_family,pool.scope.endpoint_id,
                pool.scope.native_scope_id) for pool in bundle.pools} for row in operations),
                'An original intent escapes the approved recovery native scopes')
        if resolved:
            require(all(row[2]=='RESOLVED' for row in operations),
                    'Original native uncertainty must be independently resolved before cleanup or refund')
            execution_owner=self.execution_authority
            execution_owner.operations.require_action(cursor,self.admitted,artifact,'NATIVE_CLEANUP')
        elif action=='cleanup':
            execution_owner.operations.require_recovery_fencing(cursor,self.admitted,artifact,
                original_job_id=bundle.admitted.job_id,original_operation_ids=selection['originalOperationIds'])
        projection={'format':'hosting-resource-recovery-binding/1','recovery':asdict(requested),
            'original':asdict(bundle.admitted),'selection':selection,
            'operations':[{'operation_id':row[0],'job_id':row[1],'request_digest':row[3],
                'grant_id':row[4],'lease_key':row[5],'worker_id':row[6],'owner_epoch':row[7],
                'platform_family':row[8],'endpoint_id':row[9],'native_scope_id':row[10]} for row in operations]}
        sha=c.digest(projection)
        from psycopg.types.json import Jsonb
        cursor.execute('INSERT INTO hosting_controlplane.resource_recovery_bindings '
            '(organization_id,tenant_id,recovery_job_id,original_job_id,original_plan_digest,'
            'original_selection_digest,resource_bundle_digest,reservation_digest,original_operations,binding_digest) '
            'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
            (context.organization_id,context.tenant_id,requested.job_id,bundle.admitted.job_id,
             bundle.admitted.plan_digest,bundle.selection_digest,bundle.digest,
             selection['reservationDigest'],Jsonb(projection['operations']),sha))
        cursor.execute('SELECT binding_digest FROM hosting_controlplane.resource_recovery_bindings '
            'WHERE organization_id=%s AND tenant_id=%s AND recovery_job_id=%s',
            (context.organization_id,context.tenant_id,requested.job_id))
        require(cursor.fetchone()==(sha,), 'Recovery job already binds another original resource request')
        return job,plan,selection,artifact,at

    @staticmethod
    def _require_stopped_original(cursor,old):
        cursor.execute('SELECT plan_revision,plan_digest,revocation_epoch FROM hosting_controlplane.plan_authority_state '
            'WHERE organization_id=%s AND tenant_id=%s AND plan_id=%s FOR SHARE',
            (old.organization_id,old.tenant_id,old.plan_id))
        state=cursor.fetchone()
        require(state is not None and (old.status not in {'STARTED','RUNNING'}
                or state!=(old.plan_revision,old.plan_digest,old.revocation_epoch)),
                'The original/earlier cleanup job still has current writer authority')

    @contextmanager
    def locked(self,bundle,action,observations):
        require(action in {'inspect','confirm','release'},
                'Recovery cannot reserve or renew an old job or replay a native creation')
        with self.connect() as connection,connection.cursor() as cursor:
            job,plan,selection,artifact,at=self.require_control(cursor,bundle,action,resolved=action!='inspect')
            if action!='inspect':
                from provisioner.controlplane.conversion.handover import require_write_admission
                for pool in bundle.pools:
                    require_write_admission(cursor,self.context,security_domain_id=pool.scope.security_domain_id,
                                            workload_id=bundle.workload_id)
                for observation in observations:
                    self.evidence.verify_resource_observation(cursor,bundle,action,observation)
            yield ResourceAuthorityWindow(job.source,job.destination,at,at+timedelta(seconds=self.lease_seconds),
                c.digest({'recovery':asdict(self.admitted),'original':asdict(bundle.admitted),
                          'action':action,'binding':selection,'at':at.isoformat()}))

    @contextmanager
    def locked_ipam(self,bundle,job,action):
        # Reuse the original allocation/ledger identity but only retire it after
        # resource cleanup and refund. Activation/reservation are not recovery.
        from provisioner.allocations.ipam_transactions import selection
        require(action in {'retire','quarantine','release'},
                'Approved recovery may only retire the original address ownership')
        with self.connect() as connection,connection.cursor() as cursor:
            current,plan,selected,artifact,at=self.require_control(cursor,bundle,'release',resolved=True)
            from provisioner.controlplane.conversion.handover import require_write_admission
            for pool in bundle.pools:
                require_write_admission(cursor,self.context,security_domain_id=pool.scope.security_domain_id,
                                        workload_id=bundle.workload_id)
            artifact=self.selections.load_verified(bundle.selection_digest)
            require(sum(item==selection(job) for item in artifact.get('ipamSelections',[]))==1,
                    'Recovery address differs from the protected original selection')
            yield ResourceAuthorityWindow(current.source,current.destination,at,at+timedelta(seconds=self.lease_seconds),
                c.digest({'recovery':asdict(self.admitted),'address':selection(job),'action':action}))

    def transactions(self):
        return ResourceTransactions(self.resources.database,self,clock=self.resources._clock)
