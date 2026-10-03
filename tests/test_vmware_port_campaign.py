"""Cross-owner port attachment checks and real campaign child transports."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from lab.native_readback_fixture import Fixture
from tests.test_vmware_network_campaign import inputs as network_inputs, assets_at
from tests.test_vsphere_port_observe import manifest as port_manifest, Client as PortClient
from tests.test_vsphere_observe import Client as VmClient
from tests.test_nsx_segment_observe import Client as NsxClient
from tests.test_target_campaign import window
from provisioner.execution import qualify_target as q
from provisioner.execution import vmware_network_binding as binding
from provisioner.execution import vsphere_port_observe as ports
from provisioner.execution.run_files import digest, encoded, write_new


def inputs(*origins):
    data = network_inputs(*origins); plan, vm, _, pg, *_ = data
    plan['format'] = 'hosting-target-campaign/7'; pg['profile'] = ports.PROFILE
    pg['resources'][0]['ports'] = port_manifest()['resources'][0]['ports']
    port = pg['resources'][0]['ports'][0]; nic = vm['resources'][0]['expected']['config']['hardware']['device'][2]
    port['state']['runtimeInfo']['macAddress'] = nic['macAddress']
    nic['backing']['port']['connectionCookie'] = port['connectionCookie']
    return data


def routes(nf, vf, data):
    _, vm, network, pg, *_ = data
    nf.routes = NsxClient(network).routes
    vf.routes = {p: dict(body=v) for p, v in (VmClient(vm).routes | PortClient(pg).routes).items()}
    for r in pg['resources']:
        path, body = ports.request(r)
        vf.post_routes[path] = lambda actual, expected=body, rows=r['ports']: dict(body=deepcopy(rows)) if actual == expected else dict(status=400, body={})


class PortCampaignTests(unittest.TestCase):
    def bind(self, data):
        plan, vm, network, pg, domains, workload_inputs, outputs, _ = data
        q.validate(plan); q.vsphere_binding(plan['scope'], vm, outputs, network)
        binding.bind_attachments(plan['scope'], vm, outputs, network, pg, domains, workload_inputs)
    def test_exact_attachment_assets_and_cookie_bind_before_contact(self):
        data = inputs(); self.bind(data)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); assets_at(folder, data)
            q.bound_inputs(data[0], str(folder / 'known_hosts'))
            (folder / 'portgroup_manifest').write_bytes(b'changed')
            with self.assertRaises(ValueError): q.bound_inputs(data[0], str(folder / 'known_hosts'))
    def test_wrong_vm_nic_host_mac_cookie_or_port_refused(self):
        for change in (lambda p: p['connectee']['connectedEntity'].update(value='vm-2'),
            lambda p: p['connectee'].update(nicKey='4001'), lambda p: p['proxyHost'].update(value='host-2'),
            lambda p: p['state']['runtimeInfo'].update(macAddress='00:50:56:00:00:02'),
            lambda p: p.update(connectionCookie=12346), lambda p: p.update(key='18')):
            data = inputs(); change(data[3]['resources'][0]['ports'][0])
            with self.assertRaises(ValueError): self.bind(data)
        for cookie in (None, True, 2**31):
            data = inputs(); data[1]['resources'][0]['expected']['config']['hardware']['device'][2]['backing']['port']['connectionCookie'] = cookie
            with self.assertRaises(ValueError): self.bind(data)
    def test_older_profile_cannot_supply_attachment_evidence(self):
        for old in ('vsphere-vi-json-8.0.3.0-nsx-portgroups', 'vsphere-vi-json-8.0.3.0-vm-snapshot'):
            data = inputs(); data[3]['profile'] = old
            with self.assertRaises(ValueError): self.bind(data)
        data = inputs(); data[0]['format'] = 'hosting-target-campaign/6'
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); assets_at(folder, data)
            with self.assertRaises(ValueError): q.bound_inputs(data[0], str(folder / 'known_hosts'))
    def test_extra_port_or_shared_port_across_nics_refused(self):
        data = inputs(); port = deepcopy(data[3]['resources'][0]['ports'][0]); port['key'] = '18'; port['connectee']['nicKey'] = '4001'
        data[3]['resources'][0]['ports'].append(port)
        with self.assertRaisesRegex(ValueError, 'Unassigned'): self.bind(data)
        data = inputs(); devices = data[1]['resources'][0]['expected']['config']['hardware']['device']
        nic = deepcopy(devices[2]); nic.update(key=4001, macAddress='00:50:56:00:00:02'); devices.append(nic)
        with self.assertRaisesRegex(ValueError, 'unique observed port'): self.bind(data)
    def test_real_campaign_binds_five_reports_per_phase_and_separates_credentials(self):
        with Fixture() as nf, Fixture() as vf, tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); data = inputs(nf.origin, vf.origin); plan = data[0]; routes(nf, vf, data); assets_at(folder, data, nf, vf)
            raw = encoded(plan); write_new(folder / 'plan.json', raw)
            authority = window() | dict(format='hosting-target-campaign-authority/1', plan_sha256=digest(raw), source_commit=plan['source_commit'],
                ssh_sha256=digest(Path('/usr/bin/ssh').read_bytes()), change_ref='FIXTURE', target_binding_ref='FIXTURE', isolation_ref='FIXTURE')
            write_new(folder / 'authority.json', encoded(authority)); output = folder / 'campaign'
            argv = ['qualify_target.py', str(folder / 'plan.json'), '--execute', '--authority', str(folder / 'authority.json'), '--output', str(output)]
            with patch('sys.argv', argv), patch.object(q, 'verify', return_value=dict(status='HASHES_MATCH', commit=plan['source_commit'])), \
                 patch.object(q, 'ssh_probe', return_value={'status': 'HEALTHY'}) as probe, redirect_stdout(io.StringIO()):
                self.assertEqual(q.main(), 0)
            self.assertEqual(probe.call_count, 1); self.assertFalse((output / 'ssh_key').exists())
            result = json.loads((output / 'result.json').read_bytes()); self.assertFalse(result['production_qualified'])
            for phase in ('native-before', 'native-after'):
                hashes = {k + '_sha256': digest((output / (phase + '-' + k + '.json')).read_bytes())
                          for k in ('network_before', 'portgroups_before', 'workloads', 'portgroups_after', 'network_after')}
                self.assertEqual(result[phase.replace('-', '_') + '_sha256'], digest(encoded(hashes)))
                report = json.loads((output / (phase + '-portgroups_before.json')).read_bytes())
                self.assertEqual(report['profile'], ports.PROFILE)
            self.assertTrue(all(r['method'] == 'GET' and r['has_basic_auth'] and not r['has_session_auth'] for r in nf.requests))
            self.assertTrue(all(r['has_session_auth'] and not r['has_basic_auth'] for r in vf.requests))
            self.assertEqual(len([r for r in vf.requests if r['method'] == 'POST']), 16)
    def test_changed_attachment_after_vm_observation_stops_phase(self):
        with Fixture() as nf, Fixture() as vf, tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); data = inputs(nf.origin, vf.origin); routes(nf, vf, data); assets_at(folder, data, nf, vf)
            r = data[3]['resources'][0]; path, _ = ports.request(r)
            def changed(_):
                rows = deepcopy(r['ports'])
                if any('/VirtualMachine/' in x['path'] for x in vf.requests): rows[0]['connectionCookie'] += 1
                return dict(body=rows)
            vf.post_routes[path] = changed
            assets, _, _ = q.bound_inputs(data[0], str(folder / 'known_hosts'))
            with self.assertRaises(ValueError): q.native_readback(data[0], assets, window(), folder, 'before')
            self.assertTrue((folder / 'before-workloads.json').exists())
            self.assertFalse((folder / 'before-network_after.json').exists())


if __name__ == '__main__': unittest.main()
