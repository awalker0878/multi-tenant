"""Disposable HTTPS OIDC peer for the P02 CI browser campaign only.

No production application imports this fixture. Keys, credentials and one-use codes
exist only in private runner scratch/memory; HTTP bodies and queries are not logged.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import secrets
import ssl
import subprocess
import threading
import time
from urllib.parse import parse_qs, urlencode, urlsplit


def encoded(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip('=')


class SyntheticOidc:
    def __init__(self, private: Path):
        addresses = subprocess.check_output(['hostname', '-I'], text=True).split()
        networks = [ipaddress.ip_network(value) for value in ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16']]
        self.address = next((value for value in addresses if any(ipaddress.ip_address(value) in network for network in networks)), None)
        if self.address is None:
            raise RuntimeError('The disposable provider requires a runner RFC1918 interface.')
        self.key = private / 'oidc.key'
        self.certificate = private / 'oidc.crt'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(self.key), '-out', str(self.certificate), '-days', '1', '-subj', '/CN=p02-disposable-identity', '-addext', 'subjectAltName=IP:' + self.address], check=True, capture_output=True)
        self.key.chmod(0o600)
        details = subprocess.check_output(['php', '-r', '$k=openssl_pkey_get_private(file_get_contents($argv[1])); $d=openssl_pkey_get_details($k); echo json_encode(["n"=>base64_encode($d["rsa"]["n"]),"e"=>base64_encode($d["rsa"]["e"])]);', str(self.key)], text=True)
        self.jwk = {'kty': 'RSA', 'kid': 'disposable-p02', 'alg': 'RS256', 'use': 'sig', **{key: encoded(base64.b64decode(value)) for key, value in json.loads(details).items()}}
        self.client_id = 'p02-' + secrets.token_hex(8)
        self.client_secret = secrets.token_urlsafe(32)
        self.callback = 'http://127.0.0.1:8031/identity/callback'
        self.attempts: dict[str, dict] = {}
        self.codes: dict[str, dict] = {}
        self.private_values = [self.client_secret]
        self.counts = {'discovery': 0, 'token': 0, 'jwks': 0, 'pkce_verified': 0}
        peer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def send(self, status: int, value: dict | str, location: str | None = None):
                body = json.dumps(value).encode() if isinstance(value, dict) else value.encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json' if isinstance(value, dict) else 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Referrer-Policy', 'no-referrer')
                if location:
                    self.send_header('Location', location)
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                uri = urlsplit(self.path)
                if uri.path == '/.well-known/openid-configuration':
                    peer.counts['discovery'] += 1
                    self.send(200, {'issuer': peer.issuer, 'authorization_endpoint': peer.issuer + '/authorize', 'token_endpoint': peer.issuer + '/token', 'jwks_uri': peer.issuer + '/jwks', 'response_types_supported': ['code'], 'code_challenge_methods_supported': ['S256'], 'id_token_signing_alg_values_supported': ['RS256'], 'token_endpoint_auth_methods_supported': ['client_secret_post']})
                elif uri.path == '/jwks':
                    peer.counts['jwks'] += 1
                    self.send(200, {'keys': [peer.jwk]})
                elif uri.path == '/authorize':
                    args = {key: values[0] for key, values in parse_qs(uri.query).items()}
                    if not (args.get('client_id') == peer.client_id and args.get('redirect_uri') == peer.callback and args.get('response_type') == 'code' and args.get('code_challenge_method') == 'S256' and args.get('max_age') == '0' and all(args.get(key) for key in ['state', 'nonce', 'code_challenge'])):
                        return self.send(400, {'error': 'invalid_authorization_request'})
                    attempt = secrets.token_hex(32)
                    peer.private_values.extend([attempt, args['state'], args['nonce']])
                    peer.attempts[attempt] = args | {'expires': time.time() + 60}
                    self.send(200, '<!doctype html><html lang="en"><title>Disposable identity provider</title><h1>Disposable identity provider</h1><form method="post" action="/authorize"><input type="hidden" name="attempt" value="' + attempt + '"><label for="subject">Fixture subject</label><select id="subject" name="subject"><option value="p02-admin">Administrator</option><option value="p02-reader">Reader</option><option value="p02-outsider">Unassigned user</option></select><button type="submit">Continue to console</button></form></html>')
                else:
                    self.send(404, {'error': 'not_found'})

            def do_POST(self):
                length = int(self.headers.get('Content-Length', '0'))
                if length > 16384:
                    return self.send(413, {'error': 'too_large'})
                args = {key: values[0] for key, values in parse_qs(self.rfile.read(length).decode()).items()}
                if self.path == '/authorize':
                    attempt = peer.attempts.pop(args.get('attempt', ''), None)
                    if not attempt or attempt['expires'] <= time.time() or args.get('subject') not in ['p02-admin', 'p02-reader', 'p02-outsider']:
                        return self.send(400, {'error': 'invalid_attempt'})
                    code = secrets.token_urlsafe(32)
                    peer.private_values.append(code)
                    peer.codes[code] = attempt | {'subject': args['subject']}
                    self.send(303, '', peer.callback + '?' + urlencode({'state': attempt['state'], 'code': code}))
                elif self.path == '/token':
                    peer.counts['token'] += 1
                    grant = peer.codes.pop(args.get('code', ''), None)
                    if not grant or grant['expires'] <= time.time() or args.get('client_id') != peer.client_id or not hmac.compare_digest(args.get('client_secret', ''), peer.client_secret) or args.get('grant_type') != 'authorization_code' or args.get('redirect_uri') != peer.callback or not hmac.compare_digest(encoded(hashlib.sha256(args.get('code_verifier', '').encode()).digest()), grant['code_challenge']):
                        return self.send(400, {'error': 'invalid_grant'})
                    peer.private_values.append(args['code_verifier'])
                    peer.counts['pkce_verified'] += 1
                    now = int(time.time())
                    claims = {'iss': peer.issuer, 'aud': peer.client_id, 'sub': grant['subject'], 'nonce': grant['nonce'], 'iat': now, 'auth_time': now, 'exp': now + 1800}
                    data = encoded(json.dumps({'alg': 'RS256', 'kid': peer.jwk['kid']}).encode()) + '.' + encoded(json.dumps(claims).encode())
                    signature = subprocess.check_output(['openssl', 'dgst', '-sha256', '-sign', str(peer.key)], input=data.encode())
                    self.send(200, {'id_token': data + '.' + encoded(signature), 'token_type': 'Bearer'})
                else:
                    self.send(404, {'error': 'not_found'})

        self.server = ThreadingHTTPServer((self.address, 0), Handler)
        self.issuer = 'https://' + self.address + ':' + str(self.server.server_port)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.certificate, self.key)
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def fixture(self) -> dict:
        return {'issuer': self.issuer, 'client_id': self.client_id, 'client_secret': self.client_secret, 'private_networks': self.address + '/32'}
