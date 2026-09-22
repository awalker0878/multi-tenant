"""Capability eligibility.

Placement must consume the repository's capability registry rather than invent a
second opinion. The registry is engineering evidence, not placement authority, so
this module reports blockers and never turns a missing native qualification into
an eligible platform.
"""
from __future__ import annotations

import functools

from provisioner.repository import repository_module

PLATFORM_FAMILY = {'nutanix': 'nutanix', 'vmware': 'vmware-nsx', 'openstack': 'openstack'}
PLATFORMS = ('nutanix', 'vmware', 'openstack')


@functools.lru_cache(maxsize=1)
def registry() -> dict:
    return repository_module('scripts.check_platform_capabilities').load()


def gate(platform: str, required: set[str], assurance_profile: str | None = None) -> tuple[bool, tuple[str, ...]]:
    """Evaluate one platform family against the repository capability registry."""
    if platform not in PLATFORM_FAMILY:
        raise ValueError(f'Unknown platform: {platform}')
    module = repository_module('scripts.check_platform_capabilities')
    ok, blockers = module.eligible(registry(), PLATFORM_FAMILY[platform], set(required),
                                   assurance_profile)
    return ok, tuple(blockers)


def product_tuple(platform: str) -> str:
    return registry()['profiles'][PLATFORM_FAMILY[platform]]['product_tuple']


def missing_cell_capabilities(cell_capabilities: tuple[str, ...], required: set[str]) -> tuple[str, ...]:
    return tuple(sorted(set(required) - set(cell_capabilities)))


def unknown_capabilities(required: set[str]) -> tuple[str, ...]:
    known = set(repository_module('scripts.check_platform_capabilities').CAPABILITIES)
    return tuple(sorted(set(required) - known))


def capabilities() -> tuple[str, ...]:
    """The capability ids the repository registry actually recognises."""
    return tuple(repository_module('scripts.check_platform_capabilities').CAPABILITIES)