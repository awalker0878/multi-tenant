"""Actual PostgreSQL metadata reads; ingestion uses the existing explicit test verifier."""
import os
import unittest
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

from provisioner.controlplane.discovery.freshness import DiscoveryFreshnessService, FreshnessChanged
from provisioner.controlplane.persistence.store import TenantContext
from tests.provisioning.controlplane import test_discovery_persistence as support


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_DISCOVERY_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN'),
                     'Requires isolated discovery and runtime PostgreSQL roles')
class DiscoveryFreshnessPostgresTests(unittest.TestCase):
    setUpClass = classmethod(support.DiscoveryPersistenceTests.setUpClass.__func__)
    setUp = support.DiscoveryPersistenceTests.setUp
    _campaign = support.DiscoveryPersistenceTests._campaign
    _object = support.DiscoveryPersistenceTests._object
    _publish = support.DiscoveryPersistenceTests._publish

    def authorize(self, scope, at):
        self.assertEqual(scope, self.scope)

    def test_latest_partial_generation_is_used_without_rewriting_original_capture_or_audit(self):
        self._publish(self._campaign('older'), 'COMPLETE', (self._object('vm-1','Original'),))
        latest = self._publish(self._campaign('newest'), 'PARTIAL',
                               (self._object('vm-1','Newest'),), ('VISIBLE_INVENTORY_ONLY',))
        with self.reader._session(self.ctx) as con:
            before = con.execute('SELECT count(*) FROM hosting_controlplane.audit_events').fetchone()[0]
        service = DiscoveryFreshnessService(self.reader,clock=lambda:latest.captured_at+timedelta(days=2))
        view = service.inspect(self.ctx,self.scope,self.environment_id,authorize=self.authorize)
        self.assertEqual(view['freshness'],'STALE')
        self.assertEqual(view['observation']['generation'],2)
        self.assertEqual(view['observation']['capturedAt'],latest.captured_at.isoformat())
        self.assertIn('COLLECTION_PARTIAL',view['issues'])
        self.assertEqual(self.reader.latest_generation(self.ctx,self.scope,self.environment_id),latest)
        with self.reader._session(self.ctx) as con:
            self.assertEqual(con.execute('SELECT count(*) FROM hosting_controlplane.audit_events').fetchone()[0],before)

    def test_authorized_empty_environment_is_missing_but_complete_zero_objects_is_fresh(self):
        service = DiscoveryFreshnessService(self.reader)
        self.assertEqual(service.inspect(self.ctx,self.scope,self.environment_id,authorize=self.authorize)['freshness'],'MISSING')
        self._publish(self._campaign('empty'), 'COMPLETE', ())
        view = service.inspect(self.ctx,self.scope,self.environment_id,authorize=self.authorize)
        self.assertEqual(view['freshness'],'FRESH')
        self.assertEqual(view['observation']['objectCount'],0)
        self.assertFalse(view['nativeVisibilityVerified'])

    def test_tenant_and_full_native_scope_filter_prevent_metadata_leaks(self):
        self._publish(self._campaign('scoped'),'COMPLETE',(self._object('vm-1','Scoped'),))
        service = DiscoveryFreshnessService(self.reader)
        for scope,ctx in ((replace(self.scope,site_id='other-site'),self.ctx),
                (replace(self.scope,tenant_id='other'),TenantContext(self.ctx.organization_id,'other'))):
            view = service.inspect(ctx,scope,self.environment_id,authorize=lambda s,t:None)
            self.assertEqual(view['freshness'],'MISSING')
            self.assertIsNone(view['observation'])

    def test_generation_committed_between_reads_is_not_silently_selected(self):
        self._publish(self._campaign('initial'),'COMPLETE',())
        checks = []
        def authorize(scope,at):
            checks.append(at)
            if len(checks)==2:
                self._publish(self._campaign('concurrent'),'PARTIAL',(),('VISIBLE_INVENTORY_ONLY',))
        with self.assertRaises(FreshnessChanged):
            DiscoveryFreshnessService(self.reader).inspect(
                self.ctx,self.scope,self.environment_id,authorize=authorize)

    def test_current_read_revocation_discards_database_metadata(self):
        self._publish(self._campaign('revoked'),'COMPLETE',())
        checks = []
        def authorize(scope,at):
            checks.append(at)
            if len(checks)==3: raise PermissionError('Access revoked after database read')
        with self.assertRaises(PermissionError):
            DiscoveryFreshnessService(self.reader).inspect(
                self.ctx,self.scope,self.environment_id,authorize=authorize)
