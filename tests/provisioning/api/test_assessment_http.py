"""Compare transport uses only saved selections and independently verified inputs."""
from datetime import timedelta
from dataclasses import replace
import unittest
from fastapi.testclient import TestClient

from provisioner.controlplane.api import create_app
from provisioner.controlplane.authority.service import AuthorityService
from provisioner.controlplane.authority.model import RoleGrant
from provisioner.controlplane.authority.service import JOB_READER
from provisioner.controlplane.discovery.assessment import AssessmentScopeAccess
from provisioner.controlplane.discovery.model import DiscoveryResult
from provisioner.controlplane.discovery.persistence import DiscoveryRepository, StoredGeneration
from provisioner.controlplane.discovery.routes import InstalledTuple
from provisioner.controlplane.discovery.service import VerifiedAssessmentEnvironment
from provisioner.controlplane.persistence.environments import EnvironmentDeclaration, RegisteredEnvironment
from tests.provisioning.api.test_http import (
    NOW, SOURCE_SCOPE, TARGET_SCOPE, _Environments, _Identity, _Jobs, _Ledger,
    _Plans, _Records, _VerifiedEvidence,
)

SCOPES = {'source': SOURCE_SCOPE, 'target': TARGET_SCOPE,
          'target-2': replace(TARGET_SCOPE, endpoint_id='target-2-endpoint')}


class Repository(DiscoveryRepository):
    def __init__(self):
        self.reads = []
        self.corrupt = False

    def get_generation(self, ctx, scope, environment_id, generation):
        self.reads.append((environment_id, generation))
        result = DiscoveryResult('campaign-' + environment_id, 'a' * 64, scope,
                                 NOW - timedelta(minutes=1), 'COMPLETE', (), (), ())
        return StoredGeneration(environment_id, generation, result.campaign_id, scope,
                                result.authorization_digest, '0' * 64 if self.corrupt
                                else result.digest, result.captured_at, 'COMPLETE', (), (), 0)

    def list_observations(self, *args, **kwargs):
        return []


class Inputs:
    """Test-only independent provider; no test policy is a production default."""
    def __init__(self):
        self.credentials = []

    def bind(self, credential):
        self.credentials.append(credential)
        return self

    def resolve_environment(self, ctx, actor, environment_id, purpose, as_of):
        scope = SCOPES[environment_id]
        return VerifiedAssessmentEnvironment(
            environment_id, InstalledTuple(scope, environment_id + '-tuple', 'b' * 64),
            AssessmentScopeAccess(scope, purpose, actor, 'independent-access',
                                  as_of - timedelta(minutes=1), as_of + timedelta(minutes=1)))

    def route_claims(self, *args):
        return ()

    def reviewed_findings(self, *args):
        return ()


class AssessmentHttpTests(unittest.TestCase):
    def setUp(self):
        self.repository = Repository()
        self.inputs = Inputs()
        self.environments = _Environments()
        for name, scope in SCOPES.items():
            declaration = EnvironmentDeclaration(name, name, scope)
            self.environments.rows[('org-01', 'tenant-01', name)] = RegisteredEnvironment(
                declaration, 'operator', declaration.digest(), NOW)
        identity = _Identity()
        operator = identity.tokens['operator']
        identity.tokens['operator'] = replace(operator, grants=operator.grants + (
            RoleGrant(JOB_READER, SCOPES['target-2'], NOW + timedelta(hours=1)),))
        self.authority = AuthorityService(identity, _Plans(), _Ledger(), clock=lambda: NOW)
        self.client = self.client_for(self.inputs)
        self.body = {
            'source': {'environmentId': 'source', 'generation': 7},
            'workloadNativeId': 'vm-1',
            'destinations': [{'environmentId': 'target', 'generation': 3},
                             {'environmentId': 'target-2', 'generation': 4}],
            'method': 'REBUILD_RESTORE', 'guestProfile': 'linux',
            'networkMode': 'routed', 'dataMode': 'backup-restore',
        }

    def client_for(self, inputs):
        return TestClient(create_app(_Records(), self.authority, _Jobs(), self.environments,
                                     discovery=self.repository, assessment_inputs=inputs,
                                     evidence_gate=_VerifiedEvidence(), clock=lambda: NOW))

    def request(self, token='operator', body=None, client=None):
        return (client or self.client).post('/v1/assessments/compare',
            headers={'Authorization': 'Bearer ' + token}, json=self.body if body is None else body)

    def test_pinned_unknown_comparison_does_not_become_execution_authority(self):
        response = self.request()
        self.assertEqual(response.status_code, 200, response.text)
        value = response.json()
        self.assertFalse(value['executionAuthorized'])
        self.assertEqual(value['sourceInput']['generation'], 7)
        self.assertEqual(value['destinationInputs'][0]['generation'], 3)
        self.assertEqual(value['assessments'][0]['status'], 'UNKNOWN')
        self.assertEqual(self.repository.reads, [('source', 7), ('target', 3), ('target-2', 4)])
        self.assertEqual(self.inputs.credentials, ['operator'])
        self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_all_scopes_authorized_before_inputs_or_inventory_are_read(self):
        for token in ('reader', 'one-sided', 'other-tenant'):
            response = self.request(token)
            self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(self.repository.reads, [])
        self.assertEqual(self.inputs.credentials, [])

    def test_reversed_destination_selections_keep_results_with_their_generation_bindings(self):
        response = self.request(body={**self.body, 'destinations': list(reversed(self.body['destinations']))})
        self.assertEqual(response.status_code, 200, response.text)
        value = response.json()
        self.assertEqual([item['environmentId'] for item in value['destinationInputs']],
                         ['target-2', 'target'])
        for binding, assessment in zip(value['destinationInputs'], value['assessments']):
            self.assertEqual(binding['endpointId'], assessment['destination']['endpointId'])

    def test_request_cannot_claim_native_eligibility_or_supply_authority(self):
        for field in ('claims', 'principal', 'productTupleDigest', 'executionAuthorized'):
            response = self.request(body={**self.body, field: True})
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.repository.reads, [])

    def test_configuration_and_corrupt_snapshot_fail_closed(self):
        response = self.request(client=self.client_for(None))
        self.assertEqual((response.status_code, response.json()['error']['code']),
                         (503, 'ASSESSMENT_UNAVAILABLE'))
        self.repository.corrupt = True
        response = self.request()
        self.assertEqual((response.status_code, response.json()['error']['code']),
                         (503, 'ASSESSMENT_UNAVAILABLE'))

    def test_invalid_native_route_and_mapping_cannot_proceed(self):
        body = {**self.body, 'destinations': [self.body['destinations'][0]] * 2}
        self.assertEqual(self.request(body=body).status_code, 422)
        body = {**self.body, 'destinations': [
            {'environmentId': 'target', 'generation': 3, 'capacityKind': 'pool'}]}
        self.assertEqual(self.request(body=body).status_code, 422)


if __name__ == '__main__':
    unittest.main()
