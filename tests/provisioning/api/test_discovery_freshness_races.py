"""Freshness callbacks use the current principal and stable environment identity."""
from dataclasses import replace
from datetime import timedelta
import unittest

from fastapi.testclient import TestClient

from provisioner.controlplane.api import create_app
from provisioner.controlplane.authority.service import AuthorityService
from provisioner.controlplane.persistence.environments import EnvironmentDeclaration, RegisteredEnvironment
from tests.provisioning.api.test_http import (
    NOW, SOURCE_SCOPE, _Identity, _Plans, _Ledger, _Records, _Jobs, _Environments, _VerifiedEvidence)
from tests.provisioning.discovery.test_freshness_snapshots import MetadataRows, row


class FreshnessRaceTests(unittest.TestCase):
    def setUp(self):
        self.at = NOW
        self.identities = _Identity()
        self.environments = _Environments()
        declaration = EnvironmentDeclaration('env-01', 'Source', SOURCE_SCOPE)
        self.registration = RegisteredEnvironment(declaration, 'operator', declaration.digest(), NOW)
        self.environments.rows[(SOURCE_SCOPE.organization_id, SOURCE_SCOPE.tenant_id, 'env-01')] = self.registration
        self.repository = MetadataRows((row(),))
        authority = AuthorityService(self.identities, _Plans(), _Ledger(), clock=lambda: self.at)
        self.client = TestClient(create_app(_Records(), authority, _Jobs(), self.environments,
            discovery=self.repository, evidence_gate=_VerifiedEvidence(), clock=lambda: self.at))
        self.addCleanup(self.client.close)

    def get(self):
        return self.client.get('/v1/environments/env-01/discovery/freshness',
                               headers={'Authorization': 'Bearer operator'})

    def test_renewed_grants_for_the_same_verified_human_are_used_in_environment_rechecks(self):
        current = self.identities.tokens['operator']
        initial = replace(current, grants=tuple(replace(grant, expires_at=NOW+timedelta(seconds=1))
                                                for grant in current.grants))
        self.identities.tokens['operator'] = initial
        def renew(count):
            self.at = NOW+timedelta(seconds=2)
            self.identities.tokens['operator'] = current
        self.repository.after_read = renew
        response = self.get()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['freshness'], 'FRESH')
        self.assertFalse(response.json()['executionAuthorized'])

    def test_mutating_the_shared_environment_record_cannot_replace_the_original_selection(self):
        def change(count):
            object.__setattr__(self.registration, 'record_digest', 'f'*64)
        self.repository.after_read = change
        response = self.get()
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('observation', response.json())

    def test_reauthenticated_subject_change_is_denied_even_with_identical_grants(self):
        def change(count):
            self.identities.tokens['operator'] = replace(self.identities.tokens['operator'], subject='another-human')
        self.repository.after_read = change
        response = self.get()
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('observation', response.json())

    def test_transient_clock_regression_inside_reauthorization_cannot_escape_live_checks(self):
        authenticate = self.identities.authenticate
        lookup = self.environments.get
        def regressing_authentication(credential):
            principal = authenticate(credential)
            if self.repository.reads:
                self.at = NOW-timedelta(microseconds=1)
            return principal
        def restored_lookup(*args):
            self.at = NOW
            return lookup(*args)
        self.identities.authenticate = regressing_authentication
        self.environments.get = restored_lookup
        response = self.get()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'DISCOVERY_FRESHNESS_UNAVAILABLE')
        self.assertNotIn('observation', response.json())
