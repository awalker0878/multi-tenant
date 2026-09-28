"""Directed route comparison refuses unsupported, stale and borrowed evidence."""
from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.routes import (
    InstalledTuple, QualificationEvidence, RouteCatalogue, RouteClaim, RouteKey,
)

NOW = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)


def installation(site: str, family: str, digest: str) -> InstalledTuple:
    return InstalledTuple(
        PlanScope('org', 'tenant', site, 'wsd', site + '-endpoint',
                  site + '-native', family), site + '-product-v1', digest * 64)


SOURCE = installation('site-a', 'vmware', 'a')
TARGET = installation('site-b', 'openstack', 'b')
OTHER = installation('site-c', 'nutanix', 'c')
KEY = RouteKey(SOURCE, TARGET, 'COLD_VM_CONVERSION', 'linux-uefi',
               'routed-ipv4', 'offline-disks')


def proof(side: str, selected: InstalledTuple, digest: str) -> QualificationEvidence:
    return QualificationEvidence(
        side, selected, KEY.method, KEY.guest_profile, KEY.network_mode,
        KEY.data_mode, side.lower() + '-campaign', digest * 64,
        NOW - timedelta(days=1), NOW + timedelta(days=1))


class DirectedRouteTests(unittest.TestCase):
    def test_same_platform_relocation_is_not_a_cross_family_method(self):
        with self.assertRaises(ValueError):
            replace(KEY, method='SAME_PLATFORM_RELOCATION')
        same_family = replace(TARGET, scope=replace(TARGET.scope, platform_family='vmware'))
        route = replace(KEY, destination=same_family, method='SAME_PLATFORM_RELOCATION')
        self.assertEqual(RouteCatalogue().evaluate(route, as_of=NOW).status, 'UNKNOWN')

    def test_exact_direction_and_destination_only(self):
        catalogue = RouteCatalogue((RouteClaim(
            KEY, 'NATIVE_QUALIFIED', (proof('SOURCE_EXIT', SOURCE, '1'),
                                      proof('TARGET_OPERATE', TARGET, '2'))),))
        assessments = catalogue.compare_destinations(
            SOURCE, (TARGET, OTHER), method=KEY.method,
            guest_profile=KEY.guest_profile, network_mode=KEY.network_mode,
            data_mode=KEY.data_mode, as_of=NOW)
        self.assertEqual([item.status for item in assessments], ['CANDIDATE', 'UNKNOWN'])
        self.assertEqual(assessments[1].blockers, ('ROUTE_NOT_CATALOGUED',))
        self.assertFalse(any(item.execution_authorized for item in assessments))
        reverse = replace(KEY, source=TARGET, destination=SOURCE)
        self.assertEqual(catalogue.evaluate(reverse, as_of=NOW).status, 'UNKNOWN')
        changed_tuple = replace(TARGET, product_tuple_digest='d' * 64)
        self.assertEqual(catalogue.evaluate(
            replace(KEY, destination=changed_tuple), as_of=NOW).status, 'UNKNOWN')
        with self.assertRaises(ValueError):
            RouteKey(SOURCE, replace(SOURCE, product_tuple_digest='e' * 64),
                     KEY.method, KEY.guest_profile, KEY.network_mode, KEY.data_mode)

    def test_source_and_target_are_separate_time_bounded_proofs(self):
        source = proof('SOURCE_EXIT', SOURCE, '1')
        target = proof('TARGET_OPERATE', TARGET, '2')
        self.assertEqual(RouteCatalogue((RouteClaim(
            KEY, 'RELEASED', (source, target)),)).evaluate(KEY, as_of=NOW).status,
            'CANDIDATE')
        cases = (
            ((source,), 'TARGET_OPERATE_EVIDENCE_MISSING'),
            ((source, replace(target, installation=OTHER)),
             'TARGET_OPERATE_EVIDENCE_SCOPE_MISMATCH'),
            ((replace(source, guest_profile='windows-uefi'), target),
             'SOURCE_EXIT_EVIDENCE_SCOPE_MISMATCH'),
            ((source, replace(target, expires_at=NOW)),
             'TARGET_OPERATE_EVIDENCE_EXPIRED'),
            ((replace(source, observed_at=NOW + timedelta(minutes=1)), target),
             'SOURCE_EXIT_EVIDENCE_NOT_YET_VALID'),
            ((source, replace(target, evidence_digest=source.evidence_digest)),
             'SOURCE_TARGET_EVIDENCE_NOT_INDEPENDENT'),
        )
        for evidence, blocker in cases:
            with self.subTest(blocker=blocker):
                result = RouteCatalogue((RouteClaim(KEY, 'RELEASED', evidence),)).evaluate(
                    KEY, as_of=NOW)
                self.assertEqual(result.status, 'CONDITIONAL')
                self.assertIn(blocker, result.blockers)
                self.assertFalse(result.execution_authorized)

    def test_maturity_and_unsupported_are_not_execution_authority(self):
        source, target = proof('SOURCE_EXIT', SOURCE, '1'), proof('TARGET_OPERATE', TARGET, '2')
        reviewed = RouteCatalogue((RouteClaim(KEY, 'LAB_VERIFIED', (source, target)),))
        self.assertEqual(reviewed.evaluate(KEY, as_of=NOW).blockers,
                         ('ROUTE_NOT_NATIVE_QUALIFIED',))
        blocked = RouteCatalogue((RouteClaim(KEY, 'UNSUPPORTED'),))
        self.assertEqual(blocked.evaluate(KEY, as_of=NOW).status, 'BLOCKED')
        self.assertFalse(blocked.evaluate(KEY, as_of=NOW).execution_authorized)
        with self.assertRaises(ValueError):
            RouteCatalogue((RouteClaim(KEY, 'UNSUPPORTED'), RouteClaim(KEY, 'DESIGNED')))
        with self.assertRaises(ValueError):
            RouteClaim(KEY, 'UNSUPPORTED', (source,))
        with self.assertRaises(ValueError):
            RouteClaim(KEY, 'NATIVE_QUALIFIED', (source, source))


if __name__ == '__main__':
    unittest.main()
