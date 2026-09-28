"""All dataset children must prove distinct, correctly directed file restores."""
from copy import deepcopy
import unittest

from tools.dataset_acceptance import STATUS, validate_group
from tools.restic_transfer import TransferGuard
from tools.run_files import digest, encoded, load_private
import test_restic_transfer as harness


class DatasetAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.rows = []; self.records = {}
        for number in (1, 2):
            fixture = harness.TransferTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
            spec = fixture.envelope['transfer']['spec']
            spec['datasetId'] = spec['sourceReceipt']['datasetId'] = f'dataset-{number}'
            spec['targetRef'] = f'target-dataset-{number}'
            spec['sourceNativeBinding']['nativeId'] = f'volume-{number}'
            guard = TransferGuard(fixture.service, 'worker-token', digest(encoded(fixture.envelope)),
                                  'grant-01', 'dataset-restore', 'restore-01')
            result = fixture.restore(transfer=fixture.envelope, transfer_guard=guard)
            identity = f'dataset-restore-{number}'
            self.rows.append({'step_id': identity, 'dataset_id': spec['datasetId'],
                              'target_ref': spec['targetRef'],
                              'transfer_manifest_sha256': digest(encoded(fixture.envelope))})
            self.records[identity] = {'transfer_manifest': deepcopy(fixture.envelope),
                'transfer_receipt': load_private(fixture.root / 'operation/transfer-receipt.json'),
                'restore_receipt': result}
            self.scope = fixture.envelope['destination_execution_scope']

    def test_group_completes_only_after_each_distinct_dataset_is_verified(self):
        result = validate_group('group-01', self.rows, self.records, self.scope)
        self.assertEqual(result['status'], STATUS)
        self.assertEqual(result['dataset_ids'], ['dataset-1', 'dataset-2'])
        self.assertEqual(set(result['transfers']), set(self.records))
        self.assertFalse(result['application_acceptance'])
        self.assertFalse(result['native_qualification'])
        self.assertFalse(result['production_activation'])

    def test_group_cannot_hide_a_selected_dataset_by_omitting_its_binding_and_proof(self):
        row=self.rows[0]
        with self.assertRaisesRegex(ValueError,'every selected canonical mapping'):
            validate_group('group-01',[row],{row['step_id']:self.records[row['step_id']]},self.scope)

    def test_missing_extra_duplicate_and_unbound_children_are_held(self):
        for records in ({}, {self.rows[0]['step_id']: self.records[self.rows[0]['step_id']]},
                        self.records | {'unexpected': self.records[self.rows[0]['step_id']]}):
            with self.subTest(records=records.keys()), self.assertRaisesRegex(ValueError, 'Every dataset'):
                validate_group('group-01', self.rows, records, self.scope)
        for field in self.rows[0]:
            altered = deepcopy(self.rows); altered[1][field] = altered[0][field]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'duplicate'):
                validate_group('group-01', altered, self.records, self.scope)
        with self.assertRaisesRegex(ValueError, 'explicitly bound'):
            validate_group(None, self.rows, self.records, self.scope)

    def test_misdirected_group_scope_dataset_and_snapshot_cannot_complete(self):
        with self.assertRaises(ValueError):
            validate_group('other-group', self.rows, self.records, self.scope)
        with self.assertRaises(ValueError):
            validate_group('group-01', self.rows, self.records, self.scope | {'site_key': 'other-site'})
        for field, value in (('dataset_id', 'other-dataset'), ('target_ref', 'other-target'),
                             ('snapshot_id', 'a' * 64), ('file_count', 0),
                             ('application_acceptance', True), ('native_qualification', True)):
            altered = deepcopy(self.records)
            altered[self.rows[1]['step_id']]['transfer_receipt'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_group('group-01', self.rows, altered, self.scope)

    def test_reusing_one_source_receipt_for_two_datasets_is_refused(self):
        rows, records = deepcopy(self.rows), deepcopy(self.records)
        first, second = [records[row['step_id']] for row in rows]
        reused = first['transfer_receipt']['source_receipt_sha256']
        second['transfer_manifest']['transfer']['spec']['sourceReceipt']['receiptDigest'] = reused
        second['transfer_receipt']['source_receipt_sha256'] = reused
        second_digest = digest(encoded(second['transfer_manifest']))
        rows[1]['transfer_manifest_sha256'] = second_digest
        second['transfer_receipt']['transfer_manifest_sha256'] = second_digest
        with self.assertRaisesRegex(ValueError, 'One capture or restore'):
            validate_group('group-01', rows, records, self.scope)

    def test_manifest_mutation_and_ordinary_receipt_substitution_are_refused(self):
        altered = deepcopy(self.records)
        altered[self.rows[1]['step_id']]['transfer_manifest']['target_member'] = 'different-member'
        with self.assertRaisesRegex(ValueError, 'reviewed child'):
            validate_group('group-01', self.rows, altered, self.scope)
        altered = deepcopy(self.records)
        altered[self.rows[1]['step_id']]['restore_receipt']['snapshot_id'] = 'a' * 64
        with self.assertRaises(ValueError):
            validate_group('group-01', self.rows, altered, self.scope)


if __name__ == '__main__':
    unittest.main()
