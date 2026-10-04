"""Retain real target identities before a separately approved cutover admission.

The initial creation plan cannot contain an observation of a future resource.
This fixed owner uses the actual creation registry and independent native
readback owner to append TARGET histories. It performs no guest data transfer,
source fence, production activation or native mutation.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path
import re

from provisioner.allocations.transactions import ResourceBundle
from provisioner.controlplane.authority import PlanScope
from provisioner.controlplane.persistence import (AuditContext, EnterpriseRecordStore,
    TenantContext, canonical_record_digest, RevisionConflict)
from provisioner.controlplane.reconciliation.adapters.openstack_readback import OpenStackNativeReadbackOwner
from provisioner.controlplane.reconciliation.planned import (NativeCreationObservation,
    PlannedNativeCreationRegistry, PlannedResourceLease)
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
from provisioner.domain.enterprise_records import validate_record, validate_workload_successor
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import encoded, load_private, private_path, require, write_new
from .promotion import binding_key

FORMAT = 'hosting-application-staged-handover/1'
_HASH = re.compile('[0-9a-f]{64}')
_FIELDS = {'format', 'originalAdmitted', 'originalArtifactDigest', 'originalResourceBundleDigest',
    'creationOperationId', 'creationObservationDigest', 'stagedWorkloadRevision', 'stagedWorkloadDigest',
    'targetSnapshotId', 'targetSnapshotDigest', 'associations', 'destinationScope', 'restoredDatasetReceipts'}


@dataclass(frozen=True)
class ApplicationStagedHandover:
    canonical: bytes

    def __post_init__(self):
        require(isinstance(self.canonical, bytes) and len(self.canonical) <= 1024 * 1024,
            'A bounded immutable real-target application handover is required')
        body = strict_loads(self.canonical)
        require(isinstance(body, dict) and set(body) == _FIELDS and encoded(body) == self.canonical
            and body['format'] == FORMAT and body['restoredDatasetReceipts'] == [],
            'Target staging cannot claim restored application data')
        admitted = AdmittedInput(**body['originalAdmitted'])
        destination = PlanScope.from_record(body['destinationScope'])
        require((admitted.organization_id, admitted.tenant_id) ==
            (destination.organization_id, destination.tenant_id)
            and type(body['stagedWorkloadRevision']) is int and body['stagedWorkloadRevision'] > 1
            and all(isinstance(body[name], str) and _HASH.fullmatch(body[name]) for name in
                ('originalArtifactDigest', 'originalResourceBundleDigest', 'creationObservationDigest',
                 'stagedWorkloadDigest', 'targetSnapshotDigest'))
            and isinstance(body['associations'], list) and 1 <= len(body['associations']) <= 32,
            'The exact original job, scoped observation and canonical target revision are required')
        known = set()
        for member in body['associations']:
            require(isinstance(member, dict) and set(member) ==
                {'machineId', 'sourceBinding', 'targetBinding', 'disks', 'nics'}
                and member['machineId'] not in known, 'A staged application member is missing or duplicated')
            known.add(member['machineId'])
            for kind, rows, key in (('vm', [member], 'machineId'),
                    ('disk', member['disks'], 'diskId'), ('nic', member['nics'], 'nicId')):
                require(isinstance(rows, list) and rows and len({row[key] for row in rows}) == len(rows),
                    'Complete nonduplicate staged VM/disk/NIC mappings required')
                for row in rows:
                    target = row['targetBinding']
                    require(target['resourceKind'] == kind and all(target[field] == body['destinationScope'][field]
                        for field in ('endpointId', 'nativeScopeId', 'platformFamily')),
                        'A staged target identity escapes its actual native destination')
                    binding_key(target)

    @classmethod
    def from_record(cls, body):
        return cls(encoded(body))

    def to_dict(self):
        return strict_loads(self.canonical)

    @property
    def sha256(self):
        return canonical_record_digest(self.to_dict())


def staged_workload(previous, plan, associations, snapshot_id):
    """Append complete observed TARGET histories, preserving original sources."""
    require(not validate_record(previous) and not validate_record(plan), 'Valid canonical original records required')
    machines = {member['machineId']: member for member in previous['spec']['machines']}
    mapped = {member['machineId']: member for member in plan['spec']['machineMappings']}
    require({member['machineId'] for member in associations} == set(machines) == set(mapped),
        'Staging must associate the complete selected application')
    current = deepcopy(previous); current['metadata']['revision'] += 1
    targets = {member['machineId']: member for member in current['spec']['machines']}
    native = set()
    for member in associations:
        machine = targets[member['machineId']]
        require(member['sourceBinding'] == mapped[member['machineId']]['sourceBinding']
            and machine['disksComplete'] and machine['nicsComplete'],
            'Staging association changed its source or omitted native components')
        for kind, rows, key, selected in (('vm', [machine], 'machineId', [member]),
                ('disk', machine['disks'], 'diskId', member['disks']),
                ('nic', machine['nics'], 'nicId', member['nics'])):
            require({row[key] for row in rows} == {row[key] for row in selected},
                'A source disk or NIC has no exact observed target association')
            lookup = {row[key]: row['targetBinding'] for row in selected}
            for row in rows:
                target = lookup[row[key]]; identity = binding_key(target)
                require(target['resourceKind'] == kind and identity not in native
                    and all(target[field] == plan['spec']['destination'][field]
                        for field in ('endpointId', 'nativeScopeId', 'platformFamily'))
                    and not any(history['role'] == 'TARGET' or binding_key(history['binding']) == identity
                        for history in row['bindings']),
                    'A target native identity is shared, already staged or outside its approved scope')
                native.add(identity)
                row['bindings'].append(dict(binding=deepcopy(target), role='TARGET',
                    firstSeenSnapshotId=snapshot_id, lastObservedSnapshotId=snapshot_id))
    require(not validate_workload_successor(previous, current), 'Invalid canonical staged-target association')
    return current


@dataclass(frozen=True)
class ApplicationStagingRuntime:
    records: EnterpriseRecordStore
    authority: PostgresExecutionAuthority
    creation_registry: PlannedNativeCreationRegistry
    native_reader: OpenStackNativeReadbackOwner
    lease: PlannedResourceLease
    observation: NativeCreationObservation
    bundle: ResourceBundle
    associations: bytes
    directory: Path
    prepared_directory: Path

    def __post_init__(self):
        require(isinstance(self.records, EnterpriseRecordStore) and isinstance(self.authority, PostgresExecutionAuthority)
            and isinstance(self.creation_registry, PlannedNativeCreationRegistry)
            and type(self.native_reader) is OpenStackNativeReadbackOwner
            and self.creation_registry._evidence is self.native_reader
            and isinstance(self.lease, PlannedResourceLease) and isinstance(self.observation, NativeCreationObservation)
            and isinstance(self.bundle, ResourceBundle) and isinstance(self.associations, bytes)
            and encoded(strict_loads(self.associations)) == self.associations
            and self.records._connect is self.creation_registry._connect
            and self.lease.job_id == self.bundle.admitted.job_id
            and self.lease.selection_digest == self.bundle.selection_digest,
            'Concrete original creation, actual independent native reader and complete protected associations required')
        object.__setattr__(self, 'directory', private_path(self.directory, directory=True))
        object.__setattr__(self, 'prepared_directory', private_path(self.prepared_directory, directory=True))

    @property
    def registry(self):
        return self.creation_registry

    def _native(self, admitted, selection):
        require(admitted == self.bundle.admitted
            and canonical_record_digest(selection) == self.bundle.selection_digest,
            'Staging must retain its exact original admitted resource request')
        context = TenantContext(admitted.organization_id, admitted.tenant_id)
        custody = load_private(self.native_reader.directory / (self.observation.observation.evidence_digest + '.json'))
        require(canonical_record_digest(custody) == self.observation.observation.evidence_digest
            and custody['job_id'] == admitted.job_id and custody['selection_digest'] == self.bundle.selection_digest
            and custody['bundle_digest'] == self.bundle.digest,
            'Creation custody differs from the exact original selected application')
        fresh = self.native_reader.observe_creation(context, self.lease, custody['operation_id'],
                                                    self.bundle, self.prepared_directory)
        bindings = self.creation_registry.reconcile_observed(context, custody['operation_id'], fresh)
        fresh_custody = load_private(self.native_reader.directory / (fresh.observation.evidence_digest + '.json'))
        require(bindings == self.observation.bindings
            and fresh_custody['outputs'] == custody['outputs'],
            'A target native identity changed after original creation')
        return fresh_custody, fresh_custody['facts']

    def observation_operation_id(self):
        custody = load_private(self.native_reader.directory / (self.observation.observation.evidence_digest + '.json'))
        return custody['operation_id']

    def associate(self, admitted, selection):
        path = self.directory / (admitted.job_id + '.json')
        if path.exists():
            handover = ApplicationStagedHandover(encoded(load_private(path)))
            self.verify(handover)
            return handover
        plan, original = self.authority.require_current(admitted, canonical_record_digest(selection), 'DISCOVER_READ')
        require(original == selection and plan['spec'].get('applicationStaging') ==
            {'format': 'hosting-application-staging-plan/1'}, 'A separately selected target-staging purpose is required')
        custody, facts = self._native(admitted, selection)
        associations = strict_loads(self.associations)
        actual = {('vm', row['server']['id']) for row in facts.values()} | \
                 {('disk', volume['id']) for row in facts.values() for volume in row['volumes']} | \
                 {('nic', row['port']['id']) for row in facts.values()}
        selected = {(kind, row['targetBinding']['nativeId']) for member in associations
            for kind, rows in (('vm', [member]), ('disk', member['disks']), ('nic', member['nics'])) for row in rows}
        require(selected == actual and len(selected) == sum(1 + len(member['disks']) + len(member['nics'])
            for member in associations), 'Target associations must cover exactly the actual created native resources')
        snapshot_id = 'application-target-' + canonical_record_digest(dict(associations=associations,
            creation_observation=self.observation.observation.evidence_digest))[:32]
        native_by_id = {('vm', row['server']['id']): row['server'] for row in facts.values()} | \
            {('disk', volume['id']): volume for row in facts.values() for volume in row['volumes']} | \
            {('nic', row['port']['id']): row['port'] for row in facts.values()}
        from provisioner.execution.readback_core import timestamp
        at = timestamp(custody['observed_at'])
        snapshot = dict(apiVersion='hosting.platform/v1', kind='ObservationSnapshot', metadata=dict(
            organizationId=admitted.organization_id, tenantId=admitted.tenant_id, snapshotId=snapshot_id,
            capturedAt=at.isoformat(), expiresAt=(at + timedelta(minutes=5)).isoformat()), spec=dict(
                endpointId=plan['spec']['destination']['endpointId'], readScopes=[self.lease.scope.native_scope_id],
                completeness='COMPLETE', privileges=['vm.read', 'volume.read', 'port.read'],
                objects=[dict(binding=row['targetBinding'], presence='PRESENT', revisionToken={
                    'state': 'UNKNOWN', 'reason': 'Native read API supplies no complete optimistic revision token'},
                    facts=[dict(field='nativeReadbackDigest', state='OBSERVED',
                        value=canonical_record_digest(native_by_id[(kind, row['targetBinding']['nativeId'])]))],
                    missingFields=[]) for member in associations for kind, rows in
                        (('vm', [member]), ('disk', member['disks']), ('nic', member['nics'])) for row in rows],
                collectionErrors=[], missingFields=[]))
        require(not validate_record(snapshot), 'The actual target observation could not form a canonical snapshot')
        context = TenantContext(admitted.organization_id, admitted.tenant_id)
        audit = AuditContext(self.native_reader.enrollment.subject, admitted.job_id)
        try:
            retained = self.records.create(context, snapshot, audit)
        except RevisionConflict:
            retained = self.records.get(context, 'ObservationSnapshot', snapshot_id)
            require(retained is not None and retained.record['spec'] == snapshot['spec'],
                'A retained target snapshot differs from its original native observation')
        with self.records._session(context) as connection, connection.cursor() as cursor:
            self.authority.require_canonical_transition(admitted, canonical_record_digest(selection),
                cursor=cursor, operation_kind='DISCOVER_READ')
            stored = self.records._load(connection, context, 'Workload', plan['spec']['workloadId'], lock=True)
            require(stored is not None and stored.revision == plan['spec']['workloadRevision'],
                'The original canonical application changed before target association')
            current = staged_workload(stored.record, plan, associations, snapshot_id)
            result = self.records.update_in_transaction(connection, context, current, stored.revision, audit)
        handover = ApplicationStagedHandover.from_record(dict(format=FORMAT, originalAdmitted=asdict(admitted),
            originalArtifactDigest=canonical_record_digest(selection), originalResourceBundleDigest=self.bundle.digest,
            creationOperationId=custody['operation_id'], creationObservationDigest=self.observation.observation.evidence_digest,
            stagedWorkloadRevision=result.revision, stagedWorkloadDigest=result.digest,
            targetSnapshotId=snapshot_id, targetSnapshotDigest=retained.digest,
            associations=associations, destinationScope=plan['spec']['destination'], restoredDatasetReceipts=[]))
        write_new(path, handover.canonical)
        return handover

    def verify(self, handover):
        require(isinstance(handover, ApplicationStagedHandover), 'Original typed target handover required')
        body = handover.to_dict(); admitted = AdmittedInput(**body['originalAdmitted'])
        _plan, artifact = self.authority.require_observation(admitted, body['originalArtifactDigest'], 'DISCOVER_READ')
        self._native(admitted, artifact)
        context = TenantContext(admitted.organization_id, admitted.tenant_id)
        workload = self.records.get(context, 'Workload', self.lease.workload_id)
        snapshot = self.records.get(context, 'ObservationSnapshot', body['targetSnapshotId'])
        require(body['associations'] == strict_loads(self.associations)
            and body['creationObservationDigest'] == self.observation.observation.evidence_digest
            and workload is not None and (workload.revision, workload.digest) ==
                (body['stagedWorkloadRevision'], body['stagedWorkloadDigest'])
            and snapshot is not None and snapshot.digest == body['targetSnapshotDigest'],
            'The retained canonical staged target or original observation changed')
        return body
