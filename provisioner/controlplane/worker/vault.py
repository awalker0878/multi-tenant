"""Vault response-wrapped, dynamically generated operation credentials.

This adapter never reads the underlying platform secret. A Vault role must
generate a credential constrained to the exact endpoint/action with a maximum
lease no longer than this service's five-minute grant. That external policy is
part of platform qualification; a static KV secret is not an accepted role.
"""
from __future__ import annotations

import http.client
import json
import os
import re
import ssl
import stat
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from provisioner.controlplane.authority.model import PlanScope, WorkerGrant

from .grants import ALLOWED_OPERATIONS, GrantDenied, MAX_GRANT_TTL, _ID, _aware

_PATH_SEGMENT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')


@dataclass(frozen=True)
class VaultDynamicRole:
    reference: str
    api_path: str
    scope: PlanScope
    operation_kind: str
    max_credential_ttl: timedelta

    def __post_init__(self) -> None:
        if (not isinstance(self.reference, str) or not self.reference.startswith('vault:')
                or not _ID.fullmatch(self.reference[6:])
                or not isinstance(self.api_path, str)
                or not self.api_path.endswith('/creds/' + self.reference[6:])
                or not all(_PATH_SEGMENT.fullmatch(s) for s in self.api_path.split('/'))
                or not isinstance(self.scope, PlanScope)
                or self.operation_kind not in ALLOWED_OPERATIONS
                or not isinstance(self.max_credential_ttl, timedelta)
                or not timedelta(0) < self.max_credential_ttl <= MAX_GRANT_TTL):
            raise ValueError('Vault role must name an exact dynamic credential endpoint and scope')


@dataclass(frozen=True)
class VaultWrappedCredential:
    wrapping_token: str = field(repr=False)
    creation_path: str
    expires_at: datetime
    grant_id: str

    def __post_init__(self) -> None:
        if (not self.wrapping_token or not self.creation_path
                or not _aware(self.expires_at) or not self.grant_id):
            raise ValueError('Invalid wrapped credential')


class VaultDynamicCredentialIssuer:
    """Read a Vault Agent token file and request one-time response wrapping.

    A dedicated Vault policy grants ``read`` only on configured ``/creds/``
    paths. The Vault role and backend own actual native credential generation,
    TTL, privileges and revocation. Neither the service nor workflow history
    stores the unwrapped credential or a reusable platform password.
    """

    def __init__(self, *, vault_url: str, ca_bundle: str | Path,
                 agent_token_file: str | Path,
                 roles: tuple[VaultDynamicRole, ...], namespace: str | None = None,
                 client_certificate: str | Path | None = None,
                 client_key: str | Path | None = None, timeout: float = 5):
        parsed = urlsplit(vault_url)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                or parsed.password or parsed.path or parsed.query or parsed.fragment
                or not isinstance(timeout, (int, float)) or not 0 < timeout <= 15
                or not isinstance(roles, tuple) or not roles
                or any(not isinstance(role, VaultDynamicRole) for role in roles)
                or len({role.reference for role in roles}) != len(roles)
                or (client_certificate is None) != (client_key is None)
                or (namespace is not None and
                    (not isinstance(namespace, str) or not namespace
                     or not all(_PATH_SEGMENT.fullmatch(s) for s in namespace.split('/'))))):
            raise ValueError('A pinned HTTPS Vault endpoint, roles and token source are required')
        self._host = parsed.hostname
        self._port = parsed.port or 443
        self._timeout = timeout
        self._namespace = namespace
        self._token_file = Path(agent_token_file)
        self._roles = {role.reference: role for role in roles}
        self._tls = ssl.create_default_context(cafile=str(ca_bundle))
        self._tls.minimum_version = ssl.TLSVersion.TLSv1_2
        if client_certificate is not None:
            self._tls.load_cert_chain(str(client_certificate), str(client_key))

    def _token(self) -> str:
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0)
        try:
            descriptor = os.open(self._token_file, flags)
            try:
                info = os.fstat(descriptor)
                if (not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, os.geteuid())
                        or info.st_mode & 0o077 or info.st_size > 8192):
                    raise GrantDenied('Vault Agent token file is not private')
                raw = os.read(descriptor, 8193)
            finally:
                os.close(descriptor)
            token = raw.decode('ascii').strip()
            if (not token or len(token) > 8192 or
                    any(character.isspace() or ord(character) < 33 or ord(character) > 126
                        for character in token)):
                raise GrantDenied('Vault Agent token is unavailable')
            return token
        except (OSError, UnicodeError) as exc:
            raise GrantDenied('Vault Agent token is unavailable') from exc

    def issue(self, reference: str, *, grant: WorkerGrant,
              expires_at: datetime) -> VaultWrappedCredential:
        role = self._roles.get(reference)
        if (role is None or not isinstance(grant, WorkerGrant)
                or grant.operation_scope != role.scope
                or grant.operation_kind != role.operation_kind
                or not _aware(expires_at)
                or expires_at > grant.expires_at):
            raise GrantDenied('Vault role differs from the exact worker grant')
        now = datetime.now(timezone.utc)
        remaining = int((expires_at - now).total_seconds())
        seconds = min(remaining, int(role.max_credential_ttl.total_seconds()))
        if seconds < 1:
            raise GrantDenied('Worker grant expires before credential issuance')
        headers = {
            'X-Vault-Token': self._token(),
            'X-Vault-Wrap-TTL': f'{seconds}s',
            'X-Vault-Request': 'true',
            'Accept': 'application/json',
        }
        if self._namespace is not None:
            headers['X-Vault-Namespace'] = self._namespace
        connection = http.client.HTTPSConnection(self._host, self._port,
                                                 timeout=self._timeout, context=self._tls)
        try:
            connection.request('GET', '/v1/' + role.api_path, headers=headers)
            response = connection.getresponse()
            raw = response.read(32769)
            if response.status != 200 or len(raw) > 32768:
                raise GrantDenied('Vault refused a bounded credential request')
            payload = json.loads(raw)
            if (not isinstance(payload, dict) or payload.get('data') is not None
                    or payload.get('auth') is not None):
                raise GrantDenied('Vault returned an unwrapped credential')
            wrapped = payload.get('wrap_info')
            if not isinstance(wrapped, dict):
                raise GrantDenied('Vault did not wrap its credential response')
            token = wrapped.get('token')
            ttl = wrapped.get('ttl')
            path = wrapped.get('creation_path')
            received_at = datetime.now(timezone.utc)
            if (not isinstance(token, str) or not token or len(token) > 8192
                    or any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in token)
                    or type(ttl) is not int or not 0 < ttl <= seconds
                    or path not in (role.api_path, '/v1/' + role.api_path)
                    or received_at + timedelta(seconds=ttl) > expires_at):
                raise GrantDenied('Vault wrapped credential exceeds exact grant')
            return VaultWrappedCredential(token, path,
                                          received_at + timedelta(seconds=ttl),
                                          grant.grant_id)
        except (OSError, TimeoutError, ssl.SSLError, http.client.HTTPException,
                ValueError, UnicodeError) as exc:
            raise GrantDenied('Vault credential issuance failed') from exc
        finally:
            connection.close()
