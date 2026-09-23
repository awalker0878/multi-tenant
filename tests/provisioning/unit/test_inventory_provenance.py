"""Inventory provenance: the reviewed identity must not depend on the read location.

An inventory document is one reviewed input. Where the operator's machine happened to
keep the file is diagnostic provenance, not part of the decision, so two machines that
read the same document must approve the same plan. These regressions fail if a path
separator, a checkout root or a path spelling can move the approval-critical identity.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from provisioner.allocations import addresses, owner
from provisioner.domain.request import digest
from provisioner.execution import plan as execution_plan
from provisioner.inventory import model as inventory_model

from tests.provisioning import support

#: Two spellings of one repository-relative location, as Windows and Linux render it.
POSIX_ORIGIN = 'provisioner/inventory/fixtures/openstack-reference.json'
WINDOWS_ORIGIN = 'provisioner\\inventory\\fixtures\\openstack-reference.json'

#: Two absolute checkout locations holding the same reviewed document.
CHECKOUTS = ('C:\\repo\\multi-tenant\\provisioner\\inventory\\fixtures'
             '\\openstack-reference.json',
             '/home/runner/work/multi-tenant/provisioner/inventory/fixtures'
             '/openstack-reference.json')


def _document(name: str = 'openstack-reference') -> dict:
    return json.loads((support.ROOT / 'provisioner' / 'inventory' / 'fixtures'
                       / f'{name}.json').read_text(encoding='utf-8'))


def _inventory(origin: str, name: str = 'openstack-reference'):
    return inventory_model.build(_document(name), origin=origin)


def _plan(inventory, name: str = 'internal-production'):
    path = support.request_path(name)
    return execution_plan.create_plan(support.reference_document(name), str(path),
                                      inventory, support.catalogs())


class SeparatorInvarianceTest(unittest.TestCase):
    """One document read through two separators is one reviewed decision."""

    def test_inventory_semantic_identity_is_path_separator_independent(self):
        posix = _inventory(POSIX_ORIGIN)
        windows = _inventory(WINDOWS_ORIGIN)
        self.assertEqual(posix.document_digest, windows.document_digest)
        self.assertEqual(posix.reference, windows.reference)
        self.assertNotIn('\\', json.dumps(posix.reference, sort_keys=True))

    def test_the_reference_records_the_document_not_the_invocation(self):
        """The approval-critical reference names no read location at all."""
        reference = _inventory(POSIX_ORIGIN).reference
        self.assertEqual(sorted(reference),
                         ['authoritative', 'digest', 'source', 'status'])
        for spelling in (POSIX_ORIGIN, WINDOWS_ORIGIN, *CHECKOUTS):
            with self.subTest(origin=spelling):
                self.assertEqual(_inventory(spelling).reference, reference)

    def test_the_diagnostic_origin_is_posix_on_every_platform(self):
        for spelling in (WINDOWS_ORIGIN, *CHECKOUTS):
            with self.subTest(origin=spelling):
                self.assertNotIn('\\', _inventory(spelling).origin)

    def test_manifest_digest_is_path_separator_independent(self):
        posix = _plan(_inventory(POSIX_ORIGIN))
        windows = _plan(_inventory(WINDOWS_ORIGIN))
        self.assertEqual(posix.manifest_digest, windows.manifest_digest)
        self.assertEqual(posix.digest, windows.digest)
        self.assertNotIn('\\', json.dumps(posix.manifest, sort_keys=True))

    def test_conformance_digest_is_path_separator_independent(self):
        posix = _plan(_inventory(POSIX_ORIGIN))
        windows = _plan(_inventory(WINDOWS_ORIGIN))
        self.assertEqual(digest(posix.conformance), digest(windows.conformance))


class CheckoutLocationTest(unittest.TestCase):
    """The same document read from two checkouts is one reviewed decision."""

    def test_plan_digest_is_identical_across_checkout_locations(self):
        plans = [_plan(_inventory(origin)) for origin in CHECKOUTS]
        self.assertEqual(len({plan.digest for plan in plans}), 1)
        self.assertEqual(len({plan.operation_id for plan in plans}), 1)
        for plan in plans:
            self.assertEqual(plan.manifest['inventory'],
                             plans[0].manifest['inventory'])

    def test_a_loaded_fixture_binds_the_same_identity_as_a_hand_built_one(self):
        """`load()` may not smuggle the checkout location into the identity."""
        loaded = inventory_model.fixture('openstack-reference')
        self.assertEqual(loaded.reference, _inventory(POSIX_ORIGIN).reference)
        self.assertEqual(_plan(loaded).digest, _plan(_inventory(POSIX_ORIGIN)).digest)
        self.assertEqual(loaded.origin, POSIX_ORIGIN)
        self.assertNotIn('\\', loaded.origin)


class ViewIdentityTest(unittest.TestCase):
    """Both derived views cite the reviewed identity, not the read location."""

    def test_capacity_view_digest_is_path_independent(self):
        posix = _plan(_inventory(POSIX_ORIGIN))
        windows = _plan(_inventory(WINDOWS_ORIGIN))
        self.assertEqual(owner.view_digest(posix), owner.view_digest(windows))
        self.assertEqual(owner.capacity_view(posix)['inventory'],
                         owner.capacity_view(windows)['inventory'])

    def test_address_view_digest_is_path_independent(self):
        posix = _plan(_inventory(POSIX_ORIGIN))
        windows = _plan(_inventory(WINDOWS_ORIGIN))
        self.assertEqual(addresses.address_view(posix)['inventory'],
                         addresses.address_view(windows)['inventory'])
        self.assertEqual(addresses.address_view(posix)['digest'],
                         addresses.address_view(windows)['digest'])

    def test_a_view_carries_exactly_the_declared_inventory_reference(self):
        view = addresses.address_view(_plan(_inventory(POSIX_ORIGIN)))
        self.assertEqual(sorted(view['inventory']),
                         ['authoritative', 'digest', 'source', 'status'])
        self.assertNotIn('\\', json.dumps(view, sort_keys=True))


class GoldenCrossPlatformIdentityTest(unittest.TestCase):
    """The recorded corpus is reproducible from a POSIX-relative fixture origin."""

    def test_golden_plan_identity_is_cross_platform(self):
        corpus = json.loads((support.GOLDEN / 'cross-platform.digests.json')
                            .read_text(encoding='utf-8'))
        self.assertEqual(sorted(corpus['fixtures']), sorted(support.REFERENCE_FIXTURES))
        for platform, name in sorted(support.REFERENCE_FIXTURES.items()):
            with self.subTest(platform=platform):
                origin = corpus['fixtures'][platform]
                self.assertNotIn('\\', origin)
                self.assertFalse(Path(origin).is_absolute())
                loaded = inventory_model.fixture(name)
                self.assertEqual(loaded.origin, origin)
                self.assertEqual(_inventory(origin, name).reference, loaded.reference)

    def test_every_recorded_cell_reproduces_from_a_posix_origin(self):
        corpus = json.loads((support.GOLDEN / 'cross-platform.digests.json')
                            .read_text(encoding='utf-8'))
        for name, entry in sorted(corpus['requests'].items()):
            for platform, expected in sorted(entry['platforms'].items()):
                with self.subTest(request=name, platform=platform):
                    plan = support.platform_plan(platform, name)
                    self.assertEqual(expected['plan_digest'], plan.digest)
                    self.assertEqual(expected['manifest_digest'], plan.manifest_digest)
                    self.assertNotIn('\\', json.dumps(plan.manifest, sort_keys=True))


if __name__ == '__main__':
    unittest.main()