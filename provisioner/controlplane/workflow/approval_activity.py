"""Server-side verification Activity for a Temporal approval notification.

The Signal contains no authority. The Activity locks and rechecks the current
tenant-scoped job, plan, workload, approval quorum and revocation epoch using
the B07 authority in one PostgreSQL transaction. It performs no native work.
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable

from temporalio import activity

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.jobs.repository import _JOB_SELECT, _digest, _job, _tenant
from provisioner.controlplane.persistence import TenantContext

from .admitted_job import AdmittedInput, VERIFY_ADMITTED_JOB_ACTIVITY
from .approval_gate import (ApprovalCheck, ApprovalNotice,
                            VERIFY_APPROVAL_ACTIVITY, _valid_id)


class PostgresApprovalVerifier:
    def __init__(self, connect: Callable, authority):
        if not callable(connect) or not callable(getattr(authority, 'revalidate_start', None)):
            raise ValueError('A scoped PostgreSQL connection and B07 authority are required')
        self._connect = connect
        self._authority = authority

    @activity.defn(name=VERIFY_APPROVAL_ACTIVITY)
    def verify(self, notice: ApprovalNotice) -> ApprovalCheck:
        if not isinstance(notice, ApprovalNotice) or not all(_valid_id(value) for value in (
                notice.job_id, notice.organization_id, notice.tenant_id,
                notice.plan_id, notice.approval_id)):
            raise AuthorityDenied('Malformed approval notification')
        return self._verify(notice, approval_id=notice.approval_id)

    @activity.defn(name=VERIFY_ADMITTED_JOB_ACTIVITY)
    def verify_job(self, job: AdmittedInput) -> ApprovalCheck:
        if not isinstance(job, AdmittedInput):
            raise AuthorityDenied('An exact admitted job reference is required')
        return self._verify(job, approval_id=None)

    def _verify(self, requested: AdmittedInput | ApprovalNotice, *,
                approval_id: str | None) -> ApprovalCheck:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _tenant(cursor, TenantContext(requested.organization_id, requested.tenant_id))
                cursor.execute(
                    'SELECT hosting_controlplane.lock_job_scope(%s, %s, %s)',
                    (requested.organization_id, requested.tenant_id, requested.job_id))
                if cursor.fetchone() != (True,):
                    raise AuthorityDenied('Scoped job does not exist')
                cursor.execute(
                    f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                    'WHERE organization_id = %s AND tenant_id = %s AND job_id = %s',
                    (requested.organization_id, requested.tenant_id, requested.job_id))
                row = cursor.fetchone()
                if row is None:
                    raise AuthorityDenied('Scoped job does not exist')
                job = _job(row)
                if ((job.plan_id, job.plan_revision, job.plan_digest) !=
                        (requested.plan_id, requested.plan_revision, requested.plan_digest)
                        or (isinstance(requested, AdmittedInput)
                            and job.revocation_epoch != requested.revocation_epoch)
                        or not job.approval_ids
                        or (approval_id is not None and approval_id not in job.approval_ids)
                        or job.status in ('HELD', 'FAILED', 'CANCELLED', 'SUCCEEDED')):
                    raise AuthorityDenied('Job, plan or approval notification is stale')
                cursor.execute('SELECT clock_timestamp()')
                at: datetime = cursor.fetchone()[0]
                self._authority.revalidate_start(cursor, job, at)
                # The digest describes the authority observation, not an
                # independently signed artifact or downstream execution grant.
                observation_digest = _digest({
                    'job_id': job.job_id, 'organization_id': job.organization_id,
                    'tenant_id': job.tenant_id, 'plan_id': job.plan_id,
                    'plan_revision': job.plan_revision, 'plan_digest': job.plan_digest,
                    'revocation_epoch': job.revocation_epoch,
                    'approval_ids': job.approval_ids,
                })
                return ApprovalCheck(True, job.job_id, job.organization_id,
                                     job.tenant_id, job.plan_id, job.plan_revision,
                                     job.plan_digest, job.revocation_epoch,
                                     approval_id or job.approval_ids[0], observation_digest)
