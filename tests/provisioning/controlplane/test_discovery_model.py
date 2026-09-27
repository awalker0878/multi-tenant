"""The inventory contract rejects incomplete enumeration and foreign objects."""
from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.model import (
    DiscoveryCampaignAuthorization, DiscoveryFact, DiscoveryObject,
    DiscoveryPage, NativeIdentity, assemble_discovery_result,
)


START = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
SCOPE = PlanScope('org-01', 'tenant-01', 'site-01', 'wsd-01',
                  'endpoint-01', 'project-01', 'openstack')


def campaign(**changes):
    return replace(DiscoveryCampaignAuthorization(
        'campaign-01', SCOPE, 'approved-read-01', 'collector-01',
        ('vm', 'volume'), START, START + timedelta(minutes=15),
        4, 5, 2), **changes)


def obj(native_id='vm-01', *, kind='vm', scope=SCOPE, facts=None):
    return DiscoveryObject(
        NativeIdentity(scope.endpoint_id, scope.native_scope_id,
                       scope.platform_family, kind, native_id),
        facts or (DiscoveryFact.known('name', 'server-one'),
                  DiscoveryFact.known('cpuCount', 4)))


def page(number=1, *, requested=None, next_cursor=None, objects=None,
         completeness='COMPLETE', scope=SCOPE, errors=(), privileges=()):
    return DiscoveryPage('campaign-01', scope, number, requested,
                         next_cursor, START + timedelta(minutes=number),
                         (obj(),) if objects is None else objects,
                         completeness, errors, privileges)


class DiscoveryModelTests(unittest.TestCase):
    def test_pages_bind_exact_scope_cursor_budget_and_canonical_digest(self):
        first = page(next_cursor='Opaque/Page:2', completeness=None)
        second = page(2, requested='Opaque/Page:2', objects=(
            obj('vol-01', kind='volume'),), completeness='COMPLETE')
        result = assemble_discovery_result(
            campaign(), (first, second), checked_at=START + timedelta(minutes=3))
        self.assertEqual(result.completeness, 'COMPLETE')
        self.assertEqual(len(result.objects), 2)
        self.assertEqual(len(result.digest), 64)
        self.assertEqual(result.authorization_digest, campaign().digest())
        self.assertEqual(result.digest, assemble_discovery_result(
            campaign(), (first, second),
            checked_at=START + timedelta(minutes=4)).digest)
        self.assertNotEqual(result.digest, assemble_discovery_result(
            campaign(authority_reference='other-approved-read'),
            (first, second), checked_at=START + timedelta(minutes=3)).digest)
        with self.assertRaises(FrozenInstanceError):
            result.completeness = 'PARTIAL'
        with self.assertRaises(ValueError):
            assemble_discovery_result(campaign(), (first, replace(
                second, requested_cursor='forged')),
                checked_at=START + timedelta(minutes=3))

    def test_missing_privilege_or_error_never_claims_complete_inventory(self):
        missing = DiscoveryFact.unknown(
            'disks', 'MISSING_PRIVILEGE', required_privilege='volume.read')
        partial = page(objects=(obj(facts=(missing,)),),
                       completeness='PARTIAL', privileges=('volume.read',))
        result = assemble_discovery_result(
            campaign(), (partial,), checked_at=START + timedelta(minutes=2))
        self.assertEqual(result.completeness, 'PARTIAL')
        self.assertEqual(result.missing_privileges, ('volume.read',))
        with self.assertRaises(ValueError):
            assemble_discovery_result(campaign(), (
                replace(partial, terminal_completeness='COMPLETE'),),
                checked_at=START + timedelta(minutes=2))
        with self.assertRaises(ValueError):
            page(objects=(obj(facts=(missing,)),), completeness='PARTIAL')
        with self.assertRaises(ValueError):
            assemble_discovery_result(campaign(), (
                page(errors=('PAGE_FAILED',), completeness='COMPLETE'),),
                checked_at=START + timedelta(minutes=2))

    def test_duplicate_foreign_and_unapproved_native_identities_rejected(self):
        with self.assertRaises(ValueError):
            page(objects=(obj(), obj()))
        foreign = replace(SCOPE, native_scope_id='other-project')
        with self.assertRaises(ValueError):
            page(objects=(obj(scope=foreign),))
        first = page(next_cursor='two', completeness=None)
        duplicate = page(2, requested='two')
        with self.assertRaises(ValueError):
            assemble_discovery_result(campaign(), (first, duplicate),
                                      checked_at=START + timedelta(minutes=3))
        with self.assertRaises(ValueError):
            assemble_discovery_result(campaign(), (
                page(objects=(obj(kind='host'),)),),
                checked_at=START + timedelta(minutes=2))

    def test_expiry_page_size_total_budget_and_incomplete_chain(self):
        empty = assemble_discovery_result(campaign(), (
            page(objects=()),), checked_at=START + timedelta(minutes=2))
        self.assertEqual((empty.completeness, empty.objects), ('COMPLETE', ()))
        with self.assertRaises(ValueError):
            assemble_discovery_result(campaign(max_page_size=1), (
                page(objects=(obj(), obj('vm-02'))),),
                checked_at=START + timedelta(minutes=2))
        with self.assertRaises(ValueError):
            assemble_discovery_result(campaign(max_objects=1), (
                page(objects=(obj(), obj('vm-02'))),),
                checked_at=START + timedelta(minutes=2))
        with self.assertRaises(ValueError):
            assemble_discovery_result(campaign(max_pages=1), (
                page(next_cursor='two', completeness=None),
                page(2, requested='two', objects=())),
                checked_at=START + timedelta(minutes=3))
        with self.assertRaises(ValueError):
            assemble_discovery_result(campaign(), (
                page(next_cursor='two', completeness=None),),
                checked_at=START + timedelta(minutes=2))
        with self.assertRaises(ValueError):
            assemble_discovery_result(campaign(), (page(),),
                                      checked_at=START + timedelta(minutes=15))
        with self.assertRaises(ValueError):
            assemble_discovery_result(campaign(), (
                page(next_cursor='loop', completeness=None),
                page(2, requested='loop', next_cursor='again',
                     objects=(), completeness=None),
                page(3, requested='again', next_cursor='loop',
                     objects=(), completeness=None),
                page(4, requested='loop', objects=())),
                checked_at=START + timedelta(minutes=5))

    def test_fact_value_is_immutable_and_campaign_is_not_a_b10_grant(self):
        source = {'disks': [{'id': 'disk-01'}]}
        fact = DiscoveryFact.known('deviceInventory', source)
        source['disks'][0]['id'] = 'replaced'
        returned = fact.value()
        returned['disks'][0]['id'] = 'changed-again'
        self.assertEqual(fact.value(), {'disks': [{'id': 'disk-01'}]})
        with self.assertRaises(ValueError):
            DiscoveryFact('field', 'KNOWN', '{"b":2,"a":1}')
        with self.assertRaises(ValueError):
            assemble_discovery_result({'grantId': 'job-grant'}, (page(),),
                                      checked_at=START + timedelta(minutes=2))
        with self.assertRaises(ValueError):
            campaign(expires_at=START + timedelta(hours=2))


if __name__ == '__main__':
    unittest.main()
