"""Pure, fail-closed join of distinct dataset restore evidence in one group.

The delivery runner owns dependency receipts and authenticates retained artifacts
before calling this function. It does not contact a platform, issue authority or
promote application consistency from a successful file copy.
"""
from __future__ import annotations

import re
from provisioner.domain.enterprise_records import validate_record
from tools.restic_transfer import FORMAT, RECEIPT_FORMAT
from tools.run_files import digest, encoded, require

FORMAT_GROUP = 'hosting-dataset-group-verification/1'
STATUS = 'DATASET_GROUP_FILE_BYTES_VERIFIED_NOT_APPLICATION_ACCEPTED'
_FIELDS = {'step_id', 'dataset_id', 'target_ref', 'transfer_manifest_sha256'}
_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_SHA = re.compile(r'^[0-9a-f]{64}$')


def validate_group(group_id, datasets, records, scope):
    """Return byte-verification evidence only when every exact child completed."""
    require(isinstance(group_id, str) and _ID.fullmatch(group_id)
            and isinstance(datasets, list) and 1 <= len(datasets) <= 32,
            'An explicitly bound dataset consistency group is required')
    unique = {key: set() for key in _FIELDS}
    for row in datasets:
        require(isinstance(row, dict) and set(row) == _FIELDS,
                'Exact reviewed dataset child binding required')
        for key, value in row.items():
            require(isinstance(value, str)
                    and (_SHA if key == 'transfer_manifest_sha256' else _ID).fullmatch(value)
                    and value not in unique[key],
                    'Dataset children cannot duplicate identities, targets or manifests')
            unique[key].add(value)
    require(isinstance(records, dict) and set(records) == unique['step_id'],
            'Every dataset child must supply its distinct completed restore evidence')
    declared_mappings={(row['dataset_id'],row['target_ref']) for row in datasets}
    captures, restores, proofs, plan_digests, observation_ids = set(), set(), {}, set(), set()
    for row in datasets:
        record = records[row['step_id']]
        require(isinstance(record, dict) and set(record) == {
                'transfer_manifest', 'transfer_receipt', 'restore_receipt'},
                'Exact retained restore evidence required')
        envelope, proof, restored = (record[key] for key in
            ('transfer_manifest', 'transfer_receipt', 'restore_receipt'))
        require(envelope.get('format') == FORMAT
                and digest(encoded(envelope)) == row['transfer_manifest_sha256'],
                'Dataset transfer manifest differs from the reviewed child')
        transfer = envelope['transfer']; spec = transfer['spec']
        require(not validate_record(transfer, plan=envelope['migration_plan'])
                and (spec['datasetId'], spec['targetRef'], spec['consistencyGroupId']) ==
                    (row['dataset_id'], row['target_ref'], group_id)
                and envelope['destination_execution_scope'] == scope,
                'Dataset child is directed to another plan, group or destination')
        selected_group={(mapping['datasetId'],mapping['targetRef'])
                        for mapping in envelope['migration_plan']['spec']['datasetMappings']
                        if mapping['consistencyGroupId']==group_id}
        require(declared_mappings==selected_group,
                'Dataset group must cover every selected canonical mapping')
        require(proof.get('format') == RECEIPT_FORMAT
                and proof.get('status') == restored.get('status') ==
                    'RESTORED_FILE_BYTES_VERIFIED_NOT_APPLICATION_ACCEPTED'
                and proof['transfer_manifest_sha256'] == row['transfer_manifest_sha256']
                and proof['source_receipt_sha256'] == spec['sourceReceipt']['receiptDigest']
                and proof['restore_receipt_sha256'] == digest(encoded(restored))
                and proof['migration_plan_digest'] == transfer['metadata']['planDigest']
                and (proof['dataset_id'], proof['target_ref']) == (row['dataset_id'], row['target_ref'])
                and proof['scope'] == scope
                and proof['source_scope'] == restored['scope'] == envelope['source_execution_scope']
                and proof['source_member'] == restored['member']
                and proof['member'] == envelope['target_member']
                and proof['snapshot_id'] == restored['snapshot_id'] == envelope['snapshot_id']
                and proof['repository_id'] == envelope['repository_id']
                and proof['file_manifest_sha256'] == envelope['file_manifest_sha256']
                and proof['restore_root'] == envelope['target']
                and proof['file_count'] == restored['file_count']
                and type(proof['file_count']) is int and proof['file_count'] > 0
                and proof['completed_at'] == restored['completed_at']
                and proof['application_acceptance'] is False
                and proof['native_qualification'] is False
                and proof['production_activation'] is restored['production_activation'] is False,
                'Dataset completion does not prove this exact restored mapping')
        require(proof['source_receipt_sha256'] not in captures
                and proof['restore_receipt_sha256'] not in restores,
                'One capture or restore receipt cannot complete multiple datasets')
        captures.add(proof['source_receipt_sha256']); restores.add(proof['restore_receipt_sha256'])
        plan_digests.add(proof['migration_plan_digest'])
        observation_ids.add(spec['sourceSnapshotId'])
        proofs[row['step_id']] = {'dataset_id': row['dataset_id'], 'target_ref': row['target_ref'],
                                 'source_receipt_sha256': proof['source_receipt_sha256'],
                                 'transfer_manifest_sha256': row['transfer_manifest_sha256'],
                                 'transfer_receipt_sha256': digest(encoded(proof)),
                                 'restore_receipt_sha256': proof['restore_receipt_sha256']}
    require(len(plan_digests) == len(observation_ids) == 1,
            'A consistency group must use one exact migration plan and source observation')
    return {'format': FORMAT_GROUP, 'status': STATUS, 'group_id': group_id,
            'scope': dict(scope), 'dataset_ids': sorted(unique['dataset_id']),
            'migration_plan_digest': next(iter(plan_digests)), 'transfers': proofs,
            'application_acceptance': False, 'native_qualification': False,
            'production_activation': False}


def validate_coverage(records, scope):
    """Verify the complete selected canonical plan after all group joins.

    The runner must first recompute each group against authenticated retained
    child artifacts and compare that value with the retained group result. This
    pure join prevents a caller's legacy dataset subset from hiding an entire
    group selected by the canonical plan; it supplies no execution authority.
    """
    require(isinstance(records, list) and 1 <= len(records) <= 32,
            'Complete canonical dataset group coverage required')
    group_results, declared_mappings, canonical_mappings = {}, set(), None
    plan_digest = None
    unique = {key: set() for key in ('dataset_id', 'target_ref', 'source_receipt_sha256',
                                    'restore_receipt_sha256', 'transfer_manifest_sha256',
                                    'transfer_receipt_sha256', 'step_id')}
    transfer_keys = set(unique) - {'step_id'}
    for record in records:
        require(isinstance(record, dict) and set(record) == {'group_result', 'migration_plan'},
                'Exact group verification and canonical plan required')
        result, plan = record['group_result'], record['migration_plan']
        require(isinstance(plan, dict) and plan.get('kind') == 'MigrationPlan'
                and not validate_record(plan), 'Valid canonical dataset plan required')
        selected = {(row['datasetId'], row['targetRef'], row['consistencyGroupId'])
                    for row in plan['spec']['datasetMappings']}
        if canonical_mappings is None:
            canonical_mappings, plan_digest = selected, plan['metadata']['planDigest']
        require(selected == canonical_mappings and plan['metadata']['planDigest'] == plan_digest,
                'All completed groups must belong to one exact canonical plan')
        require(isinstance(result, dict) and result.get('format') == FORMAT_GROUP
                and result.get('status') == STATUS and result.get('scope') == scope
                and result.get('migration_plan_digest') == plan_digest
                and result.get('application_acceptance') is False
                and result.get('native_qualification') is False
                and result.get('production_activation') is False,
                'Dataset group is not verified for this canonical destination')
        group_id = result.get('group_id')
        require(isinstance(group_id, str) and _ID.fullmatch(group_id)
                and group_id not in group_results,
                'Every canonical consistency group must appear exactly once')
        expected = {(dataset_id, target_ref) for dataset_id, target_ref, group in selected
                    if group == group_id}
        transfers = result.get('transfers')
        require(expected and isinstance(transfers, dict) and len(transfers) == len(expected),
                'Group verification must include every selected dataset mapping')
        actual = set()
        for step_id, transfer in transfers.items():
            require(isinstance(transfer, dict) and set(transfer) == transfer_keys,
                    'Complete distinct dataset proof identities required')
            for key, value in {'step_id': step_id, **transfer}.items():
                expression = _SHA if key.endswith('_sha256') else _ID
                require(isinstance(value, str) and expression.fullmatch(value)
                        and value not in unique[key],
                        'Datasets, mappings and capture/restore proofs cannot be reused across groups')
                unique[key].add(value)
            actual.add((transfer['dataset_id'], transfer['target_ref']))
        require(actual == expected and result.get('dataset_ids') == sorted(row[0] for row in expected),
                'Group verification is missing a selected canonical dataset')
        declared_mappings.update((dataset_id, target_ref, group_id) for dataset_id, target_ref in actual)
        group_results[group_id] = digest(encoded(result))
    require(declared_mappings == canonical_mappings,
            'All selected canonical dataset groups must complete before services acceptance')
    return {'format': 'hosting-dataset-plan-verification/1',
            'status': 'DATASET_PLAN_FILE_BYTES_VERIFIED_NOT_APPLICATION_ACCEPTED',
            'scope': dict(scope), 'migration_plan_digest': plan_digest,
            'dataset_ids': sorted(unique['dataset_id']),
            'group_results': dict(sorted(group_results.items())),
            'application_acceptance': False, 'native_qualification': False,
            'production_activation': False}
