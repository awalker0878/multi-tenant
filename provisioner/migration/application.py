"""Concrete restic children for the selected VMware/Linux/OpenStack path.

Descriptors are approved before the canonical plan is frozen. Transfer envelopes
are bound to that frozen plan afterward, avoiding a digest self-reference. The
same native intent registry and existing restore executor perform every effect;
this module supplies no arbitrary callback or alternate native dispatcher.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat
import time

from provisioner.controlplane.authority import AuthorityService, PlanScope
from provisioner.controlplane.persistence import TenantContext, canonical_record_digest
from provisioner.controlplane.persistence.store import NativeBinding, OwnerLease
from provisioner.controlplane.reconciliation import NativeOperationRegistry
from provisioner.controlplane.worker.grants import VerifiedWorkerIdentity
from provisioner.domain.enterprise_records import validate_record
from provisioner.execution import execution_journal, dataset_acceptance, restic_run
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.restic_transfer import (
    TransferGuard, destination_receipt, execute_authorized_transfer,
    validate as validate_transfer)
from provisioner.execution.run_files import (
    digest, encoded, load_private, private_path, require)

from .resources import LinuxTransferResources, TransferLimits
from .authority import ApplicationCommandAuthority

FORMAT = 'hosting-application-dataset-selection/1'
_IMPLEMENTED_DIRECTION = frozenset({('vmware', 'openstack')})
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}')
_FIELDS = {'step_id', 'operation_id', 'dataset_id', 'target_ref',
           'consistency_group_id', 'target_member', 'target_root', 'source_config',
           'source_receipt', 'file_manifest', 'target_metadata', 'resources'}
_META = {'mode', 'uid', 'gid'}


def _metadata(root):
    """Inspect useful restored files without interpreting application contents."""
    root = Path(root)
    require(root.is_dir() and not any(p.is_symlink() for p in (root, *root.parents)),
            'Ordinary restored useful directory required')
    rows = {}
    for path in sorted(root.rglob('*')):
        info = path.lstat()
        require(info.st_dev == root.stat().st_dev
                and (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)),
                'Restored metadata cannot cross mounts or contain special files')
        rows[path.relative_to(root).as_posix()] = dict(mode=stat.S_IMODE(info.st_mode),
                                                    uid=info.st_uid, gid=info.st_gid)
    return rows


def _path(value):
    require(isinstance(value, str) and Path(value).is_absolute()
            and Path(value) != Path('/') and '..' not in Path(value).parts
            and str(Path(value)) == value,
            'Canonical isolated useful-data path required')
    return Path(value)


def _metadata_mapping(value, manifest):
    require(isinstance(value, dict) and value,
            'Approved target file and directory metadata is required')
    files = set(manifest['files'])
    directories = {parent.as_posix() for name in files for parent in Path(name).parents
                   if parent != Path('.')}
    require(set(value) == files | directories,
            'Target metadata must cover every useful file and directory')
    for name, row in value.items():
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts and str(path) == name
                and isinstance(row, dict) and set(row) == _META
                and all(type(number) is int for number in row.values())
                and 0 <= row['mode'] <= 0o7777 and 0 <= row['uid'] <= 2 ** 32 - 2
                and 0 <= row['gid'] <= 2 ** 32 - 2,
                'Exact supported target ownership and mode required')


@dataclass(frozen=True)
class ApplicationDataSelection:
    """Canonical private descriptor bytes; no credential or approval lives here."""
    canonical: bytes

    def __post_init__(self):
        require(isinstance(self.canonical, bytes) and len(self.canonical) <= 16 * 1024 * 1024,
                'Bounded canonical application data selection required')
        body = strict_loads(self.canonical)
        require(self.canonical == encoded(body) and isinstance(body, dict)
                and set(body) == {'format', 'source_scope', 'destination_scope',
                                  'guest_profile', 'datasets'} and body['format'] == FORMAT,
                'Exact canonical application dataset selection required')
        source, target = body['source_scope'], body['destination_scope']
        source_scope, target_scope = PlanScope.from_record(source), PlanScope.from_record(target)
        require((source_scope.platform_family, target_scope.platform_family) in _IMPLEMENTED_DIRECTION
                and (source_scope.organization_id, source_scope.tenant_id) ==
                    (target_scope.organization_id, target_scope.tenant_id)
                and body['guest_profile'] == 'linux-ubuntu-2404',
                'Only the selected VMware to OpenStack Ubuntu 24.04 application path is implemented')
        rows = body['datasets']
        require(isinstance(rows, list) and 1 <= len(rows) <= 32,
                'One to thirty-two explicitly selected dataset children required')
        unique = {key: set() for key in ('step_id', 'operation_id', 'dataset_id',
                                        'target_ref', 'target_root', 'source_receipt')}
        roots = []
        for row in rows:
            require(isinstance(row, dict) and set(row) == _FIELDS,
                    'Exact immutable dataset descriptor required')
            for key in ('step_id', 'operation_id', 'dataset_id', 'target_ref',
                        'consistency_group_id', 'target_member'):
                require(isinstance(row[key], str) and _ID.fullmatch(row[key]),
                        'Bounded dataset, step and operation identities required')
            for key in unique:
                value = digest(encoded(row[key])) if key == 'source_receipt' else row[key]
                require(value not in unique[key], 'Dataset descriptors cannot reuse identities or receipts')
                unique[key].add(value)
            root = _path(row['target_root'])
            require(not any(root.is_relative_to(other) or other.is_relative_to(root)
                            for other in roots), 'Dataset restore roots must not overlap')
            roots.append(root)
            config, receipt, manifest = (row[name] for name in
                                        ('source_config', 'source_receipt', 'file_manifest'))
            restic_run.validate(config, allow_expired=True)
            require(receipt.get('format') == 'hosting-restic-receipt/1'
                    and receipt.get('status') == 'CAPTURED_REQUIRES_RESTORE_TEST'
                    and receipt.get('scope') == manifest.get('scope') == config['scope']
                    and receipt.get('member') == manifest.get('member') == config['member']
                    and receipt.get('repository_id') == config['repository_id']
                    and receipt.get('source') == manifest.get('source') == config['source']
                    and receipt.get('manifest_sha256') == digest(encoded(manifest))
                    and receipt.get('captured_at') == manifest.get('captured_at')
                    and manifest.get('format') == 'hosting-file-manifest/1'
                    and manifest.get('consistency_ref') == config['consistency_ref'],
                    'Dataset capture must preserve the original source manifest and receipt')
            require(isinstance(manifest.get('files'), dict) and manifest['files'],
                    'Exact useful captured files required')
            for name, file in manifest['files'].items():
                path = Path(name)
                require(isinstance(name, str) and not path.is_absolute()
                        and '..' not in path.parts and str(path) == name
                        and isinstance(file, dict) and set(file) == {'size', 'sha256'}
                        and type(file['size']) is int and file['size'] >= 0
                        and isinstance(file['sha256'], str)
                        and re.fullmatch('[0-9a-f]{64}', file['sha256']),
                        'Ordinary captured file identities and exact bytes required')
            _metadata_mapping(row['target_metadata'], manifest)
            resource = row['resources']
            require(isinstance(resource, dict)
                    and set(resource) == {'stage_parent', 'cgroup', 'block_device', 'limits'}
                    and isinstance(resource['limits'], dict)
                    and set(resource['limits']) == {'download_kib_per_second', 'block_iops',
                                                   'stage_bytes', 'expected_bytes'},
                    'Exact independently commissioned transfer resource binding required')
            controls = LinuxTransferResources(Path(resource['stage_parent']), resource['cgroup'],
                                              resource['block_device'], TransferLimits(**resource['limits']))
            require(root.parent == controls.stage_parent
                    and controls.limits.expected_bytes ==
                        sum(file['size'] for file in manifest['files'].values()),
                    'Dataset resources must cover exactly this useful capture and target volume')

    @classmethod
    def from_record(cls, body):
        return cls(encoded(body))

    @property
    def sha256(self):
        return canonical_record_digest(self.to_dict())

    def to_dict(self):
        return strict_loads(self.canonical)


@dataclass(frozen=True)
class DatasetWorkerRuntime:
    """Authenticated live worker dependencies; never hydrated from request JSON."""
    authority: AuthorityService
    registry: NativeOperationRegistry
    context: TenantContext
    lease: OwnerLease
    identity: VerifiedWorkerIdentity
    credential: object
    grant_id: str
    lease_key: str
    binary: Path
    credentials: dict
    resources: LinuxTransferResources
    ca_file: Path | None = None

    def __post_init__(self):
        require(isinstance(self.authority, AuthorityService)
                and isinstance(self.registry, NativeOperationRegistry)
                and isinstance(self.context, TenantContext)
                and isinstance(self.lease, OwnerLease)
                and isinstance(self.identity, VerifiedWorkerIdentity)
                and isinstance(self.resources, LinuxTransferResources)
                and all(isinstance(value, str) and _ID.fullmatch(value)
                        for value in (self.grant_id, self.lease_key))
                and isinstance(self.binary, Path),
                'Live enrolled worker, native intent registry and resource owners are required')


class ApplicationDataRunner:
    """Execute/reconcile one actual restic child, then join the complete mapping.

    The enclosing admitted activity must independently load this artifact from
    protected storage and revalidate its current job/plan/revocation epoch. A
    fixture, comparison result or JSON boolean never supplies those authorities.
    """
    def __init__(self, *, job_id, plan, execution_artifact, selection, ledger, database_selection=None):
        require(isinstance(job_id, str) and _ID.fullmatch(job_id)
                and isinstance(selection, ApplicationDataSelection)
                and isinstance(plan, dict) and plan.get('kind') == 'MigrationPlan'
                and not validate_record(plan), 'Exact admitted migration selection and canonical plan required')
        execution = plan['spec'].get('execution', {})
        require(execution.get('format') == 'hosting-execution-selection/1'
                and execution.get('driver') in {'openstack-linux-rebuild/1',
                    'openstack-linux-application-cutover/1', 'openstack-linux-application-database/1'}
                and execution.get('artifactDigest') == canonical_record_digest(execution_artifact)
                and execution_artifact.get('datasetSelectionDigest') == selection.sha256,
                'Canonical plan must approve this full independent execution artifact and dataset slice')
        body = selection.to_dict()
        require(plan['spec']['source'] == body['source_scope']
                and plan['spec']['destination'] == body['destination_scope']
                and (execution.get('driver'), plan['spec']['route']['method']) in {
                    ('openstack-linux-rebuild/1', 'REBUILD_RESTORE'),
                    ('openstack-linux-application-cutover/1', 'REBUILD_RESTORE'),
                    ('openstack-linux-application-database/1', 'APPLICATION_NATIVE')}
                and plan['spec']['route']['guestProfile'] == body['guest_profile'],
                'Selected application data descriptors differ from the approved directional route')
        database_mapping = set()
        if execution.get('driver') == 'openstack-linux-application-database/1':
            from .postgresql_sync import PostgresqlSyncSelection
            require(isinstance(database_selection, PostgresqlSyncSelection)
                and execution_artifact.get('applicationDatabaseSelectionDigest') == database_selection.sha256,
                'Only the actual separately selected SQL descriptor may exclude a canonical database from file copy')
            database = database_selection.to_dict()
            require(database['datasetId'] not in {row['dataset_id'] for row in body['datasets']}
                and (database['source_scope'], database['target_scope']) ==
                    (body['source_scope'], body['destination_scope']),
                'A database dataset cannot be copied or accepted by a Restic child')
            database_mapping.add((database['datasetId'], database['targetRef'], database['consistencyGroupId']))
        else:
            require(database_selection is None and 'applicationDatabaseSelectionDigest' not in execution_artifact,
                'A file route cannot silently exclude database datasets')
        require({(row['dataset_id'], row['target_ref'], row['consistency_group_id'])
                 for row in body['datasets']} ==
                {(row['datasetId'], row['targetRef'], row['consistencyGroupId'])
                 for row in plan['spec']['datasetMappings']} - database_mapping,
                'Dataset slice must cover every selected canonical dataset mapping')
        self.job_id = job_id
        self.plan_bytes = encoded(plan)
        self.selection = selection
        self.ledger = private_path(ledger, directory=True)
        self.scope = dict(owner='application-datasets', job_id=job_id,
                          selection_sha256=selection.sha256,
                          plan_digest=plan['metadata']['planDigest'])

    def _row(self, dataset_id):
        rows = [row for row in self.selection.to_dict()['datasets'] if row['dataset_id'] == dataset_id]
        require(len(rows) == 1, 'Unknown or ambiguous selected dataset')
        return rows[0]

    def _child_scope(self, dataset_id):
        return {**self.scope, 'dataset_id': dataset_id}

    def _child_states(self, events, dataset_id):
        states = self._states(events)
        require(set(states) <= {dataset_id}, 'Dataset child journal contains a foreign child')
        return states

    def _bind(self, row, runtime, envelope):
        require(isinstance(runtime, DatasetWorkerRuntime), 'Trusted dataset worker runtime required')
        plan = strict_loads(self.plan_bytes)
        require(envelope.get('migration_plan') == plan,
                'Transfer envelope must contain this exact currently approved canonical plan')
        validate_transfer(envelope, row['source_config'], row['source_receipt'],
                          row['file_manifest'], row['target_root'])
        spec = envelope['transfer']['spec']
        require((spec['datasetId'], spec['targetRef'], spec['consistencyGroupId']) ==
                (row['dataset_id'], row['target_ref'], row['consistency_group_id'])
                and envelope['target_member'] == row['target_member']
                and runtime.resources.binding() == row['resources'],
                'Transfer envelope or runtime differs from the approved external dataset descriptor')
        scope = PlanScope.from_record(spec['destinationScope'])
        require((runtime.context.organization_id, runtime.context.tenant_id,
                 runtime.identity.organization_id, runtime.identity.tenant_id,
                 runtime.identity.subject, runtime.identity.site_id) ==
                (scope.organization_id, scope.tenant_id, scope.organization_id,
                 scope.tenant_id, runtime.lease.worker_id, scope.site_id),
                'Dataset worker runtime belongs to another tenant, owner or site')
        guard = TransferGuard(runtime.authority, runtime.credential, digest(encoded(envelope)),
                              runtime.grant_id, row['step_id'], row['operation_id'])
        grant = guard.check(envelope)
        require((runtime.lease_key, runtime.lease.epoch, runtime.lease.worker_id,
                 runtime.lease.organization_id, runtime.lease.tenant_id,
                 runtime.lease.security_domain_id) ==
                (grant.lease_key, grant.lease_epoch, grant.worker_subject,
                 scope.organization_id, scope.tenant_id, scope.security_domain_id),
                'Dataset runtime owner must be the original granted native owner epoch')
        require(runtime.lease.binding == NativeBinding(scope.platform_family, scope.endpoint_id,
                    scope.native_scope_id, 'dataset', row['target_ref'])
                and runtime.lease.workload_id == plan['spec']['workloadId'],
                'The granted dataset owner must bind the exact selected target and workload')
        runtime.resources.require_target(row['target_root'])
        return scope, guard

    @staticmethod
    def _states(events):
        states = {}
        for event in events:
            data = event['data']
            require(event['kind'] in {'DATASET_STARTED', 'DATASET_COMPLETED', 'DATASET_RECONCILED'}
                    and isinstance(data.get('dataset_id'), str), 'Invalid application dataset journal event')
            key = data['dataset_id']
            if event['kind'] == 'DATASET_STARTED':
                require(key not in states
                        and set(data) in ({'dataset_id', 'descriptor_sha256', 'envelope_sha256',
                                          'operation_directory', 'started_at'},
                                         {'dataset_id', 'descriptor_sha256', 'envelope_sha256',
                                          'operation_directory', 'started_at', 'original_intent'}),
                        'Dataset restore cannot be repeated or rebound')
                states[key] = dict(started=data, complete=None)
            else:
                require(key in states and states[key]['complete'] is None
                        and set(data) == {'dataset_id', 'result'},
                        'Orphan or repeated dataset completion')
                states[key]['complete'] = data['result']
        return states

    def _receipts(self, row, envelope, operation):
        restored = load_private(operation / 'receipt.json')
        proof = load_private(operation / 'transfer-receipt.json')
        require(load_private(operation / 'transfer-manifest.json') == envelope
                and proof == destination_receipt(envelope, row['source_receipt'], restored),
                'Retained destination proof does not bind this exact original source capture')
        useful = Path(row['target_root']) / row['source_config']['source'].lstrip('/')
        require(restic_run.manifest(useful) == row['file_manifest']['files'],
                'Current useful restored bytes differ from the approved capture')
        require(_metadata(useful) == row['target_metadata'],
                'Current restored ownership or modes differ from the approved dataset')
        return dict(transfer_manifest=envelope, transfer_receipt=proof, restore_receipt=restored)

    def execute_dataset(self, dataset_id, *, runtime, envelope, restore_authority,
                        command_authority=None):
        require(isinstance(runtime, DatasetWorkerRuntime), 'Trusted dataset worker runtime required')
        require(isinstance(command_authority, ApplicationCommandAuthority)
                and command_authority.admitted.job_id == self.job_id
                and command_authority.operation_kind == 'RESTORE_DATA'
                and command_authority.identity == runtime.identity
                and command_authority.selection_digest ==
                    strict_loads(self.plan_bytes)['spec']['execution']['artifactDigest'],
                'The native restore command authority must bind this exact admitted selection')
        row = self._row(dataset_id)
        scope, guard = self._bind(row, runtime, envelope)
        command_authority.require_admission(guard.check(envelope))
        with execution_journal.locked(self.ledger, self._child_scope(dataset_id)) as log:
            states = self._child_states(log.events, dataset_id)
            if dataset_id in states:
                raise ValueError('Dataset was attempted; reconcile original retained results without rerestore')
            operation = log.directory / ('dataset-' + digest(encoded(dataset_id))[:24])
            operation_digest = digest(encoded(dict(descriptor=row, envelope=envelope,
                                                  restore_authority=restore_authority)))
            runtime.registry.prepare(runtime.context, runtime.lease, scope,
                job_id=self.job_id, grant_id=runtime.grant_id, step_id=row['step_id'],
                lease_key=runtime.lease_key, worker_identity=runtime.identity,
                operation_id=row['operation_id'], operation_kind='RESTORE_DATA',
                request_digest=operation_digest)
            # Reserve the local attempt before the central claim. Either lost
            # acknowledgement remains held; neither step can lead to a resend.
            started = dict(dataset_id=dataset_id, descriptor_sha256=digest(encoded(row)),
                           envelope_sha256=digest(encoded(envelope)),
                           operation_directory=str(operation), started_at=execution_journal.c.now())
            started['original_intent'] = dict(organization_id=runtime.context.organization_id,
                tenant_id=runtime.context.tenant_id, operation_id=row['operation_id'], grant_id=runtime.grant_id,
                step_id=row['step_id'], lease_key=runtime.lease_key, binding=runtime.lease.binding.__dict__,
                workload_id=runtime.lease.workload_id, security_domain_id=runtime.lease.security_domain_id,
                worker_id=runtime.identity.subject, owner_epoch=runtime.lease.epoch,
                operation_kind='RESTORE_DATA', request_digest=operation_digest)
            log.append('DATASET_STARTED', started)
            require(runtime.registry.claim_once(runtime.context, runtime.lease, scope,
                                                row['operation_id'], runtime.identity),
                    'Native dataset intent was already claimed; read-only reconciliation required')
            clock = time.monotonic()
            try:
                execute_authorized_transfer(
                    authority_service=runtime.authority, worker_credential=runtime.credential,
                    expected_manifest_sha256=digest(encoded(envelope)), grant_id=runtime.grant_id,
                    step_id=row['step_id'], operation_id=row['operation_id'], transfer=envelope,
                    config=row['source_config'], credentials=runtime.credentials, binary=runtime.binary,
                    operation=operation, receipt=row['source_receipt'], expected=row['file_manifest'],
                    target=row['target_root'], restore_authority=restore_authority,
                    ca_file=runtime.ca_file, resource_control=runtime.resources,
                    command_authority=command_authority)
                records = self._receipts(row, envelope, operation)
                guard.check(envelope)
                runtime.resources.require_current()
                result = dict(format='hosting-application-phase-result/1', phase='INITIAL_TRANSFER',
                              job_id=self.job_id, member_id=dataset_id,
                              selection_sha256=self.selection.sha256,
                              plan_digest=strict_loads(self.plan_bytes)['metadata']['planDigest'],
                              original_intent=started['original_intent'],
                              status='DATASET_BYTES_AND_SELECTED_METADATA_VERIFIED',
                              records=records, measured_bytes=runtime.resources.limits.expected_bytes,
                              elapsed_seconds=round(time.monotonic() - clock, 6),
                              resource_binding=runtime.resources.binding(),
                              production_activation=False, application_acceptance=False,
                              native_intent_requires_independent_resolution=True)
                log.append('DATASET_COMPLETED', dict(dataset_id=dataset_id, result=result))
                return result
            except BaseException:
                # The central uncertainty write can itself lose acknowledgement.
                # The local STARTED record still prevents a repeated restore.
                try:
                    runtime.registry.mark_uncertain(runtime.context, row['operation_id'], runtime.identity.subject)
                except Exception:
                    pass
                raise

    def reconcile_dataset(self, dataset_id, *, runtime, envelope):
        """Accept only original retained receipts and current useful bytes.

        No repository command or native mutation occurs. Native intent resolution
        still needs the existing independent registry observer/reviewer path.
        """
        row = self._row(dataset_id)
        _scope, guard = self._bind(row, runtime, envelope)
        with execution_journal.locked(self.ledger, self._child_scope(dataset_id)) as log:
            states = self._child_states(log.events, dataset_id)
            require(dataset_id in states, 'No original dataset attempt exists')
            started = states[dataset_id]['started']
            require(started['descriptor_sha256'] == digest(encoded(row))
                    and started['envelope_sha256'] == digest(encoded(envelope)),
                    'Original dataset attempt is bound to another mapping or grant')
            operation = Path(started['operation_directory'])
            require(operation == log.directory / ('dataset-' + digest(encoded(dataset_id))[:24]),
                    'Retained operation directory differs from the original attempt')
            records = self._receipts(row, envelope, operation)
            guard.check(envelope)
            runtime.resources.require_current()
            prior = states[dataset_id]['complete']
            if prior is not None:
                require(prior['records'] == records,
                        'Current dataset receipts differ from the immutable completed checkpoint')
                return prior
            result = dict(status='DATASET_BYTES_AND_SELECTED_METADATA_VERIFIED', records=records,
                          measured_bytes=runtime.resources.limits.expected_bytes,
                          elapsed_seconds=None, resource_binding=runtime.resources.binding(),
                          production_activation=False, application_acceptance=False,
                          native_intent_requires_independent_resolution=True)
            if 'original_intent' in started:
                result.update(format='hosting-application-phase-result/1', phase='INITIAL_TRANSFER',
                    job_id=self.job_id, member_id=dataset_id, selection_sha256=self.selection.sha256,
                    plan_digest=strict_loads(self.plan_bytes)['metadata']['planDigest'],
                    original_intent=started['original_intent'])
            log.append('DATASET_RECONCILED', dict(dataset_id=dataset_id, result=result))
            return result

    def inspect(self):
        """Saved progress is historical evidence; it supplies no effect authority."""
        rows = self.selection.to_dict()['datasets']
        projection = []
        for row in rows:
            dataset_id = row['dataset_id']
            with execution_journal.locked(self.ledger, self._child_scope(dataset_id)) as log:
                states = self._child_states(log.events, dataset_id)
                projection.append(dict(dataset_id=dataset_id,
                    status='NOT_STARTED' if dataset_id not in states else
                    'VERIFIED_REQUIRES_CURRENT_READBACK' if states[dataset_id]['complete'] is not None else
                    'OUTCOME_UNKNOWN_RECONCILE_ORIGINAL'))
        return dict(format='hosting-application-dataset-progress/1', job_id=self.job_id,
                    selection_sha256=self.selection.sha256, datasets=projection,
                    production_activation=False, native_qualification=False)

    def join(self):
        """Join every immutable completed child; never infer app acceptance."""
        rows = self.selection.to_dict()['datasets']
        groups = {}
        for row in rows:
            dataset_id = row['dataset_id']
            with execution_journal.locked(self.ledger, self._child_scope(dataset_id)) as log:
                states = self._child_states(log.events, dataset_id)
                require(dataset_id in states and states[dataset_id]['complete'] is not None,
                    'Every selected dataset must complete before the application data join')
                state = states[dataset_id]
                result = state['complete']
                require(result['measured_bytes'] == row['resources']['limits']['expected_bytes']
                        and result['resource_binding'] == row['resources']
                        and result['production_activation'] is result['application_acceptance'] is False,
                        'Dataset checkpoint does not bind approved bytes, limits and absent activation')
                record = result['records']
                current = self._receipts(row, record['transfer_manifest'],
                                         Path(state['started']['operation_directory']))
                require(current == record, 'Current retained dataset records differ')
                groups.setdefault(row['consistency_group_id'], []).append((row, record))
        joined = []
        for group_id, children in sorted(groups.items()):
            descriptors = [dict(step_id=row['step_id'], dataset_id=row['dataset_id'],
                                target_ref=row['target_ref'],
                                transfer_manifest_sha256=digest(encoded(record['transfer_manifest'])))
                           for row, record in children]
            result = dataset_acceptance.validate_group(
                group_id, descriptors, {row['step_id']: record for row, record in children},
                children[0][1]['transfer_manifest']['destination_execution_scope'])
            joined.append(dict(group_result=result, migration_plan=strict_loads(self.plan_bytes)))
        return dataset_acceptance.validate_coverage(joined, joined[0]['group_result']['scope'])
