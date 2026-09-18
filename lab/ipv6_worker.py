"""Private pipe worker for the fixed IPv6 namespace lab, not a remote service."""
from __future__ import annotations
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import struct
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab import ipv6_fixture as f
import dns.flags
import dns.message
import dns.rcode
import dns.rdatatype
import dns.rrset

SERVERS: list[socket.socket] = []
CONNECTIONS: dict[str, socket.socket] = {}
ACCEPTED: list[socket.socket] = []
TLS = None
DATA = None
NODE = ''
INSTALLED = False
MAX_PAYLOAD = 16384


def command(argv: list[str], *, stdin: str | None = None) -> str:
    result = subprocess.run(argv, input=stdin, capture_output=True, text=True, timeout=5)
    if result.returncode:
        raise RuntimeError(f'{argv[0]} failed: {result.stderr.strip()[:1000]}')
    return result.stdout


def read_exact(sock: socket.socket, count: int) -> bytes:
    result = bytearray()
    while len(result) < count:
        part = sock.recv(count - len(result))
        if not part:
            raise ConnectionError('Socket closed before complete challenge')
        result.extend(part)
    return bytes(result)


def query(large: bool, kind: str) -> bytes:
    if type(large) is not bool or kind not in ('A', 'AAAA'):
        raise ValueError('Unsupported DNS fixture question')
    return dns.message.make_query(('large' if large else 'small') + '.fixture.invalid', kind).to_wire()


def answer(wire: bytes, tcp: bool) -> bytes:
    q = dns.message.from_wire(wire)
    if q.flags & dns.flags.QR or len(q.question) != 1 or q.answer or q.authority or q.additional:
        raise ValueError('Only an ordinary single fixture query is accepted')
    question = q.question[0]
    if question.rdclass != 1 or question.rdtype not in (dns.rdatatype.A, dns.rdatatype.AAAA):
        raise ValueError('Only IN A and AAAA are implemented')
    response = dns.message.make_response(q)
    response.flags |= dns.flags.AA
    response.flags &= ~dns.flags.RA
    if question.name.to_text() not in ('small.fixture.invalid.', 'large.fixture.invalid.'):
        response.set_rcode(dns.rcode.NXDOMAIN)
    elif question.name.to_text().startswith('large.') and not tcp:
        response.flags |= dns.flags.TC
    else:
        value = '192.0.2.42' if question.rdtype == dns.rdatatype.A else '2001:db8:100:2::10'
        response.answer.append(dns.rrset.from_text(question.name, 30, 'IN', question.rdtype, value))
    return response.to_wire(max_size=2048)


def check_answer(wire: bytes, asked: bytes) -> bool:
    q, a = dns.message.from_wire(asked), dns.message.from_wire(wire)
    if (not q.is_response(a) or a.rcode() != dns.rcode.NOERROR or not a.flags & dns.flags.AA
            or a.authority or a.additional or a.flags & dns.flags.RA):
        raise ValueError('Unmatched or unsuccessful DNS response')
    if a.flags & dns.flags.TC:
        if a.answer: raise ValueError('Truncated fixture answer must not smuggle an answer set')
        return False
    expected = '192.0.2.42' if q.question[0].rdtype == dns.rdatatype.A else '2001:db8:100:2::10'
    if len(a.answer) != 1 or a.answer[0].name != q.question[0].name or a.answer[0].rdtype != q.question[0].rdtype or a.answer[0].rdclass != 1:
        raise ValueError('Unexpected DNS answer set')
    if {record.to_text() for record in a.answer[0]} != {expected}:
        raise ValueError('Wrong fixture DNS data')
    return True


def server_socket(address: str, port: int, kind: int) -> socket.socket:
    if address != f.endpoint(DATA, NODE) or port not in (53, 443, 444):
        raise ValueError('Listener must be this node and a fixture port')
    sock = socket.socket(socket.AF_INET6, kind)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((address, port)); SERVERS.append(sock)
    return sock


def serve(address: str, port: int, dns_tcp: bool = False) -> None:
    server = server_socket(address, port, socket.SOCK_STREAM); server.listen(16)
    def client(conn):
        with conn:
            conn.settimeout(5)
            try:
                if dns_tcp:
                    size = struct.unpack('!H', read_exact(conn, 2))[0]
                    if size > 2048: return
                    result = answer(read_exact(conn, size), True)
                    conn.sendall(struct.pack('!H', len(result)) + result)
                else:
                    while data := conn.recv(MAX_PAYLOAD): conn.sendall(data)
            except Exception: pass  # A malformed local probe does not crash other controls.
    def accept():
        while True:
            try: conn, _ = server.accept()
            except OSError: break
            ACCEPTED.append(conn); threading.Thread(target=client, args=(conn,), daemon=True).start()
    threading.Thread(target=accept, daemon=True).start()


def dns_udp(address: str) -> None:
    server = server_socket(address, 53, socket.SOCK_DGRAM)
    def loop():
        while True:
            try:
                wire, peer = server.recvfrom(2048); server.sendto(answer(wire, False), peer)
            except OSError: break
            except Exception: continue
    threading.Thread(target=loop, daemon=True).start()


def probe(address: str, port: int = 443, size: int = 24, retained: str | None = None) -> dict:
    f.address(address)
    if port not in (443, 444) or type(size) is not int or not 1 <= size <= MAX_PAYLOAD:
        raise ValueError('Probe is outside the bounded fixture')
    token = secrets.token_bytes(size); sock = CONNECTIONS.get(retained) if retained else None
    succeeded = False
    try:
        if sock is None:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.settimeout(2.5 if size > 1200 else .8)
            sock.connect((address, port))
        sock.sendall(token); succeeded = read_exact(sock, size) == token
        mtu = sock.getsockopt(socket.IPPROTO_IPV6, 24)  # IPV6_MTU, Linux UAPI.
        if retained and succeeded: CONNECTIONS[retained] = sock
        return {'success': succeeded, 'family': 6, 'bytes_echoed': size if succeeded else 0,
                'path_mtu': mtu, 'observation': 'BOUNDED_IPV6_CHALLENGE'}
    except OSError as exc:
        return {'success': False, 'family': 6, 'observation': type(exc).__name__, 'errno': exc.errno}
    finally:
        if sock and (not retained or not succeeded):
            sock.close()
            if retained: CONNECTIONS.pop(retained, None)


def dns_probe(address: str, transport: str, kind: str = 'AAAA') -> dict:
    f.address(address)
    if transport not in ('udp', 'tcp', 'fallback'): raise ValueError('Unknown DNS transport')
    wire = query(transport == 'fallback', kind); used = []
    try:
        if transport in ('udp', 'fallback'):
            with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as sock:
                sock.settimeout(.8); sock.connect((address, 53)); sock.send(wire)
                received = sock.recv(2048); used.append('udp')
            if check_answer(received, wire): return {'success': True, 'family': 6, 'query_type': kind, 'transports': used}
            if transport != 'fallback': return {'success': False, 'observation': 'TRUNCATED', 'transports': used}
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as sock:
            sock.settimeout(.8); sock.connect((address, 53)); sock.sendall(struct.pack('!H', len(wire)) + wire)
            size = struct.unpack('!H', read_exact(sock, 2))[0]
            if size > 2048: raise ValueError('Oversized answer')
            received = read_exact(sock, size); used.append('tcp')
        return {'success': check_answer(received, wire), 'family': 6, 'query_type': kind, 'transports': used}
    except (OSError, ValueError) as exc:
        return {'success': False, 'family': 6, 'transports': used, 'observation': type(exc).__name__}


def configure_forwarding(enabled: bool) -> dict:
    f.namespace_guard()
    if type(enabled) is not bool or (enabled and DATA['nodes'][NODE]['kind'] not in f.ROUTERS):
        raise ValueError('Only fixture router nodes can forward')
    if enabled and not INSTALLED: raise ValueError('Install quarantine/router policy before forwarding')
    names = [f.safe_interface(name) for _, name in socket.if_nameindex() if name != 'lo']
    values = {}
    # These are netns-local settings. Do not remount /proc or change host confinement
    # when a controller exposes read-only sysctls; report a runtime blocker instead.
    for name in ['all', 'default', *names]:
        for key, value in [('forwarding', int(enabled)), ('accept_ra', 0), ('autoconf', 0),
                           ('accept_redirects', 0), ('router_solicitations', 0), ('use_tempaddr', 0)]:
            path = Path(f'/proc/sys/net/ipv6/conf/{name}/{key}')
            path.write_text(str(value))
            if path.read_text().strip() != str(value): raise RuntimeError('Sysctl readback differs')
            values[f'{name}/{key}'] = value
    return values


def action(request: dict) -> dict:
    global TLS, INSTALLED
    op = request['op']; f.namespace_guard()
    if op == 'ip': return {'stdout': command(['ip', *request['args']])}
    if op == 'configure': return configure_forwarding(request['enabled'])
    if op == 'forward-status':
        return {'forwarding': Path('/proc/sys/net/ipv6/conf/all/forwarding').read_text().strip()}
    if op == 'filter':
        rule = f.policy(DATA, NODE, request['mode'], replace=INSTALLED,
                        contain=request.get('contain', False), block_ptb=request.get('block_ptb', False))
        command(['nft', '-f', '-'], stdin=rule); INSTALLED = True
        return {'installed': True, 'mode': request['mode'], 'table': f.TABLE}
    if op == 'counters':
        return f.counter_values(json.loads(command(['nft', '-j', 'list', 'table', 'ip6', f.TABLE])))
    if op == 'serve':
        serve(f.endpoint(DATA, NODE), 443); serve(f.endpoint(DATA, NODE), 444)
        if NODE == 'resolver': serve(f.endpoint(DATA, NODE), 53, True); dns_udp(f.endpoint(DATA, NODE))
        return {'listening': True}
    if op == 'probe': return probe(request['address'], request.get('port', 443), request.get('size', 24), request.get('retained'))
    if op == 'dns': return dns_probe(request['address'], request['transport'], request.get('kind', 'AAAA'))
    if op == 'advertise-once':
        # One deliberately unwanted RA, private test link only. No outside interface.
        name = f.safe_interface(request['interface']); index = socket.if_nametoindex(name)
        records = json.loads(command(['ip', '-6', '-j', 'addr', 'show', 'dev', name]))
        local = next(a['local'] for r in records for a in r['addr_info'] if a['scope'] == 'link')
        with socket.socket(socket.AF_INET6, socket.SOCK_RAW, socket.IPPROTO_ICMPV6) as sock:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF, index)
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, 255)
            sock.bind((local, 0, 0, index))
            sock.sendto(struct.pack('!BBHBBHII', 134, 0, 0, 64, 0, 1800, 0, 0), ('ff02::1', 0, 0, index))
        return {'sent': 1, 'interface': name, 'message_type': 134}
    if op == 'mtls-start':
        from lab.mtls_fixture import Service
        address = f.endpoint(DATA, NODE)
        for sock in SERVERS + ACCEPTED:
            try:
                if sock.getsockname()[1] == 443:
                    try: sock.shutdown(socket.SHUT_RDWR)
                    except OSError: pass
                    sock.close()
            except OSError: pass
        TLS = Service(address, 443, request['certificate'], request['key'], request['ca'], request['allowed'])
        return {'listening': True}
    if op == 'mtls-probe':
        from lab.mtls_fixture import probe as tls_probe
        return tls_probe(f.address(request['address']), 443, request['ca'], request.get('certificate'), request.get('key'),
                         request.get('hostname', 'data-01.fixture.invalid'), request.get('retained'))
    if op == 'mtls-stats': return TLS.stats()
    if op == 'mtls-grants': return TLS.grants(request['allowed'])
    if op == 'stop': return {'stopping': True}
    raise ValueError('Unknown private fixture operation')


def main() -> int:
    global DATA, NODE
    f.namespace_guard(); DATA = f.load_fixture()
    if len(sys.argv) != 2 or sys.argv[1] not in DATA['nodes']: raise ValueError('Exact fixture node required')
    NODE = sys.argv[1]
    if {name for _, name in socket.if_nameindex()} != {'lo'}: raise RuntimeError('Worker namespace is not empty')
    print(json.dumps({'ready': True, 'namespace': os.readlink('/proc/self/ns/net')}), flush=True)
    try:
        for line in sys.stdin:
            try:
                if len(line) > 16384: raise ValueError('Oversized private message')
                response = {'ok': True, 'result': action(json.loads(line))}
            except Exception as exc: response = {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}
            print(json.dumps(response), flush=True)
            if response.get('result', {}).get('stopping'): break
    finally:
        if TLS: TLS.close()
        for sock in list(CONNECTIONS.values()) + SERVERS + ACCEPTED: sock.close()
    return 0

if __name__ == '__main__': raise SystemExit(main())
