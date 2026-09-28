"""Reviewed mobility graphs fan out per dataset and join all consistency groups."""
from copy import deepcopy
import unittest

from provisioner.domain.errors import ProvisioningError
from provisioner.portability import migration, handoff
from tests.provisioning import support
from tests.provisioning.unit.test_portability import mobility_document


class DatasetFanoutTests(unittest.TestCase):
    def setUp(self):
        self.source = support.platform_plan('openstack')
        self.target = support.platform_plan('nutanix')
        self.intent = mobility_document()
        prototype = self.intent['spec']['data']['datasets'][0]
        self.intent['spec']['data']['datasets'] = [deepcopy(prototype) | {
            'name': f'dataset-{index}',
            'transferManifest': {'datasetId': f'dataset-{index}',
                'targetRef': f'target-{index}', 'consistencyGroupId': group,
                'sha256': str(index) * 64}}
            for index, group in ((1, 'group-aa'), (2, 'group-aa'), (3, 'group-bb'))]

    def build(self):
        return migration.build(self.source, self.target, self.intent)

    def test_one_child_per_dataset_and_all_group_joins_precede_cutover(self):
        plan = self.build()
        graph = handoff.build(self.target, plan, 'a' * 40)
        steps = {row['id']: row for row in graph['steps']}
        children = {name: row for name, row in steps.items() if row['kind'] == 'dataset_restore'}
        groups = {name: row for name, row in steps.items() if row['kind'] == 'dataset_acceptance'}
        self.assertEqual(len(children), 3)
        self.assertEqual(len(groups), 2)
        self.assertNotIn('dataset-restore', steps)
        self.assertEqual(sorted(len(row['needs']) for row in groups.values()), [1, 2])
        self.assertTrue(set(groups) <= set(steps['target-service-acceptance']['needs']))
        def ancestors(name):
            return {parent for parent in steps[name]['needs']} | {
                ancestor for parent in steps[name]['needs'] for ancestor in ancestors(parent)}
        self.assertTrue(set(children) | set(groups) <= ancestors('cutover-authorization'))
        for index in (1, 2, 3):
            params = graph['reviewed_parameters'][f'dataset-restore-dataset-{index}']
            self.assertEqual(params['source_scope'], self.source.identity.scope)
            self.assertEqual(params['dataset_id'], f'dataset-{index}')
            self.assertEqual(params['target_ref'], f'target-{index}')
            self.assertEqual(params['transfer_manifest_sha256'], str(index) * 64)
        self.assertFalse(plan['data_transfer']['verified'])
        self.assertFalse(plan['data_transfer']['native_qualified'])

    def test_dataset_children_inherit_fixed_bootstrap_and_guest_dependencies(self):
        plan = self.build()
        steps = {row['id']: row for row in plan['delivery']['steps']}
        self.assertIn('target-bootstrap-apply', steps)
        self.assertIn('target-bootstrap-approval', steps)
        for row in steps.values():
            if row['kind'] == 'dataset_restore':
                self.assertEqual(row['needs'], ['target-guest-apply'])
        self.assertNotIn('target-bootstrap', steps['target-bootstrap-acceptance']['needs'])

    def test_missing_transfer_binding_is_explicitly_held_and_never_invented(self):
        del self.intent['spec']['data']['datasets'][0]['transferManifest']
        plan = self.build()
        self.assertIn('DATASET_TRANSFER_BINDING_ABSENT:dataset-1', plan['blockers'])
        self.assertEqual(plan['readiness'], 'HELD')
        self.assertIsNone(plan['data_transfer']['datasets'][0]['transfer_binding'])
        params = plan['delivery']['reviewed_parameters']['dataset-restore-dataset-1']
        self.assertIsNone(params['transfer_manifest_sha256'])
        self.assertIsNone(params['dataset_id'])

    def test_unimplemented_transfer_method_cannot_be_reinterpreted_as_restic(self):
        self.intent['spec']['data']['datasets'][0]['method'] = 'block-copy'
        plan = self.build()
        self.assertIn('DATA_TRANSFER_METHOD_NOT_IMPLEMENTED:block-copy', plan['blockers'])
        params = plan['delivery']['reviewed_parameters']['dataset-restore-dataset-1']
        self.assertIsNone(params['transfer_manifest_sha256'])
        self.assertIsNone(params['dataset_id'])

    def test_duplicate_names_dataset_mappings_targets_and_manifests_are_refused(self):
        for field in ('name', 'datasetId', 'targetRef', 'sha256'):
            modified = deepcopy(self.intent)
            rows = modified['spec']['data']['datasets']
            if field == 'name': rows[1][field] = rows[0][field]
            else: rows[1]['transferManifest'][field] = rows[0]['transferManifest'][field]
            with self.subTest(field=field), self.assertRaises(ProvisioningError):
                migration.build(self.source, self.target, modified)

    def test_reviewed_plan_digest_changes_with_one_dataset_target_or_manifest(self):
        original = self.build()['digest']
        self.intent['spec']['data']['datasets'][0]['transferManifest']['targetRef'] = 'other-target'
        changed = self.build()['digest']
        self.assertNotEqual(original, changed)
        self.intent['spec']['data']['datasets'][0]['transferManifest']['sha256'] = 'e' * 64
        self.assertNotEqual(changed, self.build()['digest'])


if __name__ == '__main__':
    unittest.main()
