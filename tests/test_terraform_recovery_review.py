"""Held attempt bindings and immutable evidence; no replay or ledger release."""
from copy import deepcopy
from datetime import timedelta
import fcntl
import json
import os
from pathlib import Path
import tempfile
import unittest
from tests.test_native_readback import context
from tests.test_vsphere_task_tree import manifest, Client
from tools import readback_core as c, terraform_recovery_review as r, vsphere_task_tree_observe as tree
from tools.run_files import digest, encoded, write_new, load_private, utcnow
from tools.terraform_run import select_scope


class AttemptRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.base = Path(self.tmp.name)
        self.operation = self.base / 'operation'; self.operation.mkdir(mode=0o700)
        self.ledger = self.base / 'ledger'; self.ledger.mkdir(mode=0o700)
        self.m = manifest('https://vc.example.test')
        inputs = json.loads((r.ROOT / 'terraform/stacks/wsd/vmware/workloads/inputs.tfvars.json.example').read_text())
        inputs.update(allow_restricted_build=True, test_authorization_ref='FIXTURE', platform_endpoint='vc.example.test')
        _, scope, state_key = select_scope(r.ROOT, 'vmware-wsd-workloads', inputs)
        self.m.update(tenant_id=scope['tenant_key'], scope_id=scope['wsd_key'])
        backend = dict(state_key=state_key, address='https://state.example.test/fixture', lock_address='https://state.example.test/fixture/lock',
                       unlock_address='https://state.example.test/fixture/lock', lock_method='POST', unlock_method='DELETE')
        self.folder = self.ledger / digest(backend['address'].encode()); self.folder.mkdir(mode=0o700)
        write_new(self.folder / 'writer.lock', b'')
        identity = self.m['resources'][0]['expected']['config']['uuid']
        self.plan = dict(format_version='1.2', complete=True, resource_changes=[dict(
            address='module.owned.module.member["processor-01"].vsphere_virtual_machine.workload', type='vsphere_virtual_machine',
            mode='managed', provider_name='registry.terraform.io/hashicorp/vsphere',
            change=dict(actions=['update'], before={'id': identity}, after={'id': identity}, after_unknown={}))])
        values = {'inputs.json': encoded(inputs), 'backend.json': encoded(backend), 'plan.json': encoded(self.plan), 'saved.tfplan': b'FIXTURE-NOT-TERRAFORM'}
        self.bundle = dict(format='hosting-terraform-bundle/1', status='AWAITING_EXACT_PLAN_REVIEW', catalog_id='vmware-wsd-workloads',
                           scope=scope, state_key=state_key, operation_id=self.m['operation_id'], generation=4,
                           artifacts={key: digest(value) for key, value in values.items()})
        for name, raw in values.items(): write_new(self.operation / name, raw)
        write_new(self.operation / 'bundle.json', encoded(self.bundle))
        start = (c.timestamp(self.m['task']['records'][0]['queued_at']) - timedelta(seconds=1)).isoformat()
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

    def run_review(self, name='review.json'):
        return r.review_attempt(self.operation, self.ledger, self.base / 'manifest', self.base / 'readback', self.base / 'context', self.base / name)

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


if __name__ == '__main__': unittest.main()
