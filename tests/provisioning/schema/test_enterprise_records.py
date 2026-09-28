"""Canonical product records bind observed identity and migration provenance."""
from __future__ import annotations

import unittest
from copy import deepcopy
from dataclasses import replace

from provisioner.domain.enterprise_records import (BindingPromotion, VerifiedBindingCutover,
                                                   VerifiedWsdTransition, plan_digest,
                                                   validate_destination_activation,
                                                   validate_record, validate_workload_successor)
from provisioner.schemas import registry


DIGEST = 'a' * 64
SOURCE = {'organizationId': 'org-01', 'tenantId': 'tenant-01', 'securityDomainId': 'wsd-01',
          'endpointId': 'vcenter-01', 'nativeScopeId': 'dc1',
          'locationId': 'cluster-east', 'platformFamily': 'vmware'}
TARGET = {'organizationId': 'org-01', 'tenantId': 'tenant-01', 'securityDomainId': 'wsd-02',
          'endpointId': 'vcenter-02', 'nativeScopeId': 'dc2',
          'locationId': 'cluster-west', 'platformFamily': 'vmware'}


def binding(kind: str, native_id: str) -> dict:
    return {'endpointId': SOURCE['endpointId'], 'nativeScopeId': SOURCE['nativeScopeId'],
            'nativeId': native_id, 'resourceKind': kind, 'platformFamily': 'vmware'}


def history(kind: str, native_id: str) -> dict:
    return {'binding': binding(kind, native_id), 'role': 'SOURCE',
            'firstSeenSnapshotId': 'snapshot-01', 'lastObservedSnapshotId': 'snapshot-01'}


def machine(number: int) -> dict:
    return {
        'machineId': f'machine-{number}', 'displayName': f'app-{number}',
        'bindings': [history('vm', f'vm-{number}')],
        'guestProfile': {'state': 'KNOWN', 'value': 'linux-ubuntu-2404'},
        'cpuCount': {'state': 'KNOWN', 'value': 4},
        'memoryMiB': {'state': 'KNOWN', 'value': 8192},
        'firmware': {'state': 'KNOWN', 'value': 'uefi'},
        'disks': [
            {'diskId': f'disk-{number}-{slot}', 'bindings': [history('disk', f'vmdk-{number}-{slot}')],
             'slot': slot, 'sizeBytes': {'state': 'KNOWN', 'value': 1000000},
             'format': {'state': 'KNOWN', 'value': 'vmdk'}, 'unknownFields': []}
            for slot in (0, 1)
        ], 'disksComplete': True,
        'nics': [
            {'nicId': f'nic-{number}-{slot}', 'bindings': [history('nic', f'vnic-{number}-{slot}')],
             'slot': slot, 'network': {'state': 'KNOWN', 'value': 'tenant-net'},
             'address': {'state': 'UNKNOWN', 'reason': 'guest discovery unavailable'},
             'unknownFields': ['address']}
            for slot in (0, 1)
        ], 'nicsComplete': True, 'unknownFields': []
    }


def workload() -> dict:
    return {
        'apiVersion': 'hosting.platform/v1', 'kind': 'Workload',
        'metadata': {'organizationId': 'org-01', 'tenantId': 'tenant-01',
                     'workloadId': 'workload-01', 'wsdId': 'wsd-01', 'revision': 1,
                     'ownerId': 'owner-01', 'criticality': 'moderate'},
        'spec': {'state': 'DISCOVERED', 'name': 'two-vm-application',
                 'membership': {'state': 'ACCEPTED', 'candidateWsdId': None,
                                'transition': None, 'history': []},
                 'machines': [machine(1), machine(2)],
                 'datasets': [
                     {'datasetId': f'dataset-{number}', 'kind': 'volume',
                      'machineId': f'machine-{number}',
                      'sourceBindings': [binding('volume', f'volume-{number}')],
                      'consistencyGroupId': 'group-01',
                      'sizeBytes': {'state': 'UNKNOWN', 'reason': 'volume metric unavailable'},
                      'unknownFields': ['sizeBytes']}
                     for number in (1, 2)
                 ], 'unknownFields': []}
    }


def stage_target_bindings(item: dict) -> None:
    for vm in item['spec']['machines']:
        for resource in (vm, *vm['disks'], *vm['nics']):
            original = resource['bindings'][0]['binding']
            target_binding = deepcopy(original)
            target_binding['endpointId'] = TARGET['endpointId']
            target_binding['nativeScopeId'] = TARGET['nativeScopeId']
            target_binding['nativeId'] = 'target-' + original['nativeId']
            resource['bindings'].append(
                {'binding': target_binding, 'role': 'TARGET',
                 'firstSeenSnapshotId': 'snapshot-02',
                 'lastObservedSnapshotId': 'snapshot-02'})


def promote_target_bindings(item: dict) -> None:
    for vm in item['spec']['machines']:
        for resource in (vm, *vm['disks'], *vm['nics']):
            resource['bindings'][0]['role'] = 'RETIRED'
            resource['bindings'][1]['role'] = 'SOURCE'


def native_key(binding_record: dict) -> tuple[str, str, str, str, str]:
    return (binding_record['endpointId'], binding_record['nativeScopeId'],
            binding_record['resourceKind'], binding_record['nativeId'],
            binding_record['platformFamily'])


def binding_cutover(item: dict, selected_plan: dict) -> VerifiedBindingCutover:
    promotions = []
    for vm in item['spec']['machines']:
        for kind, resources in (('vm', [vm]), ('disk', vm['disks']), ('nic', vm['nics'])):
            for resource in resources:
                component_id = (vm['machineId'] if kind == 'vm' else
                                resource['diskId'] if kind == 'disk' else resource['nicId'])
                promotions.append(BindingPromotion(
                    kind, vm['machineId'], component_id,
                    native_key(resource['bindings'][0]['binding']),
                    native_key(resource['bindings'][1]['binding'])))
    meta, spec = selected_plan['metadata'], selected_plan['spec']
    return VerifiedBindingCutover(
        organization_id='org-01', tenant_id='tenant-01',
        workload_id='workload-01', wsd_id='wsd-01',
        plan_id=meta['planId'], plan_revision=meta['revision'],
        plan_digest=meta['planDigest'], source_snapshot_id=spec['sourceSnapshotId'],
        destination_snapshot_id=spec['destinationSnapshotId'],
        grant_digest=DIGEST, observation_digest='b' * 64,
        promotions=tuple(promotions))


def plan(source: dict = SOURCE, target: dict = TARGET) -> dict:
    source = deepcopy(source)
    target = deepcopy(target)
    record = {
        'apiVersion': 'hosting.platform/v1', 'kind': 'MigrationPlan',
        'metadata': {'organizationId': 'org-01', 'tenantId': 'tenant-01',
                     'planId': 'plan-01', 'revision': 1, 'planDigest': DIGEST,
                     'frozenAt': '2026-09-26T14:00:00Z'},
        'spec': {
            'workloadId': 'workload-01', 'workloadRevision': 1, 'applicationGroupId': 'app-01',
            'sourceSnapshotId': 'snapshot-01', 'destinationSnapshotId': 'snapshot-02',
            'source': source, 'destination': target,
            'route': {'routeId': 'route-01', 'method': 'SAME_PLATFORM_RELOCATION',
                      'qualificationDigest': DIGEST, 'guestProfile': 'linux-ubuntu-2404',
                      'driverVersion': '1.0'},
            'selectedMachineIds': ['machine-1', 'machine-2'],
            'selectedDatasetIds': ['dataset-1', 'dataset-2'],
            'machineMappings': [
                {'machineId': f'machine-{number}', 'sourceBinding': binding('vm', f'vm-{number}'),
                 'targetMachineId': f'target-machine-{number}', 'targetPlacementRef': 'pool-02',
                 'diskMappings': [{'diskId': f'disk-{number}-{slot}',
                                   'targetVolumeRef': f'target-volume-{number}-{slot}'}
                                  for slot in (0, 1)],
                 'nicMappings': [{'nicId': f'nic-{number}-{slot}',
                                  'targetNetworkRef': f'target-network-{slot}',
                                  'addressMode': 'READDRESS'} for slot in (0, 1)]}
                for number in (1, 2)
            ],
            'datasetMappings': [{'datasetId': f'dataset-{number}',
                                 'targetRef': f'target-dataset-{number}',
                                 'consistencyGroupId': 'group-01'} for number in (1, 2)],
            'policyDigest': DIGEST, 'acceptanceTestIds': ['app-health'],
            'maxDowntimeSeconds': 3600, 'maxDataLossSeconds': 0,
            'rollbackWindowSeconds': 86400,
        }
    }
    record['metadata']['planDigest'] = plan_digest(record)
    return record


def transfer(selected_plan: dict) -> dict:
    return {
        'apiVersion': 'hosting.platform/v1', 'kind': 'TransferManifest',
        'metadata': {'organizationId': 'org-01', 'tenantId': 'tenant-01',
                     'transferId': 'transfer-01', 'planId': 'plan-01', 'planRevision': 1,
                     'planDigest': selected_plan['metadata']['planDigest']},
        'spec': {
            'sourceScope': deepcopy(selected_plan['spec']['source']),
            'destinationScope': deepcopy(selected_plan['spec']['destination']),
            'sourceWorkloadId': 'workload-01', 'targetWorkloadId': 'workload-01',
            'datasetId': 'dataset-1', 'consistencyGroupId': 'group-01',
            'sourceSnapshotId': 'snapshot-01',
            'sourceReceipt': {'sourceScope': deepcopy(selected_plan['spec']['source']),
                              'datasetId': 'dataset-1', 'snapshotId': 'snapshot-01',
                              'receiptDigest': DIGEST},
            'sourceNativeBinding': binding('volume', 'volume-1'),
            'targetRef': 'target-dataset-1', 'sourceFormat': 'raw', 'targetFormat': 'raw',
            'expectedBytes': {'state': 'UNKNOWN', 'reason': 'native metric unavailable'},
            'encryptionKeyRef': 'key-ref-01', 'transportId': 'transport-01',
            'grant': {'grantId': 'grant-01', 'grantDigest': DIGEST,
                      'sourceScope': deepcopy(selected_plan['spec']['source']),
                      'destinationScope': deepcopy(selected_plan['spec']['destination'])},
        }
    }


class EnterpriseRecordTest(unittest.TestCase):
    def assert_invalid(self, record: dict, path: str, **related: dict) -> None:
        problems = validate_record(record, **related)
        self.assertTrue(any(p['path'].startswith(path) for p in problems), problems)

    def test_multi_machine_inventory_and_same_family_move(self):
        source_workload = workload()
        selected_plan = plan()
        self.assertEqual(validate_record(source_workload), [])
        self.assertEqual(validate_record(selected_plan, workload=source_workload), [])
        self.assertEqual(validate_record(transfer(selected_plan), plan=selected_plan), [])
        self.assertNotEqual(selected_plan['spec']['source'], selected_plan['spec']['destination'])
        self.assertEqual(selected_plan['spec']['source']['platformFamily'],
                         selected_plan['spec']['destination']['platformFamily'])

    def test_directed_cross_platform_move_is_structurally_representable(self):
        destination = deepcopy(TARGET)
        destination['platformFamily'] = 'openstack'
        destination['endpointId'] = 'openstack-01'
        selected_plan = plan(target=destination)
        selected_plan['spec']['route']['method'] = 'COLD_VM_CONVERSION'
        selected_plan['metadata']['planDigest'] = plan_digest(selected_plan)
        self.assertEqual(validate_record(selected_plan, workload=workload()), [])
        self.assertEqual(validate_record(transfer(selected_plan), plan=selected_plan), [])
        selected_plan['spec']['route']['method'] = 'SAME_PLATFORM_RELOCATION'
        selected_plan['metadata']['planDigest'] = plan_digest(selected_plan)
        self.assert_invalid(selected_plan, '$.spec.route.method')

    def test_bad_native_identity_and_unknown_fields_are_refused(self):
        item = workload()
        item['spec']['machines'][1]['bindings'][0]['binding'] = deepcopy(
            item['spec']['machines'][0]['bindings'][0]['binding'])
        self.assert_invalid(item, '$.spec.machines')
        item = workload()
        item['spec']['machines'][0]['providerSecret'] = 'not-an-allowed-field'
        self.assert_invalid(item, '$')
        item = workload()
        item['spec']['machines'][0]['cpuCount'] = {'state': 'UNKNOWN', 'value': 4}
        self.assert_invalid(item, '$')

    def test_colons_in_logical_ids_cannot_hide_shared_native_binding(self):
        item = workload()
        first, second = item['spec']['machines']
        first['machineId'], first['disks'][0]['diskId'] = 'a:b', 'c'
        second['machineId'], second['disks'][0]['diskId'] = 'a', 'b:c'
        item['spec']['datasets'][0]['machineId'] = 'a:b'
        item['spec']['datasets'][1]['machineId'] = 'a'
        second['disks'][0]['bindings'][0]['binding'] = deepcopy(
            first['disks'][0]['bindings'][0]['binding'])
        problems = validate_record(item)
        self.assertTrue(any('bound to two logical resources' in p['message']
                            for p in problems), problems)

    def test_migration_source_binding_must_be_active_in_selected_snapshot(self):
        item = workload()
        selected_plan = plan()
        item['spec']['machines'][0]['bindings'][0]['role'] = 'RETIRED'
        self.assert_invalid(selected_plan, '$.spec.machineMappings[0].sourceBinding',
                            workload=item)
        item['spec']['machines'][0]['bindings'][0]['role'] = 'SOURCE'
        item['spec']['machines'][0]['bindings'][0]['lastObservedSnapshotId'] = 'stale-snapshot'
        self.assert_invalid(selected_plan, '$.spec.machineMappings[0].sourceBinding',
                            workload=item)

    def test_each_logical_resource_has_at_most_one_source_binding(self):
        for collection, kind, native_id in (('bindings', 'vm', 'new-vm'),
                                            ('disks', 'disk', 'new-disk'),
                                            ('nics', 'nic', 'new-nic')):
            item = workload()
            machine_record = item['spec']['machines'][0]
            resource = (machine_record if collection == 'bindings' else
                        machine_record[collection][0])
            resource['bindings'].append(history(kind, native_id))
            problems = validate_record(item)
            self.assertTrue(any('more than one current SOURCE binding' in p['message']
                                for p in problems), (collection, problems))

    def test_retired_binding_cannot_be_reactivated(self):
        earlier = workload()
        earlier['spec']['machines'][0]['bindings'][0]['role'] = 'RETIRED'
        later = deepcopy(earlier)
        later['metadata']['revision'] = 2
        later['spec']['machines'][0]['bindings'][0]['role'] = 'SOURCE'
        problems = validate_workload_successor(earlier, later)
        self.assertTrue(any('role transition is not allowed' in p['message']
                            for p in problems), problems)

    def test_new_source_cannot_skip_target_staging_for_existing_resource(self):
        earlier = workload()
        later = deepcopy(earlier)
        later['metadata']['revision'] = 2
        vm = later['spec']['machines'][0]
        vm['bindings'][0]['role'] = 'RETIRED'
        staged = deepcopy(vm['bindings'][0])
        staged['binding']['endpointId'] = TARGET['endpointId']
        staged['binding']['nativeScopeId'] = TARGET['nativeScopeId']
        staged['binding']['nativeId'] = 'new-vm-direct-source'
        staged['firstSeenSnapshotId'] = 'snapshot-02'
        staged['lastObservedSnapshotId'] = 'snapshot-02'
        staged['role'] = 'SOURCE'
        vm['bindings'].append(staged)
        self.assertEqual(validate_record(later), [])
        problems = validate_workload_successor(earlier, later)
        self.assertTrue(any('must first be staged as TARGET' in p['message']
                            for p in problems), problems)

    def test_same_wsd_target_promotion_requires_future_verified_cutover(self):
        earlier = workload()
        stage_target_bindings(earlier)
        later = deepcopy(earlier)
        later['metadata']['revision'] = 2
        promote_target_bindings(later)
        problems = validate_workload_successor(earlier, later)
        self.assertTrue(any('Target promotion requires' in p['message']
                            for p in problems), problems)
        same_wsd_target = deepcopy(TARGET)
        same_wsd_target['securityDomainId'] = 'wsd-01'
        selected_plan = plan(target=same_wsd_target)
        decision = binding_cutover(earlier, selected_plan)
        self.assertEqual(validate_workload_successor(
            earlier, later, plan=selected_plan, verified_cutover=decision), [])
        stale_decision = replace(decision, destination_snapshot_id='stale-snapshot')
        self.assertTrue(validate_workload_successor(
            earlier, later, plan=selected_plan, verified_cutover=stale_decision))
        stale_plan = deepcopy(selected_plan)
        stale_plan['spec']['workloadRevision'] = 2
        stale_plan['metadata']['planDigest'] = plan_digest(stale_plan)
        self.assertTrue(validate_workload_successor(
            earlier, later, plan=stale_plan,
            verified_cutover=replace(decision, plan_digest=stale_plan['metadata']['planDigest'])))
        retired_source = deepcopy(earlier)
        for vm in retired_source['spec']['machines']:
            for resource in (vm, *vm['disks'], *vm['nics']):
                resource['bindings'][0]['role'] = 'RETIRED'
        retired_target = deepcopy(retired_source)
        retired_target['metadata']['revision'] = 2
        for vm in retired_target['spec']['machines']:
            for resource in (vm, *vm['disks'], *vm['nics']):
                resource['bindings'][1]['role'] = 'SOURCE'
        self.assertTrue(validate_workload_successor(
            retired_source, retired_target, plan=selected_plan,
            verified_cutover=decision))
        pending = deepcopy(earlier)
        pending['spec']['membership'] = {
            'state': 'PENDING', 'candidateWsdId': 'wsd-02',
            'transition': {'planId': selected_plan['metadata']['planId'],
                           'planRevision': selected_plan['metadata']['revision'],
                           'planDigest': selected_plan['metadata']['planDigest'],
                           'grantDigest': None, 'observationDigest': None},
            'history': []}
        premature = deepcopy(pending)
        premature['metadata']['revision'] = 2
        promote_target_bindings(premature)
        self.assertTrue(validate_workload_successor(
            pending, premature, plan=selected_plan, verified_cutover=decision))

    def test_missing_disk_and_nic_mappings_are_refused(self):
        item = plan()
        item['spec']['machineMappings'][0]['diskMappings'].pop()
        item['metadata']['planDigest'] = plan_digest(item)
        self.assert_invalid(item, '$.spec.machineMappings[0].diskMappings', workload=workload())
        item = plan()
        item['spec']['machineMappings'][1]['nicMappings'].pop()
        item['metadata']['planDigest'] = plan_digest(item)
        self.assert_invalid(item, '$.spec.machineMappings[1].nicMappings', workload=workload())
        item = plan()
        item['spec']['machineMappings'][1]['diskMappings'][0]['targetVolumeRef'] = (
            item['spec']['machineMappings'][0]['diskMappings'][0]['targetVolumeRef'])
        item['metadata']['planDigest'] = plan_digest(item)
        self.assert_invalid(item, '$.spec.machineMappings', workload=workload())

    def test_incomplete_inventory_is_not_migration_ready(self):
        item = workload()
        item['spec']['machines'][0]['disksComplete'] = False
        item['spec']['machines'][0]['unknownFields'] = ['disks']
        self.assertEqual(validate_record(item), [])
        self.assert_invalid(plan(), '$.spec.machineMappings[0]', workload=item)

    def test_unknown_inventory_values_require_explicit_unknown_fields(self):
        item = workload()
        item['spec']['machines'][0]['cpuCount'] = {'state': 'UNKNOWN', 'reason': 'read denied'}
        self.assert_invalid(item, '$.spec.machines[0].unknownFields')
        item['spec']['machines'][0]['unknownFields'].append('cpuCount')
        self.assertEqual(validate_record(item), [])
        item['spec']['machines'][0]['cpuCount'] = {'state': 'KNOWN', 'value': 4}
        self.assert_invalid(item, '$.spec.machines[0].unknownFields')

    def test_cross_scope_transfer_retains_source_receipt_and_dual_grant(self):
        selected_plan = plan()
        item = transfer(selected_plan)
        item['spec']['sourceReceipt']['sourceScope'] = deepcopy(TARGET)
        self.assert_invalid(item, '$.spec.sourceReceipt', plan=selected_plan)
        item = transfer(selected_plan)
        item['spec']['grant']['destinationScope'] = deepcopy(SOURCE)
        self.assert_invalid(item, '$.spec.grant', plan=selected_plan)
        item = transfer(selected_plan)
        item['spec']['grant']['destinationScope']['securityDomainId'] = 'wsd-03'
        self.assert_invalid(item, '$.spec.grant', plan=selected_plan)
        item = transfer(selected_plan)
        item['spec']['destinationScope']['tenantId'] = 'other-tenant'
        self.assert_invalid(item, '$.spec.destinationScope', plan=selected_plan)
        item = transfer(selected_plan)
        item['spec']['datasetId'] = 'dataset-2'
        self.assert_invalid(item, '$.spec.sourceReceipt', plan=selected_plan)
        item = transfer(selected_plan)
        item['spec']['destinationScope'] = deepcopy(SOURCE)
        item['spec']['grant']['destinationScope'] = deepcopy(SOURCE)
        self.assertEqual(validate_record(item), [])  # same-scope restore uses the same contract
        self.assert_invalid(item, '$.spec.sourceScope', plan=selected_plan)

    def test_plan_digest_binds_revision_and_exact_mappings(self):
        item = plan()
        item['spec']['maxDataLossSeconds'] = 30
        self.assert_invalid(item, '$.metadata.planDigest')
        item = plan()
        item['spec']['selectedMachineIds'].pop()
        item['metadata']['planDigest'] = plan_digest(item)
        self.assert_invalid(item, '$.spec.machineMappings')
        item = plan()
        item['spec']['destination']['tenantId'] = 'other-tenant'
        item['metadata']['planDigest'] = plan_digest(item)
        self.assert_invalid(item, '$.spec.destination', workload=workload())
        item = plan()
        item['spec']['source']['securityDomainId'] = 'wrong-wsd'
        item['metadata']['planDigest'] = plan_digest(item)
        self.assert_invalid(item, '$.spec.source.securityDomainId', workload=workload())
        item = plan()
        item['spec']['machineMappings'][0]['sourceBinding']['platformFamily'] = 'nutanix'
        item['metadata']['planDigest'] = plan_digest(item)
        problems = validate_record(item)
        self.assertTrue(any('does not match source scope' in p['message']
                            for p in problems), problems)

    def test_observation_tracks_unknowns_and_freshness(self):
        item = {
            'apiVersion': 'hosting.platform/v1', 'kind': 'ObservationSnapshot',
            'metadata': {'organizationId': 'org-01', 'tenantId': 'tenant-01',
                         'snapshotId': 'snapshot-01', 'capturedAt': '2026-09-26T14:00:00Z',
                         'expiresAt': '2026-09-26T15:00:00Z'},
            'spec': {'endpointId': 'vcenter-01', 'readScopes': ['dc1'],
                     'completeness': 'PARTIAL', 'privileges': ['vm.read'],
                     'objects': [{'binding': binding('vm', 'vm-1'), 'presence': 'PRESENT',
                                  'revisionToken': {'state': 'UNKNOWN', 'reason': 'API omitted token'},
                                  'facts': [{'field': 'cpuCount', 'state': 'OBSERVED', 'value': 4},
                                            {'field': 'firmware', 'state': 'UNKNOWN', 'reason': 'permission denied'}],
                                  'missingFields': ['firmware']}],
                     'collectionErrors': ['firmware privilege denied'], 'missingFields': ['firmware']}
        }
        self.assertEqual(validate_record(item), [])
        item['spec']['objects'][0]['missingFields'] = []
        self.assert_invalid(item, '$.spec.objects[0].missingFields')
        item['spec']['objects'][0]['missingFields'] = ['firmware']
        item['metadata']['expiresAt'] = '2026-09-26T13:00:00Z'
        self.assert_invalid(item, '$.metadata.expiresAt')

    def test_application_membership_and_order(self):
        item = {
            'apiVersion': 'hosting.platform/v1', 'kind': 'ApplicationGroup',
            'metadata': {'organizationId': 'org-01', 'tenantId': 'tenant-01',
                         'applicationGroupId': 'app-01', 'revision': 1, 'ownerId': 'owner-01'},
            'spec': {'name': 'app', 'workloadIds': ['workload-01', 'workload-02'],
                     'datasetIds': ['dataset-1'], 'dependencies': [],
                     'startupOrder': ['workload-01', 'workload-02'],
                     'consistencyGroups': [{'groupId': 'group-01', 'datasetIds': ['dataset-1']}],
                     'acceptanceTestIds': ['app-health'], 'unknownFields': []}
        }
        self.assertEqual(validate_record(item), [])
        item['spec']['startupOrder'] = ['workload-01']
        self.assert_invalid(item, '$.spec.startupOrder')

    def test_activity_result_requires_evidence_or_reconciliation(self):
        selected_plan = plan()
        item = {
            'apiVersion': 'hosting.platform/v1', 'kind': 'ActivityResult',
            'metadata': {'organizationId': 'org-01', 'tenantId': 'tenant-01',
                         'activityId': 'activity-01', 'operationId': 'operation-01',
                         'attempt': 1, 'planId': 'plan-01', 'planRevision': 1,
                         'planDigest': selected_plan['metadata']['planDigest'],
                         'observedAt': '2026-09-26T14:00:00Z'},
            'spec': {'status': 'OUTCOME_UNKNOWN', 'effects': 'UNKNOWN', 'nativeTaskId': None,
                     'evidenceDigests': [], 'failureCode': None, 'continuationRef': None,
                     'retry': 'RECONCILE'}
        }
        self.assertEqual(validate_record(item, plan=selected_plan), [])
        item['spec']['retry'] = 'SAFE'
        self.assert_invalid(item, '$.spec.retry', plan=selected_plan)
        item['spec'].update({'status': 'COMPLETED', 'effects': 'KNOWN', 'retry': 'NEVER'})
        self.assert_invalid(item, '$.spec.status', plan=selected_plan)
        item['spec']['evidenceDigests'] = [DIGEST]
        self.assertEqual(validate_record(item, plan=selected_plan), [])

    def test_native_binding_history_is_immutable_across_revisions(self):
        earlier = workload()
        later = deepcopy(earlier)
        later['metadata']['revision'] = 2
        later['spec']['machines'][0]['bindings'][0]['role'] = 'RETIRED'
        later['spec']['machines'][0]['bindings'].append(
            {'binding': {'endpointId': 'vcenter-02', 'nativeScopeId': 'dc2',
                         'nativeId': 'vm-target-1', 'resourceKind': 'vm',
                         'platformFamily': 'vmware'},
             'role': 'TARGET', 'firstSeenSnapshotId': 'snapshot-02',
             'lastObservedSnapshotId': 'snapshot-02'})
        self.assertEqual(validate_workload_successor(earlier, later), [])
        later['spec']['machines'][0]['bindings'][0]['binding']['nativeId'] = 'rewritten'
        self.assertTrue(validate_workload_successor(earlier, later))

    def test_wsd_membership_moves_only_after_observation_and_external_grant(self):
        earlier = workload()
        pending = deepcopy(earlier)
        pending['metadata']['revision'] = 2
        selected_plan = plan()
        transition = {'planId': 'plan-01', 'planRevision': 1,
                      'planDigest': selected_plan['metadata']['planDigest'],
                      'grantDigest': None, 'observationDigest': None}
        pending['spec']['membership'] = {'state': 'PENDING', 'candidateWsdId': 'wsd-02',
                                         'transition': transition, 'history': []}
        self.assertEqual(validate_workload_successor(earlier, pending), [])
        self.assertTrue(validate_destination_activation(pending, 'wsd-02'))
        observed = deepcopy(pending)
        observed['metadata']['revision'] = 3
        observed['spec']['membership']['state'] = 'OBSERVED'
        observed['spec']['membership']['transition']['grantDigest'] = DIGEST
        observed['spec']['membership']['transition']['observationDigest'] = 'b' * 64
        stage_target_bindings(observed)
        self.assertEqual(validate_workload_successor(pending, observed), [])
        self.assertTrue(validate_destination_activation(observed, 'wsd-02'))
        premature = deepcopy(observed)
        premature['metadata']['revision'] = 4
        promote_target_bindings(premature)
        problems = validate_workload_successor(observed, premature)
        self.assertTrue(any('Target promotion requires' in p['message']
                            for p in problems), problems)
        accepted = deepcopy(observed)
        accepted['metadata']['revision'] = 4
        accepted['metadata']['wsdId'] = 'wsd-02'
        promote_target_bindings(accepted)
        accepted['spec']['membership'] = {
            'state': 'ACCEPTED', 'candidateWsdId': None, 'transition': None,
            'history': [{'fromWsdId': 'wsd-01', 'toWsdId': 'wsd-02',
                         'planId': 'plan-01', 'planRevision': 1,
                         'planDigest': selected_plan['metadata']['planDigest'],
                         'grantDigest': DIGEST, 'observationDigest': 'b' * 64,
                         'acceptedAt': '2026-09-26T15:00:00Z'}]}
        problems = validate_workload_successor(observed, accepted)
        self.assertTrue(any('Target promotion requires' in p['message']
                            for p in problems), problems)
        verified = VerifiedWsdTransition(
            organization_id='org-01', tenant_id='tenant-01', workload_id='workload-01',
            from_wsd_id='wsd-01', to_wsd_id='wsd-02', plan_id='plan-01',
            plan_revision=1, plan_digest=selected_plan['metadata']['planDigest'],
            grant_digest=DIGEST, observation_digest='b' * 64)
        observed_cutover = binding_cutover(observed, selected_plan)
        self.assertTrue(validate_workload_successor(observed, accepted,
                                                    verified_transition=verified))
        untouched = deepcopy(accepted)
        untouched['spec']['machines'] = deepcopy(observed['spec']['machines'])
        problems = validate_workload_successor(
            observed, untouched, verified_transition=verified,
            verified_cutover=observed_cutover, plan=selected_plan)
        self.assertTrue(any('requires a native binding cutover' in p['message']
                            for p in problems), problems)
        partial = deepcopy(accepted)
        partial['spec']['machines'][1] = deepcopy(observed['spec']['machines'][1])
        partial_cutover = replace(
            observed_cutover,
            promotions=tuple(p for p in observed_cutover.promotions if p.machine_id == 'machine-1'))
        problems = validate_workload_successor(
            observed, partial, verified_transition=verified,
            verified_cutover=partial_cutover, plan=selected_plan)
        self.assertTrue(any('promotion of every workload VM' in p['message']
                            for p in problems), problems)
        self.assertEqual(validate_workload_successor(
            observed, accepted, verified_transition=verified,
            verified_cutover=observed_cutover, plan=selected_plan), [])
        self.assertEqual(validate_destination_activation(accepted, 'wsd-02'), [])
        self.assertTrue(validate_destination_activation(accepted, 'wsd-01'))
        accepted['spec']['membership']['history'][0]['grantDigest'] = 'c' * 64
        self.assertTrue(validate_workload_successor(
            observed, accepted, verified_transition=verified,
            verified_cutover=observed_cutover, plan=selected_plan))

    def test_registered_schema_rejects_a_second_public_request_kind(self):
        self.assertEqual(registry.validate_named(workload(), 'enterprise-record'), [])
        item = workload()
        item['kind'] = 'WorkloadSecurityDomain'
        self.assertTrue(registry.validate_named(item, 'enterprise-record'))


if __name__ == '__main__':
    unittest.main()
