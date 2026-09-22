"""Request normalization.

Normalization is the only place defaults are applied. After normalization a
request has no absent optional field: every default is explicit, reviewable and
identical between two runs. Nothing native is introduced here.

The defaults themselves are not written here. They are read from the reviewed
profile catalogs, which are the single machine-readable owner of portable policy:
the catalog states the default profile of a family, the portable service list and
its default profiles, and the request-shape defaults a caller may omit. Changing a
default is a catalog review, not a code change.
"""
from __future__ import annotations

from copy import deepcopy

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import Request, build
from provisioner.profiles.loader import Catalog, load_catalogs
from provisioner.schemas import registry

NORMALIZE_FORMAT = 'hosting-normalized-request/1'
SCHEMA = 'workload-security-domain'

#: Which catalog families own request-shape defaults. Each declares them under the
#: request's own group names, so this list adds no policy of its own.
REQUEST_DEFAULT_OWNERS = ('security', 'availability', 'recovery')

#: An absent placement pin means "not pinned"; the absence is the value, not a policy default.
PLACEMENT_DEFAULTS = {'site': None, 'cell': None}


def defaults_for(catalog: Catalog) -> dict:
    """Every portable default a request may omit, as the reviewed catalogs declare it.

    The group names are the request's own group names, so a reader can see exactly
    which part of the request each catalog default fills in.
    """
    defaults = {
        'assurance': {'profile': catalog.default('assurance')},
        'network': {'profile': catalog.default('network')},
        'capacity': {'computeProfile': catalog.default('compute'),
                     'storageProfile': catalog.default('storage')},
        'services': {name: catalog.service_default(name) for name in catalog.service_names()},
        'placement': dict(PLACEMENT_DEFAULTS),
    }
    for family in REQUEST_DEFAULT_OWNERS:
        for group, value in catalog.request_default(family).items():
            defaults.setdefault(group, {}).update(value)
    return defaults


def _apply_defaults(document: dict, defaults: dict) -> None:
    spec = document['spec']
    for key, value in defaults.items():
        if key not in spec or spec[key] is None:
            spec[key] = deepcopy(value)
            continue
        if not isinstance(value, dict):
            continue
        for sub_key, sub_value in value.items():
            spec[key].setdefault(sub_key, sub_value)


def normalize(document: dict, source: str = '<memory>', catalog: Catalog | None = None) -> Request:
    """Validate a request against the v1 contract and apply every reviewed default."""
    if not isinstance(document, dict):
        raise ProvisioningError('REQUEST_SYNTAX_INVALID', 'Request must be a mapping',
                                path=source)
    catalog = load_catalogs() if catalog is None else catalog
    candidate = deepcopy(document)
    if isinstance(candidate.get('spec'), dict):
        _apply_defaults(candidate, defaults_for(catalog))
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