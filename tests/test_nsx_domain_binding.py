from copy import deepcopy
import unittest
from tests.nsx_domain_fixture import scenario
from provisioner.execution import nsx_domain_binding as binding


def fixture(stage='bootstrap'):
    transition, _, manifest, _ = scenario('https://nsx.example.test', stage)
    outputs = transition['prior_outputs']; inputs = transition['requested_inputs']
    for member in outputs['members']['value'].values(): member['lifecycle_stage'] = stage
    return transition['scope'] | {}, outputs, inputs, manifest


class DomainBindingTests(unittest.TestCase):
    def bind(self, data):
        scope, outputs, inputs, manifest = data
        return binding.bind({k: v for k, v in scope.items() if k != 'phase'}, outputs, inputs, manifest)

    def test_both_lifecycle_targets_bind_every_owned_object(self):
        for stage in ('bootstrap', 'prepared'):
            data = fixture(stage); result = self.bind(data)
            self.assertEqual(set(result['D01O']), {'tier1_path', 'segment_path', 'group_path', 'quarantine_policy_path'})

    def test_scope_endpoint_member_and_output_stage_substitution_refused(self):
        for mutate in (lambda d: d[2].update(platform_endpoint='https://foreign.example.test'),
                       lambda d: d[2].update(environment_key='foreign'), lambda d: d[2].update(allow_restricted_build=False),
                       lambda d: d[1]['members']['value']['D01O'].update(lifecycle_stage='prepared'),
                       lambda d: d[1]['members']['value']['D01O'].update(tier1_path='/infra/tier-1s/foreign'),
                       lambda d: d[1]['members']['value'].update(other=deepcopy(d[1]['members']['value']['D01O'])),
                       lambda d: d[3].update(tenant_id='foreign'), lambda d: d[3].update(scope_id='foreign')):
            data = fixture(); mutate(data)
            with self.assertRaises(ValueError): self.bind(data)

    def test_input_allocation_stage_or_security_change_cannot_match_old_observation(self):
        for changes in [dict(ipv4_cidr='192.0.2.0/26'), dict(gateway_host_number=2), dict(gateway_host_number=True),
                        dict(gateway_host_number=31), dict(transport_zone_path='/infra/foreign'), dict(quarantine_sequence=101),
                        dict(quarantine_sequence=True), dict(lifecycle_stage='prepared'), dict(bootstrap_acceptance_ref='')]:
            data = fixture(); data[2]['members']['D01O'].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError): self.bind(data)
        for changes in [dict(protocol='tcp'), dict(port=54), dict(direction='ingress'), dict(remote_ipv4='192.0.2.2')]:
            data = fixture(); data[2]['members']['D01O']['bootstrap_rules']['dns'].update(changes)
            with self.assertRaises(ValueError): self.bind(data)

    def test_native_policy_cannot_weaken_or_reorder_accepted_intent(self):
        for mutate in (lambda p: p.update(locked=True), lambda p: p.update(sequence_number=101),
                       lambda p: p.update(tcp_strict=False), lambda p: p['rules'].reverse(),
                       lambda p: p['rules'][0].update(logged=False), lambda p: p['rules'][0].update(profiles=[]),
                       lambda p: p['rules'][1].update(source_groups=['192.0.2.8/32']),
                       lambda p: p['rules'][1].update(ip_protocol='IPV4'),
                       lambda p: p['rules'][0]['service_entries'][0].update(destination_ports=['54'])):
            data = fixture(); mutate(data[3]['resources'][3]['expected'])
            with self.assertRaises(ValueError): self.bind(data)

    def test_accepted_native_sequences_need_strict_order_but_not_invented_numbers(self):
        data = fixture(); rules = data[3]['resources'][3]['expected']['rules']
        rules[0]['sequence_number'] = 10; rules[1]['sequence_number'] = 20; self.bind(data)
        rules[0]['sequence_number'] = 30
        with self.assertRaises(ValueError): self.bind(data)

    def test_retained_services_do_not_create_prepared_allow_rules(self):
        data = fixture('prepared'); self.assertTrue(data[2]['members']['D01O']['bootstrap_rules']); self.bind(data)
        bootstrap = fixture()[3]['resources'][3]['expected']['rules']
        data[3]['resources'][3]['expected']['rules'] = bootstrap
        with self.assertRaises(ValueError): self.bind(data)

    def test_reserved_terminal_rule_name_and_unreviewed_input_fields_refused(self):
        data = fixture(); services = data[2]['members']['D01O']['bootstrap_rules']
        services['deny-scoped-ip-traffic'] = services.pop('dns')
        with self.assertRaises(ValueError): self.bind(data)
        data = fixture(); data[2]['platform_password'] = 'NOT-A-CREDENTIAL'
        with self.assertRaises(ValueError): self.bind(data)
        data = fixture(); data[2]['members']['D01O']['exclude_from_dfw'] = True
        with self.assertRaises(ValueError): self.bind(data)

    def test_two_owned_domains_cannot_share_or_swap_native_objects(self):
        data = fixture(); _, outputs, inputs, manifest = data
        native = outputs['members']['value']['D01O']
        paths = {native[key]: native[key] + '-other' for key, _ in binding.OBJECTS.values()}
        def renamed(value):
            if isinstance(value, dict): return {k: renamed(v) for k, v in value.items()}
            if isinstance(value, list): return [renamed(v) for v in value]
            if isinstance(value, str):
                for old, new in paths.items(): value = value.replace(old, new)
                return value.replace('tenant-01-D01O', 'tenant-01-D02R')
            return value
        others = renamed(deepcopy(manifest['resources']))
        for resource in others: resource['expected']['id'] = resource['path'].rsplit('/', 1)[1]
        manifest['resources'].extend(others)
        outputs['members']['value']['D02R'] = renamed(deepcopy(native))
        inputs['members']['D02R'] = deepcopy(inputs['members']['D01O'])
        self.assertEqual(set(self.bind(data)), {'D01O', 'D02R'})
        outputs['members']['value']['D02R']['tier1_path'] = native['tier1_path']
        with self.assertRaises(ValueError): self.bind(data)


if __name__ == '__main__': unittest.main()
