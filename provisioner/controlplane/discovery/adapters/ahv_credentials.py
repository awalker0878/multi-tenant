"""Independently signed Prism API-key material for the AHV adapter.

An external custodian attests native identity, read-only scope and endpoint.
This implementation neither mints sessions nor infers privileges from a token.
The generic custody helpers deliberately contain no vendor imports or aliases.
"""
from __future__ import annotations

import hashlib
import ipaddress
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .ahv import API_VERSION, COLLECTOR_ID, _uuid
from ..model import DiscoveryCampaignAuthorization, _id, _json, _utc
from ..native_credentials import NativeReadHeld, decode_json, read_protected
from ..trust import _decode, _keys, _time


@dataclass(frozen=True, slots=True)
class AhvApiKeyMaterial:
    credential_reference: str
    origin: str
    connect_ip: str
    ca_digest: str
    expires_at: datetime
    binding_digest: str
    service_account_id: str
    api_key: str = field(repr=False)


class SignedFileAhvCredentialSource:
    """Reload signed material on every use; no cached-secret or stale fallback.

    The signing key belongs to the independently administered native credential
    custodian, not the campaign issuer or collector. Persist the revision floor
    across restarts and use a new revision for any binding or API-key rotation.
    The envelope contains a service-account API key, never a login password.
    Its short validity is a custody lease, not the native key expiration.
    Independent native RBAC and key revocation witnesses are still required.
    """
    def __init__(self, path: str | Path, *, authority_public_key: Ed25519PublicKey,
                 minimum_revision: int):
        if (not isinstance(authority_public_key, Ed25519PublicKey)
                or type(minimum_revision) is not int or not 1 <= minimum_revision < 2**63):
            raise ValueError('Pinned native credential authority and revision floor required')
        self._path = Path(path)
        self._key = authority_public_key
        self._revision, self._digest = minimum_revision, None
        self._lock = RLock()

    @property
    def authority_public_key(self) -> Ed25519PublicKey:
        return self._key

    def read(self, campaign: DiscoveryCampaignAuthorization,
             environment_id: str, *, checked_at: datetime) -> AhvApiKeyMaterial:
        try:
            with self._lock:
                document = _keys(decode_json(read_protected(self._path, 32768), 32768),
                                 {'binding', 'apiKey', 'signature'})
                binding = _keys(document['binding'], {
                    'format', 'revision', 'campaignDigest', 'environmentId', 'collectorId',
                    'serviceAccountId', 'credentialReference', 'apiVersion', 'origin',
                    'connectIp', 'caDigest', 'apiKeyDigest', 'notBefore', 'expiresAt'})
                payload = _json(binding).encode('ascii')
                self._key.verify(_decode(document['signature'], 64), payload)
                token = document['apiKey']
                start, end = _time(binding['notBefore']), _time(binding['expiresAt'])
                revision = binding['revision']
                if (not isinstance(campaign, DiscoveryCampaignAuthorization)
                        or campaign.scope.platform_family != 'nutanix' or campaign.collector_id != COLLECTOR_ID
                        or _uuid(campaign.scope.native_scope_id) != campaign.scope.native_scope_id
                        or not _id(environment_id)
                        or binding['format'] != 'hosting-ahv-read-credential/1'
                        or type(revision) is not int or not 1 <= revision < 2**63
                        or binding['campaignDigest'] != campaign.digest()
                        or binding['environmentId'] != environment_id
                        or binding['collectorId'] != COLLECTOR_ID
                        or _uuid(binding['serviceAccountId']) != binding['serviceAccountId']
                        or binding['serviceAccountId'] is None
                        or binding['apiVersion'] != API_VERSION
                        or not _id(binding['credentialReference'])
                        or not _utc(checked_at) or not start <= campaign.issued_at <= checked_at < campaign.expires_at
                        or not campaign.expires_at <= end or not timedelta(0) < end - start <= timedelta(hours=1)
                        or not isinstance(token, str) or not 16 <= len(token) <= 8192
                        or any(not 33 <= ord(char) <= 126 for char in token)
                        or binding['apiKeyDigest'] != hashlib.sha256(token.encode('ascii')).hexdigest()
                        or not isinstance(binding['caDigest'], str)
                        or not re.fullmatch(r'[0-9a-f]{64}', binding['caDigest'])):
                    raise NativeReadHeld('Native credential does not bind this campaign')
                origin = binding['origin']
                if not isinstance(origin, str) or len(origin) > 512:
                    raise ValueError('Invalid native origin')
                url = urlsplit(origin)
                address = ipaddress.ip_address(binding['connectIp'])
                host = url.hostname
                if (url.scheme != 'https' or not host or url.username is not None
                        or url.password is not None or url.path or url.query or url.fragment
                        or not re.fullmatch(r'[a-z0-9.:-]+', host)
                        or '%' in origin or '\\' in origin or any(not 33 <= ord(c) <= 126 for c in origin)
                        or url.port is not None and not 1 <= url.port <= 65535
                        or address.is_unspecified or address.is_multicast
                        or str(address) != binding['connectIp']):
                    raise ValueError('Invalid pinned native endpoint')
                digest = hashlib.sha256(payload).hexdigest()
                if (revision < self._revision or revision == self._revision
                        and self._digest is not None and digest != self._digest):
                    raise NativeReadHeld('Native credential binding was rolled back')
                self._revision, self._digest = revision, digest
                return AhvApiKeyMaterial(binding['credentialReference'], origin,
                    str(address), binding['caDigest'], end, digest, binding['serviceAccountId'], token)
        except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError,
                OverflowError, InvalidSignature, NativeReadHeld):
            raise NativeReadHeld('Signed native read credential is unavailable or invalid') from None
