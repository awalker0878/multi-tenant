"""Read-only local recovery inspection; no native or server status is inferred."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unittest
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

from provisioner.controlplane.discovery import collector_runtime, publication
from provisioner.controlplane.discovery.model import _json
from provisioner.controlplane.discovery.publication import (
    DiscoveryPublicationHeld, PrivateDiscoveryOutbox, stage_submission)
from provisioner.controlplane.persistence.store import TenantContext
from tests.provisioning.discovery.test_publication import PublicationFixture
from tests.provisioning.discovery.test_collector_runtime import encoded_key, write_json


class OutboxInspectionTests(PublicationFixture, unittest.TestCase):
    def setUp(self):
        self.configure()

    def inspect(self, **kw):
        return self.outbox.inspect(self.f.campaign, self.environment, self.signature,
                                  verifier=self.verifier, clock=kw.pop('clock', self.clock), **kw)

    def claim(self):
        return self.outbox._claim_collection(self.f.campaign, self.environment,
                                             self.signature, self.clock())

    def tree(self):
        # Ignore access times: inspection must not change entries, modes or file bytes.
        return {str(p.relative_to(self.outbox_root)):
                (p.stat().st_mode, p.read_bytes() if p.is_file() else None)
                for p in self.outbox_root.rglob('*')}

    def test_empty_outbox_is_reported_without_creating_directories(self):
        with patch.object(publication, '_atomic_new', side_effect=AssertionError('write')):
            result = self.inspect()
        self.assertEqual(result['status'], 'LOCAL_REFERENCE_ABSENT')
        self.assertIsNone(result['original'])
        self.assertIsNone(result['collectionIntent'])
        self.assertTrue(result['reconciliationRequired'])
        self.assertEqual(self.tree(), {})

    def test_unfinished_capture_preserves_intent_and_requires_reconciliation(self):
        path, raw = self.claim()
        before = self.tree()
        result = self.inspect()
        self.assertEqual(result['status'], 'COLLECTION_UNRESOLVED')
        self.assertEqual(result['collectionIntent']['recordDigest'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['collectionIntent']['attemptId'], json.loads(raw)['attemptId'])
        self.assertTrue(result['reconciliationRequired'])
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(self.tree(), before)

    def test_completed_original_keeps_digests_capture_time_and_unknown_server_status(self):
        self.claim()
        original = self.signed()
        self.outbox.retain(original)
        before = self.tree()
        result = self.inspect()
        self.assertEqual(result['status'], 'STAGED_ORIGINAL')
        self.assertEqual(result['original'], {
            'requestDigest': original.digest, 'resultDigest': original.result.digest,
            'capturedAt': original.result.captured_at.isoformat(),
            'completeness': original.result.completeness, 'objectCount': len(original.result.objects)})
        self.assertEqual(result['publicationStatus'], 'NOT_CHECKED')
        self.assertTrue(result['localCustodyOnly'])
        self.assertFalse(result['reconciliationRequired'])
        for field in ('collectionRequested', 'publicationAttempted', 'executionAuthorized'):
            self.assertIs(result[field], False)
        self.assertEqual(self.tree(), before)

    def test_original_without_new_intent_is_still_verified_not_rewritten(self):
        self.outbox.retain(self.signed())
        before = self.tree()
        result = self.inspect()
        self.assertEqual(result['status'], 'STAGED_ORIGINAL')
        self.assertIsNone(result['collectionIntent'])
        self.assertEqual(self.tree(), before)

    def test_loose_signed_blob_is_not_scanned_or_promoted(self):
        original = self.signed()
        self.outbox._store(original.digest).put(original.digest, original.body)
        before = self.tree()
        result = self.inspect()
        self.assertEqual(result['status'], 'LOCAL_REFERENCE_ABSENT')
        self.assertIsNone(result['original'])
        self.assertEqual(self.tree(), before)

    def test_missing_referenced_payload_is_a_hold_not_absent_or_repaired(self):
        original = self.signed()
        self.outbox.retain(original)
        path = self.outbox._store(original.digest).root / original.digest[:2] / original.digest
        path.unlink()
        before = self.tree()
        with self.assertRaises(DiscoveryPublicationHeld): self.inspect()
        self.assertEqual(self.tree(), before)

    def test_invalid_claim_fields_formats_times_and_authority_hold(self):
        path, raw = self.claim()
        initial = json.loads(raw)
        changes = {'format': 'hosting-discovery-collection-intent/0', 'campaignId': 'other',
            'environmentId': 'other', 'authorizationDigest': '0'*64,
            'campaignSignatureDigest': '0'*64, 'attemptId': True,
            'claimedAt': self.f.campaign.expires_at.isoformat(), 'executionAuthorized': True}
        for name, value in changes.items():
            with self.subTest(field=name):
                path.write_bytes(_json({**initial, name: value}).encode())
                with self.assertRaises(DiscoveryPublicationHeld): self.inspect()
        for value in (b'{}', raw+b' ', raw.replace(b'{', b'{"format":"bad",', 1), b'x'*1025):
            path.write_bytes(value)
            with self.assertRaises(DiscoveryPublicationHeld): self.inspect()

    def test_future_and_non_utc_claims_hold(self):
        path, raw = self.claim()
        initial = json.loads(raw)
        for at in ((self.clock()+timedelta(seconds=1)).isoformat(),
                   self.clock().replace(tzinfo=None).isoformat(),
                   self.f.campaign.issued_at.isoformat().replace('+00:00', '+01:00')):
            path.write_bytes(_json({**initial, 'claimedAt': at}).encode())
            with self.assertRaises(DiscoveryPublicationHeld): self.inspect()

    def test_public_symlink_fifo_and_directory_claims_hold_without_replacement(self):
        path, raw = self.claim()
        path.chmod(0o644)
        with self.assertRaises(DiscoveryPublicationHeld): self.inspect()
        path.unlink()
        saved = path.with_suffix('.saved'); saved.write_bytes(raw); saved.chmod(0o600)
        path.symlink_to(saved)
        with self.assertRaises(DiscoveryPublicationHeld): self.inspect()
        path.unlink(); os.mkfifo(path, 0o600)
        with self.assertRaises(DiscoveryPublicationHeld): self.inspect()
        path.unlink(); path.mkdir(mode=0o700)
        with self.assertRaises(DiscoveryPublicationHeld): self.inspect()

    def test_unsafe_namespace_and_shard_are_not_reported_as_absent(self):
        path, _ = self.claim()
        for parent in (path.parent, path.parent.parent):
            with self.subTest(parent=parent.name):
                parent.chmod(0o755)
                with self.assertRaises(DiscoveryPublicationHeld): self.inspect()
                parent.chmod(0o700)
        path.unlink(); shard = path.parent; saved = shard.with_name(shard.name+'-saved')
        shard.rename(saved); shard.symlink_to(saved, target_is_directory=True)
        with self.assertRaises(DiscoveryPublicationHeld): self.inspect()

    def test_corrupt_or_noncanonical_reference_holds(self):
        original = self.signed(); self.outbox.retain(original)
        path = self.outbox._campaign_path(self.f.campaign.campaign_id)
        initial = json.loads(path.read_bytes())
        for value in ('../other', 4, 'A'*64, None):
            path.write_bytes(_json({**initial, 'requestDigest': value}).encode())
            with self.assertRaises(DiscoveryPublicationHeld): self.inspect()
        path.write_bytes(_json(initial).encode()+b' ')
        with self.assertRaises(DiscoveryPublicationHeld): self.inspect()

    def test_tampered_result_with_self_consistent_hash_cannot_bypass_signature(self):
        original = self.signed()
        body = json.loads(original.body)
        body['resultSignature']['signature'] = self.signature.signature
        raw = _json(body).encode(); digest = hashlib.sha256(raw).hexdigest()
        self.outbox._store(digest).put(digest, raw)
        path = self.outbox._campaign_path(self.f.campaign.campaign_id)
        publication._atomic_new(path, _json({'format': 'hosting-discovery-outbox-campaign/1',
            'environmentId': self.environment, 'authorizationDigest': self.f.campaign.digest(),
            'requestDigest': digest}).encode())
        with self.assertRaises(DiscoveryPublicationHeld): self.inspect()

    def test_changed_campaign_environment_or_tenant_cannot_inspect_original(self):
        self.claim()
        with self.assertRaises((ValueError, DiscoveryPublicationHeld)):
            self.outbox.inspect(self.f.campaign, 'other-environment', self.signature,
                                verifier=self.verifier, clock=self.clock)
        other = PrivateDiscoveryOutbox(self.outbox_root, TenantContext('other-org','other-tenant'))
        with self.assertRaises(ValueError):
            other.inspect(self.f.campaign,self.environment,self.signature,
                          verifier=self.verifier,clock=self.clock)
        with self.assertRaises(DiscoveryPublicationHeld):
            self.outbox.inspect(replace(self.f.campaign, campaign_id='other'),self.environment,
                                self.signature,verifier=self.verifier,clock=self.clock)

    def test_expired_campaign_is_refused_before_local_record_reads(self):
        with patch.object(self.outbox, '_read_inspection_file') as read:
            with self.assertRaises(DiscoveryPublicationHeld):
                self.inspect(clock=lambda:self.f.campaign.expires_at)
        read.assert_not_called()

    def test_revoked_witness_holds_even_when_original_is_complete(self):
        self.outbox.retain(self.signed()); self.revoke()
        with self.assertRaises(DiscoveryPublicationHeld): self.inspect()

    def test_mid_inspection_revocation_is_rechecked(self):
        self.outbox.retain(self.signed())
        actual = self.outbox._read_inspection_file
        def read(path, maximum):
            result = actual(path, maximum)
            if maximum > 1024: self.revoke()
            return result
        with patch.object(self.outbox, '_read_inspection_file', side_effect=read):
            with self.assertRaises(DiscoveryPublicationHeld): self.inspect()

    def test_completion_between_snapshots_is_held_not_spliced_into_earlier_state(self):
        self.claim(); original = self.signed(); calls = 0
        actual = self.outbox._read_inspection_file
        def read(path, maximum):
            nonlocal calls
            value = actual(path, maximum); calls += 1
            if calls == 2: self.outbox.retain(original)
            return value
        with patch.object(self.outbox, '_read_inspection_file', side_effect=read):
            with self.assertRaises(DiscoveryPublicationHeld): self.inspect()
        self.assertEqual(self.inspect()['status'], 'STAGED_ORIGINAL')

    def test_claim_removed_between_snapshots_holds(self):
        path, _ = self.claim(); actual = self.outbox._read_inspection_file; calls = 0
        def read(selected, maximum):
            nonlocal calls
            value = actual(selected, maximum); calls += 1
            if calls == 2: path.unlink()
            return value
        with patch.object(self.outbox, '_read_inspection_file', side_effect=read):
            with self.assertRaises(DiscoveryPublicationHeld): self.inspect()

    def test_regressing_clock_during_inspection_holds(self):
        at = self.clock(); times = iter([at, at-timedelta(microseconds=1)])
        with self.assertRaises(DiscoveryPublicationHeld): self.inspect(clock=lambda:next(times))

    def test_storage_errors_do_not_escape_as_private_paths_or_native_details(self):
        with patch.object(self.outbox, '_read_inspection_file', side_effect=OSError('secret/path/token')):
            with self.assertRaises(DiscoveryPublicationHeld) as caught: self.inspect()
        self.assertNotIn('secret',str(caught.exception))

    def test_inspection_does_not_unlock_failed_capture(self):
        self.claim(); self.inspect(); calls=[]
        with self.assertRaises(DiscoveryPublicationHeld):
            stage_submission(self.f.campaign,self.environment,self.signature,collect=lambda:calls.append(1),
                signer=self.signer,verifier=self.verifier,outbox=self.outbox,clock=self.clock)
        self.assertEqual(calls,[])

    def config(self):
        doc = self.f.document()
        campaign_file = self.f.root/'inspect-campaign.json'
        write_json(campaign_file, {k:doc[k] for k in ('environmentId','campaign','campaignSignature')})
        config = {'format': 'hosting-discovery-collector/1', 'campaignFile': str(campaign_file),
            'outboxRoot': str(self.outbox_root),
            'trust': {'policyFile': str(self.f.root/'trust.json'),
                'rootKey': encoded_key(self.f.root_key), 'minimumRevision': 1},
            'witness': {'policyFile': str(self.f.witness_path),
                'rootKey': encoded_key(self.f.witness_key), 'minimumRevision': 1}}
        path = self.f.root/'inspect.json'; write_json(path,config)
        return path

    def test_runtime_inspects_without_native_or_signer_material_and_cannot_publish(self):
        original = self.signed(); self.outbox.retain(original)
        config = self.config(); self.key_path.unlink(); before = self.tree()
        with patch.object(collector_runtime,'create_native_collector',side_effect=AssertionError('native')), \
             patch.object(collector_runtime,'DiscoveryHttpsPublisher',side_effect=AssertionError('HTTP')):
            result = collector_runtime.execute(config,'inspect')
        self.assertEqual(result['status'],'STAGED_ORIGINAL')
        self.assertEqual(self.tree(),before)

    def test_fresh_command_reads_unresolved_claim_without_changing_any_records(self):
        self.claim(); config=self.config(); before=self.tree()
        run=subprocess.run([sys.executable,'-m','provisioner.controlplane.discovery.collector_runtime',
            'inspect','--config',str(config)],capture_output=True,text=True,timeout=15)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        result=json.loads(run.stdout)
        self.assertEqual(result['status'],'COLLECTION_UNRESOLVED')
        self.assertTrue(result['reconciliationRequired'])
        self.assertNotIn(str(self.outbox_root),run.stdout+run.stderr)
        self.assertEqual(self.tree(),before)

    def test_fresh_command_corruption_is_a_generic_hold_not_an_empty_report(self):
        path,_=self.claim(); path.write_bytes(b'secret-corrupt-claim'); config=self.config()
        run=subprocess.run([sys.executable,'-m','provisioner.controlplane.discovery.collector_runtime',
            'inspect','--config',str(config)],capture_output=True,text=True,timeout=15)
        self.assertEqual(run.returncode,2)
        self.assertEqual(json.loads(run.stdout)['status'],'HELD')
        self.assertNotIn('secret',run.stdout+run.stderr)
        self.assertEqual(path.read_bytes(),b'secret-corrupt-claim')


if __name__ == '__main__':
    unittest.main()
