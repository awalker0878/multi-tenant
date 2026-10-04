"""Fixed Temporal activities around the actual application migration owners.

Only admitted IDs and approved digests cross Temporal history. Protected files,
enrolled worker identities, resource controls and ephemeral secrets are supplied
by the installed runtime. Unimplemented native writer/activation owners return a
precise hold; they are never substituted with an operator assertion or callback.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
from provisioner.execution import execution_journal
from provisioner.execution.run_files import (
    encoded, load_private, private_path, require, sync_directory, write_new)

from .application import ApplicationDataRunner, ApplicationDataSelection, DatasetWorkerRuntime
from .authority import ApplicationCommandAuthority
from .cutover import (SourceFenceRunner, SourceFenceSelection, SourceWorkerRuntime,
                      recovery_projection)
from .lifecycle import ApplicationLifecycleSelection, PHASES
from .application_lifecycle import ApplicationLifecycleRunner, ApplicationRepositoryRuntime, LifecycleHeld
from .remote_app import ApplicationGuestRuntime, ApplicationHealthReadRuntime
from .source_exclusion import SourceDiskFenceRuntime
from .native_openstack import OpenStackApplicationRuntime
from .lifecycle_evidence import ApplicationEvidenceReader
from .traffic import ApplicationTrafficRuntime
from .staging import ApplicationStagedHandover, ApplicationStagingRuntime
from .promotion import ApplicationPromotionRuntime
from .recovery import (ApplicationRecoverySelection, ApplicationRecoveryRuntime,
                       ApplicationRecoveryRunner, FORWARD_PHASES)
from provisioner.controlplane.jobs.progress import APPLICATION_HOLD_CODES

STAGE_VERIFIED = 'STAGE_VERIFIED'
HELD = 'HELD'
_REASONS = frozenset({'NATIVE_UNCERTAIN', 'AUTHORITY_REVOKED', 'OPERATOR_HOLD',
                      'WORKFLOW_FAILED', 'VALIDATION_FAILED'})
_HOLDS = APPLICATION_HOLD_CODES


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
    def __init__(self, *, dataset_directory, cutover_directory, runtime_directory, lifecycle_directory=None,
                 recovery_directory=None, staging_directory=None):
        self.dataset_directory = private_path(dataset_directory, directory=True)
        self.cutover_directory = private_path(cutover_directory, directory=True)
        self.runtime_directory = private_path(runtime_directory, directory=True)
        self.lifecycle_directory = None if lifecycle_directory is None else private_path(lifecycle_directory, directory=True)
        self.recovery_directory = None if recovery_directory is None else private_path(recovery_directory, directory=True)
        self.staging_directory = None if staging_directory is None else private_path(staging_directory, directory=True)

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

    def lifecycle(self, selected_digest):
        require(_valid_digest(selected_digest) and self.lifecycle_directory is not None,
                'The exact protected application lifecycle store is unavailable')
        selected = ApplicationLifecycleSelection(self._read(self.lifecycle_directory / (selected_digest + '.json')))
        require(selected.sha256 == selected_digest, 'The selected application lifecycle content changed')
        return selected

    def staged(self, selected_digest):
        require(_valid_digest(selected_digest) and self.staging_directory is not None,
                'The exact protected real-target handover store is unavailable')
        selected = ApplicationStagedHandover(self._read(self.staging_directory / (selected_digest + '.json')))
        require(selected.sha256 == selected_digest, 'The approved real-target handover changed')
        return selected

    def recovery(self, selected_digest):
        require(_valid_digest(selected_digest) and self.recovery_directory is not None,
                'The separately approved protected application recovery store is unavailable')
        selected = ApplicationRecoverySelection(self._read(self.recovery_directory / (selected_digest + '.json')))
        require(selected.sha256 == selected_digest, 'The original committed-data recovery selection changed')
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
    lifecycle_guests: Mapping[tuple[str, str, str], ApplicationGuestRuntime] = field(default_factory=dict)
    repositories: Mapping[tuple[str, str, str], ApplicationRepositoryRuntime] = field(default_factory=dict)
    source_disk_fences: Mapping[tuple[str, str, str], SourceDiskFenceRuntime] = field(default_factory=dict)
    target_native_workers: Mapping[tuple[str, str, str], OpenStackApplicationRuntime] = field(default_factory=dict)
    evidence_readers: Mapping[str, ApplicationEvidenceReader] = field(default_factory=dict)
    traffic: Mapping[str, ApplicationTrafficRuntime] = field(default_factory=dict)
    health_readers: Mapping[tuple[str, str, str], ApplicationHealthReadRuntime] = field(default_factory=dict)
    staging: Mapping[str, ApplicationStagingRuntime] = field(default_factory=dict)
    promotions: Mapping[str, ApplicationPromotionRuntime] = field(default_factory=dict)
    recoveries: Mapping[str, ApplicationRecoveryRuntime] = field(default_factory=dict)

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
        for name, owner, arity in (
            ('lifecycle_guests', ApplicationGuestRuntime, 3), ('repositories', ApplicationRepositoryRuntime, 3),
            ('source_disk_fences', SourceDiskFenceRuntime, 3), ('target_native_workers', OpenStackApplicationRuntime, 3),
            ('evidence_readers', ApplicationEvidenceReader, 1), ('traffic', ApplicationTrafficRuntime, 1),
            ('health_readers', ApplicationHealthReadRuntime, 3),
            ('staging', ApplicationStagingRuntime, 1), ('promotions', ApplicationPromotionRuntime, 1),
            ('recoveries', ApplicationRecoveryRuntime, 1)):
            values = getattr(self, name)
            require(isinstance(values, Mapping) and all(isinstance(value, owner) and
                    ((_valid_id(key)) if arity == 1 else (isinstance(key, tuple) and len(key) == arity
                    and all(_valid_id(part) for part in key[:2])
                    and (arity != 3 or key[2] in ({'source', 'destination'} if name == 'health_readers' else PHASES))))
                    for key, value in values.items()),
                    'Every application owner must select one exact original job, member and phase')
            object.__setattr__(self, name, MappingProxyType(dict(values)))


class ApplicationMigrationActivities:
    def __init__(self, *, authority, selections, runtimes, journals_directory,
                 outputs_directory, source_root, database_final_proof=None):
        require(isinstance(authority, PostgresExecutionAuthority)
                and isinstance(selections, FileMigrationSelectionStore)
                and isinstance(runtimes, MigrationRuntimeBindings),
                'The installed execution authority, protected stores and enrolled runtimes are required')
        self.authority, self.selections, self.runtimes = authority, selections, runtimes
        self.journals = private_path(journals_directory, directory=True)
        self.outputs = private_path(outputs_directory, directory=True)
        self.source_root = Path(source_root)
        if database_final_proof is not None:
            from .postgresql_activities import DatabaseFinalProofOwner
            require(type(database_final_proof) is DatabaseFinalProofOwner
                and database_final_proof.activities.authority is authority,
                'Only the actual installed SQL final owner may supply the separately selected database proof')
        self.database_final_proof = database_final_proof

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
        database = None
        if 'applicationDatabaseSelectionDigest' in artifact:
            if self.database_final_proof is None:
                raise LifecycleHeld('APPLICATION_LIFECYCLE_OWNER_UNAVAILABLE')
            database = self.database_final_proof.activities.selections.load(artifact['applicationDatabaseSelectionDigest'])
        return ApplicationDataRunner(job_id=request.admitted.job_id, plan=plan,
            execution_artifact=artifact, selection=selected, ledger=self._journal(request.admitted.job_id),
            database_selection=database)

    def _lifecycle(self, request, operation, *, observation=True):
        plan, artifact = (self._observation if observation else self._current)(request, operation)
        selected_digest = artifact.get('applicationLifecycleSelectionDigest')
        if selected_digest is None:
            raise LifecycleHeld('APPLICATION_LIFECYCLE_OWNER_UNAVAILABLE')
        lifecycle = self.selections.lifecycle(selected_digest)
        reader = self.runtimes.evidence_readers.get(request.admitted.job_id)
        if reader is None:
            raise LifecycleHeld('APPLICATION_LIFECYCLE_OWNER_UNAVAILABLE')
        return ApplicationLifecycleRunner(admitted=request.admitted, plan=plan, execution_artifact=artifact,
            lifecycle=lifecycle, datasets=self.selections.datasets(artifact['datasetSelectionDigest']),
            ledger=self._journal(request.admitted.job_id), evidence=reader,
            database_final_proof=self.database_final_proof if 'applicationDatabaseSelectionDigest' in artifact else None)

    def _lifecycle_phase(self, request, phase):
        operation = PHASES[phase][1]
        try:
            runner = self._lifecycle(request, operation)
            members = [request.member_id] if request.member_id else [row['machine_id']
                        for row in runner.lifecycle.to_dict()['members']]
            results = []
            for member_id in members:
                # Observe a retained original completion first. An expired or
                # revoked old writer is never refreshed merely to read it.
                try:
                    receipt, proof = runner.independently_resolved(member_id, phase)
                except (FileNotFoundError, LifecycleHeld):
                    with execution_journal.locked(runner.ledger, runner._scope(member_id, phase)) as log:
                        attempted = bool(log.events)
                    if attempted or request.mode == 'OBSERVE_ORIGINAL':
                        return self._held(request, 'ORIGINAL_APPLICATION_EFFECT_REQUIRES_RECONCILIATION',
                                          reason='NATIVE_UNCERTAIN', evidence=self._retain(runner.inspect()))
                    key = (request.admitted.job_id, member_id, phase)
                    guest = self.runtimes.lifecycle_guests.get(key)
                    if guest is None:
                        raise LifecycleHeld('APPLICATION_LIFECYCLE_OWNER_UNAVAILABLE')
                    self._current(request, operation)
                    native = self.runtimes.target_native_workers.get(key) if phase in {'TARGET_PREPARE', 'TARGET_FENCE', 'POSTWRITE_CAPTURE'} \
                        else self.runtimes.source_disk_fences.get(key)
                    receipt = runner.execute(phase, member_id, guest=guest,
                        repository=self.runtimes.repositories.get(key), native_runtime=native)
                    reference = self._retain(receipt)
                    try:
                        receipt, proof = runner.independently_resolved(member_id, phase)
                    except Exception:
                        return self._held(request, 'ORIGINAL_APPLICATION_EFFECT_REQUIRES_RECONCILIATION',
                                          reason='NATIVE_UNCERTAIN', evidence=reference)
                results.append(dict(member_id=member_id, original_phase_receipt_digest=self._retain(receipt),
                                    current_independent_resolution=proof))
            result = dict(format='hosting-application-lifecycle-stage/1', phase=phase,
                job_id=request.admitted.job_id, lifecycle_digest=runner.lifecycle.sha256,
                original_artifact_digest=request.selection_digest, members=results,
                production_acceptance=False, native_qualification=False)
            return MigrationActivityResult(STAGE_VERIFIED, request.admitted.job_id, request.member_id,
                                           evidence_digest=self._retain(result))
        except LifecycleHeld as exc:
            return self._held(request, exc.hold_code)
        except AuthorityDenied:
            return self._held(request, 'CURRENT_AUTHORITY_UNAVAILABLE', reason='AUTHORITY_REVOKED')
        except Exception:
            return self._held(request, 'ORIGINAL_APPLICATION_EFFECT_REQUIRES_RECONCILIATION', reason='NATIVE_UNCERTAIN')

    def _recovery(self, request, operation):
        plan, artifact = self._observation(request, operation)
        digest = artifact.get('applicationRecoverySelectionDigest')
        runtime = self.runtimes.recoveries.get(request.admitted.job_id)
        if digest is None or runtime is None:
            raise LifecycleHeld('SEPARATELY_APPROVED_RECOVERY_PLAN_REQUIRED')
        return ApplicationRecoveryRunner(admitted=request.admitted, plan=plan, artifact=artifact,
            lifecycle=self.selections.lifecycle(artifact['applicationLifecycleSelectionDigest']),
            selection=self.selections.recovery(digest), runtime=runtime, ledger=self._journal(request.admitted.job_id))

    def _recovery_phase(self, request, phase):
        operation = PHASES[phase][1]
        try:
            runner = self._recovery(request, operation)
            members = [request.member_id] if request.member_id else [row['machine_id']
                for row in runner.lifecycle.to_dict()['members']]
            results = []
            for member_id in members:
                try:
                    receipt, proof = runner.independently_resolved(member_id, phase)
                except (FileNotFoundError, LifecycleHeld):
                    with execution_journal.locked(runner.ledger, runner._scope(member_id, phase)) as log:
                        attempted = bool(log.events)
                    if attempted or request.mode == 'OBSERVE_ORIGINAL':
                        raise LifecycleHeld('ORIGINAL_APPLICATION_EFFECT_REQUIRES_RECONCILIATION')
                    key = (request.admitted.job_id, member_id, phase)
                    guest = self.runtimes.lifecycle_guests.get(key)
                    if guest is None:
                        raise LifecycleHeld('APPLICATION_LIFECYCLE_OWNER_UNAVAILABLE')
                    self._current(request, operation)
                    receipt = runner.execute(phase, member_id, guest=guest,
                        repository=self.runtimes.repositories.get(key),
                        native_runtime=self.runtimes.target_native_workers.get(key))
                    reference = self._retain(receipt)
                    try:
                        receipt, proof = runner.independently_resolved(member_id, phase)
                    except Exception:
                        return self._held(request, 'ORIGINAL_APPLICATION_EFFECT_REQUIRES_RECONCILIATION',
                            reason='NATIVE_UNCERTAIN', evidence=reference)
                results.append(dict(member_id=member_id, original_phase_receipt_digest=self._retain(receipt),
                    current_independent_resolution=proof))
            return MigrationActivityResult(STAGE_VERIFIED, request.admitted.job_id, request.member_id,
                evidence_digest=self._retain(dict(format='hosting-application-recovery-stage/1', phase=phase,
                    job_id=request.admitted.job_id, recovery_selection_digest=runner.selection.sha256,
                    lifecycle_digest=runner.lifecycle.sha256, members=results, production_acceptance=False,
                    native_qualification=False)))
        except LifecycleHeld as exc:
            return self._held(request, exc.hold_code)
        except AuthorityDenied:
            return self._held(request, 'CURRENT_AUTHORITY_UNAVAILABLE', reason='AUTHORITY_REVOKED')
        except Exception:
            return self._held(request, 'ORIGINAL_APPLICATION_EFFECT_REQUIRES_RECONCILIATION', reason='NATIVE_UNCERTAIN')

    @activity.defn(name='application_recovery_reattach')
    def recovery_reattach(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        return self._recovery_phase(request, 'TARGET_REATTACH')

    @activity.defn(name='application_recovery_start')
    def recovery_start(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        return self._recovery_phase(request, 'TARGET_START')

    @activity.defn(name='application_recovery_restore')
    def recovery_restore(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        return self._recovery_phase(request, 'FORWARD_REPAIR')

    @activity.defn(name='application_recovery_activate')
    def recovery_activate(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        return self._recovery_phase(request, 'FORWARD_ACTIVATE')

    @activity.defn(name='application_recovery_verify')
    def recovery_verify(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        try:
            require(request.member_id == '', 'Final repair acceptance must cover every application member')
            runner = self._recovery(request, 'DESTINATION_ACTIVATE')
            original_traffic = self.runtimes.traffic.get(runner.original.admitted.job_id)
            result = runner.verify(traffic=original_traffic, health_readers=self.runtimes.health_readers,
                promotion=self.runtimes.promotions.get(request.admitted.job_id))
            self._observation(request, 'DESTINATION_ACTIVATE')
            return MigrationActivityResult(STAGE_VERIFIED, request.admitted.job_id, '', evidence_digest=self._retain(result))
        except LifecycleHeld as exc:
            return self._held(request, exc.hold_code)
        except AuthorityDenied:
            return self._held(request, 'CURRENT_AUTHORITY_UNAVAILABLE', reason='AUTHORITY_REVOKED')
        except Exception:
            return self._held(request, 'POSTWRITE_COMMITTED_DATA_RECOVERY_REQUIRED', reason='NATIVE_UNCERTAIN')

    @activity.defn(name='application_transfer_dataset')
    def transfer_dataset(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        try:
            runner = self._data(request)
            require(request.mode == 'EXECUTE', 'Restore effects cannot use observation mode')
            _plan, artifact = self._current(request, 'RESTORE_DATA')
            if 'applicationStagingSelectionDigest' in artifact:
                raise LifecycleHeld('ISOLATED_MANAGEMENT_BOOTSTRAP_REQUIRED')
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
        except LifecycleHeld as exc:
            return self._held(request, exc.hold_code)
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
            _plan, selected_artifact = self._observation(request, 'SOURCE_FENCE')
            if selected_artifact.get('applicationLifecycleSelectionDigest') is not None:
                return self._lifecycle_phase(request, 'SOURCE_FENCE')
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
        try:
            _, artifact = self._observation(request, 'DESTINATION_ACTIVATE')
            if artifact.get('applicationLifecycleSelectionDigest') is not None:
                return self._lifecycle_phase(request, 'REHEARSAL')
        except Exception:
            return self._held(request, 'CURRENT_AUTHORITY_UNAVAILABLE', reason='AUTHORITY_REVOKED')
        return self._missing_owner(request, 'DESTINATION_ACTIVATE', 'ISOLATED_REHEARSAL_OWNER_UNAVAILABLE')

    @activity.defn(name='application_final_sync')
    def final_sync(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        try:
            _, artifact = self._observation(request, 'RESTORE_DATA')
            if artifact.get('applicationLifecycleSelectionDigest') is not None:
                return self._lifecycle_phase(request, 'FINAL_SYNC')
        except Exception:
            return self._held(request, 'CURRENT_AUTHORITY_UNAVAILABLE', reason='AUTHORITY_REVOKED')
        return self._missing_owner(request, 'SOURCE_FENCE', 'FINAL_CONSISTENCY_OWNER_UNAVAILABLE')

    @activity.defn(name='application_cutover')
    def cutover(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        try:
            runner = self._lifecycle(request, 'DESTINATION_ACTIVATE')
            result = self._lifecycle_phase(request, 'ACTIVATE')
            if result.status != STAGE_VERIFIED:
                return result
            traffic = self.runtimes.traffic.get(request.admitted.job_id)
            if traffic is None:
                raise LifecycleHeld('CURRENT_APPLICATION_TRAFFIC_REQUIRED')
            members = [request.member_id] if request.member_id else [row['machine_id'] for row in runner.lifecycle.to_dict()['members']]
            facts = []
            for member_id in members:
                member = runner.lifecycle.member(member_id)
                for label in ('cutover_dns', 'cutover_propagation'):
                    traffic.run_stage(request.admitted, strict_loads(runner.artifact_bytes), member['traffic_steps'][label],
                                      lifecycle_runner=runner, health_readers=self.runtimes.health_readers)
                facts.append(traffic.verify(request.admitted, strict_loads(runner.artifact_bytes), member_id))
            return MigrationActivityResult(STAGE_VERIFIED, request.admitted.job_id, request.member_id,
                evidence_digest=self._retain(dict(format='hosting-application-cutover-stage/1',
                    job_id=request.admitted.job_id, lifecycle_digest=runner.lifecycle.sha256,
                    activation_evidence_digest=result.evidence_digest, traffic=facts, production_acceptance=False)))
        except LifecycleHeld as exc:
            if exc.hold_code == 'APPLICATION_LIFECYCLE_OWNER_UNAVAILABLE':
                return self._missing_owner(request, 'DESTINATION_ACTIVATE', 'TRAFFIC_AND_TARGET_ACTIVATION_OWNER_UNAVAILABLE')
            return self._held(request, exc.hold_code)
        except AuthorityDenied:
            return self._held(request, 'CURRENT_AUTHORITY_UNAVAILABLE', reason='AUTHORITY_REVOKED')
        except Exception:
            return self._held(request, 'CURRENT_APPLICATION_TRAFFIC_REQUIRED', reason='NATIVE_UNCERTAIN')

    @activity.defn(name='application_verify_cutover')
    def verify_cutover(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        try:
            require(request.member_id == '', 'Final application acceptance must cover the complete selected member set')
            runner = self._lifecycle(request, 'DESTINATION_ACTIVATE')
            traffic = self.runtimes.traffic.get(request.admitted.job_id)
            if traffic is None:
                raise LifecycleHeld('CURRENT_APPLICATION_TRAFFIC_REQUIRED')
            result = runner.verify_cutover(traffic=traffic, health_readers=self.runtimes.health_readers,
                promotion=self.runtimes.promotions.get(request.admitted.job_id))
            self._observation(request, 'DESTINATION_ACTIVATE')
            return MigrationActivityResult(STAGE_VERIFIED, request.admitted.job_id, '', evidence_digest=self._retain(result))
        except LifecycleHeld as exc:
            return self._held(request, exc.hold_code)
        except AuthorityDenied:
            return self._held(request, 'CURRENT_AUTHORITY_UNAVAILABLE', reason='AUTHORITY_REVOKED')
        except Exception:
            return self._held(request, 'CURRENT_APPLICATION_TRAFFIC_REQUIRED', reason='NATIVE_UNCERTAIN')

    @activity.defn(name='application_stage_targets')
    def stage_targets(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        try:
            require(request.member_id == '', 'Target staging must cover the complete canonical application')
            plan, artifact = self._observation(request, 'DISCOVER_READ')
            runtime = self.runtimes.staging.get(request.admitted.job_id)
            if runtime is None:
                raise LifecycleHeld('APPLICATION_STAGING_OWNER_UNAVAILABLE')
            handover = runtime.associate(request.admitted, artifact)
            require(handover.to_dict()['originalAdmitted']['plan_digest'] == plan['metadata']['planDigest'],
                'The target handover differs from the original creation admission')
            return MigrationActivityResult(STAGE_VERIFIED, request.admitted.job_id, '',
                evidence_digest=self._retain(handover.to_dict()))
        except LifecycleHeld as exc:
            return self._held(request, exc.hold_code)
        except AuthorityDenied:
            return self._held(request, 'CURRENT_AUTHORITY_UNAVAILABLE', reason='AUTHORITY_REVOKED')
        except Exception:
            return self._held(request, 'CURRENT_STAGED_APPLICATION_TARGET_REQUIRED', reason='NATIVE_UNCERTAIN')

    @activity.defn(name='application_verify_staged_data')
    def verify_staged_data(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        try:
            require(request.member_id == '', 'The staged handover must cover the complete new cutover admission')
            plan, artifact = self._current(request, 'DISCOVER_READ')
            digest = artifact.get('applicationStagingSelectionDigest')
            runtime = self.runtimes.staging.get(request.admitted.job_id)
            if digest is None or runtime is None:
                raise LifecycleHeld('APPLICATION_STAGING_OWNER_UNAVAILABLE')
            handover = self.selections.staged(digest); body = runtime.verify(handover)
            require((plan['spec']['workloadRevision'], plan['spec']['destinationSnapshotId'],
                plan['spec']['destination']) == (body['stagedWorkloadRevision'], body['targetSnapshotId'],
                body['destinationScope'])
                and plan['spec'].get('applicationStagedCutover') == dict(
                    format='hosting-application-staged-cutover-plan/1',
                    originalJobId=body['originalAdmitted']['job_id'],
                    originalPlanDigest=body['originalAdmitted']['plan_digest'],
                    originalArtifactDigest=body['originalArtifactDigest'], stagedHandoverDigest=digest),
                'The new current cutover approval differs from its actual canonical TARGET handover')
            lifecycle = self.selections.lifecycle(artifact['applicationLifecycleSelectionDigest'])
            associations = {row['machineId']: row for row in body['associations']}
            require({row['machine_id'] for row in lifecycle.to_dict()['members']} == set(associations)
                and all(row['target']['native_id'] == associations[row['machine_id']]['targetBinding']['nativeId']
                    for row in lifecycle.to_dict()['members']),
                'The application lifecycle selects another actual staged target')
            result = dict(format='hosting-verified-staged-application-targets/1',
                job_id=request.admitted.job_id, staging_selection_digest=digest,
                original_job_id=body['originalAdmitted']['job_id'], workload_digest=body['stagedWorkloadDigest'],
                target_snapshot_digest=body['targetSnapshotDigest'],
                restored_application_data=False, production_acceptance=False, native_qualification=False)
            return MigrationActivityResult(STAGE_VERIFIED, request.admitted.job_id, '',
                evidence_digest=self._retain(result))
        except LifecycleHeld as exc:
            return self._held(request, exc.hold_code)
        except AuthorityDenied:
            return self._held(request, 'CURRENT_AUTHORITY_UNAVAILABLE', reason='AUTHORITY_REVOKED')
        except Exception:
            return self._held(request, 'CURRENT_STAGED_APPLICATION_TARGET_REQUIRED', reason='NATIVE_UNCERTAIN')

    @activity.defn(name='application_target_exclude')
    def target_exclude(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        return self._lifecycle_phase(request, 'TARGET_FENCE')

    @activity.defn(name='application_target_prepare')
    def target_prepare(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        return self._lifecycle_phase(request, 'TARGET_PREPARE')

    @activity.defn(name='application_source_reattach')
    def source_reattach(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        return self._lifecycle_phase(request, 'SOURCE_REATTACH')

    @activity.defn(name='application_source_start')
    def source_start(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        return self._lifecycle_phase(request, 'SOURCE_START')

    @activity.defn(name='application_prewrite_return')
    def prewrite_return(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        return self._lifecycle_phase(request, 'PREWRITE_RETURN')

    @activity.defn(name='application_capture_committed_target')
    def capture_committed_target(self, request: MigrationActivityRequest) -> MigrationActivityResult:
        return self._lifecycle_phase(request, 'POSTWRITE_CAPTURE')

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
