"""The Ansible execution boundary.

Ansible realizes guest-side state only. It is reached through the reviewed
playbook catalog, and only after the platform phase has produced the identities a
guest needs. The provisioner never runs a playbook.
"""
from __future__ import annotations

import functools

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import loads
from provisioner.repository import asset_path

CATALOG_PATH = asset_path('ansible/catalog.json')
CATALOG_FORMAT = 'hosting-ansible-catalog/1'
PROFILES = ('local', 'native-linux')

# Reviewed playbooks this pipeline may name as a downstream scope.
GUEST_SCOPES = {
    'local': ('playbooks/local/validate_readback.yml',),
    'native-linux': ('playbooks/native/configure_linux.yml',),
}


@functools.lru_cache(maxsize=1)
def catalog() -> dict:
    try:
        document = loads(CATALOG_PATH.read_text(encoding='utf-8'), str(CATALOG_PATH))
    except OSError as exc:
        raise ProvisioningError('ENVIRONMENT_CONTRACT_INVALID',
                                f'Unreadable Ansible catalog: {exc}',
                                path='ansible/catalog.json') from exc
    if document.get('format') != CATALOG_FORMAT:
        raise ProvisioningError('ENVIRONMENT_CONTRACT_INVALID',
                                f'Unknown Ansible catalog format {document.get("format")!r}',
                                path='ansible/catalog.json')
    rows = document.get('playbooks')
    if not isinstance(rows, list) or not rows:
        raise ProvisioningError('ENVIRONMENT_CONTRACT_INVALID', 'Empty Ansible catalog',
                                path='ansible/catalog.json')
    seen: set[str] = set()
    for row in rows:
        if not {'path', 'profile'} <= set(row):
            raise ProvisioningError('ENVIRONMENT_CONTRACT_INVALID',
                                    'Incomplete Ansible catalog entry',
                                    path='ansible/catalog.json')
        if row['path'] in seen:
            raise ProvisioningError('ENVIRONMENT_CONTRACT_INVALID',
                                    f'Duplicate Ansible catalog entry {row["path"]!r}',
                                    path='ansible/catalog.json')
        seen.add(row['path'])
        if row['profile'] not in PROFILES:
            raise ProvisioningError('ENVIRONMENT_CONTRACT_INVALID',
                                    f'Unknown Ansible profile {row["profile"]!r}',
                                    path='ansible/catalog.json')
    return document


def scope(profile: str, phase: str) -> dict:
    """The reviewed guest scope for one platform phase, or an explicit hold."""
    if profile not in PROFILES:
        raise ProvisioningError('UNSUPPORTED_FEATURE', f'Unknown Ansible profile {profile!r}',
                                path='ansible/catalog.json')
    registered = {row['path'] for row in catalog()['playbooks']}
    selected = [p for p in GUEST_SCOPES[profile] if p in registered]
    missing = [p for p in GUEST_SCOPES[profile] if p not in registered]
    if missing:
        raise ProvisioningError('ENVIRONMENT_CONTRACT_INVALID',
                                f'Ansible scope names unregistered playbooks: {missing}',
                                path='ansible/catalog.json')
    return {'profile': profile, 'phase': phase, 'playbooks': sorted(selected),
            'status': 'HELD_PENDING_PLATFORM_IDENTITY',
            'requires': 'domain and workload identities observed natively first',
            'native_contact': False,
            'limits': ['Guest execution requires a live, authorized target']}


def to_dict() -> dict:
    return {'format': CATALOG_FORMAT,
            'profiles': {p: scope(p, 'workloads') for p in PROFILES},
            'limits': ['Ansible realizes guest state only and is never run by this repository']}
