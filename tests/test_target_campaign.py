from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import json
from urllib.parse import urlencode
import threading
import unittest

from lab.native_readback_fixture import Fixture, manifest, responses, credentials
from tools.guest_probe import probe
from tools.qualify_target import (ASSETS, authority_matches, budget, native_readback,
                                  traffic_campaign, validate, bound_inputs, workload_binding, WORKLOAD_ASSETS)
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
    def test_v2_real_tls_combines_network_and_workload_observations(self):
        from tests.test_openstack_observe import OpenStackReadbackTests, PROJECT
        from tools import neutron_observe as n
        fixture = OpenStackReadbackTests(); fixture.setUp()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                native = json.loads(Path('ansible/fixtures/neutron_manifest.json').read_text())
                native['project_id'] = PROJECT
                for r in native['resources']:
                    query = urlencode([('fields', x) for x in sorted(n.FIELDS[r['kind']])])
                    path = '/v2.0/' + n.COLLECTION[r['kind']] + '/' + r['id'] + '?' + query
                    fixture.f.routes[path] = {'body': {r['kind']: {'id': r['id'], 'project_id': PROJECT,
                        'revision_number': 1, **r['expected']}}}
                ca = (fixture.f.directory / 'ca.pem').read_bytes()
                write_new(directory / 'native_manifest', encoded(native)); write_new(directory / 'native_ca', ca)
                assets = {'native_credentials': encoded({'token': 'fixture'}), 'workload_manifest': encoded(fixture.m),
                          'workload_token': b'fixture', 'workload_ca': ca}
                plan = {'format': 'hosting-target-campaign/2', 'scope': fixture.m['scope'], 'origin': fixture.f.origin}
                combined = native_readback(plan, assets, window(), directory, 'before')
                self.assertEqual(len(combined), 64)
                self.assertTrue((directory / 'before-workloads.json').is_file())
                fixture.f.routes[fixture.paths[0]]['body']['server']['OS-EXT-SRV-ATTR:host'] = 'unexpected-host'
                with self.assertRaises(ValueError): native_readback(plan, assets, window(), directory, 'after')
        finally: fixture.doCleanups()

    def test_v2_requires_exact_workload_assets_and_owned_storage(self):
        from tests.test_openstack_observe import manifest as workload_manifest, PROJECT, SERVER, VOLUME
        import copy
        plan = plan_fixture(); plan['format'] = 'hosting-target-campaign/2'; plan['scope']['platform'] = 'openstack'
        with self.assertRaises(ValueError): validate(plan)
        plan['assets'].update({k: dict(path='/private/' + k, sha256='a' * 64) for k in WORKLOAD_ASSETS})
        validate(plan)
        m = workload_manifest(plan['origin']); m['scope'] = plan['scope']
        outputs = {'members': {'value': {'guest': {'server_id': SERVER, 'boot_volume_id': VOLUME, 'data_volume_ids': []}}}}
        workload_binding(plan['scope'], m, outputs, PROJECT)
        for mutation in ('server', 'volume', 'project', 'scope', 'image'):
            bad = copy.deepcopy(m)
            if mutation in ('server', 'volume', 'image'): bad['resources'] = [r for r in bad['resources'] if r['kind'] != mutation]
            if mutation == 'project': bad['project_id'] = 'f' * 32
            if mutation == 'scope': bad['scope']['tenant_key'] = 'foreign'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): workload_binding(plan['scope'], bad, outputs, PROJECT)
        bad = copy.deepcopy(m)
        bad['resources'][1]['expected']['attachments'][0]['server_id'] = VOLUME
        with self.assertRaises(ValueError): workload_binding(plan['scope'], bad, outputs, PROJECT)
        bad = copy.deepcopy(m)
        bad['resources'][1]['expected']['volume_image_metadata']['image_id'] = VOLUME
        with self.assertRaises(ValueError): workload_binding(plan['scope'], bad, outputs, PROJECT)

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
