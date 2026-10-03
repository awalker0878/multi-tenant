"""Held attempt bindings and immutable evidence; no replay or ledger release."""
from copy import deepcopy
from datetime import timedelta
import fcntl
import json
import os
from pathlib import Path
import tempfile
import unittest
from tests.test_vsphere_task_activity import manifest, Client, context
from tests.test_vsphere_observe import ref
from tests import test_vsphere_port_observe as ports
from provisioner.execution import readback_core as c
from tools import terraform_recovery_review as r, vsphere_task_tree_observe as tree
from provisioner.execution.run_files import digest, encoded, write_new, load_private, utcnow
from provisioner.execution.terraform_run import select_scope


class AttemptRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.base = Path(self.tmp.name)
        self.operation = self.base / 'operation'; self.operation.mkdir(mode=0o700)
        self.ledger = self.base / 'ledger'; self.ledger.mkdir(mode=0o700)
        self.m = manifest('https://vc.example.test')
        inputs = json.loads((r.ROOT / 'terraform/stacks/wsd/vmware/workloads/inputs.tfvars.json.example').read_text())
        inputs.update(allow_restricted_build=True, test_authorization_ref='FIXTURE', platform_endpoint='vc.example.test')
        inputs['members']['processor-01']['resource_pool_id'] = 'resgroup-1'
        inputs['members']['processor-01']['datastore_id'] = 'datastore-1'
        inputs['members']['processor-01']['quarantine_network_id'] = 'dvportgroup-1'
        disk = self.m['resources'][0]['expected']['config']['hardware']['device'][1]
        disk.update(capacityInKB=41943040, capacityInBytes=42949672960)
        disk['backing'].update(thinProvisioned=True, eagerlyScrub=False, sharing='sharingNone', writeThrough=False)
        nic = self.m['resources'][0]['expected']['config']['hardware']['device'][2]
        nic.update(addressType='generated', backing=dict(_typeName='VirtualEthernetCardDistributedVirtualPortBackingInfo',
            port=dict(switchUuid='fixture-dvs-uuid', portgroupKey='fixture-pg-key', portKey='17', connectionCookie=12345)))
        self.m['resources'][0]['expected']['config']['name'] = 'processor-01'
        _, scope, state_key = select_scope(r.ROOT, 'vmware-wsd-workloads', inputs)
        self.m.update(tenant_id=scope['tenant_key'], scope_id=scope['wsd_key'])
        backend = dict(state_key=state_key, address='https://state.example.test/fixture', lock_address='https://state.example.test/fixture/lock',
                       unlock_address='https://state.example.test/fixture/lock', lock_method='POST', unlock_method='DELETE')
        self.folder = self.ledger / digest(backend['address'].encode()); self.folder.mkdir(mode=0o700)
        write_new(self.folder / 'writer.lock', b'')
        identity = self.m['resources'][0]['expected']['config']['uuid']
        after = dict(id=identity, name='processor-01', num_cpus=2, num_cores_per_socket=1, memory=4096, resource_pool_id='resgroup-1',
                     firmware='efi', network_interface=[dict(network_id='dvportgroup-1', key=4000,
                         mac_address='00:50:56:00:00:01', adapter_type='vmxnet3', use_static_mac=False)])
        after.update(datastore_id='datastore-1', scsi_type='pvscsi', scsi_controller_count=1,
            storage_policy_id=inputs['members']['processor-01']['storage_policy_id'], disk=[dict(label='disk0',
                key=2000, uuid='6000C290-fixture-disk', unit_number=0, controller_type='scsi', size=40,
                path='vm/vm.vmdk', datastore_id='datastore-1', disk_mode='persistent', thin_provisioned=True,
                eagerly_scrub=False, keep_on_remove=True, attach=False, disk_sharing='sharingNone', write_through=False,
                storage_policy_id=inputs['members']['processor-01']['storage_policy_id'])])
        self.plan = dict(format_version='1.2', complete=True, resource_changes=[dict(
            address='module.owned.module.member["processor-01"].vsphere_virtual_machine.workload', type='vsphere_virtual_machine',
            mode='managed', provider_name='registry.terraform.io/hashicorp/vsphere',
            change=dict(actions=['update'], before=deepcopy(after) | dict(num_cpus=1), after=after, after_unknown={}))])
        values = {'inputs.json': encoded(inputs), 'backend.json': encoded(backend), 'plan.json': encoded(self.plan), 'saved.tfplan': b'FIXTURE-NOT-TERRAFORM'}
        self.bundle = dict(format='hosting-terraform-bundle/1', status='AWAITING_EXACT_PLAN_REVIEW', catalog_id='vmware-wsd-workloads',
                           scope=scope, state_key=state_key, operation_id=self.m['operation_id'], generation=4,
                           artifacts={key: digest(value) for key, value in values.items()})
        for name, raw in values.items(): write_new(self.operation / name, raw)
        write_new(self.operation / 'bundle.json', encoded(self.bundle))
        start = self.m['task']['activity_since']
        self.started = dict(format='hosting-terraform-attempt/1', status='STARTED_OUTCOME_UNKNOWN', scope=scope,
            bundle_sha256=digest(encoded(self.bundle)), operation_id=self.m['operation_id'], generation=4,
            change_ref='FIXTURE-CHANGE', started_at=start)
        self.attempt_id = digest(encoded({'operation': self.m['operation_id'], 'generation': 4}))
        write_new(self.folder / (self.attempt_id + '.started.json'), encoded(self.started))
        self.head = self.started | dict(status='HOLD_RECONCILIATION_REQUIRED', stopped_at=utcnow().isoformat())
        write_new(self.folder / (self.attempt_id + '.result.json'), encoded(self.head)); write_new(self.folder / 'head.json', encoded(self.head))
        report = c.observe(self.m, Client(self.m), tree, interval=0); x = context(self.m, report)
        x.update(accepted_plan_sha256=digest(values['saved.tfplan']), attempted_at=start, change_record_ref='FIXTURE-CHANGE')
        for name, value in [('manifest', self.m), ('readback', report), ('context', x)]: write_new(self.base / name, encoded(value))
        self.network = ports.manifest(self.m['origin'])
        self.network.update({key: self.m[key] for key in ('operation_id', 'tenant_id', 'scope_id', 'engineering_record_ref', 'target_binding_ref')})
        self.network['resources'][0]['expected']['config']['key'] = 'fixture-pg-key'
        port = self.network['resources'][0]['ports'][0]; port['portgroupKey'] = 'fixture-pg-key'
        port['state']['runtimeInfo']['macAddress'] = nic['macAddress']
        self.network_report = c.observe(self.network, ports.Client(self.network), ports.p, interval=0)
        write_new(self.base / 'network', encoded(self.network)); write_new(self.base / 'network-report', encoded(self.network_report))

    def run_review(self, name='review.json'):
        return r.review_attempt(self.operation, self.ledger, self.base / 'manifest', self.base / 'readback', self.base / 'context', self.base / name,
                               network_manifest=self.base / 'network', network_readback=self.base / 'network-report')

    def test_review_binds_held_attempt_and_preserves_all_ledger_bytes(self):
        before = {p.name: p.read_bytes() for p in self.folder.iterdir()}
        report = self.run_review()
        self.assertEqual(report['triage']['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        self.assertFalse(report['ledger_released']); self.assertFalse(report['may_apply'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.folder.iterdir()})
        self.assertEqual((self.base / 'review.json').stat().st_mode & 0o777, 0o600)
        with self.assertRaises(FileExistsError): self.run_review()
    def test_changed_plan_context_or_superseded_ledger_is_rejected(self):
        for name, mutate in [('plan.json', lambda x: x.update(complete=False)),
                            ('context', lambda x: x.update(accepted_plan_sha256='a' * 64)),
                            ('context', lambda x: x.update(attempted_generation=5)),
                            ('head.json', lambda x: x.update(operation_id='foreign'))]:
            path = self.operation / name if name == 'plan.json' else self.folder / name if name == 'head.json' else self.base / name
            original = path.read_bytes(); changed = json.loads(original); mutate(changed); path.write_bytes(encoded(changed))
            with self.subTest(name=name), self.assertRaises(ValueError): self.run_review()
            path.write_bytes(original)
    def test_concurrent_executor_lock_blocks_review_and_output_in_ledger_is_refused(self):
        fd = os.open(self.folder / 'writer.lock', os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.run_review()
        finally: os.close(fd)
        with self.assertRaises(ValueError): self.run_review(self.folder / 'review.json')
    def test_ambiguous_created_replaced_or_foreign_vm_cannot_be_bound(self):
        inputs = load_private(self.operation / 'inputs.json')
        for mutate in (lambda x: x['resource_changes'][0]['change'].update(actions=['create'], before=None),
                       lambda x: x['resource_changes'][0]['change'].update(actions=['delete', 'create']),
                       lambda x: x['resource_changes'][0]['change']['after'].update(id='foreign'),
                       lambda x: x['resource_changes'][0]['change']['after_unknown'].update(id=True),
                       lambda x: x['resource_changes'].clear()):
            plan = deepcopy(self.plan); mutate(plan)
            with self.assertRaises(ValueError): r.bind_plan(plan, inputs, self.m)
    def test_unfenced_attempt_is_recorded_as_hold_and_never_released(self):
        path = self.base / 'context'; x = load_private(path); x['writer_fence']['state'] = 'UNVERIFIED'; path.write_bytes(encoded(x))
        report = self.run_review()
        self.assertEqual(report['triage']['result'], 'HOLD_WRITER_NOT_FENCED')
        self.assertEqual(load_private(self.folder / 'head.json'), self.head)
    def test_known_task_only_profile_cannot_downgrade_receipt_review(self):
        m = deepcopy(self.m); m['profile'] = tree.PROFILE; del m['task']['activity_since']
        tree.validate(m)
        (self.base / 'manifest').write_bytes(encoded(m))
        with self.assertRaisesRegex(ValueError, 'activity coverage required'): self.run_review()
        self.assertFalse((self.base / 'review.json').exists())
    def test_activity_window_must_bind_to_immutable_attempt_start(self):
        for delta in (-1, 0.5):
            m = deepcopy(self.m)
            m['task']['activity_since'] = (c.timestamp(self.started['started_at']) + timedelta(seconds=delta)).isoformat()
            tree.validate(m); (self.base / 'manifest').write_bytes(encoded(m))
            with self.assertRaisesRegex(ValueError, 'Activity window differs'): self.run_review()
        self.assertFalse((self.base / 'review.json').exists())
    def test_clone_activity_cannot_enter_existing_vm_review_or_release_ledger(self):
        from tests.test_vsphere_clone_activity import manifest as clone_manifest
        m = clone_manifest(self.m['origin'])
        m.update({k: self.m[k] for k in ('operation_id', 'tenant_id', 'scope_id')})
        tree.validate(m); (self.base / 'manifest').write_bytes(encoded(m))
        before = {p.name: p.read_bytes() for p in self.folder.iterdir()}
        with self.assertRaisesRegex(ValueError, 'clone adoption remains separate'): self.run_review()
        self.assertFalse((self.base / 'review.json').exists())
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.folder.iterdir()})
    def test_unrecorded_vm_activity_keeps_attempt_held(self):
        before = {p.name: p.read_bytes() for p in self.folder.iterdir()}
        client = Client(self.m); other = deepcopy(client.activity_rows['vm-1']['completed'][0])
        old = (c.timestamp(self.started['started_at']) - timedelta(hours=1)).isoformat()
        other.update(key='task-99', task=ref('Task', 'task-99'), queueTime=old, startTime=old)
        client.activity_rows['vm-1']['completed'].append(other)
        report = c.observe(self.m, client, tree, interval=0)
        x = context(self.m, report)
        x.update(accepted_plan_sha256=self.bundle['artifacts']['saved.tfplan'], change_record_ref=self.started['change_ref'])
        (self.base / 'readback').write_bytes(encoded(report)); (self.base / 'context').write_bytes(encoded(x))
        result = self.run_review()
        self.assertEqual(result['triage']['result'], 'RECONCILE_DIVERGENCE')
        self.assertFalse(result['ledger_released']); self.assertFalse(result['may_apply'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.folder.iterdir()})
    def test_matching_uuid_cannot_hide_different_planned_configuration(self):
        inputs = load_private(self.operation / 'inputs.json')
        for field, value in [('name', 'another-vm'), ('num_cpus', 8), ('num_cores_per_socket', 2), ('memory', 8192),
                             ('resource_pool_id', 'resgroup-2'), ('num_cpus', True)]:
            m = deepcopy(self.m); plan = deepcopy(self.plan)
            plan['resource_changes'][0]['change']['after'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): r.bind_plan(plan, inputs, m)
        m = deepcopy(self.m); m['resources'][0]['expected']['config']['hardware']['numCPU'] = 8
        with self.assertRaises(ValueError): r.bind_plan(self.plan, inputs, m)
    def test_unobserved_changes_unknowns_and_adoption_do_not_get_review_packet(self):
        inputs = load_private(self.operation / 'inputs.json')
        for mutate in (lambda p: p['resource_changes'][0]['change']['after'].update(firmware='bios'),
            lambda p: p['resource_changes'][0]['change']['after']['network_interface'][0].update(network_id='foreign'),
            lambda p: p['resource_changes'][0]['change']['after_unknown'].update(memory=True),
            lambda p: p['resource_changes'][0]['change']['after_unknown'].update(memory=1),
            lambda p: p['resource_changes'][0]['change']['after_unknown'].update(network_interface=[{'network_id': True}]),
            lambda p: p['resource_changes'][0]['change'].update(actions=['no-op']),
            lambda p: p['resource_changes'][0].update(previous_address='another-address'),
            lambda p: p['resource_changes'][0]['change'].update(importing={'id': 'foreign'}),
            lambda p: p.update(resource_drift=[{'type': 'vsphere_virtual_machine'}])):
            plan = deepcopy(self.plan); mutate(plan)
            with self.assertRaises(ValueError): r.bind_plan(plan, inputs, self.m)
    def test_known_native_metadata_must_match_and_computed_revision_may_be_unknown(self):
        inputs = load_private(self.operation / 'inputs.json')
        for key, value in [('moid', 'vm-2'), ('uuid', 'foreign'), ('change_version', 'foreign'), ('power_state', 'off')]:
            plan = deepcopy(self.plan); change = plan['resource_changes'][0]['change']
            change['before'][key] = value; change['after'][key] = value
            with self.assertRaises(ValueError): r.bind_plan(plan, inputs, self.m)
        plan = deepcopy(self.plan); change = plan['resource_changes'][0]['change']
        change['before']['change_version'] = 'old'; change['after_unknown']['change_version'] = True
        self.assertEqual(len(r.bind_plan(plan, inputs, self.m)), 1)


if __name__ == '__main__': unittest.main()
