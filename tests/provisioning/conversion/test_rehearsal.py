"""Real old-contract writers exercise the offline importer without native contact."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import timedelta
import io
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from provisioner.controlplane.conversion import rehearsal as conversion
from provisioner.domain.enterprise_records import validate_record
from provisioner.execution import terraform_apply as apply
from provisioner.execution import terraform_run as run
from provisioner.execution.run_files import digest, encoded, load_private, read_private, utcnow, write_new
from tests.test_terraform_run import TerraformRunFixture
from tests.provisioning.schema.test_enterprise_records import workload


class RehearsalTests(TerraformRunFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        # Use the actual selected OpenStack compiler/executor contracts. Only
        # platform processes/source transport are replaced; these are local
        # persistence fixtures, never native migration/qualification evidence.
        self.inputs = json.loads((run.ROOT / 'terraform/stacks/wsd/openstack/workloads/inputs.tfvars.json.example').read_text())
        self.inputs.update(allow_restricted_build=True, test_authorization_ref='TEST-PRIVATE-CHANGE',
                           openstack_cloud='test')
        self.entry, self.scope, self.state_key = run.select_scope(run.ROOT, 'openstack-wsd-workloads', self.inputs)
        self.args.catalog_id = self.entry['id']
        self.backend['state_key'] = self.state_key
        self.cloud = {'clouds': {'test': {'auth_type': 'v3applicationcredential', 'verify': True,
            'region_name': 'region-1', 'interface': 'internal', 'auth': {
                'auth_url': 'https://identity.example.test/v3', 'application_credential_id': 'fixture-id',
                'application_credential_secret': 'SYNTHETIC-RETAINED-SECRET'}}}}
        self.args.cloud = self.base / 'cloud'
        write_new(self.args.cloud, encoded(self.cloud))
        self.authority.update(scope=self.scope, input_sha256=digest(encoded(self.inputs)),
                              backend_sha256=digest(encoded(self.backend)), cloud_sha256=digest(encoded(self.cloud)))
        for name, value in {'inputs': self.inputs, 'backend': self.backend, 'authority': self.authority}.items():
            (self.base / name).write_bytes(encoded(value))
        self.prepare()
        bundle = load_private(self.args.output / 'bundle.json')
        at = utcnow()
        approval = {'format': 'hosting-terraform-approval/1', 'bundle_sha256': digest(encoded(bundle)),
            'review_sha256': digest(read_private(self.args.output / 'review.json')),
            'operation_id': bundle['operation_id'], 'generation': bundle['generation'],
            'valid_from': at.isoformat(), 'valid_until': (at + timedelta(minutes=20)).isoformat(),
            'change_ref': 'CHG-RETAINED-FIXTURE'}
        approval_file = self.base / 'approval'
        write_new(approval_file, encoded(approval))
        ledger = self.base / 'native-ledger'; ledger.mkdir(mode=0o700)
        member_id = next(iter(self.inputs['members']))
        self.outputs = {'scope': {'value': self.scope},
            'delivery_state': {'value': 'PREPARED_NOT_QUALIFIED_NOT_SERVICE_READY'},
            'members': {'value': {member_id: {
                'server_id': '11111111-1111-4111-8111-111111111111',
                'port_id': '22222222-2222-4222-8222-222222222222',
                'boot_volume_id': '33333333-3333-4333-8333-333333333333', 'data_volume_ids': [],
                'delivery_state': 'PREPARED_NOT_QUALIFIED_NOT_SERVICE_READY'}}}}

        def engine(binary, directory, argv, environment, output, **kwargs):
            write_new(output, encoded(self.outputs) if argv[0] == 'output' else b'local fixture apply\n')
            return 0

        args = argparse.Namespace(bundle=self.args.output, approval=approval_file,
                                  ledger=ledger, terraform=self.binary, execute_approved_change=True)
        with patch.object(apply, 'verify', return_value={'status': 'HASHES_MATCH', 'commit': self.source}), \
             patch.object(apply, 'command', side_effect=engine):
            apply.apply(args)
        self.source_root = self.base / 'retained'; self.source_root.mkdir(mode=0o700)
        operations = self.source_root / 'operations'; operations.mkdir(mode=0o700)
        shutil.copytree(self.args.output, operations / 'run-01')
        shutil.copytree(ledger, self.source_root / 'terraform-ledger')
        self.native_ledger = next((self.source_root / 'terraform-ledger').iterdir())
        self.scope_record = {'organizationId': 'org-01', 'tenantId': 'tenant-01',
            'securityDomainId': 'wsd-01', 'workloadId': 'workload-01',
            'endpointId': 'openstack-01', 'nativeScopeId': 'project-01', 'locationId': 'cell-01',
            'platformFamily': 'openstack', 'environmentKey': self.scope['environment_key'],
            'siteKey': self.scope['site_key']}

        def binding(kind, field):
            return {'endpointId': 'openstack-01', 'nativeScopeId': 'project-01',
                    'resourceKind': kind, 'nativeId': self.outputs['members']['value'][member_id][field],
                    'platformFamily': 'openstack'}

        self.bindings = [binding('vm', 'server_id'), binding('nic', 'port_id'), binding('volume', 'boot_volume_id')]
        self.workload = workload()
        machine = self.workload['spec']['machines'][0]
        machine['bindings'][0]['binding'] = self.bindings[0]
        machine['nics'] = machine['nics'][:1]
        machine['nics'][0]['bindings'][0]['binding'] = self.bindings[1]
        machine['disks'] = []
        self.workload['spec']['machines'] = [machine]
        self.workload['spec']['datasets'] = self.workload['spec']['datasets'][:1]
        self.workload['spec']['datasets'][0]['sourceBindings'] = [self.bindings[2]]
        self.assertEqual(validate_record(self.workload), [])
        write_new(self.source_root / 'workload.json', encoded(self.workload))
        at = utcnow(); self.as_of = at + timedelta(seconds=1)
        write_new(self.source_root / 'native.json', encoded({'format': 'hosting-retained-native-inventory/1',
            'scope': self.scope_record, 'capturedAt': at.isoformat(), 'observerId': 'native-observer',
            'complete': True, 'bindings': [{'binding': value, 'lifecycleStage': 'prepared'} for value in self.bindings]}))
        write_new(self.source_root / 'freeze.json', encoded({'format': 'hosting-retained-writer-freeze/1',
            'scope': self.scope_record, 'frozenAt': (at - timedelta(seconds=1)).isoformat(),
            'observerId': 'fence-observer', 'oldWriters': [{'writerId': 'legacy-runner', 'frozen': True,
                                                       'epoch': 1, 'proofDigest': 'e' * 64}]}))
        write_new(self.source_root / 'owners.json', encoded({'format': 'hosting-retained-owner-snapshot/1',
            'scope': self.scope_record, 'capturedAt': at.isoformat(), 'observerId': 'database-observer',
            'observationOnly': True, 'owners': [{'binding': value, 'epoch': 2, 'workerId': None}
                                             for value in self.bindings]}))
        self.manifest = {'format': conversion.FORMAT, 'batchId': 'fixture-batch', 'capturedAt': at.isoformat(),
            'scope': self.scope_record, 'sourceFileSha256': {}, 'workloadFiles': ['workload.json'],
            'terraformRuns': ['operations/run-01'],
            'terraformLedgers': [self.native_ledger.relative_to(self.source_root).as_posix()],
            'deliveryJournals': [], 'sourceCounts': {},
            'evidence': {'nativeInventory': 'native.json', 'oldWriterFreeze': 'freeze.json',
                         'newOwnerSnapshot': 'owners.json'}}
        self.manifest_file = self.base / 'manifest.json'
        self.destination = self.base / 'rehearsals'; self.destination.mkdir(mode=0o700)
        self.seal()

    def seal(self):
        self.manifest['sourceFileSha256'] = {
            file.relative_to(self.source_root).as_posix(): digest(file.read_bytes())
            for file in self.source_root.rglob('*') if file.is_file()}
        self.manifest['sourceCounts'] = {'files': len(self.manifest['sourceFileSha256']),
            'workloads': len(self.manifest['workloadFiles']), 'terraformRuns': len(self.manifest['terraformRuns']),
            'terraformStarts': len(list(self.native_ledger.glob('*.started.json'))),
            'terraformResults': len(list(self.native_ledger.glob('*.result.json'))), 'deliveryEvents': 0}
        self.manifest_file.write_bytes(encoded(self.manifest)); self.manifest_file.chmod(0o600)

    def rehearse(self):
        return conversion.rehearse(self.manifest_file, self.source_root, self.destination, as_of=self.as_of)

    def replace(self, path, mutate):
        path = self.source_root / path
        value = load_private(path); mutate(value); path.write_bytes(encoded(value)); self.seal()

    def explicit_stage(self, stage):
        """Rebind a generated fixture's exact v1 digests for explicit-stage cases."""
        operation = self.source_root / 'operations/run-01'
        inputs = load_private(operation / 'inputs.json')
        for value in inputs['members'].values():
            value['lifecycle_stage'] = stage
        (operation / 'inputs.json').write_bytes(encoded(inputs))
        contact = load_private(operation / 'contact.json'); contact['input_sha256'] = digest(encoded(inputs))
        (operation / 'contact.json').write_bytes(encoded(contact))
        outputs = load_private(operation / 'outputs.json')
        for value in outputs['members']['value'].values():
            value['lifecycle_stage'] = stage
        (operation / 'outputs.json').write_bytes(encoded(outputs))
        bundle = load_private(operation / 'bundle.json')
        bundle['artifacts']['inputs.json'] = digest(encoded(inputs))
        bundle['artifacts']['contact.json'] = digest(encoded(contact))
        (operation / 'bundle.json').write_bytes(encoded(bundle))
        bundle_digest = digest(encoded(bundle))
        approval = load_private(operation / 'approval.json'); approval['bundle_sha256'] = bundle_digest
        (operation / 'approval.json').write_bytes(encoded(approval))
        start_path = next(self.native_ledger.glob('*.started.json'))
        start = load_private(start_path); start['bundle_sha256'] = bundle_digest
        start_path.write_bytes(encoded(start))
        result_path = next(self.native_ledger.glob('*.result.json'))
        result = load_private(result_path); result.update(bundle_sha256=bundle_digest, outputs_sha256=digest(encoded(outputs)))
        result_path.write_bytes(encoded(result))
        (self.native_ledger / 'head.json').write_bytes(encoded(result))
        (operation / 'result.json').write_bytes(encoded(result))
        self.seal()

    def test_authentic_canonical_and_saved_plan_records_archive_and_reconcile(self):
        report = self.rehearse()
        self.assertEqual(report['status'], 'REHEARSAL_RECONCILED_OBSERVATION_ONLY')
        self.assertEqual(report['sourceCounts'], report['observedCounts'])
        self.assertEqual(report['retainedNativeIdCount'], 3)
        self.assertFalse(report['writesAuthorized']); self.assertFalse(report['databaseImported'])
        self.assertFalse(report['evidenceAuthenticated'])
        projection = load_private(self.destination / 'fixture-batch/projection.json')
        self.assertEqual(projection['lifecycleStages'][0]['lifecycleStage'], 'prepared')
        self.assertEqual(projection['lifecycleStages'][0]['stageOrigin'], 'NATIVE_OBSERVATION')
        self.assertNotIn('lifecycle_stage', load_private(self.source_root / 'operations/run-01/outputs.json')['members']['value']['processor-01'])
        for name in self.manifest['sourceFileSha256']:
            original = self.destination / 'fixture-batch/originals' / name
            self.assertEqual(original.read_bytes(), (self.source_root / name).read_bytes())
            self.assertEqual(original.stat().st_mode & 0o777, 0o400)

    def test_exact_reimport_is_idempotent_and_tampered_archive_conflicts(self):
        first = self.rehearse()
        self.assertEqual(self.rehearse(), first)
        archive = self.destination / 'fixture-batch/originals/workload.json'
        archive.chmod(0o600); archive.write_bytes(archive.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'published rehearsal bytes'):
            self.rehearse()

    def test_batch_identity_cannot_replace_prior_source_bytes(self):
        self.rehearse()
        self.replace('workload.json', lambda value: value['metadata'].update(ownerId='another-owner'))
        with self.assertRaisesRegex(ValueError, 'published rehearsal bytes'):
            self.rehearse()

    def test_uncertain_native_start_stays_unknown_even_with_complete_readbacks(self):
        result_path = next(self.native_ledger.glob('*.result.json')); result_path.unlink()
        start = load_private(next(self.native_ledger.glob('*.started.json')))
        (self.native_ledger / 'head.json').write_bytes(encoded(start))
        (self.source_root / 'operations/run-01/result.json').unlink()
        self.seal()
        report = self.rehearse()
        self.assertIn('HOLD_UNCERTAIN_NATIVE_START_REQUIRES_CANONICAL_RECOVERY', report['holds'])
        self.assertEqual(report['uncertainAttemptCount'], 1)
        projection = load_private(self.destination / 'fixture-batch/projection.json')
        self.assertEqual(projection['attempts'][0]['outcome'], 'UNKNOWN')
        self.assertFalse(projection['attempts'][0]['retryAuthorized'])

    def test_absent_native_inventory_never_becomes_empty_success(self):
        (self.source_root / 'native.json').unlink()
        self.manifest['evidence']['nativeInventory'] = None; self.seal()
        report = self.rehearse()
        self.assertIn('HOLD_MISSING_NATIVEINVENTORY', report['holds'])
        self.assertIn('HOLD_NATIVE_ID_INVENTORY_MISMATCH', report['holds'])
        projection = load_private(self.destination / 'fixture-batch/projection.json')
        self.assertIsNone(projection['lifecycleStages'][0]['lifecycleStage'])
        self.assertEqual(projection['lifecycleStages'][0]['stageOrigin'], 'UNRESOLVED')

    def test_missing_freeze_or_epoch_advance_blocks_owner_handover(self):
        self.replace('freeze.json', lambda value: value['oldWriters'][0].update(frozen=False))
        self.replace('owners.json', lambda value: value['owners'][0].update(epoch=1))
        report = self.rehearse()
        self.assertIn('HOLD_OLD_WRITER_NOT_FROZEN', report['holds'])
        self.assertIn('HOLD_NEW_OWNER_EPOCH_NOT_ADVANCED', report['holds'])

    def test_missing_legacy_stage_can_be_proposed_from_agreed_bootstrap_observation(self):
        self.replace('native.json', lambda value: [row.update(lifecycleStage='bootstrap') for row in value['bindings']])
        # Without a legacy stage, the proposal records the independently supplied
        # bootstrap stage. It never rewrites v1 bytes or claims approval renewal.
        report = self.rehearse()
        self.assertEqual(report['status'], 'REHEARSAL_RECONCILED_OBSERVATION_ONLY')
        projection = load_private(self.destination / 'fixture-batch/projection.json')
        self.assertEqual(projection['lifecycleStages'][0]['lifecycleStage'], 'bootstrap')

    def test_explicit_bootstrap_originals_are_preserved_and_native_mismatch_holds(self):
        self.explicit_stage('bootstrap')
        self.replace('native.json', lambda value: [row.update(lifecycleStage='bootstrap') for row in value['bindings']])
        report = self.rehearse()
        self.assertEqual(report['status'], 'REHEARSAL_RECONCILED_OBSERVATION_ONLY')
        projection = load_private(self.destination / 'fixture-batch/projection.json')
        self.assertEqual(projection['lifecycleStages'][0]['stageOrigin'], 'EXPLICIT_LEGACY')
        self.assertEqual(projection['lifecycleStages'][0]['nativeEvidenceDigest'],
                         self.manifest['sourceFileSha256']['native.json'])
        self.manifest['batchId'] = 'mismatch-batch'
        self.replace('native.json', lambda value: [row.update(lifecycleStage='prepared') for row in value['bindings']])
        self.assertIn('HOLD_LIFECYCLE_STAGE_NATIVE_MISMATCH', self.rehearse()['holds'])

    def test_conflicting_native_stages_remain_unresolved(self):
        self.replace('native.json', lambda value: value['bindings'][0].update(lifecycleStage='bootstrap'))
        self.assertIn('HOLD_UNRESOLVED_NATIVE_LIFECYCLE_STAGE', self.rehearse()['holds'])

    def test_bad_digest_is_rejected_before_any_publication(self):
        (self.source_root / 'workload.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'bytes changed'):
            self.rehearse()
        self.assertFalse((self.destination / 'fixture-batch').exists())

    def test_malformed_canonical_legacy_fixture_is_rejected(self):
        self.replace('workload.json', lambda value: value['spec']['machines'][0].pop('guestProfile'))
        with self.assertRaisesRegex(ValueError, 'Authentic canonical'):
            self.rehearse()

    def test_mixed_old_new_ledger_is_rejected_instead_of_normalized(self):
        path = next(self.native_ledger.glob('*.result.json')).relative_to(self.source_root).as_posix()
        self.replace(path, lambda value: value.update(format='hosting-terraform-attempt/2'))
        with self.assertRaisesRegex(ValueError, 'attempt contract'):
            self.rehearse()

    def test_completed_output_bytes_must_match_retained_result_digest(self):
        self.replace('operations/run-01/outputs.json', lambda value: value['members']['value']['processor-01'].update(server_id='another-native-id'))
        with self.assertRaisesRegex(ValueError, 'result output bytes differ'):
            self.rehearse()

    def test_foreign_scope_rejects_and_duplicate_native_ids_reject(self):
        self.replace('native.json', lambda value: value['bindings'][0]['binding'].update(nativeScopeId='foreign-project'))
        with self.assertRaisesRegex(ValueError, 'another scope'):
            self.rehearse()
        self.replace('native.json', lambda value: value['bindings'][0]['binding'].update(nativeScopeId='project-01'))
        self.replace('native.json', lambda value: value['bindings'].append(deepcopy(value['bindings'][0])))
        with self.assertRaisesRegex(ValueError, 'Duplicate independently'):
            self.rehearse()

    def test_manifest_count_mismatch_and_unknown_retained_file_are_explicit_holds(self):
        write_new(self.source_root / 'unknown-record.json', b'{"format":"unsupported-state/1"}\n')
        self.seal(); self.manifest['sourceCounts']['terraformResults'] += 1
        self.manifest_file.write_bytes(encoded(self.manifest))
        report = self.rehearse()
        self.assertIn('HOLD_SOURCE_COUNT_MISMATCH', report['holds'])
        self.assertIn('HOLD_UNRECOGNIZED_RETAINED_FILES', report['holds'])

    def test_implicit_zero_inventory_and_new_active_owner_do_not_pass(self):
        self.replace('owners.json', lambda value: value['owners'][0].update(workerId='active-worker'))
        with self.assertRaisesRegex(ValueError, 'active writer'):
            self.rehearse()

    def test_source_published_after_inventory_is_not_ignored(self):
        write_new(self.source_root / 'late.result.json', b'{}')
        with self.assertRaisesRegex(ValueError, 'Enumerated retained files'):
            self.rehearse()

    def test_interrupted_publication_replays_originals_without_overwrite(self):
        publish = conversion._publish

        def interrupt(path, raw):
            if path.name == 'projection.json':
                raise InterruptedError('interrupted publication')
            return publish(path, raw)

        with patch.object(conversion, '_publish', side_effect=interrupt), self.assertRaises(InterruptedError):
            self.rehearse()
        self.assertFalse((self.destination / 'fixture-batch/reconciliation.json').exists())
        self.assertEqual(self.rehearse()['status'], 'REHEARSAL_RECONCILED_OBSERVATION_ONLY')

    def test_old_writer_publication_during_archive_cannot_emit_final_report(self):
        publish = conversion._publish
        changed = False

        def late_write(path, raw):
            nonlocal changed
            result = publish(path, raw)
            if not changed and path.name == 'workload.json':
                changed = True
                write_new(self.source_root / 'late.result.json', b'{}')
            return result

        with patch.object(conversion, '_publish', side_effect=late_write), \
                self.assertRaisesRegex(ValueError, 'changed during rehearsal'):
            self.rehearse()
        self.assertFalse((self.destination / 'fixture-batch/reconciliation.json').exists())

    def test_private_paths_and_ambiguous_json_are_rejected(self):
        (self.source_root / 'workload.json').chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'owner-only'):
            self.rehearse()
        (self.source_root / 'workload.json').chmod(0o600)
        self.manifest_file.write_bytes(b'{"format":"one","format":"two"}')
        with self.assertRaises(ValueError):
            self.rehearse()

    def test_console_never_exports_originals_secrets_or_private_paths(self):
        out = io.StringIO()
        with patch('sys.stdout', out):
            exit_code = conversion.main(['--manifest', str(self.manifest_file), '--source-root',
                str(self.source_root), '--destination', str(self.destination), '--as-of', self.as_of.isoformat()])
        self.assertEqual(exit_code, 0)
        self.assertNotIn('SYNTHETIC', out.getvalue()); self.assertNotIn(str(self.base), out.getvalue())
        self.assertFalse(json.loads(out.getvalue())['writesAuthorized'])


if __name__ == '__main__':
    unittest.main()
