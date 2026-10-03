from datetime import timedelta
from pathlib import Path
import tempfile
import unittest

from test_compile_wsd import example, receipts
from provisioner.compiler.wsd import compile_environment
from provisioner.execution.run_files import digest, encoded, load_private, utcnow, write_new
from tools.wsd_handoff import compile_runs


class WsdHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def runs(self, platform='nutanix'):
        env = example(platform)
        outputs, bindings = receipts(env)
        files, scopes = compile_environment(env)
        directories = []
        for n, row in enumerate(scopes['scopes']):
            directory = self.base / (platform + str(n))
            directory.mkdir(mode=0o700)
            key = row['scope']['tenant_key'] + '/' + row['scope']['wsd_key']
            inputs = files[row['input']]
            bundle = {'format': 'hosting-terraform-bundle/1', 'source_commit': 'a' * 40,
                      'scope': row['scope'], 'operation_id': 'op-' + str(n), 'generation': 1,
                      'artifacts': {'inputs.json': digest(encoded(inputs))}}
            result = {'format': 'hosting-terraform-attempt/1', 'status': 'APPLIED_REQUIRES_NATIVE_ACCEPTANCE',
                      'scope': row['scope'], 'operation_id': bundle['operation_id'], 'generation': 1,
                      'bundle_sha256': digest(encoded(bundle)), 'outputs_sha256': digest(encoded(outputs[key])),
                      'completed_at': utcnow().isoformat()}
            for name, data in [('inputs.json', inputs), ('outputs.json', outputs[key]), ('bundle.json', bundle), ('result.json', result)]:
                write_new(directory / name, encoded(data))
            directories.append(directory)
        return env, directories, bindings

    def test_all_platforms_use_actual_receipts_and_keep_drafts_disabled(self):
        for platform in ('nutanix', 'openstack', 'vmware'):
            env, runs, bindings = self.runs(platform)
            files, scopes, provenance = compile_runs(env, runs, bindings)
            self.assertEqual(len(scopes['scopes']), 2)
            self.assertEqual(len(provenance['runs']), 2)
            for inputs in files.values():
                self.assertFalse(inputs['allow_restricted_build'])
                self.assertTrue(all(v['accepted_quarantine_ref'] == '' for v in inputs['members'].values()))

    def test_missing_duplicate_and_foreign_receipts_reject(self):
        env, runs, _ = self.runs()
        for supplied in (runs[:1], runs + runs[:1]):
            with self.assertRaises(ValueError):
                compile_runs(env, supplied)
        env['site_key'] = 'other-site'
        with self.assertRaises(ValueError):
            compile_runs(env, runs)

    def test_changed_native_output_cannot_supply_a_new_id(self):
        env, runs, _ = self.runs()
        path = runs[0] / 'outputs.json'
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'bytes changed'):
            compile_runs(env, runs)

    def test_failed_or_stale_execution_is_not_a_handoff(self):
        env, runs, _ = self.runs()
        path = runs[0] / 'result.json'
        result = load_private(path)
        for changes in ({'status': 'HOLD_RECONCILIATION_REQUIRED'},
                        {'completed_at': (utcnow() - timedelta(days=2)).isoformat()}):
            path.write_bytes(encoded({**result, **changes}))
            with self.assertRaises(ValueError):
                compile_runs(env, runs)

    def test_changed_allocation_intent_rejects_old_domain_run(self):
        env, runs, _ = self.runs()
        env['wsds'][0]['domains'][0]['inputs']['gateway_host_number'] = 5
        with self.assertRaisesRegex(ValueError, 'differ from current'):
            compile_runs(env, runs)
