"""Scoped DNS retirement against real loopback TLS and signed TCP fixtures."""
from copy import deepcopy
from datetime import timedelta
import json
import unittest
from unittest.mock import patch
import uuid

from lab.dns_authority import Authority
from tests import test_netbox_dns as registration_fixture
from tests.test_dns_transactions import example
from tools import dns_change as dns_writer, netbox_dns as handoff
from tools.run_files import digest, encoded, load_private, replace_private, utcnow


class NetboxDNSWithdrawalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registration_fixture.NetboxDNSTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        registration_fixture.NetboxDNSTests.tearDownClass.__func__(cls)

    run_action = registration_fixture.NetboxDNSTests.run_action
    prepare_dns = registration_fixture.NetboxDNSTests.prepare_dns
    transaction = registration_fixture.NetboxDNSTests.transaction

    def setUp(self):
        registration_fixture.NetboxDNSTests.setUp(self)

    def run_dns(self, action='register'):
        return handoff.operate(self.job, self.receipt, self.dns_job, self.scope, self.authority,
                               self.client, self.dns_client, self.ledger, action=action,
                               registration=self.registration if action in handoff.WITHDRAW_ACTIONS else None,
                               fixture=True)

    def prepare_withdrawal(self):
        self.registration = deepcopy(dict(job=self.dns_job, scope=self.scope))
        record = self.dns_job['records'][0]
        self.dns_job['previous_marker'] = dns_writer.marker_value(self.registration['job'])
        self.dns_job['operation_id'] = self.scope['operation_id'] = str(uuid.uuid4())
        record['before'], record['after'] = record['after'], None

    def registered(self):
        self.run_dns()
        self.prepare_withdrawal()

    def withdrawal_transaction(self):
        return next(self.ledger.glob('*/dns-*/withdrawal-transaction.json'))

    def test_owned_A_withdrawal_keeps_tombstones_other_names_and_IPAM(self):
        self.registered()
        self.dns_server.set('other.fixture.invalid.', 'A', 60, ['192.0.2.99'])
        registration = self.transaction().read_bytes()
        ipam = next(self.ledger.glob('*/head.json')).read_bytes()
        result = self.run_dns('withdraw')
        self.assertEqual(result['status'], 'AUTHORITATIVE_TOMBSTONE_OBSERVED')
        self.assertFalse(result['activation_authorized'] or result['reusable'])
        self.assertNotIn(('app.fixture.invalid.', 'A'), self.dns_server.store)
        self.assertIn(('other.fixture.invalid.', 'A'), self.dns_server.store)
        self.assertTrue(dns_writer.matches(dns_writer.snapshot(self.dns_job, self.dns_client), self.dns_job, 'after'))
        self.assertEqual(self.transaction().read_bytes(), registration)
        self.assertEqual(next(self.ledger.glob('*/head.json')).read_bytes(), ipam)
        with self.assertRaises(FileExistsError): self.run_dns('withdraw')
        self.assertEqual(self.run_dns('reconcile-withdrawal')['status'], 'AUTHORITATIVE_TOMBSTONE_OBSERVED')
        self.assertEqual(self.dns_server.update_requests, 2)

    def test_owned_PTR_withdrawal_keeps_reverse_tombstone(self):
        server = Authority('2.0.192.in-addr.arpa.', 'owner.fixture.invalid.', self.secret).__enter__()
        self.addCleanup(server.__exit__, None, None, None)
        self.dns_server = server
        self.dns_job, self.scope = example(server.port, zone='2.0.192.in-addr.arpa.',
                    name='20.2.0.192.in-addr.arpa.', rtype='PTR', value='app.fixture.invalid.')
        self.prepare_dns()
        self.registered()
        self.assertEqual(self.run_dns('withdraw')['status'], 'AUTHORITATIVE_TOMBSTONE_OBSERVED')
        self.assertNotIn(('20.2.0.192.in-addr.arpa.', 'PTR'), server.store)
        self.assertIn(('_hosting-owner.20.2.0.192.in-addr.arpa.', 'TXT'), server.store)

    def test_exact_generation_record_parent_and_transport_required_before_contact(self):
        self.registered()
        original = deepcopy((self.dns_job, self.scope, self.registration))
        before_queries, before_calls = self.dns_server.queries, len(self.calls)
        for case in ('marker', 'value', 'TTL', 'name', 'replacement', 'same_operation', 'transport', 'parent', 'missing'):
            self.dns_job, self.scope, self.registration = deepcopy(original)
            if case == 'marker': self.dns_job['previous_marker'] = None
            if case == 'value': self.dns_job['records'][0]['before']['values'] = ['192.0.2.21']
            if case == 'TTL': self.dns_job['records'][0]['before']['ttl'] += 1
            if case == 'name': self.dns_job['records'][0]['name'] = self.scope['allowed_records'][0]['name'] = 'other.fixture.invalid.'
            if case == 'replacement': self.dns_job['records'][0]['after'] = deepcopy(self.dns_job['records'][0]['before'])
            if case == 'same_operation':
                self.dns_job['operation_id'] = self.scope['operation_id'] = self.registration['job']['operation_id']
            if case == 'transport': self.dns_job['port'] = self.scope['port'] = 53
            if case == 'parent': self.registration['scope']['allowed_records'][0]['maximum_ttl'] += 1
            if case == 'missing': self.registration = None
            with self.subTest(case=case), self.assertRaises(ValueError): self.run_dns('withdraw')
        self.assertEqual((self.dns_server.queries, len(self.calls)), (before_queries, before_calls))
        self.assertEqual(self.dns_server.update_requests, 1)
        self.assertFalse(list(self.ledger.glob('*/dns-*/withdrawal-attempt.json')))

    def test_missing_or_held_registration_cannot_be_adopted_for_cleanup(self):
        self.prepare_withdrawal()
        with self.assertRaises(OSError): self.run_dns('withdraw')
        self.dns_job, self.scope = deepcopy((self.registration['job'], self.registration['scope']))
        self.registered()
        parent = load_private(self.transaction())
        parent['status'] = 'DNS_REGISTRATION_HELD'
        replace_private(self.transaction(), encoded(parent))
        with self.assertRaises(ValueError): self.run_dns('withdraw')
        self.assertEqual(self.dns_server.update_requests, 1)

    def test_lost_withdrawal_reply_stays_held_until_read_only_recovery(self):
        self.registered()
        # Enable readback failure only after the second (withdrawal) commit.
        self.dns_server.drop_update_reply = True
        self.dns_server.before_update = lambda server: setattr(server, 'fail_after_commit', True)
        result = self.run_dns('withdraw')
        self.assertEqual(result['status'], 'DNS_WITHDRAWAL_HELD')
        original = self.withdrawal_transaction().read_bytes()
        with self.assertRaises(FileExistsError): self.run_dns('withdraw')
        self.dns_server.fail_after_commit = False
        self.assertEqual(self.run_dns('reconcile-withdrawal')['status'], 'AUTHORITATIVE_TOMBSTONE_OBSERVED')
        self.assertEqual(self.withdrawal_transaction().read_bytes(), original)
        self.assertEqual(self.dns_server.update_requests, 2)

    def test_failed_prewrite_observation_never_allows_a_second_attempt(self):
        self.registered()
        with patch.object(self.dns_client, 'exchange', side_effect=TimeoutError):
            self.assertEqual(self.run_dns('withdraw')['status'], 'DNS_WITHDRAWAL_HELD')
        self.assertEqual(self.run_dns('reconcile-withdrawal')['status'], 'DNS_WITHDRAWAL_HELD')
        with self.assertRaises(FileExistsError): self.run_dns('withdraw')
        self.assertIn(('app.fixture.invalid.', 'A'), self.dns_server.store)
        self.assertEqual(self.dns_server.update_requests, 1)

    def test_server_prerequisites_preserve_a_racing_foreign_value(self):
        self.registered()
        self.dns_server.before_update = lambda server: server.set('app.fixture.invalid.', 'A', 60, ['192.0.2.99'])
        result = self.run_dns('withdraw')
        self.assertEqual(result['status'], 'DNS_WITHDRAWAL_HELD')
        self.assertEqual(result['dns']['status'], 'PREREQUISITE_CONFLICT')
        self.assertEqual(self.dns_server.store[('app.fixture.invalid.', 'A')]['values'], ['192.0.2.99'])
        self.assertEqual(self.dns_server.commits, 1)

    def test_IPAM_change_after_withdrawal_cannot_report_cleanup_success(self):
        self.registered()
        def retire(_): type(self).row['status']['value'] = 'deprecated'
        self.dns_server.before_update = retire
        with self.assertRaises(ValueError): self.run_dns('withdraw')
        result = load_private(self.withdrawal_transaction())
        self.assertEqual(result['status'], 'DNS_WITHDRAWAL_HELD')
        self.assertEqual(result['dns']['status'], 'APPLIED_OBSERVED')
        self.assertNotIn(('app.fixture.invalid.', 'A'), self.dns_server.store)

    def test_failed_pending_journal_prevents_deletion(self):
        self.registered()
        real = handoff.replace_private
        def fail(path, data):
            record = json.loads(data)
            if record.get('dns') and record['dns']['status'] == 'UPDATE_PENDING':
                raise OSError('Synthetic durable write failure')
            return real(path, data)
        with patch.object(handoff, 'replace_private', side_effect=fail), self.assertRaises(OSError):
            self.run_dns('withdraw')
        self.assertIn(('app.fixture.invalid.', 'A'), self.dns_server.store)
        self.assertEqual(self.dns_server.update_requests, 1)

    def test_expired_withdrawal_can_be_read_back_without_renewing_mutation(self):
        self.registered()
        self.run_dns('withdraw')
        later = utcnow() + timedelta(hours=2)
        self.authority = dict(valid_from=(later - timedelta(minutes=1)).isoformat(),
                              valid_until=(later + timedelta(minutes=5)).isoformat())
        with patch.object(handoff, 'utcnow', return_value=later), patch('tools.run_files.utcnow', return_value=later):
            self.assertEqual(self.run_dns('reconcile-withdrawal')['status'], 'AUTHORITATIVE_TOMBSTONE_OBSERVED')
            with self.assertRaises(ValueError): self.run_dns('withdraw')
        self.assertEqual(self.dns_server.update_requests, 2)

    def test_withdrawal_authority_binds_parent_and_distinct_action(self):
        self.registered()
        binding = handoff.validate(self.job, self.receipt, self.dns_job, self.scope, action='withdraw',
                                    registration=self.registration, fixture=True)
        authority = self.authority | dict(format='hosting-netbox-dns-authority/1', binding_sha256=binding,
                    action='withdraw', change_ref='CHANGE-CLEANUP', token_sha256=digest(b'token'),
                    ca_sha256=None, tsig_sha256=digest(b'secret'))
        handoff.validate_authority(binding, 'withdraw', authority, b'token', None, b'secret')
        with self.assertRaises(ValueError):
            handoff.validate_authority(binding, 'reconcile-withdrawal', authority, b'token', None, b'secret')
        other = deepcopy(self.registration)
        other['scope']['allowed_records'][0]['maximum_ttl'] += 1
        changed = handoff.validate(self.job, self.receipt, self.dns_job, self.scope, action='withdraw',
                                    registration=other, fixture=True)
        self.assertNotEqual(binding, changed)
