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
from .execution_selection import DRIVER, FileExecutionSelectionStore


class PostgresApplicationSelector:
    """No native action or qualification is granted by this bounded read."""
    def __init__(self, connect, selections: FileExecutionSelectionStore, delivery_store: Path):
        require(callable(connect) and isinstance(selections, FileExecutionSelectionStore),
                'Actual scoped plan and protected selection owners are required')
        self.connect, self.selections = connect, selections
        self.delivery_store = private_path(delivery_store, directory=True)

    def __call__(self, admitted) -> ApplicationJobInput | None:
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
            require(selected['driver'] == DRIVER, 'This approved driver is not installed')
            artifact = self.selections.load_verified(selected['artifactDigest'])
            require((artifact['workloadId'], artifact['workloadRevision'], artifact['source'],
                     artifact['destination'], artifact['qualificationDigest'], artifact['guestProfile']) ==
                    (plan['spec']['workloadId'], plan['spec']['workloadRevision'], plan['spec']['source'],
                     plan['spec']['destination'], plan['spec']['route']['qualificationDigest'],
                     plan['spec']['route']['guestProfile']), 'The selected graph differs from the approved plan')
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
            return ApplicationJobInput(admitted, selected['artifactDigest'],
                tuple(step['id'] for step in delivery['steps']),
                tuple(plan['spec']['selectedDatasetIds']), tuple(plan['spec']['selectedMachineIds']))
