"""Recovery admission refuses unsafe bytes and incomplete consistency boundaries."""
import base64
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from permit_desk.bundle import digest, encode, validate_bundle
from permit_desk.state import export_files, import_files, validate
from run_permit_desk import PermitCampaign, prepare_fixture

ROOT = Path(__file__).resolve().parents[2]
IMAGE = 'sha256:'+'a'*64
REVISION = 'b'*40
CONFIG = json.loads((ROOT/'deploy/fixtures/permit-desk/config.json').read_text())


def capture():
    content = b'synthetic attachment\n'
    file = {'key': 't_demo--permit_one.bin', 'base64': base64.b64encode(content).decode(), 'sha256': digest(content), 'bytes': len(content), 'mode': 0o640}
    archive = b'PGDMPsynthetic-header-for-admission-test-only'
    return {'schema_version': 1, 'fixture': 'permit-desk-v1', 'image_id': IMAGE, 'source_revision': REVISION,
            'config': copy.deepcopy(CONFIG), 'database': {'base64': base64.b64encode(archive).decode(), 'sha256': digest(archive), 'bytes': len(archive)},
            'attachments': [file], 'snapshot': {'fixture_schema': [{'version': 1}], 'tenants': [{'tenant_id': 't_demo'}, {'tenant_id': 't_other'}],
                'permits': [{'tenant_id': 't_demo', 'permit_id': 'permit_one'}],
                'attachments': [{'tenant_id': 't_demo', 'permit_id': 'permit_one', 'object_key': file['key'], 'sha256': file['sha256'], 'bytes': file['bytes']}]},
            'writers': {'application': 'stopped', 'runtime_login': 'disabled', 'runtime_sessions': 0, 'other_writers': []}}


class CaptureTest(unittest.TestCase):
    def test_round_trip_complete_fixture(self):
        bundle = capture()
        self.assertTrue(validate_bundle(bundle, digest(encode(bundle)), IMAGE, REVISION, CONFIG).startswith(b'PGDMP'))
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.assertEqual(import_files(directory, bundle['attachments']), bundle['attachments'])
            self.assertEqual(export_files(directory), bundle['attachments'])
            with self.assertRaisesRegex(ValueError, 'empty'):
                import_files(directory, bundle['attachments'])

    def test_tampered_capture_fails_external_digest(self):
        bundle = capture()
        checksum = digest(encode(bundle))
        bundle['config']['native_writes'] = True
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            validate_bundle(bundle, checksum, IMAGE, REVISION, CONFIG)

    def test_rehashed_incomplete_or_unsafe_capture_is_still_rejected(self):
        mutations = [
            lambda b: b['attachments'].clear(),
            lambda b: b['snapshot']['permits'].clear(),
            lambda b: b['writers'].update(runtime_sessions=1),
            lambda b: b['writers'].update(application='running'),
            lambda b: b['config'].update(native_writes=True),
            lambda b: b.update(image_id='sha256:'+'c'*64),
            lambda b: b['database'].update(base64=base64.b64encode(b'PGDMPbroken').decode()),
            lambda b: b['attachments'][0].update(key='../escape'),
            lambda b: b['attachments'][0].update(mode=0o777),
            lambda b: b['snapshot']['attachments'][0].update(tenant_id='t_other'),
        ]
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                bundle = capture()
                mutation(bundle)
                with self.assertRaises(ValueError):
                    validate_bundle(bundle, digest(encode(bundle)), IMAGE, REVISION, CONFIG)

    def test_symlinks_and_unexpected_paths_are_never_archived(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory/'t_demo--permit_one.bin').symlink_to('/etc/passwd')
            with self.assertRaisesRegex(ValueError, 'Unexpected'):
                export_files(directory)
        entries = capture()['attachments']
        entries.append(copy.deepcopy(entries[0]))
        with self.assertRaisesRegex(ValueError, 'path or metadata'):
            validate(entries)

    def test_invalid_capture_allocates_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            campaign = PermitCampaign(ROOT, Path(tmp)/'evidence', REVISION)
            self.addCleanup(shutil.rmtree, campaign.runtime.parent, True)
            campaign.image = IMAGE
            bundle = capture()
            bundle['writers']['runtime_login'] = 'enabled'
            with patch('run_permit_desk.prepare_fixture') as prepare, patch.object(campaign, 'command') as command:
                with self.assertRaises(ValueError):
                    campaign.install('forbidden', bundle, digest(encode(bundle)))
                prepare.assert_not_called()
                command.assert_not_called()
            self.assertEqual(campaign.stacks, {})

    def test_manifest_has_private_roles_and_distinct_volumes_without_secret_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)/'fixture'
            path = prepare_fixture(ROOT, runtime, IMAGE, REVISION, CONFIG)
            contents = path.read_text()
            manifest = json.loads(contents)
            self.assertEqual(manifest['volumes'], {'database': {}, 'attachments': {}})
            self.assertFalse(manifest['services']['postgres'].get('ports'))
            self.assertTrue(manifest['networks']['database']['internal'])
            app = manifest['services']['app']
            self.assertEqual(app['user'], '10001:10001')
            self.assertTrue(app['read_only'])
            self.assertEqual(app['cap_drop'], ['ALL'])
            self.assertEqual(app['ports'][0]['host_ip'], '127.0.0.1')
            mounted = {s['source'] for s in app['secrets']}
            self.assertNotIn('migrator-password', mounted)
            self.assertNotIn('backup-password', mounted)
            self.assertNotIn('ca.key', manifest['secrets'])
            for name in ('runtime-password', 'migrator-password', 'writer_a'):
                self.assertNotIn((runtime/'secrets'/name).read_text().strip(), contents)

    def test_configuration_and_payload_fail_closed(self):
        # Only import checks that do not access the database; actual authentication
        # and transaction assertions are executed by the real Compose campaign.
        spec = importlib.util.spec_from_file_location('fixture_app', ROOT/'scripts/p01/permit_desk/app.py')
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'psycopg': type(sys)('psycopg'), 'psycopg.rows': type(sys)('psycopg.rows')}):
            sys.modules['psycopg.rows'].dict_row = None
            spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'config.json'
            path.write_text(json.dumps(CONFIG))
            self.assertEqual(module.configuration(path), CONFIG)
            path.write_text(json.dumps({**CONFIG, 'native_writes': True}))
            with self.assertRaises(ValueError):
                module.configuration(path)
        good = {'permit_id': 'permit_one', 'title': 'Synthetic', 'attachment_base64': 'YWJj'}
        self.assertEqual(module.payload(encode(good)), ('permit_one', 'Synthetic', b'abc'))
        for changed in ({**good, 'tenant_id': 't_other'}, {**good, 'permit_id': '../escape'}, {**good, 'attachment_base64': 'invalid%'}):
            with self.assertRaises(ValueError):
                module.payload(encode(changed))


if __name__ == '__main__':
    unittest.main()
