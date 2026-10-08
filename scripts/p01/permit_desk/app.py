"""Synthetic Permit Desk workload, never a hosting control-plane service."""
from __future__ import annotations

import base64
import binascii
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import json
from pathlib import Path
import re
import ssl

import psycopg
from psycopg.rows import dict_row

CONFIG = Path('/run/config/config.json')
SECRETS = Path('/run/secrets')
ATTACHMENTS = Path('/attachments')
ID = re.compile(r'[a-z][a-z0-9_]{0,47}\Z')
MAX_BODY = 100_000


def configuration(path=CONFIG):
    config = json.loads(path.read_text())
    expected = {'schema_version', 'fixture', 'native_writes', 'principals', 'database'}
    if set(config) != expected or config['schema_version'] != 1 or config['fixture'] != 'permit-desk-v1' or config['native_writes'] is not False:
        raise ValueError('Unsupported fixture configuration')
    if config['database'] != {'host': 'postgres', 'name': 'permit_desk', 'user': 'pd_runtime'}:
        raise ValueError('Unrecognized fixture database')
    if config['principals'] != {
        'writer_a': {'tenant': 't_demo', 'role': 'writer'},
        'reader_a': {'tenant': 't_demo', 'role': 'reader'},
        'writer_b': {'tenant': 't_other', 'role': 'writer'},
    }:
        raise ValueError('Unrecognized synthetic principal inventory')
    return config


def connection():
    return psycopg.connect(host='postgres', port=5432, dbname='permit_desk', user='pd_runtime',
                          password=(SECRETS/'runtime-password').read_text().strip(),
                          sslmode='verify-full', sslrootcert=str(SECRETS/'ca.crt'),
                          connect_timeout=2, options='-c statement_timeout=2000 -c lock_timeout=2000',
                          row_factory=dict_row)


def payload(raw):
    data = json.loads(raw)
    if not isinstance(data, dict) or set(data) != {'permit_id', 'title', 'attachment_base64'}:
        raise ValueError('Unexpected permit fields')
    if not isinstance(data['permit_id'], str) or not ID.fullmatch(data['permit_id']):
        raise ValueError('Invalid permit identity')
    if not isinstance(data['title'], str) or not 1 <= len(data['title']) <= 120:
        raise ValueError('Invalid title')
    if not isinstance(data['attachment_base64'], str):
        raise ValueError('Invalid attachment encoding')
    contents = base64.b64decode(data['attachment_base64'], validate=True)
    if not 1 <= len(contents) <= 65_536:
        raise ValueError('Invalid attachment size')
    return data['permit_id'], data['title'], contents


class Handler(BaseHTTPRequestHandler):
    server_version = 'PermitDeskFixture/1'
    sys_version = ''

    def log_message(self, *_):
        # Authorization headers, tokens and request payloads never enter access logs.
        pass

    def reply(self, status, body):
        encoded = json.dumps(body, sort_keys=True, separators=(',', ':')).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(encoded)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(encoded)

    def principal(self):
        authorization = self.headers.get('Authorization', '')
        if not authorization.startswith('Bearer '):
            return None
        for name, identity in self.server.fixture_config['principals'].items():
            expected = (SECRETS/name).read_text().strip()
            if len(expected) < 32:
                raise ValueError('Invalid fixture credential')
            if hmac.compare_digest(authorization[7:].encode(), expected.encode()):
                return identity
        return None

    def handle_request(self, write=False):
        if self.path == '/health/live' and not write:
            self.reply(200, {'scope': 'synthetic_permit_desk', 'native_writes': False})
            return
        identity = self.principal()
        if identity is None:
            self.reply(401, {'error': 'unauthenticated'})
            return
        parts = self.path.split('/')
        if len(parts) not in (5, 6, 7) or parts[:3] != ['', 'api', 'tenants'] or parts[4] != 'permits':
            self.reply(404, {'error': 'not_found'})
            return
        tenant = parts[3]
        if tenant != identity['tenant']:
            self.reply(403, {'error': 'forbidden'})
            return
        if write and (identity['role'] != 'writer' or len(parts) != 5):
            self.reply(403, {'error': 'forbidden'})
            return
        if len(parts) >= 6 and not ID.fullmatch(parts[5]):
            self.reply(404, {'error': 'not_found'})
            return
        if len(parts) == 7 and parts[6] != 'attachment':
            self.reply(404, {'error': 'not_found'})
            return
        if write:
            if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type') != 'application/json':
                self.reply(415, {'error': 'json_required'})
                return
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY:
                self.reply(413, {'error': 'invalid_length'})
                return
            self.connection.settimeout(5)
            permit, title, contents = payload(self.rfile.read(length))
            key = f'{tenant}--{permit}.bin'
            created_file = False
            try:
                with connection() as db:
                    db.execute('INSERT INTO app.permits(tenant_id,permit_id,title) VALUES (%s,%s,%s)', (tenant, permit, title))
                    db.execute('INSERT INTO app.attachments VALUES (%s,%s,%s,%s,%s)', (tenant, permit, key, hashlib.sha256(contents).hexdigest(), len(contents)))
                    # No overwrite, even if a previous interrupted write left an orphan.
                    with (ATTACHMENTS/key).open('xb') as file:
                        created_file = True
                        file.write(contents)
                        file.flush()
                        import os
                        os.fsync(file.fileno())
                    (ATTACHMENTS/key).chmod(0o640)
            except Exception:
                # A lost commit acknowledgement is ambiguous: preserve the file and
                # require reconciliation. Never delete potentially committed state.
                if created_file:
                    print('Fixture write failed; inspect database/file consistency', flush=True)
                raise
            self.reply(201, {'permit_id': permit, 'tenant_id': tenant})
            return
        with connection() as db:
            query = ('SELECT p.tenant_id,p.permit_id,p.title,p.created_at,a.object_key,a.sha256,a.bytes '
                     'FROM app.permits p JOIN app.attachments a USING (tenant_id,permit_id) WHERE p.tenant_id=%s')
            rows = db.execute(query + (' AND p.permit_id=%s' if len(parts) >= 6 else '') + ' ORDER BY p.permit_id',
                              (tenant, parts[5]) if len(parts) >= 6 else (tenant,)).fetchall()
        if len(parts) >= 6 and not rows:
            self.reply(404, {'error': 'not_found'})
            return
        for row in rows:
            row['created_at'] = row['created_at'].isoformat()
            key = f'{row["tenant_id"]}--{row["permit_id"]}.bin'
            if row['object_key'] != key:
                raise ValueError('Attachment identity mismatch')
            content = (ATTACHMENTS/key).read_bytes()
            if hashlib.sha256(content).hexdigest() != row['sha256'] or len(content) != row['bytes']:
                raise ValueError('Attachment integrity mismatch')
            if len(parts) == 7:
                row['attachment_base64'] = base64.b64encode(content).decode()
        self.reply(200, {'permits': rows, 'scope': 'synthetic_permit_desk', 'native_writes': False})

    def dispatch(self, write=False):
        try:
            self.handle_request(write)
        except psycopg.errors.UniqueViolation:
            self.reply(409, {'error': 'conflict'})
        except (json.JSONDecodeError, binascii.Error, ValueError) as error:
            # Validation errors on writes are caller errors; read integrity/config
            # failures are unavailable service, never an empty successful dataset.
            self.reply(422 if write else 503, {'error': 'invalid_input' if write else 'unavailable'})
        except (OSError, psycopg.Error):
            self.reply(503, {'error': 'unavailable'})

    def do_GET(self):
        self.dispatch()

    def do_POST(self):
        self.dispatch(True)


def main():
    config = configuration()
    for name in (*config['principals'], 'runtime-password'):
        if len((SECRETS/name).read_text().strip()) < 32:
            raise ValueError('Missing or invalid fixture credential')
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(str(SECRETS/'web.crt'), str(SECRETS/'web.key'))
    # The single request writer and stopped server form this fixture's capture
    # boundary. This is not a concurrent production application implementation.
    server = HTTPServer(('0.0.0.0', 8443), Handler)
    server.fixture_config = config
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
