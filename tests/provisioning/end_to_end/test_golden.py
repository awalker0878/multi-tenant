"""Golden path: every reviewed reference request reproduces its stored artifacts."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import canonical_json, digest

from tests.provisioning import support

RESOLVED = support.RESOLVED
GOLDEN = support.GOLDEN
BRITTLE = ('timestamp', 'created_at', 'generated_at', 'T00:', 'T12:')


def load(directory: Path, name: str) -> dict:
    return json.loads((directory / name).read_text(encoding='utf-8'))


def request_keys(document: dict) -> set:
    """Every key the request document names, at any depth."""
    seen: set = set()

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                seen.add(key)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(document)
    return seen


class GoldenCorpusTest(unittest.TestCase):
    """The corpus itself must stay a reviewed, self-consistent set of examples."""

    def test_the_corpus_covers_the_required_reference_requests(self):
        self.assertEqual(support.REFERENCE_REQUESTS,
                         ('internal-development', 'internal-production', 'multi-tier',
                          'recovery-enabled', 'storage-heavy'))
        for name in support.REFERENCE_REQUESTS:
            self.assertTrue(support.request_path(name).exists(), name)

    def test_every_request_resolves_to_a_disabled_plan(self):
        index = load(GOLDEN, 'digests.json')['subjects']
        self.assertEqual(sorted(index), sorted(support.REFERENCE_REQUESTS))
        for name in support.REFERENCE_REQUESTS:
            plan = support.reference_plan(name)
            self.assertEqual(plan.status, 'PLANNED_DISABLED_NOT_AUTHORIZED', name)
            self.assertIs(plan.native_contact, False, name)
            self.assertEqual(plan.request.tenant, 'tenant-01', name)

    def test_the_corpus_uses_only_implemented_profiles(self):
        catalog = support.catalogs()
        for name in support.REFERENCE_REQUESTS:
            resolution = support.reference_plan(name).resolution
            for family, profile in resolution.profiles.items():
                if family == 'services':
                    pairs = [(service, value) for service, value in sorted(profile.items())]
                elif profile is None:
                    continue
                else:
                    pairs = [(family, profile)]
                for scope, value in pairs:
                    entry = catalog.get('service' if family == 'services' else family, value)
                    self.assertEqual(entry.status, 'IMPLEMENTED_INTERNAL_IPV4_OZ_RZ',
                                     f'{name}: {scope}/{value}')

    def test_no_golden_artifact_carries_a_brittle_field(self):
        for directory in (RESOLVED, GOLDEN):
            for path in sorted(directory.glob('*.json')):
                text = path.read_text(encoding='utf-8')
                for brittle in BRITTLE:
                    self.assertNotIn(brittle, text, f'{path.name} contains {brittle}')

    def test_no_golden_artifact_claims_native_contact(self):
        for directory in (RESOLVED, GOLDEN):
            for path in sorted(directory.glob('*.json')):
                payload = json.loads(path.read_text(encoding='utf-8'))
                self.assertIsNot(payload.get('native_contact'), True, path.name)

    def test_the_corpus_records_the_reviewed_catalog_revisions(self):
        catalog = support.catalogs()
        for name, index in (('digests.json', load(GOLDEN, 'digests.json')),
                            ('cross-platform.digests.json',
                             load(GOLDEN, 'cross-platform.digests.json'))):
            with self.subTest(index=name):
                self.assertEqual(index['catalogs']['versions'], catalog.versions)
                self.assertEqual(index['catalogs']['digest'], catalog.digest)

    def test_every_resolution_artifact_states_its_reviewed_revision_set(self):
        catalog = support.catalogs()
        for name in support.REFERENCE_REQUESTS:
            with self.subTest(request=name):
                payload = load(RESOLVED, f'{name}.resolution.json')
                self.assertEqual(payload['format'], 'hosting-resolved-profile-set/2')
                self.assertEqual(payload['catalog_versions'], catalog.versions)
                self.assertEqual(payload['catalog_digest'], catalog.digest)
                for family, profile in sorted(payload['profiles'].items()):
                    if family == 'services' or profile is None:
                        continue
                    self.assertEqual(payload['profile_versions'][family],
                                     catalog.get(family, profile).version)


class GoldenReplayTest(unittest.TestCase):
    """Recomputing a reference request must reproduce every stored artifact byte for byte."""

    def test_resolved_profile_sets_are_reproduced(self):
        for name in support.REFERENCE_REQUESTS:
            with self.subTest(request=name):
                plan = support.reference_plan(name)
                expected = load(RESOLVED, f'{name}.resolution.json')
                self.assertEqual(expected['profiles'], dict(plan.resolution.profiles))
                self.assertEqual(expected['profile_versions'],
                                 dict(plan.resolution.profile_versions))
                self.assertEqual(expected['catalog_versions'],
                                 dict(plan.resolution.catalog_versions))
                self.assertEqual(expected['catalog_digest'], plan.resolution.catalog_digest)
                self.assertEqual(expected['request_digest'], plan.request.digest)
                self.assertEqual(expected['policy'], dict(plan.policy))
                self.assertEqual(expected['services'], dict(plan.resolution.services))
                self.assertEqual(expected['required_capabilities'],
                                 list(plan.resolution.required_capabilities))

    def test_placement_decisions_are_reproduced(self):
        for name in support.REFERENCE_REQUESTS:
            with self.subTest(request=name):
                plan = support.reference_plan(name)
                expected = load(RESOLVED, f'{name}.placement.json')
                self.assertEqual(canonical_json(expected),
                                 canonical_json(plan.decision.to_dict()))

    def test_desired_states_are_reproduced(self):
        for name in support.REFERENCE_REQUESTS:
            with self.subTest(request=name):
                plan = support.reference_plan(name)
                expected = load(RESOLVED, f'{name}.desired-state.json')
                self.assertEqual(canonical_json(expected),
                                 canonical_json(plan.desired_state.to_dict()))

    def test_environments_are_reproduced(self):
        for name in support.REFERENCE_REQUESTS:
            with self.subTest(request=name):
                plan = support.reference_plan(name)
                expected = load(GOLDEN, f'{name}.environment.json')
                self.assertEqual(canonical_json(expected), canonical_json(plan.environment))

    def test_conformance_reports_are_reproduced(self):
        for name in support.REFERENCE_REQUESTS:
            with self.subTest(request=name):
                plan = support.reference_plan(name)
                expected = load(GOLDEN, f'{name}.conformance.json')
                self.assertEqual(canonical_json(expected), canonical_json(plan.conformance))

    def test_the_digest_index_is_reproduced(self):
        index = load(GOLDEN, 'digests.json')['subjects']
        for name in support.REFERENCE_REQUESTS:
            with self.subTest(request=name):
                plan = support.reference_plan(name)
                expected = index[name]
                self.assertEqual(expected['request_digest'], plan.request.digest)
                self.assertEqual(expected['plan_digest'], plan.digest)
                self.assertEqual(expected['manifest_digest'], plan.manifest_digest)
                self.assertEqual(expected['resolution_digest'],
                                 digest(plan.resolution.to_dict()))
                self.assertEqual(expected['placement_digest'], plan.decision.digest)
                self.assertEqual(expected['desired_state_digest'], plan.desired_state.digest)
                self.assertEqual(expected['environment_digest'], digest(plan.environment))
                self.assertEqual(expected['conformance_digest'], digest(plan.conformance))
                self.assertEqual(expected['compiled_files'], sorted(plan.compiled))
                self.assertEqual(expected['status'], plan.status)

    def test_distinct_requests_produce_distinct_plans(self):
        digests = {name: support.reference_plan(name).digest
                   for name in support.REFERENCE_REQUESTS}
        self.assertEqual(len(set(digests.values())), len(digests))


class CrossPlatformGoldenTest(unittest.TestCase):
    """The full reference-request x platform matrix, with no cell omitted."""

    def corpus(self) -> dict:
        return load(GOLDEN, 'cross-platform.digests.json')

    def requests(self) -> dict:
        return self.corpus()['requests']

    def test_the_corpus_covers_every_request_and_every_platform(self):
        corpus = self.corpus()
        self.assertEqual(corpus['format'], 'hosting-golden-cross-platform/2')
        self.assertIs(corpus['native_contact'], False)
        self.assertEqual(sorted(corpus['fixtures']), sorted(support.REFERENCE_FIXTURES))
        self.assertEqual(sorted(self.requests()), sorted(support.REFERENCE_REQUESTS))
        for name, entry in sorted(self.requests().items()):
            with self.subTest(request=name):
                self.assertEqual(entry['request'], f'examples/requests/{name}.yaml')
                self.assertEqual(sorted(entry['platforms']), sorted(support.PLATFORMS))
                self.assertEqual(sorted({row['fixture'] for row in entry['refusals']}),
                                 sorted(support.PLATFORMS))

    def test_every_platform_is_asked_the_same_portable_question(self):
        digests_seen: set = set()
        for name, entry in sorted(self.requests().items()):
            with self.subTest(request=name):
                portable = support.portable_request(name)
                self.assertEqual(entry['portable_digest'], digest(portable))
                digests_seen.add(entry['portable_digest'])
                for platform in sorted(support.PLATFORMS):
                    expected = copy.deepcopy(portable)
                    expected['spec']['platform']['preference'] = platform
                    self.assertEqual(support.platform_request(platform, name), expected)
        self.assertEqual(len(digests_seen), len(support.REFERENCE_REQUESTS))

    def test_every_cell_reproduces_its_stored_digests(self):
        for name, entry in sorted(self.requests().items()):
            for platform, expected in sorted(entry['platforms'].items()):
                with self.subTest(request=name, platform=platform):
                    plan = support.platform_plan(platform, name)
                    self.assertEqual(expected['request_digest'], plan.request.digest)
                    self.assertEqual(expected['resolution_digest'],
                                     digest(plan.resolution.to_dict()))
                    self.assertEqual(expected['placement_digest'], plan.decision.digest)
                    self.assertEqual(expected['desired_state_digest'],
                                     plan.desired_state.digest)
                    self.assertEqual(expected['environment_digest'], digest(plan.environment))
                    self.assertEqual(expected['plan_digest'], plan.digest)
                    self.assertEqual(expected['manifest_digest'], plan.manifest_digest)

    def test_every_cell_records_its_provider_native_realization_root(self):
        for name, entry in sorted(self.requests().items()):
            for platform, expected in sorted(entry['platforms'].items()):
                with self.subTest(request=name, platform=platform):
                    plan = support.platform_plan(platform, name)
                    self.assertEqual(plan.desired_state.platform, platform)
                    root = f'terraform/stacks/wsd/{platform}/domains'
                    self.assertEqual(expected['stack_roots'], [root])
                    self.assertEqual(expected['stack_roots'],
                                     sorted({scope['root'] for scope in plan.terraform_scopes}))
                    self.assertEqual(expected['compiled_files'], sorted(plan.compiled))
                    for other in support.PLATFORMS:
                        if other != platform:
                            self.assertNotIn(f'/{other}/', root)

    def test_no_matrix_input_carries_a_provider_native_field(self):
        native: set = set()
        for platform in sorted(support.PLATFORMS):
            native |= support.native_field_names(platform)
        for name in sorted(self.requests()):
            for platform in sorted(support.PLATFORMS):
                with self.subTest(request=name, platform=platform):
                    keys = request_keys(support.platform_request(platform, name))
                    self.assertEqual(sorted(keys & native), [])
        text = (GOLDEN / 'cross-platform.digests.json').read_text(encoding='utf-8')
        for field in sorted(native):
            self.assertNotIn(f'"{field}"', text, field)

    def test_every_cell_records_its_expected_realization_gaps(self):
        for name, entry in sorted(self.requests().items()):
            for platform, expected in sorted(entry['platforms'].items()):
                with self.subTest(request=name, platform=platform):
                    plan = support.platform_plan(platform, name)
                    self.assertEqual(expected['realization_gaps'],
                                     sorted(warning['code'] for warning in plan.warnings))
                    self.assertIn('INVENTORY_NOT_AUTHORITATIVE', expected['realization_gaps'])

    def test_the_vmware_realization_boundary_is_recorded_not_dropped(self):
        # The reviewed VMware module carries the address on the NSX segment, so the
        # workload phase cannot take one: every VMware cell must say so, and no other
        # platform may report a boundary it does not have.
        for name, entry in sorted(self.requests().items()):
            with self.subTest(request=name):
                self.assertIn('REALIZATION_INPUT_UNAVAILABLE',
                              entry['platforms']['vmware']['realization_gaps'])
                for platform in ('nutanix', 'openstack'):
                    self.assertNotIn('REALIZATION_INPUT_UNAVAILABLE',
                                     entry['platforms'][platform]['realization_gaps'])

    def test_no_cell_claims_native_contact_or_production_authority(self):
        for name, entry in sorted(self.requests().items()):
            for platform, expected in sorted(entry['platforms'].items()):
                with self.subTest(request=name, platform=platform):
                    self.assertIs(expected['native_contact'], False)
                    self.assertEqual(expected['status'], 'PLANNED_DISABLED_NOT_AUTHORIZED')
                    plan = support.platform_plan(platform, name)
                    self.assertIs(plan.native_contact, False)
                    self.assertEqual(plan.status, 'PLANNED_DISABLED_NOT_AUTHORIZED')
                    self.assertFalse(plan.decision.authorized)
                    self.assertEqual(plan.conformance['status'],
                                     'BLOCKED_ON_EXTERNAL_EVIDENCE')
                    self.assertFalse(plan.conformance['ready'])
                    self.assertIs(plan.conformance['native_contact'], False)

    def test_every_incompatible_combination_records_its_explicit_refusal(self):
        for name, entry in sorted(self.requests().items()):
            recorded = {(row['declared_preference'], row['fixture']): row
                        for row in entry['refusals']}
            expected = {(declared, fixture)
                        for declared in support.PLATFORMS
                        for fixture in support.PLATFORMS if declared != fixture}
            with self.subTest(request=name):
                self.assertEqual(sorted(recorded), sorted(expected))
            for (declared, fixture), row in sorted(recorded.items()):
                with self.subTest(request=name, declared=declared, fixture=fixture):
                    outcome = support.platform_refusal(declared, fixture, name)
                    self.assertIsInstance(outcome, ProvisioningError)
                    self.assertEqual(row['code'], outcome.code)
                    self.assertEqual(row['path'], outcome.path)
                    self.assertEqual(row['reason'], outcome.message)
                    self.assertEqual(row['status'], (outcome.details or {}).get('status'))
                    self.assertNotEqual(row['declared_preference'], row['fixture'])


class GoldenCorpusCommandTest(unittest.TestCase):
    """Every reference request must be reachable through the real command line."""

    def run_cli(self, *arguments: str) -> tuple[int, dict]:
        completed = subprocess.run(
            [sys.executable, '-m', 'provisioner.cli', *arguments],
            cwd=str(support.ROOT), capture_output=True, text=True, encoding='utf-8')
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            raise AssertionError(
                f'CLI did not emit JSON (exit {completed.returncode}): '
                f'{completed.stdout!r} {completed.stderr!r}')
        return completed.returncode, payload

    def test_validate_and_resolve_succeed_for_every_request(self):
        for name in support.REFERENCE_REQUESTS:
            with self.subTest(request=name):
                code, payload = self.run_cli('validate', str(support.request_path(name)))
                self.assertEqual(code, 0, payload)
                self.assertEqual(payload['status'], 'VALID')
                code, payload = self.run_cli('resolve', str(support.request_path(name)))
                self.assertEqual(code, 0, payload)
                self.assertEqual(payload['status'], 'RESOLVED')

    def test_plan_reproduces_the_stored_digest_for_every_request(self):
        index = load(GOLDEN, 'digests.json')['subjects']
        for name in support.REFERENCE_REQUESTS:
            with self.subTest(request=name):
                code, payload = self.run_cli('plan', str(support.request_path(name)))
                self.assertEqual(code, 0, payload)
                self.assertEqual(payload['status'], index[name]['status'])
                self.assertEqual(payload['digest'], index[name]['plan_digest'])


if __name__ == '__main__':
    unittest.main()