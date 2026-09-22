"""Golden path: every reviewed reference request reproduces its stored artifacts."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from provisioner.domain.request import canonical_json, digest

from tests.provisioning import support

RESOLVED = support.RESOLVED
GOLDEN = support.GOLDEN
BRITTLE = ('timestamp', 'created_at', 'generated_at', 'T00:', 'T12:')


def load(directory: Path, name: str) -> dict:
    return json.loads((directory / name).read_text(encoding='utf-8'))


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


class GoldenReplayTest(unittest.TestCase):
    """Recomputing a reference request must reproduce every stored artifact byte for byte."""

    def test_resolved_profile_sets_are_reproduced(self):
        for name in support.REFERENCE_REQUESTS:
            with self.subTest(request=name):
                plan = support.reference_plan(name)
                expected = load(RESOLVED, f'{name}.resolution.json')
                self.assertEqual(expected['profiles'], dict(plan.resolution.profiles))
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
    """One portable request must reproduce its stored digest on every platform."""

    def corpus(self) -> dict:
        return load(GOLDEN, 'cross-platform.digests.json')

    def test_the_corpus_covers_every_platform_with_a_reviewed_fixture(self):
        corpus = self.corpus()
        self.assertEqual(corpus['format'], 'hosting-golden-cross-platform/1')
        self.assertEqual(sorted(corpus['platforms']), sorted(support.REFERENCE_FIXTURES))

    def test_every_platform_is_asked_the_same_portable_request(self):
        portable = []
        for platform in sorted(support.REFERENCE_FIXTURES):
            document = support.platform_request(platform)
            document['spec']['platform'].pop('preference')
            portable.append(canonical_json(document))
        self.assertEqual(len(set(portable)), 1)
        self.assertEqual(len({entry['portable_digest']
                              for entry in self.corpus()['platforms'].values()}), 1)

    def test_every_platform_reproduces_its_stored_digests(self):
        for platform, expected in sorted(self.corpus()['platforms'].items()):
            with self.subTest(platform=platform):
                plan = support.platform_plan(platform)
                self.assertEqual(expected['request_digest'], plan.request.digest)
                self.assertEqual(expected['plan_digest'], plan.digest)
                self.assertEqual(expected['desired_state_digest'], plan.desired_state.digest)
                self.assertEqual(expected['environment_digest'], digest(plan.environment))
                self.assertEqual(expected['status'], plan.status)
                self.assertEqual(expected['stack_roots'],
                                 sorted({scope['root'] for scope in plan.terraform_scopes}))
                self.assertEqual(expected['compiled_files'], sorted(plan.compiled))
                self.assertEqual(expected['realization_gaps'],
                                 sorted(warning['code'] for warning in plan.warnings))
                self.assertIs(plan.native_contact, False)
                self.assertEqual(plan.desired_state.platform, platform)

    def test_an_unavailable_realization_input_is_recorded_not_dropped(self):
        platforms = self.corpus()['platforms']
        # The reviewed VMware module carries the address on the NSX segment, so the
        # workload phase cannot take one: the plan must say so instead of dropping it.
        self.assertIn('REALIZATION_INPUT_UNAVAILABLE', platforms['vmware']['realization_gaps'])
        for platform in ('nutanix', 'openstack'):
            self.assertNotIn('REALIZATION_INPUT_UNAVAILABLE',
                             platforms[platform]['realization_gaps'])


class GoldenCorpusCommandTest(unittest.TestCase):
    """Every reference request must be reachable through the real command line."""

    def run_cli(self, *arguments: str) -> tuple[int, dict]:
        completed = subprocess.run(
            [sys.executable, '-m', 'provisioner.cli.main', *arguments],
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