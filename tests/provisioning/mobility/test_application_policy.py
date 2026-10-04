"""Native conditional policy composition over real TLS; synthetic B10 ports.

Exact rules, one retained port, independent project reads and effect journaling
are verified. These tests provide no native datapath or site acceptance.
"""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from provisioner.controlplane.persistence import canonical_record_digest
from provisioner.migration.application_network import management_snapshot
from provisioner.migration.bootstrap_selection import validate_policy_selection
from provisioner.migration.lifecycle import ApplicationLifecycleSelection
from provisioner.migration.native_openstack import OpenStackApplicationClient
from provisioner.execution.run_files import encoded
from tests.provisioning.mobility import test_application_network as network
from tests.provisioning.mobility.test_application_openstack_native import PROJECT, REQUEST, SERVER

GROUP = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
RULE = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'


def policy_record(port=8080, project=PROJECT):
    rule = deepcopy(network.management_record(project=project)['security_group_rules'][0])
    rule.update(id=RULE, security_group_id=GROUP, port_range_min=port, port_range_max=port,
                remote_ip_prefix='192.0.2.30/32')
    return dict(security_group_id=GROUP, security_group_rules=[rule])


class ProductionPolicyWireTests(unittest.TestCase):
    def setUp(self):
        self.wire = network.ManagementWireTests(); self.wire.setUp()
        self.addCleanup(self.wire.doCleanups)
        wire = self.wire
        wire.port.update(admin_state_up=True, status='ACTIVE')
        wire.interfaces[0]['port_state'] = 'ACTIVE'
        wire.fixture.guard.phase, wire.fixture.guard.operation_kind = 'TARGET_POLICY', 'POLICY_APPLY'
        wire.fixture.guard.member['target'] = dict(health=dict(port=8080))
        self.policy = policy_record()
        wire.fixture.guard.member['target_policy'] = self.policy
        self.group = dict(id=GROUP, project_id=PROJECT, stateful=True,
                          security_group_rules=deepcopy(self.policy['security_group_rules']))
        wire.fixture.native.routes[('GET', '/v2.0/security-groups/' + GROUP)] = \
            lambda _: dict(body=dict(security_group=deepcopy(self.group)))
        wire.fixture.native.routes[('PUT', '/v2.0/ports/' + network.PORT)] = self.update
        self.client = OpenStackApplicationClient(wire.fixture.runtime, wire.fixture.guard, wire.fixture.authority)

    def update(self, request):
        wire = self.wire
        enable = wire.fixture.guard.phase == 'TARGET_POLICY'
        groups = [network.GROUP] + ([GROUP] if enable else [])
        self.assertEqual(request['body'], encoded({'port': {'security_groups': groups}}))
        self.assertEqual(request['headers']['If-Match'], 'revision_number=' + str(wire.port['revision_number']))
        wire.port.update(security_groups=groups, revision_number=wire.port['revision_number'] + 1)
        return dict(body={'port': deepcopy(wire.port)}, headers=[('X-OpenStack-Request-Id', REQUEST)])

    def snapshot(self, enabled=False):
        wire = self.wire
        return management_snapshot(lambda service, path: self.client.request(service, 'GET', '/' + path)[0],
            wire.selected, wire.fixture.scope, SERVER, enabled=True, policy=self.policy,
            policy_enabled=enabled, health_port=wire.fixture.guard.member['target']['health']['port'])

    def independent_runtime(self):
        wire = self.wire
        runtime, artifact, admitted, lifecycle, handover = wire.independent_runtime()
        body = lifecycle.to_dict(); member = body['members'][0]
        self.policy = policy_record(member['target']['health']['port'])
        self.group['security_group_rules'] = deepcopy(self.policy['security_group_rules'])
        member['target_policy'] = self.policy
        for phase in ('TARGET_POLICY', 'TARGET_ISOLATE'):
            member['phases'][phase] = dict(step_id=phase.lower(), operation_id=phase.lower() + '-operation',
                                         scope_side='destination', operation_kind='POLICY_APPLY')
        lifecycle = ApplicationLifecycleSelection.from_record(body)
        artifact['applicationLifecycleSelectionDigest'] = lifecycle.sha256
        digest = canonical_record_digest(artifact)
        object.__setattr__(runtime.enrollment, 'selection_digest', digest)
        runtime.guest_reader.enrollment.selection_digest = digest
        wire.fixture.guard.lifecycle = lifecycle; wire.fixture.guard.member = lifecycle.member('machine-1')
        wire.fixture.guard.phase, wire.fixture.guard.operation_kind = 'TARGET_POLICY', 'POLICY_APPLY'
        wire.fixture.guard.selection_bytes = encoded(artifact)
        self.client = OpenStackApplicationClient(wire.fixture.runtime, wire.fixture.guard, wire.fixture.authority)
        return runtime, artifact, admitted, lifecycle, handover

    def test_conditional_policy_attachment_and_separate_isolation_use_one_exact_port(self):
        wire = self.wire
        request_id, _ = self.client.set_production_policy(self.snapshot(), enable=True)
        self.assertEqual(request_id, REQUEST)
        self.assertTrue(self.snapshot(True)['production_policy_enabled'])
        wire.fixture.guard.phase = 'TARGET_ISOLATE'
        self.client.set_production_policy(self.snapshot(True), enable=False)
        self.assertFalse(self.snapshot()['production_policy_enabled'])
        self.assertEqual(wire.port['security_groups'], [network.GROUP])
        writes = [row for row in wire.fixture.native.requests if row['method'] == 'PUT']
        self.assertEqual(len(writes), 2)
        self.assertEqual([row['path'] for row in writes], ['/v2.0/ports/' + network.PORT] * 2)
        self.assertFalse(any(row['method'] in {'DELETE', 'PATCH'} for row in wire.fixture.native.requests))
        wire.fixture.registry.task_accepted.assert_not_called()

    def test_broad_additive_foreign_or_changed_native_policy_holds_before_write(self):
        for change in (
            lambda: self.group['security_group_rules'][0].update(remote_ip_prefix='0.0.0.0/0'),
            lambda: self.group['security_group_rules'].append(deepcopy(self.group['security_group_rules'][0])),
            lambda: self.group.update(project_id=SERVER),
            lambda: self.group.update(stateful=False),
            lambda: self.wire.port.update(security_groups=[network.GROUP, GROUP]),
        ):
            group, port = deepcopy(self.group), deepcopy(self.wire.port); change()
            with self.assertRaises(ValueError): self.snapshot()
            self.group.clear(); self.group.update(group); self.wire.port.clear(); self.wire.port.update(port)
        self.assertFalse(any(row['method'] == 'PUT' for row in self.wire.fixture.native.requests))

    def test_native_revision_conflict_is_not_retried(self):
        self.wire.fixture.native.routes[('PUT', '/v2.0/ports/' + network.PORT)] = dict(status=412, body={})
        with self.assertRaises(ValueError): self.client.set_production_policy(self.snapshot(), enable=True)
        self.assertEqual(sum(row['method'] == 'PUT' for row in self.wire.fixture.native.requests), 1)

    def test_network_or_policy_grants_cannot_borrow_power_storage_or_foreign_port_writes(self):
        before = self.snapshot()
        for kind in ('NETWORK_ATTACH', 'VM_POWER', 'DISK_ATTACH', 'SOURCE_FENCE', 'DISCOVER_READ'):
            self.wire.fixture.guard.operation_kind = kind
            with self.assertRaises(ValueError): self.client.set_production_policy(before, enable=True)
        self.wire.fixture.guard.operation_kind = 'POLICY_APPLY'
        with self.assertRaises(ValueError): self.client.request('compute', 'POST', '/servers/' + SERVER + '/action', {})
        with self.assertRaises(ValueError): self.client.request('network', 'PUT', '/ports/' + SERVER,
            {'port': {'security_groups': [network.GROUP, GROUP]}}, revision=7)
        self.assertFalse(any(row['method'] == 'PUT' for row in self.wire.fixture.native.requests))

    def test_independent_reader_observes_exact_policy_before_receipt_without_datapath_claim(self):
        runtime, _, _, _, handover = self.independent_runtime()
        log = SimpleNamespace(append=Mock())
        with patch.object(type(self.wire.fixture.runtime), 'client', return_value=self.client):
            result = runtime.execute_policy(self.wire.fixture.authority, handover, log,
                                            self.wire.fixture.runtime, enable=True)
        self.assertEqual(result['status'], 'TARGET_PRODUCTION_POLICY_INDEPENDENTLY_OBSERVED')
        self.assertEqual(result['native_request_id'], REQUEST)
        self.assertFalse(result['native_datapath_qualification'])
        runtime.guest_reader.observe_bootstrap.assert_called_once()
        self.assertIn(('TARGET_POLICY_CHANGE_RETURNED', {'native_request_id': REQUEST}),
            [call.args for call in log.append.call_args_list])
        contacts = [row for row in self.wire.fixture.native.requests
                    if row['headers'].get('X-Auth-Token') == 'independent-native-app-token']
        self.assertTrue(contacts and all(row['method'] == 'GET' for row in contacts))

    def test_malformed_accepted_reply_retains_request_identity_before_hold(self):
        runtime, _, _, _, handover = self.independent_runtime()
        def malformed(request):
            result = self.update(request); result['body']['port']['id'] = SERVER
            return result
        self.wire.fixture.native.routes[('PUT', '/v2.0/ports/' + network.PORT)] = malformed
        log = SimpleNamespace(append=Mock())
        with patch.object(type(self.wire.fixture.runtime), 'client', return_value=self.client):
            with self.assertRaises(ValueError): runtime.execute_policy(self.wire.fixture.authority, handover, log,
                self.wire.fixture.runtime, enable=True)
        self.assertIn(('TARGET_POLICY_CHANGE_RETURNED', {'native_request_id': REQUEST}),
            [call.args for call in log.append.call_args_list])
        self.assertEqual(sum(row['method'] == 'PUT' for row in self.wire.fixture.native.requests), 1)

    def test_late_genuine_policy_reply_is_retained_before_revocation_blocks_followup_reads(self):
        runtime, _, _, _, handover = self.independent_runtime()
        def late(request):
            result = self.update(request)
            result['before_response'] = lambda: setattr(self.wire.fixture, 'revoked', True)
            return result
        self.wire.fixture.native.routes[('PUT', '/v2.0/ports/' + network.PORT)] = late
        log = SimpleNamespace(append=Mock())
        with patch.object(type(self.wire.fixture.runtime), 'client', return_value=self.client):
            with self.assertRaises(PermissionError): runtime.execute_policy(self.wire.fixture.authority, handover, log,
                self.wire.fixture.runtime, enable=True)
        self.assertIn(('TARGET_POLICY_CHANGE_RETURNED', {'native_request_id': REQUEST}),
            [call.args for call in log.append.call_args_list])
        self.assertEqual(self.wire.fixture.native.requests[-1]['method'], 'PUT')

    def test_native_policy_tamper_after_update_holds_with_original_identity_retained(self):
        runtime, _, _, _, handover = self.independent_runtime()
        def changed(request):
            result = self.update(request)
            self.group['security_group_rules'][0]['remote_ip_prefix'] = '0.0.0.0/0'
            return result
        self.wire.fixture.native.routes[('PUT', '/v2.0/ports/' + network.PORT)] = changed
        log = SimpleNamespace(append=Mock())
        with patch.object(type(self.wire.fixture.runtime), 'client', return_value=self.client):
            with self.assertRaises(ValueError): runtime.execute_policy(self.wire.fixture.authority, handover, log,
                self.wire.fixture.runtime, enable=True)
        self.assertIn(('TARGET_POLICY_CHANGE_RETURNED', {'native_request_id': REQUEST}),
            [call.args for call in log.append.call_args_list])
        self.assertEqual(sum(row['method'] == 'PUT' for row in self.wire.fixture.native.requests), 1)

    def test_bootstrap_with_selected_unattached_production_group_precedes_conditional_policy_admission(self):
        runtime, _, _, _, handover = self.independent_runtime()
        wire = self.wire
        wire.fixture.guard.phase, wire.fixture.guard.operation_kind = 'TARGET_BOOTSTRAP', 'NETWORK_ATTACH'
        wire.port.update(admin_state_up=False, status='DOWN'); wire.interfaces[0]['port_state'] = 'DOWN'
        wire.fixture.native.routes[('PUT', '/v2.0/ports/' + network.PORT)] = wire.enable
        self.client = OpenStackApplicationClient(wire.fixture.runtime, wire.fixture.guard, wire.fixture.authority)
        with patch.object(type(wire.fixture.runtime), 'client', return_value=self.client):
            bootstrap = runtime.execute(wire.fixture.authority, handover, SimpleNamespace(append=Mock()))
        self.assertFalse(bootstrap['current_management']['native_snapshot']['production_policy_enabled'])
        wire.fixture.guard.phase, wire.fixture.guard.operation_kind = 'TARGET_POLICY', 'POLICY_APPLY'
        wire.fixture.native.routes[('PUT', '/v2.0/ports/' + network.PORT)] = self.update
        self.client = OpenStackApplicationClient(wire.fixture.runtime, wire.fixture.guard, wire.fixture.authority)
        with patch.object(type(wire.fixture.runtime), 'client', return_value=self.client):
            production = runtime.execute_policy(wire.fixture.authority, handover, SimpleNamespace(append=Mock()),
                                                wire.fixture.runtime, enable=True)
        self.assertTrue(production['current_management']['native_snapshot']['production_policy_enabled'])
        self.assertEqual(sum(row['method'] == 'PUT' for row in wire.fixture.native.requests), 2)

    def test_already_isolated_port_is_currently_observed_without_sending_another_change(self):
        runtime, _, _, _, handover = self.independent_runtime()
        self.wire.fixture.guard.phase = 'TARGET_ISOLATE'
        with patch.object(type(self.wire.fixture.runtime), 'client', return_value=self.client):
            result = runtime.execute_policy(self.wire.fixture.authority, handover, SimpleNamespace(append=Mock()),
                self.wire.fixture.runtime, enable=False)
        self.assertEqual(result['status'], 'TARGET_POLICY_ALREADY_ISOLATED')
        self.assertIsNone(result['native_request_id'])
        runtime.guest_reader.observe_bootstrap.assert_not_called()
        self.assertFalse(any(row['method'] == 'PUT' for row in self.wire.fixture.native.requests))

    def test_stopped_retained_target_allows_policy_read_but_never_claims_booted_guest(self):
        wire = self.wire
        wire.fixture.native.routes[('GET', '/v2.1/servers/' + SERVER)] = dict(body=dict(server={
            'id': SERVER, 'tenant_id': PROJECT, 'status': 'SHUTOFF',
            'OS-EXT-STS:power_state': 4, 'OS-EXT-STS:task_state': None}))
        wire.port['status'] = 'DOWN'; wire.interfaces[0]['port_state'] = 'DOWN'
        get = lambda service, path: self.client.request(service, 'GET', '/' + path)[0]
        with self.assertRaises(ValueError):
            management_snapshot(get, wire.selected, wire.fixture.scope, SERVER, enabled=True,
                policy=self.policy, health_port=8080)
        result = management_snapshot(get, wire.selected, wire.fixture.scope, SERVER, enabled=True,
            policy=self.policy, health_port=8080, require_booted=False)
        self.assertEqual(result['server']['status'], 'SHUTOFF')
        self.assertFalse(result['production_policy_enabled'])
        self.assertFalse(any(row['method'] != 'GET' and row['path'].startswith('/v2.')
            for row in wire.fixture.native.requests))


class ProductionSelectionTests(unittest.TestCase):
    def test_admission_rejects_broad_hosts_extra_listeners_management_reuse_or_foreign_scope(self):
        original = policy_record(); management = network.management_record(); scope = SimpleNamespace(native_scope_id=PROJECT)
        validate_policy_selection(original, scope, management, 8080)
        for port in (True, '8080', 22, 65536):
            with self.assertRaises(ValueError): validate_policy_selection(original, scope, management, port)
        for change in (
            lambda value: value.update(security_group_id=network.GROUP),
            lambda value: value['security_group_rules'][0].update(remote_ip_prefix='0.0.0.0/0'),
            lambda value: value['security_group_rules'][0].update(port_range_min=22, port_range_max=22),
            lambda value: value['security_group_rules'][0].update(project_id=SERVER),
            lambda value: value['security_group_rules'].append(deepcopy(value['security_group_rules'][0])),
        ):
            selected = deepcopy(original); change(selected)
            with self.assertRaises(ValueError): validate_policy_selection(selected, scope, management, 8080)
