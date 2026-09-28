"""Private, independently signed vCenter session material for one campaign.

An external native credential custodian signs the binding after verifying the
session's identity, read-only scope, installed API and endpoint. This module does
not mint sessions, issue signatures or infer native privileges from a secret.
Live issuer/enrollment/RBAC verification is separate and mandatory at use.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import os
import re
import stat
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .adapters.vmware_rest import API_RELEASE, PROFILE, FolderSelection
from .model import DiscoveryCampaignAuthorization, _id, _json, _unique_pairs, _utc
from .trust import _decode, _keys, _time


class NativeReadHeld(RuntimeError):
    """A native read was refused; never include native bodies or secret values."""


def read_protected(path: Path, limit: int, *, secret: bool = True) -> bytes:
    """No symlink/FIFO fallback; ownership and bounds are checked on the open FD."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, os.geteuid())
                or info.st_mode & (0o077 if secret else 0o022) or info.st_size > limit):
            raise NativeReadHeld('Native read configuration is not protected')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            value = stream.read(limit + 1)
        if len(value) > limit:
            raise NativeReadHeld('Native read configuration exceeds its byte limit')
        return value
    finally:
        os.close(fd)


def decode_json(raw: bytes, limit: int) -> object:
    """Bounded, duplicate-free finite JSON with an explicit nesting limit."""
    if len(raw) > limit:
        raise ValueError('Native JSON exceeds byte limit')
    def integer(text):
        value = int(text)
        if not -(2**63) <= value < 2**63:
            raise ValueError('Native integer exceeds signed 64-bit range')
        return value
    def floating(text):
        value = float(text)
        if not math.isfinite(value):
            raise ValueError('Nonfinite native number')
        return value
    result = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_pairs,
                        parse_int=integer, parse_float=floating, parse_constant=floating)
    pending, count = [(result, 0)], 0
    while pending:
        value, depth = pending.pop()
        count += 1
        if depth > 32 or count > 250000:
            raise ValueError('Native JSON structural budget exceeded')
        children = value.values() if isinstance(value, dict) else value if isinstance(value, list) else ()
        pending.extend((child, depth + 1) for child in children)
    return result


def selection_digest(selection: FolderSelection) -> str:
    return hashlib.sha256(_json({'apiRelease': selection.api_release,
        'folderIds': list(selection.folder_ids),
        'folderCoverageDigest': selection.coverage_digest}).encode('ascii')).hexdigest()


@dataclass(frozen=True, slots=True)
class VmwareSessionMaterial:
    credential_reference: str
    origin: str
    connect_ip: str
    ca_digest: str
    expires_at: datetime
    binding_digest: str
    token: str = field(repr=False)


class SignedFileVmwareCredentialSource:
    """Reload signed material on every use; no cached-secret or stale fallback.

    The signing key belongs to the independently administered native credential
    custodian, not the campaign issuer or collector. Persist the revision floor
    across restarts and use a new revision for any binding or token rotation.
    The envelope contains a high-entropy session token, never a login password.
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

    def read(self, campaign: DiscoveryCampaignAuthorization, selection: FolderSelection,
             environment_id: str, *, checked_at: datetime) -> VmwareSessionMaterial:
        try:
            with self._lock:
                document = _keys(decode_json(read_protected(self._path, 32768), 32768),
                                 {'binding', 'token', 'signature'})
                binding = _keys(document['binding'], {
                    'format', 'revision', 'campaignDigest', 'environmentId', 'collectorId',
                    'selectionDigest', 'credentialReference', 'apiRelease', 'origin',
                    'connectIp', 'caDigest', 'tokenDigest', 'notBefore', 'expiresAt'})
                payload = _json(binding).encode('ascii')
                self._key.verify(_decode(document['signature'], 64), payload)
                token = document['token']
                start, end = _time(binding['notBefore']), _time(binding['expiresAt'])
                revision = binding['revision']
                if (not isinstance(campaign, DiscoveryCampaignAuthorization)
                        or not isinstance(selection, FolderSelection) or selection.scope != campaign.scope
                        or campaign.scope.platform_family != 'vmware' or campaign.collector_id != PROFILE
                        or selection.api_release != API_RELEASE or not _id(environment_id)
                        or binding['format'] != 'hosting-vmware-read-credential/1'
                        or type(revision) is not int or not 1 <= revision < 2**63
                        or binding['campaignDigest'] != campaign.digest()
                        or binding['environmentId'] != environment_id
                        or binding['collectorId'] != PROFILE
                        or binding['selectionDigest'] != selection_digest(selection)
                        or binding['apiRelease'] != API_RELEASE
                        or not _id(binding['credentialReference'])
                        or not _utc(checked_at) or not start <= campaign.issued_at <= checked_at < campaign.expires_at
                        or not campaign.expires_at <= end or not timedelta(0) < end - start <= timedelta(hours=1)
                        or not isinstance(token, str) or not 16 <= len(token) <= 8192
                        or any(not 33 <= ord(char) <= 126 for char in token)
                        or binding['tokenDigest'] != hashlib.sha256(token.encode('ascii')).hexdigest()
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
                        or '%' in origin or '\\' in origin or origin != origin.strip()
                        or url.port is not None and not 1 <= url.port <= 65535
                        or address.is_unspecified or address.is_multicast
                        or str(address) != binding['connectIp']):
                    raise ValueError('Invalid pinned native endpoint')
                digest = hashlib.sha256(payload).hexdigest()
                if (revision < self._revision or revision == self._revision
                        and self._digest is not None and digest != self._digest):
                    raise NativeReadHeld('Native credential binding was rolled back')
                self._revision, self._digest = revision, digest
                return VmwareSessionMaterial(binding['credentialReference'], origin,
                    str(address), binding['caDigest'], end, digest, token)
        except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError,
                OverflowError, InvalidSignature, NativeReadHeld):
            raise NativeReadHeld('Signed native read credential is unavailable or invalid') from None
