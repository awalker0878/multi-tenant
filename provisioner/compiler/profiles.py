"""Profile resolution stage of the pipeline.

Thin, explicit composition so the pipeline has exactly one way to turn a
normalized request into a resolved profile set and to validate it.
"""
from __future__ import annotations

from provisioner.domain.errors import Diagnostics
from provisioner.domain.request import Request
from provisioner.placement import eligibility
from provisioner.profiles import validation
from provisioner.profiles.loader import Catalog, load_catalogs
from provisioner.profiles.resolver import Resolution, resolve as resolve_profiles


def catalogs(root=None) -> Catalog:
    return load_catalogs() if root is None else load_catalogs(root)


def resolve(request: Request, catalog: Catalog) -> Resolution:
    """Resolve the normalized request into one concrete profile set."""
    return resolve_profiles(request.spec, catalog)


def validate(resolution: Resolution, catalog: Catalog) -> Diagnostics:
    """Validate a resolved profile set against the catalogs and the capability registry."""
    return validation.validate(resolution, catalog, eligibility.capabilities())