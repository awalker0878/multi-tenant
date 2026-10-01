"""Authenticated HTTP over the real history owner with a transaction-protocol fixture.

Real PostgreSQL isolation, triggers and locks are exercised separately.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from unittest import TestCase, mock

from fastapi.testclient import TestClient
from provisioner.controlplane.api import create_app
from provisioner.controlplane.authority.service import AuthorityService
from provisioner.controlplane.evidence.gate import EvidenceHold
from provisioner.controlplane.persistence.environments import EnvironmentDeclaration
from provisioner.controlplane.persistence.store import AuditContext, TenantContext
from tests.provisioning.api import test_http as support
from tests.provisioning.discovery.test_freshness_history import Database, Discovery

BASE = '/v1/environments/env-01/discovery/freshness'
CHECKS = BASE + '/checks'


class FreshnessHistoryHttpTests(TestCase):
    def setUp(self):
        self.db = Database()
        self.discovery = Discovery(self.db)
        self.identity = support._Identity()
        self.environments = support._Environments()
        self.environments.create(TenantContext('org-01', 'tenant-01'),
            EnvironmentDeclaration('env-01', 'Source', support.SOURCE_SCOPE), AuditContext('registrar', 'registration'))
        self.authority = AuthorityService(self.identity, support._Plans(), support._Ledger(), clock=lambda: self.db.now)
        self.evidence = support._VerifiedEvidence()
        self.jobs = support._Jobs()
        self.app = self.application()
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def application(self, **values):
        return create_app(support._Records(), self.authority, self.jobs, self.environments,
            discovery=values.get('discovery', self.discovery), evidence_gate=self.evidence, clock=lambda: self.db.now)

    def auth(self, token='operator'):
        return {'Authorization': 'Bearer ' + token}

    def capture(self, check='check-1', token='operator', **options):
        return self.client.put(CHECKS + '/' + check, headers=self.auth(token), json={}, **options)

    def read(self, path=CHECKS, token='job-reader'):
        return self.client.get(path, headers=self.auth(token))

    def test_capture_records_server_sample_actor_and_no_store_but_no_job(self):
        reply = self.capture()
        self.assertEqual(reply.status_code, 200, reply.text)
        value = reply.json()
        self.assertEqual(value['recordedBy'], 'operator')
        self.assertEqual(value['report']['observation']['generation'], 1)
        self.assertEqual(value['changeKinds'], ['INITIAL_CHECK'])
        self.assertTrue(value['historicalOnly'])
        for name in ('notificationAttempted', 'collectionRequested', 'executionAuthorized'):
            self.assertIs(value[name], False)
        self.assertEqual(reply.headers['cache-control'], 'no-store')
        self.assertEqual(len(self.db.rows), 1)
        self.assertEqual(len(self.db.events), 1)
        self.assertEqual(self.jobs.submissions, [])

    def test_same_actor_retry_retains_original_without_resampling(self):
        first = self.capture().json()
        reads = self.db.reads
        self.discovery.metadata = None
        self.assertEqual(self.capture().json(), first)
        self.assertEqual(self.db.reads, reads)
        self.assertEqual(len(self.db.events), 1)
        second = self.capture('check-2').json()
        self.assertEqual(second['report']['freshness'], 'MISSING')
        self.assertEqual(second['previousRecordDigest'], first['recordDigest'])

    def test_another_actor_cannot_claim_an_existing_check(self):
        self.capture()
        reply = self.capture(token='editor')
        self.assertEqual(reply.status_code, 409, reply.text)
        self.assertEqual(reply.json()['error']['code'], 'DISCOVERY_FRESHNESS_CHECK_CONFLICT')
        self.assertEqual(len(self.db.rows), 1)

    def test_current_get_and_history_reads_do_not_append_or_resample_history(self):
        original = self.capture().json()
        self.assertEqual(self.read(CHECKS + '/check-1').json(), original)
        reads = self.db.reads
        page = self.read().json()
        self.assertEqual(page['items'], [original])
        self.assertEqual(page['consistency'], 'APPEND_ONLY_PAGE')
        self.assertEqual(self.db.reads, reads)
        self.assertEqual(self.read(BASE).status_code, 200)
        self.assertEqual(len(self.db.rows), 1)
        self.assertEqual(len(self.db.events), 1)

    def test_reader_can_read_but_cannot_append_or_retry_put(self):
        self.capture()
        self.assertEqual(self.capture('check-2', token='job-reader').status_code, 404)
        self.assertEqual(self.capture(token='job-reader').status_code, 404)
        self.assertEqual(self.read(CHECKS + '/check-1').status_code, 200)
        self.assertEqual(len(self.db.rows), 1)

    def test_no_auth_foreign_tenant_and_worker_cannot_reach_history(self):
        self.assertEqual(self.client.get(CHECKS).status_code, 401)
        self.assertEqual(self.client.put(CHECKS + '/check-1', json={}).status_code, 401)
        for token in ('reader', 'other-tenant', 'approver'):
            self.assertEqual(self.read(token=token).status_code, 404)
            self.assertEqual(self.capture(token=token).status_code, 404)
        self.identity.tokens['worker'] = replace(self.identity.tokens['operator'], kind='WORKER')
        self.assertEqual(self.capture(token='worker').status_code, 403)
        self.assertEqual(self.read(token='worker').status_code, 403)
        self.assertEqual(self.db.queries, [])

    def test_report_actor_policy_and_native_claims_are_not_accepted(self):
        for value in ({'actor': 'admin'}, {'report': {}}, {'policy': {}}, {'force': True},
                      {'generation': 1}, {'executionAuthorized': True}, [], None):
            reply = self.client.put(CHECKS + '/check-1', headers=self.auth(), json=value)
            self.assertEqual(reply.status_code, 422, reply.text)
        for raw in ('{"x":1,"x":2}', '{', '{} trailing'):
            reply = self.client.put(CHECKS + '/check-1', content=raw,
                headers={**self.auth(), 'Content-Type': 'application/json'})
            self.assertEqual(reply.status_code, 422)
        self.assertEqual(self.db.queries, [])

    def test_bounded_body_and_content_type(self):
        for raw, mime, code in ((b'{}', 'text/plain', 422), (b'\xff', 'application/json', 422),
                               (b' ' * 1025, 'application/json', 413)):
            reply = self.client.put(CHECKS + '/check-1', content=raw,
                headers={**self.auth(), 'Content-Type': mime})
            self.assertEqual(reply.status_code, code, reply.text)
        self.assertEqual(self.db.queries, [])

    def test_bounded_unique_canonical_query_parameters(self):
        for query in ('after=-1', 'after=01', 'after=1e2', 'after=true', 'after=9223372036854775808',
                      'limit=0', 'limit=51', 'limit=1&limit=2', 'after=0&after=1', 'force=true'):
            reply = self.read(CHECKS + '?' + query)
            self.assertEqual(reply.status_code, 422, reply.text)
        self.assertEqual(self.read(CHECKS + '/check-1?force=true').status_code, 422)
        self.assertEqual(self.capture(params={'force': 'true'}).status_code, 422)
        self.assertEqual(self.db.queries, [])

    def test_pages_preserve_original_sequence_and_separate_missing_record(self):
        values = [self.capture('check-' + str(n)).json() for n in range(3)]
        first = self.read(CHECKS + '?limit=2').json()
        self.assertEqual(first['items'], values[:2])
        self.assertEqual(first['nextAfter'], 2)
        self.assertEqual(self.read(CHECKS + '?after=2').json()['items'], values[2:])
        self.assertEqual(self.read(CHECKS + '/absent').status_code, 404)
        self.assertEqual(self.read(CHECKS + '?after=3').json()['items'], [])

    def test_evidence_outage_blocks_append_but_not_get_or_history(self):
        original = self.capture().json()
        with mock.patch.object(self.evidence, 'require', side_effect=EvidenceHold('private-storage-path')):
            reply = self.capture('check-2')
            self.assertEqual(reply.status_code, 503, reply.text)
            self.assertEqual(reply.json()['error']['code'], 'EVIDENCE_HOLD')
            self.assertNotIn('private-storage-path', reply.text)
            self.assertEqual(self.read(CHECKS + '/check-1').json(), original)
            self.assertEqual(self.read(BASE).status_code, 200)
        self.assertEqual(len(self.db.rows), 1)

    def test_mid_transaction_evidence_loss_rolls_back_sample_and_audit(self):
        def fail():
            self.evidence.require = mock.Mock(side_effect=EvidenceHold('private-custody'))
        self.db.after_insert = fail
        reply = self.capture()
        self.assertEqual(reply.status_code, 503, reply.text)
        self.assertEqual(self.db.rows, [])
        self.assertEqual(self.db.events, [])

    def test_changed_actor_after_insert_cannot_commit_or_receive_sample(self):
        principal = self.identity.tokens['operator']
        self.db.after_insert = lambda: self.identity.tokens.update(operator=replace(principal, subject='replacement'))
        reply = self.capture()
        self.assertEqual(reply.status_code, 404, reply.text)
        self.assertEqual(self.db.rows, [])
        self.assertEqual(self.db.events, [])

    def test_environment_disappearing_during_sample_causes_rollback(self):
        self.discovery.after_read = lambda: self.environments.rows.clear()
        self.assertEqual(self.capture().status_code, 404)
        self.assertEqual(self.db.rows, [])

    def test_corrupt_history_is_unavailable_not_missing(self):
        self.capture()
        row = list(self.db.rows[0]); row[11] = 'f' * 64; self.db.rows[0] = tuple(row)
        for path in (CHECKS, CHECKS + '/check-1'):
            reply = self.read(path)
            self.assertEqual(reply.status_code, 503, reply.text)
            self.assertNotIn('report_json', reply.text)
            self.assertNotIn('Bearer', reply.text)

    def test_disabled_repository_remains_unavailable(self):
        with TestClient(self.application(discovery=None)) as client:
            for method, path in (('get', CHECKS), ('get', CHECKS + '/check-1'), ('put', CHECKS + '/check-1')):
                options = {'json': {}} if method == 'put' else {}
                reply = getattr(client, method)(path, headers=self.auth(), **options)
                self.assertEqual(reply.status_code, 503, reply.text)

    def test_database_clock_ahead_of_api_clock_holds_without_new_record(self):
        self.db.clock = lambda: self.db.now + timedelta(seconds=1)
        self.assertEqual(self.capture().status_code, 503)
        self.assertEqual(self.db.rows, [])

    def test_history_has_no_update_delete_or_launch_routes(self):
        self.capture()
        for method in ('post', 'patch', 'delete'):
            self.assertEqual(getattr(self.client, method)(CHECKS + '/check-1', headers=self.auth()).status_code, 405)
        self.assertEqual(self.client.put(BASE, json={}, headers=self.auth()).status_code, 405)
        self.assertEqual(len(self.db.rows), 1)

    def test_changed_inventory_aborts_check_instead_of_retrying_or_saving(self):
        from provisioner.controlplane.discovery.freshness import FreshnessChanged
        with mock.patch.object(self.discovery, 'latest_generation', side_effect=FreshnessChanged('private observation')):
            reply = self.capture()
        self.assertEqual(reply.status_code, 409, reply.text)
        self.assertEqual(reply.json()['error']['code'], 'DISCOVERY_FRESHNESS_CHANGED')
        self.assertNotIn('private observation', reply.text)
        self.assertEqual(self.db.rows, [])
        self.assertEqual(self.db.events, [])

    def test_openapi_preserves_freshness_errors_and_empty_check_body(self):
        paths = self.client.get('/openapi.json').json()['paths']
        base = '/v1/environments/{environment_id}/discovery/freshness'
        self.assertIn('503', paths[base]['get']['responses'])
        put = paths[base + '/checks/{check_id}']['put']
        schema = put['requestBody']['content']['application/json']['schema']
        self.assertEqual(schema, {'type': 'object', 'properties': {}, 'additionalProperties': False})
        self.assertTrue(put['requestBody']['required'])
        self.assertIn('409', put['responses'])
