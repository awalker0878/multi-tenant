"""Approved, content-addressed execution inputs for the first directed route.

An admitted job never supplies a filename, module, command or credential. The
canonical plan binds one immutable, plan-independent selection digest. The
selected artifact remains under the installed worker's independently protected
custody; this reader neither enrolls that custody nor qualifies a platform.
"""
from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from typing import Callable

from provisioner.controlplane.authority import postgres as authority_postgres
from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.jobs.repository import (
    _JOB_SELECT, _digest, _ensure_plan, _ensure_workload, _job, _json, _tenant, _payload_from_job,
)
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.persistence import canonical_record_digest
from provisioner.domain.enterprise_records import validate_record
from provisioner.execution.run_files import load_private, private_path, require
from .admitted_job import AdmittedInput
from .approval_gate import _valid_digest, _valid_id

FORMAT = 'hosting-openstack-execution-artifact/1'
DRIVER = 'openstack-linux-rebuild/1'
DATABASE_DRIVER = 'openstack-linux-application-database/1'
STAGING_DRIVER = 'openstack-linux-application-staging/1'
CUTOVER_DRIVER = 'openstack-linux-application-cutover/1'
APPLICATION_RECOVERY_DRIVER = 'application-postwrite-recovery/1'
COLD_DRIVER = 'vmware-openstack-cold-capture/1'
COLD_FORMAT = 'hosting-cold-capture-artifact/1'
_COLD_FIELDS = frozenset({'format', 'driver', 'sourceCommit', 'workloadId', 'workloadRevision',
    'source', 'destination', 'executionScope', 'sourceTuple', 'destinationTuple', 'guestProfile',
    'qualificationDigest', 'operationsAcceptanceDigest', 'resourceBundleDigest', 'coldCaptureSelectionDigest'})
_FIELDS = frozenset({
    'format', 'driver', 'sourceCommit', 'workloadId', 'workloadRevision',
    'source', 'destination', 'executionScope', 'resourceBundleDigest',
    'datasetSelectionDigest', 'cutoverSelectionDigest', 'deliveryPlanDigest',
    'qualificationDigest', 'operationsAcceptanceDigest', 'sourceTuple', 'destinationTuple', 'guestProfile', 'stageBindings',
})
_OPTIONAL_FIELDS = frozenset({'ipamSelections', 'applicationLifecycleSelectionDigest',
                             'applicationRecoverySelectionDigest', 'applicationDatabaseSelectionDigest',
                             'resourceRecoverySelectionDigest', 'applicationStagingSelectionDigest'})
_AUTHORITY_FILES = frozenset({
    'authority', 'approval', 'environment', 'credentials', 'token',
    'token_file', 'session', 'ssh_key', 'ssh_certificate', 'tsig_file',
    'restore_authority', 'receipt', 'secrets',
})


def validate_selection(value: dict) -> dict:
    if type(value) is dict and value.get('format') == 'hosting-existing-windows-services-artifact/1':
        from .windows_service_selection import validate_artifact
        return validate_artifact(value)
    if type(value) is dict and value.get('format') == COLD_FORMAT:
        return _validate_cold_artifact(value)
    require(type(value) is dict and _FIELDS <= value.keys()
            and value.keys() <= _FIELDS | _OPTIONAL_FIELDS,
            'An exact versioned OpenStack execution selection is required')
    require(value['format'] == FORMAT and value['driver'] in {
                DRIVER, DATABASE_DRIVER, STAGING_DRIVER, CUTOVER_DRIVER, APPLICATION_RECOVERY_DRIVER},
            'An implemented directed execution driver is required')
    require(type(value['sourceCommit']) is str and len(value['sourceCommit']) == 40
            and all(c in '0123456789abcdef' for c in value['sourceCommit']),
            'The execution source must be an exact commit')
    require(_valid_id(value['workloadId']) and type(value['workloadRevision']) is int
            and value['workloadRevision'] > 0, 'An immutable workload selection is required')
    source = PlanScope.from_record(value['source'])
    destination = PlanScope.from_record(value['destination'])
    require(((source.platform_family, destination.platform_family) == ('vmware', 'openstack')
                if value['driver'] != APPLICATION_RECOVERY_DRIVER else
                ((source.platform_family, destination.platform_family) == ('vmware', 'openstack')
                    or source == destination and
                        (source.platform_family, destination.platform_family) == ('openstack', 'openstack')))
            and (source.organization_id, source.tenant_id) ==
                (destination.organization_id, destination.tenant_id),
            'Only the selected same-tenant VMware to OpenStack route is implemented')
    scope = value['executionScope']
    require(type(scope) is dict and scope.keys() == {
        'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key'},
        'The native owner requires an exact execution scope')
    require(all(_valid_id(v) for v in scope.values()) and
            (scope['platform'], scope['site_key'], scope['tenant_key'], scope['wsd_key']) ==
            (destination.platform_family, destination.site_id,
             destination.tenant_id, destination.security_domain_id),
            'Execution labels do not match the approved destination scope')
    require(all(_valid_digest(value[key]) for key in (
        'resourceBundleDigest', 'datasetSelectionDigest', 'cutoverSelectionDigest',
        'deliveryPlanDigest', 'qualificationDigest', 'operationsAcceptanceDigest')),
        'Every selected resource, data, cutover and native claim needs an exact digest')
    require(type(value['sourceTuple']) is dict and type(value['destinationTuple']) is dict
            and value['guestProfile'] == 'linux-ubuntu-2404',
            'Exact installed source and destination tuples and guest profile are required')
    bindings = value['stageBindings']
    require(type(bindings) is dict and 1 <= len(bindings) <= 100,
            'Every selected stage must bind its reviewed non-secret inputs')
    for step_id, binding in bindings.items():
        require(_valid_id(step_id) and type(binding) is dict and binding.keys() ==
                {'kind', 'parametersDigest', 'inputDigests'}, 'Exact stage binding required')
        require(_valid_id(binding['kind']) and _valid_digest(binding['parametersDigest'])
                and type(binding['inputDigests']) is dict,
                'Stage parameters and input digests must be immutable')
        require(all(_valid_id(name) and name not in _AUTHORITY_FILES and
                    _valid_digest(digest) for name, digest in binding['inputDigests'].items()),
                'Secrets and live authority must not be included in approved selection content')
    ipam = value.get('ipamSelections', [])
    require(type(ipam) is list and len(ipam) <= 100, 'Bounded selected IPAM allocations required')
    from provisioner.allocations.netbox_ipam import validate_selection as validate_ipam_selection
    for item in ipam:
        require(type(item) is dict and item.keys() == {
            'format', 'origin', 'scope', 'member', 'tenant_id', 'vrf_id',
            'prefix_id', 'prefix', 'address'} and item['scope'] == scope,
            'Exact IPAM selection must match the approved destination owner scope')
        validate_ipam_selection(item)
    require(len({_digest(item) for item in ipam}) == len(ipam), 'Duplicate selected IPAM allocations')
    if 'applicationLifecycleSelectionDigest' in value:
        require(_valid_digest(value['applicationLifecycleSelectionDigest']),
                'The selected application lifecycle needs an exact immutable digest')
    if 'applicationRecoverySelectionDigest' in value:
        require(_valid_digest(value['applicationRecoverySelectionDigest'])
                and value['driver'] == APPLICATION_RECOVERY_DRIVER
                and _valid_digest(value.get('applicationLifecycleSelectionDigest')),
                'The separately approved application recovery needs an exact immutable digest')
    require((value['driver'] == APPLICATION_RECOVERY_DRIVER) == ('applicationRecoverySelectionDigest' in value)
            and not (value['driver'] == APPLICATION_RECOVERY_DRIVER and {
                'applicationDatabaseSelectionDigest', 'applicationStagingSelectionDigest',
                'resourceRecoverySelectionDigest', 'ipamSelections'}.intersection(value)),
            'Post-write recovery needs its own exact purpose without new creation or allocation')
    if 'applicationDatabaseSelectionDigest' in value:
        require(_valid_digest(value['applicationDatabaseSelectionDigest'])
                and _valid_digest(value.get('applicationLifecycleSelectionDigest'))
                and value['driver'] == DATABASE_DRIVER,
                'Database synchronization requires the exact selected lifecycle and database descriptor')
    require(value['driver'] != DATABASE_DRIVER or 'applicationDatabaseSelectionDigest' in value,
            'The dedicated database method requires its immutable database selection')
    if 'resourceRecoverySelectionDigest' in value:
        require(_valid_digest(value['resourceRecoverySelectionDigest']) and value['driver'] == DRIVER
                and 'applicationRecoverySelectionDigest' not in value
                and 'applicationDatabaseSelectionDigest' not in value,
                'Resource cleanup requires its exact separately approved fixed purpose')
    if 'applicationStagingSelectionDigest' in value:
        require(_valid_digest(value['applicationStagingSelectionDigest'])
                and _valid_digest(value.get('applicationLifecycleSelectionDigest'))
                and value['driver'] in {CUTOVER_DRIVER, DATABASE_DRIVER},
                'Staged cutover requires its actual target handover and current lifecycle')
    require(value['driver'] != CUTOVER_DRIVER or 'applicationStagingSelectionDigest' in value,
            'The cutover driver requires exact independently observed staged targets')
    require(value['driver'] != STAGING_DRIVER or not {
                'applicationLifecycleSelectionDigest', 'applicationStagingSelectionDigest',
                'applicationRecoverySelectionDigest', 'applicationDatabaseSelectionDigest',
                'resourceRecoverySelectionDigest'}.intersection(value),
            'Initial creation cannot approve future native IDs or copied application data')
    return value


def _validate_cold_artifact(value):
    require(value.keys() == _COLD_FIELDS and value['driver'] == COLD_DRIVER,
            'One exact cold capture purpose artifact is required')
    require(type(value['sourceCommit']) is str and len(value['sourceCommit']) == 40
            and all(c in '0123456789abcdef' for c in value['sourceCommit'])
            and _valid_id(value['workloadId']) and type(value['workloadRevision']) is int
            and value['workloadRevision'] > 0, 'Exact installed cold source and workload revision required')
    source, destination = PlanScope.from_record(value['source']), PlanScope.from_record(value['destination'])
    require((source.platform_family, destination.platform_family) == ('vmware', 'openstack')
            and (source.organization_id, source.tenant_id) == (destination.organization_id, destination.tenant_id)
            and value['guestProfile'] in {'linux-ubuntu-2404', 'windows-server-2022'}
            and type(value['sourceTuple']) is dict and type(value['destinationTuple']) is dict,
            'Only the exact same-tenant VMware snapshot to OpenStack image purpose exists')
    scope = value['executionScope']
    require(type(scope) is dict and scope.keys() == {
                'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key'}
            and all(_valid_id(item) for item in scope.values())
            and (scope['platform'], scope['site_key'], scope['tenant_key'], scope['wsd_key']) ==
                (destination.platform_family, destination.site_id, destination.tenant_id, destination.security_domain_id)
            and all(_valid_digest(value[key]) for key in {
                'qualificationDigest', 'operationsAcceptanceDigest', 'resourceBundleDigest', 'coldCaptureSelectionDigest'}),
            'Exact cold scope, resource accounting and original qualification evidence required')
    return value


class FileExecutionSelectionStore:
    """Bounded no-follow reads in an explicit private content-addressed store."""

    def __init__(self, directory: Path):
        self.directory = private_path(directory, directory=True)

    def load_verified(self, selection_digest: str) -> dict:
        require(_valid_digest(selection_digest), 'An exact approved selection digest is required')
        value = validate_selection(load_private(self.directory / (selection_digest + '.json')))
        require(_digest(value) == selection_digest, 'Selected execution artifact content changed')
        return value


class PostgresExecutionAuthority:
    """Recheck the current job, original plan, approvals and retained selection.

    Qualification is an independent selected-site owner with a require_action
    method. It must authenticate original claim custody and freshness for this
    precise installed route/action. There is no permissive default verifier.
    """

    def __init__(self, connect: Callable, selections: FileExecutionSelectionStore,
                 qualification, evidence, operations, instance_gate=None):
        from provisioner.controlplane.operations.instance import OperatingInstanceGate
        require(callable(connect) and callable(getattr(selections, 'load_verified', None))
                and callable(getattr(qualification, 'require_action', None))
                and callable(getattr(evidence, 'require', None))
                and callable(getattr(operations, 'require_action', None)),
                'Current selection, qualification and independent evidence owners are required')
        self.connect, self.selections = connect, selections
        self.qualification, self.evidence = qualification, evidence
        self.operations = operations
        require(instance_gate is None or isinstance(instance_gate, OperatingInstanceGate),
                'Fixed restored-instance operating custody owner required')
        self.instance_gate = instance_gate

    def require_current(self, admitted: AdmittedInput, selection_digest: str,
                        operation_kind: str, *, continuation_grant=None,
                        continuation_identity=None) -> tuple[dict, dict]:
        return self._require(admitted, selection_digest, operation_kind,
            purpose='CONTINUATION' if continuation_grant is not None or continuation_identity is not None else 'EFFECT',
            continuation_grant=continuation_grant, continuation_identity=continuation_identity)

    def require_observation(self, admitted: AdmittedInput, selection_digest: str,
                            operation_kind: str, *, cursor=None) -> tuple[dict, dict]:
        """Read bound local evidence; this result has no native effect authority."""
        require(callable(getattr(self.operations, 'require_observation', None)),
                'A separately named operating observation gate is required')
        return self._require(admitted, selection_digest, operation_kind,
                             purpose='OBSERVATION', observation_cursor=cursor)

    def require_database_current(self, admitted: AdmittedInput, selection_digest: str,
                                 operation_kind: str, *, coordination):
        """Coordinate only the actual selected source, target and SQL fence owners."""
        from provisioner.migration.postgresql_authority import DatabaseOperationContext
        require(isinstance(coordination, DatabaseOperationContext)
                and coordination.admitted == admitted
                and coordination.artifact_digest == selection_digest
                and all(worker.command.authority is self for worker in coordination.workers.values())
                and operation_kind in {'RESTORE_DATA', 'SOURCE_FENCE'}
                and callable(getattr(self.operations, 'require_database_continuation', None)),
                'The exact separately enrolled original SQL operation context is required')
        return self._require(admitted, selection_digest, operation_kind,
                             purpose='DATABASE', database_coordination=coordination)

    def require_canonical_transition(self, admitted: AdmittedInput, selection_digest: str, *,
                                     cursor, operation_kind='DESTINATION_ACTIVATE'):
        """Recheck the original approved logical transition in its real owner transaction."""
        require(operation_kind in {'DISCOVER_READ', 'DESTINATION_ACTIVATE'},
                'Only staged target association or independently proved application promotion is allowed')
        return self._require(admitted, selection_digest, operation_kind,
                             purpose='CANONICAL_TRANSITION', observation_cursor=cursor)

    def _require(self, admitted, selection_digest, operation_kind, *, purpose,
                 continuation_grant=None, continuation_identity=None, observation_cursor=None,
                 database_coordination=None):
        from provisioner.controlplane.worker.grants import WorkerGrant, VerifiedWorkerIdentity
        continuing = continuation_grant is not None or continuation_identity is not None
        require(not continuing or (isinstance(continuation_grant, WorkerGrant)
                and isinstance(continuation_identity, VerifiedWorkerIdentity)
                and continuation_grant.operation_kind == operation_kind
                and callable(getattr(self.operations, 'require_continuation', None))),
                'A continuation requires the exact currently verified original native grant')
        require(isinstance(admitted, AdmittedInput) and _valid_digest(selection_digest),
                'The immutable admitted job and execution selection are required')
        context = TenantContext(admitted.organization_id, admitted.tenant_id)
        self.evidence.require(context)
        with ExitStack() as owned:
            if observation_cursor is None:
                connection = owned.enter_context(self.connect())
                cursor = owned.enter_context(connection.cursor())
            else:
                import psycopg
                require(purpose in {'OBSERVATION', 'CANONICAL_TRANSITION'} and not continuing
                        and isinstance(observation_cursor, psycopg.Cursor)
                        and not observation_cursor.connection.autocommit
                        and observation_cursor.connection.info.transaction_status ==
                            psycopg.pq.TransactionStatus.INTRANS,
                        'An original observation requires the actual existing scoped transaction')
                cursor = observation_cursor
            _tenant(cursor, context)
            cursor.execute('SELECT hosting_controlplane.lock_job_scope(%s, %s, %s)',
                           (context.organization_id, context.tenant_id, admitted.job_id))
            require(cursor.fetchone() == (True,), 'The admitted job is not current')
            cursor.execute(f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                           'WHERE organization_id = %s AND tenant_id = %s AND job_id = %s',
                           (context.organization_id, context.tenant_id, admitted.job_id))
            row = cursor.fetchone()
            require(row is not None, 'The admitted job is not visible in this tenant')
            job = _job(row)
            require(job.status in ({'STARTED', 'RUNNING', 'HELD', 'SUCCEEDED', 'FAILED', 'CANCELLED'} if purpose == 'OBSERVATION'
                                   else {'STARTED', 'RUNNING'}) and
                    (job.plan_id, job.plan_revision, job.plan_digest, job.revocation_epoch) ==
                    (admitted.plan_id, admitted.plan_revision, admitted.plan_digest,
                     admitted.revocation_epoch)
                    and _digest(_payload_from_job(job)) == admitted.payload_digest,
                    'The job or approval revision changed')
            cursor.execute('SELECT payload,start_payload_digest,start_run_id FROM '
                           'hosting_controlplane.job_outbox WHERE organization_id=%s '
                           'AND tenant_id=%s AND job_id=%s AND delivered_at IS NOT NULL FOR SHARE',
                           (context.organization_id, context.tenant_id, admitted.job_id))
            started = cursor.fetchone()
            require(started is not None and started[2]
                    and started[1] == admitted.payload_digest
                    and _digest(_json(started[0])) == admitted.payload_digest,
                    'The admitted job has no exact acknowledged original workflow run')
            cursor.execute('SELECT clock_timestamp()')
            at = cursor.fetchone()[0]
            if purpose != 'OBSERVATION':
                authority_postgres.revalidate_start(cursor, job, at)
            table = 'enterprise_record_history' if purpose == 'OBSERVATION' else 'enterprise_records'
            revision_query = ' AND revision = %s' if purpose == 'OBSERVATION' else ''
            parameters = (context.organization_id, context.tenant_id, job.plan_id)
            if purpose == 'OBSERVATION':
                parameters += (job.plan_revision,)
            cursor.execute('SELECT revision, record_digest, record_json FROM '
                           f'hosting_controlplane.{table} WHERE organization_id = %s '
                           "AND tenant_id = %s AND record_kind = 'MigrationPlan' AND record_id = %s"
                           + revision_query + ('' if purpose == 'OBSERVATION' else ' FOR SHARE'), parameters)
            plan = _ensure_plan(cursor.fetchone(), context, job)
            if purpose == 'OBSERVATION':
                self._require_retained_workload(cursor, context, plan)
            else:
                _ensure_workload(cursor, context, plan)
            selection = self.selections.load_verified(selection_digest)
            require(plan['spec'].get('execution') == {
                'format': 'hosting-execution-selection/1', 'driver': selection['driver'],
                'artifactDigest': selection_digest},
                'The original approved plan does not select this execution artifact')
            require((selection['workloadId'], selection['workloadRevision'],
                     selection['source'], selection['destination'], selection['qualificationDigest'],
                     selection['guestProfile']) ==
                    (plan['spec']['workloadId'], plan['spec']['workloadRevision'],
                     plan['spec']['source'], plan['spec']['destination'],
                     plan['spec']['route']['qualificationDigest'], plan['spec']['route']['guestProfile']),
                    'Execution content differs from the approved workload, route or scope')
            recovery = plan['spec'].get('resourceRecovery')
            require((recovery is None and 'resourceRecoverySelectionDigest' not in selection) or
                    (type(recovery) is dict and selection.get('resourceRecoverySelectionDigest') ==
                     canonical_record_digest(recovery)),
                    'The selected resource recovery purpose differs from the approved original intents')
            cutover = plan['spec'].get('applicationStagedCutover')
            require((cutover is None and 'applicationStagingSelectionDigest' not in selection) or
                    (type(cutover) is dict and selection.get('applicationStagingSelectionDigest') ==
                     cutover['stagedHandoverDigest'] and selection['driver'] in {CUTOVER_DRIVER, DATABASE_DRIVER}),
                    'The current cutover differs from the approved actual staged targets')
            require((selection['driver'] == STAGING_DRIVER) ==
                    (plan['spec'].get('applicationStaging') == {'format': 'hosting-application-staging-plan/1'}),
                    'Only an explicit staging approval may create and associate new targets')
            application_recovery = plan['spec'].get('applicationRecovery')
            require((selection['driver'] == APPLICATION_RECOVERY_DRIVER) == (application_recovery is not None),
                    'Post-write application recovery requires a separately approved fixed purpose')
            if application_recovery is not None:
                require(application_recovery['mode'] == 'FORWARD_REPAIR'
                        and application_recovery['originalJobId'] != admitted.job_id
                        and application_recovery['originalPlanDigest'] != admitted.plan_digest,
                        'Only independently admitted forward repair of the existing target has an effect owner')
            cold = plan['spec'].get('coldCapture')
            require((selection['driver'] == COLD_DRIVER) == (cold is not None)
                    and (cold is None or cold == {'format': 'hosting-cold-capture-purpose/1',
                        'selectionDigest': selection.get('coldCaptureSelectionDigest')}),
                    'Cold bytes require their exact partial purpose and original selection')
            from .windows_service_selection import DRIVER as WINDOWS_DRIVER, WindowsServiceSelection
            require((selection['driver'] == WINDOWS_DRIVER) == ('windowsServices' in plan['spec']),
                    'Existing Windows services require their separately approved operational purpose')
            if selection['driver'] == WINDOWS_DRIVER:
                WindowsServiceSelection.from_record(selection['windowsServices']).require_plan(plan, selection)
            if purpose == 'OBSERVATION':
                self.operations.require_observation(cursor, admitted, selection)
                if self.instance_gate is not None:
                    self.instance_gate.require_observation(cursor, context)
            elif purpose == 'DATABASE':
                from provisioner.execution.run_files import encoded
                require(selection['driver'] == DATABASE_DRIVER
                        and encoded(selection) == database_coordination.artifact
                        and selection['applicationDatabaseSelectionDigest'] ==
                            database_coordination.descriptor.sha256,
                        'The SQL operation context differs from the original protected artifact')
                self._require_instance(cursor, context, selection, operation_kind)
                self.qualification.require_action(cursor, admitted, selection, operation_kind)
                self.operations.require_database_continuation(cursor, admitted, selection,
                    coordination=database_coordination)
            elif continuing:
                self._require_instance(cursor, context, selection, operation_kind)
                self.qualification.require_action(cursor, admitted, selection, operation_kind)
                self.operations.require_continuation(cursor, admitted, selection,
                    grant=continuation_grant, worker_identity=continuation_identity)
            else:
                self._require_instance(cursor, context, selection, operation_kind)
                self.qualification.require_action(cursor, admitted, selection, operation_kind)
                self.operations.require_action(cursor, admitted, selection, operation_kind)
            return plan, selection

    def _require_instance(self, cursor, context, selection, operation_kind):
        # Genuine enrolled read-only discovery remains available to establish
        # independent commissioning facts. It cannot select a mutation owner.
        if operation_kind == 'DISCOVER_READ':
            if self.instance_gate is not None:
                self.instance_gate.require_observation(cursor, context)
            return
        require(self.instance_gate is not None,
                'Uncommissioned operating instance cannot authorize a native effect')
        require(selection['sourceCommit'] == self.instance_gate.source_commit,
                'Execution selection differs from the commissioned installed source')
        self.instance_gate.require_write_admission(cursor, context,
            security_domain_id=selection['destination']['securityDomainId'],
            workload_id=selection['workloadId'])

    @staticmethod
    def _require_retained_workload(cursor, context, plan):
        """Validate original immutable facts without accepting a new effect."""
        selected = plan['spec']
        cursor.execute('SELECT revision, record_digest, record_json FROM '
            'hosting_controlplane.enterprise_record_history WHERE organization_id = %s '
            "AND tenant_id = %s AND record_kind = 'Workload' AND record_id = %s "
            'AND revision = %s',
            (context.organization_id, context.tenant_id, selected['workloadId'],
             selected['workloadRevision']))
        row = cursor.fetchone()
        require(row is not None, 'Original retained workload facts are unavailable')
        revision, record_digest, raw = row
        workload = _json(raw)
        require(type(workload) is dict and workload.get('kind') == 'Workload'
                and workload.get('metadata', {}).get('revision') == revision
                and workload['metadata'].get('workloadId') == selected['workloadId']
                and (workload['metadata'].get('organizationId'), workload['metadata'].get('tenantId')) ==
                    (context.organization_id, context.tenant_id)
                and canonical_record_digest(workload) == record_digest
                and not validate_record(workload) and not validate_record(plan, workload=workload),
                'Original retained workload facts or selected source binding changed')

    def require_packet(self, admitted: AdmittedInput, selection_digest: str,
                       delivery: dict, step: dict, packet: dict, operation_kind: str) -> dict:
        plan, selection = self.require_current(admitted, selection_digest, operation_kind)
        require(_digest(delivery) == selection['deliveryPlanDigest'] and
                delivery['source_commit'] == selection['sourceCommit'] and
                delivery['scope'] == selection['executionScope'],
                'The selected delivery or source changed')
        binding = selection['stageBindings'].get(step['id'])
        require(binding is not None and binding['kind'] == step['kind'] and
                binding['parametersDigest'] == _digest(packet['parameters']),
                'The stage differs from the approved execution selection')
        immutable = {name: entry['sha256'] for name, entry in packet['files'].items()
                     if name not in _AUTHORITY_FILES}
        require(immutable == binding['inputDigests'],
                'The exact non-secret stage inputs were not approved')
        return plan
