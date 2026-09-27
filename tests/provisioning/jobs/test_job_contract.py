"""Pure contract checks; PostgreSQL durability is exercised separately."""
from __future__ import annotations

import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from provisioner.controlplane.authority.model import AuthorizedPlan, FrozenPlan
from provisioner.controlplane.jobs import (AdmissionConflict, AdmissionRefused,
                                            JobRepository, OutboxDispatcher,
                                            OutboxMessage, StartReceipt)
from provisioner.controlplane.jobs.repository import _digest, _ensure_plan, _ensure_workload
from provisioner.controlplane.persistence import TenantContext, canonical_record_digest
from tests.provisioning.schema.test_enterprise_records import plan, workload


def decision(record):
    frozen = FrozenPlan.from_record(record, author_subject='author-01')
    return AuthorizedPlan(
        frozen.organization_id, frozen.tenant_id, frozen.plan_id,
        frozen.revision, frozen.digest, frozen.source, frozen.destination,
        ('source-approval', 'destination-approval'), 0,
        datetime.now(timezone.utc) + timedelta(hours=1), 'operator-01')


class AdmissionContractTest(unittest.TestCase):
    def setUp(self):
        self.record = plan()
        self.authorized = decision(self.record)
        self.tenant = TenantContext('org-01', 'tenant-01')

    def test_exact_plan_digest_revision_and_both_scopes_are_checked(self):
        row = (1, canonical_record_digest(self.record), self.record)
        _ensure_plan(row, self.tenant, self.authorized)
        with self.assertRaises(AdmissionRefused):
            _ensure_plan((2, row[1], row[2]), self.tenant, self.authorized)
        with self.assertRaises(AdmissionRefused):
            _ensure_plan((1, '0' * 64, row[2]), self.tenant, self.authorized)
        with self.assertRaises(AdmissionRefused):
            _ensure_plan(row, self.tenant,
                         replace(self.authorized, plan_digest='0' * 64))
        with self.assertRaises(AdmissionRefused):
            _ensure_plan(row, self.tenant,
                         replace(self.authorized,
                                 destination=self.authorized.source))

    def test_submission_requires_transactional_authority_dependency(self):
        with self.assertRaises(ValueError):
            JobRepository(lambda: None, None)

    def test_current_workload_revision_and_source_bindings_gate_plan(self):
        selected = self.record
        observed = workload()

        class Cursor:
            def __init__(self, record):
                self.record = record

            def execute(self, query, params):
                self.params = params

            def fetchone(self):
                return (self.record['metadata']['revision'],
                        canonical_record_digest(self.record), self.record)

        _ensure_workload(Cursor(observed), self.tenant, selected)
        successor = deepcopy(observed)
        successor['metadata']['revision'] = 2
        with self.assertRaises(AdmissionRefused):
            _ensure_workload(Cursor(successor), self.tenant, selected)
        changed_binding = deepcopy(observed)
        changed_binding['spec']['machines'][0]['bindings'][0]['binding']['nativeId'] = 'other-vm'
        with self.assertRaises(AdmissionRefused):
            _ensure_workload(Cursor(changed_binding), self.tenant, selected)

    def test_mismatched_receipt_cannot_mark_job_started(self):
        repository = JobRepository(lambda: self.fail('DB must not be touched'),
                                   SimpleNamespace(revalidate_admission=lambda *a: None,
                                                   revalidate_start=lambda *a: None))
        payload = {'plan_id': 'p', 'plan_revision': 1, 'plan_digest': 'a' * 64}
        message = OutboxMessage('o', 'job-1', payload, 'claim', 1)
        receipt = StartReceipt('ns', 'job-1', 'run-1', 'job-1', 'p', 1,
                               'a' * 64, _digest(payload))
        for forged in (replace(receipt, workflow_id='other'),
                       replace(receipt, namespace='other'),
                       replace(receipt, payload_digest='0' * 64),
                       replace(receipt, run_id='')):
            with self.assertRaises(AdmissionConflict):
                repository.mark_started(self.tenant, message, forged, namespace='ns')


class _Workflow:
    def __init__(self):
        self.runs = {}
        self.starts = 0

    def start(self, *, namespace, workflow_id, payload):
        self.starts += 1
        key = namespace, workflow_id
        if key not in self.runs:
            self.runs[key] = StartReceipt(
                namespace, workflow_id, 'durable-run-1', payload['job_id'],
                payload['plan_id'], payload['plan_revision'],
                payload['plan_digest'], _digest(payload))
        return self.runs[key]


class _Jobs:
    """Protocol fake only. It does not simulate PostgreSQL durability."""

    def __init__(self):
        self.payload = {'job_id': 'job-1', 'plan_id': 'plan-1',
                        'plan_revision': 1, 'plan_digest': 'a' * 64}
        self.message = OutboxMessage('outbox-1', 'job-1', self.payload, 'claim', 1)
        self.job = SimpleNamespace(job_id='job-1', plan_id='plan-1',
                                   plan_revision=1, plan_digest='a' * 64)
        self.fail_after_workflow_start = True
        self.acked = False

    def claim_start(self, context, **kwargs):
        return None if self.acked else self.message

    def revalidate_start(self, context, message):
        return self.job

    def mark_started(self, context, message, receipt, *, namespace):
        if self.fail_after_workflow_start:
            self.fail_after_workflow_start = False
            raise ConnectionError('crash after workflow persisted start')
        self.acked = True
        return True

    def hold_start(self, context, message):
        self.acked = True
        return True


class DispatchContractTest(unittest.TestCase):
    def test_crash_after_workflow_start_retries_same_logical_run(self):
        jobs, workflow = _Jobs(), _Workflow()
        dispatcher = OutboxDispatcher(jobs, workflow,
                                      dispatcher_id='dispatch-1', namespace='site-a')
        with self.assertRaises(ConnectionError):
            dispatcher.run_one(TenantContext('org-01', 'tenant-01'))
        result = dispatcher.run_one(TenantContext('org-01', 'tenant-01'))
        self.assertEqual(result.disposition, 'STARTED')
        self.assertEqual(len(workflow.runs), 1)
        self.assertEqual(workflow.starts, 2)

    def test_foreign_workflow_binding_cannot_ack_outbox(self):
        jobs, workflow = _Jobs(), _Workflow()
        workflow.runs[('site-a', 'job-1')] = StartReceipt(
            'site-a', 'job-1', 'foreign-run', 'other-job', 'plan-1', 1,
            'a' * 64, _digest(jobs.payload))
        dispatcher = OutboxDispatcher(jobs, workflow,
                                      dispatcher_id='dispatch-1', namespace='site-a')
        with self.assertRaises(AdmissionConflict):
            dispatcher.run_one(TenantContext('org-01', 'tenant-01'))
        self.assertFalse(jobs.acked)


if __name__ == '__main__':
    unittest.main()
