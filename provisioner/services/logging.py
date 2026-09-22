"""Logging service declaration.

Logging is a collector handoff. The provisioner records the reviewed collectors
and the audit requirement the profile implies. It does not configure retention,
tamper protection or shipping guarantees.
"""
from __future__ import annotations

from provisioner.domain.errors import ProvisioningError

SERVICE = 'logging'
REQUIRED_ENDPOINTS = ('collectors',)


def validate(endpoints: dict, site: str) -> None:
    missing = [name for name in REQUIRED_ENDPOINTS if not endpoints.get(name)]
    if missing:
        raise ProvisioningError('SERVICE_UNAVAILABLE',
                                f'{SERVICE} binding at {site} is incomplete: {missing}',
                                path=f'inventory.services.{SERVICE}',
                                details={'required_endpoints': list(REQUIRED_ENDPOINTS)})


def describe(endpoints: dict, protected: bool) -> dict:
    return {'collectors': list(endpoints['collectors']),
            'audit_required': True,
            'protected_class': protected,
            'obligations': ['Retention and tamper protection remain owner obligations',
                            'The provisioner does not verify shipping']}