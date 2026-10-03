"""Real loopback TLS and independent signatures exercise the native GET path.

No installed Prism Central, Vault or workload is contacted. Session tokens and keys are
synthetic. The native server is a protocol fixture, not platform qualification.
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import ssl
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provisioner.controlplane.discovery import native_https
from provisioner.controlplane.discovery.adapters.ahv_https import AhvHttpsTransport
from provisioner.controlplane.discovery.adapters.ahv import COLLECTOR_ID, API_VERSION, VM_PATH
from provisioner.controlplane.discovery.model import _json, assemble_discovery_result
from provisioner.controlplane.discovery.native_credentials import NativeReadHeld
from provisioner.controlplane.discovery.adapters.ahv_credentials import SignedFileAhvCredentialSource
from provisioner.controlplane.discovery.trust import (
    DiscoveryKeyEnrollment, DiscoverySignature, DiscoveryTrustPolicy,
    SignedDiscoveryIngestVerifier, SignedFileDiscoveryTrustStore,
    campaign_signing_bytes, trust_policy_signing_bytes)
from provisioner.controlplane.discovery.witness import (
    NativeCredentialWitnessPolicy, NativeReadCredentialWitness,
    SignedFileDiscoveryCredentialAuthority, credential_witness_signing_bytes)
from tests.provisioning.controlplane.test_ahv_discovery import (
    CLUSTER, VM1, VM2, campaign, vm, response)
from urllib.parse import parse_qs, urlsplit
from tests.provisioning.worker.tls_fixtures import TestPki


def encoded(value):
    return base64.b64encode(value).decode('ascii')


class AhvHttpsTests(unittest.TestCase):
    def setUp(self):
        self.pki = TestPki()
        self.addCleanup(self.pki.close)
        self.root = self.pki.root
        self.pki.issue('native')
        self.root_key, self.native_key, self.issuer_key, self.collector_key = (
            Ed25519PrivateKey.generate() for _ in range(4))
        self.now = datetime.now(timezone.utc)
        before, after = self.now - timedelta(seconds=10), self.now + timedelta(minutes=20)
        self.campaign = replace(campaign(), issued_at=before, expires_at=self.now + timedelta(minutes=2))
        self.environment = 'environment-1'
        self.reference = 'vault:native-reader'
        self.trust_path, self.witness_path = self.root / 'trust.json', self.root / 'witness.json'
        enrollments = (
            DiscoveryKeyEnrollment('issuer', 'approval-service', 'issuer',
                encoded(self.issuer_key.public_key().public_bytes_raw()), self.environment,
                self.campaign.scope, before, after),
            DiscoveryKeyEnrollment('collector', COLLECTOR_ID, 'collector',
                encoded(self.collector_key.public_key().public_bytes_raw()), self.environment,
                self.campaign.scope, before, after, self.reference))
        self.policy = DiscoveryTrustPolicy(1, before, after, enrollments)
        self.write_trust()
        self.witness = NativeReadCredentialWitness(self.reference, COLLECTOR_ID, self.environment,
            self.campaign.scope, 'native-rbac-review', 'a' * 64, before, after, True)
        self.witness_policy = NativeCredentialWitnessPolicy(1, before,
            self.now + timedelta(minutes=4), (self.witness,))
        self.write_witness()
        self.verifier = SignedDiscoveryIngestVerifier(
            SignedFileDiscoveryTrustStore(self.trust_path,
                authority_public_key=self.root_key.public_key(), minimum_revision=1),
            SignedFileDiscoveryCredentialAuthority(self.witness_path,
                authority_public_key=self.native_key.public_key(), minimum_revision=1)).bind(
                    DiscoverySignature('issuer', encoded(self.issuer_key.sign(
                        campaign_signing_bytes(self.campaign, self.environment)))))
        self.calls, self.on_get, self.delay = [], None, 0
        self.responses = {0: response([vm()], 2, next_page=1), 1: response([vm(VM2)], 2)}
        self.response_status = 200
        self.request_started = threading.Event()
        self.headers_sent = threading.Event()
        self.handler_finished = threading.Event()
        self.stop_response = threading.Event()
        self.raw_body, self.extra_headers, self.drip = None, [], False
        case = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def handle(self):
                try:
                    super().handle()
                except (OSError, ssl.SSLError):
                    pass  # Expected when revocation stops the client after TLS.
            def do_GET(self):
                # A request owns its behavior. A late handler must not read the
                # next request's mutable delay/drip configuration.
                delay, drip = case.delay, case.drip
                case.calls.append((self.command, self.path, dict(self.headers)))
                case.request_started.set()
                try:
                    if case.on_get:
                        case.on_get()
                    if case.stop_response.wait(delay):
                        return
                    index = int(parse_qs(urlsplit(self.path).query)['$page'][0])
                    value = case.responses.get(index, response([], 0))
                    body = case.raw_body if case.raw_body is not None else json.dumps(value).encode()
                    self.send_response(case.response_status)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(body)))
                    for name, value in case.extra_headers:
                        self.send_header(name, value)
                    self.end_headers()
                    case.headers_sent.set()
                    if drip:
                        for byte in body:
                            self.wfile.write(bytes([byte]))
                            self.wfile.flush()
                            if case.stop_response.wait(0.02):
                                return
                    else:
                        self.wfile.write(body)
                except (OSError, ssl.SSLError):
                    pass
                finally:
                    case.handler_finished.set()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.root / 'native.pem', self.root / 'native.key')
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={'poll_interval': 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.credential_path = self.root / 'credential.json'
        self.token = 'synthetic-session-token-no-native-authority'
        self.binding = {
            'format': 'hosting-ahv-read-credential/1', 'revision': 1,
            'campaignDigest': self.campaign.digest(), 'environmentId': self.environment,
            'collectorId': COLLECTOR_ID, 'serviceAccountId': 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
            'credentialReference': self.reference, 'apiVersion': API_VERSION,
            'origin': f'https://localhost:{self.server.server_port}', 'connectIp': '127.0.0.1',
            'caDigest': hashlib.sha256((self.root / 'ca.pem').read_bytes()).hexdigest(),
            'apiKeyDigest': hashlib.sha256(self.token.encode()).hexdigest(),
            'notBefore': before.isoformat(), 'expiresAt': after.isoformat()}
        self.write_material()
        self.source = SignedFileAhvCredentialSource(self.credential_path,
            authority_public_key=self.native_key.public_key(), minimum_revision=1)
        self.transport = self.client()

    def stop(self):
        self.stop_response.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def write_signed(self, path, body, key, payload):
        path.write_text(json.dumps({'policy': body.as_dict(),
            'signature': encoded(key.sign(payload(body)))}))
        path.chmod(0o600)

    def write_trust(self):
        self.write_signed(self.trust_path, self.policy, self.root_key, trust_policy_signing_bytes)

    def write_witness(self):
        self.write_signed(self.witness_path, self.witness_policy,
                          self.native_key, credential_witness_signing_bytes)

    def write_material(self, *, signer=None):
        self.credential_path.write_text(json.dumps({'binding': self.binding, 'apiKey': self.token,
            'signature': encoded((signer or self.native_key).sign(_json(self.binding).encode('ascii')))}))
        self.credential_path.chmod(0o600)

    def client(self, **changes):
        args = dict(verifier=self.verifier, credentials=self.source,
                    ca_bundle=self.root / 'ca.pem', clock=lambda: self.now)
        args.update(changes)
        return AhvHttpsTransport(self.campaign, self.environment, **args)

    def read_material(self):
        return self.source.read(self.campaign, self.environment, checked_at=self.now)

    def revoke_witness(self):
        self.witness_policy = replace(self.witness_policy, revision=self.witness_policy.revision + 1,
            witnesses=(replace(self.witness, revoked_at=self.now),))
        self.write_witness()

    def params(self, page=0):
        return {'$page': page, '$limit': 1, '$filter': f"cluster/extId eq '{CLUSTER}'"}

    def test_actual_tls_collects_two_cluster_pages_without_claiming_complete_visibility(self):
        result = assemble_discovery_result(self.campaign, self.transport.collect(), checked_at=self.now)
        self.assertEqual(result.completeness, 'PARTIAL')
        self.assertIn('VISIBLE_INVENTORY_ONLY', result.collection_errors)
        self.assertEqual([o.identity.native_id for o in result.objects], [VM1, VM2])
        self.assertEqual(len(self.calls), 2)
        for index, (method, path, headers) in enumerate(self.calls):
            self.assertEqual(method, 'GET')
            self.assertEqual(urlsplit(path).path, VM_PATH)
            self.assertEqual(parse_qs(urlsplit(path).query),
                             {k: [str(v)] for k, v in self.params(index).items()})
            self.assertEqual(headers['X-Ntnx-Api-Key'], self.token)
            self.assertNotIn('Authorization', headers)
        self.assertNotIn(self.token, repr(result))
        self.assertNotIn(self.token, repr(self.read_material()))

    def test_empty_visible_list_does_not_prove_complete_inventory(self):
        self.responses = {0: response([], 0)}
        result = assemble_discovery_result(self.campaign, self.transport.collect(), checked_at=self.now)
        self.assertEqual(result.completeness, 'PARTIAL')
        self.assertEqual(result.objects, ())
        self.assertIn('VISIBLE_INVENTORY_ONLY', result.collection_errors)

    def test_paths_page_filter_and_limit_are_exact_before_connection(self):
        for path, params in (
            ('https://evil.invalid'+VM_PATH, self.params()),
            (VM_PATH+'?all=true', self.params()),
            (VM_PATH+'/vm-1/$actions/power-off', self.params()),
            ('/api/iam/v4.0/authn/users', self.params()),
            (VM_PATH, {**self.params(), '$filter': 'true'}),
            (VM_PATH, {**self.params(), '$limit': True}),
            (VM_PATH, {**self.params(), '$limit': 100}),
            (VM_PATH, {**self.params(), '$page': True}),
            (VM_PATH, self.params(1)),
            (VM_PATH, {**self.params(), '$select': '*'})):
            with self.subTest(path=path, params=params), self.assertRaises(NativeReadHeld):
                self.client().get(path, params=params)
        self.assertEqual(self.calls, [])

    def test_pages_cannot_repeat_skip_or_exceed_budget(self):
        self.transport.get(VM_PATH, params=self.params())
        with self.assertRaises(NativeReadHeld):
            self.transport.get(VM_PATH, params=self.params())
        other = self.client()
        other._requests = self.campaign.max_pages
        with self.assertRaises(NativeReadHeld):
            other.get(VM_PATH, params=self.params(other._requests))
        with self.assertRaises(NativeReadHeld):
            self.transport.get(VM_PATH, params=self.params(1))
        self.assertEqual(len(self.calls), 1)

    def test_missing_unsigned_and_modified_material_prevents_native_read(self):
        self.write_material(signer=Ed25519PrivateKey.generate())
        with self.assertRaises(NativeReadHeld):
            self.client().get(VM_PATH, params=self.params())
        self.write_material()
        doc = json.loads(self.credential_path.read_text())
        doc['apiKey'] += 'tampered'
        self.credential_path.write_text(json.dumps(doc))
        with self.assertRaises(NativeReadHeld):
            self.client().get(VM_PATH, params=self.params())
        self.credential_path.unlink()
        with self.assertRaises(NativeReadHeld):
            self.client().get(VM_PATH, params=self.params())
        self.assertEqual(self.calls, [])

    def test_binding_must_match_exact_campaign_account_api_and_enrollment(self):
        original = dict(self.binding)
        for field, bad in (('campaignDigest', 'f'*64), ('environmentId', 'other'),
                           ('collectorId', 'other'), ('apiVersion', 'v4.1'),
                           ('serviceAccountId', None), ('serviceAccountId', 'administrator'),
                           ('credentialReference', 'vault:other'),
                           ('format', 'hosting-vmware-read-credential/1')):
            with self.subTest(field=field):
                self.binding = {**original, field: bad}
                self.write_material()
                with self.assertRaises(NativeReadHeld):
                    self.client().get(VM_PATH, params=self.params())
        self.assertEqual(self.calls, [])

    def test_campaign_root_issuer_and_collector_cannot_sign_native_material(self):
        for key in (self.root_key, self.issuer_key, self.collector_key):
            self.write_material(signer=key)
            source = SignedFileAhvCredentialSource(self.credential_path,
                authority_public_key=key.public_key(), minimum_revision=1)
            with self.assertRaises(NativeReadHeld):
                self.client(credentials=source).get(VM_PATH, params=self.params())
        self.assertEqual(self.calls, [])

    def test_revoked_or_write_capable_witness_prevents_native_reads(self):
        self.revoke_witness()
        with self.assertRaises(NativeReadHeld):
            self.transport.get(VM_PATH, params=self.params())
        self.witness_policy = replace(self.witness_policy, revision=3,
                                      witnesses=(replace(self.witness, read_only=False),))
        self.write_witness()
        with self.assertRaises(NativeReadHeld):
            self.client().get(VM_PATH, params=self.params())
        self.assertEqual(self.calls, [])

    def test_revocation_during_collection_cannot_be_published_as_error_pages(self):
        self.on_get = self.revoke_witness
        with self.assertRaises(NativeReadHeld):
            self.transport.collect()
        self.assertEqual(len(self.calls), 1)

    def test_rotation_during_tls_cannot_send_old_key(self):
        original = ssl.SSLSocket.do_handshake
        case = self
        def rotate(sock, *args, **kwargs):
            result = original(sock, *args, **kwargs)
            if not sock.server_side:
                case.binding['revision'] += 1
                case.write_material()
            return result
        with patch.object(ssl.SSLSocket, 'do_handshake', rotate), self.assertRaises(NativeReadHeld):
            self.transport.get(VM_PATH, params=self.params())
        self.assertEqual(self.calls, [])

    def test_rotation_during_response_discards_result(self):
        def rotate():
            self.binding['revision'] += 1
            self.write_material()
        self.on_get = rotate
        with self.assertRaises(NativeReadHeld):
            self.transport.get(VM_PATH, params=self.params())
        self.assertEqual(len(self.calls), 1)

    def test_valid_rotation_is_accepted_between_page_reads(self):
        self.transport.get(VM_PATH, params=self.params())
        self.binding['revision'] += 1
        self.token += '-rotated'
        self.binding['apiKeyDigest'] = hashlib.sha256(self.token.encode()).hexdigest()
        self.write_material()
        status, _ = self.transport.get(VM_PATH, params=self.params(1))
        self.assertEqual(status, 200)
        self.assertEqual(self.calls[-1][2]['X-Ntnx-Api-Key'], self.token)

    def test_private_files_no_symlink_fifo_or_public_read_fallback(self):
        self.credential_path.chmod(0o644)
        with self.assertRaises(NativeReadHeld):
            self.read_material()
        self.credential_path.chmod(0o600)
        saved = self.credential_path.with_suffix('.saved')
        self.credential_path.rename(saved)
        self.credential_path.symlink_to(saved)
        with self.assertRaises(NativeReadHeld):
            self.read_material()
        self.credential_path.unlink()
        os.mkfifo(self.credential_path, 0o600)
        with self.assertRaises(NativeReadHeld):
            self.read_material()
        self.credential_path.unlink()

    def test_revision_floor_rollback_and_equivocation_are_rejected(self):
        self.read_material()
        self.binding['serviceAccountId'] = VM2
        self.write_material()
        with self.assertRaises(NativeReadHeld):
            self.read_material()
        self.binding['revision'] = 2
        self.write_material()
        self.read_material()
        self.binding['revision'] = 1
        self.write_material()
        with self.assertRaises(NativeReadHeld):
            self.read_material()
        other = SignedFileAhvCredentialSource(self.credential_path,
            authority_public_key=self.native_key.public_key(), minimum_revision=2)
        with self.assertRaises(NativeReadHeld):
            other.read(self.campaign, self.environment, checked_at=self.now)

    def test_bad_tls_identity_and_changed_ca_never_send_key(self):
        self.binding['origin'] = self.binding['origin'].replace('localhost', 'wrong.invalid')
        self.write_material()
        with self.assertRaises(NativeReadHeld):
            self.client().get(VM_PATH, params=self.params())
        self.binding['origin'] = self.binding['origin'].replace('wrong.invalid', 'localhost')
        self.write_material()
        (self.root/'ca.pem').write_bytes((self.root/'ca.pem').read_bytes()+b'\n')
        with self.assertRaises(NativeReadHeld):
            self.client().get(VM_PATH, params=self.params())
        self.assertEqual(self.calls, [])

    def test_redirect_error_body_and_retry_are_not_followed(self):
        self.response_status = 302
        self.raw_body = self.token.encode()
        self.extra_headers = [('Location', 'https://other.invalid/')]
        with self.assertRaises(NativeReadHeld) as caught:
            self.transport.get(VM_PATH, params=self.params())
        self.assertNotIn(self.token, str(caught.exception))
        with self.assertRaises(NativeReadHeld):
            self.transport.get(VM_PATH, params=self.params(1))
        self.assertEqual(len(self.calls), 1)
        self.response_status = 403
        other = self.client()
        self.assertEqual(other.get(VM_PATH, params=self.params()), (403, None))
        with self.assertRaises(NativeReadHeld):
            other.get(VM_PATH, params=self.params(1))

    def test_http_denial_is_unknown_not_empty_success(self):
        self.response_status = 403
        self.raw_body = self.token.encode()
        result = assemble_discovery_result(self.campaign, self.transport.collect(), checked_at=self.now)
        self.assertEqual(result.completeness, 'UNKNOWN')
        self.assertIn('VM_LIST_PERMISSION_DENIED', result.collection_errors)
        self.assertNotIn(self.token, repr(result))

    def test_invalid_json_framing_and_size_are_held(self):
        for body in (b' {"data":[],"data":[]}', b'{"x":NaN}', b'{"x":1e9999}',
                     b'{"x":9223372036854775808}', b'['*34+b'0'+b']'*34, b'\xff'):
            self.raw_body = body
            with self.subTest(body=body), self.assertRaises(NativeReadHeld):
                self.client().get(VM_PATH, params=self.params())
        self.raw_body = b' '*2048
        with self.assertRaises(NativeReadHeld):
            self.client(max_response_bytes=1024).get(VM_PATH, params=self.params())
        self.raw_body = None
        self.extra_headers = [('Content-Length', '1')]
        with self.assertRaises(NativeReadHeld):
            self.client().get(VM_PATH, params=self.params())

    def test_cross_cluster_response_and_untrusted_links_remain_unknown(self):
        self.responses = {0: response([vm(native_cluster=VM2)], 1)}
        result = assemble_discovery_result(self.campaign, self.transport.collect(), checked_at=self.now)
        self.assertEqual(result.completeness, 'UNKNOWN')
        self.assertIn('VM_OUTSIDE_NATIVE_SCOPE', result.collection_errors)
        answer = response([vm()], 2, next_page=1)
        answer['metadata']['links'][-1]['href'] = 'https://untrusted.invalid/vms'
        self.responses = {0: answer}
        result = assemble_discovery_result(self.campaign, self.client().collect(), checked_at=self.now)
        self.assertEqual(result.completeness, 'UNKNOWN')
        self.assertEqual(len(self.calls), 2)

    def test_expired_or_backward_clock_cannot_start_or_finish_collection(self):
        for at in (None, self.campaign.expires_at, self.campaign.issued_at-timedelta(seconds=1)):
            with self.subTest(at=at), self.assertRaises(NativeReadHeld):
                self.client(clock=lambda: at).get(VM_PATH, params=self.params())
        self.assertEqual(self.calls, [])
        self.on_get = lambda: setattr(self, 'now', self.campaign.expires_at)
        with self.assertRaises(NativeReadHeld):
            self.transport.collect()
        self.assertEqual(len(self.calls), 1)

    def test_slow_headers_close_response_and_exhaust_transport(self):
        self.delay = 3
        client = self.client(timeout=0.2)
        observed = []
        class Response(http.client.HTTPResponse):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                observed.append(self)
        try:
            with patch.object(http.client.HTTPConnection, 'response_class', Response):
                with self.assertRaises(NativeReadHeld):
                    client.get(VM_PATH, params=self.params())
            self.assertTrue(self.request_started.is_set())
            self.assertTrue(observed)
            self.assertTrue(all(r.isclosed() for r in observed))
            self.assertTrue(client._failed)
        finally:
            self.stop_response.set()
            self.assertTrue(self.handler_finished.wait(2))

    def test_binding_size_types_duplicate_keys_and_secret_header_injection(self):
        original = dict(self.binding)
        for field, value in (('origin', 'http://localhost'), ('origin', 'https://user:pass@localhost'),
                             ('origin', 'https://local\nhost'), ('connectIp', '0.0.0.0'),
                             ('connectIp', 'dns.example'), ('caDigest', 'bad'),
                             ('revision', True), ('revision', 2**63),
                             ('expiresAt', (self.now+timedelta(hours=2)).isoformat())):
            with self.subTest(field=field, value=value):
                self.binding = {**original, field: value}
                self.write_material()
                with self.assertRaises(NativeReadHeld):
                    self.client().get(VM_PATH, params=self.params())
        self.binding = original
        self.write_material()
        raw = self.credential_path.read_text()
        self.credential_path.write_text(raw.replace('"revision": 1', '"revision": 1, "revision": 1'))
        with self.assertRaises(NativeReadHeld):
            self.read_material()
        self.token += '\r\nInjected:header'
        self.binding['apiKeyDigest'] = hashlib.sha256(self.token.encode()).hexdigest()
        self.write_material()
        with self.assertRaises(NativeReadHeld):
            self.read_material()
        self.credential_path.write_text(' '*32769)
        with self.assertRaises(NativeReadHeld):
            self.read_material()
        self.assertEqual(self.calls, [])

    def test_campaign_expiry_after_error_never_publishes_current_error_evidence(self):
        self.response_status = 403
        self.on_get = lambda: setattr(self, 'now', self.campaign.expires_at)
        with self.assertRaises(NativeReadHeld):
            self.transport.collect()
        self.assertEqual(len(self.calls), 1)

    def test_concurrent_request_is_bounded_without_a_second_connection(self):
        client = self.client(timeout=0.01)
        client._lock.acquire()
        try:
            with self.assertRaises(NativeReadHeld):
                client.get(VM_PATH, params=self.params())
        finally:
            client._lock.release()
        self.assertEqual(self.calls, [])

    def test_drip_response_cannot_extend_total_deadline(self):
        self.drip = True
        self.raw_body = b'{' + b' '*200 + b'}'
        client = self.client(timeout=0.2)
        start = time.monotonic()
        try:
            with self.assertRaises(NativeReadHeld):
                client.get(VM_PATH, params=self.params())
            self.assertTrue(self.headers_sent.is_set())
            self.assertLess(time.monotonic()-start, 2)
        finally:
            self.stop_response.set()
            self.assertTrue(self.handler_finished.wait(2))

    def test_valid_decode_after_deadline_is_not_returned(self):
        expired = threading.Event()
        monotonic = time.monotonic
        clock = SimpleNamespace(monotonic=lambda: monotonic()+(60 if expired.is_set() else 0))
        decode = native_https.decode_json
        def late_decode(body, limit):
            result = decode(body, limit)
            expired.set()
            return result
        with patch.object(native_https, 'time', clock), patch.object(native_https, 'decode_json', late_decode):
            with self.assertRaises(NativeReadHeld):
                self.transport.get(VM_PATH, params=self.params())
        self.assertTrue(expired.is_set())
        self.assertTrue(self.transport._failed)

    def test_wrong_native_scope_or_collector_requires_a_new_campaign(self):
        original = self.campaign
        for c in (replace(original, collector_id='other'),
                  replace(original, scope=replace(original.scope, native_scope_id='not-a-uuid')),
                  replace(original, allowed_kinds=('vm', 'network'))):
            self.campaign = c
            with self.assertRaises(ValueError):
                self.client()
        self.campaign = replace(original, scope=replace(original.scope, tenant_id='other'))
        with self.assertRaises(NativeReadHeld):
            self.client().get(VM_PATH, params=self.params())
        self.assertEqual(self.calls, [])

    def test_no_vendor_imports_in_shared_https_and_no_legacy_credential_aliases(self):
        from provisioner.controlplane.discovery import native_credentials
        from provisioner.controlplane.discovery.adapters import ahv_credentials, ahv_https
        self.assertEqual(SignedFileAhvCredentialSource.__module__, ahv_credentials.__name__)
        self.assertFalse(hasattr(native_credentials, 'SignedFileAhvCredentialSource'))
        self.assertIs(ahv_https.read_json, native_https.read_json)


if __name__ == '__main__':
    unittest.main()
