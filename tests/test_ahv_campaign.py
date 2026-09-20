"""Bound AHV workload collection before/after native guest campaigns."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from lab.native_readback_fixture import Fixture, manifest, responses
from tests.test_nutanix_vm_observe import manifest as vm_manifest, uid
from tests.test_target_campaign import plan_fixture, window
from tests.test_guest_inventory import fixture as guests
from tools import nutanix_vm_observe as ahv, qualify_target as q
from tools.guest_inventory import build
from tools.run_files import digest, encoded, write_new


def inputs(origin):
    plan = plan_fixture(); plan.update(format='hosting-target-campaign/3', origin=origin)
    plan['cases'] = plan['cases'][:1]
    plan['assets']['workload_manifest'] = {'path': '/private/workloads', 'sha256': 'a' * 64}
    workload = vm_manifest(origin); workload.update(contact_enabled=True, tenant_id=plan['scope']['tenant_key'], scope_id=plan['scope']['wsd_key'])
    network = manifest('nutanix', origin)
    for key in ('operation_id', 'tenant_id', 'scope_id', 'target_binding_ref', 'engineering_record_ref'): network[key] = workload[key]
    network['resources'][0]['expected']['tenantId'] = uid(2)
    network['resources'].append({'kind': 'subnet', 'ext_id': uid(8), 'expected_etag': '"subnet-1"',
        'expected': {'extId': uid(8), '$objectType': 'networking.v4.config.Subnet', 'tenantId': uid(2),
        'name': 'fixture-subnet', 'subnetType': 'OVERLAY', 'vpcReference': network['resources'][0]['ext_id'],
        'isExternal': False, 'ipConfig': []}})
    network['task']['entity_ids'].append(uid(8))
    outputs, access = guests()
    outputs['members']['value']['guest-01']['vm_id'] = uid(1)
    access['targets']['guest-01']['native_id'] = uid(1)
    access['targets']['guest-01']['address'] = '192.0.2.10'
    return plan, workload, network, outputs, access


class AhvCampaignTests(unittest.TestCase):
    def test_manifest_binding_rejects_foreign_missing_and_disconnected_workloads(self):
        plan, workload, network, outputs, access = inputs('https://prism.example.test')
        q.validate(plan); q.ahv_binding(plan['scope'], workload, outputs, access, network)
        for mutate in (lambda w: w.update(origin='https://foreign.example.test'),
                       lambda w: w.update(scope_id='foreign'), lambda w: w.update(tenant_id='foreign'),
                       lambda w: w.update(target_binding_ref='foreign'), lambda w: w.update(contact_enabled=False),
                       lambda w: w['resources'][0]['expected'].update(tenantId=uid(20)),
                       lambda w: w['resources'][0]['expected'].update(powerState='OFF'),
                       lambda w: w['resources'][0]['expected']['nics'][0]['nicBackingInfo'].update(isConnected=False),
                       lambda w: w['resources'][0]['expected']['nics'][0]['nicNetworkInfo']['subnet'].update(extId=uid(20)),
                       lambda w: w['resources'][0]['expected']['nics'][0]['nicNetworkInfo']['ipv4Config']['ipAddress'].update(value='192.0.2.11')):
            bad = deepcopy(workload); mutate(bad)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): q.ahv_binding(plan['scope'], bad, outputs, access, network)
        outputs['members']['value']['guest-01']['vm_id'] = uid(20)
        with self.assertRaises(ValueError): q.ahv_binding(plan['scope'], workload, outputs, access, network)
        plan['scope']['platform'] = 'vmware'
        with self.assertRaises(ValueError): q.validate(plan)

    def test_bound_inputs_checks_ahv_asset_bytes_before_any_contact(self):
        plan, workload, network, outputs, access = inputs('https://prism.example.test')
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            inventory, _ = build(outputs, access, str(directory / 'known_hosts'))
            values = {'inventory': inventory, 'native_manifest': network, 'workload_manifest': workload}
            for key in plan['assets']:
                raw = encoded(values.get(key, {})); path = directory / key; write_new(path, raw)
                plan['assets'][key] = {'path': str(path), 'sha256': digest(raw)}
            q.bound_inputs(plan, str(directory / 'known_hosts'))
            (directory / 'workload_manifest').write_bytes(b'changed')
            with self.assertRaises(ValueError): q.bound_inputs(plan, str(directory / 'known_hosts'))

    def test_real_observer_children_bind_both_reports_and_hold_on_vm_drift(self):
        with Fixture() as service, tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); plan, workload, network, _, _ = inputs(service.origin)
            service.routes = responses(network)
            resource = workload['resources'][0]; target = ahv.resource_target(resource)
            service.routes[target] = {'body': {'data': resource['expected']}, 'etag': resource['expected_etag']}
            for key, value in (('native_manifest', encoded(network)), ('workload_manifest', encoded(workload)),
                               ('native_ca', (service.directory / 'ca.pem').read_bytes())): write_new(directory / key, value)
            assets = {'native_credentials': encoded({'username': 'fixture', 'password': 'fixture'})}
            result = q.native_readback(plan, assets, window(), directory, 'before')
            expected = {'network_sha256': digest((directory / 'before.json').read_bytes()),
                        'workloads_sha256': digest((directory / 'before-workloads.json').read_bytes())}
            self.assertEqual(result, digest(encoded(expected)))
            self.assertTrue(all(r['method'] == 'GET' for r in service.requests))
            service.routes[target]['body']['data']['host']['extId'] = uid(20)
            with self.assertRaises(ValueError): q.native_readback(plan, assets, window(), directory, 'after')
            self.assertTrue((directory / 'after-workloads.json').exists())


if __name__ == '__main__': unittest.main()
