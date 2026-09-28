"""Versioned profile catalogs are the reviewed owner of portable policy.

A catalog is a reviewed artifact, not a code constant: it declares its own revision,
the revision of every profile in it, the default profile of the family, the portable
service list and the request-shape defaults a caller may omit. These tests hold the
catalog to that role, and hold a plan to the exact reviewed revision it used.
"""
from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from provisioner.compiler import normalize
from provisioner.profiles import resolver
from provisioner.domain.errors import ProvisioningError
from provisioner.execution import plan as execution_plan
from provisioner.inventory.model import fixture
from provisioner.profiles import loader
from provisioner.profiles.loader import Catalog, load_catalogs

from tests.provisioning import support

#: The request groups a reviewed catalog default may fill in.
DEFAULT_GROUPS = ('assurance', 'capacity', 'exposure', 'network', 'placement',
                  'recovery', 'services', 'zones')


def _write(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, indent=2, sort_keys=False) + '\n',
                    encoding='utf-8', newline='\n')


def _edit(path: Path, change) -> None:
    document = json.loads(path.read_text(encoding='utf-8'))
    change(document)
    _write(path, document)


def edited_catalogs(change) -> Catalog:
    """The reviewed catalog set, copied aside and edited, then loaded as a whole.

    Editing a copy is how a reviewer would propose a policy change: the loader must
    accept or refuse the proposed set exactly as it would the reviewed one.
    """
    with tempfile.TemporaryDirectory() as root:
        target = Path(root) / 'profiles'
        shutil.copytree(loader.PROFILE_ROOT, target)
        change(target)
        return load_catalogs(target)


def minimal_document() -> dict:
    """A request that states only what the contract requires, so every default applies."""
    return {'apiVersion': 'hosting.platform/v1', 'kind': 'WorkloadSecurityDomain',
            'metadata': {'tenant': 'tenant-01', 'name': 'wsd-minimal',
                         'owner': 'platform-team'},
            'spec': {'environment': 'development',
                     'security': {'profile': 'internal-baseline'},
                     'platform': {'preference': 'auto'},
                     'placement': {'region': 'east'},
                     'availability': {'profile': 'single-zone'}}}


def set_profile_version(document: dict, profile: str, version: str) -> None:
    for row in document['profiles']:
        if row['profile'] == profile:
            row['version'] = version
            return
    raise AssertionError(f'no such profile in this catalog: {profile}')


class CatalogVersionTest(unittest.TestCase):
    """Every reviewed revision is declared, unique and covered by the catalog digest."""

    def test_every_catalog_declares_a_reviewed_version(self):
        catalog = support.catalogs()
        self.assertEqual(sorted(catalog.versions), sorted(loader.FAMILIES))
        for family in loader.FAMILIES:
            with self.subTest(family=family):
                self.assertRegex(catalog.version(family), loader.VERSION)

    def test_every_profile_declares_a_reviewed_version(self):
        catalog = support.catalogs()
        for family in loader.FAMILIES:
            for name, profile in sorted(catalog.family(family).items()):
                with self.subTest(profile=f'{family}/{name}'):
                    self.assertRegex(profile.version, loader.VERSION)
                    self.assertEqual(profile.to_dict()['version'], profile.version)

    def test_the_catalog_versions_form_one_reviewed_revision_ladder(self):
        versions = support.catalogs().versions
        self.assertEqual(len(set(versions.values())), len(versions),
                         f'catalog versions must be distinct: {versions}')

    def test_the_catalog_digest_covers_the_whole_reviewed_set(self):
        first, second = support.catalogs(), support.catalogs()
        self.assertEqual(first.digest, second.digest)
        self.assertEqual(first.manifest(), second.manifest())
        self.assertEqual(sorted(first.version_set()), ['catalogs', 'profiles'])
        self.assertEqual(first.version_set()['catalogs'], first.versions)
        self.assertEqual(first.version_set()['profiles']['compute'],
                         {name: profile.version
                          for name, profile in sorted(first.family('compute').items())})

    def test_a_catalog_without_a_version_is_refused(self):
        with self.assertRaises(ProvisioningError) as caught:
            edited_catalogs(lambda root: _edit(root / 'compute' / 'catalog.json',
                                               lambda d: d.pop('version')))
        self.assertEqual(caught.exception.code, 'UNSUPPORTED_PROFILE')
        self.assertIn('version', str(caught.exception))

    def test_a_catalog_with_an_invalid_version_is_refused(self):
        for invalid in ('0', '1.0', 'latest', '-1', 1, None, ''):
            with self.subTest(version=invalid):
                with self.assertRaises(ProvisioningError) as caught:
                    edited_catalogs(
                        lambda root, v=invalid: _edit(root / 'compute' / 'catalog.json',
                                                      lambda d: d.__setitem__('version', v)))
                self.assertEqual(caught.exception.code, 'UNSUPPORTED_PROFILE')

    def test_a_profile_without_a_version_is_refused(self):
        with self.assertRaises(ProvisioningError) as caught:
            edited_catalogs(lambda root: _edit(
                root / 'storage' / 'catalog.json',
                lambda d: d['profiles'][0].pop('version')))
        self.assertEqual(caught.exception.code, 'UNSUPPORTED_PROFILE')
        self.assertIn('Profile', str(caught.exception))

    def test_a_profile_with_an_invalid_version_is_refused(self):
        with self.assertRaises(ProvisioningError) as caught:
            edited_catalogs(lambda root: _edit(
                root / 'storage' / 'catalog.json',
                lambda d: set_profile_version(d, 'standard', 'v2')))
        self.assertEqual(caught.exception.code, 'UNSUPPORTED_PROFILE')

    def test_a_duplicate_catalog_version_is_refused(self):
        with self.assertRaises(ProvisioningError) as caught:
            edited_catalogs(lambda root: _edit(root / 'storage' / 'catalog.json',
                                               lambda d: d.__setitem__('version', support.catalogs().version('compute'))))
        self.assertEqual(caught.exception.code, 'UNSUPPORTED_PROFILE')
        self.assertIn('revision ladder', str(caught.exception))

    def test_a_version_bump_changes_the_catalog_digest(self):
        baseline = support.catalogs()
        bumped = edited_catalogs(lambda root: _edit(root / 'compute' / 'catalog.json',
                                                    lambda d: d.__setitem__('version', str(max(map(int, support.catalogs().versions.values())) + 1))))
        self.assertEqual(bumped.family('compute').keys(), baseline.family('compute').keys())
        self.assertNotEqual(bumped.version('compute'), baseline.version('compute'))
        self.assertNotEqual(bumped.digest, baseline.digest)
        self.assertNotEqual(bumped.version_set(), baseline.version_set())

    def test_a_profile_version_bump_changes_the_catalog_digest(self):
        baseline = support.catalogs()
        bumped = edited_catalogs(lambda root: _edit(
            root / 'storage' / 'catalog.json',
            lambda d: set_profile_version(d, 'standard', str(int(support.catalogs().get('storage', 'standard').version) + 1))))
        self.assertNotEqual(bumped.get('storage', 'standard').version,
                            baseline.get('storage', 'standard').version)
        self.assertNotEqual(bumped.digest, baseline.digest)


class CatalogOwnedDefaultsTest(unittest.TestCase):
    """Portable defaults live in the catalogs, not in the code that consumes them."""

    def test_every_default_owner_declares_an_implemented_default_profile(self):
        catalog = support.catalogs()
        for family in loader.DEFAULT_OWNERS:
            with self.subTest(family=family):
                default = catalog.default(family)
                self.assertIn(default, catalog.family(family))
                self.assertTrue(catalog.get(family, default).implemented)

    def test_the_service_catalog_owns_the_portable_service_list(self):
        catalog = support.catalogs()
        self.assertEqual(list(catalog.service_names()),
                         ['dns', 'ntp', 'identity', 'logging', 'backup'])
        for name in catalog.service_names():
            with self.subTest(service=name):
                profile = catalog.service_default(name)
                self.assertTrue(catalog.get('service', f'{name}/{profile}').implemented)

    def test_no_catalog_declares_a_deferred_profile_as_a_default(self):
        catalog = support.catalogs()
        for family, declared in catalog.defaults.items():
            with self.subTest(family=family):
                self.assertTrue(catalog.get(family, declared).implemented)

    def test_only_the_service_catalog_declares_the_service_list(self):
        with self.assertRaises(ProvisioningError) as caught:
            edited_catalogs(lambda root: _edit(
                root / 'network' / 'catalog.json',
                lambda d: d.__setitem__('services', ['dns'])))
        self.assertEqual(caught.exception.code, 'UNSUPPORTED_PROFILE')

    def test_service_defaults_must_name_every_service_exactly_once(self):
        with self.assertRaises(ProvisioningError) as caught:
            edited_catalogs(lambda root: _edit(
                root / 'service' / 'catalog.json',
                lambda d: d['defaults'].pop('backup')))
        self.assertEqual(caught.exception.code, 'UNSUPPORTED_PROFILE')

    def test_a_deferred_default_profile_is_refused(self):
        with self.assertRaises(ProvisioningError) as caught:
            edited_catalogs(lambda root: _edit(
                root / 'storage' / 'catalog.json',
                lambda d: d.__setitem__('default', 'encrypted-high-capacity')))
        self.assertEqual(caught.exception.code, 'UNSUPPORTED_PROFILE')

    def test_a_default_that_is_not_a_profile_of_the_family_is_refused(self):
        with self.assertRaises(ProvisioningError) as caught:
            edited_catalogs(lambda root: _edit(
                root / 'compute' / 'catalog.json',
                lambda d: d.__setitem__('default', 'enormous')))
        self.assertEqual(caught.exception.code, 'UNSUPPORTED_PROFILE')

    def test_the_defaults_are_exactly_what_the_catalogs_declare(self):
        catalog = support.catalogs()
        defaults = normalize.defaults_for(catalog)
        self.assertEqual(sorted(defaults), list(DEFAULT_GROUPS))
        self.assertEqual(defaults['assurance'], {'profile': catalog.default('assurance')})
        self.assertEqual(defaults['network'], {'profile': catalog.default('network')})
        self.assertEqual(defaults['capacity'],
                         {'computeProfile': catalog.default('compute'),
                          'storageProfile': catalog.default('storage')})
        self.assertEqual(defaults['services'],
                         {name: catalog.service_default(name)
                          for name in catalog.service_names()})
        self.assertEqual(defaults['recovery'],
                         catalog.request_default('recovery')['recovery'])
        self.assertEqual(defaults['exposure'],
                         catalog.request_default('security')['exposure'])
        self.assertEqual(defaults['zones'],
                         catalog.request_default('availability')['zones'])
        self.assertEqual(defaults['placement'], {'site': None, 'cell': None})

    def test_the_defaults_are_deterministic(self):
        first = normalize.defaults_for(support.catalogs())
        second = normalize.defaults_for(support.catalogs())
        self.assertEqual(first, second)
        self.assertEqual(normalize.defaults_for(support.catalogs()), first)

    def test_normalization_applies_every_catalog_default(self):
        defaults = normalize.defaults_for(support.catalogs())
        request = normalize.normalize(minimal_document(), source='<test>')
        for group, declared in defaults.items():
            with self.subTest(group=group):
                self.assertIn(group, request.spec)
                if group == 'placement':
                    for key, value in declared.items():
                        self.assertIsNone(request.spec[group][key])
                    continue
                self.assertEqual(request.spec[group], declared)

    def test_a_changed_catalog_default_changes_the_normalized_request(self):
        document = minimal_document()
        baseline = normalize.normalize(copy.deepcopy(document), source='<test>',
                                       catalog=support.catalogs())
        changed_catalog = edited_catalogs(lambda root: _edit(
            root / 'compute' / 'catalog.json', lambda d: d.__setitem__('default', 'large')))
        changed = normalize.normalize(copy.deepcopy(document), source='<test>',
                                      catalog=changed_catalog)
        self.assertEqual(baseline.spec['capacity']['computeProfile'], 'medium')
        self.assertEqual(changed.spec['capacity']['computeProfile'], 'large')
        self.assertNotEqual(changed.digest, baseline.digest)

    def test_a_changed_request_default_changes_the_normalized_request(self):
        document = minimal_document()
        baseline = normalize.normalize(copy.deepcopy(document), source='<test>',
                                       catalog=support.catalogs())
        changed_catalog = edited_catalogs(lambda root: _edit(
            root / 'availability' / 'catalog.json',
            lambda d: d['requestDefaults']['zones']['restricted'].__setitem__('enabled', False)))
        changed = normalize.normalize(copy.deepcopy(document), source='<test>',
                                      catalog=changed_catalog)
        self.assertTrue(baseline.spec['zones']['restricted']['enabled'])
        self.assertFalse(changed.spec['zones']['restricted']['enabled'])
        self.assertNotEqual(changed.digest, baseline.digest)

    def test_normalization_still_refuses_a_request_that_breaks_the_contract(self):
        for case, mutate in (('missing-required', lambda d: d['spec'].pop('platform')),
                             ('unknown-field', lambda d: d['spec'].__setitem__('native_vlan', 42))):
            with self.subTest(case=case):
                document = minimal_document()
                mutate(document)
                with self.assertRaises(ProvisioningError) as caught:
                    normalize.normalize(document, source='<test>')
                self.assertEqual(caught.exception.code, 'SCHEMA_VALIDATION_FAILED')


class VersionedIdentityTest(unittest.TestCase):
    """A reviewed revision is part of the identity of everything derived from it."""

    def test_the_resolution_records_the_reviewed_revision_set(self):
        catalog = support.catalogs()
        resolution = support.reference_plan().resolution
        self.assertEqual(resolution.format, 'hosting-profile-resolution/2')
        self.assertEqual(resolution.catalog_versions, catalog.versions)
        self.assertEqual(resolution.catalog_digest, catalog.digest)
        self.assertEqual(sorted(resolution.profile_versions),
                         sorted(resolution.profiles))
        for family, name in sorted(resolution.profiles.items()):
            if family == 'services':
                continue
            with self.subTest(family=family):
                if name is None:
                    self.assertIsNone(resolution.profile_versions[family])
                else:
                    self.assertEqual(resolution.profile_versions[family],
                                     catalog.get(family, name).version)
        for service, name in sorted(resolution.profiles['services'].items()):
            with self.subTest(service=service):
                self.assertEqual(resolution.profile_versions['services'][service],
                                 catalog.get('service', name).version)

    def test_the_resolution_document_carries_the_revision_set(self):
        resolution = support.reference_plan().resolution.to_dict()
        catalog = support.catalogs()
        self.assertEqual(resolution['catalog_versions'], catalog.versions)
        self.assertEqual(resolution['catalog_digest'], catalog.digest)
        self.assertEqual(resolution['profile_versions']['storage'],
                         catalog.get('storage', resolution['profiles']['storage']).version)

    def test_the_desired_state_records_the_reviewed_revision_set(self):
        catalog = support.catalogs()
        state = support.reference_plan().desired_state
        self.assertEqual(state.catalog_versions, catalog.versions)
        self.assertEqual(state.catalog_digest, catalog.digest)
        self.assertEqual(state.profile_versions['compute'],
                                 catalog.get('compute', 'medium').version)
        document = state.to_dict()
        self.assertEqual(document['catalog_versions'], catalog.versions)
        self.assertEqual(document['profile_versions'], state.profile_versions)

    def test_a_profile_version_bump_changes_desired_state_and_plan_identity(self):
        baseline = support.reference_plan()
        bumped = edited_catalogs(lambda root: _edit(
            root / 'storage' / 'catalog.json',
            lambda d: set_profile_version(d, 'standard', str(int(support.catalogs().get('storage', 'standard').version) + 1))))
        changed = execution_plan.create_plan(support.reference_document(), 'in-memory',
                                            fixture(), bumped)
        self.assertEqual(changed.request.digest, baseline.request.digest)
        self.assertEqual(changed.resolution.profiles, baseline.resolution.profiles)
        self.assertEqual(changed.environment, baseline.environment)
        self.assertNotEqual(changed.resolution.catalog_digest,
                            baseline.resolution.catalog_digest)
        self.assertNotEqual(changed.desired_state.digest, baseline.desired_state.digest)
        self.assertNotEqual(changed.digest, baseline.digest)

    def test_a_catalog_version_bump_changes_desired_state_and_plan_identity(self):
        baseline = support.reference_plan()
        bumped = edited_catalogs(lambda root: _edit(
            root / 'compute' / 'catalog.json', lambda d: d.__setitem__('version', str(max(map(int, support.catalogs().versions.values())) + 1))))
        changed = execution_plan.create_plan(support.reference_document(), 'in-memory',
                                            fixture(), bumped)
        self.assertEqual(changed.request.digest, baseline.request.digest)
        self.assertEqual(changed.resolution.profiles, baseline.resolution.profiles)
        self.assertEqual(changed.environment, baseline.environment)
        self.assertNotEqual(changed.resolution.catalog_versions,
                            baseline.resolution.catalog_versions)
        self.assertNotEqual(changed.desired_state.digest, baseline.desired_state.digest)
        self.assertNotEqual(changed.digest, baseline.digest)

    def test_an_unchanged_catalog_set_reproduces_the_same_identity(self):
        first = support.reference_plan()
        second = support.reference_plan()
        self.assertEqual(first.resolution.catalog_digest, second.resolution.catalog_digest)
        self.assertEqual(first.resolution.profile_versions, second.resolution.profile_versions)
        self.assertEqual(first.digest, second.digest)

    def test_a_deferred_profile_is_still_explicitly_refused(self):
        document = support.reference_document()
        document['spec']['capacity']['storageProfile'] = 'encrypted-high-capacity'
        with self.assertRaises(ProvisioningError) as caught:
            execution_plan.create_plan(document, 'in-memory', fixture(), support.catalogs())
        self.assertEqual(caught.exception.code, 'UNSUPPORTED_FEATURE')
        self.assertIn('deferred', str(caught.exception))

    def test_a_deferred_service_profile_is_still_explicitly_refused(self):
        document = support.reference_document()
        document['spec']['services']['dns'] = 'external-view'
        with self.assertRaises(ProvisioningError) as caught:
            execution_plan.create_plan(document, 'in-memory', fixture(), support.catalogs())
        self.assertEqual(caught.exception.code, 'UNSUPPORTED_FEATURE')

    def test_the_contract_refuses_a_service_the_catalog_does_not_own(self):
        document = support.reference_document()
        document['spec']['services']['telemetry'] = 'default'
        with self.assertRaises(ProvisioningError) as caught:
            execution_plan.create_plan(document, 'in-memory', fixture(), support.catalogs())
        self.assertEqual(caught.exception.code, 'SCHEMA_VALIDATION_FAILED')

    def test_resolution_refuses_an_unknown_service_without_the_contract(self):
        spec = copy.deepcopy(normalize.normalize(support.reference_document(),
                                                 source='<test>').spec)
        spec['services']['telemetry'] = 'default'
        with self.assertRaises(ProvisioningError) as caught:
            resolver.resolve(spec, support.catalogs())
        self.assertEqual(caught.exception.code, 'UNSUPPORTED_PROFILE')
        self.assertIn('telemetry', str(caught.exception))


if __name__ == '__main__':
    unittest.main()