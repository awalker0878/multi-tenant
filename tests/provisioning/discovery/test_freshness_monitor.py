"""Periodic freshness projection tests; no collection or notification delivery."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import unittest

from provisioner.controlplane.discovery import freshness_monitor as module
from provisioner.controlplane.discovery.freshness_history import FreshnessHistoryRepository
from provisioner.controlplane.persistence.store import AuditContext, TenantContext
from tests.provisioning.api.test_http import NOW, SOURCE_SCOPE
from tests.provisioning.discovery.test_freshness_history import Database, Discovery


class FreshnessMonitorTests(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.discovery = Discovery(self.db)
        self.history = FreshnessHistoryRepository(self.discovery)
        self.ctx = TenantContext(SOURCE_SCOPE.organization_id, SOURCE_SCOPE.tenant_id)
        self.policy = module.FreshnessMonitorPolicy(interval_seconds=300, max_targets=4, max_cycles=4)
        self.target = module.FreshnessMonitorTarget('env-01', SOURCE_SCOPE)
        self.authorizations = []
        self.denied = False

    def authorize(self, scope, at):
        self.assertEqual(scope, SOURCE_SCOPE)
        self.authorizations.append(at)
        if self.denied:
            raise PermissionError('synthetic revocation')

    def monitor(self, **kwargs):
        return module.FreshnessMonitor(self.history, policy=self.policy, **kwargs)

    def test_policy_and_target_are_closed_and_bounded(self):
        self.assertEqual(self.policy.document(), {
            'format': 'hosting-discovery-freshness-monitor-policy/1',
            'intervalSeconds': 300, 'maxTargets': 4, 'maxCycles': 4})
        for values in ({'interval_seconds': 29}, {'interval_seconds': 86401}, {'max_targets': 0},
                       {'max_targets': True}, {'max_cycles': 0}, {'max_cycles': 2017}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                module.FreshnessMonitorPolicy(**values)
        with self.assertRaises(ValueError):
            module.FreshnessMonitorTarget('bad id', SOURCE_SCOPE)

    def test_check_identity_is_stable_inside_slot_and_changes_across_slots(self):
        first = module.check_id(self.target, self.policy, NOW)
        self.assertEqual(first, module.check_id(self.target, self.policy, NOW + timedelta(seconds=299)))
        self.assertNotEqual(first, module.check_id(self.target, self.policy, NOW + timedelta(seconds=300)))
        self.assertNotEqual(first, module.check_id(
            module.FreshnessMonitorTarget('env-02', SOURCE_SCOPE), self.policy, NOW))

    def test_cycle_records_once_and_retry_does_not_resample(self):
        monitor = self.monitor()
        first = monitor.run_cycle(self.ctx, [self.target], actor_id='freshness-monitor',
                                  scheduled_at=NOW, authorize=self.authorize)
        reads, events = self.db.reads, len(self.db.events)
        second = monitor.run_cycle(self.ctx, [self.target], actor_id='freshness-monitor',
                                   scheduled_at=NOW + timedelta(seconds=10), authorize=self.authorize)
        self.assertEqual(first['items'], second['items'])
        self.assertEqual(self.db.reads, reads)
        self.assertEqual(len(self.db.events), events)
        item = first['items'][0]
        self.assertEqual(item['status'], 'CHECK_RETAINED')
        self.assertEqual(item['alert']['severity'], 'WARNING')
        self.assertEqual(item['alert']['issueCodes'],
                         ['COLLECTION_ERRORS_PRESENT', 'COLLECTION_PARTIAL'])
        self.assertFalse(item['executionAuthorized'])
        self.assertEqual(first['notificationDelivery'], 'EXTERNAL_NOT_ATTEMPTED')

    def test_critical_issue_beats_warning_without_sending_notification(self):
        self.discovery.metadata = None
        cycle = self.monitor().run_cycle(self.ctx, [self.target], actor_id='freshness-monitor',
                                         scheduled_at=NOW, authorize=self.authorize)
        alert = cycle['items'][0]['alert']
        self.assertEqual(alert['severity'], 'CRITICAL')
        self.assertEqual(alert['issueCodes'], ['INVENTORY_MISSING'])
        self.assertTrue(alert['notificationRequired'])
        self.assertFalse(alert['notificationAttempted'])
        self.assertEqual(alert['deliveryOwner'], 'EXTERNAL')
        self.assertFalse(alert['collectionRequested'])

    def test_non_actionable_native_visibility_issue_does_not_create_alert(self):
        self.discovery.metadata = replace(
            self.discovery.metadata, completeness='COMPLETE',
            collection_errors=(), missing_privileges=())
        check = self.history.capture(
            self.ctx, SOURCE_SCOPE, 'env-01', 'manual-check',
            audit=AuditContext('freshness-monitor', 'manual-check'), authorize=self.authorize)
        self.assertEqual(check['report']['issues'], ['NATIVE_VISIBILITY_UNVERIFIED'])
        self.assertIsNone(module.alert_projection(check))

    def test_invalid_retained_shapes_digests_and_authority_claims_are_rejected(self):
        check = self.history.capture(
            self.ctx, SOURCE_SCOPE, 'env-01', 'manual-check',
            audit=AuditContext('freshness-monitor', 'manual-check'), authorize=self.authorize)
        mutations = [
            ('historicalOnly', False), ('notificationAttempted', True),
            ('collectionRequested', True), ('executionAuthorized', True),
            ('recordDigest', 'A'*64), ('changeKinds', 'INITIAL_CHECK')]
        for key, value in mutations:
            altered = deepcopy(check); altered[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                module.alert_projection(altered)
        altered = deepcopy(check)
        altered['report']['issues'] = ['INVENTORY_MISSING']
        with self.assertRaises(ValueError):
            module.alert_projection(altered)

    def test_duplicate_and_oversized_targets_are_rejected_before_database_access(self):
        monitor = self.monitor()
        with self.assertRaises(ValueError):
            monitor.run_cycle(self.ctx, [self.target, self.target], actor_id='freshness-monitor',
                              scheduled_at=NOW, authorize=self.authorize)
        too_many = [module.FreshnessMonitorTarget(f'env-{n}', SOURCE_SCOPE) for n in range(5)]
        with self.assertRaises(ValueError):
            monitor.run_cycle(self.ctx, too_many, actor_id='freshness-monitor',
                              scheduled_at=NOW, authorize=self.authorize)
        self.assertEqual(self.db.queries, [])

    def test_revocation_holds_one_target_without_converting_it_to_success(self):
        self.denied = True
        result = self.monitor().run_cycle(
            self.ctx, [self.target], actor_id='freshness-monitor',
            scheduled_at=NOW, authorize=self.authorize)
        self.assertEqual(result['items'][0]['status'], 'CHECK_HELD')
        self.assertIsNone(result['items'][0]['recordDigest'])
        self.assertIsNone(result['items'][0]['alert'])
        self.assertEqual(self.db.rows, [])

    def test_bounded_runner_does_not_repeat_a_slot(self):
        class Clock:
            def __init__(self): self.value = NOW
            def __call__(self): return self.value
            def sleep(self, seconds): self.value += timedelta(seconds=seconds)
        clock = Clock()
        result = self.monitor(clock=clock, sleeper=clock.sleep).run(
            self.ctx, [self.target], actor_id='freshness-monitor',
            authorize=self.authorize, duration_seconds=601)
        self.assertLessEqual(len(result), self.policy.max_cycles)
        self.assertEqual(len({row['slot'] for row in result}), len(result))
        self.assertTrue(all(row['collectionRequested'] is False for row in result))

    def test_regressed_monitor_clock_is_rejected(self):
        values = iter([NOW, NOW - timedelta(seconds=1)])
        monitor = self.monitor(clock=lambda: next(values))
        self.assertEqual(monitor._now(), NOW)
        with self.assertRaises(ValueError):
            monitor._now()


if __name__ == '__main__':
    unittest.main()
