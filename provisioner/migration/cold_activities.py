"""Concrete enrolled cold capture/import activities for the existing job queue.

Only these fixed product owners can dispatch. A native image lease and B10
grant are issued after the original snapshot capture has actual independently
accepted custody. No input contains a worker, credential, filename or callback.
"""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import ssl
from types import MappingProxyType

from temporalio import activity

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.jobs.repository import _digest,_tenant
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.reconciliation.planned_image import PlannedImageLeaseAuthority,PlannedImageRegistry
from provisioner.controlplane.reconciliation.registry import RecoveryHeld
from provisioner.controlplane.worker.command_runtime import WorkerCommandRuntime
from provisioner.controlplane.worker.grants import CredentialBroker,GrantDenied,GrantRequest,PostgresWorkerGrants
from provisioner.controlplane.worker.pki import MutualTlsWorkerVerifier
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.cold_capture_job import ColdCaptureStageRequest,ColdCaptureStageResult
from provisioner.controlplane.workflow.cold_capture_selection import PostgresColdCaptureSelector
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import encoded,private_path,require,write_new
from provisioner.execution.source_integrity import verify,verify_runtime
from .cold_authority import ColdExportAuthority,ColdImageAuthority
from .cold_capture import ColdCaptureStore,VsphereColdCapture,VsphereExportReadbackOwner
from .cold_selection import ColdVmSelection
from .glance_image import GlanceImageImporter


class ColdImageEnrollment:
    """Actual current mTLS edge enrollment, not a deferred worker factory.

The protected descriptor fixes all actions. This owner delegates both image
ownership and grant issuance to their original PostgreSQL owners, using the
real verified socket on every phase. It cannot commission a certificate or
capability, mint native identity, or revive an expired original image owner.
"""
    def __init__(self,*,authority,grants,verifier,transport_evidence,admitted,artifact,cold,
                 root,registry,broker,consumer,ca_bundle,store):
        require(isinstance(authority,PostgresExecutionAuthority) and isinstance(grants,PostgresWorkerGrants)
                and isinstance(verifier,MutualTlsWorkerVerifier) and type(transport_evidence) is ssl.SSLSocket
                and type(admitted) is AdmittedInput and type(artifact) is dict and type(cold) is ColdVmSelection
                and isinstance(root,Path) and isinstance(registry,PlannedImageRegistry)
                and isinstance(registry.leases,PlannedImageLeaseAuthority)
                and registry.grants is grants and grants._leases is registry.leases
                and isinstance(broker,CredentialBroker) and isinstance(consumer,VaultCredentialConsumer)
                and broker._identities is verifier and broker._grants is grants
                and broker._issuer is consumer.issuer and consumer.issuer._lease_store is not None
                and isinstance(store,ColdCaptureStore) and registry.leases.captures is store,
                'Actual current mTLS, original image lease/grant registry and revocable native credential owners required')
        self.authority,self.grants,self.verifier,self.transport_evidence=authority,grants,verifier,transport_evidence
        self.admitted,self.artifact,self.cold,self.root=admitted,deepcopy(artifact),cold,root
        self.registry,self.broker,self.consumer,self.ca_bundle,self.store=registry,broker,consumer,Path(ca_bundle),store
        self.artifact_digest,self.cold_digest=_digest(artifact),cold.sha256
        self.identity=verifier.verify(transport_evidence)
        self.context=TenantContext(admitted.organization_id,admitted.tenant_id)
        require((self.identity.organization_id,self.identity.tenant_id,self.identity.site_id)==
            (admitted.organization_id,admitted.tenant_id,PlanScope.from_record(cold.to_dict()['destination_scope']).site_id)
            and registry.evidence.cold==cold and registry.evidence.enrollment.subject!=self.identity.subject,
            'Native image enrollment or independent reader belongs to another tenant, site or immutable selection')

    def execute(self,*,capture_digest,disk_id,phase):
        require(self.verifier.verify(self.transport_evidence)==self.identity
                and _digest(self.artifact)==self.artifact_digest and self.cold.sha256==self.cold_digest,
                'The actual enrolled image peer or original protected purpose changed')
        source=verify(self.root)
        require(source['status']=='HASHES_MATCH' and source['commit']==self.artifact['sourceCommit']
                and verify_runtime(self.root)['status']=='RUNTIME_SOURCES_MATCH',
                'Actual image worker source differs from its approved installed artifact')
        plan,artifact=self.authority.require_current(self.admitted,self.artifact_digest,'SNAPSHOT_IMPORT')
        require(artifact==self.artifact,'The current image enrollment selects another protected artifact')
        self.cold.require_plan(plan,artifact)
        scope=PlanScope.from_record(self.cold.to_dict()['destination_scope'])
        lease=self.registry.leases.register_image(self.context,scope,job_id=self.admitted.job_id,
            disk_id=disk_id,capture_digest=capture_digest,phase=phase,worker_identity=self.identity)
        row=self.cold.disk(disk_id)['phases'][phase]
        grant=self.grants.issue_grant(self.context,self.identity,GrantRequest(self.admitted.job_id,
            row['step_id'],row['operation_id'],'SNAPSHOT_IMPORT',scope,row['lease_key'],lease.owner.epoch,
            timedelta(minutes=5)))
        command=WorkerCommandRuntime(self.authority,self.grants,self.verifier,self.transport_evidence,
                                    self.context,self.identity,grant)
        current=ColdImageAuthority(command,self.admitted,self.artifact,self.cold,self.root,
            registry=self.registry,lease=lease,disk_id=disk_id,phase=phase)
        return GlanceImageImporter(current,broker=self.broker,consumer=self.consumer,
                                   ca_bundle=self.ca_bundle,store=self.store).execute()


class ColdCaptureRuntimeBindings:
    """Fixed process-local enrolled owners; missing enrollment causes a hold."""
    def __init__(self,*,exports=(),image_workers=()):
        require(type(exports) is tuple and type(image_workers) is tuple
                and all(type(pair) is tuple and len(pair)==2 and type(pair[0]) is VsphereColdCapture
                    and type(pair[1]) is VsphereExportReadbackOwner for pair in exports)
                and all(type(owner) is ColdImageEnrollment for owner in image_workers),
                'Only the concrete snapshot/export-reader and image-enrollment owners may be registered')
        export_keys=[]
        for writer,reader in exports:
            authority=writer.authority
            require(type(authority) is ColdExportAuthority and reader.cold==authority.cold
                    and writer.store is reader.store and authority.registry.evidence is reader
                    and reader.enrollment.subject!=authority.command.identity.subject,
                    'Original export registry and independent actual native readback must share exact capture custody')
            export_keys.append((authority.admitted.job_id,authority.cold_digest))
        image_keys=[(owner.admitted.job_id,owner.cold_digest) for owner in image_workers]
        require(len(export_keys)==len(set(export_keys)) and len(image_keys)==len(set(image_keys)),
                'One cold purpose cannot have competing export or image enrollment owners')
        self.exports=MappingProxyType(dict(zip(export_keys,exports)))
        self.image_workers=MappingProxyType(dict(zip(image_keys,image_workers)))


class ColdCaptureActivities:
    def __init__(self,*,selector,bindings,directory):
        require(type(selector) is PostgresColdCaptureSelector and type(bindings) is ColdCaptureRuntimeBindings,
                'Actual current cold selector and concrete installed process enrollments required')
        self.selector,self.bindings=selector,bindings; self.directory=private_path(directory,directory=True)

    def _selected(self,request):
        require(type(request) is ColdCaptureStageRequest,'Fixed admitted cold-purpose stage required')
        return self.selector.require_input(request.input)

    def _proof(self,request,selected,status,facts):
        document={'format':'hosting-cold-purpose-stage-proof/1','job_id':request.input.admitted.job_id,
            'plan_digest':request.input.admitted.plan_digest,'selection_digest':request.input.selection_digest,
            'cold_selection_digest':selected.cold.sha256,'step_id':request.step_id,
            'capture_digest':facts['capture_digest'],'status':status,'facts':facts,
            'guest_boot_qualified':False,'production_activation':False}
        sha=c.digest(document); write_new(self.directory/(sha+'.json'),encoded(document))
        return ColdCaptureStageResult(request.input.admitted.job_id,request.step_id,status,sha,facts['capture_digest'])

    @staticmethod
    def _held(request,error):
        reason=('AUTHORITY_REVOKED' if isinstance(error,(AuthorityDenied,GrantDenied)) else
                'NATIVE_UNCERTAIN' if isinstance(error,RecoveryHeld) else 'RECOVERY_REQUIRED')
        return ColdCaptureStageResult(request.input.admitted.job_id,request.step_id,'HELD',
                                      capture_digest=request.capture_digest,reason_code=reason)

    def _owners(self,request,selected):
        key=(request.input.admitted.job_id,selected.cold.sha256)
        export=self.bindings.exports.get(key); images=self.bindings.image_workers.get(key)
        return export,images

    @activity.defn(name='cold_capture_export')
    def export_snapshot(self,request:ColdCaptureStageRequest)->ColdCaptureStageResult:
        try:
            selected=self._selected(request)
            require(request.step_id==selected.input.export_step_id and request.capture_digest is None,
                    'Only the exact original native snapshot export stage may dispatch')
            export,_images=self._owners(request,selected)
            require(export is not None,'The actual independently excluded source export worker is not enrolled')
            writer,reader=export; authority=writer.authority
            require(authority.admitted==request.input.admitted and authority.artifact==selected.artifact
                    and authority.cold==selected.cold,
                    'Source enrollment differs from this exact admitted complete cold purpose')
            sha=writer.capture(reader)
            capture=writer.store.load_verified(sha,selected.cold)
            return self._proof(request,selected,'CAPTURED',{'capture_digest':sha,
                'original_export_operation_id':selected.cold.to_dict()['export']['operation_id'],
                'native_lease_id':capture['nativeLeaseId'],'ready_observation_digest':capture['readyObservationDigest']})
        except Exception as error: return self._held(request,error)

    @activity.defn(name='cold_capture_import')
    def import_image(self,request:ColdCaptureStageRequest)->ColdCaptureStageResult:
        try:
            selected=self._selected(request)
            require(request.step_id in selected.input.image_steps and request.capture_digest is not None,
                    'Only an exact selected original image create/upload stage may dispatch')
            _export,owner=self._owners(request,selected)
            require(owner is not None and owner.admitted==request.input.admitted and owner.artifact==selected.artifact,
                    'The actual destination image worker is not enrolled for this exact original purpose')
            phases=[(disk['disk_id'],phase,row) for disk in selected.cold.to_dict()['disks']
                    for phase,row in disk['phases'].items() if row['step_id']==request.step_id]
            require(len(phases)==1,'The image stage does not identify one immutable disk and phase')
            disk,phase,row=phases[0]
            native_id=owner.execute(capture_digest=request.capture_digest,disk_id=disk,phase=phase)
            return self._proof(request,selected,'IMPORTED',{'capture_digest':request.capture_digest,
                'disk_id':disk,'phase':phase,'original_operation_id':row['operation_id'],'native_image_id':native_id})
        except Exception as error: return self._held(request,error)

    @activity.defn(name='cold_capture_verify')
    def verify_imported(self,request:ColdCaptureStageRequest)->ColdCaptureStageResult:
        try:
            selected=self._selected(request)
            require(not request.step_id and request.capture_digest is not None,
                    'Only the complete original image set may be independently inspected')
            export,owner=self._owners(request,selected)
            require(export is not None and owner is not None and owner.artifact==selected.artifact,
                    'The actual original capture and independent destination image readers must remain enrolled')
            writer,reader=export; capture=writer.store.load_verified(request.capture_digest,selected.cold)
            export_observation=reader.observe(request.capture_digest)
            context=owner.context; images=[]
            with owner.registry.connect() as connection,connection.cursor() as cursor:
                _tenant(cursor,context)
                original=writer.authority.registry._get(cursor,context,
                    selected.cold.to_dict()['export']['operation_id'])
                require(original.state=='RESOLVED' and original.outcome=='EFFECT_PRESENT'
                        and original.native_task_id==capture['nativeLeaseId'],
                        'Original native snapshot export has not been independently accepted')
                reader.verify_native_observation(cursor,original,export_observation)
                for disk in selected.cold.to_dict()['disks']:
                    operations=[]
                    for phase in ('CREATE','UPLOAD'):
                        row=disk['phases'][phase]
                        operation=owner.registry._get(cursor,context,row['operation_id'],lock=False)
                        require(operation.state=='RESOLVED' and operation.outcome=='EFFECT_PRESENT'
                                and operation.job_id==request.input.admitted.job_id,
                                'Every original image create and upload requires its separate accepted native readback')
                        operations.append(operation)
                    # Reconstruct only the immutable historical lease/inputs;
                    # this inspection does not extend an expired owner or issue
                    # a new writer grant. The independent reader is still live.
                    from provisioner.controlplane.reconciliation.planned_image import PlannedImageLease,PlannedResourceLease
                    scope=PlanScope.from_record(selected.cold.to_dict()['destination_scope'])
                    cursor.execute('SELECT selection_digest,request_digest,reservation_digest,worker_id,'
                        'owner_epoch,lease_expires_at,workload_id FROM hosting_controlplane.planned_resource_ownership '
                        'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s AND resource_id=%s',
                        (context.organization_id,context.tenant_id,request.input.admitted.job_id,disk['logical_image_id']))
                    stored=cursor.fetchone(); require(stored is not None,'Original image owner custody is missing')
                    owned=PlannedResourceLease(context.organization_id,context.tenant_id,request.input.admitted.job_id,
                        disk['logical_image_id'],'image',*stored[:3],scope,stored[6],*stored[3:6])
                    lease=PlannedImageLease(owned,disk['disk_id'],'UPLOAD',operations[1].step_id,
                        operations[1].request_digest,request.capture_digest)
                    # One observer connection is used throughout this original
                    # ledger transaction; no competing successful journal exists.
                    owner.registry.evidence.enrollment.require_current(cursor=cursor)
                    native_id,facts,inputs=owner.registry.evidence._read(cursor,context,lease)
                    require(inputs['capture_digest']==request.capture_digest and facts['status']=='active',
                            'The final active native image changed its accepted original captured byte extent')
                    images.append({'disk_id':disk['disk_id'],'native_image_id':native_id,
                        'original_operation_ids':[item.operation_id for item in operations],
                        'output_sha256':inputs['output_sha256'],'output_bytes':inputs['output_bytes']})
            return self._proof(request,selected,'VERIFIED',{'capture_digest':request.capture_digest,
                'export_observation_digest':export_observation.evidence_digest,'images':images})
        except Exception as error: return self._held(request,error)

    @property
    def activities(self): return (self.export_snapshot,self.import_image,self.verify_imported)
