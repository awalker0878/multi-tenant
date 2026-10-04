"""Selected private Glance images through the original planned/native owners.

The immutable logical image has no pre-created UUID. CREATE and UPLOAD have
separate B10 mappings and original B11 intents. A response UUID alone resolves
nothing; another currently enrolled native reader must verify it and its bytes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from types import MappingProxyType
from datetime import timedelta
import hashlib
import json
import os
import stat

from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.worker.grants import PostgresWorkerGrants, VerifiedWorkerIdentity
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import require
from provisioner.migration.cold_capture import ColdCaptureStore, VsphereExportReadbackOwner
from provisioner.migration.cold_selection import ColdVmSelection, FileColdSelectionStore, DRIVER, PHASES
from .planned import PlannedLeaseAuthority, PlannedResourceLease, reservation_identity_digest
from .staged_resources import StagedPlannedLeaseAuthority
from .registry import (NativeObservation, NativeOperationRegistry, OperationConflict,
                       RecoveryHeld, _fresh, _key, _row, _SELECT)


def image_bytes(path,expected_sha,expected_bytes):
    """Hash one sealed checked extent once for both native secure hash profiles."""
    descriptor = os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size == expected_bytes
                and before.st_mode & 0o777 == 0o400, 'One sealed private converted image extent required')
        sha256,sha512 = hashlib.sha256(),hashlib.sha512(); count = 0
        with os.fdopen(descriptor,'rb',closefd=False) as stream:
            while True:
                chunk = stream.read(min(1048576,expected_bytes-count+1))
                if not chunk: break
                count += len(chunk); require(count <= expected_bytes, 'Converted image grew during digest verification')
                sha256.update(chunk); sha512.update(chunk)
        after = os.fstat(descriptor)
        require(count == expected_bytes and (before.st_size,before.st_mtime_ns,before.st_ctime_ns) ==
                (after.st_size,after.st_mtime_ns,after.st_ctime_ns) and sha256.hexdigest() == expected_sha,
                'Converted image changed during original request binding')
        return sha512.hexdigest()
    finally:
        os.close(descriptor)


def image_input(cold,capture_digest,capture,store,disk_id):
    require(isinstance(cold,ColdVmSelection) and isinstance(store,ColdCaptureStore)
            and capture['coldSelectionDigest'] == cold.sha256,
            'Exact retained original native capture and selected image required')
    path,converted = store.image(capture_digest,cold,disk_id); disk = cold.disk(disk_id)
    sha512 = image_bytes(path,converted['outputSha256'],converted['outputBytes'])
    value = cold.to_dict()
    return {'format':'hosting-planned-glance-image-input/1','cold_selection_digest':cold.sha256,
        'source_operation_id':value['export']['operation_id'],'capture_digest':capture_digest,
        'source_snapshot_moid':value['vm']['snapshot_moid'],'disk_id':disk_id,'device_key':disk['device_key'],
        'nfc_key':disk['nfc_key'],'output_sha256':converted['outputSha256'],'output_sha512':sha512,
        'output_bytes':converted['outputBytes'],'virtual_bytes':converted['virtualSize'],
        'image_name':disk['logical_image_id']}


def image_request_digest(cold,scope,resource_id,inputs,bundle):
    return c.digest({'format':'hosting-planned-glance-image-request/1','scope':asdict(scope),
        'resource_id':resource_id,'cold_selection_digest':cold.sha256,'inputs':inputs,'resource_bundle_sha256':bundle.digest})


def image_phase_digest(owner_digest,cold,disk_id,phase):
    require(phase in PHASES, 'A separately selected image phase required')
    return c.digest({'format':'hosting-planned-glance-image-action/1','request_digest':owner_digest,
                     'phase':phase,'action':cold.disk(disk_id)['phases'][phase]})


@dataclass(frozen=True)
class PlannedImageLease:
    owner: PlannedResourceLease
    disk_id: str
    phase: str
    step_id: str
    request_digest: str
    capture_digest: str

    def __post_init__(self):
        require(isinstance(self.owner,PlannedResourceLease) and self.owner.resource_kind == 'image'
                and self.phase in PHASES and all(_key(value) for value in (self.disk_id,self.step_id))
                and c.HEX.fullmatch(self.request_digest) and c.HEX.fullmatch(self.capture_digest),
                'Exact original logical image owner/action projection required')


@dataclass(frozen=True)
class PlannedImageOperation:
    operation_id: str
    job_id: str
    grant_id: str
    step_id: str
    lease_key: str
    resource_id: str
    request_digest: str
    worker_id: str
    owner_epoch: int
    phase: str
    state: str
    outcome: str | None


@dataclass(frozen=True)
class NativeImageObservation:
    observation: NativeObservation
    native_image_id: str

    def __post_init__(self):
        require(isinstance(self.observation,NativeObservation) and type(self.native_image_id) is str
                and c.UUID.fullmatch(self.native_image_id), 'Actual independently observed Glance UUID required')


_INPUT_FIELDS = ('cold_selection_digest','source_operation_id','capture_digest','source_snapshot_moid',
                 'disk_id','device_key','nfc_key','output_sha256','output_sha512','output_bytes','virtual_bytes','image_name')


class PlannedImageLeaseAuthority(StagedPlannedLeaseAuthority):
    """Fixed image mux over the same current bundle, resource and B10 owners."""
    def __init__(self,connect,*,resources,selections,bundle_lookup,staged_resources=None,
                 cold_selections=None,captures=None,export_reader=None,**options):
        super().__init__(connect,resources=resources,selections=selections,bundle_lookup=bundle_lookup,
                         staged_resources={} if staged_resources is None else staged_resources,**options)
        self.cold_selections,self.captures=None,None
        self.export_readers=MappingProxyType({}); self._cold_enrolled=False
        if any(value is not None for value in (cold_selections,captures,export_reader)):
            self.enroll_cold_resources(cold_selections,captures,export_reader)

    def enroll_cold_resources(self,cold_selections,captures,export_reader):
        """One explicit native enrollment before sealing the shared B10 owner."""
        if type(export_reader) is VsphereExportReadbackOwner:
            export_reader={export_reader.enrollment.admitted.job_id:export_reader}
        with self._enrollment_lock:
            require(not self._worker_sealed and not self._cold_enrolled
                    and type(cold_selections) is FileColdSelectionStore and type(captures) is ColdCaptureStore
                    and type(export_reader) in {dict,MappingProxyType} and export_reader
                    and all(type(reader) is VsphereExportReadbackOwner and reader.store is captures
                        and _key(job_id) for job_id,reader in export_reader.items()),
                    'Concrete immutable cold readers and original byte custody must be enrolled once before worker registration')
            self.cold_selections,self.captures=cold_selections,captures
            self.export_readers=MappingProxyType(dict(export_reader)); self._cold_enrolled=True

    def _require_selected_driver(self,execution):
        if type(execution) is dict and execution.get('driver') == DRIVER:
            require(execution.keys() == {'format','driver','artifactDigest'} and
                    execution['format'] == 'hosting-execution-selection/1' and c.HEX.fullmatch(execution['artifactDigest']),
                    'Exact fixed cold execution selection required')
        else:
            super()._require_selected_driver(execution)

    def register(self,context,scope,**options):
        # The cold subclass cannot borrow the earlier Linux VM/service writer.
        with self._connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context); _job,plan,_bundle = self._bundle(cursor,context,options['job_id'])
            if plan['spec']['execution']['driver'] == DRIVER:
                raise OperationConflict('Cold lower selection admits only its explicit image register_image owner')
        return super().register(context,scope,**options)

    def _cold(self,cursor,context,job_id,capture_digest,disk_id):
        require(self._cold_enrolled and job_id in self.export_readers,
                'This actual cold job has no commissioned independent export/captured-byte custody owner')
        job,plan,bundle = self._bundle(cursor,context,job_id)
        artifact = self.selections.load_verified(bundle.selection_digest)
        cold = self.cold_selections.load_verified(artifact['coldCaptureSelectionDigest'])
        cold.require_plan(plan,artifact)
        export_reader=self.export_readers[job_id]
        require(export_reader.cold == cold, 'Independent export reader belongs to another cold selection')
        capture = self.captures.load_verified(capture_digest,cold)
        value = cold.to_dict(); row = cold.disk(disk_id)
        cursor.execute(f'SELECT {_SELECT} FROM hosting_controlplane.native_operation_intents '
            'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s FOR SHARE',
            (context.organization_id,context.tenant_id,value['export']['operation_id']))
        stored = cursor.fetchone(); require(stored is not None, 'The original native export is unavailable')
        original = _row(stored)
        require(original.job_id == job_id and original.binding == cold.binding()
                and original.workload_id == value['workload_id'] and original.operation_kind == 'SNAPSHOT_EXPORT'
                and original.state == 'RESOLVED' and original.outcome == 'EFFECT_PRESENT'
                and original.native_task_id == capture['nativeLeaseId'],
                'Only the original independently accepted native export may supply image bytes')
        cursor.execute('SELECT observation_id,evidence_digest,observer_subject,native_task_id,outcome,'
            'native_quiesced,observed_at FROM hosting_controlplane.native_operation_observations '
            'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s AND outcome=\'EFFECT_PRESENT\' '
            'ORDER BY recorded_at DESC LIMIT 1',
            (context.organization_id,context.tenant_id,original.operation_id))
        observation = cursor.fetchone(); require(observation is not None, 'Original independent export observation is missing')
        native = NativeObservation(*observation)
        export_reader.verify_native_observation(cursor,original,native)
        from provisioner.execution.run_files import load_private
        document = load_private(export_reader.directory/(native.evidence_digest+'.json'))
        require(document['captureDigest'] == capture_digest,
                'Image bytes differ from the original independently observed native export')
        inputs = image_input(cold,capture_digest,capture,self.captures,disk_id)
        pools = [pool for pool in bundle.pools if pool.scope == job.destination
                 and pool.catalog['pool_id'] == value['image_pool_id']]
        require(len(pools) == 1 and pools[0].inputs is None and 'glance-image-staging' in pools[0].capabilities
                and pools[0].staging.storage_gb*10**9 >= sum(disk['max_output_bytes'] for disk in value['disks']),
                'Every selected private image must remain charged to its commissioned native image staging pool')
        self.resources._require_accounted(bundle)
        return job,plan,bundle,cold,inputs,row

    def register_image(self,context,scope,*,job_id,disk_id,capture_digest,phase,worker_identity,ttl_seconds=300):
        require(phase in PHASES and isinstance(worker_identity,VerifiedWorkerIdentity)
                and type(ttl_seconds) is int and 1 <= ttl_seconds <= 300 and _key(job_id) and _key(disk_id)
                and type(capture_digest) is str and c.HEX.fullmatch(capture_digest),
                'Exact selected original image action and independently verified worker required')
        with self._connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            job,plan,bundle,cold,inputs,row = self._cold(cursor,context,job_id,capture_digest,disk_id)
            require(scope == job.destination and (worker_identity.organization_id,worker_identity.tenant_id,
                    worker_identity.site_id) == (context.organization_id,context.tenant_id,scope.site_id),
                    'The image belongs to another approved destination or enrolled site')
            from provisioner.controlplane.conversion.handover import require_write_admission
            require_write_admission(cursor,context,security_domain_id=scope.security_domain_id,workload_id=bundle.workload_id)
            accounted = self.resources._require_accounted(bundle)
            reservation_digest = reservation_identity_digest(accounted['receipts'])
            request = image_request_digest(cold,scope,row['logical_image_id'],inputs,bundle)
            now = NativeOperationRegistry._clock(cursor)
            require(worker_identity.expires_at > now, 'The image writer certificate expired')
            expires = min(now+timedelta(seconds=ttl_seconds),worker_identity.expires_at,
                *(c.timestamp(receipt['lease_expires_at']) for receipt in accounted['receipts']
                  if receipt['lease_expires_at'] is not None))
            cursor.execute('INSERT INTO hosting_controlplane.planned_resource_ownership '
                '(organization_id,tenant_id,job_id,resource_id,selection_digest,request_digest,reservation_digest,'
                'resource_kind,platform_family,endpoint_id,native_scope_id,site_id,security_domain_id,workload_id,'
                'worker_id,owner_epoch,lease_expires_at) VALUES (%s,%s,%s,%s,%s,%s,%s,\'image\',%s,%s,%s,%s,%s,%s,%s,1,%s) '
                'ON CONFLICT DO NOTHING',
                (context.organization_id,context.tenant_id,job_id,row['logical_image_id'],bundle.selection_digest,
                 request,reservation_digest,scope.platform_family,scope.endpoint_id,scope.native_scope_id,
                 scope.site_id,scope.security_domain_id,bundle.workload_id,worker_identity.subject,expires))
            cursor.execute('SELECT worker_id,owner_epoch,lease_expires_at,request_digest,reservation_digest '
                'FROM hosting_controlplane.planned_resource_ownership WHERE organization_id=%s AND tenant_id=%s '
                'AND job_id=%s AND resource_id=%s',
                (context.organization_id,context.tenant_id,job_id,row['logical_image_id']))
            stored = cursor.fetchone()
            require(stored is not None and stored[0] == worker_identity.subject and stored[2] > now
                    and stored[3:] == (request,reservation_digest), 'The image has another original request/writer or expired owner')
            owner = PlannedResourceLease(context.organization_id,context.tenant_id,job_id,row['logical_image_id'],
                'image',bundle.selection_digest,request,reservation_digest,scope,bundle.workload_id,*stored[:3])
            names = ','.join(_INPUT_FIELDS)
            cursor.execute('INSERT INTO hosting_controlplane.planned_image_inputs '
                '(organization_id,tenant_id,job_id,resource_id,'+names+',request_digest) '
                'VALUES ('+','.join(['%s']*(5+len(_INPUT_FIELDS)))+') ON CONFLICT DO NOTHING',
                (context.organization_id,context.tenant_id,job_id,owner.resource_id,
                 *(inputs[field] for field in _INPUT_FIELDS),request))
            cursor.execute('SELECT '+names+',request_digest FROM hosting_controlplane.planned_image_inputs '
                'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s AND resource_id=%s',
                (context.organization_id,context.tenant_id,job_id,owner.resource_id))
            require(cursor.fetchone() == tuple(inputs[field] for field in _INPUT_FIELDS)+(request,),
                    'The original image bytes, captured lineage or import request changed')
            action = row['phases'][phase]; phase_digest = image_phase_digest(request,cold,disk_id,phase)
            cursor.execute('INSERT INTO hosting_controlplane.native_operation_leases '
                '(organization_id,tenant_id,lease_key,job_id,operation_id,platform_family,endpoint_id,native_scope_id,'
                'resource_kind,native_id,planned_resource_id,site_id,security_domain_id,worker_id,owner_epoch,expires_at) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,\'image\',NULL,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                (context.organization_id,context.tenant_id,action['lease_key'],job_id,action['operation_id'],
                 scope.platform_family,scope.endpoint_id,scope.native_scope_id,owner.resource_id,scope.site_id,
                 scope.security_domain_id,owner.worker_id,owner.epoch,owner.expires_at))
            cursor.execute('INSERT INTO hosting_controlplane.planned_image_bindings '
                '(organization_id,tenant_id,lease_key,job_id,resource_id,step_id,phase,request_digest) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                (context.organization_id,context.tenant_id,action['lease_key'],job_id,owner.resource_id,
                 action['step_id'],phase,phase_digest))
            self.require_current(cursor,context,lease_key=action['lease_key'],lease_epoch=owner.epoch,
                job_id=job_id,operation_id=action['operation_id'],scope=scope,worker_subject=owner.worker_id)
            return PlannedImageLease(owner,disk_id,phase,action['step_id'],phase_digest,capture_digest)

    def require_current(self,cursor,context,*,lease_key,lease_epoch,job_id,operation_id,scope,worker_subject):
        cursor.execute('SELECT resource_kind FROM hosting_controlplane.native_operation_leases '
            'WHERE organization_id=%s AND tenant_id=%s AND lease_key=%s',
            (context.organization_id,context.tenant_id,lease_key))
        kind = cursor.fetchone()
        if kind != ('image',):
            return super().require_current(cursor,context,lease_key=lease_key,lease_epoch=lease_epoch,
                job_id=job_id,operation_id=operation_id,scope=scope,worker_subject=worker_subject)
        _tenant(cursor,context)
        cursor.execute('SELECT * FROM hosting_controlplane.lock_planned_worker_scope(%s,%s,%s)',
                       (context.organization_id,context.tenant_id,lease_key))
        stored = cursor.fetchone(); now = NativeOperationRegistry._clock(cursor)
        require(stored is not None and stored[:2] == (job_id,operation_id) and stored[3] == 'image'
                and tuple(stored[4:9]) == (scope.platform_family,scope.endpoint_id,scope.native_scope_id,
                                           scope.site_id,scope.security_domain_id)
                and stored[9:11] == (worker_subject,lease_epoch) and min(stored[11:13]) > now,
                'The original image owner/lease scope changed or expired')
        cursor.execute('SELECT i.capture_digest,i.disk_id,b.step_id,b.phase,b.request_digest FROM '
            'hosting_controlplane.planned_image_bindings b JOIN hosting_controlplane.planned_image_inputs i '
            'ON (i.organization_id,i.tenant_id,i.job_id,i.resource_id)='
            '(b.organization_id,b.tenant_id,b.job_id,b.resource_id) '
            'WHERE b.organization_id=%s AND b.tenant_id=%s AND b.lease_key=%s',
            (context.organization_id,context.tenant_id,lease_key))
        action = cursor.fetchone(); require(action is not None, 'Original selected image action is missing')
        _job,_plan,bundle,cold,inputs,row = self._cold(cursor,context,job_id,action[0],action[1])
        request = image_request_digest(cold,scope,row['logical_image_id'],inputs,bundle)
        require(stored[13:16] == (bundle.selection_digest,request,
                reservation_identity_digest(self.resources._require_accounted(bundle)['receipts']))
                and stored[2] == row['logical_image_id'] and action[2] == row['phases'][action[3]]['step_id']
                and lease_key == row['phases'][action[3]]['lease_key']
                and operation_id == row['phases'][action[3]]['operation_id']
                and action[4] == image_phase_digest(request,cold,action[1],action[3]),
                'The exact original image bytes, reservation, action or selection changed')

    def require_operation(self,cursor,context,*,lease_key,operation_kind,step_id):
        cursor.execute('SELECT b.step_id FROM hosting_controlplane.planned_image_bindings b '
            'WHERE b.organization_id=%s AND b.tenant_id=%s AND b.lease_key=%s',
            (context.organization_id,context.tenant_id,lease_key))
        row = cursor.fetchone()
        if row is not None:
            require(operation_kind == 'SNAPSHOT_IMPORT' and row == (step_id,),
                    'An image action cannot borrow VM creation, cleanup or another step authority')
            return
        return super().require_operation(cursor,context,lease_key=lease_key,operation_kind=operation_kind,step_id=step_id)


class PlannedImageRegistry:
    def __init__(self,connect,*,leases,grants,evidence):
        from provisioner.migration.glance_image import GlanceImageReadbackOwner
        require(callable(connect) and isinstance(leases,PlannedImageLeaseAuthority)
                and isinstance(grants,PostgresWorkerGrants) and isinstance(evidence,GlanceImageReadbackOwner),
                'Actual image lease/current grant and separate native Glance reader required')
        self.connect,self.leases,self.grants,self.evidence = connect,leases,grants,evidence

    @staticmethod
    def _get(cursor,context,operation_id,*,lock=True):
        cursor.execute('SELECT n.operation_id,n.job_id,n.grant_id,n.step_id,n.lease_key,n.planned_resource_id,'
            'n.request_digest,n.worker_id,n.owner_epoch,b.phase,n.state,n.outcome FROM '
            'hosting_controlplane.native_operation_intents n JOIN hosting_controlplane.planned_image_bindings b '
            'ON (b.organization_id,b.tenant_id,b.lease_key)=(n.organization_id,n.tenant_id,n.lease_key) '
            'WHERE n.organization_id=%s AND n.tenant_id=%s AND n.operation_id=%s '
            "AND n.operation_kind='SNAPSHOT_IMPORT' AND n.resource_kind='image'"+
            (' FOR UPDATE OF n' if lock else ''),(context.organization_id,context.tenant_id,operation_id))
        row = cursor.fetchone(); require(row is not None, 'The original image native intent is unavailable')
        return PlannedImageOperation(*row)

    def _grant(self,cursor,context,lease,operation,identity):
        require(isinstance(lease,PlannedImageLease) and
                (operation.job_id,operation.resource_id,operation.step_id,operation.phase,operation.request_digest,
                 operation.worker_id,operation.owner_epoch) ==
                (lease.owner.job_id,lease.owner.resource_id,lease.step_id,lease.phase,lease.request_digest,
                 lease.owner.worker_id,lease.owner.epoch), 'Image intent differs from its original immutable action lease')
        return self.grants.verify_intent(cursor,context,grant_id=operation.grant_id,job_id=operation.job_id,
            step_id=operation.step_id,operation_id=operation.operation_id,operation_kind='SNAPSHOT_IMPORT',
            operation_scope=lease.owner.scope,worker_identity=identity,lease_key=operation.lease_key,lease_epoch=lease.owner.epoch)

    def prepare(self,context,lease,*,grant,identity):
        proposed = PlannedImageOperation(grant.operation_id,lease.owner.job_id,grant.grant_id,lease.step_id,
            grant.lease_key,lease.owner.resource_id,lease.request_digest,lease.owner.worker_id,lease.owner.epoch,
            lease.phase,'PREPARED',None)
        with self.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context); self._grant(cursor,context,lease,proposed,identity); owner = lease.owner
            cursor.execute('INSERT INTO hosting_controlplane.native_operation_intents '
                '(organization_id,tenant_id,operation_id,job_id,grant_id,step_id,lease_key,platform_family,endpoint_id,'
                'native_scope_id,resource_kind,native_id,planned_resource_id,workload_id,security_domain_id,worker_id,'
                'owner_epoch,operation_kind,request_digest) VALUES '
                '(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,\'image\',NULL,%s,%s,%s,%s,%s,\'SNAPSHOT_IMPORT\',%s) '
                'ON CONFLICT DO NOTHING',
                (context.organization_id,context.tenant_id,grant.operation_id,owner.job_id,grant.grant_id,lease.step_id,
                 grant.lease_key,owner.scope.platform_family,owner.scope.endpoint_id,owner.scope.native_scope_id,
                 owner.resource_id,owner.workload_id,owner.scope.security_domain_id,owner.worker_id,owner.epoch,lease.request_digest))
            original = self._get(cursor,context,grant.operation_id)
            require(replace(original,state='PREPARED',outcome=None) == proposed,
                    'This image operation ID already belongs to another original attempt')
            return original

    def claim_once(self,context,lease,operation_id,identity):
        with self.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context); before = self._get(cursor,context,operation_id,lock=False)
            self._grant(cursor,context,lease,before,identity); original = self._get(cursor,context,operation_id)
            require(original == before, 'Original image intent changed while acquiring current authority')
            if original.state != 'PREPARED': return False
            cursor.execute("UPDATE hosting_controlplane.native_operation_intents SET state='IN_FLIGHT',"
                'updated_at=clock_timestamp() WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s',
                (context.organization_id,context.tenant_id,operation_id))
            return True

    def mark_uncertain(self,context,operation_id,worker_id):
        with self.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context); original = self._get(cursor,context,operation_id)
            require(original.worker_id == worker_id, 'Image uncertainty belongs to another original worker')
            if original.state == 'UNCERTAIN': return
            require(original.state == 'IN_FLIGHT', 'Only a claimed image request may become uncertain')
            cursor.execute("UPDATE hosting_controlplane.native_operation_intents SET state='UNCERTAIN',"
                'updated_at=clock_timestamp() WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s',
                (context.organization_id,context.tenant_id,operation_id))

    def retain_created(self,context,operation_id,worker_id,native_image_id,native_request_id):
        require(type(native_image_id) is str and c.UUID.fullmatch(native_image_id)
                and type(native_request_id) is str and native_request_id.startswith('req-')
                and c.UUID.fullmatch(native_request_id[4:]), 'Actual native Glance response UUID and request ID required')
        with self.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context); original = self._get(cursor,context,operation_id)
            require(original.phase == 'CREATE' and original.worker_id == worker_id
                    and original.state in {'IN_FLIGHT','UNCERTAIN'}, 'Native receipt belongs to another original create attempt')
            cursor.execute('INSERT INTO hosting_controlplane.planned_image_receipts '
                '(organization_id,tenant_id,operation_id,job_id,resource_id,native_image_id,native_request_id) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                (context.organization_id,context.tenant_id,operation_id,original.job_id,original.resource_id,
                 native_image_id,native_request_id))
            require(self._receipt(cursor,context,original.job_id,original.resource_id) == (native_image_id,native_request_id),
                    'An original Glance response identity cannot be replaced')

    @staticmethod
    def _receipt(cursor,context,job_id,resource_id):
        cursor.execute('SELECT native_image_id,native_request_id FROM hosting_controlplane.planned_image_receipts '
            'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s AND resource_id=%s',
            (context.organization_id,context.tenant_id,job_id,resource_id))
        return cursor.fetchone()

    def native_image(self,context,lease):
        with self.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            receipt = self._receipt(cursor,context,lease.owner.job_id,lease.owner.resource_id)
            require(receipt is not None, 'Original Glance UUID is unknown; never discover an image by name')
            if lease.phase == 'UPLOAD':
                cursor.execute('SELECT n.state,n.outcome FROM hosting_controlplane.native_operation_intents n '
                    'JOIN hosting_controlplane.planned_image_receipts r ON '
                    '(r.organization_id,r.tenant_id,r.operation_id)=(n.organization_id,n.tenant_id,n.operation_id) '
                    'WHERE r.organization_id=%s AND r.tenant_id=%s AND r.job_id=%s AND r.resource_id=%s',
                    (context.organization_id,context.tenant_id,lease.owner.job_id,lease.owner.resource_id))
                require(cursor.fetchone() == ('RESOLVED','EFFECT_PRESENT'),
                        'Original image creation has not been independently accepted')
            return receipt[0]

    @staticmethod
    def _inputs(cursor,context,lease):
        cursor.execute('SELECT '+','.join(_INPUT_FIELDS)+',request_digest FROM '
            'hosting_controlplane.planned_image_inputs WHERE organization_id=%s AND tenant_id=%s '
            'AND job_id=%s AND resource_id=%s',
            (context.organization_id,context.tenant_id,lease.owner.job_id,lease.owner.resource_id))
        row = cursor.fetchone()
        require(row is not None and row[-1] == lease.owner.request_digest
                and row[2] == lease.capture_digest and row[4] == lease.disk_id,
                'The original protected image inputs differ from their immutable owner')
        return dict(zip(_INPUT_FIELDS,row[:-1]))

    def inputs(self,context,lease):
        with self.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            return self._inputs(cursor,context,lease)

    def acknowledge(self,context,lease,operation_id,identity,observed):
        require(isinstance(observed,NativeImageObservation), 'Actual separately collected native image observation required')
        with self.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context); before = self._get(cursor,context,operation_id,lock=False)
            self._grant(cursor,context,lease,before,identity); original = self._get(cursor,context,operation_id)
            native = observed.observation; now = NativeOperationRegistry._clock(cursor)
            require(original == before and original.state == 'IN_FLIGHT' and native.native_task_id is None
                    and native.outcome == 'EFFECT_PRESENT' and native.native_quiesced
                    and native.observer_subject != original.worker_id and _fresh(native.observed_at,now),
                    'Only a current original image action with independent quiesced native readback can resolve')
            receipt = self._receipt(cursor,context,original.job_id,original.resource_id)
            require(receipt is not None and receipt[0] == observed.native_image_id,
                    'The native image differs from the original genuine create response UUID')
            self.evidence.verify_image_observation(cursor,context,lease,original,observed)
            self._grant(cursor,context,lease,original,identity)
            cursor.execute('INSERT INTO hosting_controlplane.native_operation_observations '
                '(organization_id,tenant_id,observation_id,operation_id,evidence_digest,observer_subject,native_task_id,'
                'outcome,native_quiesced,observed_at,created_native_image_id) VALUES '
                '(%s,%s,%s,%s,%s,%s,NULL,%s,%s,%s,%s)',
                (context.organization_id,context.tenant_id,native.observation_id,operation_id,native.evidence_digest,
                 native.observer_subject,native.outcome,native.native_quiesced,native.observed_at,observed.native_image_id))
            cursor.execute("UPDATE hosting_controlplane.native_operation_intents SET state='UNCERTAIN',"
                'updated_at=clock_timestamp() WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s',
                (context.organization_id,context.tenant_id,operation_id))
            cursor.execute("UPDATE hosting_controlplane.native_operation_intents SET state='RESOLVED',outcome='EFFECT_PRESENT',"
                'resolution_evidence_digest=%s,updated_at=clock_timestamp() '
                'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s',
                (native.evidence_digest,context.organization_id,context.tenant_id,operation_id))
            return observed.native_image_id
