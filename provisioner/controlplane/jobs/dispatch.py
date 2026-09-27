"""Deliver admitted intents to one durable workflow by stable workflow ID.

The workflow adapter must persist a matching binding before acknowledging a
start, including on a duplicate start. An uncertain transport result is left
pending: claim expiry permits retry, and a duplicate must resolve to the same
workflow/job/plan revision/digest. This module never executes native work.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from provisioner.controlplane.authority import AuthorityDenied

from .repository import (AdmissionConflict, AdmissionRefused, JobRepository,
                         StartReceipt, _digest)


class DurableWorkflowStarter(Protocol):
    def start(self, *, namespace: str, workflow_id: str,
              payload: dict) -> StartReceipt:
        """Start or verify an existing durable run with the exact same binding."""


@dataclass(frozen=True)
class DispatchResult:
    job_id: str
    disposition: str  # STARTED, HELD, or CLAIM_LOST


class OutboxDispatcher:
    def __init__(self, jobs: JobRepository, workflow: DurableWorkflowStarter,
                 *, dispatcher_id: str, namespace: str):
        if jobs is None or workflow is None or not callable(getattr(workflow, 'start', None)):
            raise ValueError('Durable job and workflow services are required')
        self.jobs = jobs
        self.workflow = workflow
        self.dispatcher_id = dispatcher_id
        if not isinstance(namespace, str) or not namespace:
            raise ValueError('Durable workflow namespace is required')
        self.namespace = namespace

    def run_one(self, context, *, lease_seconds: int = 30) -> DispatchResult | None:
        message = self.jobs.claim_start(context, dispatcher_id=self.dispatcher_id,
                                        lease_seconds=lease_seconds)
        if message is None:
            return None
        try:
            job = self.jobs.revalidate_start(context, message)
        except (AdmissionRefused, AuthorityDenied):
            held = self.jobs.hold_start(context, message)
            return DispatchResult(message.job_id, 'HELD' if held else 'CLAIM_LOST')
        # The external start is deliberately after the database commit. A
        # crash here is retried with the same workflow ID, not a new run.
        receipt = self.workflow.start(namespace=self.namespace,
                                      workflow_id=job.job_id,
                                      payload=message.payload)
        if not isinstance(receipt, StartReceipt) or (
                receipt.namespace, receipt.workflow_id, receipt.job_id,
                receipt.plan_id, receipt.plan_revision,
                receipt.plan_digest, receipt.payload_digest) != (
                self.namespace, job.job_id, job.job_id, job.plan_id,
                job.plan_revision, job.plan_digest,
                _digest(message.payload)) or not receipt.run_id:
            raise AdmissionConflict('Workflow start did not acknowledge the exact job binding')
        acknowledged = self.jobs.mark_started(context, message, receipt,
                                              namespace=self.namespace)
        return DispatchResult(job.job_id, 'STARTED' if acknowledged else 'CLAIM_LOST')
