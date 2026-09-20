"""Bind owned VM identities to dual-origin NSX/vCenter collection."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from lab.native_readback_fixture import Fixture, manifest as network_manifest, responses
from tests.test_vsphere_observe import manifest, Client
from tests.test_vsphere_task_observe import manifest as task_manifest, task_body
from tests.test_target_campaign import plan_fixture, window
from tests.test_guest_inventory import fixture as guests
from tools import qualify_target as q, vsphere_task_observe as tasks
from tools.guest_inventory import build
from tools.run_files import digest, encoded, write_new


def inputs(nsx_origin, vc_origin, task=False):
    plan = plan_fixture(); plan.update(format='hosting-target-campaign/5', origin=nsx_origin)
    plan['scope']['platform'] = 'vmware'; plan['cases'] = plan['cases'][:1]
    plan['assets'].update({key: dict(path='/private/' + key, sha256='a' * 64) for key in q.VSPHERE_ASSETS})
    vm = (task_manifest if task else manifest)(vc_origin)
    vm.update(contact_enabled=True, tenant_id=plan['scope']['tenant_key'], scope_id=plan['scope']['wsd_key'])
    network = network_manifest('nsx', nsx_origin)
    for key in ('operation_id', 'tenant_id', 'scope_id', 'target_binding_ref', 'engineering_record_ref'): network[key] = vm[key]
    outputs, access = guests(); outputs['scope']['value']['platform'] = 'vmware'
    outputs['members']['value']['guest-01']['vm_id'] = vm['resources'][0]['expected']['config']['uuid']
    access['targets']['guest-01']['native_id'] = outputs['members']['value']['guest-01']['vm_id']
    return plan, vm, network, outputs, access


class VsphereCampaignTests(unittest.TestCase):
    def test_both_profiles_require_exact_owned_uuids_and_live_nics(self):
        for task in (False, True):
            plan, vm, network, outputs, _ = inputs('https://nsx.example.test', 'https://vc.example.test', task)
            q.validate(plan); q.vsphere_binding(plan['scope'], vm, outputs, network)
            for mutate in (lambda v: v.update(target_binding_ref='foreign'), lambda v: v.update(tenant_id='foreign'),
                lambda v: v.update(contact_enabled=False), lambda v: v['resources'][0]['expected']['runtime'].update(powerState='poweredOff'),
                lambda v: v['resources'][0]['expected']['config']['hardware']['device'][2]['connectable'].update(connected=False)):
                bad = deepcopy(vm); mutate(bad)
                with self.assertRaises(ValueError): q.vsphere_binding(plan['scope'], bad, outputs, network)
            outputs['members']['value']['guest-01']['vm_id'] = 'foreign'
            with self.assertRaises(ValueError): q.vsphere_binding(plan['scope'], vm, outputs, network)

    def test_private_assets_bound_before_contact(self):
        plan, vm, network, outputs, access = inputs('https://nsx.example.test', 'https://vc.example.test')
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); inventory, _ = build(outputs, access, str(directory / 'known_hosts'))
            values = dict(inventory=inventory, native_manifest=network, workload_manifest=vm)
            for key in plan['assets']:
                raw = encoded(values.get(key, {})); path = directory / key; write_new(path, raw)
                plan['assets'][key] = dict(path=str(path), sha256=digest(raw))
            q.bound_inputs(plan, str(directory / 'known_hosts'))
            (directory / 'workload_manifest').write_bytes(b'changed')
            with self.assertRaises(ValueError): q.bound_inputs(plan, str(directory / 'known_hosts'))

    def test_real_children_use_separate_origins_trust_and_credentials(self):
        with Fixture() as nsx, Fixture() as vc, tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); plan, vm, network, _, _ = inputs(nsx.origin, vc.origin, task=True)
            nsx.routes = responses(network)
            vc.routes = {key: dict(body=value) for key, value in Client(vm).routes.items()}
            path = tasks.task_target(vm['task']['records'][0]); vc.routes[path] = dict(body=task_body(vm))
            assets = {'native_credentials': encoded(dict(username='fixture', password='fixture')),
                      'workload_manifest': encoded(vm), 'workload_session': b'fixture-session'}
            for key, value in (('native_manifest', encoded(network)), ('workload_manifest', assets['workload_manifest']),
                ('native_ca', (nsx.directory / 'ca.pem').read_bytes()), ('workload_ca', (vc.directory / 'ca.pem').read_bytes())):
                write_new(directory / key, value)
            actual = q.native_readback(plan, assets, window(), directory, 'before')
            expected = dict(network_sha256=digest((directory / 'before.json').read_bytes()),
                            workloads_sha256=digest((directory / 'before-workloads.json').read_bytes()))
            self.assertEqual(actual, digest(encoded(expected)))
            self.assertTrue(all(x['has_basic_auth'] and not x['has_session_auth'] for x in nsx.requests))
            self.assertTrue(all(x['has_session_auth'] and not x['has_basic_auth'] for x in vc.requests))
            vc.routes[path]['body']['state'] = 'error'
            with self.assertRaises(ValueError): q.native_readback(plan, assets, window(), directory, 'after')


if __name__ == '__main__': unittest.main()
