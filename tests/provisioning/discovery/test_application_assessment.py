"""Real signed owner review plus synthetic inventories; never native qualification."""
import copy
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from provisioner.controlplane.discovery.application_assessment import (
    ApplicationAssessmentService, ApplicationMemberProfile, aggregate_capacity)
from provisioner.controlplane.discovery.application_drafts import ApplicationDraftRepository, StoredApplicationDraft, _digest
from provisioner.controlplane.discovery.application_reviews import ApplicationReviewService, ApplicationReviewUnavailable, _view
from provisioner.controlplane.discovery.assessment_inputs import parse_evidence
from provisioner.controlplane.discovery.grouping import (
    GroupDraft, GroupMember, ConsistencyProposal, DependencyAssertion, proposal_document)
from provisioner.controlplane.discovery.model import DiscoveryFact, _json
from provisioner.controlplane.discovery.service import (
    AssessmentDestination, AssessmentMember, AssessmentSelection, AssessmentService)
from tests.provisioning.discovery.test_service import Repository, VerifiedInputs, INSTALLATIONS, CTX, NOW
from tests.provisioning.discovery.test_application_review import OwnerFixture, review_document


def field(obj, name, value):
    return replace(obj, facts=tuple(f for f in obj.facts if f.name != name) + (DiscoveryFact.known(name, value),))


class Drafts(ApplicationDraftRepository):
    def __init__(self, stored):
        self.stored, self.calls, self.corrupt = stored, 0, {}
    def get(self, ctx, scope, environment_id, application_group_id, *, revision, authorize):
        authorize(scope, NOW); self.calls += 1
        return {**self.stored.document(latest_generation=self.stored.generation), **self.corrupt}


class Reviews(ApplicationReviewService):
    def __init__(self, stored, result, fixture):
        self.stored, self.result, self.fixture = stored, result, fixture
        self.document = review_document(stored)
        self.signatures = fixture.sign(self.document)
        self.calls, self.before, self.missing, self.none = 0, None, False, False
        self.latest_generation, self.latest_revision = 7, 1
    def get(self, ctx, scope, environment_id, application_group_id, *, revision, authorize):
        authorize(scope, NOW); self.calls += 1
        if self.before: self.before(self.calls)
        if self.missing: return None
        evidence = parse_evidence(self.document)
        self.fixture.trust.verify(evidence, self.signatures, NOW)
        return _view(self.stored, self.result, None if self.none else evidence,
                     self.latest_generation, self.latest_revision, NOW)


class ApplicationAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.repository, self.inputs = Repository(), VerifiedInputs()
        for name in ('target-a', 'target-b'):
            target = self.repository.results[name, 7]
            self.repository.results[name, 7] = replace(target,
                objects=(field(target.objects[0], 'availableVmCount', 100),))
        original = self.repository.results['source', 7]
        vm1 = original.objects[0]
        vm2 = replace(vm1, identity=replace(vm1.identity, native_id='vm-2'))
        self.result = replace(original, objects=(vm1, vm2))
        self.repository.results['source', 7] = self.result
        self.draft = GroupDraft('app-1', 'Application', 'owner-a',
            (GroupMember('db', vm1.identity), GroupMember('web', vm2.identity)),
            ('db-data', 'web-data'), (ConsistencyProposal('all-data', ('db-data', 'web-data')),), ('db', 'web'))
        self.edges = (DependencyAssertion('edge', 'web', 'db', 'STARTS_AFTER', 'KNOWN',
                        'APPLICATION_OWNER', 'review-1', self.result.captured_at),)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.bind()
        self.inputs.qualified = True
        self.assessment = AssessmentService(self.repository, self.inputs, clock=lambda: NOW)
        self.service = ApplicationAssessmentService(self.drafts, self.reviews, self.assessment)
        self.destinations = tuple(AssessmentDestination(AssessmentSelection(name, 7), 'pool', 'pool-1')
                                   for name in ('target-a', 'target-b'))
        self.profiles = (ApplicationMemberProfile('db', 'linux-uefi'), ApplicationMemberProfile('web', 'linux-uefi'))

    def bind(self):
        proposal = proposal_document(self.result, self.draft, self.edges)
        self.stored = StoredApplicationDraft('source', self.result.scope, 'app-1', 1, 7,
            self.result.digest, _json(proposal), _digest(proposal), 'editor-a', self.result.captured_at, '')
        self.stored = replace(self.stored, record_digest=_digest(self.stored.binding()))
        self.fixture = OwnerFixture(Path(self.temp.name)/'trust.json', self.stored)
        self.drafts, self.reviews = Drafts(self.stored), Reviews(self.stored, self.result, self.fixture)
        if hasattr(self, 'assessment'):
            self.service = ApplicationAssessmentService(self.drafts, self.reviews, self.assessment)

    def compare(self, **changes):
        params = dict(revision=1, record_digest=self.stored.record_digest, profiles=self.profiles,
            destinations=self.destinations, method='COLD_VM_CONVERSION', network_mode='routed', data_mode='offline')
        params.update(changes)
        return self.service.compare(CTX, 'operator-1', AssessmentSelection('source', 7), 'app-1', **params)

    def test_every_member_is_compared_and_logical_demand_is_summed(self):
        doc = self.compare()
        self.assertEqual(doc['status'], 'ASSESSED_NOT_AUTHORIZED')
        self.assertEqual(doc['applicationReview']['candidateDigest'], self.reviews.get(
            CTX, self.result.scope, 'source', 'app-1', revision=1, authorize=lambda *a: None)['candidateDigest'])
        self.assertEqual(doc['startupOrder'], ['db', 'web'])
        for row in doc['assessments']:
            self.assertEqual(row['status'], 'CONDITIONAL')
            self.assertEqual(row['capacity']['resources']['VCPU']['required'], 8)
            self.assertEqual(row['capacity']['resources']['MEMORY']['required'], 16000)
            self.assertEqual(row['capacity']['resources']['STORAGE']['required'], 40000)
            self.assertEqual([member['workloadId'] for member in row['members']], ['db', 'web'])
            self.assertTrue(all(member['status'] == 'ELIGIBLE' for member in row['members']))
        for flag in ('executionAuthorized', 'ownershipAccepted', 'reservationHeld', 'dependencyEvidenceVerified'):
            self.assertIs(doc[flag], False)

    def test_members_fitting_separately_can_fail_combined_capacity_in_each_dimension(self):
        for native, label, amount in (('availableVcpu', 'VCPU', 6),
                ('availableMemoryBytes', 'MEMORY', 12000), ('availableStorageBytes', 'STORAGE', 30000)):
            old = self.repository.results['target-a', 7]
            self.repository.results['target-a', 7] = replace(old, objects=(field(old.objects[0], native, amount),))
            with self.subTest(resource=label):
                doc = self.compare(); a, b = doc['assessments']
                self.assertEqual(a['status'], 'BLOCKED'); self.assertEqual(b['status'], 'CONDITIONAL')
                self.assertTrue(all(member['status'] == 'ELIGIBLE' for member in a['members']))
                self.assertIn('APPLICATION_' + label + '_CAPACITY_INSUFFICIENT', {x['code'] for x in a['issues']})
            self.repository.results['target-a', 7] = old

    def test_instance_slots_are_not_inferred_from_vcpu_or_memory(self):
        old = self.repository.results['target-a', 7]
        self.repository.results['target-a', 7] = replace(old,
            objects=(field(old.objects[0], 'availableVmCount', 1),))
        row = self.compare()['assessments'][0]
        self.assertEqual(row['status'], 'BLOCKED')
        self.assertIn('APPLICATION_VM_COUNT_CAPACITY_INSUFFICIENT', {x['code'] for x in row['issues']})
        self.repository.results['target-a', 7] = replace(old,
            objects=(replace(old.objects[0], facts=tuple(f for f in old.objects[0].facts if f.name != 'availableVmCount')),))
        self.assertEqual(self.compare()['assessments'][0]['status'], 'UNKNOWN')

    def test_snapshot_hydration_happens_once_per_scope_not_per_vm(self):
        self.compare()
        self.assertEqual([x[:2] for x in self.repository.reads if x[2] == 'header'],
                         [('source', 7), ('target-a', 7), ('target-b', 7)])
        self.assertEqual(len([x for x in self.repository.reads if x[2] == 'objects']), 3)

    def test_unreviewed_revoked_partial_and_superseded_reviews_do_not_compare(self):
        for state in ('UNREVIEWED', 'REVOKED', 'PARTIAL', 'DRAFT', 'INVENTORY'):
            self.bind(); self.repository.reads.clear()
            if state == 'UNREVIEWED': self.reviews.none = True
            if state == 'REVOKED':
                self.reviews.document = review_document(self.stored, decision='REVOKE')
                self.reviews.signatures = self.fixture.sign(self.reviews.document)
            if state == 'PARTIAL': self.reviews.result = replace(self.result, completeness='PARTIAL', collection_errors=('VISIBLE_INVENTORY_ONLY',))
            if state == 'DRAFT': self.reviews.latest_revision = 2
            if state == 'INVENTORY': self.reviews.latest_generation = 8
            with self.subTest(state=state):
                # Partial's changed digest must not masquerade as the pinned result.
                if state == 'PARTIAL':
                    with self.assertRaises(ApplicationReviewUnavailable): self.compare()
                else:
                    doc = self.compare(); self.assertEqual(doc['status'], 'HELD_APPLICATION_REVIEW')
                    self.assertEqual(doc['assessments'], [])
                self.assertEqual(self.repository.reads, [])

    def test_unknown_dependencies_never_disappear_or_become_eligible(self):
        self.edges = (replace(self.edges[0], target_workload_id=None, relation='SERVICE_CALL',
                              state='UNKNOWN', unknown_reason='UNRESOLVED_TARGET'),)
        self.bind()
        doc = self.compare()
        self.assertEqual(doc['applicationReview']['unknownDependencyCount'], 1)
        self.assertTrue(all(row['status'] == 'UNKNOWN' for row in doc['assessments']))

    def test_unverified_cmdb_label_does_not_become_independent_dependency_evidence(self):
        self.edges = (replace(self.edges[0], source='CMDB'),); self.bind()
        doc = self.compare()
        for row in doc['assessments']:
            self.assertEqual(row['status'], 'UNKNOWN')
            self.assertIn('APPLICATION_DEPENDENCY_EVIDENCE_UNVERIFIED', {x['code'] for x in row['issues']})

    def test_all_source_and_destination_access_precedes_draft_or_inventory_reads(self):
        self.inputs.denied = 'target-b'
        with self.assertRaises(PermissionError): self.compare()
        self.assertEqual((self.reviews.calls, self.drafts.calls, self.repository.reads), (0, 0, []))

    def test_member_profiles_cannot_omit_add_duplicate_or_replace_members(self):
        for profiles in ((self.profiles[0],), self.profiles + (self.profiles[0],),
                (self.profiles[0], ApplicationMemberProfile('stranger', 'linux-uefi'))):
            with self.subTest(profiles=profiles), self.assertRaises(ValueError): self.compare(profiles=profiles)
        self.assertEqual(self.repository.reads, [])

    def test_different_member_guest_profiles_use_independent_route_checks(self):
        doc = self.compare(profiles=(self.profiles[0], ApplicationMemberProfile('web', 'windows')))
        for row in doc['assessments']:
            self.assertEqual(row['members'][0]['status'], 'ELIGIBLE')
            self.assertEqual(row['members'][1]['status'], 'BLOCKED')
            self.assertEqual(row['members'][1]['guestProfile'], 'windows')
            self.assertEqual(row['status'], 'BLOCKED')

    def test_destination_order_and_capacity_identity_remain_bound(self):
        doc = self.compare(destinations=tuple(reversed(self.destinations)))
        self.assertEqual([x['environmentId'] for x in doc['assessments']], ['target-b', 'target-a'])
        for row, pin in zip(doc['assessments'], doc['destinationInputs']):
            self.assertEqual(row['capacityIdentity'][0], pin['endpointId'])

    def test_unselected_pool_cannot_be_filled_from_a_different_pool(self):
        target = AssessmentDestination(self.destinations[0].selection, 'pool', 'missing')
        doc = self.compare(destinations=(target, self.destinations[1]))
        a, b = doc['assessments']
        self.assertEqual(a['status'], 'UNKNOWN'); self.assertEqual(b['status'], 'CONDITIONAL')
        self.assertIsNone(a['capacity']['resources']['VCPU']['available'])

    def test_owner_revocation_during_member_comparison_discards_report(self):
        def revoke(count):
            if count == 2:
                self.reviews.document = review_document(self.stored, decision='REVOKE', revision=2)
                self.reviews.signatures = self.fixture.sign(self.reviews.document)
        self.reviews.before = revoke
        with self.assertRaises(ApplicationReviewUnavailable): self.compare()
        self.assertTrue(self.repository.reads)

    def test_new_draft_during_comparison_cannot_inherit_old_acceptance(self):
        def change(count):
            if count == 2: self.reviews.latest_revision = 2
        self.reviews.before = change
        with self.assertRaises(ApplicationReviewUnavailable): self.compare()

    def test_record_digest_and_corrupt_proposal_are_not_reinterpreted(self):
        with self.assertRaises(ApplicationReviewUnavailable): self.compare(record_digest='f'*64)
        self.drafts.corrupt = {'proposal': {}}
        with self.assertRaises(ApplicationReviewUnavailable): self.compare()

    def test_missing_source_review_is_not_replaced_by_per_vm_route_claims(self):
        self.reviews.missing = True
        with self.assertRaises(LookupError): self.compare()
        self.assertEqual(self.repository.reads, [])

    def test_combination_budget_is_checked_before_any_io(self):
        profiles = tuple(ApplicationMemberProfile('vm-'+str(i), 'linux') for i in range(100))
        with self.assertRaises(ValueError): self.compare(profiles=profiles, destinations=self.destinations*2)
        self.assertEqual((self.reviews.calls, self.repository.reads), (0, []))

    def test_route_relocation_blocks_only_the_cross_family_destination(self):
        doc = self.compare(method='SAME_PLATFORM_RELOCATION')
        self.assertEqual(doc['assessments'][0]['status'], 'CONDITIONAL')
        self.assertEqual(doc['assessments'][1]['status'], 'BLOCKED')

    def test_resource_unknown_zero_boolean_and_overflow_are_not_zero_demand(self):
        for value in (None, True, 0, -1, 2**63-1):
            source = replace(self.result, objects=tuple(field(obj, 'vcpuCount', value) for obj in self.result.objects))
            capacity, issues = aggregate_capacity(source, tuple(m.native_vm for m in self.draft.members),
                                                  self.repository.results['target-a', 7].objects[0])
            with self.subTest(value=value):
                self.assertIsNone(capacity['resources']['VCPU']['required'])
                self.assertIn('APPLICATION_VCPU_DEMAND_UNKNOWN', {x['code'] for x in issues})
                self.assertIsNotNone(capacity['resources']['MEMORY']['required'])

    def test_batch_rejects_duplicate_native_identity(self):
        with self.assertRaises(ValueError):
            self.assessment.compare_many(CTX, 'operator-1', AssessmentSelection('source', 7),
                (AssessmentMember('vm-1', 'linux-uefi'),)*2, self.destinations,
                method='COLD_VM_CONVERSION', network_mode='routed', data_mode='offline')
        self.assertEqual(self.repository.reads, [])

    def test_late_inventory_generation_holds_all_members_not_just_last(self):
        calls = [0]; old = self.repository.latest_generation
        def latest(*args):
            calls[0] += 1
            if calls[0] == 7:
                self.repository.results['target-a', 8] = self.repository.results['target-a', 7]
            return old(*args)
        self.repository.latest_generation = latest
        doc = self.compare()
        self.assertTrue(all(row['status'] == 'UNKNOWN' for row in doc['assessments'][0]['members']))
        self.assertTrue(doc['destinationInputs'][0]['superseded'])

    def test_final_route_recheck_cannot_use_the_first_members_old_claim(self):
        count = [0]; old = self.inputs.route_claims
        def changed(*args):
            count[0] += 1
            return () if count[0] >= 3 else old(*args)
        self.inputs.route_claims = changed
        with self.assertRaises(PermissionError): self.compare()

    def test_oversized_report_is_refused_not_truncated_to_selected_members(self):
        with patch('provisioner.controlplane.discovery.application_assessment.MAX_RESPONSE_BYTES', 32):
            with self.assertRaises(ValueError): self.compare()

    def test_final_control_recheck_cannot_use_removed_security_evidence(self):
        count = [0]; old = self.inputs.reviewed_findings
        def changed(*args):
            count[0] += 1
            return () if count[0] >= 5 else old(*args)
        self.inputs.reviewed_findings = changed
        with self.assertRaises(PermissionError): self.compare()


if __name__ == '__main__':
    unittest.main()
