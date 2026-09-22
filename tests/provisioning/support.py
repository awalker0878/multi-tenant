"""Shared helpers for the provisioning tests.

These tests are pure Python and Windows-safe: they never import a Linux-only
module, never contact a platform and never run Terraform or Ansible.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from provisioner.domain.request import load as load_document
from provisioner.execution.plan import create_plan
from provisioner.inventory.model import fixture
from provisioner.profiles.loader import load_catalogs

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


def reference_fixture(platform: str):
    """The reviewed fixture inventory that represents one platform."""
    return fixture(REFERENCE_FIXTURES[platform])


def platform_request(platform: str, name: str = 'internal-production') -> dict:
    """The reviewed reference request with only the platform preference selected."""
    document = copy.deepcopy(reference_document(name))
    document['spec']['platform']['preference'] = platform
    return document


def platform_plan(platform: str, name: str = 'internal-production',
                  compile_environment: bool = True):
    """Plan the reviewed reference request against that platform's reviewed fixture."""
    path = request_path(name)
    return create_plan(platform_request(platform, name), str(path),
                       reference_fixture(platform), catalogs(),
                       compile_environment=compile_environment)


def reference_plan(name: str = 'internal-production', compile_environment: bool = True):
    path = request_path(name)
    return create_plan(load_document(path), str(path), fixture(), catalogs(),
                       compile_environment=compile_environment)


def golden(name: str) -> dict:
    return json.loads((GOLDEN / name).read_text(encoding='utf-8'))