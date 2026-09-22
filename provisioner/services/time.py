"""Time service declaration.

Time is an internal-source handoff. The provisioner records the reviewed time
sources. Accuracy of the source itself is an external operating obligation.
"""
from __future__ import annotations

from provisioner.domain.errors import ProvisioningError

SERVICE = 'ntp'
REQUIRED_ENDPOINTS = ('sources',)


def validate(endpoints: dict, site: str) -> None:
    missing = [name for name in REQUIRED_ENDPOINTS if not endpoints.get(name)]
    if missing:
        raise ProvisioningError('SERVICE_UNAVAILABLE',
                                f'{SERVICE} binding at {site} is incomplete: {missing}',
                                path=f'inventory.services.{SERVICE}',
                                details={'required_endpoints': list(REQUIRED_ENDPOINTS)})


def describe(endpoints: dict) -> dict:
    return {'sources': list(endpoints['sources']),
            'obligations': ['Time-source accuracy remains an external operating obligation']}