"""Source outbox, mTLS ingest, original signatures and real PostgreSQL publication."""
from __future__ import annotations

import hashlib
import os
import socket
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization

from provisioner.controlplane.discovery import ingest
from provisioner.controlplane.discovery.model import DiscoveryFact
from provisioner.controlplane.discovery.publication import PrivateDiscoveryOutbox, PrivateFileDiscoveryResultSigner
from provisioner.controlplane.discovery.publication_https import (
    DiscoveryHttpsPublisher, DiscoveryPublicationUnknown, DiscoveryPublishTarget)
from provisioner.controlplane.discovery.trust import DiscoverySignature
from tests.provisioning.controlplane import test_discovery_ingest_postgres as existing_fixture


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_DISCOVERY_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN'),
                     'Requires dedicated disposable PostgreSQL discovery roles')
class DiscoveryPublicationPostgresTests(unittest.TestCase):
    def setUp(self):
        self.f = existing_fixture.DiscoveryIngestPostgresTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        f,root = self.f,self.f.pki.root
        self.verifier=f.server.service.signature_verifier
        signature=f.document()['campaignSignature']
        self.signature=DiscoverySignature(signature['keyId'],signature['signature'])
        key=f.root/'collector-result.pem'
        key.write_bytes(f.collector_key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        key.chmod(0o600)
        self.signer=PrivateFileDiscoveryResultSigner(key,key_id='collector-key')
        outbox=f.root/'outbox'
        outbox.mkdir(mode=0o700)
        self.outbox=PrivateDiscoveryOutbox(outbox,f.context)
        (root/'collector.key').chmod(0o600)
        self.target=DiscoveryPublishTarget(origin=f'https://localhost:{f.server.server_port}',
            connect_ip='127.0.0.1',trust_domain='workers.example',ca_bundle=root/'ca.pem',
            ca_digest=hashlib.sha256((root/'ca.pem').read_bytes()).hexdigest(),crl_bundle=root/'crl.pem',
            crl_digest=hashlib.sha256((root/'crl.pem').read_bytes()).hexdigest(),
            client_certificate=root/'collector.pem',
            certificate_digest=hashlib.sha256((root/'collector.pem').read_bytes()).hexdigest(),
            client_key=root/'collector.key')

    def publisher(self):
        return DiscoveryHttpsPublisher(self.target,verifier=self.verifier,outbox=self.outbox)

    def signed(self,result=None):
        return self.signer.sign(self.f.campaign,result or self.f.result,self.f.environment,
            self.signature,verifier=self.verifier,clock=lambda:datetime.now(timezone.utc))

    def generations(self):
        return self.f.reader.list_generations(self.f.context,self.f.scope,self.f.environment)

    def test_original_request_retry_has_one_generation_and_exact_retained_bytes(self):
        value=self.signed()
        first=self.publisher().publish(value)
        again=self.publisher().publish(self.outbox.load(value.digest))
        self.assertEqual(first,again)
        self.assertEqual(len(self.generations()),1)
        self.assertEqual(self.generations()[0].result_digest,value.result.digest)
        self.assertEqual(next(self.f.evidence.rglob(value.digest)).read_bytes(),value.body)
        self.assertIs(again.execution_authorized,False)

    def test_lost_ack_retry_reconciles_without_duplicate_generation(self):
        value=self.signed()
        reply=ingest._DiscoveryHandler._reply
        def lost(handler,status,document):
            if document.get('status')=='RESULT_PUBLISHED':
                handler.connection.shutdown(socket.SHUT_RDWR)
                handler.close_connection=True
                return
            reply(handler,status,document)
        with patch.object(ingest._DiscoveryHandler,'_reply',lost):
            with self.assertRaises(DiscoveryPublicationUnknown): self.publisher().publish(value)
        self.assertEqual(len(self.generations()),1)
        receipt=self.publisher().publish(self.outbox.load(value.digest))
        self.assertEqual(receipt.generation,1)
        self.assertEqual(len(self.generations()),1)

    def test_different_result_for_same_campaign_conflicts_without_overwrite(self):
        original=self.signed()
        self.publisher().publish(original)
        changed=replace(self.f.result,objects=(replace(self.f.result.objects[0],
            facts=(DiscoveryFact.known('name','different-observation'),)),))
        with self.assertRaises(DiscoveryPublicationUnknown): self.publisher().publish(self.signed(changed))
        self.assertEqual(len(self.generations()),1)
        self.assertEqual(self.generations()[0].result_digest,original.result.digest)


if __name__ == '__main__':
    unittest.main()
