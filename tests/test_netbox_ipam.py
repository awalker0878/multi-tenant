"""Real loopback TLS transport with synthetic NetBox-shaped responses."""
from copy import deepcopy
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import ssl
import tempfile
import threading
import unittest
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from lab.native_readback_fixture import credentials
from tools.netbox_ipam import AllocationReader, operate, validate_authority, validate
from tools.run_files import digest, encoded, load_private, utcnow
from tools.service_http import JsonService


class NetboxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        credentials(cls.base)
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, value, status=200):
                body = encoded(value)
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('API-Version', cls.version)
                self.send_header('ETag', 'W/"current"')
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                cls.calls.append((self.command, self.path))
                if cls.redirect:
                    self.send_response(302)
                    self.send_header('Location', 'https://never-contacted.invalid/')
                    self.end_headers()
                    return
                if self.path.startswith('/api/ipam/prefixes/'):
                    self.reply(dict(id=3, prefix='192.0.2.0/24', tenant={'id': 1}, vrf={'id': 2}))
                elif self.path.startswith('/api/ipam/vrfs/'):
                    self.reply(dict(id=2, tenant={'id': 1}, enforce_unique=cls.unique))
                elif self.path.startswith('/api/ipam/ip-addresses/?'):
                    self.reply(dict(count=int(cls.row is not None), next=None, results=[cls.row] if cls.row else []))
                elif self.path == '/api/ipam/ip-addresses/4/' and cls.row:
                    self.reply(cls.row)
                else:
                    self.reply({}, 404)

            def do_POST(self):
                cls.calls.append((self.command, self.path))
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if cls.row is not None:
                    self.reply({}, 400)
                    return
                cls.row = dict(payload, id=4)
                cls.row['tenant'] = {'id': payload['tenant']}
                cls.row['vrf'] = {'id': payload['vrf']}
                cls.row['status'] = {'value': payload['status']}
                self.reply(cls.row, 201)

            def do_PATCH(self):
                cls.calls.append((self.command, self.path))
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if cls.conflict or self.headers.get('If-Match') != 'W/"current"':
                    self.reply({}, 412)
                    return
                cls.row['status'] = {'value': payload['status']}
                self.reply(cls.row)
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(cls.base / 'server.pem'), str(cls.base / 'server.key'))
        cls.server.socket = context.wrap_socket(cls.server.socket, server_side=True)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={'poll_interval': .02}, daemon=True)
        cls.thread.start()
        cls.origin = f'https://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def setUp(self):
        cls = type(self)
        cls.row, cls.calls, cls.version = None, [], '4.7'
        cls.redirect, cls.conflict, cls.unique = False, False, True
        self.ledger_temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.ledger_temp.cleanup)
        self.ledger = Path(self.ledger_temp.name)
        self.job = dict(format='hosting-netbox-allocation/1', origin=self.origin,
                        scope=dict(environment_key='test', site_key='site-a', platform='openstack',
                                   tenant_key='tenant-a', wsd_key='science'), member='guest-a',
                        operation_id='allocation-a', generation=1, tenant_id=1, vrf_id=2, prefix_id=3,
                        prefix='192.0.2.0/24', address='192.0.2.20/24', reservation_ref='FIXTURE-ONLY')
        self.authority = dict(valid_from=(utcnow() - timedelta(minutes=1)).isoformat(),
                              valid_until=(utcnow() + timedelta(minutes=5)).isoformat())
        self.client = JsonService(self.origin, 'Bearer fixture-only', self.base / 'ca.pem')

    def run_action(self, action):
        return operate(self.job, action, self.authority, self.client, self.ledger)

    def test_reserve_confirm_retire_and_no_reuse(self):
        self.assertEqual(self.run_action('reserve')['allocation_status'], 'reserved')
        self.run_action('reserve')
        self.assertEqual(sum(method == 'POST' for method, _ in self.calls), 1)
        self.assertEqual(self.run_action('confirm')['allocation_status'], 'active')
        self.assertEqual(self.run_action('retire')['allocation_status'], 'deprecated')
        self.assertFalse(self.run_action('reconcile')['reusable'])
        with self.assertRaises(ValueError):
            self.run_action('reserve')
        with self.assertRaises(ValueError):
            self.run_action('confirm')
        self.assertFalse(any(method == 'DELETE' for method, _ in self.calls))

    def test_lost_success_is_read_back_without_second_post(self):
        request = self.client.request
        def lose(method, *args, **kwargs):
            result = request(method, *args, **kwargs)
            if method == 'POST':
                raise TimeoutError('Synthetic lost reply')
            return result
        with patch.object(self.client, 'request', side_effect=lose), self.assertRaises(TimeoutError):
            self.run_action('reserve')
        self.assertEqual(load_private(next(self.ledger.glob('*/head.json')))['status'], 'OUTCOME_UNKNOWN')
        with self.assertRaises(ValueError):
            self.run_action('reserve')
        self.assertEqual(self.run_action('reconcile')['allocation_status'], 'reserved')
        self.assertEqual(sum(method == 'POST' for method, _ in self.calls), 1)

    def test_uncertain_missing_object_stays_held(self):
        request = self.client.request
        def lose(method, *args, **kwargs):
            if method == 'POST':
                raise TimeoutError('No known response')
            return request(method, *args, **kwargs)
        with patch.object(self.client, 'request', side_effect=lose), self.assertRaises(TimeoutError):
            self.run_action('reserve')
        with self.assertRaises(ValueError):
            self.run_action('reconcile')
        with self.assertRaises(ValueError):
            self.run_action('reserve')

    def test_stale_conditional_update_holds(self):
        self.run_action('reserve')
        type(self).conflict = True
        with self.assertRaises(HTTPError):
            self.run_action('confirm')
        with self.assertRaises(ValueError):
            self.run_action('reconcile')
        self.assertEqual(type(self).row['status']['value'], 'reserved')

    def test_foreign_owner_and_changed_request_rejected(self):
        self.run_action('reserve')
        type(self).row['tenant'] = {'id': 99}
        with self.assertRaises(ValueError):
            self.run_action('confirm')
        self.job['generation'] = 2
        with self.assertRaises(ValueError):
            self.run_action('reserve')

    def test_service_and_tls_boundaries_before_mutation(self):
        for attribute, value in [('version', '4.5'), ('unique', False), ('redirect', True)]:
            original = getattr(type(self), attribute)
            setattr(type(self), attribute, value)
            with self.subTest(attribute=attribute), self.assertRaises(ValueError):
                self.run_action('reserve')
            setattr(type(self), attribute, original)
        untrusted = JsonService(self.origin, 'Bearer fixture-only')
        with self.assertRaises(URLError):
            operate(self.job, 'reserve', self.authority, untrusted, self.ledger)
        self.assertFalse(any(method != 'GET' for method, _ in self.calls))

    def test_exact_authority_binding_and_expiry(self):
        authority = self.authority | dict(request_sha256=validate(self.job), action='reserve',
                   change_ref='CHANGE-1', cleanup_ref=None, token_sha256=digest(b'fixture'), ca_sha256=None)
        validate_authority(self.job, 'reserve', authority, b'fixture', None)
        for change in [dict(action='retire'), dict(token_sha256='wrong'),
                       dict(valid_until=(utcnow() - timedelta(seconds=1)).isoformat())]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_authority(self.job, 'reserve', authority | change, b'fixture', None)

    def test_exact_readback_rejects_list_detail_identity_and_status_races(self):
        self.run_action('reserve')
        request = self.client.request
        for change in [dict(id=5), dict(status={'value': 'active'})]:
            def changed(method, path, *args, **kwargs):
                row, headers = request(method, path, *args, **kwargs)
                if path == '/api/ipam/ip-addresses/4/':
                    row.update(change)
                return row, headers
            before = len(self.calls)
            with self.subTest(change=change), patch.object(self.client, 'request', side_effect=changed):
                with self.assertRaises(ValueError):
                    self.run_action('confirm')
            self.assertTrue(all(method == 'GET' for method, _ in self.calls[before:]))
        self.assertEqual(load_private(next(self.ledger.glob('*/head.json')))['allocation_status'], 'reserved')

    def test_malformed_native_identity_and_collection_cannot_confirm(self):
        self.run_action('reserve')
        request = self.client.request
        cases = [('list', {'count': True}), ('list', {'count': -1}), ('list', {'results': None}),
                 ('detail', {'tenant': {'id': True}}), ('detail', {'id': True}),
                 ('detail', {'status': {'value': 'dhcp'}}), ('prefix', {'tenant': {'id': True}})]
        for target, change in cases:
            def changed(method, path, *args, **kwargs):
                row, headers = request(method, path, *args, **kwargs)
                if ((target == 'list' and '?' in path)
                        or (target == 'detail' and path == '/api/ipam/ip-addresses/4/')
                        or (target == 'prefix' and '/prefixes/' in path)):
                    row.update(change)
                return row, headers
            before = len(self.calls)
            with self.subTest(target=target, change=change), patch.object(self.client, 'request', side_effect=changed):
                with self.assertRaises(ValueError):
                    self.run_action('confirm')
            self.assertTrue(all(method == 'GET' for method, _ in self.calls[before:]))

    def test_dependent_readback_preserves_allocation_ledger(self):
        self.run_action('reserve')
        self.run_action('confirm')
        before = {p: p.read_bytes() for p in self.ledger.rglob('*') if p.is_file()}
        count = len(self.calls)
        reader = AllocationReader(self.job, self.authority, self.client)
        reader.namespace()
        row, etag = reader.observed()
        self.assertEqual((row['id'], reader.check(row), etag), (4, 'active', 'W/"current"'))
        self.assertTrue(all(method == 'GET' for method, _ in self.calls[count:]))
        self.assertEqual(before, {p: p.read_bytes() for p in self.ledger.rglob('*') if p.is_file()})
