"""Planning-kit checks only. No native platform or completed evidence is exercised."""
from __future__ import annotations
import ast
from contextlib import redirect_stdout
import hashlib
import sys
import copy
import csv
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import commissioning_pack as pack

ROOT = Path(__file__).resolve().parents[1]


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT / pack.PLAN).read_text())

    def reject(self, mutation):
        candidate = copy.deepcopy(self.plan)
        mutation(candidate)
        with self.assertRaises(ValueError):
            pack.validate(candidate)

    def test_complete_planning_shape(self):
        pack.validate(self.plan)

    def test_real_source_associations(self):
        plan, original, report = pack.inspect(ROOT)
        self.assertEqual(set(original), pack.IDS)
        self.assertEqual(report['status'], 'PLANNING_PACKAGE_CONSISTENT_NOT_EXECUTED')
        for flag in ('may_apply', 'may_delete', 'may_activate'):
            self.assertIs(report[flag], False)
        self.assertEqual(report['inputs'], len(plan['inputs']))

    def test_unknown_top_level(self):
        self.reject(lambda p: p.update(secret='not-permitted'))

    def test_not_a_result(self):
        self.reject(lambda p: p.update(status='PASSED_NATIVE'))

    def test_unpinned_basis(self):
        self.reject(lambda p: p.update(basis_commit='main'))

    def test_no_public_exposure(self):
        self.reject(lambda p: p['scope'].update(public_ingress=True))

    def test_boolean_zero_not_false(self):
        self.reject(lambda p: p['scope'].update(internet_egress=0))

    def test_no_selected_platform(self):
        self.reject(lambda p: p['scope'].update(platform='installed-product'))

    def test_no_authority_status(self):
        self.reject(lambda p: p['scope'].update(production_authority='APPROVED'))

    def test_no_unverified_family_offer(self):
        self.reject(lambda p: p['scope'].update(families='DUAL_STACK_QUALIFIED'))

    def test_duplicate_input(self):
        self.reject(lambda p: p['inputs'].append(copy.deepcopy(p['inputs'][0])))

    def test_empty_owner(self):
        self.reject(lambda p: p['inputs'][0].update(owner_role=''))

    def test_unknown_input_source(self):
        self.reject(lambda p: p['inputs'][0].update(source_refs=['other.md']))

    def test_unreferenced_question(self):
        def change(p):
            new = copy.deepcopy(p['inputs'][0]); new['id'] = 'UNREFERENCED'; p['inputs'].append(new)
        self.reject(change)

    def test_duplicate_package(self):
        self.reject(lambda p: p['work_packages'].append(copy.deepcopy(p['work_packages'][0])))

    def test_unknown_input(self):
        self.reject(lambda p: p['work_packages'][0].update(input_refs=['MISSING']))

    def test_dependency_cycle(self):
        self.reject(lambda p: p['work_packages'][0].update(depends_on=['NC90']))

    def test_unknown_dependency(self):
        self.reject(lambda p: p['work_packages'][1].update(depends_on=['NC99']))

    def test_duplicate_dependency(self):
        self.reject(lambda p: p['work_packages'][1].update(depends_on=['NC00', 'NC00']))

    def test_unknown_source_stage(self):
        self.reject(lambda p: p['work_packages'][0].update(source_stage='B14-99'))

    def test_missing_original_phase(self):
        self.reject(lambda p: [s.update(source_stage='B14-07') for s in p['work_packages'] if s['source_stage']=='B14-08'])

    def test_unknown_owner_package(self):
        self.reject(lambda p: p['work_packages'][0].update(packages=['P99']))

    def test_initial_readiness_cannot_be_later_recurring(self):
        self.reject(lambda p: next(s for s in p['work_packages'] if s['id']=='NC70').update(packages=['G4-recurring']))

    def test_production_requires_initial_readiness_dependency(self):
        self.reject(lambda p: next(s for s in p['work_packages'] if s['id']=='NC80').update(depends_on=['NC60']))

    def test_first_qualification_not_circular(self):
        self.reject(lambda p: p['work_packages'][3]['packages'].append('G2'))

    def test_missing_observation(self):
        self.reject(lambda p: p['observations'].pop())

    def test_duplicate_observation(self):
        self.reject(lambda p: p['observations'].append(copy.deepcopy(p['observations'][0])))

    def test_cleanup_independent_of_production(self):
        self.reject(lambda p: p.update(cleanup_step='NC90'))

    def test_cleanup_requires_owned_lifecycle_step(self):
        self.reject(lambda p: p.update(cleanup_step='NC00'))

    def test_cleanup_not_dependent_on_qualification(self):
        self.reject(lambda p: next(s for s in p['work_packages'] if s['id']=='NC55').update(depends_on=['NC60']))

    def test_unknown_observation(self):
        self.reject(lambda p: p['observations'][0].update(assertion_id='CT-001'))

    def test_no_native_pass_in_plan(self):
        self.reject(lambda p: p['observations'][0].update(execution_status='PASSED'))

    def test_no_negative_claim_without_control(self):
        self.reject(lambda p: p['observations'][0].update(control=''))

    def test_no_missing_safe_stop(self):
        self.reject(lambda p: p['observations'][0].update(safe_stop=''))

    def test_control_characters_rejected(self):
        self.reject(lambda p: p['inputs'][0].update(question='hello\x00bad'))

    def test_g1_acceptance_marker_cannot_disappear(self):
        self.reject(lambda p: next(s for s in p['work_packages'] if s['id']=='NC20').update(packages=['P1']))

    def test_g3_review_marker_cannot_disappear(self):
        self.reject(lambda p: next(s for s in p['work_packages'] if s['id']=='NC80').update(packages=['P4', 'P5']))

    def test_g2_marker_must_remain_in_source_stage(self):
        self.reject(lambda p: next(s for s in p['work_packages'] if s['id']=='NC60').update(packages=['P2']))

    def test_denied_domain_preparation_cannot_disappear(self):
        self.reject(lambda p: next(s for s in p['work_packages'] if s['id']=='NC40').update(packages=['P0']))

    def test_disposable_workload_preparation_cannot_disappear(self):
        self.reject(lambda p: next(s for s in p['work_packages'] if s['id']=='NC50').update(packages=['P4']))

    def test_cleanup_needs_scope_and_owner_review(self):
        self.reject(lambda p: next(s for s in p['work_packages'] if s['id']=='NC55').update(depends_on=[]))

    def test_cleanup_not_held_behind_domain_preparation(self):
        self.reject(lambda p: next(s for s in p['work_packages'] if s['id']=='NC55').update(depends_on=['NC40']))

    def test_cleanup_not_held_behind_platform_installation(self):
        self.reject(lambda p: next(s for s in p['work_packages'] if s['id']=='NC55').update(depends_on=['NC30']))


class SourceTests(unittest.TestCase):
    def test_json_duplicate_property(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'duplicate.json'; p.write_text('{"same":1,"same":2}')
            with self.assertRaises(ValueError): pack.load_json(p)

    def test_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'invalid.json'; p.write_text('{"value":NaN}')
            with self.assertRaises(ValueError): pack.load_json(p)

    def test_root_array_is_not_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'invalid.json'; p.write_text('[]')
            with self.assertRaises(ValueError): pack.load_json(p)

    def test_size_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'large.json'; p.write_bytes(b' ' * (pack.MAX_BYTES + 1))
            with self.assertRaises(ValueError): pack.load_json(p)

    def test_source_traversal_and_urls(self):
        for relative in ('../outside', '/tmp/file', 'a/../b', 'a\\b', 'https://example.invalid/a', '.git/config'):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                pack.safe_source(ROOT, relative)

    def test_source_missing(self):
        with self.assertRaises(ValueError): pack.safe_source(ROOT, 'missing-commissioning-source.json')

    def test_source_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp); (r / 'real').write_text('fixture'); (r / 'alias').symlink_to(r / 'real')
            with self.assertRaises(ValueError): pack.safe_source(r, 'alias')

    def test_mutated_original_association_rejected(self):
        plan = json.loads((ROOT / pack.PLAN).read_text())
        families, raw = pack.load_json(ROOT / pack.FAMILIES)
        candidate = copy.deepcopy(families)
        row = next(r for r in candidate['supplemental_mappings'] if r['family'] == 'W14')
        row['original_record']['mapped_procedures_and_status'] = 'CT-080 / NOT RUN'
        with patch.object(pack, 'load_json', return_value=(candidate, raw)), self.assertRaises(ValueError):
            pack.sources(ROOT, plan)

    def test_qualified_source_record_cannot_be_reused_as_unrun_spec(self):
        plan = json.loads((ROOT / pack.PLAN).read_text())
        families, raw = pack.load_json(ROOT / pack.FAMILIES)
        candidate = copy.deepcopy(families)
        next(r for r in candidate['supplemental_mappings'] if r['family'] == 'W14')['execution_status'] = 'passed'
        with patch.object(pack, 'load_json', return_value=(candidate, raw)), self.assertRaises(ValueError):
            pack.sources(ROOT, plan)

    def test_only_standard_library_no_execution_or_network_module(self):
        tree = ast.parse((ROOT / 'scripts/commissioning_pack.py').read_text())
        names = {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        names |= {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertFalse(names & {'subprocess', 'socket', 'urllib', 'http', 'requests', 'ansible'})


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan, cls.originals, cls.report = pack.inspect(ROOT)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name); self.destination = self.parent / 'new-campaign'
        self.payloads = pack.worksheets(self.plan, self.originals)

    def test_deterministic_worksheets(self):
        self.assertEqual(self.payloads, pack.worksheets(self.plan, self.originals))

    def test_source_assertion_and_procedure_retained(self):
        rows = list(csv.DictReader(io.StringIO(self.payloads['observation-attempts.csv'].decode())))
        self.assertEqual(len(rows), 12)
        for row in rows:
            original = self.originals[row['assertion_id']]
            self.assertEqual(row['original_observation'], original['observation'])
            self.assertEqual(row['original_procedures'], original['mapped_procedures_and_status'])
            self.assertEqual(row['result'], 'NOT_RUN')
            for field in ('attempt_id', 'platform_tuple_ref', 'family', 'artifact_ref', 'reviewer', 'control_result_ref'):
                self.assertEqual(row[field], '')
            self.assertNotIn(None, row)

    def test_every_csv_row_has_correct_width(self):
        for data in self.payloads.values():
            rows = list(csv.reader(io.StringIO(data.decode())))
            self.assertTrue(all(len(row) == len(rows[0]) for row in rows))

    def test_review_inputs_start_unreviewed(self):
        rows = list(csv.DictReader(io.StringIO(self.payloads['engineering-inputs.csv'].decode())))
        self.assertTrue(all(r['review_state'] == 'UNREVIEWED' and r['controlled_record_reference'] == '' for r in rows))

    def test_output_is_new_private_and_not_authority(self):
        pack.write_new(self.destination, self.payloads, self.report)
        manifest = json.loads((self.destination / 'manifest.json').read_text())
        self.assertEqual(manifest['status'], 'DRAFT_ONLY_NOT_EVIDENCE')
        self.assertEqual(manifest['native_execution'], 'NOT_RUN')
        self.assertEqual(manifest['authority'], 'NOT_ASSESSED')
        for flag in ('may_apply', 'may_delete', 'may_activate'): self.assertIs(manifest[flag], False)
        self.assertEqual(self.destination.stat().st_mode & 0o777, 0o700)
        for p in self.destination.iterdir(): self.assertEqual(p.stat().st_mode & 0o777, 0o600)
        for name, data in self.payloads.items(): self.assertEqual(manifest['file_sha256'][name], pack.digest(data))

    def test_existing_output_not_overwritten(self):
        self.destination.mkdir(); (self.destination / 'manifest.json').write_text('keep')
        with self.assertRaises(FileExistsError): pack.write_new(self.destination, self.payloads, self.report)
        self.assertEqual((self.destination / 'manifest.json').read_text(), 'keep')

    def test_relative_output_rejected(self):
        with self.assertRaises(ValueError): pack.write_new(Path('relative'), self.payloads, self.report)

    def test_output_inside_repository_rejected(self):
        with self.assertRaises(ValueError): pack.write_new(ROOT / 'unfilled-test-output', self.payloads, self.report)

    def test_symlink_parent_rejected(self):
        link = self.parent / 'alias'; link.symlink_to(self.parent, target_is_directory=True)
        with self.assertRaises(ValueError): pack.write_new(link / 'draft', self.payloads, self.report)

    def test_missing_parent_not_created(self):
        target = self.parent / 'missing' / 'draft'
        with self.assertRaises(ValueError): pack.write_new(target, self.payloads, self.report)
        self.assertFalse(target.parent.exists())

    def test_unexpected_output_set_rejected(self):
        self.payloads['../escape'] = b'bad'
        with self.assertRaises(ValueError): pack.write_new(self.destination, self.payloads, self.report)
        self.assertFalse(self.destination.exists())

    def test_csv_formula_safety(self):
        for value in ('=SUM(A1)', ' +1', '-DDE', '@command'):
            self.assertTrue(pack.cell(value).startswith("'"))
        self.assertEqual(pack.cell('Ordinary source text'), 'Ordinary source text')

    def test_interrupted_export_stays_incomplete(self):
        real = os.open
        def fail_on_worksheet(path, flags, mode=0o777):
            if str(path).endswith('work-package-runs.csv'): raise OSError('synthetic disk failure')
            return real(path, flags, mode)
        with patch.object(pack.os, 'open', side_effect=fail_on_worksheet), self.assertRaises(OSError):
            pack.write_new(self.destination, self.payloads, self.report)
        self.assertEqual(json.loads((self.destination / 'manifest.json').read_text())['status'], 'STARTED_INCOMPLETE')


class IntegrationTests(unittest.TestCase):
    def test_actual_output_dimensions_are_explicit_and_unfilled(self):
        plan, originals, _ = pack.inspect(ROOT)
        payload = pack.worksheets(plan, originals)['observation-attempts.csv']
        rows = list(csv.DictReader(io.StringIO(payload.decode())))
        for key in ('direction', 'operation', 'observer_identity_ref'):
            self.assertIn(key, pack.ACTUAL_OBSERVATION_FIELDS)
        for row in rows:
            for key in pack.ACTUAL_OBSERVATION_FIELDS:
                self.assertEqual(row[key], '')
            self.assertEqual(row['result'], 'NOT_RUN')

    def test_report_identifies_actual_exporter_bytes(self):
        _, _, report = pack.inspect(ROOT)
        self.assertEqual(report['exporter_sha256'], hashlib.sha256((ROOT/'scripts/commissioning_pack.py').read_bytes()).hexdigest())

    def test_export_manifest_retains_exporter_identity(self):
        plan, originals, report = pack.inspect(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'new'
            pack.write_new(target, pack.worksheets(plan, originals), report)
            self.assertEqual(json.loads((target/'manifest.json').read_text())['exporter_sha256'], report['exporter_sha256'])

    def navigation(self):
        from scripts.check_documentation import Builder
        builder = Builder(ROOT)
        captured = {}
        with patch.object(builder, 'write', side_effect=lambda name, text: captured.update({name:text.rstrip()+'\n'})):
            builder.navigation()
        return captured

    def test_generated_implementation_navigation_matches(self):
        self.assertEqual(self.navigation()['docs/implementation/README.md'], (ROOT/'docs/implementation/README.md').read_text())

    def test_generated_engineering_navigation_preserves_ipv6(self):
        self.assertEqual(self.navigation()['docs/engineering/README.md'], (ROOT/'docs/engineering/README.md').read_text())

    def test_generated_navigation_keeps_both_work_packages(self):
        actual = self.navigation()['docs/implementation/README.md']
        self.assertIn('routed-ipv6-lab.md', actual)
        self.assertIn('native-reference/README.md', actual)

    def test_native_plan_does_not_reuse_packet_results(self):
        plan, _, _ = pack.inspect(ROOT)
        self.assertIn('docs/engineering/routed-ipv6-qualification.md', plan['source_refs'])
        self.assertTrue(all(row['execution_status']=='NOT_RUN' for row in plan['observations']))
        self.assertEqual(plan['scope']['families'], 'SELECT_AT_SITE_REVIEW')

    def test_check_cli_never_opens_a_write_descriptor(self):
        with patch.object(sys, 'argv', ['commissioning_pack.py', 'check']), patch.object(pack.os, 'open') as opened, redirect_stdout(io.StringIO()):
            self.assertEqual(pack.main(), 0)
        opened.assert_not_called()

    def test_draft_cli_and_exclusive_second_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'new'
            with patch.object(sys, 'argv', ['commissioning_pack.py', 'draft', '--output', str(target)]), redirect_stdout(io.StringIO()):
                self.assertEqual(pack.main(), 0)
                before = {p.name:p.read_bytes() for p in target.iterdir()}
                self.assertEqual(pack.main(), 2)
            self.assertEqual(before, {p.name:p.read_bytes() for p in target.iterdir()})
            manifest=json.loads(before['manifest.json'])
            self.assertEqual(manifest['status'], 'DRAFT_ONLY_NOT_EVIDENCE')
            for key in ('may_apply', 'may_delete', 'may_activate'):
                self.assertIs(manifest[key], False)


if __name__ == '__main__':
    unittest.main()
