"""Fixed installed PostgreSQL17 application phases and original-result custody."""
from dataclasses import dataclass,field
import os
from pathlib import Path
import threading
from types import MappingProxyType
from typing import Mapping

from temporalio import activity

from provisioner.controlplane.authority import AuthorityDenied,PlanScope
from provisioner.controlplane.persistence import canonical_record_digest
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
from provisioner.controlplane.reconciliation.registry import RecoveryHeld
from provisioner.execution import execution_journal
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import encoded,private_path,read_private,require,sync_directory,write_new
from .activities import MigrationActivityRequest,MigrationActivityResult
from .lifecycle_evidence import ApplicationEvidenceReader
from .postgresql_authority import (DatabaseWorkerRuntime,DatabaseOperationContext,DatabaseCommandAuthority,
                                  DatabaseCredentialRetirer,open_database)
from .postgresql_sync import PostgresqlSyncSelection,PostgresqlSyncRunner
from .postgresql_readback import PostgresqlReadbackOwner


class DatabaseHeld(RuntimeError):
    def __init__(self,code):super().__init__(code);self.code=code


class FilePostgresqlSelectionStore:
    def __init__(self,directory):self.directory=private_path(directory,directory=True)
    def load(self,selected_digest):
        import re
        require(isinstance(selected_digest,str) and re.fullmatch('[0-9a-f]{64}',selected_digest),
                'The original protected SQL descriptor digest is required')
        selected=private_path(self.directory/(selected_digest+'.json'))
        with os.fdopen(os.open(selected,os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:raw=stream.read(65537)
        descriptor=PostgresqlSyncSelection(raw)
        require(descriptor.sha256==selected_digest,'The original protected SQL selection changed')
        return descriptor


@dataclass(frozen=True)
class DatabaseRuntimeBindings:
    workers:Mapping[tuple[str,str,str],DatabaseWorkerRuntime]
    evidence_readers:Mapping[str,ApplicationEvidenceReader]
    native_readbacks:Mapping[str,PostgresqlReadbackOwner]=field(default_factory=dict)
    def __post_init__(self):
        import re
        def valid(value):return isinstance(value,str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9._:-]{0,127}',value)
        require(isinstance(self.workers,Mapping) and isinstance(self.evidence_readers,Mapping) and isinstance(self.native_readbacks,Mapping)
                and all(isinstance(key,tuple) and len(key)==3 and valid(key[0]) and valid(key[1])
                    and key[2] in {'source','target','fence'} and isinstance(value,DatabaseWorkerRuntime)
                    for key,value in self.workers.items())
                and all(valid(key) and isinstance(value,ApplicationEvidenceReader)
                    for key,value in self.evidence_readers.items())
                and all(valid(key) and type(value) is PostgresqlReadbackOwner for key,value in self.native_readbacks.items()),
                'Actual enrolled SQL workers and original evidence readers required')
        object.__setattr__(self,'workers',MappingProxyType(dict(self.workers)))
        object.__setattr__(self,'evidence_readers',MappingProxyType(dict(self.evidence_readers)))
        object.__setattr__(self,'native_readbacks',MappingProxyType(dict(self.native_readbacks)))


class PostgresqlSyncActivities:
    def __init__(self,*,authority,selections,runtimes,journals_directory,outputs_directory,source_root):
        require(isinstance(authority,PostgresExecutionAuthority) and isinstance(selections,FilePostgresqlSelectionStore)
                and isinstance(runtimes,DatabaseRuntimeBindings),'The actual installed selected SQL owners are required')
        self.authority=authority;self.selections=selections;self.runtimes=runtimes
        self.journals=private_path(journals_directory,directory=True)
        self.outputs=private_path(outputs_directory,directory=True);self.source_root=Path(source_root)
        self._contexts={};self._lock=threading.RLock()

    def _selected(self,request,kind='RESTORE_DATA'):
        require(isinstance(request,MigrationActivityRequest) and request.member_id,'Exact admitted SQL member required')
        plan,artifact=self.authority.require_observation(request.admitted,request.selection_digest,kind)
        require(artifact.get('driver')=='openstack-linux-application-database/1',
                'A file rebuild cannot silently select database CDC')
        descriptor=self.selections.load(artifact['applicationDatabaseSelectionDigest'])
        require(descriptor.to_dict()['memberId']==request.member_id,'The original SQL member changed')
        body=descriptor.to_dict()
        require(body['datasetId'] in plan['spec']['selectedDatasetIds']
                and dict(datasetId=body['datasetId'],targetRef=body['targetRef'],consistencyGroupId=body['consistencyGroupId'])
                    in plan['spec']['datasetMappings'],'The SQL dataset differs from canonical selected mapping')
        from provisioner.controlplane.jobs.repository import _tenant,_json
        from provisioner.controlplane.persistence import TenantContext
        with self.authority.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,TenantContext(request.admitted.organization_id,request.admitted.tenant_id))
            cursor.execute('SELECT record_json FROM hosting_controlplane.enterprise_record_history '
                "WHERE organization_id=%s AND tenant_id=%s AND record_kind='Workload' AND record_id=%s AND revision=%s",
                (request.admitted.organization_id,request.admitted.tenant_id,artifact['workloadId'],artifact['workloadRevision']))
            original=cursor.fetchone();require(original is not None,'The original canonical database workload is unavailable')
            dataset=[row for row in _json(original[0])['spec']['datasets'] if row['datasetId']==body['datasetId']]
            require(len(dataset)==1 and dataset[0]['kind']=='database' and dataset[0]['machineId']==body['memberId']
                    and dataset[0]['consistencyGroupId']==body['consistencyGroupId'],
                    'The SQL dataset is not associated with this exact original logical application machine')
        return artifact,descriptor

    def _ledger(self,job):
        path=self.journals/job
        try:path.mkdir(mode=0o700);sync_directory(self.journals)
        except FileExistsError:private_path(path,directory=True)
        return path

    def _retain(self,result):
        sha=canonical_record_digest(result);path=self.outputs/(sha+'.json')
        try:write_new(path,encoded(result))
        except FileExistsError:
            require(strict_loads(read_private(path))==result,'The original SQL receipt custody changed')
        return sha

    def _context(self,request,artifact,descriptor):
        key=(request.admitted.job_id,request.member_id)
        with self._lock:
            if key in self._contexts:
                context,guards=self._contexts[key]
                require(context.artifact==encoded(artifact) and context.admitted==request.admitted
                        and context.descriptor==descriptor,'The original SQL process context was rebound')
                return context,guards
            workers={side:self.runtimes.workers.get(key+(side,)) for side in ('source','target','fence')}
            if any(value is None for value in workers.values()):raise DatabaseHeld('APPLICATION_DATABASE_RUNTIME_UNAVAILABLE')
            context=DatabaseOperationContext(request.admitted,encoded(artifact),descriptor,workers)
            guards={side:DatabaseCommandAuthority(worker,request.admitted,artifact,descriptor,side,self.source_root,
                                                coordination=context) for side,worker in workers.items()}
            # Store before the first original claim. A lost second claim never
            # permits reconstruction/reissue of the first side in this process.
            self._contexts[key]=context,guards
            try:
                for side in ('source','target'):guards[side].claim()
            except BaseException:
                for guard in guards.values():guard.uncertain()
                raise
            return context,guards

    def _reader(self,request,context=None):
        reader=self.runtimes.evidence_readers.get(request.admitted.job_id)
        if reader is None:raise DatabaseHeld('APPLICATION_DATABASE_EVIDENCE_UNAVAILABLE')
        if context is not None:
            require(reader.registry is context.workers['source'].registry,'SQL proofs must retain the same original native registry')
        return reader

    def _preflight(self,request):
        if any(self.runtimes.workers.get((request.admitted.job_id,request.member_id,side)) is None
               for side in ('source','target','fence')):
            raise DatabaseHeld('APPLICATION_DATABASE_RUNTIME_UNAVAILABLE')
        self._reader(request)
        self._readback(request)

    def _readback(self,request):
        reader=self.runtimes.native_readbacks.get(request.admitted.job_id)
        if reader is None:raise DatabaseHeld('APPLICATION_DATABASE_EVIDENCE_UNAVAILABLE')
        return reader

    def _phase_receipt(self,request,descriptor,phase,guard,observations):
        return dict(format='hosting-application-phase-result/1',phase=phase,job_id=request.admitted.job_id,
            member_id=request.member_id,selection_sha256=descriptor.sha256,plan_digest=request.admitted.plan_digest,
            original_intent=guard.original_intent(),status=observations['status'],observations=observations,
            native_intent_requires_independent_resolution=True,production_acceptance=False,native_qualification=False)

    def _phase_scope(self,request,descriptor,phase):
        return {'job':request.admitted.job_id,'dataset':descriptor.to_dict()['datasetId'],
                'selection':descriptor.sha256,'phase':phase,'owner':'postgresql17'}

    def _retire_group(self,request,descriptor,context,guards,sides):
        phase='DATABASE_CREDENTIALS_'+('_'.join(sides)).upper()
        scope=self._phase_scope(request,descriptor,phase)
        with execution_journal.locked(self._ledger(request.admitted.job_id),scope) as log:
            if log.events:
                if len(log.events)==2 and log.events[-1]['kind']=='DATABASE_RETIREMENT_COMPLETED':
                    return log.events[-1]['data']['retirements']
                raise DatabaseHeld('ORIGINAL_DATABASE_EFFECT_REQUIRES_RECONCILIATION')
            if request.mode=='OBSERVE_ORIGINAL':raise DatabaseHeld('ORIGINAL_DATABASE_EFFECT_REQUIRES_RECONCILIATION')
            log.append('DATABASE_RETIREMENT_STARTED',{'sides':list(sides)})
            retirements={side:DatabaseCredentialRetirer(guards[side]).close() for side in sides}
            log.append('DATABASE_RETIREMENT_COMPLETED',{'retirements':retirements})
            return retirements

    def _receipt(self,request,descriptor,phase):
        with execution_journal.locked(self._ledger(request.admitted.job_id),self._phase_scope(request,descriptor,phase)) as log:
            if len(log.events)!=2 or [event['kind'] for event in log.events]!=['DATABASE_PHASE_STARTED','DATABASE_PHASE_COMPLETED']:
                raise DatabaseHeld('ORIGINAL_DATABASE_EFFECT_REQUIRES_RECONCILIATION')
            result=log.events[1]['data']['result']
            require(result['selection_sha256']==descriptor.sha256,'The original SQL phase receipt changed')
            return result

    def _once(self,request,descriptor,phase,effect):
        with execution_journal.locked(self._ledger(request.admitted.job_id),self._phase_scope(request,descriptor,phase)) as log:
            if log.events:
                if len(log.events)==2 and log.events[-1]['kind']=='DATABASE_PHASE_COMPLETED':return log.events[-1]['data']['result']
                raise DatabaseHeld('ORIGINAL_DATABASE_EFFECT_REQUIRES_RECONCILIATION')
            if request.mode=='OBSERVE_ORIGINAL':raise DatabaseHeld('ORIGINAL_DATABASE_EFFECT_REQUIRES_RECONCILIATION')
            log.append('DATABASE_PHASE_STARTED',{'selectionDigest':descriptor.sha256,'phase':phase})
            result=effect();self._retain(result);log.append('DATABASE_PHASE_COMPLETED',{'result':result})
            return result

    def _result(self,request,result):
        return MigrationActivityResult('STAGE_VERIFIED',request.admitted.job_id,request.member_id,
                                       evidence_digest=self._retain(result))

    def _held(self,request,code,*,reason='OPERATOR_HOLD',result=None):
        return MigrationActivityResult('HELD',request.admitted.job_id,request.member_id,reason_code=reason,
            hold_code=code,evidence_digest=None if result is None else self._retain(result))

    def _sync(self,request,phase):
        selected=False
        try:
            artifact,descriptor=self._selected(request)
            if request.mode!='OBSERVE_ORIGINAL':self._preflight(request)
            selected=True
            def effect():
                context,guards=self._context(request,artifact,descriptor);reader=self._reader(request,context)
                with open_database(guards['source']) as source,open_database(guards['target']) as target:
                    runner=PostgresqlSyncRunner(descriptor,source,target,ledger=self._ledger(request.admitted.job_id),evidence=reader)
                    observations=runner.initialize() if phase=='DATABASE_INITIAL' else runner.synchronize()
                result=self._phase_receipt(request,descriptor,phase,guards['target'],observations)
                result['source_original_intent']=guards['source'].original_intent()
                return result
            result=self._once(request,descriptor,phase,effect)
            return self._result(request,result)
        except DatabaseHeld as error:return self._held(request,error.code)
        except AuthorityDenied:return self._held(request,'CURRENT_AUTHORITY_UNAVAILABLE',reason='AUTHORITY_REVOKED')
        except (FileNotFoundError,KeyError,ValueError):
            return self._held(request,'ORIGINAL_DATABASE_EFFECT_REQUIRES_RECONCILIATION' if selected
                else 'APPLICATION_DATABASE_SELECTION_UNAVAILABLE',reason='NATIVE_UNCERTAIN' if selected else 'VALIDATION_FAILED')
        except Exception:return self._held(request,'ORIGINAL_DATABASE_EFFECT_REQUIRES_RECONCILIATION',reason='NATIVE_UNCERTAIN')

    @activity.defn(name='application_database_initialize')
    def database_initialize(self,request:MigrationActivityRequest)->MigrationActivityResult:
        return self._sync(request,'DATABASE_INITIAL')

    @activity.defn(name='application_database_synchronize')
    def database_synchronize(self,request:MigrationActivityRequest)->MigrationActivityResult:
        return self._sync(request,'DATABASE_INCREMENTAL')

    @activity.defn(name='application_database_source_fence')
    def database_source_fence(self,request:MigrationActivityRequest)->MigrationActivityResult:
        try:
            artifact,descriptor=self._selected(request,'SOURCE_FENCE')
            if request.mode!='OBSERVE_ORIGINAL':self._preflight(request)
            def effect():
                context,guards=self._context(request,artifact,descriptor);guard=guards['fence'];guard.claim()
                with open_database(guard) as session:
                    args=(descriptor.to_dict()['streamId'],descriptor.sha256)
                    # The second command runs after the first NOLOGIN commit
                    # and drains a client whose login raced that native commit.
                    for _ in range(2):session.execute('SELECT hosting_sync.fence_application_writers(%s,%s)',args).fetchone()
                    observed=session.execute('SELECT hosting_sync.inspect_writer_fence(%s,%s)',args).fetchone()[0]
                    body=descriptor.to_dict()
                    require(observed==dict(state='SELECTED_APPLICATION_WRITERS_FENCED',writerRoles=body['sourceWriterRoles'],
                        applicationLoginAllowed=False,activeApplicationSessions=0,preparedTransactions=0,databaseRunning=True,
                        datasetId=body['datasetId'],selectionDigest=descriptor.sha256),'The actual original source SQL writer fence was not observed')
                    guard.require_current()
                return self._phase_receipt(request,descriptor,'SOURCE_DATABASE_WRITER_FENCE',guard,
                    dict(status='SOURCE_DATABASE_CLIENTS_PERSISTENTLY_FENCED',database_writer_exclusion=observed,
                         nativeGenerations=self._receipt(request,descriptor,'DATABASE_INITIAL')['observations']['nativeGenerations']))
            result=self._once(request,descriptor,'SOURCE_DATABASE_WRITER_FENCE',effect)
            native=self._readback(request);registry=self._reader(request).registry
            try:native.require_current_acknowledgment(result,registry)
            except (ValueError,RecoveryHeld):
                context,guards=self._context(request,artifact,descriptor)
                retirement=self._retire_group(request,descriptor,context,guards,('fence',))['fence']
                native.acknowledge(result,side='fence',retirement=retirement,context=context)
            return self._result(request,result)
        except DatabaseHeld as error:return self._held(request,error.code)
        except AuthorityDenied:return self._held(request,'CURRENT_AUTHORITY_UNAVAILABLE',reason='AUTHORITY_REVOKED')
        except Exception:return self._held(request,'ORIGINAL_DATABASE_FENCE_REQUIRES_INDEPENDENT_RESOLUTION',reason='NATIVE_UNCERTAIN',
            result=locals().get('result'))

    @activity.defn(name='application_database_final')
    def database_final(self,request:MigrationActivityRequest)->MigrationActivityResult:
        try:
            artifact,descriptor=self._selected(request)
            if request.mode!='OBSERVE_ORIGINAL':self._preflight(request)
            fence=self._receipt(request,descriptor,'SOURCE_DATABASE_WRITER_FENCE')
            reader=self._reader(request)
            native=self._readback(request)
            native.require_current_acknowledgment(fence,reader.registry)
            def effect():
                context,guards=self._context(request,artifact,descriptor)
                with open_database(guards['source']) as source,open_database(guards['target']) as target:
                    runner=PostgresqlSyncRunner(descriptor,source,target,ledger=self._ledger(request.admitted.job_id),
                                                evidence=reader,native_readback=native)
                    observations=runner.final(fence)
                target_receipt=self._phase_receipt(request,descriptor,'DATABASE_FINAL_TARGET',guards['target'],observations)
                source_receipt=self._phase_receipt(request,descriptor,'DATABASE_FINAL_SOURCE',guards['source'],observations)
                return dict(format='hosting-application-database-final/1',job_id=request.admitted.job_id,
                    member_id=request.member_id,selection_sha256=descriptor.sha256,source=source_receipt,
                    target=target_receipt,fence=fence,observations=observations,native_qualification=False)
            result=self._once(request,descriptor,'DATABASE_FINAL',effect)
            pending=[]
            for side in ('source','target'):
                try:native.require_current_acknowledgment(result[side],reader.registry)
                except (ValueError,RecoveryHeld):pending.append(side)
            if pending:
                context,guards=self._context(request,artifact,descriptor)
                retirements=self._retire_group(request,descriptor,context,guards,('source','target'))
            for side in ('source','target'):
                # The original current synchronous completion can be observed
                # in this run. Unknown or lost closure/ACK never dispatches SQL.
                try:native.require_current_acknowledgment(result[side],reader.registry)
                except (ValueError,RecoveryHeld):
                    retirement=retirements[side]
                    self._retain(result[side])
                    native.acknowledge(result[side],side=side,retirement=retirement,context=context)
            native.require_current_acknowledgment(fence,reader.registry)
            return self._result(request,result)
        except DatabaseHeld as error:return self._held(request,error.code)
        except AuthorityDenied:return self._held(request,'CURRENT_AUTHORITY_UNAVAILABLE',reason='AUTHORITY_REVOKED')
        except Exception:return self._held(request,'ORIGINAL_DATABASE_EFFECT_REQUIRES_RECONCILIATION',reason='NATIVE_UNCERTAIN',
            result=locals().get('result'))

    def final_receipt(self,request):
        """Local original receipt only; activation must recheck independent proofs."""
        _artifact,descriptor=self._selected(request)
        return descriptor,self._receipt(request,descriptor,'DATABASE_FINAL')


@dataclass(frozen=True)
class DatabaseFinalProofOwner:
    """Current original database proof for the fixed guest ACTIVATE owner."""
    activities:PostgresqlSyncActivities
    def __post_init__(self):
        require(isinstance(self.activities,PostgresqlSyncActivities),
                'The installed original database activity owner is required')
    def require_final(self,admitted,artifact,lifecycle,member_id):
        descriptor,result,request=self._bound(admitted,artifact,lifecycle,member_id)
        return self._proof(admitted,result,descriptor,request,source_only=False)

    def _bound(self,admitted,artifact,lifecycle,member_id):
        from .lifecycle import ApplicationLifecycleSelection
        require(isinstance(lifecycle,ApplicationLifecycleSelection) and type(artifact) is dict
                and artifact.get('applicationLifecycleSelectionDigest')==lifecycle.sha256,
                'The exact selected application lifecycle is required')
        request=MigrationActivityRequest(admitted,canonical_record_digest(artifact),member_id,'OBSERVE_ORIGINAL')
        descriptor,result=self.activities.final_receipt(request);body=descriptor.to_dict();member=lifecycle.member(member_id)
        require(body['datasetId']!=member['dataset_id'] and body['memberId']==member_id
                and body['source_scope']==lifecycle.to_dict()['source_scope']
                and body['target_scope']==lifecycle.to_dict()['destination_scope']
                and all(body[side+'Guest']=={key:member[side][key] for key in ('native_id','native_uuid','machine_id')}
                    for side in ('source','target')),'The SQL engine differs from the actual selected application guests or data')
        require(result['observations']['sourcePersistentFenceVerified'] is True
                and result['observations']['pendingSelectedTransactions']==0
                and result['observations']['status']=='LOCKED_SELECTED_TABLES_EQUAL',
                'The original final application database proof is incomplete')
        return descriptor,result,request

    def _proof(self,admitted,result,descriptor,request,*,source_only):
        body=descriptor.to_dict();member_id=request.member_id
        reader=self.activities._reader(request)
        native=self.activities._readback(request)
        proofs=({'source':native.require_source_exclusion(result['source'],reader.registry)} if source_only else
            {side:native.require_current_acknowledgment(result[side],reader.registry) for side in ('source','target')})
        proofs['fence']=native.require_current_acknowledgment(result['fence'],reader.registry)
        directories={key:proofs['source'][key] for key in ('sourceDataDirectory','targetDataDirectory')}
        require(all(proof[key]==directories[key] for proof in proofs.values() for key in directories),
                'The actual independently observed native database engine moved')
        return dict(format='hosting-current-application-database-proof/1',job_id=admitted.job_id,
            member_id=member_id,dataset_id=body['datasetId'],database_selection_digest=descriptor.sha256,
            final_receipt_digest=canonical_record_digest(result),observations=dict(result['observations'],**directories),
            original_native_proofs=proofs,source_writer_exclusion_only=source_only,native_qualification=False)

    def require_source_exclusion(self,admitted,artifact,lifecycle,member_id):
        descriptor,result,request=self._bound(admitted,artifact,lifecycle,member_id)
        return self._proof(admitted,result,descriptor,request,source_only=True)
