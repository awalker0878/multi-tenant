from copy import deepcopy
from datetime import timedelta
import os
from pathlib import Path
import signal
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from tests.test_guest_run import inputs, prepare, SOURCE
from tools import guest_apply as a, guest_run as g
from provisioner.execution.run_files import digest, encoded, file_map, load_private, utcnow, write_new


def configured(folder, mode='check', ssh=None):
    args = inputs(folder, mode)
    if ssh is not None: args.ssh = ssh
    prepare(args)
    approval = dict(format='hosting-guest-approval/1', bundle_sha256=digest((args.output/'bundle.json').read_bytes()),
        operation_id=args.operation_id, generation=args.generation, valid_from=(utcnow()-timedelta(seconds=5)).isoformat(),
        valid_until=(utcnow()+timedelta(minutes=10)).isoformat(), change_ref=load_private(args.access)['change_ref'])
    write_new(folder/'approval.json', encoded(approval)); (folder/'ledger').mkdir(mode=0o700)
    return SimpleNamespace(bundle=args.output, approval=folder/'approval.json', ledger=folder/'ledger', execute=True)


def successful_child(argv, directory, env, timeout):
    assert (directory/'runtime/ssh_key').exists()
    summary = dict(ok=4, failures=0, unreachable=0, changed=1, skipped=0, rescued=0, ignored=0)
    write_new(directory/'runtime/stats.json', encoded(dict(format='hosting-guest-stats/1',
        completed_at=utcnow().isoformat(), hosts={'localhost': summary, 'guest-01': summary})))


class GuestExecutionTests(unittest.TestCase):
    def test_ledger_replays_complete_receipts_and_rejects_damaged_history_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = configured(Path(tmp))
            with patch.object(g, 'verify', return_value=SOURCE), patch.object(a, 'run_process', side_effect=successful_child):
                a.apply(args)
            scope = load_private(args.bundle/'bundle.json')['scope']
            ledger = args.ledger/digest(encoded(scope))
            saved = {p.name: p.read_bytes() for p in ledger.iterdir()}
            start = next(ledger.glob('*.started.json')); result = next(ledger.glob('*.result.json'))
            stats = next(ledger.glob('*.stats.json'))
            self.assertEqual(stats.read_bytes(), (args.bundle/'runtime/stats.json').read_bytes())
            with a.scope_ledger(args.ledger, scope): pass
            for fault in ('source', 'change', 'mode', 'scope', 'boolean_generation', 'authority',
                          'missing_stats', 'altered_stats', 'missing_start', 'renamed_start',
                          'missing_head', 'head_drift', 'missing_result', 'inverted_time',
                          'counter_drift', 'target_drift', 'unknown_field', 'status'):
                for p in ledger.iterdir(): p.unlink()
                for name, raw in saved.items(): write_new(ledger/name, raw)
                data = load_private(result)
                if fault == 'source': data['source_commit'] = 'b'*40
                elif fault == 'change': data['change_ref'] = 'OTHER-CHANGE'
                elif fault == 'mode': data['mode'] = 'configure'
                elif fault == 'scope': data['scope']['tenant_key'] = 'foreign'
                elif fault == 'authority': data['native_acceptance'] = True
                elif fault == 'inverted_time': data['completed_at'] = '2000-01-01T00:00:00Z'
                elif fault == 'counter_drift': data['hosts']['guest-01']['changed'] += 1
                elif fault == 'target_drift': data['targets'] = ['foreign-guest']
                elif fault == 'unknown_field': data['replay_authorized'] = True
                elif fault == 'status': data['status'] = 'CONFIGURED_REQUIRES_NATIVE_ACCEPTANCE'
                elif fault == 'boolean_generation':
                    prior = load_private(start); prior['generation'] = True; start.write_bytes(encoded(prior))
                elif fault == 'missing_stats': stats.unlink()
                elif fault == 'altered_stats': stats.write_bytes(stats.read_bytes()+b' ')
                elif fault == 'missing_start': start.unlink()
                elif fault == 'renamed_start': start.rename(ledger/('0'*64+'.started.json'))
                elif fault == 'missing_head': (ledger/'head.json').unlink()
                elif fault == 'head_drift': (ledger/'head.json').write_bytes(encoded({'status': 'CHECK_COMPLETED_REQUIRES_REVIEW'}))
                elif fault == 'missing_result': result.unlink()
                if result.exists(): result.write_bytes(encoded(data))
                before = file_map(args.ledger)
                with self.subTest(fault=fault), self.assertRaises((ValueError, OSError)):
                    with a.scope_ledger(args.ledger, scope): self.fail('Damaged ledger was admitted')
                self.assertEqual(file_map(args.ledger), before)

    def test_completion_rejects_ambiguous_or_unsuccessful_counters(self):
        now = utcnow(); summary = dict(ok=4, failures=0, unreachable=0, changed=1, skipped=0, rescued=0, ignored=0)
        original = dict(format='hosting-guest-stats/1', completed_at=now.isoformat(),
                        hosts={'localhost': summary, 'guest-01': summary.copy()})
        for fault in ('duplicate', 'float', 'bool', 'negative', 'excess_changed', 'rescued', 'failed', 'missing', 'future', 'empty'):
            data = deepcopy(original)
            if fault == 'float': data['hosts']['guest-01']['ok'] = 4.0
            elif fault == 'bool': data['hosts']['guest-01']['ok'] = True
            elif fault == 'negative': data['hosts']['guest-01']['changed'] = -1
            elif fault == 'excess_changed': data['hosts']['guest-01']['changed'] = 5
            elif fault == 'rescued': data['hosts']['guest-01']['rescued'] = 1
            elif fault == 'failed': data['hosts']['guest-01']['failures'] = 1
            elif fault == 'missing': data['hosts'].pop('guest-01')
            elif fault == 'future': data['completed_at'] = (now+timedelta(seconds=1)).isoformat()
            raw = encoded(data)
            if fault == 'duplicate': raw = raw.replace(b'"ok": 4', b'"ok": 0, "ok": 4')
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                a.validate_stats(raw, set() if fault == 'empty' else {'guest-01'}, now, now)

    def test_expired_enrollment_after_dispatch_leaves_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = configured(Path(tmp), 'configure'); deadline = a.execution_deadline
            calls = []
            def end_after_dispatch(access, approval):
                return utcnow()-timedelta(seconds=1) if calls else deadline(access, approval)
            def child(*values): successful_child(*values); calls.append(True)
            with patch.object(g, 'verify', return_value=SOURCE), patch.object(a, 'run_process', side_effect=child), \
                 patch.object(a, 'execution_deadline', side_effect=end_after_dispatch), self.assertRaises(ValueError):
                a.apply(args)
            self.assertEqual(load_private(args.bundle/'result.json')['status'], 'HOLD_RECONCILIATION_REQUIRED')
            self.assertFalse((args.bundle/'runtime/ssh_key').exists())

    def test_real_ansible_uses_pinned_ssh_after_gate_and_records_unreachable_guest(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); ssh = folder/'ssh-fixture'; calls = folder/'ssh-calls.json'
            ssh.write_text('#!/usr/bin/python3\nimport json,sys\nfrom pathlib import Path\n'
                + 'Path('+repr(str(calls))+').write_text(json.dumps(sys.argv[1:]))\nraise SystemExit(255)\n')
            ssh.chmod(0o700); args = configured(folder, ssh=ssh)
            source = file_map(args.bundle/'source')
            with patch.dict(os.environ, {'ANSIBLE_CONFIG': '/untrusted', 'ANSIBLE_SSH_ARGS': '-o StrictHostKeyChecking=no',
                    'SSH_AUTH_SOCK': '/untrusted', 'PYTHONPATH': '/untrusted'}), \
                 patch.object(g, 'verify', return_value=SOURCE), self.assertRaises(ValueError): a.apply(args)
            self.assertTrue(calls.exists(), (args.bundle/'ansible.log').read_text())
            argv = __import__('json').loads(calls.read_text())
            for option in ('/dev/null', 'IdentitiesOnly=yes', 'IdentityAgent=none', 'ProxyCommand=none',
                           'ControlMaster=no', 'StrictHostKeyChecking=yes',
                           'PubkeyAcceptedAlgorithms=ssh-ed25519-cert-v01@openssh.com'):
                self.assertIn(option, argv)
            report = load_private(args.bundle/'runtime/stats.json')
            self.assertGreater(report['hosts']['localhost']['ok'], 0)
            self.assertEqual(report['hosts']['guest-01']['unreachable'], 1)
            self.assertEqual(load_private(args.bundle/'result.json')['status'], 'HOLD_RECONCILIATION_REQUIRED')
            self.assertEqual(file_map(args.bundle/'source'), source)
            self.assertFalse((args.bundle/'runtime/ssh_key').exists())

    def test_success_requires_counters_and_check_mode_cannot_become_configure(self):
        for mode, status in [('check', 'CHECK_COMPLETED_REQUIRES_REVIEW'), ('configure', 'CONFIGURED_REQUIRES_NATIVE_ACCEPTANCE')]:
            with tempfile.TemporaryDirectory() as tmp:
                args = configured(Path(tmp), mode)
                with patch.object(g, 'verify', return_value=SOURCE), patch.object(a, 'run_process', side_effect=successful_child) as child:
                    result = a.apply(args)
                self.assertEqual(result['status'], status); self.assertFalse(result['native_acceptance'])
                self.assertEqual('--check' in child.call_args.args[0], mode == 'check')
                self.assertIn('-I', child.call_args.args[0]); self.assertNotIn('--diff', child.call_args.args[0])
                self.assertFalse((args.bundle/'runtime/ssh_key').exists())
                receipt = load_private(args.bundle/'result.json')
                self.assertEqual(receipt['stats_sha256'], digest((args.bundle/'runtime/stats.json').read_bytes()))
                self.assertEqual(len(list(args.ledger.rglob('*.started.json'))), 1)

    def test_altered_inputs_source_runtime_inventory_or_approval_prevent_any_attempt(self):
        for fault in ('source', 'inventory', 'pins', 'runtime', 'mode', 'approval', 'approval_generation', 'expiry', 'key', 'budget', 'opt_in'):
            with tempfile.TemporaryDirectory() as tmp:
                args = configured(Path(tmp)); bad_source = False
                if fault == 'source': bad_source = True
                elif fault == 'inventory':
                    p = args.bundle/'inventory.json'; data = load_private(p)
                    data['all']['children']['hosting_guests']['hosts']['guest-01']['ansible_connection'] = 'local'; p.write_bytes(encoded(data))
                elif fault == 'pins': (args.bundle/'known_hosts').write_bytes(b'wrong-host')
                elif fault == 'runtime':
                    p = args.bundle/'runtime.json'; data = load_private(p); data['ssh_sha256'] = '0'*64; p.write_bytes(encoded(data))
                elif fault == 'mode':
                    p = args.bundle/'bundle.json'; data = load_private(p); data['mode'] = 'configure'; p.write_bytes(encoded(data))
                elif fault in {'approval', 'approval_generation', 'expiry', 'budget'}:
                    data = load_private(args.approval)
                    if fault == 'approval': data['bundle_sha256'] = '0'*64
                    elif fault == 'approval_generation': data['generation'] = True
                    elif fault == 'expiry': data['valid_until'] = (utcnow()-timedelta(seconds=1)).isoformat()
                    else: data['valid_until'] = (utcnow()+timedelta(seconds=20)).isoformat()
                    args.approval.write_bytes(encoded(data))
                elif fault == 'key': (Path(tmp)/'key').write_bytes(b'changed-key')
                elif fault == 'opt_in': args.execute = False
                with patch.object(g, 'verify', return_value=SOURCE | {'commit': 'b'*40} if bad_source else SOURCE), \
                     patch.object(a, 'run_process') as child, self.subTest(fault=fault), self.assertRaises(ValueError): a.apply(args)
                child.assert_not_called(); self.assertEqual(list(args.ledger.rglob('*.started.json')), [])

    def test_rehashed_unsafe_inventory_still_cannot_override_generated_connections(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = configured(Path(tmp)); p = args.bundle/'inventory.json'; data = load_private(p)
            data['all']['vars']['ansible_connection'] = 'local'; p.write_bytes(encoded(data))
            bundle = load_private(args.bundle/'bundle.json'); bundle['artifacts']['inventory.json'] = digest(p.read_bytes())
            (args.bundle/'bundle.json').write_bytes(encoded(bundle))
            approval = load_private(args.approval); approval['bundle_sha256'] = digest(encoded(bundle)); args.approval.write_bytes(encoded(approval))
            with patch.object(g, 'verify', return_value=SOURCE), self.assertRaises(ValueError): a.apply(args)

    def test_failure_interrupt_and_missing_or_false_stats_leave_durable_hold(self):
        for fault in ('timeout', 'interrupt', 'missing', 'foreign', 'ignored', 'stale'):
            with tempfile.TemporaryDirectory() as tmp:
                args = configured(Path(tmp), 'configure')
                def fail(argv, directory, env, timeout):
                    started = list(args.ledger.rglob('*.started.json'))
                    self.assertEqual(len(started), 1); self.assertEqual(load_private(started[0])['status'], 'STARTED_OUTCOME_UNKNOWN')
                    if fault == 'timeout': raise subprocess.TimeoutExpired(argv, timeout)
                    if fault == 'interrupt': raise KeyboardInterrupt
                    if fault == 'missing': return
                    successful_child(argv, directory, env, timeout)
                    p = directory/'runtime/stats.json'; data = load_private(p)
                    if fault == 'foreign': data['hosts']['foreign'] = data['hosts'].pop('guest-01')
                    elif fault == 'ignored': data['hosts']['guest-01']['ignored'] = 1
                    else: data['completed_at'] = '2000-01-01T00:00:00Z'
                    p.write_bytes(encoded(data))
                with patch.object(g, 'verify', return_value=SOURCE), patch.object(a, 'run_process', side_effect=fail), \
                     self.subTest(fault=fault), self.assertRaises((ValueError, OSError, subprocess.TimeoutExpired, KeyboardInterrupt)): a.apply(args)
                receipt = load_private(args.bundle/'result.json')
                self.assertEqual(receipt['status'], 'HOLD_RECONCILIATION_REQUIRED')
                self.assertFalse((args.bundle/'runtime/ssh_key').exists())
                self.assertEqual(load_private(next(args.ledger.rglob('head.json'))), receipt)

    def test_uncertain_scope_blocks_new_operation_and_renamed_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); args = configured(folder)
            with patch.object(g, 'verify', return_value=SOURCE), patch.object(a, 'run_process', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt): a.apply(args)
            before = file_map(args.ledger); next_folder = folder/'next'; next_folder.mkdir(mode=0o700)
            candidate = configured(next_folder); candidate.ledger = args.ledger
            bundle = load_private(candidate.bundle/'bundle.json'); bundle['operation_id'] = 'different-operation'
            (candidate.bundle/'bundle.json').write_bytes(encoded(bundle))
            approval = load_private(candidate.approval); approval.update(operation_id=bundle['operation_id'], bundle_sha256=digest(encoded(bundle)))
            candidate.approval.write_bytes(encoded(approval))
            with patch.object(g, 'verify', return_value=SOURCE), patch.object(a, 'run_process') as child, self.assertRaises(ValueError): a.apply(candidate)
            child.assert_not_called(); self.assertEqual(file_map(args.ledger), before)
            moved = folder/'moved'; candidate.bundle.rename(moved); candidate.bundle = moved
            with patch.object(g, 'verify', return_value=SOURCE), self.assertRaises(ValueError): a.apply(candidate)

    def test_controller_timeout_terminates_its_process_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            process = unittest.mock.Mock(pid=123456)
            process.wait.side_effect = [subprocess.TimeoutExpired(['fixture'], 1), -9]
            with patch.object(a.subprocess, 'Popen', return_value=process) as launch, patch.object(a.os, 'killpg') as kill:
                with self.assertRaises(subprocess.TimeoutExpired): a.run_process(['fixture'], Path(tmp), {}, 1)
            self.assertTrue(launch.call_args.kwargs['start_new_session']); kill.assert_called_once_with(123456, signal.SIGKILL)

    def test_start_record_without_head_blocks_new_work_and_preserves_every_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = configured(Path(tmp)); scope = load_private(args.bundle/'bundle.json')['scope']
            ledger = args.ledger/digest(encoded(scope)); ledger.mkdir(mode=0o700)
            write_new(ledger/'lost.started.json', encoded(dict(format='hosting-guest-attempt/1', scope=scope,
                      status='STARTED_OUTCOME_UNKNOWN', operation_id='previous-operation')))
            before = file_map(args.ledger)
            with patch.object(g, 'verify', return_value=SOURCE), patch.object(a, 'run_process') as child, self.assertRaises(ValueError): a.apply(args)
            child.assert_not_called()
            after = file_map(args.ledger); after.pop(str(ledger.relative_to(args.ledger)/'writer.lock'))
            self.assertEqual(before, after)

    def test_successful_attempt_cannot_be_replayed_from_a_new_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); first = configured(folder)
            with patch.object(g, 'verify', return_value=SOURCE), patch.object(a, 'run_process', side_effect=successful_child): a.apply(first)
            before = file_map(first.ledger); other = folder/'next'; other.mkdir(mode=0o700)
            second = configured(other); second.ledger = first.ledger
            with patch.object(g, 'verify', return_value=SOURCE), patch.object(a, 'run_process') as child, self.assertRaises(ValueError): a.apply(second)
            child.assert_not_called(); self.assertEqual(file_map(first.ledger), before)
            bundle = load_private(second.bundle/'bundle.json'); bundle['generation'] = 2
            (second.bundle/'bundle.json').write_bytes(encoded(bundle))
            approval = load_private(second.approval); approval.update(generation=2, bundle_sha256=digest(encoded(bundle)))
            second.approval.write_bytes(encoded(approval))
            with patch.object(g, 'verify', return_value=SOURCE), patch.object(a, 'run_process', side_effect=successful_child):
                self.assertEqual(a.apply(second)['status'], 'CHECK_COMPLETED_REQUIRES_REVIEW')
            self.assertEqual(len(list(first.ledger.rglob('*.started.json'))), 2)


if __name__ == '__main__': unittest.main()
