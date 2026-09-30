"""Draft validation does not manufacture an owner review from incomplete inventory."""
import unittest
from dataclasses import replace
from datetime import timedelta

from provisioner.controlplane.discovery.application_drafts import parse_content
from provisioner.controlplane.discovery.grouping import (
    GroupingHeld, proposal_document, proposal_digest, reviewed_candidate, validate_draft)
from tests.provisioning.discovery.test_grouping import DRAFT, RESULT, KNOWN, UNKNOWN, NOW, review


def content(result=RESULT, draft=DRAFT, edges=(KNOWN, UNKNOWN)):
    value = proposal_document(result, draft, edges)
    import json
    return json.loads(json.dumps({'draft': value['draft'], 'dependencies': value['dependencies']}))


class ApplicationDraftContractTests(unittest.TestCase):
    def test_canonical_roundtrip_preserves_original_proposal_digest(self):
        draft, edges = parse_content(content())
        self.assertEqual((draft, edges), (DRAFT, (KNOWN, UNKNOWN)))
        self.assertEqual(proposal_digest(RESULT,draft,edges),proposal_digest(RESULT,DRAFT,(KNOWN,UNKNOWN)))

    def test_partial_inventory_is_draftable_but_not_reviewed(self):
        partial = replace(RESULT, completeness='PARTIAL', collection_errors=('VISIBLE_INVENTORY_ONLY',))
        self.assertEqual(validate_draft(partial,DRAFT,(KNOWN,UNKNOWN),checked_at=NOW),(UNKNOWN,))
        with self.assertRaises(GroupingHeld):
            reviewed_candidate(partial,DRAFT,(KNOWN,),review(result=partial),checked_at=NOW)

    def test_client_review_authority_and_unknown_fields_are_rejected(self):
        for field in ('review','ownershipAccepted','executionAuthorized','recordedBy'):
            value = content(); value[field] = 'caller-claim'
            with self.subTest(field=field), self.assertRaises(ValueError): parse_content(value)
        for segment in ('draft','dependencies'):
            value=content()
            (value[segment] if segment=='draft' else value[segment][0])['untrusted']='secret'
            with self.subTest(segment=segment), self.assertRaises(ValueError): parse_content(value)

    def test_dataset_group_and_member_budgets_are_bounded(self):
        for field,maximum in (('members',100),('datasetIds',1000),('consistencyGroups',100),('startupOrder',100)):
            value=content(); value['draft'][field] = [value['draft'][field][0]]*(maximum+1)
            with self.subTest(field=field), self.assertRaises(ValueError): parse_content(value)
        value=content(); value['dependencies'] *= 251
        with self.assertRaises(ValueError): parse_content(value)

    def test_draft_validation_also_enforces_budgets_for_direct_callers(self):
        huge = replace(DRAFT, dataset_ids=tuple('data-'+str(i) for i in range(1001)))
        with self.assertRaises(GroupingHeld): validate_draft(RESULT,huge,(KNOWN,),checked_at=NOW)

    def test_generation_membership_and_freshness_remain_required_for_drafts(self):
        for result in (replace(RESULT, objects=RESULT.objects[:1]),
                       replace(RESULT, captured_at=RESULT.captured_at-timedelta(days=1))):
            with self.subTest(result=result.digest), self.assertRaises(GroupingHeld):
                validate_draft(result,DRAFT,(KNOWN,),checked_at=NOW)

    def test_unresolved_edges_cannot_name_unscoped_members(self):
        edge=replace(UNKNOWN,target_workload_id='foreign')
        with self.assertRaises(GroupingHeld): validate_draft(RESULT,DRAFT,(edge,),checked_at=NOW)

    def test_member_duplicate_and_startup_cycle_are_rejected(self):
        for draft in (replace(DRAFT,members=(DRAFT.members[0],DRAFT.members[0])),
                      replace(DRAFT,startup_order=tuple(reversed(DRAFT.startup_order)))):
            with self.assertRaises(GroupingHeld): validate_draft(RESULT,draft,(KNOWN,),checked_at=NOW)

    def test_decoding_does_not_retain_mutable_caller_arrays(self):
        value=content(); draft,edges=parse_content(value)
        value['draft']['members'].clear(); value['dependencies'].clear()
        self.assertEqual(draft,DRAFT); self.assertEqual(edges,(KNOWN,UNKNOWN))

    def test_invalid_native_identity_and_timestamp_are_rejected(self):
        value=content(); value['draft']['members'][0]['nativeVm']=['x']
        with self.assertRaises(ValueError): parse_content(value)
        for stamp in ('2026-09-29T12:00:00',False,None,'not-a-date'):
            value=content(); value['dependencies'][0]['observedAt']=stamp
            with self.assertRaises((ValueError,TypeError)): parse_content(value)


if __name__=='__main__': unittest.main()
