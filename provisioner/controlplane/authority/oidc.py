"""Pinned OIDC access-token verification backed by a live role directory.

The JWT proves an issuer, subject and session, not organization membership or
authorization. The directory is an independent server-side source of those
facts and must check that the session is still active on every lookup.
"""
from __future__ import annotations

import json
import ssl
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Callable, Mapping, Protocol
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

import jwt

from .model import PlanScope, PortfolioScope, RoleGrant, VerifiedPrincipal
from .service import AuthenticationFailed


@dataclass(frozen=True)
class DirectoryIdentity:
    """Current server-owned enrollment and scoped grants for one OIDC session."""

    subject: str
    session_id: str
    organization_id: str
    tenant_id: str
    kind: str
    active: bool
    grants: tuple[RoleGrant, ...]


class RoleDirectory(Protocol):
    def resolve(self, issuer: str, subject: str, session_id: str) -> DirectoryIdentity:
        """Return current enrollment or fail; never use client role claims."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _download_jwks(url: str) -> Mapping[str, object]:
    """Fetch only the configured HTTPS endpoint; reject redirects and large sets."""
    request = Request(url, headers={'Accept': 'application/jwk-set+json, application/json'})
    opener = build_opener(HTTPSHandler(context=ssl.create_default_context()), _NoRedirect())
    with opener.open(request, timeout=5) as response:
        document = response.read(131073)
    if len(document) > 131072:
        raise ValueError('JWKS document exceeds the configured size bound')
    result = json.loads(document)
    if not isinstance(result, dict):
        raise ValueError('JWKS must be an object')
    return result


def _https_url(value: str) -> bool:
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme == 'https' and bool(parsed.hostname)
                and parsed.username is None and parsed.password is None
                and not parsed.fragment and parsed.port != 0)
    except ValueError:
        return False


def _timestamp(value: object, label: str) -> datetime:
    if type(value) is not int or value < 0:
        raise AuthenticationFailed(f'{label} must be an integer timestamp')
    try:
        return datetime.fromtimestamp(value, timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:
        raise AuthenticationFailed(f'{label} is outside the supported range') from exc


class OIDCIdentityProvider:
    """RS256 access-token verifier implementing ``IdentityProvider``.

    ``fetch_jwks`` is an internal deployment/test port. Production uses the
    bounded, TLS-validating downloader. Neither a JWT header nor its claims
    can select a different key server, organization, tenant or role grant.
    A removed key is rejected after the short cache TTL; an unknown kid causes
    one immediate refresh to support signing-key rotation.
    """

    def __init__(self, *, issuer: str, audience: str, jwks_uri: str,
                 directory: RoleDirectory, step_up_acr: frozenset[str],
                 max_token_age: timedelta = timedelta(minutes=15),
                 jwks_cache_ttl: timedelta = timedelta(minutes=2),
                 fetch_jwks: Callable[[str], Mapping[str, object]] | None = None) -> None:
        if (not _https_url(issuer) or not _https_url(jwks_uri)
                or not isinstance(audience, str) or not audience.strip()
                or not isinstance(step_up_acr, frozenset) or not step_up_acr
                or any(not isinstance(acr, str) or not acr for acr in step_up_acr)
                or not isinstance(max_token_age, timedelta)
                or not timedelta(0) < max_token_age <= timedelta(hours=24)
                or not isinstance(jwks_cache_ttl, timedelta)
                or not timedelta(0) < jwks_cache_ttl <= timedelta(minutes=5)):
            raise ValueError('OIDC verifier needs pinned HTTPS and bounded policy')
        self._issuer = issuer
        self._audience = audience
        self._jwks_uri = jwks_uri
        self._directory = directory
        self._step_up_acr = step_up_acr
        self._max_token_age = max_token_age
        self._jwks_ttl = jwks_cache_ttl.total_seconds()
        self._fetch = fetch_jwks or _download_jwks
        self._keys: dict[str, object] = {}
        self._cache_until = 0.0
        self._lock = Lock()

    def _refresh(self) -> None:
        # A failed refresh must not leave a previously usable key set behind.
        self._cache_until = 0.0
        self._keys = {}
        document = self._fetch(self._jwks_uri)
        if not isinstance(document, Mapping):
            raise ValueError('Invalid JWKS document')
        candidates = document.get('keys')
        if not isinstance(candidates, list) or not 0 < len(candidates) <= 64:
            raise ValueError('JWKS contains no bounded key set')
        keys: dict[str, object] = {}
        for item in candidates:
            if not isinstance(item, dict):
                raise ValueError('Invalid JWK')
            kid = item.get('kid')
            if (not isinstance(kid, str) or not 0 < len(kid) <= 256
                    or kid in keys or item.get('kty') != 'RSA'
                    or item.get('alg', 'RS256') != 'RS256'
                    or item.get('use', 'sig') != 'sig'
                    or (item.get('key_ops') is not None
                        and item['key_ops'] != ['verify'])):
                raise ValueError('JWK cannot be used as a unique RS256 verification key')
            public = jwt.PyJWK.from_dict(item, algorithm='RS256').key
            if public.key_size < 2048:
                raise ValueError('RSA verification key is too small')
            keys[kid] = public
        self._keys = keys
        self._cache_until = time.monotonic() + self._jwks_ttl

    def _key(self, kid: str) -> object:
        with self._lock:
            if time.monotonic() >= self._cache_until or kid not in self._keys:
                # Never fall back to an expired or stale cache on network errors.
                self._refresh()
            if kid not in self._keys:
                raise ValueError('Signing key is absent from the pinned JWKS')
            return self._keys[kid]

    def authenticate(self, credential: object) -> VerifiedPrincipal:
        try:
            if (not isinstance(credential, str) or not 0 < len(credential) <= 16384
                    or credential != credential.strip()
                    or credential.count('.') != 2):
                raise ValueError('Expected a bounded JWT access token')
            header = jwt.get_unverified_header(credential)
            kid = header.get('kid')
            if (header.get('alg') != 'RS256' or header.get('typ') != 'at+jwt'
                    or not isinstance(kid, str) or not 0 < len(kid) <= 256
                    or any(name in header for name in
                           ('crit', 'cty', 'jku', 'x5u', 'jwk'))):
                raise ValueError('Unsupported JWT header')
            claims = jwt.decode(
                credential, self._key(kid), algorithms=['RS256'],
                issuer=self._issuer, audience=self._audience,
                options={'require': ['iss', 'aud', 'sub', 'sid', 'iat', 'nbf', 'exp'],
                         'strict_aud': True}, leeway=0)
            now = datetime.now(timezone.utc)
            issued_at = _timestamp(claims['iat'], 'iat')
            not_before = _timestamp(claims['nbf'], 'nbf')
            expires_at = _timestamp(claims['exp'], 'exp')
            if (not_before > now or issued_at > now or expires_at <= now
                    or expires_at <= issued_at
                    or now - issued_at > self._max_token_age):
                raise ValueError('JWT validity window or maximum age failed')
            subject, session = claims['sub'], claims['sid']
            if (not isinstance(subject, str) or not 0 < len(subject) <= 256
                    or not isinstance(session, str) or not 0 < len(session) <= 256):
                raise ValueError('Subject and session must be exact identities')

            # OIDC acr only establishes step-up when the verified authentication
            # time is present. A token with a declared but malformed time fails.
            acr = claims.get('acr')
            if acr is not None and not isinstance(acr, str):
                raise ValueError('acr must be a string')
            auth_time = claims.get('auth_time')
            step_up_at = None
            if auth_time is not None:
                auth_time = _timestamp(auth_time, 'auth_time')
                if auth_time > now or auth_time >= expires_at:
                    raise ValueError('auth_time lies outside the session')
            if acr in self._step_up_acr:
                if auth_time is None:
                    raise ValueError('Step-up token lacks verified auth_time')
                step_up_at = auth_time

            identity = self._directory.resolve(self._issuer, subject, session)
            if (not isinstance(identity, DirectoryIdentity) or identity.active is not True
                    or (identity.subject, identity.session_id) != (subject, session)
                    or not identity.organization_id or not identity.tenant_id
                    or identity.kind not in ('HUMAN', 'WORKER')
                    or not isinstance(identity.grants, tuple)):
                raise ValueError('Session is not enrolled or has been revoked')
            for grant in identity.grants:
                if (not isinstance(grant, RoleGrant)
                        or not isinstance(grant.scope, (PlanScope, PortfolioScope))
                        or (grant.scope.organization_id, grant.scope.tenant_id) !=
                           (identity.organization_id, identity.tenant_id)
                        or not isinstance(grant.role, str) or not grant.role
                        or grant.expires_at.tzinfo is None
                        or grant.expires_at.utcoffset() is None):
                    raise ValueError('Directory returned an invalid scoped role')
            return VerifiedPrincipal(
                subject, identity.organization_id, identity.tenant_id,
                identity.kind, issued_at, expires_at, step_up_at, identity.grants)
        except Exception as exc:
            # A verifier must not disclose token claims, directory membership or
            # key distribution failures through the authentication boundary.
            raise AuthenticationFailed('Enterprise identity could not be verified') from exc
