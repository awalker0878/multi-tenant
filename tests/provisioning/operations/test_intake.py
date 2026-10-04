"""Cryptographic final-code evidence tests; no native/pilot observation claimed."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from provisioner.controlplane.persistence import TenantContext
from provisioner.qualification import mobility
from provisioner.qualification.intake import FinalEvidenceIntake
from tests.provisioning.operations.campaign_fixtures import AS_OF, fixture
from tests.provisioning.operations.signed_intake_fixtures import RetainedFixture, attach_native, signed, sha256
from tests.provisioning.operations.test_release import TestSigner


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.spec, self.bundle, _ = fixture()
        self.context = TenantContext('synthetic-intake-org', 'synthetic-intake-tenant')
        self.custody = RetainedFixture(self.context)
        self.observer = TestSigner('synthetic-independent-native-observer')
        attach_native(self.spec, self.bundle, self.custody, self.observer)
        self.intake = FinalEvidenceIntake(evidence_gate=self.custody, context=self.context,
            observer_verifier=self.observer, observer_key_ids=frozenset({self.observer.key_id}))
        self.attempt = self.bundle['campaign']['records'][0]['attempts'][0]
        self.product_tuple = self.bundle['qualification']['records'][0]['product_tuple']

    def require(self, **kwargs):
        return self.intake.require_native_observation(kwargs.pop('spec', self.spec),
            endpoint=kwargs.pop('endpoint', 'source'), attempt=kwargs.pop('attempt', self.attempt),
            product_tuple=kwargs.pop('product_tuple', self.product_tuple), as_of=AS_OF, **kwargs)

    def resign(self, **changes):
        value = deepcopy(self.custody.values[self.attempt['evidence_ref']]['payload'])
        value.update(changes)
        envelope = signed(value, self.observer)
        self.custody.values[self.attempt['evidence_ref']] = envelope
        self.attempt['artifact_sha256'] = sha256(envelope)

    def test_original_separate_signed_packet_can_only_stage_a_review_candidate(self):
        self.require()
        with tempfile.TemporaryDirectory() as temporary:
            result = self.intake.stage_observation(self.spec, endpoint='source', attempt=self.attempt,
                product_tuple=self.product_tuple, destination=Path(temporary) / 'candidate', as_of=AS_OF)
            self.assertFalse(result['activeIndexesChanged'])
            self.assertFalse(result['qualificationIssued'])
            self.assertFalse(result['mutationAuthorized'])
            with self.assertRaises(FileExistsError):
                self.intake.stage_observation(self.spec, endpoint='source', attempt=self.attempt,
                    product_tuple=self.product_tuple, destination=Path(temporary) / 'candidate', as_of=AS_OF)

    def test_reverse_direction_method_profile_job_plan_revision_or_bytes_never_inherit(self):
        variants = [replace(self.spec, source=self.spec.destination, destination=self.spec.source),
            replace(self.spec, method='COLD_WHOLE_VM'), replace(self.spec, guest_profile='windows-server-2022'),
            replace(self.spec, job_id='foreign-job'), replace(self.spec, plan_digest='f' * 64),
            replace(self.spec, code_revision='f' * 40), replace(self.spec, installed_artifact_sha256='e' * 64)]
        for spec in variants:
            with self.subTest(route=spec.route_id), self.assertRaises(ValueError):
                self.require(spec=spec)
        with self.assertRaises(ValueError):
            self.require(endpoint='destination')

    def test_same_product_id_different_canonical_tuple_cannot_supply_exact_evidence(self):
        changed = deepcopy(self.product_tuple)
        changed['server_build'] = 'different-exact-native-build'
        with self.assertRaises(ValueError):
            self.require(product_tuple=changed)

    def test_locally_relabelled_or_boolean_claim_even_independently_signed_is_rejected(self):
        for changes in ({'executionOrigin': 'LOCAL_FIXTURE'}, {'result': True},
                        {'codeRevision': 'f' * 40}, {'endpoint': 'destination'}):
            with self.subTest(changes=changes):
                self.resign(**changes)
                with self.assertRaises(ValueError):
                    self.require()

    def test_actual_original_raw_byte_custody_and_current_observer_are_mandatory(self):
        packet = self.custody.values[self.attempt['evidence_ref']]
        del self.custody.values[packet['payload']['observationEvidenceRef']]
        with self.assertRaisesRegex(ValueError, 'bytes'):
            self.require()
        attach_native(self.spec, self.bundle, self.custody, self.observer)
        packet = self.custody.values[self.attempt['evidence_ref']]
        packet['keyId'] = 'revoked-observer'
        self.attempt['artifact_sha256'] = sha256(packet)
        with self.assertRaisesRegex(ValueError, 'signature'):
            self.require()

    def test_current_metadata_without_original_native_signatures_is_not_final_evidence(self):
        assessment = mobility.assess(self.spec, qualification_index=self.bundle['qualification'],
            provenance_index=self.bundle['provenance'], campaign_index=self.bundle['campaign'],
            selection_index=self.bundle['targetSelection'], as_of=AS_OF)
        self.assertEqual(assessment['status'], 'CURRENT_NATIVE_EVIDENCE_SELECTED')
        self.intake.require_campaign(self.spec, assessment, self.bundle['campaign'],
                                    self.bundle['qualification'], as_of=AS_OF)
        self.custody.values.clear()
        with self.assertRaises(ValueError):
            self.intake.require_campaign(self.spec, assessment, self.bundle['campaign'],
                                        self.bundle['qualification'], as_of=AS_OF)


if __name__ == '__main__':
    unittest.main()
