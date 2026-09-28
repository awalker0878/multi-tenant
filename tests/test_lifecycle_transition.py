import copy
from datetime import timedelta
import json
import unittest
from uuid import uuid5, NAMESPACE_URL

from tools import lifecycle_transition as t, terraform_run as run
from provisioner.compiler.wsd import STATE
from tools.plan_review import review
from tools.run_files import digest, encoded, utcnow


def nsx_rules(member, group, stage):
    result = []
    for key, rule in sorted(member.get('bootstrap_rules', {}).items()) if stage == 'bootstrap' else []:
        peer = [rule['remote_ipv4'] + '/32']
        result.append(dict(display_name=key, action='ALLOW', direction='IN_OUT', logged=True, disabled=False,
            ip_version='IPV4', services=[], source_groups=peer if rule['direction'] == 'ingress' else [group],
            destination_groups=[group] if rule['direction'] == 'ingress' else peer,
            service_entries=[{'l4_port_set_entry': [{'protocol': rule['protocol'].upper(),
                'destination_ports': [str(rule['port'])], 'source_ports': []}]}]))
    result.append(dict(display_name='deny-scoped-ip-traffic', action='DROP', direction='IN_OUT',
        logged=True, disabled=False, ip_version='IPV4_IPV6', services=[], source_groups=[], destination_groups=[], service_entries=[]))
    return result


def fixture(platform='nutanix', stage='bootstrap'):
    phase = 'workloads' if platform == 'nutanix' else 'domains'
    inputs = json.loads((run.ROOT / f'terraform/stacks/wsd/{platform}/{phase}/inputs.tfvars.json.example').read_text())
    inputs.update(allow_restricted_build=True, test_authorization_ref='FIXTURE-CHANGE')
    previous = copy.deepcopy(inputs)
    _, scope, _ = run.select_scope(run.ROOT, platform + '-wsd-' + phase, inputs)
    outputs = {'scope': {'value': scope}, 'delivery_state': {'value': STATE}, 'members': {'value': {}}}
    for name, member in inputs['members'].items():
        member.update(lifecycle_stage=stage, bootstrap_acceptance_ref='FIXTURE-ACCEPTANCE')
        uid = str(uuid5(NAMESPACE_URL, name))
        outputs['members']['value'][name] = {'delivery_state': STATE, 'vm_id': uid, 'segment_path': '/infra/segments/' + uid,
            'group_path': '/infra/domains/default/groups/' + uid, 'quarantine_policy_path': '/infra/domains/default/security-policies/' + uid}
        if platform == 'vmware':
            member['bootstrap_rules'] = {'dns': {'direction': 'egress', 'protocol': 'udp', 'port': 53, 'remote_ipv4': '10.42.0.53'}}
    now = utcnow()
    record = dict(format=t.FORMAT, scope=scope, input_sha256=digest(encoded(inputs)), prior_bundle_sha256='a' * 64,
        prior_outputs=outputs, prior_inputs=previous, requested_inputs=inputs, target_stage=stage,
        valid_from=(now - timedelta(seconds=1)).isoformat(), valid_until=(now + timedelta(minutes=10)).isoformat(),
        acceptance_refs={k: 'FIXTURE-' + k for k in t.os_transition.REFS})
    record['resources'] = t.bindings(record)
    changes = []
    for address, spec in record['resources'].items():
        member = inputs['members'][spec['member']]; native = outputs['members']['value'][spec['member']]
        kind = spec['type']; after = {spec['identity_field']: spec['id']}
        if platform == 'nutanix':
            after.update(power_state='ON' if stage == 'bootstrap' else 'OFF', disks=[{'id': 'retained-volume', 'size': 40}],
                cluster=[{'ext_id': member['cluster_id']}], project=[{'ext_id': member['project_id']}], categories=[{'ext_id': member['security_category_id']}],
                nics=[{'nic_backing_info': [{'virtual_ethernet_nic': [{'is_connected': stage == 'bootstrap', 'model': 'VIRTIO'}]}],
                    'nic_network_info': [{'virtual_ethernet_nic_network_info': [{'subnet': [{'ext_id': member['subnet_id']}],
                        'ipv4_config': [{'ip_address': [{'value': member['ipv4_address']}]}]}]}]}])
        elif kind == 'nsxt_policy_segment':
            after['advanced_config'] = [{'connectivity': 'ON' if stage == 'bootstrap' else 'OFF', 'urpf_mode': 'STRICT'}]
        else:
            after.update(scope=[native['group_path']], category='Emergency', stateful=True, tcp_strict=True,
                         sequence_number=member['quarantine_sequence'], rule=nsx_rules(member, native['group_path'], stage))
        before = copy.deepcopy(after)
        if platform == 'nutanix':
            before['power_state'] = 'OFF' if stage == 'bootstrap' else 'ON'
            before['nics'][0]['nic_backing_info'][0]['virtual_ethernet_nic'][0]['is_connected'] = stage != 'bootstrap'
        elif kind == 'nsxt_policy_segment': before['advanced_config'][0]['connectivity'] = 'OFF' if stage == 'bootstrap' else 'ON'
        else: before['rule'] = nsx_rules(member, native['group_path'], 'prepared' if stage == 'bootstrap' else 'bootstrap')
        changes.append(dict(address=address, type=kind, mode='managed',
            provider_name='registry.terraform.io/' + ('nutanix/nutanix' if platform == 'nutanix' else 'vmware/nsxt'),
            change=dict(actions=['update'], before=before, after=after, after_unknown={})))
    return record, {'format_version': '1.2', 'complete': True, 'resource_changes': changes}


class LifecycleTests(unittest.TestCase):
    def test_exact_bootstrap_and_withdrawal_both_platforms(self):
        for platform in ('vmware', 'nutanix'):
            for stage in ('bootstrap', 'prepared'):
                with self.subTest(platform=platform, stage=stage):
                    record, plan = fixture(platform, stage)
                    t.validate(record, record['scope'], encoded(record['requested_inputs']))
                    self.assertNotEqual(review(plan, transition=record)['status'], 'BLOCKED')
                    if stage == 'bootstrap': self.assertEqual(review(plan)['status'], 'BLOCKED')

    def test_foreign_id_replacement_omission_unknown_and_unrelated_change_block(self):
        for platform in ('vmware', 'nutanix'):
            for mutation in ('id', 'replace', 'missing', 'unknown', 'unrelated', 'drift'):
                record, plan = fixture(platform); change = plan['resource_changes'][0]['change']
                if mutation == 'id': change['after']['id' if platform == 'nutanix' else 'path'] = 'foreign'
                if mutation == 'replace': change['actions'] = ['delete', 'create']
                if mutation == 'missing': plan['resource_changes'].pop()
                if mutation == 'unknown': change['after_unknown']['nics' if platform == 'nutanix' else 'advanced_config'] = True
                if mutation == 'unrelated': change['after']['arbitrary_mutation'] = True
                if mutation == 'drift': plan['resource_drift'] = [plan['resource_changes'][0]]
                with self.subTest(platform=platform, mutation=mutation): self.assertEqual(review(plan, transition=record)['status'], 'BLOCKED')

    def test_ahv_disk_or_subnet_or_nic_replacement_block(self):
        for mutation in ('disk', 'subnet', 'nic', 'category'):
            record, plan = fixture(); after = plan['resource_changes'][0]['change']['after']
            if mutation == 'disk': after['disks'][0]['id'] = 'replacement'
            if mutation == 'subnet': after['nics'][0]['nic_network_info'][0]['virtual_ethernet_nic_network_info'][0]['subnet'][0]['ext_id'] = 'foreign'
            if mutation == 'nic': after['nics'].append(copy.deepcopy(after['nics'][0]))
            if mutation == 'category': after['categories'] = []
            with self.subTest(mutation=mutation): self.assertEqual(review(plan, transition=record)['status'], 'BLOCKED')

    def test_nsx_widening_reordering_exclusion_and_scope_override_block(self):
        for mutation in ('peer', 'port', 'drop', 'order', 'exclude', 'scope', 'ip', 'unlogged', 'new_selector'):
            record, plan = fixture('vmware'); after = plan['resource_changes'][1]['change']['after']; rule = after['rule'][0]
            if mutation == 'peer': rule['destination_groups'] = ['0.0.0.0/0']
            if mutation == 'port': rule['service_entries'][0]['l4_port_set_entry'][0]['destination_ports'] = ['1-65535']
            if mutation == 'drop': after['rule'].pop()
            if mutation == 'order': after['rule'].reverse()
            if mutation == 'exclude': rule['destinations_excluded'] = True
            if mutation == 'scope': rule['scope'] = ['/infra/domains/default/groups/foreign']
            if mutation == 'ip': rule['ip_version'] = 'IPV4_IPV6'
            if mutation == 'unlogged': rule['logged'] = False
            if mutation == 'new_selector': rule['unreviewed_protocol'] = 'ANY'
            with self.subTest(mutation=mutation): self.assertEqual(review(plan, transition=record)['status'], 'BLOCKED')

    def test_contract_cannot_change_prior_inputs_or_expire(self):
        for mutation in ('allocation', 'scope', 'hash', 'expiry', 'resource'):
            record, _ = fixture()
            if mutation == 'allocation': next(iter(record['requested_inputs']['members'].values()))['vcpu'] = 8
            if mutation == 'scope': record['scope']['tenant_key'] = 'foreign'
            if mutation == 'hash': record['input_sha256'] = 'b' * 64
            if mutation == 'expiry': record['valid_until'] = (utcnow() - timedelta(seconds=1)).isoformat()
            if mutation == 'resource': next(iter(record['resources'].values()))['values']['power_state'] = 'OFF'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): t.validate(record, record['scope'], encoded(record['requested_inputs']))

    def test_rule_computed_ids_allowed_security_unknowns_held(self):
        record, plan = fixture('vmware'); change = plan['resource_changes'][1]['change']
        change['after_unknown']['rule'] = [{'nsx_id': True, 'revision': True, 'rule_id': True}, {'nsx_id': True}]
        self.assertNotEqual(review(plan, transition=record)['status'], 'BLOCKED')
        change['after_unknown']['rule'][0]['destination_groups'] = True
        self.assertEqual(review(plan, transition=record)['status'], 'BLOCKED')

    def test_nsx_pinned_provider_empty_service_fields_are_accepted_but_other_protocols_block(self):
        record, plan = fixture('vmware'); change = plan['resource_changes'][1]['change']
        for index, rule in enumerate(change['after']['rule']):
            rule.update(nsx_id=None, path=None, revision=None, rule_id=None, sequence_number=None,
                        description='', notes='', log_label='', tag=[], scope=[], profiles=[],
                        sources_excluded=False, destinations_excluded=False)
            if rule['service_entries']:
                entry = rule['service_entries'][0]
                entry.update({key: [] for key in ('icmp_entry', 'igmp_entry', 'ether_type_entry', 'ip_protocol_entry', 'algorithm_entry')})
                entry['l4_port_set_entry'][0].update(display_name='', description='')
        change['after_unknown']['rule'] = [{key: True for key in t.RULE_METADATA} for _ in change['after']['rule']]
        self.assertNotEqual(review(plan, transition=record)['status'], 'BLOCKED')
        change['after']['rule'][0]['service_entries'][0]['algorithm_entry'] = [{'algorithm': 'FTP'}]
        self.assertEqual(review(plan, transition=record)['status'], 'BLOCKED')

    def test_nsx_explicit_sequence_must_preserve_reviewed_order(self):
        for sequence, blocked in (([0, 0], False), ([10, 20], False), ([20, 10], True),
                                  ([10, 10], True), ([True, 20], True), ([-1, 20], True)):
            record, plan = fixture('vmware'); rules = plan['resource_changes'][1]['change']['after']['rule']
            for rule, number in zip(rules, sequence): rule['sequence_number'] = number
            with self.subTest(sequence=sequence):
                self.assertEqual(review(plan, transition=record)['status'] == 'BLOCKED', blocked)


if __name__ == '__main__': unittest.main()
