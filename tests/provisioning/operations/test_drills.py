"""Actual loopback mTLS protocol tests; these do not qualify site HA."""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import ssl
import socket
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.operations.drills import (
    SwitchoverSpec, DrillAuthority, PatroniOwner, WriterDrain,
    OperatingInstanceDrain, ControlledSwitchover, ControlStateObserver, TemporalRetainedObserver,
    database_selection_digest, _node,
)
from provisioner.controlplane.operations.instance import digest
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.workflow.temporal_adapter import TemporalConnection
from provisioner.controlplane.workflow.installed_identity import InstalledApplicationIdentity
from tests.provisioning.operations.signed_intake_fixtures import RetainedFixture, signed
from tests.provisioning.operations.test_release import TestSigner
from tests.provisioning.worker.tls_fixtures import TestPki


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.calls.append(('GET', self.path))
        name = self.server.member
        if self.path == '/primary':
            self.send_response(200 if name == 'old-primary' else 503)
            self.end_headers()
            return
        values = {'/patroni': {'state': 'running', 'role': 'primary' if name == 'old-primary' else 'replica',
            'database_system_identifier': '123456789', 'timeline': 5,
            'patroni': {'name': name, 'scope': 'isolated-test-cluster'}},
            '/cluster': {'members': [{'name': 'old-primary', 'api_url': 'https://foreign.invalid/'},
                                     {'name': 'selected-candidate'}]}, '/history': [[4, 1234, 'fixture-time']]}
        raw = json.dumps(values[self.path]).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        value = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.calls.append(('POST', self.path, value))
        if getattr(self.server, 'lose_post_reply', False):
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        raw = b'Synthetic loopback switchover accepted, no actual cluster'
        self.send_response(202)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


class DrillTests(unittest.TestCase):
    def setUp(self):
        self.pki = TestPki()
        self.pki.issue('patroni')
        self.pki.issue('drill-client', client=True, uri='spiffe://isolated-test/drill')
        self.servers, self.threads = [], []
        for member in ('old-primary', 'selected-candidate'):
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            server.member, server.calls = member, []
            tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            tls.load_cert_chain(self.pki.root / 'patroni.pem', self.pki.root / 'patroni.key')
            tls.load_verify_locations(cafile=str(self.pki.root / 'ca.pem'))
            tls.verify_mode = ssl.CERT_REQUIRED
            server.socket = tls.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.servers.append(server)
            self.threads.append(thread)
        client = ssl.create_default_context(cafile=str(self.pki.root / 'ca.pem'))
        client.load_cert_chain(self.pki.root / 'drill-client.pem', self.pki.root / 'drill-client.key')
        self.source = PatroniOwner(f'https://localhost:{self.servers[0].server_port}', tls_context=client)
        self.candidate = PatroniOwner(f'https://localhost:{self.servers[1].server_port}', tls_context=client)
        self.source_dsn = 'host=source.example user=observer dbname=control sslmode=verify-full'
        self.candidate_dsn = self.source_dsn.replace('source.example', 'candidate.example')
        self.drain_dsn = self.source_dsn.replace('observer', 'custodian')
        self.spec = SwitchoverSpec('drill-fixture', 'a' * 32, 1, 'b' * 40, 'c' * 64,
            'isolated-test-cluster', 'old-primary', 'selected-candidate',
            self.source.selection_digest, self.candidate.selection_digest,
            database_selection_digest(self.source_dsn), database_selection_digest(self.candidate_dsn),
            database_selection_digest(self.drain_dsn), ('hosting-control-application-worker.service',), 0, 120)
        self.context = TenantContext('synthetic-drill-org', 'synthetic-drill-tenant')
        self.custody = RetainedFixture(self.context)
        self.operating, self.observer = TestSigner('synthetic-operating'), TestSigner('synthetic-observer')
        now = datetime.now(timezone.utc)
        raw = {'format': 'hosting-independent-old-primary-observation/1',
            'specificationSha256': self.spec.digest, 'oldPrimaryName': self.spec.leader,
            'writerSetSha256': digest(list(self.spec.writer_units)),
            'observations': {'fixtureOnlyNeverHA': True}}
        proof = {'format': 'hosting-independent-old-primary-exclusion/1',
            'specificationSha256': self.spec.digest, 'observedAt': (now - timedelta(minutes=2)).isoformat(),
            'freshUntil': (now + timedelta(minutes=20)).isoformat(), 'oldPrimaryName': self.spec.leader,
            'writerSetSha256': digest(list(self.spec.writer_units)), 'restartExclusionSha256': 'd' * 64,
            'delayedRequestExclusionSha256': 'e' * 64, 'observationEventKey': 'raw-proof',
            'observationSha256': digest(raw)}
        self.proof = signed(proof, self.observer)
        decision = {'format': 'hosting-controlled-ha-drill-authority/1',
            'specificationSha256': self.spec.digest, 'organizationId': self.context.organization_id,
            'tenantId': self.context.tenant_id, 'allowedSteps': ['DRAIN_CONTROL_WRITERS', 'CONTROL_DB_SWITCHOVER'],
            'authorizedAt': (now - timedelta(minutes=1)).isoformat(),
            'expiresAt': (now + timedelta(minutes=20)).isoformat(), 'changeRef': 'change-fixture',
            'exclusionEventKey': 'proof-fixture', 'exclusionSha256': digest(self.proof)}
        self.decision = signed(decision, self.operating)
        self.custody.values.update({'decision-fixture': self.decision, 'proof-fixture': self.proof, 'raw-proof': raw})
        original_get = self.custody.get
        def get(context, key):
            found = original_get(context, key)
            if found is None:
                return None
            kind = {'decision-fixture': 'RECOVERY_DECISION', 'raw-proof': 'OBSERVATION'}.get(key, 'VERIFICATION_RESULT')
            return SimpleNamespace(event_key=key, evidence_kind=kind, subject_id=self.spec.digest), found[1]
        self.custody.get = get
        # The source/interpreter identity has its own real sealed-build campaign.
        # This local TLS protocol test cannot mint that acceptance.
        installed_current = patch.object(InstalledApplicationIdentity, 'require_current',
            return_value=(self.spec.source_commit, self.spec.artifact_sha256))
        installed_current.start()
        self.addCleanup(installed_current.stop)
        installed = InstalledApplicationIdentity(self.pki.root / 'synthetic-not-installed.json',
            self.pki.root, '0' * 64, self.spec.source_commit, self.spec.artifact_sha256)
        self.authority = DrillAuthority(evidence_gate=self.custody, context=self.context, spec=self.spec,
            decision_key='decision-fixture', decision_sha256=digest(self.decision),
            operating_verifier=self.operating, operating_keys=frozenset({self.operating.key_id}),
            observer_verifier=self.observer, observer_keys=frozenset({self.observer.key_id}),
            installed_identity=installed)

    def tearDown(self):
        for server in self.servers:
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join(timeout=5)
        self.pki.close()

    def test_actual_mtls_reads_and_fixed_candidate_post_do_not_infer_completion(self):
        source, candidate = self.source.observe(), self.candidate.observe()
        _node(source, name='old-primary', scope=self.spec.cluster_scope, primary=True)
        _node(candidate, name='selected-candidate', scope=self.spec.cluster_scope,
              system_id='123456789', primary=False)
        response = self.source.switchover(self.spec, self.authority)
        self.assertEqual(response['httpStatus'], 202)
        self.assertNotIn('accepted', response)
        self.assertEqual(self.servers[0].calls[-1], ('POST', '/switchover',
            {'leader': 'old-primary', 'candidate': 'selected-candidate'}))
        self.assertEqual(len(self.servers[0].calls), 5)
        self.assertEqual(len(self.servers[1].calls), 4)

    def test_withdrawn_custody_or_changed_original_decision_prevents_native_post(self):
        self.custody.available = False
        with self.assertRaises(Exception):
            self.source.switchover(self.spec, self.authority)
        self.assertFalse(self.servers[0].calls)

    def test_absent_or_changed_actual_installation_prevents_native_post(self):
        installed = self.authority.installed_identity
        self.authority.installed_identity = None
        with self.assertRaises(AuthorityDenied):
            self.source.switchover(self.spec, self.authority)
        self.assertFalse(self.servers[0].calls)
        self.authority.installed_identity = installed
        with patch.object(InstalledApplicationIdentity, 'require_current',
                          side_effect=AuthorityDenied('Actual sealed installation changed')):
            with self.assertRaises(AuthorityDenied):
                self.source.switchover(self.spec, self.authority)
        self.assertFalse(self.servers[0].calls)
        self.custody.available = True
        self.custody.values['decision-fixture']['payload']['changeRef'] = 'forged-change'
        with self.assertRaises(AuthorityDenied):
            self.source.switchover(self.spec, self.authority)
        self.assertFalse(self.servers[0].calls)

    def test_proof_same_owner_and_plain_http_arbitrary_paths_or_promotion_refused(self):
        for method, path, value in (('POST', '/failover', {'candidate': 'selected-candidate'}),
                                    ('PATCH', '/config', {}), ('GET', '/config', None),
                                    ('POST', '/switchover', {'leader': 'old-primary'})):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.source._request(method, path, value)
        with self.assertRaises(ValueError):
            PatroniOwner('http://localhost', tls_context=ssl.create_default_context())
        self.assertFalse(self.servers[0].calls)

    def test_timeline_wrong_system_pause_and_unlocked_roles_are_rejected(self):
        original = self.source.observe()
        for field, value in (('timeline', 0), ('database_system_identifier', 'foreign'),
                             ('pause', True), ('cluster_unlocked', True), ('role', 'replica')):
            changed = deepcopy(original)
            changed['patroni'][field] = value
            with self.subTest(field=field), self.assertRaises(AuthorityDenied):
                _node(changed, name='old-primary', scope=self.spec.cluster_scope, primary=True)

    def test_selected_database_hash_ignores_rotated_password_but_not_scope_or_role(self):
        dsn = 'host=db.example user=observer dbname=control sslmode=verify-full'
        self.assertEqual(database_selection_digest(dsn + ' password=one'), database_selection_digest(dsn + ' password=two'))
        self.assertNotEqual(database_selection_digest(dsn), database_selection_digest(dsn.replace('control', 'foreign')))
        with self.assertRaises(ValueError):
            database_selection_digest(dsn.replace('verify-full', 'require'))

    def test_fixed_systemctl_stop_and_readback_actual_argv_rechecks_authority(self):
        path = Path('/usr/local/bin/systemctl')
        if not path.exists():
            path = Path('/usr/bin/systemctl')
        if not path.exists():
            self.skipTest('No systemctl binary installed; site service drill remains held')
        owner = WriterDrain(systemctl=path, systemctl_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        calls = []
        def process(argv, **kwargs):
            calls.append(argv)
            return SimpleNamespace(stdout=b'LoadState=loaded\nActiveState=inactive\nSubState=dead\nMainPID=0\nResult=success\n')
        with patch('provisioner.controlplane.operations.drills.subprocess.run', side_effect=process):
            result = owner.stop(self.spec, self.authority)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], [str(path.resolve()), '--no-pager', 'stop', self.spec.writer_units[0]])
        self.assertEqual(result[0]['serviceFacts']['MainPID'], '0')
        self.custody.available = False
        with patch('provisioner.controlplane.operations.drills.subprocess.run', side_effect=self.fail), self.assertRaises(Exception):
            owner.stop(self.spec, self.authority)

    def test_actual_lost_tls_post_reply_retains_original_attempt_without_replay(self):
        path = Path('/usr/local/bin/systemctl')
        if not path.exists():
            path = Path('/usr/bin/systemctl')
        if not path.exists():
            self.skipTest('No systemctl binary available for fixed-owner contract')
        temporal = TemporalRetainedObserver(TemporalConnection('temporal.example:7233', 'fixture', 'fixture',
            server_ca=self.pki.root / 'ca.pem', client_cert=self.pki.root / 'drill-client.pem',
            client_key=self.pki.root / 'drill-client.key', server_name='temporal.example'))
        runner = ControlledSwitchover(source=self.source, candidate=self.candidate,
            source_state=ControlStateObserver(self.source_dsn, temporal),
            candidate_state=ControlStateObserver(self.candidate_dsn, temporal),
            instance=OperatingInstanceDrain(self.drain_dsn), authority=self.authority,
            writers=WriterDrain(systemctl=path, systemctl_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        self.servers[0].lose_post_reply = True
        before = {'inRecovery': False, 'databaseSystemIdentifier': '123456789',
            'stateDigest': 'd' * 64, 'temporalHeads': {}, 'retainedAuditHighWaterAt': None}
        process = SimpleNamespace(stdout=b'LoadState=loaded\nActiveState=inactive\nSubState=dead\nMainPID=0\nResult=success\n')
        with tempfile.TemporaryDirectory() as temporary, \
                patch('provisioner.controlplane.operations.drills.subprocess.run', return_value=process), \
                patch.object(OperatingInstanceDrain, 'drain', return_value={'mode': 'DRAINED'}), \
                patch.object(ControlStateObserver, 'observe', return_value=before):
            directory = Path(temporary) / 'attempt'
            result = runner.run(directory)
            self.assertEqual(result['status'], 'SWITCHOVER_UNKNOWN_RECONCILE_NO_REPLAY')
            self.assertFalse(result['haAcceptanceIssued'])
            self.assertFalse(result['writersStarted'])
            self.assertTrue(result['nativeContact'])
            self.assertTrue(result['nativeMutationAttempted'])
            self.assertTrue((directory / 'switchover-attempt.json').is_file())
            self.assertFalse((directory / 'switchover-response.json').exists())
            with self.assertRaises(FileExistsError):
                runner.run(directory)
            with patch.object(OperatingInstanceDrain, 'drain',
                              side_effect=AuthorityDenied('Actual instance no longer eligible')):
                held = runner.run(Path(temporary) / 'pre-post-refusal')
                self.assertEqual(held['status'], 'DRILL_HELD')
                self.assertTrue(held['nativeContact'])
                self.assertFalse(held['nativeMutationAttempted'])
                self.assertFalse(held['writersStarted'])
        self.assertEqual(sum(call[0] == 'POST' for call in self.servers[0].calls), 1)


if __name__ == '__main__':
    unittest.main()
