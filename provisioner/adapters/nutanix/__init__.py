"""Nutanix realization boundary.

Domain isolation is realized as an independent Nutanix VPC domain; the security
edge owns any qualified handoff. Nothing here contacts Prism Central.
"""
from __future__ import annotations

from provisioner.adapters.base import (Adapter, WorkloadLifecycle,
                                       WorkloadLifecycleMode, _adapter)

LIMITS = (
    'Nutanix product tuple is unselected in the capability registry',
    'Domain isolation and route handoff remain unqualified natively',
)


WORKLOAD_LIFECYCLE = WorkloadLifecycle(WorkloadLifecycleMode.SAVED_PLAN, 'terraform_apply')

def adapter() -> Adapter:
    return _adapter('nutanix', 'nutanix-route', LIMITS,
                    workload_lifecycle=WORKLOAD_LIFECYCLE)
