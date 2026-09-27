"""Real PostgreSQL coverage for the separate, append-only discovery plane."""
from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.model import (
    DiscoveryCampaignAuthorization, DiscoveryFact, DiscoveryObject,
    DiscoveryResult, NativeIdentity,
)
from provisioner.controlplane.discovery.persistence import (
    DiscoveryConflict, DiscoveryRepository, VerificationEvidence,
)
from provisioner.controlplane.persistence.environments import (
    EnvironmentDeclaration, EnvironmentRepository,
)
from provisioner.controlplane.persistence.store import AuditContext, TenantContext


class _IndependentTestVerifier:
    """Explicit isolated-test verifier; no production service uses this object."""

    def verify_campaign(self, campaign, environment_id, checked_at):
        if not environment_id or not checked_at:
            raise ValueError('Missing exact environment or verifier time')
        return VerificationEvidence(campaign.digest(), None, 'test-issuer',
                                    'test-campaign-signature')

    def verify_result(self, campaign, result, environment_id, checked_at):
        if not environment_id or not checked_at or campaign.scope != result.scope:
            raise ValueError('Untrusted collector provenance')
        return VerificationEvidence(campaign.digest(), result.digest,
                                    'test-collector', 'test-result-signature')


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_DISCOVERY_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN'),
                     'Requires dedicated disposable PostgreSQL discovery roles')
class DiscoveryPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        cls.psycopg = psycopg
        cls.ingest_dsn = os.environ['HOSTING_TEST_POSTGRES_DISCOVERY_DSN']
        cls.runtime_dsn = os.environ['HOSTING_TEST_POSTGRES_RUNTIME_DSN']
        cls.site_dsn = os.environ.get('HOSTING_TEST_POSTGRES_SITE_WORKER_DSN')
        cls.reader = DiscoveryRepository(lambda: psycopg.connect(cls.runtime_dsn))
        cls.writer = DiscoveryRepository(
            lambda: psycopg.connect(cls.ingest_dsn),
            ingest_role='hosting_discovery_ingest',
            ingest_verifier=_IndependentTestVerifier())

    def setUp(self):
        suffix = uuid4().hex[:12]
        self.ctx = TenantContext('org-' + suffix, 'tenant-1')
        self.scope = PlanScope(self.ctx.organization_id, self.ctx.tenant_id,
                               'site-1', 'wsd-1', 'endpoint-1', 'scope-1', 'vmware')
        self.environment_id = 'env-' + suffix
        self.environments = EnvironmentRepository(
            lambda: self.psycopg.connect(self.runtime_dsn))
        self.environments.create(
            self.ctx, EnvironmentDeclaration(self.environment_id, 'Lab', self.scope),
            AuditContext('test-authorized-registrar', 'test-' + suffix))

    def _campaign(self, name: str) -> DiscoveryCampaignAuthorization:
        now = datetime.now(timezone.utc)
        return DiscoveryCampaignAuthorization(
            'campaign-' + name + '-' + self.environment_id, self.scope,
            'independent-issuer', 'enrolled-read-collector', ('vm',),
            now - timedelta(minutes=1), now + timedelta(minutes=20),
            10, 100, 50)

    def _object(self, native_id: str, name: str) -> DiscoveryObject:
        return DiscoveryObject(
            NativeIdentity('endpoint-1', 'scope-1', 'vmware', 'vm', native_id),
            (DiscoveryFact.known('name', name),))

    def _publish(self, campaign, completeness, objects, errors=()):
        self.writer.register_verified_campaign(self.ctx, self.environment_id,
                                               campaign)
        result = DiscoveryResult(campaign.campaign_id, campaign.digest(),
                                 campaign.scope, datetime.now(timezone.utc),
                                 completeness, tuple(objects), tuple(errors), ())
        return self.writer.publish_verified_result(
            self.ctx, self.environment_id, result)

    def test_rename_history_partial_no_absence_complete_comparable_absence(self):
        first = self._publish(self._campaign('first'), 'COMPLETE',
                              (self._object('vm-1', 'Old name'),
                               self._object('vm-2', 'Other name')))
        partial = self._publish(self._campaign('partial'), 'PARTIAL',
                                (self._object('vm-1', 'New name'),),
                                ('COLLECTION_ERROR',))
        self.assertEqual(first.generation, 1)
        self.assertEqual(partial.generation, 2)
        self.assertEqual(self.reader.list_absence_candidates(
            self.ctx, self.scope, self.environment_id, 2), [])
        with self.psycopg.connect(self.ingest_dsn) as connection:
            connection.execute(
                "SELECT set_config('app.organization_id', %s, true), "
                "set_config('app.tenant_id', %s, true)",
                (self.ctx.organization_id, self.ctx.tenant_id))
            with self.assertRaises(self.psycopg.Error), connection.transaction():
                connection.execute(
                    'INSERT INTO hosting_controlplane.discovery_absence_candidates '
                    '(organization_id, tenant_id, environment_id, generation, '
                    'resource_kind, native_id, prior_generation) VALUES '
                    '(%s, %s, %s, 2, %s, %s, 1)',
                    (self.ctx.organization_id, self.ctx.tenant_id,
                     self.environment_id, 'vm', 'vm-2'))
        final = self._publish(self._campaign('final'), 'COMPLETE',
                              (self._object('vm-1', 'New name'),))
        self.assertEqual(final.generation, 3)
        self.assertEqual(self.reader.list_absence_candidates(
            self.ctx, self.scope, self.environment_id, 3), [('vm', 'vm-2', 1)])
        old = self.reader.list_observations(self.ctx, self.scope,
                                             self.environment_id, 1, limit=1)
        renamed = self.reader.list_observations(self.ctx, self.scope,
                                                 self.environment_id, 3)
        self.assertEqual(old[0].facts[0]['value'], 'Old name')
        self.assertEqual(renamed[0].facts[0]['value'], 'New name')
        self.assertEqual(old[0].identity.native_id, renamed[0].identity.native_id)
        self.assertEqual(len(self.reader.list_generations(
            self.ctx, self.scope, self.environment_id, limit=2)), 2)
        self.assertEqual([g.generation for g in self.reader.list_generations(
            self.ctx, self.scope, self.environment_id, after=2)], [3])
        self.assertEqual([o.identity.native_id for o in self.reader.list_observations(
            self.ctx, self.scope, self.environment_id, 1,
            after=('vm', 'vm-1'))], ['vm-2'])
        with self.psycopg.connect(self.runtime_dsn) as connection:
            connection.execute(
                "SELECT set_config('app.organization_id', %s, true), "
                "set_config('app.tenant_id', %s, true)",
                (self.ctx.organization_id, self.ctx.tenant_id))
            events = connection.execute(
                'SELECT record_kind, record_digest, audit_sequence '
                'FROM hosting_controlplane.audit_events WHERE record_kind '
                "IN ('DiscoveryCampaign', 'DiscoveryGeneration') "
                'ORDER BY audit_sequence').fetchall()
        self.assertEqual([row[0] for row in events],
                         ['DiscoveryCampaign', 'DiscoveryGeneration'] * 3)
        self.assertEqual([row[2] for row in events], list(range(2, 8)))
        self.assertEqual(events[-1][1], final.result_digest)

        other_site = PlanScope(self.ctx.organization_id, self.ctx.tenant_id,
                               'site-2', 'wsd-1', 'endpoint-1', 'scope-1', 'vmware')
        self.assertEqual(self.reader.list_generations(
            self.ctx, other_site, self.environment_id), [])
        self.assertEqual(self.reader.list_observations(
            self.ctx, other_site, self.environment_id, 1), [])
        with self.assertRaises(ValueError):
            self.reader.list_generations(
                TenantContext(self.ctx.organization_id, 'another-tenant'),
                self.scope, self.environment_id)
        with self.psycopg.connect(self.ingest_dsn) as connection:
            connection.execute(
                "SELECT set_config('app.organization_id', %s, true), "
                "set_config('app.tenant_id', %s, true)",
                (self.ctx.organization_id, self.ctx.tenant_id))
            with self.assertRaises(self.psycopg.Error):
                connection.execute(
                    'UPDATE hosting_controlplane.discovery_observations '
                    "SET facts_json = '[]' WHERE environment_id = %s",
                    (self.environment_id,))

    def test_refuses_unverified_publication_wrong_role_and_site_sql(self):
        campaign = self._campaign('denied')
        unverified = DiscoveryRepository(lambda: self.psycopg.connect(self.ingest_dsn),
                                         ingest_role='hosting_discovery_ingest')
        with self.assertRaises(RuntimeError):
            unverified.register_verified_campaign(self.ctx, self.environment_id,
                                                  campaign)
        wrong_role = DiscoveryRepository(
            lambda: self.psycopg.connect(self.runtime_dsn),
            ingest_role='hosting_discovery_ingest',
            ingest_verifier=_IndependentTestVerifier())
        with self.assertRaises(RuntimeError):
            wrong_role.register_verified_campaign(self.ctx, self.environment_id,
                                                  campaign)
        self.writer.register_verified_campaign(self.ctx, self.environment_id,
                                               campaign)
        with self.assertRaises(DiscoveryConflict):
            self.writer.register_verified_campaign(self.ctx, self.environment_id,
                                                   campaign)
        if self.site_dsn:
            with self.psycopg.connect(self.site_dsn) as site:
                site.execute(
                    "SELECT set_config('app.organization_id', %s, true), "
                    "set_config('app.tenant_id', %s, true)",
                    (self.ctx.organization_id, self.ctx.tenant_id))
                with self.assertRaises(self.psycopg.Error):
                    site.execute('SELECT * FROM hosting_controlplane.discovery_campaigns')


if __name__ == '__main__':
    unittest.main()
