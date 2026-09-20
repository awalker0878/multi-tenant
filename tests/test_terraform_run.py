import argparse
import copy
from datetime import timedelta
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import terraform_run as run
from tools.run_files import current_window, digest, encoded, load_private, read_private, utcnow, write_new


def closed_plan():
    return {'format_version': '1.2', 'resource_changes': [{
        'address': 'module.owned.openstack_networking_network_v2.domain', 'mode': 'managed',
        'type': 'openstack_networking_network_v2',
        'provider_name': 'registry.terraform.io/terraform-provider-openstack/openstack',
        'change': {'actions': ['create'], 'before': None, 'after_unknown': {},
                   'after': {'admin_state_up': False, 'shared': False, 'external': False,
                             'port_security_enabled': True}}}]}


class TerraformRunFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.inputs = json.loads((run.ROOT / 'terraform/stacks/wsd/nutanix/domains/inputs.tfvars.json.example').read_text())
        self.inputs.update(allow_restricted_build=True, test_authorization_ref='TEST-PRIVATE-CHANGE')
        self.entry, self.scope, self.state_key = run.select_scope(run.ROOT, 'nutanix-wsd-domains', self.inputs)
        self.backend = {'state_key': self.state_key, 'address': 'https://state.example.test/state/1',
                        'lock_address': 'https://state.example.test/state/1/lock',
                        'unlock_address': 'https://state.example.test/state/1/lock',
                        'lock_method': 'POST', 'unlock_method': 'DELETE'}
        self.source = 'a' * 40
        now = utcnow()
        self.authority = {'format': 'hosting-terraform-contact/1', 'source_commit': self.source,
                          'scope': self.scope, 'operation_id': 'op-01', 'generation': 1,
                          'input_sha256': digest(encoded(self.inputs)), 'backend_sha256': digest(encoded(self.backend)),
                          'valid_from': (now - timedelta(minutes=1)).isoformat(),
                          'valid_until': (now + timedelta(minutes=20)).isoformat(), 'change_ref': 'CHG-001'}
        for name, value in {'inputs': self.inputs, 'backend': self.backend, 'authority': self.authority,
                            'environment': {'TF_VAR_platform_password': 'SYNTHETIC-SECRET'}}.items():
            write_new(self.base / name, encoded(value))
        self.binary = self.base / 'terraform'
        write_new(self.binary, b'not a native engine; test double only\n')
        self.binary.chmod(0o700)
        self.args = argparse.Namespace(**{k: self.base / k for k in ('inputs', 'backend', 'authority', 'environment')},
             terraform=self.binary, output=self.base / 'operation', references=None,
             catalog_id='nutanix-wsd-domains', read_authorized_target=True)
        self.calls = []

    def snapshot(self, root, destination):
        directory = destination / self.entry['root']
        directory.mkdir(parents=True, mode=0o700)
        write_new(directory / 'main.tf.json', b'{}\n')

    def engine(self, binary, directory, argv, environment, output, **kwargs):
        self.calls.append(argv)
        value = b'private engine log\n'
        if argv[0] == 'version':
            value = encoded({'terraform_version': json.loads((run.ROOT / 'config/toolchain.json').read_text())['terraform']})
        elif argv[0] == 'plan':
            write_new(self.args.output / 'saved.tfplan', b'SYNTHETIC BINARY PLAN')
        elif argv[0] == 'show':
            value = encoded(closed_plan())
        write_new(output, value)
        return 0

    def prepare(self):
        with patch.object(run, 'verify', return_value={'status': 'HASHES_MATCH', 'commit': self.source}), \
             patch.object(run, 'snapshot', side_effect=self.snapshot), \
             patch.object(run, 'command', side_effect=self.engine):
            return run.prepare(self.args)


class TerraformRunTests(TerraformRunFixture, unittest.TestCase):
    def test_prepare_saves_the_binary_plan_and_derives_its_json(self):
        result = self.prepare()
        self.assertEqual([c[0] for c in self.calls], ['version', 'init', 'plan', 'show'])
        self.assertIn('-lockfile=readonly', self.calls[1])
        self.assertIn('-lock=true', self.calls[2])
        self.assertEqual(self.calls[3], ['show', '-json', str(self.args.output / 'saved.tfplan')])
        bundle = load_private(self.args.output / 'bundle.json')
        self.assertEqual(bundle['state_key'], self.state_key)
        self.assertEqual(result['bundle_sha256'], digest(read_private(self.args.output / 'bundle.json')))
        self.assertFalse(result['native_apply'])
        self.assertNotIn('SYNTHETIC-SECRET', json.dumps(result))

    def test_contact_opt_in_is_required_before_any_command(self):
        self.args.read_authorized_target = False
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(self.calls, [])

    def test_no_overwrite_of_a_reviewed_operation(self):
        self.prepare()
        with self.assertRaises(FileExistsError):
            self.prepare()

    def test_stale_contact_authority_stops_before_command(self):
        self.authority['valid_until'] = (utcnow() - timedelta(seconds=1)).isoformat()
        self.args.authority.write_bytes(encoded(self.authority))
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(self.calls, [])

    def test_changed_inputs_stop_before_command(self):
        self.inputs['site_key'] = 'other-site'
        self.args.inputs.write_bytes(encoded(self.inputs))
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(self.calls, [])

    def test_backend_rejects_wrong_scope_or_unsafe_transport(self):
        for key, value in [('state_key', 'other'), ('address', 'http://state.example.test/a'),
                           ('address', 'https://user:secret@state.example.test/a'),
                           ('lock_address', 'https://other.example.test/a')]:
            with self.subTest(field=key, value=value):
                backend = {**self.backend, key: value}
                with self.assertRaises(ValueError):
                    run.backend_settings(backend, self.state_key)

    def test_backend_requires_explicit_lock_endpoints(self):
        del self.backend['lock_address']
        with self.assertRaises(ValueError):
            run.backend_settings(self.backend, self.state_key)

    def test_environment_cannot_override_execution_or_target(self):
        for key in ('TF_CLI_ARGS', 'TF_CLI_ARGS_plan', 'TF_HTTP_ADDRESS', 'TF_WORKSPACE', 'TF_VAR_site_key', 'TF_LOG'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                run.process_environment({key: 'forbidden'})
        with patch.dict(os.environ, {'TF_CLI_ARGS_apply': '-lock=false', 'TF_LOG': 'TRACE'}):
            self.assertNotIn('TF_CLI_ARGS_apply', run.process_environment({}))
            self.assertNotIn('TF_LOG', run.process_environment({}))

    def test_private_input_permissions_and_links(self):
        self.args.inputs.chmod(0o644)
        with self.assertRaises(ValueError):
            self.prepare()
        self.args.inputs.chmod(0o600)
        link = self.base / 'link'
        link.symlink_to(self.args.inputs)
        with self.assertRaises(ValueError):
            read_private(link)

    def test_expiry_is_not_a_fixture_clock(self):
        record = {'valid_from': '2020-01-01T00:00:00Z', 'valid_until': '2020-01-01T00:01:00Z'}
        with self.assertRaises(ValueError):
            current_window(record)

    def test_ambiguous_json_is_rejected(self):
        self.args.inputs.write_bytes(b'{"site_key":"one","site_key":"two"}')
        with self.assertRaises(ValueError):
            self.prepare()

    def test_disabled_inputs_and_embedded_passwords_rejected(self):
        for changes in ({'allow_restricted_build': False}, {'platform_password': 'secret'}):
            with self.assertRaises(ValueError):
                run.select_scope(run.ROOT, 'nutanix-wsd-domains', {**self.inputs, **changes})


if __name__ == '__main__':
    unittest.main()
