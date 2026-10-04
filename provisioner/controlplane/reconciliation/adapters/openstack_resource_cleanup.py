"""All selected OpenStack children, native dependencies and original charges.

This concrete proof cannot cover another native platform or a nonzero retained,
snapshot or staging purpose. Such charges require that purpose's actual owner.
It never treats a missing output, expired lease or worker assertion as absence.
"""
from dataclasses import asdict

from provisioner.allocations import capacity_owner
from provisioner.allocations.transactions import ResourceBundle,ResourceObservation,ResourceUnits
from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.persistence import NativeBinding,TenantContext
from provisioner.controlplane.reconciliation.registry import NativeOperationRegistry
from provisioner.controlplane.worker.credential_custody import VaultRecoveryRevoker
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import encoded,load_private,private_path,require,utcnow,write_new
from .openstack_cleanup import OpenStackCleanupReadbackOwner


class OpenStackResourceCleanupProof:
    def __init__(self,*,readback,registry,resources,revokers,directory):
        from provisioner.allocations.transactions import ResourceTransactions
        require(type(readback) is OpenStackCleanupReadbackOwner
                and isinstance(registry,NativeOperationRegistry) and registry._evidence is readback
                and isinstance(resources,ResourceTransactions) and isinstance(revokers,tuple) and revokers
                and all(type(owner) is VaultRecoveryRevoker and owner.bundle==readback.bundle for owner in revokers),
                'Actual cleanup journal, complete old issuance custody and original capacity owner required')
        self.readback,self.registry,self.resources,self.revokers=readback,registry,resources,revokers
        self.directory=private_path(directory,directory=True)

    def _children(self,cursor,bundle):
        context=TenantContext(bundle.admitted.organization_id,bundle.admitted.tenant_id)
        cursor.execute('SELECT i.operation_id,o.evidence_digest,o.created_native_bindings '
            'FROM hosting_controlplane.native_operation_intents i '
            'JOIN hosting_controlplane.native_operation_observations o ON '
            '(i.organization_id,i.tenant_id,i.operation_id)=(o.organization_id,o.tenant_id,o.operation_id) '
            'WHERE i.organization_id=%s AND i.tenant_id=%s AND i.job_id=%s '
            "AND i.operation_kind='VM_CREATE' AND i.state='RESOLVED' AND i.outcome='EFFECT_PRESENT' "
            "AND o.outcome='EFFECT_PRESENT' AND o.native_quiesced ORDER BY o.recorded_at DESC",
            (context.organization_id,context.tenant_id,bundle.admitted.job_id))
        children={}
        for operation_id,evidence,native in cursor.fetchall():
            records=c.strict_loads(native) if type(native) is str else native
            require(type(records) is list and 1<=len(records)<=1000,
                    'The original independently resolved creation has no complete child projection')
            for row in records:
                binding=NativeBinding(**row)
                require(binding.key()[:3]==(self.readback.scope.platform_family,self.readback.scope.endpoint_id,
                    self.readback.scope.native_scope_id),'A child escapes the exact selected native project')
                children[binding.key()]=binding
        pool=next(pool for pool in bundle.pools if pool.scope==self.readback.scope and pool.inputs is not None)
        expected=sum(3+(1 if member.get('data_disk_gib',0)>0 else 0) for member in pool.inputs['members'].values())
        require(len(children)==expected,'The original journal does not cover every selected VM, port and volume')
        return tuple(children[key] for key in sorted(children))

    def _resolved(self,cursor,bundle,binding):
        context=TenantContext(bundle.admitted.organization_id,bundle.admitted.tenant_id)
        cursor.execute('SELECT i.operation_id,o.evidence_digest FROM hosting_controlplane.native_operation_intents i '
            'JOIN hosting_controlplane.resource_recovery_bindings r ON '
            '(i.organization_id,i.tenant_id,i.job_id)=(r.organization_id,r.tenant_id,r.recovery_job_id) '
            'JOIN hosting_controlplane.native_operation_observations o ON '
            '(i.organization_id,i.tenant_id,i.operation_id)=(o.organization_id,o.tenant_id,o.operation_id) '
            'WHERE i.organization_id=%s AND i.tenant_id=%s AND r.original_job_id=%s '
            'AND r.original_plan_digest=%s AND r.original_selection_digest=%s AND r.resource_bundle_digest=%s '
            "AND i.operation_kind='NATIVE_CLEANUP' AND i.state='RESOLVED' AND i.outcome='EFFECT_PRESENT' "
            'AND (i.platform_family,i.endpoint_id,i.native_scope_id,i.resource_kind,i.native_id)=(%s,%s,%s,%s,%s) '
            "AND o.outcome='EFFECT_PRESENT' AND o.native_quiesced ORDER BY o.recorded_at DESC LIMIT 1",
            (context.organization_id,context.tenant_id,bundle.admitted.job_id,bundle.admitted.plan_digest,
             bundle.selection_digest,bundle.digest,*binding.key()))
        row=cursor.fetchone(); require(row is not None,'A native child lacks its independently resolved original cleanup')
        operation=self.registry._get(cursor,context,row[0])
        original=load_private(self.readback.directory/(row[1]+'.json'))
        require(c.digest(original)==row[1] and original['operation_id']==operation.operation_id
                and original['request_digest']==operation.request_digest and original['binding']==asdict(binding),
                'The original accepted cleanup proof changed its native identity or request')
        child=self.readback.child(cursor,context,binding)
        current=self.readback.observe_cleanup(context,operation,original['request'],child,
            original['http_receipt'],cursor=cursor)
        self.readback.verify_native_observation(cursor,operation,current)
        return current.evidence_digest

    def observe_release(self,cursor,bundle):
        require(isinstance(bundle,ResourceBundle) and bundle==self.readback.bundle,
                'Only the original immutable native charge can be inspected for cleanup')
        pools=[pool for pool in bundle.pools if pool.scope==self.readback.scope]
        require(len(pools)==1 and pools[0].inputs is not None
                and all(asdict(purpose)==asdict(ResourceUnits()) for purpose in
                    (pools[0].staging,pools[0].snapshots,pools[0].retained_source)),
                'Nonzero temporary, snapshot or retained-source purposes require their separate observed cleanup owners')
        self.readback.enrollment.require_current(cursor=cursor)
        context=TenantContext(bundle.admitted.organization_id,bundle.admitted.tenant_id)
        _tenant(cursor,context)
        current_job=self.revokers[0].recovery.admitted.job_id
        cursor.execute('SELECT DISTINCT worker_id FROM hosting_controlplane.native_operation_intents '
            'WHERE organization_id=%s AND tenant_id=%s AND (job_id=%s OR job_id IN '
            '(SELECT recovery_job_id FROM hosting_controlplane.resource_recovery_bindings '
            'WHERE organization_id=%s AND tenant_id=%s AND original_job_id=%s AND recovery_job_id<>%s)) ORDER BY worker_id',
            (context.organization_id,context.tenant_id,bundle.admitted.job_id,
             context.organization_id,context.tenant_id,bundle.admitted.job_id,current_job))
        workers=[row[0] for row in cursor.fetchall()]
        # The current recovery's still-enrolled cleanup writer has independently
        # resolved exact DELETE intents; it cannot create/restore original UUIDs.
        # Earlier writers must all be explicitly excluded, including credentials.
        cursor.execute('SELECT operation_kind,state FROM hosting_controlplane.native_operation_intents '
            'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s ORDER BY operation_id',
            (context.organization_id,context.tenant_id,current_job))
        require(all(row==('NATIVE_CLEANUP','RESOLVED') for row in cursor.fetchall()),
                'Current recovery still owns unresolved or unbounded native work; keep the original charge')
        fence={}
        for worker in workers:
            owners=[owner for owner in self.revokers if owner.recovery.admitted.job_id==current_job]
            require(len(owners)==1,'One enrolled current exact original credential inspection owner is required')
            fence[worker]=owners[0].inspect_original(worker,cursor=cursor)
        children=self._children(cursor,bundle)
        cleanup={c.digest(list(binding.key())):self._resolved(cursor,bundle,binding) for binding in children}
        with capacity_owner.database(self.resources.database) as database:
            capacity_owner.verify_events(database)
            envelope=c.strict_loads(database.execute('SELECT body FROM envelope WHERE singleton=1').fetchone()[0])
        request=next(request for request in bundle.requests(envelope['owner_id'],current=False)
            if request['resource_binding']['native_scope']==asdict(self.readback.scope))
        at=utcnow(); ids=tuple(sorted(binding.native_id for binding in children))
        record={'format':'hosting-openstack-resource-cleanup/1','original_job_id':bundle.admitted.job_id,
            'resource_bundle_digest':bundle.digest,'reservation_id':request['reservation_id'],
            'native_ids':list(ids),'scope':asdict(self.readback.scope),'cleanup':cleanup,'fence':fence,
            'units':asdict(ResourceUnits()),'observed_at':at.isoformat()}
        sha=c.digest(record); write_new(self.directory/(sha+'.json'),encoded(record))
        return ResourceObservation(request['reservation_id'],sha,ids,ResourceUnits(),'NO_EFFECT',at)

    def verify_resource_observation(self,cursor,bundle,action,observation):
        require(action=='release' and isinstance(observation,ResourceObservation),
                'This owner only verifies complete original native cleanup; it cannot affirm creation occupancy')
        record=load_private(self.directory/(observation.evidence_digest+'.json'))
        require(c.digest(record)==observation.evidence_digest
                and record['format']=='hosting-openstack-resource-cleanup/1'
                and record['resource_bundle_digest']==bundle.digest and record['original_job_id']==bundle.admitted.job_id
                and (record['reservation_id'],tuple(record['native_ids']),record['units'],record['observed_at'])==
                    (observation.reservation_id,observation.native_ids,asdict(observation.units),observation.observed_at.isoformat())
                and observation.outcome=='NO_EFFECT' and observation.units==ResourceUnits(),
                'Release observation differs from actual independent original cleanup custody')
        current=self.observe_release(cursor,bundle)
        require((current.reservation_id,current.native_ids,current.units,current.outcome)==
                (observation.reservation_id,observation.native_ids,observation.units,observation.outcome),
                'Original native cleanup or exact charge coverage changed before refund')
