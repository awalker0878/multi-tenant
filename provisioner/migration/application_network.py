"""Enable one retained isolated management port and independently read it.

The existing Nova server/Neutron port must already be associated by target
staging. This owner creates no network or policy and never discovers resources
by name. It retains the one original conditional update before any subsequent
authority check. The separate project reader observes policy before a separate
guest reader contacts the pinned SSH endpoint. Native datapath qualification
and production traffic admission remain separate acceptance work.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from provisioner.controlplane.reconciliation.adapters.openstack_readback import OpenStackProjectReader
from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.execution.run_files import digest, read_private, require, utcnow
from provisioner.execution.neutron_observe import strict_loads
from .bootstrap_selection import RULE_FIELDS, validate_management_selection
from .native_openstack import OpenStackApplicationRuntime
from .remote_app import ApplicationHealthReadRuntime
from .staging import ApplicationStagedHandover


def management_snapshot(get, selected, scope, server_id, *, enabled):
    """Read only fixed IDs; missing or foreign native facts are never defaults."""
    validate_management_selection(selected, scope)
    server = get('compute', 'servers/' + server_id)['server']
    interfaces = get('compute', 'servers/' + server_id + '/os-interface')['interfaceAttachments']
    port = get('network', 'ports/' + selected['port_id'])['port']
    network = get('network', 'networks/' + selected['network_id'])['network']
    subnet = get('network', 'subnets/' + selected['subnet_id'])['subnet']
    group = get('network', 'security-groups/' + selected['security_group_id'])['security_group']
    require(server.get('id') == server_id and server.get('tenant_id') == scope.native_scope_id
            and server.get('status') == 'ACTIVE' and server.get('OS-EXT-STS:power_state') == 1
            and 'OS-EXT-STS:task_state' in server and server['OS-EXT-STS:task_state'] is None,
            'The exact management target is not independently observed as booted and quiescent')
    fixed = [{'subnet_id': selected['subnet_id'], 'ip_address': selected['ipv4_address']}]
    require(type(interfaces) is list and len(interfaces) == 1
            and interfaces[0].get('port_id') == selected['port_id']
            and interfaces[0].get('net_id') == selected['network_id']
            and interfaces[0].get('mac_addr') == selected['mac_address']
            and interfaces[0].get('fixed_ips') == fixed,
            'The actual server has a missing, foreign or additional network interface')
    expected_port = dict(id=selected['port_id'], project_id=scope.native_scope_id,
        network_id=selected['network_id'], device_id=server_id, mac_address=selected['mac_address'],
        admin_state_up=enabled, port_security_enabled=True, security_groups=[selected['security_group_id']],
        fixed_ips=fixed, allowed_address_pairs=[], **{'binding:vnic_type': 'normal', 'binding:profile': {}})
    require(all(key in port and port[key] == value and type(port[key]) is type(value)
                for key, value in expected_port.items())
            and type(port.get('device_owner')) is str and port['device_owner'].startswith('compute:')
            and port.get('binding:vif_type') in {'ovs', 'bridge'}
            and type(port.get('binding:vif_details')) is dict
            and port['binding:vif_details'].get('port_filter') is True
            and not port.get('trunk_details') and port.get('status') == ('ACTIVE' if enabled else 'DOWN')
            and type(port.get('revision_number')) is int and port['revision_number'] >= 0,
            'The management port is changing, bypassing policy or outside the exact retained attachment')
    expected_network = dict(id=selected['network_id'], project_id=scope.native_scope_id,
        admin_state_up=True, shared=False, port_security_enabled=True,
        subnets=[selected['subnet_id']], mtu=selected['mtu'], **{'router:external': False})
    expected_subnet = dict(id=selected['subnet_id'], project_id=scope.native_scope_id,
        network_id=selected['network_id'], ip_version=4, **selected['subnet'])
    for actual, expected in ((network, expected_network), (subnet, expected_subnet)):
        require(all(key in actual and actual[key] == value and type(actual[key]) is type(value)
                    for key, value in expected.items()),
                'The current private management network, MTU or subnet service paths changed')
    require(group.get('id') == selected['security_group_id']
            and group.get('project_id') == scope.native_scope_id and group.get('stateful') is True
            and type(group.get('security_group_rules')) is list,
            'The selected stateful native management policy is missing or foreign')
    rules = group['security_group_rules']
    require(all(type(rule) is dict and RULE_FIELDS <= rule.keys() for rule in rules),
            'A native management rule omits its exact selector or bypass facts')
    projected_rules = [{key: rule[key] for key in RULE_FIELDS} for rule in rules]
    require(sorted(projected_rules, key=lambda rule: rule['id']) ==
            sorted(selected['security_group_rules'], key=lambda rule: rule['id']),
            'Native management rules are missing, additive or changed since selection')
    return dict(server={key: server[key] for key in
                ('id', 'tenant_id', 'status', 'OS-EXT-STS:power_state', 'OS-EXT-STS:task_state')},
        interfaces=interfaces, port=expected_port | {key: port[key] for key in
                ('device_owner', 'binding:vif_type', 'binding:vif_details', 'status', 'revision_number')},
        network=expected_network, subnet=expected_subnet,
        group=dict(id=group['id'], project_id=group['project_id'], stateful=True,
                   security_group_rules=sorted(projected_rules, key=lambda rule: rule['id'])))


def require_staged_management(staged, lifecycle, member_id):
    require(type(staged) is ApplicationStagedHandover,
            'Management enablement needs the protected actual target-creation handover')
    body, member = staged.to_dict(), lifecycle.member(member_id)
    require(body['destinationScope'] == lifecycle.to_dict()['destination_scope'],
            'The retained management target belongs to another native destination')
    rows = [row for row in body['associations'] if row['machineId'] == member_id]
    require(len(rows) == 1 and rows[0]['targetBinding']['nativeId'] == member['target']['native_id']
            and len(rows[0]['nics']) == 1
            and rows[0]['nics'][0]['targetBinding']['nativeId'] == member['target_management']['port_id'],
            'The selected management port was not independently retained for this exact target VM')


@dataclass(frozen=True)
class OpenStackBootstrapRuntime:
    native: OpenStackApplicationRuntime
    enrollment: NativeReadEnrollment
    guest_reader: ApplicationHealthReadRuntime

    def __post_init__(self):
        require(type(self.native) is OpenStackApplicationRuntime
                and type(self.enrollment) is NativeReadEnrollment
                and type(self.guest_reader) is ApplicationHealthReadRuntime
                and self.guest_reader.side == 'destination' and self.guest_reader.recovery is None
                and self.guest_reader.writer is self.native.guest.worker
                and self.guest_reader.writer_guest is self.native.guest
                and self.guest_reader.registry is self.registry
                and self.enrollment.command.authority is self.native.guest.worker.execution_authority
                and self.enrollment.command.grants is self.registry._grants
                and self.enrollment.command.context == self.native.guest.worker.context
                and self.enrollment.subject != self.native.guest.worker.identity.subject
                and self.enrollment.scope == self.native.guest.worker.scope,
                'Independent current project/guest readers must share the original enrolled native owners')

    @property
    def registry(self):
        return self.native.registry

    def observe(self, admitted, artifact, lifecycle, member_id, *, enabled=True):
        from provisioner.controlplane.authority import PlanScope
        from provisioner.controlplane.persistence import canonical_record_digest
        member = lifecycle.member(member_id)
        require(self.enrollment.admitted == admitted
                and self.enrollment.selection_digest == canonical_record_digest(artifact)
                and self.guest_reader.enrollment.admitted == admitted
                and self.guest_reader.enrollment.selection_digest == self.enrollment.selection_digest
                and PlanScope.from_record(lifecycle.to_dict()['destination_scope']) == self.enrollment.scope,
                'The independent management readers are enrolled for another original application')
        selected, fence = member['target_management'], member['target_native_fence']
        require(digest(read_private(self.native.ca_file)) == fence['ca_sha256'],
                'The selected native management trust bundle changed')
        reader = OpenStackProjectReader(self.enrollment, identity_endpoint=fence['identity_url'],
            ca_bundle=self.native.ca_file, alias=fence['cloud_alias'],
            compute_origin='https://' + urlsplit(fence['compute_endpoint']).netloc)
        require(all(reader.endpoints[key].rstrip('/') == endpoint.rstrip('/') for key, endpoint in
                    (('compute', fence['compute_endpoint']), ('volume', fence['volume_endpoint']),
                     ('network', selected['network_endpoint']))),
                'The independently authenticated native service catalogue changed')
        snapshot = management_snapshot(reader.get, selected, self.enrollment.scope,
                                      member['target']['native_id'], enabled=enabled)
        self.enrollment.require_current()
        return dict(reader_subject=self.enrollment.subject,
            read_grant_id=self.enrollment.command.grant.grant_id,
            read_operation_id=self.enrollment.command.grant.operation_id,
            observed_at=utcnow().isoformat(), native_snapshot=snapshot)

    def execute(self, authority, staged, log):
        from provisioner.controlplane.persistence import canonical_record_digest
        guard = authority.intent_guard
        require(guard.phase == 'TARGET_BOOTSTRAP' and guard.runtime is self.native.guest.worker,
                'Only the exact retained target management-port operation is executable')
        require_staged_management(staged, guard.lifecycle, guard.member_id)
        artifact = strict_loads(guard.selection_bytes)
        before = self.observe(guard.admitted, artifact, guard.lifecycle, guard.member_id,
                              enabled=False)
        client = self.native.client(guard)
        log.append('MANAGEMENT_PORT_ENABLE_STARTED', dict(
            original_native_snapshot_digest=canonical_record_digest(before['native_snapshot'])))
        request_id = client.enable_management(before['native_snapshot'])
        log.append('MANAGEMENT_PORT_ENABLE_RETURNED', dict(native_request_id=request_id))
        after = self.observe(guard.admitted, artifact, guard.lifecycle, guard.member_id)
        guest = self.guest_reader.observe_bootstrap(guard.admitted, artifact,
                                                    guard.lifecycle, guard.member_id)
        current = self.observe(guard.admitted, artifact, guard.lifecycle, guard.member_id)
        require(current['native_snapshot'] == after['native_snapshot'],
                'The independently observed management policy changed during pinned guest reachability readback')
        return dict(status='ISOLATED_MANAGEMENT_PORT_AND_GUEST_INDEPENDENTLY_OBSERVED',
            original_native_snapshot=before, native_request_id=request_id,
            current_management=current, independent_guest=guest,
            isolated_management_reachability_verified=True, native_datapath_qualification=False)
