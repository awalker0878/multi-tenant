"""Backup service declaration.

Backup is an isolated target handoff. The provisioner records the reviewed
target. It never schedules a job, never holds backup credentials and never claims
a restore has been exercised.
"""
from __future__ import annotations

from provisioner.domain.errors import ProvisioningError

SERVICE = 'backup'
REQUIRED_ENDPOINTS = ('target',)


def validate(endpoints: dict, site: str) -> None:
    missing = [name for name in REQUIRED_ENDPOINTS if not endpoints.get(name)]
    if missing:
        raise ProvisioningError('SERVICE_UNAVAILABLE',
                                f'{SERVICE} binding at {site} is incomplete: {missing}',
                                path=f'inventory.services.{SERVICE}',
                                details={'required_endpoints': list(REQUIRED_ENDPOINTS)})


def describe(endpoints: dict, recovery_enabled: bool) -> dict:
    return {'target': endpoints['target'],
            'recovery_enabled': recovery_enabled,
            'restore_exercised': False,
            'obligations': ['An exercised restore remains an external recovery obligation',
                            'The provisioner does not verify backup completion']}