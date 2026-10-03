from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from tests.test_guest_inventory import fixture
from tests.test_guest_services import fixture as service_fixture
from lab.native_readback_fixture import credentials
from tools import guest_run as g
from provisioner.execution.run_files import digest, encoded, load_private, write_new

SOURCE = {'status': 'HASHES_MATCH', 'commit': 'a'*40}


def inputs(folder, mode='check'):
    outputs, access = fixture()
    for name, value in [('outputs.json', outputs), ('access.json', access),
                        ('references.json', {k: 'FIXTURE-ONLY' for k in g.REFERENCES})]:
        write_new(folder/name, encoded(value))
    write_new(folder/'key', b'-----BEGIN OPENSSH PRIVATE KEY-----\nFIXTURE-NOT-A-KEY\n')
    write_new(folder/'cert', b'ssh-ed25519-cert-v01@openssh.com Zml4dHVyZQ==\n')
    return SimpleNamespace(operation_id='guest-01', generation=1, mode=mode, max_seconds=60,
        workload_run=None, workload_outputs=folder/'outputs.json', access=folder/'access.json',
        references=folder/'references.json', ssh_key=folder/'key', ssh_certificate=folder/'cert',
        python=Path(sys.executable), ssh=Path('/usr/bin/ssh'), output=folder/'bundle')


def prepare(args):
    with patch.object(g, 'verify', return_value=SOURCE): return g.prepare(args)


class GuestPreparationTests(unittest.TestCase):
    def test_private_bundle_has_exact_source_inputs_and_no_copied_ssh_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); args = inputs(folder); result = prepare(args); directory = args.output
            self.assertFalse(result['target_contacted']); bundle = load_private(directory/'bundle.json')
            self.assertEqual(bundle['mode'], 'check'); self.assertFalse((directory/'runtime/ssh_key').exists())
            self.assertEqual(bundle['source_files'], g.file_map(directory/'source'))
            self.assertEqual(result['bundle_sha256'], digest((directory/'bundle.json').read_bytes()))
            for path in directory.rglob('*'): self.assertEqual(path.stat().st_mode & 0o077, 0)
            self.assertNotIn('FIXTURE-NOT-A-KEY', '\n'.join(p.read_text() for p in directory.iterdir() if p.is_file()))
            runtime = load_private(directory/'runtime.json')
            self.assertEqual(runtime['packages']['ansible']['version'], '2.19.7')
            self.assertEqual(runtime['ssh_sha256'], digest(Path('/usr/bin/ssh').read_bytes()))

    def test_unknown_references_bad_scope_expiry_and_bad_source_stop_preparation(self):
        for fault in ('references', 'scope', 'expiry', 'source', 'generation', 'mode', 'limit', 'certificate'):
            with tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp); args = inputs(folder)
                if fault == 'references': (folder/'references.json').write_bytes(encoded({}))
                elif fault in {'scope', 'expiry'}:
                    access = load_private(args.access)
                    if fault == 'scope': access['scope']['tenant_key'] = 'foreign'
                    else: access['valid_until'] = '2000-01-01T00:00:00Z'
                    args.access.write_bytes(encoded(access))
                elif fault == 'generation': args.generation = True
                elif fault == 'mode': args.mode = 'activate'
                elif fault == 'limit': args.max_seconds = 3601
                elif fault == 'certificate': args.ssh_certificate.write_bytes(b'not-a-certificate')
                with patch.object(g, 'verify', return_value=SOURCE if fault != 'source' else {'status': 'DIRTY'}), \
                     self.subTest(fault=fault), self.assertRaises(ValueError): g.prepare(args)
                self.assertFalse(args.output.exists())

    def test_changed_source_during_copy_cannot_produce_a_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = inputs(Path(tmp))
            with patch.object(g, 'verify', side_effect=[SOURCE, SOURCE | {'commit': 'b'*40}]), self.assertRaises(ValueError): g.prepare(args)
            self.assertFalse((args.output/'bundle.json').exists())

    def test_service_credentials_are_snapshotted_and_rebound_privately(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); args = inputs(folder); credentials(folder)
            access = load_private(args.access); target = access['targets']['guest-01']
            target['profile'] = g.PROFILE; target['services'] = service_fixture(folder)[0]['services']
            for asset in g.assets(target):
                path = Path(asset['path']); path.chmod(0o600); asset['sha256'] = digest(path.read_bytes())
            args.access.write_bytes(encoded(access)); prepare(args)
            rewritten = load_private(args.output/'access.json')['targets']['guest-01']
            for original, sealed in zip(g.assets(target), g.assets(rewritten)):
                self.assertTrue(Path(sealed['path']).is_relative_to(args.output/'assets'))
                self.assertEqual(Path(original['path']).read_bytes(), Path(sealed['path']).read_bytes())
                Path(original['path']).write_bytes(b'changed-after-preparation')
                self.assertEqual(digest(Path(sealed['path']).read_bytes()), sealed['sha256'])

    def test_private_paths_overwrite_and_unsafe_paths_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = inputs(Path(tmp)); args.access.chmod(0o644)
            with self.assertRaises(ValueError): prepare(args)
            args.access.chmod(0o600); prepare(args)
            with self.assertRaises(FileExistsError): prepare(args)
            args.output = Path(tmp)/'unsafe path'
            with self.assertRaises(ValueError): prepare(args)

    def test_child_environment_drops_ambient_connection_and_python_overrides(self):
        with patch.dict('os.environ', {'ANSIBLE_CONFIG': '/evil', 'PYTHONPATH': '/evil',
                'SSH_AUTH_SOCK': '/evil', 'ANSIBLE_SSH_ARGS': '-o StrictHostKeyChecking=no', 'HTTPS_PROXY': '/evil'}):
            env = g.runtime_environment(Path('/private/guest'))
        self.assertFalse({'PYTHONPATH', 'SSH_AUTH_SOCK', 'ANSIBLE_SSH_ARGS', 'HTTPS_PROXY'} & set(env))
        self.assertEqual(env['ANSIBLE_CONFIG'], '/private/guest/ansible.cfg')


if __name__ == '__main__': unittest.main()
