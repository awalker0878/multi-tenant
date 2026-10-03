"""Bind each owned VM to its assigned domain, with real dual-origin HTTPS readers."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from lab.native_readback_fixture import Fixture
from tests.test_vsphere_campaign import inputs as base_inputs
from tests.test_vsphere_observe import Client as VmClient
from tests.test_vsphere_network_observe import manifest as pg_manifest, Client as PgClient
from tests.test_nsx_segment_observe import manifest as nsx_manifest, Client as NsxClient
from tests.test_target_campaign import window
from tests.test_nutanix_vm_observe import uid
from tools import qualify_target as q, vmware_network_binding as binding, nsx_segment_observe as nsx
from tools.guest_inventory import build
from provisioner.execution.run_files import digest, encoded, write_new


def inputs(nsx_origin='https://nsx.example.test', vc_origin='https://vc.example.test'):
    plan, vm, _, outputs, access = base_inputs(nsx_origin, vc_origin)
    plan['format'] = 'hosting-target-campaign/6'
    plan['assets'].update({key: dict(path='/private/' + key, sha256='a' * 64) for key in q.NETWORK_BINDING_ASSETS})
    network = nsx_manifest(nsx_origin); portgroups = pg_manifest(vc_origin)
    for m in (network, portgroups):
        m.update({key: vm[key] for key in ('operation_id', 'tenant_id', 'scope_id', 'engineering_record_ref', 'target_binding_ref')})
        m['contact_enabled'] = True
    config = portgroups['resources'][0]['expected']['config']
    vm['resources'][0]['expected']['config']['hardware']['device'][2]['backing'] = dict(
        _typeName='VirtualEthernetCardDistributedVirtualPortBackingInfo',
        port=dict(switchUuid=portgroups['resources'][0]['expected']['switch']['uuid'], portgroupKey=config['key'], portKey='17'))
    domains = dict(scope={'value': plan['scope'] | {'phase': 'domains'}}, delivery_state={'value': q.STATE},
        members={'value': {'D01O': dict(segment_path=network['resources'][0]['path'], delivery_state=q.STATE)}})
    workload_inputs = {key: plan['scope'][key] for key in ('environment_key', 'site_key', 'tenant_key', 'wsd_key')}
    workload_inputs.update(platform_endpoint=vc_origin, members={'guest-01': dict(domain_key='D01O', quarantine_network_id='dvportgroup-1')})
    return plan, vm, network, portgroups, domains, workload_inputs, outputs, access


def assets_at(directory, data, nsx_fixture=None, vc_fixture=None):
    plan, vm, network, portgroups, domains, workload_inputs, outputs, access = data
    inventory, _ = build(outputs, access, str(directory / 'known_hosts'))
    values = dict(inventory=encoded(inventory), workload_manifest=encoded(vm), native_manifest=encoded(network),
        portgroup_manifest=encoded(portgroups), domain_outputs=encoded(domains), workload_inputs=encoded(workload_inputs),
        workload_session=b'fixture-session', native_credentials=encoded(dict(username='fixture', password='fixture')))
    if nsx_fixture: values['native_ca'] = (nsx_fixture.directory / 'ca.pem').read_bytes()
    if vc_fixture: values['workload_ca'] = (vc_fixture.directory / 'ca.pem').read_bytes()
    for key in plan['assets']:
        raw = values.get(key, b'fixture'); path = directory / key; write_new(path, raw)
        plan['assets'][key] = dict(path=str(path), sha256=digest(raw))


class NetworkCampaignTests(unittest.TestCase):
    def bind(self, data):
        plan, vm, network, pg, domains, inputs, outputs, _ = data
        q.validate(plan); q.vsphere_binding(plan['scope'], vm, outputs, network)
        binding.bind(plan['scope'], vm, outputs, network, pg, domains, inputs)
    def test_exact_associations_and_assets_bind_before_contact(self):
        data = inputs(); self.bind(data)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); assets_at(folder, data); plan = data[0]
            q.bound_inputs(plan, str(folder / 'known_hosts'))
            for key in q.NETWORK_BINDING_ASSETS:
                path = folder / key; original = path.read_bytes(); path.write_bytes(b'changed')
                with self.assertRaises(ValueError): q.bound_inputs(plan, str(folder / 'known_hosts'))
                path.write_bytes(original)
    def test_foreign_network_origin_scope_uuid_and_opaque_backing_refused(self):
        for mutate in (lambda d: d[3].update(origin='https://other.example.test'), lambda d: d[3].update(target_binding_ref='other'),
            lambda d: d[3]['resources'][0]['expected']['config'].update(logicalSwitchUuid=uid(31)),
            lambda d: d[1]['resources'][0]['expected']['config']['hardware']['device'][2]['backing']['port'].update(switchUuid='other'),
            lambda d: d[1]['resources'][0]['expected']['config']['hardware']['device'][2]['backing']['port'].update(portgroupKey='other'),
            lambda d: d[1]['resources'][0]['expected']['config']['hardware']['device'][2].update(backing=dict(_typeName='VirtualEthernetCardOpaqueNetworkBackingInfo', opaqueNetworkId=uid(30), opaqueNetworkType='nsx.LogicalSwitch')),
            lambda d: d[5].update(platform_endpoint='https://other.example.test'),
            lambda d: d[5].update(platform_endpoint=42),
            lambda d: d[5]['members']['guest-01'].update(quarantine_network_id='dvportgroup-99'),
            lambda d: d[4]['scope']['value'].update(tenant_key='foreign'),
            lambda d: d[4]['members']['value']['D01O'].update(segment_path='/infra/segments/other')):
            data = inputs(); mutate(data)
            with self.assertRaises(ValueError): self.bind(data)
    def test_a_second_owned_domain_does_not_authorize_cross_domain_attachment(self):
        data = inputs(); _, vm, network, pg, domains, workload_inputs, _, _ = data
        r = deepcopy(network['resources'][0]); r['path'] = '/infra/segments/other'; r['expected'].update(path=r['path'], id='other')
        r['logical_switch'].update(id='other', path='/infra/realized-state/enforcement-points/default/logical-switches/other',
            intent_reference=[r['path']], realization_specific_identifier=uid(31)); network['resources'].append(r)
        domains['members']['value']['D02R'] = dict(segment_path=r['path'], delivery_state=q.STATE)
        other = pg['resources'][0]; other['segment_path'] = r['path']; other['expected']['config']['logicalSwitchUuid'] = uid(31)
        with self.assertRaisesRegex(ValueError, 'different owned domain'): self.bind(data)
    def test_old_profile_extra_or_missing_coverage_cannot_substitute(self):
        for mutate in (lambda d: d[2].update(profile='nsx-local-policy-v1-selected-fields'),
            lambda d: d[0]['assets'].pop('workload_inputs'), lambda d: d[5]['members'].clear(),
            lambda d: d[6]['members']['value'].update(extra=deepcopy(d[6]['members']['value']['guest-01'])),
            lambda d: d[4]['members']['value'].clear()):
            data = inputs(); mutate(data)
            with self.assertRaises(ValueError): self.bind(data)
    def test_real_campaign_collects_both_origins_around_guest_probe(self):
        with Fixture() as nf, Fixture() as vf, tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); data = inputs(nf.origin, vf.origin); plan, vm, network, pg, *_ = data
            nf.routes = NsxClient(network).routes
            vf.routes = {path: dict(body=value) for path, value in (VmClient(vm).routes | PgClient(pg).routes).items()}
            assets_at(folder, data, nf, vf)
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
            for label in ('native-before', 'native-after'):
                hashes = {key + '_sha256': digest((output / (label + '-' + key + '.json')).read_bytes())
                          for key in ('network_before', 'portgroups_before', 'workloads', 'portgroups_after', 'network_after')}
                self.assertEqual(result[label.replace('-', '_') + '_sha256'], digest(encoded(hashes)))
            self.assertTrue(all(r['method'] == 'GET' and r['has_basic_auth'] and not r['has_session_auth'] for r in nf.requests))
            self.assertTrue(all(r['method'] == 'GET' and r['has_session_auth'] and not r['has_basic_auth'] for r in vf.requests))
    def test_change_after_workload_read_stops_collection(self):
        with Fixture() as nf, Fixture() as vf, tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); data = inputs(nf.origin, vf.origin); plan, vm, network, pg, *_ = data
            nf.routes = NsxClient(network).routes
            vf.routes = {path: dict(body=value) for path, value in (VmClient(vm).routes | PgClient(pg).routes).items()}
            def change(path, count, spec):
                if '/DistributedVirtualPortgroup/' in path and count > 4: spec['body']['logicalSwitchUuid'] = uid(31)
                return spec
            vf.hook = change; assets_at(folder, data, nf, vf)
            assets, _, _ = q.bound_inputs(plan, str(folder / 'known_hosts'))
            with self.assertRaises(ValueError): q.native_readback(plan, assets, window(), folder, 'before')
            self.assertTrue((folder / 'before-workloads.json').exists())
            self.assertFalse((folder / 'before-network_after.json').exists())


if __name__ == '__main__': unittest.main()
