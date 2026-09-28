import copy
import json
import unittest

from provisioner.compiler.wsd import COMPONENTS, NETWORK, ROOT, STATE, compile_environment


def example(platform='nutanix'):
    return json.loads((ROOT / f'examples/environments/{platform}.json.example').read_text())


def receipts(env):
    outputs, bindings = {}, {}
    for wsd in env['wsds']:
        key = wsd['tenant_key'] + '/' + wsd['wsd_key']
        scope = {k: env[k] for k in ('environment_key', 'site_key', 'platform')}
        scope.update(tenant_key=wsd['tenant_key'], wsd_key=wsd['wsd_key'], phase='domains')
        members = {}
        for domain in wsd['domains']:
            native = {k: domain['id'] + '-' + k for k in NETWORK[env['platform']]}
            native.update(delivery_state=STATE, segment_path='/infra/' + domain['id'])
            members[domain['id']] = native
            bindings[key + '/' + domain['id']] = {'segment_path': native['segment_path'], 'network_id': 'network-' + domain['id']}
        outputs[key] = {'scope': {'value': scope}, 'members': {'value': members}, 'delivery_state': {'value': STATE}}
    return outputs, bindings


class WsdCompilerTests(unittest.TestCase):
    def test_initial_compiler_cannot_bootstrap(self):
        for key, value in [('lifecycle_stage', 'bootstrap'),
                           ('bootstrap_acceptance_ref', 'CHG-123'),
                           ('bootstrap_rules', {'ssh': {}})]:
            env = example('openstack')
            env['wsds'][0]['domains'][0]['inputs'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                compile_environment(env)

    def test_two_tenants_four_domains_three_platforms(self):
        for platform in COMPONENTS:
            with self.subTest(platform=platform):
                env = example(platform)
                files, plan = compile_environment(env)
                self.assertEqual(sum(len(v['members']) for v in files.values()), 4)
                self.assertEqual(len({s['state_key'] for s in plan['scopes']}), 2)
                self.assertFalse(any(v['allow_restricted_build'] for v in files.values()))
                outputs, bindings = receipts(env)
                files, plan = compile_environment(env, 'workloads', outputs, bindings)
                self.assertEqual(sum(len(v['members']) for v in files.values()), 4)
                for values in files.values():
                    self.assertFalse(values['allow_restricted_build'])
                    self.assertTrue(all(v['accepted_quarantine_ref'] == '' for v in values['members'].values()))

    def test_zone_trust_entitlement_and_dedication_reject(self):
        mutations = [('zone', 'RZ'), ('role', 'management'), ('trust', 'other-trust'),
                     ('eligible_tenants', ['tenant-99']), ('service_classes', ['other-class']),
                     ('dedicated_wsd', 'tenant-99/wsd-99')]
        for field, value in mutations:
            with self.subTest(field=field):
                env = example(); env['clusters'][0][field] = value
                with self.assertRaises(ValueError):
                    compile_environment(env)

    def test_overlapping_hosts_reject(self):
        env = example(); env['clusters'][1]['host_ids'] = env['clusters'][0]['host_ids']
        with self.assertRaisesRegex(ValueError, 'Physical hosts'):
            compile_environment(env)

    def test_native_placement_cannot_be_overridden(self):
        env = example(); values = next(iter(env['wsds'][0]['domains'][0]['workloads'].values()))
        values['cluster_id'] = 'escape'
        with self.assertRaisesRegex(ValueError, 'owned native input'):
            compile_environment(env)

    def test_cross_environment_outputs_reject(self):
        env = example(); outputs, bindings = receipts(env)
        outputs['tenant-01/wsd-01']['scope']['value']['environment_key'] = 'production-01'
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            compile_environment(env, 'workloads', outputs, bindings)

    def test_missing_or_extra_output_scopes_reject(self):
        env = example(); outputs, _ = receipts(env)
        outputs['unexpected'] = copy.deepcopy(next(iter(outputs.values())))
        with self.assertRaises(ValueError):
            compile_environment(env, 'workloads', outputs)
        with self.assertRaises(ValueError):
            compile_environment(env, 'workloads', {})

    def test_vmware_requires_segment_network_binding(self):
        env = example('vmware'); outputs, bindings = receipts(env)
        with self.assertRaisesRegex(ValueError, 'explicitly mapped'):
            compile_environment(env, 'workloads', outputs)
        next(iter(bindings.values()))['segment_path'] = '/wrong'
        with self.assertRaises(ValueError):
            compile_environment(env, 'workloads', outputs, bindings)

    def test_duplicate_names_across_tenants_reject(self):
        env = example(); name = next(iter(env['wsds'][0]['domains'][0]['workloads']))
        other = env['wsds'][1]['domains'][0]
        other['workloads'] = {name: next(iter(other['workloads'].values()))}
        with self.assertRaisesRegex(ValueError, 'native name reused'):
            compile_environment(env)

    def test_address_outside_domain_reject(self):
        env = example(); next(iter(env['wsds'][0]['domains'][0]['workloads'].values()))['ipv4_address'] = '198.51.100.2'
        with self.assertRaisesRegex(ValueError, 'workload address'):
            compile_environment(env)
