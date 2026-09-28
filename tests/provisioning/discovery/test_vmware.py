"""Protocol and identity regressions for assessment-only VMware enumeration."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import unittest
from unittest.mock import patch

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.adapters.vmware import (
    EnumerationHeld, VmPage, VmSummary, compare_generations, enumerate_vms,
)


SCOPE = PlanScope('org-a', 'tenant-a', 'site-a', 'wsd-a', 'vc-a',
                  'dc-a', 'vmware')
OTHER = PlanScope('org-a', 'tenant-b', 'site-a', 'wsd-a', 'vc-a',
                  'dc-a', 'vmware')
VM1 = VmSummary('vm-101', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'Front end')
VM2 = VmSummary('vm-102', 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'Database')


def reader(*pages):
    calls = []

    def fetch(scope, cursor, limit):
        calls.append((scope, cursor, limit))
        return pages[len(calls) - 1]

    return fetch, calls


class VMwareEnumerationTests(unittest.TestCase):
    def test_follows_exact_scope_and_cursor_to_terminal_count(self):
        fetch, calls = reader(
            VmPage(SCOPE, None, (VM2,), 'opaque-page-2', 2),
            VmPage(SCOPE, 'opaque-page-2', (VM1,), None, 2))
        generation = enumerate_vms(SCOPE, fetch, page_size=1)
        self.assertEqual(calls, [(SCOPE, None, 1),
                                 (SCOPE, 'opaque-page-2', 1)])
        self.assertEqual(generation.items, (VM1, VM2))
        self.assertEqual(generation.pages, 2)
        self.assertTrue(generation.page_chain_complete)
        self.assertFalse(generation.native_qualified)
        self.assertFalse(generation.ownership_accepted)
        self.assertEqual(len(generation.digest), 64)

    def test_empty_terminal_scope_is_a_valid_observation_not_adoption(self):
        fetch, _ = reader(VmPage(SCOPE, None, (), None, 0))
        self.assertEqual(enumerate_vms(SCOPE, fetch).items, ())

    def test_page_scope_cursor_and_shape_must_match(self):
        invalid_pages = (
            VmPage(OTHER, None, (VM1,), None, 1),
            VmPage(SCOPE, 'wrong', (VM1,), None, 1),
            VmPage(SCOPE, None, (VM1, VM2), None, 2),
            VmPage(SCOPE, None, (VM1,), '', 1),
            VmPage(SCOPE, None, [VM1], None, 1),
        )
        for page in invalid_pages:
            with self.subTest(page=page):
                fetch, _ = reader(page)
                with self.assertRaises(EnumerationHeld):
                    enumerate_vms(SCOPE, fetch, page_size=1)

    def test_partial_permission_failure_or_truncated_chain_never_returns_rows(self):
        def denied(_scope, cursor, _limit):
            if cursor is None:
                return VmPage(SCOPE, None, (VM1,), 'next', None)
            raise PermissionError('hidden native permission detail')

        with self.assertRaisesRegex(EnumerationHeld, 'unavailable or unauthorized'):
            enumerate_vms(SCOPE, denied)
        incomplete, _ = reader(VmPage(SCOPE, None, (VM1,), 'next', 2))
        with self.assertRaises(EnumerationHeld):
            enumerate_vms(SCOPE, incomplete, max_pages=1)

    def test_repeated_cursor_empty_nonterminal_and_changing_count_hold(self):
        cases = (
            (VmPage(SCOPE, None, (VM1,), 'one', 2),
             VmPage(SCOPE, 'one', (VM2,), 'one', 2)),
            (VmPage(SCOPE, None, (VM1,), 'one', 2),
             VmPage(SCOPE, 'one', (), 'two', 2)),
            (VmPage(SCOPE, None, (VM1,), 'one', 2),
             VmPage(SCOPE, 'one', (VM2,), None, 3)),
            (VmPage(SCOPE, None, (VM1,), 'one', 2),
             VmPage(SCOPE, 'one', (VM2,), None, None)),
        )
        for pages in cases:
            with self.subTest(pages=pages):
                fetch, _ = reader(*pages)
                with self.assertRaises(EnumerationHeld):
                    enumerate_vms(SCOPE, fetch)

    def test_duplicate_moid_or_uuid_and_mismatched_terminal_total_hold(self):
        cases = (
            (VM1, VM1, 2),
            (VM1, VmSummary('vm-103', VM1.instance_uuid, 'Copy'), 2),
            (VM1, VM2, 3),
        )
        for one, two, total in cases:
            fetch, _ = reader(VmPage(SCOPE, None, (one, two), None, total))
            with self.subTest(two=two, total=total), self.assertRaises(EnumerationHeld):
                enumerate_vms(SCOPE, fetch)

    def test_invalid_identity_and_budgets_hold(self):
        for invalid in (VmSummary('vm-0', VM1.instance_uuid, 'VM'),
                        VmSummary('vm-101', 'bad-uuid', 'VM'),
                        VmSummary('vm-101', VM1.instance_uuid, 'name\n')):
            fetch, _ = reader(VmPage(SCOPE, None, (invalid,), None, 1))
            with self.subTest(invalid=invalid), self.assertRaises(EnumerationHeld):
                enumerate_vms(SCOPE, fetch)
        fetch, _ = reader(VmPage(SCOPE, None, (VM1, VM2), None, None))
        with self.assertRaises(EnumerationHeld):
            enumerate_vms(SCOPE, fetch, max_records=1)
        with self.assertRaises(ValueError):
            enumerate_vms(OTHER, fetch)
        with self.assertRaises(ValueError):
            enumerate_vms(SCOPE, fetch, page_size=501)

    def test_deadline_after_slow_reader_holds_instead_of_publishing(self):
        fetch, _ = reader(VmPage(SCOPE, None, (VM1,), None, 1))
        with patch('provisioner.controlplane.discovery.adapters.vmware.time.monotonic',
                   side_effect=(0, 2)):
            with self.assertRaisesRegex(EnumerationHeld, 'deadline'):
                enumerate_vms(SCOPE, fetch, max_seconds=1)

    def test_same_endpoint_identity_survives_rename_and_absence_is_not_deletion(self):
        fetch, _ = reader(VmPage(SCOPE, None, (VM1, VM2), None, 2))
        previous = enumerate_vms(SCOPE, fetch)
        renamed = replace(VM1, name='Frontend renamed')
        fetch, _ = reader(VmPage(SCOPE, None, (renamed,), None, 1))
        current = enumerate_vms(SCOPE, fetch)
        self.assertEqual(tuple(change.kind for change in compare_generations(previous, current)),
                         ('RENAMED', 'NOT_SEEN'))
        self.assertEqual(compare_generations(previous, current)[0].moid, VM1.moid)
        self.assertEqual(compare_generations(previous, current)[0].instance_uuid,
                         VM1.instance_uuid)

    def test_reused_native_id_or_cross_endpoint_comparison_is_held(self):
        fetch, _ = reader(VmPage(SCOPE, None, (VM1,), None, 1))
        previous = enumerate_vms(SCOPE, fetch)
        fetch, _ = reader(VmPage(SCOPE, None, (replace(VM1, instance_uuid=VM2.instance_uuid),),
                                 None, 1))
        current = enumerate_vms(SCOPE, fetch)
        with self.assertRaises(EnumerationHeld):
            compare_generations(previous, current)
        with self.assertRaises(EnumerationHeld):
            compare_generations(previous, replace(current, scope=OTHER))
        with self.assertRaises(EnumerationHeld):
            compare_generations(previous, replace(previous,
                observed_at=previous.observed_at - timedelta(seconds=1)))


if __name__ == '__main__':
    unittest.main()
