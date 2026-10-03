"""Bounded batch scheduling and real signed/TLS staging; no fleet acceptance."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from provisioner.controlplane.discovery import batch_runtime, collector_runtime
from provisioner.controlplane.discovery.batch_runtime import DiscoveryBatch, run_batch
from tests.provisioning.discovery import test_collector_runtime as runtime_fixture


def specification(config, campaign, environment, *, now):
    scope = campaign.scope
    return {'format': 'hosting-discovery-batch/1', 'batchId': 'batch-1',
        'maxParallelCollections': 2, 'maxDurationSeconds': 10,
        'endpoints': [{'policyId': 'native', 'organizationId': scope.organization_id,
            'siteId': scope.site_id, 'platformFamily': scope.platform_family,
            'endpointId': scope.endpoint_id, 'maxConcurrentReads': 1, 'minReadIntervalMilliseconds': 50}],
        'tasks': [{'taskId': 'task-1', 'environmentId': environment, 'campaignDigest': campaign.digest(),
            'collectorConfigFile': str(config), 'collectorConfigDigest': hashlib.sha256(config.read_bytes()).hexdigest(),
            'policyId': 'native', 'notBefore': (now-timedelta(seconds=1)).isoformat(),
            'notAfter': (now+timedelta(seconds=50)).isoformat()}]}


class BatchRuntimeTests(runtime_fixture.RuntimeFixture, unittest.TestCase):
    def setUp(self):
        self.configure()
        self.batch = specification(self.config_path, self.native.campaign, self.native.environment, now=self.native.now)
        self.batch_path = self.native.root/'batch.json'
        self.write_batch()

    def write_batch(self):
        runtime_fixture.write_json(self.batch_path, self.batch)

    def run_batch(self):
        self.write_batch()
        return run_batch(self.batch_path, clock=lambda: self.native.now)

    def test_actual_batch_uses_signed_campaign_native_tls_and_original_outbox(self):
        outcome = self.run_batch()
        self.assertEqual(outcome['status'], 'BATCH_EVALUATED')
        self.assertEqual(outcome['stagedCount'], 1)
        self.assertEqual(len(self.native.calls), 2)
        self.assertEqual(outcome['items'][0]['collector']['completeness'], 'PARTIAL')
        self.assertFalse(outcome['publicationAttempted'])
        self.assertFalse(outcome['executionAuthorized'])
        self.assertFalse(outcome['durableSchedule'])
        self.assertEqual(outcome['limitScope'], 'THIS_PROCESS_ONLY')
        original = self.outbox().for_campaign(self.native.campaign, self.native.environment)
        self.assertEqual(original.digest, outcome['items'][0]['collector']['requestDigest'])
        self.assertNotIn(self.native.token, json.dumps(outcome))

    def test_fresh_process_command_runs_the_batch(self):
        result = subprocess.run([sys.executable, '-m', 'provisioner.controlplane.discovery.collector_runtime',
            'batch-stage', '--config', str(self.batch_path)], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(json.loads(result.stdout)['stagedCount'], 1)
        self.assertEqual(len(self.native.calls), 2)

    def test_repeated_batch_reuses_original_without_native_credentials_or_signer(self):
        first = self.run_batch()
        self.native.credential_path.unlink(); self.signer_path.unlink()
        second = self.run_batch()
        self.assertEqual(second['stagedCount'], 1)
        self.assertEqual(second['items'][0]['collector']['requestDigest'], first['items'][0]['collector']['requestDigest'])
        self.assertFalse(second['items'][0]['collector']['collectionRequested'])
        self.assertEqual(len(self.native.calls), 2)

    def test_replay_still_rechecks_live_credential_revocation(self):
        self.run_batch(); self.native.revoke_witness()
        outcome = self.run_batch()
        self.assertEqual(outcome['status'], 'BATCH_HELD')
        self.assertEqual(outcome['stagedCount'], 0)
        self.assertEqual(len(self.native.calls), 2)

    def test_changed_config_bytes_are_refused_before_native_contact(self):
        self.config_path.write_bytes(self.config_path.read_bytes()+b'\n')
        self.assertEqual(self.run_batch()['items'][0]['status'], 'HELD')
        self.assertEqual(self.native.calls, [])

    def test_environment_campaign_and_endpoint_selection_are_bound(self):
        original = copy.deepcopy(self.batch)
        for change in ('environment', 'campaign', 'endpoint'):
            self.batch = copy.deepcopy(original)
            if change == 'environment': self.batch['tasks'][0]['environmentId'] = 'foreign'
            if change == 'campaign': self.batch['tasks'][0]['campaignDigest'] = 'f'*64
            if change == 'endpoint': self.batch['endpoints'][0]['endpointId'] = 'foreign'
            self.assertEqual(self.run_batch()['items'][0]['status'], 'HELD')
        self.assertEqual(self.native.calls, [])

    def test_unsigned_campaign_changes_are_not_authority(self):
        path = Path(self.config['campaignFile']); doc = json.loads(path.read_bytes())
        doc['campaign']['maxObjects'] += 1
        runtime_fixture.write_json(path, doc)
        self.assertEqual(self.run_batch()['items'][0]['status'], 'HELD')
        self.assertFalse(self.native.calls)

    def test_future_task_does_not_read_its_configuration_or_wait(self):
        self.batch['tasks'][0]['notBefore'] = (self.native.now+timedelta(seconds=10)).isoformat()
        self.config_path.unlink()
        outcome = self.run_batch()
        self.assertEqual(outcome['items'][0]['status'], 'NOT_DUE')
        self.assertEqual(outcome['stagedCount'], 0)
        self.assertFalse(self.native.calls)

    def test_expired_task_window_prevents_collection(self):
        self.batch['tasks'][0]['notBefore'] = (self.native.now-timedelta(seconds=20)).isoformat()
        self.batch['tasks'][0]['notAfter'] = self.native.now.isoformat()
        self.assertEqual(self.run_batch()['items'][0]['status'], 'WINDOW_EXPIRED')
        self.assertFalse(self.native.calls)

    def test_window_expiry_during_read_cannot_stage_replacement_evidence(self):
        end = datetime.fromisoformat(self.batch['tasks'][0]['notAfter'])
        self.native.on_get = lambda: setattr(self.native, 'now', end)
        outcome = self.run_batch()
        self.assertEqual(outcome['items'][0]['status'], 'HELD')
        self.assertEqual(len(self.native.calls), 1)
        self.assertIsNone(self.outbox().for_campaign(self.native.campaign, self.native.environment))

    def test_clock_regression_after_selection_holds_before_native_contact(self):
        self.write_batch(); first = self.native.now
        calls = 0
        def clock():
            nonlocal calls
            calls += 1
            return first if calls == 1 else first-timedelta(seconds=1)
        result = run_batch(self.batch_path, clock=clock)
        self.assertEqual(result['items'][0]['status'], 'HELD')
        self.assertFalse(self.native.calls)

    def test_duration_stops_new_reads_and_waits_for_socket_cleanup(self):
        self.batch['maxDurationSeconds'] = 1
        self.native.delay = 1.2
        result = self.run_batch()
        self.assertEqual(result['items'][0]['status'], 'HELD')
        self.assertEqual(len(self.native.calls), 1)
        self.assertFalse(any(t.name.startswith('discovery-batch') for t in threading.enumerate()))

    def test_batch_requires_private_regular_bounded_configuration(self):
        self.batch_path.chmod(0o644)
        with self.assertRaises(Exception): run_batch(self.batch_path)
        self.batch_path.unlink(); os.mkfifo(self.batch_path, 0o600)
        with self.assertRaises(Exception): run_batch(self.batch_path)
        self.batch_path.unlink(); self.batch_path.symlink_to(self.config_path)
        with self.assertRaises(Exception): run_batch(self.batch_path)
        self.batch_path.unlink(); self.write_batch()
        self.batch_path.write_bytes(b' '*131073)
        with self.assertRaises(Exception): run_batch(self.batch_path)
        self.assertFalse(self.native.calls)

    def test_invalid_or_duplicate_policy_tasks_and_windows_are_rejected_as_a_whole(self):
        initial = copy.deepcopy(self.batch)
        changes = [lambda d:d.update(format='hosting-discovery-batch/0'),
            lambda d:d.update(maxParallelCollections=True), lambda d:d.update(maxParallelCollections=17),
            lambda d:d.update(maxDurationSeconds=0), lambda d:d.update(maxDurationSeconds=3601),
            lambda d:d.update(token='secret'), lambda d:d['tasks'].append(d['tasks'][0]),
            lambda d:d['endpoints'].append(d['endpoints'][0]),
            lambda d:d['tasks'][0].update(collectorConfigFile='../other'),
            lambda d:d['tasks'][0].update(campaignDigest='unknown'),
            lambda d:d['tasks'][0].update(policyId='absent'),
            lambda d:d['tasks'][0].update(notBefore=d['tasks'][0]['notAfter']),
            lambda d:d['tasks'][0].update(notAfter='2026-09-30T12:00:00'),
            lambda d:d.update(tasks=[]),lambda d:d.update(endpoints=[])]
        for change in changes:
            self.batch = copy.deepcopy(initial); change(self.batch); self.write_batch()
            with self.assertRaises((ValueError, TypeError)): DiscoveryBatch.from_file(self.batch_path)
        self.assertFalse(self.native.calls)

    def test_duplicate_json_is_refused(self):
        self.batch_path.write_text('{"format":"a","format":"b"}')
        with self.assertRaises(ValueError): DiscoveryBatch.from_file(self.batch_path)


class BatchOtherNativeTests(runtime_fixture.RuntimeFixture, unittest.TestCase):
    def batch_stage(self):
        path = self.native.root/'batch.json'
        runtime_fixture.write_json(path, specification(self.config_path, self.native.campaign,
                                  self.native.environment, now=self.native.now))
        return run_batch(path, clock=lambda: self.native.now)

    def test_vmware_batch_uses_actual_folder_reads(self):
        f = runtime_fixture.vmware_fixture; selection = f.SELECTION
        self.configure(f.VmwareHttpsTests(), selection={'folderIds': list(selection.folder_ids),
                                                      'coverageDigest': selection.coverage_digest})
        self.assertEqual(self.batch_stage()['stagedCount'], 1)
        self.assertEqual(len(self.native.calls), 2)

    def test_openstack_batch_uses_all_four_actual_service_read_paths(self):
        from tests.provisioning.discovery import test_openstack_https as fixture
        self.configure(fixture.OpenStackHttpsTests())
        n = self.native
        self.config['native']['selection'] = {s:n.endpoints.for_service(s) for s in fixture.API_VERSIONS}
        self.config['native']['caBundles'] = {s:str(n.root/'ca.pem') for s in fixture.API_VERSIONS}
        self.save()
        self.assertEqual(self.batch_stage()['stagedCount'], 1)
        self.assertEqual([c[0] for c in n.calls], ['compute','volume','network']*2 + ['image'])


class BatchDispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'batch.json'; self.now = datetime.now(timezone.utc)
        endpoint = {'policyId':'a','organizationId':'org','siteId':'site','platformFamily':'nutanix',
                    'endpointId':'endpoint-a','maxConcurrentReads':1,'minReadIntervalMilliseconds':1}
        self.spec = {'format':'hosting-discovery-batch/1','batchId':'batch','maxParallelCollections':2,
                    'maxDurationSeconds':5,'endpoints':[endpoint,{**endpoint,'policyId':'b','endpointId':'endpoint-b'}],
                    'tasks':[{'taskId':f'task-{i}','environmentId':'env','campaignDigest':f'{i:064x}',
                        'collectorConfigFile':str(Path(self.temp.name)/f'config-{i}.json'),
                        'collectorConfigDigest':'a'*64,'policyId':'a' if i<3 else 'b',
                        'notBefore':(self.now-timedelta(seconds=1)).isoformat(),
                        'notAfter':(self.now+timedelta(seconds=30)).isoformat()} for i in range(6)]}

    def run_with(self, effect):
        runtime_fixture.write_json(self.path, self.spec)
        with patch.object(batch_runtime, 'execute', side_effect=effect):
            return run_batch(self.path, clock=lambda:self.now)

    def test_global_collection_concurrency_is_bounded_and_every_due_task_runs_once(self):
        active = peak = 0; seen=[]; lock=threading.Lock()
        def effect(path, action, **kwargs):
            nonlocal active, peak
            self.assertEqual(action,'stage'); self.assertIn('read_gate',kwargs); kwargs['clock']()
            with lock: active+=1; peak=max(peak,active); seen.append(path)
            time.sleep(.02)
            with lock: active-=1
            return {'status':'STAGED','executionAuthorized':False}
        result = self.run_with(effect)
        self.assertEqual(peak,2); self.assertEqual(len(set(seen)),6); self.assertEqual(result['stagedCount'],6)
        self.assertEqual([r['taskId'] for r in result['items']], [t['taskId'] for t in self.spec['tasks']])

    def test_round_robin_dispatch_does_not_put_one_endpoints_whole_queue_first(self):
        self.spec['maxParallelCollections']=1; seen=[]
        self.run_with(lambda p,a,**k:seen.append(p.name) or {'status':'STAGED'})
        self.assertEqual(seen,['config-0.json','config-3.json','config-1.json','config-4.json','config-2.json','config-5.json'])

    def test_failed_task_does_not_retry_leak_exception_or_cancel_other_tasks(self):
        seen=[]
        def effect(path,*a,**k):
            seen.append(path.name)
            if path.name=='config-0.json':raise ValueError('private-token-never-output')
            return {'status':'STAGED'}
        result=self.run_with(effect)
        self.assertEqual(len(seen),6); self.assertEqual(result['stagedCount'],5)
        self.assertEqual(result['status'],'BATCH_HELD'); self.assertNotIn('private-token',json.dumps(result))

    def test_interruption_stops_and_drains_workers_before_return(self):
        self.spec['maxParallelCollections']=1
        with self.assertRaises(KeyboardInterrupt):
            self.run_with(lambda *a,**k: (_ for _ in ()).throw(KeyboardInterrupt()))
        self.assertFalse(any(t.name.startswith('discovery-batch') for t in threading.enumerate()))

    def test_cli_interrupt_keeps_reconciliation_required(self):
        output=io.StringIO()
        with patch.object(batch_runtime,'run_batch',side_effect=KeyboardInterrupt),redirect_stdout(output):
            code=collector_runtime.main(['batch-stage','--config',str(self.path)])
        self.assertEqual(code,130);self.assertTrue(json.loads(output.getvalue())['reconciliationRequired'])
