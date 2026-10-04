"""Promote an independently observed application through the existing record owner.

Native IDs must already be observed TARGET histories in the approved workload
revision. This owner never creates a target identity from a placement name or
Terraform output, and never puts a newly created VM in an older snapshot.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from urllib.parse import urlsplit

from provisioner.controlplane.persistence import (AuditContext, EnterpriseRecordStore,
    TenantContext, canonical_record_digest)
from provisioner.controlplane.reconciliation.adapters.openstack_readback import OpenStackProjectReader
from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
from provisioner.domain.enterprise_records import (BindingPromotion, VerifiedBindingCutover,
    VerifiedWsdTransition, validate_record, validate_workload_successor)
from provisioner.execution.run_files import require, utcnow


def binding_key(binding):
    return tuple(binding[key] for key in
        ('endpointId', 'nativeScopeId', 'resourceKind', 'nativeId', 'platformFamily'))


def selected_promotions(workload, plan):
    """Complete one-to-one observed VM/disk/NIC histories, without mutation."""
    require(not validate_record(workload) and not validate_record(plan)
        and workload['kind'] == 'Workload' and plan['kind'] == 'MigrationPlan',
        'Valid complete canonical workload and exact plan are required')
    spec = plan['spec']; machines = {row['machineId']: row for row in workload['spec']['machines']}
    require(set(spec['selectedMachineIds']) == set(machines),
        'Whole-application acceptance requires every canonical workload member')
    promotions = []
    for mapping in spec['machineMappings']:
        machine = machines[mapping['machineId']]
        require(machine['disksComplete'] and machine['nicsComplete']
            and {row['diskId'] for row in machine['disks']} ==
                {row['diskId'] for row in mapping['diskMappings']}
            and {row['nicId'] for row in machine['nics']} ==
                {row['nicId'] for row in mapping['nicMappings']},
            'Canonical promotion requires all observed disks and NICs')
        for kind, rows, key in (('vm', [machine], 'machineId'),
                ('disk', machine['disks'], 'diskId'), ('nic', machine['nics'], 'nicId')):
            for row in rows:
                histories = {}
                for role, side in (('SOURCE', 'source'), ('TARGET', 'destination')):
                    scope = spec[side]
                    found = [history for history in row['bindings'] if history['role'] == role
                        and history['lastObservedSnapshotId'] == spec[side + 'SnapshotId']
                        and all(history['binding'][field] == scope[field]
                            for field in ('endpointId', 'nativeScopeId', 'platformFamily'))]
                    require(len(found) == 1,
                        'The current approved workload lacks one exact observed source/target history')
                    histories[role] = found[0]
                require(kind != 'vm' or histories['SOURCE']['binding'] == mapping['sourceBinding'],
                    'The canonical source VM differs from its approved mapping')
                promotions.append(BindingPromotion(kind, machine['machineId'], row[key],
                    binding_key(histories['SOURCE']['binding']), binding_key(histories['TARGET']['binding'])))
    require(len({row.source_binding for row in promotions}) == len(promotions)
        and len({row.target_binding for row in promotions}) == len(promotions),
        'A canonical binding cannot stand for two logical application resources')
    return tuple(promotions)


def promoted_record(previous, promotions, *, destination_wsd, transition=None):
    current = deepcopy(previous); current['metadata']['revision'] += 1
    selected = {(row.resource_kind, row.machine_id, row.component_id): row for row in promotions}
    for machine in current['spec']['machines']:
        for kind, rows, key in (('vm', [machine], 'machineId'),
                ('disk', machine['disks'], 'diskId'), ('nic', machine['nics'], 'nicId')):
            for row in rows:
                promotion = selected[(kind, machine['machineId'], row[key])]
                for history in row['bindings']:
                    identity = binding_key(history['binding'])
                    if identity == promotion.source_binding:
                        require(history['role'] == 'SOURCE', 'The old canonical source has already changed')
                        history['role'] = 'RETIRED'
                    if identity == promotion.target_binding:
                        require(history['role'] == 'TARGET', 'The staged canonical target has already changed')
                        history['role'] = 'SOURCE'
    if previous['metadata']['wsdId'] != destination_wsd:
        require(isinstance(transition, VerifiedWsdTransition), 'Authenticated WSD transition required')
        current['metadata']['wsdId'] = destination_wsd
        membership = current['spec']['membership']
        membership.update(state='ACCEPTED', candidateWsdId=None, transition=None)
        membership['history'].append(dict(fromWsdId=transition.from_wsd_id,
            toWsdId=transition.to_wsd_id, planId=transition.plan_id,
            planRevision=transition.plan_revision, planDigest=transition.plan_digest,
            grantDigest=transition.grant_digest, observationDigest=transition.observation_digest))
    return current


@dataclass(frozen=True)
class ApplicationPromotionRuntime:
    records: EnterpriseRecordStore
    authority: PostgresExecutionAuthority
    enrollment: NativeReadEnrollment
    ca_file: object

    def __post_init__(self):
        require(isinstance(self.records, EnterpriseRecordStore)
            and isinstance(self.authority, PostgresExecutionAuthority)
            and type(self.enrollment) is NativeReadEnrollment
            and self.enrollment.command.authority is self.authority
            and self.records._connect is self.enrollment.command.grants._connect,
            'Actual canonical record owner and independent native read enrollment required')

    @property
    def registry(self):
        # Record changes use the existing record owner; there is no second
        # native intent ledger and no native write permission in this runtime.
        return self.records

    def _observe_targets(self, lifecycle, promotions):
        scope = self.enrollment.scope
        from provisioner.controlplane.authority import PlanScope
        require(scope == PlanScope.from_record(lifecycle.to_dict()['destination_scope']),
            'The canonical promotion reader is scoped to another destination')
        observed = []
        for member in lifecycle.to_dict()['members']:
            fence = member['target_native_fence']; endpoint = urlsplit(fence['compute_endpoint'])
            reader = OpenStackProjectReader(self.enrollment, identity_endpoint=fence['identity_url'],
                ca_bundle=self.ca_file, alias=fence['cloud_alias'],
                compute_origin='https://' + endpoint.netloc)
            selected = [row for row in promotions if row.machine_id == member['machine_id']]
            vm = [row for row in selected if row.resource_kind == 'vm']
            disks = {row.target_binding[3] for row in selected if row.resource_kind == 'disk'}
            nics = {row.target_binding[3] for row in selected if row.resource_kind == 'nic'}
            require(len(vm) == 1 and vm[0].target_binding[3] == member['target']['native_id'],
                'The canonical target VM differs from the independently useful application')
            server = reader.get('compute', 'servers/' + vm[0].target_binding[3])['server']
            require(server.get('id') == member['target']['native_id']
                and server.get('tenant_id') == scope.native_scope_id and server.get('status') == 'ACTIVE'
                and server.get('OS-EXT-STS:task_state') is None
                and {row['id'] for row in server.get('os-extended-volumes:volumes_attached', [])} == disks,
                'The actual target VM attachment set differs from its complete canonical mapping')
            native = dict(server=server, volumes=[], ports=[])
            interfaces = reader.get('compute', 'servers/' + member['target']['native_id'] + '/os-interface')['interfaceAttachments']
            require(isinstance(interfaces, list) and len(interfaces) == len(nics)
                and {row.get('port_id') for row in interfaces} == nics,
                'The actual complete target NIC set differs from the canonical application mapping')
            native['interfaces'] = interfaces
            for identity in sorted(disks):
                volume = reader.get('volume', 'volumes/' + identity)['volume']
                require(volume.get('id') == identity and volume.get('status') == 'in-use'
                    and volume.get('multiattach') is False
                    and len(volume.get('attachments', [])) == 1
                    and volume['attachments'][0].get('server_id') == member['target']['native_id'],
                    'A canonical target disk is unavailable, shared or attached to another VM')
                native['volumes'].append(volume)
            require(fence['volume_id'] in disks, 'The final application data volume is not canonically mapped')
            for identity in sorted(nics):
                port = reader.get('network', 'ports/' + identity)['port']
                require(port.get('id') == identity and port.get('project_id', port.get('tenant_id')) == scope.native_scope_id
                    and port.get('device_id') == member['target']['native_id'] and port.get('status') == 'ACTIVE',
                    'A canonical target NIC is unavailable or belongs to another VM/project')
                native['ports'].append(port)
            observed.append(dict(member_id=member['machine_id'], observation_digest=canonical_record_digest(native)))
        self.enrollment.require_current()
        return observed

    def confirm_current_source(self, runner):
        """Read the already accepted current target; no no-op promotion is made."""
        from .recovery import ApplicationRecoveryRunner
        from provisioner.execution.neutron_observe import strict_loads
        require(type(runner) is ApplicationRecoveryRunner,
            'Only the concrete retained-target repair may confirm its existing accepted source')
        plan, artifact = strict_loads(runner.plan_bytes), strict_loads(runner.artifact_bytes)
        require(plan['spec']['source'] == plan['spec']['destination']
            and self.enrollment.admitted == runner.admitted
            and self.enrollment.selection_digest == canonical_record_digest(artifact),
            'Current-source confirmation differs from the exact approved retained-target repair')
        context = TenantContext(runner.admitted.organization_id, runner.admitted.tenant_id)
        stored = self.records.get(context, 'Workload', plan['spec']['workloadId'])
        require(stored is not None and stored.revision == plan['spec']['workloadRevision']
            and stored.record['metadata']['wsdId'] == plan['spec']['source']['securityDomainId']
            and stored.record['spec']['membership']['state'] == 'ACCEPTED',
            'The repaired target is not the current accepted canonical application source')
        mappings = {row['machineId']: row for row in plan['spec']['machineMappings']}
        require(set(mappings) == {row['machineId'] for row in stored.record['spec']['machines']},
            'Current-source repair must cover the complete canonical application')
        current = []
        for machine in stored.record['spec']['machines']:
            require(machine['disksComplete'] and machine['nicsComplete'],
                'Current-source repair lacks complete native disk/NIC associations')
            for kind, rows, key in (('vm', [machine], 'machineId'), ('disk', machine['disks'], 'diskId'),
                                    ('nic', machine['nics'], 'nicId')):
                for row in rows:
                    source = [history for history in row['bindings'] if history['role'] == 'SOURCE']
                    require(len(source) == 1 and source[0]['lastObservedSnapshotId'] == plan['spec']['sourceSnapshotId']
                        and all(source[0]['binding'][field] == plan['spec']['source'][field]
                            for field in ('endpointId', 'nativeScopeId', 'platformFamily')),
                        'A repaired canonical resource is not an independently observed current target source')
                    identity = binding_key(source[0]['binding'])
                    require(kind != 'vm' or source[0]['binding'] == mappings[machine['machineId']]['sourceBinding'],
                        'The approved current source differs from its observed existing VM')
                    current.append(BindingPromotion(kind, machine['machineId'], row[key], identity, identity))
        native = self._observe_targets(runner.lifecycle, current)
        runner._all_source_exclusions()
        self.authority.require_observation(runner.admitted, canonical_record_digest(artifact), 'DISCOVER_READ')
        return dict(format='hosting-canonical-current-application-source/1', job_id=runner.admitted.job_id,
            workload_id=plan['spec']['workloadId'], workload_revision=stored.revision, workload_digest=stored.digest,
            current_wsd_id=stored.record['metadata']['wsdId'], original_plan_digest=runner.admitted.plan_digest,
            native_target_observations=native, observed_at=utcnow().isoformat())

    def promote(self, runner, acceptance):
        from .application_lifecycle import ApplicationLifecycleRunner, LifecycleHeld
        from .recovery import ApplicationRecoveryRunner
        require(isinstance(runner, (ApplicationLifecycleRunner, ApplicationRecoveryRunner)) and isinstance(acceptance, dict)
            and acceptance.get('format') in {'hosting-application-cutover-acceptance/1',
                                           'hosting-application-postwrite-recovery-acceptance/1'}
            and acceptance.get('job_id') == runner.admitted.job_id
            and acceptance.get('lifecycle_digest') == runner.lifecycle.sha256,
            'Canonical promotion requires this actual complete independent application acceptance')
        from provisioner.execution.neutron_observe import strict_loads
        plan = strict_loads(runner.plan_bytes); artifact = strict_loads(runner.artifact_bytes)
        require(self.enrollment.admitted == runner.admitted
            and self.enrollment.selection_digest == canonical_record_digest(artifact),
            'The independently enrolled canonical reader differs from the original selected job')
        context = TenantContext(runner.admitted.organization_id, runner.admitted.tenant_id)
        stored = self.records.get(context, 'Workload', plan['spec']['workloadId'])
        if stored is None or stored.revision != plan['spec']['workloadRevision']:
            raise LifecycleHeld('CANONICAL_APPLICATION_PROMOTION_REQUIRED')
        try:
            promotions = selected_promotions(stored.record, plan)
        except ValueError:
            raise LifecycleHeld('CANONICAL_APPLICATION_PROMOTION_REQUIRED') from None
        for side in ('source', 'destination'):
            snapshot = self.records.get(context, 'ObservationSnapshot', plan['spec'][side + 'SnapshotId'])
            require(snapshot is not None and not validate_record(snapshot.record),
                'The exact immutable canonical source/target observation is unavailable')
            known = {binding_key(row['binding']) for row in snapshot.record['spec']['objects']
                if row['presence'] == 'PRESENT' and not row['missingFields']}
            require({getattr(row, 'source_binding' if side == 'source' else 'target_binding')
                for row in promotions} <= known,
                'The approved snapshot lacks an observed VM, disk or NIC in the canonical application')
        native = self._observe_targets(runner.lifecycle, promotions)
        # A new record write still requires current exact approval. Observation
        # of expired original writes never silently authorizes this transition.
        current_plan, current_artifact = self.authority.require_current(runner.admitted,
            canonical_record_digest(artifact), 'DESTINATION_ACTIVATE')
        require(current_plan == plan and current_artifact == artifact, 'The approved canonical plan changed')
        runner._all_source_exclusions()
        observation_digest = canonical_record_digest(dict(acceptance=acceptance, canonical_targets=native))
        grant_digest = canonical_record_digest([member['activation'] for member in acceptance['members']])
        meta, spec = plan['metadata'], plan['spec']; before = stored.record['metadata']
        cutover = VerifiedBindingCutover(before['organizationId'], before['tenantId'], before['workloadId'],
            before['wsdId'], meta['planId'], meta['revision'], meta['planDigest'],
            spec['sourceSnapshotId'], spec['destinationSnapshotId'], grant_digest, observation_digest, promotions)
        transition = None
        audit = AuditContext(self.enrollment.subject, runner.admitted.job_id)
        # PENDING, OBSERVED and ACCEPTED are one atomic existing record-owner
        # transaction. Intermediate membership states cannot leak, and a failed
        # promotion rolls back all history/audit changes together.
        with self.records._session(context) as connection, connection.cursor() as cursor:
            selected_plan, selected_artifact = self.authority.require_canonical_transition(
                runner.admitted, canonical_record_digest(artifact), cursor=cursor,
                operation_kind='DESTINATION_ACTIVATE')
            require((selected_plan, selected_artifact) == (plan, artifact),
                'The exact approved canonical transition changed')
            self.enrollment.require_current(cursor=cursor)
            locked = self.records._load(connection, context, 'Workload', spec['workloadId'], lock=True)
            require(locked is not None and (locked.revision, locked.digest) == (stored.revision, stored.digest),
                'The canonical application changed after independent final observation')
            stored = locked
            if before['wsdId'] != spec['destination']['securityDomainId']:
                transition = VerifiedWsdTransition(before['organizationId'], before['tenantId'], before['workloadId'],
                    before['wsdId'], spec['destination']['securityDomainId'], meta['planId'], meta['revision'],
                    meta['planDigest'], grant_digest, observation_digest)
                for state in ('PENDING', 'OBSERVED'):
                    value = deepcopy(stored.record); value['metadata']['revision'] += 1
                    value['spec']['membership'].update(state=state, candidateWsdId=transition.to_wsd_id,
                        transition=dict(planId=meta['planId'], planRevision=meta['revision'], planDigest=meta['planDigest'],
                            grantDigest=grant_digest, observationDigest=observation_digest))
                    stored = self.records.update_in_transaction(connection, context, value, stored.revision, audit)
            value = promoted_record(stored.record, promotions, destination_wsd=spec['destination']['securityDomainId'],
                transition=transition)
            require(not validate_workload_successor(stored.record, value, verified_transition=transition,
                verified_cutover=cutover, plan=plan), 'The exact canonical application transition is invalid')
            result = self.records.update_in_transaction(connection, context, value, stored.revision, audit,
                verified_transition=transition, verified_cutover=cutover, plan=plan)
        return dict(format='hosting-canonical-application-promotion/1', job_id=runner.admitted.job_id,
            workload_id=before['workloadId'], workload_revision=result.revision, workload_digest=result.digest,
            current_wsd_id=result.record['metadata']['wsdId'], original_plan_digest=meta['planDigest'],
            grant_digest=grant_digest, observation_digest=observation_digest,
            target_bindings=[list(row.target_binding) for row in promotions], observed_at=utcnow().isoformat())
