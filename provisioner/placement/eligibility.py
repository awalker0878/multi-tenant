"""Capability eligibility.

Placement consumes the repository's reviewed capability registry rather than
inventing a second opinion, and it treats native qualification as a mandatory
eligibility filter: a platform whose required capabilities are not natively
qualified can never produce a placed decision, however attractive its score is.
Qualification blockers and cell capability blockers stay distinct so a hold is
always actionable.

Two qualification sources exist, and they are deliberately not interchangeable:

* `RepositoryQualification` reads the reviewed capability registry. It is the only
  authoritative source, it is the default, and it is the only source an
  authoritative inventory may be planned against.
* `DeclaredQualification` reads an explicit declaration document. It is permanently
  non-authoritative, it may only be paired with a non-authoritative inventory, and
  every decision that relies on it records that declaration.
"""
from __future__ import annotations

import functools
import json
from dataclasses import dataclass
from pathlib import Path

from provisioner.repository import repository_module

PLATFORM_FAMILY = {'nutanix': 'nutanix', 'vmware': 'vmware-nsx', 'openstack': 'openstack'}
PLATFORMS = ('nutanix', 'vmware', 'openstack')

REPOSITORY_SOURCE = 'repository-capability-registry'
REPOSITORY_STATUS = 'REVIEWED_ENGINEERING_EVIDENCE_REGISTRY'
DECLARED_STATUS = 'DECLARED_NOT_NATIVE_QUALIFICATION'
DECLARATION_FORMAT = 'hosting-qualification-declaration/1'
DECLARATION = (Path(__file__).resolve().parents[1] / 'inventory' / 'fixtures'
               / 'demonstration-qualification.json')

_DECLARATION_PLATFORM_KEYS = {'product_tuple'}


def _capability_module():
    return repository_module('scripts.check_platform_capabilities')


@functools.lru_cache(maxsize=1)
def registry() -> dict:
    return _capability_module().load()


def capabilities() -> tuple[str, ...]:
    """The capability ids the repository registry actually recognises."""
    return tuple(_capability_module().CAPABILITIES)


def unknown_capabilities(required: set[str]) -> tuple[str, ...]:
    return tuple(sorted(set(required) - set(capabilities())))


def missing_cell_capabilities(cell_capabilities: tuple[str, ...], required: set[str]) -> tuple[str, ...]:
    return tuple(sorted(set(required) - set(cell_capabilities)))


@dataclass(frozen=True)
class RepositoryQualification:
    """The reviewed capability registry: the repository's only authoritative source."""

    source: str = REPOSITORY_SOURCE
    status: str = REPOSITORY_STATUS

    @property
    def authoritative(self) -> bool:
        return True

    def gate(self, platform: str, required: set[str],
             assurance_profile: str | None = None) -> tuple[bool, tuple[str, ...]]:
        if platform not in PLATFORM_FAMILY:
            raise ValueError(f'Unknown platform: {platform}')
        ok, blockers = _capability_module().eligible(registry(), PLATFORM_FAMILY[platform],
                                                     set(required), assurance_profile)
        return ok, tuple(blockers)

    def product_tuple(self, platform: str) -> str:
        return registry()['profiles'][PLATFORM_FAMILY[platform]]['product_tuple']

    def to_dict(self, platforms) -> dict:
        return {'source': self.source, 'status': self.status, 'authoritative': True,
                'product_tuples': {p: self.product_tuple(p) for p in sorted(platforms)}}


@dataclass(frozen=True)
class DeclaredQualification:
    """A declared qualification assumption. Never authoritative, never native evidence."""

    source: str
    capability_ids: tuple[str, ...]
    platforms: dict
    status: str = DECLARED_STATUS

    @property
    def authoritative(self) -> bool:
        return False

    def gate(self, platform: str, required: set[str],
             assurance_profile: str | None = None) -> tuple[bool, tuple[str, ...]]:
        if platform not in PLATFORMS:
            raise ValueError(f'Unknown platform: {platform}')
        unknown = unknown_capabilities(required)
        if unknown:
            raise ValueError(f'Unknown capability requirement: {", ".join(unknown)}')
        if platform not in self.platforms:
            return False, (f'platform:{platform}:NOT_DECLARED',)
        missing = tuple(f'capability:{name}:{DECLARED_STATUS}'
                        for name in sorted(set(required) - set(self.capability_ids)))
        return not missing, missing

    def product_tuple(self, platform: str) -> str:
        return self.platforms.get(platform, 'UNSELECTED')

    def to_dict(self, platforms) -> dict:
        return {'source': self.source, 'status': self.status, 'authoritative': False,
                'product_tuples': {p: self.product_tuple(p) for p in sorted(platforms)}}


@functools.lru_cache(maxsize=1)
def declaration() -> dict:
    """Load the repository's declared demonstration qualification assumption."""
    with DECLARATION.open(encoding='utf-8') as stream:
        document = json.load(stream)
    if document.get('format') != DECLARATION_FORMAT:
        raise ValueError(f'Unsupported qualification declaration: {document.get("format")!r}')
    if document.get('status') != DECLARED_STATUS:
        raise ValueError('A qualification declaration must not claim native qualification')
    declared = set(document.get('capability_ids', ()))
    if not declared or declared - set(capabilities()):
        raise ValueError('A qualification declaration must only name reviewed capability ids')
    platforms = document.get('platforms', {})
    if not platforms or set(platforms) - set(PLATFORMS):
        raise ValueError('A qualification declaration must only name reviewed platforms')
    for platform, entry in platforms.items():
        if set(entry) != _DECLARATION_PLATFORM_KEYS:
            raise ValueError(f'Qualification declaration for {platform} must state a product tuple')
    return document


@functools.lru_cache(maxsize=1)
def demonstration() -> DeclaredQualification:
    """The declared qualification the non-authoritative fixture corpus is planned against."""
    document = declaration()
    return DeclaredQualification(
        source='declared:' + document['source'],
        capability_ids=tuple(document['capability_ids']),
        platforms={platform: entry['product_tuple']
                   for platform, entry in document['platforms'].items()})


def qualification_for(inventory) -> RepositoryQualification | DeclaredQualification:
    """The qualification source an inventory may be planned against when none is given."""
    return RepositoryQualification() if inventory.authoritative else demonstration()


def gate(platform: str, required: set[str],
         assurance_profile: str | None = None) -> tuple[bool, tuple[str, ...]]:
    """Evaluate one platform family against the repository capability registry."""
    return RepositoryQualification().gate(platform, required, assurance_profile)


def product_tuple(platform: str) -> str:
    return RepositoryQualification().product_tuple(platform)