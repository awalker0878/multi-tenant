"""Bounded history pages verify their cursor predecessor, not just row hashes.

Tampering is injected below the repository in a transaction-protocol fixture. It
models damaged retained state, not a runtime SQL privilege or native qualification.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import json
import unittest

from provisioner.controlplane.discovery import freshness_history as module
from provisioner.controlplane.discovery.freshness import FreshnessUnavailable
from provisioner.controlplane.discovery.model import _json
from provisioner.controlplane.persistence.store import AuditContext, TenantContext
from tests.provisioning.discovery.test_freshness_history import Database, Discovery
from tests.provisioning.api.test_http import SOURCE_SCOPE


class FreshnessHistoryPageTests(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.discovery = Discovery(self.db)
        self.history = module.FreshnessHistoryRepository(self.discovery)
        self.ctx = TenantContext(SOURCE_SCOPE.organization_id, SOURCE_SCOPE.tenant_id)
        self.audit = AuditContext('page-reader', 'page-tests')
        self.denied = False
        self.calls = 0
        self.originals = [self.capture('check-' + str(n)) for n in range(1, 4)]

    def authorize(self, scope, at):
        self.assertEqual(scope, SOURCE_SCOPE)
        self.calls += 1
        if self.denied:
            raise PermissionError('test revocation')

    def capture(self, check):
        return self.history.capture(self.ctx, SOURCE_SCOPE, 'env-01', check,
            audit=self.audit, authorize=self.authorize)

    def page(self, **kwargs):
        return self.history.list_checks(self.ctx, SOURCE_SCOPE, 'env-01',
            authorize=self.authorize, **kwargs)

    def rewrite(self, index, **changes):
        """Rehash a contradictory but individually valid row to exercise links."""
        original = self.db.rows[index]
        value = module.StoredFreshnessCheck('env-01', SOURCE_SCOPE, *original[8:])
        value = replace(value, **changes)
        value = replace(value, record_digest=module._digest(value.binding()))
        self.db.rows[index] = (*original[:8], value.check_id, value.sequence,
            value.report_json, value.report_digest, value.recorded_by,
            value.recorded_at, value.previous_record_digest, value.changes_json,
            value.record_digest)
        module.FreshnessHistoryRepository._row('env-01', SOURCE_SCOPE, self.db.rows[index][8:])

    def test_first_and_following_pages_keep_original_documents_without_returning_anchor(self):
        first = self.page(limit=1)
        self.assertEqual(first['items'], self.originals[:1])
        self.assertEqual(first['nextAfter'], 1)
        second = self.page(after=first['nextAfter'], limit=1)
        self.assertEqual(second['items'], self.originals[1:2])
        self.assertEqual(second['nextAfter'], 2)
        self.assertEqual(self.page(after=2)['items'], self.originals[2:])

    def test_cursor_record_and_bounded_lookahead_are_read_in_one_statement(self):
        self.db.queries.clear()
        self.page(after=1, limit=1)
        reads = [(sql, args) for sql, args in self.db.queries
                 if sql.startswith('SELECT ') and module._TABLE in sql]
        self.assertEqual(len(reads), 1)
        self.assertEqual(reads[0][1][-2:], (0, 3))
        self.db.queries.clear()
        self.page(after=1, limit=50)
        reads = [(sql, args) for sql, args in self.db.queries
                 if sql.startswith('SELECT ') and module._TABLE in sql]
        self.assertEqual(reads[0][1][-1], 52)

    def test_missing_cursor_record_with_retained_successor_is_held(self):
        self.db.rows.pop(0)
        with self.assertRaises(FreshnessUnavailable):
            self.page(after=1)

    def test_rehashed_wrong_boundary_link_is_held(self):
        self.rewrite(1, previous_record_digest='f' * 64)
        self.db.rows = self.db.rows[:2]
        with self.assertRaises(FreshnessUnavailable):
            self.page(after=1, limit=1)

    def test_corrupt_cursor_is_checked_before_returning_successors(self):
        row = list(self.db.rows[0])
        row[16] = 'f' * 64
        self.db.rows[0] = tuple(row)
        with self.assertRaises(ValueError):
            self.page(after=1)

    def test_terminal_cursor_is_validated_even_when_the_page_would_be_empty(self):
        row = list(self.db.rows[-1])
        row[16] = 'f' * 64
        self.db.rows[-1] = tuple(row)
        with self.assertRaises(ValueError):
            self.page(after=3)

    def test_empty_and_beyond_end_positions_preserve_read_only_behavior(self):
        rows, events, reads = deepcopy(self.db.rows), deepcopy(self.db.events), self.db.reads
        for cursor in (3, 4, 2**63 - 1):
            page = self.page(after=cursor)
            self.assertEqual(page['items'], [])
            self.assertIsNone(page['nextAfter'])
        self.assertEqual(self.db.rows, rows)
        self.assertEqual(self.db.events, events)
        self.assertEqual(self.db.reads, reads)

    def test_invented_monitoring_transition_is_not_accepted_from_rehashed_row(self):
        self.rewrite(1, changes_json=_json(['POLICY_CHANGED']))
        self.db.rows = self.db.rows[:2]
        with self.assertRaises(FreshnessUnavailable):
            self.page(after=1, limit=1)

    def test_elapsed_staleness_transition_cannot_be_omitted(self):
        self.db.now += timedelta(days=2)
        value = self.capture('stale')
        self.assertEqual(value['changeKinds'], ['FRESHNESS_CHANGED'])
        self.rewrite(3, changes_json=_json([]))
        with self.assertRaises(FreshnessUnavailable):
            self.page(after=3)

    def test_reordered_change_kinds_are_not_a_canonical_transition(self):
        self.discovery.metadata = replace(self.discovery.metadata, generation=2,
            result_digest='d' * 64, completeness='COMPLETE', collection_errors=())
        value = self.capture('changed')
        self.assertEqual(value['changeKinds'], ['OBSERVATION_CHANGED', 'COLLECTION_HEALTH_CHANGED'])
        self.rewrite(3, changes_json=_json(list(reversed(value['changeKinds']))))
        with self.assertRaises(FreshnessUnavailable):
            self.page(after=3)

    def test_regressed_check_time_is_detected_across_cursor_boundary(self):
        report = json.loads(self.db.rows[1][10])
        checked = module._time(report['checkedAt']) - timedelta(microseconds=1)
        report['checkedAt'] = checked.isoformat()
        report['ageMicroseconds'] -= 1
        self.rewrite(1, report_json=_json(report), report_digest=module._digest(report))
        self.db.rows = self.db.rows[:2]
        with self.assertRaises(FreshnessUnavailable):
            self.page(after=1, limit=1)

    def test_regressed_record_time_is_detected_across_cursor_boundary(self):
        # The first row remains valid in isolation; the second is earlier than it.
        self.rewrite(0, recorded_at=self.db.now + timedelta(microseconds=1))
        self.rewrite(1, previous_record_digest=self.db.rows[0][16])
        self.db.rows = self.db.rows[:2]
        with self.assertRaises(FreshnessUnavailable):
            self.page(after=1, limit=1)

    def test_valid_policy_observation_and_freshness_changes_remain_readable(self):
        self.history = module.FreshnessHistoryRepository(self.discovery,
            policy=module.FreshnessPolicy(1, 2))
        changed = self.capture('new-policy')
        self.assertEqual(changed['changeKinds'], ['POLICY_CHANGED', 'FRESHNESS_CHANGED'])
        self.assertEqual(self.page(after=3)['items'], [changed])

    def test_invalid_lookahead_prevents_partial_success(self):
        self.rewrite(2, changes_json=_json(['POLICY_CHANGED']))
        with self.assertRaises(FreshnessUnavailable):
            self.page(after=1, limit=1)

    def test_post_read_revocation_withholds_a_valid_page(self):
        calls = []
        def authorize(scope, at):
            calls.append(at)
            if len(calls) == 2:
                raise PermissionError('test post-read revocation')
        with self.assertRaises(PermissionError):
            self.history.list_checks(self.ctx, SOURCE_SCOPE, 'env-01', after=1,
                authorize=authorize)
        self.assertEqual(len(self.db.rows), 3)


if __name__ == '__main__':
    unittest.main()
