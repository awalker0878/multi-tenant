"""One current revocable vSphere session and actual native identity/scope checks.

Payload labels are selectors. The session's native user, VM datacenter lineage
and effective privileges must independently match before an effect is sent.
Only fixed commissioned profiles are supported; there is no native write API
or credential routing callback in this owner.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re

from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.controlplane.worker.command_runtime import ApplicationWorkerCommandAuthority, WorkerCommandRuntime
from provisioner.controlplane.worker.grants import CredentialBroker
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from provisioner.execution import readback_core as c, vsphere_observe as vm
from provisioner.execution.vsphere_history import CollectorClient
from provisioner.execution.run_files import require, utcnow

_BASE = frozenset({'System.Anonymous', 'System.View', 'System.Read'})
_PRIVILEGES = {
    'DISCOVER_READ': _BASE,
    'SOURCE_FENCE': _BASE | {'VirtualMachine.Interact.PowerOff', 'VirtualMachine.Config.RemoveDisk'},
    'DISK_ATTACH': _BASE | {'VirtualMachine.Config.AddExistingDisk'},
    'VM_POWER': _BASE | {'VirtualMachine.Interact.PowerOn'},
    'SNAPSHOT_EXPORT': _BASE | {'VApp.Export'},
}


@dataclass(frozen=True)
class NativeVsphereSession:
    token: str = field(repr=False)
    expires_at: datetime

    def __post_init__(self):
        require(isinstance(self.token, str) and self.token and not any(char.isspace() for char in self.token)
            and isinstance(self.expires_at, datetime) and self.expires_at.tzinfo is not None,
            'One bounded current native session is required')


@dataclass(frozen=True)
class VsphereNativeCredentialProfile:
    origin: str
    datacenter_id: str
    session_manager_id: str
    authorization_manager_id: str
    principal: str

    def __post_init__(self):
        require(c.origin(self.origin) == self.origin and re.fullmatch('datacenter-[1-9][0-9]{0,15}', self.datacenter_id),
            'One commissioned native vCenter/datacenter is required')
        for value in (self.session_manager_id, self.authorization_manager_id):
            c.identifier(value)
        c.text(self.principal, length=256)


@dataclass(frozen=True)
class VsphereNativeCredentialOwner:
    commands: WorkerCommandRuntime
    broker: CredentialBroker
    consumer: VaultCredentialConsumer
    profile: VsphereNativeCredentialProfile

    def __post_init__(self):
        require(isinstance(self.commands, WorkerCommandRuntime) and isinstance(self.broker, CredentialBroker)
            and isinstance(self.consumer, VaultCredentialConsumer) and isinstance(self.profile, VsphereNativeCredentialProfile)
            and self.broker._grants is self.commands.grants and self.broker._identities is self.commands.verifier
            and self.broker._issuer is self.consumer.issuer and self.consumer.issuer._lease_store is not None,
            'Actual current mTLS, B10 broker and independently retained revocable native credential custody required')

    def _binding(self, authority):
        from .cold_authority import ColdExportAuthority
        if isinstance(authority, ApplicationWorkerCommandAuthority):
            require(authority.runtime is self.commands and authority.intent_guard.claimed,
                'The original lifecycle native intent must be claimed before credential acquisition')
            guard = authority.intent_guard
            return guard.scope, guard.binding.native_id, guard.operation_kind
        if isinstance(authority, ColdExportAuthority):
            require(authority.command is self.commands and authority.claimed,
                'The original cold export must be claimed before credential acquisition')
            return authority.scope, authority.lease.binding.native_id, authority.operation_kind
        if type(authority) is NativeReadEnrollment:
            require(authority.command is self.commands, 'The independent native reader differs from its real current worker')
            # The caller provides the separately selected exact native VM; a
            # project/datacenter read grant never invents a mutation capability.
            return authority.scope, None, 'DISCOVER_READ'
        raise TypeError('Only actual selected lifecycle/cold or independently enrolled read owners are supported')

    def acquire(self, authority, *, native_id, origin, ca_file):
        return self.acquire_session(authority, native_id=native_id, origin=origin, ca_file=ca_file).token

    def acquire_session(self, authority, *, native_id, origin, ca_file, cursor=None):
        scope, selected, purpose = self._binding(authority)
        require(selected in {None, native_id} and purpose in _PRIVILEGES
            and scope.native_scope_id == self.profile.datacenter_id and origin == self.profile.origin,
            'The native VM, vCenter or datacenter differs from the actually commissioned credential owner')
        vm.moid(native_id, 'vm')
        require(cursor is None or type(authority) is NativeReadEnrollment,
            'Only an independently enrolled read may use the existing scoped observation transaction')
        options = {'cursor': cursor} if cursor is not None else {}
        grant, deadline = authority.require_current(**options)
        if type(authority) is NativeReadEnrollment:
            material = authority.acquire(**options)
        else:
            handle = self.broker.acquire(self.commands.transport_evidence, self.commands.context, grant.grant_id,
                **self.commands.grant_arguments(authority.admitted))
            material = self.consumer.unwrap(handle, grant)
        data = material.data
        if data.get('format') == 'hosting-application-command-credentials/1':
            require(set(data) == {'format', 'repository', 'vsphere', 'openstack'} and data['openstack'] is None,
                'The selected combined application credential projection changed')
            data = data['vsphere']
        require(isinstance(data, dict) and set(data) ==
            {'format', 'origin', 'native_scope_id', 'principal', 'session_token'}
            and data['format'] == 'hosting-vsphere-session/1'
            and (data['origin'], data['native_scope_id'], data['principal']) ==
                (self.profile.origin, self.profile.datacenter_id, self.profile.principal)
            and min(material.expires_at, deadline) > utcnow(),
            'The current dynamic native credential differs from the exact commissioned session projection')
        session = data['session_token']; c.text(session, length=4096)
        require(not any(char.isspace() for char in session), 'Invalid native session header')
        probe = CollectorClient(origin, origin, session, {vm.PREFIX + 'SessionManager/' +
            self.profile.session_manager_id + '/currentSession'}, 'TaskManager', str(ca_file))

        def exchange(method, path, payload=None, *, response_type=dict):
            _current, current_deadline = authority.require_current(**options)
            remaining = (min(material.expires_at, deadline, current_deadline) - utcnow()).total_seconds()
            require(remaining > 0, 'The native session expired before identity verification')
            import time
            probe.timeout = min(10, remaining)
            probe.deadline = min(probe.deadline, time.monotonic() + remaining)
            result, _etag = probe._request(method, path, payload, response_type=response_type)
            authority.require_current(**options)
            return result

        current = exchange('GET', vm.PREFIX + 'SessionManager/' + self.profile.session_manager_id + '/currentSession')
        require(isinstance(current, dict) and current.get('userName') == self.profile.principal
            and current.get('key') == session, 'Actual native session user or identity differs from the current enrolled credential')
        parent = exchange('GET', vm.resource_target({'moid': native_id}, 'parent'))
        visited = set()
        for _ in range(16):
            require(isinstance(parent, dict) and set(parent) <= {'_typeName', 'type', 'value'}
                and parent.get('type') in {'Folder', 'Datacenter'} and isinstance(parent.get('value'), str),
                'The exact native VM has no unambiguous datacenter lineage')
            identity = (parent['type'], parent['value']); require(identity not in visited, 'Cyclic native VM parent lineage')
            visited.add(identity)
            if parent['type'] == 'Datacenter':
                require(parent['value'] == self.profile.datacenter_id, 'The actual native VM belongs to another datacenter')
                break
            require(re.fullmatch('group-[A-Za-z]?[1-9][0-9]{0,15}', parent['value']),
                'Invalid exact native folder reference')
            parent = exchange('GET', vm.PREFIX + 'Folder/' + parent['value'] + '/parent')
        else:
            raise ValueError('The bounded native VM parent lineage did not reach its datacenter')
        privileges = exchange('POST', vm.PREFIX + 'AuthorizationManager/' + self.profile.authorization_manager_id +
            '/FetchUserPrivilegeOnEntities', {'entities': [{'type': 'VirtualMachine', 'value': native_id}],
                'userName': self.profile.principal}, response_type=list)
        require(isinstance(privileges, list) and len(privileges) == 1
            and privileges[0].get('entity', {}).get('type') == 'VirtualMachine'
            and privileges[0]['entity'].get('value') == native_id
            and isinstance(privileges[0].get('privileges'), list)
            and set(privileges[0]['privileges']) == _PRIVILEGES[purpose]
            and len(privileges[0]['privileges']) == len(_PRIVILEGES[purpose]),
            'Actual effective native privileges differ from the exact bounded enrolled operation profile')
        _current, current_deadline = authority.require_current(**options)
        expires_at = min(material.expires_at, deadline, current_deadline)
        require(expires_at > utcnow(), 'The native session expired before contact admission')
        return NativeVsphereSession(session, expires_at)
