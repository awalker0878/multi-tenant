"""Actual PostgreSQL listing and CLI/API draft round-trips; no native platform calls."""
import copy
import io
import json
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from provisioner.controlplane.persistence.store import TenantContext
from tests.provisioning.controlplane import test_application_drafts_postgres as support


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_DISCOVERY_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN'),
                     'Requires disposable PostgreSQL discovery/runtime roles')
class ApplicationDraftListingPostgresTests(unittest.TestCase):
    setUpClass = classmethod(support.ApplicationDraftPostgresTests.setUpClass.__func__)
    setUp = support.ApplicationDraftPostgresTests.setUp
    _campaign = support.ApplicationDraftPostgresTests._campaign
    _object = support.ApplicationDraftPostgresTests._object
    _publish = support.ApplicationDraftPostgresTests._publish
    authorize = support.ApplicationDraftPostgresTests.authorize
    save = support.ApplicationDraftPostgresTests.save
    get = support.ApplicationDraftPostgresTests.get

    def listing(self, **changes):
        values = dict(authorize=self.authorize)
        values.update(changes)
        return self.repo.list_current(self.ctx, self.scope, self.environment_id, **values)

    def test_empty_listing_retains_source_metadata_without_inventing_drafts(self):
        value = self.listing()
        self.assertEqual(value['items'], [])
        self.assertEqual(value['latestGeneration'], 1)
        self.assertIsNone(value['nextAfter'])
        self.assertFalse(value['executionAuthorized'])

    def test_listing_returns_latest_revisions_in_byte_order_with_bounded_cursors(self):
        for identity in ('app:z', 'App:A', 'app-a'):
            value = copy.deepcopy(self.content)
            value['draft']['applicationGroupId'] = identity
            self.save(content=value)
            value['draft']['name'] = 'Latest '+identity
            self.save(content=value, expected_revision=1)
        first = self.listing(limit=2)
        self.assertEqual([d['applicationGroupId'] for d in first['items']], ['App:A', 'app-a'])
        self.assertEqual(first['nextAfter'], 'app-a')
        self.assertEqual([d['revision'] for d in first['items']], [2, 2])
        second = self.listing(after=first['nextAfter'], limit=2)
        self.assertEqual([d['applicationGroupId'] for d in second['items']], ['app:z'])
        self.assertIsNone(second['nextAfter'])
        self.assertEqual(self.listing(after='app:z')['items'], [])

    def test_listing_summaries_preserve_counts_and_do_not_return_full_assertions(self):
        saved = self.save()
        value = self.listing()['items'][0]
        self.assertNotIn('proposal', value)
        self.assertEqual((value['memberCount'], value['datasetCount'], value['dependencyCount'],
                          value['unknownDependencyCount']), (2, 1, 1, 1))
        self.assertEqual(value['recordDigest'], saved.record_digest)
        self.assertEqual(value['ownerId'], 'owner-ref')
        self.assertEqual(value['status'], 'UNREVIEWED')
        self.assertFalse(value['ownershipAccepted'])
        self.assertFalse(value['sourceSuperseded'])

    def test_listing_marks_superseded_sources_without_rebasing_history(self):
        self.save()
        self._publish(self._campaign('new'), 'PARTIAL', (self._object('vm-1', 'Changed'),),
                      ('VISIBLE_INVENTORY_ONLY',))
        listing = self.listing()
        self.assertEqual(listing['latestGeneration'], 2)
        self.assertEqual(listing['items'][0]['generation'], 1)
        self.assertTrue(listing['items'][0]['sourceSuperseded'])
        self.assertEqual(listing['consistency'], 'LIVE_PAGE')

    def test_listing_rechecks_authority_after_read_even_for_empty_pages(self):
        calls = []
        def revoked(scope, at):
            calls.append(at)
            if len(calls) == 2: raise PermissionError('revoked during list')
        with self.assertRaises(PermissionError): self.listing(authorize=revoked)
        self.assertEqual(len(calls), 2)

    def test_listing_cursors_do_not_grant_cross_scope_or_tenant_access(self):
        self.save()
        scope = replace(self.scope, endpoint_id='different')
        self.assertEqual(self.repo.list_current(self.ctx, scope, self.environment_id,
                         authorize=lambda *_: None)['items'], [])
        ctx = TenantContext(self.ctx.organization_id, 'another-tenant')
        foreign = replace(self.scope, tenant_id=ctx.tenant_id)
        self.assertEqual(self.repo.list_current(ctx, foreign, self.environment_id,
                         after='app-0', authorize=lambda *_: None)['items'], [])
        with self.assertRaises(ValueError):
            self.repo.list_current(ctx, self.scope, self.environment_id, authorize=lambda *_: None)

    def test_listing_direct_caller_bounds_are_not_coerced(self):
        for value in (True, 1.0, '1', 0, 101):
            with self.subTest(limit=value), self.assertRaises(ValueError): self.listing(limit=value)
        for value in ('', '../other', 'x'*129, True):
            with self.subTest(after=value), self.assertRaises(ValueError): self.listing(after=value)




if __name__ == '__main__': unittest.main()
