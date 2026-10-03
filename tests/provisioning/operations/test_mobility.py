from copy import deepcopy
from dataclasses import replace
import unittest

from provisioner.qualification.mobility import assess, unsupported_matrix, from_document
from tests.provisioning.operations.campaign_fixtures import AS_OF, fixture


class MobilityTests(unittest.TestCase):
    def run_assessment(self, spec, bundle):
        return assess(spec, qualification_index=bundle['qualification'],
            provenance_index=bundle['provenance'], campaign_index=bundle['campaign'],
            selection_index=bundle['targetSelection'], as_of=AS_OF)

    def test_complete_synthetic_native_chain_selects_only_its_exact_direction_method_and_profile(self):
        spec, bundle, _ = fixture()
        result = self.run_assessment(spec, bundle)
        self.assertEqual(result['status'], 'CURRENT_NATIVE_EVIDENCE_SELECTED')
        self.assertEqual(len(result['retainedEvidence']), 2 * len(spec.assertions()))
        self.assertFalse(result['qualificationIssued'])
        self.assertFalse(result['mutationAuthorized'])

    def test_route_method_guest_and_code_change_never_infers_support(self):
        spec, bundle, _ = fixture()
        for changed in (replace(spec, source=spec.destination, destination=spec.source),
                        replace(spec, method='COLD_WHOLE_VM'), replace(spec, guest_profile='WINDOWS'),
                        replace(spec, code_revision='d' * 40), replace(spec, job_id='different-job'),
                        replace(spec, installed_artifact_sha256='e' * 64)):
            with self.subTest(route=changed.route_id):
                self.assertEqual(self.run_assessment(changed, bundle)['status'], 'UNSUPPORTED_HELD')

    def test_revoked_dossier_cannot_supply_route_evidence(self):
        spec, bundle, _ = fixture()
        bundle['qualification']['records'] = []
        result = self.run_assessment(spec, bundle)
        self.assertEqual(result['status'], 'UNSUPPORTED_HELD')
        self.assertTrue(any('NO_CURRENT_EXACT_NATIVE_DOSSIER' in value for value in result['blockers']))

    def test_stale_contact_or_scope_mismatch_is_not_passed(self):
        spec, bundle, _ = fixture()
        bundle['campaign']['records'][0]['scope']['product_tuple_id'] = 'foreign-tuple'
        with self.assertRaises(ValueError):
            self.run_assessment(spec, bundle)
        spec, bundle, _ = fixture()
        bundle['qualification']['records'][0]['approval']['expires_at'] = '2026-10-01T00:00:00Z'
        with self.assertRaises(ValueError):
            self.run_assessment(spec, bundle)

    def test_unsupported_matrix_keeps_reverse_whole_vm_and_special_guest_rows(self):
        spec, bundle, _ = fixture()
        matrix = unsupported_matrix([self.run_assessment(spec, bundle)])
        rows = {row['routeId']: row for row in matrix['routes']}
        self.assertEqual(sum(row['status'] == 'CURRENT_NATIVE_EVIDENCE_SELECTED' for row in rows.values()), 1)
        self.assertEqual(rows['openstack:vmware-nsx:APPLICATION_REBUILD_RESTORE:LINUX']['status'], 'UNSUPPORTED_HELD')
        self.assertEqual(rows['vmware-nsx:openstack:COLD_WHOLE_VM:ENCRYPTED_VTPM']['status'], 'UNSUPPORTED_HELD')
        self.assertFalse(matrix['productionAuthorityIssued'])

    def test_run_sheet_preserves_not_run_external_campaign_and_strict_source_binding(self):
        spec, _, _ = fixture()
        sheet = spec.run_sheet()
        self.assertFalse(sheet['nativeContact'])
        self.assertIn('REVOKED_AUTHORITY_REJECTED', [r['assertionId'] for r in sheet['assertions']])
        changed = deepcopy(sheet)
        with self.assertRaises(ValueError):
            from_document(changed)


if __name__ == '__main__':
    unittest.main()
