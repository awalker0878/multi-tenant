from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest

from lab.native_readback_fixture import Fixture, manifest, responses, credentials
from tools.guest_probe import probe
from tools.qualify_target import (ASSETS, authority_matches, budget, native_readback,
                                  traffic_campaign, validate, bound_inputs)
from tools.run_files import digest, encoded, utcnow, write_new
from tools.guest_inventory import build
from tests.test_guest_inventory import fixture


def window():
    return {'valid_from': (utcnow() - timedelta(seconds=1)).isoformat(),
            'valid_until': (utcnow() + timedelta(minutes=5)).isoformat()}


def plan_fixture():
    positive = dict(id='healthy-a', guest='guest-01', destination='192.0.2.130', port=443,
                    server_name='service.example.test', path='/health', body_sha256=digest(b'healthy'),
                    expect='allow', healthy_control=None)
    return dict(format='hosting-target-campaign/1', source_commit='a' * 40,
        scope=dict(environment_key='test-01', site_key='site-01', platform='nutanix', tenant_key='tenant-01', wsd_key='wsd-01'),
        origin='https://native.example.test', assets={k: dict(path='/private/' + k, sha256='a' * 64) for k in ASSETS},
        cases=[positive, positive | dict(id='denied-b', guest='guest-02', expect='deny', healthy_control='healthy-a')])


class CampaignTests(unittest.TestCase):
    def test_denial_requires_matching_healthy_peer_and_never_accepts_failed_control(self):
        cases = validate(plan_fixture())
        calls = []
        def observe(case):
            calls.append(case['id'])
            return {'status': 'BLOCKED' if case['expect'] == 'deny' else 'HEALTHY'}
        report = traffic_campaign(cases, observe)
        self.assertTrue(all(r['passed'] for r in report))
        self.assertEqual(calls, ['healthy-a', 'healthy-a', 'denied-b', 'healthy-a'])
        for statuses in [('HEALTHY', 'HEALTHY', 'BLOCKED', 'UNHEALTHY'),
                         ('HEALTHY', 'HEALTHY', 'UNEXPECTED_CONNECTION', 'HEALTHY'),
                         ('HEALTHY', 'HEALTHY', 'INCONCLUSIVE', 'HEALTHY')]:
            sequence = iter(statuses)
            self.assertFalse(traffic_campaign(cases, lambda _: {'status': next(sequence)})[-1]['passed'])
        for change in [dict(healthy_control=None), dict(port=444), dict(guest='guest-01')]:
            plan = plan_fixture(); plan['cases'][1].update(change)
            with self.assertRaises(ValueError): validate(plan)

    def test_inputs_are_bounded_and_authority_is_exact(self):
        for key, value in [('path', '/health\r\nX-Evil: 1'), ('destination', '127.0.0.1'),
                           ('port', True), ('server_name', '-bad name'), ('body_sha256', 'unknown')]:
            plan = plan_fixture(); plan['cases'][0][key] = value
            with self.assertRaises(ValueError): validate(plan)
        raw = encoded(plan_fixture())
        authority = window() | dict(format='hosting-target-campaign-authority/1', plan_sha256=digest(raw),
            source_commit='a' * 40, ssh_sha256=digest(b'ssh'), change_ref='FIXTURE', target_binding_ref='FIXTURE', isolation_ref='FIXTURE')
        authority_matches(authority, raw, 'a' * 40, b'ssh')
        with self.assertRaises(ValueError): authority_matches(authority, raw + b' ', 'a' * 40, b'ssh')
        with self.assertRaises(ValueError): authority_matches(authority, raw, 'b' * 40, b'ssh')
        with self.assertRaises(ValueError): budget(authority | {'valid_until': utcnow().isoformat()}, 20)

    def test_exact_assets_and_guest_binding_fail_before_contact(self):
        outputs, access = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); plan = plan_fixture(); plan['cases'] = plan['cases'][:1]
            inventory, _ = build(outputs, access, str(directory / 'known_hosts'))
            native = manifest('nutanix', plan['origin'])
            for key in ASSETS:
                value = encoded(inventory if key == 'inventory' else native if key == 'native_manifest' else {})
                path = directory / key; write_new(path, value)
                plan['assets'][key] = dict(path=str(path), sha256=digest(value))
            bound_inputs(plan, str(directory / 'known_hosts'))
            plan['scope']['site_key'] = 'foreign'
            with self.assertRaises(ValueError): bound_inputs(plan, str(directory / 'known_hosts'))
            plan['scope']['site_key'] = 'site-01'
            (directory / 'ssh_key').write_bytes(b'changed')
            with self.assertRaises(ValueError): bound_inputs(plan, str(directory / 'known_hosts'))

    def test_real_observer_child_contacts_only_loopback_tls_fixture(self):
        for platform, adapter in [('vmware', 'nsx'), ('nutanix', 'nutanix')]:
            with self.subTest(platform=platform), Fixture() as service, tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp); m = manifest(adapter, service.origin); service.routes = responses(m)
                assets = {'native_credentials': encoded({'username': 'fixture', 'password': 'fixture'})}
                write_new(directory / 'native_manifest', encoded(m))
                write_new(directory / 'native_ca', (service.directory / 'ca.pem').read_bytes())
                result = native_readback({'scope': {'platform': platform}, 'origin': service.origin}, assets, window(), directory, 'capture')
                self.assertEqual(len(result), 64)
                self.assertTrue(service.requests)
                self.assertTrue(all(r['method'] == 'GET' for r in service.requests))


class GuestProbeTests(unittest.TestCase):
    def test_real_https_body_trust_and_machine_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); credentials(directory)
            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *_): pass
                def do_GET(self):
                    self.send_response(200); self.send_header('Content-Length', '7'); self.end_headers(); self.wfile.write(b'healthy')
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(directory / 'server.pem', directory / 'server.key')
            server.socket = context.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .02}, daemon=True); thread.start()
            request = dict(machine_id=Path('/etc/machine-id').read_text().strip(), source='127.0.0.1',
                destination='127.0.0.1', port=server.server_port, server_name='localhost', path='/health',
                body_sha256=digest(b'healthy'), expect='allow', ca_pem=(directory / 'ca.pem').read_text())
            try:
                self.assertEqual(probe(request)['status'], 'HEALTHY')
                self.assertEqual(probe(request | {'body_sha256': digest(b'wrong')})['status'], 'UNHEALTHY')
                self.assertEqual(probe(request | {'server_name': 'wrong.invalid'})['status'], 'INCONCLUSIVE')
                self.assertEqual(probe(request | {'machine_id': 'wrong'})['status'], 'WRONG_GUEST')
                self.assertEqual(probe(request | {'expect': 'deny'})['status'], 'UNEXPECTED_CONNECTION')
                completed = subprocess.run([sys.executable, 'tools/guest_probe.py'], input=encoded(request), capture_output=True, timeout=15)
                self.assertIn(b'HEALTHY', completed.stdout)
            finally:
                server.shutdown(); server.server_close(); thread.join()
            # Hold a real unlistened port to distinguish refusal from a bind error.
            with socket.socket() as unlistened:
                unlistened.bind(('127.0.0.1', 0))
                self.assertEqual(probe(request | {'port': unlistened.getsockname()[1]})['status'], 'BLOCKED')
                self.assertEqual(probe(request | {'source': '192.0.2.254'})['status'], 'INCONCLUSIVE')
