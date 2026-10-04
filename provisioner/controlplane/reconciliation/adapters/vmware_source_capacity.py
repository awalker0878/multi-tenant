"""Retained-source occupancy from a separately enrolled vCenter reader.

Only approved original VM selectors are read. Power-off does not release a
charge, a disk UUID comes from actual backing data, and detached base disks
require their separately enrolled current file reader. Native snapshot chains
remain held until their complete storage accounting owner is commissioned.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path
import time

from provisioner.allocations.transactions import PoolDemand, ResourceBundle, ResourceObservation, ResourceUnits
from provisioner.controlplane.authority import PlanScope
from provisioner.controlplane.persistence import EnterpriseRecordStore, NativeBinding, canonical_record_digest
from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
from provisioner.execution import readback_core as c, vsphere_observe as vm
from provisioner.execution.vsphere_history import CollectorClient
from provisioner.execution.run_files import encoded, load_private, private_path, require, utcnow, write_new
from provisioner.migration.vsphere_credentials import VsphereNativeCredentialOwner


@dataclass(frozen=True)
class SourceCapacityReadRuntime:
    enrollment: NativeReadEnrollment
    credentials: VsphereNativeCredentialOwner
    authority: PostgresExecutionAuthority
    records: EnterpriseRecordStore
    resource_pool_id: str
    ca_file: Path
    directory: Path
    backing_reader: object = None

    def __post_init__(self):
        require(type(self.enrollment) is NativeReadEnrollment and type(self.credentials) is VsphereNativeCredentialOwner
            and self.credentials.commands is self.enrollment.command
            and isinstance(self.authority, PostgresExecutionAuthority)
            and self.enrollment.command.authority is self.authority and isinstance(self.records, EnterpriseRecordStore)
            and self.records._connect is self.enrollment.command.grants._connect,
            'Actual independent current reader, revocable native custody and original protected record owners required')
        vm.moid(self.resource_pool_id, 'resgroup')
        object.__setattr__(self, 'directory', private_path(self.directory, directory=True))
        object.__setattr__(self, 'ca_file', Path(self.ca_file))
        if self.backing_reader is not None:
            from .vmware_source_backing import SourceBackingReadRuntime
            require(type(self.backing_reader) is SourceBackingReadRuntime
                and self.backing_reader.enrollment is self.enrollment
                and self.backing_reader.credentials is self.credentials
                and self.backing_reader.ca_file == self.ca_file,
                'The retained-backing reader must use this exact independently enrolled native custody')

    def _selected(self, bundle, pool, selected, *, cursor=None):
        require(isinstance(bundle, ResourceBundle) and type(pool) is PoolDemand and pool in bundle.pools
            and pool.scope == self.enrollment.scope and pool.inputs is None
            and pool.catalog['origin'] == self.credentials.profile.origin,
            'The retained-source observation differs from its independently enrolled pool/datacenter')
        plan, artifact = self.authority.require_observation(bundle.admitted, bundle.selection_digest,
            'DISCOVER_READ', **({'cursor': cursor} if cursor is not None else {}))
        require(artifact['resourceBundleDigest'] == bundle.digest and PlanScope.from_record(plan['spec']['source']) == pool.scope
            and (plan['spec']['workloadId'], plan['spec']['workloadRevision']) ==
                (bundle.workload_id, bundle.workload_revision),
            'The original retained-source resource custody changed')
        expected = tuple(NativeBinding(row['sourceBinding']['platformFamily'], row['sourceBinding']['endpointId'],
            row['sourceBinding']['nativeScopeId'], 'vm', row['sourceBinding']['nativeId'])
            for row in plan['spec']['machineMappings'])
        require(isinstance(selected, tuple) and set(selected) == set(expected) and len(selected) == len(expected),
            'Only the complete exact originally approved source VM selectors may be accounted')
        return expected

    def _read(self, bundle, pool, selected, *, cursor=None, retained_facts=None):
        selected = self._selected(bundle, pool, selected, cursor=cursor)
        options = {'cursor': cursor} if cursor is not None else {}
        facts, native_ids, cpu, memory, storage = [], set(), 0, 0, 0
        retained = {}
        if retained_facts is not None:
            require(type(retained_facts) is list and len(retained_facts) == len(selected),
                'The complete exact original retained VM observations are required')
            for fact in retained_facts:
                binding = NativeBinding(**fact['binding'])
                require(binding in selected and binding.native_id not in retained,
                    'The original retained source contains a foreign or duplicate VM')
                retained[binding.native_id] = fact['native']
        for binding in selected:
            def exchange(path):
                self.enrollment.require_current(**options)
                session = self.credentials.acquire_session(self.enrollment, native_id=binding.native_id,
                    origin=self.credentials.profile.origin, ca_file=self.ca_file, cursor=cursor)
                client = CollectorClient(self.credentials.profile.origin, self.credentials.profile.origin,
                    session.token, {path}, 'TaskManager', str(self.ca_file))
                seconds = (session.expires_at - utcnow()).total_seconds(); require(seconds > 0, 'Native source read expired')
                client.timeout = min(10, seconds); client.deadline = time.monotonic() + seconds
                value, _etag = client._request('GET', path, response_type=(dict, type(None)) if path.endswith('/snapshot') else dict)
                self.enrollment.require_current(**options)
                return value
            base = vm.PREFIX + 'VirtualMachine/' + binding.native_id + '/'
            first = {key: exchange(base + key) for key in ('config', 'runtime', 'resourcePool', 'snapshot')}
            require(first['resourcePool'] == {'type': 'ResourcePool', 'value': self.resource_pool_id}
                or first['resourcePool'] == {'_typeName': 'ManagedObjectReference', 'type': 'ResourcePool',
                                             'value': self.resource_pool_id},
                'The actual original VM belongs to another commissioned source resource pool')
            require(first['snapshot'] is None, 'Source VM snapshot/storage chains require separate complete retained accounting')
            config, runtime = first['config'], first['runtime']; hardware = config['hardware']
            require(config.get('template') is False and isinstance(config.get('changeVersion'), str)
                and runtime.get('connectionState') == 'connected'
                and runtime.get('powerState') in {'poweredOn', 'poweredOff'}
                and not runtime.get('vmFailoverInProgress') and not runtime.get('consolidationNeeded')
                and type(hardware.get('numCPU')) is int and hardware['numCPU'] > 0
                and type(hardware.get('memoryMB')) is int and hardware['memoryMB'] > 0,
                'The actual source occupancy is incomplete, changing or unavailable')
            vm.devices(hardware['device'])
            disks = [row for row in hardware['device'] if row['_typeName'] == 'VirtualDisk']
            detached = []
            if retained_facts is not None:
                original = retained[binding.native_id]['config']
                require(all(config.get(key) == original.get(key) for key in ('uuid', 'instanceUuid', 'template'))
                    and hardware['numCPU'] == original['hardware']['numCPU']
                    and hardware['memoryMB'] == original['hardware']['memoryMB'],
                    'The originally charged source VM identity or compute footprint changed')
                vm.devices(original['hardware']['device'])
                originals = {row['key']: row for row in original['hardware']['device']
                    if row['_typeName'] == 'VirtualDisk'}
                require(all(row['key'] in originals and row == originals[row['key']] for row in disks),
                    'An attached disk differs from the exact originally charged native backing')
                detached = [row for key, row in originals.items() if key not in {disk['key'] for disk in disks}]
                require(not detached or self.backing_reader is not None,
                    'Detached original storage needs its separately enrolled complete current backing reader')
            detached_facts = [self.backing_reader.observe(binding, disk, cursor=cursor) for disk in detached]
            datastore_ids = {row['backing']['datastore']['value'] for row in disks}
            datastores = {}
            for identity in sorted(datastore_ids):
                summary = exchange(vm.PREFIX + 'Datastore/' + identity + '/summary')
                require(summary.get('accessible') is True and summary.get('multipleHostAccess') is True
                    and type(summary.get('capacity')) is int and summary['capacity'] > 0
                    and type(summary.get('freeSpace')) is int and 0 <= summary['freeSpace'] <= summary['capacity'],
                    'The source backing datastore is unavailable or lacks exact current storage units')
                datastores[identity] = summary
            second = {key: exchange(base + key) for key in ('config', 'runtime', 'resourcePool', 'snapshot')}
            require(first == second, 'The actual source native configuration changed during capacity observation')
            disk_ids = {row['backing']['uuid'] for row in disks + detached}
            require(not (native_ids & (disk_ids | {binding.native_id})), 'A shared native VM/backing cannot be double counted')
            native_ids |= disk_ids | {binding.native_id}
            cpu += hardware['numCPU']; memory += hardware['memoryMB'] * 1024**2
            storage += sum(row['capacityInBytes'] for row in disks + detached)
            fact = dict(binding=asdict(binding), native=first, datastores=datastores)
            if detached_facts:
                fact['detached_backings'] = detached_facts
            facts.append(fact)
        units = ResourceUnits.from_bytes(vcpu=cpu, memory_bytes=memory, storage_bytes=storage)
        require(all(asdict(pool.retained_source)[key] <= asdict(units)[key] <= pool.total(current=False)[key]
            for key in ('vcpu', 'memory_mb', 'storage_gb')),
            'The measured retained source footprint lies outside its exact approved charged resource envelope')
        return tuple(sorted(native_ids)), units, facts

    def observe_resource(self, bundle, pool, reservation_id, selected_source_bindings, cursor=None):
        ids, units, facts = self._read(bundle, pool, selected_source_bindings, cursor=cursor)
        at = utcnow()
        record = dict(format='hosting-vsphere-source-capacity-observation/1', job_id=bundle.admitted.job_id,
            selection_digest=bundle.selection_digest, bundle_digest=bundle.digest, pool_id=pool.catalog['pool_id'],
            reservation_id=reservation_id, scope=asdict(pool.scope), units=asdict(units), native_ids=list(ids),
            selected_source_bindings=[asdict(row) for row in selected_source_bindings], facts=facts,
            reader_subject=self.enrollment.subject, reader_grant_id=self.enrollment.command.grant.grant_id,
            observed_at=at.isoformat(), cleanup_observed=False)
        reference = canonical_record_digest(record); write_new(self.directory / (reference + '.json'), encoded(record))
        return ResourceObservation(reservation_id, reference, ids, units, 'EFFECT_PRESENT', at)

    def verify_resource_observation(self, cursor, bundle, action, observation):
        require(action == 'confirm' and isinstance(observation, ResourceObservation)
            and observation.outcome == 'EFFECT_PRESENT', 'Source occupancy never supplies cleanup or refund authority')
        record = load_private(self.directory / (observation.evidence_digest + '.json'))
        require(canonical_record_digest(record) == observation.evidence_digest
            and (record['job_id'], record['selection_digest'], record['bundle_digest'], record['reservation_id']) ==
                (bundle.admitted.job_id, bundle.selection_digest, bundle.digest, observation.reservation_id)
            and record['reader_subject'] == self.enrollment.subject
            and record['reader_grant_id'] == self.enrollment.command.grant.grant_id
            and record['native_ids'] == list(observation.native_ids) and record['units'] == asdict(observation.units)
            and record['observed_at'] == observation.observed_at.isoformat()
            and utcnow() - timedelta(minutes=5) <= observation.observed_at <= utcnow(),
            'The independently retained source occupancy differs from its original native evidence')
        pool = next(row for row in bundle.pools if row.scope == self.enrollment.scope
            and row.catalog['pool_id'] == record['pool_id'])
        ids, units, facts = self._read(bundle, pool, tuple(NativeBinding(**row) for row in record['selected_source_bindings']), cursor=cursor)
        require(ids == observation.native_ids and units == observation.units
            and canonical_record_digest(facts) == canonical_record_digest(record['facts']),
            'The original native retained-source occupancy changed; preserve all earlier charges')

    def require_accounted(self, cursor, bundle, pool, receipt, original_plan):
        """Re-read exact original occupancy, including selected detached files.

        Current power alone does not alter CPU/RAM or retained storage charges.
        The old observation selects exact files; fresh native UUID, capacity and
        extent reads supply presence. It never supplies cleanup/refund authority.
        """
        require(receipt.get('status') == 'CONFIRMED' and original_plan['metadata']['planDigest'] == bundle.admitted.plan_digest,
            'Only the exact independently confirmed original source charge may continue')
        selected = tuple(NativeBinding(row['sourceBinding']['platformFamily'], row['sourceBinding']['endpointId'],
            row['sourceBinding']['nativeScopeId'], 'vm', row['sourceBinding']['nativeId'])
            for row in original_plan['spec']['machineMappings'])
        reference = receipt.get('evidence_ref')
        require(type(reference) is str and c.HEX.fullmatch(reference), 'Original source evidence custody is unavailable')
        record = load_private(self.directory / (reference + '.json'))
        require(canonical_record_digest(record) == reference
            and record['format'] == 'hosting-vsphere-source-capacity-observation/1'
            and (record['job_id'], record['selection_digest'], record['bundle_digest'], record['reservation_id']) ==
                (bundle.admitted.job_id, bundle.selection_digest, bundle.digest, receipt['reservation_id'])
            and record['pool_id'] == pool.catalog['pool_id'] and record['scope'] == asdict(pool.scope)
            and record['reader_subject'] == self.enrollment.subject
            and record['reader_grant_id'] == self.enrollment.command.grant.grant_id
            and len(record['selected_source_bindings']) == len(selected)
            and {NativeBinding(**row) for row in record['selected_source_bindings']} == set(selected)
            and set(record['native_ids']) == set(receipt['native_ids'])
            and all(record['units'][key] <= receipt['units'][key] for key in receipt['units'])
            and record['cleanup_observed'] is False,
            'The retained selector differs from the exact original independently confirmed source charge')
        ids, units, facts = self._read(bundle, pool, selected, cursor=cursor, retained_facts=record['facts'])
        require(set(receipt['native_ids']) == set(ids)
            and all(asdict(units)[key] <= receipt['units'][key] for key in ('vcpu', 'memory_mb', 'storage_gb')),
            'A retained source native identity is missing or its charged footprint changed; keep the original charge held')
        return dict(format='hosting-current-retained-source-capacity/1', native_ids=list(ids), units=asdict(units),
            original_reservation_id=receipt['reservation_id'], native_observation_digest=canonical_record_digest(facts),
            observed_at=utcnow().isoformat(), cleanup_observed=False)
