"""Read-only destination assessment on exact observed and reviewed generations."""
from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.assessment import (
    AssessmentEngine, AssessmentScopeAccess, DestinationOption, ReviewedFinding,
)
from provisioner.controlplane.discovery.model import (
    DiscoveryFact, DiscoveryObject, DiscoveryResult, NativeIdentity,
)
from provisioner.controlplane.discovery.routes import (
    InstalledTuple, QualificationEvidence, RouteCatalogue, RouteClaim, RouteKey,
)

NOW = datetime(2026, 9, 27, 15, tzinfo=timezone.utc)


def installed(site: str, family: str, digest: str) -> InstalledTuple:
    return InstalledTuple(PlanScope('org', 'tenant', site, 'wsd',
                                    site + '-endpoint', site + '-scope', family),
                          site + '-product', digest * 64)


SOURCE = installed('site-a', 'vmware', 'a')
TARGET_B = installed('site-b', 'nutanix', 'b')
TARGET_C = installed('site-c', 'openstack', 'c')
VM = NativeIdentity('site-a-endpoint', 'site-a-scope', 'vmware', 'vm', 'vm-101')


def native(installation: InstalledTuple, kind: str, native_id: str) -> NativeIdentity:
    scope = installation.scope
    return NativeIdentity(scope.endpoint_id, scope.native_scope_id,
                          scope.platform_family, kind, native_id)


def fact_set(**values: object) -> tuple[DiscoveryFact, ...]:
    return tuple(DiscoveryFact.known(name, value)
                 for name, value in sorted(values.items()))


def source_snapshot(*, captured_at: datetime = NOW - timedelta(hours=1),
                    facts: tuple[DiscoveryFact, ...] | None = None,
                    complete: bool = True) -> DiscoveryResult:
    if facts is None:
        facts = fact_set(vcpuCount=4, memorySizeBytes=8_000,
                         diskCapacityBytes=20_000, guestProfile='linux-uefi',
                         networkMode='routed-ipv4', dataMode='offline-disks',
                         measuredTransferBytes=10_000)
    return DiscoveryResult('source-campaign', 'a' * 64, SOURCE.scope,
                           captured_at, 'COMPLETE' if complete else 'PARTIAL',
                           (DiscoveryObject(VM, facts),), (),
                           ('VM_CONFIG_READ',) if not complete else ())


def target_snapshot(installation: InstalledTuple, *,
                    captured_at: datetime = NOW - timedelta(hours=1),
                    capacity: dict | None = None,
                    complete: bool = True) -> tuple[DiscoveryResult, NativeIdentity]:
    identity = native(installation, 'pool', 'pool-1')
    values = dict(availableVcpu=24, availableMemoryBytes=120_000,
                  availableStorageBytes=900_000,
                  supportedGuestProfiles=['linux-uefi'],
                  supportedNetworkModes=['routed-ipv4'],
                  supportedDataModes=['offline-disks'],
                  measuredTransferBytesPerSecond=200)
    if capacity is not None:
        values = capacity
    return (DiscoveryResult(installation.scope.site_id + '-campaign', 'f' * 64,
                            installation.scope, captured_at,
                            'COMPLETE' if complete else 'UNKNOWN',
                            (DiscoveryObject(identity, fact_set(**values)),),
                            (), ()), identity)


def route(installation: InstalledTuple, method: str = 'COLD_VM_CONVERSION') -> RouteKey:
    return RouteKey(SOURCE, installation, method, 'linux-uefi',
                    'routed-ipv4', 'offline-disks')


def proof(key: RouteKey, side: str, digit: str) -> QualificationEvidence:
    installation = key.source if side == 'SOURCE_EXIT' else key.destination
    return QualificationEvidence(side, installation, key.method, key.guest_profile,
                                 key.network_mode, key.data_mode,
                                 side.lower() + '-' + installation.scope.site_id,
                                 digit * 64, NOW - timedelta(days=1),
                                 NOW + timedelta(days=1))


def claim(installation: InstalledTuple, maturity: str = 'NATIVE_QUALIFIED') -> RouteClaim:
    key = route(installation)
    return RouteClaim(key, maturity,
                      (proof(key, 'SOURCE_EXIT', '1'),
                       proof(key, 'TARGET_OPERATE',
                             '2' if installation == TARGET_B else '3')))


def findings(key: RouteKey, source: DiscoveryResult,
             target: DiscoveryResult) -> tuple[ReviewedFinding, ...]:
    return tuple(ReviewedFinding(control, key, source.digest, target.digest,
                                 'PASS', control.lower() + '-review', str(index) * 64,
                                 NOW - timedelta(minutes=30), NOW + timedelta(days=1))
                 for index, control in enumerate((
                     'POLICY_TRANSLATION', 'SECURITY_EQUIVALENCE',
                     'RECOVERY_READINESS'), 4))


def access(installation: InstalledTuple, purpose: str,
           actor: str = 'operator-1') -> AssessmentScopeAccess:
    return AssessmentScopeAccess(installation.scope, purpose, actor,
                                 purpose.lower() + '-' + installation.scope.site_id,
                                 NOW - timedelta(hours=2), NOW + timedelta(hours=1))


def option(installation: InstalledTuple, source: DiscoveryResult, *,
           target: DiscoveryResult | None = None,
           capacity_id: NativeIdentity | None = None,
           reviews: tuple[ReviewedFinding, ...] | None = None) -> DestinationOption:
    if target is None and capacity_id is None:
        target, capacity_id = target_snapshot(installation)
    return DestinationOption(installation, target, capacity_id,
                             findings(route(installation), source, target)
                             if reviews is None and target else reviews or (),
                             access(installation, 'DESTINATION_READ'))


def compare(engine: AssessmentEngine, source: DiscoveryResult,
            b: DestinationOption, c: DestinationOption, **extra):
    params = dict(method='COLD_VM_CONVERSION', guest_profile='linux-uefi',
                  network_mode='routed-ipv4', data_mode='offline-disks', as_of=NOW,
                  source_access=access(SOURCE, 'SOURCE_READ'))
    params.update(extra)
    # Deliberately submit in reverse order: stable output is keyed by tuple.
    return engine.compare(SOURCE, source, VM, (c, b), **params)


class AssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = source_snapshot()
        self.engine = AssessmentEngine(RouteCatalogue((claim(TARGET_B), claim(TARGET_C))))
        self.b = option(TARGET_B, self.source)
        self.c = option(TARGET_C, self.source)

    def test_two_exact_destinations_have_stable_read_only_comparison(self):
        result = compare(self.engine, self.source, self.b, self.c)
        self.assertEqual([item.destination for item in result], [TARGET_B, TARGET_C])
        self.assertEqual([item.status for item in result], ['ELIGIBLE', 'ELIGIBLE'])
        self.assertTrue(all(not item.execution_authorized for item in result))
        self.assertEqual(result[0].estimate.transfer_bytes, 10_000)
        self.assertEqual(result[0].estimate.copy_phase_seconds, 50)
        self.assertEqual(result[0].estimate.confidence, 'LOW')
        self.assertEqual(result[0].to_document()['executionAuthorized'], False)
        self.assertNotIn('downtimeSeconds', result[0].to_document()['estimate'])
        self.assertEqual(compare(self.engine, self.source, self.b, self.c), result)

    def test_unknown_observations_and_controls_never_become_eligible(self):
        missing_source = source_snapshot(facts=(
            DiscoveryFact.known('memorySizeBytes', 8000),
            DiscoveryFact.known('diskCapacityBytes', 20000),
            DiscoveryFact.unknown('guestProfile', 'NOT_RETURNED')),
            complete=False)
        target, capacity_id = target_snapshot(TARGET_B, capacity={
            'availableVcpu': 24, 'availableMemoryBytes': 120_000,
            'availableStorageBytes': 900_000,
            'supportedGuestProfiles': ['linux-uefi'],
            'supportedNetworkModes': ['routed-ipv4'],
            # Explicitly omitted supportedDataModes.
        })
        b = DestinationOption(TARGET_B, target, capacity_id, (),
                              access(TARGET_B, 'DESTINATION_READ'))
        b_result = compare(self.engine, missing_source, b, self.c)[0]
        self.assertEqual(b_result.status, 'UNKNOWN')
        self.assertIn('SOURCE_SNAPSHOT_INCOMPLETE', b_result.unknowns)
        self.assertIn('SOURCE_VCPU_UNKNOWN', b_result.unknowns)
        self.assertIn('SOURCE_GUEST_UNKNOWN', b_result.unknowns)
        self.assertIn('SUPPORTEDDATAMODES_UNKNOWN', b_result.unknowns)
        self.assertIn('POLICY_TRANSLATION_EVIDENCE_MISSING', b_result.unknowns)
        self.assertTrue(all(issue.remediation for issue in b_result.issues))

    def test_hard_capacity_guest_and_review_failures_block(self):
        target, capacity_id = target_snapshot(TARGET_B, capacity={
            'availableVcpu': 2, 'availableMemoryBytes': 120_000,
            'availableStorageBytes': 900_000,
            'supportedGuestProfiles': ['windows-uefi'],
            'supportedNetworkModes': ['routed-ipv4'],
            'supportedDataModes': ['offline-disks'],
        })
        reviews = findings(route(TARGET_B), self.source, target)
        rejected = replace(reviews[1], outcome='FAIL')
        b = DestinationOption(TARGET_B, target, capacity_id,
                              (reviews[0], rejected, reviews[2]),
                              access(TARGET_B, 'DESTINATION_READ'))
        assessed = compare(self.engine, self.source, b, self.c)[0]
        self.assertEqual(assessed.status, 'BLOCKED')
        self.assertIn('CAPACITY_VCPU_INSUFFICIENT', assessed.blockers)
        self.assertIn('GUEST_UNSUPPORTED', assessed.blockers)
        self.assertIn('SECURITY_EQUIVALENCE_FAILED', assessed.blockers)

    def test_stale_borrowed_and_unqualified_route_evidence(self):
        stale_source = source_snapshot(captured_at=NOW - timedelta(days=2))
        b = option(TARGET_B, stale_source)
        self.assertIn('SOURCE_SNAPSHOT_STALE',
                      compare(self.engine, stale_source, b, self.c)[0].unknowns)
        target, capacity_id = target_snapshot(TARGET_B)
        borrowed = findings(route(TARGET_B), self.source, target)
        borrowed = (replace(borrowed[0], route=route(TARGET_C)), *borrowed[1:])
        b = DestinationOption(TARGET_B, target, capacity_id, borrowed,
                              access(TARGET_B, 'DESTINATION_READ'))
        self.assertIn('POLICY_TRANSLATION_SCOPE_MISMATCH',
                      compare(self.engine, self.source, b, self.c)[0].unknowns)
        preview = AssessmentEngine(RouteCatalogue((claim(TARGET_B, 'DESIGNED'),
                                                   claim(TARGET_C))))
        self.assertEqual(compare(preview, self.source, self.b, self.c)[0].status,
                         'CONDITIONAL')
        self.assertIn('ROUTE_NOT_NATIVE_QUALIFIED',
                      compare(preview, self.source, self.b, self.c)[0].conditions)

    def test_unsupported_method_and_uncatalogued_direction(self):
        unsupported = compare(self.engine, self.source, self.b, self.c,
                              method='UNSUPPORTED_METHOD')
        self.assertEqual([item.status for item in unsupported], ['BLOCKED', 'BLOCKED'])
        self.assertIn('METHOD_UNSUPPORTED', unsupported[0].blockers)
        uncatalogued = AssessmentEngine(RouteCatalogue((claim(TARGET_C),)))
        b_result = compare(uncatalogued, self.source, self.b, self.c)[0]
        self.assertEqual(b_result.status, 'UNKNOWN')
        self.assertIn('ROUTE_NOT_CATALOGUED', b_result.unknowns)

    def test_cross_tenant_and_ungranted_native_target_fail_closed(self):
        no_target_access = replace(self.b, access=None)
        assessed = compare(self.engine, self.source, no_target_access, self.c)[0]
        self.assertEqual(assessed.status, 'UNKNOWN')
        self.assertIn('DESTINATION_ACCESS_UNVERIFIED', assessed.unknowns)
        wrong_actor = replace(self.b, access=access(TARGET_B, 'DESTINATION_READ',
                                                   'somebody-else'))
        assessed = compare(self.engine, self.source, wrong_actor, self.c)[0]
        self.assertEqual(assessed.status, 'BLOCKED')
        self.assertIn('DESTINATION_ACCESS_SCOPE_MISMATCH', assessed.blockers)
        wrong_wsd = replace(self.b, access=AssessmentScopeAccess(
            replace(TARGET_B.scope, security_domain_id='other-wsd'),
            'DESTINATION_READ', 'operator-1', 'other-wsd-grant',
            NOW - timedelta(hours=1), NOW + timedelta(hours=1)))
        assessed = compare(self.engine, self.source, wrong_wsd, self.c)[0]
        self.assertIn('DESTINATION_ACCESS_SCOPE_MISMATCH', assessed.blockers)
        other_tenant = installed('site-d', 'nutanix', 'd')
        other_tenant = replace(other_tenant,
                               scope=replace(other_tenant.scope, tenant_id='other-tenant'))
        target, capacity_id = target_snapshot(other_tenant)
        cross_tenant = DestinationOption(other_tenant, target, capacity_id, (),
                                         access(other_tenant, 'DESTINATION_READ'))
        assessed = next(item for item in compare(self.engine, self.source,
                                                 cross_tenant, self.c)
                        if item.destination == other_tenant)
        self.assertEqual(assessed.status, 'BLOCKED')
        self.assertIn('CROSS_TENANT_DESTINATION', assessed.blockers)

    def test_cross_scope_inputs_and_duplicate_targets_are_rejected(self):
        foreign, identity = target_snapshot(TARGET_C)
        with self.assertRaises(ValueError):
            DestinationOption(TARGET_B, foreign, identity)
        with self.assertRaises(ValueError):
            DestinationOption(TARGET_B, self.b.inventory, identity)
        with self.assertRaises(ValueError):
            self.engine.compare(SOURCE, self.source, VM, (self.b, self.b),
                                method='COLD_VM_CONVERSION', guest_profile='linux-uefi',
                                network_mode='routed-ipv4', data_mode='offline-disks',
                                as_of=NOW, source_access=access(SOURCE, 'SOURCE_READ'))
        with self.assertRaises(ValueError):
            self.engine.compare(SOURCE, foreign, VM, (self.b, self.c),
                                method='COLD_VM_CONVERSION', guest_profile='linux-uefi',
                                network_mode='routed-ipv4', data_mode='offline-disks',
                                as_of=NOW, source_access=access(SOURCE, 'SOURCE_READ'))


if __name__ == '__main__':
    unittest.main()
