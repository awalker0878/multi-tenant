"""Select one newly approved recovery purpose without an application graph."""
from dataclasses import dataclass

from provisioner.allocations.transactions import ResourceBundle
from provisioner.controlplane.authority import postgres as authority_postgres
from provisioner.controlplane.jobs.repository import (_JOB_SELECT,_digest,_ensure_plan,
    _ensure_workload,_job,_json,_payload_from_job,_tenant)
from provisioner.controlplane.persistence import NativeBinding,TenantContext
from provisioner.controlplane.reconciliation.resource_recovery import validate_recovery_selection
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.execution_selection import FileExecutionSelectionStore
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import require
from .resource_recovery_job import ResourceRecoveryInput


def cleanup_binding_key(binding):
    require(isinstance(binding,NativeBinding),'An original independently observed native binding is required')
    # Native VM deletion detaches its selected port and volumes first. This
    # order is compiled here, never supplied as an executable queued command.
    order={'vm':'0','nic':'1','volume':'2'}.get(binding.resource_kind,'9')
    return 'cleanup-'+order+'-'+c.digest(list(binding.key()))[:40]


@dataclass(frozen=True)
class SelectedResourceRecovery:
    input: ResourceRecoveryInput
    plan: dict
    artifact: dict
    bundle: ResourceBundle
    original_operations: tuple[dict,...]
    cleanup_bindings: tuple[NativeBinding,...]


class PostgresResourceRecoverySelector:
    """Same B09 admission/queue and protected resource store, fixed recovery purpose.

    Selection may occur before the outbox start is acknowledged. Effect
    activities separately require the acknowledged running recovery admission.
    """
    def __init__(self,connect,selections,bundles):
        require(callable(connect) and isinstance(selections,FileExecutionSelectionStore) and callable(bundles),
                'Existing scoped job and concrete protected resource custody required')
        self.connect,self.selections,self.bundles=connect,selections,bundles

    def __call__(self,admitted):
        return self.load(admitted).input

    @staticmethod
    def _admitted(job):
        return AdmittedInput(job.job_id,job.organization_id,job.tenant_id,job.plan_id,
            job.plan_revision,job.plan_digest,job.revocation_epoch,_digest(_payload_from_job(job)))

    def load(self,admitted):
        require(isinstance(admitted,AdmittedInput),'The newly admitted recovery input is required')
        context=TenantContext(admitted.organization_id,admitted.tenant_id)
        with self.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            cursor.execute('SELECT hosting_controlplane.lock_job_scope(%s,%s,%s)',
                (context.organization_id,context.tenant_id,admitted.job_id))
            require(cursor.fetchone()==(True,),'The newly admitted recovery job is unavailable')
            cursor.execute(f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s',
                (context.organization_id,context.tenant_id,admitted.job_id))
            row=cursor.fetchone(); require(row is not None,'The recovery job is not visible in this tenant')
            job=_job(row)
            require(self._admitted(job)==admitted and job.status in {'QUEUED','START_REQUESTED','STARTED','RUNNING'},
                    'The newly admitted recovery payload or running authority changed')
            cursor.execute('SELECT clock_timestamp()'); at=cursor.fetchone()[0]
            authority_postgres.revalidate_start(cursor,job,at)
            cursor.execute('SELECT revision,record_digest,record_json FROM hosting_controlplane.enterprise_records '
                "WHERE organization_id=%s AND tenant_id=%s AND record_kind='MigrationPlan' AND record_id=%s FOR SHARE",
                (context.organization_id,context.tenant_id,job.plan_id))
            plan=_ensure_plan(cursor.fetchone(),context,job); _ensure_workload(cursor,context,plan)
            recovery=validate_recovery_selection(plan['spec'].get('resourceRecovery',{}))
            execution=plan['spec'].get('execution',{})
            require(execution.get('format')=='hosting-execution-selection/1',
                    'The new recovery plan lacks its exact protected execution selection')
            artifact=self.selections.load_verified(execution.get('artifactDigest'))
            require(artifact.get('resourceRecoverySelectionDigest')==c.digest(recovery)
                    and artifact.get('resourceBundleDigest')==recovery['resourceBundleDigest']
                    and _digest(artifact)==execution['artifactDigest']
                    and (artifact['workloadId'],artifact['workloadRevision'],artifact['source'],artifact['destination'])==
                        (plan['spec']['workloadId'],plan['spec']['workloadRevision'],plan['spec']['source'],plan['spec']['destination']),
                    'The protected recovery artifact changed its original resource purpose or exact approved scope')
            cursor.execute(f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s FOR SHARE',
                (context.organization_id,context.tenant_id,recovery['originalJobId']))
            row=cursor.fetchone(); require(row is not None,'Original recovery admission is unavailable')
            original_job=_job(row); original=self._admitted(original_job)
            require(original.job_id!=admitted.job_id and original.plan_digest==recovery['originalPlanDigest']
                    and (original_job.source,original_job.destination)==(job.source,job.destination),
                    'The original recovery admission differs from its new approved native scopes')
            original_artifact=self.selections.load_verified(recovery['originalSelectionDigest'])
            bundle=self.bundles(original,original_artifact)
            require(isinstance(bundle,ResourceBundle) and bundle.admitted==original
                    and bundle.digest==recovery['resourceBundleDigest']
                    and bundle.selection_digest==recovery['originalSelectionDigest']
                    and (bundle.workload_id,bundle.workload_revision)==
                        (plan['spec']['workloadId'],plan['spec']['workloadRevision']),
                    'The original charged bundle differs from retained approved recovery custody')
            cursor.execute('SELECT operation_id,job_id,worker_id,operation_kind,state,outcome,request_digest,'
                'platform_family,endpoint_id,native_scope_id,resource_kind,native_id '
                'FROM hosting_controlplane.native_operation_intents WHERE organization_id=%s AND tenant_id=%s '
                'AND (job_id=%s OR job_id IN (SELECT recovery_job_id FROM hosting_controlplane.resource_recovery_bindings '
                'WHERE organization_id=%s AND tenant_id=%s AND original_job_id=%s AND recovery_job_id<>%s '
                'AND original_plan_digest=%s AND original_selection_digest=%s AND resource_bundle_digest=%s '
                'AND reservation_digest=%s)) ORDER BY operation_id FOR SHARE',
                (context.organization_id,context.tenant_id,original.job_id,context.organization_id,context.tenant_id,
                 original.job_id,admitted.job_id,original.plan_digest,bundle.selection_digest,bundle.digest,
                 recovery['reservationDigest']))
            rows=cursor.fetchall()
            require([row[0] for row in rows]==recovery['originalOperationIds'],
                    'The new recovery must preserve every original and earlier cleanup intent')
            operations=tuple(dict(zip(('operation_id','job_id','worker_id','operation_kind','state','outcome',
                'request_digest','platform_family','endpoint_id','native_scope_id','resource_kind','native_id'),row))
                for row in rows)
            bindings={}
            for operation in operations:
                scope_key=(operation['platform_family'],operation['endpoint_id'],operation['native_scope_id'])
                require(scope_key in {(pool.scope.platform_family,pool.scope.endpoint_id,pool.scope.native_scope_id)
                        for pool in bundle.pools},'An original native intent escapes the approved recovery scope')
                if operation['operation_kind']=='VM_CREATE':
                    cursor.execute('SELECT created_native_bindings FROM hosting_controlplane.native_operation_observations '
                        'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s '
                        "AND outcome='EFFECT_PRESENT' AND native_quiesced ORDER BY recorded_at DESC LIMIT 1",
                        (context.organization_id,context.tenant_id,operation['operation_id']))
                    observed=cursor.fetchone()
                    if observed is not None and observed[0] is not None:
                        for record in _json(observed[0]):
                            binding=NativeBinding(**record)
                            require(binding.key()[:3]==scope_key,'Observed creation children escape their original native scope')
                            bindings[binding.key()]=binding
                elif operation['native_id'] is not None and operation['operation_kind']=='NATIVE_CLEANUP':
                    binding=NativeBinding(operation['platform_family'],operation['endpoint_id'],
                        operation['native_scope_id'],operation['resource_kind'],operation['native_id'])
                    bindings[binding.key()]=binding
            actual=tuple(bindings[key] for key in sorted(bindings))
            input=ResourceRecoveryInput(admitted,execution['artifactDigest'],c.digest(recovery),original.job_id,
                bundle.selection_digest,
                bundle.digest,tuple(sorted({row['worker_id'] for row in operations})),
                tuple(sorted(cleanup_binding_key(binding) for binding in actual)),tuple(recovery['actions']))
            return SelectedResourceRecovery(input,plan,artifact,bundle,operations,actual)

    def require_input(self,input):
        require(isinstance(input,ResourceRecoveryInput),'Typed canonical recovery references required')
        selected=self.load(input.admitted)
        require(selected.input==input,'Queued recovery references differ from the current exact approved original purpose')
        return selected
