"""The B08 gate must never report a workload migrated."""
import unittest
from unittest.mock import patch, sentinel
from types import SimpleNamespace
from temporalio.common import VersioningBehavior

from provisioner.controlplane.jobs import StartReceipt
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.workflow.approval_gate import GateResult
from provisioner.controlplane.workflow.application_job import ApplicationJobResult
from provisioner.controlplane.jobs.repository import _progress_detail
from provisioner.controlplane.workflow.runtime import (
    _connect, _worker_deployment_config, project_one)


class RuntimeConnectionTests(unittest.TestCase):
    def test_postgres_connection_has_bounded_timeout(self):
        with patch.dict('os.environ', {'HOSTING_WORKFLOW_POSTGRES_DSN':
                                      'postgresql://runtime@db.example/control'}):
            with patch('provisioner.controlplane.workflow.runtime.psycopg.connect',
                       return_value=sentinel.connection) as connect:
                self.assertIs(_connect(), sentinel.connection)
        connect.assert_called_once_with(
            'postgresql://runtime@db.example/control', connect_timeout=5)

    def test_worker_requires_an_immutable_versioned_deployment(self):
        with patch.dict('os.environ', {
                'HOSTING_TEMPORAL_WORKER_DEPLOYMENT': 'mobility-management',
                'HOSTING_TEMPORAL_WORKER_BUILD_ID': 'a' * 40}):
            config = _worker_deployment_config()
            self.assertTrue(config.use_worker_versioning)
            self.assertEqual(config.default_versioning_behavior, VersioningBehavior.PINNED)
            self.assertEqual(config.version.deployment_name, 'mobility-management')
            self.assertEqual(config.version.build_id, 'a' * 40)
        for invalid in ('latest', 'a' * 12, 'A' * 40, 'a' * 39):
            with self.subTest(invalid=invalid):
                with patch.dict('os.environ', {
                        'HOSTING_TEMPORAL_WORKER_DEPLOYMENT': 'mobility-management',
                        'HOSTING_TEMPORAL_WORKER_BUILD_ID': invalid}):
                    with self.assertRaises(ValueError):
                        _worker_deployment_config()


class GateProjectionTests(unittest.TestCase):
    def test_verified_application_projects_success_with_final_acceptance_reference(self):
        receipt = StartReceipt('ns', 'job', 'run', 'job', 'plan', 1, 'a'*64, 'b'*64)
        events = []
        jobs = SimpleNamespace(start_run=lambda context, job_id: receipt,
            append_progress=lambda context, job_id, **event: events.append(event))
        result = ApplicationJobResult('job', 'plan', 1, 'a'*64, 'c'*64,
            'SUCCEEDED', 'VERIFY', None, 'd'*64, 12, 12, None, 'e'*64)
        self.assertTrue(project_one(jobs, SimpleNamespace(completed_job=lambda _: result),
                                   TenantContext('org', 'tenant'), 'job'))
        self.assertEqual(events[0]['event_type'], 'APPLICATION_EXECUTION_SUCCEEDED')
        self.assertEqual(events[0]['status'], 'SUCCEEDED')
        self.assertEqual(events[0]['detail']['evidenceDigest'], 'd'*64)
        self.assertNotIn('reasonCode', events[0]['detail'])
        self.assertNotIn('holdCode', events[0]['detail'])
        _progress_detail(events[0]['detail'])

    def test_selected_hold_retains_fixed_reason_and_progress_without_authority(self):
        receipt = StartReceipt('ns', 'job', 'run', 'job', 'plan', 1, 'a'*64, 'b'*64)
        events = []
        jobs = SimpleNamespace(start_run=lambda context, job_id: receipt,
            append_progress=lambda context, job_id, **event: events.append(event))
        result = ApplicationJobResult('job', 'plan', 1, 'a'*64, 'c'*64, 'HELD',
            'PROVISION', 'OPERATOR_HOLD', 'd'*64, 3, 10,
            'GUEST_PER_COMMAND_AUTHORITY_UNAVAILABLE')
        workflow = SimpleNamespace(completed_job=lambda original: result)
        self.assertTrue(project_one(jobs, workflow, TenantContext('org', 'tenant'), 'job'))
        self.assertEqual(events[0]['event_key'], 'temporal-application:run')
        self.assertEqual(events[0]['status'], 'HELD')
        detail = events[0]['detail']
        self.assertEqual(detail['holdCode'], 'GUEST_PER_COMMAND_AUTHORITY_UNAVAILABLE')
        self.assertEqual((detail['completed'], detail['total']), (3, 10))
        _progress_detail(detail)
        with self.assertRaises(ValueError):
            _progress_detail(detail | {'holdCode': '/private/token'})
        with self.assertRaises(ValueError):
            _progress_detail(detail | {'nativeExecutionAuthorized': True})

    def test_passing_gate_stays_held_until_native_execution_is_implemented(self):
        receipt = StartReceipt('ns', 'job', 'run', 'job', 'plan', 1,
                               'a' * 64, 'b' * 64)

        class Jobs:
            def __init__(self):
                self.events = []

            def start_run(self, context, job_id):
                return receipt

            def append_progress(self, context, job_id, **event):
                self.events.append(event)

        jobs = Jobs()
        workflow = SimpleNamespace(completed_job=lambda _: GateResult(
            'GATE_PASSED', 'job', 'plan', 1, 'a' * 64, 'approval', 'c' * 64))
        self.assertTrue(project_one(jobs, workflow, TenantContext('org', 'tenant'), 'job'))
        self.assertEqual(len(jobs.events), 1)
        self.assertEqual(jobs.events[0]['status'], 'HELD')
        self.assertEqual(jobs.events[0]['event_type'], 'GATE_PASSED_EXECUTION_HELD')
