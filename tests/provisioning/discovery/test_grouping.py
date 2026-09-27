"""A source-attributed application candidate never adopts discovered VMs."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.grouping import (
    ConsistencyProposal, DependencyAssertion, GroupDraft, GroupMember,
    GroupingHeld, OwnerReview, proposal_digest, reviewed_candidate,
)
from provisioner.controlplane.discovery.model import (
    DiscoveryFact, DiscoveryObject, DiscoveryResult, NativeIdentity,
)

T0 = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)
NOW = T0 + timedelta(minutes=10)
SCOPE = PlanScope('org-a', 'tenant-a', 'site-a', 'wsd-a',
                  'vcenter-a', 'datacenter-1', 'vmware')
VM1 = NativeIdentity('vcenter-a', 'datacenter-1', 'vmware', 'vm', 'vm-101')
VM2 = NativeIdentity('vcenter-a', 'datacenter-1', 'vmware', 'vm', 'vm-102')
RESULT = DiscoveryResult('campaign-a', 'a' * 64, SCOPE, T0, 'COMPLETE', (
    DiscoveryObject(VM1, (DiscoveryFact.known('name', 'Database'),)),
    DiscoveryObject(VM2, (DiscoveryFact.known('name', 'Frontend'),)),
), (), ())
DRAFT = GroupDraft('application-a', 'Application A', 'owner-a', (
    GroupMember('db', VM1), GroupMember('web', VM2)),
    ('database-data', 'web-data'),
    (ConsistencyProposal('data-group', ('database-data', 'web-data')),),
    ('db', 'web'))
KNOWN = DependencyAssertion('edge-a', 'web', 'db', 'STARTS_AFTER', 'KNOWN',
                            'CMDB', 'cmdb-ticket-a', T0)
UNKNOWN = DependencyAssertion('edge-b', 'web', None, 'SERVICE_CALL', 'UNKNOWN',
                              'MONITORING', 'trace-a', T0, 'UNRESOLVED_TARGET')


def review(result=RESULT, draft=DRAFT, edges=(KNOWN,)):
    return OwnerReview(draft.owner_id, SCOPE, 'owner-review-a', T0 + timedelta(minutes=5),
                       proposal_digest(result, draft, edges))


class ApplicationGroupingTests(unittest.TestCase):
    def test_multi_vm_review_binds_current_observation_dependencies_and_data(self):
        candidate = reviewed_candidate(RESULT, DRAFT, (KNOWN,), review(), checked_at=NOW)
        self.assertEqual(candidate.status, 'REVIEWED_ASSESSMENT_ONLY')
        self.assertEqual(candidate.scope, SCOPE)
        self.assertEqual(candidate.discovery_digest, RESULT.digest)
        self.assertEqual(candidate.draft.startup_order, ('db', 'web'))
        self.assertEqual(candidate.draft.consistency_groups[0].dataset_ids,
                         ('database-data', 'web-data'))
        self.assertEqual(candidate.dependencies[0].source_reference, 'cmdb-ticket-a')
        self.assertFalse(candidate.ownership_accepted)
        self.assertFalse(candidate.execution_approved)
        self.assertEqual(len(candidate.digest), 64)

    def test_unresolved_edges_remain_visible_and_do_not_create_external_member(self):
        edges = (KNOWN, UNKNOWN)
        candidate = reviewed_candidate(RESULT, DRAFT, edges, review(edges=edges),
                                       checked_at=NOW)
        self.assertEqual(candidate.status, 'REVIEWED_WITH_UNKNOWNS')
        self.assertEqual(candidate.unknown_edges, (UNKNOWN,))
        self.assertEqual(len(candidate.draft.members), 2)

    def test_stale_or_partial_observation_cannot_group(self):
        stale = replace(RESULT, captured_at=T0 - timedelta(hours=2))
        partial = DiscoveryResult('campaign-b', 'a' * 64, SCOPE, T0, 'PARTIAL',
                                  RESULT.objects, ('NATIVE_PAGE_MISSING',), ())
        for result in (stale, partial):
            with self.subTest(result=result.completeness), self.assertRaises(GroupingHeld):
                reviewed_candidate(result, DRAFT, (KNOWN,), review(result=result),
                                   checked_at=NOW)

    def test_cross_scope_and_foreign_vm_membership_rejected(self):
        foreign = NativeIdentity('vcenter-b', 'datacenter-2', 'vmware', 'vm', 'vm-103')
        draft = replace(DRAFT, members=(DRAFT.members[0], GroupMember('web', foreign)))
        with self.assertRaises(GroupingHeld):
            reviewed_candidate(RESULT, draft, (KNOWN,), review(draft=draft),
                               checked_at=NOW)
        other_tenant = replace(RESULT, scope=replace(SCOPE, tenant_id='tenant-b'))
        with self.assertRaises(GroupingHeld):
            reviewed_candidate(other_tenant, DRAFT, (KNOWN,),
                               review(result=other_tenant), checked_at=NOW)

    def test_owner_review_cannot_be_replayed_for_changed_membership_or_edge(self):
        original_review = review()
        changed = replace(DRAFT, startup_order=('web', 'db'))
        with self.assertRaises(GroupingHeld):
            reviewed_candidate(RESULT, changed, (KNOWN,), original_review,
                               checked_at=NOW)
        altered_edge = replace(KNOWN, source_reference='cmdb-ticket-b')
        with self.assertRaises(GroupingHeld):
            reviewed_candidate(RESULT, DRAFT, (altered_edge,), original_review,
                               checked_at=NOW)
        with self.assertRaises(GroupingHeld):
            reviewed_candidate(RESULT, DRAFT, (KNOWN,),
                               replace(original_review, owner_id='other-owner'),
                               checked_at=NOW)

    def test_known_order_and_unattributed_or_unknown_target_are_held(self):
        wrong_order = replace(DRAFT, startup_order=('web', 'db'))
        with self.assertRaisesRegex(GroupingHeld, 'Startup order'):
            reviewed_candidate(RESULT, wrong_order, (KNOWN,),
                               review(draft=wrong_order), checked_at=NOW)
        for edge in (replace(KNOWN, source='INFERRED'),
                     replace(KNOWN, target_workload_id='foreign-workload'),
                     replace(UNKNOWN, target_workload_id='foreign-workload')):
            with self.subTest(edge=edge), self.assertRaises(GroupingHeld):
                reviewed_candidate(RESULT, DRAFT, (edge,),
                                   review(edges=(edge,)), checked_at=NOW)

    def test_dataset_consistency_proposal_requires_exact_coverage(self):
        draft = replace(DRAFT, consistency_groups=(
            ConsistencyProposal('data-group', ('database-data',)),))
        with self.assertRaises(GroupingHeld):
            reviewed_candidate(RESULT, draft, (KNOWN,), review(draft=draft),
                               checked_at=NOW)


if __name__ == '__main__':
    unittest.main()
