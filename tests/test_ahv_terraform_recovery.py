"""AHV saved-plan/held-attempt binding with native readback over fixture TLS."""
from copy import deepcopy
from datetime import timedelta
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from lab.native_readback_fixture import Fixture
from lab.run_readback_lab import operator_context
from tests import test_nutanix_vm_activity as activity_fixture
from tests.test_lifecycle_transition import fixture as lifecycle_fixture
from provisioner.execution import nutanix_terraform_recovery as ahv
from provisioner.execution import terraform_recovery_review as review
from provisioner.execution import readback_core as c
from provisioner.execution import lifecycle_transition as lifecycle
from provisioner.execution import nutanix_vm_activity_observe as activity
from provisioner.execution.run_files import digest, encoded, write_new, load_private
from provisioner.execution.terraform_run import select_scope


def scenario(origin, stage='bootstrap', *, expired=False):
    transition, _ = lifecycle_fixture('nutanix', stage)
    inputs = transition['requested_inputs']; inputs['platform_endpoint'] = origin
    transition['prior_inputs']['platform_endpoint'] = origin
    member = inputs['members']['processor-01']; m = activity_fixture.manifest(origin)
    m.update(tenant_id=inputs['tenant_key'], scope_id=inputs['wsd_key'])
    e = m['resources'][0]['expected']; identity = transition['prior_outputs']['members']['value']['processor-01']['vm_id']
    m['resources'][0]['ext_id'] = e['extId'] = identity; e['name'] = 'processor-01'
    m['task']['entity_ids'] = [identity]; m['task']['descendants'][0]['entity_ids'] = [identity]
    e.update(numSockets=1, numCoresPerSocket=member['vcpu'], powerState='ON' if stage == 'bootstrap' else 'OFF')
    for field, key in [('cluster', 'cluster_id'), ('project', 'project_id')]: e[field]['extId'] = member[key]
    e['categories'][0]['extId'] = member['security_category_id']
    nic = e['nics'][0]; nic['nicBackingInfo']['isConnected'] = stage == 'bootstrap'
    nic['nicNetworkInfo']['subnet']['extId'] = member['subnet_id']
    disk = e['disks'][0]; disk['backingInfo'].update(diskSizeBytes=40*1073741824, storageContainer={'extId': member['storage_container_id']})
    after = dict(id=identity, ext_id=identity, name='processor-01', num_sockets=1, num_cores_per_socket=2,
        memory_size_bytes=4*1073741824, power_state=e['powerState'], host=[{'ext_id': e['host']['extId']}],
        cluster=[{'ext_id': member['cluster_id']}], project=[{'ext_id': member['project_id']}],
        categories=[{'ext_id': member['security_category_id']}],
        nics=[dict(ext_id=nic['extId'], nic_backing_info=[{'virtual_ethernet_nic': [dict(
            model='VIRTIO', mac_address='02:00:00:00:00:01', is_connected=stage == 'bootstrap')]}],
            nic_network_info=[{'virtual_ethernet_nic_network_info': [dict(nic_type='NORMAL_NIC',
                subnet=[{'ext_id': member['subnet_id']}], ipv4_config=[dict(should_assign_ip=True,
                ip_address=[dict(value='192.0.2.10', prefix_length=24)])])]}])],
        disks=[dict(ext_id=disk['extId'], disk_address=[dict(bus_type='SCSI', index=0)],
            backing_info=[{'vm_disk': [dict(disk_ext_id=disk['backingInfo']['diskExtId'], disk_size_bytes=40*1073741824,
                storage_container=[{'ext_id': member['storage_container_id']}])]}])])
    after['disks'][0]['backing_info'][0]['vm_disk'][0]['data_source'] = [
        {'reference': [{'image_reference': [{'image_ext_id': member['image_id']}]}]}]
    before = deepcopy(after); before['power_state'] = 'OFF' if stage == 'bootstrap' else 'ON'
    before['nics'][0]['nic_backing_info'][0]['virtual_ethernet_nic'][0]['is_connected'] = stage != 'bootstrap'
    plan = dict(format_version='1.2', complete=True, resource_changes=[dict(address=next(iter(transition['resources'])),
        type='nutanix_virtual_machine_v2', mode='managed', provider_name='registry.terraform.io/nutanix/nutanix',
        change=dict(actions=['update'], before=before, after=after, after_unknown={}))])
    start = c.timestamp(m['task']['created_after'])
    transition.update(input_sha256=digest(encoded(inputs)), valid_from=(start-timedelta(seconds=1)).isoformat(),
                      valid_until=(start+timedelta(seconds=30 if expired else 600)).isoformat())
    transition['resources'] = lifecycle.bindings(transition)
    return transition, plan, m


class HeldAhvTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.f = Fixture()
    @classmethod
    def tearDownClass(cls): cls.f.close()
    def setUp(self): self.setup_case()
    def setup_case(self, stage='bootstrap', *, expired=False):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.base = Path(tmp.name)
        self.operation = self.base/'operation'; self.operation.mkdir(mode=0o700)
        self.ledger = self.base/'ledger'; self.ledger.mkdir(mode=0o700)
        self.transition, self.plan, self.m = scenario(self.f.origin, stage, expired=expired)
        self.inputs = self.transition['requested_inputs']; self.start = self.m['task']['created_after']
        _, scope, state_key = select_scope(review.ROOT, 'nutanix-wsd-workloads', self.inputs)
        backend = dict(state_key=state_key, address='https://state.example.test/ahv',
            lock_address='https://state.example.test/ahv/lock', unlock_address='https://state.example.test/ahv/lock',
            lock_method='POST', unlock_method='DELETE')
        self.folder = self.ledger/digest(backend['address'].encode()); self.folder.mkdir(mode=0o700)
        write_new(self.folder/'writer.lock', b'')
        values = {'inputs.json': encoded(self.inputs), 'backend.json': encoded(backend), 'plan.json': encoded(self.plan),
                  'saved.tfplan': b'FIXTURE-NOT-TERRAFORM', 'transition.json': encoded(self.transition)}
        bundle = dict(format='hosting-terraform-bundle/1', status='AWAITING_EXACT_PLAN_REVIEW', catalog_id='nutanix-wsd-workloads',
            scope=scope, state_key=state_key, operation_id=self.m['operation_id'], generation=4,
            artifacts={k: digest(v) for k, v in values.items()})
        for name, data in values.items(): write_new(self.operation/name, data)
        write_new(self.operation/'bundle.json', encoded(bundle))
        started = dict(format='hosting-terraform-attempt/1', status='STARTED_OUTCOME_UNKNOWN', scope=scope,
            bundle_sha256=digest(encoded(bundle)), operation_id=self.m['operation_id'], generation=4,
            change_ref='FIXTURE-CHANGE', started_at=self.start)
        ident = digest(encoded({'operation': self.m['operation_id'], 'generation': 4}))
        write_new(self.folder/(ident+'.started.json'), encoded(started))
        head = started | dict(status='HOLD_RECONCILIATION_REQUIRED', stopped_at=c.now())
        write_new(self.folder/(ident+'.result.json'), encoded(head)); write_new(self.folder/'head.json', encoded(head))
        self.f.routes = activity_fixture.fixtures.responses(self.m)
        self.f.routes.update(activity_fixture.activity_routes(self.m, self.f.routes)); self.f.requests = []; self.f.counts = {}; self.f.hook = None
        client = c.ReadClient(self.f.origin, self.f.origin, 'fixture', 'fixture', activity.targets(self.m), str(self.f.directory/'ca.pem'))
        report = c.observe(self.m, client, activity, interval=0); context = operator_context(self.m, report)
        context.update(accepted_plan_sha256=digest(values['saved.tfplan']), attempted_at=self.start, change_record_ref='FIXTURE-CHANGE')
        for name, value in [('manifest', self.m), ('readback', report), ('context', context)]: write_new(self.base/name, encoded(value))
    def run_review(self, output=None):
        return review.review_attempt(self.operation, self.ledger, self.base/'manifest', self.base/'readback', self.base/'context', output or self.base/'review')
    def bind(self, plan=None, m=None, inputs=None, transition=None):
        return ahv.bind_plan(plan or self.plan, inputs or self.inputs, m or self.m, transition or self.transition, attempted_at=self.start)

    def test_bootstrap_and_withdrawal_review_preserve_every_ledger_byte(self):
        for stage in ('bootstrap', 'prepared'):
            self.setup_case(stage); before = {p.name: p.read_bytes() for p in self.folder.iterdir()}
            result = self.run_review()
            self.assertEqual(result['triage']['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
            self.assertEqual(result['lifecycle_sha256'], digest(encoded(self.transition)))
            self.assertEqual(set(result['plan_configuration_fields']), ahv.OBSERVED_PLAN_FIELDS)
            self.assertTrue(all(result[k] is False for k in ('ledger_released', 'may_apply', 'may_delete', 'may_activate')))
            self.assertEqual(before, {p.name: p.read_bytes() for p in self.folder.iterdir()})
            self.assertEqual((self.base/'review').stat().st_mode & 0o777, 0o600)

    def test_expired_transition_is_only_reviewed_at_immutable_attempt_time(self):
        self.setup_case(expired=True)
        with self.assertRaises(ValueError): lifecycle.validate(self.transition)
        with self.assertRaises(ValueError): lifecycle.plan_bindings(self.plan, self.transition)
        self.assertEqual(self.run_review()['triage']['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        bad = deepcopy(self.transition); bad['valid_from'] = (c.timestamp(self.start)+timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError): self.bind(transition=bad)

    def test_foreign_or_missing_planned_native_identity_and_retained_disks_hold(self):
        for mutate in (lambda x: x.update(ext_id='foreign'), lambda x: x.update(name='foreign'),
                       lambda x: x.update(num_sockets=2), lambda x: x.update(memory_size_bytes=True),
                       lambda x: x['host'][0].update(ext_id=activity_fixture.uid(80)),
                       lambda x: x['nics'][0].update(ext_id=activity_fixture.uid(80)),
                       lambda x: x['nics'][0]['nic_backing_info'][0]['virtual_ethernet_nic'][0].update(mac_address='02:00:00:00:00:02'),
                       lambda x: x['disks'][0]['backing_info'][0]['vm_disk'][0].update(disk_ext_id=activity_fixture.uid(80)),
                       lambda x: x['disks'].clear(), lambda x: x.pop('ext_id')):
            plan = deepcopy(self.plan)
            # An unchanged but foreign baseline must not satisfy planned readback binding.
            mutate(plan['resource_changes'][0]['change']['before']); mutate(plan['resource_changes'][0]['change']['after'])
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): self.bind(plan=plan)

    def test_unresolved_unrelated_replaced_or_adopted_changes_hold(self):
        for mutate in (lambda p: p['resource_changes'][0]['change'].update(actions=['create'], before=None),
                       lambda p: p['resource_changes'][0]['change'].update(actions=['delete', 'create']),
                       lambda p: p['resource_changes'][0]['change'].update(actions=['no-op']),
                       lambda p: p['resource_changes'][0]['change']['after_unknown'].update(nics=True),
                       lambda p: p['resource_changes'][0]['change']['after_unknown'].update(nics=1),
                       lambda p: p['resource_changes'][0]['change']['after'].update(arbitrary_setting=True),
                       lambda p: p['resource_changes'][0]['change'].update(importing={'id': 'foreign'}),
                       lambda p: p['resource_changes'][0].update(provider_name='registry.terraform.io/foreign/nutanix'),
                       lambda p: p.update(resource_drift=[{}]), lambda p: p['resource_changes'].clear()):
            plan = deepcopy(self.plan); mutate(plan)
            with self.assertRaises(ValueError): self.bind(plan=plan)

    def test_old_profile_shifted_window_and_wrong_scope_cannot_enter_review(self):
        for mutate in (lambda m: m.update(profile=activity_fixture.fixtures.ahv.PROFILE),
                       lambda m: m['task'].update(created_after=(c.timestamp(self.start)+timedelta(seconds=1)).isoformat()),
                       lambda m: m.update(tenant_id='foreign'), lambda m: m.update(origin='https://foreign.example.test')):
            m = deepcopy(self.m); mutate(m); (self.base/'manifest').write_bytes(encoded(m))
            with self.assertRaises(ValueError): self.run_review()
        self.assertFalse((self.base/'review').exists())

    def test_modified_or_missing_sealed_lifecycle_record_holds(self):
        original = (self.operation/'transition.json').read_bytes()
        (self.operation/'transition.json').write_bytes(b'{}')
        with self.assertRaises(ValueError): self.run_review()
        (self.operation/'transition.json').write_bytes(original); (self.operation/'transition.json').unlink()
        with self.assertRaises(OSError): self.run_review()
        self.assertFalse((self.base/'review').exists())

    def test_unfenced_attempt_retains_hold(self):
        context = load_private(self.base/'context'); context['writer_fence']['state'] = 'UNKNOWN'
        (self.base/'context').write_bytes(encoded(context))
        result = self.run_review(); self.assertEqual(result['triage']['result'], 'HOLD_WRITER_NOT_FENCED')
        self.assertEqual(result['ledger_status'], 'HOLD_RECONCILIATION_REQUIRED')

    def test_unrecorded_late_work_cannot_release_matching_held_attempt(self):
        extra = deepcopy(self.f.routes[activity_fixture.tree.target(activity_fixture.fixtures.CHILD)]['body']['data'])
        extra.update(extId='unrecorded-root', status='RUNNING', completedTime=None,
                     createdTime=(c.timestamp(self.start)-timedelta(days=1)).isoformat())
        self.f.routes.update(activity_fixture.activity_routes(self.m, self.f.routes, [extra]))
        client = c.ReadClient(self.f.origin, self.f.origin, 'fixture', 'fixture', activity.targets(self.m), str(self.f.directory/'ca.pem'))
        report = c.observe(self.m, client, activity, interval=0)
        context = load_private(self.base/'context'); context['report_sha256'] = report['content_sha256']
        (self.base/'context').write_bytes(encoded(context)); (self.base/'readback').write_bytes(encoded(report))
        before = {p.name: p.read_bytes() for p in self.folder.iterdir()}
        self.assertEqual(self.run_review()['triage']['result'], 'RECONCILE_DIVERGENCE')
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.folder.iterdir()})

    def test_concurrent_executor_and_output_overwrite_are_refused(self):
        fd = os.open(self.folder/'writer.lock', os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.run_review()
        finally: os.close(fd)
        with self.assertRaises(ValueError): self.run_review(self.folder/'review')
        self.run_review()
        with self.assertRaises(FileExistsError): self.run_review()

    def test_cli_reviews_without_contact_or_ledger_release(self):
        before = len(self.f.requests)
        args = [sys.executable, str(Path(review.__file__))]
        for key, value in dict(bundle=self.operation, ledger=self.ledger, manifest=self.base/'manifest',
                               readback=self.base/'readback', context=self.base/'context', output=self.base/'cli-review').items():
            args += ['--'+key, str(value)]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(len(self.f.requests), before)
        self.assertFalse(load_private(self.base/'cli-review')['ledger_released'])


if __name__ == '__main__': unittest.main()
