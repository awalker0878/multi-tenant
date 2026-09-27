"""Operator portfolio reads use exact scope and expose only safe summaries."""
from __future__ import annotations

import unittest
from datetime import timedelta

from fastapi.testclient import TestClient

from provisioner.controlplane.api import create_app
from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.authority.service import AuthorityService
from provisioner.controlplane.discovery.model import NativeIdentity
from provisioner.controlplane.discovery.persistence import (
    DiscoveryRepository, StoredGeneration, StoredObservation,
)
from provisioner.controlplane.persistence.environments import (
    EnvironmentDeclaration, RegisteredEnvironment,
)
from tests.provisioning.api.test_http import (
    NOW, SOURCE_SCOPE, _Environments, _Identity, _Jobs, _Ledger, _Plans,
    _Records, _VerifiedEvidence,
)


class _Discovery(DiscoveryRepository):
    def __init__(self):
        self.scopes = []
        self.foreign = False
        self.generations = [StoredGeneration(
            'env-01', number, 'campaign-01', SOURCE_SCOPE,
            'a' * 64, str(number) * 64, NOW + timedelta(minutes=number),
            'PARTIAL', ('READ_TIMEOUT',), ('read.vm.disk',), 3)
            for number in (1, 2)]
        self.observations = [StoredObservation(
            2, NativeIdentity(SOURCE_SCOPE.endpoint_id,
                              SOURCE_SCOPE.native_scope_id,
                              SOURCE_SCOPE.platform_family, 'vm', native_id),
            ({'name': 'name', 'state': 'KNOWN', 'value': name,
              'reason': None, 'requiredPrivilege': None},
             {'name': 'guest', 'state': 'UNKNOWN', 'value': None,
              'reason': 'MISSING_PRIVILEGE',
              'requiredPrivilege': 'read.vm.guest'},
             {'name': 'secret', 'state': 'KNOWN', 'value': 'do-not-expose',
              'reason': None, 'requiredPrivilege': None}),
            digest * 64)
            for native_id, name, digest in (('vm-01', 'Payroll', 'b'),
                                            ('vm-02', 'Directory', 'c'))]

    def list_generations(self, ctx, scope, environment_id, *, after=0, limit=51):
        self.scopes.append((ctx, scope, environment_id))
        rows = [row for row in self.generations if row.generation > after]
        return rows[:limit]

    def list_observations(self, ctx, scope, environment_id, generation,
                          *, after=None, limit=51):
        self.scopes.append((ctx, scope, environment_id))
        rows = [row for row in self.observations
                if row.generation == generation
                and (row.identity.resource_kind, row.identity.native_id) >
                    (after or ('', ''))]
        if self.foreign and rows:
            row = rows[0]
            rows[0] = StoredObservation(row.generation, NativeIdentity(
                'foreign-endpoint', row.identity.native_scope_id,
                row.identity.platform_family, row.identity.resource_kind,
                row.identity.native_id), row.facts, row.object_digest)
        return rows[:limit]


class DiscoveryHttpTests(unittest.TestCase):
    def setUp(self):
        self.environments = _Environments()
        declaration = EnvironmentDeclaration('env-01', 'Source', SOURCE_SCOPE)
        self.environments.rows[('org-01', 'tenant-01', 'env-01')] = (
            RegisteredEnvironment(declaration, 'operator', declaration.digest(), NOW))
        self.discovery = _Discovery()
        identity = _Identity()
        authority = AuthorityService(identity, _Plans(), _Ledger(), clock=lambda: NOW)
        self.app = create_app(_Records(), authority, _Jobs(), self.environments,
                              discovery=self.discovery, evidence_gate=_VerifiedEvidence(),
                              clock=lambda: NOW)
        self.client = TestClient(self.app)

    @staticmethod
    def auth(token):
        return {'Authorization': 'Bearer ' + token}

    def test_generation_page_requires_exact_current_native_role(self):
        path = '/v1/environments/env-01/discovery/generations?limit=1'
        self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.get(path, headers=self.auth('reader')).status_code, 404)
        self.assertEqual(self.discovery.scopes, [])
        first = self.client.get(path, headers=self.auth('operator'))
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()['nextAfter'], 1)
        self.assertEqual(first.json()['items'][0], {
            'environmentId': 'env-01', 'generation': 1,
            'campaignId': 'campaign-01', 'resultDigest': '1' * 64,
            'capturedAt': (NOW + timedelta(minutes=1)).isoformat().replace('+00:00', 'Z'),
            'completeness': 'PARTIAL', 'objectCount': 3,
            'collectionErrorCount': 1, 'missingPrivilegeCount': 1})
        second = self.client.get(path + '&after=1', headers=self.auth('operator'))
        self.assertEqual([row['generation'] for row in second.json()['items']], [2])
        self.assertIsNone(second.json()['nextAfter'])
        self.assertTrue(all(scope == SOURCE_SCOPE for _, scope, _ in self.discovery.scopes))

    def test_object_page_is_bounded_and_never_returns_raw_facts(self):
        path = '/v1/environments/env-01/discovery/generations/2/objects?limit=1'
        first = self.client.get(path, headers=self.auth('operator'))
        self.assertEqual(first.status_code, 200, first.text)
        item = first.json()['items'][0]
        self.assertEqual(item, {'resourceKind': 'vm', 'nativeId': 'vm-01',
                                'displayName': 'Payroll', 'unknownCount': 1,
                                'objectDigest': 'b' * 64})
        self.assertNotIn('do-not-expose', first.text)
        self.assertNotIn('facts', first.text)
        cursor = first.json()['nextAfter']
        second = self.client.get(path + '&after=' + cursor,
                                 headers=self.auth('operator'))
        self.assertEqual([item['nativeId'] for item in second.json()['items']],
                         ['vm-02'])
        self.assertIsNone(second.json()['nextAfter'])
        self.assertEqual(self.client.get(path + '&after=bad+',
                                         headers=self.auth('operator')).status_code, 422)
        self.assertEqual(self.client.get(path.replace('/2/', '/3/'),
                                         headers=self.auth('operator')).status_code, 404)

    def test_foreign_backend_row_fails_closed(self):
        self.discovery.foreign = True
        response = self.client.get(
            '/v1/environments/env-01/discovery/generations/2/objects',
            headers=self.auth('operator'))
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('foreign-endpoint', response.text)


if __name__ == '__main__':
    unittest.main()
