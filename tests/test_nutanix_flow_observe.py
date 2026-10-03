"""Exact microseg wire snapshots and transport; no enforcement qualification."""
from copy import deepcopy
import json
import unittest
from lab.native_readback_fixture import Fixture
from provisioner.execution import readback_core as c
from provisioner.execution import nutanix_flow_observe as flow
from tests.test_nutanix_vm_observe import uid, Client


def manifest(origin='https://prism.example.invalid'):
    group = {'securedGroupCategoryAssociatedEntityType': 'VM', 'securedGroupCategoryReferences': [uid(6)]}
    app = group | {'$objectType': flow.TYPE + 'ApplicationRuleSpec', 'srcAllowSpec': 'NONE', 'destAllowSpec': 'NONE'}
    rules = [dict(extId=uid(21), type='APPLICATION', spec=deepcopy(app)),
             dict(extId=uid(22), type='INTRA_GROUP', spec=group | {
                 '$objectType': flow.TYPE + 'IntraEntityGroupRuleSpec', 'securedGroupAction': 'DENY'}),
             dict(extId=uid(23), type='APPLICATION', description='dns', spec=app | {
                 'srcCategoryAssociatedEntityType': 'VM', 'destCategoryAssociatedEntityType': 'VM',
                 'isAllProtocolAllowed': False, 'destSubnet': {'value': '192.0.2.130', 'prefixLength': 32},
                 'udpServices': [{'startPort': 53, 'endPort': 53}]})]
    expected = {'extId': uid(20), '$objectType': flow.TYPE + 'NetworkSecurityPolicy', 'tenantId': uid(2),
        'name': 'fixture-only', 'type': 'APPLICATION', 'state': 'ENFORCE', 'scope': 'VPC_LIST',
        'vpcReferences': [uid(30)], 'isHitlogEnabled': True, 'isIpv6TrafficAllowed': False, 'rules': rules}
    return dict(platform='nutanix', profile=flow.PROFILE, origin=origin, operation_id='fixture-snapshot',
        tenant_id='tenant-001', scope_id='WSD01', engineering_record_ref='FIXTURE', target_binding_ref='FIXTURE',
        contact_enabled=False, resources=[dict(kind='policy', ext_id=uid(20), category_id=uid(6), vpc_id=uid(30),
            expected_etag='"fixture-1"', services={'dns': dict(direction='egress', protocol='udp', port=53,
                remote_ipv4='192.0.2.130')}, expected=expected)])


class FlowSnapshots(unittest.TestCase):
    def setUp(self): self.m = manifest(); self.client = Client(self.m)
    def observe(self): return c.observe(self.m, self.client, flow, interval=0)
    def test_match_does_not_prove_enforcement_task_or_activation(self):
        report = self.observe()
        self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
        self.assertFalse(report['may_activate'])
        self.assertFalse(report['history'][-1]['states'][0]['task_completion_observed'])
    def test_offline_snapshot_cannot_claim_task_completion_or_ignore_shape(self):
        states = self.observe()['history'][-1]['states']
        for mutate in (lambda s: s[0].update(task_completion_observed=True),
                       lambda s: s[0].update(progress='PENDING'),
                       lambda s: s[0].update(config_sha256='0'*64),
                       lambda s: s[0]['policy_witness'].update(policy_shape_valid=False)):
            bad = deepcopy(states); mutate(bad)
            with self.assertRaises(c.ObservationError): flow.validate_observation_history(self.m, [], bad)
        self.client.body['data']['networkFunctionReferences'] = [uid(50)]
        states = self.observe()['history'][0]['states']; states[0].update(config_status='MATCH', mismatch_fields=[])
        with self.assertRaises(c.ObservationError): flow.validate_observation_history(self.m, [], states)
    def test_extra_native_selectors_cannot_hide_outside_selected_projection(self):
        mutations = [lambda e: e.update(networkFunctionReferences=[uid(50)]),
            lambda e: e.update(scopeReferences=[uid(50)]), lambda e: e.update(securedGroups=[uid(50)]),
            lambda e: e.update(isIpv6AddressScope=True), lambda e: e['rules'][2]['spec'].update(srcAllowSpec='ALL'),
            lambda e: e['rules'][2]['spec'].update(srcSubnet={'value': '192.0.2.1', 'prefixLength': 32}),
            lambda e: e['rules'][2]['spec'].update(destIpv6Subnet={'value': '2001:db8::1', 'prefixLength': 128}),
            lambda e: e['rules'][2]['spec'].update(serviceGroupReferences=[uid(50)]),
            lambda e: e['rules'][2]['spec']['udpServices'][0].update(endPort=65535),
            lambda e: e['rules'][2].update({'$specItemDiscriminator': flow.TYPE + 'IntraEntityGroupRuleSpec'}),
            lambda e: e['rules'][2]['spec']['udpServices'][0].update({'$objectType': flow.TYPE + 'TcpPortRangeSpec'}),
            lambda e: e['rules'][2]['spec']['destSubnet'].update({'$objectType': 'common.v1.config.IPv6Address'}),
            lambda e: e['rules'][2].update(tenantId=uid(50))]
        for mutate in mutations:
            self.client = Client(self.m); mutate(self.client.body['data'])
            with self.subTest(mutate=mutate): self.assertEqual(self.observe()['outcome'], 'HOLD_DIFFERENCE')
    def test_missing_identity_selector_or_revision_holds_uncertain(self):
        for mutate in (lambda e: e.pop('tenantId'), lambda e: e['rules'][2]['spec'].pop('destSubnet'),
                       lambda e: e.update(isHitlogEnabled=1), lambda e: e['rules'].reverse()):
            self.client = Client(self.m); mutate(self.client.body['data'])
            self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
        self.client = Client(self.m, etag=None)
        self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
        self.client = Client(self.m, etag='"other"')
        self.assertEqual(self.observe()['outcome'], 'HOLD_DIFFERENCE')
    def test_readonly_metadata_is_not_journaled(self):
        self.client.body['data']['description'] = 'PRIVATE-SENTINEL'
        self.client.body['data']['networkFunctionReferences'] = []
        rule = self.client.body['data']['rules'][2]
        rule['$specItemDiscriminator'] = rule['spec']['$objectType']
        rule['spec']['destSubnet']['$reserved'] = {'$fv': 'v1.r0'}
        rule['spec']['udpServices'][0]['$reserved'] = {'$fv': 'v4.r2'}
        report = self.observe()
        self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
        self.assertNotIn('PRIVATE-SENTINEL', json.dumps(report))
    def test_ambiguous_or_widened_expected_intent_rejected_before_contact(self):
        mutations = [lambda m: m.update(task={}), lambda m: m['resources'].append(deepcopy(m['resources'][0])),
            lambda m: m['resources'][0].update(expected_etag='W/"weak"'),
            lambda m: m['resources'][0]['expected'].update(scope='GLOBAL'),
            lambda m: m['resources'][0]['expected']['rules'][2].update(extId=uid(21)),
            lambda m: m['resources'][0]['services']['dns'].update(port=54)]
        for mutate in mutations:
            m = deepcopy(self.m); mutate(m)
            with self.assertRaises(ValueError): flow.targets(m)
    def test_real_tls_get_is_exact_microseg_endpoint(self):
        with Fixture() as fixture:
            m = manifest(fixture.origin); r = m['resources'][0]
            target = '/api/microseg/v4.2/config/policies/' + r['ext_id']
            fixture.routes = {target: {'body': {'data': r['expected']}, 'etag': r['expected_etag']}}
            client = c.ReadClient(fixture.origin, fixture.origin, 'reader', 'fixture-only', flow.targets(m), str(fixture.directory / 'ca.pem'))
            self.assertEqual(c.observe(m, client, flow, interval=0)['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
            self.assertEqual(len(fixture.requests), 2)
            self.assertTrue(all(x['method'] == 'GET' and x['path'] == target for x in fixture.requests))


if __name__ == '__main__': unittest.main()
