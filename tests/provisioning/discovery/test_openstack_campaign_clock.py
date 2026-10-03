"""An expired discovery campaign cannot authorize even the first native read."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from provisioner.controlplane.discovery.adapters.openstack import (
    OpenStackDiscoveryHeld, collect_openstack_project)
from tests.provisioning.discovery.test_openstack import ENDPOINTS, FakeTransport, campaign


class OpenStackCampaignClockTests(unittest.TestCase):
    def test_expired_campaign_never_contacts_native_transport(self):
        now = datetime.now(timezone.utc)
        expired = replace(campaign(), issued_at=now - timedelta(minutes=20),
                          expires_at=now - timedelta(minutes=1))
        transport = FakeTransport()
        with self.assertRaises(OpenStackDiscoveryHeld):
            collect_openstack_project(expired, ENDPOINTS, transport)
        self.assertEqual(transport.calls, [])

    def test_future_naive_non_utc_and_invalid_clocks_never_read(self):
        authority = campaign()
        for at in (authority.issued_at - timedelta(seconds=1),
                   datetime.now(), datetime.now(timezone(timedelta(hours=1))), None):
            with self.subTest(at=at):
                transport = FakeTransport()
                with self.assertRaises(OpenStackDiscoveryHeld):
                    collect_openstack_project(authority, ENDPOINTS, transport, clock=lambda: at)
                self.assertEqual(transport.calls, [])

    def test_expiry_before_each_collection_or_quota_read_sends_no_request(self):
        for allowed in range(6):
            with self.subTest(allowed_reads=allowed):
                authority, transport = campaign(), FakeTransport()
                # Initial check; each completed read has pre/post/append checks.
                values = iter([authority.issued_at] * (1 + 3 * allowed)
                              + [authority.expires_at])
                with self.assertRaises(OpenStackDiscoveryHeld):
                    collect_openstack_project(authority, ENDPOINTS, transport,
                                              clock=lambda: next(values))
                self.assertEqual(len(transport.calls), allowed)

    def test_late_native_success_and_error_cannot_publish(self):
        for fail in (False, True):
            with self.subTest(error=fail):
                authority, transport = campaign(), FakeTransport()
                now = [authority.issued_at]
                original = transport.get_json
                def late(*args):
                    result = original(*args)
                    now[0] = authority.expires_at
                    if fail:
                        raise RuntimeError('native failure')
                    return result
                transport.get_json = late
                with self.assertRaises(OpenStackDiscoveryHeld):
                    collect_openstack_project(authority, ENDPOINTS, transport, clock=lambda: now[0])
                self.assertEqual(len(transport.calls), 1)

    def test_backward_clock_stops_before_next_native_request(self):
        authority, transport = campaign(), FakeTransport()
        now = authority.issued_at + timedelta(seconds=10)
        values = iter([now, now, now, now, now - timedelta(seconds=1)])
        with self.assertRaises(OpenStackDiscoveryHeld):
            collect_openstack_project(authority, ENDPOINTS, transport,
                                      clock=lambda: next(values))
        self.assertEqual(len(transport.calls), 1)

    def test_exact_expiry_boundary_is_not_valid(self):
        authority, transport = campaign(), FakeTransport()
        with self.assertRaises(OpenStackDiscoveryHeld):
            collect_openstack_project(authority, ENDPOINTS, transport,
                                      clock=lambda: authority.expires_at)
        self.assertEqual(transport.calls, [])


if __name__ == '__main__':
    unittest.main()
