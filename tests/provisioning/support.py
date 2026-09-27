"""Shared helpers for the provisioning tests.

These tests are pure Python and Windows-safe: they never import a Linux-only
module, never contact a platform and never run Terraform or Ansible.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import load as load_document
from provisioner.execution.plan import create_plan
from provisioner.inventory.model import fixture
from provisioner.profiles.loader import load_catalogs
from tools import compile_wsd

ROOT = Path(__file__).resolve().parents[2]
REQUESTS = ROOT / 'examples' / 'requests'
REQUEST = REQUESTS / 'internal-production.yaml'
GOLDEN = ROOT / 'examples' / 'golden'
RESOLVED = ROOT / 'examples' / 'resolved'

#: The reviewed reference corpus. Every request here must validate and resolve.
REFERENCE_REQUESTS = ('internal-development', 'internal-production', 'multi-tier',
                       'recovery-enabled', 'storage-heavy')


def catalogs():
    return load_catalogs()


def request_path(name: str) -> Path:
    return REQUESTS / f'{name}.yaml'


def reference_document(name: str = 'internal-production') -> dict:
    return load_document(request_path(name))


#: The reviewed per-platform fixture inventory for the cross-platform contract.
REFERENCE_FIXTURES = {'nutanix': 'nutanix-reference', 'vmware': 'vmware-reference',
                      'openstack': 'openstack-reference'}

#: The reviewed platforms, in the order the cross-platform corpus indexes them.
PLATFORMS = ('nutanix', 'openstack', 'vmware')


def reference_fixture(platform: str):
    """The reviewed fixture inventory that represents one platform."""
    return fixture(REFERENCE_FIXTURES[platform])


def native_field_names(platform: str) -> set:
    """Every provider-native input name one platform's realization declares.

    Read from the reviewed compiler declaration, so the portable request contract is
    checked against the artifact the platform layer consumes rather than a second
    hand-written copy of the same list.
    """
    return set(compile_wsd.PLACEMENT[platform]) | set(compile_wsd.NETWORK[platform])


def platform_request(platform: str, name: str = 'internal-production') -> dict:
    """The reviewed reference request with only the platform preference selected."""
    document = copy.deepcopy(reference_document(name))
    document['spec']['platform']['preference'] = platform
    return document


def portable_request(name: str = 'internal-production') -> dict:
    """The reference request body with no platform selected at all."""
    document = copy.deepcopy(reference_document(name))
    document['spec']['platform'].pop('preference')
    return document


def platform_plan(platform: str, name: str = 'internal-production',
                  compile_environment: bool = True, generation: int = 1):
    """Plan the reviewed reference request against that platform's reviewed fixture."""
    path = request_path(name)
    return create_plan(platform_request(platform, name), str(path),
                       reference_fixture(platform), catalogs(),
                       compile_environment=compile_environment, generation=generation)


def platform_refusal(declared: str, fixture_platform: str,
                     name: str = 'internal-production'):
    """Plan a request that selects one platform against another platform's fixture.

    A reviewed fixture represents exactly one platform, so this combination must be
    refused rather than placed somewhere else. The refusal is returned as raised; a
    plan that succeeded instead is returned so the caller can fail on it.
    """
    path = request_path(name)
    try:
        return create_plan(platform_request(declared, name), str(path),
                           reference_fixture(fixture_platform), catalogs())
    except ProvisioningError as exc:
        return exc


def reference_plan(name: str = 'internal-production', compile_environment: bool = True,
                   generation: int = 1):
    path = request_path(name)
    return create_plan(load_document(path), str(path), fixture(), catalogs(),
                       compile_environment=compile_environment, generation=generation)


def golden(name: str) -> dict:
    return json.loads((GOLDEN / name).read_text(encoding='utf-8'))


def source_commit() -> str:
    """The commit the working checkout reports, for handoff-binding tests."""
    from provisioner import repository
    return repository.source_commit()['commit']
