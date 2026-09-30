"""Freshness monitoring is scoped read-only API behavior, not a collector."""
from dataclasses import replace
from datetime import timedelta
import unittest

from fastapi.testclient import TestClient
from provisioner.controlplane.api import create_app
from provisioner.controlplane.authority.service import AuthorityService
from provisioner.controlplane.persistence.environments import EnvironmentDeclaration, RegisteredEnvironment
from tests.provisioning.api.test_http import (
    NOW, SOURCE_SCOPE, _Environments, _Identity, _Jobs, _Ledger, _Plans, _Records, _VerifiedEvidence)
from tests.provisioning.discovery.test_freshness import ROW, Rows

PATH = '/v1/environments/env-1/discovery/freshness'


class DiscoveryFreshnessHttpTests(unittest.TestCase):
    def setUp(self):
        self.identities = _Identity()
        self.authority = AuthorityService(self.identities, _Plans(), _Ledger(), clock=lambda: NOW)
        self.environments = _Environments()
        declaration = EnvironmentDeclaration('env-1', 'Source', SOURCE_SCOPE)
        self.environments.rows[('org-01','tenant-01','env-1')] = RegisteredEnvironment(
            declaration,'operator',declaration.digest(),NOW)
        self.repository = Rows(replace(ROW, scope=SOURCE_SCOPE, captured_at=NOW-timedelta(minutes=10)))
        self.app = create_app(_Records(), self.authority, _Jobs(), self.environments,
            discovery=self.repository, evidence_gate=_VerifiedEvidence(), clock=lambda: NOW)
        self.client = TestClient(self.app)

    def read(self, token='operator', path=PATH):
        return self.client.get(path, headers={'Authorization':'Bearer '+token})

    def test_scoped_reader_and_operator_receive_no_store_freshness(self):
        for token in ('operator','job-reader'):
            reply = self.read(token)
            self.assertEqual(reply.status_code,200,reply.text)
            self.assertEqual(reply.headers['cache-control'],'no-store')
            self.assertEqual(reply.json()['freshness'],'FRESH')
            self.assertEqual(reply.json()['policy']['maxAgeSeconds'],86400)
            self.assertFalse(reply.json()['collectionRequested'])
            self.assertFalse(reply.json()['executionAuthorized'])

    def test_anonymous_wrong_scope_and_other_tenant_cannot_read_inventory(self):
        self.assertEqual(self.client.get(PATH).status_code,401)
        for token in ('reader','other-tenant','approver'):
            self.assertEqual(self.read(token).status_code,404)
        self.assertEqual(self.repository.calls,[])

    def test_worker_is_not_promoted_to_human_freshness_reader(self):
        self.identities.tokens['worker'] = replace(self.identities.tokens['operator'],kind='WORKER')
        self.assertEqual(self.read('worker').status_code,403)
        self.assertEqual(self.repository.calls,[])

    def test_query_cannot_override_server_policy_or_inject_a_generation(self):
        for query in ('?maxAgeSeconds=999999999','?generation=1','?force=true','?x=1&x=2'):
            self.assertEqual(self.read(path=PATH+query).status_code,422)
        self.assertEqual(self.repository.calls,[])

    def test_latest_unknown_result_is_not_replaced_by_an_older_complete_capture(self):
        self.repository.row = replace(self.repository.row, completeness='UNKNOWN',
            collection_errors=('private-native-detail',), missing_privileges=('private-permission',))
        reply = self.read()
        self.assertEqual(reply.status_code,200,reply.text)
        self.assertEqual(reply.json()['observation']['generation'],7)
        self.assertIn('COLLECTION_UNKNOWN',reply.json()['issues'])
        self.assertNotIn('private-',reply.text)

    def test_authorized_missing_inventory_is_not_unknown_environment(self):
        self.repository.row = None
        self.assertEqual(self.read().json()['freshness'],'MISSING')
        self.assertEqual(self.read(path=PATH.replace('env-1','absent')).status_code,404)

    def test_generation_change_discards_result_instead_of_retrying(self):
        self.repository.after_read = lambda n: setattr(self.repository,'row',replace(self.repository.row,generation=8))
        reply = self.read()
        self.assertEqual(reply.status_code,409,reply.text)
        self.assertEqual(reply.json()['error']['code'],'DISCOVERY_FRESHNESS_CHANGED')
        self.assertNotIn('observation',reply.json())
        self.assertEqual(len(self.repository.calls),2)

    def test_post_read_revocation_discards_metadata_even_when_missing(self):
        for row in (self.repository.row,None):
            self.repository.row = row
            original = self.identities.tokens['operator']
            self.repository.after_read = lambda n: self.identities.tokens.update(operator=replace(original,grants=()))
            self.assertEqual(self.read().status_code,404)
            self.identities.tokens['operator'] = original

    def test_same_token_cannot_change_subject_after_a_metadata_read(self):
        original = self.identities.tokens['operator']
        self.repository.after_read = lambda n: self.identities.tokens.update(operator=replace(original,subject='different'))
        self.assertEqual(self.read().status_code,404)

    def test_disappearing_environment_cannot_release_retained_metadata(self):
        self.repository.after_read = lambda n: self.environments.rows.clear()
        self.assertEqual(self.read().status_code,404)

    def test_unavailable_backend_and_invalid_metadata_do_not_become_missing_or_expose_errors(self):
        def unavailable(n): raise RuntimeError('secret-dsn-do-not-expose')
        self.repository.after_read = unavailable
        reply = self.read()
        self.assertEqual(reply.status_code,503)
        self.assertNotIn('secret-dsn',reply.text)
        self.repository.after_read = None
        self.repository.row = replace(self.repository.row,scope=replace(SOURCE_SCOPE,tenant_id='foreign'))
        self.assertEqual(self.read().status_code,503)
        original_get = self.environments.get
        def unavailable_environment(*args): raise RuntimeError('private-environment-dsn')
        self.environments.get = unavailable_environment
        reply = self.read()
        self.assertEqual(reply.status_code,503)
        self.assertNotIn('private-environment-dsn',reply.text)
        self.environments.get = original_get

    def test_disabled_repository_returns_unavailable_not_missing(self):
        app = create_app(_Records(),self.authority,_Jobs(),self.environments,
            evidence_gate=_VerifiedEvidence(),clock=lambda:NOW)
        reply = TestClient(app).get(PATH,headers={'Authorization':'Bearer operator'})
        self.assertEqual(reply.status_code,503)
        self.assertEqual(reply.json()['error']['code'],'DISCOVERY_UNAVAILABLE')

    def test_stale_and_future_times_have_distinct_http_results(self):
        for capture, expected in ((NOW-timedelta(days=2),'STALE'),(NOW+timedelta(seconds=1),'FUTURE_CAPTURE')):
            self.repository.row = replace(self.repository.row,captured_at=capture)
            reply = self.read()
            self.assertEqual(reply.status_code,200,reply.text)
            self.assertEqual(reply.json()['freshness'],expected)

    def test_non_get_requests_do_not_create_a_refresh_job(self):
        for method in ('post','put','delete'):
            self.assertEqual(getattr(self.client,method)(PATH,headers={'Authorization':'Bearer operator'}).status_code,405)
        self.assertEqual(self.repository.calls,[])
