import copy
from datetime import timedelta
import json
import unittest
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid5

from tools import openstack_transition as t, terraform_apply as apply, terraform_run as run
from provisioner.compiler.wsd import STATE
from tools.plan_review import review
from tools.run_files import digest, encoded, load_private, read_private, utcnow, write_new
from test_terraform_run import TerraformRunFixture


def fixture(phase='domains', stage='bootstrap'):
    inputs = json.loads((run.ROOT / f'terraform/stacks/wsd/openstack/{phase}/inputs.tfvars.json.example').read_text())
    inputs.update(allow_restricted_build=True, test_authorization_ref='CHG-FIXTURE')
    _, scope, _ = run.select_scope(run.ROOT, 'openstack-wsd-' + phase, inputs)
    members = {}
    for name, value in inputs['members'].items():
        value.update(lifecycle_stage=stage, bootstrap_acceptance_ref='ACCEPTED-FIXTURE-ONLY')
        members[name] = {'delivery_state': STATE, **{key: str(uuid5(NAMESPACE_URL, name + key))
                          for key in ('network_id', 'router_id', 'security_group_id', 'server_id', 'port_id')}}
        if phase == 'domains':
            value['bootstrap_rules'] = {'dns': {'direction': 'egress', 'protocol': 'udp', 'port': 53, 'remote_ipv4': '10.42.0.53'}}
            members[name]['bootstrap_rule_ids'] = {} if stage == 'bootstrap' else {'dns': str(uuid5(NAMESPACE_URL, name + 'dns'))}
        else: value['config_drive'] = True
    outputs = {'scope': {'value': scope}, 'members': {'value': members}, 'delivery_state': {'value': STATE}}
    now = utcnow()
    record = {'format': 'hosting-openstack-transition/1', 'scope': scope, 'input_sha256': digest(encoded(inputs)),
              'prior_bundle_sha256': 'a' * 64, 'prior_outputs': outputs, 'target_stage': stage,
              'valid_from': (now - timedelta(minutes=1)).isoformat(), 'valid_until': (now + timedelta(minutes=10)).isoformat(),
              'acceptance_refs': {k: 'FIXTURE-' + k for k in t.REFS}, 'resources': t.bindings(scope, inputs, outputs, stage)}
    changes = []
    for address, spec in record['resources'].items():
        after = {'id': spec['id'], **spec['values']}
        if spec['type'] == 'openstack_networking_network_v2': after.update(shared=False, external=False, port_security_enabled=True)
        if spec['type'] == 'openstack_networking_port_v2': after.update(port_security_enabled=True, security_group_ids=['group'])
        if spec['type'] == 'openstack_compute_instance_v2': after.update(config_drive=True, block_device=[{'delete_on_termination': False}])
        before = copy.deepcopy(after) if spec['id'] else None
        if before and spec['type'] != t.RULE:
            field = t.FIELDS[spec['type']][1]
            before[field] = not after[field] if field == 'admin_state_up' else ('shutoff' if stage == 'bootstrap' else 'active')
        actions = ['create'] if before is None else ['no-op'] if before == after else ['update']
        changes.append({'address': address, 'type': spec['type'], 'mode': 'managed',
                        'provider_name': 'registry.terraform.io/terraform-provider-openstack/openstack',
                        'change': {'before': before, 'after': after, 'actions': actions, 'after_unknown': {}}})
    return inputs, record, {'format_version': '1.2', 'complete': True, 'resource_changes': changes}


class TransitionTests(unittest.TestCase):
    def test_bootstrap_and_withdrawal_require_exact_contract(self):
        for phase in ('domains', 'workloads'):
            for stage in ('prepared', 'bootstrap'):
                with self.subTest(phase=phase, stage=stage):
                    inputs, record, plan = fixture(phase, stage)
                    t.validate(record, record['scope'], encoded(inputs))
                    self.assertNotEqual(review(plan, transition=record)['status'], 'BLOCKED')
                    if stage == 'bootstrap' or phase == 'domains': self.assertEqual(review(plan)['status'], 'BLOCKED')

    def test_cross_scope_inputs_and_tampered_ownership_rejected(self):
        inputs, record, _ = fixture()
        for mutation in ('inputs', 'scope', 'id'):
            r = copy.deepcopy(record); values = copy.deepcopy(inputs); scope = copy.deepcopy(record['scope'])
            if mutation == 'inputs': values['test_authorization_ref'] = 'OTHER'
            if mutation == 'scope': scope['tenant_key'] = 'other-tenant'
            if mutation == 'id': next(iter(r['resources'].values()))['id'] = str(uuid5(NAMESPACE_URL, 'foreign'))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): t.validate(r, scope, encoded(values))

    def test_unrelated_mutations_replacement_unknown_and_drift_block(self):
        _, record, base = fixture()
        for mutation in ('delete', 'other_id', 'other_attribute', 'unknown', 'missing', 'extra', 'drift', 'import'):
            plan = copy.deepcopy(base); item = plan['resource_changes'][0]; change = item['change']
            if mutation == 'delete': change['actions'] = ['delete', 'create']
            if mutation == 'other_id': change['after']['id'] = str(uuid5(NAMESPACE_URL, 'other'))
            if mutation == 'other_attribute': change['after']['mtu'] = 1400
            if mutation == 'unknown': change['after_unknown']['admin_state_up'] = True
            if mutation == 'missing': plan['resource_changes'].pop()
            if mutation == 'extra':
                extra = copy.deepcopy(item); extra['address'] = 'foreign'; plan['resource_changes'].append(extra)
            if mutation == 'drift': plan['resource_drift'] = [item]
            if mutation == 'import': change['importing'] = {'id': 'x'}
            with self.subTest(mutation=mutation): self.assertEqual(review(plan, transition=record)['status'], 'BLOCKED')

    def test_rule_widening_and_scalar_override_block(self):
        _, record, plan = fixture()
        rule = next(i for i in plan['resource_changes'] if i['type'] == t.RULE)
        rule['change']['after']['remote_ip_prefix'] = '0.0.0.0/0'
        self.assertEqual(review(plan, transition=record)['status'], 'BLOCKED')

    def test_missing_native_security_fields_cannot_be_approved_as_review_only(self):
        for phase, kind, field in [('domains', 'openstack_networking_network_v2', 'port_security_enabled'),
                                    ('workloads', 'openstack_networking_port_v2', 'security_group_ids'),
                                    ('workloads', 'openstack_compute_instance_v2', 'block_device')]:
            _, record, plan = fixture(phase)
            change = next(r['change'] for r in plan['resource_changes'] if r['type'] == kind)
            del change['before'][field]; del change['after'][field]
            with self.subTest(field=field): self.assertEqual(review(plan, transition=record)['status'], 'BLOCKED')
        _, record, plan = fixture()
        next(iter(record['resources'].values()))['values']['port_security_enabled'] = False
        self.assertEqual(review(plan, transition=record)['status'], 'BLOCKED')

    def test_withdrawal_cannot_drop_or_create_rules(self):
        inputs, record, _ = fixture(stage='prepared')
        member = next(iter(inputs['members'].values())); member['bootstrap_rules'] = {}
        with self.assertRaises(ValueError): t.bindings(record['scope'], inputs, record['prior_outputs'], 'prepared')
        inputs, record, _ = fixture(stage='prepared')
        next(iter(record['prior_outputs']['members']['value'].values()))['bootstrap_rule_ids'] = {}
        with self.assertRaises(ValueError): t.bindings(record['scope'], inputs, record['prior_outputs'], 'prepared')

    def test_bootstrap_output_must_be_explicit(self):
        inputs, record, _ = fixture('workloads')
        with self.assertRaisesRegex(ValueError, 'lifecycle'): apply.verify_outputs(record['prior_outputs'], {'scope': record['scope']}, inputs)


class TransitionBundleTests(TerraformRunFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.inputs, self.transition, self.plan = fixture()
        self.entry, self.scope, self.state_key = run.select_scope(run.ROOT, 'openstack-wsd-domains', self.inputs)
        self.args.catalog_id = 'openstack-wsd-domains'; self.backend['state_key'] = self.state_key
        self.cloud = {'clouds': {self.inputs['openstack_cloud']: {'auth_type': 'v3applicationcredential',
                       'auth': {'auth_url': 'https://identity.example.test/v3', 'application_credential_id': 'fixture',
                                'application_credential_secret': 'SYNTHETIC'}, 'region_name': 'site-01', 'interface': 'internal', 'verify': True}}}
        self.args.cloud = self.base / 'cloud'; self.args.transition = self.base / 'transition'
        write_new(self.args.cloud, encoded(self.cloud)); write_new(self.args.transition, encoded(self.transition))
        self.authority.update(scope=self.scope, input_sha256=digest(encoded(self.inputs)),
                              backend_sha256=digest(encoded(self.backend)), cloud_sha256=digest(encoded(self.cloud)))
        for key in ('inputs', 'backend', 'authority'): (self.base / key).write_bytes(encoded(getattr(self, key)))

    def engine(self, binary, directory, argv, environment, output, **kwargs):
        if argv[0] == 'show': self.calls.append(argv); write_new(output, encoded(self.plan)); return 0
        return super().engine(binary, directory, argv, environment, output, **kwargs)

    def test_transition_is_sealed_and_rechecked_at_apply(self):
        self.prepare(); operation = self.args.output
        bundle = load_private(operation / 'bundle.json')
        self.assertIn('transition.json', bundle['artifacts'])
        now = utcnow()
        approval = {'format': 'hosting-terraform-approval/1', 'bundle_sha256': digest(read_private(operation / 'bundle.json')),
                    'review_sha256': digest(read_private(operation / 'review.json')), 'operation_id': bundle['operation_id'],
                    'generation': bundle['generation'], 'change_ref': 'FIXTURE-APPROVAL',
                    'valid_from': now.isoformat(), 'valid_until': (now + timedelta(minutes=5)).isoformat()}
        with patch.object(apply, 'verify', return_value={'status': 'HASHES_MATCH', 'commit': self.source}):
            apply.validate_bundle(operation, approval, self.binary)
            (operation / 'transition.json').write_bytes(b'{}')
            with self.assertRaises(ValueError): apply.validate_bundle(operation, approval, self.binary)

    def test_expired_transition_blocks_before_contact(self):
        self.transition['valid_until'] = (utcnow() - timedelta(seconds=1)).isoformat()
        self.args.transition.write_bytes(encoded(self.transition))
        with self.assertRaises(ValueError): self.prepare()
        self.assertFalse(self.calls)
