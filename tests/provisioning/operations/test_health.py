from datetime import datetime, timezone
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import ssl
import threading
from types import SimpleNamespace
import unittest

from provisioner.controlplane.operations.health import IncidentDispatcher, MonitorPolicy, signal, retain_delivery
from provisioner.controlplane.persistence import TenantContext
from tests.provisioning.worker.tls_fixtures import TestPki


class Handler(BaseHTTPRequestHandler):
    mismatch = False
    acknowledge = False
    captures = []

    def do_POST(self):
        value = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.captures.append((self.path, self.headers['Idempotency-Key'], value))
        receipt = {'signalId': 'wrong-scope' if self.mismatch else value['signalId'],
                   'signalSha256': value['signalSha256'], 'incidentId': 'INC-fixture',
                   'acknowledgedBy': 'oncall-fixture' if self.acknowledge else None,
                   'acknowledgedAt': datetime.now(timezone.utc).isoformat() if self.acknowledge else None}
        raw = json.dumps(receipt).encode()
        self.send_response(201)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.pki = TestPki()
        self.pki.issue('itsm')
        Handler.captures = []
        Handler.mismatch = Handler.acknowledge = False
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(self.pki.root / 'itsm.pem', self.pki.root / 'itsm.key')
        self.server.socket = tls.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.context = ssl.create_default_context(cafile=str(self.pki.root / 'ca.pem'))
        self.endpoint = f'https://localhost:{self.server.server_port}/incident-intake'
        self.item = signal(TenantContext('fixture-org', 'fixture-tenant'), 'NATIVE_UNCERTAIN',
                           'operation-fixture', epoch=42, detail='retained-native-state:UNCERTAIN')

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.pki.temporary.cleanup()

    def dispatcher(self, **kwargs):
        return IncidentDispatcher(self.endpoint, tls_context=self.context,
                                  token=lambda: 'synthetic-intake-token', **kwargs)

    def test_actual_loopback_tls_dispatch_and_idempotency_do_not_infer_operator_ack(self):
        first = self.dispatcher().dispatch(self.item)
        second = self.dispatcher().dispatch(self.item)
        self.assertEqual(first['deliveryStatus'], 'DELIVERED')
        self.assertFalse(first['operatorAcknowledged'])
        self.assertFalse(first['mutationAuthorized'])
        self.assertEqual(Handler.captures[0][1], Handler.captures[1][1])
        self.assertEqual(second['incidentId'], 'INC-fixture')

    def test_actual_receipt_acknowledgement_and_wrong_scope_refusal(self):
        Handler.acknowledge = True
        self.assertTrue(self.dispatcher().dispatch(self.item)['operatorAcknowledged'])
        Handler.mismatch = True
        with self.assertRaisesRegex(RuntimeError, 'exact retained signal'):
            self.dispatcher().dispatch(self.item)

    def test_retained_actual_dispatch_preserves_ack_identity_and_refuses_boolean_substitution(self):
        context = TenantContext('fixture-org', 'fixture-tenant')
        Handler.acknowledge = True
        receipt = self.dispatcher().dispatch(self.item)
        class Custody:
            def __init__(owner):
                owner.evidence = owner
                owner.appended = []
                owner.checkpoints = 0
            def require(owner, scoped):
                self.assertEqual(scoped, context)
            def append(owner, scoped, **record):
                self.assertEqual(scoped, context)
                owner.appended.append(deepcopy(record))
                return SimpleNamespace(event_key=record['event_key'], blob_digest='a' * 64)
            def checkpoint(owner, scoped):
                self.assertEqual(scoped, context)
                owner.checkpoints += 1
        custody = Custody()
        retained = retain_delivery(custody, context, self.item, receipt)
        self.assertEqual(custody.appended[0]['artifact'], receipt)
        self.assertEqual(custody.appended[0]['evidence_kind'], 'VERIFICATION_RESULT')
        self.assertEqual(custody.appended[0]['subject_id'], self.item['signalId'])
        self.assertEqual(custody.checkpoints, 1)
        self.assertEqual(retained['acknowledgedBy'], 'oncall-fixture')
        for changed in (dict(receipt, acknowledgedBy=None, acknowledgedAt=None),
                        dict(receipt, operatorAcknowledged=False),
                        dict(receipt, acknowledgedAt=None), dict(receipt, incidentId=True),
                        dict(receipt, extraAuthority=True)):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                retain_delivery(custody, context, self.item, changed)
        self.assertEqual(len(custody.appended), 1)
        self.assertEqual(custody.checkpoints, 1)

    def test_changed_signal_wrong_tenant_and_header_injection_rejected_before_contact(self):
        changed = dict(self.item, tenantId='foreign-tenant')
        with self.assertRaises(ValueError):
            self.dispatcher().dispatch(changed)
        self.assertFalse(Handler.captures)
        dispatcher = IncidentDispatcher(self.endpoint, tls_context=self.context,
                                         token=lambda: 'bad\r\ninjected-header')
        with self.assertRaises(ValueError):
            dispatcher.dispatch(self.item)
        self.assertFalse(Handler.captures)

    def test_tls_and_bounded_policy_fail_closed(self):
        for endpoint in ('http://localhost/intake', 'https://user:pass@localhost/intake',
                         'https://localhost/intake?secret=none', 'https://localhost/'):
            with self.assertRaises(ValueError):
                IncidentDispatcher(endpoint, tls_context=self.context, token=lambda: 'fixture')
        with self.assertRaises(ValueError):
            IncidentDispatcher(self.endpoint, tls_context=ssl._create_unverified_context(),
                                 token=lambda: 'fixture')
        for policy in ({'limit': 0}, {'stuck_seconds': True}, {'freshness_seconds': 1}):
            with self.assertRaises(ValueError):
                MonitorPolicy(**policy)


if __name__ == '__main__':
    unittest.main()
