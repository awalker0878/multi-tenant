"""Synthetic custody chains prove admission boundaries, never native support."""
from copy import deepcopy
from dataclasses import replace
import unittest

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.qualification.directed_mobility import (
    IMPLEMENTATIONS, campaign_implementation_blockers, expansion_assertions,
    require_implemented_action_selection,
)
from provisioner.qualification.mobility import (
    CampaignEndpoint, METHODS, PLATFORMS, GUESTS, assess, unsupported_matrix,
)
from tests.provisioning.operations.campaign_fixtures import AS_OF, fixture
from tests.qualification_fixture_support import campaign_record


def complete_chain_for_method(method):
    """Rebuild the existing exported evidence contract for a selected method."""
    original, bundle, selection = fixture()
    spec = replace(original, method=method)
    for number, (side, endpoint) in enumerate((('source', spec.source), ('destination', spec.destination))):
        q = bundle['qualification']['records'][number]
        target = bundle['targetSelection']['records'][number]
        required = spec.assertions()
        refs = ['controlled-expansion:' + side + ':' + assertion for assertion in required]
        exported = campaign_record(refs, endpoint.platform, endpoint.product_tuple_id,
            campaign_id=endpoint.campaign_id, selection_id=endpoint.selection_id,
            site_ref=target['scope']['site_ref'], cell_ref=target['scope']['cell_ref'],
            campaign_scope_ref=target['scope']['campaign_scope_ref'])
        exported['required_assertions'] = list(required)
        for attempt, (assertion, observation_class) in zip(exported['attempts'], required.items()):
            attempt.update(assertion_id=assertion, observation_class=observation_class,
                           attempt_id=side + '-' + assertion, variant_ref=spec.variant_ref)
            if observation_class == 'NEGATIVE_CONTROL':
                attempt['positive_control_attempt_ref'] = side + '-DISCOVERY_INDEPENDENT'
        q['evidence'] = [{'ref': row['evidence_ref'], 'sha256': row['artifact_sha256'],
                         'observed_at': row['observed_at'], 'expires_at': row['fresh_until'],
                         'test_set': 'CT-FIXTURE'} for row in exported['attempts']]
        q['tested_limits'][0]['evidence_ref'] = refs[0]
        bundle['campaign']['records'][number] = exported
    return spec, bundle, selection


def assessment(spec, bundle):
    return assess(spec, qualification_index=bundle['qualification'], provenance_index=bundle['provenance'],
                  campaign_index=bundle['campaign'], selection_index=bundle['targetSelection'], as_of=AS_OF)


class DirectedAdmissionTests(unittest.TestCase):
    def test_all_other_directions_methods_and_guest_profiles_remain_unimplemented(self):
        base, _, _ = fixture()
        available = []
        for source in PLATFORMS:
            for target in PLATFORMS:
                for method in METHODS:
                    if method == 'SAME_FAMILY_RELOCATION' and source != target:
                        continue
                    for guest in GUESTS:
                        spec = replace(base,
                            source=CampaignEndpoint(source, 'source-tuple', 'source-selection', 'SOURCE-CAMPAIGN'),
                            destination=CampaignEndpoint(target, 'destination-tuple', 'destination-selection', 'DESTINATION-CAMPAIGN'),
                            method=method, guest_profile=guest)
                        if not campaign_implementation_blockers(spec):
                            available.append((source, target, method, guest))
        self.assertEqual(set(available), set(IMPLEMENTATIONS))
        self.assertEqual(len(available), 1)

    def test_complete_synthetic_cold_chain_cannot_supply_a_missing_native_export_driver(self):
        spec, bundle, _ = complete_chain_for_method('COLD_WHOLE_VM')
        result = assessment(spec, bundle)
        self.assertEqual(len(result['retainedEvidence']), 2 * len(spec.assertions()))
        self.assertEqual(result['status'], 'UNSUPPORTED_HELD')
        self.assertIn('NATIVE_COLD_CAPTURE_EXPORT_OWNER_MISSING', result['blockers'])
        self.assertIn('TARGET_IMAGE_IMPORT_AND_BOOT_OWNER_MISSING', result['blockers'])
        self.assertFalse(result['mutationAuthorized'])

    def test_complete_database_or_warm_chain_cannot_claim_vm_or_committed_data_support(self):
        for method, blocker in (
            ('APPLICATION_NATIVE_DATABASE_SYNC', 'COMMIT_POSITION_AND_DIVERGENCE_OWNER_MISSING'),
            ('WARM_WHOLE_VM', 'RAM_DEVICE_AND_KEY_STATE_PRESERVATION_UNIMPLEMENTED')):
            with self.subTest(method=method):
                spec, bundle, _ = complete_chain_for_method(method)
                result = assessment(spec, bundle)
                self.assertEqual(len(result['retainedEvidence']), 2 * len(spec.assertions()))
                self.assertEqual(result['status'], 'UNSUPPORTED_HELD')
                self.assertIn(blocker, result['blockers'])

    def test_whole_vm_negative_controls_retain_positive_control_and_exact_variant_binding(self):
        spec, bundle, _ = complete_chain_for_method('COLD_WHOLE_VM')
        assertions = spec.assertions()
        self.assertEqual(assertions['BROKEN_DISK_CHAIN_REJECTED'], 'NEGATIVE_CONTROL')
        self.assertEqual(assertions['ENCRYPTED_OR_VTPM_DEVICE_REJECTED'], 'NEGATIVE_CONTROL')
        self.assertEqual(assertions['PASSTHROUGH_OR_SHARED_DISK_REJECTED'], 'NEGATIVE_CONTROL')
        exported = bundle['campaign']['records'][0]
        negative = next(row for row in exported['attempts'] if row['assertion_id'] == 'BROKEN_DISK_CHAIN_REJECTED')
        negative['positive_control_attempt_ref'] = None
        with self.assertRaises(ValueError):
            assessment(spec, bundle)

    def test_direction_guest_job_method_and_artifact_changes_do_not_borrow_exact_evidence(self):
        spec, bundle, _ = fixture()
        changed_specs = (
            replace(spec, source=spec.destination, destination=spec.source),
            replace(spec, guest_profile='LINUX'),
            replace(spec, guest_profile='windows-server-2022'),
            replace(spec, job_id='another-job'),
            replace(spec, installed_artifact_sha256='f' * 64),
            replace(spec, code_revision='d' * 40),
        )
        for changed in changed_specs:
            with self.subTest(route=changed.route_id, job=changed.job_id):
                self.assertEqual(assessment(changed, bundle)['status'], 'UNSUPPORTED_HELD')

    def test_same_family_is_topology_specific_and_never_cross_family(self):
        spec, _, _ = fixture()
        same = replace(spec, destination=CampaignEndpoint('vmware-nsx', 'destination-tuple',
                            'destination-selection', 'DESTINATION-CAMPAIGN'), method='SAME_FAMILY_RELOCATION')
        self.assertIn('QUALIFIED_TOPOLOGY_RELOCATION_DRIVER_MISSING', campaign_implementation_blockers(same))
        self.assertIn('SAME_RESOURCE_NOOP_REJECTED', same.assertions())
        with self.assertRaises(ValueError):
            replace(spec, method='SAME_FAMILY_RELOCATION')

    def test_installed_driver_never_accepts_broad_guest_or_reverse_or_fake_driver(self):
        _, _, selection = fixture()
        implementation = require_implemented_action_selection(selection)
        self.assertEqual(implementation.guest_profile, 'linux-ubuntu-2404')
        for mutation in (
            lambda value: value.update(guestProfile='LINUX'),
            lambda value: value.update(guestProfile='windows-server-2022'),
            lambda value: value.update(driver='caller-supplied-cold-driver'),
            lambda value: value.update(source=value['destination'], destination=value['source']),
            lambda value: value['destination'].update(tenantId='foreign-tenant'),
            lambda value: value['source'].update(nativeScopeId=''),
        ):
            changed = deepcopy(selection); mutation(changed)
            with self.subTest(selection=changed['guestProfile']), self.assertRaises(AuthorityDenied):
                require_implemented_action_selection(changed)

    def test_wave_assertions_require_explicit_applicability_and_do_not_qualify_single_job(self):
        basic = expansion_assertions('APPLICATION_REBUILD_RESTORE')
        wave = expansion_assertions('APPLICATION_REBUILD_RESTORE', include_wave=True)
        self.assertNotIn('WAVE_CONCURRENT_RESOURCE_BUDGET_STOP', basic)
        self.assertIn('WAVE_CONCURRENT_RESOURCE_BUDGET_STOP', wave)
        self.assertIn('WAVE_SHARED_RISK_CONTAINED', wave)
        with self.assertRaises(ValueError):
            expansion_assertions('APPLICATION_REBUILD_RESTORE', include_wave='yes')

    def test_matrix_preserves_each_unimplemented_extension_even_after_complete_cold_evidence(self):
        cold, bundle, _ = complete_chain_for_method('COLD_WHOLE_VM')
        matrix = unsupported_matrix([assessment(cold, bundle)])
        rows = {row['routeId']: row for row in matrix['routes']}
        self.assertEqual(rows[cold.route_id]['status'], 'UNSUPPORTED_HELD')
        self.assertEqual(rows['nutanix:vmware-nsx:APPLICATION_REBUILD_RESTORE:linux-ubuntu-2404']['status'], 'UNSUPPORTED_HELD')
        self.assertEqual(rows['openstack:nutanix:APPLICATION_REBUILD_RESTORE:windows-server-2022']['status'], 'UNSUPPORTED_HELD')


if __name__ == '__main__':
    unittest.main()
