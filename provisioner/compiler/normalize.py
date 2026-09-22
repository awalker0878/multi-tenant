"""Request normalization.

Normalization is the only place defaults are applied. After normalization a
request has no absent optional field: every default is explicit, reviewable and
identical between two runs. Nothing native is introduced here.
"""
from __future__ import annotations

from copy import deepcopy

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import Request, build
from provisioner.profiles.resolver import DEFAULT_NETWORK_PROFILE, DEFAULT_SERVICE_PROFILES
from provisioner.schemas import registry

NORMALIZE_FORMAT = 'hosting-normalized-request/1'
SCHEMA = 'workload-security-domain'

DEFAULTS = {
    'assurance': {'profile': 'standard'},
    'network': {'profile': DEFAULT_NETWORK_PROFILE},
    'capacity': {'computeProfile': 'medium', 'storageProfile': 'standard'},
    'recovery': {'enabled': False},
    'services': dict(DEFAULT_SERVICE_PROFILES),
    'exposure': {'publicIngress': False, 'internetEgress': False},
    'zones': {'operations': {'enabled': True}, 'restricted': {'enabled': True}},
    'placement': {'site': None, 'cell': None},
}


def _apply_defaults(document: dict) -> None:
    spec = document['spec']
    for key, value in DEFAULTS.items():
        if key not in spec or spec[key] is None:
            spec[key] = deepcopy(value)
            continue
        if not isinstance(value, dict):
            continue
        for sub_key, sub_value in value.items():
            spec[key].setdefault(sub_key, sub_value)


def normalize(document: dict, source: str = '<memory>') -> Request:
    """Validate a request against the v1 contract and apply every default."""
    if not isinstance(document, dict):
        raise ProvisioningError('REQUEST_SYNTAX_INVALID', 'Request must be a mapping',
                                path=source)
    candidate = deepcopy(document)
    if isinstance(candidate.get('spec'), dict):
        _apply_defaults(candidate)
    problems = registry.validate_named(candidate, SCHEMA, path=source)
    if problems:
        first = problems[0]
        raise ProvisioningError('SCHEMA_VALIDATION_FAILED',
                                f'Request does not satisfy {SCHEMA}: {first["message"]}',
                                path=first['path'],
                                details={'violations': problems})
    return build(candidate, source=source)


def zones(request: Request) -> tuple[str, ...]:
    """The enabled zone keys, in canonical order."""
    spec = request.spec.get('zones', {})
    enabled = []
    if spec.get('operations', {}).get('enabled'):
        enabled.append('OZ')
    if spec.get('restricted', {}).get('enabled'):
        enabled.append('RZ')
    return tuple(enabled)