"""Selected service intents in the one existing native operation journal."""
from __future__ import annotations

from dataclasses import dataclass, replace

from provisioner.controlplane.jobs.repository import _tenant
from provisioner.execution import readback_core as c
from .planned import PlannedLeaseAuthority, PlannedServiceLease
from .registry import NativeObservation, NativeOperationRegistry, OperationConflict, RecoveryHeld, _fresh


@dataclass(frozen=True)
class PlannedServiceOperation:
    operation_id: str
    job_id: str
    grant_id: str
    step_id: str
    lease_key: str
    resource_id: str
    operation_kind: str
    request_digest: str
    worker_id: str
    owner_epoch: int
    state: str
    outcome: str | None


class PlannedServiceRegistry:
    def __init__(self, connect, *, leases, grants, evidence):
        if (not callable(connect) or not isinstance(leases, PlannedLeaseAuthority)
                or not callable(getattr(grants, 'verify_intent', None))
                or not callable(getattr(evidence, 'verify_service_observation', None))):
            raise TypeError('The real planned lease, current grant and independent service reader are required')
        self.connect, self.leases, self.grants, self.evidence = connect, leases, grants, evidence

    @staticmethod
    def _get(cursor, context, operation_id, *, lock=True):
        cursor.execute('SELECT operation_id,job_id,grant_id,step_id,lease_key,planned_resource_id,'
            'operation_kind,request_digest,worker_id,owner_epoch,state,outcome '
            'FROM hosting_controlplane.native_operation_intents WHERE organization_id=%s '
            'AND tenant_id=%s AND operation_id=%s AND planned_resource_id IS NOT NULL '
            "AND operation_kind IN ('IPAM_RESERVE','DNS_CHANGE','QUOTA_CHANGE')"+
            (' FOR UPDATE' if lock else ''),
            (context.organization_id, context.tenant_id, operation_id))
        row = cursor.fetchone()
        if row is None:
            raise OperationConflict('The exact original selected service intent is unavailable')
        return PlannedServiceOperation(*row)

    def get(self, context, operation_id):
        with self.connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, context)
            return self._get(cursor, context, operation_id, lock=False)

    def _grant(self, cursor, context, lease, operation, identity):
        owner = lease.owner
        from provisioner.controlplane.conversion.handover import require_write_admission
        require_write_admission(cursor,context,security_domain_id=owner.scope.security_domain_id,
                                workload_id=owner.workload_id)
        if ((operation.job_id, operation.resource_id, operation.step_id, operation.operation_kind,
             operation.request_digest, operation.worker_id, operation.owner_epoch) !=
                (owner.job_id, owner.resource_id, lease.step_id, lease.operation_kind,
                 lease.request_digest, owner.worker_id, owner.epoch)):
            raise OperationConflict('Service operation differs from its immutable lease projection')
        return self.grants.verify_intent(cursor, context, grant_id=operation.grant_id,
            job_id=operation.job_id, step_id=operation.step_id, operation_id=operation.operation_id,
            operation_kind=operation.operation_kind, operation_scope=owner.scope,
            worker_identity=identity, lease_key=operation.lease_key, lease_epoch=owner.epoch)

    def prepare(self, context, lease, *, grant, identity):
        if not isinstance(lease, PlannedServiceLease):
            raise TypeError('An originally selected service lease is required')
        proposed = PlannedServiceOperation(grant.operation_id, lease.owner.job_id, grant.grant_id,
            lease.step_id, grant.lease_key, lease.owner.resource_id, lease.operation_kind,
            lease.request_digest, lease.owner.worker_id, lease.owner.epoch, 'PREPARED', None)
        with self.connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, context)
            self._grant(cursor, context, lease, proposed, identity)
            owner = lease.owner
            cursor.execute('INSERT INTO hosting_controlplane.native_operation_intents '
                '(organization_id,tenant_id,operation_id,job_id,grant_id,step_id,lease_key,'
                'platform_family,endpoint_id,native_scope_id,resource_kind,native_id,planned_resource_id,'
                'workload_id,security_domain_id,worker_id,owner_epoch,operation_kind,request_digest) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,%s,%s,%s,%s,%s,%s,%s) '
                'ON CONFLICT DO NOTHING',
                (context.organization_id,context.tenant_id,grant.operation_id,owner.job_id,grant.grant_id,
                 lease.step_id,grant.lease_key,owner.scope.platform_family,owner.scope.endpoint_id,
                 owner.scope.native_scope_id,owner.resource_kind,owner.resource_id,owner.workload_id,
                 owner.scope.security_domain_id,owner.worker_id,owner.epoch,lease.operation_kind,
                 lease.request_digest))
            original = self._get(cursor, context, grant.operation_id)
            if replace(original, state='PREPARED', outcome=None) != proposed:
                raise OperationConflict('This service operation ID already names another original request')
            return original

    def claim_once(self, context, lease, operation_id, identity):
        with self.connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, context)
            before = self._get(cursor, context, operation_id, lock=False)
            self._grant(cursor, context, lease, before, identity)
            original = self._get(cursor, context, operation_id)
            if original != before:
                raise OperationConflict('The service intent changed while current authority was acquired')
            if original.state != 'PREPARED':
                return False
            cursor.execute("UPDATE hosting_controlplane.native_operation_intents SET state='IN_FLIGHT',"
                'updated_at=clock_timestamp() WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s',
                (context.organization_id,context.tenant_id,operation_id))
            return True

    def mark_uncertain(self, context, operation_id, worker_id):
        with self.connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, context)
            original = self._get(cursor, context, operation_id)
            if original.worker_id != worker_id:
                raise OperationConflict('Original service intent belongs to another writer')
            if original.state == 'UNCERTAIN':
                return
            if original.state != 'IN_FLIGHT':
                raise RecoveryHeld('Only an in-flight service operation can become uncertain')
            cursor.execute("UPDATE hosting_controlplane.native_operation_intents SET state='UNCERTAIN',"
                'updated_at=clock_timestamp() WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s',
                (context.organization_id,context.tenant_id,operation_id))

    def acknowledge(self, context, lease, operation_id, identity, observation):
        if not isinstance(observation, NativeObservation):
            raise TypeError('A current independently collected service observation is required')
        with self.connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, context)
            original = self._get(cursor, context, operation_id, lock=False)
            self._grant(cursor, context, lease, original, identity)
            original = self._get(cursor, context, operation_id)
            self._verify(cursor, context, lease, original, observation)
            if original.state == 'RESOLVED':
                if original.outcome != observation.outcome:
                    raise RecoveryHeld('Independent observation differs from the original resolution')
                return original
            if original.state != 'IN_FLIGHT':
                raise RecoveryHeld('An uncertain service request requires approved writer-excluded recovery')
            cursor.execute('INSERT INTO hosting_controlplane.native_operation_observations '
                '(organization_id,tenant_id,observation_id,operation_id,evidence_digest,observer_subject,'
                'native_task_id,outcome,native_quiesced,observed_at) VALUES (%s,%s,%s,%s,%s,%s,NULL,%s,%s,%s)',
                (context.organization_id,context.tenant_id,observation.observation_id,operation_id,
                 observation.evidence_digest,observation.observer_subject,observation.outcome,
                 observation.native_quiesced,observation.observed_at))
            if original.state == 'IN_FLIGHT':
                cursor.execute("UPDATE hosting_controlplane.native_operation_intents SET state='UNCERTAIN',"
                    'updated_at=clock_timestamp() WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s',
                    (context.organization_id,context.tenant_id,operation_id))
            cursor.execute("UPDATE hosting_controlplane.native_operation_intents SET state='RESOLVED',"
                'outcome=%s,resolution_evidence_digest=%s,updated_at=clock_timestamp() '
                'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s',
                (observation.outcome,observation.evidence_digest,context.organization_id,context.tenant_id,operation_id))
            return replace(original, state='RESOLVED', outcome=observation.outcome)

    def _verify(self, cursor, context, lease, operation, observation):
        now = NativeOperationRegistry._clock(cursor)
        if (not _fresh(observation.observed_at, now) or not observation.native_quiesced
                or observation.observer_subject == operation.worker_id
                or observation.native_task_id is not None or observation.outcome != 'EFFECT_PRESENT'):
            raise RecoveryHeld('Service completion needs current independently observed native state')
        self.evidence.verify_service_observation(cursor, context, lease, operation, observation)

    def reconcile_observed(self, context, lease, operation_id, observation):
        # Readback of a resolved original operation never reclaims or writes it.
        with self.connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, context)
            original = self._get(cursor, context, operation_id)
            if original.state != 'RESOLVED' or original.outcome != 'EFFECT_PRESENT':
                raise RecoveryHeld('An unresolved service intent requires its current recovery admission')
            self._verify(cursor, context, lease, original, observation)
            return original
