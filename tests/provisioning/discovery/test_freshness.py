"""Bounded freshness projections preserve age, coverage and access separately."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.freshness import (
    DiscoveryFreshnessService, FreshnessChanged, FreshnessPolicy, FreshnessUnavailable)
from provisioner.controlplane.discovery.persistence import DiscoveryRepository, StoredGeneration
from provisioner.controlplane.persistence.store import TenantContext

NOW = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
CTX = TenantContext('org-1', 'tenant-1')
SCOPE = PlanScope('org-1', 'tenant-1', 'site-1', 'wsd-1', 'endpoint-1', 'native-1', 'openstack')
ROW = StoredGeneration('env-1', 7, 'campaign-7', SCOPE, 'a'*64, 'b'*64,
                       NOW-timedelta(minutes=10), 'COMPLETE', (), (), 0)


class Rows(DiscoveryRepository):
    def __init__(self, row=ROW):
        self.row = row
        self.calls = []
        self.after_read = None

    def latest_generation(self, ctx, scope, environment_id):
        self.calls.append((ctx, scope, environment_id))
        row = self.row
        if self.after_read:
            self.after_read(len(self.calls))
        return row

    def list_observations(self, *args, **kwargs):
        raise AssertionError('Freshness must not hydrate raw observations')


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.repository = Rows()
        self.at = NOW
        self.checks = []
        self.service = DiscoveryFreshnessService(self.repository, clock=lambda: self.at)

    def authorize(self, scope, at):
        self.checks.append((scope, at))

    def inspect(self, **kwargs):
        return self.service.inspect(CTX, SCOPE, 'env-1', authorize=kwargs.get('authorize', self.authorize))

    def test_fresh_empty_complete_inventory_is_not_missing_or_native_qualification(self):
        report = self.inspect()
        self.assertEqual(report['freshness'], 'FRESH')
        self.assertEqual(report['observation']['generation'], 7)
        self.assertEqual(report['observation']['objectCount'], 0)
        self.assertEqual(report['ageMicroseconds'], 600000000)
        self.assertFalse(report['refreshDue'])
        self.assertFalse(report['nativeVisibilityVerified'])
        self.assertFalse(report['executionAuthorized'])
        self.assertFalse(report['collectionRequested'])
        self.assertEqual(report['integrityVerification'], 'METADATA_ONLY')
        self.assertEqual(report['issues'], ['NATIVE_VISIBILITY_UNVERIFIED'])
        self.assertEqual(len(self.repository.calls), 2)
        self.assertEqual(len(self.checks), 3)

    def test_missing_inventory_has_no_fabricated_generation_or_capture_time(self):
        self.repository.row = None
        report = self.inspect()
        self.assertEqual(report['freshness'], 'MISSING')
        self.assertIsNone(report['observation'])
        self.assertIsNone(report['ageMicroseconds'])
        self.assertTrue(report['refreshDue'])
        self.assertEqual(len(self.checks), 3)

    def test_future_capture_is_not_clamped_to_zero_or_treated_as_fresh(self):
        self.repository.row = replace(ROW, captured_at=NOW+timedelta(microseconds=1))
        report = self.inspect()
        self.assertEqual(report['freshness'], 'FUTURE_CAPTURE')
        self.assertIsNone(report['ageMicroseconds'])
        self.assertTrue(report['refreshDue'])

    def test_refresh_boundary_is_inclusive_and_microsecond_exact(self):
        for age, due in ((timedelta(hours=1)-timedelta(microseconds=1), False),
                         (timedelta(hours=1), True)):
            self.repository.row = replace(ROW, captured_at=NOW-age)
            self.assertEqual(self.inspect()['refreshDue'], due)
            self.assertEqual(self.inspect()['freshness'], 'FRESH')

    def test_max_age_boundary_matches_inclusive_assessment_window(self):
        self.repository.row = replace(ROW, captured_at=NOW-timedelta(days=1))
        report = self.inspect()
        self.assertEqual(report['freshness'], 'FRESH')
        self.at += timedelta(microseconds=1)
        report = self.inspect()
        self.assertEqual(report['freshness'], 'STALE')
        self.assertEqual(report['ageMicroseconds'], 86400000001)
        self.assertIn('INVENTORY_STALE', report['issues'])

    def test_recent_partial_and_unknown_captures_keep_collection_problems(self):
        for completeness in ('PARTIAL', 'UNKNOWN'):
            self.repository.row = replace(ROW, completeness=completeness,
                collection_errors=('PRIVATE_NATIVE_ERROR',), missing_privileges=('PRIVATE_ROLE',))
            report = self.inspect()
            self.assertEqual(report['freshness'], 'FRESH')
            self.assertEqual(report['observation']['completeness'], completeness)
            self.assertIn('COLLECTION_'+completeness, report['issues'])
            self.assertIn('MISSING_PRIVILEGES', report['issues'])
            self.assertNotIn('PRIVATE_NATIVE_ERROR', str(report))
            self.assertNotIn('PRIVATE_ROLE', str(report))

    def test_stale_partial_result_retains_both_findings(self):
        self.repository.row = replace(ROW, captured_at=NOW-timedelta(days=2), completeness='PARTIAL')
        report = self.inspect()
        self.assertIn('INVENTORY_STALE', report['issues'])
        self.assertIn('COLLECTION_PARTIAL', report['issues'])

    def test_age_uses_capture_time_not_when_generation_was_inspected(self):
        first = self.inspect()
        self.at += timedelta(minutes=1)
        second = self.inspect()
        self.assertEqual(first['observation'], second['observation'])
        self.assertEqual(second['ageMicroseconds']-first['ageMicroseconds'], 60000000)

    def test_new_or_disappearing_inventory_requires_explicit_reinspection(self):
        for replacement in (None, replace(ROW, generation=8), replace(ROW, result_digest='c'*64)):
            self.repository = Rows()
            self.service = DiscoveryFreshnessService(self.repository, clock=lambda: NOW)
            self.repository.after_read = lambda n: setattr(self.repository, 'row', replacement)
            with self.assertRaises(FreshnessChanged): self.inspect()
            self.assertEqual(len(self.repository.calls), 2)

    def test_missing_to_present_transition_is_not_reported_as_missing(self):
        self.repository.row = None
        self.repository.after_read = lambda n: setattr(self.repository, 'row', ROW)
        with self.assertRaises(FreshnessChanged): self.inspect()

    def test_backend_failure_is_not_a_missing_inventory_result(self):
        def fail(n): raise OSError('Database unavailable')
        self.repository.after_read = fail
        with self.assertRaises(OSError): self.inspect()

    def test_denied_access_prevents_even_the_first_metadata_read(self):
        def denied(scope, at): raise PermissionError('Denied')
        with self.assertRaises(PermissionError): self.inspect(authorize=denied)
        self.assertEqual(self.repository.calls, [])

    def test_revocation_after_read_discards_existing_and_missing_metadata(self):
        for row in (ROW, None):
            self.repository.row = row
            calls = []
            def authorize(scope, at):
                calls.append(at)
                if len(calls) == 3: raise PermissionError('Revoked')
            with self.assertRaises(PermissionError): self.inspect(authorize=authorize)

    def test_invalid_and_regressing_clocks_do_not_generate_status(self):
        for times in ((NOW, NOW-timedelta(microseconds=1)), (NOW.replace(tzinfo=None),)):
            sequence = iter(times)
            self.service = DiscoveryFreshnessService(self.repository, clock=lambda: next(sequence))
            with self.assertRaises(FreshnessUnavailable): self.inspect()

    def test_age_is_evaluated_after_slow_metadata_and_authority_reads(self):
        self.repository.row = replace(ROW, captured_at=NOW-timedelta(days=1))
        self.repository.after_read = lambda n: setattr(self, 'at', NOW+timedelta(seconds=n))
        self.assertEqual(self.inspect()['freshness'], 'STALE')

    def test_foreign_or_invalid_stored_metadata_is_rejected(self):
        changes = ({'environment_id':'foreign'}, {'scope':replace(SCOPE, tenant_id='other')},
            {'generation':True}, {'generation':0}, {'generation':2**63}, {'campaign_id':'../bad'},
            {'result_digest':'bad'}, {'authorization_digest':None}, {'captured_at':NOW.replace(tzinfo=None)},
            {'completeness':'good'}, {'object_count':True}, {'object_count':-1},
            {'collection_errors':[]}, {'missing_privileges':('x',)*1025},
            {'collection_errors':('private\nerror',)}, {'collection_errors':('error',)})
        for change in changes:
            self.repository.row = replace(ROW, **change)
            with self.subTest(change=change), self.assertRaises(FreshnessUnavailable): self.inspect()

    def test_wrong_tenant_context_is_rejected_before_repository_access(self):
        with self.assertRaises(ValueError):
            self.service.inspect(TenantContext('other', CTX.tenant_id), SCOPE, 'env-1', authorize=self.authorize)
        self.assertEqual(self.repository.calls, [])

    def test_invalid_or_unbounded_policy_is_rejected(self):
        for values in ((True,86400),(0,86400),(10,1),(1,604801),(1,False),(1.0,86400)):
            with self.subTest(values=values), self.assertRaises(ValueError): FreshnessPolicy(*values)
        policy = FreshnessPolicy(60, 120)
        service = DiscoveryFreshnessService(self.repository, policy=policy, clock=lambda: NOW)
        self.assertEqual(service.inspect(CTX,SCOPE,'env-1',authorize=self.authorize)['freshness'],'STALE')

    def test_exact_scope_and_generation_identity_are_retained(self):
        report = self.inspect()
        self.assertEqual(report['scope'], vars(SCOPE))
        self.assertEqual(report['observation']['resultDigest'], ROW.result_digest)
        self.assertEqual(report['observation']['authorizationDigest'], ROW.authorization_digest)
        self.assertEqual(self.repository.calls, [(CTX,SCOPE,'env-1')]*2)
