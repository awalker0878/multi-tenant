"""Identity service declaration.

Identity is a directory handoff. The provisioner records the realm and the
reviewed directory servers so the workload can be joined by its owner; it never
creates accounts and never holds directory credentials.
"""
from __future__ import annotations

from provisioner.domain.errors import ProvisioningError

SERVICE = 'identity'
REQUIRED_ENDPOINTS = ('realm', 'servers')


def validate(endpoints: dict, site: str) -> None:
    missing = [name for name in REQUIRED_ENDPOINTS if not endpoints.get(name)]
    if missing:
        raise ProvisioningError('SERVICE_UNAVAILABLE',
                                f'{SERVICE} binding at {site} is incomplete: {missing}',
                                path=f'inventory.services.{SERVICE}',
                                details={'required_endpoints': list(REQUIRED_ENDPOINTS)})


def describe(endpoints: dict) -> dict:
    return {'realm': endpoints['realm'],
            'servers': list(endpoints['servers']),
            'join_mode': 'directory-joined-no-local-authority',
            'obligations': ['The owner performs the directory join',
                            'No directory credential is stored by the provisioner']}