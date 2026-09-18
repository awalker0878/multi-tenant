"""Fixed IPv6-only WD14 lab policy; no arbitrary inventory or native target input.

The reference is reused without adding guessed service ports or IPv6 provider claims.
This is a Linux test instrument, not a supported production security edge.
"""
from __future__ import annotations
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'examples/wd14-routing.json'
FIXTURE_SHA256 = '8b7fd1df0ce826b77bdae8360ecff6235999949b22f8eb8dabf9f3a2c1477cc9'
DOCUMENTATION = ipaddress.ip_network('2001:db8::/32')
TABLE = 'hosting_v6_fixture'
ROUTERS = {'native', 'edge', 'service_edge'}
COUNTERS = ('nd', 'mld', 'control_drop', 'input_drop', 'forward_drop', 'new_allow',
            'established', 'related_error', 'containment', 'ptb_block', 'native_forward')


def address(value: str) -> str:
    ip = ipaddress.ip_address(value)
    if ip.version != 6 or ip not in DOCUMENTATION:
        raise ValueError('Only the fixed IPv6 documentation-address scope is accepted')
    return str(ip)


def load_fixture() -> dict:
    raw = FIXTURE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FIXTURE_SHA256:
        raise ValueError('The fixed WD14 source changed; review and requalify the lab profile')
    data = json.loads(raw)
    for node in data['nodes'].values():
        for item in node['interfaces']:
            ip = ipaddress.ip_interface(item['address'])
            if ip.version == 6:
                address(str(ip.ip))
        for route in node['routes']:
            network = ipaddress.ip_network(route['destination'])
            if network.version == 6:
                address(route['next_hop'])
                if network.prefixlen and not network.subnet_of(DOCUMENTATION):
                    raise ValueError('Route escapes the fixed documentation scope')
    return data


def interfaces(data: dict, node: str) -> list[dict]:
    return [i for i in data['nodes'][node]['interfaces'] if ipaddress.ip_interface(i['address']).version == 6]


def routes(data: dict, node: str) -> list[dict]:
    return [r for r in data['nodes'][node]['routes'] if ipaddress.ip_network(r['destination']).version == 6]


def endpoint(data: dict, node: str) -> str:
    return address(str(ipaddress.ip_interface(interfaces(data, node)[0]['address']).ip))


def namespace_guard() -> str:
    own = os.readlink('/proc/self/ns/net')
    original = os.environ.get('HOSTING_LAB_ORIGINAL_NETNS')
    master = os.environ.get('HOSTING_LAB_MASTER_NETNS')
    if not original or not master or own in (original, master):
        raise RuntimeError('An independent disposable worker network namespace is required')
    return own


def policy(data: dict, node: str, mode: str, *, replace: bool = False,
           contain: bool = False, block_ptb: bool = False) -> str:
    if any(type(value) is not bool for value in (replace, contain, block_ptb)):
        raise ValueError('Policy switches must be explicit booleans')
    if node not in data['nodes'] or mode not in ('host', 'router', 'edge', 'quarantine'):
        raise ValueError('Unknown fixture node or policy mode')
    kind = data['nodes'][node]['kind']
    permitted = {'native': {'router'}, 'edge': {'edge', 'quarantine'},
                 'service_edge': {'edge', 'quarantine'}, 'workload': {'host'}, 'service': {'host'}}
    if mode not in permitted[kind] or (contain and node != 'EC-01') or (block_ptb and node != 'NG-D01O'):
        raise ValueError('Policy variation is outside the fixed experiment')
    lines = [f'delete table ip6 {TABLE}'] if replace else []
    lines += [f'table ip6 {TABLE} {{']
    lines += [f' counter {name} {{ }}' for name in COUNTERS]
    lines += [' chain input { type filter hook input priority 0; policy drop;',
              '  iifname "lo" accept',
              '  icmpv6 type { 134, 137 } counter name control_drop drop',
              '  ip6 hoplimit 255 icmpv6 type { 135, 136 } counter name nd accept',
              '  ip6 saddr { fe80::/10, ::/128 } ip6 hoplimit 1 icmpv6 type { 130, 131, 132, 143 } counter name mld accept',
              '  ct state invalid counter name input_drop drop',
              '  icmpv6 type { 1, 2, 3, 4 } ct state related counter name related_error accept',
              '  ct state established counter name established accept']
    if mode == 'host':
        lines += ['  tcp dport { 443, 444 } ct state new accept']
        if node == 'resolver':
            lines += ['  tcp dport 53 ct state new accept', '  udp dport 53 ct state new accept']
    lines += ['  counter name input_drop drop', ' }',
              ' chain forward { type filter hook forward priority 0; policy drop;']
    if contain:
        source, target = endpoint(data, 'processor-01'), endpoint(data, 'data-01')
        lines += [f'  ip6 saddr {source} ip6 daddr {target} counter name containment drop',
                  f'  ip6 saddr {target} ip6 daddr {source} counter name containment drop']
    if block_ptb:
        lines += ['  icmpv6 type 2 counter name ptb_block drop']
    if mode == 'router':
        lines += ['  counter name native_forward accept']
    elif mode == 'edge':
        lines += ['  ct state invalid counter name forward_drop drop',
                  '  icmpv6 type { 1, 2, 3, 4 } ct state related counter name related_error accept',
                  '  ct state established counter name established accept']
        for flow in data['approved_flows']:
            if node in flow['via']:
                source, target = endpoint(data, flow['source']), endpoint(data, flow['destination'])
                if flow['protocol'] not in ('tcp', 'udp') or flow['port'] not in (53, 443):
                    raise ValueError('Unsupported fixture flow')
                lines += [f"  ip6 saddr {source} ip6 daddr {target} {flow['protocol']} dport {flow['port']} ct state new counter name new_allow accept"]
    lines += ['  counter name forward_drop drop', ' }',
              ' chain output { type filter hook output priority 0; policy accept; }', '}']
    return '\n'.join(lines) + '\n'


def counter_values(raw: dict) -> dict[str, int]:
    result = {}
    for entry in raw.get('nftables', []):
        c = entry.get('counter', {})
        if c.get('table') == TABLE and c.get('family') == 'ip6':
            name = c.get('name'); count = c.get('packets')
            if name in result or name not in COUNTERS or type(count) is not int or count < 0:
                raise ValueError('Unexpected named counter')
            result[name] = count
    if set(result) != set(COUNTERS):
        raise ValueError('Incomplete fixture counter coverage')
    return result


def safe_interface(name: str) -> str:
    if not re.fullmatch(r'v[0-9]{1,3}b', name):
        raise ValueError('Only lab-created veth interfaces are accepted')
    return name


def ready_addresses(data: dict, node: str, rows: list[dict]) -> bool:
    """Require every exact static address and completed DAD, not a vacuous empty read."""
    expected = {str(ipaddress.ip_interface(i['address']).ip) for i in interfaces(data, node)}
    observed = set()
    for row in rows:
        for item in row.get('addr_info', []):
            if item.get('family') != 'inet6':
                continue
            flags = item.get('flags', [])
            if any(item.get(key) is True or key in flags for key in ('tentative', 'dadfailed')):
                return False
            local = str(ipaddress.ip_address(item['local']))
            if not ipaddress.ip_address(local).is_link_local and local != '::1':
                observed.add(local)
    return bool(expected) and observed == expected


def no_global_ipv4(rows: list[dict]) -> bool:
    return not any(a.get('family') == 'inet' and a.get('scope') == 'global'
                   for row in rows for a in row.get('addr_info', []))
