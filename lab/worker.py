"""Private worker for the fixed disposable packet fixture; not a management service.

Started only by run_namespace_lab.py inside a fresh network namespace. JSON lines
are local pipe messages, not a remotely exposed API. All servers bind fixture IPs.
"""
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
from typing import Any

CONNECTIONS: dict[str, socket.socket] = {}
SERVERS: list[socket.socket] = []
PLAIN_CONNECTIONS: list[socket.socket] = []
TLS_SERVICE = None
TIMEOUT = 0.65


def fixture_ip(value: str) -> str:
    ip = ipaddress.ip_address(value)
    if ip.version != 4 or not any(ip in ipaddress.ip_network(n) for n in
                                 ('192.0.2.0/24', '198.51.100.0/24', '203.0.113.0/24')):
        raise ValueError('Only IPv4 documentation fixture addresses are accepted')
    return str(ip)


def recv_exact(sock: socket.socket, n: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < n:
        data = sock.recv(n - len(chunks))
        if not data:
            raise ConnectionError('Unexpected end of stream')
        chunks.extend(data)
    return bytes(chunks)


def dns_question(name: str, transaction: int) -> bytes:
    labels = name.encode('ascii').split(b'.')
    if any(not label or len(label) > 63 for label in labels):
        raise ValueError('Invalid fixture DNS name')
    return struct.pack('!6H', transaction, 0x0100, 1, 0, 0, 0) + b''.join(
        bytes([len(x)]) + x for x in labels) + b'\0\0\x01\0\x01'


def dns_answer(query: bytes, tcp: bool) -> bytes:
    if len(query) < 17:
        raise ValueError('Truncated DNS request')
    qid, _, questions, _, _, _ = struct.unpack('!6H', query[:12])
    if questions != 1:
        raise ValueError('Only one fixture question supported')
    pos, labels = 12, []
    while True:
        length = query[pos]
        pos += 1
        if length == 0:
            break
        if length > 63 or pos + length >= len(query):
            raise ValueError('Unsupported compressed or truncated question')
        labels.append(query[pos:pos + length])
        pos += length
    if pos + 4 != len(query) or query[pos:pos + 4] != b'\0\x01\0\x01':
        raise ValueError('Only one IN A fixture query supported')
    name = b'.'.join(labels)
    if name not in (b'small.fixture.invalid', b'large.fixture.invalid'):
        return struct.pack('!6H', qid, 0x8183, 1, 0, 0, 0) + query[12:]
    if name.startswith(b'large.') and not tcp:
        return struct.pack('!6H', qid, 0x8380, 1, 0, 0, 0) + query[12:]
    answer = b'\xc0\x0c' + struct.pack('!HHIH', 1, 1, 30, 4) + socket.inet_aton('192.0.2.42')
    return struct.pack('!6H', qid, 0x8180, 1, 1, 0, 0) + query[12:] + answer


def validate_dns_answer(answer: bytes, query: bytes) -> bool:
    if len(answer) < 12 or answer[:2] != query[:2]:
        raise ValueError('DNS transaction mismatch')
    _, flags, qd, an, _, _ = struct.unpack('!6H', answer[:12])
    if not flags & 0x8000 or flags & 0xf or qd != 1:
        raise ValueError('DNS response invalid')
    if flags & 0x0200:
        return False
    if an != 1 or not answer.endswith(socket.inet_aton('192.0.2.42')):
        raise ValueError('Unexpected fixture DNS answer')
    return True


def start_tcp(address: str, port: int, dns: bool = False) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((fixture_ip(address), port))
    server.listen(32)
    SERVERS.append(server)

    def client(conn: socket.socket) -> None:
        with conn:
            conn.settimeout(6)
            try:
                if dns:
                    size = struct.unpack('!H', recv_exact(conn, 2))[0]
                    if size > 2048:
                        return
                    answer = dns_answer(recv_exact(conn, size), True)
                    conn.sendall(struct.pack('!H', len(answer)) + answer)
                else:
                    while data := conn.recv(256):
                        conn.sendall(data)
            except (OSError, ValueError, IndexError):
                pass

    def accept() -> None:
        while True:
            try:
                conn, _ = server.accept()
            except OSError:
                break
            PLAIN_CONNECTIONS.append(conn)
            threading.Thread(target=client, args=(conn,), daemon=True).start()

    threading.Thread(target=accept, daemon=True).start()


def start_dns_udp(address: str) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((fixture_ip(address), 53))
    SERVERS.append(server)

    def run() -> None:
        while True:
            try:
                data, peer = server.recvfrom(2048)
                server.sendto(dns_answer(data, False), peer)
            except (ValueError, IndexError):
                continue
            except OSError:
                break

    threading.Thread(target=run, daemon=True).start()


def probe(address: str, port: int, retained: str | None = None) -> dict[str, Any]:
    token = secrets.token_bytes(24)
    sock = CONNECTIONS.get(retained) if retained else None
    new = sock is None
    try:
        if new:
            sock = socket.create_connection((fixture_ip(address), port), timeout=TIMEOUT)
        assert sock is not None
        sock.sendall(token)
        success = recv_exact(sock, len(token)) == token
        if retained and success:
            CONNECTIONS[retained] = sock
        return {'success': success, 'observation': 'CHALLENGE_ECHO' if success else 'BAD_RESPONSE'}
    except OSError as exc:
        return {'success': False, 'observation': type(exc).__name__, 'errno': exc.errno}
    finally:
        if sock and not retained:
            sock.close()


def dns_probe(address: str, transport: str, large: bool = False) -> dict[str, Any]:
    query = dns_question('large.fixture.invalid' if large else 'small.fixture.invalid', secrets.randbelow(65536))
    used: list[str] = []
    try:
        if transport in ('udp', 'fallback'):
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(TIMEOUT)
                sock.connect((fixture_ip(address), 53))
                sock.send(query)
                answer = sock.recv(2048)
                used.append('udp')
            if validate_dns_answer(answer, query):
                return {'success': True, 'transports': used, 'truncated_udp': False}
            if transport != 'fallback':
                return {'success': False, 'transports': used, 'truncated_udp': True}
        with socket.create_connection((fixture_ip(address), 53), timeout=TIMEOUT) as sock:
            sock.sendall(struct.pack('!H', len(query)) + query)
            size = struct.unpack('!H', recv_exact(sock, 2))[0]
            if size > 2048:
                raise ValueError('Oversized fixture answer')
            answer = recv_exact(sock, size)
            used.append('tcp')
        return {'success': validate_dns_answer(answer, query), 'transports': used,
                'truncated_udp': transport == 'fallback'}
    except (OSError, ValueError) as exc:
        return {'success': False, 'transports': used, 'observation': type(exc).__name__}


def action(request: dict[str, Any]) -> Any:
    global TLS_SERVICE
    command = request['op']
    if command == 'ip':
        # The pipe is private to the fixed-fixture master, not a remote executor.
        run = subprocess.run(['ip', *request['args']], capture_output=True, text=True, timeout=5)
        if run.returncode:
            raise RuntimeError(run.stderr.strip())
        return {'stdout': run.stdout}
    if command == 'forward':
        from link_config import set_forwarding
        return set_forwarding(request['enabled'])
    if command == 'forward-status':
        values = {name: Path(f'/proc/sys/net/ipv4/conf/{name}/forwarding').read_text().strip()
                  for _, name in socket.if_nameindex() if name != 'lo'}
        return {'interfaces': values, 'all_disabled': bool(values) and all(v == '0' for v in values.values())}
    if command == 'filter':
        env = dict(os.environ, HOSTING_LAB_NETNS=os.readlink('/proc/self/ns/net'))
        args = [request['helper'], str(request.get('family', 4)), request['action']]
        if request['action'] == 'install':
            args += [request['rules'], request['mode']]
        result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=5)
        if result.returncode:
            raise RuntimeError(result.stderr.strip())
        return json.loads(result.stdout)
    if command == 'serve':
        for port in request.get('ports', []):
            start_tcp(request['address'], port)
        if request.get('dns'):
            start_tcp(request['address'], 53, True)
            start_dns_udp(request['address'])
        return {'listening': True}
    if command == 'mtls-start':
        from mtls_fixture import Service
        # Replace only this worker's fixed test listener and existing echo sessions.
        for sock in list(SERVERS) + list(PLAIN_CONNECTIONS):
            try:
                if sock.getsockname()[1] == request['port']:
                    try: sock.shutdown(socket.SHUT_RDWR)
                    except OSError: pass
                    sock.close()
            except OSError: pass
        if TLS_SERVICE: TLS_SERVICE.close()
        TLS_SERVICE = Service(fixture_ip(request['address']), request['port'], request['certificate'],
                              request['key'], request['ca'], request['allowed'])
        return {'listening': True, 'port': TLS_SERVICE.port}
    if command == 'mtls-grants':
        return TLS_SERVICE.grants(request['allowed'])
    if command == 'mtls-stats':
        return TLS_SERVICE.stats()
    if command == 'mtls-probe':
        from mtls_fixture import probe as tls_probe
        return tls_probe(fixture_ip(request['address']), request['port'], request['ca'],
                         request.get('certificate'), request.get('key'),
                         request.get('hostname', 'data-01.fixture.invalid'), request.get('retained'))
    if command == 'probe':
        return probe(request['address'], request['port'], request.get('retained'))
    if command == 'dns':
        return dns_probe(request['address'], request['transport'], request.get('large', False))
    if command == 'stop':
        return {'stopping': True}
    raise ValueError('Unknown private fixture operation')


def main() -> int:
    original = os.environ.get('HOSTING_LAB_ORIGINAL_NETNS')
    own = os.readlink('/proc/self/ns/net')
    master = os.environ.get('HOSTING_LAB_MASTER_NETNS')
    if not original or not master or own in (original, master):
        print(json.dumps({'error': 'Worker must be in a separate disposable namespace'}), flush=True)
        return 2
    print(json.dumps({'ready': True, 'namespace': own, 'pid': os.getpid()}), flush=True)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = {'ok': True, 'result': action(request)}
        except Exception as exc:
            response = {'ok': False, 'error': str(exc)}
        print(json.dumps(response), flush=True)
        if response.get('result', {}).get('stopping'):
            break
    for sock in [*CONNECTIONS.values(), *SERVERS]:
        sock.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
