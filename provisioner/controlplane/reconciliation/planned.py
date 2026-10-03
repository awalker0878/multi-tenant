"""Planned OpenStack creation through the existing B10/B11 owner and journal.

An uncreated deployment has a logical planned identity, never an invented native
ID. Creation is claimed once in native_operation_intents. Its returned IDs become
native observations only after an independent reader verifies the selected
children; timeout and expiry preserve that one uncertain attempt.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
import json

from provisioner.allocations.transactions import ResourceBundle, ResourceTransactions
from provisioner.controlplane.authority import postgres as authority_postgres
from provisioner.controlplane.authority.model import PlanScope, VerifiedPrincipal
from provisioner.controlplane.authority.service import EXECUTION_OPERATOR
from provisioner.controlplane.jobs.repository import (
    _JOB_SELECT, _digest, _ensure_plan, _job, _payload_from_job, _tenant)
from provisioner.controlplane.persistence import NativeBinding, TenantContext
from provisioner.controlplane.worker.grants import VerifiedWorkerIdentity
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.execution import readback_core as c
from .registry import (
    NativeLeaseAuthority, NativeObservation, NativeOperationRegistry, OperationConflict,
    OwnerRecoveryEvidence, RecoveryHeld, _fresh, _identity, _key, _text)


def deployment_id(bundle: ResourceBundle, scope: PlanScope) -> str:
    return 'deployment-'+c.digest([bundle.digest,asdict(scope)])[:32]


def creation_request_digest(bundle: ResourceBundle, scope: PlanScope, resource_id: str) -> str:
    pools=[pool for pool in bundle.pools if pool.scope==scope and pool.inputs is not None]
    if len(pools)!=1:
        raise OperationConflict('One immutable workload pool must own this creation scope')
    inputs=pools[0].inputs
    if resource_id==deployment_id(bundle,scope):
        selected=inputs
    elif resource_id in inputs['members']:
        selected=inputs|{'members':{resource_id:inputs['members'][resource_id]}}
    else:
        raise OperationConflict('Planned creation child is absent from the reviewed workload inputs')
    return c.digest({'format':'hosting-planned-creation-request/1',
                     'resource_id':resource_id,'scope':asdict(scope),'inputs':selected,
                     'resource_bundle_sha256':bundle.digest})


def creation_children(bundle: ResourceBundle, scope: PlanScope, resource_id: str) -> tuple[str, ...]:
    """Select reviewed logical children without giving them native identities."""
    creation_request_digest(bundle,scope,resource_id)
    inputs=next(pool.inputs for pool in bundle.pools if pool.scope==scope and pool.inputs is not None)
    return tuple(sorted(inputs['members'])) if resource_id==deployment_id(bundle,scope) else (resource_id,)


def require_creation_inputs(bundle: ResourceBundle, scope: PlanScope, resource_id: str, inputs: dict) -> None:
    """Bind the saved Terraform plan's complete inputs to commissioned demand."""
    pools=[pool for pool in bundle.pools if pool.scope==scope and pool.inputs is not None]
    creation_request_digest(bundle,scope,resource_id)
    selected=pools[0].inputs
    if resource_id!=deployment_id(bundle,scope):
        selected=selected|{'members':{resource_id:selected['members'][resource_id]}}
    if inputs!=selected:
        raise OperationConflict('Saved Terraform inputs differ from the immutable capacity/workload selection')


@dataclass(frozen=True)
class PlannedResourceLease:
    organization_id: str
    tenant_id: str
    job_id: str
    resource_id: str
    resource_kind: str
    selection_digest: str
    request_digest: str
    reservation_digest: str
    scope: PlanScope
    workload_id: str
    worker_id: str
    epoch: int
    expires_at: datetime


@dataclass(frozen=True)
class PlannedCreationOperation:
    operation_id: str
    job_id: str
    grant_id: str
    step_id: str
    lease_key: str
    resource_id: str
    resource_kind: str
    scope: PlanScope
    workload_id: str
    worker_id: str
    owner_epoch: int
    request_digest: str
    state: str
    native_task_id: str | None
    outcome: str | None

    @property
    def operation_kind(self):
        return 'VM_CREATE'


@dataclass(frozen=True)
class NativeCreationObservation:
    observation: NativeObservation
    bindings: tuple[NativeBinding, ...]

    def __post_init__(self):
        if (not isinstance(self.observation,NativeObservation)
                or not isinstance(self.bindings,tuple)
                or any(not isinstance(binding,NativeBinding) for binding in self.bindings)
                or len({binding.key() for binding in self.bindings})!=len(self.bindings)
                or (self.observation.outcome=='EFFECT_PRESENT')!=bool(self.bindings)):
            raise ValueError('Observed creation requires exact independently verified native bindings')


class PlannedLeaseAuthority:
    """B10 lease lookup, with actual existing-native lookup on the same owner.

    bundle_lookup(admitted, protected_artifact) must load the protected immutable
    selection, not queue paths. The receipt comparison reads the existing SQLite
    capacity owner inside the already-locked PostgreSQL grant transaction.
    """
    def __init__(self, connect, *, resources: ResourceTransactions, selections,
                 bundle_lookup, authority=authority_postgres):
        if (not callable(connect) or not isinstance(resources,ResourceTransactions)
                or not callable(getattr(selections,'load_verified',None))
                or not callable(bundle_lookup)
                or not callable(getattr(authority,'revalidate_start',None))):
            raise TypeError('Current PostgreSQL, protected bundle custody and actual resource owner required')
        self._connect,self.resources,self.selections=connect,resources,selections
        self.bundle_lookup,self.authority=bundle_lookup,authority
        self.native=NativeLeaseAuthority(connect)

    def _bundle(self,cursor,context,job_id):
        cursor.execute('SELECT hosting_controlplane.lock_job_scope(%s, %s, %s)',
                       (context.organization_id,context.tenant_id,job_id))
        if cursor.fetchone()!=(True,):
            raise OperationConflict('Current scoped job required for planned creation')
        cursor.execute(f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                       'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s',
                       (context.organization_id,context.tenant_id,job_id))
        row=cursor.fetchone()
        if row is None:
            raise OperationConflict('Current scoped job required for planned creation')
        job=_job(row)
        if job.status not in {'STARTED','RUNNING'}:
            raise OperationConflict('Planned native creation requires a running job')
        now=NativeOperationRegistry._clock(cursor)
        self.authority.revalidate_start(cursor,job,now)
        cursor.execute('SELECT revision, record_digest, record_json FROM '
                       'hosting_controlplane.enterprise_records WHERE organization_id=%s '
                       "AND tenant_id=%s AND record_kind='MigrationPlan' AND record_id=%s",
                       (context.organization_id,context.tenant_id,job.plan_id))
        plan=_ensure_plan(cursor.fetchone(),context,job)
        execution=plan['spec'].get('execution')
        if (not isinstance(execution,dict)
                or execution.get('format')!='hosting-execution-selection/1'
                or execution.get('driver')!='openstack-linux-rebuild/1'):
            raise OperationConflict('Canonical plan lacks a selected creation driver')
        artifact=self.selections.load_verified(execution['artifactDigest'])
        admitted=AdmittedInput(job.job_id,job.organization_id,job.tenant_id,job.plan_id,
                              job.plan_revision,job.plan_digest,job.revocation_epoch,
                              _digest(_payload_from_job(job)))
        bundle=self.bundle_lookup(admitted,artifact)
        if (not isinstance(bundle,ResourceBundle) or bundle.admitted!=admitted
                or bundle.selection_digest!=execution['artifactDigest']
                or bundle.digest!=artifact.get('resourceBundleDigest')
                or (bundle.workload_id,bundle.workload_revision)!=
                   (plan['spec']['workloadId'],plan['spec']['workloadRevision'])
                or (artifact.get('workloadId'),artifact.get('workloadRevision'),
                    artifact.get('source'),artifact.get('destination'))!=
                   (plan['spec']['workloadId'],plan['spec']['workloadRevision'],
                    plan['spec']['source'],plan['spec']['destination'])
                or any(pool.scope not in (job.source,job.destination) for pool in bundle.pools)):
            raise OperationConflict('Protected resource bundle differs from canonical admitted execution')
        return job,plan,bundle

    def register(self,context: TenantContext,scope: PlanScope,*,job_id: str,
                 resource_id: str,lease_key: str,operation_id: str,
                 worker_identity: VerifiedWorkerIdentity,ttl_seconds=300) -> PlannedResourceLease:
        if (not all(_key(value) for value in (job_id,resource_id,lease_key,operation_id))
                or type(ttl_seconds) is not int or not 1<=ttl_seconds<=300
                or not isinstance(scope,PlanScope) or scope.platform_family not in {'openstack'}
                or not isinstance(worker_identity,VerifiedWorkerIdentity)
                or (scope.organization_id,scope.tenant_id,scope.site_id)!=
                   (context.organization_id,context.tenant_id,worker_identity.site_id)
                or (worker_identity.organization_id,worker_identity.tenant_id)!=
                   (context.organization_id,context.tenant_id)):
            raise OperationConflict('Exact planned OpenStack scope and independently verified worker required')
        with self._connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            job,plan,bundle=self._bundle(cursor,context,job_id)
            if scope!=job.destination:
                raise OperationConflict('Creation scope differs from approved destination')
            selected={mapping['targetMachineId'] for mapping in plan['spec']['machineMappings']}
            members={member for pool in bundle.pools if pool.scope==scope and pool.inputs is not None
                     for member in pool.inputs['members']}
            if selected!=members:
                raise OperationConflict('Every approved target machine must match the immutable creation children')
            request_digest=creation_request_digest(bundle,scope,resource_id)
            accounted=self.resources._require_accounted(bundle)
            reservation_digest=c.digest(accounted['receipts'])
            now=NativeOperationRegistry._clock(cursor)
            if worker_identity.expires_at<=now:
                raise OperationConflict('Planned writer certificate expired')
            expires=min(now+timedelta(seconds=ttl_seconds),worker_identity.expires_at,
                        *(c.timestamp(receipt['lease_expires_at']) for receipt in accounted['receipts']
                          if receipt['lease_expires_at'] is not None))
            kind='deployment' if resource_id==deployment_id(bundle,scope) else 'vm'
            cursor.execute('INSERT INTO hosting_controlplane.planned_resource_ownership '
                           '(organization_id,tenant_id,job_id,resource_id,selection_digest,request_digest,'
                           'reservation_digest,resource_kind,platform_family,endpoint_id,native_scope_id,'
                           'site_id,security_domain_id,workload_id,worker_id,owner_epoch,lease_expires_at) '
                           'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s) '
                           'ON CONFLICT DO NOTHING',
                           (context.organization_id,context.tenant_id,job_id,resource_id,bundle.selection_digest,
                            request_digest,reservation_digest,kind,scope.platform_family,scope.endpoint_id,
                            scope.native_scope_id,scope.site_id,scope.security_domain_id,bundle.workload_id,
                            worker_identity.subject,expires))
            cursor.execute('SELECT worker_id,owner_epoch,lease_expires_at,request_digest,reservation_digest '
                           'FROM hosting_controlplane.planned_resource_ownership WHERE organization_id=%s '
                           'AND tenant_id=%s AND job_id=%s AND resource_id=%s',
                           (context.organization_id,context.tenant_id,job_id,resource_id))
            previous=cursor.fetchone()
            if (previous is None or previous[0]!=worker_identity.subject
                    or previous[3:]!=(request_digest,reservation_digest) or previous[2]<=now):
                raise OperationConflict('Planned resource already belongs to another request/writer or is expired')
            lease=PlannedResourceLease(context.organization_id,context.tenant_id,job_id,resource_id,kind,
                bundle.selection_digest,request_digest,reservation_digest,scope,bundle.workload_id,
                previous[0],previous[1],previous[2])
            for child in creation_children(bundle,scope,resource_id):
                cursor.execute('INSERT INTO hosting_controlplane.planned_creation_children '
                    '(organization_id,tenant_id,job_id,resource_id,platform_family,endpoint_id,'
                    'native_scope_id,workload_id,target_machine_id) VALUES '
                    '(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                    (context.organization_id,context.tenant_id,job_id,resource_id,scope.platform_family,
                     scope.endpoint_id,scope.native_scope_id,bundle.workload_id,child))
                cursor.execute('SELECT job_id,resource_id FROM hosting_controlplane.planned_creation_children '
                    'WHERE organization_id=%s AND tenant_id=%s AND platform_family=%s AND endpoint_id=%s '
                    'AND native_scope_id=%s AND workload_id=%s AND target_machine_id=%s',
                    (context.organization_id,context.tenant_id,scope.platform_family,scope.endpoint_id,
                     scope.native_scope_id,bundle.workload_id,child))
                if cursor.fetchone()!=(job_id,resource_id):
                    raise OperationConflict('Selected child already belongs to another aggregate or creation attempt')
            cursor.execute('INSERT INTO hosting_controlplane.native_operation_leases '
                '(organization_id,tenant_id,lease_key,job_id,operation_id,platform_family,endpoint_id,'
                'native_scope_id,resource_kind,native_id,planned_resource_id,site_id,security_domain_id,'
                'worker_id,owner_epoch,expires_at) VALUES '
                '(%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                (context.organization_id,context.tenant_id,lease_key,job_id,operation_id,scope.platform_family,
                 scope.endpoint_id,scope.native_scope_id,kind,resource_id,scope.site_id,
                 scope.security_domain_id,lease.worker_id,lease.epoch,lease.expires_at))
            self.require_current(cursor,context,lease_key=lease_key,lease_epoch=lease.epoch,
                job_id=job_id,operation_id=operation_id,scope=scope,worker_subject=lease.worker_id)
            return lease

    def require_current(self,cursor,context,*,lease_key,lease_epoch,job_id,operation_id,
                        scope,worker_subject):
        _tenant(cursor,context)
        cursor.execute('SELECT planned_resource_id FROM hosting_controlplane.native_operation_leases '
                       'WHERE organization_id=%s AND tenant_id=%s AND lease_key=%s',
                       (context.organization_id,context.tenant_id,lease_key))
        kind=cursor.fetchone()
        if kind is None:
            raise OperationConflict('Exact operation lease is unavailable')
        if kind[0] is None:
            return self.native.require_current(cursor,context,lease_key=lease_key,lease_epoch=lease_epoch,
                job_id=job_id,operation_id=operation_id,scope=scope,worker_subject=worker_subject)
        cursor.execute('SELECT * FROM hosting_controlplane.lock_planned_worker_scope(%s,%s,%s)',
                       (context.organization_id,context.tenant_id,lease_key))
        row=cursor.fetchone()
        now=NativeOperationRegistry._clock(cursor)
        if (row is None or tuple(row[:2])!=(job_id,operation_id)
                or tuple(row[4:9])!=(scope.platform_family,scope.endpoint_id,scope.native_scope_id,
                                     scope.site_id,scope.security_domain_id)
                or tuple(row[9:11])!=(worker_subject,lease_epoch)
                or row[11]<=now or row[12]<=now):
            raise OperationConflict('Planned owner/lease/scoped writer changed or expired')
        _job_record,_plan,bundle=self._bundle(cursor,context,job_id)
        accounted=self.resources._require_accounted(bundle)
        if (row[13]!=bundle.selection_digest or row[14]!=creation_request_digest(bundle,scope,row[2])
                or row[15]!=c.digest(accounted['receipts'])):
            raise OperationConflict('Planned resource reservation or immutable selection changed')
        cursor.execute('SELECT target_machine_id FROM hosting_controlplane.planned_creation_children '
                       'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s AND resource_id=%s '
                       'ORDER BY target_machine_id',
                       (context.organization_id,context.tenant_id,job_id,row[2]))
        if tuple(child[0] for child in cursor.fetchall())!=creation_children(bundle,scope,row[2]):
            raise OperationConflict('Immutable planned creation children differ from approved demand')


_SELECT=('operation_id,job_id,grant_id,step_id,lease_key,planned_resource_id,resource_kind,'
         'platform_family,endpoint_id,native_scope_id,workload_id,security_domain_id,worker_id,'
         'owner_epoch,request_digest,state,native_task_id,outcome')


class PlannedNativeCreationRegistry:
    def __init__(self,connect,*,leases: PlannedLeaseAuthority,grants,evidence):
        if (not callable(connect) or not isinstance(leases,PlannedLeaseAuthority)
                or not callable(getattr(grants,'verify_intent',None))
                or not callable(getattr(evidence,'verify_creation_observation',None))
                or not callable(getattr(evidence,'verify_creation_owner_exclusion',None))):
            raise TypeError('Actual planned owner, live worker grants and independent creation evidence required')
        self._connect,self.leases,self._grants,self._evidence=connect,leases,grants,evidence

    @staticmethod
    def _get(cursor,context,operation_id,*,lock=True):
        cursor.execute(f'SELECT {_SELECT} FROM hosting_controlplane.native_operation_intents '
                       'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s '
                       'AND planned_resource_id IS NOT NULL'+(' FOR UPDATE' if lock else ''),
                       (context.organization_id,context.tenant_id,operation_id))
        row=cursor.fetchone()
        if row is None: raise OperationConflict('Planned creation intent is unavailable in this tenant')
        cursor.execute('SELECT site_id FROM hosting_controlplane.planned_resource_ownership '
                       'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s AND resource_id=%s',
                       (context.organization_id,context.tenant_id,row[1],row[5]))
        scope=PlanScope(context.organization_id,context.tenant_id,cursor.fetchone()[0],row[11],
                        row[8],row[9],row[7])
        return PlannedCreationOperation(*row[:7],scope,row[10],row[12],row[13],*row[14:])

    def _grant(self,cursor,context,lease,operation,identity):
        if ((operation.job_id,operation.resource_id,operation.scope,operation.worker_id,
             operation.owner_epoch,operation.request_digest)!=
                (lease.job_id,lease.resource_id,lease.scope,lease.worker_id,lease.epoch,lease.request_digest)):
            raise OperationConflict('Creation belongs to another planned owner')
        self._grants.verify_intent(cursor,context,grant_id=operation.grant_id,
            job_id=operation.job_id,step_id=operation.step_id,operation_id=operation.operation_id,
            operation_kind='VM_CREATE',operation_scope=lease.scope,worker_identity=identity,
            lease_key=operation.lease_key,lease_epoch=lease.epoch)

    def prepare(self,context,lease,*,grant_id,step_id,lease_key,operation_id,worker_identity):
        if not isinstance(lease,PlannedResourceLease) or not all(map(_key,(grant_id,step_id,lease_key,operation_id))):
            raise OperationConflict('Exact planned owner and operation identities required')
        with self._connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            proposed=PlannedCreationOperation(operation_id,lease.job_id,grant_id,step_id,lease_key,
                lease.resource_id,lease.resource_kind,lease.scope,lease.workload_id,lease.worker_id,
                lease.epoch,lease.request_digest,'PREPARED',None,None)
            self._grant(cursor,context,lease,proposed,worker_identity)
            cursor.execute('INSERT INTO hosting_controlplane.native_operation_intents '
                '(organization_id,tenant_id,operation_id,job_id,grant_id,step_id,lease_key,'
                'platform_family,endpoint_id,native_scope_id,resource_kind,native_id,planned_resource_id,'
                'workload_id,security_domain_id,worker_id,owner_epoch,operation_kind,request_digest) '
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,%s,%s,%s,%s,%s,'VM_CREATE',%s) "
                'ON CONFLICT DO NOTHING',
                (context.organization_id,context.tenant_id,operation_id,lease.job_id,grant_id,step_id,lease_key,
                 lease.scope.platform_family,lease.scope.endpoint_id,lease.scope.native_scope_id,
                 lease.resource_kind,lease.resource_id,lease.workload_id,lease.scope.security_domain_id,
                 lease.worker_id,lease.epoch,lease.request_digest))
            operation=self._get(cursor,context,operation_id)
            if replace(operation,state='PREPARED',native_task_id=None,outcome=None)!=proposed:
                raise OperationConflict('Creation operation identity was used for another request')
            return operation

    def claim_once(self,context,lease,operation_id,worker_identity):
        with self._connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            proposed=self._get(cursor,context,operation_id,lock=False)
            self._grant(cursor,context,lease,proposed,worker_identity)
            operation=self._get(cursor,context,operation_id)
            if operation!=proposed:
                raise OperationConflict('Creation changed while acquiring current authority')
            if operation.state!='PREPARED': return False
            cursor.execute("UPDATE hosting_controlplane.native_operation_intents SET state='IN_FLIGHT',"
                           'updated_at=clock_timestamp() WHERE organization_id=%s AND tenant_id=%s '
                           'AND operation_id=%s',
                           (context.organization_id,context.tenant_id,operation_id))
            return True

    def task_accepted(self,context,operation_id,worker_id,native_task_id):
        if not _text(native_task_id): raise ValueError('Exact native task receipt required')
        with self._connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context); operation=self._get(cursor,context,operation_id)
            if operation.worker_id!=worker_id: raise OperationConflict('Receipt belongs to another planned writer')
            if operation.state=='TASK_ACCEPTED' and operation.native_task_id==native_task_id: return False
            if operation.state!='IN_FLIGHT': raise RecoveryHeld('Late creation receipt requires independent observation')
            cursor.execute("UPDATE hosting_controlplane.native_operation_intents SET state='TASK_ACCEPTED',"
                'native_task_id=%s,updated_at=clock_timestamp() WHERE organization_id=%s AND tenant_id=%s '
                'AND operation_id=%s',(native_task_id,context.organization_id,context.tenant_id,operation_id))
            return True

    def mark_uncertain(self,context,operation_id,worker_id):
        with self._connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context); operation=self._get(cursor,context,operation_id)
            if operation.worker_id!=worker_id: raise OperationConflict('Uncertainty belongs to another planned writer')
            if operation.state=='UNCERTAIN': return False
            if operation.state not in {'IN_FLIGHT','TASK_ACCEPTED'}:
                raise OperationConflict('Only claimed creation may become uncertain')
            cursor.execute("UPDATE hosting_controlplane.native_operation_intents SET state='UNCERTAIN',"
                           'updated_at=clock_timestamp() WHERE organization_id=%s AND tenant_id=%s '
                           'AND operation_id=%s',(context.organization_id,context.tenant_id,operation_id))
            return True

    def _verify_observation(self,cursor,operation,observation):
        if not isinstance(observation,NativeCreationObservation):
            raise TypeError('Independent creation observation required')
        native=observation.observation
        at=NativeOperationRegistry._clock(cursor)
        if (not _fresh(native.observed_at,at) or native.observer_subject==operation.worker_id
                or (operation.native_task_id is not None and native.native_task_id!=operation.native_task_id)
                or any((binding.platform_family,binding.endpoint_id,binding.native_scope_id)!=
                       (operation.scope.platform_family,operation.scope.endpoint_id,operation.scope.native_scope_id)
                       for binding in observation.bindings)):
            raise RecoveryHeld('Creation readback is stale, foreign or not independent')
        self._evidence.verify_creation_observation(cursor,operation,observation)

    def observe(self,context,operation_id,observation):
        with self._connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context); operation=self._get(cursor,context,operation_id)
            if operation.state in {'PREPARED','RESOLVED'}:
                raise OperationConflict('Creation is not awaiting observation')
            self._verify_observation(cursor,operation,observation)
            self._insert_observation(cursor,context,operation_id,observation)

    @staticmethod
    def _insert_observation(cursor,context,operation_id,observation):
        native=observation.observation
        cursor.execute('INSERT INTO hosting_controlplane.native_operation_observations '
            '(organization_id,tenant_id,observation_id,operation_id,evidence_digest,observer_subject,'
            'native_task_id,outcome,native_quiesced,observed_at,created_native_bindings) '
            'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)',
            (context.organization_id,context.tenant_id,native.observation_id,operation_id,
             native.evidence_digest,native.observer_subject,native.native_task_id,native.outcome,
             native.native_quiesced,native.observed_at,
             json.dumps([asdict(binding) for binding in observation.bindings]) if observation.bindings else None))

    def acknowledge_created(self,context,lease,operation_id,worker_identity,observation):
        """Resolve a current successful attempt only after independent readback.

        Async/lost or expired attempts stay in this journal for fenced recovery.
        This method records actual IDs; it creates no native resource and issues
        no activation or cross-WSD membership acceptance.
        """
        with self._connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            proposed=self._get(cursor,context,operation_id,lock=False)
            self._grant(cursor,context,lease,proposed,worker_identity)
            operation=self._get(cursor,context,operation_id)
            if operation!=proposed or operation.state not in {'IN_FLIGHT','TASK_ACCEPTED','UNCERTAIN'}:
                raise RecoveryHeld('Creation cannot acknowledge from this state')
            self._verify_observation(cursor,operation,observation)
            native=observation.observation
            if native.outcome!='EFFECT_PRESENT' or not native.native_quiesced:
                raise RecoveryHeld('Creation success is not independently quiesced and present')
            self._insert_observation(cursor,context,operation_id,observation)
            if operation.state=='IN_FLIGHT':
                cursor.execute("UPDATE hosting_controlplane.native_operation_intents SET state='UNCERTAIN',"
                    'updated_at=clock_timestamp() WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s',
                    (context.organization_id,context.tenant_id,operation_id))
            resolution=c.digest({'observation':asdict(native)|{'observed_at':native.observed_at.isoformat()},
                                 'bindings':[asdict(binding) for binding in observation.bindings]})
            cursor.execute("UPDATE hosting_controlplane.native_operation_intents SET state='RESOLVED',"
                "outcome='EFFECT_PRESENT',resolution_evidence_digest=%s,updated_at=clock_timestamp() "
                'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s',
                (resolution,context.organization_id,context.tenant_id,operation_id))
            return observation.bindings

    @staticmethod
    def _stored_observation(cursor,context,operation_id,observation_id):
        cursor.execute('SELECT evidence_digest,observer_subject,native_task_id,outcome,native_quiesced,'
            'observed_at,created_native_bindings FROM hosting_controlplane.native_operation_observations '
            'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s AND observation_id=%s',
            (context.organization_id,context.tenant_id,operation_id,observation_id))
        row=cursor.fetchone()
        if row is None: raise RecoveryHeld('Independently collected creation observation is unavailable')
        raw=row[6]
        if isinstance(raw,str): raw=json.loads(raw)
        native=NativeObservation(observation_id,*row[:6])
        return NativeCreationObservation(native,tuple(NativeBinding(**binding) for binding in (raw or [])))

    def get(self,context,operation_id):
        """Read only; status does not establish fresh native success."""
        with self._connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            return self._get(cursor,context,operation_id,lock=False)

    def reconcile_observed(self,context,operation_id,observation):
        """Read-only recovery of an already resolved creation's actual IDs.

        Unknown/in-flight attempts require fenced outcome review; this method
        never retries native creation or rewrites an observed identity.
        """
        with self._connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context); operation=self._get(cursor,context,operation_id,lock=False)
            if operation.state!='RESOLVED' or operation.outcome!='EFFECT_PRESENT':
                raise RecoveryHeld('Creation is unresolved; independently reconcile and fence it first')
            self._verify_observation(cursor,operation,observation)
            native=observation.observation
            if native.outcome!='EFFECT_PRESENT' or not native.native_quiesced:
                raise RecoveryHeld('Resolved creation currently differs from verified native state')
            cursor.execute('SELECT observation_id FROM hosting_controlplane.native_operation_observations '
                'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s '
                "AND outcome='EFFECT_PRESENT' ORDER BY recorded_at DESC LIMIT 1",
                (context.organization_id,context.tenant_id,operation_id))
            previous=self._stored_observation(cursor,context,operation_id,cursor.fetchone()[0])
            if {binding.key() for binding in previous.bindings}!={binding.key() for binding in observation.bindings}:
                raise RecoveryHeld('Created native identities changed during read-only reconciliation')
            return observation.bindings

    def review_outcome(self,context,lease,operation_id,observation_id,principal: VerifiedPrincipal,
                       *,decision,exclusion: OwnerRecoveryEvidence):
        """Two independent operators resolve one expired, actually fenced writer.

        Lease expiry is only a reason to stop new work. Readback, actual worker
        exclusion and both current reviewer identities must independently prove
        that late/delayed API effects can no longer change this outcome.
        """
        if decision not in {'NO_EFFECT','EFFECT_PRESENT'} or not isinstance(exclusion,OwnerRecoveryEvidence):
            raise ValueError('Concrete outcome and independent planned-writer exclusion required')
        with self._connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            cursor.execute('SELECT worker_id,owner_epoch,lease_expires_at FROM '
                'hosting_controlplane.planned_resource_ownership WHERE organization_id=%s '
                'AND tenant_id=%s AND job_id=%s AND resource_id=%s',
                (context.organization_id,context.tenant_id,lease.job_id,lease.resource_id))
            owner=cursor.fetchone()
            now=NativeOperationRegistry._clock(cursor)
            if owner is None or owner[:2]!=(lease.worker_id,lease.epoch) or owner[2]>now:
                raise RecoveryHeld('Expired exact planned owner required for recovery')
            operation=self._get(cursor,context,operation_id)
            if (operation.state not in {'TASK_ACCEPTED','UNCERTAIN'}
                    or (operation.job_id,operation.resource_id,operation.worker_id,operation.owner_epoch)!=
                    (lease.job_id,lease.resource_id,lease.worker_id,lease.epoch)):
                raise RecoveryHeld('Planned operation is not eligible for outcome recovery')
            actor=_identity(principal,EXECUTION_OPERATOR,lease.scope,now)
            observation=self._stored_observation(cursor,context,operation_id,observation_id)
            native=observation.observation
            if (native.outcome!=decision or not native.native_quiesced
                    or actor in (operation.worker_id,native.observer_subject)
                    or not _fresh(exclusion.observed_at,now)):
                raise RecoveryHeld('Fresh independent quiesced observation and reviewer required')
            self._evidence.verify_creation_owner_exclusion(cursor,lease,lease.scope,exclusion)
            self._verify_observation(cursor,operation,observation)
            digest=c.digest({'observation':asdict(native)|{'observed_at':native.observed_at.isoformat()},
                             'bindings':[asdict(binding) for binding in observation.bindings],
                             'exclusion':asdict(exclusion)|{'observed_at':exclusion.observed_at.isoformat()}})
            cursor.execute('INSERT INTO hosting_controlplane.native_operation_reviews '
                '(organization_id,tenant_id,operation_id,reviewer_subject,observation_id,evidence_digest,'
                'decision,incident_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                (context.organization_id,context.tenant_id,operation_id,actor,observation_id,digest,
                 decision,exclusion.incident_id))
            cursor.execute('SELECT reviewer_subject,observation_id,evidence_digest,decision,incident_id '
                'FROM hosting_controlplane.native_operation_reviews WHERE organization_id=%s '
                'AND tenant_id=%s AND operation_id=%s',
                (context.organization_id,context.tenant_id,operation_id))
            reviews=cursor.fetchall()
            if len(reviews)>2 or any(row[1:]!=(observation_id,digest,decision,exclusion.incident_id) for row in reviews):
                raise RecoveryHeld('Conflicting creation recovery reviews retain the hold')
            if len(reviews)!=2: return False
            cursor.execute("UPDATE hosting_controlplane.native_operation_intents SET state='RESOLVED',"
                'outcome=%s,resolution_evidence_digest=%s,updated_at=clock_timestamp() '
                'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s',
                (decision,digest,context.organization_id,context.tenant_id,operation_id))
            return True

    def materialize_native_ownership(self,context,lease,operation_id,observation,principal):
        """Attach actual verified IDs to B06 after accepted WSD and occupancy.

        Native ownership's accepted-workload/WSD trigger remains authoritative.
        Cross-WSD target membership must complete its explicit transition first.
        This method does not change portable workload membership or activate it.
        """
        bindings=self.reconcile_observed(context,operation_id,observation)
        with self._connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            _job_record,_plan,bundle=self.leases._bundle(cursor,context,lease.job_id)
            operation=self._get(cursor,context,operation_id)
            now=NativeOperationRegistry._clock(cursor)
            _identity(principal,EXECUTION_OPERATOR,lease.scope,now)
            if (operation.job_id,operation.resource_id,operation.scope)!=(lease.job_id,lease.resource_id,lease.scope):
                raise RecoveryHeld('Observed ownership belongs to another planned resource')
            self._verify_observation(cursor,operation,observation)
            accounted=self.leases.resources._require_accounted(bundle)
            if any(receipt['status']!='CONFIRMED' for receipt in accounted['receipts']):
                raise RecoveryHeld('Confirm observed native occupancy under every selected capacity owner first')
            for binding in bindings:
                cursor.execute('INSERT INTO hosting_controlplane.native_ownership '
                    '(platform_family,endpoint_id,native_scope_id,resource_kind,native_id,organization_id,'
                    'tenant_id,security_domain_id,workload_id,worker_id,lease_epoch,lease_expires_at) '
                    'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                    (*binding.key(),context.organization_id,context.tenant_id,lease.scope.security_domain_id,
                     lease.workload_id,lease.worker_id,lease.epoch,lease.expires_at))
                cursor.execute('SELECT organization_id,tenant_id,security_domain_id,workload_id,worker_id,lease_epoch '
                    'FROM hosting_controlplane.native_ownership WHERE platform_family=%s AND endpoint_id=%s '
                    'AND native_scope_id=%s AND resource_kind=%s AND native_id=%s FOR SHARE',binding.key())
                actual=cursor.fetchone()
                if actual!=(context.organization_id,context.tenant_id,lease.scope.security_domain_id,
                            lease.workload_id,lease.worker_id,lease.epoch):
                    raise RecoveryHeld('Verified created resource is already owned by another scope or writer')
            return bindings
