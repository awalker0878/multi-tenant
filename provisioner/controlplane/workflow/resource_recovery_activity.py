"""Concrete selected recovery activities on the ordinary admitted job queue."""
from types import MappingProxyType

from temporalio import activity

from provisioner.allocations.transactions import ResourceTransactions
from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.reconciliation.adapters.openstack_cleanup import EnrolledOpenStackCleanupRuntime
from provisioner.controlplane.reconciliation.adapters.openstack_resource_cleanup import OpenStackResourceCleanupProof
from provisioner.controlplane.reconciliation.registry import RecoveryHeld
from provisioner.controlplane.reconciliation.resource_recovery import PostgresResourceRecoveryAuthority
from provisioner.controlplane.worker.credential_custody import VaultRecoveryRevoker
from provisioner.controlplane.worker.grants import GrantDenied
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import encoded,private_path,require,write_new
from .resource_recovery_job import ResourceRecoveryStageRequest,ResourceRecoveryStageResult
from .resource_recovery_selection import PostgresResourceRecoverySelector,cleanup_binding_key


class ResourceRecoveryRuntimeBindings:
    """Installed process enrollment; no queued module, path or affirming callback."""
    def __init__(self,*,authority,revokers=(),cleanup=(),release_proofs=()):
        require(type(authority) is PostgresResourceRecoveryAuthority
                and all(isinstance(values,tuple) for values in (revokers,cleanup,release_proofs))
                and all(type(owner) is VaultRecoveryRevoker and owner.recovery is authority for owner in revokers)
                and all(type(owner) is EnrolledOpenStackCleanupRuntime and owner.recovery is authority for owner in cleanup)
                and all(type(owner) is OpenStackResourceCleanupProof for owner in release_proofs),
                'Only concrete enrolled current recovery, native cleanup and original release owners are accepted')
        keys=[cleanup_binding_key(owner.lease.binding) for owner in cleanup]
        require(len(set(keys))==len(keys),'A selected original native child has multiple cleanup writers')
        self.authority,self.revokers=authority,revokers
        self.cleanup=MappingProxyType(dict(zip(keys,cleanup)))
        self.release_proofs=release_proofs


class ResourceRecoveryActivities:
    def __init__(self,*,selector,resources,bindings,directory):
        require(type(selector) is PostgresResourceRecoverySelector and isinstance(resources,ResourceTransactions)
                and type(bindings) is ResourceRecoveryRuntimeBindings
                and bindings.authority.resources is resources
                and bindings.authority.selections is selector.selections
                and bindings.authority.connect is selector.connect,
                'Same current admission, protected recovery selection and existing allocation owners required')
        self.selector,self.resources,self.bindings=selector,resources,bindings
        self.directory=private_path(directory,directory=True)

    def _selected(self,request):
        require(type(request) is ResourceRecoveryStageRequest,'Fixed typed admitted recovery stage required')
        selected=self.selector.require_input(request.input)
        require(self.bindings.authority.admitted==request.input.admitted,
                'The process enrollment belongs to another newly admitted recovery job')
        return selected

    def _result(self,request,evidence):
        sha=c.digest(evidence); write_new(self.directory/(sha+'.json'),encoded(evidence))
        return ResourceRecoveryStageResult(request.input.admitted.job_id,request.member_id,'STAGE_VERIFIED',sha)

    @staticmethod
    def _held(request,error):
        reason=('AUTHORITY_REVOKED' if isinstance(error,(AuthorityDenied,GrantDenied)) else
                'NATIVE_UNCERTAIN' if isinstance(error,RecoveryHeld) else 'RECOVERY_REQUIRED')
        return ResourceRecoveryStageResult(request.input.admitted.job_id,request.member_id,'HELD',reason_code=reason)

    def _revoker(self,selected):
        owners=[owner for owner in self.bindings.revokers if owner.bundle==selected.bundle]
        require(len(owners)==1,'One concrete scoped original credential exclusion owner must be enrolled')
        return owners[0]

    @activity.defn(name='resource_recovery_fence_original')
    def fence_original(self,request: ResourceRecoveryStageRequest)->ResourceRecoveryStageResult:
        try:
            selected=self._selected(request)
            require('cleanup' in selected.input.actions and request.member_id in selected.input.original_worker_ids,
                    'A new cleanup approval must select this exact original native worker')
            proof=self._revoker(selected).revoke_original(request.member_id)
            return self._result(request,{'format':'hosting-recovery-stage-proof/1','stage':'fence_original',
                'admitted':request.input.admitted.job_id,'selection_digest':request.input.selection_digest,
                'recovery_selection_digest':request.input.recovery_selection_digest,
                'worker_id':request.member_id,'fence_digest':proof})
        except Exception as error: return self._held(request,error)

    @activity.defn(name='resource_recovery_inspect_fence')
    def inspect_fence(self,request: ResourceRecoveryStageRequest)->ResourceRecoveryStageResult:
        try:
            selected=self._selected(request)
            require('release' in selected.input.actions and request.member_id in selected.input.original_worker_ids,
                    'A current release approval must select this exact original worker inspection')
            proof=self._revoker(selected).inspect_original(request.member_id)
            return self._result(request,{'format':'hosting-recovery-stage-proof/1','stage':'inspect_fence',
                'admitted':request.input.admitted.job_id,'selection_digest':request.input.selection_digest,
                'worker_id':request.member_id,'fence_digest':proof})
        except Exception as error: return self._held(request,error)

    @activity.defn(name='resource_recovery_require_original_resolution')
    def require_original_resolution(self,request: ResourceRecoveryStageRequest)->ResourceRecoveryStageResult:
        try:
            selected=self._selected(request); require(not request.member_id,'Whole original intent set required')
            owner=self.bindings.authority
            with owner.connect() as connection,connection.cursor() as cursor:
                job,plan,purpose,artifact,at=owner.require_control(cursor,selected.bundle,'inspect',resolved=True)
                # Operator resolution uses the existing independently fenced
                # B11 quorum. This activity cannot write a successful outcome.
                proof={'format':'hosting-recovery-stage-proof/1','stage':'require_original_resolution',
                    'admitted':request.input.admitted.job_id,'selection_digest':request.input.selection_digest,
                    'original_operations':purpose['originalOperationIds'],'observed_at':at.isoformat()}
            return self._result(request,proof)
        except Exception as error: return self._held(request,error)

    def _native(self,request,*,effect):
        try:
            selected=self._selected(request)
            require(request.member_id in selected.input.cleanup_binding_keys,
                    'Native recovery child is absent from its approved immutable original intent set')
            owner=self.bindings.cleanup.get(request.member_id)
            require(owner is not None and owner.bundle==selected.bundle,
                    'The exact independently observed original native child has no enrolled cleanup owner')
            if effect:
                require('cleanup' in selected.input.actions,'A release-only plan cannot issue native DELETE')
                proof=owner.cleanup(selected.input.admitted,selected.artifact)
            else:
                # Inspection requires a previously RESOLVED original DELETE.
                # It cannot claim/replay the cleanup operation or mint its writer.
                proof=owner.inspect_cleanup(selected.input.admitted,selected.artifact)
            return self._result(request,{'format':'hosting-recovery-stage-proof/1',
                'stage':'cleanup_native' if effect else 'inspect_native','admitted':request.input.admitted.job_id,
                'selection_digest':request.input.selection_digest,'binding_key':request.member_id,'native':proof})
        except Exception as error: return self._held(request,error)

    @activity.defn(name='resource_recovery_cleanup_native')
    def cleanup_native(self,request: ResourceRecoveryStageRequest)->ResourceRecoveryStageResult:
        return self._native(request,effect=True)

    @activity.defn(name='resource_recovery_inspect_native')
    def inspect_native(self,request: ResourceRecoveryStageRequest)->ResourceRecoveryStageResult:
        return self._native(request,effect=False)

    def _observe_release(self,cursor,selected):
        observations=tuple(owner.observe_release(cursor,selected.bundle) for owner in self.bindings.release_proofs)
        require(len(observations)==len(selected.bundle.pools)
                and len({item.reservation_id for item in observations})==len(observations),
                'Every selected original pool and temporary/retained purpose requires its actual independent cleanup owner')
        return observations

    @activity.defn(name='resource_recovery_verify_resources')
    def verify_resources(self,request: ResourceRecoveryStageRequest)->ResourceRecoveryStageResult:
        try:
            selected=self._selected(request); require(not request.member_id,'Whole original resource selection required')
            owner=self.bindings.authority
            with owner.connect() as connection,connection.cursor() as cursor:
                owner.require_control(cursor,selected.bundle,'inspect',resolved=True)
                # Cleanup without refund retains every original owner receipt.
                # Each native child must still have its independent resolved
                # proof; keeping capacity charged is part of the outcome.
                if 'release' in selected.input.actions:
                    observed=self._observe_release(cursor,selected)
                    evidence=[asdict_observation(item) for item in observed]
                else:
                    require(set(self.bindings.cleanup)==set(selected.input.cleanup_binding_keys),
                            'Every originally observed native cleanup child must remain owned')
                    evidence=[owner.inspect_cleanup(selected.input.admitted,selected.artifact,cursor=cursor)
                        for owner in self.bindings.cleanup.values()]
            accounted=owner.transactions().inspect(selected.bundle)
            return self._result(request,{'format':'hosting-recovery-stage-proof/1','stage':'verify_resources',
                'admitted':request.input.admitted.job_id,'selection_digest':request.input.selection_digest,
                'original_resource_charge':accounted,'native_cleanup':evidence,'refund_authorized':False})
        except Exception as error: return self._held(request,error)

    @activity.defn(name='resource_recovery_release_observed')
    def release_observed(self,request: ResourceRecoveryStageRequest)->ResourceRecoveryStageResult:
        try:
            selected=self._selected(request)
            require(not request.member_id and 'release' in selected.input.actions,
                    'Only separately selected whole original resource refund is allowed')
            owner=self.bindings.authority
            with owner.connect() as connection,connection.cursor() as cursor:
                owner.require_control(cursor,selected.bundle,'release',resolved=True)
                observed=self._observe_release(cursor,selected)
            # ResourceTransactions re-locks current admission and independently
            # recontacts every observation before the existing SQLite refund.
            result=owner.transactions().release(selected.bundle,observed)
            return self._result(request,{'format':'hosting-recovery-stage-proof/1','stage':'release_observed',
                'admitted':request.input.admitted.job_id,'selection_digest':request.input.selection_digest,
                'original_resource_release':result})
        except Exception as error: return self._held(request,error)

    @property
    def activities(self):
        return (self.fence_original,self.inspect_fence,self.require_original_resolution,self.cleanup_native,
                self.inspect_native,self.verify_resources,self.release_observed)


class ResourceRecoveryActivityRouter:
    """Seven fixed owners selected from immutable, process-enrolled jobs.

    Queue input supplies only an already admitted job identity. It cannot load
    credential factories, change the resource database or add another owner.
    """
    def __init__(self,*,selector,resources,bindings,directory):
        require(type(selector) is PostgresResourceRecoverySelector and isinstance(resources,ResourceTransactions)
                and type(bindings) in {dict,MappingProxyType}
                and all(type(value) is ResourceRecoveryRuntimeBindings
                    and key==value.authority.admitted.job_id and value.authority.resources is resources
                    and value.authority.connect is selector.connect
                    and value.authority.selections is selector.selections for key,value in bindings.items()),
                'An immutable map of actual same-owner current recovery enrollments is required')
        execution={id(value.authority.execution_authority) for value in bindings.values()}
        grants={id(owner.command_runtime.grants) for value in bindings.values() for owner in value.cleanup.values()}
        require(len(execution)<=1 and len(grants)<=1
                and all(owner.registry._connect is selector.connect
                    and owner.readback.enrollment.command.grants is owner.command_runtime.grants
                    for value in bindings.values() for owner in value.cleanup.values())
                and all(proof.resources is resources for value in bindings.values() for proof in value.release_proofs),
                'Recovery routing must preserve current execution, grants and independently enrolled native proof owners')
        self.selector,self.resources=selector,resources
        self.bindings=MappingProxyType(dict(bindings))
        self.directory=private_path(directory,directory=True)
        self.owners=MappingProxyType({key:ResourceRecoveryActivities(selector=selector,resources=resources,
            bindings=value,directory=self.directory) for key,value in self.bindings.items()})

    def _owner(self,request):
        require(type(request) is ResourceRecoveryStageRequest,'Fixed typed current recovery input required')
        owner=self.owners.get(request.input.admitted.job_id)
        require(owner is not None and owner.bindings.authority.admitted==request.input.admitted,
                'The exact newly admitted recovery job has no installed concrete owner')
        return owner

    def _run(self,request,method):
        try:return getattr(self._owner(request),method)(request)
        except Exception as error:return ResourceRecoveryActivities._held(request,error)

    @activity.defn(name='resource_recovery_fence_original')
    def fence_original(self,request:ResourceRecoveryStageRequest)->ResourceRecoveryStageResult:
        return self._run(request,'fence_original')

    @activity.defn(name='resource_recovery_inspect_fence')
    def inspect_fence(self,request:ResourceRecoveryStageRequest)->ResourceRecoveryStageResult:
        return self._run(request,'inspect_fence')

    @activity.defn(name='resource_recovery_require_original_resolution')
    def require_original_resolution(self,request:ResourceRecoveryStageRequest)->ResourceRecoveryStageResult:
        return self._run(request,'require_original_resolution')

    @activity.defn(name='resource_recovery_cleanup_native')
    def cleanup_native(self,request:ResourceRecoveryStageRequest)->ResourceRecoveryStageResult:
        return self._run(request,'cleanup_native')

    @activity.defn(name='resource_recovery_inspect_native')
    def inspect_native(self,request:ResourceRecoveryStageRequest)->ResourceRecoveryStageResult:
        return self._run(request,'inspect_native')

    @activity.defn(name='resource_recovery_verify_resources')
    def verify_resources(self,request:ResourceRecoveryStageRequest)->ResourceRecoveryStageResult:
        return self._run(request,'verify_resources')

    @activity.defn(name='resource_recovery_release_observed')
    def release_observed(self,request:ResourceRecoveryStageRequest)->ResourceRecoveryStageResult:
        return self._run(request,'release_observed')

    @property
    def activities(self):
        return (self.fence_original,self.inspect_fence,self.require_original_resolution,self.cleanup_native,
                self.inspect_native,self.verify_resources,self.release_observed)


def asdict_observation(value):
    from dataclasses import asdict
    return asdict(value)|{'observed_at':value.observed_at.isoformat()}
