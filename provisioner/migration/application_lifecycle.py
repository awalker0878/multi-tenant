"""Fixed enrolled Linux application rehearsal, final export and activation.

The graph is deliberately concrete: systemd isolation, an exclusive filesystem,
Restic's existing capture/restore owners and persistent VMware device removal.
Every phase owns one original native intent and durable named checkpoints. A
worker result is retained before independent B11 resolution; no callback, exit
code or earlier successful comparison grants the next phase.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time

from provisioner.controlplane.authority import PlanScope
from provisioner.controlplane.persistence import canonical_record_digest
from provisioner.controlplane.jobs.progress import APPLICATION_HOLD_CODES
from provisioner.controlplane.worker.grants import CredentialBroker
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from provisioner.domain.enterprise_records import validate_record
from provisioner.execution import execution_journal, restic_run, vsphere_power
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.restic_transfer import destination_receipt, grant_digest, validate as validate_transfer, TransferGuard
from provisioner.execution.run_files import digest, encoded, private_path, require, utcnow
from .application import ApplicationDataRunner, ApplicationDataSelection
from .authority import ApplicationCommandAuthority
from .lifecycle import ApplicationLifecycleSelection, LifecycleCommandGuard
from .lifecycle_evidence import ApplicationEvidenceReader
from .lifecycle_evidence import CurrentWriterExclusions
from .native_openstack import OpenStackApplicationRuntime
from .remote_app import ApplicationGuestRuntime, ApplicationHealthReadRuntime
from .source_exclusion import (
    SourceDiskFenceRuntime, _ApplicationVsphereClient, observe_removed, observe_added, selected_disks)


class LifecycleHeld(RuntimeError):
    def __init__(self, hold_code):
        require(hold_code in APPLICATION_HOLD_CODES,
            'A fixed application lifecycle hold is required')
        self.hold_code = hold_code
        super().__init__(hold_code)


@dataclass(frozen=True)
class ApplicationRepositoryRuntime:
    """Ephemeral operation-scoped credentials enrolled outside queue history."""
    guest: ApplicationGuestRuntime
    broker: CredentialBroker
    consumer: VaultCredentialConsumer

    def __post_init__(self):
        require(isinstance(self.guest, ApplicationGuestRuntime)
                and isinstance(self.broker, CredentialBroker)
                and isinstance(self.consumer, VaultCredentialConsumer)
                and self.broker._issuer is self.consumer.issuer
                and self.broker._grants is self.guest.commands.command_runtime.grants
                and self.broker._identities is self.guest.commands.command_runtime.verifier,
                'The exact actual guest, current B10 broker and enrolled revocable repository issuer are required')

    def credentials(self, authority, config):
        runtime = self.guest.commands.command_runtime
        require(authority.runtime is runtime and authority.intent_guard.claimed,
                'Repository credentials require the exact claimed original application command')
        grant, deadline = authority.require_current()
        handle = self.broker.acquire(runtime.transport_evidence, runtime.context, grant.grant_id,
                                     **runtime.grant_arguments(authority.admitted))
        consumed = self.consumer.unwrap(handle, grant)
        authority.require_current()
        data = consumed.data
        if data.get('format') == 'hosting-application-command-credentials/1':
            require(set(data) == {'format', 'repository', 'vsphere', 'openstack'},
                'The shared source command credential projection changed')
            data = data['repository']
        require(isinstance(data, dict) and set(data) ==
                {'repository_id', 'repository', 'password', 'username', 'http_password'}
                and (data['repository_id'], data['repository']) == (config['repository_id'], config['repository'])
                and all(isinstance(data[key], str) and data[key] and '\x00' not in data[key]
                        for key in ('password', 'username', 'http_password'))
                and min(consumed.expires_at, deadline) > utcnow(),
                'The fresh repository credential differs from its enrolled original repository or current grant')
        return {key: data[key] for key in ('password', 'username', 'http_password')}

    @property
    def registry(self):
        return self.guest.registry


class ApplicationLifecycleRunner:
    def __init__(self, *, admitted, plan, execution_artifact, lifecycle, datasets, ledger, evidence,
                 database_final_proof=None, staged=None, management=None):
        require(isinstance(plan, dict) and not validate_record(plan)
                and isinstance(lifecycle, ApplicationLifecycleSelection)
                and isinstance(datasets, ApplicationDataSelection)
                and isinstance(evidence, ApplicationEvidenceReader)
                and plan['spec'].get('execution', {}).get('artifactDigest') == canonical_record_digest(execution_artifact)
                and execution_artifact.get('applicationLifecycleSelectionDigest') == lifecycle.sha256
                and execution_artifact.get('datasetSelectionDigest') == datasets.sha256,
                'The canonical plan must select this complete immutable application lifecycle and dataset slice')
        body = lifecycle.to_dict()
        self.database_final_proof = database_final_proof
        database_ids = set()
        self.database_selection = None
        if 'applicationDatabaseSelectionDigest' in execution_artifact:
            from .postgresql_activities import DatabaseFinalProofOwner
            require(type(database_final_proof) is DatabaseFinalProofOwner,
                'The actual selected PostgreSQL final proof owner is required for mixed application data')
            self.database_selection = database_final_proof.activities.selections.load(
                execution_artifact['applicationDatabaseSelectionDigest'])
            database_ids.add(self.database_selection.to_dict()['datasetId'])
            require(self.database_selection.to_dict()['memberId'] in {row['machine_id'] for row in body['members']}
                and database_final_proof.activities.runtimes.evidence_readers.get(admitted.job_id).registry is evidence.registry,
                'The original SQL proof must share this application member and actual native registry')
        else:
            require(database_final_proof is None, 'A file selection cannot borrow a database success proof')
        require(plan['spec']['source'] == body['source_scope']
                and plan['spec']['destination'] == body['destination_scope']
                and (execution_artifact.get('driver', plan['spec']['execution']['driver']),
                     plan['spec']['route']['method']) in {
                     ('openstack-linux-rebuild/1', 'REBUILD_RESTORE'),
                     ('openstack-linux-application-cutover/1', 'REBUILD_RESTORE'),
                     ('openstack-linux-application-database/1', 'APPLICATION_NATIVE')}
                and plan['spec']['route']['guestProfile'] == body['guest_profile']
                and {(row['machineId'], row['sourceBinding']['nativeId']) for row in plan['spec']['machineMappings']} ==
                    {(row['machine_id'], row['source']['native_id']) for row in body['members']}
                and set(plan['spec']['selectedDatasetIds']) == {row['dataset_id'] for row in body['members']} | database_ids,
                'The lifecycle must cover the complete selected application and its original source VM bindings')
        data = {row['dataset_id']: row for row in datasets.to_dict()['datasets']}
        for row in body['members']:
            selected = data[row['dataset_id']]
            require(row['source_export']['source'] == selected['source_config']['source']
                    and row['source_export']['repository_id'] == selected['source_config']['repository_id']
                    and row['source_export']['repository'] == selected['source_config']['repository']
                    and row['initial_target_path'] == str(Path(selected['target_root']) /
                                                       selected['source_config']['source'].lstrip('/')),
                    'The application cannot replace its source repository or initial restored dataset mapping')
        self.admitted, self.plan_bytes, self.artifact_bytes = admitted, encoded(plan), encoded(execution_artifact)
        self.lifecycle, self.datasets, self.evidence = lifecycle, datasets, evidence
        self.staged = staged
        self.management = management
        self.ledger = private_path(ledger, directory=True)

    def _target_prepare(self, guest, authority, native_runtime, log):
        """Power the current observed target with its separate native capability.

        No SSH is used. This receipt does not assert that quarantined ports have
        been enabled or that a management path is reachable; that independently
        selected network/bootstrap owner must precede subsequent guest contact.
        """
        guard = authority.intent_guard
        require(type(native_runtime) is OpenStackApplicationRuntime and native_runtime.guest is guest
            and guard.phase == 'TARGET_PREPARE', 'The actual current existing-target power owner is required')
        client = native_runtime.client(guard)
        before = client.snapshot(attached=True)
        log.append('NATIVE_START_STARTED', dict(original_native_snapshot_digest=canonical_record_digest(before)))
        request_id = client.start()
        log.append('NATIVE_START_RETURNED', dict(native_request_id=request_id))
        after = client.snapshot(attached=True, powered=True)
        require(client.snapshot(attached=True, powered=True) == after,
            'The original target server or volume changed during independent power readback')
        return dict(status='OBSERVED_EXISTING_TARGET_BOOTED_NETWORK_BOOTSTRAP_REQUIRED',
            original_native_snapshot=before, native_snapshot=after, native_request_id=request_id,
            isolated_management_reachability_verified=False)

    def _scope(self, member_id, phase):
        return dict(owner='application-lifecycle', job_id=self.admitted.job_id, member_id=member_id,
                    phase=phase, lifecycle_sha256=self.lifecycle.sha256,
                    artifact_sha256=canonical_record_digest(strict_loads(self.artifact_bytes)),
                    plan_digest=strict_loads(self.plan_bytes)['metadata']['planDigest'])

    @staticmethod
    def _state(events):
        started, complete = None, None
        for event in events:
            if event['kind'] == 'APPLICATION_PHASE_STARTED':
                require(started is None and complete is None, 'An application phase cannot be repeated')
                started = event['data']
            elif event['kind'] == 'APPLICATION_PHASE_COMPLETED':
                require(started is not None and complete is None, 'Orphan or repeated application completion')
                complete = event['data']['result']
            else:
                require(started is not None and complete is None and event['kind'] in
                        {'SOURCE_DISK_REMOVE_STARTED', 'SOURCE_DISK_TASK_RETURNED', 'TARGET_WRITE_ADMISSION_STARTED',
                         'NATIVE_SHUTDOWN_STARTED', 'NATIVE_SHUTDOWN_RETURNED', 'TARGET_DISK_REMOVE_STARTED',
                         'TARGET_DISK_TASK_RETURNED', 'SOURCE_DISK_ADD_STARTED', 'SOURCE_DISK_ADD_RETURNED',
                         'TARGET_DISK_ADD_STARTED', 'TARGET_DISK_ADD_RETURNED', 'NATIVE_START_STARTED', 'NATIVE_START_RETURNED',
                         'MANAGEMENT_PORT_ENABLE_STARTED', 'MANAGEMENT_PORT_ENABLE_RETURNED',
                         'TARGET_POLICY_CHANGE_STARTED', 'TARGET_POLICY_CHANGE_RETURNED'},
                        'The original application phase journal was changed')
        return started, complete

    def receipt(self, member_id, phase):
        with execution_journal.locked(self.ledger, self._scope(member_id, phase)) as log:
            started, complete = self._state(log.events)
            if started is None or complete is None:
                raise LifecycleHeld('ORIGINAL_APPLICATION_EFFECT_REQUIRES_RECONCILIATION')
            require(complete['original_intent'] == started['original_intent']
                    and complete['selection_sha256'] == self.lifecycle.sha256
                    and complete['plan_digest'] == strict_loads(self.plan_bytes)['metadata']['planDigest'],
                    'The original application result was rebound')
            return complete

    def independently_resolved(self, member_id, phase):
        receipt = self.receipt(member_id, phase)
        selected = self.lifecycle.member(member_id)['phases'][phase]
        scope = PlanScope.from_record(self.lifecycle.to_dict()[selected['scope_side'] + '_scope'])
        outcome = 'NO_EFFECT' if phase == 'TARGET_ISOLATE' and receipt['observations']['status'] == \
            'TARGET_POLICY_ALREADY_ISOLATED' else 'EFFECT_PRESENT'
        return receipt, self.evidence.require_resolved(receipt, scope, outcome=outcome)

    def current_policy(self, member_id, *, production, require_booted=True):
        if 'applicationStagingSelectionDigest' not in strict_loads(self.artifact_bytes):
            return None
        from .activities import ApplicationMigrationActivities
        from .application_network import OpenStackBootstrapRuntime
        require(type(self.management) is ApplicationMigrationActivities,
                'The actual current selected application management owner is required')
        runtime = self.management.runtimes.network_bootstraps.get((self.admitted.job_id, member_id))
        if type(runtime) is not OpenStackBootstrapRuntime or 'target_policy' not in self.lifecycle.member(member_id):
            raise LifecycleHeld('APPLICATION_PRODUCTION_POLICY_REQUIRED')
        return runtime.observe(self.admitted, strict_loads(self.artifact_bytes), self.lifecycle, member_id,
                               policy_enabled=production, require_booted=require_booted)

    def _initial(self, member_id):
        member = self.lifecycle.member(member_id)
        runner = ApplicationDataRunner(job_id=self.admitted.job_id, plan=strict_loads(self.plan_bytes),
            execution_artifact=strict_loads(self.artifact_bytes), selection=self.datasets, ledger=self.ledger,
            database_selection=self.database_selection)
        runner.join()
        with execution_journal.locked(self.ledger, runner._child_scope(member['dataset_id'])) as log:
            result = runner._child_states(log.events, member['dataset_id'])[member['dataset_id']]['complete']
        self.evidence.require_resolved(result, PlanScope.from_record(self.lifecycle.to_dict()['destination_scope']))
        require(result['records']['restore_receipt']['target_machine_id'] == member['target']['machine_id'],
                'The original dataset restore was not observed on this exact selected application target guest')
        return result

    def current_health(self, member_id, readers, *, side='destination'):
        self.current_policy(member_id, production=side == 'destination', require_booted=side == 'destination')
        reader = readers.get((self.admitted.job_id, member_id, side))
        if not isinstance(reader, ApplicationHealthReadRuntime):
            raise LifecycleHeld('APPLICATION_LIFECYCLE_OWNER_UNAVAILABLE')
        phase = 'ACTIVATE' if side == 'destination' else 'PREWRITE_RETURN'
        original = self.receipt(member_id, phase)['original_intent']
        require(reader.registry is self.evidence.registry and reader.side == side
                and (reader.writer.grant_id, reader.writer.identity.subject, reader.writer.lease.epoch,
                     reader.writer.lease.binding.__dict__) ==
                    (original['grant_id'], original['worker_id'], original['owner_epoch'], original['binding']),
                'The independent health reader was not enrolled against this exact original application writer')
        result = reader.observe(self.admitted, strict_loads(self.artifact_bytes), self.lifecycle, member_id)
        self.current_policy(member_id, production=side == 'destination', require_booted=side == 'destination')
        return result

    def verify_cutover(self, *, traffic, health_readers, promotion):
        from .traffic import ApplicationTrafficRuntime
        require(isinstance(traffic, ApplicationTrafficRuntime) and traffic.lifecycle == self.lifecycle,
                'The current exact selected authoritative traffic owner is required')
        members = []
        for member in self.lifecycle.to_dict()['members']:
            member_id = member['machine_id']
            source, source_proof = self.independently_resolved(member_id, 'SOURCE_FENCE')
            final, final_proof = self.independently_resolved(member_id, 'FINAL_SYNC')
            activated, activation_proof = self.independently_resolved(member_id, 'ACTIVATE')
            require(source['observations']['persistent_disk_exclusion']['state'] == 'SOURCE_DATA_DISKS_DETACHED_PERSISTENTLY'
                    and final['observations']['capture'] == source['observations']['final_capture']
                    and activated['observations']['final_sync_proof']['phase_receipt_digest'] == canonical_record_digest(final),
                    'The final useful application does not bind its original persistent source exclusion and final committed data')
            current_traffic = traffic.verify(self.admitted, strict_loads(self.artifact_bytes), member_id)
            health = self.current_health(member_id, health_readers)
            self._all_source_exclusions()
            members.append(dict(member_id=member_id, dataset_id=member['dataset_id'], source=source_proof,
                final_sync=final_proof, activation=activation_proof, current_traffic=current_traffic,
                independent_useful_health=health))
        acceptance = dict(format='hosting-application-cutover-acceptance/1', job_id=self.admitted.job_id,
            original_plan_digest=strict_loads(self.plan_bytes)['metadata']['planDigest'],
            original_artifact_digest=canonical_record_digest(strict_loads(self.artifact_bytes)),
            lifecycle_digest=self.lifecycle.sha256, members=members,
            status='APPLICATION_CUTOVER_INDEPENDENTLY_OBSERVED', production_acceptance=True,
            native_qualification=False)
        from .promotion import ApplicationPromotionRuntime
        if not isinstance(promotion, ApplicationPromotionRuntime):
            raise LifecycleHeld('CANONICAL_APPLICATION_PROMOTION_REQUIRED')
        acceptance['canonical_promotion'] = promotion.promote(self, acceptance)
        return acceptance

    def _all_source_exclusions(self, *, database_phase='POST_WRITE'):
        require(database_phase in {'PRE_WRITE', 'POST_WRITE'}, 'An exact source consistency boundary is required')
        exclusions = {member['machine_id']: self.independently_resolved(member['machine_id'], 'SOURCE_FENCE')[1]
                for member in self.lifecycle.to_dict()['members']}
        if self.database_final_proof is not None:
            member = self.database_selection.to_dict()['memberId']
            owner = self.database_final_proof
            if database_phase == 'PRE_WRITE':
                exclusions['database:' + member] = owner.require_final(self.admitted,
                    strict_loads(self.artifact_bytes), self.lifecycle, member)
            else:
                exclusions['database:' + member] = owner.require_source_exclusion(self.admitted,
                    strict_loads(self.artifact_bytes), self.lifecycle, member)
        return exclusions

    def inspect(self):
        members = []
        for member in self.lifecycle.to_dict()['members']:
            with execution_journal.locked(self.ledger, self._scope(member['machine_id'], 'ACTIVATE')) as log:
                started, complete = self._state(log.events)
                boundary = any(event['kind'] == 'TARGET_WRITE_ADMISSION_STARTED' for event in log.events)
            members.append(dict(member_id=member['machine_id'],
                original_activation_operation_id=member['phases']['ACTIVATE']['operation_id'],
                target_write_boundary='TARGET_WRITES_POSSIBLE' if boundary else
                    'TARGET_WRITE_STATE_UNKNOWN' if started and not complete else 'BEFORE_TARGET_WRITES',
                retained_completion=complete is not None))
        return dict(format='hosting-application-lifecycle-inspection/1', job_id=self.admitted.job_id,
            lifecycle_digest=self.lifecycle.sha256, members=members, source_restart_authorized=False,
            production_acceptance=False, native_qualification=False)

    def _require_before_target_writes(self, member_id):
        with execution_journal.locked(self.ledger, self._scope(member_id, 'ACTIVATE')) as log:
            started, complete = self._state(log.events)
            if any(event['kind'] == 'TARGET_WRITE_ADMISSION_STARTED' for event in log.events) or complete:
                raise LifecycleHeld('POSTWRITE_COMMITTED_DATA_RECOVERY_REQUIRED')
            if started:
                # A missing durable write marker cannot establish absence of a
                # late accepted operation. Its independently retained original
                # NO_EFFECT decision is mandatory before returning the source.
                original = dict(format='hosting-application-phase-result/1', phase='ACTIVATE',
                    job_id=self.admitted.job_id, member_id=member_id, selection_sha256=self.lifecycle.sha256,
                    plan_digest=strict_loads(self.plan_bytes)['metadata']['planDigest'],
                    original_intent=started['original_intent'],
                    status='ORIGINAL_ACTIVATION_INCOMPLETE_REQUIRES_NATIVE_ABSENCE',
                    original_journal_digest=canonical_record_digest(log.events))
                self.evidence.require_resolved(original, PlanScope.from_record(
                    self.lifecycle.to_dict()['destination_scope']), outcome='NO_EFFECT')
        return True

    def _recovery_exclusions(self, member_id, *, postwrite=False):
        source, _ = self.independently_resolved(member_id, 'SOURCE_FENCE')
        target, _ = self.independently_resolved(member_id, 'POSTWRITE_CAPTURE' if postwrite else 'TARGET_FENCE')
        exclusions = CurrentWriterExclusions(self.evidence, (
            (PlanScope.from_record(self.lifecycle.to_dict()['source_scope']), source),
            (PlanScope.from_record(self.lifecycle.to_dict()['destination_scope']), target)))
        exclusions.require_current()
        return exclusions

    def _current_target_exclusion(self, member_id, *, postwrite=False):
        target, _ = self.independently_resolved(member_id, 'POSTWRITE_CAPTURE' if postwrite else 'TARGET_FENCE')
        exclusions = CurrentWriterExclusions(self.evidence, (
            (PlanScope.from_record(self.lifecycle.to_dict()['destination_scope']), target),))
        exclusions.require_current()
        return exclusions

    def _target_fence(self, guest, authority, native_runtime, log, *, repository=None, committed=False):
        require(isinstance(native_runtime, OpenStackApplicationRuntime) and native_runtime.guest is guest,
                'The actual enrolled Nova/Cinder target volume owner is required')
        guard, member = authority.intent_guard, authority.intent_guard.member
        if not committed:
            self._require_before_target_writes(guard.member_id)
        selected = member['target']
        guest.action(authority, 'IMAGE_OBSERVE', {})
        guest.systemctl(authority, 'mask', selected['unit']); guest.systemctl(authority, 'stop', selected['unit'])
        readonly = self._readonly(guest, authority, selected, member['max_bytes'], target=not committed)
        capture = None
        if committed:
            require(isinstance(repository, ApplicationRepositoryRuntime) and repository.guest is guest,
                    'The actual original target committed-data repository owner is required')
            capture = self._capture(guest, authority, repository, target=True)
            require(capture['data'] == readonly['readonly']['data'],
                    'The original committed target bytes changed while they were fenced and captured')
        client = native_runtime.client(guard)
        original = client.snapshot(attached=True, powered=True)
        log.append('NATIVE_SHUTDOWN_STARTED', dict(native_snapshot_digest=canonical_record_digest(original)))
        shutdown = client.stop()
        log.append('NATIVE_SHUTDOWN_RETURNED', dict(native_request_id=shutdown))
        before = client.snapshot(attached=True)
        log.append('TARGET_DISK_REMOVE_STARTED', dict(native_snapshot_digest=canonical_record_digest(before),
                                                     volume_id=client.volume_id))
        task_id = client.detach(before)
        log.append('TARGET_DISK_TASK_RETURNED', dict(native_request_id=task_id))
        after = client.snapshot(attached=False)
        require(client.snapshot(attached=False) == after,
                'The original retained target volume or powered-off VM changed during exclusion readback')
        persistent = dict(state='NATIVE_DATA_VOLUME_DETACHED_PERSISTENTLY', native_task_id=None,
            native_request_id=task_id,
            original_shutdown_request_id=shutdown, volume_id=client.volume_id, original_snapshot=original,
            before_detach=before, retained_detached_snapshot=after, observed_at=utcnow().isoformat())
        observed = dict(status='TARGET_COMMITTED_DATA_FENCED_AND_CAPTURED' if committed else
            'PREWRITE_TARGET_DATA_VOLUME_DETACHED_PERSISTENTLY', application_consistency=readonly,
            persistent_disk_exclusion=persistent, source_restart_authorized=False)
        if committed:
            observed['committed_data_capture'] = capture
            observed['recovery_actions'] = ['REVERSE_SYNC_TO_EXCLUDED_SOURCE', 'RESTORE_CAPTURE_TO_NEW_TARGET', 'FORWARD_REPAIR']
        return observed

    def _source_reattach(self, guest, authority, native_runtime, log):
        guard, member = authority.intent_guard, authority.intent_guard.member
        self._require_before_target_writes(guard.member_id)
        exclusions = self._recovery_exclusions(guard.member_id)
        require(isinstance(native_runtime, SourceDiskFenceRuntime), 'The actual original source native owner is required')
        source, _ = self.independently_resolved(guard.member_id, 'SOURCE_FENCE')
        current = source['observations']['persistent_disk_exclusion']['vm_snapshot']
        request = member['native_fence']['power_request']
        client = _ApplicationVsphereClient(request, native_runtime, guard, authority, exclusions)
        disks = selected_disks(request, member['native_fence']['disk_keys'])
        from provisioner.execution import vsphere_observe as vm
        observed, _ = vm.snapshot(vsphere_power.validate(request), client)
        require(observed == current, 'The original retained source VM changed before approved prewrite reattachment')
        started = log.append('SOURCE_DISK_ADD_STARTED', dict(original_source_fence_digest=canonical_record_digest(source),
            selected_backing_digests=[vsphere_power.c.digest(disk['backing']) for disk in disks]))
        task_id = client.attach(current, disks)
        log.append('SOURCE_DISK_ADD_RETURNED', dict(native_task_id=task_id))
        guard.runtime.registry.task_accepted(guard.runtime.context, guard.row['operation_id'],
                                            guard.runtime.identity.subject, task_id)
        attached = observe_added(request, disks, task_id, started['at'], client)
        return dict(status='ORIGINAL_SOURCE_DATA_DISKS_REATTACHED_STOPPED', retained_disk_attachment=attached,
                    current_target_exclusion_digests=[canonical_record_digest(row) for row in exclusions.require_current()],
                    source_application_start_authorized=False)

    def _source_start(self, guest, authority, native_runtime):
        guard, member = authority.intent_guard, authority.intent_guard.member
        self._require_before_target_writes(guard.member_id)
        exclusions = self._current_target_exclusion(guard.member_id)
        attached, _ = self.independently_resolved(guard.member_id, 'SOURCE_REATTACH')
        require(isinstance(native_runtime, SourceDiskFenceRuntime), 'The actual original source power owner is required')
        request = strict_loads(encoded(member['native_fence']['power_request']))
        request['desired_power'] = 'poweredOn'; request['generation'] += 1
        request['snapshot']['resources'][0]['expected'] = attached['observations']['retained_disk_attachment']['vm_snapshot']
        client = _ApplicationVsphereClient(request, native_runtime, guard, authority, exclusions)
        authority_record = dict(format='hosting-vsphere-power-authority/1', request_sha256=vsphere_power.c.digest(request),
            valid_from=utcnow().isoformat(), valid_until=guard.require_current()[1].isoformat(),
            change_ref='application:' + guard.row['operation_id'],
            writer_fence_ref='original:' + canonical_record_digest(exclusions.require_current()),
            containment_ref='original:' + guard.row['operation_id'], placement_ref='approved:' + guard.selection_digest,
            data_quiesce_ref=None)
        power = vsphere_power.execute(request, authority_record, self.ledger, client,
            execute_approved_change=True, root=guest.source_root)
        guard.runtime.registry.task_accepted(guard.runtime.context, guard.row['operation_id'],
                                            guard.runtime.identity.subject, power['task_witness']['key'])
        return dict(status='ORIGINAL_SOURCE_BOOTED_WITH_APPLICATION_PERSISTENTLY_MASKED',
                    source_power=power, source_application_start_authorized=False)

    def _prewrite_return(self, guest, authority, log):
        guard, member = authority.intent_guard, authority.intent_guard.member
        self._require_before_target_writes(guard.member_id)
        exclusions = self._current_target_exclusion(guard.member_id)
        self.independently_resolved(guard.member_id, 'SOURCE_START')
        original = self.receipt(guard.member_id, 'SOURCE_FENCE')
        selected = member['source']; capture = original['observations']['final_capture']
        guest.action(authority, 'IMAGE_OBSERVE', {}); self._service_off(guest, authority, selected)
        readonly = guest.action(authority, 'READONLY_OBSERVE', dict(max_bytes=member['max_bytes']))
        require(readonly['data'] == capture['data'],
                'Prewrite return would start stale or changed original source data')
        log.append('TARGET_WRITE_ADMISSION_STARTED', dict(return_source=True,
            original_target_exclusion_digest=canonical_record_digest(exclusions.require_current()),
            original_final_manifest_digest=digest(encoded(capture['data']))))
        marker = guest.action(authority, 'ACTIVATION_MARKER', dict(final_manifest_sha256=digest(encoded(capture['data'])),
            original_source_fence_sha256=canonical_record_digest(exclusions.require_current())))
        guest.action(authority, 'BOOT_READWRITE', dict(fstab_sha256=readonly['fstab_sha256']))
        exclusions.require_current(); guest.action(authority, 'REMOUNT_READWRITE', {})
        exclusions.require_current(); guest.systemctl(authority, 'unmask', selected['unit'])
        exclusions.require_current(); guest.systemctl(authority, 'start', selected['unit'])
        state = guest.systemctl(authority, 'show', selected['unit'], properties=('ActiveState', 'SubState', 'MainPID'))
        require(state['ActiveState'] == 'active' and state['SubState'] == 'running'
                and state['MainPID'].isdigit() and int(state['MainPID']) > 1,
                'The actual original source application has not returned usefully')
        health = guest.action(authority, 'HEALTH_PRODUCTION', dict(main_pid=int(state['MainPID'])))
        exclusions.require_current()
        return dict(status='PREWRITE_SOURCE_APPLICATION_RETURN_OBSERVED_TRAFFIC_REQUIRED',
            target_write_boundary='SOURCE_WRITES_POSSIBLE', source_write_marker=marker,
            application_service=state, useful_health=health, original_source_data_digest=digest(encoded(capture['data'])))

    @staticmethod
    def _service_off(guest, authority, selected):
        state = guest.systemctl(authority, 'show', selected['unit'],
            properties=('ActiveState', 'SubState', 'UnitFileState', 'MainPID'))
        require(state['ActiveState'] == 'inactive' and state['SubState'] == 'dead'
                and state['MainPID'] == '0' and state['UnitFileState'] == 'masked',
                'The original application unit is not persistently masked and stopped')
        return state

    def _readonly(self, guest, authority, selected, maximum, *, target=False):
        observed = guest.action(authority, 'TARGET_OBSERVE' if target else 'OBSERVE', dict(max_bytes=maximum))
        persistent = guest.action(authority, 'BOOT_READONLY', dict(fstab_sha256=observed['fstab_sha256']))
        guest.action(authority, 'REMOUNT_READONLY', {})
        readonly = guest.action(authority, 'TARGET_READONLY_OBSERVE' if target else 'READONLY_OBSERVE', dict(max_bytes=maximum))
        require(readonly['data'] == observed['data'] and readonly['fstab_sha256'] == persistent['after_sha256'],
                'The actual application consistency point changed while fencing its filesystem')
        return dict(service=self._service_off(guest, authority, selected),
                    persistent_mount=persistent, readonly=readonly)

    def _capture(self, guest, authority, repository, *, target=False):
        member = authority.intent_guard.member
        config = member['target_export' if target else 'source_export']
        base = dict(config=config, max_bytes=member['max_bytes'], source_io=member['target_io' if target else 'source_io'])
        prepared = guest.action(authority, 'CAPTURE_PREPARE', base)
        for stage in ('REPOSITORY', 'BACKUP'):
            guest.action(authority, 'CAPTURE_COMMAND', dict(base, stage=stage,
                credentials=repository.credentials(authority, config)))
        final = guest.action(authority, 'CAPTURE_FINISH', base)
        require(final['data'] == prepared['data'] and final['file_manifest'] == prepared['file_manifest']
                and final['source_receipt']['manifest_sha256'] == digest(encoded(final['file_manifest']))
                and final['data']['useful_bytes'] <= member['max_bytes'],
                'The original fenced final capture changed')
        return final

    def _rehearsal(self, guest, authority):
        guard, member = authority.intent_guard, authority.intent_guard.member
        self._initial(guard.member_id)
        selected = member['target']
        guest.action(authority, 'IMAGE_OBSERVE', {})
        guest.systemctl(authority, 'mask', selected['unit'])
        guest.systemctl(authority, 'stop', selected['unit'])
        target_fence = self._readonly(guest, authority, selected, member['max_bytes'], target=True)
        initial = guest.action(authority, 'DATA_OBSERVE', dict(path=member['initial_target_path'], max_bytes=member['max_bytes']))['data']
        copied = guest.action(authority, 'COPY_REHEARSAL', dict(source=member['initial_target_path'],
            destination=member['rehearsal_path'], manifest=initial, max_bytes=member['max_bytes']))
        unit, state = guest.start_rehearsal(authority, selected, member['rehearsal_path'])
        health = guest.action(authority, 'HEALTH_ISOLATED', dict(main_pid=int(state['MainPID']),
                                                              isolated_data_path=member['rehearsal_path']))
        guest.systemctl(authority, 'stop', unit)
        stopped = guest.systemctl(authority, 'show', unit, properties=('ActiveState', 'MainPID'))
        require(stopped == {'ActiveState': 'inactive', 'MainPID': '0'}
                and guest.action(authority, 'DATA_OBSERVE', dict(path=member['initial_target_path'],
                            max_bytes=member['max_bytes']))['data'] == initial,
                'The rehearsal remains running or changed the original restored dataset')
        return dict(status='ISOLATED_APPLICATION_REHEARSAL_OBSERVED',
                    target_fence=target_fence, restored_data=initial, isolated_copy=copied,
                    isolated_service=state, useful_health=health, stopped_service=stopped)

    def _source_fence(self, guest, authority, repository, native_runtime, log):
        guard, member = authority.intent_guard, authority.intent_guard.member
        self.independently_resolved(guard.member_id, 'REHEARSAL')
        require(isinstance(native_runtime, SourceDiskFenceRuntime)
                and isinstance(repository, ApplicationRepositoryRuntime) and repository.guest is guest,
                'The exact enrolled native source and final repository owners are required')
        previous = native_runtime.require_previous_exclusion(guard)
        database_owner = None
        database_proof = None
        if self.database_selection is not None and self.database_selection.to_dict()['memberId'] == guard.member_id:
            database_owner = self.database_final_proof
            database_proof = database_owner.require_final(self.admitted,
                strict_loads(self.artifact_bytes), self.lifecycle, guard.member_id)
            require(member.get('source_database_directory') == database_proof['observations']['sourceDataDirectory']
                and member.get('target_database_directory') == database_proof['observations']['targetDataDirectory'],
                'The actual PostgreSQL engine directories differ from their separately approved file-disk placement')
            separated = guest.action(authority, 'DATABASE_SEPARATION_OBSERVE',
                dict(data_directory=member['source_database_directory']))
        selected = member['source']
        guest.action(authority, 'IMAGE_OBSERVE', {})
        guest.systemctl(authority, 'mask', selected['unit'])
        guest.systemctl(authority, 'stop', selected['unit'])
        consistency = self._readonly(guest, authority, selected, member['max_bytes'])
        capture = self._capture(guest, authority, repository)
        require(capture['data'] == consistency['readonly']['data'],
                'The final export differs from the actual stopped, fenced application consistency point')
        request = member['native_fence']['power_request']
        client = _ApplicationVsphereClient(request, native_runtime, guard, authority,
                                           database_final_proof=database_owner)
        # Existing vSphere power owner still owns its exact durable power task.
        power_authority = dict(format='hosting-vsphere-power-authority/1', request_sha256=vsphere_power.c.digest(request),
            valid_from=utcnow().isoformat(), valid_until=guard.require_current()[1].isoformat(),
            change_ref='application:' + guard.row['operation_id'], writer_fence_ref='native:' + previous['worker_fence_digest'],
            containment_ref='original:' + guard.row['operation_id'], placement_ref='approved:' + guard.selection_digest,
            data_quiesce_ref='capture:' + capture['source_receipt']['manifest_sha256'])
        if database_owner is None:
            shutdown = vsphere_power.execute(request, power_authority, self.ledger, client,
                execute_approved_change=True, root=guest.source_root)
            current_native = shutdown['snapshot']
        else:
            from provisioner.execution import vsphere_observe as vm
            samples = [vm.snapshot(vsphere_power.validate(request), client) for _ in range(2)]
            require(samples[0] == samples[1] and not samples[-1][1]
                and not client.activity(utcnow().isoformat()),
                'The original running SQL VM changed or has pending native work before file-disk exclusion')
            current_native = samples[-1][0]
            shutdown = dict(status='RUNNING_SEPARATE_SQL_ENGINE_RETAINED', snapshot=current_native,
                current_database_proof=database_proof, actual_guest_database_separation=separated)
        disks = selected_disks(request, member['native_fence']['disk_keys'])
        started = log.append('SOURCE_DISK_REMOVE_STARTED', dict(selected_backing_digests=
            [vsphere_power.c.digest(disk['backing']) for disk in disks], current_config_sha256=
            vsphere_power.c.digest(current_native['config'])))
        task_id = client.detach(current_native, disks)
        log.append('SOURCE_DISK_TASK_RETURNED', dict(native_task_id=task_id))
        guard.runtime.registry.task_accepted(guard.runtime.context, guard.row['operation_id'],
                                            guard.runtime.identity.subject, task_id)
        removed = observe_removed(request, disks, task_id, started['at'], client)
        return dict(status='APPLICATION_SOURCE_FENCED_FINAL_CAPTURE_RETAINED',
                    prior_writer_exclusion=previous, application_consistency=consistency,
                    final_capture=capture, source_power=shutdown, persistent_disk_exclusion=removed)

    def _final_sync(self, guest, authority, repository):
        guard, member = authority.intent_guard, authority.intent_guard.member
        exclusions = self._all_source_exclusions(database_phase='PRE_WRITE')
        source, _proof = self.independently_resolved(guard.member_id, 'SOURCE_FENCE')
        capture = source['observations']['final_capture']
        require(isinstance(repository, ApplicationRepositoryRuntime) and repository.guest is guest,
                'The exact enrolled isolated final restore repository owner is required')
        controls = strict_loads(encoded(member['target_resources']))
        controls['limits']['expected_bytes'] = capture['data']['useful_bytes']
        base = dict(config=member['source_export'], receipt=capture['source_receipt'],
            file_manifest=capture['file_manifest'], target=member['final_target_path'],
            resources=controls, max_bytes=member['max_bytes'])
        initial = self._initial(guard.member_id)
        envelope = strict_loads(encoded(initial['records']['transfer_manifest']))
        envelope['transfer']['metadata']['transferId'] = guard.row['operation_id']
        spec = envelope['transfer']['spec']
        spec['sourceReceipt']['receiptDigest'] = digest(encoded(capture['source_receipt']))
        spec['expectedBytes'] = dict(state='KNOWN', value=capture['data']['useful_bytes'])
        grant, _deadline = authority.require_current()
        spec['grant']['grantId'] = grant.grant_id; spec['grant']['grantDigest'] = grant_digest(grant)
        envelope.update(source_config_sha256=digest(encoded(base['config'])),
            snapshot_id=capture['source_receipt']['snapshot_id'],
            file_manifest_sha256=digest(encoded(capture['file_manifest'])), target=member['final_target_path'])
        validate_transfer(envelope, base['config'], base['receipt'], base['file_manifest'], base['target'])
        transfer_guard = TransferGuard(guest.worker.worker_authority, guest.worker.credential,
            digest(encoded(envelope)), guest.worker.grant_id, guard.row['step_id'], guard.row['operation_id'],
            ApplicationCommandAuthority(guest.worker.execution_authority, self.admitted, guard.selection_digest,
                                        guest.worker.identity, 'RESTORE_DATA', management=self.management))
        transfer_guard.check(envelope)
        guest.action(authority, 'RESTORE_PREPARE', base)
        for stage in ('REPOSITORY', 'SNAPSHOTS', 'RESTORE'):
            self._all_source_exclusions(database_phase='PRE_WRITE')
            transfer_guard.check(envelope)
            guest.action(authority, 'RESTORE_COMMAND', dict(base, stage=stage,
                credentials=repository.credentials(authority, base['config'])))
        restored = guest.action(authority, 'RESTORE_FINISH', base)
        require(restored['data'] == capture['data'], 'The final application copy changed useful bytes or POSIX metadata')
        self._all_source_exclusions(database_phase='PRE_WRITE')
        transfer_guard.check(envelope)
        return dict(status='FINAL_APPLICATION_BYTES_AND_METADATA_RESTORED', source_exclusions=exclusions,
                    source_capture_digest=canonical_record_digest(capture), capture=capture, restored=restored,
                    transfer_manifest=envelope, destination_receipt=destination_receipt(envelope,
                        capture['source_receipt'], restored['restore_receipt']),
                    final_data_path=str(Path(member['final_target_path']) / member['source_export']['source'].lstrip('/')))

    def _activate(self, guest, authority, log):
        guard, member = authority.intent_guard, authority.intent_guard.member
        exclusions = self._all_source_exclusions(database_phase='PRE_WRITE')
        final, final_proof = self.independently_resolved(guard.member_id, 'FINAL_SYNC')
        observed = final['observations']
        selected = member['target']
        database_proof = None
        if self.database_selection is not None and self.database_selection.to_dict()['memberId'] == guard.member_id:
            database_proof = self.database_final_proof.require_final(self.admitted,
                strict_loads(self.artifact_bytes), self.lifecycle, guard.member_id)
            require(member.get('target_database_directory') == database_proof['observations']['targetDataDirectory'],
                'The actual target SQL directory differs from its approved placement')
            guest.action(authority, 'DATABASE_SEPARATION_OBSERVE',
                dict(data_directory=member['target_database_directory']))
        guest.action(authority, 'IMAGE_OBSERVE', {})
        self._service_off(guest, authority, selected)
        target = guest.action(authority, 'TARGET_READONLY_OBSERVE', dict(max_bytes=member['max_bytes']))
        current = guest.action(authority, 'DATA_OBSERVE', dict(path=observed['final_data_path'], max_bytes=member['max_bytes']))['data']
        require(current == observed['capture']['data'], 'The final restored application data changed before target write admission')
        log.append('TARGET_WRITE_ADMISSION_STARTED', dict(original_source_exclusion_digests=
            {key: canonical_record_digest(value) for key, value in exclusions.items()},
            final_sync_receipt_digest=canonical_record_digest(final)))
        marker = guest.action(authority, 'ACTIVATION_MARKER', dict(final_manifest_sha256=digest(encoded(current)),
            original_source_fence_sha256=canonical_record_digest(exclusions)))
        guest.action(authority, 'BOOT_READWRITE', dict(fstab_sha256=target['fstab_sha256']))
        self._all_source_exclusions()
        guest.action(authority, 'REMOUNT_READWRITE', {})
        published = guest.action(authority, 'PUBLISH_FINAL', dict(source=observed['final_data_path'],
            manifest=current, max_bytes=member['max_bytes']))
        self._all_source_exclusions()
        guest.systemctl(authority, 'unmask', selected['unit'])
        guest.systemctl(authority, 'start', selected['unit'])
        state = guest.systemctl(authority, 'show', selected['unit'],
            properties=('ActiveState', 'SubState', 'MainPID', 'User', 'Group', 'NoNewPrivileges', 'ProtectSystem'))
        require(state['ActiveState'] == 'active' and state['SubState'] == 'running'
                and state['User'] == str(selected['uid']) and state['Group'] == str(selected['gid'])
                and state['NoNewPrivileges'] == 'yes' and state['ProtectSystem'] == 'strict'
                and state['MainPID'].isdigit() and int(state['MainPID']) > 1,
                'The actual target application has no selected unprivileged useful service')
        health = guest.action(authority, 'HEALTH_PRODUCTION', dict(main_pid=int(state['MainPID'])))
        self._all_source_exclusions()
        return dict(status='TARGET_APPLICATION_WRITE_ADMISSION_OBSERVED_TRAFFIC_REQUIRED',
                    original_source_exclusions=exclusions, final_sync_proof=final_proof,
                    target_write_marker=marker, published=published, application_service=state, useful_health=health,
                    independent_database_final_proof=database_proof,
                    target_write_boundary='TARGET_WRITES_POSSIBLE')

    def execute(self, phase, member_id, *, guest, repository=None, native_runtime=None, network_runtime=None):
        require(isinstance(guest, ApplicationGuestRuntime) and phase in {'TARGET_PREPARE', 'TARGET_BOOTSTRAP', 'TARGET_POLICY', 'TARGET_ISOLATE', 'REHEARSAL', 'SOURCE_FENCE', 'FINAL_SYNC', 'ACTIVATE',
                'TARGET_FENCE', 'SOURCE_REATTACH', 'SOURCE_START', 'PREWRITE_RETURN', 'POSTWRITE_CAPTURE'},
                'The concrete selected application phase owner is required')
        if phase in {'REHEARSAL', 'SOURCE_FENCE', 'FINAL_SYNC', 'ACTIVATE'} and \
                'applicationStagingSelectionDigest' in strict_loads(self.artifact_bytes):
            from .application_network import OpenStackBootstrapRuntime
            if type(network_runtime) is not OpenStackBootstrapRuntime:
                raise LifecycleHeld('ISOLATED_MANAGEMENT_BOOTSTRAP_REQUIRED')
            self.independently_resolved(member_id, 'TARGET_BOOTSTRAP')
            if phase == 'ACTIVATE':
                if 'target_policy' not in self.lifecycle.member(member_id):
                    raise LifecycleHeld('APPLICATION_PRODUCTION_POLICY_REQUIRED')
                self.independently_resolved(member_id, 'TARGET_POLICY')
            network_runtime.observe(self.admitted, strict_loads(self.artifact_bytes), self.lifecycle, member_id,
                                    policy_enabled=phase == 'ACTIVATE')
        guard = LifecycleCommandGuard(guest.worker, self.admitted, strict_loads(self.artifact_bytes),
                                      self.lifecycle, phase, member_id, network_gate=network_runtime)
        authority = guest.select(guard)
        # The current independently retained original results are required before
        # creating another native intent. Missing facts cannot create a new
        # uncertain command merely by asking to continue the graph.
        if phase == 'TARGET_PREPARE':
            require('TARGET_PREPARE' in guard.member['phases'], 'Historical selections cannot invent target power authority')
        elif phase == 'TARGET_BOOTSTRAP':
            from .application_network import OpenStackBootstrapRuntime
            if type(network_runtime) is not OpenStackBootstrapRuntime:
                raise LifecycleHeld('ISOLATED_MANAGEMENT_BOOTSTRAP_REQUIRED')
            self.independently_resolved(member_id, 'TARGET_PREPARE')
        elif phase in {'TARGET_POLICY', 'TARGET_ISOLATE'}:
            from .application_network import OpenStackBootstrapRuntime
            if type(network_runtime) is not OpenStackBootstrapRuntime or 'target_policy' not in guard.member:
                raise LifecycleHeld('APPLICATION_PRODUCTION_POLICY_REQUIRED')
            self.independently_resolved(member_id, 'TARGET_BOOTSTRAP')
            if phase == 'TARGET_POLICY':
                self._all_source_exclusions(database_phase='PRE_WRITE')
                self.independently_resolved(member_id, 'FINAL_SYNC')
            else:
                self._require_before_target_writes(member_id)
        elif phase == 'REHEARSAL':
            self._initial(member_id)
        elif phase == 'SOURCE_FENCE':
            self.independently_resolved(member_id, 'REHEARSAL')
            require(isinstance(native_runtime, SourceDiskFenceRuntime), 'Actual persistent source disk fence owner required')
            native_runtime.require_previous_exclusion(guard)
        elif phase == 'FINAL_SYNC':
            self._all_source_exclusions(database_phase='PRE_WRITE')
        elif phase == 'ACTIVATE':
            self._all_source_exclusions(database_phase='PRE_WRITE'); self.independently_resolved(member_id, 'FINAL_SYNC')
        elif phase == 'POSTWRITE_CAPTURE':
            self.independently_resolved(member_id, 'ACTIVATE')
        elif phase == 'TARGET_FENCE':
            self._require_before_target_writes(member_id)
        elif phase == 'SOURCE_REATTACH':
            self._require_before_target_writes(member_id); self._recovery_exclusions(member_id)
        elif phase == 'SOURCE_START':
            self._require_before_target_writes(member_id); self._current_target_exclusion(member_id)
            self.independently_resolved(member_id, 'SOURCE_REATTACH')
        elif phase == 'PREWRITE_RETURN':
            self._require_before_target_writes(member_id); self._current_target_exclusion(member_id)
            self.independently_resolved(member_id, 'SOURCE_START')
        request_digest = canonical_record_digest(dict(lifecycle_digest=self.lifecycle.sha256,
            artifact_digest=guard.selection_digest, member=guard.member, phase=phase,
            plan_digest=strict_loads(self.plan_bytes)['metadata']['planDigest']))
        with execution_journal.locked(self.ledger, self._scope(member_id, phase)) as log:
            require(not log.events, 'The original application phase was attempted; independently observe it')
            runtime = guest.worker
            original = dict(organization_id=runtime.context.organization_id, tenant_id=runtime.context.tenant_id,
                operation_id=guard.row['operation_id'], grant_id=runtime.grant_id, step_id=guard.row['step_id'],
                lease_key=runtime.lease_key, binding=runtime.lease.binding.__dict__, workload_id=runtime.lease.workload_id,
                security_domain_id=runtime.lease.security_domain_id, worker_id=runtime.identity.subject,
                owner_epoch=runtime.lease.epoch, operation_kind=guard.operation_kind, request_digest=request_digest)
            log.append('APPLICATION_PHASE_STARTED', dict(original_intent=original, lifecycle_sha256=self.lifecycle.sha256))
            try:
                guard.claim(request_digest)
                if phase == 'TARGET_PREPARE':
                    observed = self._target_prepare(guest, authority, native_runtime, log)
                elif phase == 'TARGET_BOOTSTRAP':
                    observed = network_runtime.execute(authority, self.staged, log)
                elif phase in {'TARGET_POLICY', 'TARGET_ISOLATE'}:
                    observed = network_runtime.execute_policy(authority, self.staged, log, native_runtime,
                                                              enable=phase == 'TARGET_POLICY')
                elif phase == 'REHEARSAL':
                    observed = self._rehearsal(guest, authority)
                elif phase == 'SOURCE_FENCE':
                    observed = self._source_fence(guest, authority, repository, native_runtime, log)
                elif phase == 'FINAL_SYNC':
                    observed = self._final_sync(guest, authority, repository)
                elif phase == 'ACTIVATE':
                    observed = self._activate(guest, authority, log)
                elif phase == 'TARGET_FENCE':
                    observed = self._target_fence(guest, authority, native_runtime, log)
                elif phase == 'SOURCE_REATTACH':
                    observed = self._source_reattach(guest, authority, native_runtime, log)
                elif phase == 'SOURCE_START':
                    observed = self._source_start(guest, authority, native_runtime)
                elif phase == 'PREWRITE_RETURN':
                    observed = self._prewrite_return(guest, authority, log)
                else:
                    observed = self._target_fence(guest, authority, native_runtime, log,
                                                  repository=repository, committed=True)
                guard.require_current()
                result = dict(format='hosting-application-phase-result/1', phase=phase,
                    job_id=self.admitted.job_id, member_id=member_id, selection_sha256=self.lifecycle.sha256,
                    plan_digest=strict_loads(self.plan_bytes)['metadata']['planDigest'], original_intent=original,
                    status=observed['status'], observations=observed,
                    native_intent_requires_independent_resolution=True, production_acceptance=False,
                    native_qualification=False)
                log.append('APPLICATION_PHASE_COMPLETED', dict(result=result))
                return result
            except BaseException:
                try:
                    guard.uncertain()
                except Exception:
                    pass
                raise
