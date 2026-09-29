"""Independently attested project tokens and catalog bindings for OpenStack reads.

This owner does not log in, discover endpoints or prove RBAC from token bytes.
The custodian verifies Keystone scope, service catalog and native privileges;
current campaign enrollment and read-only witnesses remain independently required.
"""
from __future__ import annotations

import hashlib
import ipaddress
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock
from types import MappingProxyType

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .openstack import OpenStackServiceEndpoints, _PROJECT
from ..model import DiscoveryCampaignAuthorization, _id, _json, _utc
from ..native_credentials import NativeReadHeld, decode_json, read_protected
from ..trust import _decode, _keys, _time

COLLECTOR_ID = 'openstack-project-https-1'
# Deliberately selected API contracts, not the latest supported deployment tuple.
API_VERSIONS = MappingProxyType({'compute': '2.79', 'volume': '3.60', 'network': '2.0'})


@dataclass(frozen=True, slots=True)
class OpenStackEndpointBinding:
    service: str
    url: str
    catalog_endpoint_id: str
    connect_ip: str
    ca_digest: str


@dataclass(frozen=True, slots=True)
class OpenStackTokenMaterial:
    credential_reference: str
    project_id: str
    user_id: str
    expires_at: datetime
    token_expires_at: datetime
    endpoints: tuple[OpenStackEndpointBinding, ...]
    binding_digest: str
    token: str = field(repr=False)

    def for_service(self, service: str) -> OpenStackEndpointBinding:
        return next(endpoint for endpoint in self.endpoints if endpoint.service == service)


class SignedFileOpenStackCredentialSource:
    """Read a private, bounded, independently signed project-token envelope.

    Revisions are monotonic for this source instance. The supplied minimum must
    come from protected persistent custody; this class is not a durable floor.
    A signed catalog attestation is not itself proof of complete native visibility.
    """
    def __init__(self, path: str | Path, *, authority_public_key: Ed25519PublicKey,
                 minimum_revision: int):
        if (not isinstance(authority_public_key, Ed25519PublicKey)
                or type(minimum_revision) is not int or not 1 <= minimum_revision < 2**63):
            raise ValueError('Independent credential authority and revision floor required')
        self._path, self._key = Path(path), authority_public_key
        self._revision, self._digest = minimum_revision, None
        self._lock = RLock()

    @property
    def authority_public_key(self) -> Ed25519PublicKey:
        return self._key

    def read(self, campaign: DiscoveryCampaignAuthorization, endpoints: OpenStackServiceEndpoints,
             environment_id: str, *, checked_at: datetime) -> OpenStackTokenMaterial:
        try:
            with self._lock:
                document = _keys(decode_json(read_protected(self._path, 65536), 65536),
                                 {'binding', 'token', 'signature'})
                binding = _keys(document['binding'], {
                    'format', 'revision', 'campaignDigest', 'environmentId', 'collectorId',
                    'credentialReference', 'scopeType', 'projectId', 'userId', 'catalogDigest',
                    'regionId', 'interface', 'apiVersions', 'endpoints', 'tokenDigest',
                    'tokenIssuedAt', 'tokenExpiresAt', 'notBefore', 'expiresAt'})
                payload = _json(binding).encode('ascii')
                self._key.verify(_decode(document['signature'], 64), payload)
                token, revision = document['token'], binding['revision']
                start, end = _time(binding['notBefore']), _time(binding['expiresAt'])
                issued, expiry = _time(binding['tokenIssuedAt']), _time(binding['tokenExpiresAt'])
                if (not isinstance(campaign, DiscoveryCampaignAuthorization)
                        or campaign.scope.platform_family != 'openstack'
                        or campaign.collector_id != COLLECTOR_ID
                        or not isinstance(endpoints, OpenStackServiceEndpoints)
                        or endpoints.endpoint_id != campaign.scope.endpoint_id
                        or endpoints.project_id != campaign.scope.native_scope_id
                        or not _id(environment_id)
                        or binding['format'] != 'hosting-openstack-read-credential/1'
                        or type(revision) is not int or not 1 <= revision < 2**63
                        or binding['campaignDigest'] != campaign.digest()
                        or binding['environmentId'] != environment_id
                        or binding['collectorId'] != COLLECTOR_ID
                        or binding['scopeType'] != 'project'
                        or binding['projectId'] != endpoints.project_id
                        or not isinstance(binding['userId'], str) or not _PROJECT.fullmatch(binding['userId'])
                        or not _id(binding['credentialReference']) or not _id(binding['regionId'])
                        or binding['interface'] not in ('internal', 'public')
                        or binding['apiVersions'] != dict(API_VERSIONS)
                        or not _utc(checked_at) or not start <= campaign.issued_at <= checked_at < campaign.expires_at
                        or not campaign.expires_at <= end <= expiry or not issued <= checked_at < expiry
                        or not timedelta(0) < end - start <= timedelta(hours=1)
                        or not isinstance(token, str) or not 16 <= len(token) <= 8192
                        or any(not 33 <= ord(char) <= 126 for char in token)
                        or binding['tokenDigest'] != hashlib.sha256(token.encode('ascii')).hexdigest()
                        or not isinstance(binding['catalogDigest'], str)
                        or not re.fullmatch(r'[0-9a-f]{64}', binding['catalogDigest'])):
                    raise NativeReadHeld('Native credential does not bind this project campaign')
                native_endpoints = _keys(binding['endpoints'], set(API_VERSIONS))
                selected, identities = [], set()
                for service in API_VERSIONS:
                    row = _keys(native_endpoints[service], {'url', 'catalogEndpointId', 'connectIp', 'caDigest'})
                    address = ipaddress.ip_address(row['connectIp'])
                    if (row['url'] != endpoints.for_service(service)
                            or not isinstance(row['catalogEndpointId'], str)
                            or not _PROJECT.fullmatch(row['catalogEndpointId'])
                            or row['catalogEndpointId'] in identities
                            or str(address) != row['connectIp'] or address.is_unspecified or address.is_multicast
                            or '%' in row['connectIp']
                            or not isinstance(row['caDigest'], str)
                            or not re.fullmatch(r'[0-9a-f]{64}', row['caDigest'])):
                        raise NativeReadHeld('Native service endpoint is not the selected catalog binding')
                    identities.add(row['catalogEndpointId'])
                    selected.append(OpenStackEndpointBinding(service, row['url'], row['catalogEndpointId'],
                                                            str(address), row['caDigest']))
                digest = hashlib.sha256(payload).hexdigest()
                if (revision < self._revision or revision == self._revision
                        and self._digest is not None and digest != self._digest):
                    raise NativeReadHeld('Native credential binding was rolled back')
                self._revision, self._digest = revision, digest
                return OpenStackTokenMaterial(binding['credentialReference'], binding['projectId'],
                    binding['userId'], end, expiry, tuple(selected), digest, token)
        except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError,
                OverflowError, InvalidSignature, NativeReadHeld):
            raise NativeReadHeld('Signed OpenStack read credential is unavailable or invalid') from None
