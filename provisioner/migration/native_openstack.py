"""Fixed Nova/Cinder retained-volume fencing and recovery for an existing VM.

Every individual exchange authenticates a freshly brokered application
credential against the commissioned Keystone project and service catalogue.
Nova owns attachment changes; Cinder is read for their independent storage
postconditions. No force-detach, reset-state or deletion endpoint is available.
"""
from __future__ import annotations

from dataclasses import dataclass
import http.client
from pathlib import Path
import re
import ssl
from urllib.parse import urlsplit

from provisioner.controlplane.persistence.store import OwnerLease
from provisioner.controlplane.reconciliation import OwnerRecoveryEvidence
from provisioner.controlplane.reconciliation.planned_terraform import VaultOpenStackCredentialConsumer
from provisioner.controlplane.worker.grants import CredentialBroker
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from provisioner.execution import readback_core as c, terraform_run
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import digest, encoded, read_private, require, utcnow
from .lifecycle import LifecycleCommandGuard
from .remote_app import ApplicationGuestRuntime
from .source_exclusion import require_previous_writer

_UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
_REQUEST_ID = re.compile(r'req-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')


def _endpoint(value):
    parsed = urlsplit(value)
    require(parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password
            and not parsed.query and not parsed.fragment and parsed.path and '..' not in parsed.path.split('/'),
            'One commissioned HTTPS native service endpoint is required')
    return parsed


class ApplicationOpenStackCredentialConsumer(VaultCredentialConsumer):
    """Fixed combined revocable native/repository projection for capture phases."""
    def unwrap(self, handle, grant):
        material = super().unwrap(handle, grant)
        data = material.data
        require(isinstance(data, dict) and set(data) == {'format', 'repository', 'vsphere', 'openstack'}
            and data['format'] == 'hosting-application-command-credentials/1'
            and data['vsphere'] is None and isinstance(data['openstack'], dict)
            and set(data['openstack']) == {'environment', 'cloud'},
            'A capture phase requires the exact enrolled combined OpenStack/repository credential projection')
        return data['openstack'], material.expires_at, material.lease_digest


@dataclass(frozen=True)
class OpenStackApplicationRuntime:
    guest: ApplicationGuestRuntime
    broker: CredentialBroker
    consumer: VaultOpenStackCredentialConsumer | ApplicationOpenStackCredentialConsumer
    ca_file: Path
    previous_lease: OwnerLease
    previous_exclusion: OwnerRecoveryEvidence

    def __post_init__(self):
        require(isinstance(self.guest, ApplicationGuestRuntime) and isinstance(self.broker, CredentialBroker)
                and isinstance(self.consumer, (VaultOpenStackCredentialConsumer, ApplicationOpenStackCredentialConsumer))
                and self.broker._issuer is self.consumer.issuer
                and self.broker._grants is self.guest.commands.command_runtime.grants
                and self.broker._identities is self.guest.commands.command_runtime.verifier
                and isinstance(self.previous_lease, OwnerLease)
                and isinstance(self.previous_exclusion, OwnerRecoveryEvidence),
                'An actual scoped native credential and independently excluded old writer are required')
        object.__setattr__(self, 'ca_file', Path(self.ca_file))

    @property
    def registry(self):
        return self.guest.registry

    def client(self, guard):
        require(isinstance(guard, LifecycleCommandGuard) and guard.runtime is self.guest.worker
                and guard.operation_kind in {'SOURCE_FENCE', 'DISK_ATTACH', 'VM_POWER', 'NETWORK_ATTACH', 'POLICY_APPLY'},
                'Only exact enrolled fence, retained attachment and power actions are implemented')
        return OpenStackApplicationClient(self, guard, self.guest.select(guard))


class OpenStackApplicationClient:
    def __init__(self, runtime, guard, authority):
        self.runtime, self.guard, self.authority = runtime, guard, authority
        self.selected = dict(guard.member['target_native_fence' if guard.row['scope_side'] == 'destination' else 'native_fence'])
        if guard.phase in {'TARGET_BOOTSTRAP', 'TARGET_POLICY', 'TARGET_ISOLATE'}:
            from .bootstrap_selection import validate_management_selection
            validate_management_selection(guard.member['target_management'], guard.scope)
            self.selected['network_endpoint'] = guard.member['target_management']['network_endpoint']
        for key in ('identity_url', 'compute_endpoint', 'volume_endpoint'):
            _endpoint(self.selected[key])
        require(urlsplit(self.selected['identity_url']).path.rstrip('/') == '/v3'
                and digest(read_private(runtime.ca_file)) == self.selected['ca_sha256'],
                'The selected Keystone authority or actual trust bundle changed')
        self.server_id = guard.binding.native_id
        self.volume_id = self.selected['volume_id']
        require(_UUID.fullmatch(self.server_id) and _UUID.fullmatch(self.volume_id),
                'The exact existing Nova server and retained Cinder volume UUIDs are required')
        self.tls = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.tls.minimum_version = ssl.TLSVersion.TLSv1_2
        self.tls.verify_flags |= ssl.VERIFY_X509_STRICT
        self.tls.load_verify_locations(cadata=read_private(runtime.ca_file).decode('ascii'))

    def _current(self):
        require_previous_writer(self.guard, self.runtime.previous_lease,
            self.runtime.previous_exclusion, self.selected['previous_owner'])
        return self.authority.require_current()

    def _http(self, endpoint, method, suffix, body, headers, accepted, expires, *, retain_native_response=False):
        self._current()
        parsed = _endpoint(endpoint)
        remaining = min(self.authority.timeout(30), (expires-utcnow()).total_seconds())
        require(remaining > 0, 'The original native command credential expired')
        connection = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443,
                                                 timeout=remaining, context=self.tls)
        try:
            path = parsed.path.rstrip('/') + suffix
            connection.request(method, path, body=None if body is None else encoded(body),
                headers={'Accept': 'application/json', 'Content-Type': 'application/json',
                         'Accept-Encoding': 'identity', 'Connection': 'close'} | headers)
            response = connection.getresponse(); raw = response.read(2**20+1)
            lengths = response.headers.get_all('Content-Length', [])
            require(len(lengths) == 1 and lengths[0].isdigit() and int(lengths[0]) == len(raw)
                    and not response.headers.get_all('Transfer-Encoding', [])
                    and response.headers.get_all('Content-Encoding', []) in ([], ['identity'])
                    and all(len(response.headers.get_all(name, [])) <= 1
                            for name in ('Content-Type', 'X-OpenStack-Request-Id', 'X-Subject-Token')),
                    'The native reply has ambiguous framing or original identity headers')
            require(response.status in accepted and len(raw) <= 2**20
                    and (not raw or response.headers.get_content_type() == 'application/json'),
                    'The exact native exchange failed or returned unbounded data')
            result = strict_loads(raw) if raw else None
            retained_headers = {key.lower(): value for key, value in response.getheaders()
                                if key.lower() in {'x-openstack-request-id', 'x-subject-token'}}
            if retain_native_response:
                require(method in {'POST', 'DELETE', 'PUT'} and endpoint in
                        {self.selected['compute_endpoint'], self.selected['volume_endpoint'],
                         self.selected.get('network_endpoint')}
                        and _REQUEST_ID.fullmatch(retained_headers.get('x-openstack-request-id', '')),
                        'An authentic native request identity is required for the original effect receipt')
                # Retain a genuine late reply before the caller's next current
                # check. Revocation must stop readback/acceptance, never erase
                # the identity of an effect that the native service accepted.
            else:
                self._current()
            return result, retained_headers
        finally:
            connection.close()

    def _credential(self):
        command = self.runtime.guest.commands.command_runtime
        grant, deadline = self._current()
        handle = self.runtime.broker.acquire(command.transport_evidence, command.context, grant.grant_id,
                                            **command.grant_arguments(self.authority.admitted))
        data, expires, _lease = self.runtime.consumer.unwrap(handle, grant)
        require(data['environment'] == {}, 'Application native fencing cannot borrow backend credentials')
        cloud = terraform_run.cloud_config(encoded(data['cloud']), self.selected['cloud_alias'])
        selected = cloud['clouds'][self.selected['cloud_alias']]
        require((selected['auth']['auth_url'], selected['region_name'], selected['interface']) ==
                (self.selected['identity_url'], self.selected['region'], self.selected['interface']),
                'The fresh credential changes the commissioned native authority')
        body = {'auth': {'identity': {'methods': ['application_credential'], 'application_credential': {
            'id': selected['auth']['application_credential_id'],
            'secret': selected['auth']['application_credential_secret']}}}}
        result, headers = self._http(self.selected['identity_url'], 'POST', '/auth/tokens', body, {},
                                    {201}, min(expires, deadline))
        token = result.get('token') if isinstance(result, dict) else None
        require(isinstance(token, dict) and token.get('methods') == ['application_credential']
                and token.get('application_credential', {}).get('id') == selected['auth']['application_credential_id']
                and token.get('project', {}).get('id') == grant.operation_scope.native_scope_id
                and token.get('system') is None and token.get('domain') is None
                and isinstance(token.get('roles'), list)
                and [role.get('name') for role in token['roles']] == ['member']
                and headers.get('x-subject-token'),
                'Actual native authentication differs from the exact enrolled project-member role')
        services = [('compute', 'compute_endpoint'), ('volumev3', 'volume_endpoint')]
        if 'network_endpoint' in self.selected:
            services.append(('network', 'network_endpoint'))
        for service_type, field in services:
            endpoints = [endpoint for service in token.get('catalog', []) if service.get('type') == service_type
                for endpoint in service.get('endpoints', [])
                if endpoint.get('region_id', endpoint.get('region')) == self.selected['region']
                and endpoint.get('interface') == self.selected['interface']]
            require(len(endpoints) == 1 and endpoints[0]['url'].rstrip('/') == self.selected[field].rstrip('/'),
                    'The actual service catalogue differs from the commissioned native project endpoints')
        deadline = min(deadline, expires, c.timestamp(token['expires_at']))
        require(deadline > utcnow(), 'The actual native project token expired')
        return headers['x-subject-token'], deadline

    def request(self, service, method, suffix, body=None, *, accepted=(200,), revision=None):
        require(service in {'compute', 'volume', 'network'} and method in {'GET', 'POST', 'DELETE', 'PUT'},
                'Only the fixed compute and block storage application owners may contact native APIs')
        if service == 'network':
            bootstrap = self.guard.phase == 'TARGET_BOOTSTRAP' and self.guard.operation_kind == 'NETWORK_ATTACH'
            policy = self.guard.phase in {'TARGET_POLICY', 'TARGET_ISOLATE'} and self.guard.operation_kind == 'POLICY_APPLY'
            groups = [self.guard.member['target_management']['security_group_id']]
            if self.guard.phase == 'TARGET_POLICY':
                groups.append(self.guard.member['target_policy']['security_group_id'])
            expected = {'port': {'admin_state_up': True}} if bootstrap else {'port': {'security_groups': groups}}
            require((bootstrap or policy) and
                    ((method == 'GET' and revision is None and body is None) or
                     (method == 'PUT' and suffix == '/ports/' + self.guard.member['target_management']['port_id']
                      and body == expected and type(revision) is int and revision >= 0)),
                    'Only the original port enablement or exact approved production/isolation policy set is implemented')
        else:
            require(method != 'PUT' and revision is None, 'A management revision cannot authorize another native effect')
            require(self.guard.operation_kind not in {'NETWORK_ATTACH', 'POLICY_APPLY'} or method == 'GET',
                    'A network capability cannot authorize native power or storage effects')
        token, expires = self._credential()
        headers = {'X-Auth-Token': token}
        if service != 'network':
            headers['OpenStack-API-Version'] = 'compute 2.89' if service == 'compute' else 'volume 3.70'
        if revision is not None:
            headers['If-Match'] = 'revision_number=' + str(revision)
        return self._http(self.selected[service + '_endpoint'], method, suffix, body, headers,
                          set(accepted), expires, retain_native_response=method != 'GET')

    def enable_management(self, before, *, retain_response=False):
        from .application_network import management_snapshot
        require(self.guard.phase == 'TARGET_BOOTSTRAP' and self.guard.operation_kind == 'NETWORK_ATTACH',
                'The original management-port operation needs its separate network capability')
        require(type(retain_response) is bool, 'The original reply retention mode must be explicit')
        selected = self.guard.member['target_management']
        require(management_snapshot(lambda service, path: self.request(service, 'GET', '/' + path)[0],
                    selected, self.guard.scope, self.server_id, enabled=False,
                    policy=self.guard.member.get('target_policy'),
                    health_port=self.guard.member.get('target', {}).get('health', {}).get('port')) == before,
                'The original isolated management policy changed before port enablement')
        extension, _ = self.request('network', 'GET', '/extensions/revision-if-match')
        require(extension.get('extension', {}).get('alias') == 'revision-if-match',
                'Native compare-and-swap port transitions are not available on this deployment')
        result, headers = self.request('network', 'PUT', '/ports/' + selected['port_id'],
            {'port': {'admin_state_up': True}}, revision=before['port']['revision_number'])
        if retain_response:
            return headers['x-openstack-request-id'], result
        require(result.get('port', {}).get('id') == selected['port_id']
                and result['port'].get('admin_state_up') is True,
                'The original management-port update has no exact native response')
        return headers['x-openstack-request-id']

    def set_production_policy(self, before, *, enable):
        from .application_network import management_snapshot
        require(type(enable) is bool and self.guard.operation_kind == 'POLICY_APPLY'
                and self.guard.phase == ('TARGET_POLICY' if enable else 'TARGET_ISOLATE'),
                'Only the separate exact production/isolation policy capability is executable')
        member = self.guard.member
        require(management_snapshot(lambda service, path: self.request(service, 'GET', '/' + path)[0],
                    member['target_management'], self.guard.scope, self.server_id, enabled=True,
                    policy=member['target_policy'], policy_enabled=False if enable else True,
                    health_port=member['target']['health']['port']) == before,
                'The exact retained port or independently approved production rules changed before policy realization')
        extension, _ = self.request('network', 'GET', '/extensions/revision-if-match')
        require(extension.get('extension', {}).get('alias') == 'revision-if-match',
                'Native conditional policy transitions are unavailable')
        groups = [member['target_management']['security_group_id']] + \
            ([member['target_policy']['security_group_id']] if enable else [])
        reply, headers = self.request('network', 'PUT', '/ports/' + member['target_management']['port_id'],
            {'port': {'security_groups': groups}}, revision=before['port']['revision_number'])
        return headers['x-openstack-request-id'], reply

    def snapshot(self, *, attached, powered=False):
        server, _ = self.request('compute', 'GET', '/servers/' + self.server_id)
        attachments, _ = self.request('compute', 'GET', '/servers/' + self.server_id + '/os-volume_attachments')
        volume, _ = self.request('volume', 'GET', '/volumes/' + self.volume_id)
        server, volume = server['server'], volume['volume']
        rows = attachments['volumeAttachments']
        require(server.get('id') == self.server_id and server.get('tenant_id') == self.guard.scope.native_scope_id
                and server.get('status') == ('ACTIVE' if powered else 'SHUTOFF')
                and server.get('OS-EXT-STS:power_state') == (1 if powered else 4)
                and server.get('OS-EXT-STS:task_state') is None and isinstance(rows, list)
                and volume.get('id') == self.volume_id and volume.get('multiattach') is False
                and volume.get('bootable') == 'false' and volume.get('migration_status') is None
                and not volume.get('group_id') and isinstance(volume.get('attachments'), list),
                'The exact retained native VM/volume is running, shared, migrating or changing')
        selected = [row for row in rows if row.get('volumeId') == self.volume_id]
        if attached:
            require(len(selected) == 1 and selected[0].get('serverId') == self.server_id
                    and selected[0].get('device') == self.selected['device']
                    and selected[0].get('delete_on_termination') is False
                    and volume['status'] == 'in-use' and len(volume['attachments']) == 1
                    and volume['attachments'][0].get('server_id') == self.server_id
                    and volume['attachments'][0].get('attachment_id') == selected[0].get('attachment_id'),
                    'The original retained data volume has another native writer or attachment identity')
        else:
            require(not selected and volume['status'] == 'available' and volume['attachments'] == [],
                    'The retained native data volume remains attached or its outcome is pending')
        return dict(server=server, attachments=rows, volume=volume)

    def stop(self):
        require(self.guard.operation_kind == 'SOURCE_FENCE', 'Shutdown requires its exact source-fence grant')
        result, headers = self.request('compute', 'POST', '/servers/' + self.server_id + '/action',
                                       {'os-stop': None}, accepted=(202,))
        require(result is None and headers.get('x-openstack-request-id'),
                'The original Nova shutdown returned no retained request identity')
        return headers['x-openstack-request-id']

    def detach(self, before):
        require(self.guard.operation_kind == 'SOURCE_FENCE', 'Native detach requires its exact source-fence grant')
        require(self.snapshot(attached=True) == before, 'The retained native attachment changed before removal')
        result, headers = self.request('compute', 'DELETE', '/servers/' + self.server_id +
            '/os-volume_attachments/' + self.volume_id, accepted=(202,))
        require(result is None and headers.get('x-openstack-request-id'),
                'The original Nova detach returned no retained request identity')
        return headers['x-openstack-request-id']

    def attach(self, before):
        require(self.guard.operation_kind == 'DISK_ATTACH', 'Retained-volume reattachment needs its own grant')
        require(self.snapshot(attached=False) == before, 'The retained detached volume changed before reattachment')
        result, headers = self.request('compute', 'POST', '/servers/' + self.server_id + '/os-volume_attachments',
            {'volumeAttachment': {'volumeId': self.volume_id, 'device': self.selected['device'],
                                  'delete_on_termination': False}}, accepted=(200,))
        require(result['volumeAttachment'].get('volumeId') == self.volume_id
                and result['volumeAttachment'].get('serverId') == self.server_id
                and headers.get('x-openstack-request-id'),
                'The original retained-volume attachment has no exact native response')
        return headers['x-openstack-request-id']

    def start(self):
        require(self.guard.operation_kind == 'VM_POWER', 'Native start needs its separate exact power grant')
        self.snapshot(attached=True)
        result, headers = self.request('compute', 'POST', '/servers/' + self.server_id + '/action',
                                       {'os-start': None}, accepted=(202,))
        require(result is None and headers.get('x-openstack-request-id'),
                'The original native start returned no retained request identity')
        return headers['x-openstack-request-id']
