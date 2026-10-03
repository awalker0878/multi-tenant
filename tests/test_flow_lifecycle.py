"""Flow exact-plan scope and security negatives; no enforcement qualification."""
from copy import deepcopy
from datetime import timedelta
import json
import unittest
from provisioner.execution import lifecycle_transition as t, terraform_run as run
from provisioner.compiler.wsd import STATE
from provisioner.execution.plan_review import review
from provisioner.execution.run_files import digest, encoded, utcnow

CATEGORY = '11111111-1111-4111-8111-111111111111'
VPC = '22222222-2222-4222-8222-222222222222'
POLICY = '33333333-3333-4333-8333-333333333333'


def policy(services):
    group = {'secured_group_category_associated_entity_type': 'VM', 'secured_group_category_references': [CATEGORY]}
    baseline = group | {'src_allow_spec': 'NONE', 'dest_allow_spec': 'NONE'}
    rules = [{'type': 'APPLICATION', 'spec': [{'application_rule_spec': [deepcopy(baseline)]}]},
             {'type': 'INTRA_GROUP', 'spec': [{'intra_entity_group_rule_spec': [group | {'secured_group_action': 'DENY'}]}]}]
    for name, service in sorted(services.items()):
        side = 'src' if service['direction'] == 'ingress' else 'dest'
        spec = baseline | {'src_category_associated_entity_type': 'VM', 'dest_category_associated_entity_type': 'VM',
            'is_all_protocol_allowed': False, side + '_subnet': [{'value': service['remote_ipv4'], 'prefix_length': 32}],
            service['protocol'] + '_services': [{'start_port': service['port'], 'end_port': service['port']}]}
        rules.append({'type': 'APPLICATION', 'description': name, 'spec': [{'application_rule_spec': [spec]}]})
    return {'id': POLICY, 'ext_id': POLICY, 'type': 'APPLICATION', 'state': 'ENFORCE', 'scope': 'VPC_LIST',
            'vpc_reference': [VPC], 'is_hitlog_enabled': True, 'is_ipv6_traffic_allowed': False, 'rules': rules}


def fixture(stage='bootstrap'):
    inputs = json.loads((run.ROOT / 'terraform/stacks/wsd/nutanix/domains/inputs.tfvars.json.example').read_text())
    inputs.update(allow_restricted_build=True, test_authorization_ref='FIXTURE')
    previous = deepcopy(inputs); _, scope, _ = run.select_scope(run.ROOT, 'nutanix-wsd-domains', inputs)
    outputs = {'scope': {'value': scope}, 'delivery_state': {'value': STATE}, 'members': {'value': {}}}
    services = {'dns': {'direction': 'egress', 'protocol': 'udp', 'port': 53, 'remote_ipv4': '192.0.2.130'}}
    for name, member in inputs['members'].items():
        member.update(lifecycle_stage=stage, bootstrap_acceptance_ref='FIXTURE', bootstrap_rules=services)
        outputs['members']['value'][name] = {'delivery_state': STATE, 'quarantine_policy_id': POLICY, 'vpc_id': VPC, 'security_category_id': CATEGORY}
    record = dict(format=t.FORMAT, scope=scope, input_sha256=digest(encoded(inputs)), prior_bundle_sha256='a' * 64,
                  prior_inputs=previous, requested_inputs=inputs, prior_outputs=outputs, target_stage=stage,
                  valid_from=(utcnow()-timedelta(seconds=1)).isoformat(), valid_until=(utcnow()+timedelta(minutes=10)).isoformat(),
                  acceptance_refs={k: 'FIXTURE' for k in t.os_transition.REFS})
    record['resources'] = t.bindings(record)
    changes = [dict(address=address, type=spec['type'], mode='managed', provider_name='registry.terraform.io/nutanix/nutanix',
        change={'actions': ['update'], 'before': policy({} if stage == 'bootstrap' else services),
                'after': policy(services if stage == 'bootstrap' else {}), 'after_unknown': {}}) for address, spec in record['resources'].items()]
    return record, {'format_version': '1.2', 'complete': True, 'resource_changes': changes}


class FlowLifecycleTests(unittest.TestCase):
    def test_bootstrap_and_withdrawal_are_bound_to_prior_native_policy(self):
        for stage in ('bootstrap', 'prepared'):
            record, plan = fixture(stage)
            t.validate(record, record['scope'], encoded(record['requested_inputs']))
            self.assertNotEqual(review(plan, transition=record)['status'], 'BLOCKED')
            if stage == 'bootstrap': self.assertEqual(review(plan)['status'], 'BLOCKED')
    def test_widened_policy_selectors_and_service_rejected(self):
        mutations = [lambda a: a.update(scope='GLOBAL'), lambda a: a.update(state='MONITOR'),
                     lambda a: a.update(vpc_reference=[VPC, CATEGORY]), lambda a: a.update(is_hitlog_enabled=False),
                     lambda a: a.update(is_ipv6_traffic_allowed=True), lambda a: a['rules'].pop(1)]
        for mutate in mutations:
            record, plan = fixture(); mutate(plan['resource_changes'][0]['change']['after'])
            with self.subTest(mutate=mutate): self.assertEqual(review(plan, transition=record)['status'], 'BLOCKED')
        for key, value in [('dest_allow_spec', 'ALL'), ('is_all_protocol_allowed', True),
                           ('dest_subnet', [{'value': '192.0.2.0', 'prefix_length': 24}]),
                           ('udp_services', [{'start_port': 1, 'end_port': 65535}]),
                           ('src_category_references', [CATEGORY]), ('network_function_reference', POLICY),
                           ('secured_group_category_references', [VPC]), ('unknown_selector', True)]:
            record, plan = fixture(); app = plan['resource_changes'][0]['change']['after']['rules'][2]['spec'][0]['application_rule_spec'][0]
            app[key] = value
            with self.subTest(key=key): self.assertEqual(review(plan, transition=record)['status'], 'BLOCKED')
    def test_unknown_security_is_held_but_computed_rule_id_is_allowed(self):
        record, plan = fixture(); change = plan['resource_changes'][0]['change']
        change['after_unknown']['rules'] = [{}, {}, {'ext_id': True}]
        self.assertNotEqual(review(plan, transition=record)['status'], 'BLOCKED')
        change['after_unknown']['rules'][2]['spec'] = True
        self.assertEqual(review(plan, transition=record)['status'], 'BLOCKED')
    def test_replacement_or_unrelated_native_change_is_held(self):
        for mutate in (lambda c: c.update(actions=['delete', 'create']), lambda c: c['after'].update(ext_id=VPC),
                       lambda c: c['after'].update(name='other'), lambda c: c['after']['rules'][0].update(ext_id=POLICY)):
            record, plan = fixture(); mutate(plan['resource_changes'][0]['change'])
            with self.subTest(mutate=mutate): self.assertEqual(review(plan, transition=record)['status'], 'BLOCKED')


if __name__ == '__main__': unittest.main()
