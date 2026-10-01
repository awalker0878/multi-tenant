"""Catalog types and cross-profile obligations fail before native placement."""
from __future__ import annotations

import copy
import unittest

from provisioner.compiler import normalize, profiles
from provisioner.domain.errors import ProvisioningError
from provisioner.execution.plan import create_plan, validate_request
from provisioner.inventory.model import fixture
from provisioner.profiles.requirements import _FIELDS, _OPTIONAL
from tests.provisioning import support
from tests.provisioning.policy.test_profile_versions import _edit, edited_catalogs


def change_requirement(family, key, value):
    return edited_catalogs(lambda root: _edit(root / family / 'catalog.json',
        lambda doc: doc['profiles'][0]['requires'].__setitem__(key, value)))


class RequirementContractTests(unittest.TestCase):
    def test_every_required_field_is_checked_before_resolver_subscripts(self):
        for family, fields in _FIELDS.items():
            for key in fields.keys() - _OPTIONAL.get(family, frozenset()):
                with self.subTest(family=family, key=key), self.assertRaises(ProvisioningError):
                    edited_catalogs(lambda root: _edit(root / family / 'catalog.json',
                        lambda doc: doc['profiles'][0]['requires'].pop(key)))

    def test_quantities_reject_boolean_string_float_negative_and_overflow(self):
        for family, fields in _FIELDS.items():
            for key, expected in fields.items():
                if not isinstance(expected, tuple):
                    continue
                for value in (True, False, '1', 1.0, None, expected[1]-1, expected[2]+1):
                    with self.subTest(family=family, key=key, value=value), self.assertRaises(ProvisioningError):
                        change_requirement(family, key, value)

    def test_policy_booleans_are_not_truthy_strings_or_numbers(self):
        for family, fields in _FIELDS.items():
            for key, expected in fields.items():
                if expected is not bool:
                    continue
                for value in ('false', 'true', 0, 1, None, [], {}):
                    with self.subTest(family=family, key=key, value=value), self.assertRaises(ProvisioningError):
                        change_requirement(family, key, value)

    def test_relationships_are_explicit_bounded_unique_names(self):
        for family, key in (('availability', 'zones'), ('security', 'zones'), ('recovery', 'services')):
            for value in ([], 'OZ', ['OZ', 'OZ'], [None], [''], ['OZ\n'],
                          [str(n) for n in range(65)]):
                with self.subTest(family=family, value=value), self.assertRaises(ProvisioningError):
                    change_requirement(family, key, value)

    def test_text_fields_are_not_silently_defaulted_or_coerced(self):
        for family, fields in _FIELDS.items():
            for key, expected in fields.items():
                if expected is not str:
                    continue
                for value in ('', ' ', 'name\n', 'name\x00', 'x'*129, False, 1, [], None):
                    with self.subTest(family=family, key=key, value=value), self.assertRaises(ProvisioningError):
                        change_requirement(family, key, value)

    def test_address_parameters_must_fit_the_declared_family(self):
        for key, value in (('address_family', 'auto'), ('prefix_length', 33),
                           ('gateway_host_number', 32)):
            with self.subTest(key=key), self.assertRaises(ProvisioningError):
                change_requirement('network', key, value)
        with self.assertRaises(ProvisioningError):
            change_requirement('placement', 'selection', 'random-unimplemented')

    def test_explicit_false_and_zero_data_disk_remain_valid(self):
        catalog = change_requirement('assurance', 'recovery_required', False)
        self.assertIs(catalog.get('assurance', 'standard').requires['recovery_required'], False)
        self.assertEqual(change_requirement('storage', 'data_disk_gib', 0)
                         .get('storage', 'standard').requires['data_disk_gib'], 0)

    def test_assurance_recovery_has_one_owner_in_standalone_and_full_validation(self):
        document = copy.deepcopy(support.reference_document('internal-development'))
        document['spec']['assurance'] = {'profile': 'elevated'}
        document['spec']['recovery'] = {'enabled': False}
        catalog = support.catalogs()
        request = normalize.normalize(document, source='<test>')
        resolved = profiles.resolve(request, catalog)
        errors = profiles.validate(resolved, catalog).errors
        self.assertEqual(sum('Assurance profile' in error.message for error in errors), 1)
        with self.assertRaises(ProvisioningError) as caught:
            validate_request(document, '<test>', catalog)
        diagnostic = caught.exception.details['diagnostics']
        self.assertEqual(sum('Assurance profile' in error['message'] for error in diagnostic), 1)

    def test_availability_minimum_is_enforced_before_placement(self):
        catalog = edited_catalogs(lambda root: _edit(root / 'availability/catalog.json',
            lambda doc: next(row for row in doc['profiles'] if row['profile'] == 'high')
                ['requires'].__setitem__('min_workloads_per_zone', 2)))
        with self.assertRaises(ProvisioningError) as caught:
            create_plan(support.reference_document(), '<test>', fixture(), catalog)
        self.assertEqual(caught.exception.code, 'POLICY_VIOLATION')
        self.assertIn('workload count', caught.exception.message)

    def test_recovery_zone_cannot_be_outside_the_selected_composition(self):
        document = copy.deepcopy(support.reference_document('internal-development'))
        document['spec']['availability'] = {'profile': 'single-zone'}
        document['spec']['recovery'] = {'enabled': True, 'profile': 'standard'}
        with self.assertRaises(ProvisioningError) as caught:
            validate_request(document, '<test>', support.catalogs())
        self.assertTrue(any('Recovery zone' in error['message']
                            for error in caught.exception.details['diagnostics']))

    def test_independent_recovery_cannot_be_enabled_by_relabelling_a_profile(self):
        catalog = change_requirement('recovery', 'independent_site', True)
        with self.assertRaises(ProvisioningError) as caught:
            validate_request(support.reference_document('recovery-enabled'), '<test>', catalog)
        self.assertEqual(caught.exception.code, 'UNSUPPORTED_FEATURE')
        self.assertIn('Independent-site recovery', caught.exception.message)

    def test_valid_reference_profiles_do_not_gain_execution_authority(self):
        for name in support.REFERENCE_REQUESTS:
            plan = support.reference_plan(name)
            self.assertFalse(plan.native_contact)
            self.assertFalse(plan.decision.authorized)
            self.assertEqual(plan.status, 'PLANNED_DISABLED_NOT_AUTHORIZED')


if __name__ == '__main__':
    unittest.main()
