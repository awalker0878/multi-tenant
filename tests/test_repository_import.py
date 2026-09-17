"""Tests of repository import and local Ansible logic; not Ansible engine tests."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from scripts import check_repository as repo
from scripts.catalog_artifacts import collect
from scripts import import_into_checkout as importer
from tools.verify_terraform import plan_only_mock_tests

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "hosting_filters_under_test", ROOT / "ansible/filter_plugins/hosting_filters.py")
filters = importlib.util.module_from_spec(spec)
spec.loader.exec_module(filters)


def fixture():
    return json.loads((ROOT / 'ansible/fixtures/reference_bundle.json').read_text())['hosting_bundle']


class TestAnsiblePureValidation(unittest.TestCase):
    def test_reference_fixture_preserves_non_authority(self):
        result = filters.validate_bundle(fixture())
        self.assertIs(result['may_apply'], False)
        self.assertIs(result['may_activate'], False)
        self.assertEqual(result['status'], 'STAGED_REFERENCE_NOT_QUALIFIED')

    def test_input_not_mutated(self):
        value = fixture(); before = copy.deepcopy(value)
        filters.validate_bundle(value)
        self.assertEqual(value, before)

    def test_wrong_purpose_rejected(self):
        value = fixture(); value['purpose'] = 'PRODUCTION'
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_unknown_field_rejected(self):
        value = fixture(); value['password'] = 'NOT-A-CREDENTIAL'
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_missing_field_rejected(self):
        value = fixture(); del value['attachment_cidr']
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_nonmapping_rejected(self):
        with self.assertRaises(ValueError): filters.validate_bundle([])

    def test_paths_not_labels(self):
        value = fixture(); value['tenant'] = '../tenant'
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_comma_cannot_inject_csv(self):
        value = fixture(); value['engineering_record_ref'] = 'ENG,OTHER'
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_unsupported_zone_rejected(self):
        value = fixture(); value['zone_class'] = 'MZ'
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_actual_address_rejected(self):
        value = fixture(); value['network_cidr'] = '10.20.0.0/24'
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_ipv6_not_silently_accepted(self):
        value = fixture(); value['network_cidr'] = '2001:db8::/64'
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_host_bits_rejected(self):
        value = fixture(); value['network_cidr'] = '192.0.2.1/27'
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_attachment_overlap_rejected(self):
        value = fixture(); value['attachment_cidr'] = '192.0.2.0/30'
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_nonusable_attachment_rejected(self):
        value = fixture(); value['attachment_cidr'] = '192.0.2.128/31'
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_empty_routes_rejected(self):
        value = fixture(); value['routes'] = []
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_duplicate_destination_rejected(self):
        value = fixture(); value['routes'] *= 2
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_competing_connected_destination_rejected(self):
        value = fixture(); value['routes'][0]['destination'] = value['network_cidr']
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_default_route_rejected(self):
        value = fixture(); value['routes'][0]['destination'] = '0.0.0.0/0'
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_offlink_next_hop_rejected(self):
        value = fixture(); value['routes'][0]['next_hop'] = '192.0.2.254'
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_network_address_hop_rejected(self):
        value = fixture(); value['routes'][0]['next_hop'] = '192.0.2.128'
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_broadcast_address_hop_rejected(self):
        value = fixture(); value['routes'][0]['next_hop'] = '192.0.2.131'
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_foreign_owner_rejected(self):
        value = fixture(); value['routes'][0]['owner'] = 'D02O'
        with self.assertRaises(ValueError): filters.validate_bundle(value)

    def test_missing_marker_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): filters.staging_directory(tmp, 'tenant-01', 'D01O')

    def test_valid_marker_and_scoped_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'.hosting-staging').write_text(filters.MARKER)
            self.assertEqual(Path(filters.staging_directory(tmp, 'tenant-01', 'D01O')).name,
                             'tenant-01--D01O')
            self.assertFalse((Path(tmp)/'tenant-01--D01O').exists())

    def test_relative_root_rejected(self):
        with self.assertRaises(ValueError): filters.staging_directory('relative', 'tenant-01', 'D01O')

    def test_symlink_root_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'real'; target.mkdir(); (target/'.hosting-staging').write_text(filters.MARKER)
            link=Path(tmp)/'link'; link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(ValueError): filters.staging_directory(str(link), 'tenant-01', 'D01O')

    def test_symlink_output_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'.hosting-staging').write_text(filters.MARKER)
            out=root/'tenant-01--D01O'; out.mkdir(); (out/'routes.csv').symlink_to(root/'outside')
            with self.assertRaises(ValueError): filters.staging_directory(tmp, 'tenant-01', 'D01O')

    def test_pure_template_render_deterministic(self):
        env=Environment(loader=FileSystemLoader(ROOT/'ansible/roles/configuration_bundle/templates'),
                        undefined=StrictUndefined, keep_trailing_newline=True)
        env.filters['to_nice_json']=lambda value: json.dumps(value, indent=4, sort_keys=True)
        value=filters.validate_bundle(fixture())
        first=env.get_template('engineering-handoff.json.j2').render(hosting_normalized=value)
        second=env.get_template('engineering-handoff.json.j2').render(hosting_normalized=value)
        self.assertEqual(first,second)
        self.assertFalse(json.loads(first)['may_activate'])
        csv=env.get_template('routes.csv.j2').render(hosting_normalized=value)
        self.assertIn('192.0.2.32/27',csv)
        self.assertEqual(len(csv.strip().splitlines()),2)

    def test_opt_out_is_default(self):
        defaults=yaml.safe_load((ROOT/'ansible/roles/configuration_bundle/defaults/main.yml').read_text())
        self.assertIs(defaults['hosting_stage_enabled'],False)

    def test_all_playbooks_localhost_no_privilege_escalation(self):
        for path in (ROOT/'ansible/playbooks').glob('*.yml'):
            for play in yaml.safe_load(path.read_text()):
                self.assertEqual(play['hosts'],'localhost')
                self.assertEqual(play['connection'],'local')
                self.assertIs(play['become'],False)

    def test_no_native_contact_or_shell_in_new_tasks(self):
        for path in (ROOT/'ansible/roles').glob('*/tasks/main.yml'):
            text=path.read_text()
            self.assertNotIn('--read-authorized-target',text)
            self.assertNotIn('--execute-approved-change',text)
            self.assertNotIn('ansible.builtin.shell',text)


class TestTerraformMockGuard(unittest.TestCase):
    def guard(self, text, alternate_json=False):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'tests').mkdir()
            (root/'main.tf.json').write_text(json.dumps({'terraform':{'required_providers':{'demo':{}}}}))
            (root/'tests/mock.tftest.hcl').write_text(text)
            if alternate_json: (root/'tests/extra.tftest.json').write_text('{}')
            return plan_only_mock_tests(root)

    def test_explicit_mock_plan_passes(self):
        self.assertTrue(self.guard('mock_provider "demo" {}\nrun "a" { command = plan }'))

    def test_real_provider_refused(self):
        self.assertFalse(self.guard('mock_provider "demo" {}\nprovider "demo" {}\nrun "a" { command = plan }'))

    def test_missing_mock_refused(self):
        self.assertFalse(self.guard('run "a" { command = plan }'))

    def test_apply_refused(self):
        self.assertFalse(self.guard('mock_provider "demo" {}\nrun "a" { command = apply }'))

    def test_implicit_apply_refused(self):
        self.assertFalse(self.guard('mock_provider "demo" {}\nrun "a" {}'))

    def test_module_override_refused(self):
        self.assertFalse(self.guard('mock_provider "demo" {}\nrun "a" { command = plan module { source = "other" } }'))

    def test_provider_remap_refused(self):
        self.assertFalse(self.guard('mock_provider "demo" {}\nrun "a" { command = plan providers = { demo = demo.real } }'))

    def test_commented_mock_cannot_satisfy_guard(self):
        self.assertFalse(self.guard('# mock_provider "demo" {}\nrun "a" { command = plan }'))

    def test_block_comment_command_cannot_satisfy_guard(self):
        self.assertFalse(self.guard('mock_provider "demo" {}\nrun "a" { /* command = plan */ }'))

    def test_comment_cannot_change_run_count(self):
        self.assertTrue(self.guard('mock_provider "demo" {}\n# run "b" {}\nrun "a" { command = plan }'))

    def test_alternate_json_tests_refused(self):
        self.assertFalse(self.guard('mock_provider "demo" {}\nrun "a" { command = plan }',True))

    def test_shipped_ten_profiles_pass_guard(self):
        modules=list((ROOT/'terraform/modules').glob('*/main.tf.json'))
        self.assertEqual(len(modules),10)
        for path in modules:self.assertTrue(plan_only_mock_tests(path.parent),path.parent.name)


class TestRepositoryPolicy(unittest.TestCase):
    def test_yaml_duplicate_keys_rejected(self):
        with self.assertRaises(ValueError):yaml.load('item: 1\nitem: 2',Loader=repo.UniqueLoader)

    def test_doc_catalogue_matches_actual_files(self):
        rows=json.loads((ROOT/'sources/artifact_catalog.json').read_text())
        self.assertEqual(rows,collect(ROOT))
        self.assertEqual(len(rows),27)

    def test_no_secret_flag_from_header_only(self):
        self.assertFalse(repo.high_confidence_secret('-----BEGIN PRIVATE KEY-----'))

    def test_secret_body_is_flagged(self):
        # Construct synthetic data in memory, not a real key and not a key in source.
        value='-----BEGIN '+'PRIVATE KEY-----\n'+'A'*90
        self.assertTrue(repo.high_confidence_secret(value))

    def test_state_and_live_values_forbidden(self):
        for path in ('terraform/main.tfstate','terraform/dev.tfvars.json','private/site.json'):
            self.assertTrue(repo.forbidden_path(Path(path)))

    def test_examples_and_actual_lock_are_allowed(self):
        for path in ('terraform/inputs.tfvars.json.example','terraform/.terraform.lock.hcl'):
            self.assertFalse(repo.forbidden_path(Path(path)))

    def test_workflow_tokens_are_not_credentials(self):
        for path in (ROOT/'.github/workflows').glob('*.yml'):
            doc=yaml.load(path.read_text(),Loader=yaml.BaseLoader)
            self.assertEqual(doc['permissions'],{'contents':'read'})
            self.assertNotIn('pull_request_target',doc['on'])
            for job in doc['jobs'].values():
                self.assertEqual(job['runs-on'],'ubuntu-24.04')
                self.assertNotIn('continue-on-error',job)
                for step in job['steps']:
                    if 'uses' in step:self.assertRegex(step['uses'],r'@[0-9a-f]{40}$')
                    self.assertNotIn('secrets.',step.get('run',''))

    def test_git_stage_preserves_frozen_csv_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'.gitattributes').write_bytes((ROOT/'.gitattributes').read_bytes())
            original = b'identity,value\r\nfixture,123\r\n'
            (root/'reference').mkdir()
            (root/'reference/fixture.csv').write_bytes(original)
            for command in (['git', 'init', '-q', str(root)],
                            ['git', '-C', str(root), 'add', '.']):
                result = subprocess.run(command, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run(['git', '-C', str(root), 'show', ':reference/fixture.csv'],
                                    capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, original)

    def test_native_engine_missing_is_blocked(self):
        # Actual blocked CLI runs are recorded separately; require code to fail gates.
        for path in ('scripts/verify_ansible.py','tools/verify_terraform.py'):
            text=(ROOT/path).read_text()
            self.assertIn('BLOCKED_TOOLCHAIN',text)
            self.assertNotIn('continue-on-error',text)


class TestImportPreflight(unittest.TestCase):
    def _case(self, changes=None, collision=False, symlink=False):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); src=root/'source';dst=root/'checkout';src.mkdir();dst.mkdir()
            (src/'sources').mkdir();(src/'evidence/imported').mkdir(parents=True)
            (src/'README.md').write_text('new\n')
            (src/'evidence/imported/github-initial-README.md').write_text('old\n')
            (src/'sources/release_manifest.json').write_text(json.dumps({'file_sha256':{'README.md':importer.sha(src/'README.md')}}))
            (dst/'README.md').write_text('other\n' if collision else 'old\n')
            if symlink:
                (dst/'README.md').unlink();(dst/'README.md').symlink_to(root/'outside')
            answers={('rev-parse','--show-toplevel'):str(dst),('remote','get-url','origin'):'git@github.com:awalker0878/multi-tenant.git',('branch','--show-current'):'main',('status','--porcelain','--untracked-files=all'):''}
            answers.update(changes or {})
            with patch.object(importer,'git',side_effect=lambda path,*args: answers[args]),patch.object(importer,'verify',return_value={'issues':[]}):
                return importer.plan(dst,src)

    def test_exact_initial_readme_is_only_overwrite(self):
        result=self._case();self.assertEqual(next(r for r in result if r['path']=='README.md')['action'],'REPLACE_INITIAL_README')

    def test_unknown_collision_refused(self):
        with self.assertRaises(ValueError):self._case(collision=True)

    def test_dirty_checkout_refused(self):
        with self.assertRaises(ValueError):self._case({('status','--porcelain','--untracked-files=all'):' M README.md'})

    def test_wrong_origin_refused(self):
        with self.assertRaises(ValueError):self._case({('remote','get-url','origin'):'git@github.com:other/repo.git'})

    def test_nonmain_refused(self):
        with self.assertRaises(ValueError):self._case({('branch','--show-current'):'different'})

    def test_symlink_collision_refused(self):
        with self.assertRaises(ValueError):self._case(symlink=True)


if __name__ == '__main__':unittest.main()
