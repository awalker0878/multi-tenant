"""Three independent loopback TLS services exercise exact-project discovery.

All tokens, certificates, catalog identities and RBAC witnesses are synthetic.
These tests qualify protocol behavior, not an installed OpenStack environment.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import ssl
import threading
import time
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provisioner.controlplane.discovery import native_https
from provisioner.controlplane.discovery.adapters.openstack import OpenStackServiceEndpoints
from provisioner.controlplane.discovery.adapters.openstack_credentials import (
    API_VERSIONS, COLLECTOR_ID, SignedFileOpenStackCredentialSource)
from provisioner.controlplane.discovery.adapters.openstack_https import OpenStackHttpsTransport
from provisioner.controlplane.discovery.model import _json, assemble_discovery_result
from provisioner.controlplane.discovery.native_credentials import NativeReadHeld
from provisioner.controlplane.discovery.trust import (
    DiscoveryKeyEnrollment, DiscoverySignature, DiscoveryTrustPolicy,
    SignedDiscoveryIngestVerifier, SignedFileDiscoveryTrustStore,
    campaign_signing_bytes, trust_policy_signing_bytes)
from provisioner.controlplane.discovery.witness import (
    NativeCredentialWitnessPolicy, NativeReadCredentialWitness,
    SignedFileDiscoveryCredentialAuthority, credential_witness_signing_bytes)
from tests.provisioning.discovery.test_openstack import (
    ENDPOINTS, OTHER, PROJECT, VM1, VM2, campaign, responses)
from tests.provisioning.worker.tls_fixtures import TestPki


def encoded(value):
    return base64.b64encode(value).decode('ascii')


class OpenStackHttpsTests(unittest.TestCase):
    def setUp(self):
        self.pki = TestPki()
        self.addCleanup(self.pki.close)
        self.root = self.pki.root
        self.pki.issue('native')
        self.root_key, self.native_key, self.issuer_key, self.collector_key = (
            Ed25519PrivateKey.generate() for _ in range(4))
        self.now = datetime.now(timezone.utc)
        before, after = self.now - timedelta(seconds=10), self.now + timedelta(minutes=20)
        self.campaign = replace(campaign(), collector_id=COLLECTOR_ID,
                                issued_at=before, expires_at=self.now + timedelta(minutes=2))
        self.environment, self.reference = 'environment-1', 'vault:project-reader'
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
            self.campaign.scope, 'four-service-image-rbac-review', 'a'*64, before, after, True)
        self.witness_policy = NativeCredentialWitnessPolicy(1, before,
            self.now + timedelta(minutes=4), (self.witness,))
        self.write_witness()
        self.trust_verifier = SignedDiscoveryIngestVerifier(
            SignedFileDiscoveryTrustStore(self.trust_path,
                authority_public_key=self.root_key.public_key(), minimum_revision=1),
            SignedFileDiscoveryCredentialAuthority(self.witness_path,
                authority_public_key=self.native_key.public_key(), minimum_revision=1))
        self.bind_campaign()
        self.calls, self.on_get = [], None
        self.stop_response = threading.Event()
        self.request_started = threading.Event()
        self.headers_sent = threading.Event()
        self.delay, self.drip = 0, False
        self.raw_body = None
        self.statuses = {service: 200 for service in API_VERSIONS}
        self.version_headers = {
            'compute': [('OpenStack-API-Version', 'compute ' + API_VERSIONS['compute'])],
            'volume': [('OpenStack-API-Version', 'volume ' + API_VERSIONS['volume'])],
            'network': [], 'image': []}
        self.extra_headers = []
        self.values = {(service, path, marker): value
            for (endpoint, path, marker), value in responses().items()
            for service in API_VERSIONS if ENDPOINTS.for_service(service) == endpoint}
        self.servers, self.threads = {}, []
        self.addCleanup(self.stop)
        for service in API_VERSIONS:
            self.start_server(service)
        self.endpoints = OpenStackServiceEndpoints(ENDPOINTS.endpoint_id, PROJECT,
            f'https://localhost:{self.servers["compute"].server_port}/compute/v2.1/{PROJECT}',
            f'https://localhost:{self.servers["volume"].server_port}/volume/v3/{PROJECT}',
            f'https://localhost:{self.servers["network"].server_port}/network/v2.0',
            f'https://localhost:{self.servers["image"].server_port}/image/v2')
        self.credential_path = self.root / 'credential.json'
        self.token = 'synthetic-project-token-no-native-authority'
        self.binding = {
            'format': 'hosting-openstack-read-credential/1', 'revision': 1,
            'campaignDigest': self.campaign.digest(), 'environmentId': self.environment,
            'collectorId': COLLECTOR_ID, 'credentialReference': self.reference,
            'scopeType': 'project', 'projectId': PROJECT, 'userId': VM1,
            'catalogDigest': 'b'*64, 'regionId': 'RegionOne', 'interface': 'internal',
            'apiVersions': dict(API_VERSIONS),
            'endpoints': {service: {
                'url': self.endpoints.for_service(service), 'catalogEndpointId': str(index)*32,
                'connectIp': '127.0.0.1',
                'caDigest': hashlib.sha256((self.root/'ca.pem').read_bytes()).hexdigest()}
                for index, service in enumerate(API_VERSIONS, 3)},
            'tokenDigest': hashlib.sha256(self.token.encode()).hexdigest(),
            'tokenIssuedAt': before.isoformat(), 'tokenExpiresAt': after.isoformat(),
            'notBefore': before.isoformat(), 'expiresAt': after.isoformat()}
        self.write_material()
        self.source = SignedFileOpenStackCredentialSource(self.credential_path,
            authority_public_key=self.native_key.public_key(), minimum_revision=1)
        self.transport = self.client()

    def start_server(self, service):
        case = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def handle(self):
                try:
                    super().handle()
                except (OSError, ssl.SSLError):
                    pass
            def do_GET(self):
                delay, drip = case.delay, case.drip
                status = case.statuses[service]
                versions, extras = list(case.version_headers[service]), list(case.extra_headers)
                case.calls.append((service, self.command, self.path, dict(self.headers)))
                case.request_started.set()
                try:
                    url = urlsplit(self.path)
                    prefix = urlsplit(case.endpoints.for_service(service)).path + '/'
                    relative = url.path.removeprefix(prefix)
                    marker = parse_qs(url.query).get('marker', [None])[0]
                    value = case.values.get((service, relative, marker), {})
                    body = case.raw_body if case.raw_body is not None else json.dumps(value).encode()
                    if case.on_get:
                        case.on_get()
                    if case.stop_response.wait(delay):
                        return
                    self.send_response(status)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(body)))
                    for key, item in versions + extras:
                        self.send_header(key, item)
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
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.daemon_threads = True
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.root/'native.pem', self.root/'native.key')
        server.socket = context.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever,
                                  kwargs={'poll_interval': 0.01}, daemon=True)
        self.servers[service] = server
        self.threads.append(thread)
        thread.start()

    def stop(self):
        self.stop_response.set()
        for server in self.servers.values():
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join(timeout=2)

    def write_signed(self, path, body, key, payload):
        path.write_text(json.dumps({'policy': body.as_dict(),
            'signature': encoded(key.sign(payload(body)))}))
        path.chmod(0o600)

    def write_trust(self):
        self.write_signed(self.trust_path, self.policy, self.root_key, trust_policy_signing_bytes)

    def write_witness(self):
        self.write_signed(self.witness_path, self.witness_policy,
                          self.native_key, credential_witness_signing_bytes)

    def bind_campaign(self):
        self.verifier = self.trust_verifier.bind(DiscoverySignature('issuer',
            encoded(self.issuer_key.sign(campaign_signing_bytes(self.campaign, self.environment)))))

    def write_material(self, signer=None):
        self.credential_path.write_text(json.dumps({'binding': self.binding, 'token': self.token,
            'signature': encoded((signer or self.native_key).sign(_json(self.binding).encode('ascii')))}))
        self.credential_path.chmod(0o600)

    def client(self, **changes):
        args = dict(verifier=self.verifier, credentials=self.source,
                    ca_bundles={service: self.root/'ca.pem' for service in API_VERSIONS},
                    clock=lambda: self.now)
        args.update(changes)
        return OpenStackHttpsTransport(self.campaign, self.endpoints, self.environment, **args)

    def read_material(self):
        return self.source.read(self.campaign, self.endpoints, self.environment, checked_at=self.now)

    def first(self, client=None):
        return (client or self.transport).get_json(self.endpoints.compute, 'servers/detail',
            {'limit': str(self.campaign.max_page_size), 'all_tenants': 'false'})

    def revoke_witness(self):
        self.witness_policy = replace(self.witness_policy, revision=self.witness_policy.revision+1,
            witnesses=(replace(self.witness, revoked_at=self.now),))
        self.write_witness()

    def change_campaign(self, **changes):
        self.campaign = replace(self.campaign, **changes)
        self.bind_campaign()
        self.binding['campaignDigest'] = self.campaign.digest()
        self.write_material()
        self.transport = self.client()

    def test_four_real_tls_endpoints_receive_exact_scope_token_and_versions(self):
        result = assemble_discovery_result(self.campaign, self.transport.collect(), checked_at=self.now)
        self.assertEqual(result.completeness, 'PARTIAL')
        self.assertIn('VISIBLE_INVENTORY_ONLY', result.collection_errors)
        self.assertEqual(len(result.objects), 7)
        self.assertEqual([call[0] for call in self.calls], ['compute','volume','network']*2 + ['image'])
        for service, method, path, headers in self.calls:
            self.assertEqual(method, 'GET')
            self.assertEqual(headers['X-Auth-Token'], self.token)
            self.assertEqual(headers['Host'], f'localhost:{self.servers[service].server_port}')
            self.assertNotIn('Authorization', headers)
            self.assertNotIn('X-Ntnx-Api-Key', headers)
            if service in ('compute', 'volume'):
                self.assertEqual(headers['OpenStack-API-Version'], service+' '+API_VERSIONS[service])
            else:
                self.assertNotIn('OpenStack-API-Version', headers)
        self.assertEqual(parse_qs(urlsplit(self.calls[2][2]).query),
                         {'limit': ['2'], 'project_id': [PROJECT]})
        self.assertNotIn(self.token, repr(result))
        self.assertNotIn(self.token, repr(self.read_material()))
        with self.assertRaises(NativeReadHeld):
            self.transport.collect()
        self.assertEqual(len(self.calls), 7)

    def test_empty_visible_inventory_is_partial_not_complete(self):
        for service, path, key in (('compute','servers/detail','servers'),
                ('volume','volumes/detail','volumes'), ('network','ports','ports')):
            self.values[(service,path,None)] = {key: []}
        result = assemble_discovery_result(self.campaign, self.transport.collect(), checked_at=self.now)
        self.assertEqual(result.completeness, 'PARTIAL')
        self.assertEqual({obj.identity.resource_kind for obj in result.objects}, {'quota'})

    def test_consecutive_pagination_uses_only_last_observed_identity(self):
        row = self.values[('compute','servers/detail',None)]['servers'][0]
        self.values[('compute','servers/detail',None)]['servers'].append({**row, 'id': VM2})
        self.values[('compute','servers/detail',VM2)] = {'servers': []}
        self.transport.collect()
        self.assertEqual(parse_qs(urlsplit(self.calls[1][2]).query)['marker'], [VM2])
        self.assertEqual(len(self.calls), 8)

    def test_linked_short_page_is_read_without_following_server_url(self):
        self.values[('compute','servers/detail',None)]['servers_links'] = [
            {'rel':'next','href':self.endpoints.compute+'/servers/detail?marker='+VM1}]
        self.values[('compute','servers/detail',VM1)] = {'servers': []}
        self.transport.collect()
        self.assertEqual(parse_qs(urlsplit(self.calls[1][2]).query),
                         {'limit':['2'],'all_tenants':['false'],'marker':[VM1]})

    def test_wrong_service_path_project_or_query_is_rejected_before_connection(self):
        params = {'limit':'2','all_tenants':'false'}
        attempts = (
            ('https://foreign.invalid','servers/detail',params),
            (self.endpoints.volume,'servers/detail',params),
            (self.endpoints.compute,'../servers/detail',params),
            (self.endpoints.compute,'servers/detail?all_tenants=true',params),
            (self.endpoints.compute,f'os-quota-sets/{OTHER}',{}),
            (self.endpoints.compute,'servers/detail',{**params,'all_tenants':'true'}),
            (self.endpoints.compute,'servers/detail',{**params,'marker':VM2}),
            (self.endpoints.compute,'servers/detail',{**params,'project_id':OTHER}),
            (self.endpoints.compute,'servers/detail',{**params,'limit':True}),
        )
        for endpoint, path, query in attempts:
            with self.subTest(path=path, query=query), self.assertRaises(NativeReadHeld):
                self.client().get_json(endpoint,path,query)
        self.assertEqual(self.calls, [])

    def test_repeated_read_latches_instance_closed(self):
        self.first()
        with self.assertRaises(NativeReadHeld):
            self.first()
        with self.assertRaises(NativeReadHeld):
            self.transport.get_json(self.endpoints.volume,'volumes/detail',{'limit':'2'})
        self.assertEqual(len(self.calls), 1)

    def test_page_and_object_budgets_do_not_publish_short_scans(self):
        self.change_campaign(max_pages=5)
        with self.assertRaises(NativeReadHeld):
            self.transport.collect()
        self.assertEqual(len(self.calls), 5)

    def test_object_budget_stops_before_further_reads(self):
        self.change_campaign(max_objects=2)
        with self.assertRaises(NativeReadHeld):
            self.transport.collect()
        self.assertEqual(len(self.calls), 3)

    def test_cross_project_body_is_not_accepted_or_published(self):
        self.values[('compute','servers/detail',None)]['servers'][0]['tenant_id'] = OTHER
        with self.assertRaises(NativeReadHeld):
            self.transport.collect()
        self.assertEqual(len(self.calls), 1)

    def test_server_link_cannot_redirect_credentials(self):
        self.values[('compute','servers/detail',None)]['servers_links'] = [
            {'rel':'next','href':'https://foreign.invalid/servers/detail?marker='+VM1}]
        with self.assertRaises(NativeReadHeld):
            self.transport.collect()
        self.assertEqual(len(self.calls), 1)

    def test_duplicate_objects_and_nonadvancing_markers_are_rejected(self):
        row = self.values[('compute','servers/detail',None)]['servers'][0]
        self.values[('compute','servers/detail',None)]['servers'] = [row,row]
        with self.assertRaises(NativeReadHeld):
            self.transport.collect()
        self.assertEqual(len(self.calls), 1)

    def test_missing_different_or_duplicate_version_is_not_schema_evidence(self):
        for service in ('compute','volume'):
            original = self.version_headers[service]
            for headers in ([], [('OpenStack-API-Version',service+' latest')], original*2):
                with self.subTest(service=service, headers=headers):
                    self.version_headers[service] = headers
                    with self.assertRaises(NativeReadHeld):
                        self.client().collect()
            self.version_headers[service] = original

    def test_missing_tampered_unsigned_material_stops_before_read(self):
        self.write_material(Ed25519PrivateKey.generate())
        with self.assertRaises(NativeReadHeld): self.first(self.client())
        self.write_material()
        document = json.loads(self.credential_path.read_text())
        document['token'] += '-tampered'
        self.credential_path.write_text(json.dumps(document))
        with self.assertRaises(NativeReadHeld): self.first(self.client())
        self.credential_path.unlink()
        with self.assertRaises(NativeReadHeld): self.first(self.client())
        self.assertEqual(self.calls, [])

    def test_exact_signed_campaign_project_principal_catalog_and_api_are_required(self):
        original = copy.deepcopy(self.binding)
        invalid = (
            ('campaignDigest','f'*64), ('environmentId','other'), ('collectorId','site-worker-01'),
            ('credentialReference','vault:other'), ('scopeType','system'), ('scopeType','domain'),
            ('projectId',OTHER), ('userId',None), ('catalogDigest','bad'), ('regionId',''),
            ('interface','admin'), ('apiVersions',{**dict(API_VERSIONS),'compute':'latest'}),
            ('format','hosting-ahv-read-credential/1'),
            ('tokenExpiresAt',self.now.isoformat()),
            ('tokenIssuedAt',(self.now+timedelta(seconds=1)).isoformat()),
            ('expiresAt',(self.now+timedelta(hours=2)).isoformat()),
        )
        for field, value in invalid:
            with self.subTest(field=field):
                self.binding = {**copy.deepcopy(original),field:value}
                self.write_material()
                with self.assertRaises(NativeReadHeld): self.first(self.client())
        self.assertEqual(self.calls, [])

    def test_every_signed_endpoint_must_match_before_first_token_transmission(self):
        original = copy.deepcopy(self.binding)
        for field, bad in (('url',self.endpoints.compute), ('catalogEndpointId','bad'),
                ('catalogEndpointId',original['endpoints']['compute']['catalogEndpointId']),
                ('connectIp','0.0.0.0'), ('connectIp','224.0.0.1'), ('connectIp','fe80::1%eth0'),
                ('caDigest','bad')):
            with self.subTest(field=field, bad=bad):
                self.binding = copy.deepcopy(original)
                self.binding['endpoints']['network'][field] = bad
                self.write_material()
                with self.assertRaises(NativeReadHeld): self.first(self.client())
        self.assertEqual(self.calls, [])

    def test_campaign_root_issuer_and_collector_cannot_sign_credentials(self):
        for key in (self.root_key,self.issuer_key,self.collector_key):
            self.write_material(key)
            source = SignedFileOpenStackCredentialSource(self.credential_path,
                authority_public_key=key.public_key(),minimum_revision=1)
            with self.assertRaises(NativeReadHeld): self.first(self.client(credentials=source))
        self.assertEqual(self.calls, [])

    def test_revoked_or_write_capable_witness_blocks_native_reads(self):
        self.revoke_witness()
        with self.assertRaises(NativeReadHeld): self.first(self.client())
        self.witness_policy = replace(self.witness_policy,revision=3,
            witnesses=(replace(self.witness,read_only=False),))
        self.write_witness()
        with self.assertRaises(NativeReadHeld): self.first(self.client())
        self.assertEqual(self.calls, [])

    def test_revocation_on_success_is_not_swallowed_as_publishable_error_page(self):
        self.on_get = self.revoke_witness
        with self.assertRaises(NativeReadHeld): self.transport.collect()
        self.assertEqual(len(self.calls), 1)

    def test_revocation_on_error_is_not_swallowed_as_publishable_error_page(self):
        self.on_get = self.revoke_witness
        self.statuses['compute'] = 403
        with self.assertRaises(NativeReadHeld): self.transport.collect()
        self.assertEqual(len(self.calls), 1)

    def test_rotation_after_tls_does_not_send_stale_token(self):
        original = ssl.SSLSocket.do_handshake
        case = self
        def rotate(sock,*args,**kwargs):
            value = original(sock,*args,**kwargs)
            if not sock.server_side:
                case.binding['revision'] += 1
                case.write_material()
            return value
        with patch.object(ssl.SSLSocket,'do_handshake',rotate), self.assertRaises(NativeReadHeld):
            self.first()
        self.assertEqual(self.calls, [])

    def test_rotation_after_request_discards_response(self):
        def rotate():
            self.binding['revision'] += 1
            self.write_material()
        self.on_get = rotate
        with self.assertRaises(NativeReadHeld): self.first()
        self.assertEqual(len(self.calls), 1)

    def test_new_signed_revision_can_rotate_token_between_service_reads(self):
        self.first()
        self.binding['revision'] = 2
        self.token += '-rotated'
        self.binding['tokenDigest'] = hashlib.sha256(self.token.encode()).hexdigest()
        self.write_material()
        value = self.transport.get_json(self.endpoints.volume,'volumes/detail',{'limit':'2'})
        self.assertIn('volumes',value)
        self.assertEqual(self.calls[-1][3]['X-Auth-Token'],self.token)

    def test_public_symlink_fifo_and_oversized_credential_files_are_rejected(self):
        self.credential_path.chmod(0o644)
        with self.assertRaises(NativeReadHeld): self.read_material()
        self.credential_path.chmod(0o600)
        saved = self.credential_path.with_suffix('.saved')
        self.credential_path.rename(saved)
        self.credential_path.symlink_to(saved)
        with self.assertRaises(NativeReadHeld): self.read_material()
        self.credential_path.unlink()
        os.mkfifo(self.credential_path,0o600)
        with self.assertRaises(NativeReadHeld): self.read_material()
        self.credential_path.unlink()
        self.credential_path.write_bytes(b' '*65537)
        self.credential_path.chmod(0o600)
        with self.assertRaises(NativeReadHeld): self.read_material()

    def test_revision_floor_rollback_and_equivocation_are_rejected(self):
        self.read_material()
        self.binding['userId'] = VM2
        self.write_material()
        with self.assertRaises(NativeReadHeld): self.read_material()
        self.binding['revision'] = 2
        self.write_material()
        self.read_material()
        self.binding['revision'] = 1
        self.write_material()
        with self.assertRaises(NativeReadHeld): self.read_material()
        source = SignedFileOpenStackCredentialSource(self.credential_path,
            authority_public_key=self.native_key.public_key(), minimum_revision=2)
        with self.assertRaises(NativeReadHeld):
            source.read(self.campaign,self.endpoints,self.environment,checked_at=self.now)

    def test_current_campaign_time_is_checked_on_success_and_failure(self):
        self.on_get = lambda: setattr(self,'now',self.campaign.expires_at)
        with self.assertRaises(NativeReadHeld): self.transport.collect()
        self.assertEqual(len(self.calls),1)

    def test_expired_campaign_and_regressed_clock_cannot_send_token(self):
        for at in (self.campaign.expires_at,self.campaign.issued_at-timedelta(seconds=1)):
            with self.subTest(at=at), self.assertRaises(NativeReadHeld):
                self.first(self.client(clock=lambda: at))
        self.assertEqual(self.calls,[])
        self.first()
        self.now = self.campaign.issued_at
        with self.assertRaises(NativeReadHeld):
            self.transport.get_json(self.endpoints.volume,'volumes/detail',{'limit':'2'})
        self.assertEqual(len(self.calls),1)

    def test_changed_ca_cannot_receive_token(self):
        (self.root/'ca.pem').write_bytes((self.root/'ca.pem').read_bytes()+b'\n')
        with self.assertRaises(NativeReadHeld): self.first()
        self.assertEqual(self.calls,[])

    def test_bad_tls_hostname_cannot_receive_token(self):
        self.endpoints = replace(self.endpoints,compute=self.endpoints.compute.replace('localhost','wrong.invalid'))
        self.binding['endpoints']['compute']['url'] = self.endpoints.compute
        self.write_material()
        with self.assertRaises(NativeReadHeld): self.first(self.client())
        self.assertEqual(self.calls,[])

    def test_redirects_errors_and_native_bodies_are_not_exposed_or_retried(self):
        self.raw_body = self.token.encode()
        for status in (302,401,403,406,429,503):
            with self.subTest(status=status):
                self.statuses['compute'] = status
                client = self.client()
                with self.assertRaises(NativeReadHeld) as raised: client.collect()
                self.assertNotIn(self.token,str(raised.exception))
                count = len(self.calls)
                with self.assertRaises(NativeReadHeld): self.first(client)
                self.assertEqual(len(self.calls),count)
        self.assertEqual(len(self.calls),6)

    def test_duplicate_json_truncation_and_oversize_cannot_advance_collection(self):
        for body in (b'{"servers":[],"servers":[]}',b'{"servers":',b'{"x":1e999}',
                     b'{"x":9223372036854775808}',b'[]',b' '*1025):
            with self.subTest(body=body[:40]):
                self.raw_body = body
                with self.assertRaises(NativeReadHeld): self.client(max_response_bytes=1024).collect()

    def test_invalid_framing_is_rejected(self):
        for headers in ([('Content-Length','0')],[('Transfer-Encoding','chunked')],
                        [('Content-Encoding','gzip')]):
            with self.subTest(headers=headers):
                self.extra_headers = headers
                with self.assertRaises(NativeReadHeld): self.client().collect()

    def test_slow_headers_exceed_total_deadline(self):
        self.delay = 2
        started = time.monotonic()
        with self.assertRaises(NativeReadHeld): self.first(self.client(timeout=0.2))
        self.assertTrue(self.request_started.is_set())
        self.assertLess(time.monotonic()-started,1.5)

    def test_dripping_body_cannot_extend_total_deadline(self):
        self.drip = True
        started = time.monotonic()
        with self.assertRaises(NativeReadHeld): self.first(self.client(timeout=0.3))
        self.assertTrue(self.headers_sent.is_set())
        self.assertLess(time.monotonic()-started,1.5)

    def test_response_decoded_after_deadline_is_not_returned(self):
        monotonic = time.monotonic
        now = [monotonic()]
        clock = SimpleNamespace(monotonic=lambda:now[0])
        decode = native_https.decode_json
        def late_decode(*args,**kwargs):
            result = decode(*args,**kwargs)
            now[0] += 20
            return result
        with patch.object(native_https,'time',clock), patch.object(native_https,'decode_json',late_decode):
            with self.assertRaises(NativeReadHeld): self.first()

    def test_proxy_environment_cannot_change_signed_destination(self):
        with patch.dict(os.environ,{'HTTPS_PROXY':'http://proxy.invalid:9999','ALL_PROXY':'http://proxy.invalid:9999'}):
            self.first()
        self.assertEqual(len(self.calls),1)

    def test_active_owners_and_shared_mechanism_have_no_forwarding_aliases(self):
        from provisioner.controlplane.discovery.adapters import openstack_credentials, openstack_https
        self.assertEqual(SignedFileOpenStackCredentialSource.__module__,openstack_credentials.__name__)
        self.assertEqual(OpenStackHttpsTransport.__module__,openstack_https.__name__)
        self.assertIs(openstack_https.read_json,native_https.read_json)


if __name__ == '__main__':
    unittest.main()
