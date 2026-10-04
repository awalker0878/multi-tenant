"""Fixed existing-target Windows services, separate from workload mobility.

These content-addressed references are inputs, never worker identity, native
credential or permission. Selection uses the existing B09 plan and execution
store; current effects still require the enrolled command authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from provisioner.controlplane.authority import postgres as authority_postgres
from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.jobs.repository import (_JOB_SELECT, _digest, _ensure_plan,
    _ensure_workload, _job, _payload_from_job, _tenant)
from provisioner.controlplane.persistence import NativeBinding, TenantContext
from provisioner.execution.delivery_run import validate as validate_delivery
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import encoded, load_private, private_path, require
from .admitted_job import AdmittedInput
from .approval_gate import _valid_digest, _valid_id

FORMAT = 'hosting-existing-windows-services-artifact/1'
DRIVER = 'windows-server-2022-existing-services/1'
PLAN_FORMAT = 'hosting-existing-windows-services-plan/1'
SELECTION_FORMAT = 'hosting-existing-windows-services-selection/1'
METHOD = 'EXISTING_GUEST_SERVICES'
_FIELDS = frozenset({'format','driver','sourceCommit','workloadId','workloadRevision',
    'source','destination','executionScope','sourceTuple','destinationTuple','guestProfile',
    'qualificationDigest','operationsAcceptanceDigest','deliveryPlanDigest','stageBindings','windowsServices'})


@dataclass(frozen=True)
class WindowsOriginalServiceIntent:
    """Exact historical references; actual root/registry reads prove custody."""
    canonical: bytes

    def __post_init__(self):
        require(type(self.canonical) is bytes and len(self.canonical)<=8192,
                'Bounded immutable original Windows intent references required')
        body=strict_loads(self.canonical)
        require(type(body) is dict and encoded(body)==self.canonical and body.keys()=={
            'originalAdmitted','artifactDigest','operationId','stepId','requestDigest',
            'leaseKey','workerSubject','ownerEpoch','windowsSelectionDigest','nativeBinding'},
            'Exact original Windows admission, selected input and native intent references required')
        admitted=AdmittedInput(**body['originalAdmitted'])
        binding=NativeBinding.from_record(body['nativeBinding'])
        require(binding.resource_kind=='vm' and all(_valid_id(body[key]) for key in
                ('operationId','stepId','leaseKey','workerSubject'))
                and all(_valid_digest(body[key]) for key in
                ('artifactDigest','requestDigest','windowsSelectionDigest'))
                and type(body['ownerEpoch']) is int and body['ownerEpoch']>0
                and admitted.job_id,
                'The original Windows VM, operation and source custody must be exact')

    @classmethod
    def from_record(cls,body): return cls(encoded(body))

    def to_dict(self): return strict_loads(self.canonical)

    @property
    def admitted(self): return AdmittedInput(**self.to_dict()['originalAdmitted'])


@dataclass(frozen=True)
class WindowsServiceSelection:
    canonical: bytes

    def __post_init__(self):
        require(type(self.canonical) is bytes and len(self.canonical)<=16384,
                'A bounded immutable existing Windows service purpose is required')
        body=strict_loads(self.canonical)
        require(type(body) is dict and encoded(body)==self.canonical and body.keys()=={
            'format','action','machineId','nativeBinding','writerSelectionDigest','readerSelectionDigest',
            'originalSelectionDigest','caDigest','write','read','original'},
            'One exact selected Windows service purpose is required')
        require(body['format']==SELECTION_FORMAT and body['action'] in {
            'CONFIGURE_AND_OBSERVE','OBSERVE_ORIGINAL','REMEDIATE_AND_OBSERVE'}
            and _valid_id(body['machineId']) and all(_valid_digest(body[key]) for key in
                ('writerSelectionDigest','readerSelectionDigest','originalSelectionDigest','caDigest')),
            'Fixed Windows service action and exact descriptor/trust hashes required')
        binding=NativeBinding.from_record(body['nativeBinding'])
        require(binding.resource_kind=='vm','Only one already observed Windows VM may be selected')
        for name in ('write','read'):
            row=body[name]
            if name=='write' and body['action']=='OBSERVE_ORIGINAL':
                require(row is None,'An observation purpose cannot contain a service mutation'); continue
            require(type(row) is dict and row.keys()=={'stepId','operationId','kind'}
                    and _valid_id(row['stepId']) and _valid_id(row['operationId'])
                    and row['kind']==('windows_guest_observe' if name=='read' else
                        'windows_guest_apply' if body['action']=='CONFIGURE_AND_OBSERVE' else
                        'windows_guest_remediate'), 'Exact fixed Windows service stage and original operation required')
        if body['write'] is not None:
            require(body['write']['stepId']!=body['read']['stepId']
                    and body['write']['operationId']!=body['read']['operationId'],
                    'Native writer and independent reader need distinct fixed stages and operations')
        if body['action']=='CONFIGURE_AND_OBSERVE':
            require(body['original'] is None and body['originalSelectionDigest']==body['writerSelectionDigest'],
                    'New configuration cannot borrow an old native service intent')
        else:
            original=WindowsOriginalServiceIntent.from_record(body['original'])
            record=original.to_dict()
            require(record['nativeBinding']==body['nativeBinding']
                    and record['windowsSelectionDigest']==body['originalSelectionDigest']
                    and body['read']['operationId']!=record['operationId'],
                    'Selected service follow-up changed the original native VM, input or read purpose')
            if body['action']=='OBSERVE_ORIGINAL':
                require(body['writerSelectionDigest']==body['originalSelectionDigest'],
                        'Original service observation cannot select a new writer descriptor')
            else:
                require(body['write']['operationId']!=record['operationId'],
                        'A new remediation cannot retry its old native intent')

    @classmethod
    def from_record(cls,body): return cls(encoded(body))

    def to_dict(self): return strict_loads(self.canonical)

    @property
    def sha256(self): return _digest(self.to_dict())

    @property
    def original(self):
        body=self.to_dict()['original']
        return None if body is None else WindowsOriginalServiceIntent.from_record(body)

    def expected_bindings(self):
        body=self.to_dict(); result={}; writer=body['write']
        if writer is not None:
            files={'windows_selection':body['writerSelectionDigest'],'winrm_ca':body['caDigest']}
            parameters={}
            if writer['kind']=='windows_guest_remediate':
                files['original_windows_selection']=body['originalSelectionDigest']
                parameters={'original_operation_id':body['original']['operationId']}
            result[writer['stepId']]={'kind':writer['kind'],'parametersDigest':_digest(parameters),'inputDigests':files}
        original_id=body['original']['operationId'] if writer is None else writer['operationId']
        result[body['read']['stepId']]={'kind':'windows_guest_observe',
            'parametersDigest':_digest({'original_operation_id':original_id}),
            'inputDigests':{'windows_selection':body['readerSelectionDigest'],
                           'original_windows_selection':body['writerSelectionDigest'],'winrm_ca':body['caDigest']}}
        return result

    def require_guest(self,descriptor,*,reader=False):
        from provisioner.execution.windows_guest import WindowsGuestSelection
        body=self.to_dict()
        require(type(descriptor) is WindowsGuestSelection and descriptor.sha256==
                body['readerSelectionDigest' if reader else 'writerSelectionDigest']
                and descriptor.to_dict()['native_binding']==body['nativeBinding']
                and descriptor.to_dict()['machine_id']==body['machineId'],
                'The physical Windows descriptor must bind the exact independently observed selected VM and machine')

    def require_delivery(self,delivery):
        validate_delivery(delivery); body=self.to_dict(); writer=body['write']; reader=body['read']
        expected=[] if writer is None else [{'id':writer['stepId'],'kind':writer['kind'],'needs':[]}]
        expected.append({'id':reader['stepId'],'kind':reader['kind'],
                         'needs':[] if writer is None else [writer['stepId']]})
        require(delivery['steps']==expected,
                'Existing Windows services cannot create, transfer, cut over or execute another owner')
        return tuple(row['id'] for row in expected)

    def require_plan(self,plan,artifact):
        spec=plan['spec']; body=self.to_dict()
        require(spec.get('windowsServices')=={'format':PLAN_FORMAT,'selectionDigest':self.sha256}
                and spec.get('execution')=={'format':'hosting-execution-selection/1',
                    'driver':DRIVER,'artifactDigest':_digest(artifact)}
                and spec['route']['method']==METHOD and spec['route']['guestProfile']=='windows-server-2022'
                and spec['source']==spec['destination']==artifact['source']==artifact['destination']
                and spec['sourceSnapshotId']==spec['destinationSnapshotId']
                and spec['selectedMachineIds']==[body['machineId']]
                and not spec['selectedDatasetIds'] and not spec['datasetMappings']
                and len(spec['machineMappings'])==1
                and spec['machineMappings'][0]['machineId']==spec['machineMappings'][0]['targetMachineId']==body['machineId']
                and spec['machineMappings'][0]['sourceBinding']==body['nativeBinding']
                and not {'applicationStaging','applicationStagedCutover','applicationRecovery',
                         'resourceRecovery','coldCapture'}.intersection(spec),
                'The approved existing Windows service purpose changed its actual target or selected a mobility operation')
        return body


def validate_artifact(value):
    require(type(value) is dict and value.keys()==_FIELDS and value['format']==FORMAT and value['driver']==DRIVER,
            'One exact existing-target Windows service execution artifact is required')
    require(type(value['sourceCommit']) is str and len(value['sourceCommit'])==40
            and all(char in '0123456789abcdef' for char in value['sourceCommit'])
            and _valid_id(value['workloadId']) and type(value['workloadRevision']) is int and value['workloadRevision']>0,
            'Current Windows service source and canonical workload revision required')
    source=PlanScope.from_record(value['source']); destination=PlanScope.from_record(value['destination'])
    require(source==destination and value['guestProfile']=='windows-server-2022'
            and type(value['sourceTuple']) is dict and value['sourceTuple']==value['destinationTuple'],
            'Existing Windows service operation cannot claim another location, guest or directed tuple')
    purpose=WindowsServiceSelection.from_record(value['windowsServices'])
    binding=NativeBinding.from_record(purpose.to_dict()['nativeBinding'])
    require((binding.platform_family,binding.endpoint_id,binding.native_scope_id)==
                (source.platform_family,source.endpoint_id,source.native_scope_id)
            and value['stageBindings']==purpose.expected_bindings(),
            'Fixed Windows stages must bind the exact existing VM, descriptor bytes and purpose')
    scope=value['executionScope']
    require(type(scope) is dict and scope.keys()=={'environment_key','site_key','platform','tenant_key','wsd_key'}
            and all(_valid_id(item) for item in scope.values())
            and (scope['platform'],scope['site_key'],scope['tenant_key'],scope['wsd_key'])==
                (source.platform_family,source.site_id,source.tenant_id,source.security_domain_id)
            and all(_valid_digest(value[key]) for key in
                ('qualificationDigest','operationsAcceptanceDigest','deliveryPlanDigest')),
            'Current scope, service commissioning, operations and fixed delivery evidence required')
    if purpose.original is not None:
        previous=purpose.original.admitted
        require((previous.organization_id,previous.tenant_id)==(source.organization_id,source.tenant_id),
                'Retained original Windows intent is outside the current tenant')
    return value


class PostgresWindowsServiceSelector:
    """Original B09 admission and protected fixed graph; no native permission."""
    def __init__(self,connect,selections,delivery_store:Path):
        from .execution_selection import FileExecutionSelectionStore
        require(callable(connect) and isinstance(selections,FileExecutionSelectionStore),
                'Actual scoped job and existing protected execution store required')
        self.connect,self.selections=connect,selections
        self.delivery_store=private_path(delivery_store,directory=True)

    def __call__(self,admitted):
        from .windows_service_job import WindowsServiceInput
        require(type(admitted) is AdmittedInput,'An exact admitted existing Windows service request is required')
        context=TenantContext(admitted.organization_id,admitted.tenant_id)
        with self.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            cursor.execute('SELECT hosting_controlplane.lock_job_scope(%s,%s,%s)',
                (context.organization_id,context.tenant_id,admitted.job_id))
            require(cursor.fetchone()==(True,),'The original Windows service job is unavailable')
            cursor.execute(f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s',
                (context.organization_id,context.tenant_id,admitted.job_id))
            row=cursor.fetchone(); require(row is not None,'The Windows service job is not visible in this tenant')
            job=_job(row)
            require((job.job_id,job.plan_id,job.plan_revision,job.plan_digest,job.revocation_epoch)==
                (admitted.job_id,admitted.plan_id,admitted.plan_revision,admitted.plan_digest,admitted.revocation_epoch)
                and _digest(_payload_from_job(job))==admitted.payload_digest
                and job.status in {'QUEUED','START_REQUESTED','STARTED','RUNNING'},
                'The exact Windows service admission or current start payload changed')
            cursor.execute('SELECT clock_timestamp()'); authority_postgres.revalidate_start(cursor,job,cursor.fetchone()[0])
            cursor.execute('SELECT revision,record_digest,record_json FROM hosting_controlplane.enterprise_records '
                "WHERE organization_id=%s AND tenant_id=%s AND record_kind='MigrationPlan' AND record_id=%s FOR SHARE",
                (context.organization_id,context.tenant_id,job.plan_id))
            plan=_ensure_plan(cursor.fetchone(),context,job); _ensure_workload(cursor,context,plan)
            reference=plan['spec'].get('execution',{})
            artifact=validate_artifact(self.selections.load_verified(reference.get('artifactDigest')))
            purpose=WindowsServiceSelection.from_record(artifact['windowsServices']); body=purpose.require_plan(plan,artifact)
            require((artifact['workloadId'],artifact['workloadRevision'],artifact['qualificationDigest'])==
                (plan['spec']['workloadId'],plan['spec']['workloadRevision'],plan['spec']['route']['qualificationDigest']),
                'The selected Windows service artifact changed its approved workload or commissioning evidence')
            delivery=load_private(self.delivery_store/(artifact['deliveryPlanDigest']+'.json'))
            steps=purpose.require_delivery(delivery)
            require(_digest(delivery)==artifact['deliveryPlanDigest']
                    and delivery['source_commit']==artifact['sourceCommit'] and delivery['scope']==artifact['executionScope'],
                    'The protected Windows service graph or source changed')
            return WindowsServiceInput(admitted,reference['artifactDigest'],purpose.sha256,body['action'],steps,body['machineId'])
