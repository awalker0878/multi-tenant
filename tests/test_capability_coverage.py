"""Complete capability rows and evidence boundaries, without native contact."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from provisioner.domain import capabilities as vocabulary
from provisioner.qualification import registry as registry
from provisioner.qualification import native as qualification


class CapabilityCoverageTests(unittest.TestCase):
    def setUp(self):
        self.document = registry.load()

    def test_vocabulary_has_one_owner_and_no_duplicate_ids(self):
        ids = [cap for group in vocabulary.CAPABILITY_GROUPS.values() for cap in group]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(vocabulary.CAPABILITY_GROUPS), {
            'compute', 'storage', 'network', 'security', 'guest', 'discovery',
            'migration', 'services', 'operations'})
        self.assertIs(registry.CAPABILITIES, vocabulary.CAPABILITIES)
        self.assertIs(qualification.CAPABILITIES, vocabulary.CAPABILITIES)
        with self.assertRaises(TypeError):
            vocabulary.CAPABILITY_GROUPS['magic'] = ('magic',)

    def test_all_platforms_explicitly_cover_the_same_reviewed_vocabulary(self):
        for platform, profile in self.document['profiles'].items():
            with self.subTest(platform=platform):
                self.assertEqual(set(profile['capabilities']), vocabulary.CAPABILITIES)
                self.assertEqual(profile['product_tuple'], 'UNSELECTED')
                self.assertTrue(all(c['qualification'] == 'NOT_QUALIFIED'
                                    for c in profile['capabilities'].values()))
        self.assertEqual(self.document['capability_catalog_sha256'], vocabulary.catalog_digest())

    def test_missing_row_from_any_group_is_refused_for_every_platform(self):
        for platform in vocabulary.PLATFORMS:
            for group, ids in vocabulary.CAPABILITY_GROUPS.items():
                with self.subTest(platform=platform, group=group):
                    changed = deepcopy(self.document)
                    del changed['profiles'][platform]['capabilities'][ids[0]]
                    with self.assertRaises(ValueError):
                        registry.validate(changed)

    def test_unqualified_workload_capabilities_cannot_satisfy_placement(self):
        required = {'vm_create', 'boot_volume', 'dataset_transfer', 'source_fencing'}
        for platform in vocabulary.PLATFORMS:
            allowed, blockers = registry.eligible(self.document, platform, required)
            self.assertFalse(allowed)
            for cap in required:
                self.assertIn(f'capability:{cap}:NOT_IMPLEMENTED', blockers)

    def test_extended_native_claim_still_requires_a_current_dossier(self):
        changed = deepcopy(self.document)
        profile = changed['profiles']['openstack']
        profile['product_tuple'] = 'site-accepted-tuple'
        profile['capabilities']['vm_create'].update(
            qualification='NATIVE_QUALIFIED', native_evidence_refs=['external:test-only'])
        with self.assertRaisesRegex(ValueError, 'qualification dossier'):
            registry.validate(changed)

    def test_old_network_only_format_is_not_a_compatibility_path(self):
        changed = deepcopy(self.document)
        changed['format'] = 'portable-hosting-capability-registry/1'
        with self.assertRaisesRegex(ValueError, 'format'):
            registry.validate(changed)

    def test_changed_vocabulary_digest_is_refused(self):
        changed = deepcopy(self.document)
        changed['capability_catalog_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'digest'):
            registry.validate(changed)

    def test_malformed_container_types_fail_closed(self):
        for field, value in [('capability_ids', {}), ('profiles', []),
                             ('capability_ids', ['vm_create', 'vm_create'])]:
            with self.subTest(field=field, value=value):
                changed = deepcopy(self.document)
                changed[field] = value
                with self.assertRaises(ValueError):
                    registry.validate(changed)
        for field, value in [('capabilities', []), ('terraform_providers', ['x', 'x']),
                             ('assurance_profiles', 'standard'), ('product_tuple', None)]:
            changed = deepcopy(self.document)
            changed['profiles']['openstack'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                registry.validate(changed)

    def test_load_rejects_duplicate_keys_nonfinite_values_and_nonobject_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'registry.json'
            for raw in ['[]', '{"x":1,"x":2}', '{"x":NaN}']:
                path.write_text(raw)
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    registry.load(path)

    def test_source_references_cannot_escape_through_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'resources'
            root.mkdir()
            external = Path(directory) / 'external.txt'
            external.write_text('not a repository resource')
            try:
                (root / 'escape').symlink_to(external)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable on this host')
            changed = deepcopy(self.document)
            for profile in changed['profiles'].values():
                for claim in profile['capabilities'].values():
                    claim['evidence_refs'] = ['escape']
            from unittest.mock import patch
            with patch.object(qualification, 'validate', return_value={
                    'records': [], 'current_records': 0}):
                with self.assertRaisesRegex(ValueError, 'escapes resource root'):
                    registry.validate(changed, root=root)


if __name__ == '__main__':
    unittest.main()
