"""Real Keystone/Nova/Neutron TLS and conditional effects; synthetic B10 ports.

These are protocol and isolation-boundary tests, not native site acceptance.
Guest reachability in the composition test is an explicitly synthetic reader.
"""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from provisioner.execution.run_files import digest, encoded
from provisioner.migration.application_network import (
    OpenStackBootstrapRuntime, management_snapshot, require_staged_management)
from provisioner.migration.bootstrap_selection import validate_management_selection
from provisioner.migration.lifecycle import ApplicationLifecycleSelection
from provisioner.migration.native_openstack import OpenStackApplicationClient
from provisioner.migration.staging import ApplicationStagedHandover
from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.controlplane.persistence import canonical_record_digest
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from tests.test_application_lifecycle import lifecycle_record
from tests.provisioning.mobility import test_application_openstack_native as wire_fixture
from tests.provisioning.mobility.test_application_openstack_native import PROJECT, REQUEST, SERVER, VOLUME

PORT = '55555555-5555-4555-8555-555555555555'
NETWORK = '66666666-6666-4666-8666-666666666666'
SUBNET = '77777777-7777-4777-8777-777777777777'
GROUP = '88888888-8888-4888-8888-888888888888'
RULE = '99999999-9999-4999-8999-999999999999'


def management_record(origin='https://network.example.invalid', project=PROJECT):
    return dict(network_endpoint=origin + '/v2.0', port_id=PORT, network_id=NETWORK, subnet_id=SUBNET,
        ipv4_address='192.0.2.10', mac_address='fa:16:3e:00:00:01', security_group_id=GROUP,
        worker_ipv4_address='192.0.2.20', ssh_host_key_sha256=digest(b'selected-host-key'), mtu=1500,
        subnet=dict(cidr='192.0.2.0/24', gateway_ip=None, enable_dhcp=False, dns_nameservers=[], host_routes=[]),
        security_group_rules=[dict(id=RULE, project_id=project, security_group_id=GROUP, direction='ingress',
            ethertype='IPv4', protocol='tcp', port_range_min=22, port_range_max=22,
            remote_ip_prefix='192.0.2.20/32', remote_group_id=None, remote_address_group_id=None)])


class ManagementWireTests(unittest.TestCase):
    def setUp(self):
        self.fixture = wire_fixture.NativeApplicationWireTests('test_target_prepare_does_not_register_request_id_as_a_native_task')
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        self.selected = management_record(f.native.origin)
        f.guard.member['target_management'] = self.selected
        f.guard.phase, f.guard.operation_kind = 'TARGET_BOOTSTRAP', 'NETWORK_ATTACH'
        f.server.update(status='ACTIVE', **{'OS-EXT-STS:power_state': 1})
        f.token['token']['catalog'].append(dict(type='network', endpoints=[dict(
            url=self.selected['network_endpoint'], region_id='RegionOne', interface='internal')]))
        self.client = OpenStackApplicationClient(f.runtime, f.guard, f.authority)
        self.port = dict(id=PORT, project_id=PROJECT, network_id=NETWORK, device_id=SERVER,
            device_owner='compute:nova', mac_address=self.selected['mac_address'], admin_state_up=False,
            port_security_enabled=True, security_groups=[GROUP],
            fixed_ips=[dict(subnet_id=SUBNET, ip_address=self.selected['ipv4_address'])],
            allowed_address_pairs=[], status='DOWN', revision_number=7,
            **{'binding:vnic_type': 'normal', 'binding:profile': {}, 'binding:vif_type': 'ovs',
               'binding:vif_details': {'port_filter': True}})
        self.interfaces = [dict(port_id=PORT, net_id=NETWORK, mac_addr=self.selected['mac_address'],
                                fixed_ips=deepcopy(self.port['fixed_ips']), port_state='DOWN')]
        self.network = dict(id=NETWORK, project_id=PROJECT, admin_state_up=True, shared=False,
            port_security_enabled=True, subnets=[SUBNET], mtu=1500, **{'router:external': False})
        self.subnet = dict(id=SUBNET, project_id=PROJECT, network_id=NETWORK, ip_version=4, **self.selected['subnet'])
        self.group = dict(id=GROUP, project_id=PROJECT, stateful=True,
                          security_group_rules=deepcopy(self.selected['security_group_rules']))
        routes = {('compute', '/v2.1/servers/' + SERVER): ('server', f.server),
            ('compute', '/v2.1/servers/' + SERVER + '/os-interface'): ('interfaceAttachments', self.interfaces),
            ('network', '/v2.0/ports/' + PORT): ('port', self.port),
            ('network', '/v2.0/networks/' + NETWORK): ('network', self.network),
            ('network', '/v2.0/subnets/' + SUBNET): ('subnet', self.subnet),
            ('network', '/v2.0/security-groups/' + GROUP): ('security_group', self.group)}
        for (service, path), (key, body) in routes.items():
            def read(request, key=key, body=body, service=service):
                return dict(body={key: deepcopy(body)}, headers=[] if service == 'network' else
                            [('OpenStack-API-Version', request['headers']['OpenStack-API-Version'])])
            f.native.routes[('GET', path)] = read
        f.native.routes[('GET', '/v2.0/extensions/revision-if-match')] = dict(
            body={'extension': {'alias': 'revision-if-match'}})
        f.native.routes[('PUT', '/v2.0/ports/' + PORT)] = self.enable

    def snapshot(self, enabled=False):
        return management_snapshot(lambda service, path: self.client.request(service, 'GET', '/' + path)[0],
                                   self.selected, self.fixture.scope, SERVER, enabled=enabled)

    def enable(self, request):
        self.assertEqual(request['body'], encoded({'port': {'admin_state_up': True}}))
        self.assertEqual(request['headers']['If-Match'], 'revision_number=7')
        self.port.update(admin_state_up=True, status='ACTIVE', revision_number=8)
        self.interfaces[0]['port_state'] = 'ACTIVE'
        return dict(body={'port': deepcopy(self.port)}, headers=[('X-OpenStack-Request-Id', REQUEST)])

    def test_one_exact_conditional_port_enablement_preserves_policy_and_uses_fresh_native_credentials(self):
        before = self.snapshot()
        self.assertEqual(self.client.enable_management(before), REQUEST)
        after = self.snapshot(True)
        self.assertTrue(after['port']['admin_state_up'])
        writes = [row for row in self.fixture.native.requests if row['method'] == 'PUT']
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0]['path'], '/v2.0/ports/' + PORT)
        native = [row for row in self.fixture.native.requests if row['path'] != '/v3/auth/tokens']
        self.assertEqual(self.fixture.runtime.broker.acquire.call_count, len(native))
        self.fixture.registry.task_accepted.assert_not_called()

    def test_added_policy_address_pairs_extra_nic_or_bypass_blocks_before_port_write(self):
        changes = [lambda: self.group['security_group_rules'].append(deepcopy(self.group['security_group_rules'][0])),
            lambda: self.port.update(allowed_address_pairs=[{'ip_address': '0.0.0.0/0'}]),
            lambda: self.interfaces.append(deepcopy(self.interfaces[0])),
            lambda: self.port.update(**{'binding:vnic_type': 'direct'}),
            lambda: self.port['binding:vif_details'].update(port_filter=False),
            lambda: self.network.update(shared=True), lambda: self.network.update(**{'router:external': True}),
            lambda: self.subnet.update(project_id=SERVER), lambda: self.port.pop('revision_number')]
        for change in changes:
            with self.subTest(change=change):
                objects = [deepcopy(obj) for obj in (self.port, self.network, self.subnet, self.group)]
                interfaces = deepcopy(self.interfaces)
                change()
                with self.assertRaises((ValueError, KeyError)): self.snapshot()
                self.assertFalse(any(row['method'] == 'PUT' for row in self.fixture.native.requests))
                for obj, original in zip((self.port, self.network, self.subnet, self.group), objects):
                    obj.clear(); obj.update(original)
                self.interfaces[:] = interfaces

    def test_policy_drift_between_initial_read_and_effect_cannot_enable_the_port(self):
        before = self.snapshot()
        self.port['security_groups'] = [VOLUME]
        with self.assertRaises(ValueError): self.client.enable_management(before)
        self.assertFalse(any(row['method'] == 'PUT' for row in self.fixture.native.requests))

    def test_revision_conflict_is_original_uncertainty_without_a_retry(self):
        self.fixture.native.routes[('PUT', '/v2.0/ports/' + PORT)] = dict(status=412, body={'error': 'changed'})
        with self.assertRaises(ValueError): self.client.enable_management(self.snapshot())
        self.assertEqual(sum(row['method'] == 'PUT' for row in self.fixture.native.requests), 1)

    def test_genuine_late_port_reply_is_retained_before_revocation_stops_readback(self):
        def late(request):
            spec = self.enable(request)
            spec['before_response'] = lambda: setattr(self.fixture, 'revoked', True)
            return spec
        self.fixture.native.routes[('PUT', '/v2.0/ports/' + PORT)] = late
        self.assertEqual(self.client.enable_management(self.snapshot()), REQUEST)
        count = len(self.fixture.native.requests)
        with self.assertRaises(PermissionError): self.snapshot(True)
        self.assertEqual(len(self.fixture.native.requests), count)

    def test_unreadable_original_enablement_reply_retains_request_before_any_current_read(self):
        from provisioner.migration.native_openstack import NativeAcceptedReplyUnreadable
        runtime, _, _, _, handover = self.independent_runtime()
        raw = b'{"port":'
        def unreadable(request):
            spec = self.enable(request); spec['raw'] = raw
            return spec
        self.fixture.native.routes[('PUT', '/v2.0/ports/' + PORT)] = unreadable
        log = SimpleNamespace(append=Mock())
        with patch.object(type(self.fixture.runtime), 'client', return_value=self.client):
            with self.assertRaises(NativeAcceptedReplyUnreadable): runtime.execute(self.fixture.authority, handover, log)
        self.assertEqual(log.append.call_args.args, ('NATIVE_ACCEPTED_REPLY_UNREADABLE',
            {'native_request_id': REQUEST, 'response_sha256': digest(raw)}))
        self.assertEqual(self.fixture.native.requests[-1]['method'], 'PUT')
        self.assertEqual(sum(row['method'] == 'PUT' for row in self.fixture.native.requests), 1)

    def test_power_disk_or_policy_capability_cannot_enable_a_management_port(self):
        before = self.snapshot()
        for kind in ('VM_POWER', 'DISK_ATTACH', 'POLICY_APPLY', 'SOURCE_FENCE', 'DISCOVER_READ'):
            self.fixture.guard.operation_kind = kind
            with self.assertRaises(ValueError): self.client.enable_management(before)
        self.assertFalse(any(row['method'] == 'PUT' for row in self.fixture.native.requests))

    def independent_runtime(self):
        """Real native reader; B10/mTLS custody and SSH are explicit test ports."""
        from tempfile import TemporaryDirectory
        temporary = TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        body = lifecycle_record(temporary.name)
        body['destination_scope'].update(organizationId='org-01', tenantId='tenant-01', locationId='site-01',
            securityDomainId='wsd-01', endpointId='openstack-01', nativeScopeId=PROJECT)
        member = body['members'][0]
        member['target_management'] = deepcopy(self.selected)
        member['target_native_fence'].update({key: value for key, value in self.fixture.selected.items()
                                              if key != 'previous_owner'})
        member['phases']['TARGET_BOOTSTRAP'] = dict(step_id='bootstrap-step', operation_id='bootstrap-operation',
                                                   scope_side='destination', operation_kind='NETWORK_ATTACH')
        lifecycle = ApplicationLifecycleSelection.from_record(body)
        artifact = {'applicationLifecycleSelectionDigest': lifecycle.sha256}
        admitted = AdmittedInput('job-01', 'org-01', 'tenant-01', 'plan-01', 1, 'a' * 64, 0, 'b' * 64)
        enrollment = object.__new__(NativeReadEnrollment)
        read_grant = SimpleNamespace(grant_id='independent-native-read-grant', operation_id='native-read-operation',
                                     operation_scope=self.fixture.scope)
        for key, value in dict(command=SimpleNamespace(grant=read_grant,
                identity=SimpleNamespace(subject='independent-native-reader')), admitted=admitted,
                selection_digest=canonical_record_digest(artifact), broker=None, consumer=None).items():
            object.__setattr__(enrollment, key, value)
        def acquire(*_, **__):
            data, deadline, _ = self.fixture.material()
            data['cloud']['clouds']['target']['auth']['application_credential_id'] = 'independent-native-app'
            return SimpleNamespace(data=data, expires_at=deadline)
        patcher = patch.object(NativeReadEnrollment, 'acquire', side_effect=acquire)
        patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.object(NativeReadEnrollment, 'require_current', return_value=(read_grant, self.fixture.deadline))
        patcher.start(); self.addCleanup(patcher.stop)
        def token(request):
            from provisioner.execution.neutron_observe import strict_loads
            selected = deepcopy(self.fixture.token)
            identity = strict_loads(request['body'])['auth']['identity']['application_credential']['id']
            if identity == 'independent-native-app':
                selected['token']['roles'] = [{'name': 'reader'}]
                selected['token']['application_credential']['id'] = identity
            return dict(status=201, body=selected, headers=[('X-Subject-Token', identity + '-token')])
        self.fixture.native.routes[('POST', '/v3/auth/tokens')] = token
        runtime = object.__new__(OpenStackBootstrapRuntime)
        guest_reader = SimpleNamespace(enrollment=SimpleNamespace(admitted=admitted,
            selection_digest=enrollment.selection_digest), observe_bootstrap=Mock(return_value={'synthetic_ssh': True}))
        for key, value in dict(native=self.fixture.runtime, enrollment=enrollment, guest_reader=guest_reader).items():
            object.__setattr__(runtime, key, value)
        self.fixture.guard.lifecycle = lifecycle; self.fixture.guard.member_id = 'machine-1'
        self.fixture.guard.selection_bytes = encoded(artifact); self.fixture.guard.admitted = admitted
        self.fixture.guest.worker = SimpleNamespace()
        self.fixture.guard.runtime = self.fixture.guest.worker
        target_scope = body['destination_scope']
        def binding(kind, identity):
            return {key: target_scope[key] for key in ('platformFamily', 'endpointId', 'nativeScopeId')} | {
                'resourceKind': kind, 'nativeId': identity}
        source = {'platformFamily': 'vmware', 'endpointId': 'vcenter-01', 'nativeScopeId': 'datacenter-01',
                  'resourceKind': 'vm', 'nativeId': 'vm-1'}
        handover = ApplicationStagedHandover.from_record(dict(format='hosting-application-staged-handover/1',
            originalAdmitted=dict(job_id='creation-job', organization_id='org-01', tenant_id='tenant-01',
                plan_id='creation-plan', plan_revision=1, plan_digest='a' * 64, revocation_epoch=0, payload_digest='b' * 64),
            originalArtifactDigest='c' * 64, originalResourceBundleDigest='d' * 64,
            creationOperationId='creation-operation', creationObservationDigest='e' * 64,
            stagedWorkloadRevision=2, stagedWorkloadDigest='f' * 64, targetSnapshotId='target-snapshot',
            targetSnapshotDigest='a' * 64, destinationScope=target_scope, restoredDatasetReceipts=[],
            associations=[dict(machineId='machine-1', sourceBinding=source, targetBinding=binding('vm', SERVER),
                disks=[dict(diskId='disk-1', sourceBinding=source, targetBinding=binding('disk', VOLUME))],
                nics=[dict(nicId='nic-1', sourceBinding=source, targetBinding=binding('nic', PORT))])]))
        return runtime, artifact, admitted, lifecycle, handover

    def test_independent_project_reader_confirms_policy_before_synthetic_pinned_guest_reader(self):
        runtime, artifact, admitted, lifecycle, handover = self.independent_runtime()
        log = SimpleNamespace(append=Mock())
        with patch.object(type(self.fixture.runtime), 'client', return_value=self.client):
            result = runtime.execute(self.fixture.authority, handover, log)
        self.assertTrue(result['isolated_management_reachability_verified'])
        self.assertFalse(result['native_datapath_qualification'])
        self.assertEqual(result['native_request_id'], REQUEST)
        self.assertEqual(result['current_management']['reader_subject'], 'independent-native-reader')
        runtime.guest_reader.observe_bootstrap.assert_called_once_with(admitted, artifact, lifecycle, 'machine-1')
        self.assertIn(('MANAGEMENT_PORT_ENABLE_RETURNED', {'native_request_id': REQUEST}),
                      [call.args for call in log.append.call_args_list])
        reader_contacts = [row for row in self.fixture.native.requests
                           if row['headers'].get('X-Auth-Token') == 'independent-native-app-token']
        self.assertTrue(reader_contacts and all(row['method'] == 'GET' for row in reader_contacts))

    def test_independent_policy_tamper_after_native_enablement_prevents_guest_contact(self):
        runtime, _, _, _, handover = self.independent_runtime()
        def enable_and_tamper(request):
            result = self.enable(request)
            self.group['security_group_rules'][0]['remote_ip_prefix'] = '0.0.0.0/0'
            return result
        self.fixture.native.routes[('PUT', '/v2.0/ports/' + PORT)] = enable_and_tamper
        log = SimpleNamespace(append=Mock())
        with patch.object(type(self.fixture.runtime), 'client', return_value=self.client):
            with self.assertRaises(ValueError): runtime.execute(self.fixture.authority, handover, log)
        runtime.guest_reader.observe_bootstrap.assert_not_called()
        self.assertIn(('MANAGEMENT_PORT_ENABLE_RETURNED', {'native_request_id': REQUEST}),
                      [call.args for call in log.append.call_args_list])

    def test_foreign_staged_port_cannot_be_enabled_even_if_the_native_uuid_exists(self):
        runtime, _, _, lifecycle, handover = self.independent_runtime()
        body = handover.to_dict(); body['associations'][0]['nics'][0]['targetBinding']['nativeId'] = VOLUME
        changed = ApplicationStagedHandover.from_record(body)
        with self.assertRaises(ValueError): require_staged_management(changed, lifecycle, 'machine-1')
        self.assertEqual(self.fixture.native.requests, [])


class ManagementSelectionTests(unittest.TestCase):
    def test_broad_or_additive_management_policy_is_not_admissible(self):
        scope = SimpleNamespace(native_scope_id=PROJECT)
        original = management_record()
        validate_management_selection(original, scope)
        for key, value in [('remote_ip_prefix', '0.0.0.0/0'), ('protocol', None),
                ('port_range_max', 443), ('remote_group_id', GROUP), ('ethertype', 'IPv6'),
                ('remote_ip_prefix', '192.0.2.30/32'), ('project_id', SERVER)]:
            selected = deepcopy(original); selected['security_group_rules'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_management_selection(selected, scope)

    def test_historical_descriptor_cannot_invent_a_network_grant(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            body = lifecycle_record(directory)
            ApplicationLifecycleSelection.from_record(body)
            member = body['members'][0]
            member['target_management'] = management_record(project=body['destination_scope']['nativeScopeId'])
            with self.assertRaises(ValueError): ApplicationLifecycleSelection.from_record(body)
            member['phases']['TARGET_BOOTSTRAP'] = dict(step_id='bootstrap-port', operation_id='bootstrap-port-operation',
                                                       scope_side='destination', operation_kind='NETWORK_ATTACH')
            lifecycle = ApplicationLifecycleSelection.from_record(body)
            self.assertEqual(lifecycle.member('machine-1')['target_management']['port_id'], PORT)
            member['phases']['TARGET_BOOTSTRAP']['operation_kind'] = 'VM_POWER'
            with self.assertRaises(ValueError): ApplicationLifecycleSelection.from_record(body)


if __name__ == '__main__':
    unittest.main()
