"""Source signatures and outbox custody against the existing live trust fixtures."""
from __future__ import annotations

import json
import os
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provisioner.controlplane.discovery.model import DiscoveryPage, DiscoveryObject, DiscoveryFact, _json
from provisioner.controlplane.discovery.publication import (
    DiscoveryPublicationHeld, DiscoverySubmission, PrivateDiscoveryOutbox,
    PrivateFileDiscoveryResultSigner, collect_submission)
from provisioner.controlplane.discovery.trust import DiscoverySignature
from provisioner.controlplane.persistence.store import TenantContext
from tests.provisioning.controlplane import test_discovery_ingest as ingest_fixture


class PublicationFixture:
    """Reuse setup/custody assertions without inheriting or rerunning its test methods."""
    def configure(self):
        self.f = ingest_fixture.DiscoveryIngestTlsTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.verifier = self.f.service.signature_verifier
        self.environment = 'environment-01'
        signed = self.f.document()['campaignSignature']
        self.signature = DiscoverySignature(signed['keyId'], signed['signature'])
        self.key_path = self.f.root / 'result-signing.pem'
        self.key_path.write_bytes(self.f.collector_key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        self.key_path.chmod(0o600)
        self.signer = PrivateFileDiscoveryResultSigner(self.key_path, key_id='collector-key')
        self.outbox_root = self.f.root / 'outbox'
        self.outbox_root.mkdir(mode=0o700)
        self.context = TenantContext(self.f.campaign.scope.organization_id,
                                     self.f.campaign.scope.tenant_id)
        self.outbox = PrivateDiscoveryOutbox(self.outbox_root, self.context)
        self.clock = lambda: datetime.now(timezone.utc)

    def signed(self, result=None):
        return self.signer.sign(self.f.campaign, result or self.f.result,
            self.environment, self.signature, verifier=self.verifier, clock=self.clock)

    def revoke(self):
        self.f.witness_policy = replace(self.f.witness_policy, revision=2,
            witnesses=(replace(self.f.witness, revoked_at=self.clock()),))
        from provisioner.controlplane.discovery.witness import credential_witness_signing_bytes
        self.f.write_signed(self.f.witness_path, self.f.witness_policy,
                            self.f.witness_key, credential_witness_signing_bytes)

    def pages(self):
        return (DiscoveryPage(self.f.campaign.campaign_id, self.f.campaign.scope,
            1, None, None, self.f.result.captured_at, self.f.result.objects,
            terminal_completeness='PARTIAL', collection_errors=('VISIBLE_INVENTORY_ONLY',)),)


class DiscoveryPublicationTests(PublicationFixture, unittest.TestCase):
    def setUp(self):
        self.configure()

    def test_actual_ahv_https_collection_is_signed_without_relabeling_evidence(self):
        from tests.provisioning.discovery import test_ahv_https as native_fixture
        native = native_fixture.AhvHttpsTests()
        native.setUp()
        self.addCleanup(native.doCleanups)
        path = native.root / 'collector-result.pem'
        path.write_bytes(native.collector_key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        path.chmod(0o600)
        signer = PrivateFileDiscoveryResultSigner(path, key_id='collector')
        value = collect_submission(native.campaign, native.environment,
            native.verifier.campaign_signature, collect=native.transport.collect,
            signer=signer, verifier=native.verifier.verifier, clock=lambda:native.now)
        value.verify(native.verifier.verifier, native.now)
        self.assertEqual(len(native.calls), 2)
        self.assertEqual(len(value.result.objects), 2)
        self.assertEqual(value.result.completeness, 'PARTIAL')
        self.assertIn('VISIBLE_INVENTORY_ONLY', value.result.collection_errors)
        self.assertNotIn(native.token.encode(), value.body)
        self.assertEqual(value.campaign_signature, native.verifier.campaign_signature)

    def test_original_issuer_signature_and_result_digest_roundtrip(self):
        value = self.signed()
        self.assertEqual(value, DiscoverySubmission.from_bytes(value.body))
        self.assertEqual(value.result.digest, self.f.result.digest)
        self.assertEqual(json.loads(value.body)['campaignSignature'], self.f.document()['campaignSignature'])
        value.verify(self.verifier, self.clock())
        self.assertNotIn('PRIVATE KEY', value.body.decode())
        self.assertNotIn('PRIVATE KEY', repr(self.signer))

    def test_collect_preserves_partial_inventory_unknown_facts_and_capture_time(self):
        obj = replace(self.f.result.objects[0], facts=(DiscoveryFact.unknown('architecture','NOT_RETURNED'),))
        pages = (replace(self.pages()[0],objects=(obj,)),)
        value = collect_submission(self.f.campaign,self.environment,self.signature,
            collect=lambda:pages,signer=self.signer,verifier=self.verifier,clock=self.clock)
        self.assertEqual(value.result.completeness,'PARTIAL')
        self.assertEqual(value.result.collection_errors,('VISIBLE_INVENTORY_ONLY',))
        self.assertEqual(value.result.objects[0].facts[0].state,'UNKNOWN')
        self.assertEqual(value.result.captured_at,pages[0].collected_at)
        self.assertEqual(self.f.events,[])

    def test_expired_campaign_cannot_invoke_collector(self):
        collect = Mock(return_value=self.pages())
        with self.assertRaises(DiscoveryPublicationHeld):
            collect_submission(self.f.campaign,self.environment,self.signature,collect=collect,
                signer=self.signer,verifier=self.verifier,clock=lambda:self.f.campaign.expires_at)
        collect.assert_not_called()

    def test_revocation_during_collection_cannot_produce_signed_submission(self):
        def collect():
            self.revoke()
            return self.pages()
        with self.assertRaises(DiscoveryPublicationHeld):
            collect_submission(self.f.campaign,self.environment,self.signature,collect=collect,
                signer=self.signer,verifier=self.verifier,clock=self.clock)
        self.assertEqual(self.f.events,[])

    def test_native_failure_is_not_replaced_by_synthetic_success(self):
        collect = Mock(side_effect=RuntimeError('do-not-log-native-content'))
        with self.assertRaises(DiscoveryPublicationHeld) as raised:
            collect_submission(self.f.campaign,self.environment,self.signature,collect=collect,
                signer=self.signer,verifier=self.verifier,clock=self.clock)
        self.assertNotIn('do-not-log',str(raised.exception))

    def test_incomplete_page_chain_and_unbounded_iterable_are_rejected(self):
        invalid = ([*self.pages()], (), (replace(self.pages()[0],next_cursor='next',terminal_completeness=None),))
        for pages in invalid:
            with self.subTest(pages=type(pages)), self.assertRaises(DiscoveryPublicationHeld):
                collect_submission(self.f.campaign,self.environment,self.signature,collect=lambda:pages,
                    signer=self.signer,verifier=self.verifier,clock=self.clock)

    def test_issuer_or_unknown_key_cannot_sign_collector_results(self):
        for key in (self.f.issuer_key,Ed25519PrivateKey.generate()):
            self.key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
            with self.assertRaises(DiscoveryPublicationHeld): self.signed()

    def test_missing_public_symlink_fifo_and_oversized_signing_keys_fail_closed(self):
        self.key_path.chmod(0o644)
        with self.assertRaises(DiscoveryPublicationHeld): self.signed()
        self.key_path.chmod(0o600)
        saved = self.key_path.with_suffix('.saved')
        self.key_path.rename(saved)
        self.key_path.symlink_to(saved)
        with self.assertRaises(DiscoveryPublicationHeld): self.signed()
        self.key_path.unlink()
        os.mkfifo(self.key_path,0o600)
        with self.assertRaises(DiscoveryPublicationHeld): self.signed()
        self.key_path.unlink()
        with self.assertRaises(DiscoveryPublicationHeld): self.signed()
        self.key_path.write_bytes(b'x'*8193)
        self.key_path.chmod(0o600)
        with self.assertRaises(DiscoveryPublicationHeld): self.signed()

    def test_wire_bytes_reject_ambiguity_extra_fields_and_noncanonical_encoding(self):
        value = self.signed()
        for raw in (value.body+b' ',b'{"x":1,"x":2}', _json({**json.loads(value.body),'other':False}).encode()):
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                DiscoverySubmission.from_bytes(raw)

    def test_changed_body_digest_scope_or_signature_is_not_verified(self):
        value = self.signed()
        for field, item in (('environmentId','other-environment'),('resultSignature',
                           {'keyId':'collector-key','signature':self.signature.signature})):
            raw = _json({**json.loads(value.body),field:item}).encode()
            changed = DiscoverySubmission.from_bytes(raw)
            with self.subTest(field=field), self.assertRaises(ValueError):
                changed.verify(self.verifier,self.clock())
        object.__setattr__(value,'digest','f'*64)
        with self.assertRaises(ValueError): value.verify(self.verifier,self.clock())

    def test_fact_set_canonicalization_preserves_device_order_and_signed_digest(self):
        original = self.f.result.objects[0]
        facts = (DiscoveryFact.known('z_name', 'observed'),
                 DiscoveryFact.known('deviceOrder', ['disk-9', 'disk-1']))
        first = replace(self.f.result, objects=(replace(original, facts=facts),))
        reordered = replace(first, objects=(replace(original, facts=tuple(reversed(facts))),))
        value, again = self.signed(first), self.signed(reordered)
        self.assertEqual(value.body, again.body)
        self.assertEqual(value.result.digest, first.digest)
        self.assertEqual(next(f.value() for f in value.result.objects[0].facts
                              if f.name == 'deviceOrder'), ['disk-9', 'disk-1'])
        self.assertEqual(self.outbox.load(self.outbox.retain(value)), value)

    def test_signing_clock_regression_is_rejected(self):
        at = self.clock()
        ticks = iter((at, at-timedelta(microseconds=1)))
        with self.assertRaises(DiscoveryPublicationHeld):
            self.signer.sign(self.f.campaign,self.f.result,self.environment,self.signature,
                verifier=self.verifier,clock=lambda:next(ticks))

    def test_outbox_retains_identical_bytes_across_instances_and_repeated_writes(self):
        value = self.signed()
        self.assertEqual(self.outbox.retain(value),value.digest)
        self.assertEqual(self.outbox.retain(value),value.digest)
        restored = PrivateDiscoveryOutbox(self.outbox_root,self.context).load(value.digest)
        self.assertEqual(restored.body,value.body)
        self.assertEqual(list(self.outbox_root.rglob(value.digest))[0].stat().st_mode & 0o777,0o600)

    def test_outbox_rejects_corruption_fifo_symlink_and_permissions(self):
        value = self.signed()
        self.outbox.retain(value)
        path = next(self.outbox_root.rglob(value.digest))
        path.write_bytes(b'{}')
        with self.assertRaises(ValueError): self.outbox.load(value.digest)
        with self.assertRaises(ValueError): self.outbox.retain(value)
        path.unlink()
        os.mkfifo(path,0o600)
        with self.assertRaises(RuntimeError): self.outbox.load(value.digest)
        with self.assertRaises(RuntimeError): self.outbox.retain(value)
        path.unlink()
        path.symlink_to(self.key_path)
        with self.assertRaises(OSError): self.outbox.load(value.digest)
        self.outbox_root.chmod(0o755)
        with self.assertRaises(ValueError): self.outbox.retain(value)

    def test_outbox_rejects_cross_tenant_packets_and_path_traversal(self):
        foreign = PrivateDiscoveryOutbox(self.outbox_root,replace(self.context,tenant_id='other'))
        with self.assertRaises(ValueError): foreign.retain(self.signed())
        for digest in ('../key',None,'A'*64,'f'*63):
            with self.subTest(digest=digest), self.assertRaises(ValueError): self.outbox.load(digest)

    def test_reloading_retained_bytes_does_not_bypass_revocation(self):
        value = self.signed()
        self.outbox.retain(value)
        self.revoke()
        restored = self.outbox.load(value.digest)
        self.assertEqual(restored.body,value.body)
        with self.assertRaises(ValueError): restored.verify(self.verifier,self.clock())

    def test_signer_refuses_aggregate_larger_than_ingest_limit(self):
        campaign = replace(self.f.campaign,max_objects=600,max_pages=2,max_page_size=500)
        signature_doc = self.f.document(campaign=campaign)['campaignSignature']
        signature = DiscoverySignature(signature_doc['keyId'],signature_doc['signature'])
        base = self.f.result.objects[0]
        objects = tuple(DiscoveryObject(replace(base.identity,native_id=f'vm-{i}'),
            (DiscoveryFact.known('name','x'*2000),)) for i in range(600))
        result = replace(self.f.result,authorization_digest=campaign.digest(),objects=objects)
        with self.assertRaises(DiscoveryPublicationHeld):
            self.signer.sign(campaign,result,self.environment,signature,
                verifier=self.verifier,clock=self.clock)
        self.assertFalse(list(self.outbox_root.rglob('*')))


if __name__ == '__main__':
    unittest.main()
