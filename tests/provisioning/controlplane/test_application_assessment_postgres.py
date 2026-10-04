"""Real draft/evidence/discovery persistence; route inputs remain test fixtures."""
import os
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from provisioner.controlplane.discovery.application_assessment import ApplicationAssessmentService, ApplicationMemberProfile
from provisioner.controlplane.discovery.application_reviews import ApplicationReviewUnavailable
from provisioner.controlplane.discovery.assessment import AssessmentScopeAccess
from provisioner.controlplane.discovery.model import DiscoveryObject, DiscoveryFact, DiscoveryResult, NativeIdentity
from provisioner.controlplane.discovery.routes import InstalledTuple
from provisioner.controlplane.discovery.service import AssessmentService, AssessmentSelection, AssessmentDestination, VerifiedAssessmentEnvironment
from provisioner.controlplane.persistence.environments import EnvironmentDeclaration
from provisioner.controlplane.persistence.store import AuditContext
from tests.provisioning.controlplane import test_application_reviews_postgres as review_support
from tests.provisioning.discovery.test_service import VerifiedInputs, inventory


class Inputs(VerifiedInputs):
    def __init__(self, installations):
        super().__init__(); self.installations = installations; self.at = datetime.now(timezone.utc)
        self.qualified = True; self.after_findings = None
    def resolve_environment(self, ctx, actor, environment_id, purpose, as_of):
        installed = self.installations[environment_id]
        return VerifiedAssessmentEnvironment(environment_id, installed,
            AssessmentScopeAccess(installed.scope, purpose, actor, 'test-only-reader',
                                  self.at-timedelta(minutes=1), self.at+timedelta(minutes=30)))
    def route_claims(self, ctx, actor, routes, as_of):
        return super().route_claims(ctx, actor, routes, self.at)
    def reviewed_findings(self, ctx, actor, route, source, destination, as_of):
        result = tuple(replace(finding, observed_at=self.at) for finding in
            super().reviewed_findings(ctx, actor, route, source, destination, self.at))
        if self.after_findings: self.after_findings()
        return result


@unittest.skipUnless(all(os.environ.get(name) for name in (
    'HOSTING_TEST_POSTGRES_ASSESSMENT_DSN', 'HOSTING_TEST_POSTGRES_DISCOVERY_DSN',
    'HOSTING_TEST_POSTGRES_RUNTIME_DSN')), 'Requires isolated discovery, assessment and runtime PostgreSQL roles')
class ApplicationAssessmentPostgresTests(unittest.TestCase):
    setUpClass = classmethod(review_support.ApplicationReviewPostgresTests.setUpClass.__func__)
    _campaign = review_support.ApplicationReviewPostgresTests._campaign
    _publish = review_support.ApplicationReviewPostgresTests._publish
    authorize = review_support.ApplicationReviewPostgresTests.authorize
    save = review_support.ApplicationReviewPostgresTests.save
    document = review_support.ApplicationReviewPostgresTests.document
    ingest = review_support.ApplicationReviewPostgresTests.ingest

    def _object(self, native_id, name):
        original = review_support.ApplicationReviewPostgresTests._object(self, native_id, name)
        return replace(original, facts=original.facts + inventory('source').objects[0].facts)

    def setUp(self):
        review_support.ApplicationReviewPostgresTests.setUp(self)
        self.reviews = self.service
        installations = {self.environment_id: InstalledTuple(self.scope, 'source-tuple', 'a'*64)}
        destinations = []
        for suffix, available in (('a', 6), ('b', 100)):
            name = self.environment_id+'-'+suffix
            scope = replace(self.scope, endpoint_id='endpoint-'+suffix, native_scope_id='pool-scope-'+suffix)
            self.environments.create(self.ctx, EnvironmentDeclaration(name, 'Target '+suffix, scope),
                                     AuditContext('test-registrar', 'target-'+suffix))
            campaign = replace(self._campaign('target-'+suffix), scope=scope, allowed_kinds=('pool',))
            self.writer.register_verified_campaign(self.ctx, name, campaign)
            original = inventory('target-a').objects[0]
            facts = tuple(f for f in original.facts if f.name != 'availableVcpu') + (
                DiscoveryFact.known('availableVcpu', available), DiscoveryFact.known('availableVmCount', 100))
            obj = DiscoveryObject(NativeIdentity(scope.endpoint_id, scope.native_scope_id,
                                  scope.platform_family, 'pool', 'pool-1'), facts)
            result = DiscoveryResult(campaign.campaign_id, campaign.digest(), scope,
                                     datetime.now(timezone.utc), 'COMPLETE', (obj,), (), ())
            self.writer.publish_verified_result(self.ctx, name, result)
            installations[name] = InstalledTuple(scope, 'target-'+suffix, suffix*64)
            destinations.append(AssessmentDestination(AssessmentSelection(name, 1), 'pool', 'pool-1'))
        self.destinations = tuple(destinations)
        self.inputs = Inputs(installations)
        self.service = ApplicationAssessmentService(self.repo, self.reviews,
            AssessmentService(self.reader, self.inputs))

    def compare(self):
        return self.service.compare(self.ctx, 'reader', AssessmentSelection(self.environment_id, self.source.generation),
            'app-1', revision=1, record_digest=self.original.record_digest,
            profiles=(ApplicationMemberProfile('db', 'linux-uefi'), ApplicationMemberProfile('web', 'linux-uefi')),
            destinations=self.destinations, method='COLD_VM_CONVERSION', network_mode='routed', data_mode='offline')

    def test_persisted_signed_draft_is_compared_without_writing_a_job_or_revision(self):
        self.ingest(self.document())
        report = self.compare()
        self.assertEqual(report['status'], 'ASSESSED_NOT_AUTHORIZED')
        self.assertEqual(report['assessments'][0]['status'], 'BLOCKED')
        self.assertEqual(report['assessments'][0]['capacity']['resources']['VCPU']['required'], 8)
        self.assertEqual(report['assessments'][1]['status'], 'UNKNOWN')  # unresolved asserted dependency retained
        self.assertFalse(report['executionAuthorized']); self.assertFalse(report['reservationHeld'])
        with self.repo._session(self.ctx, self.scope, self.environment_id, self.authorize) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM hosting_controlplane.application_draft_revisions').fetchone()[0], 1)

    def test_unreviewed_real_draft_cannot_become_an_application_comparison(self):
        report = self.compare()
        self.assertEqual(report['status'], 'HELD_APPLICATION_REVIEW'); self.assertEqual(report['assessments'], [])

    def test_persisted_revocation_withholds_the_application(self):
        self.ingest(self.document()); self.ingest(self.document(decision='REVOKE', revision=2))
        report = self.compare()
        self.assertEqual(report['applicationReview']['status'], 'REVOKED'); self.assertEqual(report['assessments'], [])

    def test_owner_revocation_committed_during_assessment_discards_earlier_results(self):
        self.ingest(self.document())
        def revoke():
            self.inputs.after_findings = None
            self.ingest(self.document(decision='REVOKE', revision=2))
        self.inputs.after_findings = revoke
        with self.assertRaises(ApplicationReviewUnavailable): self.compare()

    def test_new_source_generation_holds_previously_signed_application(self):
        self.ingest(self.document())
        self._publish(self._campaign('new'), 'COMPLETE', (self._object('vm-1', 'Database'), self._object('vm-2', 'Frontend')))
        report = self.compare()
        self.assertEqual(report['applicationReview']['status'], 'HELD_SUPERSEDED_INVENTORY')
        self.assertEqual(report['assessments'], [])


if __name__ == '__main__': unittest.main()
