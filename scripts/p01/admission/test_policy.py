"""Precise denial cases for stale, self-approved or weakened admission inputs."""
import copy
from datetime import datetime, timedelta, timezone
import unittest

from policy import Denied, affected, review, check_exceptions

NOW = datetime(2026, 10, 5, tzinfo=timezone.utc)


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = {'status': 'ACTIVE', 'repository': 'fixture/repository', 'allowed_check_app_id': 15368,
                       'required_checks': ['quality'], 'accounts': {'11': {'login': 'fixture-owner', 'type': 'User'},
                       '12': {'login': 'fixture-security', 'type': 'User'}},
                       'roles': {'catalogue': ['11'], 'planning': ['11'], 'platform': ['11'], 'security': ['12']}}
        self.snapshot = {'repository': 'fixture/repository', 'state': 'open', 'draft': False,
                         'head_sha': 'a'*40, 'base_sha': 'b'*40, 'tested_sha': 'c'*40,
                         'tested_parents': ['b'*40, 'a'*40], 'head_after': 'a'*40, 'base_after': 'b'*40,
                         'author_id': 10, 'unresolved_threads': 0, 'exceptions': [],
                         'permissions': {'11': 'write', '12': 'write'},
                         'checks': [{'id': 1, 'name': 'quality', 'app_id': 15368, 'head_sha': 'c'*40,
                                     'status': 'completed', 'conclusion': 'success'}],
                         'reviews': [{'id': 1, 'user_id': 11, 'login': 'fixture-owner', 'state': 'APPROVED', 'commit_id': 'a'*40},
                                     {'id': 2, 'user_id': 12, 'login': 'fixture-security', 'state': 'APPROVED', 'commit_id': 'a'*40}]}
        self.impact = {'components': ['catalogue', 'planning'], 'unknown_paths': [], 'removed_components': []}

    def run_review(self):
        return review(self.policy, self.snapshot, ['release/review-policy.json'], self.impact, NOW)

    def test_exact_source_distinct_roles_and_checks_pass(self):
        self.assertEqual(self.run_review()['result'], 'ADMITTED')

    def test_unconfigured_mapping_cannot_pass(self):
        self.policy['status'] = 'UNCONFIGURED'
        with self.assertRaisesRegex(Denied, '^review_roles_unconfigured$'):self.run_review()

    def test_author_cannot_approve(self):
        self.snapshot['author_id'] = 11
        with self.assertRaisesRegex(Denied, '^missing_role_review:'):self.run_review()

    def test_wrong_source_and_changed_source_denied(self):
        for key,value,code in [('tested_parents',['b'*40,'d'*40],'stale_or_unrelated_test_merge'),
                               ('head_after','d'*40,'revision_changed_during_review'),
                               ('base_after','d'*40,'revision_changed_during_review')]:
            with self.subTest(key=key):
                original=self.snapshot[key];self.snapshot[key]=value
                with self.assertRaisesRegex(Denied,'^'+code+'$'):self.run_review()
                self.snapshot[key]=original

    def test_stale_dismissed_and_blocking_reviews_denied(self):
        for state,sha in [('APPROVED','d'*40),('DISMISSED','a'*40),('CHANGES_REQUESTED','a'*40)]:
            with self.subTest(state=state,sha=sha):
                r=self.snapshot['reviews'][0];r.update(state=state,commit_id=sha)
                with self.assertRaises(Denied):self.run_review()

    def test_comment_does_not_clear_blocking_review(self):
        self.snapshot['reviews'][0]['state']='CHANGES_REQUESTED'
        self.snapshot['reviews'].append(dict(self.snapshot['reviews'][0],id=3,state='COMMENTED'))
        with self.assertRaisesRegex(Denied,'^changes_requested$'):self.run_review()

    def test_missing_wrong_app_stale_check_denied(self):
        for key,value in [('app_id',99),('head_sha','d'*40),('name','lookalike')]:
            original=self.snapshot['checks'][0][key];self.snapshot['checks'][0][key]=value
            with self.assertRaisesRegex(Denied,'^missing_required_check:quality$'):self.run_review()
            self.snapshot['checks'][0][key]=original

    def test_failed_cancelled_skipped_and_pending_check_denied(self):
        for conclusion in ['failure','cancelled','skipped',None,'neutral','timed_out']:
            self.snapshot['checks'][0]['conclusion']=conclusion
            with self.subTest(conclusion=conclusion),self.assertRaisesRegex(Denied,'^required_check_not_success:quality$'):self.run_review()

    def test_old_success_cannot_hide_latest_failure(self):
        self.snapshot['checks'].append(dict(self.snapshot['checks'][0],id=2,conclusion='failure'))
        with self.assertRaisesRegex(Denied,'^required_check_not_success:quality$'):self.run_review()

    def test_one_person_with_all_roles_is_insufficient(self):
        self.policy['roles']['security']=['11']
        with self.assertRaisesRegex(Denied,'^distinct_reviewers_required$'):self.run_review()

    def test_changed_or_unprivileged_identity_denied(self):
        self.snapshot['permissions']['11']='read'
        with self.assertRaisesRegex(Denied,'^reviewer_not_authorized$'):self.run_review()
        self.snapshot['permissions']['11']='write';self.snapshot['reviews'][0]['login']='different'
        with self.assertRaisesRegex(Denied,'^reviewer_identity_changed$'):self.run_review()

    def test_unresolved_thread_and_unknown_source_denied(self):
        self.snapshot['unresolved_threads']=1
        with self.assertRaisesRegex(Denied,'^unresolved_review_threads$'):self.run_review()
        self.snapshot['unresolved_threads']=0;self.impact['unknown_paths']=['services/unknown/source.py']
        with self.assertRaisesRegex(Denied,'^unclassified_or_removed_component$'):self.run_review()

    def test_deleted_dependency_edge_still_selects_old_consumer(self):
        owners={'catalogue':{'path':'services/catalogue'},'planning':{'path':'services/planning'}}
        old={'dependencies':{'planning':['catalogue']}};new={'dependencies':{'planning':[]}}
        self.assertEqual(affected(['services/catalogue/app/fact.php'],owners,owners,old,new)['components'],['catalogue','planning'])

    def test_rename_uses_both_owner_inventories(self):
        old={'catalogue':{'path':'services/old'}};new={'catalogue':{'path':'services/catalogue'}}
        self.assertEqual(affected(['services/old/fact.php'],old,new,{}, {})['components'],['catalogue'])

    def test_unknown_path_is_not_a_green_empty_selection(self):
        owners={'catalogue':{'path':'services/catalogue'}}
        r=affected(['services/unregistered/a.py'],owners,owners,{}, {})
        self.assertEqual(r['components'],['catalogue']);self.assertEqual(len(r['unknown_paths']),1)

    def test_exception_expiry_wildcard_and_untrusted_reviewer(self):
        e={'id':'EX-1','kind':'architecture','owner':'fixture-owner','reason':'test','removal_task':'fixture-1',
           'compensating_check':'fixture-check','source_revision':'a'*40,'paths':['services/catalogue/app/Fact.php'],
           'rule_id':'boundary','approved_by':11,'approved_at':(NOW-timedelta(hours=1)).isoformat(),
           'expires_at':(NOW+timedelta(days=1)).isoformat()}
        check_exceptions([e],self.policy['accounts'],NOW)
        for key,value,code in [('expires_at',NOW.isoformat(),'exception_expired_or_unbounded'),
                               ('paths',['services/**'],'wildcard_exception'),('approved_by',99,'unknown_exception_approver'),
                               ('kind','native-fencing','forbidden_exception_scope')]:
            with self.subTest(key=key),self.assertRaisesRegex(Denied,'^'+code+'$'):
                check_exceptions([dict(e,**{key:value})],self.policy['accounts'],NOW)


if __name__ == '__main__':unittest.main()
