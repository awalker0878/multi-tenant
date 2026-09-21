"""Saved device identities cannot be replaced by a matching VM UUID."""
from copy import deepcopy
import unittest
from tests import test_terraform_recovery_review as attempts
from tools import terraform_recovery_review as r
from tools.run_files import load_private


class DiskBindingTests(unittest.TestCase):
    setUp = attempts.AttemptRecoveryTests.setUp

    def bind(self, plan=None, manifest=None, inputs=None):
        return r.bind_plan(plan or self.plan, inputs or load_private(self.operation / 'inputs.json'), manifest or self.m)

    def test_existing_boot_disk_matches_and_size_units_are_exact(self):
        self.assertEqual(len(self.bind()), 1)
        for field, value in [('capacityInBytes', 42949672961), ('capacityInKB', 41943039)]:
            m = deepcopy(self.m); m['resources'][0]['expected']['config']['hardware']['device'][1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.bind(manifest=m)

    def test_unchanged_foreign_disk_in_both_plan_states_is_rejected(self):
        for field, value in [('uuid', 'another-disk'), ('key', 2001), ('unit_number', 1), ('size', 41),
                ('path', 'other/vm.vmdk'), ('datastore_id', 'datastore-2'), ('disk_mode', 'independent_persistent'),
                ('thin_provisioned', False), ('eagerly_scrub', True), ('keep_on_remove', False), ('attach', True),
                ('storage_policy_id', 'foreign-policy'), ('controller_type', 'sata'), ('key', True),
                ('device_address', 'scsi:1:0'), ('write_through', True), ('disk_sharing', 'sharingMultiWriter')]:
            plan = deepcopy(self.plan)
            for phase in ('before', 'after'): plan['resource_changes'][0]['change'][phase]['disk'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.bind(plan)

    def test_missing_or_extra_plan_disks_and_native_inventory_are_rejected(self):
        for value in (None, [], {}, [self.plan['resource_changes'][0]['change']['after']['disk'][0]] * 2):
            plan = deepcopy(self.plan)
            for phase in ('before', 'after'): plan['resource_changes'][0]['change'][phase]['disk'] = value
            with self.assertRaises(ValueError): self.bind(plan)
        for field in ('uuid', 'key', 'path', 'size', 'controller_type', 'keep_on_remove'):
            plan = deepcopy(self.plan)
            for phase in ('before', 'after'): del plan['resource_changes'][0]['change'][phase]['disk'][0][field]
            with self.subTest(field=field), self.assertRaises(ValueError): self.bind(plan)
        m = deepcopy(self.m); m['resources'][0]['expected']['config']['hardware']['device'].pop(1)
        with self.assertRaises(ValueError): self.bind(manifest=m)

    def test_native_disk_flags_backing_and_controller_must_be_explicit(self):
        changes = [lambda ds: ds[0].update(busNumber=1), lambda ds: ds[0].update(busNumber=False),
            lambda ds: ds[0].update(_typeName='VirtualAHCIController'),
            lambda ds: ds.append(deepcopy(ds[0]) | dict(key=1001, busNumber=1)),
            lambda ds: ds[1].update(controllerKey=999), lambda ds: ds[1].update(unitNumber=1),
            lambda ds: ds[1]['backing'].pop('thinProvisioned'), lambda ds: ds[1]['backing'].pop('eagerlyScrub'),
            lambda ds: ds[1]['backing'].pop('sharing'),
            lambda ds: ds[1]['backing'].update(sharing='sharingMultiWriter'),
            lambda ds: ds[1]['backing'].update(parent={'uuid': 'snapshot'}),
            lambda ds: ds[1]['backing'].update(fileName='[fixture-ds] ../escape.vmdk')]
        for change in changes:
            m = deepcopy(self.m); change(m['resources'][0]['expected']['config']['hardware']['device'])
            with self.assertRaises(ValueError): self.bind(manifest=m)

    def test_sealed_member_storage_intent_cannot_be_substituted(self):
        for field, value in [('boot_disk_gib', 41), ('boot_disk_gib', True), ('data_disk_gib', 1),
                ('data_disk_gib', False), ('datastore_id', 'datastore-2'), ('storage_policy_id', 'other'),
                ('scsi_type', 'lsilogic'), ('vcpu', True), ('memory_gib', True)]:
            inputs = load_private(self.operation / 'inputs.json'); inputs['members']['processor-01'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.bind(inputs=inputs)

    def test_optional_data_disk_is_bound_by_label_identity_and_slot(self):
        plan = deepcopy(self.plan); m = deepcopy(self.m); inputs = load_private(self.operation / 'inputs.json')
        inputs['members']['processor-01']['data_disk_gib'] = 20
        disks = m['resources'][0]['expected']['config']['hardware']['device']
        data = deepcopy(disks[1]); data.update(key=2001, unitNumber=1, capacityInKB=20971520, capacityInBytes=21474836480)
        data['backing'].update(uuid='6000C290-fixture-data', fileName='[fixture-ds] vm/data.vmdk'); disks.append(data)
        for phase in ('before', 'after'):
            rows = plan['resource_changes'][0]['change'][phase]['disk']; row = deepcopy(rows[0])
            row.update(label='data0', key=2001, unit_number=1, size=20, path='vm/data.vmdk', uuid='6000C290-fixture-data')
            rows.insert(0, row)  # Provider list order is not the disk's identity.
        self.assertEqual(len(self.bind(plan, m, inputs)), 1)
        data['backing']['uuid'] = disks[1]['backing']['uuid']
        with self.assertRaises(ValueError): self.bind(plan, m, inputs)

    def test_unknown_device_configuration_never_gets_a_binding(self):
        for mask in (True, [{'uuid': True}], [{'size': True}], [{'uuid': 1}]):
            plan = deepcopy(self.plan); plan['resource_changes'][0]['change']['after_unknown']['disk'] = mask
            with self.assertRaises(ValueError): self.bind(plan)


if __name__ == '__main__': unittest.main()
