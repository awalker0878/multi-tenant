"""Reviewed descriptors refuse route widening and changed protected bytes."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from provisioner.controlplane.jobs.repository import _digest
from provisioner.controlplane.workflow.execution_selection import (FileExecutionSelectionStore,
    validate_selection)
from provisioner.domain.enterprise_records import plan_digest, validate_record
from provisioner.execution.run_files import encoded, write_new
from tests.provisioning.schema.test_enterprise_records import SOURCE, TARGET, plan


def artifact():
    target = {**TARGET, 'platformFamily': 'openstack', 'endpointId': 'cloud-01',
              'nativeScopeId': 'project-01'}
    return {'format': 'hosting-openstack-execution-artifact/1', 'driver': 'openstack-linux-rebuild/1',
        'sourceCommit': 'a'*40, 'workloadId': 'workload-01', 'workloadRevision': 1,
        'source': dict(SOURCE), 'destination': target,
        'executionScope': {'environment_key': 'environment-01', 'site_key': target['locationId'],
            'platform': target['platformFamily'], 'tenant_key': target['tenantId'],
            'wsd_key': target['securityDomainId']},
        'resourceBundleDigest': 'b'*64, 'datasetSelectionDigest': 'c'*64,
        'cutoverSelectionDigest': 'd'*64, 'deliveryPlanDigest': 'e'*64,
        'qualificationDigest': 'f'*64, 'operationsAcceptanceDigest': '1'*64,
        'sourceTuple': {}, 'destinationTuple': {}, 'guestProfile': 'linux-ubuntu-2404',
        'stageBindings': {'prepare': {'kind': 'guest_plan', 'parametersDigest': '2'*64,
                                     'inputDigests': {'inputs': '3'*64}}}}


class ExecutionSelectionTests(unittest.TestCase):
    def test_ipam_namespace_and_scope_are_reviewed_without_runtime_authority(self):
        selected = artifact()
        allocation = {'format': 'hosting-netbox-allocation/1', 'origin': 'https://ipam.example.test',
            'scope': selected['executionScope'], 'member': 'vm-01', 'tenant_id': 3,
            'vrf_id': 5, 'prefix_id': 7, 'prefix': '192.0.2.0/24', 'address': '192.0.2.10/24'}
        selected['ipamSelections'] = [allocation]
        self.assertEqual(validate_selection(selected), selected)
        for changed in (allocation | {'scope': allocation['scope'] | {'tenant_key': 'other-tenant'}},
                allocation | {'address': '192.0.2.0/24'}, allocation | {'prefix_id': True},
                allocation | {'reservation_ref': 'capacity:old-job'},
                allocation | {'origin': 'http://ipam.example.test'}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                validate_selection(selected | {'ipamSelections': [changed]})

    def test_changed_resource_data_or_operating_inputs_need_new_digest_and_review(self):
        selected = artifact()
        original = _digest(selected)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            path = root / (original + '.json')
            write_new(path, encoded(selected))
            store = FileExecutionSelectionStore(root)
            self.assertEqual(store.load_verified(original), selected)
            for key in ('resourceBundleDigest', 'datasetSelectionDigest', 'operationsAcceptanceDigest'):
                changed = {**selected, key: '4'*64}
                path.write_bytes(encoded(changed))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    store.load_verified(original)

    def test_reverse_direction_generic_linux_windows_and_unapproved_secret_fields_are_rejected(self):
        cases = []
        selected = artifact(); selected['source'], selected['destination'] = selected['destination'], selected['source']; cases.append(selected)
        for profile in ('LINUX', 'WINDOWS', 'linux-debian-12'):
            selected = artifact(); selected['guestProfile'] = profile; cases.append(selected)
        selected = artifact(); selected['stageBindings']['prepare']['inputDigests']['credentials'] = '4'*64; cases.append(selected)
        selected = artifact(); selected['stageBindings']['prepare']['inputDigests']['secrets'] = '4'*64; cases.append(selected)
        selected = artifact(); selected['credentialFile'] = '/private/token'; cases.append(selected)
        selected = artifact(); selected['executionScope']['tenant_key'] = 'other-tenant'; cases.append(selected)
        selected = artifact(); selected['ipamSelections'] = [{'operation_id': 'runtime-job'}]; cases.append(selected)
        for selected in cases:
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                validate_selection(selected)

    def test_database_sync_requires_separate_descriptor_and_whole_application_lifecycle(self):
        selected = artifact() | {'applicationDatabaseSelectionDigest': '4'*64}
        with self.assertRaises(ValueError):
            validate_selection(selected)
        selected['applicationLifecycleSelectionDigest'] = '5'*64
        with self.assertRaises(ValueError):
            validate_selection(selected)
        selected['driver'] = 'openstack-linux-application-database/1'
        self.assertEqual(validate_selection(selected), selected)
        with self.assertRaises(ValueError):
            validate_selection({key: value for key, value in selected.items()
                                if key != 'applicationDatabaseSelectionDigest'})
        for field in ('applicationLifecycleSelectionDigest', 'applicationRecoverySelectionDigest',
                      'applicationDatabaseSelectionDigest'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_selection(selected | {field: '/private/unchecked'})

    def test_database_plan_requires_its_explicit_method_and_new_reviewed_digest(self):
        selected = plan(target=artifact()['destination'])
        selected['spec']['execution'] = {'format': 'hosting-execution-selection/1',
            'driver': 'openstack-linux-application-database/1', 'artifactDigest': 'a' * 64}
        selected['spec']['route']['method'] = 'REBUILD_RESTORE'
        selected['metadata']['planDigest'] = plan_digest(selected)
        self.assertTrue(any(problem['path'] == '$.spec.execution'
                            for problem in validate_record(selected)))
        selected['spec']['route']['method'] = 'APPLICATION_NATIVE'
        selected['metadata']['planDigest'] = plan_digest(selected)
        self.assertEqual(validate_record(selected), [])

    def test_plan_digest_binds_driver_and_artifact_without_reinterpreting_old_plan(self):
        target = artifact()['destination']
        selected = plan(target=target)
        selected['spec']['route']['method'] = 'REBUILD_RESTORE'
        selected['metadata']['planDigest'] = plan_digest(selected)
        self.assertEqual(validate_record(selected), [])
        old_digest = selected['metadata']['planDigest']
        selected['spec']['execution'] = {'format': 'hosting-execution-selection/1',
            'driver': 'openstack-linux-rebuild/1', 'artifactDigest': _digest(artifact())}
        self.assertTrue(validate_record(selected))
        selected['metadata']['planDigest'] = plan_digest(selected)
        self.assertNotEqual(old_digest, selected['metadata']['planDigest'])
        self.assertEqual(validate_record(selected), [])
        changed = deepcopy(selected)
        changed['spec']['source'], changed['spec']['destination'] = changed['spec']['destination'], changed['spec']['source']
        changed['metadata']['planDigest'] = plan_digest(changed)
        self.assertTrue(any(problem['path'] == '$.spec.execution' for problem in validate_record(changed)))
