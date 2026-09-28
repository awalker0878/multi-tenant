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
        proofs[row['step_id']] = {'transfer_manifest_sha256': row['transfer_manifest_sha256'],
                                 'transfer_receipt_sha256': digest(encoded(proof)),
                                 'restore_receipt_sha256': proof['restore_receipt_sha256']}
    require(len(plan_digests) == len(observation_ids) == 1,
            'A consistency group must use one exact migration plan and source observation')
    return {'format': FORMAT_GROUP, 'status': STATUS, 'group_id': group_id,
            'scope': dict(scope), 'dataset_ids': sorted(unique['dataset_id']),
            'migration_plan_digest': next(iter(plan_digests)), 'transfers': proofs,
            'application_acceptance': False, 'native_qualification': False,
            'production_activation': False}
