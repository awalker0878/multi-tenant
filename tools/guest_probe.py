"""Fixed read-only probe shipped over pinned SSH; no remote installation needed."""
import errno
import hashlib
import http.client
import json
from pathlib import Path
import signal
import socket
import ssl
import sys


def probe(request):
    if Path('/etc/machine-id').read_text().strip() != request['machine_id']:
        return {'status': 'WRONG_GUEST'}
    # Binding errors are inconclusive, never evidence of enforced denial.
    raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw.settimeout(3)
    try:
        raw.bind((request['source'], 0))
        try:
            raw.connect((request['destination'], request['port']))
        except OSError as exc:
            return {'status': 'BLOCKED' if isinstance(exc, TimeoutError) or exc.errno in
                    {errno.ECONNREFUSED, errno.ETIMEDOUT} else 'INCONCLUSIVE'}
        if request['expect'] == 'deny':
            return {'status': 'UNEXPECTED_CONNECTION'}
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.verify_flags |= ssl.VERIFY_X509_STRICT
        context.load_verify_locations(cadata=request['ca_pem'])
        with context.wrap_socket(raw, server_hostname=request['server_name']) as connection:
            host = request['server_name'] + ':' + str(request['port'])
            message = 'GET ' + request['path'] + ' HTTP/1.1\r\nHost: ' + host + '\r\nConnection: close\r\nAccept-Encoding: identity\r\n\r\n'
            connection.sendall(message.encode('ascii'))
            response = http.client.HTTPResponse(connection)
            response.begin()
            # Redirects, TLS failures and error pages cannot prove service health.
            if response.status != 200 or response.getheader('Content-Encoding', 'identity') != 'identity':
                return {'status': 'UNHEALTHY'}
            content = response.read(1024 * 1024 + 1)
            healthy = len(content) <= 1024 * 1024 and hashlib.sha256(content).hexdigest() == request['body_sha256']
            return {'status': 'HEALTHY' if healthy else 'UNHEALTHY'}
    except (OSError, ValueError, http.client.HTTPException):
        return {'status': 'INCONCLUSIVE'}
    finally:
        raw.close()


def main():
    # Bound execution even if a peer drip-feeds headers or the SSH client dies.
    def expired(*_):
        raise TimeoutError('Probe deadline')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(10)
    try:
        result = probe(json.loads(sys.stdin.read(128 * 1024)))
    except (OSError, ValueError, KeyError, TypeError):
        result = {'status': 'INCONCLUSIVE'}
    finally:
        signal.alarm(0)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
