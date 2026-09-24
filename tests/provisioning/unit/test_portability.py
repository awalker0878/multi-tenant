"""Sovereign portability and cross-platform mobility contracts."""
from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import sys
import unittest

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import load
from provisioner.portability import artifacts, bundle, capabilities, migration, policy

from tests.provisioning import support

MOBILITY = support.ROOT / 'examples' / 'mobility' / 'internal-production-openstack-to-nutanix.yaml'


def mobility_document():
    return load(MOBILITY)


class ArtifactResolutionTest(unittest.TestCase):
    def test_same_logical_artifact_resolves_to_platform_native_inputs(self):
        image = mobility_document()['spec']['artifact']['image']
        openstack = artifacts.resolve(image, 'openstack', 'site-01')
        nutanix = artifacts.resolve(image, 'nutanix', 'site-01')
        vmware = artifacts.resolve(image, 'vmware', 'site-01')
        self.assertEqual(openstack['reference']['artifact_ref'], image['artifactRef'])
        self.assertEqual(nutanix['reference']['artifact_sha256'], image['sha256'])
        self.assertIn('image_id', openstack['native_inputs'])
        self.assertIn('image_id', nutanix['native_inputs'])
        self.assertIn('template_uuid', vmware['native_inputs'])
        self.assertNotEqual(openstack['native_inputs'], vmware['native_inputs'])

    def test_artifact_digest_drift_is_refused(self):
        image = copy.deepcopy(mobility_document()['spec']['artifact']['image'])
        image['sha256'] = 'c' * 64
        with self.assertRaises(ProvisioningError) as raised:
            artifacts.resolve(image, 'openstack', 'site-01')
        self.assertEqual(raised.exception.code, 'ARTIFACT_INTEGRITY_FAILED')


class PortabilityBundleTest(unittest.TestCase):
    def setUp(self):
        self.source = support.platform_plan('openstack')
        self.bundle = bundle.build(self.source)

    def test_bundle_is_provider_neutral_where_state_must_move(self):
        for workload in self.bundle['workloads']:
            self.assertEqual(sorted(workload), ['compute', 'name', 'storage', 'zone'])
            text = str(workload)
            for forbidden in ('address', 'cluster', 'prefix', 'project', 'segment', 'vlan', 'vni'):
                self.assertNotIn(forbidden, text.lower())
        self.assertEqual(sorted(self.bundle['network']),
                         ['address_family', 'prefix_length', 'profile', 'zones'])
        self.assertEqual(self.bundle['portability_rules']['addresses'],
                         'reallocate-on-target')
        self.assertEqual(self.bundle['portability_rules']['native_ids'], 'never-portable')

    def test_policy_capsule_binds_portable_security_outcome(self):
        capsule = policy.build(self.source)
        self.assertEqual(capsule, self.bundle['policy'])
        self.assertEqual(capsule['requirements']['trust'], self.source.resolution.trust)
        self.assertEqual(capsule['requirements']['service_class'],
                         self.source.resolution.service_class)
        self.assertEqual(capsule['requirements']['capabilities'],
                         list(self.source.resolution.required_capabilities))
        self.assertEqual(capsule['policy']['rules_digest'],
                         self.source.policy['rules_digest'])
        self.assertFalse(capsule['native_contact'])

    def test_wrapper_capabilities_are_explicit(self):
        rows = {row['dimension']: row for row in capabilities.dimensions(self.source)}
        self.assertEqual(set(rows), set(capabilities.PORTABILITY_DIMENSIONS))
        for required in ('portable-intent', 'security-policy', 'workload-artifact',
                         'data-transfer', 'secret-key-rebind', 'cutover-fencing'):
            self.assertTrue(rows[required]['implemented'], required)


class MobilityPlanTest(unittest.TestCase):
    def setUp(self):
        self.intent = mobility_document()
        self.source = support.platform_plan('openstack')
        self.target = support.platform_plan('nutanix')
        self.plan = migration.build(self.source, self.target, self.intent)

    def test_migration_preserves_profile_policy_and_capability_semantics(self):
        equivalence = self.plan['equivalence']
        self.assertEqual(equivalence['semantic_mismatches'], [])
        self.assertEqual(equivalence['required_capabilities'],
                         list(self.source.resolution.required_capabilities))
        self.assertEqual(self.source.resolution.profiles, self.target.resolution.profiles)
        self.assertEqual(self.source.policy['rules_digest'], self.target.policy['rules_digest'])

    def test_missing_native_qualification_holds_both_ends(self):
        blockers = self.plan['blockers']
        self.assertIn('SOURCE_NATIVE_QUALIFICATION_ABSENT', blockers)
        self.assertIn('TARGET_NATIVE_QUALIFICATION_ABSENT', blockers)
        self.assertEqual(self.plan['readiness'], 'HELD')
        self.assertEqual(self.plan['status'], 'PLANNED_DISABLED_NOT_AUTHORIZED')
        self.assertFalse(self.plan['native_contact'])

    def test_rebuild_restore_is_the_only_current_repository_mode(self):
        changed = copy.deepcopy(self.intent)
        changed['spec']['strategy']['mode'] = 'image-convert'
        plan = migration.build(self.source, self.target, changed)
        self.assertEqual(plan['status'], 'HELD_REPOSITORY_CAPABILITY_GAP')
        self.assertIn('MIGRATION_MODE_NOT_IMPLEMENTED:image-convert', plan['blockers'])

    def test_identity_change_is_refused_not_migrated(self):
        changed = copy.deepcopy(self.intent)
        changed['metadata']['name'] = 'another-wsd'
        with self.assertRaises(ProvisioningError) as raised:
            migration.build(self.source, self.target, changed)
        self.assertEqual(raised.exception.code, 'PORTABILITY_POLICY_MISMATCH')

    def test_same_platform_is_not_disguised_as_cross_platform_migration(self):
        changed = copy.deepcopy(self.intent)
        changed['spec']['target']['platform'] = 'openstack'
        with self.assertRaises(ProvisioningError) as raised:
            migration.build(self.source, self.source, changed)
        self.assertEqual(raised.exception.code, 'PORTABILITY_POLICY_MISMATCH')

    def test_target_request_changes_placement_not_workload_policy(self):
        target = migration.target_request(self.source.request.document, self.intent)
        self.assertEqual(target['spec']['platform']['preference'], 'nutanix')
        self.assertEqual(target['spec']['placement']['region'], 'east')
        for key in ('security', 'assurance', 'availability', 'network', 'recovery',
                    'capacity', 'zones', 'services', 'exposure', 'environment'):
            self.assertEqual(target['spec'][key], self.source.request.document['spec'][key])


class MobilityCliTest(unittest.TestCase):
    def test_active_cli_plans_the_mobility_contract(self):
        completed = subprocess.run(
            [sys.executable, '-m', 'provisioner.cli', 'mobility-plan',
             str(support.REQUEST),
             '--inventory', str(support.ROOT / 'provisioner/inventory/fixtures/openstack-reference.json'),
             '--mobility-intent', str(MOBILITY),
             '--target-inventory', str(support.ROOT / 'provisioner/inventory/fixtures/nutanix-reference.json')],
            cwd=str(support.ROOT), capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        import json
        payload = json.loads(completed.stdout)
        self.assertEqual(payload['format'], 'hosting-mobility-plan-result/1')
        self.assertEqual(payload['source']['platform'], 'openstack')
        self.assertEqual(payload['target']['platform'], 'nutanix')
        self.assertEqual(payload['readiness'], 'HELD')
        self.assertIn('SOURCE_ARTIFACT_MAPPING_NOT_AUTHORITATIVE', payload['blockers'])
        self.assertIn('TARGET_ARTIFACT_MAPPING_NOT_AUTHORITATIVE', payload['blockers'])
        artifact = payload['portability_bundle']['workloads'][0]['artifact']
        self.assertEqual(artifact['artifactRef'], 'artifact://linux/rhel9-base')
        self.assertFalse(payload['native_contact'])


if __name__ == '__main__':
    unittest.main()
