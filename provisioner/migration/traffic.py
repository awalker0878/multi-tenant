"""Application traffic uses the selected authoritative DNS and resolver owners.

The existing delivery journal remains the sole owner of selected stage packets
and dependency receipts. This binding can execute only the four DNS stages in
the immutable application descriptor; it has no arbitrary stage dispatcher.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from provisioner.controlplane.reconciliation.service_runtime import EnrolledServiceProvisioningRuntime
from provisioner.controlplane.reconciliation.service_propagation import EnrolledDnsPropagationRuntime
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
from provisioner.execution import delivery_run, delivery_steps, execution_journal
from provisioner.execution.run_files import encoded, load_private, private_path, read_private, require, sync_directory, write_new
from provisioner.execution.source_integrity import verify, verify_runtime
from provisioner.execution.neutron_observe import strict_loads
from provisioner.controlplane.persistence import canonical_record_digest
from .lifecycle import ApplicationLifecycleSelection


@dataclass(frozen=True)
class ApplicationTrafficRuntime:
    authority: PostgresExecutionAuthority
    lifecycle: ApplicationLifecycleSelection
    writers: Mapping[str, EnrolledServiceProvisioningRuntime]
    readers: Mapping[str, EnrolledDnsPropagationRuntime]
    delivery_directory: Path
    inbox_directory: Path
    journals_directory: Path
    source_root: Path

    def __post_init__(self):
        require(isinstance(self.authority, PostgresExecutionAuthority)
                and isinstance(self.lifecycle, ApplicationLifecycleSelection)
                and isinstance(self.writers, Mapping) and isinstance(self.readers, Mapping),
                'Actual selected DNS mutation and independent propagation owners are required')
        stages = {value for row in self.lifecycle.to_dict()['members'] for key, value in row['traffic_steps'].items()
                  if key.endswith('_dns')}
        sweeps = {value for row in self.lifecycle.to_dict()['members'] for key, value in row['traffic_steps'].items()
                  if key.endswith('_propagation')}
        require(set(self.writers) == stages and set(self.readers) == sweeps
                and all(type(value) is EnrolledServiceProvisioningRuntime for value in self.writers.values())
                and all(type(value) is EnrolledDnsPropagationRuntime for value in self.readers.values())
                and all(value.command_runtime.authority is self.authority for value in
                        tuple(self.writers.values()) + tuple(self.readers.values())),
                'Every selected traffic operation needs its exact separately enrolled native owner')
        object.__setattr__(self, 'writers', MappingProxyType(dict(self.writers)))
        object.__setattr__(self, 'readers', MappingProxyType(dict(self.readers)))
        for name in ('delivery_directory', 'inbox_directory', 'journals_directory'):
            object.__setattr__(self, name, private_path(getattr(self, name), directory=True))
        object.__setattr__(self, 'source_root', Path(self.source_root))

    @property
    def registry(self):
        return next(iter(self.writers.values())).registry

    def _delivery(self, admitted, selection, step_id, *, observation):
        operation = 'DNS_CHANGE' if step_id in self.writers else 'DISCOVER_READ'
        gate = self.authority.require_observation if observation else self.authority.require_current
        _, artifact = gate(admitted, canonical_record_digest(selection), operation)
        require(artifact == selection and selection.get('applicationLifecycleSelectionDigest') == self.lifecycle.sha256,
                'Traffic cannot use another approved application lifecycle')
        delivery = load_private(self.delivery_directory / (selection['deliveryPlanDigest'] + '.json'))
        delivery_run.validate(delivery)
        require(canonical_record_digest(delivery) == selection['deliveryPlanDigest'], 'The original traffic graph changed')
        step = next(row for row in delivery['steps'] if row['id'] == step_id)
        require(step['kind'] == ('dns_cutover' if step_id in self.writers else 'dns_propagation'),
                'Application traffic requires the concrete cutover and independent resolver owners')
        ledger = private_path(self.journals_directory / admitted.job_id, directory=True)
        return delivery, step, ledger

    def run_stage(self, admitted, selection, step_id, *, lifecycle_runner, health_readers):
        from .application_lifecycle import ApplicationLifecycleRunner
        require(isinstance(lifecycle_runner, ApplicationLifecycleRunner)
                and lifecycle_runner.admitted == admitted and lifecycle_runner.lifecycle == self.lifecycle
                and canonical_record_digest(selection) == canonical_record_digest(strict_loads(lifecycle_runner.artifact_bytes)),
                'A traffic effect requires the actual exact selected application phase owner')
        require(step_id in self.writers or step_id in self.readers, 'The selected traffic step is unavailable')
        # Completed stage receipts are observations. Never reacquire the old
        # writer just to inspect its independently retained authoritative state.
        delivery, step, ledger = self._delivery(admitted, selection, step_id, observation=True)
        with execution_journal.locked(ledger, {'owner': 'delivery', **delivery['scope']}) as log:
            starts, receipts, _new, _closed, _renewals = delivery_run.replay(log, delivery)
            base = log.directory / 'runs' / canonical_record_digest(delivery)
            directory = base / 'steps' / step_id
            if step_id in receipts:
                packet = starts[step_id]['packet']
                owner = self.writers.get(step_id) or self.readers[step_id]
                return owner.inspect_resolved(admitted, selection, delivery, step, packet, directory, base, self.source_root)
            require(step_id not in starts, 'Original traffic outcome is uncertain; independently resolve it before continuing')
            labels = {key for member in self.lifecycle.to_dict()['members']
                      for key, value in member['traffic_steps'].items() if value == step_id}
            require(len(labels) == 1, 'One traffic operation cannot mix cutover and return')
            returning = next(iter(labels)).startswith('return_')
            for member in self.lifecycle.to_dict()['members']:
                if returning:
                    lifecycle_runner._require_before_target_writes(member['machine_id'])
                    lifecycle_runner._current_target_exclusion(member['machine_id'])
                    lifecycle_runner.independently_resolved(member['machine_id'], 'PREWRITE_RETURN')
                else:
                    lifecycle_runner._all_source_exclusions()
                    lifecycle_runner.independently_resolved(member['machine_id'], 'ACTIVATE')
                lifecycle_runner.current_health(member['machine_id'], health_readers,
                                                side='source' if returning else 'destination')
            self._delivery(admitted, selection, step_id, observation=False)
            source = verify(self.source_root)
            require(source['status'] == 'HASHES_MATCH' and source['commit'] == selection['sourceCommit']
                    and verify_runtime(self.source_root)['status'] == 'RUNTIME_SOURCES_MATCH',
                    'The actual traffic execution code differs from the selected original source')
            require(set(step['needs']) <= receipts.keys(), 'The original traffic dependencies are incomplete')
            packet = delivery_run.packet(self.inbox_directory / admitted.job_id / (step_id + '.json'), delivery, step, receipts)
            operation = 'DNS_CHANGE' if step_id in self.writers else 'DISCOVER_READ'
            self.authority.require_packet(admitted, canonical_record_digest(selection), delivery, step, packet, operation)
            for path in (base, base / 'steps', directory):
                if not path.exists():
                    path.mkdir(mode=0o700); sync_directory(path.parent)
                private_path(path, directory=True)
            require(not tuple(directory.iterdir()), 'A previous unrecorded traffic attempt must be reconciled')
            write_new(directory / 'packet.json', encoded(packet))
            log.append('STEP_STARTED', dict(step_id=step_id, packet=packet, packet_sha256=canonical_record_digest(packet)))
            owner = self.writers.get(step_id) or self.readers[step_id]
            result, names = owner.run_step(admitted, selection, delivery, step, packet, directory, base, self.source_root)
            receipt = dict(step_id=step_id, packet_sha256=canonical_record_digest(packet), status=result['status'],
                artifacts=delivery_run.artifact_receipt(directory, names), native_acceptance=False, production_activation=False)
            log.append('STEP_COMPLETED', receipt)
            return dict(format='hosting-application-traffic-stage-retained/1', step_id=step_id,
                        receipt_digest=canonical_record_digest(receipt), independent_current_readback_required=True)

    def verify(self, admitted, selection, member_id, *, returning=False):
        member = self.lifecycle.member(member_id)
        prefix = 'return' if returning else 'cutover'
        selected = member['traffic_steps']
        facts = {}
        for label in ('dns', 'propagation'):
            step_id = selected[prefix + '_' + label]
            delivery, step, ledger = self._delivery(admitted, selection, step_id, observation=True)
            with execution_journal.locked(ledger, {'owner': 'delivery', **delivery['scope']}) as log:
                starts, receipts, *_ = delivery_run.replay(log, delivery)
                require(step_id in receipts and step_id in starts, 'The selected original traffic stage is not retained')
                base = log.directory / 'runs' / canonical_record_digest(delivery)
                directory = base / 'steps' / step_id
                require(canonical_record_digest(load_private(directory / 'packet.json')) == receipts[step_id]['packet_sha256'],
                        'The retained original traffic packet changed')
                owner = self.writers[step_id] if label == 'dns' else self.readers[step_id]
                facts[label] = owner.inspect_resolved(admitted, selection, delivery, step,
                    starts[step_id]['packet'], directory, base, self.source_root)
        primary = facts['dns']
        propagation = facts['propagation']
        require(primary['format'] == 'hosting-resolved-service-inspection/1'
                and propagation['format'] == 'hosting-enrolled-dns-propagation/1'
                and propagation['primary_operation_id'] == primary['operation_id']
                and propagation['primary_request_digest'] == primary['request_digest']
                and propagation['primary_receipt_digest'] == canonical_record_digest(primary['receipt']),
                'The independent resolver generation differs from the exact original authoritative change')
        return dict(format='hosting-current-application-traffic/1', member_id=member_id,
            lifecycle_digest=self.lifecycle.sha256, original_job_id=admitted.job_id, direction=prefix, evidence=facts)
