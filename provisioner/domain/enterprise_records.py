"""Validation for internal enterprise workload and migration records.

These records describe observed resources and selected operations. They are not
accepted as portable WSD requests and validation is not execution authority.
The database will enforce unique identities, revisions and append-only history.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime

from provisioner.schemas import registry


def _problem(problems: list[dict], path: str, message: str) -> None:
    problems.append({'path': path, 'message': message})


def _duplicates(items: list, path: str, problems: list[dict]) -> None:
    seen = set()
    for index, item in enumerate(items):
        key = json.dumps(item, sort_keys=True, separators=(',', ':'))
        if key in seen:
            _problem(problems, f'{path}[{index}]', 'Duplicate identity')
        seen.add(key)


def _binding_key(binding: dict) -> tuple:
    return (binding['endpointId'], binding['nativeScopeId'],
            binding['resourceKind'], binding['nativeId'], binding['platformFamily'])


def _scope_key(scope: dict) -> tuple:
    return (scope['organizationId'], scope['tenantId'], scope['securityDomainId'],
            scope['endpointId'], scope['nativeScopeId'], scope['locationId'])


def _scope_tenant_matches(scope: dict, metadata: dict) -> bool:
    return (scope['organizationId'], scope['tenantId']) == (
        metadata['organizationId'], metadata['tenantId'])


@dataclass(frozen=True)
class VerifiedWsdTransition:
    """Decision already authenticated by the future product authority boundary.

    Constructing this value does not authenticate a grant. It must come from an
    independent approval/observation check, never directly from a client record.
    """
    organization_id: str
    tenant_id: str
    workload_id: str
    from_wsd_id: str
    to_wsd_id: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    grant_digest: str
    observation_digest: str


def _binding_in_scope(binding: dict, scope: dict) -> bool:
    return (binding['endpointId'] == scope['endpointId']
            and binding['nativeScopeId'] == scope['nativeScopeId']
            and binding['platformFamily'] == scope['platformFamily'])


def _check_unknown_fields(resource: dict, fields: tuple[str, ...],
                          path: str, problems: list[dict],
                          incomplete: tuple[str, ...] = ()) -> None:
    declared = set(resource['unknownFields'])
    unknown = {field for field in fields if resource[field]['state'] == 'UNKNOWN'}
    unknown.update(field for field in incomplete if not resource[field + 'Complete'])
    missing = unknown - declared
    falsely_unknown = declared & (set(fields) | set(incomplete)) - unknown
    if missing or falsely_unknown:
        _problem(problems, path + '.unknownFields',
                 'Known/unknown facts and collection completeness must match unknownFields')


def plan_digest(plan: dict) -> str:
    """Content digest for a plan revision, excluding only its own digest field."""
    unsigned = deepcopy(plan)
    unsigned['metadata'].pop('planDigest', None)
    raw = json.dumps(unsigned, sort_keys=True, separators=(',', ':'),
                     ensure_ascii=False, allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _workload(record: dict, problems: list[dict]) -> None:
    spec = record['spec']
    membership = spec['membership']
    accepted = record['metadata']['wsdId']
    candidate = membership['candidateWsdId']
    transition = membership['transition']
    if membership['state'] == 'ACCEPTED':
        if candidate is not None or transition is not None:
            _problem(problems, '$.spec.membership', 'Accepted membership cannot include a pending target')
    elif not candidate or candidate == accepted or transition is None:
        _problem(problems, '$.spec.membership', 'Provisional membership requires a distinct target and plan')
    elif membership['state'] == 'PENDING' and transition['observationDigest'] is not None:
        _problem(problems, '$.spec.membership.transition', 'Pending membership cannot claim observed realization')
    elif membership['state'] == 'OBSERVED' and (not transition['grantDigest'] or not transition['observationDigest']):
        _problem(problems, '$.spec.membership.transition', 'Observed membership requires grant and observation digests')
    previous_target = None
    for index, event in enumerate(membership['history']):
        if event['fromWsdId'] == event['toWsdId'] or (previous_target is not None and previous_target != event['fromWsdId']):
            _problem(problems, f'$.spec.membership.history[{index}]', 'Membership history is not a continuous transition')
        previous_target = event['toWsdId']
    if previous_target is not None and previous_target != accepted:
        _problem(problems, '$.spec.membership.history', 'Latest accepted membership does not match history')
    machines = spec['machines']
    machine_ids = {machine['machineId'] for machine in machines}
    _duplicates([m['machineId'] for m in machines], '$.spec.machines', problems)
    _duplicates([d['datasetId'] for d in spec['datasets']], '$.spec.datasets', problems)
    native_owner: dict[tuple, tuple[str, str, str]] = {}
    for index, machine in enumerate(machines):
        path = f'$.spec.machines[{index}]'
        _check_unknown_fields(machine, ('guestProfile', 'cpuCount', 'memoryMiB', 'firmware'),
                              path, problems, ('disks', 'nics'))
        if spec['state'] != 'PLANNED' and not machine['bindings']:
            _problem(problems, path + '.bindings', 'Discovered machines require a native binding')
        _duplicates([d['diskId'] for d in machine['disks']], path + '.disks', problems)
        _duplicates([d['slot'] for d in machine['disks']], path + '.disks', problems)
        _duplicates([n['nicId'] for n in machine['nics']], path + '.nics', problems)
        _duplicates([n['slot'] for n in machine['nics']], path + '.nics', problems)
        for disk_index, disk in enumerate(machine['disks']):
            _check_unknown_fields(disk, ('sizeBytes', 'format'),
                                  f'{path}.disks[{disk_index}]', problems)
        for nic_index, nic in enumerate(machine['nics']):
            _check_unknown_fields(nic, ('network', 'address'),
                                  f'{path}.nics[{nic_index}]', problems)
        for resource_kind, resources in (('vm', [machine]), ('disk', machine['disks']),
                                         ('nic', machine['nics'])):
            for resource in resources:
                component_id = (machine['machineId'] if resource_kind == 'vm' else
                                resource['diskId'] if resource_kind == 'disk' else resource['nicId'])
                owner = (resource_kind, machine['machineId'], component_id)
                _duplicates([_binding_key(b['binding']) for b in resource['bindings']],
                            path + '.bindings', problems)
                for history in resource['bindings']:
                    binding = history['binding']
                    if binding['resourceKind'] != resource_kind:
                        _problem(problems, path + '.bindings', 'Native binding has the wrong resource kind')
                    key = _binding_key(binding)
                    if key in native_owner and native_owner[key] != owner:
                        _problem(problems, path + '.bindings', 'Native identity is bound to two logical resources')
                    native_owner[key] = owner
    for index, dataset in enumerate(spec['datasets']):
        _check_unknown_fields(dataset, ('sizeBytes',), f'$.spec.datasets[{index}]', problems)
        if dataset['machineId'] is not None and dataset['machineId'] not in machine_ids:
            _problem(problems, f'$.spec.datasets[{index}].machineId', 'Unknown machine identity')
        _duplicates([_binding_key(b) for b in dataset['sourceBindings']],
                    f'$.spec.datasets[{index}].sourceBindings', problems)


def _application(record: dict, problems: list[dict]) -> None:
    spec = record['spec']
    workloads = set(spec['workloadIds'])
    if not workloads:
        _problem(problems, '$.spec.workloadIds', 'Application group requires workloads')
    if set(spec['startupOrder']) != workloads or len(spec['startupOrder']) != len(workloads):
        _problem(problems, '$.spec.startupOrder', 'Startup order must include every workload once')
    dataset_ids = set(spec['datasetIds'])
    groups = spec['consistencyGroups']
    _duplicates([g['groupId'] for g in groups], '$.spec.consistencyGroups', problems)
    _duplicates([d for g in groups for d in g['datasetIds']], '$.spec.consistencyGroups', problems)
    for index, group in enumerate(groups):
        if not group['datasetIds'] or not set(group['datasetIds']) <= dataset_ids:
            _problem(problems, f'$.spec.consistencyGroups[{index}].datasetIds',
                     'Consistency group requires known datasets')
    _duplicates([d['dependencyId'] for d in spec['dependencies']], '$.spec.dependencies', problems)
    for index, dependency in enumerate(spec['dependencies']):
        if dependency['sourceWorkloadId'] not in workloads:
            _problem(problems, f'$.spec.dependencies[{index}].sourceWorkloadId',
                     'Dependency source is not in this application')


def _observation(record: dict, problems: list[dict]) -> None:
    meta, spec = record['metadata'], record['spec']
    try:
        captured = datetime.fromisoformat(meta['capturedAt'].replace('Z', '+00:00'))
        expires = datetime.fromisoformat(meta['expiresAt'].replace('Z', '+00:00'))
        if expires <= captured:
            _problem(problems, '$.metadata.expiresAt', 'Observation must expire after capture')
    except ValueError:
        _problem(problems, '$.metadata.capturedAt', 'Invalid UTC timestamp')
    if spec['completeness'] == 'COMPLETE' and (spec['collectionErrors'] or spec['missingFields']):
        _problem(problems, '$.spec.completeness', 'Complete observation has errors or missing fields')
    _duplicates([_binding_key(o['binding']) for o in spec['objects']], '$.spec.objects', problems)
    for index, observation in enumerate(spec['objects']):
        path = f'$.spec.objects[{index}]'
        binding = observation['binding']
        if binding['endpointId'] != spec['endpointId'] or binding['nativeScopeId'] not in spec['readScopes']:
            _problem(problems, path + '.binding', 'Native object lies outside observed endpoint or read scopes')
        _duplicates([f['field'] for f in observation['facts']], path + '.facts', problems)
        if observation['presence'] != 'PRESENT' and observation['facts']:
            _problem(problems, path + '.facts', 'Unobserved objects cannot have observed facts')
        unknown = {f['field'] for f in observation['facts'] if f['state'] == 'UNKNOWN'}
        if unknown != set(observation['missingFields']):
            _problem(problems, path + '.missingFields', 'Missing fields must equal unknown facts')
        if spec['completeness'] == 'COMPLETE' and (observation['presence'] == 'UNKNOWN' or unknown):
            _problem(problems, path, 'Complete observation cannot contain unknown objects or fields')


def _plan(record: dict, problems: list[dict], workload: dict | None) -> None:
    meta, spec = record['metadata'], record['spec']
    if meta['planDigest'] != plan_digest(record):
        _problem(problems, '$.metadata.planDigest', 'Plan digest does not bind this exact revision')
    if _scope_key(spec['source']) == _scope_key(spec['destination']):
        _problem(problems, '$.spec.destination', 'Source and destination locations are identical')
    for name in ('source', 'destination'):
        if not _scope_tenant_matches(spec[name], meta):
            _problem(problems, f'$.spec.{name}', 'Scope lies outside plan organization or tenant')
    if spec['route']['method'] == 'SAME_PLATFORM_RELOCATION' and spec['source']['platformFamily'] != spec['destination']['platformFamily']:
        _problem(problems, '$.spec.route.method', 'Native relocation requires the same platform family')
    mappings = spec['machineMappings']
    _duplicates([m['machineId'] for m in mappings], '$.spec.machineMappings', problems)
    _duplicates([m['targetMachineId'] for m in mappings], '$.spec.machineMappings', problems)
    _duplicates([_binding_key(m['sourceBinding']) for m in mappings],
                '$.spec.machineMappings', problems)
    _duplicates([d['targetVolumeRef'] for m in mappings for d in m['diskMappings']],
                '$.spec.machineMappings', problems)
    if {m['machineId'] for m in mappings} != set(spec['selectedMachineIds']):
        _problem(problems, '$.spec.machineMappings', 'Every selected machine requires exactly one mapping')
    for index, mapping in enumerate(mappings):
        path = f'$.spec.machineMappings[{index}]'
        if mapping['sourceBinding']['resourceKind'] != 'vm' or not _binding_in_scope(mapping['sourceBinding'], spec['source']):
            _problem(problems, path + '.sourceBinding', 'Source VM binding does not match source scope')
        _duplicates([d['diskId'] for d in mapping['diskMappings']], path + '.diskMappings', problems)
        _duplicates([d['targetVolumeRef'] for d in mapping['diskMappings']], path + '.diskMappings', problems)
        _duplicates([n['nicId'] for n in mapping['nicMappings']], path + '.nicMappings', problems)
    dataset_mappings = spec['datasetMappings']
    _duplicates([d['datasetId'] for d in dataset_mappings], '$.spec.datasetMappings', problems)
    _duplicates([d['targetRef'] for d in dataset_mappings], '$.spec.datasetMappings', problems)
    if {d['datasetId'] for d in dataset_mappings} != set(spec['selectedDatasetIds']):
        _problem(problems, '$.spec.datasetMappings', 'Every selected dataset requires exactly one mapping')
    if workload is None:
        return
    if validate_record(workload) or workload['kind'] != 'Workload':
        _problem(problems, '$.spec.workloadId', 'Invalid bound workload record')
        return
    wm = workload['metadata']
    if (wm['organizationId'], wm['tenantId'], wm['workloadId'], wm['revision']) != (
            meta['organizationId'], meta['tenantId'], spec['workloadId'], spec['workloadRevision']):
        _problem(problems, '$.spec.workloadId', 'Plan does not bind this workload revision and tenant')
        return
    if spec['source']['securityDomainId'] != wm['wsdId']:
        _problem(problems, '$.spec.source.securityDomainId', 'Source WSD does not match accepted workload membership')
    membership = workload['spec']['membership']
    if (membership['state'] != 'ACCEPTED'
            and membership['candidateWsdId'] != spec['destination']['securityDomainId']):
        _problem(problems, '$.spec.destination.securityDomainId',
                 'Destination WSD differs from provisional workload membership')
    machines = {m['machineId']: m for m in workload['spec']['machines']}
    for index, mapping in enumerate(mappings):
        path = f'$.spec.machineMappings[{index}]'
        machine = machines.get(mapping['machineId'])
        if machine is None:
            _problem(problems, path + '.machineId', 'Machine is not in the bound workload')
            continue
        if not any(h['binding'] == mapping['sourceBinding'] and h['role'] == 'SOURCE'
                   and h['lastObservedSnapshotId'] == spec['sourceSnapshotId']
                   for h in machine['bindings']):
            _problem(problems, path + '.sourceBinding',
                     'Source binding must be active and observed in selected source snapshot')
        if not machine['disksComplete'] or not machine['nicsComplete']:
            _problem(problems, path, 'Selected machine has incomplete disk or NIC inventory')
        if {d['diskId'] for d in mapping['diskMappings']} != {d['diskId'] for d in machine['disks']}:
            _problem(problems, path + '.diskMappings', 'Every discovered disk requires a mapping')
        if {n['nicId'] for n in mapping['nicMappings']} != {n['nicId'] for n in machine['nics']}:
            _problem(problems, path + '.nicMappings', 'Every discovered NIC requires a mapping')
    datasets = {d['datasetId']: d for d in workload['spec']['datasets']}
    for index, mapping in enumerate(dataset_mappings):
        source_dataset = datasets.get(mapping['datasetId'])
        if source_dataset is None or source_dataset['consistencyGroupId'] != mapping['consistencyGroupId']:
            _problem(problems, f'$.spec.datasetMappings[{index}]', 'Dataset or consistency group is not in the bound workload')


def _transfer(record: dict, problems: list[dict], plan: dict | None) -> None:
    meta, spec = record['metadata'], record['spec']
    source, target = spec['sourceScope'], spec['destinationScope']
    for name, scope in (('sourceScope', source), ('destinationScope', target)):
        if not _scope_tenant_matches(scope, meta):
            _problem(problems, f'$.spec.{name}', 'Transfer scope lies outside organization or tenant')
    receipt, grant = spec['sourceReceipt'], spec['grant']
    if receipt['sourceScope'] != source or receipt['datasetId'] != spec['datasetId'] or receipt['snapshotId'] != spec['sourceSnapshotId']:
        _problem(problems, '$.spec.sourceReceipt', 'Source receipt provenance does not match transfer')
    if grant['sourceScope'] != source or grant['destinationScope'] != target:
        _problem(problems, '$.spec.grant', 'Grant must bind both original source and destination scopes')
    if not _binding_in_scope(spec['sourceNativeBinding'], source):
        _problem(problems, '$.spec.sourceNativeBinding', 'Dataset binding does not match source scope')
    if plan is None:
        return
    if validate_record(plan) or plan['kind'] != 'MigrationPlan':
        _problem(problems, '$.metadata.planId', 'Invalid bound migration plan')
        return
    pm, ps = plan['metadata'], plan['spec']
    if (meta['organizationId'], meta['tenantId'], meta['planId'], meta['planRevision'], meta['planDigest']) != (
            pm['organizationId'], pm['tenantId'], pm['planId'], pm['revision'], pm['planDigest']):
        _problem(problems, '$.metadata.planId', 'Transfer does not bind this exact plan and tenant')
    if source != ps['source'] or target != ps['destination']:
        _problem(problems, '$.spec.sourceScope', 'Transfer scopes do not match migration plan')
    if spec['sourceWorkloadId'] != ps['workloadId'] or spec['targetWorkloadId'] != ps['workloadId']:
        _problem(problems, '$.spec.sourceWorkloadId', 'Stable workload identity must survive migration')
    if spec['sourceSnapshotId'] != ps['sourceSnapshotId']:
        _problem(problems, '$.spec.sourceSnapshotId', 'Transfer does not use the selected source snapshot')
    if not any(d['datasetId'] == spec['datasetId']
               and d['targetRef'] == spec['targetRef']
               and d['consistencyGroupId'] == spec['consistencyGroupId']
               for d in ps['datasetMappings']):
        _problem(problems, '$.spec.datasetId', 'Dataset mapping is not in the selected plan')


def _activity(record: dict, problems: list[dict], plan: dict | None) -> None:
    meta, spec = record['metadata'], record['spec']
    status = spec['status']
    if status == 'COMPLETED' and (not spec['evidenceDigests'] or spec['effects'] == 'UNKNOWN' or spec['failureCode'] is not None):
        _problem(problems, '$.spec.status', 'Completed activity needs evidence and known effects')
    if status == 'RUNNING' and not (spec['nativeTaskId'] or spec['continuationRef']):
        _problem(problems, '$.spec.nativeTaskId', 'Running activity needs a task or continuation reference')
    if status == 'FAILED' and not spec['failureCode']:
        _problem(problems, '$.spec.failureCode', 'Failed activity requires a failure code')
    if status == 'OUTCOME_UNKNOWN' and (spec['effects'] != 'UNKNOWN' or spec['retry'] != 'RECONCILE'):
        _problem(problems, '$.spec.retry', 'Unknown native effect requires reconciliation before retry')
    if spec['effects'] == 'UNKNOWN' and spec['retry'] == 'SAFE':
        _problem(problems, '$.spec.retry', 'Unknown effects cannot be retried blindly')
    if plan is not None:
        if validate_record(plan) or plan['kind'] != 'MigrationPlan':
            _problem(problems, '$.metadata.planId', 'Invalid bound migration plan')
        elif (meta['organizationId'], meta['tenantId'], meta['planId'], meta['planRevision'], meta['planDigest']) != (
                plan['metadata']['organizationId'], plan['metadata']['tenantId'], plan['metadata']['planId'],
                plan['metadata']['revision'], plan['metadata']['planDigest']):
            _problem(problems, '$.metadata.planId', 'Activity does not bind this exact plan and tenant')


def validate_record(record: dict, *, workload: dict | None = None,
                    plan: dict | None = None) -> list[dict]:
    """Fail closed on shape, identity, mapping, provenance and result invariants.

    Supply the selected workload/plan to validate relationships before a plan
    or transfer is stored. Installed-platform qualification remains a separate gate.
    """
    problems = registry.validate_named(record, 'enterprise-record')
    if problems:
        return problems
    kind = record['kind']
    if kind == 'Workload':
        _workload(record, problems)
    elif kind == 'ApplicationGroup':
        _application(record, problems)
    elif kind == 'ObservationSnapshot':
        _observation(record, problems)
    elif kind == 'MigrationPlan':
        _plan(record, problems, workload)
    elif kind == 'TransferManifest':
        _transfer(record, problems, plan)
    elif kind == 'ActivityResult':
        _activity(record, problems, plan)
    return problems


def validate_destination_activation(workload: dict, destination_wsd_id: str) -> list[dict]:
    """A provisional target WSD is never a production membership."""
    problems = validate_record(workload)
    if problems:
        return problems
    if workload['kind'] != 'Workload':
        return [{'path': '$.kind', 'message': 'Expected Workload record'}]
    if (workload['spec']['membership']['state'] != 'ACCEPTED'
            or workload['metadata']['wsdId'] != destination_wsd_id):
        _problem(problems, '$.spec.membership', 'Destination activation requires accepted WSD membership')
    return problems


def validate_workload_successor(previous: dict, current: dict, *,
                                verified_transition: VerifiedWsdTransition | None = None) -> list[dict]:
    """Preserve identity/history; accept a WSD move only with a verified decision.

    The caller must independently authenticate the decision and native evidence.
    An unverified pending/observed target remains attached to the accepted WSD.
    """
    problems = validate_record(previous) + validate_record(current)
    if problems:
        return problems
    if previous['kind'] != 'Workload' or current['kind'] != 'Workload':
        return [{'path': '$.kind', 'message': 'Both revisions must be Workload records'}]
    before, after = previous['metadata'], current['metadata']
    if (before['organizationId'], before['tenantId'], before['workloadId']) != (
            after['organizationId'], after['tenantId'], after['workloadId']):
        _problem(problems, '$.metadata', 'Workload and tenant identity cannot change')
    if after['revision'] != before['revision'] + 1:
        _problem(problems, '$.metadata.revision', 'Revision must advance exactly once')
    prior_membership = previous['spec']['membership']
    next_membership = current['spec']['membership']
    old_history = prior_membership['history']
    new_history = next_membership['history']
    if new_history[:len(old_history)] != old_history:
        _problem(problems, '$.spec.membership.history', 'Accepted transition history is append-only')
    if before['wsdId'] == after['wsdId']:
        if len(new_history) != len(old_history):
            _problem(problems, '$.spec.membership.history', 'A membership event requires an accepted WSD change')
        if next_membership['state'] == 'OBSERVED':
            prior = prior_membership['transition']
            current_transition = next_membership['transition']
            if (prior_membership['state'] != 'PENDING'
                    or prior_membership['candidateWsdId'] != next_membership['candidateWsdId']
                    or prior is None or current_transition is None
                    or (prior['planId'], prior['planRevision'], prior['planDigest']) != (
                        current_transition['planId'], current_transition['planRevision'], current_transition['planDigest'])):
                _problem(problems, '$.spec.membership', 'Observation must follow the same pending transition')
    else:
        event = new_history[-1] if len(new_history) == len(old_history) + 1 else None
        prior = prior_membership['transition']
        if (prior_membership['state'] != 'OBSERVED'
                or prior_membership['candidateWsdId'] != after['wsdId']
                or next_membership['state'] != 'ACCEPTED'
                or event is None or prior is None):
            _problem(problems, '$.spec.membership', 'WSD change requires an observed pending transition and history event')
        else:
            expected = (before['organizationId'], before['tenantId'], before['workloadId'],
                        before['wsdId'], after['wsdId'], prior['planId'], prior['planRevision'],
                        prior['planDigest'], prior['grantDigest'], prior['observationDigest'])
            recorded = (event['fromWsdId'], event['toWsdId'], event['planId'],
                        event['planRevision'], event['planDigest'], event['grantDigest'],
                        event['observationDigest'])
            if recorded != expected[3:]:
                _problem(problems, '$.spec.membership.history', 'Accepted history does not match observed transition')
            if verified_transition is None or (
                    verified_transition.organization_id, verified_transition.tenant_id,
                    verified_transition.workload_id, verified_transition.from_wsd_id,
                    verified_transition.to_wsd_id, verified_transition.plan_id,
                    verified_transition.plan_revision, verified_transition.plan_digest,
                    verified_transition.grant_digest, verified_transition.observation_digest) != expected:
                _problem(problems, '$.spec.membership', 'Independent transition authorization and observation required')
    new_machines = {m['machineId']: m for m in current['spec']['machines']}
    for index, old_machine in enumerate(previous['spec']['machines']):
        new_machine = new_machines.get(old_machine['machineId'])
        if new_machine is None:
            _problem(problems, f'$.spec.machines[{index}]', 'Existing machine identity cannot disappear')
            continue
        for collection, logical_id in (('bindings', None), ('disks', 'diskId'), ('nics', 'nicId')):
            old_resources = [old_machine] if logical_id is None else old_machine[collection]
            new_resources = [new_machine] if logical_id is None else new_machine[collection]
            resources_by_id = {r[logical_id]: r for r in new_resources} if logical_id else None
            for old_resource in old_resources:
                new_resource = new_machine if logical_id is None else resources_by_id.get(old_resource[logical_id])
                if new_resource is None:
                    _problem(problems, f'$.spec.machines[{index}].{collection}', 'Existing component identity cannot disappear')
                    continue
                old_bindings = {(tuple(_binding_key(h['binding'])), h['firstSeenSnapshotId']) for h in old_resource['bindings']}
                new_bindings = {(tuple(_binding_key(h['binding'])), h['firstSeenSnapshotId']) for h in new_resource['bindings']}
                if not old_bindings <= new_bindings:
                    _problem(problems, f'$.spec.machines[{index}].{collection}', 'Historical native binding cannot be rewritten or removed')
    return problems
