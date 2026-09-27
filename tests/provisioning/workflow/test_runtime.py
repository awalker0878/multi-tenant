"""The B08 gate must never report a workload migrated."""
import unittest
from types import SimpleNamespace

from provisioner.controlplane.jobs import StartReceipt
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.workflow.approval_gate import GateResult
from provisioner.controlplane.workflow.runtime import project_one


class GateProjectionTests(unittest.TestCase):
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
        workflow = SimpleNamespace(completed_gate=lambda _: GateResult(
            'GATE_PASSED', 'job', 'plan', 1, 'a' * 64, 'approval', 'c' * 64))
        self.assertTrue(project_one(jobs, workflow, TenantContext('org', 'tenant'), 'job'))
        self.assertEqual(len(jobs.events), 1)
        self.assertEqual(jobs.events[0]['status'], 'HELD')
        self.assertEqual(jobs.events[0]['event_type'], 'GATE_PASSED_EXECUTION_HELD')
