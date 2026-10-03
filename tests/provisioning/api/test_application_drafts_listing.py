"""Scoped transport checks for bounded, non-authoritative draft summary pages."""
import copy
import unittest

from tests.provisioning.api import test_application_drafts_http as draft_support
from tests.provisioning.api import test_http as support


class ApplicationDraftListingHttpTests(unittest.TestCase):
    setUp = draft_support.ApplicationDraftHttpTests.setUp
    build = draft_support.ApplicationDraftHttpTests.build

    def listing(self, token='job-reader', query=''):
        return self.client.get('/v1/environments/env-01/application-drafts'+query,
                               headers={'Authorization': 'Bearer '+token})

    def install(self):
        self.seen = []
        self.value = {'format': 'hosting-application-draft-list/1', 'scope': vars(support.SOURCE_SCOPE),
            'environmentId': 'env-01', 'latestGeneration': 2, 'consistency': 'LIVE_PAGE',
            'items': [], 'nextAfter': None, 'executionAuthorized': False}
        def read(ctx, scope, env, *, after, limit, authorize):
            if self.repo.before_check: self.repo.before_check()
            authorize(scope, support.NOW)
            self.seen.append((ctx, scope, env, after, limit))
            return copy.deepcopy(self.value)
        self.repo.list_current = read

    def test_reader_gets_one_explicit_live_page_without_write_authority(self):
        self.install()
        response = self.listing(query='?after=app%3Aa&limit=2')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.seen[0][1:], (support.SOURCE_SCOPE, 'env-01', 'app:a', 2))
        self.assertEqual(response.json()['consistency'], 'LIVE_PAGE')
        self.assertIs(response.json()['executionAuthorized'], False)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(self.repo.saved, [])

    def test_list_does_not_expand_tenant_or_scope_access(self):
        self.install()
        for token in ('reader', 'other-tenant', 'other-wsd', 'approver'):
            with self.subTest(token=token): self.assertEqual(self.listing(token).status_code, 404)
        self.assertEqual(self.client.get('/v1/environments/env-01/application-drafts').status_code, 401)
        self.assertEqual(self.seen, [])

    def test_revoked_session_cannot_return_a_page(self):
        self.install()
        self.repo.before_check = lambda: self.identity.tokens.pop('job-reader')
        self.assertEqual(self.listing().status_code, 404)
        self.assertEqual(self.seen, [])

    def test_invalid_cursors_and_page_budgets_are_rejected(self):
        self.install()
        for query in ('?limit=0', '?limit=101', '?limit=true', '?after=', '?after=../other',
                      '?after='+'x'*129, '?after=https://foreign.invalid'):
            with self.subTest(query=query): self.assertEqual(self.listing(query=query).status_code, 422)
        self.assertEqual(self.seen, [])

    def test_wrong_scope_approval_claim_and_invalid_cursor_are_not_returned(self):
        self.install()
        original = copy.deepcopy(self.value)
        for field, value in (('scope', {}), ('environmentId', 'foreign'), ('executionAuthorized', True),
                             ('consistency', 'SNAPSHOT'), ('nextAfter', 'invented')):
            self.value = {**original, field: value}
            with self.subTest(field=field): self.assertEqual(self.listing().status_code, 503)

    def test_full_proposals_and_duplicate_summaries_are_rejected(self):
        self.install()
        item = {'scope': vars(support.SOURCE_SCOPE), 'environmentId': 'env-01',
            'applicationGroupId': 'app-1', 'status': 'UNREVIEWED', 'revision': 1,
            'ownershipAccepted': False, 'executionAuthorized': False}
        for items in ([{**item, 'proposal': {}}], [item, item]):
            self.value['items'] = items
            with self.subTest(items=items): self.assertEqual(self.listing().status_code, 503)

    def test_complete_summary_page_is_validated_without_hiding_supersession(self):
        self.install()
        item = {'scope': vars(support.SOURCE_SCOPE), 'environmentId': 'env-01',
            'applicationGroupId': 'app-1', 'status': 'UNREVIEWED', 'revision': 1,
            'generation': 1, 'latestGeneration': 2, 'sourceSuperseded': True,
            'ownershipAccepted': False, 'executionAuthorized': False}
        self.value['items'] = [item]
        self.value['nextAfter'] = 'app-1'
        response = self.listing(query='?limit=1')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()['items'][0]['sourceSuperseded'])
        for key, val in (('latestGeneration', 1), ('generation', True), ('sourceSuperseded', False),
                         ('applicationGroupId', 'bad/identity'), ('ownershipAccepted', True)):
            self.value['items'] = [{**item, key:val}]
            with self.subTest(key=key): self.assertEqual(self.listing(query='?limit=1').status_code, 503)

    def test_openapi_advertises_bounded_listing(self):
        spec = self.client.get('/openapi.json').json()['paths'][
            '/v1/environments/{environment_id}/application-drafts']['get']
        self.assertIn('security', spec)
        params = {p['name']: p for p in spec['parameters']}
        self.assertEqual(params['limit']['schema']['maximum'], 100)
        self.assertIn('after', params)


if __name__ == '__main__': unittest.main()
