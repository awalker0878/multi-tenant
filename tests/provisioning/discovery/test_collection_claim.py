"""Shared-outbox collection admission with real signatures and durable files.

These tests cover local cooperative custody, not a global scheduler or a native
platform fence. Child processes use synthetic page data, not production endpoints.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from threading import Event
from unittest.mock import Mock, patch

from provisioner.controlplane.discovery import publication
from provisioner.controlplane.discovery.publication import (
    DiscoveryPublicationHeld, PrivateDiscoveryOutbox)
from tests.provisioning.discovery.test_publication import PublicationFixture
from tests.provisioning.discovery.test_collector_runtime import RuntimeFixture


class CollectionClaimTests(PublicationFixture, unittest.TestCase):
    def setUp(self):
        self.configure()

    def stage(self, **overrides):
        args = dict(collect=Mock(return_value=self.pages()), signer=self.signer,
                    verifier=self.verifier, outbox=self.outbox, clock=self.clock)
        args.update(overrides)
        return publication.stage_submission(self.f.campaign, self.environment,
                                            self.signature, **args)

    def test_independent_outbox_instances_cannot_both_enter_collection(self):
        started, release = Event(), Event()
        calls = []
        def first_collect():
            calls.append('first')
            started.set()
            if not release.wait(5):
                raise RuntimeError('fixture release deadline')
            return self.pages()
        def second_collect():
            calls.append('second')
            return self.pages()
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.stage, collect=first_collect)
            try:
                self.assertTrue(started.wait(3))
                second = pool.submit(self.stage, collect=second_collect,
                    outbox=PrivateDiscoveryOutbox(self.outbox_root, self.context))
                with self.assertRaises(DiscoveryPublicationHeld):
                    second.result(timeout=3)
            finally:
                release.set()
                try:
                    first.result(timeout=3)
                except DiscoveryPublicationHeld:
                    pass
        self.assertEqual(calls, ['first'])

    def intent_path(self):
        paths = list(self.outbox_root.rglob('*.collection'))
        self.assertEqual(len(paths), 1)
        return paths[0]

    def assert_retry_held(self):
        collect = Mock(return_value=self.pages())
        with self.assertRaises(DiscoveryPublicationHeld):
            self.stage(collect=collect,
                outbox=PrivateDiscoveryOutbox(self.outbox_root, self.context))
        collect.assert_not_called()

    def test_claim_is_private_durable_and_precedes_native_callback(self):
        def collect():
            path = self.intent_path()
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            record = json.loads(path.read_bytes())
            self.assertEqual(record['format'], 'hosting-discovery-collection-intent/1')
            self.assertEqual(record['campaignId'], self.f.campaign.campaign_id)
            self.assertEqual(record['environmentId'], self.environment)
            self.assertEqual(record['authorizationDigest'], self.f.campaign.digest())
            self.assertIs(record['executionAuthorized'], False)
            self.assertNotIn('signature', record)
            self.assertNotIn('native', record)
            self.assertNotIn('PRIVATE KEY', path.read_text())
            self.assertEqual(len(record['attemptId']), 32)
            self.assertLess(len(path.read_bytes()), 1024)
            self.assertIsNone(self.outbox.for_campaign(self.f.campaign, self.environment))
            return self.pages()
        self.stage(collect=collect)
        self.assertTrue(self.intent_path().exists())

    def test_complete_original_resumes_despite_existing_claim_without_new_signing(self):
        first = self.stage()
        path = self.intent_path()
        raw = path.read_bytes()
        self.key_path.unlink()
        collect = Mock(side_effect=AssertionError('must not collect twice'))
        with patch.object(self.signer, 'sign', side_effect=AssertionError('must not resign')):
            second = self.stage(collect=collect)
        self.assertEqual(second.body, first.body)
        self.assertEqual(path.read_bytes(), raw)
        collect.assert_not_called()

    def test_historical_original_without_claim_still_resumes(self):
        first = self.signed()
        self.outbox.retain(first)
        self.assertEqual(list(self.outbox_root.rglob('*.collection')), [])
        collect = Mock(side_effect=AssertionError('must not rescan historical original'))
        self.assertEqual(self.stage(collect=collect), first)
        self.assertEqual(list(self.outbox_root.rglob('*.collection')), [])
        collect.assert_not_called()

    def test_native_failure_does_not_release_claim(self):
        with self.assertRaises(DiscoveryPublicationHeld) as raised:
            self.stage(collect=Mock(side_effect=RuntimeError('private-native-error')))
        self.assertNotIn('private-native-error', str(raised.exception))
        self.assertTrue(self.intent_path().exists())
        self.assert_retry_held()

    def test_keyboard_interrupt_does_not_release_claim(self):
        with self.assertRaises(KeyboardInterrupt):
            self.stage(collect=Mock(side_effect=KeyboardInterrupt()))
        self.assertTrue(self.intent_path().exists())
        self.assert_retry_held()

    def test_signing_failure_does_not_recollect_on_retry(self):
        self.key_path.unlink()
        collect = Mock(return_value=self.pages())
        with self.assertRaises(DiscoveryPublicationHeld):
            self.stage(collect=collect)
        collect.assert_called_once()
        self.assertTrue(self.intent_path().exists())
        self.assert_retry_held()

    def test_failed_original_retention_leaves_an_unresolved_claim(self):
        with patch.object(self.outbox, 'retain', side_effect=OSError('storage unavailable')):
            with self.assertRaises(DiscoveryPublicationHeld):
                self.stage()
        self.assert_retry_held()

    def test_claim_storage_failure_prevents_native_collection(self):
        collect = Mock(return_value=self.pages())
        with patch.object(publication, '_atomic_new', side_effect=OSError('sync failed')):
            with self.assertRaises(DiscoveryPublicationHeld):
                self.stage(collect=collect)
        collect.assert_not_called()

    def test_post_link_durability_failure_leaves_claim_but_never_collects(self):
        collect = Mock(return_value=self.pages())
        atomic = publication._atomic_new
        def sync_failure(path, content):
            atomic(path, content)
            raise OSError('directory sync response unknown')
        with patch.object(publication, '_atomic_new', side_effect=sync_failure):
            with self.assertRaises(DiscoveryPublicationHeld):
                self.stage(collect=collect)
        collect.assert_not_called()
        self.assert_retry_held()

    def test_current_authority_is_rechecked_after_claim_and_before_native_read(self):
        acquire = self.outbox._claim_collection
        def revoked(*args):
            claim = acquire(*args)
            self.revoke()
            return claim
        collect = Mock(return_value=self.pages())
        with patch.object(self.outbox, '_claim_collection', side_effect=revoked):
            with self.assertRaises(DiscoveryPublicationHeld):
                self.stage(collect=collect)
        collect.assert_not_called()
        self.assertTrue(self.intent_path().exists())

    def test_unauthorized_campaign_creates_no_claim_and_never_collects(self):
        self.revoke()
        collect = Mock(return_value=self.pages())
        with self.assertRaises(DiscoveryPublicationHeld):
            self.stage(collect=collect)
        collect.assert_not_called()
        self.assertEqual(list(self.outbox_root.rglob('*.collection')), [])

    def test_changed_claim_after_collection_cannot_publish_an_original(self):
        def collect():
            self.intent_path().write_bytes(b'{}')
            return self.pages()
        with self.assertRaises(DiscoveryPublicationHeld):
            self.stage(collect=collect)
        self.assertIsNone(self.outbox.for_campaign(self.f.campaign, self.environment))
        self.assert_retry_held()

    def test_reused_campaign_id_cannot_select_another_claim_by_changing_authority(self):
        claim = self.outbox._claim_collection(self.f.campaign, self.environment,
                                             self.signature, self.clock())
        changed = replace(self.f.campaign, max_objects=self.f.campaign.max_objects + 1)
        document = self.f.document(campaign=changed)
        signature = publication.DiscoverySignature(**{
            'key_id': document['campaignSignature']['keyId'],
            'signature': document['campaignSignature']['signature']})
        collect = Mock(return_value=self.pages())
        with self.assertRaises(DiscoveryPublicationHeld):
            publication.stage_submission(changed, self.environment, signature, collect=collect,
                signer=self.signer, verifier=self.verifier, outbox=self.outbox, clock=self.clock)
        collect.assert_not_called()
        self.assertEqual(claim[0].read_bytes(), claim[1])

    def test_conflicting_environment_does_not_replace_claim(self):
        claim = self.outbox._claim_collection(self.f.campaign, self.environment,
                                             self.signature, self.clock())
        with self.assertRaises(DiscoveryPublicationHeld):
            self.outbox._claim_collection(self.f.campaign, 'other-environment',
                                          self.signature, self.clock())
        self.assertEqual(claim[0].read_bytes(), claim[1])

    def test_foreign_tenant_cannot_claim_the_campaign(self):
        foreign = PrivateDiscoveryOutbox(self.outbox_root, replace(self.context, tenant_id='other'))
        collect = Mock(return_value=self.pages())
        with self.assertRaises(DiscoveryPublicationHeld):
            self.stage(outbox=foreign, collect=collect)
        collect.assert_not_called()
        self.assertEqual(list(self.outbox_root.rglob('*.collection')), [])

    def test_existing_invalid_or_unsafe_intent_blocks_without_reading_it(self):
        path = self.outbox._campaign_path(self.f.campaign.campaign_id).with_suffix('.collection')
        for kind in ('corrupt', 'public', 'fifo', 'symlink', 'directory', 'oversize'):
            with self.subTest(kind=kind):
                if kind == 'fifo':
                    os.mkfifo(path, 0o600)
                elif kind == 'symlink':
                    path.symlink_to(self.key_path)
                elif kind == 'directory':
                    path.mkdir(mode=0o700)
                else:
                    path.write_bytes(b'x' * (1025 if kind == 'oversize' else 1))
                    path.chmod(0o644 if kind == 'public' else 0o600)
                try:
                    self.assert_retry_held()
                finally:
                    if kind == 'directory':
                        path.rmdir()
                    else:
                        path.unlink()

    def test_elapsed_time_cannot_expire_or_steal_an_incomplete_claim(self):
        claim = self.outbox._claim_collection(self.f.campaign, self.environment,
                                             self.signature, self.clock())
        collect = Mock(return_value=self.pages())
        with self.assertRaises(DiscoveryPublicationHeld):
            self.stage(collect=collect, clock=lambda: self.f.now + timedelta(minutes=1))
        collect.assert_not_called()
        self.assertEqual(claim[0].read_bytes(), claim[1])

    def test_separate_outbox_roots_are_not_misrepresented_as_globally_coordinated(self):
        other_root = self.f.root / 'other-outbox'
        other_root.mkdir(mode=0o700)
        other = PrivateDiscoveryOutbox(other_root, self.context)
        first = self.outbox._claim_collection(self.f.campaign, self.environment,
                                              self.signature, self.clock())
        second = other._claim_collection(self.f.campaign, self.environment,
                                          self.signature, self.clock())
        self.assertNotEqual(first[0], second[0])
        self.assertNotEqual(first[1], second[1])

    def worker(self, mode):
        from provisioner.controlplane.discovery.ingest import campaign_document, result_document
        document = {'campaign': campaign_document(self.f.campaign),
            'result': result_document(self.f.result),
            'environmentId': self.environment,
            'signature': publication.DiscoverySubmission.signature_document(self.signature),
            'rootKey': self.f.root_key.public_key().public_bytes_raw().hex(),
            'witnessKey': self.f.witness_key.public_key().public_bytes_raw().hex(),
            'root': str(self.f.root), 'outbox': str(self.outbox_root)}
        inputs = self.f.root / 'child-input.json'
        inputs.write_text(json.dumps(document))
        inputs.chmod(0o600)
        process = subprocess.Popen([sys.executable, '-c', _CHILD, str(inputs), mode],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.close_worker, process)
        return process

    @staticmethod
    def close_worker(process):
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)

    def test_separate_processes_share_first_capture_exclusion_and_original_resume(self):
        import select
        first = self.worker('wait')
        self.assertTrue(select.select([first.stdout], [], [], 5)[0], 'worker startup timeout')
        self.assertEqual(first.stdout.readline().strip(), 'COLLECTING')
        second = self.worker('quick')
        second_out, second_err = second.communicate(timeout=5)
        self.assertEqual(second.returncode, 2, second_err)
        self.assertEqual(second_out.strip(), 'HELD')
        output, errors = first.communicate(input='continue\n', timeout=5)
        self.assertEqual(first.returncode, 0, errors)
        self.assertEqual(output.strip(), 'STAGED')
        self.key_path.unlink()
        resumed = self.worker('quick')
        output, errors = resumed.communicate(timeout=5)
        self.assertEqual(resumed.returncode, 0, errors)
        self.assertEqual(output.strip(), 'STAGED')

    def test_abrupt_process_exit_after_claim_prevents_automatic_recapture(self):
        crashed = self.worker('crash')
        output, errors = crashed.communicate(timeout=5)
        self.assertEqual(crashed.returncode, 23, errors)
        self.assertEqual(output.strip(), 'COLLECTING')
        self.assertTrue(self.intent_path().exists())
        self.assertIsNone(self.outbox.for_campaign(self.f.campaign, self.environment))
        retry = self.worker('quick')
        output, errors = retry.communicate(timeout=5)
        self.assertEqual(retry.returncode, 2, errors)
        self.assertEqual(output.strip(), 'HELD')


_CHILD = r'''
import json, os, select, sys
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from provisioner.controlplane.discovery.ingest import _campaign, _result, _signature
from provisioner.controlplane.discovery.model import DiscoveryPage
from provisioner.controlplane.discovery.publication import (
    DiscoveryPublicationHeld, PrivateDiscoveryOutbox, PrivateFileDiscoveryResultSigner, stage_submission)
from provisioner.controlplane.discovery.trust import SignedDiscoveryIngestVerifier, SignedFileDiscoveryTrustStore
from provisioner.controlplane.discovery.witness import SignedFileDiscoveryCredentialAuthority
from provisioner.controlplane.persistence.store import TenantContext
v = json.loads(Path(sys.argv[1]).read_text())
root = Path(v['root']); campaign = _campaign(v['campaign']); result = _result(v['result'])
verifier = SignedDiscoveryIngestVerifier(
    SignedFileDiscoveryTrustStore(root/'trust.json', authority_public_key=
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(v['rootKey'])), minimum_revision=1),
    SignedFileDiscoveryCredentialAuthority(root/'witness.json', authority_public_key=
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(v['witnessKey'])), minimum_revision=1))
outbox = PrivateDiscoveryOutbox(v['outbox'], TenantContext(campaign.scope.organization_id, campaign.scope.tenant_id))
def collect():
    print('COLLECTING', flush=True)
    if sys.argv[2] == 'crash':
        os._exit(23)
    if sys.argv[2] == 'wait':
        if not select.select([sys.stdin], [], [], 5)[0]:
            raise RuntimeError('fixture release timeout')
        sys.stdin.readline()
    return (DiscoveryPage(campaign.campaign_id, campaign.scope, 1, None, None,
        result.captured_at, result.objects, terminal_completeness='PARTIAL',
        collection_errors=('VISIBLE_INVENTORY_ONLY',)),)
try:
    stage_submission(campaign, v['environmentId'], _signature(v['signature']), collect=collect,
        signer=PrivateFileDiscoveryResultSigner(root/'result-signing.pem', key_id='collector-key'),
        verifier=verifier, outbox=outbox, clock=lambda:datetime.now(timezone.utc))
except DiscoveryPublicationHeld:
    print('HELD'); sys.exit(2)
print('STAGED')
'''


class InstalledCollectionClaimTests(RuntimeFixture, unittest.TestCase):
    """Fresh installed-command processes use the actual local AHV HTTPS fixture."""
    def setUp(self):
        self.configure()
        self.release = Event()
        self.addCleanup(self.release.set)
        self.native.on_get = lambda: self.release.wait(5)

    def start_command(self):
        process = subprocess.Popen([sys.executable, '-m',
            'provisioner.controlplane.discovery.collector_runtime',
            'stage', '--config', str(self.config_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(CollectionClaimTests.close_worker, process)
        return process

    def test_two_command_processes_send_only_one_native_page_chain(self):
        first = self.start_command()
        try:
            self.assertTrue(self.native.request_started.wait(5))
            second = self.command('stage')
            self.assertEqual(second.returncode, 2, second.stderr)
            self.assertEqual(json.loads(second.stdout)['status'], 'HELD')
            self.assertEqual(len(self.native.calls), 1)
        finally:
            self.release.set()
        output, errors = first.communicate(timeout=5)
        self.assertEqual(first.returncode, 0, errors)
        original = json.loads(output)
        self.assertEqual(original['status'], 'STAGED')
        self.assertEqual(len(self.native.calls), 2)
        self.signer_path.unlink()
        resumed = self.command('stage')
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertEqual(json.loads(resumed.stdout)['requestDigest'], original['requestDigest'])
        self.assertIs(json.loads(resumed.stdout)['collectionRequested'], False)
        self.assertEqual(len(self.native.calls), 2)

    def test_terminated_native_client_cannot_be_automatically_replaced(self):
        first = self.start_command()
        try:
            self.assertTrue(self.native.request_started.wait(5))
            first.kill()
            first.communicate(timeout=5)
            self.assertNotEqual(first.returncode, 0)
            retry = self.command('stage')
            self.assertEqual(retry.returncode, 2, retry.stderr)
            self.assertEqual(json.loads(retry.stdout)['status'], 'HELD')
            self.assertEqual(len(self.native.calls), 1)
            self.assertIsNone(self.outbox().for_campaign(self.native.campaign, self.native.environment))
        finally:
            self.release.set()
