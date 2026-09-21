#!/usr/bin/env python3
"""Apply an expiring, exact-flow policy on an adopted provider-owned Linux edge.

One table, one immutable interface boundary, one writer ledger. No route, NAT,
link, namespace, host-input or global-ruleset changes are performed.
"""
import argparse
from datetime import datetime
import fcntl
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.run_files import (current_window, digest, encoded, load_private, new_directory,
                             private_path, replace_private, require, utcnow, write_new, OperatorError)


def validate(spec):
    require(set(spec) == {'format', 'scope', 'machine_id', 'network_namespace_inode', 'nft_sha256',
            'operation_id', 'generation', 'interfaces', 'owned_interfaces', 'flows', 'max_lease_seconds'},
            'Invalid security-edge specification')
    require(spec['format'] == 'hosting-nft-edge/1', 'Unknown edge specification')
    require(set(spec['scope']) == {'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key'},
            'Complete edge scope required')
    for value in [*spec['scope'].values(), spec['operation_id']]:
        require(isinstance(value, str) and re.fullmatch(r'[a-z][a-z0-9-]{1,40}', value), 'Stable edge identity required')
    require(spec['scope']['platform'] in {'nutanix', 'vmware', 'openstack'}, 'Unknown platform')
    require(re.fullmatch('[0-9a-f]{32}', spec['machine_id']) and re.fullmatch('[0-9a-f]{64}', spec['nft_sha256']),
            'Observed edge machine and approved executable required')
    for key in ('network_namespace_inode', 'generation'):
        require(type(spec[key]) is int and spec[key] > 0, 'Positive native namespace/generation required')
    require(type(spec['max_lease_seconds']) is int and 1 <= spec['max_lease_seconds'] <= 3600, 'Bounded policy lease required')
    interfaces = spec['interfaces']
    require(isinstance(interfaces, dict) and 2 <= len(interfaces) <= 8, 'Explicit edge interfaces required')
    networks = {}
    for name, prefixes in interfaces.items():
        require(re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,14}', name) and name != 'lo', 'Exact interface name required')
        require(isinstance(prefixes, list) and 1 <= len(prefixes) <= 16, 'Bounded interface address scopes required')
        networks[name] = [ipaddress.ip_network(p, strict=True) for p in prefixes]
        require(all(n.version == 4 and n.prefixlen >= 8 for n in networks[name]), 'Explicit IPv4 route scopes required')
    owned = spec['owned_interfaces']
    require(isinstance(owned, list) and owned and len(set(owned)) == len(owned) and set(owned) <= set(interfaces),
            'Exact provider-owned domain interfaces required')
    require(isinstance(spec['flows'], list) and len(spec['flows']) <= 256, 'Bounded flow list required')
    seen = set()
    for flow in spec['flows']:
        require(set(flow) == {'ingress', 'egress', 'source', 'destination', 'protocol', 'port', 'phase'},
                'Exact endpoint/protocol flow required')
        require(flow['ingress'] in interfaces and flow['egress'] in interfaces and flow['ingress'] != flow['egress']
                and ({flow['ingress'], flow['egress']} & set(owned)), 'Flow is outside the owned boundary')
        for key, interface in [('source', flow['ingress']), ('destination', flow['egress'])]:
            address = ipaddress.ip_address(flow[key])
            require(address.version == 4 and str(address) == flow[key] and not (address.is_multicast
                    or address.is_unspecified or address.is_loopback or address.is_link_local)
                    and any(address in n for n in networks[interface]), 'Endpoint differs from its accepted interface scope')
        require(flow['protocol'] in {'tcp', 'udp'} and type(flow['port']) is int and 1 <= flow['port'] <= 65535
                and flow['phase'] in {'bootstrap', 'active'}, 'Only exact scoped TCP/UDP services are supported')
        key = tuple(flow[k] for k in ('ingress', 'egress', 'source', 'destination', 'protocol', 'port'))
        require(key not in seen, 'Duplicate flow authority')
        seen.add(key)
    scope_hash = digest(encoded(spec['scope']))
    return 'hosting_' + scope_hash[:20], scope_hash


def render(spec, mode, lease_seconds, *, exists=False):
    table, scope_hash = validate(spec)
    require(mode in {'bootstrap', 'active', 'withdraw'} and type(lease_seconds) is int
            and 1 <= lease_seconds <= spec['max_lease_seconds'], 'Invalid edge mode/lease')
    flows = [] if mode == 'withdraw' else [x for x in spec['flows'] if mode == 'active' or x['phase'] == 'bootstrap']
    # Native nft comments are bounded to 128 bytes. Full input digests remain
    # in the private receipt; ownership retains the complete scope digest.
    marker = 'hosting:' + scope_hash + ':' + digest(encoded(spec))[:16] + ':' + mode
    lines = ([f'delete table inet {table}'] if exists else []) + [f'table inet {table} {{', f' comment "{marker}"']
    for i, flow in enumerate(flows):
        lines += [f' set f{i} {{', '  type ipv4_addr . ipv4_addr . inet_service', '  flags timeout',
                  f'  timeout {lease_seconds}s',
                  f'  elements = {{ {flow["source"]} . {flow["destination"]} . {flow["port"]} timeout {lease_seconds}s }}', ' }']
    lines += [' chain forward {', '  type filter hook forward priority -100; policy accept;']
    for i, flow in enumerate(flows):
        protocol = flow['protocol']
        forward = f'iifname "{flow["ingress"]}" oifname "{flow["egress"]}"'
        reverse = f'iifname "{flow["egress"]}" oifname "{flow["ingress"]}"'
        lines += [f'  {forward} ip saddr . ip daddr . {protocol} dport @f{i} ct state {{ new, established }} counter accept',
                  f'  {reverse} ip daddr . ip saddr . {protocol} sport @f{i} ct state established counter accept',
                  # ICMP errors for an allowed tracked tuple expire with that tuple.
                  f'  {reverse} ip protocol icmp ct state related ct original ip saddr . ct original ip daddr . ct original proto-dst @f{i} counter accept']
    for interface in spec['owned_interfaces']:
        for direction in ('iifname', 'oifname'):
            lines += [f'  {direction} "{interface}" limit rate 10/second log prefix "{table[:28]} "',
                      f'  {direction} "{interface}" counter drop']
    return '\n'.join(lines + [' }', '}', ''])


def normalized(value):
    if isinstance(value, dict):
        return {k: normalized(v) for k, v in value.items() if k not in {'handle', 'packets', 'bytes', 'expires', 'metainfo'}}
    if isinstance(value, list):
        return [normalized(v) for v in value if not (isinstance(v, dict) and 'metainfo' in v)]
    return value


class Kernel:
    def __init__(self, binary, operation):
        self.binary, self.operation, self.counter = str(binary), Path(operation), 0

    def command(self, arguments):
        self.counter += 1
        output = self.operation / f'kernel-{self.counter:02d}.json'
        error = self.operation / f'kernel-{self.counter:02d}.log'
        with os.fdopen(os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as out, \
             os.fdopen(os.open(error, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as err:
            result = subprocess.run([self.binary, *arguments], stdin=subprocess.DEVNULL,
                stdout=out, stderr=err, env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C'}, timeout=10, umask=0o077)
        require(result.returncode == 0, 'Native firewall operation failed; inspect private logs')
        return output.read_text()

    def inspect(self, spec):
        table, scope_hash = validate(spec)
        tables = json.loads(self.command(['-j', 'list', 'tables']))
        exists = any(x.get('table', {}).get('family') == 'inet' and x['table'].get('name') == table for x in tables['nftables'])
        if not exists:
            return None, digest(encoded(None))
        state = json.loads(self.command(['-j', 'list', 'table', 'inet', table]))
        header = [x['table'] for x in state['nftables'] if 'table' in x]
        require(len(header) == 1 and header[0].get('comment', '').startswith('hosting:' + scope_hash + ':'),
                'Existing firewall table is not owned by this scope')
        return state, digest(encoded(normalized(state)))


def completed_history(ledger, boundary):
    """Containment cannot make an older uncertain native write disappear."""
    starts=list(ledger.glob('*.started.json')); results=list(ledger.glob('*.result.json'))
    identities={path.name.removesuffix('.started.json') for path in starts}
    require(identities=={path.name.removesuffix('.result.json') for path in results},
            'Unresolved native edge history requires reconciliation before opening flows')
    completed=[]
    for path in starts:
        attempt=load_private(path)
        require(set(attempt)=={'status','generation','operation_id','mode','boundary_sha256','spec_sha256','started_at'}
                and attempt['status']=='OUTCOME_UNKNOWN' and type(attempt['generation']) is int
                and attempt['generation']>0 and attempt['mode'] in {'withdraw','bootstrap','active'}
                and attempt['boundary_sha256']==boundary,'Invalid native edge attempt history')
        identity=digest(encoded([attempt['operation_id'],attempt['generation'],attempt['mode']]))
        require(path.name==identity+'.started.json','Edge attempt identity changed')
        result=load_private(ledger/(identity+'.result.json'))
        require(set(result)==set(attempt)|{'observed_state_sha256','completed_at','lease_seconds','production_qualified'}
                and result['status']=='APPLIED_EXPIRING_POLICY_NOT_QUALIFIED'
                and all(result[key]==value and type(result[key]) is type(value) for key,value in attempt.items() if key!='status')
                and result['production_qualified'] is False
                and re.fullmatch('[0-9a-f]{64}',result['observed_state_sha256'])
                and type(result['lease_seconds']) is int and result['lease_seconds']>0,
                'Native edge completion binding changed')
        start=datetime.fromisoformat(attempt['started_at']); end=datetime.fromisoformat(result['completed_at'])
        require(start.tzinfo is not None and end.tzinfo is not None and start<=end<=utcnow(),
                'Native edge completion chronology changed')
        completed.append(result)
    head=ledger/'head.json'
    if not completed:
        require(not head.exists(),'Native edge head has no immutable history')
        return 0
    completed.sort(key=lambda item:datetime.fromisoformat(item['completed_at']))
    require(head.exists() and load_private(head)==completed[-1],'Native edge head differs from immutable completion')
    for previous,current in zip(completed,completed[1:]):
        require(datetime.fromisoformat(previous['completed_at'])<=datetime.fromisoformat(current['started_at']),
                'Native edge execution history overlaps')
    return max(item['generation'] for item in completed)


def apply(spec, mode, authority, kernel, ledger, operation):
    table, scope_hash = validate(spec)
    require(set(authority) == {'spec_sha256', 'mode', 'expected_state_sha256', 'valid_from', 'valid_until',
                              'change_ref', 'boundary_acceptance_ref', 'readiness_ref'}, 'Invalid edge authority')
    require(authority['spec_sha256'] == digest(encoded(spec)) and authority['mode'] == mode, 'Edge authority differs')
    for key in ('change_ref', 'boundary_acceptance_ref', 'readiness_ref'):
        require(re.fullmatch(r'[A-Za-z0-9:._/-]{3,200}', authority[key]), 'Current boundary/readiness handoff required')
    current_window(authority)
    private_path(ledger, directory=True)
    ledger = Path(ledger) / scope_hash
    ledger.mkdir(mode=0o700, exist_ok=True)
    private_path(ledger, directory=True)
    fd = os.open(ledger / 'writer.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        private_path(ledger / 'writer.lock')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        boundary = digest(encoded([spec['interfaces'], spec['owned_interfaces'], spec['machine_id'], spec['network_namespace_inode']]))
        if mode != 'withdraw':
            require(spec['generation']>completed_history(ledger,boundary),'Native edge generation must exceed its full history')
        head_path = ledger / 'head.json'
        if head_path.exists():
            head = load_private(head_path)
            require(head['boundary_sha256'] == boundary, 'Boundary migration requires a separate native design')
            require(mode == 'withdraw' or (head['status'] == 'APPLIED_EXPIRING_POLICY_NOT_QUALIFIED'
                    and spec['generation'] > head['generation']), 'Prior outcome unknown or generation already attempted')
        current, observed_hash = kernel.inspect(spec)
        require(observed_hash == authority['expected_state_sha256'], 'Native policy changed since exact review')
        require(current is not None or mode == 'withdraw', 'Install and verify the deny boundary before opening any flow')
        seconds = (datetime.fromisoformat(authority['valid_until'].replace('Z', '+00:00')) - utcnow()).total_seconds()
        # Reserve the bounded native-command interval; the kernel expires allows
        # even if the controller is killed immediately after installation.
        lease = min(spec['max_lease_seconds'], math.floor(seconds) - 40)
        require(lease >= 1, 'Insufficient remaining authority for a native transaction')
        path = Path(operation) / 'candidate.nft'
        write_new(path, render(spec, mode, lease, exists=current is not None).encode())
        kernel.command(['--check', '--file', str(path)])
        _, observed_hash = kernel.inspect(spec)
        require(observed_hash == authority['expected_state_sha256'], 'Policy changed during candidate validation')
        current_window(authority)
        remaining = (datetime.fromisoformat(authority['valid_until'].replace('Z', '+00:00')) - utcnow()).total_seconds()
        require(remaining >= lease + 10, 'Prepare a new bounded policy after delayed validation')
        attempt = {'status': 'OUTCOME_UNKNOWN', 'generation': spec['generation'], 'operation_id': spec['operation_id'],
                   'mode': mode, 'boundary_sha256': boundary, 'spec_sha256': digest(encoded(spec)), 'started_at': utcnow().isoformat()}
        identity = digest(encoded([spec['operation_id'], spec['generation'], mode]))
        write_new(ledger / (identity + '.started.json'), encoded(attempt))
        replace_private(head_path, encoded(attempt))
        kernel.command(['--file', str(path)])
        after, after_hash = kernel.inspect(spec)
        require(after is not None, 'Applied edge table not observed')
        result = attempt | {'status': 'APPLIED_EXPIRING_POLICY_NOT_QUALIFIED', 'observed_state_sha256': after_hash,
                            'completed_at': utcnow().isoformat(), 'lease_seconds': lease, 'production_qualified': False}
        write_new(ledger / (identity + '.result.json'), encoded(result))
        replace_private(head_path, encoded(result))
        write_new(Path(operation) / 'receipt.json', encoded(result))
        return result
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['inspect', 'apply'])
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--nft', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=['bootstrap', 'active', 'withdraw'])
    parser.add_argument('--authority', type=Path)
    parser.add_argument('--ledger', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    try:
        spec = load_private(args.spec)
        validate(spec)
        if not args.execute:
            print('{"status":"VALIDATED_NO_NATIVE_CONTACT"}')
            return 0
        require(Path('/etc/machine-id').read_text().strip() == spec['machine_id']
                and os.stat('/proc/self/ns/net').st_ino == spec['network_namespace_inode'], 'Wrong native edge machine or namespace')
        require(hashlib.sha256(args.nft.read_bytes()).hexdigest() == spec['nft_sha256'], 'Native firewall executable changed')
        operation = new_directory(args.output, ROOT)
        kernel = Kernel(args.nft.resolve(strict=True), operation)
        if args.action == 'inspect':
            state, state_hash = kernel.inspect(spec)
            write_new(operation / 'inspection.json', encoded({'state': state, 'state_sha256': state_hash}))
            result = {'status': 'OBSERVED_NOT_QUALIFIED', 'state_sha256': state_hash}
        else:
            require(args.authority and args.ledger and args.mode, 'Exact mutation inputs required')
            result = apply(spec, args.mode, load_private(args.authority), kernel, args.ledger, operation)
        print(json.dumps({k: v for k, v in result.items() if k in {'status', 'state_sha256', 'lease_seconds'}}))
        return 0
    except OperatorError as exc:
        print(json.dumps({'status': 'STOPPED', 'reason': str(exc)}))
        return 2
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print('{"status":"STOPPED","reason":"Inspect the private edge ledger; lease expiry preserves the drop boundary"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
