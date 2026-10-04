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
                and guard.operation_kind in {'SOURCE_FENCE', 'DISK_ATTACH', 'VM_POWER'},
                'Only exact enrolled fence, retained attachment and power actions are implemented')
        return OpenStackApplicationClient(self, guard, self.guest.select(guard))


class OpenStackApplicationClient:
    def __init__(self, runtime, guard, authority):
        self.runtime, self.guard, self.authority = runtime, guard, authority
        self.selected = guard.member['target_native_fence' if guard.row['scope_side'] == 'destination' else 'native_fence']
        for key in ('identity_url', 'compute_endpoint', 'volume_endpoint'):
            _endpoint(self.selected[key])
        require(urlsplit(self.selected['identity_url']).path.rstrip('/') == '/v3'
                and digest(read_private(runtime.ca_file)) == self.selected['ca_sha256'],
                'The selected Keystone authority or actual trust bundle changed')
        self.server_id = guard.binding.native_id
        self.volume_id = self.selected['volume_id']
        require(re.fullmatch(r'[0-9a-f-]{36}', self.server_id), 'The exact existing Nova server UUID is required')
        self.tls = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.tls.minimum_version = ssl.TLSVersion.TLSv1_2
        self.tls.verify_flags |= ssl.VERIFY_X509_STRICT
        self.tls.load_verify_locations(cadata=read_private(runtime.ca_file).decode('ascii'))

    def _current(self):
        require_previous_writer(self.guard, self.runtime.previous_lease,
            self.runtime.previous_exclusion, self.selected['previous_owner'])
        return self.authority.require_current()

    def _http(self, endpoint, method, suffix, body, headers, accepted, expires):
        self._current()
        parsed = _endpoint(endpoint)
        remaining = min(self.authority.timeout(30), (expires-utcnow()).total_seconds())
        require(remaining > 0, 'The original native command credential expired')
        connection = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443,
                                                 timeout=remaining, context=self.tls)
        try:
            path = parsed.path.rstrip('/') + suffix
            connection.request(method, path, body=None if body is None else encoded(body),
                headers={'Accept': 'application/json', 'Content-Type': 'application/json'} | headers)
            response = connection.getresponse(); raw = response.read(2**20+1)
            require(response.status in accepted and len(raw) <= 2**20
                    and (not raw or response.headers.get_content_type() == 'application/json'),
                    'The exact native exchange failed or returned unbounded data')
            result = strict_loads(raw) if raw else None
            retained_headers = {key.lower(): value for key, value in response.getheaders()
                                if key.lower() in {'x-openstack-request-id', 'x-subject-token'}}
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
                and {role.get('name') for role in token['roles']} == {'member'}
                and headers.get('x-subject-token'),
                'Actual native authentication differs from the exact enrolled project-member role')
        for service_type, field in (('compute', 'compute_endpoint'), ('volumev3', 'volume_endpoint')):
            endpoints = [endpoint for service in token.get('catalog', []) if service.get('type') == service_type
                for endpoint in service.get('endpoints', []) if endpoint.get('region') == self.selected['region']
                and endpoint.get('interface') == self.selected['interface']]
            require(len(endpoints) == 1 and endpoints[0]['url'].rstrip('/') == self.selected[field].rstrip('/'),
                    'The actual service catalogue differs from the commissioned native project endpoints')
        deadline = min(deadline, expires, c.timestamp(token['expires_at']))
        require(deadline > utcnow(), 'The actual native project token expired')
        return headers['x-subject-token'], deadline

    def request(self, service, method, suffix, body=None, *, accepted=(200,)):
        require(service in {'compute', 'volume'} and method in {'GET', 'POST', 'DELETE'},
                'Only the fixed compute and block storage application owners may contact native APIs')
        token, expires = self._credential()
        headers = {'X-Auth-Token': token,
            'OpenStack-API-Version': 'compute 2.89' if service == 'compute' else 'volume 3.70'}
        return self._http(self.selected[service + '_endpoint'], method, suffix, body, headers, set(accepted), expires)

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
