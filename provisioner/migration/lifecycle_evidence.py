"""Read exact original application intent resolution through its B11 verifier.

A private receipt, worker completion or operator flag cannot authorize the next
phase. The existing registry's independent native and credential/task exclusion
owners recheck both retained proofs in the same tenant-scoped transaction.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import os
from pathlib import Path
import re

from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.persistence import TenantContext, canonical_record_digest
from provisioner.controlplane.persistence.store import OwnerLease
from provisioner.controlplane.reconciliation import (
    NativeObservation, NativeOperationRegistry, OwnerRecoveryEvidence)
from provisioner.controlplane.reconciliation import registry as native
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import private_path, require


def _time(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'An exact aware native observation time is required')
    return result


@dataclass(frozen=True)
class ApplicationEvidenceReader:
    registry: NativeOperationRegistry
    proof_directory: Path

    def __post_init__(self):
        require(isinstance(self.registry, NativeOperationRegistry),
                'The original native intent registry with independent verifier is required')
        object.__setattr__(self, 'proof_directory', private_path(self.proof_directory, directory=True))

    def _packet(self, job_id, operation_id):
        require(all(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', value)
                    for value in (job_id, operation_id)), 'The exact original job and operation are required')
        selected = private_path(self.proof_directory / job_id / (operation_id + '.json'))
        with os.fdopen(os.open(selected, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
            raw = stream.read(1024 * 1024 + 1)
        require(len(raw) <= 1024 * 1024, 'The independent original native proof exceeds its bound')
        result = strict_loads(raw)
        require(isinstance(result, dict) and set(result) ==
                {'format', 'job_id', 'operation_id', 'phase_receipt_digest', 'observation', 'exclusion'}
                and result['format'] == 'hosting-application-original-resolution/1'
                and (result['job_id'], result['operation_id']) == (job_id, operation_id),
                'The independent proof names another original application operation')
        observation, exclusion = result['observation'], result['exclusion']
        require(isinstance(observation, dict) and set(observation) ==
                {'observation_id', 'evidence_digest', 'observer_subject', 'native_task_id',
                 'outcome', 'native_quiesced', 'observed_at'}
                and isinstance(exclusion, dict) and set(exclusion) ==
                {'native_evidence_digest', 'worker_fence_digest', 'observed_at', 'incident_id'},
                'Exact independently enrolled native and old-worker exclusion records are required')
        return result, NativeObservation(**dict(observation, observed_at=_time(observation['observed_at']))), \
            OwnerRecoveryEvidence(**dict(exclusion, observed_at=_time(exclusion['observed_at'])))

    def require_resolved(self, receipt, scope, *, outcome='EFFECT_PRESENT'):
        require(isinstance(receipt, dict) and receipt.get('format') == 'hosting-application-phase-result/1'
                and outcome in {'NO_EFFECT', 'EFFECT_PRESENT'}, 'The retained original phase receipt is required')
        original = receipt['original_intent']
        context = TenantContext(original['organization_id'], original['tenant_id'])
        packet, observation, exclusion = self._packet(receipt['job_id'], original['operation_id'])
        require(packet['phase_receipt_digest'] == canonical_record_digest(receipt),
                'The original independently observed phase receipt changed')
        with self.registry._connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, context)
            cursor.execute(f'SELECT {native._SELECT} FROM hosting_controlplane.native_operation_intents '
                'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s AND operation_id=%s FOR SHARE',
                (context.organization_id, context.tenant_id, receipt['job_id'], original['operation_id']))
            row = cursor.fetchone()
            require(row is not None, 'The original application native intent is unavailable')
            operation = native._row(row)
            require(operation.state == 'RESOLVED' and operation.outcome == outcome
                    and observation.outcome == outcome and observation.native_quiesced
                    and operation.worker_id != observation.observer_subject
                    and all(getattr(operation, key) == original[key] for key in
                        ('operation_id', 'grant_id', 'step_id', 'lease_key', 'workload_id',
                         'security_domain_id', 'worker_id', 'owner_epoch', 'operation_kind', 'request_digest'))
                    and operation.binding.__dict__ == original['binding']
                    and (operation.native_task_id is None or operation.native_task_id == observation.native_task_id),
                    'The original effect has not been independently resolved on the exact selected VM')
            native._scope(context, scope, operation.binding, operation.security_domain_id)
            cursor.execute('SELECT clock_timestamp()')
            now = cursor.fetchone()[0]
            require(all(now - timedelta(minutes=5) <= stamp <= now
                        for stamp in (observation.observed_at, exclusion.observed_at)),
                    'The independent native or late-request exclusion observation has expired')
            cursor.execute('SELECT reviewer_subject,observation_id,evidence_digest,decision,incident_id '
                'FROM hosting_controlplane.native_operation_reviews WHERE organization_id=%s '
                'AND tenant_id=%s AND operation_id=%s FOR SHARE',
                (context.organization_id, context.tenant_id, operation.operation_id))
            reviews = cursor.fetchall()
            expected = (observation.observation_id, native._resolution_digest(observation, exclusion),
                        outcome, exclusion.incident_id)
            require(len(reviews) == 2 and len({review[0] for review in reviews}) == 2
                    and all(review[1:] == expected and review[0] not in
                            {operation.worker_id, observation.observer_subject} for review in reviews),
                    'The exact original effect needs two independent matching native outcome reviews')
            cursor.execute('SELECT evidence_digest,observer_subject,native_task_id,outcome,native_quiesced,observed_at '
                'FROM hosting_controlplane.native_operation_observations WHERE organization_id=%s '
                'AND tenant_id=%s AND operation_id=%s AND observation_id=%s FOR SHARE',
                (context.organization_id, context.tenant_id, operation.operation_id, observation.observation_id))
            require(cursor.fetchone() == (observation.evidence_digest, observation.observer_subject,
                    observation.native_task_id, observation.outcome, observation.native_quiesced,
                    observation.observed_at), 'The original native observation is not retained by its owner')
            lease = OwnerLease(operation.binding, context.organization_id, context.tenant_id,
                operation.security_domain_id, operation.workload_id, operation.worker_id,
                operation.owner_epoch, now)
            # These are the actually enrolled B11 independent owners, not a
            # caller-supplied function or a deserialized native_quiesced flag.
            self.registry._evidence.verify_owner_exclusion(cursor, lease, scope, exclusion)
            self.registry._evidence.verify_native_observation(cursor, operation, observation)
        return dict(original_job_id=receipt['job_id'], original_operation_id=operation.operation_id,
                    original_request_digest=operation.request_digest,
                    phase_receipt_digest=packet['phase_receipt_digest'],
                    native_observation_digest=observation.evidence_digest,
                    worker_fence_digest=exclusion.worker_fence_digest,
                    observed_at=observation.observed_at.isoformat(), outcome=outcome)


@dataclass(frozen=True)
class CurrentWriterExclusions:
    """Exact independently resolved original source and target disk fences."""
    reader: ApplicationEvidenceReader
    receipts: tuple

    def __post_init__(self):
        from provisioner.controlplane.authority import PlanScope
        require(isinstance(self.reader, ApplicationEvidenceReader) and isinstance(self.receipts, tuple)
                and self.receipts and all(isinstance(scope, PlanScope) and isinstance(receipt, dict)
                    and receipt.get('phase') in {'SOURCE_FENCE', 'TARGET_FENCE', 'POSTWRITE_CAPTURE'}
                    and receipt.get('observations', {}).get('persistent_disk_exclusion', {}).get('state') in
                        {'SOURCE_DATA_DISKS_DETACHED_PERSISTENTLY', 'NATIVE_DATA_VOLUME_DETACHED_PERSISTENTLY'}
                    for scope, receipt in self.receipts),
                'Current recovery needs actual original persistent source and target disk exclusions')

    def require_current(self):
        return tuple(self.reader.require_resolved(receipt, scope) for scope, receipt in self.receipts)
