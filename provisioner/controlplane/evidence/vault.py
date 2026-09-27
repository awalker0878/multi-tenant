"""Vault Transit checkpoint signing over a separately administered HTTPS API.

The service token comes from an injected short-lived credential provider. The
application process never handles the Transit private key. A separate verifier
identity may be given only verify permission and an explicit trust list.
"""
from __future__ import annotations

import base64
import json
import re
import ssl
from typing import Callable
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')
_SIGNATURE = re.compile(r'^vault:v[1-9][0-9]*:[A-Za-z0-9+/]+={0,2}$')


class VaultTransitClient:
    def __init__(self, base_url: str, token_provider: Callable[[], str], *,
                 tls_context: ssl.SSLContext | None = None, timeout: float = 5.0):
        parsed = urlsplit(base_url)
        if (parsed.scheme != 'https' or not parsed.netloc or parsed.username or
                parsed.password or parsed.query or parsed.fragment or
                parsed.path not in ('', '/')):
            raise ValueError('Vault Transit requires a dedicated HTTPS origin')
        if not callable(token_provider) or not 0 < timeout <= 30:
            raise ValueError('Short-lived Vault token provider and bounded timeout required')
        self._origin = base_url.rstrip('/')
        self._token_provider = token_provider
        self._tls = tls_context or ssl.create_default_context()
        self._timeout = timeout

    def post(self, mount: str, operation: str, key: str, payload: dict) -> dict:
        if (not _NAME.fullmatch(mount) or not _NAME.fullmatch(key) or
                operation not in ('sign', 'verify')):
            raise ValueError('Invalid Transit key identity')
        token = self._token_provider()
        if not isinstance(token, str) or not token or '\n' in token or '\r' in token:
            raise ValueError('Vault credential provider returned no valid token')
        body = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
        request = Request(f'{self._origin}/v1/{mount}/{operation}/{key}', body,
                          headers={'Content-Type': 'application/json', 'X-Vault-Token': token},
                          method='POST')
        with urlopen(request, timeout=self._timeout, context=self._tls) as response:
            raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError('Vault response exceeded size limit')
        result = json.loads(raw)
        if not isinstance(result, dict) or not isinstance(result.get('data'), dict):
            raise ValueError('Vault Transit returned no result')
        return result['data']


class VaultTransitSigner:
    def __init__(self, client: VaultTransitClient, *, key_id: str,
                 mount: str, key: str):
        if not _NAME.fullmatch(key_id) or not _NAME.fullmatch(mount) or not _NAME.fullmatch(key):
            raise ValueError('Invalid Vault signing identity')
        self._client = client
        self.key_id = key_id
        self._mount = mount
        self._key = key

    def sign(self, payload: bytes) -> bytes:
        if not isinstance(payload, bytes) or len(payload) > 8192:
            raise ValueError('Checkpoint signing payload is invalid')
        result = self._client.post(self._mount, 'sign', self._key,
                                   {'input': base64.b64encode(payload).decode('ascii')})
        signature = result.get('signature')
        if not isinstance(signature, str) or not _SIGNATURE.fullmatch(signature):
            raise ValueError('Vault Transit returned no versioned signature')
        return signature.encode('ascii')


class VaultTransitVerifier:
    def __init__(self, client: VaultTransitClient,
                 trusted_keys: dict[str, tuple[str, str]]):
        if not trusted_keys or any(not _NAME.fullmatch(label) or
                                   not _NAME.fullmatch(mount) or not _NAME.fullmatch(key)
                                   for label, (mount, key) in trusted_keys.items()):
            raise ValueError('Explicit Vault verification trust list required')
        self._client = client
        self._trusted = dict(trusted_keys)

    def verify(self, key_id: str, payload: bytes, signature: bytes) -> None:
        pair = self._trusted.get(key_id)
        if pair is None:
            raise ValueError('Unknown or revoked Vault signing identity')
        try:
            signature_text = signature.decode('ascii')
        except UnicodeDecodeError as exc:
            raise ValueError('Invalid Vault signature encoding') from exc
        if not _SIGNATURE.fullmatch(signature_text):
            raise ValueError('Invalid Vault signature format')
        result = self._client.post(pair[0], 'verify', pair[1],
                                   {'input': base64.b64encode(payload).decode('ascii'),
                                    'signature': signature_text})
        if result.get('valid') is not True:
            raise ValueError('Vault Transit signature was rejected')
