"""Separately approved, retained-target repair after application writes.

This owner never restarts the old source. It consumes the original committed
target capture and persistent source/target exclusions, then runs four concrete
Nova/Cinder, Restic and isolated-systemd phases with new B10/B11 identities.
Unknown original effects need independent observation, not another dispatch.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re

from provisioner.controlplane.authority import PlanScope
from provisioner.controlplane.persistence import canonical_record_digest
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
from provisioner.execution import execution_journal
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import digest, encoded, private_path, require
from .application_lifecycle import ApplicationLifecycleRunner, ApplicationRepositoryRuntime, LifecycleHeld
from .lifecycle import ApplicationLifecycleSelection, LifecycleCommandGuard
from .native_openstack import OpenStackApplicationRuntime
from .remote_app import ApplicationGuestRuntime, ApplicationHealthReadRuntime

FORMAT = 'hosting-application-recovery-selection/1'
DRIVER = 'application-postwrite-recovery/1'
FORWARD_PHASES = ('TARGET_REATTACH', 'TARGET_START', 'FORWARD_REPAIR', 'FORWARD_ACTIVATE')
_HASH = re.compile(r'[0-9a-f]{64}')
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}')


@dataclass(frozen=True)
class ApplicationRecoverySelection:
    canonical: bytes

    def __post_init__(self):
        require(isinstance(self.canonical, bytes) and len(self.canonical) <= 1024 * 1024,
            'A bounded immutable application recovery descriptor is required')
        body = strict_loads(self.canonical)
        require(isinstance(body, dict) and encoded(body) == self.canonical and set(body) ==
            {'format', 'mode', 'originalAdmitted', 'originalArtifactDigest', 'originalLifecycleDigest',
             'currentLifecycleDigest', 'captures'} and body['format'] == FORMAT
            and body['mode'] in {'FORWARD_REPAIR', 'REVERSE_SYNC', 'RESTORE_CAPTURE'},
            'An exact separately approved committed-data recovery purpose is required')
        original = AdmittedInput(**body['originalAdmitted'])
        require(asdict(original) == body['originalAdmitted'] and all(_HASH.fullmatch(body[key]) for key in
            ('originalArtifactDigest', 'originalLifecycleDigest', 'currentLifecycleDigest'))
            and body['currentLifecycleDigest'] != body['originalLifecycleDigest'],
            'Recovery must preserve the original admission and select new phase identities')
        require(isinstance(body['captures'], list) and 1 <= len(body['captures']) <= 32,
            'Recovery must cover the complete bounded application capture set')
        members = set()
        for row in body['captures']:
            require(isinstance(row, dict) and set(row) == {'memberId', 'sourceFenceReceiptDigest',
                'activationReceiptDigest', 'captureReceiptDigest'} and _ID.fullmatch(row['memberId'])
                and row['memberId'] not in members and all(_HASH.fullmatch(row[key]) for key in
                    ('sourceFenceReceiptDigest', 'activationReceiptDigest', 'captureReceiptDigest')),
                'Every recovered member needs its exact original source, activation and committed capture')
            members.add(row['memberId'])

    @classmethod
    def from_record(cls, value):
        return cls(encoded(value))

    def to_dict(self):
        return strict_loads(self.canonical)

    @property
    def sha256(self):
        return canonical_record_digest(self.to_dict())

    @property
    def capture_receipts_digest(self):
        return canonical_record_digest(self.to_dict()['captures'])

    @property
    def members(self):
        return tuple(row['memberId'] for row in self.to_dict()['captures'])

    def plan_purpose(self):
        body = self.to_dict()
        return dict(format='hosting-application-recovery-plan/1', mode=body['mode'],
            originalJobId=body['originalAdmitted']['job_id'],
            originalPlanDigest=body['originalAdmitted']['plan_digest'],
            originalArtifactDigest=body['originalArtifactDigest'],
            originalLifecycleDigest=body['originalLifecycleDigest'],
            captureReceiptsDigest=self.capture_receipts_digest)

    def require_plan(self, plan, artifact):
        body = self.to_dict()
        require(body['mode'] == 'FORWARD_REPAIR' and plan['spec'].get('applicationRecovery') == self.plan_purpose()
            and plan['spec']['execution']['driver'] == artifact.get('driver') == DRIVER
            and artifact.get('applicationRecoverySelectionDigest') == self.sha256
            and artifact.get('applicationLifecycleSelectionDigest') == body['currentLifecycleDigest']
            and plan['spec']['execution']['artifactDigest'] == canonical_record_digest(artifact)
            and set(plan['spec']['selectedMachineIds']) == set(self.members)
            and plan['metadata']['planDigest'] != body['originalAdmitted']['plan_digest'],
            'The current repair approval differs from its exact separately approved original purpose')
        return self

    def require_forward_plan(self, plan, artifact, lifecycle):
        body = self.to_dict(); native = lifecycle.to_dict(); target = native['destination_scope']
        allowed = ((native['source_scope'], target), (target, target))
        self.require_plan(plan, artifact)
        require((plan['spec']['source'], plan['spec']['destination']) in allowed
            and body['currentLifecycleDigest'] == lifecycle.sha256,
            'The current repair approval must be a new exact retained-target purpose, not source rollback authority')


@dataclass(frozen=True)
class ApplicationRecoveryRuntime:
    """Original protected owners retained across the new approved recovery job."""
    authority: PostgresExecutionAuthority
    original: ApplicationLifecycleRunner

    def __post_init__(self):
        require(isinstance(self.authority, PostgresExecutionAuthority)
            and isinstance(self.original, ApplicationLifecycleRunner),
            'Recovery requires the actual protected original application and current execution authority')

    @property
    def registry(self):
        return self.original.evidence.registry


class ApplicationRecoveryRunner:
    def __init__(self, *, admitted, plan, artifact, lifecycle, selection, runtime, ledger):
        require(isinstance(admitted, AdmittedInput) and type(selection) is ApplicationRecoverySelection
            and type(runtime) is ApplicationRecoveryRuntime and type(lifecycle) is ApplicationLifecycleSelection,
            'Concrete original custody and a separately approved repair are required')
        selection.require_forward_plan(plan, artifact, lifecycle)
        body, original = selection.to_dict(), runtime.original
        require(asdict(original.admitted) == body['originalAdmitted'] and admitted.job_id != original.admitted.job_id
            and canonical_record_digest(strict_loads(original.artifact_bytes)) == body['originalArtifactDigest']
            and original.lifecycle.sha256 == body['originalLifecycleDigest']
            and lifecycle.to_dict()['source_scope'] == original.lifecycle.to_dict()['source_scope']
            and lifecycle.to_dict()['destination_scope'] == original.lifecycle.to_dict()['destination_scope']
            and 'applicationDatabaseSelectionDigest' not in artifact
            and original.database_final_proof is None,
            'This retained-file target repair cannot borrow another original job or a SQL repair proof')
        current = {row['machine_id']: row for row in lifecycle.to_dict()['members']}
        captured = {row['memberId']: row for row in body['captures']}
        require(set(current) == set(captured) == {row['machine_id'] for row in original.lifecycle.to_dict()['members']},
            'A repaired application must cover every original member')
        for member_id, member in current.items():
            old = original.lifecycle.member(member_id)
            # New source code/expiry is approved by the new selection; the actual
            # native guests, image, data, repository and finite controls stay fixed.
            for key in set(member) - {'phases', 'forward_target_path', 'rehearsal_path', 'source', 'target',
                                      'source_export', 'target_export'}:
                require(member[key] == old[key], 'Repair changed original application data or retained native exclusion')
            for side in ('source', 'target'):
                require({key: value for key, value in member[side].items() if key != 'action_runtime'} ==
                    {key: value for key, value in old[side].items() if key != 'action_runtime'},
                    'Repair changed its original guest, executable, useful health or data disk')
                require({key: value for key, value in member[side + '_export'].items() if key != 'valid_until'} ==
                    {key: value for key, value in old[side + '_export'].items() if key != 'valid_until'},
                    'Repair changed the original committed-data repository or consistency identity')
            require(member['forward_target_path'] != old['forward_target_path']
                and member['rehearsal_path'] != old['rehearsal_path']
                and not ({row['operation_id'] for row in member['phases'].values()} &
                         {row['operation_id'] for row in old['phases'].values()})
                and not ({row['step_id'] for row in member['phases'].values()} &
                         {row['step_id'] for row in old['phases'].values()}),
                'Repair needs new isolated staging and separately named native phase operations')
        source_side = 'target' if plan['spec']['source'] == plan['spec']['destination'] else 'source'
        require(set(plan['spec']['selectedDatasetIds']) == {row['dataset_id'] for row in current.values()}
            and {(row['machineId'], row['sourceBinding']['nativeId']) for row in plan['spec']['machineMappings']} ==
                {(row['machine_id'], row[source_side]['native_id']) for row in current.values()},
            'The new canonical repair must select the actual current target source and complete file dataset set')
        self.admitted, self.plan_bytes, self.artifact_bytes = admitted, encoded(plan), encoded(artifact)
        self.lifecycle, self.selection, self.runtime, self.original = lifecycle, selection, runtime, original
        self.evidence = original.evidence
        self.ledger = private_path(ledger, directory=True)

    def _scope(self, member_id, phase):
        return dict(owner='application-postwrite-recovery', job_id=self.admitted.job_id, member_id=member_id,
            phase=phase, recovery_digest=self.selection.sha256, lifecycle_sha256=self.lifecycle.sha256,
            artifact_sha256=canonical_record_digest(strict_loads(self.artifact_bytes)),
            plan_digest=self.admitted.plan_digest)

    def _all_source_exclusions(self):
        return {member['machine_id']: self.original_capture(member['machine_id'], detached=False)[1]['SOURCE_FENCE']
            for member in self.lifecycle.to_dict()['members']}

    def receipt(self, member_id, phase):
        require(phase in FORWARD_PHASES, 'Only the fixed retained-target repair graph is executable')
        with execution_journal.locked(self.ledger, self._scope(member_id, phase)) as log:
            started, result = ApplicationLifecycleRunner._state(log.events)
        if result is None:
            raise LifecycleHeld('ORIGINAL_APPLICATION_EFFECT_REQUIRES_RECONCILIATION')
        require(result['original_intent'] == started['original_intent'] and result['selection_sha256'] == self.lifecycle.sha256
            and result['plan_digest'] == self.admitted.plan_digest
            and result['observations']['recovery_selection_digest'] == self.selection.sha256,
            'The original retained-target repair result was rebound')
        return result

    def independently_resolved(self, member_id, phase):
        result = self.receipt(member_id, phase)
        return result, self.evidence.require_resolved(result, PlanScope.from_record(self.lifecycle.to_dict()['destination_scope']))

    def original_capture(self, member_id, *, detached=True):
        self.runtime.authority.require_observation(self.original.admitted,
            self.selection.to_dict()['originalArtifactDigest'], 'SOURCE_FENCE')
        row = next(row for row in self.selection.to_dict()['captures'] if row['memberId'] == member_id)
        facts = {}
        for phase, key in (('SOURCE_FENCE', 'sourceFenceReceiptDigest'), ('ACTIVATE', 'activationReceiptDigest'),
                           ('POSTWRITE_CAPTURE', 'captureReceiptDigest')):
            receipt = self.original.receipt(member_id, phase)
            require(canonical_record_digest(receipt) == row[key], 'The original committed-data repair proof changed')
            if phase == 'SOURCE_FENCE' or (phase == 'POSTWRITE_CAPTURE' and detached):
                scope = PlanScope.from_record(self.original.lifecycle.to_dict()[
                    'source_scope' if phase == 'SOURCE_FENCE' else 'destination_scope'])
                facts[phase] = self.original.evidence.require_resolved(receipt, scope)
            facts[phase + '_receipt'] = receipt
        capture = facts['POSTWRITE_CAPTURE_receipt']['observations']['committed_data_capture']
        require(facts['POSTWRITE_CAPTURE_receipt']['observations']['persistent_disk_exclusion']['state'] ==
            'NATIVE_DATA_VOLUME_DETACHED_PERSISTENTLY'
            and capture['data']['useful_bytes'] <= self.lifecycle.member(member_id)['max_bytes'],
            'Repair requires the original bounded committed target capture and persistent volume exclusion')
        return capture, facts

    def _prerequisites(self, member_id, phase):
        capture, original = self.original_capture(member_id, detached=phase == 'TARGET_REATTACH')
        previous = {'TARGET_START': 'TARGET_REATTACH', 'FORWARD_REPAIR': 'TARGET_START',
                    'FORWARD_ACTIVATE': 'FORWARD_REPAIR'}.get(phase)
        if previous:
            self.independently_resolved(member_id, previous)
        return capture, original

    def _restore(self, guest, authority, repository):
        guard, member = authority.intent_guard, authority.intent_guard.member
        require(type(repository) is ApplicationRepositoryRuntime and repository.guest is guest,
            'The current repaired-target repository owner is required')
        capture, _original = self._prerequisites(guard.member_id, 'FORWARD_REPAIR')
        guest.action(authority, 'IMAGE_OBSERVE', {})
        ApplicationLifecycleRunner._service_off(guest, authority, member['target'])
        readonly = guest.action(authority, 'READONLY_OBSERVE', dict(max_bytes=member['max_bytes']))
        require(readonly['data']['useful_bytes'] <= member['max_bytes'],
            'The retained target volume exceeds the approved finite repair bound')
        controls = strict_loads(encoded(member['target_resources']))
        controls['limits']['expected_bytes'] = capture['data']['useful_bytes']
        base = dict(config=member['target_export'], receipt=capture['source_receipt'], file_manifest=capture['file_manifest'],
            target=member['forward_target_path'], resources=controls, max_bytes=member['max_bytes'])
        guest.action(authority, 'FORWARD_RESTORE_PREPARE', base)
        for stage in ('REPOSITORY', 'SNAPSHOTS', 'RESTORE'):
            self.original_capture(guard.member_id, detached=False)
            guest.action(authority, 'FORWARD_RESTORE_COMMAND', dict(base, stage=stage,
                credentials=repository.credentials(authority, base['config'])))
        restored = guest.action(authority, 'FORWARD_RESTORE_FINISH', base)
        require(restored['data'] == capture['data'] and restored['restore_receipt']['target_machine_id'] == member['target']['machine_id'],
            'The repaired target bytes, metadata or actual guest differ from the committed capture')
        useful_path = str(Path(member['forward_target_path']) / member['target_export']['source'].lstrip('/'))
        copied = guest.action(authority, 'COPY_REHEARSAL', dict(source=useful_path, destination=member['rehearsal_path'],
            manifest=capture['data'], max_bytes=member['max_bytes']))
        unit, state = guest.start_rehearsal(authority, member['target'], member['rehearsal_path'])
        health = guest.action(authority, 'HEALTH_ISOLATED', dict(main_pid=int(state['MainPID']),
            isolated_data_path=member['rehearsal_path']))
        guest.systemctl(authority, 'stop', unit)
        stopped = guest.systemctl(authority, 'show', unit, properties=('ActiveState', 'MainPID'))
        require(stopped == {'ActiveState': 'inactive', 'MainPID': '0'} and
            guest.action(authority, 'DATA_OBSERVE', dict(path=useful_path, max_bytes=member['max_bytes']))['data'] == capture['data'],
            'The isolated repair rehearsal remains active or changed the repaired application')
        self.original_capture(guard.member_id, detached=False)
        return dict(status='COMMITTED_TARGET_CAPTURE_RESTORED_AND_REHEARSED', restored=restored,
            capture_digest=canonical_record_digest(capture), capture=capture, final_data_path=useful_path,
            isolated_copy=copied, isolated_service=state, useful_health=health, stopped_service=stopped)

    def _activate(self, guest, authority, log):
        guard, member = authority.intent_guard, authority.intent_guard.member
        capture, original = self._prerequisites(guard.member_id, 'FORWARD_ACTIVATE')
        repaired, repair_proof = self.independently_resolved(guard.member_id, 'FORWARD_REPAIR')
        observed = repaired['observations']
        require(observed['capture_digest'] == canonical_record_digest(capture), 'Repair switched its original committed capture')
        guest.action(authority, 'IMAGE_OBSERVE', {})
        ApplicationLifecycleRunner._service_off(guest, authority, member['target'])
        readonly = guest.action(authority, 'READONLY_OBSERVE', dict(max_bytes=member['max_bytes']))
        current = guest.action(authority, 'DATA_OBSERVE', dict(path=observed['final_data_path'], max_bytes=member['max_bytes']))['data']
        require(current == capture['data'], 'The approved repaired dataset changed before new write admission')
        log.append('TARGET_WRITE_ADMISSION_STARTED', dict(original_source_fence_digest=
            canonical_record_digest(original['SOURCE_FENCE_receipt']), repair_receipt_digest=canonical_record_digest(repaired)))
        marker = guest.action(authority, 'ACTIVATION_MARKER', dict(final_manifest_sha256=digest(encoded(current)),
            original_source_fence_sha256=canonical_record_digest(original['SOURCE_FENCE_receipt'])))
        guest.action(authority, 'BOOT_READWRITE', dict(fstab_sha256=readonly['fstab_sha256']))
        self.original_capture(guard.member_id, detached=False)
        guest.action(authority, 'REMOUNT_READWRITE', {})
        published = guest.action(authority, 'PUBLISH_FINAL', dict(source=observed['final_data_path'],
            manifest=current, max_bytes=member['max_bytes']))
        self.original_capture(guard.member_id, detached=False)
        guest.systemctl(authority, 'unmask', member['target']['unit']); guest.systemctl(authority, 'start', member['target']['unit'])
        service = guest.systemctl(authority, 'show', member['target']['unit'],
            properties=('ActiveState', 'SubState', 'MainPID', 'User', 'Group', 'NoNewPrivileges', 'ProtectSystem'))
        selected = member['target']
        require(service['ActiveState'] == 'active' and service['SubState'] == 'running'
            and service['User'] == str(selected['uid']) and service['Group'] == str(selected['gid'])
            and service['NoNewPrivileges'] == 'yes' and service['ProtectSystem'] == 'strict'
            and service['MainPID'].isdigit() and int(service['MainPID']) > 1,
            'The repaired production application has no useful selected unprivileged process')
        health = guest.action(authority, 'HEALTH_PRODUCTION', dict(main_pid=int(service['MainPID'])))
        self.original_capture(guard.member_id, detached=False)
        return dict(status='FORWARD_REPAIRED_APPLICATION_WRITES_ADMITTED_TRAFFIC_REQUIRED',
            original_source_exclusion=original['SOURCE_FENCE'], repair_proof=repair_proof,
            target_write_marker=marker, published=published, application_service=service, useful_health=health,
            target_write_boundary='TARGET_WRITES_POSSIBLE')

    def execute(self, phase, member_id, *, guest, repository=None, native_runtime=None):
        require(phase in FORWARD_PHASES and isinstance(guest, ApplicationGuestRuntime),
            'A concrete retained-target repair phase is required')
        self._prerequisites(member_id, phase)
        guard = LifecycleCommandGuard(guest.worker, self.admitted, strict_loads(self.artifact_bytes),
            self.lifecycle, phase, member_id, recovery=self.selection)
        authority = guest.select(guard)
        request_digest = canonical_record_digest(dict(recovery_digest=self.selection.sha256,
            lifecycle_digest=self.lifecycle.sha256, artifact_digest=guard.selection_digest,
            member=guard.member, phase=phase, plan_digest=self.admitted.plan_digest))
        with execution_journal.locked(self.ledger, self._scope(member_id, phase)) as log:
            require(not log.events, 'The original repair was attempted; independently observe it')
            runtime = guest.worker
            original = dict(organization_id=runtime.context.organization_id, tenant_id=runtime.context.tenant_id,
                operation_id=guard.row['operation_id'], grant_id=runtime.grant_id, step_id=guard.row['step_id'],
                lease_key=runtime.lease_key, binding=runtime.lease.binding.__dict__, workload_id=runtime.lease.workload_id,
                security_domain_id=runtime.lease.security_domain_id, worker_id=runtime.identity.subject,
                owner_epoch=runtime.lease.epoch, operation_kind=guard.operation_kind, request_digest=request_digest)
            log.append('APPLICATION_PHASE_STARTED', dict(original_intent=original, lifecycle_sha256=self.lifecycle.sha256))
            try:
                guard.claim(request_digest)
                if phase in {'TARGET_REATTACH', 'TARGET_START'}:
                    require(type(native_runtime) is OpenStackApplicationRuntime and native_runtime.guest is guest,
                        'The actual current Nova/Cinder retained-volume repair owner is required')
                    client = native_runtime.client(guard)
                    if phase == 'TARGET_REATTACH':
                        _capture, facts = self.original_capture(member_id)
                        before = client.snapshot(attached=False)
                        require(before == facts['POSTWRITE_CAPTURE_receipt']['observations']['persistent_disk_exclusion']['retained_detached_snapshot'],
                            'The original retained target volume or VM changed before approved repair')
                        log.append('TARGET_DISK_ADD_STARTED', dict(original_capture_digest=
                            canonical_record_digest(facts['POSTWRITE_CAPTURE_receipt'])))
                        request_id = client.attach(before)
                        log.append('TARGET_DISK_ADD_RETURNED', dict(native_request_id=request_id))
                        after = client.snapshot(attached=True)
                    else:
                        self.independently_resolved(member_id, 'TARGET_REATTACH')
                        log.append('NATIVE_START_STARTED', dict(native_id=guard.binding.native_id))
                        request_id = client.start()
                        log.append('NATIVE_START_RETURNED', dict(native_request_id=request_id))
                        after = client.snapshot(attached=True, powered=True)
                    require(client.snapshot(attached=True, powered=phase == 'TARGET_START') == after,
                        'The retained target volume or VM changed during repair readback')
                    self.original_capture(member_id, detached=False)
                    observed = dict(status='RETAINED_TARGET_VOLUME_REATTACHED_STOPPED' if phase == 'TARGET_REATTACH'
                        else 'RETAINED_TARGET_BOOTED_APPLICATION_MASKED_READONLY', native_request_id=request_id, native_snapshot=after)
                elif phase == 'FORWARD_REPAIR':
                    observed = self._restore(guest, authority, repository)
                else:
                    observed = self._activate(guest, authority, log)
                guard.require_current()
                observed['recovery_selection_digest'] = self.selection.sha256
                result = dict(format='hosting-application-phase-result/1', phase=phase, job_id=self.admitted.job_id,
                    member_id=member_id, selection_sha256=self.lifecycle.sha256, plan_digest=self.admitted.plan_digest,
                    original_intent=original, status=observed['status'], observations=observed,
                    native_intent_requires_independent_resolution=True, production_acceptance=False, native_qualification=False)
                log.append('APPLICATION_PHASE_COMPLETED', dict(result=result))
                return result
            except BaseException:
                try:
                    guard.uncertain()
                except Exception:
                    pass
                raise

    def verify(self, *, traffic, health_readers, promotion):
        from .traffic import ApplicationTrafficRuntime
        require(type(traffic) is ApplicationTrafficRuntime and traffic.lifecycle == self.original.lifecycle,
            'Forward repair must independently recontact the original current authoritative target traffic')
        members = []
        for member in self.lifecycle.to_dict()['members']:
            member_id = member['machine_id']
            _capture, original = self.original_capture(member_id, detached=False)
            activated, activation_proof = self.independently_resolved(member_id, 'FORWARD_ACTIVATE')
            repaired, repair_proof = self.independently_resolved(member_id, 'FORWARD_REPAIR')
            require(activated['observations']['repair_proof']['phase_receipt_digest'] == canonical_record_digest(repaired),
                'The repaired activation does not bind its original independently observed committed bytes')
            reader = health_readers.get((self.admitted.job_id, member_id, 'destination'))
            require(type(reader) is ApplicationHealthReadRuntime and reader.registry is self.evidence.registry
                and reader.recovery == self.selection,
                'Repaired acceptance needs a separately enrolled useful-health reader')
            original_writer = activated['original_intent']
            require((reader.writer.grant_id, reader.writer.identity.subject, reader.writer.lease.epoch,
                     reader.writer.lease.binding.__dict__) == (original_writer['grant_id'], original_writer['worker_id'],
                     original_writer['owner_epoch'], original_writer['binding']),
                'The repaired independent reader differs from the exact new original activation writer')
            health = reader.observe(self.admitted, strict_loads(self.artifact_bytes), self.lifecycle, member_id)
            current_traffic = traffic.verify(self.original.admitted, strict_loads(self.original.artifact_bytes), member_id)
            self.original_capture(member_id, detached=False)
            members.append(dict(member_id=member_id, original_source_exclusion=original['SOURCE_FENCE'],
                repair=repair_proof, activation=activation_proof, independent_useful_health=health, current_traffic=current_traffic))
        result = dict(format='hosting-application-postwrite-recovery-acceptance/1', job_id=self.admitted.job_id,
            original_job_id=self.original.admitted.job_id, recovery_selection_digest=self.selection.sha256,
            lifecycle_digest=self.lifecycle.sha256, mode='FORWARD_REPAIR', members=members,
            status='FORWARD_REPAIRED_APPLICATION_INDEPENDENTLY_OBSERVED', source_restart_authorized=False,
            production_acceptance=True, native_qualification=False)
        from .promotion import ApplicationPromotionRuntime
        if type(promotion) is not ApplicationPromotionRuntime:
            raise LifecycleHeld('CANONICAL_APPLICATION_PROMOTION_REQUIRED')
        plan = strict_loads(self.plan_bytes)
        result['canonical_promotion'] = promotion.confirm_current_source(self) if \
            plan['spec']['source'] == plan['spec']['destination'] else promotion.promote(self, result)
        return result
