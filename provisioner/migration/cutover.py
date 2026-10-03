"""Selected source shutdown and conservative target-write recovery projection.

Native power-off is executable under the existing worker grant and native intent
registry. It is only one part of writer exclusion. No isolated topology,
application quiesce, persistent restart fence, DNS switch or production activation
is invented here; an absent native owner leaves the next stage explicitly held.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import time

from provisioner.controlplane.authority import AuthorityService, PlanScope
from provisioner.controlplane.persistence import TenantContext, canonical_record_digest
from provisioner.controlplane.persistence.store import OwnerLease
from provisioner.controlplane.reconciliation import NativeOperation, NativeOperationRegistry
from provisioner.controlplane.worker.grants import VerifiedWorkerIdentity
from provisioner.domain.enterprise_records import validate_record
from provisioner.execution import execution_journal, vsphere_power
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import digest, encoded, private_path, require, utcnow

FORMAT = 'hosting-application-cutover-selection/1'
_IMPLEMENTED_DIRECTION = frozenset({('vmware', 'openstack')})


@dataclass(frozen=True)
class SourceFenceSelection:
    canonical: bytes

    def __post_init__(self):
        require(isinstance(self.canonical, bytes) and len(self.canonical) <= 16 * 1024 * 1024,
                'Bounded canonical source-fence selection required')
        body = strict_loads(self.canonical)
        require(encoded(body) == self.canonical and isinstance(body, dict)
                and set(body) == {'format', 'source_scope', 'destination_scope', 'source_members'}
                and body['format'] == FORMAT,
                'Exact source-fence selection required')
        source, target = (PlanScope.from_record(body[key]) for key in
                          ('source_scope', 'destination_scope'))
        require((source.platform_family, target.platform_family) in _IMPLEMENTED_DIRECTION
                and (source.organization_id, source.tenant_id) ==
                    (target.organization_id, target.tenant_id),
                'Selected source fence is only VMware to OpenStack')
        members = body['source_members']
        require(isinstance(members, list) and 1 <= len(members) <= 32,
                'Complete selected source members are required')
        unique = {key: set() for key in ('machine_id', 'step_id', 'operation_id', 'native_id')}
        for row in members:
            require(isinstance(row, dict) and set(row) ==
                    {'machine_id', 'step_id', 'operation_id', 'native_id', 'power_request'},
                    'Exact source power descriptor required')
            for key, known in unique.items():
                require(isinstance(row[key], str)
                        and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', row[key])
                        and row[key] not in known, 'Source power identities cannot be duplicated')
                known.add(row[key])
            resource = vsphere_power.validate(row['power_request'])
            require(row['power_request']['desired_power'] == 'poweredOff'
                    and resource['moid'] == row['native_id'],
                    'Source fencing must select the exact reviewed shutdown request')

    @classmethod
    def from_record(cls, body):
        return cls(encoded(body))

    @property
    def sha256(self):
        return canonical_record_digest(self.to_dict())

    def to_dict(self):
        return strict_loads(self.canonical)


@dataclass(frozen=True)
class SourceWorkerRuntime:
    authority: AuthorityService
    registry: NativeOperationRegistry
    context: TenantContext
    lease: OwnerLease
    identity: VerifiedWorkerIdentity
    credential: object
    grant_id: str
    lease_key: str
    session: str
    ca_file: Path | None = None

    def __post_init__(self):
        require(isinstance(self.authority, AuthorityService)
                and isinstance(self.registry, NativeOperationRegistry)
                and isinstance(self.context, TenantContext)
                and isinstance(self.lease, OwnerLease)
                and isinstance(self.identity, VerifiedWorkerIdentity)
                and isinstance(self.grant_id, str) and self.grant_id
                and isinstance(self.lease_key, str) and self.lease_key
                and isinstance(self.session, str) and self.session,
                'Enrolled source worker, native registry and ephemeral vCenter credential required')


class _SourcePowerGuard:
    def __init__(self, runtime, row, plan):
        self.runtime, self.row, self.plan = runtime, row, plan
        self.scope = PlanScope.from_record(plan['spec']['source'])
        self.command_authority = None
        self.claimed = False

    def require_current(self):
        runtime = self.runtime
        grant, deadline = runtime.authority.require_worker_step_window(
            runtime.credential, runtime.grant_id, step_id=self.row['step_id'],
            operation_id=self.row['operation_id'], operation_kind='SOURCE_FENCE',
            operation_scope=self.scope)
        meta, spec = self.plan['metadata'], self.plan['spec']
        require((grant.organization_id, grant.tenant_id, grant.plan_id,
                 grant.plan_revision, grant.plan_digest, grant.source, grant.destination) ==
                (meta['organizationId'], meta['tenantId'], meta['planId'], meta['revision'],
                 meta['planDigest'], self.scope, PlanScope.from_record(spec['destination'])),
                'Source power grant differs from the exact approved execution plan')
        if self.command_authority is not None:
            if self.claimed:
                self.command_authority.require_current(grant)
            else:
                self.command_authority.require_admission(grant)
        return deadline


class _GuardedPowerClient(vsphere_power.Client):
    """The actual fixed VMware transport, with live checks on every request."""
    def __init__(self, request, session, guard, ca_file):
        self.guard = guard
        super().__init__(request, session, ca_file)

    def _request(self, *args, **kwargs):
        deadline = self.guard.require_current()
        self.deadline = min(self.deadline, time.monotonic() +
                            (deadline - utcnow()).total_seconds())
        result = super()._request(*args, **kwargs)
        self.guard.require_current()
        return result


class SourceFenceRunner:
    """A real source-side power owner; every native uncertainty is retained."""
    def __init__(self, *, job_id, plan, execution_artifact, selection, ledger,
                 source_root):
        require(isinstance(plan, dict) and plan.get('kind') == 'MigrationPlan'
                and not validate_record(plan) and isinstance(selection, SourceFenceSelection),
                'Exact canonical migration plan and source descriptor required')
        execution = plan['spec'].get('execution', {})
        require(execution.get('format') == 'hosting-execution-selection/1'
                and execution.get('driver') == 'openstack-linux-rebuild/1'
                and execution.get('artifactDigest') == canonical_record_digest(execution_artifact)
                and execution_artifact.get('cutoverSelectionDigest') == selection.sha256,
                'Canonical plan does not approve this exact source-fence selection')
        body = selection.to_dict()
        require(plan['spec']['source'] == body['source_scope']
                and plan['spec']['destination'] == body['destination_scope']
                and plan['spec']['route']['method'] == 'REBUILD_RESTORE'
                and plan['spec']['route']['guestProfile'] == 'linux-ubuntu-2404',
                'Source fence differs from the selected application route')
        expected = {(row['machineId'], row['sourceBinding']['nativeId'])
                    for row in plan['spec']['machineMappings']}
        require(expected == {(row['machine_id'], row['native_id'])
                             for row in body['source_members']},
                'Source fence must cover every selected original source VM')
        require(isinstance(job_id, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', job_id),
                'Exact admitted source job identity required')
        self.job_id, self.selection = job_id, selection
        self.plan_bytes = encoded(plan)
        self.ledger = private_path(ledger, directory=True)
        self.source_root = Path(source_root)

    def source_fence(self, machine_id, *, runtime, power_authority, resume=False,
                     command_authority=None):
        from .authority import ApplicationCommandAuthority
        require(isinstance(runtime, SourceWorkerRuntime), 'Trusted source power runtime required')
        require(isinstance(command_authority, ApplicationCommandAuthority)
                and command_authority.admitted.job_id == self.job_id
                and command_authority.operation_kind == 'SOURCE_FENCE'
                and command_authority.identity == runtime.identity
                and command_authority.selection_digest ==
                    strict_loads(self.plan_bytes)['spec']['execution']['artifactDigest'],
                'Source commands must bind the exact admitted execution selection')
        members = [row for row in self.selection.to_dict()['source_members']
                   if row['machine_id'] == machine_id]
        require(len(members) == 1, 'Source machine is absent from the approved fence selection')
        row = members[0]
        plan = strict_loads(self.plan_bytes)
        guard = _SourcePowerGuard(runtime, row, plan)
        guard.command_authority = command_authority
        guard.claimed = resume
        scope = guard.scope
        require((runtime.lease.binding.platform_family, runtime.lease.binding.endpoint_id,
                 runtime.lease.binding.native_scope_id, runtime.lease.binding.resource_kind,
                 runtime.lease.binding.native_id) ==
                ('vmware', scope.endpoint_id, scope.native_scope_id, 'vm', row['native_id'])
                and (runtime.identity.subject, runtime.identity.site_id) ==
                    (runtime.lease.worker_id, scope.site_id)
                and (runtime.context.organization_id, runtime.context.tenant_id,
                     runtime.identity.organization_id, runtime.identity.tenant_id,
                     runtime.lease.organization_id, runtime.lease.tenant_id,
                     runtime.lease.security_domain_id, runtime.lease.workload_id) ==
                    (scope.organization_id, scope.tenant_id, scope.organization_id, scope.tenant_id,
                     scope.organization_id, scope.tenant_id, scope.security_domain_id,
                     plan['spec']['workloadId']),
                'Source worker lease must bind the exact reviewed original VM')
        guard.require_current()
        request = row['power_request']
        vsphere_power.authorize(request, power_authority, resume=resume)
        client = _GuardedPowerClient(request, runtime.session, guard, runtime.ca_file)
        if not resume:
            runtime.registry.prepare(runtime.context, runtime.lease, scope,
                job_id=self.job_id, grant_id=runtime.grant_id, step_id=row['step_id'],
                lease_key=runtime.lease_key, worker_identity=runtime.identity,
                operation_id=row['operation_id'], operation_kind='SOURCE_FENCE',
                request_digest=digest(encoded(dict(descriptor=row, authority=power_authority))))
            require(runtime.registry.claim_once(runtime.context, runtime.lease, scope,
                                                row['operation_id'], runtime.identity),
                    'Source power intent was already claimed; read-only observation is required')
        guard.claimed = True
        try:
            result = vsphere_power.execute(request, power_authority, self.ledger, client,
                execute_approved_change=not resume, resume=resume, root=self.source_root)
            # The underlying owner returns a retained completion for an already
            # completed request. Repeat the real task/VM/activity readback so a
            # restarted or changed source cannot be represented as still off.
            native_scope = dict(owner='vsphere-power', origin=request['snapshot']['origin'],
                                vm_moid=row['native_id'])
            with execution_journal.locked(self.ledger, native_scope) as log:
                attempts = vsphere_power.attempt_state(log.events)
                require(attempts and attempts[-1]['complete'] is not None
                        and attempts[-1]['request'] == request,
                        'The exact source shutdown has no retained completed task')
                result = vsphere_power.observe_completion(request, attempts[-1], client)
            guard.require_current()
            # A completed power task is genuine native evidence, but it cannot
            # exclude a later HA restart, a reconnect, or another application writer.
            return dict(format='hosting-application-source-power-result/1',
                        status='SOURCE_POWERED_OFF_RESTART_EXCLUSION_HELD',
                        job_id=self.job_id, machine_id=machine_id,
                        selection_sha256=self.selection.sha256, native_power=result,
                        required_next_evidence=['CURRENT_RESTART_AND_LATE_REQUEST_EXCLUSION',
                                                'CURRENT_OTHER_APPLICATION_WRITER_EXCLUSION',
                                                'APPLICATION_QUIESCE_AND_FINAL_CONSISTENCY_POINT'],
                        final_sync_authorized=False, traffic_switch_authorized=False,
                        production_activation=False, native_qualification=False)
        except BaseException:
            try:
                runtime.registry.mark_uncertain(runtime.context, row['operation_id'], runtime.identity.subject)
            except Exception:
                pass
            raise


def recovery_projection(plan, *, target_activation: NativeOperation | None,
                        job_id, original_activation_operation_id):
    """Read-only operator choices from the independently loaded native intent.

    Any claimed/uncertain activation can have committed writes even when no
    acknowledgement or first-write observation was received. The actual reverse
    sync, restore or forward-repair owner must separately authorize and execute.
    """
    require(isinstance(plan, dict) and plan.get('kind') == 'MigrationPlan'
            and not validate_record(plan), 'Exact canonical plan is required for recovery projection')
    require(isinstance(original_activation_operation_id, str)
            and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', original_activation_operation_id)
            and isinstance(job_id, str)
            and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', job_id),
            'Exact original target activation identity required')
    phase = 'TARGET_WRITE_STATE_UNKNOWN'
    if target_activation is not None:
        require(isinstance(target_activation, NativeOperation)
                and target_activation.operation_id == original_activation_operation_id
                and target_activation.job_id == job_id
                and target_activation.operation_kind == 'DESTINATION_ACTIVATE'
                and target_activation.workload_id == plan['spec']['workloadId']
                and (target_activation.binding.platform_family,
                     target_activation.binding.endpoint_id,
                     target_activation.binding.native_scope_id,
                     target_activation.security_domain_id) ==
                    (plan['spec']['destination']['platformFamily'],
                     plan['spec']['destination']['endpointId'],
                     plan['spec']['destination']['nativeScopeId'],
                     plan['spec']['destination']['securityDomainId']),
                'Recovery projection must load the original target activation intent')
        if target_activation.state == 'PREPARED':
            phase = 'BEFORE_TARGET_WRITES_REQUIRES_CURRENT_EXCLUSION'
        elif target_activation.state in {'IN_FLIGHT', 'TASK_ACCEPTED', 'UNCERTAIN'}:
            phase = 'TARGET_WRITES_POSSIBLE_RECONCILE_COMMITTED_DATA'
        elif target_activation.state == 'RESOLVED' and target_activation.outcome == 'EFFECT_PRESENT':
            phase = 'AFTER_TARGET_WRITES_RECONCILE_COMMITTED_DATA'
        elif target_activation.state == 'RESOLVED' and target_activation.outcome == 'NO_EFFECT':
            # Native no-effect requires the registry's actual late-worker fence
            # and quorum; displaying that retained state does not keep it fresh.
            phase = 'BEFORE_TARGET_WRITES_REQUIRES_CURRENT_EXCLUSION'
    return dict(format='hosting-application-recovery-options/1',
                job_id=job_id, plan_id=plan['metadata']['planId'], plan_revision=plan['metadata']['revision'],
                plan_digest=plan['metadata']['planDigest'], target_write_boundary=phase,
                actions=['READ_CURRENT_NATIVE_AND_WRITER_STATE',
                         'SELECT_REVERSE_SYNC_RESTORE_OR_FORWARD_REPAIR'] if
                        phase not in {'BEFORE_TARGET_WRITES_REQUIRES_CURRENT_EXCLUSION'} else
                        ['READ_CURRENT_NATIVE_AND_WRITER_STATE',
                         'REVIEW_PRE_WRITE_SOURCE_RETURN_WITH_CURRENT_TARGET_EXCLUSION'],
                source_restart_authorized=False, source_retirement_authorized=False,
                capacity_release_authorized=False, production_activation=False)
