"""Authenticated exact-byte import into the existing canonical/native owners.

Only the bounded legacy contracts actually parsed by rehearsal are imported.
All original starts remain historical/no-replay facts. New ownership stays
unleased and observation-only until the separate scoped handover transaction.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from provisioner.controlplane.evidence.gate import EvidenceMutationGate
from provisioner.controlplane.jobs.repository import _json, _tenant
from provisioner.controlplane.persistence import AuditContext, TenantContext
from provisioner.controlplane.persistence.store import EnterpriseRecordStore, NativeBinding, _encode
from provisioner.domain.enterprise_records import validate_record, validate_workload_successor
from provisioner.execution import readback_core as c
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import digest, encoded, read_private, require
from .originals import RetainedOriginalStore
from .proofs import ConversionProofs, require_independent, scope_digest
from .rehearsal import Snapshot, _legacy, _manifest, reconcile

FORMAT = 'hosting-retained-state-import/1'
RECOVERY_HOLDS = frozenset({'HOLD_UNCERTAIN_NATIVE_START_REQUIRES_CANONICAL_RECOVERY',
    'HOLD_MIXED_OR_UNCERTAIN_LEDGER_REQUIRES_RECONCILIATION',
    'HOLD_UNCERTAIN_DELIVERY_STEP_REQUIRES_CANONICAL_RECOVERY', 'HOLD_INCOMPLETE_DELIVERY'})


@dataclass(frozen=True)
class ImportReceipt:
    batch_id: str
    manifest_digest: str
    imported: bool
    history_count: int
    file_count: int
    native_count: int
    recovery_count: int
    service_mode: str = 'OBSERVATION_ONLY'
    retry_authorized: bool = False


@dataclass(frozen=True)
class PreparedSource:
    raw_manifest: bytes
    value: dict
    snapshot: Snapshot
    history: list[dict]
    report: dict
    projection: dict
    recoveries: list[dict]
    archive_rows: list[dict]
    batch_digest: str
    projection_digest: str
    archive_digest: str
    epochs: list[dict]

    def proposal(self):
        inventory = self.value['inventory']
        return {'format':'hosting-retained-conversion-proposal/1','batchId':inventory['batchId'],
            'scope':inventory['scope'],'scopeDigest':scope_digest(inventory['scope']),
            'manifestDigest':self.batch_digest,'serviceMode':'OBSERVATION_ONLY',
            'writesAuthorized':False,'retryAuthorized':False,'recovery':self.recoveries,
            'importStatement':{'projectionDigest':self.projection_digest,'archiveInventoryDigest':self.archive_digest,
                'sourceCounts':inventory['sourceCounts'],'workloadDigest':_encode(self.history[-1])[1],
                'canonicalHistoryCount':len(self.history),'nativeEpochs':self.epochs},
            'custodyStatement':{'originalManifestSha256':self.batch_digest,'archiveInventoryDigest':self.archive_digest,
                'sourceCounts':inventory['sourceCounts'],'sourceBoundary':{'database':self.value['sourceDatabaseBoundary'],
                    'workflow':self.value['sourceWorkflowBoundary']}}}


def _boundary(value: dict, kind: str):
    c.exact_keys(value, {'format', 'mode', 'recordCount', 'snapshotDigest',
                         'auditSequence', 'auditHeadHash', 'evidenceSequence', 'evidenceHeadHash'})
    require(value['format'] == 'hosting-retained-' + kind + '-boundary/1' and
            value['mode'] in {'NOT_DEPLOYED', 'CANONICAL_FILES'}, 'Explicit supported retained boundary required')
    for name in ('recordCount', 'auditSequence', 'evidenceSequence'):
        require(type(value[name]) is int and value[name] >= 0, 'Exact retained high-water/count required')
    for name in ('snapshotDigest', 'auditHeadHash', 'evidenceHeadHash'):
        require(isinstance(value[name], str) and c.HEX.fullmatch(value[name]), 'Retained high-water digest required')
    if value['mode'] == 'NOT_DEPLOYED':
        require(all(value[name] == 0 for name in ('recordCount', 'auditSequence', 'evidenceSequence'))
                and all(value[name] == '0' * 64 for name in
                        ('snapshotDigest', 'auditHeadHash', 'evidenceHeadHash')),
                'Explicit absence must have independently attested zero boundaries')
    else:
        require(value['snapshotDigest'] != '0' * 64 and value['recordCount'] > 0,
                'A deployed source boundary cannot omit its exact retained records')


def manifest(value, *, as_of):
    c.exact_keys(value, {'format', 'inventory', 'workloadHistoryFiles',
                         'sourceDatabaseBoundary', 'sourceWorkflowBoundary'})
    require(value['format'] == FORMAT, 'Unsupported authenticated retained import version')
    _manifest(value['inventory'], as_of)
    files = value['workloadHistoryFiles']
    require(isinstance(files, list) and len(files) < 10000 and len(set(files)) == len(files),
            'Explicit unique retained workload history files required')
    require(not set(files) & set(value['inventory']['workloadFiles']), 'Current workload is duplicated in history')
    _boundary(value['sourceDatabaseBoundary'], 'postgres')
    _boundary(value['sourceWorkflowBoundary'], 'workflow')
    # Temporal database histories have a different owner. This concrete profile
    # never fabricates their namespace/run IDs from Terraform generations.
    require(value['sourceWorkflowBoundary']['mode'] == 'NOT_DEPLOYED',
            'Existing Temporal histories require their original workflow export owner')


def canonical_history(snapshot, value):
    inventory, history = value['inventory'], []
    require(len(inventory['workloadFiles']) == 1, 'One exact current workload required')
    names = [*value['workloadHistoryFiles'], *inventory['workloadFiles']]
    scope = inventory['scope']
    for name in names:
        record = snapshot.json(name)
        require(not validate_record(record) and record['kind'] == 'Workload', 'Canonical workload history is invalid')
        meta = record['metadata']
        require((meta['organizationId'], meta['tenantId'], meta['wsdId'], meta['workloadId']) ==
                (scope['organizationId'], scope['tenantId'], scope['securityDomainId'], scope['workloadId']),
                'Retained canonical history belongs to another exact workload scope')
        history.append(record)
    history.sort(key=lambda record: record['metadata']['revision'])
    require([record['metadata']['revision'] for record in history] == list(range(1, len(history) + 1)),
            'Full contiguous retained canonical history is required; never reset a revision')
    require(history[-1] == snapshot.json(inventory['workloadFiles'][0]), 'Current retained workload is not the history head')
    for previous, successor in zip(history, history[1:]):
        require(not validate_workload_successor(previous, successor),
                'Retained WSD/cutover transitions require their original verified authority')
    boundary = value['sourceDatabaseBoundary']
    if boundary['mode'] == 'CANONICAL_FILES':
        require(boundary['recordCount'] == len(history) and boundary['snapshotDigest'] ==
                digest(encoded({name: digest(snapshot.raw[name]) for name in sorted(names)})),
                'Retained PostgreSQL canonical export counts/digest differ')
    return history


def recovery_rows(snapshot, inventory, projection):
    rows = []
    starts = {}
    for directory in inventory['terraformLedgers']:
        for name in snapshot.files_under(directory):
            if name.endswith('.started.json'):
                start = snapshot.json(name)
                starts[(start['operation_id'], start['generation'])] = digest(snapshot.raw[name])
    for attempt in projection['attempts']:
        identity = (attempt['operationId'], attempt['generation'])
        require(identity in starts, 'Original start record is missing')
        rows.append({'operationId': identity[0], 'generation': identity[1],
            'format': 'hosting-terraform-attempt/1', 'originDigest': starts[identity], 'outcome': attempt['outcome']})
    from provisioner.execution.execution_journal import FORMAT as JOURNAL_FORMAT, Journal
    for directory in inventory['deliveryJournals']:
        log = Journal(snapshot.root / directory, {'owner': 'delivery', **_legacy(inventory['scope'], phase=False)})
        active, step_rows = None, {}
        for event in log.events:
            if event['kind'] == 'DELIVERY_STARTED':
                active, step_rows = event['data']['plan'], {}
            elif event['kind'] == 'STEP_STARTED':
                identity = 'legacy-delivery:' + digest(encoded({'operation': active['operation_id'],
                    'generation': active['generation'], 'step': event['data']['step_id']}))
                row = {'operationId': identity, 'generation': active['generation'],
                    'format': JOURNAL_FORMAT, 'originDigest': digest(encoded(event)), 'outcome': 'UNKNOWN'}
                rows.append(row)
                step_rows[event['data']['step_id']] = row
            elif event['kind'] == 'STEP_COMPLETED':
                step_rows[event['data']['step_id']]['outcome'] = 'LEGACY_STEP_COMPLETED'
    require(len({(row['operationId'], row['generation']) for row in rows}) == len(rows),
            'Duplicate original native/recovery operation')
    return sorted(rows, key=lambda row: (row['operationId'], row['generation']))


def native_statement(value, bindings, recoveries, *, native_digest, state_digest=None, handover=False):
    c.exact_keys(value, {'complete', 'bindings', 'tasks', 'retainedNativeDigest', 'reconciliationDigest'})
    require(value['complete'] is True and value['retainedNativeDigest'] == native_digest and
            value['reconciliationDigest'] == state_digest, 'Current native readback does not bind the original inventory/state')
    require(isinstance(value['bindings'], list), 'Complete original-native readback required')
    observed = {}
    for row in value['bindings']:
        c.exact_keys(row, {'binding', 'lifecycleStage'})
        require(row['lifecycleStage'] in {'prepared', 'bootstrap'}, 'Native lifecycle stage is unobserved')
        binding = NativeBinding.from_record(row['binding'])
        require(binding.key() not in observed, 'Duplicate native readback identity')
        observed[binding.key()] = row
    require(set(observed) == {NativeBinding.from_record(row).key() for row in bindings},
            'Current native identities differ from the exact retained inventory')
    require(isinstance(value['tasks'], list), 'Explicit original native-task inventory required')
    tasks = {}
    for task in value['tasks']:
        c.exact_keys(task, {'operationId', 'generation', 'outcome', 'nativeQuiesced', 'nativeTaskIds'})
        c.identifier(task['operationId'])
        require(type(task['generation']) is int and task['generation'] > 0 and type(task['nativeQuiesced']) is bool
                and task['outcome'] in {'UNKNOWN', 'IN_PROGRESS', 'NO_EFFECT', 'EFFECT_PRESENT'}
                and isinstance(task['nativeTaskIds'], list) and len(task['nativeTaskIds']) <= 10000
                and len(set(task['nativeTaskIds'])) == len(task['nativeTaskIds']), 'Native task disposition is ambiguous')
        for identity in task['nativeTaskIds']:
            c.text(identity, length=512)
        key = (task['operationId'], task['generation'])
        require(key not in tasks, 'Duplicate original native-task disposition')
        tasks[key] = task
        if handover:
            require(task['nativeQuiesced'] is True and task['outcome'] in {'NO_EFFECT', 'EFFECT_PRESENT'},
                    'Unknown/active original native task keeps handover held')
    require(set(tasks) == {(row['operationId'], row['generation']) for row in recoveries},
            'Original native task count/identity differs; no missing-start default')


def prepare_source(manifest_path: Path, source_root: Path, *, as_of) -> PreparedSource:
    """Validate/describe originals; the returned proposal has no authority."""
    raw_manifest=read_private(manifest_path)
    value=strict_loads(raw_manifest)
    manifest(value,as_of=as_of)
    inventory=value['inventory']
    snapshot=Snapshot(source_root,inventory)
    history=canonical_history(snapshot,value)
    report,projection=reconcile(snapshot,inventory,as_of=as_of)
    require(set(report['holds'])<=RECOVERY_HOLDS,'Unrecognized, mismatched or unsupported retained state remains held')
    recoveries=recovery_rows(snapshot,inventory,projection)
    projection={**projection,'canonicalHistoryDigests':[_encode(record)[1] for record in history],'recovery':recoveries}
    archive_rows=[{'path':name,'sha256':digest(raw),'bytes':len(raw)} for name,raw in sorted(snapshot.raw.items())]
    batch_digest=digest(raw_manifest)
    archive_digest=digest(encoded({'manifestSha256':batch_digest,'files':archive_rows}))
    native=snapshot.json(inventory['evidence']['nativeInventory'])
    source_epoch=report['maximumOldWriterEpoch']
    epochs=[{'binding':row['binding'],'sourceEpoch':source_epoch,'targetEpoch':source_epoch+1}
        for row in sorted(native['bindings'],key=lambda row:NativeBinding.from_record(row['binding']).key())]
    snapshot.recheck()
    return PreparedSource(raw_manifest,value,snapshot,history,report,projection,recoveries,
        archive_rows,batch_digest,digest(encoded(projection)),archive_digest,epochs)


class RetainedStateImporter:
    def __init__(self, connect, *, proofs: ConversionProofs, originals: RetainedOriginalStore,
                 evidence_gate: EvidenceMutationGate):
        if (not callable(connect) or not isinstance(proofs, ConversionProofs)
                or not isinstance(originals, RetainedOriginalStore)
                or not isinstance(evidence_gate, EvidenceMutationGate)):
            raise TypeError('Current database, independent proof and protected originals owners required')
        self._connect, self.proofs, self.originals, self.evidence = connect, proofs, originals, evidence_gate

    def import_batch(self, manifest_path: Path, source_root: Path, *, proof_events: dict[str, str]) -> ImportReceipt:
        raw_manifest = read_private(manifest_path)
        value = strict_loads(raw_manifest)
        inventory = value['inventory']
        scope, batch = inventory['scope'], inventory['batchId']
        context = TenantContext(scope['organizationId'], scope['tenantId'])
        batch_digest = digest(raw_manifest)
        self.evidence.require(context)
        with self._connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, context)
            cursor.execute('SELECT clock_timestamp()')
            now = cursor.fetchone()[0]
            prepared=prepare_source(manifest_path,source_root,as_of=now)
            require(prepared.raw_manifest==raw_manifest,'Original import manifest changed while preparing')
            snapshot,history,report,recoveries=prepared.snapshot,prepared.history,prepared.report,prepared.recoveries
            projection_digest,archive_rows,archive_digest=prepared.projection_digest,prepared.archive_rows,prepared.archive_digest
            c.exact_keys(proof_events, {'IMPORT', 'CUSTODY', 'NATIVE', 'EXCLUSION'})
            proofs = {purpose: self.proofs.verify(cursor, context, scope, event_key=event,
                batch_id=batch, manifest_digest=batch_digest, purpose=purpose)
                for purpose, event in proof_events.items()}
            require_independent(list(proofs.values()))
            boundary = {'database': value['sourceDatabaseBoundary'], 'workflow': value['sourceWorkflowBoundary']}
            custody = proofs['CUSTODY'].statement
            c.exact_keys(custody, {'originalManifestSha256', 'archiveInventoryDigest', 'sourceBoundary', 'sourceCounts'})
            require(custody == {'originalManifestSha256': batch_digest, 'archiveInventoryDigest': archive_digest,
                'sourceBoundary': boundary, 'sourceCounts': inventory['sourceCounts']},
                'Independent originals custody, source counts or high-water marks differ')
            original_native = snapshot.json(inventory['evidence']['nativeInventory'])
            bindings = [row['binding'] for row in original_native['bindings']]
            native_digest = inventory['sourceFileSha256'][inventory['evidence']['nativeInventory']]
            native_statement(proofs['NATIVE'].statement, bindings, recoveries, native_digest=native_digest)
            exclusion = proofs['EXCLUSION'].statement
            freeze = snapshot.json(inventory['evidence']['oldWriterFreeze'])
            c.exact_keys(exclusion, {'oldWriters', 'allExcluded', 'queuedRequestsExcluded',
                                   'nativeTasksQuiesced', 'retainedFreezeDigest', 'reconciliationDigest'})
            require(exclusion['oldWriters'] == freeze['oldWriters'] and exclusion['allExcluded'] is True
                    and exclusion['queuedRequestsExcluded'] is True and type(exclusion['nativeTasksQuiesced']) is bool
                    and exclusion['reconciliationDigest'] is None and exclusion['retainedFreezeDigest'] ==
                    inventory['sourceFileSha256'][inventory['evidence']['oldWriterFreeze']],
                    'Actual original writers/queued requests have not been independently excluded')
            source_epoch = report['maximumOldWriterEpoch']
            epochs = prepared.epochs
            authority = proofs['IMPORT'].statement
            c.exact_keys(authority, {'projectionDigest', 'archiveInventoryDigest', 'sourceCounts',
                                     'workloadDigest', 'canonicalHistoryCount', 'nativeEpochs'})
            require(authority == {'projectionDigest': projection_digest, 'archiveInventoryDigest': archive_digest,
                'sourceCounts': inventory['sourceCounts'], 'workloadDigest': _encode(history[-1])[1],
                'canonicalHistoryCount': len(history), 'nativeEpochs': epochs},
                'Import authority covers another exact history/projection/epoch boundary')
            # Retain every byte (including empty locks and private credentials)
            # outside sanitized evidence before entering the canonical import.
            self.originals.retain(batch_digest, raw_manifest)
            for name, raw in snapshot.raw.items():
                self.originals.retain(digest(raw), raw)
            snapshot.recheck()
            cursor.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,31))',
                (digest(encoded({'organizationId':context.organization_id,
                    'tenantId':context.tenant_id,'workloadId':scope['workloadId']})),))
            cursor.execute('SELECT manifest_digest FROM hosting_controlplane.retained_conversion_batches '
                'WHERE organization_id=%s AND tenant_id=%s AND batch_id=%s',
                (context.organization_id, context.tenant_id, batch))
            existing = cursor.fetchone()
            if existing is not None:
                require(existing[0] == batch_digest, 'One-time import batch identity conflicts')
                self._compare_import(cursor, context, batch, history, archive_rows, recoveries, epochs)
                return ImportReceipt(batch, batch_digest, False, len(history), len(archive_rows), len(bindings), len(recoveries))
            cursor.execute('INSERT INTO hosting_controlplane.retained_conversion_batches '
                '(organization_id,tenant_id,batch_id,security_domain_id,workload_id,scope_digest,scope,'
                'manifest_digest,archive_inventory_digest,projection_digest,workload_digest,workload_revision,'
                'history_count,source_counts,source_boundary,import_proof,custody_proof,native_proof,exclusion_proof) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s)',
                (context.organization_id,context.tenant_id,batch,scope['securityDomainId'],scope['workloadId'],
                 scope_digest(scope),encoded(scope).decode(),batch_digest,archive_digest,projection_digest,
                 _encode(history[-1])[1],history[-1]['metadata']['revision'],len(history),
                 encoded(inventory['sourceCounts']).decode(),encoded(boundary).decode(),
                 proof_events['IMPORT'],proof_events['CUSTODY'],proof_events['NATIVE'],proof_events['EXCLUSION']))
            self._import_history(connection, context, history, batch)
            for row in archive_rows:
                cursor.execute('INSERT INTO hosting_controlplane.retained_conversion_files VALUES (%s,%s,%s,%s,%s,%s)',
                    (context.organization_id,context.tenant_id,batch,row['path'],row['sha256'],row['bytes']))
            for row in epochs:
                binding = NativeBinding.from_record(row['binding'])
                cursor.execute('INSERT INTO hosting_controlplane.retained_conversion_bindings VALUES '
                    '(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                    (context.organization_id,context.tenant_id,batch,*binding.key(),source_epoch,source_epoch+1))
                cursor.execute('INSERT INTO hosting_controlplane.native_ownership '
                    '(platform_family,endpoint_id,native_scope_id,resource_kind,native_id,organization_id,tenant_id,'
                    'security_domain_id,workload_id,worker_id,lease_epoch,lease_expires_at) '
                    'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,%s,NULL) ON CONFLICT DO NOTHING',
                    (*binding.key(),context.organization_id,context.tenant_id,scope['securityDomainId'],
                     scope['workloadId'],source_epoch))
                cursor.execute('SELECT organization_id,tenant_id,security_domain_id,workload_id,worker_id,'
                    'lease_epoch,lease_expires_at FROM hosting_controlplane.native_ownership WHERE '
                    'platform_family=%s AND endpoint_id=%s AND native_scope_id=%s AND resource_kind=%s AND native_id=%s FOR UPDATE',
                    binding.key())
                require(cursor.fetchone() == (context.organization_id,context.tenant_id,scope['securityDomainId'],
                    scope['workloadId'],None,source_epoch,None), 'Current owner differs; existing canonical native recovery is required')
            for row in recoveries:
                cursor.execute('INSERT INTO hosting_controlplane.retained_conversion_recovery '
                    '(organization_id,tenant_id,batch_id,operation_id,generation,record_format,origin_digest,original_outcome) '
                    'VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                    (context.organization_id,context.tenant_id,batch,row['operationId'],row['generation'],
                     row['format'],row['originDigest'],row['outcome']))
            self._compare_import(cursor, context, batch, history, archive_rows, recoveries, epochs)
            snapshot.recheck()
        return ImportReceipt(batch,batch_digest,True,len(history),len(archive_rows),len(bindings),len(recoveries))

    @staticmethod
    def _import_history(connection, context, history, batch):
        current = history[-1]
        kind, identity = EnterpriseRecordStore._identity(context, current)
        existing = EnterpriseRecordStore._load(connection, context, kind, identity, lock=True)
        raw, record_digest = _encode(current)
        if existing is None:
            connection.execute('INSERT INTO hosting_controlplane.enterprise_records '
                '(organization_id,tenant_id,record_kind,record_id,revision,record_json,record_digest) '
                'VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s)',
                (context.organization_id,context.tenant_id,kind,identity,current['metadata']['revision'],raw,record_digest))
        else:
            require(existing.record == current and existing.digest == record_digest,
                    'Existing canonical record cannot be replaced by conversion')
        for record in history:
            revision = record['metadata']['revision']
            original, expected = _encode(record)
            row = connection.execute('SELECT record_digest,record_json FROM hosting_controlplane.enterprise_record_history '
                'WHERE organization_id=%s AND tenant_id=%s AND record_kind=%s AND record_id=%s AND revision=%s',
                (context.organization_id,context.tenant_id,kind,identity,revision)).fetchone()
            if row is None:
                EnterpriseRecordStore._append_history(connection,context,kind,identity,revision,original,expected)
            else:
                require(row[0] == expected and _json(row[1]) == record, 'Existing canonical history differs from immutable original')
        EnterpriseRecordStore._audit(connection,context,AuditContext('retained-state-importer',batch),
            'RECORD_CREATE',kind,identity,current['metadata']['revision'],record_digest,
            {'retainedBatch':batch,'historicalImport':True,'historyCount':len(history),'observationOnly':True})

    @staticmethod
    def _compare_import(cursor,context,batch,history,files,recoveries,epochs):
        args=(context.organization_id,context.tenant_id,batch)
        cursor.execute('SELECT source_path,original_digest,byte_count FROM hosting_controlplane.retained_conversion_files '
            'WHERE organization_id=%s AND tenant_id=%s AND batch_id=%s ORDER BY source_path',args)
        require(cursor.fetchall()==[(row['path'],row['sha256'],row['bytes']) for row in files],
                'Original/imported file counts or digests differ')
        cursor.execute('SELECT operation_id,generation,record_format,origin_digest,original_outcome,retry_authorized '
            'FROM hosting_controlplane.retained_conversion_recovery WHERE organization_id=%s AND tenant_id=%s '
            'AND batch_id=%s ORDER BY operation_id,generation',args)
        require(cursor.fetchall()==[(row['operationId'],row['generation'],row['format'],row['originDigest'],row['outcome'],False)
            for row in recoveries], 'Original/imported starts or outcomes differ')
        cursor.execute('SELECT platform_family,endpoint_id,native_scope_id,resource_kind,native_id,source_epoch,target_epoch '
            'FROM hosting_controlplane.retained_conversion_bindings WHERE organization_id=%s AND tenant_id=%s AND batch_id=%s '
            'ORDER BY platform_family,endpoint_id,native_scope_id,resource_kind,native_id',args)
        require(cursor.fetchall()==[(*NativeBinding.from_record(row['binding']).key(),row['sourceEpoch'],row['targetEpoch'])
            for row in epochs], 'Original/imported native identities or epochs differ')
        cursor.execute('SELECT revision,record_digest FROM hosting_controlplane.enterprise_record_history '
            "WHERE organization_id=%s AND tenant_id=%s AND record_kind='Workload' AND record_id=%s ORDER BY revision",
            (context.organization_id,context.tenant_id,history[-1]['metadata']['workloadId']))
        require(cursor.fetchall()==[(record['metadata']['revision'],_encode(record)[1]) for record in history],
                'Original/imported canonical history count or digest differs')
