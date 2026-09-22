"""Nutanix realization boundary.

Domain isolation is realized as an independent Nutanix VPC domain; the security
edge owns any qualified handoff. Nothing here contacts Prism Central.
"""
from __future__ import annotations

from provisioner.adapters.base import Adapter, _adapter

LIMITS = (
    'Nutanix product tuple is unselected in the capability registry',
    'Domain isolation and route handoff remain unqualified natively',
)


def adapter() -> Adapter:
    return _adapter('nutanix', 'nutanix-route', LIMITS)