"""Disposable verified-TLS service peers and broker; never imported by products."""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
import json
from pathlib import Path
import secrets
import ssl
import subprocess
import threading
import time
from urllib.parse import parse_qs, urlsplit


class NativePeer:
    """Independent synthetic native state and request observer; never an E3 claim."""
    def __init__(self, certificate, key, token):
        peer = self
        self.requests = []
        self.mode = 'complete'
        self.state = {
            'servers': [{'id': 'vm-1', 'name': '<img src=x onerror=alert(1)>', 'tenant_id': 'project-a', 'created': '2026-01-01T00:00:00Z', 'status': 'ACTIVE'},
                        {'id': 'vm-2', 'name': 'Observed worker', 'tenant_id': 'project-a', 'created': '2026-01-02T00:00:00Z', 'status': 'ACTIVE'}],
            'networks': [{'id': 'net-1', 'name': 'Application network', 'project_id': 'project-a', 'created_at': '2026-01-01T00:00:00Z', 'status': 'ACTIVE'}],
            'volumes': [{'id': 'vol-1', 'name': 'Application data', 'created_at': '2026-01-01T00:00:00Z', 'size': 20}],
        }
        self.configuration = json.loads((Path(__file__).resolve().parents[2] / 'contracts/fixtures/inventory/configuration-v1.1.json').read_text())['responses']
        self.before = hashlib.sha256(json.dumps([self.state, self.configuration], sort_keys=True).encode()).hexdigest()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                u = urlsplit(self.path)
                query = parse_qs(u.query)
                collection = {'/v2.1/servers/detail': 'servers', '/v2.0/networks': 'networks', '/v3/project-a/volumes/detail': 'volumes'}.get(u.path)
                status, body = 200, {}
                if self.headers.get('X-Auth-Token') != token:
                    status = 403
                elif u.path in peer.configuration:
                    if u.path.startswith('/v2.0/') and u.path != '/v2.0/extensions' and query.get('project_id') != ['project-a']:
                        status = 403
                    else:
                        body = peer.configuration[u.path]
                elif collection is None:
                    status = 403
                elif collection == 'networks' and (query.get('project_id') != ['project-a'] or peer.mode == 'permission_gap'):
                    status = 403
                else:
                    rows = peer.state[collection]
                    marker = query.get('marker', [None])[0]
                    index = 0 if marker is None else next((i+1 for i, row in enumerate(rows) if row['id'] == marker), len(rows))
                    # Independent provider lowers the requested limit to one.
                    body = {collection: rows[index:index+1], collection+'_links': [{'rel': 'next', 'href': 'https://169.254.169.254/forbidden'}]}
                peer.requests.append({'method': 'GET', 'path': self.path, 'status': status})
                raw = json.dumps(body).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                peer.requests.append({'method': 'POST', 'path': self.path, 'status': 405})
                self.send_error(405)

        self.server = ThreadingHTTPServer(('127.0.0.1', 8445), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certificate, key)
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def unchanged(self):
        return self.before == hashlib.sha256(json.dumps([self.state, self.configuration], sort_keys=True).encode()).hexdigest()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class TlsProxy:
    def __init__(self, port, upstream, certificate, key, fault_file=None):
        peer = self
        self.fault_file = fault_file
        self.forwarded = 0
        self.injected = 0

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def handle_request(self):
                length = int(self.headers.get('Content-Length', '0'))
                if length > 310000:
                    self.send_error(413)
                    return
                body = self.rfile.read(length) if length else None
                connection = http.client.HTTPConnection('127.0.0.1', upstream, timeout=15)
                try:
                    connection.request(self.command, self.path, body, dict(self.headers))
                    response = connection.getresponse()
                    wire = response.read()
                    peer.forwarded += 1
                    inject = False
                    if peer.fault_file and peer.fault_file.exists() and self.command == 'POST' and response.status == 201:
                        rule = json.loads(peer.fault_file.read_text())
                        if rule.get('path') == self.path:
                            peer.fault_file.unlink()
                            inject = True
                            peer.injected += 1
                    if inject:
                        wire = b'{"error":"synthetic_response_loss"}'
                    self.send_response(503 if inject else response.status)
                    for name, value in response.getheaders():
                        if name.lower() not in ['content-length', 'transfer-encoding', 'connection']:
                            self.send_header(name, value)
                    self.send_header('Content-Length', str(len(wire)))
                    self.end_headers()
                    self.wfile.write(wire)
                finally:
                    connection.close()

            do_GET = do_POST = do_PUT = handle_request

        self.server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certificate, key)
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class InventoryBroker:
    def __init__(self, root: Path, private: Path, run, secrets_list):
        self.name = 'p04-inventory-' + secrets.token_hex(6)
        self.image = json.loads((root / 'deploy/dependencies/stateful/inputs.lock.json').read_text())['images']['rabbitmq']['reference']
        self.run = run
        self.environment = {}
        self.private = private
        definitions = json.loads((root/'deploy/dependencies/stateful/inventory-facts.json').read_text())
        # Qualify the provisioned binding with an independent observer identity;
        # this does not claim the future Planning consumer is implemented.
        definitions['users'] = []
        definitions['permissions'] = []
        definitions['queues'][0]['name'] = 'p04.observer'
        definitions['bindings'][0]['destination'] = 'p04.observer'
        for user in ['inventory', 'p04-observer']:
            password = secrets.token_hex(32)
            secrets_list.append(password)
            file = private / (user + '-broker.password')
            file.write_text(password)
            file.chmod(0o600)
            salt = secrets.token_bytes(4)
            definitions['users'].append({'name': user, 'password_hash': base64.b64encode(salt + hashlib.sha256(salt + password.encode()).digest()).decode(), 'hashing_algorithm': 'rabbit_password_hashing_sha256', 'tags': []})
            definitions['permissions'].append({'user': user, 'vhost': 'product', 'configure': '^$', 'write': '^inventory\\.events$' if user == 'inventory' else '^$', 'read': '^p04\\.observer$' if user == 'p04-observer' else '^$'})
            self.environment['INVENTORY_BROKER_PASSWORD_FILE' if user == 'inventory' else 'P04_OBSERVER_PASSWORD_FILE'] = str(file)
        self.environment.update(INVENTORY_BROKER_HOST='127.0.0.1', INVENTORY_BROKER_PORT='5679', INVENTORY_BROKER_CA_FILE=str(private/'services.crt'))
        (private/'broker-definitions.json').write_text(json.dumps(definitions))
        (private/'rabbitmq.conf').write_text('listeners.tcp = none\nlisteners.ssl.default = 5671\nssl_options.certfile = /config/services.crt\nssl_options.keyfile = /config/services.key\nssl_options.cacertfile = /config/services.crt\nssl_options.verify = verify_none\nssl_options.fail_if_no_peer_cert = false\ndefinitions.import_backend = local_filesystem\ndefinitions.local.path = /config/broker-definitions.json\n')

    def start(self):
        mounts = []
        for filename in ['services.crt', 'services.key', 'broker-definitions.json', 'rabbitmq.conf']:
            path = self.private/filename
            path.chmod(0o444)
            mounts += ['-v', str(path) + ':' + ('/etc/rabbitmq/rabbitmq.conf' if filename.endswith('.conf') else '/config/'+filename) + ':ro']
        # A root health probe can create an unreadable cookie before server startup.
        self.run(['docker', 'run', '-d', '--name', self.name, '--hostname', 'p04-broker', '-p', '127.0.0.1:5679:5671', '-e', 'RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS=+S 2:2', '-e', 'RABBITMQ_CTL_ERL_ARGS=+S 2:2', '--health-cmd', 'gosu rabbitmq rabbitmq-diagnostics -q check_running', '--health-interval', '2s', '--health-retries', '45', *mounts, self.image], label='broker-start')
        deadline = time.monotonic()+90
        while True:
            state = json.loads(subprocess.check_output(['docker', 'inspect', '--format', '{{json .State}}', self.name]))
            if state.get('Health', {}).get('Status') == 'healthy':
                break
            if not state.get('Running') or time.monotonic() >= deadline:
                self.run(['docker', 'logs', self.name], label='broker-failure')
                self.run(['docker', 'inspect', '--format', '{{json .State}}', self.name], label='broker-failure-state')
                raise RuntimeError('broker_not_ready')
            time.sleep(1)
        self.run(['docker', 'exec', '--user', 'rabbitmq', self.name, 'rabbitmq-diagnostics', '-q', 'check_port_connectivity', '--address', '127.0.0.1'], label='broker-ready')

    def close(self):
        subprocess.run(['docker', 'rm', '-f', self.name], capture_output=True, timeout=30)
