"""Fixed Temporal activities around the actual application migration owners.

Only admitted IDs and approved digests cross Temporal history. Protected files,
enrolled worker identities, resource controls and ephemeral secrets are supplied
by the installed runtime. Unimplemented native writer/activation owners return a
precise hold; they are never substituted with an operator assertion or callback.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from temporalio import activity

from provisioner.controlplane.authority import PlanScope
from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.persistence import TenantContext, canonical_record_digest
from provisioner.controlplane.reconciliation import registry as native_registry
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.approval_gate import _valid_digest, _valid_id
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import (
    encoded, load_private, private_path, require, sync_directory, write_new)

from .application import ApplicationDataRunner, ApplicationDataSelection, DatasetWorkerRuntime
from .authority import ApplicationCommandAuthority
from .cutover import (SourceFenceRunner, SourceFenceSelection, SourceWorkerRuntime,
                      recovery_projection)

STAGE_VERIFIED = 'STAGE_VERIFIED'
HELD = 'HELD'
_REASONS = frozenset({'NATIVE_UNCERTAIN', 'AUTHORITY_REVOKED', 'OPERATOR_HOLD',
                      'WORKFLOW_FAILED', 'VALIDATION_FAILED'})
_HOLDS = frozenset({'CURRENT_AUTHORITY_UNAVAILABLE', 'DATASET_EFFECT_REQUIRES_RECONCILIATION',
                    'SOURCE_POWER_REQUIRES_RECONCILIATION',
                    'SOURCE_RESTART_OR_OTHER_WRITER_EXCLUSION_REQUIRED',
                    'ISOLATED_REHEARSAL_OWNER_UNAVAILABLE', 'FINAL_CONSISTENCY_OWNER_UNAVAILABLE',
                    'TRAFFIC_AND_TARGET_ACTIVATION_OWNER_UNAVAILABLE',
                    'CURRENT_TARGET_WRITE_STATE_REQUIRED', 'POSTWRITE_RECOVERY_OWNER_UNAVAILABLE',
                    'PREWRITE_TARGET_EXCLUSION_REQUIRED', 'PRIVATE_MIGRATION_INPUTS_UNAVAILABLE'})


@dataclass(frozen=True)
class MigrationActivityRequest:
    admitted: AdmittedInput
    selection_digest: str
    member_id: str = ''
    mode: str = 'EXECUTE'

    def __post_init__(self):
        require(isinstance(self.admitted, AdmittedInput) and _valid_digest(self.selection_digest)
                and (self.member_id == '' or _valid_id(self.member_id))
                and self.mode in {'EXECUTE', 'OBSERVE_ORIGINAL'},
                'An exact admitted migration job, selected digest and bounded member are required')


@dataclass(frozen=True)
class MigrationActivityResult:
    status: str
    job_id: str
    member_id: str
    reason_code: str | None = None
    hold_code: str | None = None
    evidence_digest: str | None = None

    def __post_init__(self):
        require(self.status in {STAGE_VERIFIED, HELD} and _valid_id(self.job_id)
                and (self.member_id == '' or _valid_id(self.member_id))
                and (self.reason_code is None or self.reason_code in _REASONS)
                and (self.hold_code is None or self.hold_code in _HOLDS)
                and (self.evidence_digest is None or _valid_digest(self.evidence_digest)),
                'A bounded migration activity result is required')
        require((self.status == STAGE_VERIFIED and self.reason_code is self.hold_code is None
                 and self.evidence_digest is not None)
                or (self.status == HELD and self.reason_code is not None and self.hold_code is not None),
                'Verified stages need retained evidence; held stages need a precise reason')


class FileMigrationSelectionStore:
    """Explicit content-addressed descriptor stores and protected live packets."""
    def __init__(self, *, dataset_directory, cutover_directory, runtime_directory):
        self.dataset_directory = private_path(dataset_directory, directory=True)
        self.cutover_directory = private_path(cutover_directory, directory=True)
        self.runtime_directory = private_path(runtime_directory, directory=True)

    @staticmethod
    def _read(path):
        path = private_path(path)
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
            raw = stream.read(16 * 1024 * 1024 + 1)
        require(len(raw) <= 16 * 1024 * 1024, 'Protected migration input exceeds its bounded size')
        return raw

    def datasets(self, selected_digest):
        require(_valid_digest(selected_digest), 'Exact selected dataset digest required')
        selected = ApplicationDataSelection(self._read(self.dataset_directory / (selected_digest + '.json')))
        require(selected.sha256 == selected_digest, 'Dataset descriptor content changed')
        return selected

    def cutover(self, selected_digest):
        require(_valid_digest(selected_digest), 'Exact selected source-fence digest required')
        selected = SourceFenceSelection(self._read(self.cutover_directory / (selected_digest + '.json')))
        require(selected.sha256 == selected_digest, 'Source-fence descriptor content changed')
        return selected

    def dataset_packet(self, job_id, dataset_id):
        require(_valid_id(job_id) and _valid_id(dataset_id), 'Exact job and dataset required')
        packet = strict_loads(self._read(self.runtime_directory / job_id / ('dataset-' + dataset_id + '.json')))
        require(isinstance(packet, dict) and set(packet) == {'envelope', 'restore_authority'},
                'Exact post-freeze transfer and current isolated-restore authority required')
        return packet

    def source_packet(self, job_id, machine_id):
        require(_valid_id(job_id) and _valid_id(machine_id), 'Exact job and source machine required')
        packet = strict_loads(self._read(self.runtime_directory / job_id / ('source-' + machine_id + '.json')))
        require(isinstance(packet, dict) and set(packet) == {'power_authority'},
                'Exact current source power authority required')
        return packet


@dataclass(frozen=True)
class MigrationRuntimeBindings:
    """Process-local objects enrolled by the installed worker, never from JSON."""
    dataset_workers: Mapping[tuple[str, str], DatasetWorkerRuntime]
    source_workers: Mapping[tuple[str, str], SourceWorkerRuntime]

    def __post_init__(self):
        require(isinstance(self.dataset_workers, Mapping) and isinstance(self.source_workers, Mapping),
                'Typed per-job enrolled worker bindings required')
        for workers, owner in ((self.dataset_workers, DatasetWorkerRuntime),
                               (self.source_workers, SourceWorkerRuntime)):
            require(all(isinstance(key, tuple) and len(key) == 2
                        and all(_valid_id(value) for value in key) and isinstance(value, owner)
                        for key, value in workers.items()),
                    'A worker binding must select one immutable job and member')
        object.__setattr__(self, 'dataset_workers', MappingProxyType(dict(self.dataset_workers)))
        object.__setattr__(self, 'source_workers', MappingProxyType(dict(self.source_workers)))


class ApplicationMigrationActivities:
    def __init__(self, *, authority, selections, runtimes, journals_directory,
                 outputs_directory, source_root):
        require(isinstance(authority, PostgresExecutionAuthority)
                and isinstance(selections, FileMigrationSelectionStore)
                and isinstance(runtimes, MigrationRuntimeBindings),
                'The installed execution authority, protected stores and enrolled runtimes are required')
        self.authority, self.selections, self.runtimes = authority, selections, runtimes
        self.journals = private_path(journals_directory, directory=True)
        self.outputs = private_path(outputs_directory, directory=True)
        self.source_root = Path(source_root)

    def _current(self, request, kind):
        require(isinstance(request, MigrationActivityRequest), 'Typed admitted migration activity input required')
        return self.authority.require_current(request.admitted, request.selection_digest, kind)

    def _observation(self, request, kind):
        require(isinstance(request, MigrationActivityRequest), 'Typed original migration observation required')
        return self.authority.require_observation(request.admitted, request.selection_digest, kind)

    def _continuation(self, request, kind, runtime, row, operation_scope):
        """Keep the actual claimed intent under its current B10/B11 owners."""
        require(isinstance(runtime, (DatasetWorkerRuntime, SourceWorkerRuntime)),
                'Actual authenticated original worker runtime is required')
        grant = runtime.authority.require_worker_step(runtime.credential, runtime.grant_id,
            step_id=row['step_id'], operation_id=row['operation_id'], operation_kind=kind,
            operation_scope=operation_scope)
        return self.authority.require_current(request.admitted, request.selection_digest, kind,
            continuation_grant=grant, continuation_identity=runtime.identity)

    def _journal(self, job_id):
        path = self.journals / job_id
        try:
            path.mkdir(mode=0o700)
            sync_directory(self.journals)
        except FileExistsError:
            private_path(path, directory=True)
        return path

    def _retain(self, result):
        reference = canonical_record_digest(result)
        path = self.outputs / (reference + '.json')
        try:
            write_new(path, encoded(result))
        except FileExistsError:
            require(load_private(path) == result, 'Retained migration result content changed')
        return reference

    @staticmethod
    def _held(request, hold_code, *, reason='OPERATOR_HOLD', evidence=None):
        return MigrationActivityResult(HELD, request.admitted.job_id, request.member_id,
                                       reason, hold_code, evidence)

    def _data(self, request, *, observation=False):
        gate = self._observation if observation else self._current
        plan, artifact = gate(request, 'RESTORE_DATA')
        selected = self.selections.datasets(artifact['datasetSelectionDigest'])
        return ApplicationDataRunner(job_id=request.admitted.job_id, plan=plan,
            execution_artifact=artifact, selection=selected, ledger=self._journal(request.admitted.job_id))

    @activity.defn(name='application_transfer_dataset')
    def transfer_dataset(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        try:
            runner = self._data(request)
            require(request.mode == 'EXECUTE', 'Restore effects cannot use observation mode')
            runtime = self.runtimes.dataset_workers[(request.admitted.job_id, request.member_id)]
            packet = self.selections.dataset_packet(request.admitted.job_id, request.member_id)
            # The descriptor and packet load may have taken time. Recheck the
            # complete admitted artifact immediately before entering the owner.
            self._current(request, 'RESTORE_DATA')
            result = runner.execute_dataset(request.member_id, runtime=runtime,
                envelope=packet['envelope'], restore_authority=packet['restore_authority'],
                command_authority=ApplicationCommandAuthority(self.authority, request.admitted,
                    request.selection_digest, runtime.identity, 'RESTORE_DATA'))
            reference = self._retain(result)
            self._continuation(request, 'RESTORE_DATA', runtime, runner._row(request.member_id),
                PlanScope.from_record(runner.selection.to_dict()['destination_scope']))
            return MigrationActivityResult(STAGE_VERIFIED, request.admitted.job_id,
                                           request.member_id, evidence_digest=reference)
        except AuthorityDenied:
            return self._held(request, 'CURRENT_AUTHORITY_UNAVAILABLE', reason='AUTHORITY_REVOKED')
        except Exception:
            # A held/invalid request is not permission to repeat a possible
            # restore. The owner journal distinguishes unstarted from uncertain.
            return self._held(request, 'DATASET_EFFECT_REQUIRES_RECONCILIATION', reason='NATIVE_UNCERTAIN')

    @activity.defn(name='application_reconcile_dataset')
    def reconcile_dataset(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        try:
            runner = self._data(request, observation=True)
            runtime = self.runtimes.dataset_workers[(request.admitted.job_id, request.member_id)]
            packet = self.selections.dataset_packet(request.admitted.job_id, request.member_id)
            result = runner.reconcile_dataset(request.member_id, runtime=runtime, envelope=packet['envelope'])
            reference = self._retain(result)
            self._observation(request, 'RESTORE_DATA')
            return MigrationActivityResult(STAGE_VERIFIED, request.admitted.job_id,
                                           request.member_id, evidence_digest=reference)
        except AuthorityDenied:
            return self._held(request, 'CURRENT_AUTHORITY_UNAVAILABLE', reason='AUTHORITY_REVOKED')
        except Exception:
            return self._held(request, 'DATASET_EFFECT_REQUIRES_RECONCILIATION', reason='NATIVE_UNCERTAIN')

    @activity.defn(name='application_join_datasets')
    def join_datasets(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        try:
            runner = self._data(request, observation=True)
            reference = self._retain(runner.join())
            self._observation(request, 'RESTORE_DATA')
            return MigrationActivityResult(STAGE_VERIFIED, request.admitted.job_id,
                                           request.member_id, evidence_digest=reference)
        except AuthorityDenied:
            return self._held(request, 'CURRENT_AUTHORITY_UNAVAILABLE', reason='AUTHORITY_REVOKED')
        except Exception:
            return self._held(request, 'DATASET_EFFECT_REQUIRES_RECONCILIATION', reason='NATIVE_UNCERTAIN')

    @activity.defn(name='application_inspect_datasets')
    def inspect_datasets(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        try:
            runner = self._data(request, observation=True)
            reference = self._retain(runner.inspect())
            self._observation(request, 'RESTORE_DATA')
            return MigrationActivityResult(STAGE_VERIFIED, request.admitted.job_id,
                                           request.member_id, evidence_digest=reference)
        except Exception:
            return self._held(request, 'PRIVATE_MIGRATION_INPUTS_UNAVAILABLE', reason='VALIDATION_FAILED')

    @activity.defn(name='application_source_fence')
    def source_fence(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        try:
            plan, artifact = self._current(request, 'SOURCE_FENCE')
            selected = self.selections.cutover(artifact['cutoverSelectionDigest'])
            runtime = self.runtimes.source_workers[(request.admitted.job_id, request.member_id)]
            packet = self.selections.source_packet(request.admitted.job_id, request.member_id)
            runner = SourceFenceRunner(job_id=request.admitted.job_id, plan=plan,
                execution_artifact=artifact, selection=selected,
                ledger=self._journal(request.admitted.job_id), source_root=self.source_root)
            self._current(request, 'SOURCE_FENCE')
            result = runner.source_fence(request.member_id, runtime=runtime,
                power_authority=packet['power_authority'], resume=request.mode == 'OBSERVE_ORIGINAL',
                command_authority=ApplicationCommandAuthority(self.authority, request.admitted,
                    request.selection_digest, runtime.identity, 'SOURCE_FENCE'))
            reference = self._retain(result)
            row = next(row for row in selected.to_dict()['source_members']
                       if row['machine_id'] == request.member_id)
            self._continuation(request, 'SOURCE_FENCE', runtime, row,
                               PlanScope.from_record(selected.to_dict()['source_scope']))
            return self._held(request, 'SOURCE_RESTART_OR_OTHER_WRITER_EXCLUSION_REQUIRED', evidence=reference)
        except AuthorityDenied:
            return self._held(request, 'CURRENT_AUTHORITY_UNAVAILABLE', reason='AUTHORITY_REVOKED')
        except Exception:
            return self._held(request, 'SOURCE_POWER_REQUIRES_RECONCILIATION', reason='NATIVE_UNCERTAIN')

    def _missing_owner(self, request, kind, code):
        try:
            self._current(request, kind)
            return self._held(request, code)
        except Exception:
            return self._held(request, 'CURRENT_AUTHORITY_UNAVAILABLE', reason='AUTHORITY_REVOKED')

    @activity.defn(name='application_rehearsal')
    def rehearsal(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        return self._missing_owner(request, 'DESTINATION_ACTIVATE', 'ISOLATED_REHEARSAL_OWNER_UNAVAILABLE')

    @activity.defn(name='application_final_sync')
    def final_sync(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        return self._missing_owner(request, 'SOURCE_FENCE', 'FINAL_CONSISTENCY_OWNER_UNAVAILABLE')

    @activity.defn(name='application_cutover')
    def cutover(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        return self._missing_owner(request, 'DESTINATION_ACTIVATE', 'TRAFFIC_AND_TARGET_ACTIVATION_OWNER_UNAVAILABLE')

    @activity.defn(name='application_recovery_inspect')
    def recovery_inspect(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        try:
            plan, _artifact = self._observation(request, 'DESTINATION_ACTIVATE')
            require(_valid_id(request.member_id), 'Original target activation operation required')
            ctx = TenantContext(request.admitted.organization_id, request.admitted.tenant_id)
            with self.authority.connect() as connection, connection.cursor() as cursor:
                _tenant(cursor, ctx)
                cursor.execute(f'SELECT {native_registry._SELECT} FROM '
                    'hosting_controlplane.native_operation_intents WHERE organization_id = %s '
                    'AND tenant_id = %s AND job_id = %s AND operation_id = %s FOR SHARE',
                    (ctx.organization_id, ctx.tenant_id, request.admitted.job_id, request.member_id))
                row = cursor.fetchone()
                intent = native_registry._row(row) if row is not None else None
            result = recovery_projection(plan, target_activation=intent,
                job_id=request.admitted.job_id, original_activation_operation_id=request.member_id)
            reference = self._retain(result)
            self._observation(request, 'DESTINATION_ACTIVATE')
            boundary = result['target_write_boundary']
            code = 'PREWRITE_TARGET_EXCLUSION_REQUIRED' if boundary == \
                'BEFORE_TARGET_WRITES_REQUIRES_CURRENT_EXCLUSION' else \
                'CURRENT_TARGET_WRITE_STATE_REQUIRED' if boundary == 'TARGET_WRITE_STATE_UNKNOWN' else \
                'POSTWRITE_RECOVERY_OWNER_UNAVAILABLE'
            return self._held(request, code, evidence=reference)
        except AuthorityDenied:
            return self._held(request, 'CURRENT_AUTHORITY_UNAVAILABLE', reason='AUTHORITY_REVOKED')
        except Exception:
            return self._held(request, 'CURRENT_TARGET_WRITE_STATE_REQUIRED', reason='NATIVE_UNCERTAIN')
