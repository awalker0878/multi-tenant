"""Cross-scope file copies keep source proof and require live dual-scope authority."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from provisioner.controlplane.authority import (
    ApprovalSnapshot, AuthorityDenied, AuthorityService, FrozenPlan, PlanScope,
    RoleGrant, VerifiedPrincipal, WorkerGrant)
from provisioner.controlplane.authority.service import (
    SOURCE_OWNER, DESTINATION_OWNER, SOURCE_SECURITY, DESTINATION_SECURITY,
    WORKER, LeaseState)
from provisioner.domain.enterprise_records import plan_digest
from provisioning.schema.test_enterprise_records import (
    plan as selected_plan, transfer as selected_transfer, TARGET)
from tools import restic_run
from tools.restic_transfer import (
    FORMAT, TransferGuard, execute_authorized_transfer, grant_digest, validate)
from tools.run_files import digest, encoded, load_private, utcnow
from test_restic_run import fixture


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'export'; self.source.mkdir(mode=0o700)
        (self.source / 'payload').write_bytes(b'original useful workload bytes')
        self.config = fixture(); self.config['source'] = str(self.source)
        self.config['machine_id'] = 'a' * 32
        self.target = self.root / 'restored'
        self.calls = []; self.captured = {}
        outer = self
        class Engine:
            deadline = 10**20
            def repository(self): outer.calls.append('repository')
            def command(self, argv):
                outer.calls.append(argv[0])
                if argv[0] == 'backup':
                    for path in [outer.source / 'payload', Path(argv[-1])]:
                        outer.captured[str(path)] = path.read_bytes()
                    outer.native = {'id': 'd' * 64, 'hostname': argv[4],
                                    'tags': [argv[6], argv[8]], 'paths': [argv[-2], argv[-1]]}
                    return json.dumps({'message_type': 'summary', 'snapshot_id': 'd' * 64})
                if argv[0] == 'snapshots':
                    if outer.revoke_before_restore:
                        outer.ledger.epoch += 1
                    return json.dumps([outer.native])
                if argv[0] == 'restore':
                    for source, raw in outer.captured.items():
                        destination = Path(argv[3]) / source.lstrip('/')
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(raw)
                    return '{}'
                raise AssertionError(argv)
        self.engine = Engine()
        captured = self.root / 'captured'; captured.mkdir(mode=0o700)
        self.receipt, self.manifest = restic_run.backup(self.config, self.engine, captured)
        self.calls.clear(); self.revoke_before_restore = False
        target = deepcopy(TARGET); target['platformFamily'] = 'openstack'
        target['endpointId'] = 'openstack-01'
        self.plan = selected_plan(target=target)
        self.plan['spec']['route']['method'] = 'REBUILD_RESTORE'
        self.plan['metadata']['planDigest'] = plan_digest(self.plan)
        self.transfer = selected_transfer(self.plan)
        self.transfer['spec']['sourceReceipt']['receiptDigest'] = digest(encoded(self.receipt))
        self.transfer['spec']['expectedBytes'] = {'state': 'KNOWN', 'value': 30}
        self.transfer['spec']['expectedBytes']['value'] = len(b'original useful workload bytes')
        self.envelope = {
            'format': FORMAT, 'migration_plan': self.plan, 'transfer': self.transfer,
            'source_execution_scope': deepcopy(self.config['scope']),
            'destination_execution_scope': self.config['scope'] | {
                'platform': 'openstack', 'site_key': 'site-b', 'wsd_key': 'science-target'},
            'source_config_sha256': digest(encoded(self.config)),
            'repository_id': self.config['repository_id'], 'snapshot_id': self.receipt['snapshot_id'],
            'file_manifest_sha256': digest(encoded(self.manifest)),
            'target_member': 'target-guest', 'target': str(self.target)}
        self.configure_authority()
        self.restore_authority = {
            'valid_from': (utcnow() - timedelta(minutes=1)).isoformat(),
            'valid_until': (utcnow() + timedelta(minutes=10)).isoformat(),
            'config_sha256': digest(encoded(self.config)),
            'receipt_sha256': digest(encoded(self.receipt)), 'machine_id': 'f' * 32,
            'target': str(self.target), 'isolation_ref': 'TEST-ISOLATION', 'change_ref': 'TEST-RESTORE'}

    def configure_authority(self):
        self.now = utcnow()
        now = self.now
        self.frozen = FrozenPlan.from_record(self.plan, author_subject='author')
        source, target = self.frozen.source, self.frozen.destination
        outer = self
        class Provider:
            identities = {}
            def authenticate(self, credential): return self.identities[credential]
        class Plans:
            def current(self, organization_id, tenant_id, plan_id): return outer.frozen
        class Ledger:
            epoch = 0
            def __init__(self): self.approvals = []; self.grants = {}
            def snapshot(self, plan):
                return ApprovalSnapshot(plan.organization_id, plan.tenant_id, plan.plan_id,
                                        plan.revision, plan.digest, self.epoch, tuple(self.approvals))
            def append_if_current(self, plan, approval, expected_epoch): self.approvals.append(approval)
            def worker_grant(self, grant_id): return self.grants[grant_id]
        class Leases:
            lease = LeaseState('binding:dataset-1', 7, 'worker', now + timedelta(minutes=5))
            def current(self, lease_key): return self.lease
        self.provider, self.ledger, self.leases = Provider(), Ledger(), Leases()
        self.service = AuthorityService(self.provider, Plans(), self.ledger,
                                        clock=lambda: self.now, leases=self.leases)
        roles = ((SOURCE_OWNER, source), (DESTINATION_OWNER, target),
                 (SOURCE_SECURITY, source), (DESTINATION_SECURITY, target))
        for index, (role, scope) in enumerate(roles):
            name = f'reviewer-{index}'
            self.provider.identities[name] = VerifiedPrincipal(
                name, source.organization_id, source.tenant_id, 'HUMAN',
                now - timedelta(seconds=10), now + timedelta(hours=1), now,
                (RoleGrant(role, scope, now + timedelta(hours=1)),))
            self.service.record_approval(name, self.frozen.plan_id, role,
                                         ttl=timedelta(minutes=10), expected_revision=1,
                                         expected_digest=self.frozen.digest)
        self.provider.identities['worker-token'] = VerifiedPrincipal(
            'worker', source.organization_id, source.tenant_id, 'WORKER',
            now - timedelta(seconds=10), now + timedelta(hours=1), None,
            (RoleGrant(WORKER, target, now + timedelta(hours=1)),))
        self.grant = WorkerGrant(
            'grant-01', source.organization_id, source.tenant_id, self.frozen.plan_id,
            self.frozen.revision, self.frozen.digest, source, target, 'worker',
            'dataset-restore', 'restore-01', 'RESTORE_DATA', target, 'binding:dataset-1', 7,
            tuple(a.approval_id for a in self.ledger.approvals), 0,
            now, now + timedelta(minutes=2))
        self.ledger.grants['grant-01'] = self.grant
        self.transfer['spec']['grant']['grantId'] = self.grant.grant_id
        self.transfer['spec']['grant']['grantDigest'] = grant_digest(self.grant)
        self.guard = TransferGuard(self.service, 'worker-token', digest(encoded(self.envelope)),
                                   'grant-01', 'dataset-restore', 'restore-01')

    def operation(self):
        path = self.root / 'operation'; path.mkdir(mode=0o700)
        return path

    def restore(self, **kwargs):
        return restic_run.restore(self.config, self.receipt, self.manifest, self.engine,
                                  self.operation(), self.target, **kwargs)

    def test_cross_scope_copy_preserves_source_and_emits_separate_target_receipt(self):
        original = encoded(self.receipt)
        result = self.restore(transfer=self.envelope, transfer_guard=self.guard)
        target = load_private(self.root / 'operation/transfer-receipt.json')
        self.assertEqual(self.receipt['scope'], result['scope'])
        self.assertEqual(self.envelope['destination_execution_scope'], target['scope'])
        self.assertEqual(target['source_receipt_sha256'], digest(original))
        self.assertEqual(target['dataset_id'], 'dataset-1')
        self.assertEqual(target['target_ref'], 'target-dataset-1')
        self.assertFalse(target['application_acceptance'])
        self.assertFalse(target['native_qualification'])
        self.assertEqual(original, encoded(self.receipt))
        self.assertEqual((self.target / str(self.source).lstrip('/') / 'payload').read_bytes(),
                         b'original useful workload bytes')

    def test_same_scope_restore_still_works_without_transfer_grant(self):
        result = self.restore()
        self.assertEqual(result['scope'], self.config['scope'])
        self.assertFalse((self.root / 'operation/transfer-receipt.json').exists())

    def test_transfer_json_cannot_authorize_foreign_destination(self):
        with self.assertRaisesRegex(ValueError, 'live trusted worker'):
            self.restore(transfer=self.envelope)
        self.assertEqual(self.calls, [])
        self.assertFalse(self.target.exists())

    def test_forged_guard_or_client_identity_cannot_enable_transfer(self):
        with self.assertRaises(ValueError):
            self.restore(transfer=self.envelope, transfer_guard={'approved': True})
        self.assertEqual(self.calls, [])

    def test_receipt_relabel_and_changed_dataset_snapshot_or_target_are_rejected(self):
        mutations = [
            lambda x: x['transfer']['spec'].__setitem__('datasetId', 'dataset-2'),
            lambda x: x['transfer']['spec'].__setitem__('targetRef', 'target-dataset-2'),
            lambda x: x.__setitem__('snapshot_id', 'e' * 64),
            lambda x: x.__setitem__('target', str(self.root / 'other')),
            lambda x: x['source_execution_scope'].__setitem__('tenant_key', 'tenant-b'),
            lambda x: x['transfer']['spec']['sourceReceipt'].__setitem__('receiptDigest', 'e' * 64),
            lambda x: x['transfer']['spec']['expectedBytes'].__setitem__('value', 0),
        ]
        for mutation in mutations:
            candidate = deepcopy(self.envelope); mutation(candidate)
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                validate(candidate, self.config, self.receipt, self.manifest, self.target)
        relabeled = self.receipt | {'scope': self.envelope['destination_execution_scope']}
        with self.assertRaisesRegex(ValueError, 'Original capture'):
            validate(self.envelope, self.config, relabeled, self.manifest, self.target)
        self.assertEqual(self.calls, [])

    def test_structurally_valid_unapproved_alias_mapping_rejected(self):
        altered = deepcopy(self.envelope)
        altered['destination_execution_scope']['site_key'] = 'foreign-site'
        validate(altered, self.config, self.receipt, self.manifest, self.target)
        with self.assertRaisesRegex(ValueError, 'immutable runtime mapping'):
            self.guard.check(altered)

    def test_expired_revoked_wrong_scope_and_stale_lease_grants_fail_before_contact(self):
        for field, value in (('expires_at', self.now - timedelta(seconds=1)),
                             ('source', replace(self.grant.source, endpoint_id='foreign')),
                             ('operation_scope', self.grant.source), ('lease_epoch', 8)):
            self.ledger.grants['grant-01'] = replace(self.grant, **{field: value})
            with self.subTest(field=field), self.assertRaises(AuthorityDenied):
                self.guard.check(self.envelope)
        self.ledger.grants['grant-01'] = self.grant
        self.ledger.epoch += 1
        with self.assertRaises(AuthorityDenied): self.guard.check(self.envelope)
        self.assertEqual(self.calls, [])

    def test_revocation_after_snapshot_read_prevents_restore(self):
        self.revoke_before_restore = True
        with self.assertRaises(AuthorityDenied):
            self.restore(transfer=self.envelope, transfer_guard=self.guard)
        self.assertEqual(self.calls, ['repository', 'snapshots'])
        self.assertFalse(self.target.exists())
        self.assertFalse((self.root / 'operation/transfer-receipt.json').exists())

    def test_trusted_worker_entrypoint_checks_machine_isolation_and_seals_binding(self):
        original = Path.read_text
        def machine(path, *args, **kwargs):
            return 'f' * 32 if str(path) == '/etc/machine-id' else original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', new=machine), \
             patch.object(restic_run, 'Restic', return_value=self.engine):
            execute_authorized_transfer(
                authority_service=self.service, worker_credential='worker-token',
                expected_manifest_sha256=self.guard.expected_manifest_sha256,
                grant_id='grant-01', step_id='dataset-restore', operation_id='restore-01',
                transfer=self.envelope, config=self.config, credentials={}, binary='/unused',
                operation=self.root / 'runtime', receipt=self.receipt, expected=self.manifest,
                target=self.target, restore_authority=self.restore_authority)
        context = load_private(self.root / 'runtime/context.json')
        self.assertEqual(context['transfer_manifest_sha256'], digest(encoded(self.envelope)))
        self.assertEqual(load_private(self.root / 'runtime/transfer-manifest.json'), self.envelope)
        self.assertTrue((self.root / 'runtime/transfer-receipt.json').exists())


if __name__ == '__main__':
    unittest.main()
