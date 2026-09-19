"""Current-main integration and independent evidence chronology regressions.

These use synthetic task bodies over loopback TLS. No native operation or approval.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
from unittest.mock import patch

from lab.native_readback_fixture import Fixture
from lab.nutanix_task_tree_fixture import reset
from scripts.check_documentation import Builder
from tools import readback_core as c, nutanix_observe as native, recovery_review as rr

ROOT = Path(__file__).resolve().parents[1]


class NavigationIntegrationTests(unittest.TestCase):
    def navigation(self):
        captured = {}
        builder = Builder(ROOT)
        with patch.object(builder, 'write', side_effect=lambda name, text: captured.update({name: text.rstrip()+'\n'})):
            builder.navigation()
        return captured

    def test_task_and_commissioning_navigation_match_generator(self):
        actual = self.navigation()
        for name in ('docs/engineering/README.md', 'docs/implementation/README.md'):
            self.assertEqual(actual[name], (ROOT/name).read_text())

    def test_capability_registry_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('platform-capability-registry.md', text)

    def test_native_qualification_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('platform-native-qualification.md', text)

    def test_pre_placement_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('pre-placement-platform-eligibility.md', text)

    def test_site_service_capacity_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('site-service-capacity-eligibility.md', text)

    def test_reservation_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('reservation-preflight-and-reconciliation.md', text)

    def test_ipam_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('authoritative-ipam-allocation-handoff.md', text)

    def test_dns_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('authoritative-dns-registration-handoff.md', text)

    def test_backup_restore_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('backup-isolated-restore-assurance.md', text)

    def test_control_inheritance_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('control-inheritance-and-external-dependency-assurance.md', text)

    def test_operational_handover_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('operational-handover-and-incident-readiness-assurance.md', text)

    def test_version_source_provenance_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('version-source-provenance-and-lifecycle-assurance.md', text)

    def test_bounded_extension_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('bounded-extension-adoption-and-qualification-assurance.md', text)

    def test_knowledge_maintenance_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('knowledge-maintenance-and-release-integrity-assurance.md', text)

    def test_security_edge_zip_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('security-edge-zip-assurance.md', text)

    def test_native_reconciliation_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('native-readback-writer-fencing-and-reconciliation-assurance.md', text)

    def test_native_ipv6_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('native-ipv6-address-family-assurance.md', text)

    def test_production_activation_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('production-activation-and-initial-readiness-assurance.md', text)

    def test_identity_crypto_navigation_survives_regeneration(self):
        text = self.navigation()['docs/engineering/README.md']
        self.assertIn('identity-crypto-trust-assurance.md', text)

    def test_all_three_work_packages_survive_regeneration(self):
        text = self.navigation()['docs/implementation/README.md']
        for destination in ('routed-ipv6-lab.md', 'nutanix-task-tree-readback.md', 'native-reference/README.md'):
            self.assertIn(destination, text)

    def test_planning_and_task_campaign_ci_steps_coexist(self):
        import yaml
        workflow = yaml.safe_load((ROOT/'.github/workflows/validate.yml').read_text())
        commands = [s.get('run', '') for s in workflow['jobs']['repository']['steps']]
        self.assertTrue(any('scripts/commissioning_pack.py check' in s for s in commands))
        self.assertTrue(any('scripts/check_platform_capabilities.py' in s for s in commands))
        self.assertTrue(any('scripts/check_platform_qualification.py' in s for s in commands))
        self.assertTrue(any('scripts/check_platform_family_eligibility.py' in s for s in commands))
        self.assertTrue(any('scripts/check_site_service_capacity.py' in s for s in commands))
        self.assertTrue(any('scripts/check_site_service_eligibility.py' in s for s in commands))
        self.assertTrue(any('scripts/check_reservation_records.py' in s for s in commands))
        self.assertTrue(any('scripts/check_reservation_preflight.py' in s for s in commands))
        self.assertTrue(any('scripts/check_ipam_allocation_records.py' in s for s in commands))
        self.assertTrue(any('scripts/check_ipam_allocation_preflight.py' in s for s in commands))
        self.assertTrue(any('scripts/check_dns_registration_records.py' in s for s in commands))
        self.assertTrue(any('scripts/check_dns_registration_preflight.py' in s for s in commands))
        self.assertTrue(any('scripts/check_backup_restore_assurance.py' in s for s in commands))
        self.assertTrue(any('scripts/check_backup_restore_readiness.py' in s for s in commands))
        self.assertTrue(any('scripts/check_control_inheritance_assurance.py' in s for s in commands))
        self.assertTrue(any('scripts/check_control_inheritance_readiness.py' in s for s in commands))
        self.assertTrue(any('scripts/check_operational_handover_assurance.py' in s for s in commands))
        self.assertTrue(any('scripts/check_operational_handover_readiness.py' in s for s in commands))
        self.assertTrue(any('scripts/check_version_source_provenance.py' in s for s in commands))
        self.assertTrue(any('scripts/check_version_source_readiness.py' in s for s in commands))
        self.assertTrue(any('scripts/check_extension_adoption_assurance.py' in s for s in commands))
        self.assertTrue(any('scripts/check_extension_adoption_readiness.py' in s for s in commands))
        self.assertTrue(any('scripts/check_knowledge_maintenance_assurance.py' in s for s in commands))
        self.assertTrue(any('scripts/check_knowledge_maintenance_readiness.py' in s for s in commands))
        self.assertTrue(any('scripts/check_security_edge_zip_assurance.py' in s for s in commands))
        self.assertTrue(any('scripts/check_security_edge_zip_readiness.py' in s for s in commands))
        self.assertTrue(any('scripts/check_native_reconciliation_assurance.py' in s for s in commands))
        self.assertTrue(any('scripts/check_native_reconciliation_readiness.py' in s for s in commands))
        self.assertTrue(any('scripts/check_native_ipv6_assurance.py' in s for s in commands))
        self.assertTrue(any('scripts/check_native_ipv6_readiness.py' in s for s in commands))
        self.assertTrue(any('scripts/check_production_activation_assurance.py' in s for s in commands))
        self.assertTrue(any('scripts/check_production_activation_readiness.py' in s for s in commands))
        self.assertTrue(any('scripts/check_identity_crypto_assurance.py' in s for s in commands))
        self.assertTrue(any('scripts/check_identity_crypto_readiness.py' in s for s in commands))
        self.assertTrue(any('lab/run_task_tree_lab.py --execute' in s for s in commands))
        self.assertTrue(any('tools/check_local.py' in s for s in commands))


class OfflineSampleChronologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = Fixture()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.close()

    def setUp(self):
        self.manifest = reset(self.fixture)
        self.report = c.observe(self.manifest, self.fixture.client(self.manifest), native, rounds=3, interval=0)
        self.assertEqual(self.report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
        self.now = datetime.now(timezone.utc)

    def reseal(self):
        self.report['content_sha256'] = c.digest({k: v for k, v in self.report.items() if k != 'content_sha256'})

    def test_observed_complete_tree_remains_valid_at_later_review(self):
        self.assertEqual(rr.check_report(self.manifest, self.report, self.now + timedelta(seconds=2), 300),
                         'READBACK_MATCH_NOT_QUALIFIED')

    def test_completion_after_claimed_observation_rejected_even_after_rehash(self):
        # Task completions are now-10..30 seconds. Pretend they were observed
        # at now-40 seconds. This previously passed using only the review clock.
        self.report['started_at'] = (self.now - timedelta(seconds=60)).isoformat()
        for index, row in enumerate(self.report['history']):
            row['observed_at'] = (self.now - timedelta(seconds=40-index)).isoformat()
        self.reseal()
        with self.assertRaises(ValueError):
            rr.check_report(self.manifest, self.report, self.now, 300)

    def test_task_creation_after_claimed_observation_rejected(self):
        self.report['started_at'] = (self.now - timedelta(seconds=115)).isoformat()
        for index, row in enumerate(self.report['history']):
            row['observed_at'] = (self.now - timedelta(seconds=110-index)).isoformat()
        self.reseal()
        with self.assertRaises(ValueError):
            rr.check_report(self.manifest, self.report, self.now, 300)

    def test_later_review_time_does_not_repair_impossible_sample(self):
        self.report['started_at'] = (self.now - timedelta(seconds=60)).isoformat()
        for index, row in enumerate(self.report['history']):
            row['observed_at'] = (self.now - timedelta(seconds=40-index)).isoformat()
        self.reseal()
        with self.assertRaises(ValueError):
            rr.check_report(self.manifest, self.report, self.now + timedelta(seconds=30), 300)


if __name__ == '__main__':
    unittest.main()
