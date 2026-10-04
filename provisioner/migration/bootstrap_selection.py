"""Exact existing-port management selection; no inferred or reusable names."""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

from provisioner.execution.run_files import require

UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
RULE_FIELDS = {'id', 'project_id', 'security_group_id', 'direction', 'ethertype', 'protocol',
               'port_range_min', 'port_range_max', 'remote_ip_prefix', 'remote_group_id',
               'remote_address_group_id'}


def unicast(value):
    require(type(value) is str, 'One exact management IPv4 address is required')
    address = ipaddress.IPv4Address(value)
    require(str(address) == value and not (address.is_unspecified or address.is_multicast
            or address.is_loopback or address.is_link_local or address.is_reserved),
            'One canonical unicast management address is required')
    return address


def validate_policy_selection(selected, scope, management, health_port):
    """A sole pre-existing stateful group for the bounded application listener."""
    require(type(health_port) is int and 1024 <= health_port <= 65535
        and type(selected) is dict and set(selected) == {'security_group_id', 'security_group_rules'}
        and type(selected['security_group_id']) is str and UUID.fullmatch(selected['security_group_id'])
        and selected['security_group_id'] not in {management[key] for key in
            ('port_id', 'network_id', 'subnet_id', 'security_group_id')},
        'Production policy needs one exact distinct existing native security group')
    rules = selected['security_group_rules']
    require(type(rules) is list and 1 <= len(rules) <= 32, 'Every bounded production policy rule must be selected')
    known = {rule['id'] for rule in management['security_group_rules']}
    ingress = 0
    for rule in rules:
        require(type(rule) is dict and set(rule) == RULE_FIELDS
            and type(rule['id']) is str and UUID.fullmatch(rule['id']) and rule['id'] not in known
            and rule['project_id'] == scope.native_scope_id
            and rule['security_group_id'] == selected['security_group_id']
            and rule['direction'] in {'ingress', 'egress'} and rule['ethertype'] == 'IPv4'
            and rule['protocol'] in {'tcp', 'udp'}
            and type(rule['port_range_min']) is int and type(rule['port_range_max']) is int
            and 1 <= rule['port_range_min'] == rule['port_range_max'] <= 65535
            and rule['remote_group_id'] is None and rule['remote_address_group_id'] is None
            and type(rule['remote_ip_prefix']) is str,
            'Production policy requires exact native rule IDs, single ports and explicit service peers')
        known.add(rule['id'])
        remote = ipaddress.IPv4Network(rule['remote_ip_prefix'], strict=True)
        require(str(remote) == rule['remote_ip_prefix'] and remote.prefixlen == 32,
            'Production service peers must each be one approved IPv4 host')
        unicast(str(remote.network_address))
        if rule['direction'] == 'ingress':
            require(rule['protocol'] == 'tcp' and rule['port_range_min'] == health_port,
                'This application policy admits only its selected useful-service listener')
            ingress += 1
    require(ingress > 0, 'Production policy needs a selected useful-service client')


def validate_management_selection(selected, scope):
    require(type(selected) is dict and set(selected) == {'network_endpoint', 'port_id', 'network_id',
            'subnet_id', 'ipv4_address', 'mac_address', 'security_group_id', 'security_group_rules',
            'worker_ipv4_address', 'ssh_host_key_sha256', 'mtu', 'subnet'},
            'A complete immutable isolated management-port selection is required')
    endpoint = urlsplit(selected['network_endpoint'])
    require(endpoint.scheme == 'https' and endpoint.hostname and endpoint.path == '/v2.0'
            and not endpoint.username and not endpoint.password and not endpoint.query and not endpoint.fragment,
            'The commissioned Neutron v2 HTTPS endpoint is required')
    require(all(type(selected[key]) is str and UUID.fullmatch(selected[key]) for key in
            ('port_id', 'network_id', 'subnet_id', 'security_group_id'))
            and len({selected[key] for key in ('port_id', 'network_id', 'subnet_id', 'security_group_id')}) == 4
            and type(selected['mac_address']) is str
            and re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', selected['mac_address'])
            and not int(selected['mac_address'][:2], 16) & 1
            and selected['mac_address'] != '00:00:00:00:00:00'
            and type(selected['ssh_host_key_sha256']) is str
            and re.fullmatch('[0-9a-f]{64}', selected['ssh_host_key_sha256'])
            and type(selected['mtu']) is int and 1280 <= selected['mtu'] <= 9000,
            'Exact existing native management IDs, host-key pin and MTU are required')
    address, worker = unicast(selected['ipv4_address']), unicast(selected['worker_ipv4_address'])
    require(address != worker, 'The enrolled management worker cannot be the target guest')
    subnet = selected['subnet']
    require(type(subnet) is dict and set(subnet) ==
            {'cidr', 'gateway_ip', 'enable_dhcp', 'dns_nameservers', 'host_routes'}
            and type(subnet['cidr']) is str and type(subnet['enable_dhcp']) is bool
            and type(subnet['dns_nameservers']) is list and len(subnet['dns_nameservers']) <= 3
            and len(set(subnet['dns_nameservers'])) == len(subnet['dns_nameservers'])
            and subnet['host_routes'] == [], 'Exact bounded management subnet and service routes are required')
    network = ipaddress.IPv4Network(subnet['cidr'], strict=True)
    require(str(network) == subnet['cidr'] and address in network and address not in
            {network.network_address, network.broadcast_address}, 'The target address escapes its selected subnet')
    if subnet['gateway_ip'] is not None:
        gateway = unicast(subnet['gateway_ip'])
        require(gateway in network and gateway not in {address, network.network_address, network.broadcast_address},
                'The selected management gateway is not a distinct usable subnet address')
    for value in subnet['dns_nameservers']:
        unicast(value)
    rules = selected['security_group_rules']
    require(type(rules) is list and 1 <= len(rules) <= 32
            and all(type(rule) is dict and set(rule) == RULE_FIELDS for rule in rules),
            'Every native management security rule must be explicitly selected')
    known, ingress = set(), 0
    for rule in rules:
        require(type(rule['id']) is str and UUID.fullmatch(rule['id']) and rule['id'] not in known
                and rule['project_id'] == scope.native_scope_id
                and rule['security_group_id'] == selected['security_group_id']
                and rule['direction'] in {'ingress', 'egress'} and rule['ethertype'] == 'IPv4'
                and rule['protocol'] in {'tcp', 'udp'}
                and type(rule['port_range_min']) is int and type(rule['port_range_max']) is int
                and 1 <= rule['port_range_min'] == rule['port_range_max'] <= 65535
                and rule['remote_group_id'] is None and rule['remote_address_group_id'] is None
                and type(rule['remote_ip_prefix']) is str,
                'Management rules require exact ports and hosts without additive group or address-pair bypasses')
        known.add(rule['id'])
        remote = ipaddress.IPv4Network(rule['remote_ip_prefix'], strict=True)
        require(str(remote) == rule['remote_ip_prefix'] and remote.prefixlen == 32,
                'Every management service peer must be one approved IPv4 host')
        unicast(str(remote.network_address))
        if rule['direction'] == 'ingress':
            require(rule['protocol'] == 'tcp' and rule['port_range_min'] == 22
                    and remote.network_address == worker,
                    'Only the exact management worker may initiate SSH before traffic admission')
            ingress += 1
    require(ingress == 1, 'The isolated management policy needs exactly one selected worker SSH ingress rule')
