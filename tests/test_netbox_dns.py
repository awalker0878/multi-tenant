"""Real loopback TLS IPAM + signed DNS wire handoff; no installed service claim."""
import base64
from copy import deepcopy
from datetime import timedelta
import io
import json
from pathlib import Path
import secrets
import sys
import unittest
from unittest.mock import patch
import uuid

from lab.dns_authority import Authority
from tests import test_netbox_ipam as ipam_fixture
from tests.test_dns_transactions import example
from tools import dns_change as dns_writer, netbox_dns as handoff
from tools.netbox_ipam import allocation_lock
from tools.run_files import digest, encoded, load_private, replace_private, utcnow, write_new


class NetboxDNSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ipam_fixture.NetboxTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        ipam_fixture.NetboxTests.tearDownClass.__func__(cls)

    run_action = ipam_fixture.NetboxTests.run_action

    def setUp(self):
        ipam_fixture.NetboxTests.setUp(self)
        self.run_action('reserve')
        self.receipt = self.run_action('confirm')
        self.secret = base64.b64encode(secrets.token_bytes(32)).decode()
        self.dns_server = Authority('fixture.invalid.', 'owner.fixture.invalid.', self.secret).__enter__()
        self.addCleanup(self.dns_server.__exit__, None, None, None)
        self.dns_job, self.scope = example(self.dns_server.port, value='192.0.2.20')
        self.prepare_dns()
        type(self).calls.clear()

    def prepare_dns(self):
        self.dns_job['tenant_id'] = self.scope['tenant_id'] = self.job['scope']['tenant_key']
        self.dns_job['resource_id'] = self.scope['resource_id'] = handoff.resource_id(self.job)
        self.dns_server.allow(dns_writer.marker_name(self.dns_job), *dns_writer.name_markers(self.dns_job),
                              *[r['name'] for r in self.dns_job['records']])
        self.dns_client = dns_writer.Client('127.0.0.1', self.dns_server.port,
                                            self.dns_job['key_name'], self.secret, timeout=.3)

    def run_dns(self, action='register'):
        return handoff.operate(self.job, self.receipt, self.dns_job, self.scope, self.authority,
                               self.client, self.dns_client, self.ledger, action=action, fixture=True)

    def transaction(self):
        return next(self.ledger.glob('*/dns-*/transaction.json'))

    def test_confirmed_A_registers_once_without_ipam_mutations(self):
        before = next(self.ledger.glob('*/head.json')).read_bytes()
        result = self.run_dns()
        self.assertEqual(result['status'], 'AUTHORITATIVE_REGISTRATION_OBSERVED')
        self.assertFalse(result['activation_authorized'] or result['reusable'])
        self.assertEqual(self.dns_server.commits, 1)
        self.assertTrue(all(method == 'GET' for method, _ in self.calls))
        self.assertEqual(before, next(self.ledger.glob('*/head.json')).read_bytes())
        with self.assertRaises(FileExistsError):
            self.run_dns()
        self.assertEqual(self.run_dns('reconcile')['dns']['status'], 'ALREADY_APPLIED_OBSERVED')
        self.assertEqual(self.dns_server.update_requests, 1)

    def test_exact_PTR_uses_separate_zone_transaction(self):
        self.run_dns()
        server = Authority('2.0.192.in-addr.arpa.', 'owner.fixture.invalid.', self.secret).__enter__()
        self.addCleanup(server.__exit__, None, None, None)
        self.dns_server = server
        self.dns_job, self.scope = example(server.port, zone='2.0.192.in-addr.arpa.',
                    name='20.2.0.192.in-addr.arpa.', rtype='PTR', value='app.fixture.invalid.')
        self.prepare_dns()
        self.assertEqual(self.run_dns()['status'], 'AUTHORITATIVE_REGISTRATION_OBSERVED')
        self.assertEqual(len(list(self.ledger.glob('*/dns-*/attempt.json'))), 2)
        self.assertEqual(server.commits, 1)

    def test_unconfirmed_receipt_foreign_owner_and_address_refused_offline(self):
        original = deepcopy((self.receipt, self.dns_job, self.scope))
        for field in ('reserved', 'address', 'scope', 'member', 'id', 'future', 'owner', 'dns_address', 'ipv6'):
            self.receipt, self.dns_job, self.scope = deepcopy(original)
            if field == 'reserved': self.receipt['allocation_status'] = 'reserved'
            if field == 'address': self.receipt['address'] = '192.0.2.21/24'
            if field == 'scope': self.receipt['scope']['site_key'] = 'elsewhere'
            if field == 'member': self.receipt['member'] = 'guest-b'
            if field == 'id': self.receipt['native_id'] = True
            if field == 'future': self.receipt['observed_at'] = (utcnow() + timedelta(hours=1)).isoformat()
            if field == 'owner': self.dns_job['resource_id'] = self.scope['resource_id'] = 'wrong-owner'
            if field in {'dns_address', 'ipv6'}:
                value = '192.0.2.21' if field == 'dns_address' else '2001:db8::20'
                self.dns_job['records'][0]['after']['values'] = self.scope['allowed_records'][0]['values'] = [value]
                if field == 'ipv6':
                    self.dns_job['records'][0]['type'] = self.scope['allowed_records'][0]['type'] = 'AAAA'
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.run_dns()
        self.assertEqual(self.calls, [])
        self.assertEqual(self.dns_server.queries, 0)
        self.assertFalse(list(self.ledger.glob('*/dns-*')))

    def test_unknown_or_replaced_current_ledger_refuses_before_contact(self):
        path = next(self.ledger.glob('*/head.json'))
        for row in [dict(status='OUTCOME_UNKNOWN'), self.receipt | {'native_id': 5}]:
            replace_private(path, encoded(row))
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.run_dns()
        self.assertEqual(self.calls, [])
        self.assertEqual(self.dns_server.queries, 0)

    def test_native_retirement_blocks_dns_and_leaves_attempt(self):
        type(self).row['status']['value'] = 'deprecated'
        with self.assertRaises(ValueError):
            self.run_dns()
        self.assertEqual(self.dns_server.queries, 0)
        self.assertEqual(load_private(self.transaction())['status'], 'DNS_REGISTRATION_HELD')
        with self.assertRaises(FileExistsError):
            self.run_dns()

    def test_IPAM_is_rechecked_after_dns_reads_before_update(self):
        snapshot = dns_writer.snapshot
        def retire_after_read(*args):
            result = snapshot(*args)
            type(self).row['status']['value'] = 'deprecated'
            return result
        with patch.object(dns_writer, 'snapshot', side_effect=retire_after_read), self.assertRaises(ValueError):
            self.run_dns()
        self.assertGreater(self.dns_server.queries, 0)
        self.assertEqual(self.dns_server.update_requests, 0)
        self.assertEqual(load_private(self.transaction())['dns']['status'], 'UPDATE_PENDING')

    def test_native_change_after_dns_write_cannot_report_success(self):
        def retire(_):
            type(self).row['status']['value'] = 'deprecated'
        self.dns_server.before_update = retire
        with self.assertRaises(ValueError):
            self.run_dns()
        result = load_private(self.transaction())
        self.assertEqual(result['status'], 'DNS_REGISTRATION_HELD')
        self.assertEqual(result['dns']['status'], 'APPLIED_OBSERVED')
        self.assertEqual(self.dns_server.commits, 1)

    def test_lost_reply_reconciles_read_only_and_preserves_original_journal(self):
        self.dns_server.drop_update_reply = self.dns_server.fail_after_commit = True
        result = self.run_dns()
        self.assertEqual(result['status'], 'DNS_REGISTRATION_HELD')
        self.assertEqual(result['dns']['status'], 'UNKNOWN_OUTCOME_OPERATOR_RECONCILIATION')
        original = self.transaction().read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_dns()
        self.dns_server.fail_after_commit = False
        self.assertEqual(self.run_dns('reconcile')['status'], 'AUTHORITATIVE_REGISTRATION_OBSERVED')
        self.assertEqual(self.transaction().read_bytes(), original)
        self.assertEqual(self.dns_server.update_requests, 1)

    def test_reconciliation_of_absence_never_retries_or_clears_attempt(self):
        with patch.object(self.dns_client, 'exchange', side_effect=TimeoutError):
            self.assertEqual(self.run_dns()['status'], 'DNS_REGISTRATION_HELD')
        self.assertEqual(self.run_dns('reconcile')['status'], 'DNS_REGISTRATION_HELD')
        with self.assertRaises(FileExistsError):
            self.run_dns()
        self.assertEqual(self.dns_server.update_requests, 0)

    def test_changing_operation_or_endpoint_does_not_bypass_attempt(self):
        self.run_dns()
        self.dns_job['operation_id'] = self.scope['operation_id'] = str(uuid.uuid4())
        with self.assertRaises(FileExistsError):
            self.run_dns()
        with self.assertRaises(ValueError):
            self.run_dns('reconcile')
        self.assertEqual(self.dns_server.update_requests, 1)

    def test_shared_allocation_lock_blocks_retirement_during_registration(self):
        snapshot = dns_writer.snapshot
        def concurrent_retire(*args):
            with self.assertRaises(BlockingIOError):
                self.run_action('retire')
            return snapshot(*args)
        with patch.object(dns_writer, 'snapshot', side_effect=concurrent_retire):
            self.assertEqual(self.run_dns()['status'], 'AUTHORITATIVE_REGISTRATION_OBSERVED')
        self.assertFalse(any(method != 'GET' for method, _ in self.calls))
        with allocation_lock(self.ledger, self.job), self.assertRaises(BlockingIOError):
            self.run_dns('reconcile')

    def test_failed_write_ahead_journal_prevents_dns_mutation(self):
        real = handoff.replace_private
        def fail_pending(path, data):
            if json.loads(data).get('dns', {}).get('status') == 'UPDATE_PENDING':
                raise OSError('Synthetic failed durable journal')
            return real(path, data)
        # Only inspect non-null DNS reports; initial reservation has no report.
        def guarded(path, data):
            return fail_pending(path, data) if json.loads(data).get('dns') else real(path, data)
        with patch.object(handoff, 'replace_private', side_effect=guarded), self.assertRaises(OSError):
            self.run_dns()
        self.assertEqual(self.dns_server.update_requests, 0)
        with self.assertRaises(FileExistsError):
            self.run_dns()

    def test_fresh_ipam_observation_time_does_not_erase_confirmation_binding(self):
        self.run_action('reconcile')
        self.assertEqual(self.run_dns()['status'], 'AUTHORITATIVE_REGISTRATION_OBSERVED')

    def test_new_read_authority_can_reconcile_expired_original_write_intent(self):
        self.run_dns()
        original = self.transaction().read_bytes()
        later = utcnow() + timedelta(hours=2)
        self.authority = dict(valid_from=(later - timedelta(minutes=1)).isoformat(),
                              valid_until=(later + timedelta(minutes=5)).isoformat())
        with patch.object(handoff, 'utcnow', return_value=later), \
                patch('tools.run_files.utcnow', return_value=later):
            result = self.run_dns('reconcile')
            self.assertEqual(result['status'], 'AUTHORITATIVE_REGISTRATION_OBSERVED')
            self.assertEqual(result['dns']['update_attempts'], 0)
            with self.assertRaises(ValueError):
                self.run_dns()
        self.assertEqual(self.transaction().read_bytes(), original)
        self.assertEqual(self.dns_server.update_requests, 1)

    def test_native_revision_drift_is_held_before_dns_contact(self):
        request = self.client.request
        def changed(method, path, *args, **kwargs):
            row, headers = request(method, path, *args, **kwargs)
            if path == '/api/ipam/ip-addresses/4/': headers['ETag'] = 'W/"next"'
            return row, headers
        with patch.object(self.client, 'request', side_effect=changed), self.assertRaises(ValueError):
            self.run_dns()
        self.assertEqual(self.dns_server.queries, 0)

    def test_expired_disabled_and_wrong_transport_never_contact(self):
        for case in ('disabled', 'expired', 'transport'):
            original = deepcopy(self.authority), self.dns_job['enabled'], self.scope['enabled'], self.dns_client.port
            if case == 'disabled': self.dns_job['enabled'] = self.scope['enabled'] = False
            if case == 'expired': self.authority['valid_until'] = (utcnow() - timedelta(seconds=1)).isoformat()
            if case == 'transport': self.dns_client.port += 1
            with self.subTest(case=case), self.assertRaises(ValueError): self.run_dns()
            self.authority, self.dns_job['enabled'], self.scope['enabled'], self.dns_client.port = original
        self.assertEqual(self.calls, [])
        self.assertEqual(self.dns_server.queries, 0)

    def test_authority_binds_both_credentials_CA_action_and_entire_intent(self):
        binding = handoff.validate(self.job, self.receipt, self.dns_job, self.scope, fixture=True)
        authority = self.authority | dict(format='hosting-netbox-dns-authority/1', binding_sha256=binding,
                        action='register', change_ref='CHANGE-1', token_sha256=digest(b'token'),
                        ca_sha256=None, tsig_sha256=digest(b'secret'))
        handoff.validate_authority(binding, 'register', authority, b'token', None, b'secret')
        for field in ('binding_sha256', 'token_sha256', 'ca_sha256', 'tsig_sha256', 'action'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                handoff.validate_authority(binding, 'register', authority | {field: 'changed'}, b'token', None, b'secret')
        other = deepcopy(self.scope)
        other['allowed_records'][0]['maximum_ttl'] += 1
        self.assertNotEqual(binding, handoff.validate(self.job, self.receipt, self.dns_job, other, fixture=True))

    def test_default_CLI_is_offline_and_no_fixture_switch_is_exposed(self):
        # Use native-shaped private inputs, but forbid every service call.
        allocation, receipt, job, scope = deepcopy((self.job, self.receipt, self.dns_job, self.scope))
        allocation.update(origin='https://netbox.corp.internal', prefix='10.42.0.0/24', address='10.42.0.20/24')
        receipt.update(request_sha256=handoff.validate_allocation(allocation), address=allocation['address'])
        for obj in (job, scope):
            obj.update(zone='corp.internal.', server='10.42.1.53', key_name='owner.corp.internal.')
        job['records'][0].update(name='app.corp.internal.', after={'ttl': 60, 'values': ['10.42.0.20']})
        scope['allowed_records'][0].update(name='app.corp.internal.', values=['10.42.0.20'])
        argv = ['netbox_dns.py', '--action', 'register']
        for key, data in zip(('allocation', 'confirmation', 'job', 'scope'), (allocation, receipt, job, scope)):
            path = self.ledger / (key + '.json')
            write_new(path, encoded(data))
            argv.extend(['--' + key, str(path)])
        stdout = io.StringIO()
        with patch.object(sys, 'argv', argv), patch('sys.stdout', stdout), \
                patch.object(handoff.JsonService, 'request', side_effect=AssertionError('No contact')), \
                patch.object(dns_writer.Client, 'exchange', side_effect=AssertionError('No contact')):
            self.assertEqual(handoff.main(), 0)
        self.assertEqual(json.loads(stdout.getvalue())['status'], 'VALIDATED_NO_CONTACT')
        self.assertEqual(self.calls, [])
        self.assertNotIn('--fixture', Path(handoff.__file__).read_text())
