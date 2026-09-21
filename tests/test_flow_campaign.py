"""Bind Flow, VM membership and native subnets around guest traffic."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from lab.native_readback_fixture import Fixture, responses
from tests.test_ahv_campaign import inputs as ahv_inputs
from tests.test_nutanix_flow_observe import manifest as flow_manifest
from tests.test_nutanix_vm_observe import uid
from tests.test_target_campaign import window
from tools import nutanix_vm_observe as ahv, nutanix_flow_observe as flow, qualify_target as q
from tests.test_nutanix_flow_activity import manifest as activity_manifest, responses as activity_responses
from tools import nutanix_flow_activity_observe as activity, readback_core as c
from tools.guest_inventory import build
from tools.run_files import digest, encoded, write_new


def inputs(origin):
    plan, workload, network, outputs, access = ahv_inputs(origin)
    plan['format'] = 'hosting-target-campaign/4'
    for key in q.FLOW_ASSETS: plan['assets'][key] = dict(path='/private/' + key, sha256='a' * 64)
    policy = flow_manifest(origin)
    for key in ('operation_id', 'tenant_id', 'scope_id', 'target_binding_ref', 'engineering_record_ref', 'contact_enabled'):
        policy[key] = network[key]
    vpc = network['resources'][0]['ext_id']; r = policy['resources'][0]
    r['vpc_id'] = vpc; r['expected']['vpcReferences'] = [vpc]
    domains = dict(scope={'value': plan['scope'] | {'phase': 'domains'}}, delivery_state={'value': q.STATE},
        members={'value': {'domain-01': dict(quarantine_policy_id=r['ext_id'], security_category_id=r['category_id'],
                                         vpc_id=vpc, delivery_state=q.STATE)}})
    return plan, workload, network, outputs, access, policy, domains


class FlowCampaignTests(unittest.TestCase):
    def test_domain_ownership_and_vm_category_vpc_must_agree(self):
        plan, workload, network, _, _, policy, domains = inputs('https://prism.example.test')
        q.validate(plan); q.flow_binding(plan['scope'], policy, domains, workload, network)
        for mutate in (lambda p, d, w, n: p.update(target_binding_ref='foreign'),
            lambda p, d, w, n: p.update(contact_enabled=False),
            lambda p, d, w, n: d['scope']['value'].update(tenant_key='foreign'),
            lambda p, d, w, n: d['members']['value']['domain-01'].update(quarantine_policy_id=uid(80)),
            lambda p, d, w, n: d['members']['value']['domain-01'].update(security_category_id=uid(80)),
            lambda p, d, w, n: w['resources'][0]['expected'].update(categories=[{'extId': uid(80)}]),
            lambda p, d, w, n: n['resources'][1]['expected'].update(vpcReference=uid(80)),
            lambda p, d, w, n: p['resources'][0]['expected'].update(tenantId=uid(80))):
            p, d, w, n = deepcopy((policy, domains, workload, network)); mutate(p, d, w, n)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): q.flow_binding(plan['scope'], p, d, w, n)

    def test_asset_bytes_and_bindings_checked_before_contact(self):
        plan, workload, network, outputs, access, policy, domains = inputs('https://prism.example.test')
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); inventory, _ = build(outputs, access, str(directory / 'known_hosts'))
            values = dict(inventory=inventory, native_manifest=network, workload_manifest=workload,
                          flow_manifest=policy, domain_outputs=domains)
            for key in plan['assets']:
                raw = encoded(values.get(key, {})); path = directory / key; write_new(path, raw)
                plan['assets'][key] = dict(path=str(path), sha256=digest(raw))
            q.bound_inputs(plan, str(directory / 'known_hosts'))
            (directory / 'domain_outputs').write_bytes(b'changed')
            with self.assertRaises(ValueError): q.bound_inputs(plan, str(directory / 'known_hosts'))

    def test_real_children_cover_all_three_and_hold_on_flow_drift(self):
        with Fixture() as service, tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); plan, workload, network, _, _, policy, _ = inputs(service.origin)
            service.routes = responses(network)
            for adapter, m in ((ahv, workload), (flow, policy)):
                r = m['resources'][0]
                service.routes[adapter.resource_target(r)] = dict(body={'data': r['expected']}, etag=r['expected_etag'])
            for key, value in (('native_manifest', encoded(network)), ('workload_manifest', encoded(workload)),
                ('flow_manifest', encoded(policy)), ('native_ca', (service.directory / 'ca.pem').read_bytes())):
                write_new(directory / key, value)
            assets = {'native_credentials': encoded(dict(username='fixture', password='fixture')),
                      'workload_manifest': encoded(workload), 'flow_manifest': encoded(policy)}
            result = q.native_readback(plan, assets, window(), directory, 'before')
            expected = {key + '_sha256': digest((directory / (name + '.json')).read_bytes())
                        for key, name in [('network', 'before'), ('workloads', 'before-workloads'), ('flow', 'before-flow')]}
            self.assertEqual(result, digest(encoded(expected)))
            policy['resources'][0]['expected']['rules'][2]['spec']['destAllowSpec'] = 'ALL'
            with self.assertRaises(ValueError): q.native_readback(plan, assets, window(), directory, 'after')
            self.assertTrue((directory / 'after-flow.json').exists())
            self.assertTrue(all(r['method'] == 'GET' for r in service.requests))

    def test_activity_profile_dispatch_preserves_ownership_and_all_report_hashes(self):
        with Fixture() as service, tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); plan, workload, network, _, _, policy, domains = inputs(service.origin)
            policy['profile'] = activity.PROFILE; policy['task'] = activity_manifest()['task']
            q.flow_binding(plan['scope'], policy, domains, workload, network)
            service.routes = responses(network); service.routes.update(activity_responses(policy))
            r = workload['resources'][0]
            service.routes[ahv.resource_target(r)] = dict(body={'data': r['expected']}, etag=r['expected_etag'])
            for key, value in (('native_manifest', encoded(network)), ('workload_manifest', encoded(workload)),
                ('flow_manifest', encoded(policy)), ('native_ca', (service.directory/'ca.pem').read_bytes())):
                write_new(directory/key, value)
            assets = dict(native_credentials=encoded(dict(username='fixture', password='fixture')),
                          workload_manifest=encoded(workload), flow_manifest=encoded(policy))
            result = q.native_readback(plan, assets, window(), directory, 'activity')
            expected = {key + '_sha256': digest((directory/(name+'.json')).read_bytes())
                        for key, name in [('network', 'activity'), ('workloads', 'activity-workloads'), ('flow', 'activity-flow')]}
            self.assertEqual(result, digest(encoded(expected)))
            report = c.load(directory/'activity-flow.json'); self.assertEqual(report['profile'], activity.PROFILE)
            from tools import nutanix_entity_activity as queries
            service.routes[queries.target(policy, policy['resources'][0]['ext_id'], 0)]['body'].update(
                data=[], metadata={'totalAvailableResults': 0})
            with self.assertRaises(ValueError): q.native_readback(plan, assets, window(), directory, 'held')
            self.assertEqual(c.load(directory/'held-flow.json')['outcome'], 'HOLD_DIFFERENCE')

    def test_unknown_flow_profile_has_no_snapshot_fallback(self):
        plan, workload, network, _, _, policy, domains = inputs('https://prism.example.test')
        policy['profile'] = 'future-unqualified-profile'
        with self.assertRaises(ValueError): q.flow_binding(plan['scope'], policy, domains, workload, network)


if __name__ == '__main__': unittest.main()
