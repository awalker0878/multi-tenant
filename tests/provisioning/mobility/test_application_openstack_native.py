"""Real Keystone/Nova/Cinder TLS; original SQL authority is a synthetic port.

These tests prove wire and retained-response boundaries, not site qualification,
application health, independent exclusion or production acceptance.
"""
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from provisioner.controlplane.authority import PlanScope
from provisioner.execution.run_files import digest, encoded, utcnow
from provisioner.migration.application_lifecycle import ApplicationLifecycleRunner
from provisioner.migration.lifecycle import LifecycleCommandGuard
from provisioner.migration.native_openstack import OpenStackApplicationClient, OpenStackApplicationRuntime
from tests.provisioning.mobility.cold_fixture import NativeTls


SERVER = '11111111-1111-4111-8111-111111111111'
VOLUME = '22222222-2222-4222-8222-222222222222'
PROJECT = '33333333-3333-4333-8333-333333333333'
REQUEST = 'req-44444444-4444-4444-8444-444444444444'


class NativeApplicationWireTests(unittest.TestCase):
    def setUp(self):
        self.native = NativeTls(); self.addCleanup(self.native.__exit__)
        self.revoked = False
        self.scope = PlanScope('org-01', 'tenant-01', 'site-01', 'wsd-01', 'openstack-01', PROJECT, 'openstack')
        self.selected = dict(identity_url=self.native.origin + '/v3',
            compute_endpoint=self.native.origin + '/v2.1', volume_endpoint=self.native.origin + '/v3/' + PROJECT,
            region='RegionOne', interface='internal', cloud_alias='target', volume_id=VOLUME,
            device='/dev/vdb', ca_sha256=digest(self.native.ca.read_bytes()), previous_owner={})
        self.grant = SimpleNamespace(grant_id='original-application-grant', operation_scope=self.scope)
        self.deadline = utcnow() + timedelta(seconds=120)
        self.authority = SimpleNamespace(admitted=object(), require_current=self.current, timeout=lambda _: 20)
        self.guard = object.__new__(LifecycleCommandGuard)
        self.guard.member = {'target_native_fence': self.selected}
        self.guard.row = {'scope_side': 'destination', 'operation_id': 'original-operation'}
        self.guard.binding = SimpleNamespace(native_id=SERVER)
        self.guard.scope = self.scope; self.guard.operation_kind = 'VM_POWER'; self.guard.phase = 'TARGET_PREPARE'
        self.authority.intent_guard = self.guard
        command = SimpleNamespace(transport_evidence=object(), context=object(),
            grant_arguments=lambda _: {'original': True})
        self.registry = SimpleNamespace(task_accepted=Mock(side_effect=AssertionError('Nova request IDs are not tasks')))
        self.guest = SimpleNamespace(commands=SimpleNamespace(command_runtime=command), registry=self.registry)
        self.runtime = object.__new__(OpenStackApplicationRuntime)
        for key, value in dict(guest=self.guest, broker=SimpleNamespace(acquire=Mock(return_value=object())),
            consumer=SimpleNamespace(unwrap=Mock(side_effect=self.material)), ca_file=self.native.ca,
            previous_lease=None, previous_exclusion=None).items():
            object.__setattr__(self.runtime, key, value)
        excluded = patch('provisioner.migration.native_openstack.require_previous_writer')
        excluded.start(); self.addCleanup(excluded.stop)
        self.client = OpenStackApplicationClient(self.runtime, self.guard, self.authority)
        self.server = dict(id=SERVER, tenant_id=PROJECT, status='SHUTOFF',
            **{'OS-EXT-STS:power_state': 4, 'OS-EXT-STS:task_state': None})
        self.attachment = dict(volumeId=VOLUME, serverId=SERVER, device='/dev/vdb',
            delete_on_termination=False, attachment_id='55555555-5555-4555-8555-555555555555')
        self.volume = dict(id=VOLUME, multiattach=False, bootable='false', migration_status=None,
            group_id=None, status='in-use', attachments=[dict(server_id=SERVER,
                attachment_id=self.attachment['attachment_id'])])
        self.attached = True
        self.token = {'token': dict(methods=['application_credential'], application_credential={'id': 'current-app'},
            project={'id': PROJECT}, roles=[{'name': 'member'}], expires_at=self.deadline.isoformat(), catalog=[
                dict(type=kind, endpoints=[dict(url=self.selected[field], region_id='RegionOne', interface='internal')])
                for kind, field in (('compute', 'compute_endpoint'), ('volumev3', 'volume_endpoint'))])}
        self.native.routes[('POST', '/v3/auth/tokens')] = lambda _: dict(status=201, body=deepcopy(self.token),
            headers=[('X-Subject-Token', 'native-current-member-token')])
        self.native.routes[('GET', '/v2.1/servers/' + SERVER)] = lambda _: dict(body={'server': deepcopy(self.server)})
        self.native.routes[('GET', '/v2.1/servers/' + SERVER + '/os-volume_attachments')] = lambda _: dict(
            body={'volumeAttachments': [deepcopy(self.attachment)] if self.attached else []})
        self.native.routes[('GET', '/v3/' + PROJECT + '/volumes/' + VOLUME)] = lambda _: dict(body={'volume': deepcopy(self.volume)})
        self.native.routes[('POST', '/v2.1/servers/' + SERVER + '/action')] = self.action
        self.native.routes[('DELETE', '/v2.1/servers/' + SERVER + '/os-volume_attachments/' + VOLUME)] = self.detach
        self.native.routes[('POST', '/v2.1/servers/' + SERVER + '/os-volume_attachments')] = self.attach

    def current(self):
        if self.revoked: raise PermissionError('Synthetic current original grant revoked')
        return self.grant, self.deadline

    def material(self, *_):
        cloud = {'clouds': {'target': dict(auth_type='v3applicationcredential', verify=True,
            region_name='RegionOne', interface='internal', auth=dict(auth_url=self.selected['identity_url'],
                application_credential_id='current-app', application_credential_secret='synthetic-vault-secret'))}}
        return {'environment': {}, 'cloud': cloud}, self.deadline, 'synthetic-custody-digest'

    def action(self, request):
        body = request['body']
        self.assertIn(body, (encoded({'os-start': None}), encoded({'os-stop': None})))
        on = body == encoded({'os-start': None})
        self.server.update(status='ACTIVE' if on else 'SHUTOFF',
            **{'OS-EXT-STS:power_state': 1 if on else 4})
        return dict(status=202, raw=b'', headers=[('X-OpenStack-Request-Id', REQUEST)])

    def detach(self, _):
        self.attached = False; self.volume.update(status='available', attachments=[])
        return dict(status=202, raw=b'', headers=[('X-OpenStack-Request-Id', REQUEST)])

    def attach(self, request):
        self.assertEqual(request['body'], encoded({'volumeAttachment': {
            'volumeId': VOLUME, 'device': '/dev/vdb', 'delete_on_termination': False}}))
        self.attached = True; self.volume.update(status='in-use', attachments=[dict(
            server_id=SERVER, attachment_id=self.attachment['attachment_id'])])
        return dict(body={'volumeAttachment': deepcopy(self.attachment)}, headers=[('X-OpenStack-Request-Id', REQUEST)])

    def test_original_start_uses_fresh_project_credentials_for_every_exchange_and_retains_only_request_id(self):
        self.assertEqual(self.client.start(), REQUEST)
        self.client.snapshot(attached=True, powered=True)
        contacts = [r for r in self.native.requests if r['path'] != '/v3/auth/tokens']
        self.assertEqual(self.runtime.broker.acquire.call_count, len(contacts))
        self.assertEqual(self.runtime.consumer.unwrap.call_count, len(contacts))
        self.assertTrue(all(r['headers']['X-Auth-Token'] == 'native-current-member-token' for r in contacts))
        self.assertTrue(all('synthetic-vault-secret' not in r['body'].decode() for r in contacts))
        self.registry.task_accepted.assert_not_called()

    def test_retained_detach_and_reattach_are_fixed_nova_actions_with_independent_cinder_postconditions(self):
        self.guard.operation_kind = 'SOURCE_FENCE'
        before = self.client.snapshot(attached=True)
        self.assertEqual(self.client.detach(before), REQUEST)
        detached = self.client.snapshot(attached=False)
        self.guard.operation_kind = 'DISK_ATTACH'
        self.assertEqual(self.client.attach(detached), REQUEST)
        self.client.snapshot(attached=True)
        self.registry.task_accepted.assert_not_called()

    def test_late_genuine_start_reply_is_retained_before_revocation_holds_readback(self):
        path = ('POST', '/v2.1/servers/' + SERVER + '/action')
        def late(request):
            spec = self.action(request)
            spec['before_response'] = lambda: setattr(self, 'revoked', True)
            return spec
        self.native.routes[path] = late
        self.assertEqual(self.client.start(), REQUEST)
        count = len(self.native.requests)
        with self.assertRaises(PermissionError): self.client.snapshot(attached=True, powered=True)
        self.assertEqual(len(self.native.requests), count)
        self.assertEqual(sum((r['method'], r['path']) == path for r in self.native.requests), 1)

    def test_target_prepare_does_not_register_request_id_as_a_native_task(self):
        runner = object.__new__(ApplicationLifecycleRunner)
        log = SimpleNamespace(append=Mock())
        with patch.object(OpenStackApplicationRuntime, 'client', return_value=self.client):
            result = runner._target_prepare(self.guest, self.authority, self.runtime, log)
        self.assertEqual(result['native_request_id'], REQUEST)
        self.assertFalse(result['isolated_management_reachability_verified'])
        self.registry.task_accepted.assert_not_called()
        self.assertIn(('NATIVE_START_RETURNED', {'native_request_id': REQUEST}),
                      [call.args for call in log.append.call_args_list])

    def test_wrong_native_project_duplicate_role_or_changed_catalog_cannot_dispatch_effect(self):
        for change in ('project', 'role', 'catalog'):
            with self.subTest(change=change):
                original = deepcopy(self.token)
                if change == 'project': self.token['token']['project']['id'] = SERVER
                elif change == 'role': self.token['token']['roles'].append({'name': 'member'})
                else: self.token['token']['catalog'][0]['endpoints'][0]['url'] += '/foreign'
                self.native.requests.clear()
                with self.assertRaises(ValueError): self.client.start()
                self.assertEqual([(r['method'], r['path']) for r in self.native.requests], [('POST', '/v3/auth/tokens')])
                self.token = original

    def test_ambiguous_headers_framing_or_invalid_request_identity_cannot_become_original_receipt(self):
        path = ('POST', '/v2.1/servers/' + SERVER + '/action')
        for headers in ([('X-OpenStack-Request-Id', REQUEST)] * 2,
                        [('X-OpenStack-Request-Id', 'not-a-native-request')],
                        [('X-OpenStack-Request-Id', REQUEST), ('Content-Length', '0')],
                        [('X-OpenStack-Request-Id', REQUEST), ('Content-Encoding', 'gzip')]):
            with self.subTest(headers=headers):
                self.native.routes[path] = dict(status=202, raw=b'', headers=headers)
                with self.assertRaises(ValueError): self.client.start()
        self.registry.task_accepted.assert_not_called()

    def test_revoked_authority_wrong_volume_or_other_attachment_blocks_before_native_write(self):
        self.revoked = True
        with self.assertRaises(PermissionError): self.client.start()
        self.assertEqual(self.native.requests, [])
        self.revoked = False
        self.volume['multiattach'] = True
        with self.assertRaises(ValueError): self.client.start()
        self.assertFalse(any(r['path'].endswith('/action') for r in self.native.requests))


if __name__ == '__main__':
    unittest.main()
