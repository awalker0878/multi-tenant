"""Durable approval wait for an exact admitted migration job.

Only opaque identifiers, epochs and digests enter history. A Signal is an
untrusted notification, not approval. The Activity asks the B07 ledger for a
current decision. A passing gate does not initiate any native mutation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError


VERIFY_APPROVAL_ACTIVITY = 'verify_migration_approval'
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}')
_DIGEST = re.compile(r'[0-9a-f]{64}')
_TOKEN_SHAPE = re.compile(r'(?:AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}'
                          r'|gh[pousr]_[A-Za-z0-9_]{20,}'
                          r'|xox[baprs]-[A-Za-z0-9-]{16,})', re.IGNORECASE)


def _valid_id(value: object) -> bool:
    return (isinstance(value, str) and _ID.fullmatch(value) is not None
            and _TOKEN_SHAPE.search(value) is None)


def _valid_digest(value: object) -> bool:
    return isinstance(value, str) and _DIGEST.fullmatch(value) is not None


@dataclass(frozen=True)
class GateInput:
    job_id: str
    organization_id: str
    tenant_id: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    revocation_epoch: int
    payload_digest: str
    approval_timeout_seconds: int

    def __post_init__(self) -> None:
        if not all(_valid_id(value) for value in
                   (self.job_id, self.organization_id, self.tenant_id, self.plan_id)):
            raise ValueError('Job, organization, tenant and plan IDs must match the domain contract')
        if type(self.plan_revision) is not int or self.plan_revision < 1:
            raise ValueError('A positive plan revision is required')
        if type(self.revocation_epoch) is not int or self.revocation_epoch < 0:
            raise ValueError('A nonnegative revocation epoch is required')
        if not _valid_digest(self.plan_digest) or not _valid_digest(self.payload_digest):
            raise ValueError('Plan and payload digests must be SHA-256 hex digests')
        if type(self.approval_timeout_seconds) is not int or not 1 <= self.approval_timeout_seconds <= 2592000:
            raise ValueError('The approval wait must be between one second and 30 days')


@dataclass(frozen=True)
class ApprovalNotice:
    """Untrusted prompt to re-read a decision; never a credential or grant."""

    job_id: str
    organization_id: str
    tenant_id: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    approval_id: str


@dataclass(frozen=True)
class ApprovalCheck:
    """Output of the independent product-authority Activity, not a client input."""

    authorized: bool
    job_id: str
    organization_id: str
    tenant_id: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    revocation_epoch: int
    approval_id: str
    evidence_digest: str


@dataclass(frozen=True)
class GateResult:
    status: str  # GATE_PASSED, EXPIRED, or HELD; never a native effect
    job_id: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    approval_id: str | None = None
    evidence_digest: str | None = None


def _binding(input: GateInput) -> tuple[str, str, str, str, int, str]:
    return (input.job_id, input.organization_id, input.tenant_id, input.plan_id,
            input.plan_revision, input.plan_digest)


@workflow.defn(name='MigrationApprovalGate')
class MigrationApprovalGate:
    """Wait durably for product authority and deliberately stop at a gate.

The outbox must use a stable job ID as the Temporal Workflow ID. B09 owns
submission and B07 owns authenticated approval. A passing gate is not authority
to provision, copy bytes or switch a writer.
    """

    def __init__(self) -> None:
        self._notices: list[ApprovalNotice] = []
        self._overflow = False
        self._status = 'WAITING_FOR_APPROVAL'

    @workflow.signal
    def offer_approval(self, notice: ApprovalNotice) -> None:
        if len(self._notices) >= 32:
            self._overflow = True
        else:
            self._notices.append(notice)

    @workflow.query
    def gate_status(self) -> str:
        return self._status

    @workflow.run
    async def run(self, input: GateInput) -> GateResult:
        # SDK-managed clock and timer are replay-safe. No wall clock or I/O here.
        deadline = workflow.now() + timedelta(seconds=input.approval_timeout_seconds)
        binding = _binding(input)
        seen: set[str] = set()
        while True:
            if self._overflow:
                self._status = 'HELD'
                return GateResult('HELD', input.job_id, input.plan_id,
                                  input.plan_revision, input.plan_digest)
            remaining = deadline - workflow.now()
            if remaining <= timedelta(0):
                self._status = 'EXPIRED'
                return GateResult('EXPIRED', input.job_id, input.plan_id,
                                  input.plan_revision, input.plan_digest)
            try:
                await workflow.wait_condition(lambda: bool(self._notices), timeout=remaining)
            except TimeoutError:
                self._status = 'EXPIRED'
                return GateResult('EXPIRED', input.job_id, input.plan_id,
                                  input.plan_revision, input.plan_digest)
            notice = self._notices.pop(0)
            if ((notice.job_id, notice.organization_id, notice.tenant_id, notice.plan_id,
                 notice.plan_revision, notice.plan_digest) != binding
                    or not _valid_id(notice.approval_id)):
                self._status = 'HELD'
                return GateResult('HELD', input.job_id, input.plan_id,
                                  input.plan_revision, input.plan_digest)
            if notice.approval_id in seen:
                continue
            if len(seen) >= 32:
                self._status = 'HELD'
                return GateResult('HELD', input.job_id, input.plan_id,
                                  input.plan_revision, input.plan_digest)
            seen.add(notice.approval_id)
            self._status = 'CHECKING_APPROVAL'
            try:
                check = await workflow.execute_activity(
                    VERIFY_APPROVAL_ACTIVITY,
                    notice,
                    result_type=ApprovalCheck,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(maximum_attempts=1),
                )
            except ActivityError:
                self._status = 'HELD'
                return GateResult('HELD', input.job_id, input.plan_id,
                                  input.plan_revision, input.plan_digest)
            if (self._overflow or check.authorized is not True
                    or (check.job_id, check.organization_id, check.tenant_id, check.plan_id,
                        check.plan_revision, check.plan_digest) != binding
                    or check.revocation_epoch != input.revocation_epoch
                    or check.approval_id != notice.approval_id
                    or not _valid_digest(check.evidence_digest)):
                self._status = 'HELD'
                return GateResult('HELD', input.job_id, input.plan_id,
                                  input.plan_revision, input.plan_digest)
            self._status = 'GATE_PASSED'
            return GateResult('GATE_PASSED', input.job_id, input.plan_id, input.plan_revision,
                              input.plan_digest, check.approval_id, check.evidence_digest)
