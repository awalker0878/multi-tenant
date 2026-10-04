"""Current scoped B09 selection for the fixed cold capture/import purpose."""
from dataclasses import dataclass

from provisioner.controlplane.authority import postgres as authority_postgres
from provisioner.controlplane.jobs.repository import (_JOB_SELECT,_digest,_ensure_plan,
    _ensure_workload,_job,_payload_from_job,_tenant)
from provisioner.controlplane.persistence import TenantContext
from provisioner.execution.run_files import require
from provisioner.migration.cold_selection import ColdVmSelection,FileColdSelectionStore,DRIVER
from .admitted_job import AdmittedInput
from .cold_capture_job import ColdCaptureInput
from .execution_selection import FileExecutionSelectionStore


@dataclass(frozen=True)
class SelectedColdPurpose:
    input: ColdCaptureInput
    plan: dict
    artifact: dict
    cold: ColdVmSelection


def cold_input(admitted,selection_digest,cold):
    require(type(admitted) is AdmittedInput and type(cold) is ColdVmSelection,
            'Original admission and complete protected native snapshot selection required')
    body=cold.to_dict()
    return ColdCaptureInput(admitted,selection_digest,cold.sha256,body['export']['step_id'],
        tuple(disk['phases'][phase]['step_id'] for disk in body['disks'] for phase in ('CREATE','UPLOAD')))


class PostgresColdCaptureSelector:
    """This read cannot mint a grant, native image identity or execution owner."""
    def __init__(self,connect,selections,cold_selections):
        require(callable(connect) and isinstance(selections,FileExecutionSelectionStore)
                and isinstance(cold_selections,FileColdSelectionStore),
                'Current PostgreSQL and actual protected cold artifact/selection stores required')
        self.connect,self.selections,self.cold_selections=connect,selections,cold_selections

    def __call__(self,admitted): return self.selected(admitted).input

    def selected(self,admitted):
        require(type(admitted) is AdmittedInput,'Exact admitted cold-purpose start required')
        context=TenantContext(admitted.organization_id,admitted.tenant_id)
        with self.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            cursor.execute('SELECT hosting_controlplane.lock_job_scope(%s,%s,%s)',
                (context.organization_id,context.tenant_id,admitted.job_id))
            require(cursor.fetchone()==(True,),'The original cold job is unavailable')
            cursor.execute(f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s',
                (context.organization_id,context.tenant_id,admitted.job_id))
            stored=cursor.fetchone(); require(stored is not None,'This tenant cannot see the original cold job')
            job=_job(stored)
            require((job.job_id,job.plan_id,job.plan_revision,job.plan_digest,job.revocation_epoch)==
                (admitted.job_id,admitted.plan_id,admitted.plan_revision,admitted.plan_digest,admitted.revocation_epoch)
                and _digest(_payload_from_job(job))==admitted.payload_digest,
                'The exact original cold job or committed start payload changed')
            cursor.execute('SELECT clock_timestamp()')
            authority_postgres.revalidate_start(cursor,job,cursor.fetchone()[0])
            cursor.execute('SELECT revision,record_digest,record_json FROM '
                'hosting_controlplane.enterprise_records WHERE organization_id=%s AND tenant_id=%s '
                "AND record_kind='MigrationPlan' AND record_id=%s FOR SHARE",
                (context.organization_id,context.tenant_id,job.plan_id))
            plan=_ensure_plan(cursor.fetchone(),context,job); _ensure_workload(cursor,context,plan)
            execution=plan['spec'].get('execution')
            require(type(execution) is dict and execution['driver']==DRIVER,
                    'The canonical job does not select the fixed partial cold purpose')
            artifact=self.selections.load_verified(execution['artifactDigest'])
            cold=self.cold_selections.load_verified(artifact['coldCaptureSelectionDigest'])
            cold.require_plan(plan,artifact)
            return SelectedColdPurpose(cold_input(admitted,execution['artifactDigest'],cold),plan,artifact,cold)

    def require_input(self,input):
        require(type(input) is ColdCaptureInput,'Fixed exact cold workflow references required')
        selected=self.selected(input.admitted)
        require(selected.input==input,'The queued cold graph differs from its current complete protected selection')
        return selected
