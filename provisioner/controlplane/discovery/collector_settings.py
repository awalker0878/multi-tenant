"""Protected one-shot collector configuration; no credentials or authority are issued."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .model import _id, _json
from .native_credentials import decode_json, read_protected
from .publication_https import DiscoveryPublishTarget
from .trust import _decode, _keys


MAX_CONFIG_BYTES = 65536


def protected_path(value: object) -> Path:
    """Require an explicit absolute path, without expansion or normalization."""
    if (not isinstance(value, str) or not 1 <= len(value) <= 4096
            or value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError('An explicit protected path is required')
    path = Path(value)
    if (not path.is_absolute() or str(path) != value or value.startswith('//')
            or any(part in ('.', '..') for part in path.parts)):
        raise ValueError('Relative or ambiguous configuration paths are forbidden')
    return path


def revision(value: object) -> int:
    if type(value) is not int or not 1 <= value < 2**63:
        raise ValueError('A protected positive revision floor is required')
    return value


def bounded_timeout(value: object) -> float:
    if type(value) not in (int, float) or not 0 < value <= 15:
        raise ValueError('A finite bounded timeout is required')
    return float(value)


@dataclass(frozen=True, slots=True)
class AuthoritySettings:
    policy_file: Path
    root_key: bytes = field(repr=False)
    minimum_revision: int

    @classmethod
    def parse(cls, document: object) -> AuthoritySettings:
        row = _keys(document, {'policyFile', 'rootKey', 'minimumRevision'})
        return cls(protected_path(row['policyFile']), _decode(row['rootKey'], 32),
                   revision(row['minimumRevision']))


@dataclass(frozen=True, slots=True)
class DiscoveryCollectorSettings:
    """Snapshot of bounded file configuration, not an externally issued grant.

    Optional action-specific sections are unnecessary when resuming retained bytes.
    Nested native settings are kept as immutable canonical JSON, not mutable dicts.
    All role, signature, endpoint and freshness checks remain in the active owners.
    """
    campaign_file: Path
    outbox_root: Path
    trust: AuthoritySettings
    witness: AuthoritySettings
    native_json: str | None = field(default=None, repr=False)
    signer_file: Path | None = field(default=None, repr=False)
    signer_key_id: str | None = None
    publish_target: DiscoveryPublishTarget | None = field(default=None, repr=False)
    publish_timeout: float = 5.0

    @classmethod
    def from_file(cls, path: str | Path) -> DiscoveryCollectorSettings:
        raw = read_protected(protected_path(str(path)), MAX_CONFIG_BYTES)
        doc = decode_json(raw, MAX_CONFIG_BYTES)
        required = {'format', 'campaignFile', 'outboxRoot', 'trust', 'witness'}
        optional = {'native', 'signer', 'publisher'}
        if (not isinstance(doc, dict) or not required <= doc.keys()
                or not set(doc) <= required | optional
                or doc['format'] != 'hosting-discovery-collector/1'):
            raise ValueError('Exact versioned collector configuration is required')
        trust, witness = AuthoritySettings.parse(doc['trust']), AuthoritySettings.parse(doc['witness'])
        if trust.root_key == witness.root_key:
            raise ValueError('Campaign and native witness authorities must be independent')
        native_json = None
        if 'native' in doc:
            native = _keys(doc['native'], {'profile', 'credentialFile', 'authorityKey',
                'minimumRevision', 'caBundles', 'selection', 'timeoutSeconds', 'maxResponseBytes'})
            if (not _id(native['profile']) or not isinstance(native['selection'], dict)
                    or not isinstance(native['caBundles'], dict) or not 1 <= len(native['caBundles']) <= 3
                    or type(native['maxResponseBytes']) is not int
                    or not 1024 <= native['maxResponseBytes'] <= 4*1024*1024):
                raise ValueError('Bounded native collector settings are required')
            protected_path(native['credentialFile'])
            if _decode(native['authorityKey'], 32) == trust.root_key:
                raise ValueError('Native material cannot use the campaign root')
            revision(native['minimumRevision'])
            bounded_timeout(native['timeoutSeconds'])
            for name, value in native['caBundles'].items():
                if not _id(name):
                    raise ValueError('Invalid native trust selector')
                protected_path(value)
            native_json = _json(native)
        signer_file = signer_id = None
        if 'signer' in doc:
            signer = _keys(doc['signer'], {'keyFile', 'keyId'})
            signer_file, signer_id = protected_path(signer['keyFile']), signer['keyId']
            if not _id(signer_id):
                raise ValueError('An enrolled result signing identity is required')
        target, timeout = None, 5.0
        if 'publisher' in doc:
            pub = _keys(doc['publisher'], {'origin', 'connectIp', 'trustDomain', 'caBundle', 'caDigest',
                'crlBundle', 'crlDigest', 'clientCertificate', 'certificateDigest', 'clientKey', 'timeoutSeconds'})
            timeout = bounded_timeout(pub['timeoutSeconds'])
            target = DiscoveryPublishTarget(origin=pub['origin'], connect_ip=pub['connectIp'],
                trust_domain=pub['trustDomain'], ca_bundle=protected_path(pub['caBundle']),
                ca_digest=pub['caDigest'], crl_bundle=protected_path(pub['crlBundle']),
                crl_digest=pub['crlDigest'], client_certificate=protected_path(pub['clientCertificate']),
                certificate_digest=pub['certificateDigest'], client_key=protected_path(pub['clientKey']))
        return cls(protected_path(doc['campaignFile']), protected_path(doc['outboxRoot']),
                   trust, witness, native_json, signer_file, signer_id, target, timeout)
