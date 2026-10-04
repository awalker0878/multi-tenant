"""Held VM review must bind independently observed native network attachments."""
from copy import deepcopy
from datetime import timedelta
import json
import subprocess
import sys
import unittest
from tests import test_terraform_recovery_review as attempts, test_vsphere_port_observe as ports
from tests.test_vsphere_network_replay import reseal
from tests.test_nutanix_vm_observe import uid
from provisioner.execution import readback_core as c
from provisioner.execution import terraform_recovery_review as review
from provisioner.execution import vsphere_recovery_devices as devices
from provisioner.execution.run_files import encoded, load_private


class AttachmentRecoveryTests(unittest.TestCase):
    setUp = attempts.AttemptRecoveryTests.setUp
    run_review = attempts.AttemptRecoveryTests.run_review

    def bind(self, manifest=None, network=None, inputs=None):
        return devices.bind_network(inputs or load_private(self.operation / 'inputs.json'), manifest or self.m, network or self.network)

    def test_network_moid_is_resolved_to_distinct_native_key_and_receipt_is_bound(self):
        before = {p.name: p.read_bytes() for p in self.folder.iterdir()}
        result = self.run_review(); evidence = result['network_evidence']
        self.assertEqual(result['triage']['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        self.assertEqual(evidence['manifest_sha256'], c.digest(self.network))
        self.assertEqual(evidence['report_sha256'], c.digest(self.network_report))
        binding = next(iter(evidence['native_bindings'].values()))
        self.assertEqual(binding['network_moid'], 'dvportgroup-1'); self.assertEqual(binding['portgroup_key'], 'fixture-pg-key')
        self.assertEqual(binding['connection_cookie'], 12345); self.assertIn('network_interface', result['plan_configuration_fields'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.folder.iterdir()})

    def test_missing_attachment_pair_or_old_snapshot_cannot_bypass_review(self):
        for kwargs in ({}, {'network_manifest': self.base/'network'}, {'network_readback': self.base/'network-report'}):
            with self.assertRaises(ValueError):
                review.review_attempt(self.operation, self.ledger, self.base/'manifest', self.base/'readback',
                    self.base/'context', self.base/'review', **kwargs)
        m = ports.p.group_manifest(self.network); (self.base/'network').write_bytes(encoded(m))
        with self.assertRaises(ValueError): self.run_review()
        self.assertFalse((self.base/'review.json').exists())

    def test_wrong_native_binding_or_cross_scope_is_rejected(self):
        changes = [lambda m: m.update(origin='https://other.example.test'), lambda m: m.update(operation_id='other'),
            lambda m: m.update(tenant_id='other'), lambda m: m.update(scope_id='other'),
            lambda m: m.update(engineering_record_ref='other'), lambda m: m.update(target_binding_ref='other'),
            lambda m: m['resources'][0].update(moid='dvportgroup-2'),
            lambda m: m['resources'][0]['ports'][0].update(connectionCookie=42),
            lambda m: m['resources'][0]['ports'][0]['connectee']['connectedEntity'].update(value='vm-2'),
            lambda m: m['resources'][0]['ports'][0]['connectee'].update(nicKey='4001'),
            lambda m: m['resources'][0]['ports'][0]['proxyHost'].update(value='host-2'),
            lambda m: m['resources'][0]['ports'][0]['state']['runtimeInfo'].update(macAddress='00:50:56:00:00:02')]
        for change in changes:
            network = deepcopy(self.network); change(network)
            with self.assertRaises(ValueError): self.bind(network=network)

    def test_wrong_switch_key_cookie_or_opaque_vm_backing_is_rejected(self):
        for key, value in [('switchUuid', 'other-switch'), ('portgroupKey', 'dvportgroup-1'), ('portKey', '18'),
                           ('connectionCookie', 99), ('connectionCookie', True)]:
            m = deepcopy(self.m); m['resources'][0]['expected']['config']['hardware']['device'][2]['backing']['port'][key] = value
            with self.assertRaises(ValueError): self.bind(manifest=m)
        m = deepcopy(self.m); m['resources'][0]['expected']['config']['hardware']['device'][2]['backing'] = dict(
            _typeName='VirtualEthernetCardOpaqueNetworkBackingInfo', opaqueNetworkId='fixture', opaqueNetworkType='nsx.LogicalSwitch')
        with self.assertRaises(ValueError): self.bind(manifest=m)

    def test_unchanged_foreign_plan_nic_is_not_hidden_by_before_after_equality(self):
        inputs = load_private(self.operation/'inputs.json')
        for key, value in [('key', 4001), ('key', True), ('mac_address', '00:50:56:00:00:02'),
                ('network_id', 'dvportgroup-2'), ('adapter_type', 'e1000'), ('use_static_mac', True)]:
            plan = deepcopy(self.plan)
            for phase in ('before', 'after'): plan['resource_changes'][0]['change'][phase]['network_interface'][0][key] = value
            with self.assertRaises(ValueError): review.bind_plan(plan, inputs, self.m)
        for value in ([], None, [{}], self.plan['resource_changes'][0]['change']['after']['network_interface'] * 2):
            plan = deepcopy(self.plan)
            for phase in ('before', 'after'): plan['resource_changes'][0]['change'][phase]['network_interface'] = value
            with self.assertRaises(ValueError): review.bind_plan(plan, inputs, self.m)

    def test_rehashed_false_attachment_summary_is_rejected_and_ledger_stays_held(self):
        before = {p.name: p.read_bytes() for p in self.folder.iterdir()}
        report = deepcopy(self.network_report)
        for row in report['history']: row['states'][0]['attachment_witness']['after']['17']['connectionCookie'] = 9
        reseal(report); (self.base/'network-report').write_bytes(encoded(report))
        with self.assertRaises(ValueError): self.run_review()
        self.assertFalse((self.base/'review.json').exists())
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.folder.iterdir()})

    def test_native_attachment_drift_and_missing_ports_block_packet(self):
        for change in (lambda client: client.rows['dvportgroup-1'].clear(),
                       lambda client: client.rows['dvportgroup-1'][0]['config'].update(configVersion='new')):
            client = ports.Client(self.network); change(client)
            report = c.observe(self.network, client, ports.p, interval=0)
            (self.base/'network-report').write_bytes(encoded(report))
            with self.assertRaises(ValueError): self.run_review()

    def test_stale_or_predating_network_evidence_blocks_review(self):
        for stamp in ((c.timestamp(self.started['started_at'])-timedelta(seconds=1)).isoformat(),
                      (c.timestamp(self.network_report['started_at'])-timedelta(seconds=301)).isoformat()):
            report = deepcopy(self.network_report); report.update(started_at=stamp, completed_at=stamp)
            for row in report['history']: row['observed_at'] = stamp
            reseal(report); (self.base/'network-report').write_bytes(encoded(report))
            with self.assertRaises(ValueError): self.run_review()

    def test_network_sampling_before_controls_holds_even_if_vm_sampling_is_later(self):
        context = load_private(self.base/'context'); vm_report = load_private(self.base/'readback')
        start = c.timestamp(vm_report['started_at']); earlier = (start-timedelta(milliseconds=100)).isoformat()
        context['writer_fence']['observed_at'] = start.isoformat()
        (self.base/'context').write_bytes(encoded(context))
        report = deepcopy(self.network_report); report.update(started_at=earlier, completed_at=earlier)
        for row in report['history']: row['observed_at'] = earlier
        reseal(report); (self.base/'network-report').write_bytes(encoded(report))
        result = self.run_review()
        self.assertEqual(result['triage']['result'], 'HOLD_NETWORK_NOT_UNDER_CONTROLS')
        self.assertFalse(result['ledger_released']); self.assertFalse(result['may_apply'])

    def test_shared_group_requires_exact_distinct_occupants_without_extra_ports(self):
        inputs = load_private(self.operation/'inputs.json'); inputs['members']['processor-02'] = deepcopy(inputs['members']['processor-01'])
        m = deepcopy(self.m); other = deepcopy(m['resources'][0]); other['moid'] = 'vm-2'
        other['expected']['config'].update(name='processor-02', uuid=uid(3), instanceUuid=uid(4))
        nic = other['expected']['config']['hardware']['device'][2]
        nic['macAddress'] = '00:50:56:00:00:02'; nic['backing']['port'].update(portKey='18', connectionCookie=54321)
        m['resources'].append(other); network = deepcopy(self.network)
        port = deepcopy(network['resources'][0]['ports'][0]); port.update(key='18', connectionCookie=54321)
        port['connectee']['connectedEntity']['value'] = 'vm-2'; port['state']['runtimeInfo']['macAddress'] = nic['macAddress']
        network['resources'][0]['ports'].append(port)
        self.assertEqual(len(self.bind(m, network, inputs)), 2)
        with self.assertRaises(ValueError): self.bind(network=network)  # Unowned second occupant.
        nic['backing']['port']['portKey'] = '17'
        with self.assertRaises(ValueError): self.bind(m, network, inputs)

    def test_offline_cli_binds_new_private_packet(self):
        args = [sys.executable, '-m', 'provisioner.execution.terraform_recovery_review', '--source-root', str(review.ROOT), '--bundle', str(self.operation),
            '--ledger', str(self.ledger), '--manifest', str(self.base/'manifest'), '--readback', str(self.base/'readback'),
            '--context', str(self.base/'context'), '--network-manifest', str(self.base/'network'),
            '--network-readback', str(self.base/'network-report'), '--output', str(self.base/'cli-review')]
        result = subprocess.run(args, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(json.loads(result.stdout)['ledger_released'])
        self.assertEqual((self.base/'cli-review').stat().st_mode & 0o777, 0o600)
        self.assertEqual(subprocess.run(args, capture_output=True, timeout=10).returncode, 2)


if __name__ == '__main__': unittest.main()
