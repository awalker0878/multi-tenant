"""Real POSIX process/rate locks across batches; no distributed/native qualification."""
from dataclasses import replace
from datetime import datetime, timezone, timedelta
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest

from provisioner.controlplane.discovery.read_budget import EndpointReadPolicy, NativeReadAdmissionHeld
from provisioner.controlplane.discovery.shared_read_budget import SharedNativeReadGate
from tests.provisioning.discovery.process_fixture import start_prepared, activate


class SharedBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)
        self.policy=EndpointReadPolicy('org','site','nutanix','endpoint',1,100)

    def gate(self,**kwargs):return SharedNativeReadGate(self.policy,directory=self.directory,**kwargs)

    def test_durable_rate_survives_new_gate_and_current_authority_is_rechecked(self):
        gate=self.gate();calls=[]
        with gate.permit(time.monotonic()+1,lambda:calls.append(time.monotonic())):pass
        before=time.monotonic();other=self.gate()
        with other.permit(time.monotonic()+1,lambda:calls.append(time.monotonic())):pass
        self.assertGreaterEqual(time.monotonic()-before,.07)
        self.assertGreaterEqual(len(calls),4)

    def test_shared_concurrency_applies_to_independent_gate_instances_and_threads(self):
        self.policy=replace(self.policy,min_interval_ms=1)
        gates=[self.gate(),self.gate()];active=peak=0;lock=threading.Lock();errors=[]
        def run(gate):
            nonlocal active,peak
            try:
                with gate.permit(time.monotonic()+2,lambda:None):
                    with lock:active+=1;peak=max(peak,active)
                    time.sleep(.05)
                    with lock:active-=1
            except Exception as exc:errors.append(exc)
        threads=[threading.Thread(target=run,args=(gates[i%2],)) for i in range(4)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(3)
        self.assertFalse(errors);self.assertEqual(peak,1)
        self.assertFalse(any(t.is_alive() for t in threads))

    def test_actual_competing_process_cannot_read_until_socket_slot_is_released(self):
        self.policy=replace(self.policy,min_interval_ms=1)
        program='''
import sys,time
from provisioner.controlplane.discovery.read_budget import EndpointReadPolicy,NativeReadAdmissionHeld
from provisioner.controlplane.discovery.shared_read_budget import SharedNativeReadGate
gate=SharedNativeReadGate(EndpointReadPolicy('org','site','nutanix','endpoint',1,1),directory=sys.argv[1])
fixture_ready()
try:
    with gate.permit(time.monotonic()+.2,lambda:None):sys.exit(8)
except NativeReadAdmissionHeld:sys.exit(0)
'''
        gate=self.gate();child=start_prepared(program,[str(self.directory)])
        try:
            with gate.permit(time.monotonic()+1,lambda:None):
                activate(child);output,errors=child.communicate(timeout=5)
                self.assertEqual(child.returncode,0,output+errors)
        finally:
            if child.poll() is None:child.kill()
            child.communicate(timeout=5)
        with self.gate().permit(time.monotonic()+1,lambda:None):pass

    def test_killed_process_releases_concurrency_but_does_not_refund_rate(self):
        self.policy=replace(self.policy,min_interval_ms=1000)
        program='''
import os,sys,time
from provisioner.controlplane.discovery.read_budget import EndpointReadPolicy
from provisioner.controlplane.discovery.shared_read_budget import SharedNativeReadGate
gate=SharedNativeReadGate(EndpointReadPolicy('org','site','nutanix','endpoint',1,1000),directory=sys.argv[1])
fixture_ready()
with gate.permit(time.monotonic()+2,lambda:None):os._exit(7)
'''
        child=start_prepared(program,[str(self.directory)])
        try:
            activate(child);child.communicate(timeout=5);self.assertEqual(child.returncode,7)
        finally:
            if child.poll() is None:child.kill()
            child.communicate(timeout=5)
        with self.assertRaises(NativeReadAdmissionHeld):
            with self.gate().permit(time.monotonic()+.05,lambda:None):pass
        with self.gate().permit(time.monotonic()+2,lambda:None):pass

    def test_changed_limits_and_missing_rate_hold_instead_of_resetting_budget(self):
        gate=self.gate()
        with self.assertRaises(NativeReadAdmissionHeld):
            SharedNativeReadGate(replace(self.policy,max_concurrent=2),directory=self.directory)
        Path(gate._path('.rate.json')).unlink()
        with self.assertRaises(NativeReadAdmissionHeld):self.gate()
        with self.assertRaises(NativeReadAdmissionHeld):
            with gate.permit(time.monotonic()+1,lambda:None):pass

    def test_replaced_slot_or_directory_cannot_create_a_second_lock_owner(self):
        gate=self.gate();slot=Path(gate._path('.slot-00.lock'))
        slot.rename(slot.with_suffix('.old'));slot.touch(mode=0o600)
        with self.assertRaises(NativeReadAdmissionHeld):gate.check()
        with self.assertRaises(NativeReadAdmissionHeld):self.gate()

    def test_corruption_and_symlinks_refuse_before_read(self):
        gate=self.gate();rate=Path(gate._path('.rate.json'))
        original=rate.read_bytes();rate.write_bytes(original.replace(b'1970',b'1971'))
        with self.assertRaises(NativeReadAdmissionHeld):
            with gate.permit(time.monotonic()+1,lambda:None):pass
        rate.unlink();rate.symlink_to('/dev/null')
        with self.assertRaises((OSError,ValueError)):
            with self.gate().permit(time.monotonic()+1,lambda:None):pass

    def test_revocation_after_reservation_cannot_enter_read_or_refund_rate(self):
        gate=self.gate();calls=0
        def authorize():
            nonlocal calls
            calls+=1
            if calls==2:raise PermissionError('revoked')
        with self.assertRaises(PermissionError):
            with gate.permit(time.monotonic()+1,authorize):self.fail('revoked read started')
        with self.assertRaises(NativeReadAdmissionHeld):
            with self.gate().permit(time.monotonic()+.01,lambda:None):pass

    def test_clock_regression_holds_instead_of_reserving_a_new_rate_slot(self):
        at=datetime.now(timezone.utc);gate=self.gate(clock=lambda:at)
        with gate.permit(time.monotonic()+1,lambda:None):pass
        gate=self.gate(clock=lambda:at-timedelta(seconds=1))
        with self.assertRaises(NativeReadAdmissionHeld):
            with gate.permit(time.monotonic()+1,lambda:None):pass


if __name__=='__main__':unittest.main()
