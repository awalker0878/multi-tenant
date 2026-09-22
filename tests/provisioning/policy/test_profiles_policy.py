"""Profile catalogs, resolution and the reviewed standards policy."""
from __future__ import annotations

import copy
import unittest

from provisioner.compiler import normalize, profiles
from provisioner.domain.errors import Diagnostics, ProvisioningError
from provisioner.policy import diagnostics as policy_diagnostics
from provisioner.policy import semantic, standards
from provisioner.profiles import loader
from tests.provisioning.support import catalogs, reference_document

RESOLVED_FAMILIES = ('assurance', 'availability', 'compute', 'environment', 'network',
                     'placement', 'recovery', 'security', 'services', 'storage')


class CatalogTest(unittest.TestCase):
    def test_every_family_is_catalogued(self):
        catalog = catalogs()
        self.assertEqual(sorted(catalog.families), sorted(loader.FAMILIES))

    def test_every_family_offers_an_implemented_profile(self):
        catalog = catalogs()
        for family in loader.FAMILIES:
            implemented = [p for p in catalog.family(family).values() if p.implemented]
            self.assertTrue(implemented, f'{family} has no implemented profile')

    def test_ranks_are_unique_within_a_namespace(self):
        catalog = catalogs()
        for family in loader.FAMILIES:
            seen: dict[tuple[str, int], str] = {}
            for profile in catalog.family(family).values():
                namespace = profile.profile.split('/', 1)[0]
                key = (namespace, profile.rank)
                self.assertNotIn(key, seen, f'duplicate rank in {family}')
                seen[key] = profile.profile

    def test_deferred_profiles_are_declared_not_hidden(self):
        catalog = catalogs()
        deferred = [p for family in loader.FAMILIES
                    for p in catalog.family(family).values() if not p.implemented]
        for profile in deferred:
            self.assertEqual(profile.status, loader.DEFERRED)
            self.assertTrue(profile.limits, f'{profile.profile} must state its limits')

    def test_unknown_family_and_profile_are_refused(self):
        catalog = catalogs()
        with self.assertRaises(ProvisioningError):
            catalog.get('nonexistent', 'default')
        with self.assertRaises(ProvisioningError):
            catalog.get('environment', 'nonexistent')


class ResolutionTest(unittest.TestCase):
    def setUp(self):
        self.document = reference_document()
        self.catalog = catalogs()

    def resolve(self):
        request = normalize.normalize(copy.deepcopy(self.document), source='<test>')
        return profiles.resolve(request, self.catalog)

    def test_resolution_names_every_family(self):
        self.assertEqual(sorted(self.resolve().profiles), list(RESOLVED_FAMILIES))

    def test_resolution_is_deterministic(self):
        self.assertEqual(self.resolve().to_dict(), self.resolve().to_dict())

    def test_resolution_carries_no_platform_decision(self):
        resolution = self.resolve()
        self.assertTrue(resolution.trust)
        self.assertTrue(resolution.service_class)
        self.assertTrue(resolution.required_capabilities)
        self.assertNotIn('platform', resolution.profiles)

    def test_unknown_profile_in_the_request_is_refused(self):
        document = copy.deepcopy(self.document)
        document['spec']['environment'] = 'nonexistent'
        request = normalize.normalize(document, source='<test>')
        with self.assertRaises(ProvisioningError) as caught:
            profiles.resolve(request, self.catalog)
        self.assertEqual(caught.exception.code, 'UNSUPPORTED_PROFILE')


class PolicyTest(unittest.TestCase):
    def test_rules_are_reviewed_and_unique(self):
        rules = standards.load_rules()
        self.assertTrue(rules)
        identifiers = [r['rule'] for r in rules]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        for rule in rules:
            self.assertTrue(rule.get('description'))
            self.assertTrue(rule.get('when'))
            self.assertTrue({'require', 'forbid'} & set(rule))

    def test_reference_request_satisfies_the_standards(self):
        request = normalize.normalize(copy.deepcopy(reference_document()), source='<test>')
        resolution = profiles.resolve(request, catalogs())
        errors = semantic.validate(request.document, resolution, catalogs()).errors
        diagnostics = Diagnostics()
        findings = policy_diagnostics.collect(request.document, standards.load_rules(),
                                             diagnostics)
        self.assertEqual(errors, [])
        self.assertEqual(findings, [])
        self.assertEqual(diagnostics.errors, [])

    def test_policy_summary_states_what_it_did_not_do(self):
        request = normalize.normalize(copy.deepcopy(reference_document()), source='<test>')
        rules = standards.load_rules()
        diagnostics = Diagnostics()
        violations = policy_diagnostics.collect(request.document, rules, diagnostics)
        summary = policy_diagnostics.summary(diagnostics, violations, len(rules))
        self.assertEqual(summary['rules_evaluated'], len(rules))
        self.assertEqual(summary['rules_failed'], [])
        self.assertEqual(summary['errors'], 0)


if __name__ == '__main__':
    unittest.main()