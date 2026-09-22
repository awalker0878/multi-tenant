"""Shared helpers for the provisioning tests.

These tests are pure Python and Windows-safe: they never import a Linux-only
module, never contact a platform and never run Terraform or Ansible.
"""
from __future__ import annotations

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


def reference_plan(name: str = 'internal-production', compile_environment: bool = True):
    path = request_path(name)
    return create_plan(load_document(path), str(path), fixture(), catalogs(),
                       compile_environment=compile_environment)


def golden(name: str) -> dict:
    return json.loads((GOLDEN / name).read_text(encoding='utf-8'))