"""Current cutover service authority over an immutable original native charge.

The original SQLite requests, receipts, confirmed identities and budget purposes
remain unchanged. Current jobs acquire service projections in the same B10/B11
owner after exact canonical handover, fresh occupancy and old-credential checks.
No staged projection can create another VM, reserve/rekey or refund capacity.
"""
from contextlib import contextmanager
from dataclasses import asdict
from datetime import timedelta
from types import MappingProxyType
from threading import RLock

from provisioner.allocations.transactions import ResourceBundle,ResourceTransactions,ResourceAuthorityWindow
from provisioner.controlplane.authority import postgres as authority_postgres
from provisioner.controlplane.jobs.repository import _JOB_SELECT,_job,_digest,_payload_from_job,_tenant
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.worker.grants import VerifiedWorkerIdentity
from provisioner.controlplane.worker.native_retirement import StagedNativeWriterExclusion
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority,CUTOVER_DRIVER,DATABASE_DRIVER
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import load_private,require
from provisioner.migration.staging import ApplicationStagedHandover,ApplicationStagingRuntime
from .planned import (PlannedLeaseAuthority,PlannedResourceLease,PlannedServiceLease,
    reservation_identity_digest)
from .registry import NativeOperationRegistry,OperationConflict


def staged_service_id(handover,admitted,scope,step_id):
    require(type(handover) is ApplicationStagedHandover and isinstance(admitted,AdmittedInput),
            'The actual staged handover and newly approved service admission are required')
    c.identifier(step_id)
    return 'staged-service-'+c.digest([handover.sha256,admitted.job_id,asdict(scope),step_id])[:40]


def staged_service_parent_digest(handover,bundle,scope,resource_id):
    return c.digest({'format':'hosting-staged-service-parent/1','resource_id':resource_id,
        'handover_digest':handover.sha256,'resource_bundle_digest':bundle.digest,'scope':asdict(scope)})


class StagedApplicationResourceAuthority:
    def __init__(self,*,connect,execution_authority,resources,selections,bundles,staging,handover,admitted,exclusion,
                 source_capacity=None):
        from provisioner.controlplane.workflow.execution_selection import FileExecutionSelectionStore
        from provisioner.controlplane.workflow.provisioning_activity import FileResourceBundleStore
        require(callable(connect) and type(execution_authority) is PostgresExecutionAuthority
                and isinstance(resources,ResourceTransactions) and type(selections) is FileExecutionSelectionStore
                and type(bundles) is FileResourceBundleStore and type(staging) is ApplicationStagingRuntime
                and type(handover) is ApplicationStagedHandover and isinstance(admitted,AdmittedInput)
                and type(exclusion) is StagedNativeWriterExclusion and staging.bundle.admitted.job_id!=admitted.job_id
                and (admitted.organization_id,admitted.tenant_id)==
                    (staging.bundle.admitted.organization_id,staging.bundle.admitted.tenant_id)
                and execution_authority.connect is connect and execution_authority.selections is selections
                and staging.records._connect is connect,
                'Concrete current cutover, original staging custody, resource owner and independent exclusion required')
        if source_capacity is not None:
            from .adapters.vmware_source_capacity import SourceCapacityReadRuntime
            require(type(source_capacity) is SourceCapacityReadRuntime,
                    'Only the separately enrolled actual VMware retained-source occupancy owner is accepted')
        self.connect,self.execution_authority,self.resources=connect,execution_authority,resources
        self.selections,self.bundles,self.staging,self.handover=selections,bundles,staging,handover
        self.admitted,self.exclusion,self.source_capacity=admitted,exclusion,source_capacity
        self.bundle=staging.bundle;self.context=TenantContext(admitted.organization_id,admitted.tenant_id)
        self._transactions=ResourceTransactions(resources.database,self,clock=resources._clock)

    def _current(self,cursor,admitted,artifact,*,write=False):
        require(admitted==self.admitted,'Staged accounting belongs to another current cutover admission')
        _tenant(cursor,self.context)
        cursor.execute('SELECT hosting_controlplane.lock_job_scope(%s,%s,%s)',
            (self.context.organization_id,self.context.tenant_id,admitted.job_id))
        require(cursor.fetchone()==(True,),'Current staged cutover job is unavailable')
        cursor.execute(f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
            'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s',
            (self.context.organization_id,self.context.tenant_id,admitted.job_id))
        row=cursor.fetchone();require(row is not None,'Current staged cutover is not visible')
        job=_job(row)
        require((job.plan_id,job.plan_revision,job.plan_digest,job.revocation_epoch,_digest(_payload_from_job(job)))==
            (admitted.plan_id,admitted.plan_revision,admitted.plan_digest,admitted.revocation_epoch,admitted.payload_digest)
            and job.status in {'STARTED','RUNNING'},'Staged cutover changed its original current admission')
        at=NativeOperationRegistry._clock(cursor);authority_postgres.revalidate_start(cursor,job,at)
        plan,selection=self.execution_authority.require_observation(admitted,_digest(artifact),'DISCOVER_READ',cursor=cursor)
        body=self.handover.to_dict();original=self.bundle.admitted
        require(selection==artifact and selection['driver'] in {CUTOVER_DRIVER,DATABASE_DRIVER}
                and selection.get('applicationStagingSelectionDigest')==self.handover.sha256
                and selection['resourceBundleDigest']==self.bundle.digest
                and selection['workloadId']==self.bundle.workload_id
                and selection['workloadRevision']==body['stagedWorkloadRevision']
                and body['originalAdmitted']==asdict(original)
                and (body['originalArtifactDigest'],body['originalResourceBundleDigest'])==
                    (self.bundle.selection_digest,self.bundle.digest)
                and plan['spec'].get('applicationStagedCutover')=={
                    'format':'hosting-application-staged-cutover-plan/1','originalJobId':original.job_id,
                    'originalPlanDigest':original.plan_digest,'originalArtifactDigest':self.bundle.selection_digest,
                    'stagedHandoverDigest':self.handover.sha256}
                and (plan['spec']['workloadRevision'],plan['spec']['destinationSnapshotId'],plan['spec']['destination'])==
                    (body['stagedWorkloadRevision'],body['targetSnapshotId'],body['destinationScope'])
                and all(pool.scope in (job.source,job.destination) for pool in self.bundle.pools),
                'Current cutover differs from the actual canonical target handover or original charge')
        old_plan,old_artifact=self.execution_authority.require_observation(original,self.bundle.selection_digest,
                                                                          'DISCOVER_READ',cursor=cursor)
        require(old_artifact['driver']=='openstack-linux-application-staging/1'
                and self.bundles(original,old_artifact)==self.bundle
                and (old_plan['spec']['source'],old_plan['spec']['destination'])==
                    (plan['spec']['source'],plan['spec']['destination']),
                'The original staging selection changed its charged native scope or reviewed workload')
        cursor.execute('SELECT status FROM hosting_controlplane.operation_jobs WHERE organization_id=%s '
            'AND tenant_id=%s AND job_id=%s FOR SHARE',
            (self.context.organization_id,self.context.tenant_id,original.job_id))
        require(cursor.fetchone()==('SUCCEEDED',),'Original target staging must be complete before charge handover')
        cursor.execute('SELECT 1 FROM hosting_controlplane.resource_recovery_bindings WHERE organization_id=%s '
            'AND tenant_id=%s AND original_job_id=%s LIMIT 1',
            (self.context.organization_id,self.context.tenant_id,original.job_id))
        require(cursor.fetchone() is None,'Recovered or cleaned staged targets require a new independently reviewed handover')
        cursor.execute('SELECT revision,record_digest FROM hosting_controlplane.enterprise_records '
            "WHERE organization_id=%s AND tenant_id=%s AND record_kind='Workload' AND record_id=%s FOR SHARE",
            (self.context.organization_id,self.context.tenant_id,self.bundle.workload_id))
        require(cursor.fetchone()==(body['stagedWorkloadRevision'],body['stagedWorkloadDigest']),
                'The current canonical staged application changed before resource handover')
        cursor.execute('SELECT record_digest FROM hosting_controlplane.enterprise_records '
            "WHERE organization_id=%s AND tenant_id=%s AND record_kind='ObservationSnapshot' AND record_id=%s FOR SHARE",
            (self.context.organization_id,self.context.tenant_id,body['targetSnapshotId']))
        require(cursor.fetchone()==(body['targetSnapshotDigest'],),'The actual canonical target observation changed')
        creation=self.staging.creation_registry._get(cursor,self.context,body['creationOperationId'])
        require(creation.job_id==original.job_id and creation.state=='RESOLVED' and creation.outcome=='EFFECT_PRESENT'
                and creation.request_digest==self.staging.lease.request_digest,
                'The original exact target creation is unresolved or has another immutable native request')
        custody=load_private(self.staging.native_reader.directory/(body['creationObservationDigest']+'.json'))
        require(c.digest(custody)==body['creationObservationDigest'] and custody['operation_id']==creation.operation_id
                and custody['bundle_digest']==self.bundle.digest and custody['selection_digest']==self.bundle.selection_digest,
                'The original target creation observation custody changed')
        accounted=self.resources._require_accounted(self.bundle)
        require(all(receipt['status']=='CONFIRMED' for receipt in accounted['receipts']),
                'Only independently confirmed original native occupancy can be handed over; speculative/expired holds remain charged')
        bindings,facts,units=self.staging.native_reader._read(self.bundle,job.destination,custody['outputs'],cursor=cursor)
        observed={binding.key() for binding in bindings}
        require(observed=={binding.key() for binding in self.staging.observation.bindings},
                'The actual staged VM, port or storage UUID changed before current cutover')
        targets=set()
        for member in body['associations']:
            for kind,rows in (('vm',[member]),('volume',member['disks']),('nic',member['nics'])):
                for row in rows:
                    target=row['targetBinding'];targets.add((target['platformFamily'],target['endpointId'],
                        target['nativeScopeId'],kind,target['nativeId']))
        require(targets==observed,'Actual staged target associations do not cover the original independently created allocation')
        for pool,receipt in zip(self.bundle.pools,accounted['receipts']):
            if pool.scope==job.destination:
                require(set(receipt['native_ids'])=={binding.native_id for binding in bindings}
                        and all(asdict(units)[key]<=receipt['units'][key] for key in receipt['units']),
                        'Current target occupancy differs from its immutable original charged receipt')
            else:
                require(self.source_capacity is not None,
                        'The retained original source needs its separate current independently enrolled occupancy owner')
                self.source_capacity.require_accounted(cursor,self.bundle,pool,receipt,old_plan)
        exclusion=self.exclusion.verify(cursor,self.bundle)
        if write:
            from provisioner.controlplane.conversion.handover import require_write_admission
            require_write_admission(cursor,self.context,security_domain_id=job.destination.security_domain_id,
                                    workload_id=self.bundle.workload_id)
            owner=self.execution_authority;owner.evidence.require(self.context)
            owner._require_instance(cursor,self.context,selection,'DNS_CHANGE')
            owner.qualification.require_action(cursor,admitted,selection,'DNS_CHANGE')
            owner.operations.require_action(cursor,admitted,selection,'DNS_CHANGE')
        identity={'format':'hosting-staged-resource-accounting/1','admitted':asdict(admitted),
            'current_selection_digest':_digest(selection),'original':asdict(original),
            'original_selection_digest':self.bundle.selection_digest,'resource_bundle_digest':self.bundle.digest,
            'reservation_digest':reservation_identity_digest(accounted['receipts']),'handover_digest':self.handover.sha256}
        sha=c.digest(identity)
        cursor.execute('INSERT INTO hosting_controlplane.staged_resource_accounting_bindings '
            '(organization_id,tenant_id,job_id,original_job_id,current_selection_digest,original_selection_digest,'
            'original_plan_digest,resource_bundle_digest,reservation_digest,handover_digest,binding_digest) '
            'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
            (self.context.organization_id,self.context.tenant_id,admitted.job_id,original.job_id,_digest(selection),
             self.bundle.selection_digest,original.plan_digest,self.bundle.digest,identity['reservation_digest'],self.handover.sha256,sha))
        cursor.execute('SELECT binding_digest FROM hosting_controlplane.staged_resource_accounting_bindings '
            'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s',
            (self.context.organization_id,self.context.tenant_id,admitted.job_id))
        require(cursor.fetchone()==(sha,),'Current cutover already names another original native charge')
        return job,plan,selection,accounted,at,sha

    def require_ready(self,admitted,artifact):
        with self.connect() as connection,connection.cursor() as cursor:
            _job,_plan,_selection,accounted,at,sha=self._current(cursor,admitted,artifact)
            return accounted|{'staged_accounting_digest':sha,'current_job_id':admitted.job_id,
                'handover_digest':self.handover.sha256,'capacity_rekeyed':False}

    def bundle_for(self,admitted,artifact):
        require(admitted==self.admitted and artifact.get('applicationStagingSelectionDigest')==self.handover.sha256
                and artifact.get('resourceBundleDigest')==self.bundle.digest,
                'Current service selection differs from its typed original staged resource parent')
        return self.bundle

    def service_request_digest(self,artifact,step_id):
        binding=artifact.get('stageBindings',{}).get(step_id)
        actual=self.selections.load_verified(_digest(artifact))
        require(actual==artifact and artifact.get('applicationStagingSelectionDigest')==self.handover.sha256
                and artifact['resourceBundleDigest']==self.bundle.digest and type(binding) is dict
                and binding['kind']=='dns_cutover','Staged service handover admits only exact current selected DNS generation changes')
        return c.digest({'format':'hosting-staged-service-operation/1','admitted':asdict(self.admitted),
            'selection_digest':_digest(artifact),'handover_digest':self.handover.sha256,
            'resource_bundle_digest':self.bundle.digest,'original_job_id':self.bundle.admitted.job_id,
            'step_id':step_id,'operation_kind':'DNS_CHANGE','binding':binding})

    @contextmanager
    def locked(self,bundle,action,observations):
        require(bundle==self.bundle and action=='inspect' and not observations,
                'Staged cutover cannot reserve, renew, recreate, rekey or refund the original charge')
        with self.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.context)
            cursor.execute('SELECT revision,record_digest,record_json FROM hosting_controlplane.enterprise_records '
                "WHERE organization_id=%s AND tenant_id=%s AND record_kind='MigrationPlan' AND record_id=%s",
                (self.context.organization_id,self.context.tenant_id,self.admitted.plan_id))
            row=cursor.fetchone();require(row is not None,'Current staged plan is unavailable')
            from provisioner.controlplane.jobs.repository import _json
            artifact=self.selections.load_verified(_json(row[2])['spec']['execution']['artifactDigest'])
            job,plan,selection,accounted,at,sha=self._current(cursor,self.admitted,artifact)
            yield ResourceAuthorityWindow(job.source,job.destination,at,at+timedelta(seconds=300),sha)

    @contextmanager
    def locked_ipam(self,bundle,job,action):
        from provisioner.allocations.ipam_transactions import selection
        require(bundle==self.bundle and action=='reconcile',
                'Staged traffic may inspect an original active address; it cannot create/retire another allocation')
        with self.locked(bundle,'inspect',()) as window:
            original=self.selections.load_verified(bundle.selection_digest)
            require(sum(item==selection(job) for item in original.get('ipamSelections',[]))==1,
                    'The active address differs from its protected original native resource parent')
            yield window

    def transactions(self):return self._transactions


class StagedPlannedLeaseAuthority(PlannedLeaseAuthority):
    def __init__(self,connect,*,resources,selections,bundle_lookup,staged_resources,authority=authority_postgres):
        super().__init__(connect,resources=resources,selections=selections,bundle_lookup=bundle_lookup,authority=authority)
        self._enrollment_lock=RLock();self._worker_sealed=False;self._staged_enrolled=False
        self.staged_resources=MappingProxyType({})
        require(type(staged_resources) in {dict,MappingProxyType},'Concrete staged resource owner map required')
        if staged_resources:self.enroll_staged_resources(staged_resources)

    def enroll_staged_resources(self,staged_resources):
        """One-time process enrollment before the actual worker is registered."""
        with self._enrollment_lock:
            require(not self._worker_sealed and not self._staged_enrolled
                    and type(staged_resources) in {dict,MappingProxyType} and staged_resources
                    and all(type(owner) is StagedApplicationResourceAuthority and owner.resources is self.resources
                        and owner.connect is self._connect and job_id==owner.admitted.job_id
                        and owner.selections is self.selections for job_id,owner in staged_resources.items()),
                    'Staged enrollment requires the original concrete owners before worker registration and cannot be replaced')
            self.staged_resources=MappingProxyType(dict(staged_resources));self._staged_enrolled=True

    def seal_for_worker(self):
        with self._enrollment_lock:self._worker_sealed=True

    def require_current(self,cursor,context,*,lease_key,lease_epoch,job_id,operation_id,scope,worker_subject):
        if job_id not in self.staged_resources:
            return super().require_current(cursor,context,lease_key=lease_key,lease_epoch=lease_epoch,
                job_id=job_id,operation_id=operation_id,scope=scope,worker_subject=worker_subject)
        _tenant(cursor,context)
        cursor.execute('SELECT * FROM hosting_controlplane.lock_planned_worker_scope(%s,%s,%s)',
            (context.organization_id,context.tenant_id,lease_key))
        row=cursor.fetchone();now=NativeOperationRegistry._clock(cursor)
        require(row is not None and tuple(row[:2])==(job_id,operation_id)
                and tuple(row[4:9])==(scope.platform_family,scope.endpoint_id,scope.native_scope_id,
                    scope.site_id,scope.security_domain_id) and tuple(row[9:11])==(worker_subject,lease_epoch)
                and row[11]>now and row[12]>now,'Current staged service lease or exact original native owner changed')
        artifact=self.selections.load_verified(row[13]);staged=self.staged_resources[job_id]
        job,plan,selection,accounted,at,sha=staged._current(cursor,staged.admitted,artifact)
        cursor.execute('SELECT step_id,operation_kind,request_digest,job_id,resource_id FROM '
            'hosting_controlplane.planned_service_bindings WHERE organization_id=%s AND tenant_id=%s AND lease_key=%s',
            (context.organization_id,context.tenant_id,lease_key))
        service=cursor.fetchone()
        require(service is not None and service[1]=='DNS_CHANGE' and service[3:]==(job_id,row[2])
                and row[2]==staged_service_id(staged.handover,staged.admitted,scope,service[0])
                and row[14]==staged_service_parent_digest(staged.handover,staged.bundle,scope,row[2])
                and row[15]==reservation_identity_digest(accounted['receipts'])
                and service[2]==staged.service_request_digest(selection,service[0]),
                'Current staged service projection differs from its actual handover and original charged allocation')

    def require_operation(self,cursor,context,*,lease_key,operation_kind,step_id):
        cursor.execute('SELECT job_id FROM hosting_controlplane.native_operation_leases WHERE organization_id=%s '
            'AND tenant_id=%s AND lease_key=%s',(context.organization_id,context.tenant_id,lease_key))
        row=cursor.fetchone()
        if row is not None and row[0] in self.staged_resources:
            require(operation_kind=='DNS_CHANGE','Staged accounting cannot authorize another native VM or allocation')
        return super().require_operation(cursor,context,lease_key=lease_key,operation_kind=operation_kind,step_id=step_id)

    def register_service(self,context,scope,*,job_id,resource_id,lease_key,operation_id,step_id,worker_identity,ttl_seconds=300):
        if job_id not in self.staged_resources:
            return super().register_service(context,scope,job_id=job_id,resource_id=resource_id,lease_key=lease_key,
                operation_id=operation_id,step_id=step_id,worker_identity=worker_identity,ttl_seconds=ttl_seconds)
        staged=self.staged_resources[job_id]
        require(isinstance(worker_identity,VerifiedWorkerIdentity) and type(ttl_seconds) is int and 1<=ttl_seconds<=300
                and (worker_identity.organization_id,worker_identity.tenant_id,worker_identity.site_id)==
                    (context.organization_id,context.tenant_id,scope.site_id)
                and resource_id==staged_service_id(staged.handover,staged.admitted,scope,step_id),
                'Exact new staged DNS service projection and independently verified current worker required')
        for identity in (job_id,resource_id,lease_key,operation_id,step_id):c.identifier(identity)
        with self._connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            cursor.execute('SELECT record_json FROM hosting_controlplane.enterprise_records WHERE organization_id=%s '
                "AND tenant_id=%s AND record_kind='MigrationPlan' AND record_id=%s",
                (context.organization_id,context.tenant_id,staged.admitted.plan_id))
            from provisioner.controlplane.jobs.repository import _json
            row=cursor.fetchone();require(row is not None,'Current staged cutover plan is unavailable')
            artifact=self.selections.load_verified(_json(row[0])['spec']['execution']['artifactDigest'])
            job,plan,selection,accounted,now,sha=staged._current(cursor,staged.admitted,artifact,write=True)
            require(scope==job.destination and worker_identity.expires_at>now,
                    'Current service belongs to another actual staged native destination or expired worker')
            request=staged.service_request_digest(selection,step_id)
            parent=staged_service_parent_digest(staged.handover,staged.bundle,scope,resource_id)
            reservation=reservation_identity_digest(accounted['receipts']);expires=min(now+timedelta(seconds=ttl_seconds),worker_identity.expires_at)
            cursor.execute('INSERT INTO hosting_controlplane.planned_resource_ownership '
                '(organization_id,tenant_id,job_id,resource_id,selection_digest,request_digest,reservation_digest,'
                'resource_kind,platform_family,endpoint_id,native_scope_id,site_id,security_domain_id,workload_id,'
                'worker_id,owner_epoch,lease_expires_at) VALUES (%s,%s,%s,%s,%s,%s,%s,\'deployment\',%s,%s,%s,%s,%s,%s,%s,1,%s) '
                'ON CONFLICT DO NOTHING',(context.organization_id,context.tenant_id,job_id,resource_id,_digest(selection),parent,
                    reservation,scope.platform_family,scope.endpoint_id,scope.native_scope_id,scope.site_id,
                    scope.security_domain_id,staged.bundle.workload_id,worker_identity.subject,expires))
            cursor.execute('SELECT worker_id,owner_epoch,lease_expires_at,request_digest,reservation_digest FROM '
                'hosting_controlplane.planned_resource_ownership WHERE organization_id=%s AND tenant_id=%s AND job_id=%s AND resource_id=%s',
                (context.organization_id,context.tenant_id,job_id,resource_id))
            previous=cursor.fetchone()
            require(previous is not None and previous[0]==worker_identity.subject and previous[2]>now
                    and previous[3:]==(parent,reservation),'Staged service parent already belongs to another immutable request or expired worker')
            owner=PlannedResourceLease(context.organization_id,context.tenant_id,job_id,resource_id,'deployment',
                _digest(selection),parent,reservation,scope,staged.bundle.workload_id,previous[0],previous[1],previous[2])
            cursor.execute('INSERT INTO hosting_controlplane.native_operation_leases '
                '(organization_id,tenant_id,lease_key,job_id,operation_id,platform_family,endpoint_id,native_scope_id,'
                'resource_kind,native_id,planned_resource_id,site_id,security_domain_id,worker_id,owner_epoch,expires_at) '
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'deployment',NULL,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (context.organization_id,context.tenant_id,lease_key,job_id,operation_id,scope.platform_family,scope.endpoint_id,
                    scope.native_scope_id,resource_id,scope.site_id,scope.security_domain_id,owner.worker_id,owner.epoch,owner.expires_at))
            cursor.execute('INSERT INTO hosting_controlplane.planned_service_bindings '
                '(organization_id,tenant_id,lease_key,job_id,resource_id,step_id,operation_kind,request_digest) '
                "VALUES (%s,%s,%s,%s,%s,%s,'DNS_CHANGE',%s) ON CONFLICT DO NOTHING",
                (context.organization_id,context.tenant_id,lease_key,job_id,resource_id,step_id,request))
            self.require_current(cursor,context,lease_key=lease_key,lease_epoch=owner.epoch,job_id=job_id,
                operation_id=operation_id,scope=scope,worker_subject=owner.worker_id)
            return PlannedServiceLease(owner,step_id,'DNS_CHANGE',request)
