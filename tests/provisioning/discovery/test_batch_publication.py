"""Explicit retained-original delivery/recovery using actual loopback mTLS ingest."""
from datetime import timedelta
import hashlib
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from provisioner.controlplane.discovery import batch_runtime, publication_https
from provisioner.controlplane.discovery.batch_journal import BatchJournal
from provisioner.controlplane.discovery.batch_runtime import DiscoveryBatch, publish_batch, run_batch
from tests.provisioning.discovery import test_collector_runtime as runtime
from tests.provisioning.discovery.test_batch_runtime import specification


class BatchPublicationTests(runtime.RuntimeFixture, unittest.TestCase):
    def setUp(self):
        self.configure()
        self.start_ingest()
        self.directory = self.native.root/'batch-state'; self.directory.mkdir(mode=0o700)
        self.path = self.native.root/'batch.json'
        self.doc = specification(self.config_path, self.native.campaign,
                                 self.native.environment, now=self.native.now)
        runtime.write_json(self.path, self.doc)

    def stage_batch(self):
        return run_batch(self.path, state_directory=self.directory, clock=lambda:self.native.now)

    def publish(self, **kwargs):
        return publish_batch(self.path, self.directory, clock=lambda:self.native.now, **kwargs)

    def test_mtls_acknowledgement_is_retained_and_restarts_do_not_publish_again(self):
        stage = self.stage_batch()
        original = self.outbox().for_campaign(self.native.campaign,self.native.environment)
        self.native.credential_path.unlink(); self.signer_path.unlink()
        first = self.publish()
        self.assertEqual(first['status'],'PUBLICATION_ACKNOWLEDGED')
        self.assertEqual(first['publishedCount'],1)
        self.assertEqual(self.requests,[original.body])
        self.assertEqual(first['items'][0]['collector']['requestDigest'],
                         stage['items'][0]['collector']['requestDigest'])
        second = self.publish()
        self.assertEqual(second['publishedCount'],0)
        self.assertFalse(second['publicationAttempted'])
        self.assertEqual(self.requests,[original.body])
        self.assertEqual(len(self.native.calls),2)
        self.assertFalse(first['collectionRequested'])

    def test_no_retained_capture_cannot_create_or_publish_an_original(self):
        spec=DiscoveryBatch.from_file(self.path)
        with BatchJournal(self.directory,spec,manifest_path=self.path,clock=lambda:self.native.now,enroll=True):pass
        result=self.publish()
        self.assertEqual(result['status'],'PUBLICATION_HELD')
        self.assertFalse(result['publicationAttempted'])
        self.assertEqual(self.requests,[]); self.assertEqual(self.native.calls,[])

    def test_lost_receipt_needs_explicit_same_original_retry_and_never_recollects(self):
        self.stage_batch()
        original=self.outbox().for_campaign(self.native.campaign,self.native.environment)
        actual=publication_https.DiscoveryHttpsPublisher._post
        def lost(owner,phase,submission,current):
            value=actual(owner,phase,submission,current)
            if phase=='RESULT':raise publication_https.DiscoveryPublicationUnknown(submission.digest,phase)
            return value
        with patch.object(publication_https.DiscoveryHttpsPublisher,'_post',lost):
            first=self.publish()
        self.assertEqual(first['unknownDeliveryCount'],1)
        before=list(self.requests)
        self.assertEqual(self.publish()['unknownDeliveryCount'],1)
        self.assertEqual(self.requests,before)
        self.native.credential_path.unlink(); self.signer_path.unlink()
        result=self.publish(retry_unknown=True)
        self.assertEqual(result['status'],'PUBLICATION_ACKNOWLEDGED')
        self.assertEqual(self.requests,[original.body,original.body])
        self.assertEqual(len(self.results),1)
        self.assertEqual(len(self.native.calls),2)

    def test_recovered_publication_start_is_unknown_and_attempts_are_bounded(self):
        self.stage_batch();spec=DiscoveryBatch.from_file(self.path)
        with BatchJournal(self.directory,spec,manifest_path=self.path,clock=lambda:self.native.now) as state:
            state.publication_start('task-1')
        self.assertEqual(self.publish()['unknownDeliveryCount'],1)
        self.assertEqual(self.requests,[])
        with patch.object(batch_runtime,'execute',side_effect=RuntimeError('private material')):
            self.assertEqual(self.publish(retry_unknown=True)['unknownDeliveryCount'],1)
            self.assertEqual(self.publish(retry_unknown=True)['unknownDeliveryCount'],1)
            result=self.publish(retry_unknown=True)
        self.assertEqual(result['items'][0]['status'],'PUBLICATION_HELD')
        self.assertFalse(result['publicationAttempted'])
        self.assertNotIn('private material',json.dumps(result))
        self.assertEqual(len(self.native.calls),2)

    def test_expired_or_revoked_inputs_do_not_recollect(self):
        self.stage_batch();self.native.revoke_witness()
        self.assertEqual(self.publish()['status'],'PUBLICATION_HELD')
        self.assertEqual(self.requests,[]);self.assertEqual(len(self.native.calls),2)

    def test_ack_for_another_original_cannot_be_retained(self):
        stage=self.stage_batch()['items'][0]['collector']
        receipt={**stage,'status':'PUBLISHED','generation':1,'collectionRequested':False,
                 'publicationAttempted':True,'requestDigest':'f'*64}
        receipt.pop('objectCount')
        with patch.object(batch_runtime,'execute',return_value=receipt):
            result=self.publish()
        self.assertEqual(result['unknownDeliveryCount'],1)
        self.assertEqual(result['publishedCount'],0)

    def test_installed_command_supports_original_only_batch_delivery(self):
        self.stage_batch()
        result=subprocess.run([sys.executable,'-m','provisioner.controlplane.discovery.collector_runtime',
            'batch-publish','--config',str(self.path),'--state-directory',str(self.directory)],
            capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'PUBLICATION_ACKNOWLEDGED')
        self.assertEqual(len(self.requests),1)


if __name__=='__main__':unittest.main()
