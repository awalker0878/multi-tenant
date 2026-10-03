"""Campaign v8 crosses real loopback NSX/vCenter transports with private assets."""
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import timedelta
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from lab.native_readback_fixture import Fixture
from tests.test_vmware_port_campaign import inputs as port_inputs, routes
from tests.test_vmware_network_campaign import assets_at as port_assets_at
from tests.nsx_domain_fixture import scenario
from tests.test_target_campaign import window
from tests.test_nutanix_task_tree import reseal
from provisioner.execution import readback_core as c
from provisioner.execution import qualify_target as q
from provisioner.execution import nsx_domain_switch_observe as combined
from provisioner.execution.run_files import digest, encoded, write_new, load_private, utcnow


def inputs(nsx_origin='https://nsx.example.test', vc_origin='https://vc.example.test'):
    data = list(port_inputs(nsx_origin, vc_origin)); plan, vm, prior, pg, _, _, _, _ = data
    transition, _, network, _ = scenario(nsx_origin); network['profile'] = combined.PROFILE
    network.update({key: vm[key] for key in ('operation_id', 'tenant_id', 'scope_id', 'engineering_record_ref', 'target_binding_ref')})
    segment = network['resources'][1]; segment['logical_switch'] = deepcopy(prior['resources'][0]['logical_switch'])
    segment['logical_switch']['intent_reference'] = [segment['path']]
    pg['resources'][0]['segment_path'] = segment['path']
    domains = transition['prior_outputs']; domains['scope']['value'] = plan['scope'] | {'phase': 'domains'}
    for member in domains['members']['value'].values(): member['lifecycle_stage'] = 'bootstrap'
    domain_inputs = transition['requested_inputs']
    domain_inputs.update({key: plan['scope'][key] for key in ('environment_key', 'site_key', 'tenant_key', 'wsd_key')})
    plan['format'] = q.DOMAIN_CAMPAIGN; plan['assets']['domain_inputs'] = dict(path='/private/domain_inputs', sha256='a'*64)
    data[2] = network; data[4] = domains
    return data, domain_inputs


def assets_at(folder, data, domain_inputs, nf=None, vf=None):
    port_assets_at(folder, data, nf, vf)
    raw = encoded(domain_inputs); (folder/'domain_inputs').write_bytes(raw)
    data[0]['assets']['domain_inputs']['sha256'] = digest(raw)


def execute(folder, data):
    plan = data[0]; raw = encoded(plan); write_new(folder/'plan.json', raw)
    authority = window() | dict(format='hosting-target-campaign-authority/1', plan_sha256=digest(raw), source_commit=plan['source_commit'],
        ssh_sha256=digest(Path('/usr/bin/ssh').read_bytes()), change_ref='FIXTURE', target_binding_ref='FIXTURE', isolation_ref='FIXTURE')
    write_new(folder/'authority.json', encoded(authority))
    argv = ['qualify_target.py', str(folder/'plan.json'), '--execute', '--authority', str(folder/'authority.json'), '--output', str(folder/'campaign')]
    with patch('sys.argv', argv), patch.object(q, 'verify', return_value=dict(status='HASHES_MATCH', commit=plan['source_commit'])), \
         redirect_stdout(io.StringIO()):
        return q.main()


class DomainCampaignTests(unittest.TestCase):
    def test_exact_private_domain_inputs_are_required_before_contact(self):
        data, domain_inputs = inputs()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); assets_at(folder, data, domain_inputs); q.bound_inputs(data[0], str(folder/'known_hosts'))
            (folder/'domain_inputs').write_bytes(b'changed')
            with self.assertRaises(ValueError): q.bound_inputs(data[0], str(folder/'known_hosts'))
        data[0]['assets'].pop('domain_inputs')
        with self.assertRaises(ValueError): q.validate(data[0])

    def test_rehashed_foreign_or_changed_domain_intent_refused_before_contact(self):
        for mutate in (lambda i: i.update(platform_endpoint='https://foreign.example.test'),
                       lambda i: i.update(site_key='foreign'), lambda i: i['members']['D01O'].update(quarantine_sequence=101),
                       lambda i: i['members']['D01O']['bootstrap_rules']['dns'].update(port=54)):
            with tempfile.TemporaryDirectory() as tmp:
                data, domain_inputs = inputs(); mutate(domain_inputs); folder = Path(tmp); assets_at(folder, data, domain_inputs)
                with self.assertRaises(ValueError): q.bound_inputs(data[0], str(folder/'known_hosts'))

    def test_old_profiles_and_campaign_downgrade_cannot_replace_complete_coverage(self):
        for change in ('segment', 'domain', 'portgroup', 'v7', 'nutanix'):
            data, domain_inputs = inputs()
            if change == 'segment': data[2]['profile'] = combined.switches.PROFILE
            if change == 'domain': data[2]['profile'] = combined.domain.PROFILE
            if change == 'portgroup': data[3]['profile'] = 'vsphere-vi-json-8.0.3.0-nsx-portgroups'
            if change == 'v7': data[0]['format'] = 'hosting-target-campaign/7'
            if change == 'nutanix': data[0]['scope']['platform'] = 'nutanix'
            with tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp); assets_at(folder, data, domain_inputs)
                with self.subTest(change=change), self.assertRaises(ValueError): q.bound_inputs(data[0], str(folder/'known_hosts'))

    def test_real_campaign_replays_and_binds_all_five_reports_each_side_of_traffic(self):
        with Fixture() as nf, Fixture() as vf, tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); data, domain_inputs = inputs(nf.origin, vf.origin)
            routes(nf, vf, data); assets_at(folder, data, domain_inputs, nf, vf)
            events = []
            def record(assets, name, report, started, current):
                events.append(name); return original(assets, name, report, started, current)
            original = q.check_campaign_report
            with patch.object(q, 'check_campaign_report', side_effect=record), \
                 patch.object(q, 'ssh_probe', side_effect=lambda *args: events.append('traffic') or {'status': 'HEALTHY'}):
                self.assertEqual(execute(folder, data), 0)
            order = ['native_manifest', 'portgroup_manifest', 'workload_manifest', 'portgroup_manifest', 'native_manifest']
            self.assertEqual(events, order + ['traffic'] + order)
            output = folder/'campaign'; result = load_private(output/'result.json')
            self.assertEqual(result['status'], 'COLLECTED_REQUIRES_INDEPENDENT_ACCEPTANCE'); self.assertFalse(result['production_qualified'])
            self.assertFalse((output/'ssh_key').exists()); self.assertFalse((output/'native_credentials').exists()); self.assertFalse((output/'workload_session').exists())
            for phase in ('native-before', 'native-after'):
                hashes = {key+'_sha256': digest((output/(phase+'-'+key+'.json')).read_bytes())
                          for key in ('network_before', 'portgroups_before', 'workloads', 'portgroups_after', 'network_after')}
                self.assertEqual(result[phase.replace('-', '_')+'_sha256'], digest(encoded(hashes)))
                report = load_private(output/(phase+'-network_before.json'))
                self.assertEqual(report['profile'], combined.PROFILE); self.assertEqual(len(report['history'][-1]['states']), 5)
            self.assertTrue(all(r['method'] == 'GET' and r['has_basic_auth'] and not r['has_session_auth'] for r in nf.requests))
            self.assertTrue(all(r['has_session_auth'] and not r['has_basic_auth'] for r in vf.requests))

    def test_native_policy_failure_prevents_probes_and_keeps_incomplete_packet(self):
        with Fixture() as nf, Fixture() as vf, tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); data, domain_inputs = inputs(nf.origin, vf.origin)
            routes(nf, vf, data); assets_at(folder, data, domain_inputs, nf, vf)
            path = '/policy/api/v1'+data[2]['resources'][3]['path']
            nf.routes[path]['body']['rules'][0]['alternate_selector'] = 'ANY'
            with patch.object(q, 'ssh_probe') as probe: self.assertEqual(execute(folder, data), 2)
            probe.assert_not_called(); self.assertEqual(vf.requests, [])
            output = folder/'campaign'; self.assertEqual(load_private(output/'result.json')['status'], 'HOLD_INCOMPLETE')
            self.assertFalse((output/'ssh_key').exists())

    def test_post_probe_policy_change_prevents_success(self):
        with Fixture() as nf, Fixture() as vf, tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); data, domain_inputs = inputs(nf.origin, vf.origin)
            routes(nf, vf, data); assets_at(folder, data, domain_inputs, nf, vf)
            def probe(*args):
                nf.routes['/policy/api/v1'+data[2]['resources'][3]['path']]['body']['rules'][0]['disabled'] = True
                return {'status': 'HEALTHY'}
            with patch.object(q, 'ssh_probe', side_effect=probe): self.assertEqual(execute(folder, data), 2)
            output = folder/'campaign'; self.assertEqual(load_private(output/'result.json')['status'], 'HOLD_INCOMPLETE')
            self.assertTrue((output/'native-before-network_after.json').exists())
            self.assertFalse((output/'native-after-workloads.json').exists()); self.assertFalse((output/'ssh_key').exists())

    def test_child_summaries_scope_hashes_time_and_witnesses_are_rechecked(self):
        from tests.test_nsx_segment_observe import Client
        data, _ = inputs(); m = data[2]; started = utcnow()
        report = c.observe(m, Client(m), combined, interval=0); assets = {'native_manifest': encoded(m)}
        q.check_campaign_report(assets, 'native_manifest', report, started, utcnow())
        for index, mutate in enumerate((lambda r: r.update(content_sha256='a'*64), lambda r: r.update(manifest_sha256='a'*64),
                       lambda r: r.update(tenant_id='foreign'), lambda r: r.update(stable_rounds=99),
                       lambda r: r['history'][0]['states'][0]['shape_witness'].update(before=False),
                       lambda r: r['history'][0]['states'][-1]['switch_witness']['before'][0].update(state='UNREALIZED'))):
            bad = deepcopy(report); mutate(bad)
            if index >= 4: reseal(bad)
            elif index: bad['content_sha256'] = c.digest({k: v for k, v in bad.items() if k != 'content_sha256'})
            with self.subTest(index=index), self.assertRaises(ValueError): q.check_campaign_report(assets, 'native_manifest', bad, started, utcnow())
        with self.assertRaises(ValueError): q.check_campaign_report(assets, 'native_manifest', report, c.timestamp(report['started_at'])+timedelta(microseconds=1), utcnow())
        with self.assertRaises(ValueError): q.check_campaign_report(assets, 'native_manifest', report, started, c.timestamp(report['completed_at'])+timedelta(seconds=301))

    def test_clone_activity_is_preserved_and_extra_source_work_holds_v8(self):
        from tests.test_vsphere_clone_activity import manifest as clone_manifest
        from tests.test_vsphere_clone_activity_transport import routes as clone_routes
        from tests.test_vsphere_observe import ref
        for extra in (False, True):
            with Fixture() as nf, Fixture() as vf, tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp); data, domain_inputs = inputs(nf.origin, vf.origin); vm = data[1]; clone = clone_manifest(vf.origin)
                vm.update(profile=clone['profile'], task=clone['task']); routes(nf, vf, data)
                client, filters, methods = clone_routes(vf, vm)
                if extra:
                    row = deepcopy(client.activity_rows['vm-9']['completed'][0])
                    row.update(key='task-99', task=ref('Task', 'task-99'), result=ref('VirtualMachine', 'vm-99'))
                    client.activity_rows['vm-9']['completed'].append(row)
                assets_at(folder, data, domain_inputs, nf, vf)
                with patch.object(q, 'ssh_probe', return_value={'status': 'HEALTHY'}) as probe:
                    self.assertEqual(execute(folder, data), 2 if extra else 0)
                report = load_private(folder/'campaign/native-before-workloads.json')
                self.assertEqual(report['profile'], clone['profile'])
                self.assertEqual(report['outcome'], 'HOLD_DIFFERENCE' if extra else 'READBACK_MATCH_NOT_QUALIFIED')
                self.assertEqual(probe.call_count, 0 if extra else 1)
                self.assertEqual(sum(r['path'] == methods[2] for r in vf.requests), len(filters))


if __name__ == '__main__': unittest.main()
