"""Portable request loading, canonicalization and identity.

The request is the only consumer-facing input. It carries no provider-native
identity, no credential and no authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from provisioner.domain.errors import ProvisioningError

SUPPORTED_API_VERSION = 'hosting.platform/v1'
SUPPORTED_KINDS = ('WorkloadSecurityDomain',)
REQUEST_FORMAT = 'portable-hosting-request/1'


class _UniqueLoader(yaml.SafeLoader):
    """Safe loader that refuses duplicate mapping keys."""


def _construct_mapping(loader, node, deep=False):
    out = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in out:
            raise ProvisioningError('REQUEST_SYNTAX_INVALID',
                                    f'Duplicate request key: {key}',
                                    path='$')
        out[key] = loader.construct_object(value_node, deep=deep)
    return out


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _pairs(items):
    out = {}
    for key, value in items:
        if key in out:
            raise ProvisioningError('REQUEST_SYNTAX_INVALID',
                                    f'Duplicate request key: {key}', path='$')
        out[key] = value
    return out


def loads(text: str, source: str = '<memory>') -> dict:
    """Parse a YAML or JSON request without accepting duplicate keys."""
    if not isinstance(text, str) or not text.strip():
        raise ProvisioningError('REQUEST_SOURCE_UNREADABLE', 'Empty request document', path=source)
    try:
        if text.lstrip().startswith('{'):
            document = json.loads(text, object_pairs_hook=_pairs)
        else:
            document = yaml.load(text, Loader=_UniqueLoader)
    except ProvisioningError:
        raise
    except (yaml.YAMLError, ValueError) as exc:
        raise ProvisioningError('REQUEST_SYNTAX_INVALID', f'Unparseable request: {exc}',
                                path=source) from exc
    if not isinstance(document, dict):
        raise ProvisioningError('REQUEST_SYNTAX_INVALID', 'Request must be a mapping', path=source)
    return document


def load(path: Path) -> dict:
    path = Path(path)
    try:
        text = path.read_text(encoding='utf-8')
    except OSError as exc:
        raise ProvisioningError('REQUEST_SOURCE_UNREADABLE', f'Cannot read request: {exc}',
                                path=str(path)) from exc
    return loads(text, str(path))


def canonical_json(value) -> str:
    """Deterministic JSON rendering: sorted keys, no incidental whitespace."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def digest(value) -> str:
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class Request:
    """A loaded, normalized portable request with a stable identity digest."""

    document: dict
    source: str
    digest: str
    format: str = REQUEST_FORMAT
    metadata: dict = field(default_factory=dict)
    spec: dict = field(default_factory=dict)

    @property
    def api_version(self) -> str:
        return self.document['apiVersion']

    @property
    def kind(self) -> str:
        return self.document['kind']

    @property
    def tenant(self) -> str:
        return self.document['metadata']['tenant']

    @property
    def wsd(self) -> str:
        return self.document['metadata']['name']

    @property
    def owner(self) -> str:
        return self.document['metadata']['owner']

    def to_dict(self) -> dict:
        return {'format': self.format, 'source': self.source, 'digest': self.digest,
                'apiVersion': self.api_version, 'kind': self.kind,
                'metadata': self.metadata, 'spec': self.spec}


def build(document: dict, source: str = '<memory>') -> Request:
    """Wrap an already normalized request document as an immutable identity."""
    return Request(document=document, source=source, digest=digest(document),
                   metadata=dict(document.get('metadata', {})),
                   spec=dict(document.get('spec', {})))