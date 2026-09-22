"""The request contract and the versioned schema registry.

Every artifact the pipeline produces must satisfy the schema registered for it, and
the validator must fail closed on anything outside its reviewed subset.
"""
from __future__ import annotations

import unittest

from provisioner.schemas import registry

from tests.provisioning import support


class RegistryTest(unittest.TestCase):
    def test_every_registered_schema_exists_and_parses(self):
        for name in registry.SCHEMAS:
            schema = registry.load_schema(name)
            self.assertEqual(schema['type'], 'object', name)
            self.assertTrue(schema['$id'].startswith('hosting.platform/v1/'), name)

    def test_an_unknown_schema_name_is_refused(self):
        with self.assertRaises(ValueError):
            registry.load_schema('workload-security-domain/v2')

    def test_only_reviewed_keywords_are_declared(self):
        for name in registry.SCHEMAS:
            problems: list[dict] = []
            registry._unsupported(registry.load_schema(name), '$', problems)
            self.assertEqual(problems, [], name)

    def test_the_reviewed_request_contract_validates(self):
        self.assertEqual(
            registry.validate_named(support.reference_document(),
                                    'workload-security-domain'), [])

    def test_the_resolved_desired_state_validates(self):
        plan = support.reference_plan()
        self.assertEqual(
            registry.validate_named(plan.desired_state.to_dict(),
                                    'resolved-desired-state'), [])

    def test_the_placement_decision_validates(self):
        plan = support.reference_plan()
        self.assertEqual(
            registry.validate_named(plan.decision.to_dict(), 'placement-decision'), [])

    def test_the_conformance_report_validates(self):
        plan = support.reference_plan()
        self.assertEqual(
            registry.validate_named(plan.conformance, 'conformance-report'), [])


class FailClosedTest(unittest.TestCase):
    def test_a_native_identifier_in_the_request_is_refused(self):
        document = support.reference_document()
        document['spec']['platform']['project_id'] = 'native-value'
        problems = registry.validate_named(document, 'workload-security-domain')
        self.assertTrue(any('Unknown property' in p['message'] for p in problems))

    def test_an_unknown_kind_is_refused(self):
        document = support.reference_document()
        document['kind'] = 'VirtualMachine'
        problems = registry.validate_named(document, 'workload-security-domain')
        self.assertTrue(any(p['path'] == '$.kind' for p in problems))

    def test_an_unknown_api_version_is_refused(self):
        document = support.reference_document()
        document['apiVersion'] = 'hosting.platform/v2'
        problems = registry.validate_named(document, 'workload-security-domain')
        self.assertTrue(any(p['path'] == '$.apiVersion' for p in problems))

    def test_a_missing_required_section_is_refused(self):
        document = support.reference_document()
        del document['spec']['placement']
        problems = registry.validate_named(document, 'workload-security-domain')
        self.assertTrue(any(p['path'] == '$.spec.placement' for p in problems))

    def test_an_invalid_tenant_name_is_refused(self):
        document = support.reference_document()
        document['metadata']['tenant'] = 'Tenant_01'
        problems = registry.validate_named(document, 'workload-security-domain')
        self.assertTrue(any(p['path'] == '$.metadata.tenant' for p in problems))

    def test_a_hold_decision_still_validates(self):
        from provisioner.domain.placement import FIXTURE, PlacementDecision, finalize
        held = finalize(PlacementDecision(status='HOLD_NO_ELIGIBLE_PLATFORM', authority=FIXTURE,
                                          request_digest='a' * 64,
                                          selection_rule='highest-capability-count'))
        self.assertTrue(held.digest)
        self.assertTrue(held.held)
        self.assertEqual(
            registry.validate_named(held.to_dict(), 'placement-decision'), [])

    def test_an_authoritative_placement_decision_validates(self):
        from provisioner.domain.placement import (AUTHORITATIVE, PLACED, PlacementDecision,
                                                 finalize)
        from provisioner.placement import eligibility
        placed = finalize(PlacementDecision(
            status=PLACED, authority=AUTHORITATIVE, request_digest='a' * 64,
            selection_rule='highest-capability-count',
            qualification=eligibility.RepositoryQualification().to_dict(eligibility.PLATFORMS)))
        self.assertTrue(placed.authorized)
        self.assertEqual(
            registry.validate_named(placed.to_dict(), 'placement-decision'), [])

    def test_a_decision_without_a_recorded_qualification_is_never_authorized(self):
        from provisioner.domain.placement import (AUTHORITATIVE, PLACED, PlacementDecision,
                                                 finalize)
        placed = finalize(PlacementDecision(status=PLACED, authority=AUTHORITATIVE,
                                            request_digest='a' * 64,
                                            selection_rule='highest-capability-count'))
        self.assertFalse(placed.authorized)
        self.assertEqual(placed.to_dict()['qualification']['source'], 'UNRECORDED')
        self.assertEqual(
            registry.validate_named(placed.to_dict(), 'placement-decision'), [])

    def test_a_declared_qualification_never_authorizes(self):
        from provisioner.domain.placement import (AUTHORITATIVE, PLACED, PlacementDecision,
                                                 finalize)
        from provisioner.placement import eligibility
        placed = finalize(PlacementDecision(
            status=PLACED, authority=AUTHORITATIVE, request_digest='a' * 64,
            selection_rule='highest-capability-count',
            qualification=eligibility.demonstration().to_dict(eligibility.PLATFORMS)))
        self.assertFalse(placed.authorized)
        self.assertEqual(
            registry.validate_named(placed.to_dict(), 'placement-decision'), [])

    def test_an_unknown_placement_status_is_refused(self):
        from provisioner.domain.placement import FIXTURE, PlacementDecision
        with self.assertRaises(ValueError):
            PlacementDecision(status='PROBABLY_FINE', authority=FIXTURE,
                              request_digest='a' * 64)

    def test_an_unknown_placement_authority_is_refused(self):
        from provisioner.domain.placement import PLACED, PlacementDecision
        with self.assertRaises(ValueError):
            PlacementDecision(status=PLACED, authority='VIBES', request_digest='a' * 64)

    def test_an_unknown_conformance_status_is_refused(self):
        plan = support.reference_plan()
        report = dict(plan.conformance)
        report['status'] = 'PROBABLY_FINE'
        problems = registry.validate_named(report, 'conformance-report')
        self.assertTrue(any(p['path'] == '$.status' for p in problems))


class SchemaSubsetTest(unittest.TestCase):
    def test_an_unsupported_keyword_fails_closed(self):
        problems: list[dict] = []
        registry._unsupported({'type': 'object', 'x-vendor': 1}, '$', problems)
        self.assertTrue(problems)

    def test_min_properties_is_enforced(self):
        schema = {'type': 'object', 'minProperties': 2}
        self.assertTrue(registry.validate({}, schema))
        self.assertEqual(registry.validate({'a': 1, 'b': 2}, schema), [])

    def test_an_external_schema_reference_is_refused(self):
        with self.assertRaises(ValueError):
            registry.validate({}, {'$ref': 'https://example.invalid/schema.json'})

    def test_an_internal_reference_resolves(self):
        schema = {'definitions': {'row': {'type': 'string'}},
                  '$ref': '#/definitions/row'}
        self.assertEqual(registry.validate('ok', schema), [])
        self.assertTrue(registry.validate(1, schema))


if __name__ == '__main__':
    unittest.main()