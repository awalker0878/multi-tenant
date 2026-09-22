"""The Terraform execution boundary.

The provisioner never runs Terraform. It resolves which reviewed stack a decision
belongs to, refuses a scope the reviewed catalog does not declare, and hands the
compiled inputs to the existing execution tooling. State and backends belong to
the stack owner.
"""
from __future__ import annotations

import functools

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import loads
from provisioner.repository import ROOT

CATALOG_PATH = ROOT / 'terraform' / 'catalog.json'
CATALOG_FORMAT = 'hosting-terraform-catalog/1'
PHASES = ('domains', 'workloads')
OWNER_SCOPES = ('wsd', 'security-edge')


@functools.lru_cache(maxsize=1)
def catalog() -> dict:
    """The reviewed Terraform catalog, refused if it is malformed or duplicated."""
    try:
        document = loads(CATALOG_PATH.read_text(encoding='utf-8'), str(CATALOG_PATH))
    except OSError as exc:
        raise ProvisioningError('ENVIRONMENT_CONTRACT_INVALID',
                                f'Unreadable Terraform catalog: {exc}',
                                path='terraform/catalog.json') from exc
    if document.get('format') != CATALOG_FORMAT:
        raise ProvisioningError('ENVIRONMENT_CONTRACT_INVALID',
                                f'Unknown Terraform catalog format {document.get("format")!r}',
                                path='terraform/catalog.json')
    entries = document.get('entries')
    if not isinstance(entries, list) or not entries:
        raise ProvisioningError('ENVIRONMENT_CONTRACT_INVALID', 'Empty Terraform catalog',
                                path='terraform/catalog.json')
    seen: set[str] = set()
    for entry in entries:
        if not {'id', 'platform', 'kind', 'module', 'root', 'owner_scope'} <= set(entry):
            raise ProvisioningError('ENVIRONMENT_CONTRACT_INVALID',
                                    f'Incomplete Terraform catalog entry {entry.get("id")!r}',
                                    path='terraform/catalog.json')
        if entry['id'] in seen:
            raise ProvisioningError('ENVIRONMENT_CONTRACT_INVALID',
                                    f'Duplicate Terraform catalog entry {entry["id"]!r}',
                                    path='terraform/catalog.json')
        seen.add(entry['id'])
        if entry['owner_scope'] not in OWNER_SCOPES:
            raise ProvisioningError('ENVIRONMENT_CONTRACT_INVALID',
                                    f'Unknown Terraform owner scope {entry["owner_scope"]!r}',
                                    path='terraform/catalog.json')
    return document


def composition(platform: str, phase: str) -> dict:
    """The reviewed composition root for one platform phase."""
    if phase not in PHASES:
        raise ProvisioningError('UNSUPPORTED_FEATURE', f'Unknown Terraform phase {phase!r}',
                                path='terraform/catalog.json')
    expected = f'terraform/stacks/wsd/{platform}/{phase}'
    for entry in catalog()['entries']:
        if entry['kind'] == 'composition' and entry['root'] == expected:
            return dict(entry)
    raise ProvisioningError('ENVIRONMENT_CONTRACT_INVALID',
                            f'No reviewed composition for {platform}/{phase}',
                            path='terraform/catalog.json', details={'expected_root': expected})


def assert_scopes(scopes: list[dict], platform: str) -> list[dict]:
    """Refuse any compiled scope the reviewed catalog does not declare."""
    checked = []
    for scope in scopes:
        declared = composition(platform, scope['scope']['phase'])
        if scope['root'] != declared['root']:
            raise ProvisioningError('ENVIRONMENT_CONTRACT_INVALID',
                                    f'Compiled scope root {scope["root"]!r} is not the reviewed '
                                    f'composition {declared["root"]!r}',
                                    path='terraform/catalog.json')
        checked.append({**scope, 'catalog_id': declared['id'],
                        'owner_scope': declared['owner_scope'],
                        'status': 'DRAFT_DISABLED_NOT_AUTHORIZED',
                        'backend': 'owner-provisioned; matched to state_key by its owner'})
    return checked


def to_dict(platform: str) -> dict:
    return {'format': CATALOG_FORMAT, 'platform': platform,
            'compositions': {phase: composition(platform, phase) for phase in PHASES},
            'limits': ['Terraform execution and state ownership remain with the stack owner',
                       'A compiled scope is disabled and unauthorized']}