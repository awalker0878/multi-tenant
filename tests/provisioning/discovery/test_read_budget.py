"""Actual concurrent admission plus native TLS, not installed site qualification."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import threading
import time
import unittest
from unittest.mock import patch

from provisioner.controlplane.discovery.read_budget import EndpointReadPolicy, NativeReadGate
from provisioner.controlplane.discovery.native_credentials import NativeReadHeld
from provisioner.controlplane.discovery import native_https
from tests.provisioning.discovery import test_ahv_https as ahv_fixture


def policy(**changes):
    p = EndpointReadPolicy('org-1', 'site-1', 'nutanix', 'endpoint-1', 2, 10)
    return replace(p, **changes)


class ReadBudgetTests(unittest.TestCase):
    def test_policy_rejects_unknown_endpoints_booleans_overflow_and_unbounded_limits(self):
        for change in ({'max_concurrent': True}, {'max_concurrent': 0}, {'max_concurrent': 17},
                       {'min_interval_ms': 0}, {'min_interval_ms': 15001}, {'min_interval_ms': 1.5},
                       {'platform_family': 'other'}, {'organization_id': ''}, {'endpoint_id': '../x'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                policy(**change)

    def test_limit_is_shared_and_started_reads_are_spaced(self):
        gate = NativeReadGate(policy())
        active = peak = 0
        starts = []
        lock = threading.Lock()
        def work():
            nonlocal active, peak
            with gate.permit(time.monotonic() + 5, lambda: None):
                with lock:
                    active += 1; peak = max(peak, active); starts.append(time.monotonic())
                time.sleep(.04)
                with lock:
                    active -= 1
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda _: work(), range(12)))
        self.assertEqual(peak, 2)
        self.assertEqual(gate._active, 0)
        self.assertEqual(len(gate._pending), 0)
        self.assertTrue(all(b - a >= .009 for a, b in zip(starts, starts[1:])))

    def test_waiting_reader_times_out_without_admission_and_later_reader_can_proceed(self):
        gate = NativeReadGate(policy(max_concurrent=1))
        with gate.permit(time.monotonic() + 1, lambda: None):
            with ThreadPoolExecutor(max_workers=1) as pool:
                def blocked():
                    with gate.permit(time.monotonic() + .08, lambda: None):
                        self.fail('Queued read should not start')
                with self.assertRaises(NativeReadHeld):
                    pool.submit(blocked).result(timeout=1)
        with gate.permit(time.monotonic() + 1, lambda: None):
            self.assertEqual(gate._active, 1)

    def test_current_authority_is_rechecked_while_waiting(self):
        gate = NativeReadGate(policy(max_concurrent=1))
        queued = threading.Event(); revoked = threading.Event()
        def authorize():
            queued.set()
            if revoked.is_set():
                raise NativeReadHeld('Revoked')
        with gate.permit(time.monotonic() + 2, lambda: None):
            with ThreadPoolExecutor(max_workers=1) as pool:
                def read():
                    with gate.permit(time.monotonic() + 2, authorize):
                        self.fail('Revoked reader cannot enter')
                future = pool.submit(read)
                self.assertTrue(queued.wait(1)); revoked.set()
                with self.assertRaises(NativeReadHeld):
                    future.result(timeout=1)
        self.assertEqual(len(gate._pending), 0)

    def test_failures_release_concurrency_but_do_not_refund_the_rate_slot(self):
        gate = NativeReadGate(policy(min_interval_ms=100))
        with self.assertRaises(RuntimeError):
            with gate.permit(time.monotonic() + 1, lambda: None):
                first = time.monotonic()
                raise RuntimeError('Native failure')
        with gate.permit(time.monotonic() + 1, lambda: None):
            self.assertGreaterEqual(time.monotonic() - first, .09)
        self.assertEqual(gate._active, 0)

    def test_revocation_immediately_after_admission_releases_the_slot(self):
        gate = NativeReadGate(policy())
        calls = 0
        def authorize():
            nonlocal calls
            calls += 1
            if calls == 2:
                raise NativeReadHeld('Revoked after admission')
        with self.assertRaises(NativeReadHeld):
            with gate.permit(time.monotonic() + 1, authorize):
                self.fail('Must not enter')
        self.assertEqual(gate._active, 0)

    def test_stop_refuses_new_and_waiting_reads(self):
        stop = threading.Event(); gate = NativeReadGate(policy(), stopped=stop); stop.set()
        with self.assertRaises(NativeReadHeld):
            with gate.permit(time.monotonic() + 1, lambda: None):
                self.fail('Stopped gate')
        self.assertEqual(len(gate._pending), 0)

    def test_deadline_must_be_finite_and_not_a_boolean(self):
        for deadline in (True, float('inf'), float('nan'), '1'):
            with self.subTest(deadline=deadline), self.assertRaises(NativeReadHeld):
                with NativeReadGate(policy()).permit(deadline, lambda: None):
                    self.fail('Invalid deadline')

    def test_endpoint_scope_includes_organization_site_and_platform(self):
        p = policy(); gate = NativeReadGate(p)
        gate.require_scope(p)
        for change in ({'site_id': 'other'}, {'organization_id': 'other'},
                       {'platform_family': 'vmware'}, {'endpoint_id': 'other'}):
            with self.assertRaises(NativeReadHeld):
                gate.require_scope(replace(p, **change))


class NativeReadBudgetTlsTests(unittest.TestCase):
    def setUp(self):
        self.native = ahv_fixture.AhvHttpsTests(); self.native.setUp(); self.addCleanup(self.native.doCleanups)
        s = self.native.campaign.scope
        self.gate = NativeReadGate(EndpointReadPolicy(s.organization_id, s.site_id, s.platform_family,
                                                     s.endpoint_id, 1, 50))

    def test_actual_native_gets_use_shared_rate_and_leave_no_held_slot(self):
        starts = []
        self.native.on_get = lambda: starts.append(time.monotonic())
        pages = self.native.client(read_gate=self.gate).collect()
        self.assertEqual(len(self.native.calls), 2)
        self.assertEqual(len(pages), 2)
        self.assertGreaterEqual(starts[1] - starts[0], .04)
        self.assertEqual(self.gate._active, 0)

    def test_blocked_read_never_connects_and_retains_original_deadline(self):
        with self.gate.permit(time.monotonic() + 1, lambda: None):
            with patch.object(native_https.socket, 'create_connection', side_effect=AssertionError('Must not connect')) as connect:
                with self.assertRaises(NativeReadHeld):
                    self.native.client(read_gate=self.gate, timeout=.05).collect()
                connect.assert_not_called()
        self.assertFalse(self.native.calls)

    def test_wrong_gate_scope_is_refused_before_native_contact(self):
        other = NativeReadGate(replace(self.gate.policy, endpoint_id='other'))
        with self.assertRaises(NativeReadHeld):
            self.native.client(read_gate=other)
        self.assertFalse(self.native.calls)

    def test_stop_during_response_discards_scan_and_closes_slot(self):
        self.native.on_get = self.gate._stopped.set
        with self.assertRaises(NativeReadHeld):
            self.native.client(read_gate=self.gate).collect()
        self.assertEqual(len(self.native.calls), 1)
        self.assertEqual(self.gate._active, 0)

    def test_native_failure_releases_permit(self):
        self.native.response_status = 503
        pages = self.native.client(read_gate=self.gate).collect()
        self.assertEqual(pages[-1].terminal_completeness, 'UNKNOWN')
        self.assertEqual(self.gate._active, 0)
