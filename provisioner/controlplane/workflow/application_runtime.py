"""Installed composition for the explicitly selected application workflow.

Environment settings select protected stores only. Native owners, authenticated
worker transports and independent native proof readers are process-local typed
dependencies. This module never enrolls an identity from JSON, imports a factory
named by configuration, mints a native credential or resolves uncertain work.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field, replace
import json
import os
from pathlib import Path
import stat

from provisioner.allocations.transactions import ResourceTransactions
from provisioner.allocations import capacity_owner
from provisioner.controlplane.authority import postgres as authority_postgres
from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.evidence.gate import EvidenceMutationGate
from provisioner.controlplane.evidence.runtime import EvidenceRuntimeConfig
from provisioner.controlplane.operations.action_gate import QualifiedOperatingActionGate
from provisioner.controlplane.operations.runtime import build_action_gate, build_instance_gate
from provisioner.controlplane.operations.instance import OperatingInstanceGate
from provisioner.controlplane.reconciliation.planned import (
    PlannedLeaseAuthority, PlannedNativeCreationRegistry)
from provisioner.controlplane.reconciliation.registry import NativeOperationRegistry
from provisioner.controlplane.reconciliation.resource_authority import PostgresResourceAuthority
from provisioner.controlplane.reconciliation.planned_image import PlannedImageLeaseAuthority
from provisioner.controlplane.worker.grants import PostgresWorkerGrants
from provisioner.controlplane.worker.windows_service_activity import WindowsServiceActivities, WindowsServiceRuntimeBindings
from provisioner.execution import delivery_run
from provisioner.execution.run_files import load_private, private_path, require
from provisioner.migration.activities import (
    ApplicationMigrationActivities, FileMigrationSelectionStore, MigrationRuntimeBindings)
from provisioner.migration.postgresql_activities import (DatabaseRuntimeBindings, DatabaseFinalProofOwner,
    FilePostgresqlSelectionStore, PostgresqlSyncActivities)

from .application_selection import PostgresApplicationSelector
from .admitted_job import AdmittedInput
from .execution_selection import FileExecutionSelectionStore, PostgresExecutionAuthority
from .approval_gate import _valid_digest, _valid_id
from .installed_identity import InstalledApplicationIdentity
from .provisioning_activity import (
    ApplicationProvisioningActivities, FileResourceBundleStore,
    ProvisioningRuntimeBindings, _OFFLINE, _OPERATIONS)
from .resource_recovery_activity import ResourceRecoveryActivityRouter
from .resource_recovery_selection import PostgresResourceRecoverySelector
from .cold_capture_selection import PostgresColdCaptureSelector
from provisioner.migration.cold_selection import FileColdSelectionStore
from provisioner.migration.cold_activities import ColdCaptureActivities, ColdCaptureRuntimeBindings
from provisioner.controlplane.jobs.repository import (_JOB_SELECT, _digest, _ensure_plan,
    _ensure_workload, _job, _payload_from_job, _tenant)
from provisioner.controlplane.persistence import TenantContext


_STORES = {
    'execution_store': 'HOSTING_APPLICATION_EXECUTION_STORE',
    'delivery_store': 'HOSTING_APPLICATION_DELIVERY_STORE',
    'resource_store': 'HOSTING_APPLICATION_RESOURCE_STORE',
    'inbox_store': 'HOSTING_APPLICATION_INBOX_STORE',
    'dataset_store': 'HOSTING_APPLICATION_DATASET_STORE',
    'cutover_store': 'HOSTING_APPLICATION_CUTOVER_STORE',
    'migration_input_store': 'HOSTING_APPLICATION_MIGRATION_INPUT_STORE',
    'journal_store': 'HOSTING_APPLICATION_JOURNAL_STORE',
    'result_store': 'HOSTING_APPLICATION_RESULT_STORE',
    'capacity_database': 'HOSTING_APPLICATION_CAPACITY_DATABASE',
    'source_root': 'HOSTING_APPLICATION_SOURCE_ROOT',
}
_OPTIONAL_STORES = {
    'lifecycle_store': 'HOSTING_APPLICATION_LIFECYCLE_STORE',
    'recovery_store': 'HOSTING_APPLICATION_RECOVERY_STORE',
    'database_store': 'HOSTING_APPLICATION_DATABASE_STORE',
    'staging_store': 'HOSTING_APPLICATION_STAGING_STORE',
    'cold_store': 'HOSTING_APPLICATION_COLD_STORE',
    'runtime_configuration': 'HOSTING_APPLICATION_RUNTIME_CONFIG',
}


def _binding_holds(native=None, migration=None):
    """Missing enrolled components are distinct from unimplemented source."""
    from provisioner.controlplane.worker.adapters.openstack_planning import ScopedOpenStackPlanningRuntime
    from provisioner.controlplane.worker.guest_commands import GuestCommandRuntime
    owners = tuple(native.bindings.values()) if native is not None else ()
    guests = migration.lifecycle_guests if migration is not None else {}
    phases = {key[2] for key in guests}
    checks = {
        'SCOPED_PLANNING_CREDENTIAL_OWNER_UNAVAILABLE':
            any(isinstance(getattr(owner, 'planning_credentials', None), ScopedOpenStackPlanningRuntime)
                for owner in owners),
        'GUEST_PER_COMMAND_AUTHORITY_UNAVAILABLE':
            any(isinstance(getattr(owner, 'commands', None), GuestCommandRuntime)
                for owner in guests.values()) or
            any(isinstance(getattr(owner, 'guest_commands', None), GuestCommandRuntime)
                for owner in owners),
        'ISOLATED_REHEARSAL_OWNER_UNAVAILABLE': 'REHEARSAL' in phases,
        'SOURCE_RESTART_OR_OTHER_WRITER_EXCLUSION_REQUIRED':
            migration is not None and bool(migration.source_disk_fences),
        'FINAL_CONSISTENCY_OWNER_UNAVAILABLE': 'FINAL_SYNC' in phases and bool(migration.repositories),
        'TRAFFIC_AND_TARGET_ACTIVATION_OWNER_UNAVAILABLE': 'ACTIVATE' in phases and bool(migration.traffic),
        'POSTWRITE_RECOVERY_OWNER_UNAVAILABLE':
            migration is not None and bool(getattr(migration, 'recovery_workers', {})),
    }
    return tuple(code for code, present in checks.items() if not present)


class ApplicationRuntimeHold(ValueError):
    """Sanitized startup dependency; never include paths, credentials or causes."""
    def __init__(self, hold_code: str, dependency: str):
        self.hold_code, self.dependency = hold_code, dependency
        super().__init__(f'{hold_code}: {dependency}')

    def projection(self):
        return {'format': 'hosting-application-runtime-status/1', 'status': 'HELD',
                'holdCode': self.hold_code, 'dependency': self.dependency,
                'nativeExecutionAuthorized': False, 'productionActivationAuthorized': False}


def application_execution_enabled(environment=None) -> bool:
    """The worker may register this workflow only after exact explicit opt-in."""
    env = os.environ if environment is None else environment
    value = env.get('HOSTING_APPLICATION_EXECUTION')
    if value not in (None, '0', '1'):
        raise ApplicationRuntimeHold('APPLICATION_EXECUTION_FLAG_INVALID',
                                     'HOSTING_APPLICATION_EXECUTION')
    return value == '1'


def selected_application_runtime_required(connect, admitted):
    """Disabled dispatch may not downgrade a selected graph to the old gate.

    Recheck the original scoped canonical job/plan/current approvals before the
    first Temporal RPC. Plans without an execution selection keep the existing
    gate path. Unavailable or changed plan custody cannot default to that path.
    """
    if not callable(connect) or not isinstance(admitted, AdmittedInput):
        raise ApplicationRuntimeHold('APPLICATION_SELECTION_CANNOT_BE_VERIFIED',
                                     'exact admitted job and scoped PostgreSQL owner')
    try:
        context = TenantContext(admitted.organization_id, admitted.tenant_id)
        with connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, context)
            cursor.execute('SELECT hosting_controlplane.lock_job_scope(%s,%s,%s)',
                           (context.organization_id, context.tenant_id, admitted.job_id))
            require(cursor.fetchone() == (True,), 'The exact admitted job is unavailable')
            cursor.execute(f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                           'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s',
                           (context.organization_id, context.tenant_id, admitted.job_id))
            row = cursor.fetchone()
            require(row is not None, 'The original admitted job is unavailable')
            job = _job(row)
            require((job.job_id, job.plan_id, job.plan_revision, job.plan_digest, job.revocation_epoch) ==
                    (admitted.job_id, admitted.plan_id, admitted.plan_revision, admitted.plan_digest,
                     admitted.revocation_epoch) and _digest(_payload_from_job(job)) == admitted.payload_digest,
                    'The committed original start payload changed')
            cursor.execute('SELECT clock_timestamp()')
            authority_postgres.revalidate_start(cursor, job, cursor.fetchone()[0])
            cursor.execute('SELECT revision,record_digest,record_json FROM '
                           'hosting_controlplane.enterprise_records WHERE organization_id=%s '
                           "AND tenant_id=%s AND record_kind='MigrationPlan' AND record_id=%s FOR SHARE",
                           (context.organization_id, context.tenant_id, job.plan_id))
            plan = _ensure_plan(cursor.fetchone(), context, job)
            _ensure_workload(cursor, context, plan)
            if plan['spec'].get('execution') is not None:
                raise ApplicationRuntimeHold('APPLICATION_SELECTED_DRIVER_RUNTIME_REQUIRED',
                                             'HOSTING_APPLICATION_EXECUTION=1 and commissioned application stores')
            return None
    except ApplicationRuntimeHold:
        raise
    except Exception:
        raise ApplicationRuntimeHold('APPLICATION_SELECTION_CANNOT_BE_VERIFIED',
                                     'current canonical plan and original start payload') from None


def _path_identity(name, value):
    dependency = (_STORES | _OPTIONAL_STORES)[name]
    try:
        require(isinstance(value, Path) and value.is_absolute()
                and str(value) == os.path.normpath(str(value)) and '..' not in value.parts,
                'Canonical absolute store path required')
        if name == 'source_root':
            require(not any(path.is_symlink() for path in (value, *value.parents)),
                    'Immutable source path cannot contain links')
            info = value.stat()
            require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0, os.geteuid())
                    and not stat.S_IMODE(info.st_mode) & 0o022,
                    'Protected installed source directory required')
        else:
            private_path(value, directory=name not in {'capacity_database', 'runtime_configuration'})
            info = value.stat()
            if name in {'capacity_database', 'runtime_configuration'}:
                private_path(value.parent, directory=True)
        return (info.st_dev, info.st_ino, info.st_uid, info.st_mode)
    except Exception:
        raise ApplicationRuntimeHold('APPLICATION_STORE_CUSTODY_UNAVAILABLE', dependency) from None


@dataclass(frozen=True)
class ApplicationRuntimeSettings:
    """Existing explicitly commissioned stores; construction creates nothing."""
    execution_store: Path = field(repr=False)
    delivery_store: Path = field(repr=False)
    resource_store: Path = field(repr=False)
    inbox_store: Path = field(repr=False)
    dataset_store: Path = field(repr=False)
    cutover_store: Path = field(repr=False)
    migration_input_store: Path = field(repr=False)
    journal_store: Path = field(repr=False)
    result_store: Path = field(repr=False)
    capacity_database: Path = field(repr=False)
    source_root: Path = field(repr=False)
    lifecycle_store: Path | None = field(default=None, repr=False)
    recovery_store: Path | None = field(default=None, repr=False)
    database_store: Path | None = field(default=None, repr=False)
    staging_store: Path | None = field(default=None, repr=False)
    cold_store: Path | None = field(default=None, repr=False)
    runtime_configuration: Path | None = field(default=None, repr=False)
    _identities: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        values = {name: getattr(self, name) for name in _STORES | _OPTIONAL_STORES
                  if getattr(self, name) is not None}
        identities = tuple((name, _path_identity(name, value)) for name, value in values.items())
        paths = tuple(values.values())
        if any(left == right or left.is_relative_to(right) or right.is_relative_to(left)
               for index, left in enumerate(paths) for right in paths[index + 1:]):
            raise ApplicationRuntimeHold('APPLICATION_STORES_MUST_BE_SEPARATE',
                                         'protected application stores')
        object.__setattr__(self, '_identities', identities)

    @classmethod
    def from_environment(cls, environment=None):
        env = os.environ if environment is None else environment
        application_execution_enabled(env)
        allowed = set((_STORES | _OPTIONAL_STORES).values()) | {'HOSTING_APPLICATION_EXECUTION'}
        if any(key.startswith('HOSTING_APPLICATION_') and key not in allowed for key in env):
            raise ApplicationRuntimeHold('APPLICATION_SETTING_NOT_IMPLEMENTED',
                                         'HOSTING_APPLICATION_ settings')
        paths = {}
        for name, dependency in (_STORES | _OPTIONAL_STORES).items():
            value = env.get(dependency)
            if value is None and name in _OPTIONAL_STORES:
                continue
            if not isinstance(value, str) or not value or '\x00' in value:
                raise ApplicationRuntimeHold('APPLICATION_STORE_CONFIGURATION_REQUIRED', dependency)
            if not value.startswith('/') or str(Path(value)) != value:
                raise ApplicationRuntimeHold('APPLICATION_STORE_CUSTODY_UNAVAILABLE', dependency)
            paths[name] = Path(value)
        return cls(**paths)

    def require_current(self):
        for name, identity in self._identities:
            if _path_identity(name, getattr(self, name)) != identity:
                raise ApplicationRuntimeHold('APPLICATION_STORE_IDENTITY_CHANGED',
                                             (_STORES | _OPTIONAL_STORES)[name])


@dataclass(frozen=True)
class ApplicationNativeProofBindings:
    """Trusted independently enrolled proof readers, never configuration values.

    Implementations must authenticate retained evidence and reread actual native
    state/fencing. A descriptor, success flag or returned boolean is not proof.
    No such native commissioning is inferred by this installed composition.
    """
    resource: object | None = field(default=None, repr=False)
    creation: object | None = field(default=None, repr=False)
    existing_native: object | None = field(default=None, repr=False)
    service: object | None = field(default=None, repr=False)

    def __post_init__(self):
        required = {
            'resource': ('verify_resource_observation',),
            'creation': ('verify_creation_observation', 'verify_creation_owner_exclusion'),
            'existing_native': ('verify_native_observation', 'verify_owner_exclusion'),
            'service': ('verify_service_observation',),
        }
        for name, methods in required.items():
            owner = getattr(self, name)
            if owner is not None and (isinstance(owner, (dict, str, bytes, Path))
                    or callable(owner) or not all(callable(getattr(owner, method, None))
                                                 for method in methods)):
                raise TypeError('An actual process-local independent native proof owner is required')


class _HeldResourceProof:
    """Reserve can use current admission; no confirmation or refund can pass."""
    def verify_resource_observation(self, cursor, bundle, action, observation):
        raise AuthorityDenied('Independent current resource occupancy/cleanup proof is not commissioned')


@dataclass(frozen=True)
class ApplicationWorkerComponents:
    settings: ApplicationRuntimeSettings = field(repr=False)
    selections: FileExecutionSelectionStore = field(repr=False)
    bundles: FileResourceBundleStore = field(repr=False)
    selector: PostgresApplicationSelector = field(repr=False)
    authority: PostgresExecutionAuthority = field(repr=False)
    action_gate: QualifiedOperatingActionGate = field(repr=False)
    resources: ResourceTransactions = field(repr=False)
    planned_leases: PlannedLeaseAuthority = field(repr=False)
    worker_grants: PostgresWorkerGrants = field(repr=False)
    creation_registry: PlannedNativeCreationRegistry | None = field(repr=False)
    native_registry: NativeOperationRegistry | None = field(repr=False)
    native_proofs: ApplicationNativeProofBindings = field(repr=False)
    provisioning: ApplicationProvisioningActivities = field(repr=False)
    migration: ApplicationMigrationActivities = field(repr=False)
    hold_codes: tuple[str, ...]
    database: PostgresqlSyncActivities | None = field(default=None, repr=False)
    windows_services: WindowsServiceActivities | None = field(default=None, repr=False)
    resource_recovery: ResourceRecoveryActivityRouter | None = field(default=None, repr=False)
    cold_capture: ColdCaptureActivities | None = field(default=None, repr=False)

    @property
    def activities(self):
        # Fixed registered names; no configured module or function is evaluated.
        selected = (self.provisioning.reserve_resources, self.provisioning.provision_step,
                self.migration.transfer_dataset, self.migration.reconcile_dataset,
                self.migration.join_datasets, self.migration.inspect_datasets,
                self.migration.source_fence, self.migration.rehearsal,
                self.migration.final_sync, self.migration.cutover,
                self.migration.verify_cutover, self.migration.target_exclude,
                self.migration.source_reattach, self.migration.source_start,
                self.migration.prewrite_return, self.migration.capture_committed_target,
                self.migration.stage_targets, self.migration.verify_staged_data,
                self.migration.target_prepare,
                self.migration.recovery_inspect,
                self.migration.recovery_reattach, self.migration.recovery_start,
                self.migration.recovery_restore, self.migration.recovery_activate,
                self.migration.recovery_verify)
        if self.database is not None:
            selected += (self.database.database_initialize, self.database.database_synchronize,
                         self.database.database_source_fence, self.database.database_final)
        if self.windows_services is not None:
            selected += (self.windows_services.run_step,)
        if self.resource_recovery is not None:
            selected += self.resource_recovery.activities
        if self.cold_capture is not None:
            selected += self.cold_capture.activities
        return selected

    def projection(self):
        return {'format': 'hosting-application-runtime-status/1',
                'status': 'HELD' if self.hold_codes else 'REGISTERED_REQUIRES_CURRENT_AUTHORIZATION',
                'holdCodes': list(self.hold_codes), 'registeredActivityCount': len(self.activities),
                'nativeExecutionAuthorized': False, 'productionActivationAuthorized': False}

    def graph(self, selection_digest, *, job_id=None):
        return read_only_graph(self.settings, selection_digest, job_id=job_id,
            provisioning_bindings=self.provisioning.native_bindings,
            migration_bindings=self.migration.runtimes, hold_codes=self.hold_codes)

    def with_enrolled_bindings(self, *, provisioning_bindings=None, migration_bindings=None,
                              database_bindings=None, windows_service_bindings=None,
                              staged_resource_bindings=None, resource_recovery_bindings=None,
                              cold_capture_bindings=None):
        """Compose typed owners after the actual broker enrolls live workers.

        Returns a new component set for registration before worker startup. It
        does not mutate active workers or issue an enrollment/grant/credential.
        """
        self.settings.require_current()
        native = (self.provisioning.native_bindings if provisioning_bindings is None
                  else provisioning_bindings)
        migration_runtime = (self.migration.runtimes if migration_bindings is None
                             else migration_bindings)
        database_runtime = (self.database.runtimes if self.database is not None else DatabaseRuntimeBindings({}, {})) \
            if database_bindings is None else database_bindings
        windows_runtime = (self.windows_services.native if self.windows_services is not None
                           else WindowsServiceRuntimeBindings({})) \
            if windows_service_bindings is None else windows_service_bindings
        _require_bound_owners(self.authority.connect, self.worker_grants, self.native_proofs,
                              native, migration_runtime, database_runtime, windows_runtime)
        database = _database_components(self.settings, self.authority, database_runtime)
        if staged_resource_bindings is not None:
            require(isinstance(self.planned_leases, PlannedImageLeaseAuthority),
                    'The original combined lease owner must have been constructed before enrollment')
            self.planned_leases.enroll_staged_resources(staged_resource_bindings)
        provisioning = ApplicationProvisioningActivities(authority=self.authority, resources=self.resources,
            bundles=self.bundles, delivery_directory=self.settings.delivery_store,
            inbox_directory=self.settings.inbox_store, journals_directory=self.settings.journal_store,
            source_root=self.settings.source_root, native_bindings=native,
            migration_selections=self.migration.selections,
            staged_resources=getattr(self.planned_leases, 'staged_resources', {}))
        migration = ApplicationMigrationActivities(authority=self.authority, selections=self.migration.selections,
            runtimes=migration_runtime, journals_directory=self.settings.journal_store,
            outputs_directory=self.settings.result_store, source_root=self.settings.source_root,
            database_final_proof=DatabaseFinalProofOwner(database) if database is not None else None)
        worker_holds = {
            'ENROLLED_NATIVE_PROVISIONING_WORKERS_REQUIRED': not native.bindings,
            'ENROLLED_ISOLATED_TRANSFER_WORKERS_REQUIRED': not migration_runtime.dataset_workers,
            'ENROLLED_SOURCE_POWER_WORKERS_REQUIRED': not
                (migration_runtime.source_workers or migration_runtime.source_disk_fences),
        }
        all_owner_holds = _binding_holds()
        holds = tuple(code for code in self.hold_codes if code not in worker_holds and code not in all_owner_holds)
        holds += tuple(code for code, missing in worker_holds.items() if missing)
        holds += _binding_holds(native, migration_runtime)
        windows = _windows_components(self.settings, self.authority, windows_runtime)
        recovery = self.resource_recovery
        if resource_recovery_bindings is not None:
            recovery = _recovery_components(self.settings, self.selector.recovery_selector,
                self.resources, self.worker_grants, resource_recovery_bindings)
        cold = self.cold_capture
        if cold_capture_bindings is not None:
            require(self.selector.cold_selector is not None, 'The protected cold-purpose store is required')
            cold = _cold_components(self.settings, self.selector.cold_selector, cold_capture_bindings,
                                    self.worker_grants, self.resources)
        return replace(self, provisioning=provisioning, migration=migration, database=database,
                       windows_services=windows, resource_recovery=recovery, cold_capture=cold, hold_codes=holds)


def _require_bound_owners(connect, grants, proofs, native, migration_runtime, database_runtime=None,
                          windows_runtime=None):
    from provisioner.controlplane.reconciliation.service_registry import PlannedServiceRegistry
    if not isinstance(native, ProvisioningRuntimeBindings) or not isinstance(migration_runtime, MigrationRuntimeBindings):
        raise TypeError('Typed per-job process-local enrolled worker runtimes required')
    runtimes = (*native.bindings.values(), *migration_runtime.dataset_workers.values(),
                *migration_runtime.source_workers.values(), *migration_runtime.lifecycle_guests.values(),
                *migration_runtime.repositories.values(), *migration_runtime.source_disk_fences.values(),
                *migration_runtime.target_native_workers.values(), *migration_runtime.evidence_readers.values(),
                *migration_runtime.health_readers.values(),
                *migration_runtime.recoveries.values(),
                *migration_runtime.staging.values(),
                *(owner for traffic in migration_runtime.traffic.values()
                  for owner in (*traffic.writers.values(), *traffic.readers.values())))
    if database_runtime is not None:
        if not isinstance(database_runtime, DatabaseRuntimeBindings):
            raise TypeError('Actual independently enrolled PostgreSQL runtime bindings required')
        runtimes += (*database_runtime.workers.values(), *database_runtime.evidence_readers.values())
    if windows_runtime is not None:
        if type(windows_runtime) is not WindowsServiceRuntimeBindings:
            raise TypeError('Actual independently enrolled existing Windows service runtimes required')
        runtimes += tuple(windows_runtime.bindings.values())
    for runtime in runtimes:
        registry = runtime.registry
        service = isinstance(registry, PlannedServiceRegistry)
        registry_grants, registry_connect = (registry.grants, registry.connect) if service else (
            registry._grants, registry._connect)
        if registry_grants is not grants or registry_connect is not connect:
            raise ApplicationRuntimeHold('APPLICATION_WORKER_OWNER_MISMATCH',
                                         'same current B10/B11 worker owners')
        if proofs.resource is None:
            raise ApplicationRuntimeHold('INDEPENDENT_RESOURCE_PROOF_BINDING_REQUIRED',
                                         'current independently verified occupancy and cleanup')
        proof = proofs.service if service else (proofs.creation
            if isinstance(registry, PlannedNativeCreationRegistry) else proofs.existing_native)
        retained_owner = registry.evidence if service else registry._evidence
        if proof is None or retained_owner is not proof:
            raise ApplicationRuntimeHold('INDEPENDENT_NATIVE_PROOF_BINDING_REQUIRED',
                                         'same independently enrolled native proof owner')
    for runtime in migration_runtime.promotions.values():
        if (runtime.records._connect is not connect or runtime.authority.connect is not connect
                or runtime.enrollment.command.grants is not grants):
            raise ApplicationRuntimeHold('APPLICATION_WORKER_OWNER_MISMATCH',
                                         'current canonical record and independently enrolled read owners')
    if database_runtime is not None:
        from provisioner.migration.postgresql_readback import PostgresqlNativeEvidenceMux
        for job_id, runtime in database_runtime.native_readbacks.items():
            proof = proofs.existing_native
            if (not isinstance(proof, PostgresqlNativeEvidenceMux) or proof.databases.get(job_id) is not runtime
                    or any(enrollment.command.grants is not grants
                           or enrollment.command.authority.connect is not connect
                           for enrollment in (runtime.source, runtime.target))):
                raise ApplicationRuntimeHold('INDEPENDENT_NATIVE_PROOF_BINDING_REQUIRED',
                                             'same current independently enrolled native PostgreSQL proof owner')


def _database_components(settings, authority, runtimes):
    if settings.database_store is None:
        if runtimes.workers or runtimes.evidence_readers:
            raise ApplicationRuntimeHold('APPLICATION_DATABASE_STORE_REQUIRED',
                                         'exact protected PostgreSQL selection store')
        return None
    return PostgresqlSyncActivities(authority=authority,
        selections=FilePostgresqlSelectionStore(settings.database_store), runtimes=runtimes,
        journals_directory=settings.journal_store, outputs_directory=settings.result_store,
        source_root=settings.source_root)


def _windows_components(settings, authority, runtimes):
    return WindowsServiceActivities(authority, settings.delivery_store, settings.inbox_store,
        settings.result_store, settings.source_root, runtimes)


def _cold_components(settings, selector, bindings, grants, resources):
    require(type(bindings) is ColdCaptureRuntimeBindings, 'The concrete enrolled cold owners are required')
    for writer, reader in bindings.exports.values():
        owner = writer.authority
        require(owner.command.grants is grants and owner.registry._grants is grants
                and owner.command.authority.connect is selector.connect
                and owner.registry._connect is selector.connect and owner.resources is resources
                and reader.enrollment.command.grants is grants
                and reader.enrollment.command.authority.connect is selector.connect,
                'Cold export must preserve the original current command, resource and independent read owners')
    for owner in bindings.image_workers.values():
        require(owner.grants is grants and owner.registry.grants is grants
                and owner.registry.leases is grants._leases and owner.registry.connect is selector.connect
                and owner.authority.connect is selector.connect
                and owner.registry.evidence.enrollment.command.grants is grants,
                'Cold image phases must preserve the same current original native and grant owners')
    return ColdCaptureActivities(selector=selector, bindings=bindings, directory=settings.result_store)


def _recovery_components(settings, selector, resources, grants, bindings):
    router = ResourceRecoveryActivityRouter(selector=selector, resources=resources,
        bindings=bindings, directory=settings.result_store)
    require(all(owner.command_runtime.grants is grants and owner.registry._grants is grants
                and owner.command_runtime.authority.connect is selector.connect
                for value in router.bindings.values() for owner in value.cleanup.values()),
            'Resource recovery must preserve the actual current command and original native grant owners')
    return router


def _reuse_grant_owner(connect, settings, selections, bundles, grants):
    """Do not silently repoint a live broker's authoritative lease source."""
    if not isinstance(grants, PostgresWorkerGrants):
        raise ApplicationRuntimeHold('PLANNED_WORKER_GRANT_OWNER_REQUIRED', 'PostgresWorkerGrants')
    leases = grants._leases
    if (not isinstance(leases, PlannedLeaseAuthority) or grants._connect is not connect
            or leases._connect is not connect or leases.authority is not authority_postgres
            or not isinstance(leases.selections, FileExecutionSelectionStore)
            or leases.selections.directory != selections.directory
            or not isinstance(leases.bundle_lookup, FileResourceBundleStore)
            or leases.bundle_lookup.directory != bundles.directory
            or Path(leases.resources.database) != settings.capacity_database
            or not isinstance(leases.resources.authority, PostgresResourceAuthority)
            or leases.resources.authority._connect is not connect
            or leases.resources.authority._authority is not authority_postgres
            or not isinstance(leases.resources.authority._selections, FileExecutionSelectionStore)
            or leases.resources.authority._selections.directory != selections.directory):
        raise ApplicationRuntimeHold('PLANNED_WORKER_GRANT_OWNER_REQUIRED',
                                     'same planned and existing native lease owner')
    return leases.resources, leases


def build_application_worker_components(connect, evidence_gate, *, settings=None,
        environment=None, worker_grants=None, native_proof_bindings=None,
        provisioning_bindings=None, migration_bindings=None, database_bindings=None,
        windows_service_bindings=None, resource_recovery_bindings=None, cold_capture_bindings=None,
        instance_gate=None):
    """Compose real installed owners; empty enrollment holds native dispatch.

    A trusted service may supply already enrolled typed runtimes. Nothing in the
    environment can import them or turn files/certificate bytes into a current
    authenticated worker transport. The common B10 owner covers existing native
    leases and B23 planned resources through the same PostgreSQL grant ledger.
    """
    if not callable(connect) or not isinstance(evidence_gate, EvidenceMutationGate):
        raise ApplicationRuntimeHold('APPLICATION_AUTHORITY_OWNER_REQUIRED',
                                     'scoped PostgreSQL and independent EvidenceMutationGate')
    env = os.environ if environment is None else environment
    settings = ApplicationRuntimeSettings.from_environment(env) if settings is None else settings
    if not isinstance(settings, ApplicationRuntimeSettings):
        raise TypeError('Validated explicit application store settings required')
    settings.require_current()
    proofs = ApplicationNativeProofBindings() if native_proof_bindings is None else native_proof_bindings
    if not isinstance(proofs, ApplicationNativeProofBindings):
        raise TypeError('Typed independently commissioned native proof bindings required')
    native = ProvisioningRuntimeBindings() if provisioning_bindings is None else provisioning_bindings
    migration_runtime = MigrationRuntimeBindings({}, {}) if migration_bindings is None else migration_bindings
    database_runtime = DatabaseRuntimeBindings({}, {}) if database_bindings is None else database_bindings
    windows_runtime = WindowsServiceRuntimeBindings({}) if windows_service_bindings is None else windows_service_bindings
    if not isinstance(native, ProvisioningRuntimeBindings) or not isinstance(migration_runtime, MigrationRuntimeBindings):
        raise TypeError('Typed per-job process-local enrolled worker runtimes required')

    selections = FileExecutionSelectionStore(settings.execution_store)
    bundles = FileResourceBundleStore(settings.resource_store)
    if worker_grants is None:
        resource_authority = PostgresResourceAuthority(connect, authority_postgres,
            selections, proofs.resource if proofs.resource is not None else _HeldResourceProof())
        resources = ResourceTransactions(settings.capacity_database, resource_authority)
        planned_leases = PlannedImageLeaseAuthority(connect, resources=resources,
            selections=selections, bundle_lookup=bundles)
        worker_grants = PostgresWorkerGrants(connect, planned_leases)
    else:
        resources, planned_leases = _reuse_grant_owner(connect, settings, selections, bundles, worker_grants)
        selections, bundles = planned_leases.selections, planned_leases.bundle_lookup
        if proofs.resource is not None and resources.authority._evidence is not proofs.resource:
            raise ApplicationRuntimeHold('RESOURCE_PROOF_OWNER_CHANGED', 'same independent resource proof owner')

    try:
        with capacity_owner.database(resources.database) as database:
            capacity_owner.verify_events(database)
            row = database.execute('SELECT body FROM envelope WHERE singleton=1').fetchone()
            require(row is not None, 'A commissioned existing capacity owner is required')
            from provisioner.execution.neutron_observe import strict_loads
            capacity_owner.validate_envelope(strict_loads(row[0]))
    except Exception:
        raise ApplicationRuntimeHold('APPLICATION_CAPACITY_OWNER_UNAVAILABLE',
                                     'existing commissioned capacity owner and original event chain') from None

    try:
        # Verification-only custody must already be restored/high-water current
        # for every commissioned worker tenant before activity registration.
        config = EvidenceRuntimeConfig.from_environment(env)
        scopes = config.startup_scopes()
        if not scopes:
            raise ValueError('At least one explicitly commissioned application tenant is required')
        for context in scopes:
            evidence_gate.require(context)
        gates = build_action_gate(evidence_gate, environment=env, worker_grants=worker_grants)
    except Exception:
        raise ApplicationRuntimeHold('APPLICATION_EVIDENCE_OR_OPERATING_TRUST_UNAVAILABLE',
                                     'independent startup custody and operating-signature trust') from None
    if not isinstance(gates, QualifiedOperatingActionGate):
        raise ApplicationRuntimeHold('APPLICATION_ACTION_GATE_OWNER_REQUIRED',
                                     'fixed qualification and operating gate composition')
    if instance_gate is None and settings.runtime_configuration is not None:
        try:
            installed = InstalledApplicationIdentity.from_configuration(
                settings.runtime_configuration, settings.source_root)
            instance_gate = build_instance_gate(evidence_gate, source_commit=installed.source_commit,
                artifact_sha256=installed.artifact_sha256, environment=env, installed_identity=installed)
        except Exception:
            raise ApplicationRuntimeHold('APPLICATION_INSTALLED_IDENTITY_OR_INSTANCE_TRUST_UNAVAILABLE',
                                         'exact sealed runtime and current operating instance custody') from None
    if instance_gate is not None and not isinstance(instance_gate, OperatingInstanceGate):
        raise TypeError('Only the concrete independently signed operating instance owner may authorize writes')
    authority = PostgresExecutionAuthority(connect, selections, gates.qualification,
                                          evidence_gate, gates.operations, instance_gate=instance_gate)
    creation_registry = (PlannedNativeCreationRegistry(connect, leases=planned_leases,
        grants=worker_grants, evidence=proofs.creation) if proofs.creation is not None else None)
    native_registry = (NativeOperationRegistry(connect, grants=worker_grants,
        evidence=proofs.existing_native) if proofs.existing_native is not None else None)

    _require_bound_owners(connect, worker_grants, proofs, native, migration_runtime, database_runtime, windows_runtime)
    migration_selections = FileMigrationSelectionStore(dataset_directory=settings.dataset_store,
        cutover_directory=settings.cutover_store, runtime_directory=settings.migration_input_store,
        lifecycle_directory=settings.lifecycle_store, recovery_directory=settings.recovery_store,
        staging_directory=settings.staging_store)
    database = _database_components(settings, authority, database_runtime)
    provisioning = ApplicationProvisioningActivities(authority=authority, resources=resources,
        bundles=bundles, delivery_directory=settings.delivery_store, inbox_directory=settings.inbox_store,
        journals_directory=settings.journal_store, source_root=settings.source_root, native_bindings=native,
        migration_selections=migration_selections,
        staged_resources=getattr(planned_leases, 'staged_resources', {}))
    migration = ApplicationMigrationActivities(authority=authority,
        selections=migration_selections,
        runtimes=migration_runtime, journals_directory=settings.journal_store,
        outputs_directory=settings.result_store, source_root=settings.source_root,
        database_final_proof=DatabaseFinalProofOwner(database) if database is not None else None)
    holds = []
    if instance_gate is None:
        holds.append('COMMISSIONED_INSTALLED_OPERATING_INSTANCE_REQUIRED')
    if isinstance(resources.authority._evidence, _HeldResourceProof):
        holds.append('INDEPENDENT_RESOURCE_OCCUPANCY_AND_CLEANUP_PROOF_REQUIRED')
    if creation_registry is None:
        holds.append('INDEPENDENT_CREATION_AND_OLD_WRITER_EXCLUSION_PROOF_REQUIRED')
    if native_registry is None:
        holds.append('INDEPENDENT_NATIVE_OBSERVATION_AND_OLD_WRITER_EXCLUSION_PROOF_REQUIRED')
    if not native.bindings:
        holds.append('ENROLLED_NATIVE_PROVISIONING_WORKERS_REQUIRED')
    if not migration_runtime.dataset_workers:
        holds.append('ENROLLED_ISOLATED_TRANSFER_WORKERS_REQUIRED')
    if not (migration_runtime.source_workers or migration_runtime.source_disk_fences):
        holds.append('ENROLLED_SOURCE_POWER_WORKERS_REQUIRED')
    holds.extend(_binding_holds(native, migration_runtime))
    recovery_selector = PostgresResourceRecoverySelector(connect, selections, bundles)
    cold_selector = (PostgresColdCaptureSelector(connect, selections, FileColdSelectionStore(settings.cold_store))
                     if settings.cold_store is not None else None)
    selector = PostgresApplicationSelector(connect, selections, settings.delivery_store,
            migration_selections=migration_selections,
            database_selections=database.selections if database is not None else None,
            recovery_selector=recovery_selector, cold_selector=cold_selector)
    recovery = _recovery_components(settings, recovery_selector, resources, worker_grants,
        {} if resource_recovery_bindings is None else resource_recovery_bindings)
    if cold_capture_bindings is not None and cold_selector is None:
        raise ApplicationRuntimeHold('APPLICATION_COLD_STORE_REQUIRED', 'exact protected cold capture selection store')
    cold = (_cold_components(settings, cold_selector, ColdCaptureRuntimeBindings()
             if cold_capture_bindings is None else cold_capture_bindings, worker_grants, resources)
             if cold_selector is not None else None)
    return ApplicationWorkerComponents(settings, selections, bundles, selector, authority,
        gates, resources, planned_leases, worker_grants, creation_registry, native_registry, proofs,
        provisioning, migration, tuple(holds), database, _windows_components(settings, authority, windows_runtime),
        recovery, cold)


def _resource_recovery_selector(connect, selections, bundles):
    from .resource_recovery_selection import PostgresResourceRecoverySelector
    return PostgresResourceRecoverySelector(connect, selections, bundles)


def read_only_graph(settings, selection_digest, *, job_id=None,
                    provisioning_bindings=None, migration_bindings=None, hold_codes=()):
    """Display digest-verified graph references with no database or native call.

    Presence of a process-local binding is displayed only as a binding. The
    original job/plan/current approvals/epoch, native qualification, operating
    acceptance and per-effect worker grant must still be checked by activities.
    Protected packet filenames, commands, tokens and target paths are omitted.
    """
    if not isinstance(settings, ApplicationRuntimeSettings) or not _valid_digest(selection_digest):
        raise ApplicationRuntimeHold('APPLICATION_GRAPH_SELECTION_REQUIRED', 'full selected artifact digest')
    if job_id is not None and not _valid_id(job_id):
        raise ApplicationRuntimeHold('APPLICATION_GRAPH_JOB_REFERENCE_INVALID', 'bounded original job ID')
    if (provisioning_bindings is not None and not isinstance(provisioning_bindings, ProvisioningRuntimeBindings)
            or migration_bindings is not None and not isinstance(migration_bindings, MigrationRuntimeBindings)):
        raise TypeError('Only typed process-local owner bindings may be displayed')
    settings.require_current()
    try:
        selection = FileExecutionSelectionStore(settings.execution_store).load_verified(selection_digest)
        if selection['driver'] in {'windows-server-2022-existing-services/1',
                'vmware-openstack-cold-capture/1', 'application-postwrite-recovery/1'}:
            return _purpose_graph(settings, selection_digest, selection, hold_codes)
        delivery = load_private(settings.delivery_store / (selection['deliveryPlanDigest'] + '.json'))
        delivery_run.validate(delivery)
        require(_digest(delivery) == selection['deliveryPlanDigest']
                and delivery['source_commit'] == selection['sourceCommit']
                and delivery['scope'] == selection['executionScope']
                and {step['id'] for step in delivery['steps']} == set(selection['stageBindings'])
                and all(selection['stageBindings'][step['id']]['kind'] == step['kind']
                        for step in delivery['steps']), 'The protected delivery selection changed')
        migration_store = FileMigrationSelectionStore(dataset_directory=settings.dataset_store,
            cutover_directory=settings.cutover_store, runtime_directory=settings.migration_input_store,
            lifecycle_directory=settings.lifecycle_store, recovery_directory=settings.recovery_store,
            staging_directory=settings.staging_store)
        resource_selection = selection
        if selection.get('applicationStagingSelectionDigest') is not None:
            staged = migration_store.staged(selection['applicationStagingSelectionDigest']).to_dict()
            resource_selection = FileExecutionSelectionStore(settings.execution_store).load_verified(
                staged['originalArtifactDigest'])
            require(staged['originalResourceBundleDigest'] == selection['resourceBundleDigest']
                    and staged['stagedWorkloadRevision'] == selection['workloadRevision'],
                    'The protected original resource charge or staged workload changed')
        resources = FileResourceBundleStore(settings.resource_store).load_document(resource_selection['resourceBundleDigest'])
        require((resources['workload_id'], resources['workload_revision']) ==
                    (resource_selection['workloadId'], resource_selection['workloadRevision']),
                'The protected original resource selection changed')
        staging_only = selection['driver'] == 'openstack-linux-application-staging/1'
        datasets = (None if staging_only else migration_store.datasets(selection['datasetSelectionDigest']).to_dict())
        cutover = (None if staging_only else migration_store.cutover(selection['cutoverSelectionDigest']).to_dict())
        lifecycle = (migration_store.lifecycle(selection['applicationLifecycleSelectionDigest']).to_dict()
                     if selection.get('applicationLifecycleSelectionDigest') is not None else None)
        database = None
        if selection.get('applicationDatabaseSelectionDigest') is not None:
            require(settings.database_store is not None, 'The exact protected PostgreSQL descriptor is required')
            database = FilePostgresqlSelectionStore(settings.database_store).load(
                selection['applicationDatabaseSelectionDigest']).to_dict()
            require((database['source_scope'], database['target_scope']) ==
                        (selection['source'], selection['destination']),
                    'The selected SQL method changed its protected scopes')
        require(staging_only or ((datasets['source_scope'], datasets['destination_scope'], datasets['guest_profile']) ==
                (selection['source'], selection['destination'], selection['guestProfile'])
                and (cutover['source_scope'], cutover['destination_scope']) ==
                    (selection['source'], selection['destination'])),
                'Selected migration descriptors cross the selected scopes')
    except ApplicationRuntimeHold:
        raise
    except Exception:
        raise ApplicationRuntimeHold('APPLICATION_GRAPH_INPUTS_UNAVAILABLE',
                                     'original digest-bound protected descriptors') from None
    native = provisioning_bindings
    migration = migration_bindings
    traffic_activities = ({step_id: ('application_cutover' if name.startswith('cutover_')
                                     else 'application_prewrite_return')
                          for member in lifecycle['members']
                          for name, step_id in member['traffic_steps'].items()}
                         if lifecycle is not None else {})
    stages = []
    for step in delivery['steps']:
        kind = step['kind']
        owner = native.selected(job_id, step['id']) if native is not None and job_id is not None else None
        supported = kind in _OFFLINE or kind in _OPERATIONS
        stages.append({'stepId': step['id'], 'kind': kind, 'needs': list(step['needs']),
            'activity': traffic_activities.get(step['id'], 'application_provision_step'),
            'ownerBinding': 'OFFLINE_INSTALLED_OWNER' if kind in _OFFLINE else
                'PROCESS_LOCAL_BINDING_REQUIRES_CURRENT_AUTHORIZATION' if owner is not None else
                'ENROLLED_NATIVE_OWNER_REQUIRED' if supported else 'STAGE_OWNER_NOT_IMPLEMENTED'})
    children = [{'datasetId': row['dataset_id'], 'consistencyGroupId': row['consistency_group_id'],
        'activity': 'application_transfer_dataset', 'parallelBatch': index // 4,
        'ownerBinding': 'PROCESS_LOCAL_BINDING_REQUIRES_CURRENT_AUTHORIZATION'
            if migration is not None and (job_id, row['dataset_id']) in migration.dataset_workers
            else 'ENROLLED_ISOLATED_TRANSFER_WORKER_REQUIRED'}
        for index, row in enumerate(datasets['datasets'] if datasets is not None else [])]
    sources = [{'machineId': row['machine_id'], 'activity': 'application_source_fence',
        'ownerBinding': 'PROCESS_LOCAL_BINDING_REQUIRES_CURRENT_AUTHORIZATION'
            if migration is not None and (job_id, row['machine_id']) in migration.source_workers
            else 'ENROLLED_SOURCE_POWER_WORKER_REQUIRED'} for row in (cutover['source_members'] if cutover is not None else [])]
    return {'format': 'hosting-application-runtime-graph/1', 'status': 'READ_ONLY',
        'selectionDigest': selection_digest, 'jobId': job_id,
        'driver': selection['driver'], 'route': 'vmware-to-openstack',
        'guestProfile': selection['guestProfile'], 'workloadId': selection['workloadId'],
        'workloadRevision': selection['workloadRevision'],
        'resourceActivity': ('application_reserve_resources' if selection['driver'] in {
            'openstack-linux-rebuild/1', 'openstack-linux-application-staging/1'} else None),
        'stagingActivity': 'application_stage_targets' if staging_only else 'application_verify_staged_data'
            if selection.get('applicationStagingSelectionDigest') else None,
        'stagingSelectionDigest': selection.get('applicationStagingSelectionDigest'), 'provisioning': stages,
        'datasetChildren': children, 'datasetJoinActivity': 'application_join_datasets',
        'sourceMembers': sources,
        'lifecycleSelectionDigest': selection.get('applicationLifecycleSelectionDigest'),
        'databaseSelectionDigest': selection.get('applicationDatabaseSelectionDigest'),
        'databaseStages': ([{'activity': 'application_database_' + phase, 'memberId': database['memberId']}
                            for phase in ('initialize', 'synchronize', 'source_fence', 'final')]
                           if database is not None else []),
        'finalAcceptanceActivity': 'application_verify_cutover' if lifecycle is not None else None,
        'heldStages': list(dict.fromkeys((*hold_codes, *_binding_holds(native, migration)))),
        'nativeExecutionAuthorized': False, 'productionActivationAuthorized': False}


def _purpose_graph(settings, selection_digest, selection, hold_codes):
    """Expose fixed partial/recovery owners without inventing migration support."""
    driver = selection['driver']
    stages, purpose_digest = [], None
    if driver == 'windows-server-2022-existing-services/1':
        from .windows_service_selection import WindowsServiceSelection
        purpose = WindowsServiceSelection.from_record(selection['windowsServices'])
        delivery = load_private(settings.delivery_store / (selection['deliveryPlanDigest'] + '.json'))
        purpose.require_delivery(delivery)
        require(_digest(delivery) == selection['deliveryPlanDigest']
                and delivery['source_commit'] == selection['sourceCommit']
                and delivery['scope'] == selection['executionScope'], 'The fixed Windows delivery changed')
        stages = [{'stepId': row['id'], 'kind': row['kind'], 'activity': 'windows_existing_service_step'}
                  for row in delivery['steps']]
        purpose_digest = purpose.sha256
    elif driver == 'vmware-openstack-cold-capture/1':
        from provisioner.migration.cold_selection import FileColdSelectionStore
        require(settings.cold_store is not None, 'The actual protected cold selection store is required')
        cold = FileColdSelectionStore(settings.cold_store).load_verified(selection['coldCaptureSelectionDigest'])
        body = cold.to_dict()
        require((body['source_scope'], body['destination_scope'], body['guest_profile']) ==
                    (selection['source'], selection['destination'], selection['guestProfile']),
                'The protected cold purpose changed its native scope or profile')
        stages = [{'activity': name} for name in ('cold_capture_export', 'cold_capture_import', 'cold_capture_verify')]
        purpose_digest = cold.sha256
    else:
        store = FileMigrationSelectionStore(dataset_directory=settings.dataset_store,
            cutover_directory=settings.cutover_store, runtime_directory=settings.migration_input_store,
            lifecycle_directory=settings.lifecycle_store, recovery_directory=settings.recovery_store,
            staging_directory=settings.staging_store)
        purpose = store.recovery(selection['applicationRecoverySelectionDigest'])
        lifecycle = store.lifecycle(selection['applicationLifecycleSelectionDigest'])
        require(purpose.to_dict()['currentLifecycleDigest'] == lifecycle.sha256,
                'The protected current recovery lifecycle changed')
        stages = [{'memberId': member, 'activity': 'application_recovery_' + phase}
                  for member in purpose.members for phase in ('reattach', 'start', 'restore', 'activate')]
        stages.append({'activity': 'application_recovery_verify'})
        purpose_digest = purpose.sha256
    return {'format': 'hosting-selected-application-graph/1', 'selectionDigest': selection_digest,
        'driver': driver, 'purposeSelectionDigest': purpose_digest, 'purposeStages': stages,
        'guestProfile': selection['guestProfile'], 'workloadId': selection['workloadId'],
        'workloadRevision': selection['workloadRevision'], 'heldStages': list(hold_codes),
        'nativeExecutionAuthorized': False, 'productionActivationAuthorized': False,
        'ordinaryMigrationQualified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Display the original private application graph without execution')
    parser.add_argument('action', choices=('graph',))
    parser.add_argument('--selection-digest', required=True)
    parser.add_argument('--job-id')
    args = parser.parse_args(argv)
    try:
        result = read_only_graph(ApplicationRuntimeSettings.from_environment(),
                                args.selection_digest, job_id=args.job_id)
        print(json.dumps(result, sort_keys=True, separators=(',', ':')))
        return 0
    except ApplicationRuntimeHold as hold:
        print(json.dumps(hold.projection(), sort_keys=True, separators=(',', ':')))
        return 2
    except Exception:
        print(json.dumps(ApplicationRuntimeHold('APPLICATION_RUNTIME_HELD',
            'protected installed application runtime').projection(), sort_keys=True, separators=(',', ':')))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
