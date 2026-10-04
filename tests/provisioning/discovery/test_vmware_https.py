"""Real loopback TLS and independent signatures exercise the native GET path.

No installed vCenter, Vault or workload is contacted. Session tokens and keys are
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
from provisioner.controlplane.discovery.adapters.vmware_https import VmwareHttpsTransport
from provisioner.controlplane.discovery.adapters.vmware_rest import PROFILE
from provisioner.controlplane.discovery.model import _json, assemble_discovery_result
from provisioner.controlplane.discovery.native_credentials import NativeReadHeld
from provisioner.controlplane.discovery.adapters.vmware_credentials import (
    SignedFileVmwareCredentialSource, selection_digest)
from provisioner.controlplane.discovery.trust import (
    DiscoveryKeyEnrollment, DiscoverySignature, DiscoveryTrustPolicy,
    SignedDiscoveryIngestVerifier, SignedFileDiscoveryTrustStore,
    campaign_signing_bytes, trust_policy_signing_bytes)
from provisioner.controlplane.discovery.witness import (
    NativeCredentialWitnessPolicy, NativeReadCredentialWitness,
    SignedFileDiscoveryCredentialAuthority, credential_witness_signing_bytes)
from tests.provisioning.discovery.test_vmware_hardware import (
    DETAIL, LIST, SELECTION, VM1, campaign, detail)
from tests.provisioning.worker.tls_fixtures import TestPki


def encoded(value):
    return base64.b64encode(value).decode('ascii')


class VmwareHttpsTests(unittest.TestCase):
    def setUp(self):
        self.pki = TestPki()
        self.addCleanup(self.pki.close)
        self.root = self.pki.root
        self.pki.issue('native')
        self.root_key, self.native_key, self.issuer_key, self.collector_key = (
            Ed25519PrivateKey.generate() for _ in range(4))
        self.now = datetime.now(timezone.utc)
        before, after = self.now - timedelta(seconds=10), self.now + timedelta(minutes=20)
        self.campaign = campaign(issued_at=before, expires_at=self.now + timedelta(minutes=2))
        self.environment = 'environment-1'
        self.reference = 'vault:native-reader'
        self.trust_path, self.witness_path = self.root / 'trust.json', self.root / 'witness.json'
        enrollments = (
            DiscoveryKeyEnrollment('issuer', 'approval-service', 'issuer',
                encoded(self.issuer_key.public_key().public_bytes_raw()), self.environment,
                self.campaign.scope, before, after),
            DiscoveryKeyEnrollment('collector', PROFILE, 'collector',
                encoded(self.collector_key.public_key().public_bytes_raw()), self.environment,
                self.campaign.scope, before, after, self.reference))
        self.policy = DiscoveryTrustPolicy(1, before, after, enrollments)
        self.write_trust()
        self.witness = NativeReadCredentialWitness(self.reference, PROFILE, self.environment,
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
                    value = [dict(VM1)] if self.path == LIST else detail()
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
            'format': 'hosting-vmware-read-credential/1', 'revision': 1,
            'campaignDigest': self.campaign.digest(), 'environmentId': self.environment,
            'collectorId': PROFILE, 'selectionDigest': selection_digest(SELECTION),
            'credentialReference': self.reference, 'apiRelease': SELECTION.api_release,
            'origin': f'https://localhost:{self.server.server_port}', 'connectIp': '127.0.0.1',
            'caDigest': hashlib.sha256((self.root / 'ca.pem').read_bytes()).hexdigest(),
            'tokenDigest': hashlib.sha256(self.token.encode()).hexdigest(),
            'notBefore': before.isoformat(), 'expiresAt': after.isoformat()}
        self.write_material()
        self.source = SignedFileVmwareCredentialSource(self.credential_path,
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
        self.credential_path.write_text(json.dumps({'binding': self.binding, 'token': self.token,
            'signature': encoded((signer or self.native_key).sign(_json(self.binding).encode('ascii')))}))
        self.credential_path.chmod(0o600)

    def client(self, **changes):
        args = dict(verifier=self.verifier, credentials=self.source,
                    ca_bundle=self.root / 'ca.pem', clock=lambda: self.now)
        args.update(changes)
        return VmwareHttpsTransport(self.campaign, SELECTION, self.environment, **args)

    def read_material(self):
        return self.source.read(self.campaign, SELECTION, self.environment, checked_at=self.now)

    def revoke_witness(self):
        self.witness_policy = replace(self.witness_policy, revision=self.witness_policy.revision + 1,
            witnesses=(replace(self.witness, revoked_at=self.now),))
        self.write_witness()

    def test_actual_tls_campaign_collects_hardware_but_keeps_partial_visibility(self):
        pages = self.transport.collect()
        result = assemble_discovery_result(self.campaign, pages, checked_at=self.now)
        self.assertEqual(result.completeness, 'PARTIAL')
        self.assertIn('VISIBLE_INVENTORY_ONLY', result.collection_errors)
        self.assertEqual([c[1] for c in self.calls], [LIST, DETAIL])
        self.assertTrue(all(c[0] == 'GET' for c in self.calls))
        self.assertTrue(all(c[2]['vmware-api-session-id'] == self.token for c in self.calls))
        self.assertTrue(all(c[2]['Host'].startswith('localhost:') for c in self.calls))
        self.assertNotIn(self.token, repr(result))
        self.assertNotIn(self.token, repr(self.read_material()))

    def test_only_admitted_lists_and_previously_observed_detail_ids_can_be_read(self):
        for path in (DETAIL, '/api/vcenter/vm', LIST + '&all=true',
                     LIST.replace('group-v1', 'group-v999'), LIST.replace('datacenter-1', 'datacenter-2'),
                     'https://other.invalid/api/vcenter/vm', '/api/session',
                     '/api/vcenter/vm/vm-101?action=power', '//other.invalid/', '/api/../session',
                     LIST + '\r\nHost: other.invalid'):
            with self.subTest(path=path), self.assertRaises(NativeReadHeld):
                self.client().get(path)
        self.assertEqual(self.calls, [])
        self.transport.get(LIST)
        self.assertEqual(self.transport.get(DETAIL).status, 200)
        with self.assertRaises(NativeReadHeld):
            self.transport.get('/api/vcenter/vm/vm-999')
        self.assertEqual(len(self.calls), 2)

    def test_unsigned_material_and_changed_token_never_reach_native_server(self):
        self.write_material(signer=Ed25519PrivateKey.generate())
        with self.assertRaises(NativeReadHeld):
            self.transport.get(LIST)
        self.write_material()
        doc = json.loads(self.credential_path.read_text())
        doc['token'] += 'tampered'
        self.credential_path.write_text(json.dumps(doc))
        with self.assertRaises(NativeReadHeld):
            self.transport.get(LIST)
        self.assertEqual(self.calls, [])

    def test_signed_binding_must_match_campaign_environment_selection_and_api(self):
        original = dict(self.binding)
        for field, bad in (('campaignDigest', 'f' * 64), ('environmentId', 'other'),
                           ('collectorId', 'other'), ('selectionDigest', 'f' * 64),
                           ('apiRelease', '9.0'), ('credentialReference', 'vault:other')):
            with self.subTest(field=field):
                self.binding = {**original, field: bad}
                self.write_material()
                with self.assertRaises(NativeReadHeld):
                    self.client().get(LIST)
        self.assertEqual(self.calls, [])

    def test_campaign_issuer_and_collector_roots_cannot_sign_native_material(self):
        for key in (self.root_key, self.issuer_key, self.collector_key):
            with self.subTest(key=key):
                self.write_material(signer=key)
                source = SignedFileVmwareCredentialSource(self.credential_path,
                    authority_public_key=key.public_key(), minimum_revision=1)
                with self.assertRaises(NativeReadHeld):
                    self.client(credentials=source).get(LIST)
        self.assertEqual(self.calls, [])

    def test_live_witness_revocation_or_write_permissions_prevent_native_read(self):
        self.revoke_witness()
        with self.assertRaises(NativeReadHeld):
            self.transport.get(LIST)
        self.witness_policy = replace(self.witness_policy, revision=3,
                                      witnesses=(replace(self.witness, read_only=False),))
        self.write_witness()
        with self.assertRaises(NativeReadHeld):
            self.transport.get(LIST)
        self.assertEqual(self.calls, [])

    def test_revocation_during_response_does_not_return_the_response(self):
        self.on_get = self.revoke_witness
        with self.assertRaises(NativeReadHeld):
            self.transport.get(LIST)
        self.assertEqual(len(self.calls), 1)
        with self.assertRaises(NativeReadHeld):
            self.transport.get(DETAIL)
        self.assertEqual(len(self.calls), 1)

    def test_issuer_revoked_after_list_cannot_read_vm_detail(self):
        self.transport.get(LIST)
        self.policy = replace(self.policy, revision=2, enrollments=(
            replace(self.policy.enrollments[0], revoked_at=self.now), self.policy.enrollments[1]))
        self.write_trust()
        with self.assertRaises(NativeReadHeld):
            self.transport.get(DETAIL)
        self.assertEqual(len(self.calls), 1)

    def test_tls_hostname_mismatch_and_ca_change_never_send_credentials(self):
        self.binding['origin'] = self.binding['origin'].replace('localhost', 'wrong.invalid')
        self.write_material()
        with self.assertRaises(NativeReadHeld):
            self.transport.get(LIST)
        (self.root / 'ca.pem').write_bytes((self.root / 'ca.pem').read_bytes() + b'\n')
        with self.assertRaises(NativeReadHeld):
            self.client().get(LIST)
        self.assertEqual(self.calls, [])

    def test_redirect_is_not_followed_and_error_body_is_not_exposed(self):
        self.response_status = 302
        self.extra_headers = [('Location', 'https://other.invalid/')]
        self.raw_body = self.token.encode()
        with self.assertRaises(NativeReadHeld) as caught:
            self.transport.get(LIST)
        self.assertNotIn(self.token, str(caught.exception))
        self.assertEqual(len(self.calls), 1)
        self.response_status = 403
        answer = self.client().get(LIST)
        self.assertEqual(answer.status, 403)
        self.assertIsNone(answer.body)
        self.assertEqual(len(self.calls), 2)

    def test_private_material_file_rejects_symlink_public_permissions_and_fifo(self):
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
        self.assertEqual(self.calls, [])

    def test_revision_rollback_and_same_revision_change_reject_without_cached_secret(self):
        self.read_material()
        original_token = self.token
        self.token += '-same-revision-change'
        self.binding['tokenDigest'] = hashlib.sha256(self.token.encode()).hexdigest()
        self.write_material()
        with self.assertRaises(NativeReadHeld):
            self.read_material()
        self.token = original_token
        self.binding['tokenDigest'] = hashlib.sha256(self.token.encode()).hexdigest()
        self.binding['revision'] = 2
        self.write_material()
        self.read_material()
        self.binding['revision'] = 1
        self.write_material()
        with self.assertRaises(NativeReadHeld):
            self.read_material()
        self.credential_path.unlink()
        with self.assertRaises(NativeReadHeld):
            self.read_material()

    def test_new_signed_token_revision_is_accepted_but_mid_response_rotation_is_not(self):
        self.transport.get(LIST)
        self.binding['revision'] = 2
        self.token += '-rotation'
        self.binding['tokenDigest'] = hashlib.sha256(self.token.encode()).hexdigest()
        self.write_material()
        self.assertEqual(self.transport.get(DETAIL).status, 200)
        def rotate():
            self.binding['revision'] += 1
            self.write_material()
        self.on_get = rotate
        with self.assertRaises(NativeReadHeld):
            self.client().get(LIST)

    def test_invalid_json_and_ambiguous_http_framing_are_rejected(self):
        for body in (b'{"vm":1,"vm":2}', b'{"x":NaN}', b'{"x":1e9999}',
                     b'{"x":9223372036854775808}', b'[' * 34 + b'0' + b']' * 34,
                     b'\xff', b'not-json'):
            with self.subTest(body=body):
                self.raw_body = body
                with self.assertRaises(NativeReadHeld):
                    self.client().get(LIST)
        self.raw_body = None
        for headers in ([('Content-Length', '1')], [('Transfer-Encoding', 'chunked')],
                        [('Content-Type', 'text/html')], [('Content-Encoding', 'gzip')]):
            with self.subTest(headers=headers):
                self.extra_headers = headers
                with self.assertRaises(NativeReadHeld):
                    self.client().get(LIST)

    def test_native_body_budget_rejects_oversized_content(self):
        self.raw_body = b' ' * 2048
        with self.assertRaises(NativeReadHeld):
            self.client(max_response_bytes=1024).get(LIST)

    def _assert_response_deadline(self, *, headers_expected):
        client = self.client(timeout=0.15)
        responses = []
        class ObservedResponse(http.client.HTTPResponse):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                responses.append(self)
        start = time.monotonic()
        try:
            with patch.object(http.client.HTTPConnection, 'response_class', ObservedResponse):
                with self.assertRaises(NativeReadHeld):
                    client.get(LIST)
            self.assertTrue(responses, 'The response parser must have been reached')
            self.assertTrue(all(response.isclosed() for response in responses),
                            'Held responses must release their buffered socket readers')
            # Prove that the intended response phase, not TLS setup, was tested.
            self.assertTrue(self.request_started.is_set())
            self.assertEqual(self.headers_sent.is_set(), headers_expected)
            self.assertEqual(len(self.calls), 1)
            self.assertEqual(client._seen_vms, set())
            self.assertLess(time.monotonic() - start, 2.0)
        finally:
            self.stop_response.set()
            self.assertTrue(self.handler_finished.wait(2), 'The fixture handler did not stop')

    def test_slow_headers_are_bounded_by_total_deadline(self):
        self.delay = 3
        self._assert_response_deadline(headers_expected=False)

    def test_drip_body_is_bounded_despite_continuous_socket_progress(self):
        self.drip = True
        # Valid JSON takes much longer than the deadline even though each byte
        # arrives before the inactivity timeout. A fresh fixture owns this case.
        self.raw_body = b'[' + b' ' * 200 + b']'
        self._assert_response_deadline(headers_expected=True)

    def test_completed_valid_json_is_not_admitted_after_total_deadline(self):
        # Exercise the final time check deterministically, independently of
        # server/thread scheduling. Do not patch the process-global time module.
        expired = threading.Event()
        monotonic = time.monotonic
        clock = SimpleNamespace(monotonic=lambda: monotonic() + (60 if expired.is_set() else 0))
        decode = native_https.decode_json
        def late_decode(body, limit):
            value = decode(body, limit)
            expired.set()
            return value
        client = self.client()
        with patch.object(native_https, 'time', clock), \
             patch.object(native_https, 'decode_json', late_decode):
            with self.assertRaises(NativeReadHeld):
                client.get(LIST)
        self.assertTrue(expired.is_set(), 'The fixture must reach successful JSON decoding')
        self.assertEqual(client._seen_vms, set())
        self.assertEqual(len(self.calls), 1)

    def test_request_budget_and_concurrent_reads_are_bounded(self):
        self.transport._requests = self.transport._request_limit
        with self.assertRaises(NativeReadHeld):
            self.transport.get(LIST)
        other = self.client(timeout=0.01)
        other._lock.acquire()
        try:
            with self.assertRaises(NativeReadHeld):
                other.get(LIST)
        finally:
            other._lock.release()
        self.assertEqual(self.calls, [])

    def test_expired_and_backward_clocks_never_issue_later_native_reads(self):
        for at in (self.campaign.expires_at, self.campaign.issued_at - timedelta(seconds=1), None):
            with self.subTest(at=at), self.assertRaises(NativeReadHeld):
                self.client(clock=lambda: at).get(LIST)
        self.assertEqual(self.calls, [])
        self.transport.get(LIST)
        self.now -= timedelta(seconds=1)
        with self.assertRaises(NativeReadHeld):
            self.transport.get(DETAIL)
        self.assertEqual(len(self.calls), 1)

    def test_expiry_during_response_rejects_result(self):
        self.on_get = lambda: setattr(self, 'now', self.campaign.expires_at)
        with self.assertRaises(NativeReadHeld):
            self.transport.get(LIST)
        self.assertEqual(len(self.calls), 1)

    def test_binding_limits_and_unsafe_endpoint_values_are_rejected(self):
        initial = dict(self.binding)
        for field, bad in (('origin', 'http://localhost'), ('origin', 'https://u:p@localhost'),
                           ('origin', 'https://localhost/path'), ('origin', 'https://local\nhost'), ('origin', 'https://localhost:0'),
                           ('connectIp', 'unresolved.example'), ('connectIp', '0.0.0.0'),
                           ('caDigest', 'wrong'), ('revision', True), ('revision', 2**63),
                           ('expiresAt', (self.now + timedelta(hours=2)).isoformat())):
            with self.subTest(field=field, value=bad):
                self.binding = {**initial, field: bad}
                self.write_material()
                with self.assertRaises(NativeReadHeld):
                    self.client().get(LIST)
        self.assertEqual(self.calls, [])

    def test_binding_duplicate_keys_token_injection_and_oversized_file_are_rejected(self):
        doc = self.credential_path.read_text()
        self.credential_path.write_text(doc.replace('"revision": 1', '"revision": 1, "revision": 1'))
        with self.assertRaises(NativeReadHeld):
            self.read_material()
        self.token += '\r\nInjected: header'
        self.binding['tokenDigest'] = hashlib.sha256(self.token.encode()).hexdigest()
        self.write_material()
        with self.assertRaises(NativeReadHeld):
            self.read_material()
        self.credential_path.write_bytes(b' ' * 32769)
        with self.assertRaises(NativeReadHeld):
            self.read_material()

    def test_duplicate_or_large_native_lists_do_not_authorize_detail_reads(self):
        for value in ([VM1, VM1], [VM1] * 4000, [{'vm': 'not-a-vm'}]):
            self.raw_body = json.dumps(value).encode()
            client = self.client()
            with self.assertRaises(NativeReadHeld):
                client.get(LIST)
            with self.assertRaises(NativeReadHeld):
                client.get(DETAIL)


if __name__ == '__main__':
    unittest.main()
