"""Authenticated application comparison uses existing services; no native writes."""
import copy
import unittest
from dataclasses import replace
from datetime import timedelta

from fastapi.testclient import TestClient
from provisioner.controlplane.api import create_app
from provisioner.controlplane.authority.model import RoleGrant
from provisioner.controlplane.authority.service import AuthorityService, JOB_READER
from provisioner.controlplane.discovery.persistence import DiscoveryRepository
from provisioner.controlplane.persistence.environments import EnvironmentDeclaration, RegisteredEnvironment
from tests.provisioning.api import test_http as http
from tests.provisioning.discovery import test_application_assessment as core
from tests.provisioning.discovery.test_service import CTX, NOW, INSTALLATIONS


class Repository(core.Repository, DiscoveryRepository):
    """Read-only test double, retaining the production repository interface."""


class Inputs(core.VerifiedInputs):
    def bind(self, credential):
        self.credential = credential
        return self


class ApplicationAssessmentHttpTests(unittest.TestCase):
    def setUp(self):
        self.fixture = core.ApplicationAssessmentTests()
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.repository = Repository(); self.repository.results = self.fixture.repository.results
        self.inputs = Inputs(); self.inputs.qualified = True
        self.identity = http._Identity()
        original = self.identity.tokens['operator']
        current = replace(original, organization_id=CTX.organization_id, tenant_id=CTX.tenant_id,
            issued_at=NOW-timedelta(minutes=1), expires_at=NOW+timedelta(hours=1),
            grants=tuple(RoleGrant(JOB_READER, item.scope, NOW+timedelta(hours=1)) for item in INSTALLATIONS.values()))
        self.identity.tokens['operator'] = current
        self.identity.tokens['one-sided'] = replace(current, grants=current.grants[:1])
        self.environments = http._Environments()
        for name, item in INSTALLATIONS.items():
            declaration = EnvironmentDeclaration(name, name, item.scope)
            self.environments.rows[(CTX.organization_id, CTX.tenant_id, name)] = RegisteredEnvironment(
                declaration, 'registrar', declaration.digest(), NOW)
        self.client = self.build()
        self.body = {'source': {'environmentId': 'source', 'generation': 7},
            'applicationGroupId': 'app-1', 'draftRevision': 1,
            'draftRecordDigest': self.fixture.stored.record_digest,
            'memberProfiles': [{'workloadId': name, 'guestProfile': 'linux-uefi'} for name in ('db', 'web')],
            'destinations': [{'environmentId': name, 'generation': 7,
                             'capacityKind': 'pool', 'capacityNativeId': 'pool-1'} for name in ('target-a', 'target-b')],
            'method': 'COLD_VM_CONVERSION', 'networkMode': 'routed', 'dataMode': 'offline'}

    def build(self, enabled=True):
        return TestClient(create_app(http._Records(), AuthorityService(self.identity, http._Plans(),
            http._Ledger(), clock=lambda: NOW), http._Jobs(), self.environments,
            evidence_gate=http._VerifiedEvidence(), discovery=self.repository, assessment_inputs=self.inputs,
            application_drafts=self.fixture.drafts, application_reviews=self.fixture.reviews if enabled else None,
            clock=lambda: NOW))

    def request(self, body=None, token='operator', client=None):
        return (client or self.client).post('/v1/assessments/applications/compare',
            json=self.body if body is None else body,
            headers={'Authorization': 'Bearer '+token} if token else {})

    def test_current_review_and_complete_members_return_read_only_combined_advice(self):
        response = self.request(); self.assertEqual(response.status_code, 200, response.text)
        value = response.json(); self.assertEqual(value['status'], 'ASSESSED_NOT_AUTHORIZED')
        self.assertEqual(len(value['assessments']), 2)
        self.assertFalse(value['executionAuthorized']); self.assertFalse(value['reservationHeld'])
        self.assertEqual(value['assessments'][0]['capacity']['resources']['VCPU']['required'], 8)
        self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_missing_auth_and_destination_rights_precede_inventory_or_review_reads(self):
        self.assertEqual(self.request(token=None).status_code, 401)
        self.assertEqual(self.request(token='one-sided').status_code, 404)
        self.assertEqual(self.repository.reads, []); self.assertEqual(self.fixture.reviews.calls, 0)

    def test_request_cannot_supply_candidate_membership_owner_evidence_or_capacity(self):
        for field in ('claims', 'ownerDecision', 'candidateDigest', 'members', 'availableVcpu', 'executionAuthorized'):
            with self.subTest(field=field):
                self.assertEqual(self.request({**self.body, field: True}).status_code, 422)
        self.assertEqual(self.repository.reads, [])

    def test_exact_revision_digest_and_full_member_profiles_are_required(self):
        for field, value in (('draftRevision', True), ('draftRevision', 0), ('draftRecordDigest', 'bad'),
                              ('memberProfiles', self.body['memberProfiles'][:1])):
            with self.subTest(field=field):
                self.assertEqual(self.request({**self.body, field: value}).status_code, 422)
        value = copy.deepcopy(self.body); value['memberProfiles'][1]['workloadId'] = 'stranger'
        self.assertEqual(self.request(value).status_code, 422)

    def test_unsigned_draft_returns_an_explicit_hold_not_a_vm_comparison(self):
        self.fixture.reviews.none = True
        response = self.request(); self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['status'], 'HELD_APPLICATION_REVIEW')
        self.assertEqual(response.json()['assessments'], [])
        self.assertEqual(self.repository.reads, [])

    def test_disabled_and_changed_retained_source_hold_without_exposing_internals(self):
        self.assertEqual(self.request(client=self.build(False)).status_code, 503)
        self.fixture.drafts.corrupt = {'proposal': {}}
        response = self.request(); self.assertEqual(response.status_code, 503, response.text)
        self.assertNotIn('trust.json', response.text)

    def test_operator_revocation_after_computation_prevents_response(self):
        def revoke(count):
            if count == 2: self.identity.tokens.pop('operator')
        self.fixture.reviews.before = revoke
        self.assertEqual(self.request().status_code, 404)
        self.assertTrue(self.repository.reads)

    def test_changed_authenticated_actor_cannot_receive_old_results(self):
        def change(count):
            if count == 2:
                self.identity.tokens['operator'] = replace(self.identity.tokens['operator'], subject='other')
        self.fixture.reviews.before = change
        self.assertEqual(self.request().status_code, 404)

    def test_more_than_200_member_destination_cells_is_refused(self):
        value = copy.deepcopy(self.body)
        value['memberProfiles'] = [{'workloadId': 'vm-'+str(i), 'guestProfile': 'linux'} for i in range(100)]
        value['destinations'] = value['destinations']*2
        self.assertEqual(self.request(value).status_code, 422)
        self.assertEqual(self.repository.reads, [])


if __name__ == '__main__': unittest.main()
