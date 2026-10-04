"""Campaign-addressable local custody must not replace original observations.

Real signed authority and create-only files are used. Local custody does not
prove global uniqueness, independent retention, native coverage or SQL commits.
"""
from __future__ import annotations

import hashlib
import json
import socket
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from threading import Barrier
from unittest.mock import Mock, patch

from provisioner.controlplane.discovery import ingest, publication
from provisioner.controlplane.discovery.model import DiscoveryFact, _json
from provisioner.controlplane.discovery.publication import DiscoveryPublicationHeld, PrivateDiscoveryOutbox
from provisioner.controlplane.discovery.publication_https import (
    DiscoveryHttpsPublisher, DiscoveryPublicationUnknown, DiscoveryPublishTarget)
from tests.provisioning.discovery.test_publication import PublicationFixture


class DiscoveryRecoveryTests(PublicationFixture, unittest.TestCase):
    def setUp(self):
        self.configure()

    def changed(self):
        obj = replace(self.f.result.objects[0], facts=(DiscoveryFact.known('name', 'changed-observation'),))
        return self.signed(replace(self.f.result, objects=(obj,)))

    def stage(self, **changes):
        args = dict(collect=Mock(return_value=self.pages()), signer=self.signer,
                    verifier=self.verifier, outbox=self.outbox, clock=self.clock)
        args.update(changes)
        return publication.stage_submission(self.f.campaign, self.environment, self.signature, **args)

    def binding_path(self):
        return next(self.outbox_root.rglob('*.campaign'))

    def test_two_signed_results_cannot_bind_one_campaign(self):
        first, second = self.signed(), self.changed()
        self.assertNotEqual(first.digest, second.digest)
        self.outbox.retain(first)
        with self.assertRaises(ValueError):
            self.outbox.retain(second)
        self.assertEqual(self.outbox.load(first.digest), first)

    def test_new_instance_locates_original_without_known_request_digest(self):
        original = self.signed()
        self.outbox.retain(original)
        restarted = PrivateDiscoveryOutbox(self.outbox_root, self.context)
        self.assertEqual(restarted.for_campaign(self.f.campaign, self.environment), original)
        self.assertEqual(self.binding_path().stat().st_mode & 0o777, 0o600)

    def test_missing_binding_is_not_a_successful_publication(self):
        self.assertIsNone(self.outbox.for_campaign(self.f.campaign, self.environment))
        self.assertEqual(self.f.events, [])

    def test_stage_reuses_original_without_native_reads_or_signing(self):
        original = self.stage()
        self.key_path.unlink()  # A resume needs the original signature, not a new private key.
        collect = Mock(side_effect=AssertionError('must not recollect'))
        with patch.object(self.signer, 'sign', side_effect=AssertionError('must not resign')):
            restored = self.stage(collect=collect,
                outbox=PrivateDiscoveryOutbox(self.outbox_root, self.context))
        self.assertEqual(restored.body, original.body)
        self.assertEqual(restored.result.captured_at, original.result.captured_at)
        collect.assert_not_called()
        self.assertEqual(self.f.events, [])

    def test_staged_result_is_retained_before_return(self):
        original = self.stage()
        self.assertEqual(self.outbox.load(original.digest), original)
        self.assertEqual(self.outbox.for_campaign(self.f.campaign, self.environment), original)
        self.assertEqual(original.result.completeness, 'PARTIAL')
        self.assertIn('VISIBLE_INVENTORY_ONLY', original.result.collection_errors)

    def test_expired_or_revoked_resume_is_held_without_recollection(self):
        self.stage()
        collect = Mock(return_value=self.pages())
        with self.assertRaises(DiscoveryPublicationHeld):
            self.stage(collect=collect, clock=lambda: self.f.campaign.expires_at)
        self.revoke()
        with self.assertRaises(DiscoveryPublicationHeld):
            self.stage(collect=collect)
        collect.assert_not_called()

    def test_reused_campaign_id_cannot_change_environment_or_authorization(self):
        original = self.signed()
        self.outbox.retain(original)
        with self.assertRaises(ValueError):
            self.outbox.for_campaign(self.f.campaign, 'other-environment')
        changed = replace(self.f.campaign, max_objects=self.f.campaign.max_objects+1)
        with self.assertRaises(ValueError):
            self.outbox.for_campaign(changed, self.environment)
        document = self.f.document(campaign=changed)['campaignSignature']
        signature = publication.DiscoverySignature(document['keyId'], document['signature'])
        collect = Mock(return_value=self.pages())
        with self.assertRaises(DiscoveryPublicationHeld):
            publication.stage_submission(changed, self.environment, signature, collect=collect,
                signer=self.signer, verifier=self.verifier, outbox=self.outbox, clock=self.clock)
        collect.assert_not_called()

    def test_foreign_tenant_is_rejected_before_collection(self):
        collect = Mock(return_value=self.pages())
        foreign = PrivateDiscoveryOutbox(self.outbox_root, replace(self.context, tenant_id='foreign'))
        with self.assertRaises(DiscoveryPublicationHeld):
            self.stage(collect=collect, outbox=foreign)
        collect.assert_not_called()

    def test_missing_referenced_payload_cannot_be_recreated_from_caller_bytes(self):
        original = self.signed()
        self.outbox.retain(original)
        next(self.outbox_root.rglob(original.digest)).unlink()
        with self.assertRaises((ValueError, OSError)):
            self.outbox.retain(original)
        collect = Mock(return_value=self.pages())
        with self.assertRaises(DiscoveryPublicationHeld):
            self.stage(collect=collect)
        collect.assert_not_called()

    def test_corrupt_noncanonical_or_extra_binding_fields_do_not_trigger_rescan(self):
        original = self.stage()
        path = self.binding_path()
        raw = path.read_bytes()
        payload = json.loads(raw)
        invalid = (b'{}', raw+b' ', b'{"format":1,"format":2}',
                   _json({**payload, 'extra': False}).encode(),
                   _json({**payload, 'requestDigest': 'f'*64}).encode(),
                   _json({**payload, 'environmentId': 'foreign'}).encode())
        for content in invalid:
            with self.subTest(content=content[:30]):
                path.write_bytes(content)
                collect = Mock(return_value=self.pages())
                with self.assertRaises(DiscoveryPublicationHeld):
                    self.stage(collect=collect)
                collect.assert_not_called()
        path.write_bytes(raw)
        self.assertEqual(self.outbox.for_campaign(self.f.campaign, self.environment), original)

    def test_binding_fifo_symlink_permissions_and_oversize_are_held(self):
        self.stage()
        path = self.binding_path()
        original = path.read_bytes()
        for kind in ('fifo', 'symlink', 'public', 'oversize'):
            with self.subTest(kind=kind):
                path.unlink()
                if kind == 'fifo':
                    os.mkfifo(path, 0o600)
                elif kind == 'symlink':
                    path.symlink_to(self.key_path)
                else:
                    path.write_bytes(original if kind == 'public' else b' '*1025)
                    path.chmod(0o644 if kind == 'public' else 0o600)
                with self.assertRaises((ValueError, OSError, RuntimeError)):
                    self.outbox.for_campaign(self.f.campaign, self.environment)
        path.unlink()

    def test_payload_is_durable_before_campaign_binding_is_published(self):
        original = self.signed()
        atomic_new = publication._atomic_new
        def inspect(path, data):
            self.assertEqual(self.outbox.load(original.digest), original)
            return atomic_new(path, data)
        with patch.object(publication, '_atomic_new', side_effect=inspect) as write:
            self.outbox.retain(original)
        self.assertTrue(write.called)

    def test_failed_binding_write_cannot_return_staged_success(self):
        collect = Mock(return_value=self.pages())
        with patch.object(publication, '_atomic_new', side_effect=OSError('private-storage-failed')):
            with self.assertRaises(DiscoveryPublicationHeld) as raised:
                self.stage(collect=collect)
        self.assertNotIn('private-storage-failed', str(raised.exception))
        self.assertEqual(self.f.events, [])
        self.assertIsNone(self.outbox.for_campaign(self.f.campaign, self.environment))

    def test_revocation_during_storage_keeps_original_but_refuses_staged_success(self):
        retain = self.outbox.retain
        def revoke_after_write(value):
            digest = retain(value)
            self.revoke()
            return digest
        with patch.object(self.outbox, 'retain', side_effect=revoke_after_write):
            with self.assertRaises(DiscoveryPublicationHeld):
                self.stage()
        self.assertIsNotNone(self.outbox.for_campaign(self.f.campaign, self.environment))
        collect = Mock(return_value=self.pages())
        with self.assertRaises(DiscoveryPublicationHeld):
            self.stage(collect=collect)
        collect.assert_not_called()

    def test_two_instances_racing_preserve_exactly_one_submission(self):
        first, second = self.signed(), self.changed()
        gate = Barrier(2)
        def write(value):
            outbox = PrivateDiscoveryOutbox(self.outbox_root, self.context)
            gate.wait(timeout=5)
            try:
                return outbox.retain(value)
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(write, (first, second)))
        self.assertEqual(sum(value is not None for value in results), 1)
        winner = self.outbox.for_campaign(self.f.campaign, self.environment)
        self.assertIn(winner, (first, second))
        self.assertIn(winner.digest, results)
        loser = second if winner == first else first
        with self.assertRaises(ValueError):
            PrivateDiscoveryOutbox(self.outbox_root, self.context).retain(loser)

    def test_same_original_can_be_retained_concurrently(self):
        original = self.signed()
        gate = Barrier(2)
        def write(_):
            outbox = PrivateDiscoveryOutbox(self.outbox_root, self.context)
            gate.wait(timeout=5)
            return outbox.retain(original)
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(write, range(2))), [original.digest]*2)
        self.assertEqual(self.outbox.for_campaign(self.f.campaign, self.environment), original)

    def test_post_lookup_clock_regression_does_not_revalidate_original(self):
        self.stage()
        at = self.clock()
        ticks = iter((at, at-timedelta(microseconds=1)))
        collect = Mock(return_value=self.pages())
        with self.assertRaises(DiscoveryPublicationHeld):
            self.stage(collect=collect, clock=lambda: next(ticks))
        collect.assert_not_called()

    def test_invalid_campaign_keys_never_become_paths(self):
        for value in (None, '../private', '', 'x'*129):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.outbox.for_campaign(value, self.environment)


class DiscoveryRecoveryTlsTests(PublicationFixture, unittest.TestCase):
    def setUp(self):
        self.configure()
        root = self.f.pki.root
        (root/'collector.key').chmod(0o600)
        self.target = DiscoveryPublishTarget(
            origin=f'https://localhost:{self.f.server.server_port}', connect_ip='127.0.0.1',
            trust_domain='workers.example', ca_bundle=root/'ca.pem',
            ca_digest=hashlib.sha256((root/'ca.pem').read_bytes()).hexdigest(),
            crl_bundle=root/'crl.pem', crl_digest=hashlib.sha256((root/'crl.pem').read_bytes()).hexdigest(),
            client_certificate=root/'collector.pem',
            certificate_digest=hashlib.sha256((root/'collector.pem').read_bytes()).hexdigest(),
            client_key=root/'collector.key')

    def stage(self, outbox, collect):
        return publication.stage_submission(self.f.campaign, self.environment, self.signature,
            collect=collect, signer=self.signer, verifier=self.verifier,
            outbox=outbox, clock=self.clock)

    def publisher(self, outbox=None):
        return DiscoveryHttpsPublisher(self.target, verifier=self.verifier,
            outbox=outbox or self.outbox, clock=self.clock)

    def lose_ack(self, phase):
        original = self.stage(self.outbox, self.pages)
        reply = ingest._DiscoveryHandler._reply
        def lose(handler, status, document):
            if document.get('status') == ('CAMPAIGN_REGISTERED' if phase == 'CAMPAIGN' else 'RESULT_PUBLISHED'):
                handler.connection.shutdown(socket.SHUT_RDWR)
                handler.close_connection = True
                return
            reply(handler, status, document)
        with patch.object(ingest._DiscoveryHandler, '_reply', lose):
            with self.assertRaises(DiscoveryPublicationUnknown) as raised:
                self.publisher().publish(original)
        self.assertEqual(raised.exception.phase, phase)
        self.assertEqual(raised.exception.request_digest, original.digest)
        return original

    def resume(self, original):
        # This new process-equivalent object knows the campaign, not the content
        # address. It must not contact the source or reread the signing private key.
        restarted = PrivateDiscoveryOutbox(self.outbox_root, self.context)
        self.key_path.unlink()
        collect = Mock(side_effect=AssertionError('must not recollect after uncertain delivery'))
        restored = self.stage(restarted, collect)
        self.assertEqual(restored.body, original.body)
        receipt = self.publisher(restarted).publish(restored)
        self.assertEqual(self.f.retained_requests[-1], original.body)
        self.assertEqual(receipt.request_digest, original.digest)
        self.assertIs(receipt.execution_authorized, False)
        collect.assert_not_called()

    def test_lost_result_ack_restarts_from_campaign_and_original_bytes(self):
        original = self.lose_ack('RESULT')
        self.assertEqual(len([e for e in self.f.events if e[0] == 'result-commit']), 1)
        self.resume(original)
        # The recording SQL fixture sees two attempts. Actual generation
        # idempotency remains covered by the separate PostgreSQL integration gate.
        self.assertEqual(len([e for e in self.f.events if e[0] == 'result-commit']), 2)

    def test_lost_campaign_ack_does_not_send_result_until_explicit_resume(self):
        original = self.lose_ack('CAMPAIGN')
        self.assertNotIn('result-commit', [e[0] for e in self.f.events])
        self.resume(original)
        self.assertEqual(len([e for e in self.f.events if e[0] == 'result-commit']), 1)

    def test_competing_valid_submission_is_held_before_any_post(self):
        original = self.signed()
        self.outbox.retain(original)
        changed = self.signed(replace(self.f.result,
            captured_at=self.f.result.captured_at-timedelta(microseconds=1)))
        self.assertNotEqual(changed.digest, original.digest)
        publisher = self.publisher()
        with patch.object(publisher, '_post') as post:
            with self.assertRaises(DiscoveryPublicationHeld) as raised:
                publisher.publish(changed)
        self.assertNotIsInstance(raised.exception, DiscoveryPublicationUnknown)
        post.assert_not_called()
        self.assertEqual(self.f.events, [])

    def test_reference_storage_failure_prevents_even_campaign_registration(self):
        original = self.signed()
        with patch.object(publication, '_atomic_new', side_effect=OSError('disk failure')):
            with self.assertRaises(DiscoveryPublicationHeld) as raised:
                self.publisher().publish(original)
        self.assertNotIsInstance(raised.exception, DiscoveryPublicationUnknown)
        self.assertEqual(self.f.events, [])

    def test_revocation_after_lost_ack_refuses_resume_and_keeps_original(self):
        original = self.lose_ack('RESULT')
        events = list(self.f.events)
        self.revoke()
        collect = Mock(return_value=self.pages())
        restarted = PrivateDiscoveryOutbox(self.outbox_root, self.context)
        with self.assertRaises(DiscoveryPublicationHeld):
            self.stage(restarted, collect)
        collect.assert_not_called()
        self.assertEqual(self.f.events, events)
        self.assertEqual(restarted.for_campaign(self.f.campaign, self.environment).body, original.body)


if __name__ == '__main__':
    unittest.main()
