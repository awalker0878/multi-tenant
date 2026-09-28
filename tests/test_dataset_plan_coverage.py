"""A complete group cannot hide another group selected by the canonical plan."""
from copy import deepcopy
import unittest

from provisioner.domain.enterprise_records import plan_digest
from tools.dataset_acceptance import validate_coverage, validate_group
from tools.run_files import digest, encoded, load_private
import test_restic_transfer as harness


class DatasetPlanCoverageTests(unittest.TestCase):
    def setUp(self):
        self.groups = []
        for number in (1, 2):
            fixture = harness.TransferTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
            fixture.plan['spec']['datasetMappings'][1]['consistencyGroupId'] = 'group-02'
            fixture.plan['metadata']['planDigest'] = plan_digest(fixture.plan)
            fixture.transfer['metadata']['planDigest'] = fixture.plan['metadata']['planDigest']
            spec = fixture.transfer['spec']
            spec['datasetId'] = spec['sourceReceipt']['datasetId'] = f'dataset-{number}'
            spec['targetRef'] = f'target-dataset-{number}'
            spec['sourceNativeBinding']['nativeId'] = f'volume-{number}'
            spec['consistencyGroupId'] = f'group-0{number}'
            fixture.configure_authority()
            restored = fixture.restore(transfer=fixture.envelope, transfer_guard=fixture.guard)
            step = f'dataset-child-{number}'
            rows = [{'step_id': step, 'dataset_id': spec['datasetId'],
                     'target_ref': spec['targetRef'],
                     'transfer_manifest_sha256': digest(encoded(fixture.envelope))}]
            records = {step: {'transfer_manifest': fixture.envelope,
                'transfer_receipt': load_private(fixture.root / 'operation/transfer-receipt.json'),
                'restore_receipt': restored}}
            self.scope = fixture.envelope['destination_execution_scope']
            result = validate_group(spec['consistencyGroupId'], rows, records, self.scope)
            self.groups.append({'group_result': result, 'migration_plan': deepcopy(fixture.plan)})

    def test_all_selected_groups_complete_without_promoting_application_acceptance(self):
        result = validate_coverage(self.groups, self.scope)
        self.assertEqual(result['dataset_ids'], ['dataset-1', 'dataset-2'])
        self.assertEqual(set(result['group_results']), {'group-01', 'group-02'})
        self.assertFalse(result['application_acceptance'])
        self.assertFalse(result['native_qualification'])
        self.assertFalse(result['production_activation'])

    def test_a_wholly_omitted_group_blocks_services_even_when_other_group_is_complete(self):
        self.assertEqual(self.groups[0]['group_result']['dataset_ids'], ['dataset-1'])
        with self.assertRaisesRegex(ValueError, 'All selected canonical dataset groups'):
            validate_coverage(self.groups[:1], self.scope)
        with self.assertRaisesRegex(ValueError, 'Complete canonical'):
            validate_coverage([], self.scope)

    def test_duplicate_groups_do_not_supply_missing_group_coverage(self):
        with self.assertRaisesRegex(ValueError, 'exactly once'):
            validate_coverage([self.groups[0], self.groups[0]], self.scope)

    def test_different_plan_revisions_and_destination_scopes_cannot_be_combined(self):
        changed = deepcopy(self.groups)
        changed[1]['migration_plan']['metadata']['revision'] = 2
        changed[1]['migration_plan']['metadata']['planDigest'] = plan_digest(changed[1]['migration_plan'])
        with self.assertRaisesRegex(ValueError, 'one exact canonical plan'):
            validate_coverage(changed, self.scope)
        with self.assertRaisesRegex(ValueError, 'canonical destination'):
            validate_coverage(self.groups, self.scope | {'site_key': 'foreign-site'})

    def test_same_machine_restore_roots_cannot_overlap_across_groups(self):
        for nested in (False, True):
            changed = deepcopy(self.groups)
            first = next(iter(changed[0]['group_result']['transfers'].values()))
            second = next(iter(changed[1]['group_result']['transfers'].values()))
            second['target_machine_id'] = first['target_machine_id']
            second['restore_root'] = first['restore_root'] + ('/nested' if nested else '')
            with self.subTest(nested=nested), self.assertRaisesRegex(ValueError, 'same machine must not overlap'):
                validate_coverage(changed, self.scope)

    def test_the_same_isolated_path_on_different_observed_machines_is_valid(self):
        changed = deepcopy(self.groups)
        first = next(iter(changed[0]['group_result']['transfers'].values()))
        second = next(iter(changed[1]['group_result']['transfers'].values()))
        first['target_machine_id'] = 'a' * 32
        second['target_machine_id'] = 'b' * 32
        second['restore_root'] = first['restore_root']
        result = validate_coverage(changed, self.scope)
        self.assertEqual(result['dataset_ids'], ['dataset-1', 'dataset-2'])

    def test_old_group_proofs_without_observed_machine_and_root_are_refused(self):
        changed = deepcopy(self.groups)
        changed[0]['group_result']['format'] = 'hosting-dataset-group-verification/1'
        with self.assertRaisesRegex(ValueError, 'canonical destination'):
            validate_coverage(changed, self.scope)
        changed = deepcopy(self.groups)
        del next(iter(changed[0]['group_result']['transfers'].values()))['target_machine_id']
        with self.assertRaisesRegex(ValueError, 'proof identities'):
            validate_coverage(changed, self.scope)

    def test_receipts_cannot_be_reused_between_different_groups(self):
        for field in ('source_receipt_sha256', 'restore_receipt_sha256',
                      'transfer_manifest_sha256', 'transfer_receipt_sha256'):
            changed = deepcopy(self.groups)
            first = next(iter(changed[0]['group_result']['transfers'].values()))
            second = next(iter(changed[1]['group_result']['transfers'].values()))
            second[field] = first[field]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'reused across groups'):
                validate_coverage(changed, self.scope)

    def test_incomplete_or_misdirected_group_proof_is_not_coverage(self):
        changed = deepcopy(self.groups)
        changed[1]['group_result']['transfers'] = {}
        with self.assertRaisesRegex(ValueError, 'every selected dataset'):
            validate_coverage(changed, self.scope)
        changed = deepcopy(self.groups)
        next(iter(changed[1]['group_result']['transfers'].values()))['target_ref'] = 'foreign-target'
        with self.assertRaisesRegex(ValueError, 'missing a selected canonical'):
            validate_coverage(changed, self.scope)


if __name__ == '__main__':
    unittest.main()
