from datetime import timedelta
import argparse
import json
import subprocess
import unittest
from unittest.mock import patch

from test_terraform_run import TerraformRunFixture
from tools import terraform_apply as apply
from tools.compile_wsd import STATE
from tools.run_files import digest, encoded, load_private, read_private, utcnow, write_new


class TerraformApplyTests(TerraformRunFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.prepare()
        self.bundle = load_private(self.args.output / 'bundle.json')
        now = utcnow()
        self.approval = {'format': 'hosting-terraform-approval/1',
                         'bundle_sha256': digest(read_private(self.args.output / 'bundle.json')),
                         'review_sha256': digest(read_private(self.args.output / 'review.json')),
                         'operation_id': self.bundle['operation_id'], 'generation': self.bundle['generation'],
                         'valid_from': now.isoformat(), 'valid_until': (now + timedelta(minutes=20)).isoformat(),
                         'change_ref': 'CHG-APPLY-001'}
        self.approval_file = self.base / 'approved.json'
        write_new(self.approval_file, encoded(self.approval))
        self.ledger = self.base / 'ledger'
        self.ledger.mkdir(mode=0o700)
        self.apply_args = argparse.Namespace(bundle=self.args.output, approval=self.approval_file,
            ledger=self.ledger, terraform=self.binary, execute_approved_change=True)
        self.apply_calls = []

    def outputs(self):
        return {'scope': {'value': self.scope}, 'delivery_state': {'value': STATE},
                'members': {'value': {key: {'delivery_state': STATE, 'vpc_id': 'synthetic-only'}
                                      for key in self.inputs['members']}}}

    def apply_engine(self, binary, directory, argv, environment, output, **kwargs):
        self.apply_calls.append(argv)
        write_new(output, encoded(self.outputs()) if argv[0] == 'output' else b'private apply log\n')

    def execute(self, engine=None):
        with patch.object(apply, 'verify', return_value={'status': 'HASHES_MATCH', 'commit': self.source}), \
             patch.object(apply, 'command', side_effect=engine or self.apply_engine):
            return apply.apply(self.apply_args)

    def test_apply_only_uses_reviewed_binary_plan(self):
        result = self.execute()
        self.assertEqual([c[0] for c in self.apply_calls], ['apply', 'output'])
        self.assertEqual(self.apply_calls[0][-1], str(self.args.output / 'saved.tfplan'))
        self.assertIn('-lock=true', self.apply_calls[0])
        self.assertNotIn('-auto-approve', self.apply_calls[0])
        self.assertEqual(result['status'], 'APPLIED_REQUIRES_NATIVE_ACCEPTANCE')
        self.assertFalse(result['production_activation'])

    def test_duplicate_operation_never_reapplies(self):
        self.execute()
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(len(self.apply_calls), 2)

    def test_failure_records_unknown_and_blocks_next_attempt(self):
        def interrupted(*args, **kwargs):
            raise subprocess.TimeoutExpired('terraform', 1)
        with self.assertRaises(subprocess.TimeoutExpired):
            self.execute(interrupted)
        head = load_private(next(self.ledger.glob('*/head.json')))
        self.assertEqual(head['status'], 'HOLD_RECONCILIATION_REQUIRED')
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(self.apply_calls, [])

    def test_start_record_is_durable_before_mutation(self):
        def inspect(binary, directory, argv, environment, output, **kwargs):
            if argv[0] == 'apply':
                self.assertEqual(load_private(next(self.ledger.glob('*/head.json')))['status'], 'STARTED_OUTCOME_UNKNOWN')
                self.assertEqual(len(list(self.ledger.glob('*/*.started.json'))), 1)
            self.apply_engine(binary, directory, argv, environment, output, **kwargs)
        self.execute(inspect)

    def test_changed_plan_or_inputs_block_before_native_contact(self):
        for name in ('saved.tfplan', 'inputs.json', 'environment.json', 'review.json', 'backend.hcl'):
            path = self.args.output / name
            original = path.read_bytes()
            path.write_bytes(original + b'changed')
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.execute()
            path.write_bytes(original)
        self.assertEqual(self.apply_calls, [])

    def test_changed_or_added_source_is_rejected(self):
        extra = self.args.output / 'source' / self.entry['root'] / 'override.tf'
        extra.write_text('# unreviewed')
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(self.apply_calls, [])

    def test_different_binary_is_rejected(self):
        self.binary.write_bytes(b'changed engine')
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(self.apply_calls, [])

    def test_expired_or_wrong_approval_is_rejected(self):
        for key, value in [('bundle_sha256', 'b' * 64), ('review_sha256', 'b' * 64),
                           ('generation', 2), ('valid_until', (utcnow() - timedelta(seconds=1)).isoformat())]:
            self.approval_file.write_bytes(encoded({**self.approval, key: value}))
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.execute()
        self.assertEqual(self.apply_calls, [])

    def test_output_failure_never_retries_apply(self):
        def failure(binary, directory, argv, environment, output, **kwargs):
            self.apply_calls.append(argv)
            if argv[0] == 'output':
                raise ValueError('readback unavailable')
            write_new(output, b'apply completed')
        with self.assertRaises(ValueError):
            self.execute(failure)
        self.assertEqual([c[0] for c in self.apply_calls], ['apply', 'output'])
        self.assertEqual(load_private(self.args.output / 'result.json')['status'], 'HOLD_RECONCILIATION_REQUIRED')

    def test_other_scope_outputs_are_held(self):
        outputs = self.outputs()
        outputs['scope']['value'] = {**self.scope, 'tenant_key': 'wrong-tenant'}
        with patch.object(self, 'outputs', return_value=outputs), self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(load_private(self.args.output / 'result.json')['status'], 'HOLD_RECONCILIATION_REQUIRED')

    def test_concurrent_scope_writer_is_rejected(self):
        with apply.scope_ledger(self.ledger, self.backend['address']):
            with self.assertRaises(BlockingIOError):
                self.execute()
        self.assertEqual(self.apply_calls, [])

    def test_native_opt_in_required(self):
        self.apply_args.execute_approved_change = False
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(self.apply_calls, [])

    def test_even_a_reviewed_incomplete_manifest_is_rejected(self):
        bundle = load_private(self.args.output / 'bundle.json')
        del bundle['artifacts']['environment.json']
        (self.args.output / 'bundle.json').write_bytes(encoded(bundle))
        self.approval['bundle_sha256'] = digest(encoded(bundle))
        self.approval_file.write_bytes(encoded(self.approval))
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            self.execute()
        self.assertEqual(self.apply_calls, [])


if __name__ == '__main__':
    unittest.main()
