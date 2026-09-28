from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.assessment import AssessmentScopeAccess, ReviewedFinding
from provisioner.controlplane.discovery.model import (
    DiscoveryFact, DiscoveryObject, DiscoveryResult, NativeIdentity, _digest, _object_json)
from provisioner.controlplane.discovery.normalization import NormalizationHeld
from provisioner.controlplane.discovery.persistence import StoredGeneration, StoredObservation
from provisioner.controlplane.discovery.routes import (
    InstalledTuple, QualificationEvidence, RouteClaim)
from provisioner.controlplane.discovery.service import (
    AssessmentDestination, AssessmentSelection, AssessmentService, VerifiedAssessmentEnvironment)
from provisioner.controlplane.persistence.store import TenantContext


NOW = datetime(2026, 9, 28, 15, tzinfo=timezone.utc)
CTX = TenantContext('org', 'tenant')


def installation(name, family):
    return InstalledTuple(PlanScope('org', 'tenant', name, 'wsd', name + '-endpoint',
                                    name + '-scope', family), name + '-tuple', 'a' * 64)


INSTALLATIONS = {'source': installation('source', 'vmware'),
                 'target-a': installation('target-a', 'vmware'),
                 'target-b': installation('target-b', 'nutanix')}


def inventory(name, *, at=NOW - timedelta(minutes=30), partial=False):
    scope = INSTALLATIONS[name].scope
    if name == 'source':
        kind, native_id = 'vm', 'vm-1'
        values = {'vcpuCount': 4, 'memorySizeBytes': 8000, 'diskCapacityBytes': 20000,
                  'guestProfile': 'linux-uefi', 'networkMode': 'routed', 'dataMode': 'offline',
                  'nics': [{'extId': 'nic-1', 'subnetExtId': 'subnet-1'}]}
    else:
        kind, native_id = 'pool', 'pool-1'
        values = {'availableVcpu': 16, 'availableMemoryBytes': 100000,
                  'availableStorageBytes': 100000, 'supportedGuestProfiles': ['linux-uefi'],
                  'supportedNetworkModes': ['routed'], 'supportedDataModes': ['offline']}
    obj = DiscoveryObject(NativeIdentity(scope.endpoint_id, scope.native_scope_id,
                                         scope.platform_family, kind, native_id),
                          tuple(DiscoveryFact.known(key, value) for key, value in values.items()))
    return DiscoveryResult(name + '-campaign', 'a' * 64, scope, at,
                           'PARTIAL' if partial else 'COMPLETE', (obj,),
                           ('PAGE_UNAVAILABLE',) if partial else (), ())


class Repository:
    """In-memory test double for verified append-only storage, not a provider."""

    def __init__(self):
        self.results = {(name, 7): inventory(name) for name in INSTALLATIONS}
        self.reads = []
        self.header_patch = {}
        self.drop_last = False

    def get_generation(self, ctx, scope, environment_id, generation):
        self.reads.append((environment_id, generation, 'header'))
        result = self.results.get((environment_id, generation))
        if result is None:
            return None
        assert result.scope == scope
        return replace(StoredGeneration(environment_id, generation, result.campaign_id,
                                         result.scope, result.authorization_digest, result.digest,
                                         result.captured_at, result.completeness,
                                         result.collection_errors, result.missing_privileges,
                                         len(result.objects)), **self.header_patch)

    def list_observations(self, ctx, scope, environment_id, generation, *, after=None, limit=51):
        self.reads.append((environment_id, generation, 'objects'))
        result = self.results[environment_id, generation]
        objects = sorted(result.objects, key=lambda obj: obj.identity.key())
        if self.drop_last:
            objects = objects[:-1]
        objects = [obj for obj in objects if after is None or
                   (obj.identity.resource_kind, obj.identity.native_id) > after][:limit]
        return [StoredObservation(generation, obj.identity, tuple(_object_json(obj)['facts']),
                                   _digest(_object_json(obj))) for obj in objects]


class VerifiedInputs:
    """Explicit test verifier; production requires independent backing systems."""

    def __init__(self):
        self.denied = None
        self.expired = None
        self.wrong_actor = None
        self.qualified = False
        self.raw_review = False
        self.calls = []

    def resolve_environment(self, ctx, actor_subject, environment_id, purpose, as_of):
        self.calls.append(environment_id)
        if environment_id == self.denied:
            raise PermissionError('not authorized')
        installed = INSTALLATIONS[environment_id]
        return VerifiedAssessmentEnvironment(environment_id, installed, AssessmentScopeAccess(
            installed.scope, purpose, 'someone-else' if self.wrong_actor == environment_id
            else actor_subject, 'access-review', as_of - timedelta(hours=1),
            as_of if environment_id == self.expired else as_of + timedelta(hours=1)))

    def route_claims(self, ctx, actor_subject, routes, as_of):
        if not self.qualified:
            return ()
        return tuple(RouteClaim(route, 'NATIVE_QUALIFIED', tuple(QualificationEvidence(
            side, installed, route.method, route.guest_profile, route.network_mode, route.data_mode,
            side.lower() + '-test-proof', digit * 64,
            as_of - timedelta(hours=1), as_of + timedelta(hours=1))
            for side, installed, digit in (('SOURCE_EXIT', route.source, '1'),
                                           ('TARGET_OPERATE', route.destination, '2'))))
            for route in routes)

    def reviewed_findings(self, ctx, actor_subject, route, source, destination, as_of):
        if not self.qualified or source is None or destination is None:
            return ()
        a = source.original if self.raw_review else source.inventory
        b = destination.original if self.raw_review else destination.inventory
        return tuple(ReviewedFinding(control, route, a.digest, b.digest, 'PASS',
                                     control.lower() + '-test-review', str(index) * 64,
                                     as_of - timedelta(minutes=1), as_of + timedelta(hours=1))
                     for index, control in enumerate(('POLICY_TRANSLATION', 'SECURITY_EQUIVALENCE',
                                                       'RECOVERY_READINESS'), 4))


class AssessmentServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = Repository()
        self.inputs = VerifiedInputs()
        self.service = AssessmentService(self.repository, self.inputs, clock=lambda: NOW)

    def compare(self, **options):
        params = {'method': 'COLD_VM_CONVERSION', 'guest_profile': 'linux-uefi',
                  'network_mode': 'routed', 'data_mode': 'offline'}
        params.update(options)
        return self.service.compare(CTX, 'operator-1', AssessmentSelection('source', 7), 'vm-1',
                                    tuple(AssessmentDestination(AssessmentSelection(name, 7),
                                                                'pool', 'pool-1')
                                          for name in ('target-a', 'target-b')), **params)

    def test_explicit_pins_support_same_and_cross_family_without_making_qualification(self):
        self.repository.results['source', 8] = inventory('source', at=NOW)
        result = self.compare()
        self.assertEqual([item.status for item in result.assessments], ['UNKNOWN', 'UNKNOWN'])
        self.assertEqual([item.destination.scope.platform_family for item in result.assessments],
                         ['vmware', 'nutanix'])
        self.assertTrue(all('ROUTE_NOT_CATALOGUED' in item.unknowns for item in result.assessments))
        self.assertTrue(all(read[1] == 7 for read in self.repository.reads))
        document = result.to_document()
        self.assertFalse(document['executionAuthorized'])
        self.assertEqual(document['sourceInput']['generation'], 7)
        self.assertNotEqual(document['sourceInput']['observation']['rawSnapshotDigest'],
                            document['sourceInput']['observation']['assessmentSnapshotDigest'])

    def test_eligibility_requires_verified_routes_and_normalized_snapshot_bound_reviews(self):
        self.inputs.qualified = True
        result = self.compare()
        self.assertEqual([item.status for item in result.assessments], ['ELIGIBLE', 'ELIGIBLE'])
        self.assertTrue(all(not item.execution_authorized for item in result.assessments))
        self.inputs.raw_review = True
        result = self.compare()
        self.assertEqual(result.assessments[0].status, 'UNKNOWN')
        self.assertIn('POLICY_TRANSLATION_SCOPE_MISMATCH', result.assessments[0].unknowns)

    def test_all_read_scopes_authorized_before_any_repository_access(self):
        for field in ('denied', 'expired', 'wrong_actor'):
            with self.subTest(field=field):
                setattr(self.inputs, field, 'target-b')
                with self.assertRaises(PermissionError):
                    self.compare()
                self.assertEqual(self.repository.reads, [])
                setattr(self.inputs, field, None)

    def test_missing_stale_and_partial_generation_are_visible_unknowns(self):
        self.repository.results.pop(('source', 7))
        result = self.compare()
        self.assertIn('SOURCE_SNAPSHOT_MISSING', result.assessments[0].unknowns)
        self.repository.results['source', 7] = inventory('source', at=NOW - timedelta(days=2))
        result = self.compare()
        self.assertIn('SOURCE_SNAPSHOT_STALE', result.assessments[0].unknowns)
        self.repository.results['source', 7] = inventory('source', partial=True)
        result = self.compare()
        self.assertIn('SOURCE_SNAPSHOT_INCOMPLETE', result.assessments[0].unknowns)

    def test_wrong_scope_or_truncated_repository_snapshot_fails_closed(self):
        for patch in ({'generation': 8}, {'environment_id': 'other'},
                      {'scope': replace(INSTALLATIONS['source'].scope, tenant_id='other')}):
            with self.subTest(patch=patch):
                self.repository.header_patch = patch
                with self.assertRaises(NormalizationHeld):
                    self.compare()
        self.repository.header_patch = {}
        self.repository.drop_last = True
        with self.assertRaises(NormalizationHeld):
            self.compare()

    def test_large_generation_consumes_bounded_pages_and_verifies_full_digest(self):
        original = self.repository.results['source', 7]
        objects = tuple(replace(original.objects[0], identity=replace(
            original.objects[0].identity, native_id=f'vm-{index}')) for index in range(205))
        self.repository.results['source', 7] = replace(original, objects=objects)
        result = self.compare()
        self.assertEqual(len(result.source.discovery.original.objects), 205)
        self.assertEqual(sum(1 for read in self.repository.reads
                             if read == ('source', 7, 'objects')), 3)

    def test_trusted_input_provider_is_mandatory(self):
        with self.assertRaises(ValueError):
            AssessmentService(self.repository, None)

    def test_opaque_oidc_actor_subject_is_not_restricted_to_record_ids(self):
        for actor in ('editor@example.org', 'auth0|federated-operator'):
            with self.subTest(actor=actor):
                result = self.service.compare(CTX, actor, AssessmentSelection('source', 7), 'vm-1',
                    tuple(AssessmentDestination(AssessmentSelection(name, 7), 'pool', 'pool-1')
                          for name in ('target-a', 'target-b')),
                    method='COLD_VM_CONVERSION', guest_profile='linux-uefi',
                    network_mode='routed', data_mode='offline')
                self.assertEqual(len(result.assessments), 2)


if __name__ == '__main__':
    unittest.main()
