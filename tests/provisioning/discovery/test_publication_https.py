"""Actual mTLS publisher to the existing ingest listener and signature custody."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import ssl
import time
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from provisioner.controlplane.discovery import ingest, publication_https
from provisioner.controlplane.discovery.publication import (
    DiscoveryPublicationHeld, collect_submission)
from provisioner.controlplane.discovery.publication_https import (
    DiscoveryHttpsPublisher, DiscoveryPublicationUnknown, DiscoveryPublishTarget)
from tests.provisioning.discovery.test_publication import PublicationFixture


class DiscoveryPublicationHttpsTests(PublicationFixture, unittest.TestCase):
    def setUp(self):
        self.configure()
        root = self.f.pki.root
        (root/'collector.key').chmod(0o600)
        self.target = DiscoveryPublishTarget(
            origin=f'https://localhost:{self.f.server.server_port}',connect_ip='127.0.0.1',
            trust_domain='workers.example', ca_bundle=root/'ca.pem',
            ca_digest=hashlib.sha256((root/'ca.pem').read_bytes()).hexdigest(),
            crl_bundle=root/'crl.pem',crl_digest=hashlib.sha256((root/'crl.pem').read_bytes()).hexdigest(),
            client_certificate=root/'collector.pem',
            certificate_digest=hashlib.sha256((root/'collector.pem').read_bytes()).hexdigest(),
            client_key=root/'collector.key')

    def publisher(self, **changes):
        options = dict(target=self.target,verifier=self.verifier,outbox=self.outbox,clock=self.clock)
        options.update(changes)
        return DiscoveryHttpsPublisher(**options)

    def test_collection_signing_outbox_and_actual_ingest_preserve_original_evidence(self):
        value = collect_submission(self.f.campaign,self.environment,self.signature,
            collect=self.pages,signer=self.signer,verifier=self.verifier,clock=self.clock)
        receipt = self.publisher().publish(value)
        self.assertEqual(receipt.request_digest,value.digest)
        self.assertEqual(receipt.result_digest,value.result.digest)
        self.assertEqual(receipt.generation,1)
        self.assertEqual(receipt.completeness,'PARTIAL')
        self.assertIs(receipt.execution_authorized,False)
        self.assertEqual(self.f.retained_requests[-1],value.body)
        self.assertEqual(self.outbox.load(value.digest).body,value.body)
        self.assertEqual([event[0] for event in self.f.events],
                         ['retained','campaign-commit','retained','result-commit'])

    def test_outbox_failure_prevents_any_network_publication(self):
        self.outbox_root.chmod(0o755)
        with self.assertRaises(DiscoveryPublicationHeld): self.publisher().publish(self.signed())
        self.assertEqual(self.f.events,[])

    def test_single_attempt_cannot_implicitly_republish(self):
        publisher,value = self.publisher(),self.signed()
        publisher.publish(value)
        events = list(self.f.events)
        with self.assertRaises(DiscoveryPublicationHeld): publisher.publish(value)
        self.assertEqual(self.f.events,events)

    def test_lost_result_ack_is_unknown_and_explicit_retry_uses_original_bytes(self):
        value = self.signed()
        reply = ingest._DiscoveryHandler._reply
        def lose(handler,status,document):
            if document.get('status') == 'RESULT_PUBLISHED':
                handler.connection.shutdown(socket.SHUT_RDWR)
                handler.close_connection = True
                return
            reply(handler,status,document)
        with patch.object(ingest._DiscoveryHandler,'_reply',lose):
            with self.assertRaises(DiscoveryPublicationUnknown) as caught:
                self.publisher().publish(value)
        self.assertEqual(caught.exception.phase,'RESULT')
        self.assertEqual(caught.exception.request_digest,value.digest)
        self.assertEqual(self.f.retained_requests[-1],value.body)
        retained = self.outbox.load(value.digest)
        self.publisher().publish(retained)
        self.assertEqual(self.f.retained_requests[-1],value.body)
        self.assertEqual(len([x for x in self.f.events if x[0]=='result-commit']),2)

    def test_wrong_result_digest_or_environment_or_completeness_never_becomes_success(self):
        reply = ingest._DiscoveryHandler._reply
        for changes in ({'resultDigest':'f'*64},{'environmentId':'foreign'},
                        {'campaignId':'foreign'},{'completeness':'UNKNOWN'},
                        {'generation':True},{'generation':0},{'generation':2**63},
                        {'executionAuthorized':True},{'executionAuthorized':0},{'extra':'unexpected'}):
            def wrong(handler,status,document):
                if document.get('status')=='RESULT_PUBLISHED': document = {**document,**changes}
                reply(handler,status,document)
            with self.subTest(changes=changes),patch.object(ingest._DiscoveryHandler,'_reply',wrong):
                with self.assertRaises(DiscoveryPublicationUnknown): self.publisher().publish(self.signed())

    def test_wrong_campaign_ack_never_sends_result(self):
        reply = ingest._DiscoveryHandler._reply
        def wrong(handler,status,document):
            if document.get('status')=='CAMPAIGN_REGISTERED':
                document = {**document,'authorizationDigest':'f'*64}
            reply(handler,status,document)
        with patch.object(ingest._DiscoveryHandler,'_reply',wrong):
            with self.assertRaises(DiscoveryPublicationUnknown) as caught:
                self.publisher().publish(self.signed())
        self.assertEqual(caught.exception.phase,'CAMPAIGN')
        self.assertNotIn('result-commit',[e[0] for e in self.f.events])

    def test_revoked_authority_cannot_use_retained_original_submission(self):
        value = self.signed()
        self.outbox.retain(value)
        self.revoke()
        with self.assertRaises(DiscoveryPublicationHeld): self.publisher().publish(self.outbox.load(value.digest))
        self.assertEqual(self.f.events,[])

    def test_revocation_after_registration_ack_stops_result_request(self):
        reply = ingest._DiscoveryHandler._reply
        case = self
        def revoked(handler,status,document):
            if document.get('status')=='CAMPAIGN_REGISTERED': case.revoke()
            reply(handler,status,document)
        with patch.object(ingest._DiscoveryHandler,'_reply',revoked):
            with self.assertRaises(DiscoveryPublicationUnknown): self.publisher().publish(self.signed())
        self.assertNotIn('result-commit',[e[0] for e in self.f.events])

    def test_expiry_and_clock_regression_hold_before_publication(self):
        value = self.signed()
        for at in (self.f.campaign.expires_at,self.f.campaign.issued_at-timedelta(seconds=1)):
            with self.subTest(at=at),self.assertRaises(DiscoveryPublicationHeld):
                self.publisher(clock=lambda:at).publish(value)
        self.assertEqual(self.f.events,[])

    def test_each_tls_identity_scope_component_is_checked_before_publication(self):
        root = self.f.pki.root
        for name in ('other-worker','other-site','other-tenant','other-org'):
            (root/f'{name}.key').chmod(0o600)
            target = replace(self.target,client_certificate=root/f'{name}.pem',client_key=root/f'{name}.key',
                certificate_digest=hashlib.sha256((root/f'{name}.pem').read_bytes()).hexdigest())
            with self.subTest(name=name),self.assertRaises(DiscoveryPublicationHeld):
                self.publisher(target=target).publish(self.signed())
        self.assertEqual(self.f.events,[])

    def test_ca_crl_and_client_certificate_changes_cannot_be_silently_loaded(self):
        for name in ('ca.pem','crl.pem','collector.pem'):
            path = self.f.pki.root/name
            data = path.read_bytes()
            path.write_bytes(data+b'\n')
            with self.subTest(name=name),self.assertRaises(DiscoveryPublicationHeld):
                self.publisher().publish(self.signed())
            path.write_bytes(data)
        self.assertEqual(self.f.events,[])

    def test_public_or_mismatched_tls_private_key_cannot_publish(self):
        key = self.target.client_key
        key.chmod(0o644)
        with self.assertRaises(DiscoveryPublicationHeld): self.publisher().publish(self.signed())
        key.chmod(0o600)
        wrong = self.f.pki.root/'other-worker.key'
        wrong.chmod(0o600)
        with self.assertRaises(DiscoveryPublicationHeld):
            self.publisher(target=replace(self.target,client_key=wrong)).publish(self.signed())
        self.assertEqual(self.f.events,[])

    def test_bad_server_hostname_is_rejected_by_real_tls(self):
        target = replace(self.target,origin=self.target.origin.replace('localhost','wrong.invalid'))
        with self.assertRaises(DiscoveryPublicationHeld): self.publisher(target=target).publish(self.signed())
        self.assertEqual(self.f.events,[])

    def test_revoked_client_certificate_is_rejected_by_ingest_tls(self):
        from cryptography import x509
        cert = x509.load_pem_x509_certificate(self.target.client_certificate.read_bytes())
        self.f.pki.write_crl([cert.serial_number])
        self.f.tls.reload_trust()
        target = replace(self.target,crl_digest=hashlib.sha256(self.target.crl_bundle.read_bytes()).hexdigest())
        with self.assertRaises(DiscoveryPublicationHeld): self.publisher(target=target).publish(self.signed())
        self.assertEqual(self.f.events,[])

    def test_revoked_server_certificate_is_rejected_by_client_tls(self):
        from cryptography import x509
        cert = x509.load_pem_x509_certificate((self.f.pki.root/'server.pem').read_bytes())
        self.f.pki.write_crl([cert.serial_number])
        target = replace(self.target,crl_digest=hashlib.sha256(self.target.crl_bundle.read_bytes()).hexdigest())
        with self.assertRaises(DiscoveryPublicationHeld): self.publisher(target=target).publish(self.signed())
        self.assertEqual(self.f.events,[])

    def test_proxy_and_tls_keylog_environment_are_not_used(self):
        log = self.f.root/'secret-keylog'
        with patch.dict(os.environ,{'HTTPS_PROXY':'http://invalid:9','ALL_PROXY':'http://invalid:9',
                                    'SSLKEYLOGFILE':str(log)}):
            self.publisher().publish(self.signed())
        self.assertFalse(log.exists())

    def test_redirect_error_and_invalid_framing_are_unknown_without_retry(self):
        for status,extras,body in ((302,[],b'{}'),(503,[],b'sensitive-error'),
                (200,[('Content-Length','2')],b'{}'),(200,[('Transfer-Encoding','chunked')],b'{}'),
                (200,[],b'{"status":0,"status":1}'),(200,[],b'[]')):
            def invalid(handler,_status,_document):
                handler.send_response(status)
                handler.send_header('Content-Type','application/json')
                handler.send_header('Content-Length',str(len(body)))
                for name,value in extras: handler.send_header(name,value)
                handler.end_headers()
                try: handler.wfile.write(body)
                except OSError: pass
                handler.close_connection=True
            with self.subTest(status=status,extras=extras),patch.object(ingest._DiscoveryHandler,'_reply',invalid):
                with self.assertRaises(DiscoveryPublicationUnknown) as caught:
                    self.publisher().publish(self.signed())
                self.assertNotIn('sensitive-error',str(caught.exception))
        self.assertNotIn('result-commit',[e[0] for e in self.f.events])

    def test_deadline_after_committed_campaign_ack_is_unknown(self):
        reply = ingest._DiscoveryHandler._reply
        def slow(handler,status,document):
            if document.get('status')=='CAMPAIGN_REGISTERED': time.sleep(0.5)
            try: reply(handler,status,document)
            except OSError: pass
        with patch.object(ingest._DiscoveryHandler,'_reply',slow):
            started=time.monotonic()
            with self.assertRaises(DiscoveryPublicationUnknown): self.publisher(timeout=0.2).publish(self.signed())
            self.assertLess(time.monotonic()-started,1.5)
            time.sleep(0.55)  # Join this fixture's delayed response before restoring its handler.
        self.assertNotIn('result-commit',[e[0] for e in self.f.events])

    def test_invalid_target_normalization_is_rejected(self):
        for origin in ('https://localhost/','https://localhost?','https://localhost#',
                       'https://@localhost','https://local\nhost','http://localhost',
                       'https://localhost:','https://localhost:0','https://localhost/%2e'):
            with self.subTest(origin=origin),self.assertRaises(ValueError): replace(self.target,origin=origin)
        for ip in ('0.0.0.0','224.0.0.1','fe80::1%eth0','127.000.0.1'):
            with self.subTest(ip=ip),self.assertRaises(ValueError): replace(self.target,connect_ip=ip)


if __name__ == '__main__':
    unittest.main()
