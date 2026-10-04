"""Read the original plan-selected graph when starting a new workflow type."""
from __future__ import annotations

from pathlib import Path

from provisioner.controlplane.authority import postgres as authority_postgres
from provisioner.controlplane.jobs.repository import (_JOB_SELECT, _digest, _ensure_plan,
    _ensure_workload, _job, _payload_from_job, _tenant)
from provisioner.controlplane.persistence import TenantContext
from provisioner.execution.delivery_run import validate as validate_delivery
from provisioner.execution.run_files import load_private, private_path, require
from .application_job import ApplicationJobInput
from .application_staging_job import ApplicationStagingInput
from .application_cutover_job import ApplicationCutoverInput
from .execution_selection import (DRIVER, DATABASE_DRIVER, STAGING_DRIVER, CUTOVER_DRIVER,
                                 APPLICATION_RECOVERY_DRIVER, FileExecutionSelectionStore)

_RESOURCE_RECOVERY = object()
_WINDOWS_SERVICES = object()
_COLD_CAPTURE = object()
CREATION_STAGES = frozenset({'terraform_plan', 'terraform_apply', 'terraform_approval',
                             'capacity', 'ipam', 'openstack_quota'})


def initial_provisioning_steps(delivery, lifecycle):
    """Reserve reviewed traffic steps for the current lifecycle phase owner."""
    from provisioner.migration.lifecycle import ApplicationLifecycleSelection
    require(isinstance(lifecycle, ApplicationLifecycleSelection),
            'An actual validated application lifecycle is required')
    members = lifecycle.to_dict()['members']
    traffic = {step_id: ('dns_cutover' if name.endswith('_dns') else 'dns_propagation')
               for member in members for name, step_id in member['traffic_steps'].items()}
    deferred = set(traffic)
    require(deferred and deferred <= {step['id'] for step in delivery['steps']},
            'Every phase-owned traffic stage must occur in the reviewed delivery graph')
    require(all(step['kind'] == traffic[step['id']] for step in delivery['steps']
                if step['id'] in deferred), 'A lifecycle traffic stage has the wrong fixed owner')
    first_deferred = next(index for index, step in enumerate(delivery['steps'])
                          if step['id'] in deferred)
    require(all(step['id'] in deferred for step in delivery['steps'][first_deferred:])
            and all(not deferred.intersection(step['needs']) for step in delivery['steps']
                    if step['id'] not in deferred),
            'Traffic stages must follow initial provisioning and be owned by lifecycle phases')
    return tuple(step['id'] for step in delivery['steps'] if step['id'] not in deferred)


class PostgresApplicationSelector:
    """No native action or qualification is granted by this bounded read."""
    def __init__(self, connect, selections: FileExecutionSelectionStore, delivery_store: Path,
                 *, migration_selections=None, database_selections=None, recovery_selector=None,
                 cold_selector=None):
        require(callable(connect) and isinstance(selections, FileExecutionSelectionStore),
                'Actual scoped plan and protected selection owners are required')
        self.connect, self.selections = connect, selections
        self.delivery_store = private_path(delivery_store, directory=True)
        if migration_selections is not None:
            from provisioner.migration.activities import FileMigrationSelectionStore
            require(isinstance(migration_selections, FileMigrationSelectionStore),
                    'The concrete protected migration descriptor owner is required')
        self.migration_selections = migration_selections
        if database_selections is not None:
            from provisioner.migration.postgresql_activities import FilePostgresqlSelectionStore
            require(isinstance(database_selections, FilePostgresqlSelectionStore),
                    'Actual protected PostgreSQL method descriptor store required')
        if recovery_selector is not None:
            from .resource_recovery_selection import PostgresResourceRecoverySelector
            require(isinstance(recovery_selector, PostgresResourceRecoverySelector)
                    and recovery_selector.connect is connect,
                    'Actual scoped fixed resource recovery selector required')
        self.database_selections, self.recovery_selector = database_selections, recovery_selector
        from .windows_service_selection import PostgresWindowsServiceSelector
        self.windows_selector = PostgresWindowsServiceSelector(connect, selections, self.delivery_store)
        if cold_selector is not None:
            from .cold_capture_selection import PostgresColdCaptureSelector
            require(type(cold_selector) is PostgresColdCaptureSelector and cold_selector.connect is connect,
                    'The concrete current protected cold-purpose selector is required')
        self.cold_selector = cold_selector

    def __call__(self, admitted):
        selected = self._selected_input(admitted)
        if selected is _RESOURCE_RECOVERY:
            require(self.recovery_selector is not None, 'The fixed recovery workflow is unavailable')
            # The original selection transaction has ended. The recovery owner
            # independently locks and rereads this same admission, rather than
            # waiting on our own lock through a second connection.
            return self.recovery_selector(admitted)
        if selected is _WINDOWS_SERVICES:
            return self.windows_selector(admitted)
        if selected is _COLD_CAPTURE:
            require(self.cold_selector is not None, 'The exact protected cold-purpose store is unavailable')
            return self.cold_selector(admitted)
        return selected

    def _selected_input(self, admitted):
        context = TenantContext(admitted.organization_id, admitted.tenant_id)
        with self.connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, context)
            cursor.execute('SELECT hosting_controlplane.lock_job_scope(%s,%s,%s)',
                           (context.organization_id, context.tenant_id, admitted.job_id))
            require(cursor.fetchone() == (True,), 'The original job is unavailable')
            cursor.execute(f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                           'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s',
                           (context.organization_id, context.tenant_id, admitted.job_id))
            row = cursor.fetchone()
            require(row is not None, 'The job is not visible in this tenant')
            job = _job(row)
            require(_digest(_payload_from_job(job)) == admitted.payload_digest,
                    'The committed start payload changed')
            cursor.execute('SELECT clock_timestamp()')
            authority_postgres.revalidate_start(cursor, job, cursor.fetchone()[0])
            cursor.execute('SELECT revision, record_digest, record_json FROM '
                           'hosting_controlplane.enterprise_records WHERE organization_id=%s '
                           "AND tenant_id=%s AND record_kind='MigrationPlan' AND record_id=%s FOR SHARE",
                           (context.organization_id, context.tenant_id, job.plan_id))
            plan = _ensure_plan(cursor.fetchone(), context, job)
            _ensure_workload(cursor, context, plan)
            selected = plan['spec'].get('execution')
            if selected is None:
                return None
            if plan['spec'].get('resourceRecovery') is not None:
                return _RESOURCE_RECOVERY
            if plan['spec'].get('windowsServices') is not None:
                return _WINDOWS_SERVICES
            if plan['spec'].get('coldCapture') is not None:
                return _COLD_CAPTURE
            require(selected['driver'] in {DRIVER, DATABASE_DRIVER, STAGING_DRIVER, CUTOVER_DRIVER,
                                          APPLICATION_RECOVERY_DRIVER},
                    'This approved driver is not installed')
            artifact = self.selections.load_verified(selected['artifactDigest'])
            require((artifact['workloadId'], artifact['workloadRevision'], artifact['source'],
                     artifact['destination'], artifact['qualificationDigest'], artifact['guestProfile']) ==
                    (plan['spec']['workloadId'], plan['spec']['workloadRevision'], plan['spec']['source'],
                     plan['spec']['destination'], plan['spec']['route']['qualificationDigest'],
                     plan['spec']['route']['guestProfile']), 'The selected graph differs from the approved plan')
            if selected['driver'] == APPLICATION_RECOVERY_DRIVER:
                from .application_recovery_job import ApplicationRecoveryInput
                require(self.migration_selections is not None
                        and artifact.get('applicationRecoverySelectionDigest') is not None,
                        'A protected original application recovery selection is required')
                recovery = self.migration_selections.recovery(artifact['applicationRecoverySelectionDigest'])
                lifecycle = self.migration_selections.lifecycle(artifact['applicationLifecycleSelectionDigest'])
                recovery.require_forward_plan(plan, artifact, lifecycle)
                require(recovery.to_dict()['originalAdmitted']['job_id'] != admitted.job_id,
                        'Recovery cannot reuse its original application admission')
                return ApplicationRecoveryInput(admitted, selected['artifactDigest'], lifecycle.sha256,
                    recovery.sha256, recovery.to_dict()['originalAdmitted']['job_id'], recovery.members)
            delivery = load_private(self.delivery_store / (artifact['deliveryPlanDigest'] + '.json'))
            validate_delivery(delivery)
            require(_digest(delivery) == artifact['deliveryPlanDigest']
                    and delivery['source_commit'] == artifact['sourceCommit']
                    and delivery['scope'] == artifact['executionScope']
                    and {s['id'] for s in delivery['steps']} == set(artifact['stageBindings']),
                    'The protected delivery graph changed')
            for step in delivery['steps']:
                require(artifact['stageBindings'][step['id']]['kind'] == step['kind'],
                        'The selected stage owner changed')
            if selected['driver'] == STAGING_DRIVER:
                require(plan['spec'].get('applicationStaging') == {'format': 'hosting-application-staging-plan/1'}
                        and not {'applicationLifecycleSelectionDigest', 'applicationStagingSelectionDigest',
                                 'applicationDatabaseSelectionDigest'}.intersection(artifact)
                        and all(step['kind'] not in {'dataset_restore', 'dataset_acceptance',
                            'restic', 'vsphere_power', 'dns_cutover', 'dns_propagation'}
                            for step in delivery['steps']),
                        'Initial target staging cannot fence, copy or activate application data')
                return ApplicationStagingInput(admitted, selected['artifactDigest'],
                    tuple(step['id'] for step in delivery['steps']), tuple(plan['spec']['selectedMachineIds']))
            initial_steps = tuple(step['id'] for step in delivery['steps'])
            lifecycle_digest = artifact.get('applicationLifecycleSelectionDigest')
            if lifecycle_digest is not None:
                require(self.migration_selections is not None,
                        'The selected lifecycle cannot start without its exact protected descriptor')
                selected_lifecycle = self.migration_selections.lifecycle(lifecycle_digest)
                lifecycle = selected_lifecycle.to_dict()
                require((lifecycle['source_scope'], lifecycle['destination_scope'], lifecycle['guest_profile']) ==
                        (artifact['source'], artifact['destination'], artifact['guestProfile'])
                        and {row['machine_id'] for row in lifecycle['members']} ==
                            set(plan['spec']['selectedMachineIds']),
                        'The deferred lifecycle differs from the approved complete application')
                initial_steps = initial_provisioning_steps(delivery, selected_lifecycle)
            staging_digest = artifact.get('applicationStagingSelectionDigest')
            if selected['driver'] in {CUTOVER_DRIVER, DATABASE_DRIVER}:
                require(staging_digest is not None and lifecycle_digest is not None
                        and self.migration_selections is not None,
                        'Current cutover requires a protected actual target handover and lifecycle')
                staged = self.migration_selections.staged(staging_digest).to_dict()
                require((staged['stagedWorkloadRevision'], staged['destinationScope'], staged['targetSnapshotId']) ==
                        (plan['spec']['workloadRevision'], plan['spec']['destination'], plan['spec']['destinationSnapshotId'])
                        and plan['spec'].get('applicationStagedCutover') == {
                            'format': 'hosting-application-staged-cutover-plan/1',
                            'originalJobId': staged['originalAdmitted']['job_id'],
                            'originalPlanDigest': staged['originalAdmitted']['plan_digest'],
                            'originalArtifactDigest': staged['originalArtifactDigest'],
                            'stagedHandoverDigest': staging_digest}
                        and not any(step['kind'] in CREATION_STAGES for step in delivery['steps']),
                        'The current cutover changed its actual targets or attempted duplicate creation')
                dataset_ids = tuple(plan['spec']['selectedDatasetIds'])
                db_digest, db_member = artifact.get('applicationDatabaseSelectionDigest'), None
                if selected['driver'] == DATABASE_DRIVER:
                    require(self.database_selections is not None and db_digest is not None,
                            'The selected database method owner is unavailable')
                    database = self.database_selections.load(db_digest).to_dict()
                    require(database['datasetId'] in dataset_ids
                            and database['memberId'] in plan['spec']['selectedMachineIds']
                            and (database['source_scope'], database['target_scope']) ==
                                (plan['spec']['source'], plan['spec']['destination'])
                            and any((row['datasetId'], row['targetRef'], row['consistencyGroupId']) ==
                                (database['datasetId'], database['targetRef'], database['consistencyGroupId'])
                                for row in plan['spec']['datasetMappings']),
                            'The SQL descriptor differs from the exact approved application mapping')
                    dataset_ids = tuple(value for value in dataset_ids if value != database['datasetId'])
                    db_member = database['memberId']
                return ApplicationCutoverInput(admitted, selected['artifactDigest'], initial_steps,
                    dataset_ids, tuple(plan['spec']['selectedMachineIds']), lifecycle_digest, staging_digest,
                    db_digest, db_member)
            return ApplicationJobInput(admitted, selected['artifactDigest'],
                initial_steps,
                tuple(plan['spec']['selectedDatasetIds']), tuple(plan['spec']['selectedMachineIds']),
                lifecycle_digest)
