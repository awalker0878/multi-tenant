"""Provider-neutral, pinned HTTPS GET mechanism for authorized discovery adapters.

The caller owns route selection and native credential/campaign verification.
This module neither chooses a vendor nor issues authority. Every read rechecks
that caller's current authorization before connection, before credentials are
sent, and before any response is returned. No fallback transport exists.
"""
from __future__ import annotations

import hashlib
import http.client
import ipaddress
import re
import socket
import ssl
import time
from pathlib import Path
from threading import Timer
from typing import Callable, Mapping
from urllib.parse import urlsplit

from .native_credentials import NativeReadHeld, decode_json, read_protected


def read_json(*, origin: str, connect_ip: str, ca_digest: str,
              ca_bundle: Path, path: str, credential_header: str, credential: str,
              timeout: float, max_response_bytes: int,
              authorize: Callable[[], None],
              request_headers: Mapping[str, str] | None = None,
              response_headers: Mapping[str, str] | None = None) -> tuple[int, object]:
    """Perform one bounded GET on an already selected native endpoint.

    The absolute deadline includes trust-file loading, TLS, HTTP and decoding.
    Only the adapter constructs the path and credential header. Callers must
    discard observations if authorization changes during a read.
    """
    url = urlsplit(origin)
    address = ipaddress.ip_address(connect_ip)
    if (url.scheme != 'https' or not url.hostname or url.username is not None
            or url.password is not None or url.path or url.query or url.fragment
            or address.is_unspecified or address.is_multicast or str(address) != connect_ip
            or not isinstance(path, str) or not path.startswith('/') or path.startswith('//')
            or any(ord(c) < 33 or ord(c) > 126 for c in path)
            or not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]{0,63}', credential_header)
            or credential_header.lower() in {'host', 'connection', 'content-length',
                                             'transfer-encoding', 'accept-encoding'}
            or not isinstance(credential, str) or not 16 <= len(credential) <= 8192
            or any(not 33 <= ord(c) <= 126 for c in credential)
            or type(timeout) not in (int, float) or not 0 < timeout <= 15
            or type(max_response_bytes) is not int or not 1024 <= max_response_bytes <= 4*1024*1024
            or not callable(authorize)):
        raise NativeReadHeld('Invalid bounded native HTTPS configuration')
    # Copy bounded public protocol headers; never allow overrides of custody or
    # HTTP framing. Adapters own their version values, not this neutral mechanism.
    reserved = {'host', 'connection', 'content-length', 'transfer-encoding',
                'accept', 'accept-encoding', 'authorization', 'proxy-authorization',
                'cookie', 'set-cookie', credential_header.lower()}
    def headers(value):
        if value is None:
            return {}
        if not isinstance(value, Mapping) or len(value) > 8:
            raise NativeReadHeld('Invalid native protocol headers')
        result, names = {}, set()
        for name, item in value.items():
            if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]{0,63}', name)
                    or name.lower() in reserved or name.lower() in names
                    or not isinstance(item, str) or not 1 <= len(item) <= 128
                    or item != item.strip() or any(not 32 <= ord(c) <= 126 for c in item)):
                raise NativeReadHeld('Invalid native protocol headers')
            names.add(name.lower())
            result[name] = item
        return result
    sent_headers, expected_headers = headers(request_headers), headers(response_headers)
    deadline = time.monotonic() + timeout
    active = [None]

    def remaining():
        value = deadline - time.monotonic()
        if value <= 0:
            raise NativeReadHeld('Native read deadline expired')
        return value

    def stop():
        sock = active[0]
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    timer = Timer(timeout, stop)
    timer.daemon = True
    connection = None
    response = None
    timer.start()
    try:
        authorize()
        ca = read_protected(ca_bundle, 1024 * 1024, secret=False)
        if hashlib.sha256(ca).hexdigest() != ca_digest:
            raise NativeReadHeld('Native trust bundle differs from the signed binding')
        # Do not let an inherited SSLKEYLOGFILE export native-session secrets.
        # Retain explicit hostname/chain verification and the strict/partial-chain
        # flags used by the supported Python client, without loading system roots.
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.verify_flags |= ssl.VERIFY_X509_STRICT | ssl.VERIFY_X509_PARTIAL_CHAIN
        context.load_verify_locations(cadata=ca.decode('ascii'))
        raw = socket.create_connection((connect_ip, url.port or 443), timeout=remaining())
        active[0] = raw
        raw.settimeout(remaining())
        tls = context.wrap_socket(raw, server_hostname=url.hostname, do_handshake_on_connect=False)
        active[0] = tls
        tls.settimeout(remaining())
        tls.do_handshake()
        authorize()
        tls.settimeout(remaining())
        connection = http.client.HTTPConnection(url.hostname, url.port or 443, timeout=remaining())
        connection.auto_open = 0  # Never reconnect over an unverified plaintext socket.
        connection.sock = tls
        connection.request('GET', path, headers={
            credential_header: credential, 'Accept': 'application/json',
            'Accept-Encoding': 'identity', 'Connection': 'close', **sent_headers})
        response = connection.getresponse()
        remaining()
        if response.status != 200:
            if 300 <= response.status < 400:
                raise NativeReadHeld('Native redirects are forbidden')
            authorize()
            remaining()
            return response.status, None  # Never expose native error bodies.
        for name, expected in expected_headers.items():
            if response.headers.get_all(name, []) != [expected]:
                raise NativeReadHeld('Native response protocol version is not the selected value')
        lengths = response.headers.get_all('Content-Length', [])
        transfers = response.headers.get_all('Transfer-Encoding', [])
        types = response.headers.get_all('Content-Type', [])
        encodings = response.headers.get_all('Content-Encoding', [])
        if (len(lengths) > 1 or lengths and (not lengths[0].isascii()
                or not lengths[0].isdigit() or int(lengths[0]) > max_response_bytes)
                or len(transfers) > 1 or transfers and transfers[0].lower() != 'chunked'
                or lengths and transfers or len(types) != 1
                or types[0].split(';', 1)[0].strip().lower() != 'application/json'
                or len(encodings) > 1 or encodings and encodings[0].lower() != 'identity'):
            raise NativeReadHeld('Native response framing or content type is invalid')
        body = response.read(max_response_bytes + 1)
        remaining()
        if lengths and len(body) != int(lengths[0]):
            raise NativeReadHeld('Native response was truncated')
        value = decode_json(body, max_response_bytes)
        authorize()
        remaining()
        return 200, value
    finally:
        timer.cancel()
        # HTTPResponse owns a buffered reader independently of connection.sock.
        if response is not None:
            response.close()
        if connection is not None:
            connection.close()
        if active[0] is not None:
            active[0].close()
        timer.join()
