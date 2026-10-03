"""Locked PostgreSQL authority for the one live capacity/IPAM composition.

Selection and readback custody are trusted server-side dependencies. No HTTP
payload, copied WorkerGrant, success flag or caller-supplied database path can
be substituted for their current reads. This class performs no native writes.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from datetime import timedelta

from provisioner.allocations.transactions import ResourceBundle, ResourceAuthorityWindow
from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.jobs.repository import (
    _JOB_SELECT, _digest, _ensure_plan, _job, _payload_from_job, _tenant)
from provisioner.controlplane.persistence import TenantContext
from provisioner.execution import readback_core as c


class PostgresResourceAuthority:
    def __init__(self, connect, authority, selections, evidence, *, lease_seconds=300):
        if (not callable(connect)
                or not callable(getattr(authority,'revalidate_start',None))
                or not callable(getattr(selections,'load_verified',None))
                or not callable(getattr(evidence,'verify_resource_observation',None))
                or type(lease_seconds) is not int or not 1<=lease_seconds<=3600):
            raise TypeError('PostgreSQL, protected selections and independent readback verification required')
        self._connect=connect
        self._authority=authority
        self._selections=selections
        self._evidence=evidence
        self._lease_seconds=lease_seconds

    @contextmanager
    def locked(self, bundle: ResourceBundle, action: str, observations: tuple):
        if not isinstance(bundle,ResourceBundle) or action not in {
                'reserve','renew','confirm','release','inspect'}:
            raise AuthorityDenied('Exact admitted resource transaction required')
        requested=bundle.admitted
        context=TenantContext(requested.organization_id,requested.tenant_id)
        with self._connect() as connection, connection.cursor() as cursor:
            _tenant(cursor,context)
            cursor.execute('SELECT hosting_controlplane.lock_job_scope(%s, %s, %s)',
                           (context.organization_id,context.tenant_id,requested.job_id))
            if cursor.fetchone()!=(True,):
                raise AuthorityDenied('Scoped admitted job is unavailable')
            cursor.execute(f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                           'WHERE organization_id = %s AND tenant_id = %s AND job_id = %s',
                           (context.organization_id,context.tenant_id,requested.job_id))
            row=cursor.fetchone()
            if row is None:
                raise AuthorityDenied('Scoped admitted job is unavailable')
            job=_job(row)
            if ((job.plan_id,job.plan_revision,job.plan_digest,job.revocation_epoch)!=
                    (requested.plan_id,requested.plan_revision,requested.plan_digest,
                     requested.revocation_epoch)
                    or _digest(_payload_from_job(job))!=requested.payload_digest
                    or job.status not in {'STARTED','RUNNING'}):
                raise AuthorityDenied('Admitted resource job changed or is not running')
            cursor.execute('SELECT clock_timestamp()')
            at=cursor.fetchone()[0]
            # Locks the authoritative epoch and current plan/workload using
            # the same revalidation path as JobRepository and B10 grants.
            self._authority.revalidate_start(cursor,job,at)
            cursor.execute('SELECT revision, record_digest, record_json '
                           'FROM hosting_controlplane.enterprise_records '
                           'WHERE organization_id = %s AND tenant_id = %s '
                           "AND record_kind = 'MigrationPlan' AND record_id = %s",
                           (context.organization_id,context.tenant_id,job.plan_id))
            plan=_ensure_plan(cursor.fetchone(),context,job)
            execution=plan['spec'].get('execution')
            if (not isinstance(execution,dict)
                    or execution.get('format')!='hosting-execution-selection/1'
                    or execution.get('driver')!='openstack-linux-rebuild/1'
                    or execution.get('artifactDigest')!=bundle.selection_digest
                    or (plan['spec']['workloadId'],plan['spec']['workloadRevision'])!=
                       (bundle.workload_id,bundle.workload_revision)):
                raise AuthorityDenied('Canonical plan does not select this exact resource execution')
            selection=self._selections.load_verified(bundle.selection_digest)
            if (not isinstance(selection,dict)
                    or selection.get('resourceBundleDigest')!=bundle.digest
                    or (selection.get('workloadId'),selection.get('workloadRevision'),
                        selection.get('source'),selection.get('destination'))!=
                       (plan['spec']['workloadId'],plan['spec']['workloadRevision'],
                        plan['spec']['source'],plan['spec']['destination'])
                    or any(pool.scope not in (job.source,job.destination) for pool in bundle.pools)):
                raise AuthorityDenied('Protected execution selection or native scope differs')
            for observation in observations:
                # Implementations must authenticate evidence custody and re-read
                # resources/operation uncertainty, including fenced no-effect.
                # A return value is deliberately ignored; refusal must raise.
                self._evidence.verify_resource_observation(cursor,bundle,action,observation)
            evidence_digest=c.digest({'job':asdict(requested),'action':action,
                                      'selection_sha256':bundle.selection_digest,
                                      'resource_bundle_sha256':bundle.digest,
                                      'observed_at':at.isoformat()})
            yield ResourceAuthorityWindow(job.source,job.destination,at,
                                          at+timedelta(seconds=self._lease_seconds),evidence_digest)

    @contextmanager
    def locked_ipam(self,bundle,job,action):
        from provisioner.allocations.ipam_transactions import selection
        from provisioner.allocations.netbox_ipam import ACTIONS
        if action not in ACTIONS:
            raise AuthorityDenied('Unknown selected IPAM transition')
        with self.locked(bundle,'inspect',()) as window:
            artifact=self._selections.load_verified(bundle.selection_digest)
            allocations=artifact.get('ipamSelections')
            if (not isinstance(allocations,list) or not allocations
                    or len(allocations)>1000
                    or sum(item==selection(job) for item in allocations)!=1):
                raise AuthorityDenied('Protected execution artifact does not select this exact IPAM allocation')
            yield window
